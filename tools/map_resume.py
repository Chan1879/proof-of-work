"""Tool: map_resume_to_requirements

Map resume/profile evidence to JD requirements with provenance and confidence.
"""
from __future__ import annotations

from typing import Any

from engine.audit import log_event
from engine.contracts import ContractValidationError
from helpers.questions import after_map_resume
import engine.session as session_state


def map_resume_to_requirements(
    resume_text: str,
    requirements: list[str],
    master_profile: str = "",
    resume_type: str = "tech",
    audience: str = "hiring_manager",
) -> dict[str, Any]:
    """Map resume evidence to JD requirements with provenance and confidence.

    Injects supplemental skills from an identified user's profile when
    available, computes a domain-shift score, and generates interactive
    gap-analysis questions.

    Args:
        resume_text: Full resume text (≥100 chars).
        requirements: Requirement strings to match against the resume.
        master_profile: Optional master-profile content for richer matching.
        resume_type: Profile key — tech, non_tech, hybrid, or executive.
        audience: Intended reader — hiring_manager, recruiter, etc.

    Returns:
        Tool response dict processed through
        :func:`engine.session.finalize_tool_response`.
    """
    payload = {
        "resume_text": resume_text,
        "requirements": requirements,
        "master_profile": master_profile,
        "resume_type": resume_type,
        "audience": audience,
    }

    try:
        session_state.contracts.validate_input("map_resume_to_requirements", payload)
    except ContractValidationError as exc:
        return {"status": "error", "error": str(exc)}

    sess = session_state.get_session()
    profile, _reasoning = session_state.engine.resolve_profile(payload, sess)

    # Load supplemental skills for identified users
    ctx = session_state.current_user
    stored_skills = session_state.user_store.get_skills(ctx) if not ctx.is_anonymous else []
    supplemental_block = ""
    if stored_skills:
        skill_lines = []
        for s in stored_skills:
            line = s.get("name", "")
            if s.get("proficiency"):
                line += f" ({s['proficiency']})"
            if s.get("years_experience"):
                line += f" — {s['years_experience']} yrs"
            if s.get("context"):
                line += f" — {s['context']}"
            skill_lines.append(line)
        supplemental_block = (
            "\n\nSupplemental Skills (from user profile — treat as additional "
            "evidence with default confidence 0.5, tag as USER-PROFILE unless "
            "corroborated by resume text):\n"
            + "\n".join(f"- {l}" for l in skill_lines)
        )

    result: dict[str, Any] = {
        "matches": [],
        "partials": [],
        "missing": [],
        "domain_shift_score": 0.0,
        "selected_profile": profile,
        "supplemental_skills_used": [s.get("name", "") for s in stored_skills],
        "instruction": (
            "Map each requirement against the resume text. "
            "For every mapping include: requirement, status (matched|partial|missing), "
            "confidence (0-1), evidence (exact resume excerpts), "
            "tag (VERIFIED|INFERRED|STRETCH|USER-VERIFY|USER-PROFILE), verification_needed (bool). "
            "Compute domain_shift_score (0-1). "
            f"Apply '{profile}' profile signal preferences.\n\n"
            "WORKSPACE RULE: Save mapping output to "
            "resume-workspace/tailored/company-role-YYYY-MM/mapping.md. "
            "Do NOT create alternative folder structures."
            + supplemental_block
        ),
    }

    # Interactive questions — gap analysis, volunteer prompts
    result["interactive"] = after_map_resume(
        missing=result["missing"],
        partials=result["partials"],
        profile=profile,
        domain_shift_score=result["domain_shift_score"],
    )

    sess["last_mapping"] = result
    sess["selected_profile"] = profile

    log_event("tool_call", "map_resume_to_requirements", payload)
    return session_state.finalize_tool_response("map_resume_to_requirements", payload, result)


TOOL_DEF = {
    "name": "map_resume",
    "description": (
        "Map resume evidence to job requirements with provenance tags and "
        "confidence.\n\n"
        "Args:\n"
        "    resume_text: Full resume text (minimum 100 chars).\n"
        "    requirements: List of requirement strings to match against the resume.\n"
        "    master_profile: Optional master-profile.md content for richer matching.\n"
        "    resume_type: Resume profile — tech, non_tech, hybrid, or executive.\n"
        "    audience: Who will read this — hiring_manager, recruiter, executive_panel, or ats."
    ),
    "parameters": {
        "resume_text": {"type": "str", "required": True},
        "requirements": {"type": "list[str]", "required": True},
        "master_profile": {"type": "str", "required": False, "default": ""},
        "resume_type": {"type": "str", "required": False, "default": "tech"},
        "audience": {"type": "str", "required": False, "default": "hiring_manager"},
    },
    "handler": map_resume_to_requirements,
}
