"""Interactive question generation for MCP resume tools.

Each public function returns an ``interactive`` dict suitable for embedding
directly into a tool's response payload.  The calling LLM is expected to
relay questions/suggestions to the user and feed answers back into the
next tool invocation.

Structure::

    {
        "questions":             [...],  # things that need user answers
        "suggestions":           [...],  # proactive recommendations
        "verification_needed":   [...],  # stretch claims needing confirmation
    }
"""
from __future__ import annotations

from typing import Any


def _empty() -> dict[str, list]:
    """Return a blank interactive payload skeleton."""
    return {"questions": [], "suggestions": [], "verification_needed": []}


# ---------------------------------------------------------------------------
# analyze_jd interactivity
# ---------------------------------------------------------------------------
def after_analyze_jd(
    *,
    nice_to_have: list[str],
    must_have: list[str],
    target_level: str,
    role_focus: str,
    profile: str,  # noqa: ARG001 — reserved for profile-specific logic
) -> dict[str, list]:
    """Generate detail-gathering questions after JD analysis.

    Args:
        nice_to_have: Skills listed as preferred/optional in the JD.
        must_have: Hard requirements from the JD.
        target_level: Seniority band detected (e.g. ``"senior"``).
        role_focus: Primary domain of the role.
        profile: Policy profile key (reserved for future use).

    Returns:
        Interactive payload with ``questions`` and ``suggestions``.
    """
    interactive = _empty()

    # Ask about nice-to-have skills the user might actually have
    if nice_to_have:
        interactive["questions"].append(
            "The job description lists these as nice-to-have skills: "
            + ", ".join(nice_to_have[:5])
            + ". Do you have experience with any of these? "
            "If so, please describe briefly so we can strengthen your resume."
        )

    # Ask about ambiguous must-haves
    if must_have:
        interactive["questions"].append(
            "Some must-have requirements may need clarification. "
            "For each of the following, do you have direct or adjacent "
            "experience? " + ", ".join(must_have[:5])
        )

    # Proactively suggest adding context
    if role_focus:
        interactive["suggestions"].append(
            f"The role focuses on '{role_focus}'. Do you have specific "
            "projects, metrics, or outcomes in this area you'd like highlighted?"
        )

    interactive["suggestions"].append(
        f"Target level is '{target_level}'. To strengthen your resume, "
        "consider adding scope indicators (team size, budget, org impact) "
        "if you haven't already."
    )

    return interactive


# ---------------------------------------------------------------------------
# map_resume interactivity
# ---------------------------------------------------------------------------
def after_map_resume(
    *,
    missing: list[dict[str, Any]],
    partials: list[dict[str, Any]],
    profile: str,
    domain_shift_score: float,
) -> dict[str, list]:
    """Generate gap-analysis questions and career-pivot suggestions.

    Args:
        missing: Requirements not matched by any user skill.
        partials: Requirements only partially matched.
        profile: Policy profile key (e.g. ``"non_tech"``).
        domain_shift_score: 0.0–1.0 measure of career-pivot magnitude.

    Returns:
        Interactive payload with ``questions``, ``suggestions``, and
        possible ``verification_needed`` items.
    """
    interactive = _empty()

    # Suggest adjacent skills for missing requirements
    if missing:
        missing_names = [m.get("requirement", str(m)) for m in missing[:5]]
        interactive["questions"].append(
            "You appear to be missing these requirements: "
            + ", ".join(missing_names)
            + ". Do you have related or adjacent experience (side projects, "
            "certifications, volunteer work, or transferable skills from "
            "another domain) that could help fill these gaps?"
        )

    # Partial matches — ask for more evidence
    if partials:
        partial_names = [p.get("requirement", str(p)) for p in partials[:3]]
        interactive["questions"].append(
            "These requirements are partially matched: "
            + ", ".join(partial_names)
            + ". Can you provide additional evidence, metrics, or context "
            "to strengthen these matches?"
        )

    # Volunteer work & special programs prompts
    if missing or profile in ("non_tech", "hybrid", "executive"):
        interactive["suggestions"].append(
            "Do you have volunteer work that demonstrates leadership, "
            "community engagement, or technical mentorship? These can "
            "strengthen your profile, especially for gaps in soft skills "
            "or leadership requirements."
        )
        interactive["suggestions"].append(
            "Have you participated in any special programs — mentorship "
            "cohorts, DEI initiatives, innovation labs, hackathons, or "
            "open-source contributions? These may fill experience gaps "
            "and add a 'Volunteer Experience' or 'Special Programs & "
            "Initiatives' section to your resume."
        )

    # Domain shift warning
    if domain_shift_score >= 0.35:
        interactive["suggestions"].append(
            f"Domain-shift score is {domain_shift_score:.2f} (≥ 0.35). "
            "This suggests a significant career pivot. Consider which "
            "framing works best: aggressive (lean into the new domain), "
            "conservative (emphasize transferable skills), or hybrid."
        )

    return interactive


# ---------------------------------------------------------------------------
# draft_resume interactivity
# ---------------------------------------------------------------------------
def after_draft_resume(
    *,
    verification_questions: list[str],
    evidence_log: list[dict[str, Any]],
    profile: str,
) -> dict[str, list]:
    """Surface stretch claims and verification prompts after drafting.

    Args:
        verification_questions: Free-text questions from the draft engine.
        evidence_log: List of evidence dicts with ``tag`` and ``confidence``.
        profile: Policy profile key.

    Returns:
        Interactive payload with ``verification_needed`` and optional
        ``suggestions``.
    """
    interactive = _empty()

    # Forward verification questions from the draft engine
    for q in verification_questions:
        interactive["verification_needed"].append(q)

    # Add confidence context for STRETCH and USER-VERIFY claims
    for item in evidence_log:
        tag = item.get("tag", "")
        if tag in ("STRETCH", "USER-VERIFY"):
            req = item.get("requirement", "unknown requirement")
            conf = item.get("confidence", 0)
            interactive["verification_needed"].append(
                f"Claim for '{req}' is tagged [{tag}] with confidence "
                f"{conf:.0%}. Please verify this is accurate or suggest "
                "an alternative phrasing."
            )

    # Suggest optional sections if not already present
    if profile in ("non_tech", "hybrid", "executive"):
        interactive["suggestions"].append(
            "Based on your profile type, consider adding a "
            "'Volunteer Experience' or 'Special Programs & Initiatives' "
            "section if you have relevant experience."
        )

    return interactive


# ---------------------------------------------------------------------------
# manage_skills interactivity
# ---------------------------------------------------------------------------
def after_skill_add(
    *,
    skills: list[dict[str, Any]],
) -> dict[str, list]:
    """Generate detail-gathering questions after skills are added.

    Asks the user for additional context (years, category, project
    examples) so each skill can be aligned as strongly as possible to
    future job requirements.

    Args:
        skills: List of skill dicts just persisted (each has at least
            a ``name`` key).

    Returns:
        Interactive payload with ``questions`` and ``suggestions``.
    """
    interactive = _empty()

    for skill in skills:
        name = skill.get("name", "unknown")

        if not skill.get("context"):
            interactive["questions"].append(
                f"For '{name}': Can you describe a specific project, role, "
                "or situation where you applied this skill? This helps us "
                "align it to job requirements more accurately."
            )

        if not skill.get("years_experience"):
            interactive["questions"].append(
                f"For '{name}': Approximately how many years of experience "
                "do you have with this skill?"
            )

        if not skill.get("category"):
            interactive["suggestions"].append(
                f"For '{name}': Consider adding a category (e.g. "
                "'programming', 'cloud', 'leadership', 'data', 'security') "
                "to help match it to the right job requirements."
            )

    if skills:
        interactive["suggestions"].append(
            "Tip: The more context you provide for each skill (proficiency, "
            "years, how/where used), the better the server can align them "
            "to job requirements during resume mapping and drafting."
        )

    return interactive
