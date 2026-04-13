"""Tool: finalize_resume

Finalize a draft only after required claim verification.
"""
from __future__ import annotations

from typing import Any

from engine.audit import log_event
from engine.contracts import ContractValidationError
from helpers.naming import suggest_output_path
import engine.session as session_state


def finalize_resume(
    resume_draft: str,
    verification_answers: list[dict[str, Any]],
    unresolved_verification_count: int,
    selected_profile: str = "tech",
) -> dict[str, Any]:
    """Finalize a draft only after all claim verifications are resolved.

    The server recomputes ``unresolved_verification_count`` from the
    actual *verification_answers* rather than trusting the client value,
    preventing bypass of the verification gate.

    Args:
        resume_draft: Draft resume text to finalize.
        verification_answers: Answered verification items, each with
            ``question``, ``status`` (verified/rejected/deferred), and
            ``value``.
        unresolved_verification_count: Client-reported unresolved count
            (server overrides if lower than actual).
        selected_profile: Policy profile key.

    Returns:
        Tool response dict with ``status`` of ``"finalized"`` or
        ``"blocked"`` and ``blocked_reasons`` when applicable.
    """
    payload = {
        "resume_draft": resume_draft,
        "verification_answers": verification_answers,
        "unresolved_verification_count": unresolved_verification_count,
        "selected_profile": selected_profile,
        "resume_type": selected_profile,
    }

    try:
        session_state.contracts.validate_input("finalize_resume", payload)
    except ContractValidationError as exc:
        return {"status": "error", "error": str(exc)}

    # Strict gate: recompute unresolved count server-side from the actual
    # verification_answers rather than trusting the client-supplied number.
    # This prevents a caller from passing 0 to bypass the gate.
    non_verified = [
        ans for ans in verification_answers
        if ans.get("status") != "verified"
    ]
    deferred = [
        ans for ans in verification_answers
        if ans.get("status") == "deferred"
    ]
    rejected = [
        ans for ans in verification_answers
        if ans.get("status") == "rejected"
    ]

    # Server-authoritative count: at least as high as non-verified answers
    # or the client hint — whichever is larger.
    still_unresolved = max(unresolved_verification_count, len(non_verified))

    blocked_reasons: list[str] = []

    # Warn when client count disagrees with reality
    if unresolved_verification_count < len(non_verified):
        blocked_reasons.append(
            f"Client reported {unresolved_verification_count} unresolved but "
            f"server found {len(non_verified)} non-verified answer(s); "
            "using server count"
        )

    if still_unresolved > 0:
        blocked_reasons.append(
            f"{still_unresolved} unresolved verification item(s) remain"
        )
    if deferred:
        blocked_reasons.append(
            f"{len(deferred)} verification answer(s) are deferred; "
            "deferred claims cannot appear in the final resume"
        )
    if rejected:
        blocked_reasons.append(
            f"{len(rejected)} verification answer(s) were rejected; "
            "rejected claims must be removed from the draft"
        )

    result: dict[str, Any] = {
        "status": "finalized" if still_unresolved == 0 else "blocked",
        "resume_final": resume_draft if still_unresolved == 0 else "",
        "blocked_reasons": blocked_reasons,
        "selected_profile": selected_profile,
        "unresolved_verification_count": still_unresolved,
    }

    # Override payload count so the policy engine sees the server-side value
    payload["unresolved_verification_count"] = still_unresolved

    # Suggest output path for the finalized file
    path_info = suggest_output_path(
        target_role=f"{selected_profile}-resume",
        target_company="",
    )
    result["suggested_output"] = {
        "path": f"{path_info['root']}/detailed/",
        "filename": f"{path_info['file_stem']}{path_info['extension']}",
    }

    log_event("tool_call", "finalize_resume", payload)
    return session_state.finalize_tool_response("finalize_resume", payload, result)


TOOL_DEF = {
    "name": "finalize",
    "description": (
        "Finalize a resume draft after all verification questions are "
        "answered.\n\n"
        "Blocked by policy if unresolved verification items remain or if "
        "the Quick Match stage has not been run first.\n\n"
        "Args:\n"
        "    resume_draft: The draft resume text to finalize.\n"
        "    verification_answers: List of answered verification items, each with "
        "question, status (verified/rejected/deferred), and value.\n"
        "    unresolved_verification_count: Number of still-unresolved verification items.\n"
        "    selected_profile: Resume profile used — tech, non_tech, hybrid, or executive."
    ),
    "parameters": {
        "resume_draft": {"type": "str", "required": True},
        "verification_answers": {"type": "list[dict[str, Any]]", "required": True},
        "unresolved_verification_count": {"type": "int", "required": True},
        "selected_profile": {"type": "str", "required": False, "default": "tech"},
    },
    "handler": finalize_resume,
}
