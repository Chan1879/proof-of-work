"""Tool: manage_skills

Add, list, or remove supplemental skills stored in the user's profile.
Skills persist across sessions and are injected into map_resume /
draft_resume to strengthen evidence mapping.
"""
from __future__ import annotations

from typing import Any

from engine.audit import log_event
from engine.contracts import ContractValidationError
from helpers.questions import after_skill_add
import engine.session as session_state


_VALID_ACTIONS = {"add", "list", "remove"}
_VALID_PROFICIENCIES = {"beginner", "intermediate", "advanced", "expert"}


def manage_skills(
    action: str,
    skills: list[dict[str, Any]] | None = None,
    skill_names: list[str] | None = None,
) -> dict[str, Any]:
    """Add, list, or remove supplemental skills for the current user.

    Supplemental skills are facts about the user's abilities that may not
    appear in the resume text provided to map_resume / draft_resume.  They
    are stored on-disk and survive across sessions for identified users.

    Anonymous users cannot use this tool — identify yourself first with
    the ``identify_user`` tool.
    """
    payload: dict[str, Any] = {"action": action}
    if skills is not None:
        payload["skills"] = skills
    if skill_names is not None:
        payload["skill_names"] = skill_names
    try:
        session_state.contracts.validate_input("manage_skills", payload)
    except ContractValidationError as exc:
        return {"status": "error", "action": action, "error": str(exc)}

    ctx = session_state.current_user

    # Gate: anonymous users cannot manage skills
    if ctx.is_anonymous:
        result = {
            "status": "blocked",
            "action": action,
            "message": (
                "Skill management requires user identification. "
                "Please call the identify_user tool with your name first. "
                "Anonymous sessions do not store any data."
            ),
            "skills": [],
            "count": 0,
        }
        try:
            session_state.contracts.validate_output("manage_skills", result)
        except ContractValidationError as exc:
            return {"status": "error", "action": action, "error": str(exc)}
        return result

    action = (action or "").strip().lower()
    if action not in _VALID_ACTIONS:
        return {
            "status": "error",
            "error": f"Invalid action '{action}'. Must be one of: {', '.join(sorted(_VALID_ACTIONS))}",
        }

    # -- LIST ---------------------------------------------------------------
    if action == "list":
        all_skills = session_state.user_store.get_skills(ctx)
        result = {
            "status": "ok",
            "action": "list",
            "user_slug": ctx.slug,
            "skills": all_skills,
            "count": len(all_skills),
            "message": (
                f"You have {len(all_skills)} stored skill(s)."
                if all_skills
                else "No skills stored yet. Use action 'add' to store supplemental skills."
            ),
        }
        try:
            session_state.contracts.validate_output("manage_skills", result)
        except ContractValidationError as exc:
            return {"status": "error", "action": action, "error": str(exc)}
        return result

    # -- ADD ----------------------------------------------------------------
    if action == "add":
        if not skills:
            return {
                "status": "error",
                "error": "The 'skills' parameter is required for the 'add' action.",
            }

        # Validate and normalise each skill entry
        clean: list[dict[str, Any]] = []
        for raw in skills:
            name = (raw.get("name") or "").strip()
            if not name:
                continue
            prof = (raw.get("proficiency") or "intermediate").strip().lower()
            if prof not in _VALID_PROFICIENCIES:
                prof = "intermediate"
            entry: dict[str, Any] = {
                "name": name,
                "proficiency": prof,
            }
            if raw.get("years_experience") is not None:
                entry["years_experience"] = float(raw["years_experience"])
            if raw.get("context"):
                entry["context"] = str(raw["context"]).strip()
            if raw.get("category"):
                entry["category"] = str(raw["category"]).strip().lower()
            clean.append(entry)

        if not clean:
            return {"status": "error", "error": "No valid skills provided."}

        all_skills = session_state.user_store.add_skills(ctx, clean)

        # Generate interactive prompts asking for detail alignment
        interactive = after_skill_add(skills=clean)

        result: dict[str, Any] = {
            "status": "ok",
            "action": "add",
            "user_slug": ctx.slug,
            "added": clean,
            "skills": all_skills,
            "count": len(all_skills),
            "message": (
                f"Added {len(clean)} skill(s). You now have {len(all_skills)} "
                f"stored skill(s). These will be used as supplemental evidence "
                f"in future resume mapping and drafting."
            ),
        }
        if interactive.get("questions") or interactive.get("suggestions"):
            result["interactive"] = interactive

        log_event(
            event_type="tool_call",
            tool_name="manage_skills",
            payload={"action": "add", "count": len(clean)},
            user_slug=ctx.slug,
        )
        try:
            session_state.contracts.validate_output("manage_skills", result)
        except ContractValidationError as exc:
            return {"status": "error", "action": action, "error": str(exc)}
        return result

    # -- REMOVE -------------------------------------------------------------
    if action == "remove":
        if not skill_names:
            return {
                "status": "error",
                "error": "The 'skill_names' parameter is required for the 'remove' action.",
            }

        remaining = session_state.user_store.remove_skills(ctx, skill_names)
        log_event(
            event_type="tool_call",
            tool_name="manage_skills",
            payload={"action": "remove", "removed": skill_names},
            user_slug=ctx.slug,
        )
        result = {
            "status": "ok",
            "action": "remove",
            "user_slug": ctx.slug,
            "removed": skill_names,
            "skills": remaining,
            "count": len(remaining),
            "message": f"Removed requested skills. {len(remaining)} skill(s) remaining.",
        }
        try:
            session_state.contracts.validate_output("manage_skills", result)
        except ContractValidationError as exc:
            return {"status": "error", "action": action, "error": str(exc)}
        return result

    # Should not reach here
    return {"status": "error", "error": "Unhandled action."}


TOOL_DEF = {
    "name": "manage_skills",
    "description": (
        "Add, list, or remove supplemental skills stored in your personal "
        "profile. These skills persist across sessions and are used as "
        "additional evidence when mapping and drafting resumes.\n\n"
        "Requires user identification (call identify_user first).\n\n"
        "Args:\n"
        "    action: 'add', 'list', or 'remove'.\n"
        "    skills: (for 'add') List of skill dicts with keys: name (required), "
        "proficiency (beginner/intermediate/advanced/expert), years_experience, "
        "context (how/where used), category (e.g. programming, cloud, leadership).\n"
        "    skill_names: (for 'remove') List of skill names to delete."
    ),
    "parameters": {
        "action": {"type": "str", "required": True},
        "skills": {"type": "list[dict]", "required": False, "default": None},
        "skill_names": {"type": "list[str]", "required": False, "default": None},
    },
    "handler": manage_skills,
}
