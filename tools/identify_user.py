"""Tool: identify_user

Identify the current user by name or proceed anonymously.
"""
from __future__ import annotations

from typing import Any

from engine.audit import log_event
from engine.contracts import ContractValidationError
import engine.session as session_state


def identify_user(
    user_name: str = "",
) -> dict[str, Any]:
    """Identify the active user or proceed anonymously.

    If *user_name* is provided the server creates (or re-opens) a private
    data directory for that user.  All subsequent tool calls will draw on
    that user's stored skills, preferences, and history.

    If *user_name* is omitted or empty the session continues in anonymous
    mode — all tools work normally but no data is persisted and
    supplemental skills are unavailable.
    """
    name = (user_name or "").strip()
    payload: dict[str, Any] = {"user_name": name} if name else {}

    try:
        session_state.contracts.validate_input("identify_user", payload)
    except ContractValidationError as exc:
        return {"status": "error", "error": str(exc)}

    if name:
        ctx = session_state.user_store.identify(name)
    else:
        ctx = session_state.user_store.get_anonymous()

    session_state.set_current_user(ctx)

    # Gather stats for the greeting
    skills = session_state.user_store.get_skills(ctx)
    history = session_state.user_store.get_session_history(ctx, limit=1)
    prefs = session_state.user_store.get_preferences(ctx)

    if ctx.is_anonymous:
        message = (
            "Proceeding in anonymous mode. Your session will work normally "
            "but no data will be stored between sessions and supplemental "
            "skills are not available. You can identify yourself at any "
            "time by calling this tool with your name."
        )
    elif history:
        last = history[-1]
        message = (
            f"Welcome back, {ctx.display_name}! "
            f"You have {len(skills)} stored skill(s). "
            f"Your last session used the '{last.get('tool', 'unknown')}' tool."
        )
    else:
        message = (
            f"Hello, {ctx.display_name}! A personal profile has been "
            f"created for you. You can add supplemental skills with the "
            f"manage_skills tool and they will be used in future resume "
            f"mapping and drafting."
        )

    result: dict[str, Any] = {
        "user_name": ctx.display_name,
        "user_slug": ctx.slug,
        "is_anonymous": ctx.is_anonymous,
        "stored_skills_count": len(skills),
        "message": message,
    }

    if prefs:
        result["preferences"] = prefs

    return session_state.finalize_tool_response("identify_user", payload, result)


TOOL_DEF = {
    "name": "identify_user",
    "description": (
        "Identify yourself so the server can load your stored skills, "
        "preferences, and session history. If you decline or omit your "
        "name, the session continues anonymously with no data stored.\n\n"
        "Args:\n"
        "    user_name: Your name (e.g. 'John Smith'). Leave empty for anonymous mode."
    ),
    "parameters": {
        "user_name": {"type": "str", "required": False, "default": ""},
    },
    "handler": identify_user,
}
