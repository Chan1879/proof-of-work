"""Tool: analyze_job_description

Extract and prioritize requirements from one or more job descriptions.
"""
from __future__ import annotations

from typing import Any

from engine.audit import log_event
from engine.contracts import ContractValidationError
from helpers.naming import build_workspace_setup
from helpers.questions import after_analyze_jd
import engine.session as session_state


def analyze_job_description(
    job_descriptions: list[str],
    target_level: str,
    role_focus: str = "",
    resume_type: str = "tech",
    audience: str = "hiring_manager",
) -> dict[str, Any]:
    """Extract and prioritise requirements from one or more job descriptions.

    Resolves a policy profile, builds workspace-setup instructions, and
    generates interactive follow-up questions for the calling LLM.

    Args:
        job_descriptions: 1–3 JD texts (each ≥50 chars).
        target_level: Seniority band (Senior / Staff / Principal / VP).
        role_focus: Optional keyword focus area (e.g. ``"cloud"``).
        resume_type: Profile key — tech, non_tech, hybrid, or executive.
        audience: Intended reader — hiring_manager, recruiter, etc.

    Returns:
        Tool response dict processed through
        :func:`engine.session.finalize_tool_response`.
    """
    payload = {
        "job_descriptions": job_descriptions,
        "target_level": target_level,
        "role_focus": role_focus,
        "resume_type": resume_type,
        "audience": audience,
    }

    try:
        session_state.contracts.validate_input("analyze_job_description", payload)
    except ContractValidationError as exc:
        return {"status": "error", "error": str(exc)}

    sess = session_state.get_session()
    profile, reasoning = session_state.engine.resolve_profile(payload, sess)

    result: dict[str, Any] = {
        "requirements": [],
        "commonality": [],
        "must_have": [],
        "nice_to_have": [],
        "selected_profile": profile,
        "profile_reasoning": reasoning,
        "jd_count": len(job_descriptions),
        "target_level": target_level,
        "instruction": (
            "Analyze the provided job description(s) and populate "
            "'requirements', 'must_have', 'nice_to_have', and 'commonality'. "
            f"Use the '{profile}' resume profile to prioritize signals. "
            "Tag uncertain inferences as [INFERRED].\n\n"
            "WORKSPACE RULE: Before saving any output, verify the workspace "
            "follows the structure in workspace_setup. If no resume-workspace/ "
            "exists, ask the user: 'Would you like me to create the resume "
            "workspace structure?' Create ONLY the folders listed in "
            "workspace_setup.directories — do NOT invent numbered folders "
            "(01-input/, 02-analysis/, etc.) or extra directories. "
            "Save analysis output to tailored/company-role-YYYY-MM/jd-analysis.md."
        ),
    }

    # Workspace setup — client should verify/create directory structure
    result["workspace_setup"] = build_workspace_setup(
        target_role=role_focus or target_level,
        target_company="",
    )

    # Interactive questions for the LLM to relay
    result["interactive"] = after_analyze_jd(
        nice_to_have=result["nice_to_have"],
        must_have=result["must_have"],
        target_level=target_level,
        role_focus=role_focus,
        profile=profile,
    )

    # Update session
    sess["has_quick_match"] = True
    sess["selected_profile"] = profile
    sess["profile_reasoning"] = reasoning

    log_event("tool_call", "analyze_job_description", payload)
    return session_state.finalize_tool_response("analyze_job_description", payload, result)


TOOL_DEF = {
    "name": "analyze_jd",
    "description": (
        "Analyze one or more job descriptions and extract prioritized "
        "requirements.\n\n"
        "Args:\n"
        "    job_descriptions: List of 1-3 job description texts (each at least 50 chars).\n"
        "    target_level: Career level — Senior, Staff, Principal, or VP.\n"
        "    role_focus: Optional keyword focus area (e.g. 'cloud', 'security').\n"
        "    resume_type: Resume profile — tech, non_tech, hybrid, or executive.\n"
        "    audience: Who will read this — hiring_manager, recruiter, executive_panel, or ats."
    ),
    "parameters": {
        "job_descriptions": {"type": "list[str]", "required": True},
        "target_level": {"type": "str", "required": True},
        "role_focus": {"type": "str", "required": False, "default": ""},
        "resume_type": {"type": "str", "required": False, "default": "tech"},
        "audience": {"type": "str", "required": False, "default": "hiring_manager"},
    },
    "handler": analyze_job_description,
}
