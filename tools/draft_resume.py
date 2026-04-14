"""Tool: generate_resume_draft

Generate draft resume with tagged claims and verification questions.
"""
from __future__ import annotations

from typing import Any

from engine.audit import log_event
from engine.contracts import ContractValidationError
from helpers.naming import build_workspace_setup, suggest_output_path
from helpers.questions import after_draft_resume
import engine.session as session_state


def generate_resume_draft(
    resume_source: str,
    mapping_result: dict[str, Any],
    target_role: str,
    target_company: str = "",
    resume_type: str = "tech",
    audience: str = "hiring_manager",
    output_format: str = "md",
) -> dict[str, Any]:
    """Generate a draft resume with tagged claims and verification questions.

    Every claim is provenance-tagged (VERIFIED, INFERRED, STRETCH,
    USER-VERIFY, or USER-PROFILE).  Uncertain items are surfaced as
    ``verification_questions`` that must be resolved before
    :func:`finalize_resume` will unblock.

    Args:
        resume_source: Original resume text to build from.
        mapping_result: Output from :func:`map_resume_to_requirements`.
        target_role: Target job title.
        target_company: Optional company name.
        resume_type: Profile key — tech, non_tech, hybrid, or executive.
        audience: Intended reader.
        output_format: Output format (md, txt, docx, or pdf).

    Returns:
        Tool response dict processed through
        :func:`engine.session.finalize_tool_response`.
    """
    payload = {
        "resume_source": resume_source,
        "mapping_result": mapping_result,
        "target_role": target_role,
        "target_company": target_company,
        "resume_type": resume_type,
        "audience": audience,
        "output_format": output_format,
    }

    try:
        session_state.contracts.validate_input("generate_resume_draft", payload)
    except ContractValidationError as exc:
        return {"status": "error", "error": str(exc)}

    sess = session_state.get_session()
    profile, reasoning = session_state.engine.resolve_profile(payload, sess)
    required_sections = session_state.engine.get_required_sections(profile)

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
            if s.get("context"):
                line += f" — {s['context']}"
            skill_lines.append(line)
        supplemental_block = (
            "\n\nSupplemental Skills (from user profile — include where "
            "relevant, tag as USER-PROFILE in evidence_log, add a "
            "verification question for each skill used only from profile):\n"
            + "\n".join(f"- {l}" for l in skill_lines)
        )

    result: dict[str, Any] = {
        "resume_draft": "",
        "evidence_log": [],
        "verification_questions": [],
        "unresolved_verification_count": 0,
        "selected_profile": profile,
        "profile_reasoning": reasoning,
        "supplemental_skills_used": [s.get("name", "") for s in stored_skills],
        "instruction": (
            f"Generate a resume draft for '{target_role}'"
            + (f" at {target_company}" if target_company else "")
            + f" using profile '{profile}'. "
            f"Required sections: {required_sections}. "
            "Every claim must have a provenance tag "
            "(VERIFIED, INFERRED, STRETCH, USER-VERIFY, or USER-PROFILE). "
            "Collect all uncertain items as verification_questions. "
            "Set unresolved_verification_count to the number of [USER-VERIFY] items. "
            "Use Action + Context + Result bullet format.\n\n"
            "WORKSPACE RULE: Save draft output to the path in suggested_path "
            "(under resume-workspace/tailored/company-role-YYYY-MM/). "
            "Do NOT create alternative folder structures. Use ONLY the "
            "workspace layout from workspace_setup."
            + supplemental_block
        ),
    }

    # Workspace setup — safety re-check before file writes
    result["workspace_setup"] = build_workspace_setup(
        target_role=target_role,
        target_company=target_company,
    )

    # Suggested output path for this draft
    path_info = suggest_output_path(target_role, target_company)
    result["suggested_path"] = f"{path_info['root']}/v1/"
    result["suggested_filename"] = f"{path_info['file_stem']}{path_info['extension']}"

    # Interactive questions — stretch verification
    result["interactive"] = after_draft_resume(
        verification_questions=result["verification_questions"],
        evidence_log=result["evidence_log"],
        profile=profile,
    )

    sess["selected_profile"] = profile

    log_event("tool_call", "generate_resume_draft", payload)
    return session_state.finalize_tool_response("generate_resume_draft", payload, result)


TOOL_DEF = {
    "name": "draft_resume",
    "description": (
        "Generate a draft resume with tagged claims and verification "
        "questions.\n\n"
        "Args:\n"
        "    resume_source: Original resume text to build from.\n"
        "    mapping_result: Output from the map_resume tool.\n"
        "    target_role: Target job title (e.g. 'Senior Infrastructure Engineer').\n"
        "    target_company: Optional target company name.\n"
        "    resume_type: Resume profile — tech, non_tech, hybrid, or executive.\n"
        "    audience: Who will read this — hiring_manager, recruiter, executive_panel, or ats.\n"
        "    output_format: Output format — md, txt, docx, or pdf."
    ),
    "parameters": {
        "resume_source": {"type": "str", "required": True},
        "mapping_result": {"type": "dict[str, Any]", "required": True},
        "target_role": {"type": "str", "required": True},
        "target_company": {"type": "str", "required": False, "default": ""},
        "resume_type": {"type": "str", "required": False, "default": "tech"},
        "audience": {"type": "str", "required": False, "default": "hiring_manager"},
        "output_format": {"type": "str", "required": False, "default": "md"},
    },
    "handler": generate_resume_draft,
}
