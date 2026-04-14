"""Shared session state and policy enforcement for MCP resume tools.

Provides per-user in-memory session dicts, singletons for PolicyEngine,
ContractRegistry, and UserStore, and the ``policy_check`` helper that every
tool handler calls after building its result scaffold.
"""
from __future__ import annotations

from typing import Any

from engine.audit import log_event
from engine.contracts import ContractRegistry, ContractValidationError
from engine.policy_engine import PolicyEngine
from helpers.user_store import UserContext, UserStore

engine = PolicyEngine()
contracts = ContractRegistry()
user_store = UserStore()

# ---------------------------------------------------------------------------
# Per-user session state.
# Each key is a user slug; the value is the familiar session dict.
# ``get_session`` lazily creates isolated dicts so tools don't need to know
# whether a user has been seen before.
# ---------------------------------------------------------------------------
_sessions: dict[str, dict[str, Any]] = {}

# The *active* user context — set by the identify_user tool, defaults to
# anonymous.  All tools read ``current_user`` to scope data access.
current_user: UserContext = UserStore.get_anonymous()


def _default_session() -> dict[str, Any]:
    return {
        "has_quick_match": False,
        "selected_profile": None,
        "profile_reasoning": None,
        "last_mapping": None,
        "domain_shift_score": 0.0,
    }


def get_session(user: UserContext | None = None) -> dict[str, Any]:
    """Return the isolated session dict for *user* (or ``current_user``).

    Lazily creates a default session dict on first access so tool handlers
    never need to check whether a user has been seen before.

    Args:
        user: Target user context.  Defaults to the active ``current_user``.

    Returns:
        A mutable dict with keys ``has_quick_match``, ``selected_profile``,
        ``profile_reasoning``, ``last_mapping``, and ``domain_shift_score``.
    """
    ctx = user or current_user
    if ctx.slug not in _sessions:
        _sessions[ctx.slug] = _default_session()
    return _sessions[ctx.slug]


# Convenience alias — existing tools import ``session`` directly.
# After the migration, this always reflects the *active* user's session.
@property  # type: ignore[misc]
def _session_proxy() -> dict[str, Any]:
    return get_session()


# Keep a simple dict reference for backward compatibility.  Existing tools
# do ``from session import session`` and then mutate it.  We initialise to
# the anonymous session; ``set_current_user`` re-binds it.
session: dict[str, Any] = _default_session()


def set_current_user(ctx: UserContext) -> dict[str, Any]:
    """Switch the active user and rebind the module-level ``session`` alias.

    Args:
        ctx: The new active user context.

    Returns:
        The session dict for *ctx*.
    """
    global current_user, session  # noqa: PLW0603
    current_user = ctx
    session = get_session(ctx)
    return session


def policy_check(
    tool_name: str,
    payload: dict[str, Any],
    result: dict[str, Any],
) -> dict[str, Any]:
    """Run policy evaluation and inject profile metadata into *result*.

    Calls ``PolicyEngine.evaluate()`` with the current session context,
    logs the decision to the audit trail, and either returns the enriched
    *result* dict or a ``{"status": "blocked", ...}`` response.

    Args:
        tool_name: MCP tool name (e.g. ``"finalize_resume"``).
        payload: Original tool input dict.
        result: Tool's result scaffold to evaluate.

    Returns:
        The *result* dict (possibly enriched) or a blocked-response dict.
    """
    ctx = current_user
    sess = get_session(ctx)

    decision = engine.evaluate(
        action=tool_name,
        output=result,
        input_payload=payload,
        context=sess,
    )

    # Inject profile fields if handler didn't set them
    result.setdefault("selected_profile", decision.selected_profile)
    result.setdefault("profile_reasoning", decision.profile_reasoning)

    # Inject user slug for traceability
    result.setdefault("user_slug", ctx.slug)

    log_event(
        event_type="policy_eval",
        tool_name=tool_name,
        payload=payload,
        decision={
            "blocked": decision.blocked,
            "reasons": decision.reasons,
            "selected_profile": decision.selected_profile,
        },
        user_slug=ctx.slug,
    )

    if decision.blocked:
        return {
            "status": "blocked",
            "blocked_reasons": decision.reasons,
            "selected_profile": decision.selected_profile,
            "profile_reasoning": decision.profile_reasoning,
            "user_slug": ctx.slug,
        }

    # Record tool call in session history for identified users
    user_store.append_session_history(ctx, {
        "tool": tool_name,
        "selected_profile": decision.selected_profile,
    })

    return result


def finalize_tool_response(
    tool_name: str,
    payload: dict[str, Any],
    result: dict[str, Any],
) -> dict[str, Any]:
    """Run policy checks and output-schema validation for a tool response.

    This is the standard exit path for every tool handler.  It first runs
    :func:`policy_check` and, if the response is not blocked, validates the
    result against the tool's output schema.

    Args:
        tool_name: MCP tool name.
        payload: Original tool input dict.
        result: Tool's result scaffold.

    Returns:
        The validated result dict, a blocked-response dict, or an error dict
        if output schema validation fails.
    """
    checked = policy_check(tool_name, payload, result)

    # Blocked responses use a generic shape and are not validated against
    # the tool-specific success schema.
    if checked.get("status") == "blocked":
        return checked

    try:
        contracts.validate_output(tool_name, checked)
    except ContractValidationError as exc:
        log_event(
            event_type="contract_output_error",
            tool_name=tool_name,
            payload=payload,
            decision={"error": str(exc)},
            user_slug=current_user.slug,
        )
        return {
            "status": "error",
            "error": str(exc),
            "user_slug": current_user.slug,
        }

    return checked
