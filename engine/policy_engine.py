"""Policy engine for MCP resume rule enforcement.

Loads policy-rules.yaml from the policies/ directory and evaluates
tool actions against truthfulness, verification, workflow, quality, and
formatting rules.  Returns a PolicyDecision indicating whether the action
is blocked and which sections the output must contain.
"""
from __future__ import annotations

import os
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

VALID_PROFILES = {"tech", "non_tech", "hybrid", "executive"}

POLICY_PATH = Path(os.environ.get(
    "POLICY_PACK_PATH",
    Path(__file__).resolve().parent.parent / "policies" / "policy-rules.yaml",
))


@dataclass
class PolicyDecision:
    """Result of a policy evaluation.

    Attributes:
        blocked: ``True`` if at least one hard-stop policy was violated.
        reasons: Human-readable list of violation/warning descriptions.
        required_sections: Resume sections the selected profile requires.
        selected_profile: Resolved resume profile (tech/non_tech/hybrid/executive).
        profile_reasoning: Why this profile was selected.
        violations: Machine-readable list of violation dicts with policy IDs.
    """

    blocked: bool
    reasons: list[str]
    required_sections: list[str]
    selected_profile: str
    profile_reasoning: str = ""
    violations: list[dict[str, Any]] = field(default_factory=list)


# ATS-unsafe patterns that should not appear in resume output
_ATS_FORBIDDEN = re.compile(
    r"(?:"
    r"\|.*\|.*\|"          # markdown tables
    r"|<[a-zA-Z][^>]*>"     # HTML tags
    r"|!\[.*\]\(.*\)"      # image embeds
    r")",
    re.MULTILINE,
)


class PolicyEngine:
    """Load and evaluate policy rules from a YAML configuration file.

    The engine resolves resume profiles, retrieves required sections per
    profile, and evaluates tool outputs against P0–P4 policy tiers.

    Args:
        policy_file: Optional override path to ``policy-rules.yaml``.
    """

    def __init__(self, policy_file: str | Path | None = None):
        self.policy_file = Path(policy_file) if policy_file else POLICY_PATH
        self.config = self._load_policy()

    def _load_policy(self) -> dict[str, Any]:
        with self.policy_file.open("r", encoding="utf-8") as fh:
            return yaml.safe_load(fh)

    @property
    def profiles(self) -> dict[str, Any]:
        return self.config.get("profiles", {})

    @property
    def guardrails(self) -> dict[str, Any]:
        """Return configurable guardrail thresholds from policy YAML."""
        return self.config.get("guardrails", {})

    def resolve_profile(
        self,
        input_payload: dict[str, Any],
        context: dict[str, Any] | None = None,
    ) -> tuple[str, str]:
        """Determine the resume profile and return ``(profile_name, reasoning)``.

        Resolution order:
        1. Explicit ``resume_type`` in *input_payload* if it's a valid profile.
        2. ``executive`` if audience is ``executive_panel``.
        3. ``hybrid`` if domain-shift score ≥ 0.35.
        4. ``tech`` as the default fallback.

        Args:
            input_payload: Tool input dict (may contain ``resume_type``, ``audience``).
            context: Session context dict (may contain ``domain_shift_score``).

        Returns:
            Tuple of ``(profile_name, reasoning_string)``.
        """
        context = context or {}

        requested = input_payload.get("resume_type")
        if requested in VALID_PROFILES:
            return requested, f"User explicitly requested '{requested}' profile"

        audience = input_payload.get("audience")
        if audience == "executive_panel":
            return "executive", "Audience is executive_panel; defaulting to executive profile"

        domain_shift = float(context.get("domain_shift_score", 0))
        if domain_shift >= 0.35:
            return "hybrid", f"Domain-shift score {domain_shift:.2f} >= 0.35; defaulting to hybrid"

        return "tech", "No explicit resume_type or audience signal; defaulting to tech"

    def get_required_sections(self, profile: str) -> list[str]:
        """Return the list of required resume sections for *profile*."""
        info = self.profiles.get(profile, {})
        return list(info.get("required_sections", []))

    def evaluate(
        self,
        action: str,
        output: dict[str, Any],
        input_payload: dict[str, Any] | None = None,
        context: dict[str, Any] | None = None,
    ) -> PolicyDecision:
        """Evaluate a tool action against all policy tiers.

        Checks P0 (truth/provenance), P1 (verification gate), P2 (workflow
        order), P4 (ATS formatting), and P5 (user-profile corroboration)
        rules.  Returns a :class:`PolicyDecision` indicating whether the
        action is blocked along with all violations found.

        Args:
            action: Tool action name (e.g. ``"finalize_resume"``).
            output: Tool result dict to evaluate.
            input_payload: Original tool input dict.
            context: Per-user session context dict.

        Returns:
            A :class:`PolicyDecision` with blocked status, reasons, and
            required sections.
        """
        context = context or {}
        input_payload = input_payload or {}
        blocked = False
        reasons: list[str] = []
        violations: list[dict[str, Any]] = []

        selected_profile, profile_reasoning = self.resolve_profile(input_payload, context)
        output_profile = output.get("selected_profile")

        required_sections = self.get_required_sections(selected_profile)

        unresolved = int(output.get("unresolved_verification_count", 0))
        has_quick_match = bool(context.get("has_quick_match", False))
        evidence_log: list[dict[str, Any]] = output.get("evidence_log", [])
        resume_draft: str = output.get("resume_draft", "")

        # -- configurable thresholds from policy YAML -----------------------
        guard = self.guardrails
        low_confidence_floor = float(guard.get("low_confidence_floor", 0.4))
        min_evidence_entries = int(guard.get("min_evidence_entries", 1))

        # P0: provenance tags — report ALL violations, not just the first
        valid_tags = {"VERIFIED", "INFERRED", "STRETCH", "USER-VERIFY", "USER-PROFILE"}
        for item in evidence_log:
            if item.get("tag") not in valid_tags:
                blocked = True
                reasons.append(f"Claim tag '{item.get('tag')}' is not a valid provenance tag")
                violations.append({"policy": "P0_REQUIRE_PROVENANCE_TAG", "detail": item})

        # P0: evidence coverage — drafts must have at least N evidence entries
        if action in {"generate_draft", "generate_resume_draft"}:
            if len(evidence_log) < min_evidence_entries:
                blocked = True
                reasons.append(
                    f"Evidence log has {len(evidence_log)} entries; "
                    f"minimum {min_evidence_entries} required to prevent uncovered claims"
                )
                violations.append({"policy": "P0_NO_FABRICATION", "evidence_count": len(evidence_log)})

        # P0: confidence threshold — STRETCH/INFERRED below floor must be
        # escalated to USER-VERIFY so the human is asked to confirm.
        for item in evidence_log:
            tag = item.get("tag", "")
            confidence = float(item.get("confidence", 1.0))
            if tag in {"STRETCH", "INFERRED"} and confidence < low_confidence_floor:
                blocked = True
                req = item.get("requirement", "unknown")
                reasons.append(
                    f"Claim for '{req}' tagged [{tag}] has confidence "
                    f"{confidence:.0%} below floor {low_confidence_floor:.0%}; "
                    f"must be tagged USER-VERIFY"
                )
                violations.append({
                    "policy": "P0_NO_FABRICATION",
                    "requirement": req,
                    "tag": tag,
                    "confidence": confidence,
                })

        # P0: empty evidence — every evidence_log entry must have substance
        for item in evidence_log:
            if not (item.get("resume_evidence") or "").strip():
                blocked = True
                req = item.get("requirement", "unknown")
                reasons.append(
                    f"Evidence entry for '{req}' has empty resume_evidence; "
                    "every claim must cite source text"
                )
                violations.append({"policy": "P0_NO_FABRICATION", "requirement": req, "field": "resume_evidence"})

        # P1: finalize gate
        if action in {"finalize_resume", "export_resume"} and unresolved > 0:
            blocked = True
            reasons.append(f"Unresolved verification-required claims exist ({unresolved})")
            violations.append({"policy": "P1_SOFT_STOP_FINALIZE_GATE", "unresolved": unresolved})

        # P1: profile consistency
        if output_profile is not None and output_profile != selected_profile:
            blocked = True
            reasons.append(f"Output profile '{output_profile}' does not match selected profile '{selected_profile}'")
            violations.append({"policy": "P1_REQUIRE_PROFILE_IN_OUTPUT"})

        # P2: two-stage workflow
        if action == "finalize_resume" and not has_quick_match:
            blocked = True
            reasons.append("Quick Match stage must run before finalization")
            violations.append({"policy": "P2_REQUIRE_TWO_STAGE_FLOW"})

        # P4: ATS-safe output — scan resume_draft for forbidden patterns
        if resume_draft:
            ats_matches = _ATS_FORBIDDEN.findall(resume_draft)
            if ats_matches:
                reasons.append(
                    f"Resume contains {len(ats_matches)} ATS-unsafe pattern(s): "
                    + ", ".join(repr(m[:40]) for m in ats_matches[:3])
                )
                violations.append({"policy": "P4_ATS_SAFE_OUTPUT", "count": len(ats_matches)})

        # P5: USER-PROFILE claims must be corroborated before finalize
        if action in {"finalize_resume", "export_resume"}:
            uncorroborated = [
                item for item in evidence_log
                if item.get("tag") == "USER-PROFILE"
                and float(item.get("confidence", 0)) < 0.7
            ]
            if uncorroborated:
                blocked = True
                names = [i.get("requirement", "?") for i in uncorroborated[:5]]
                reasons.append(
                    f"{len(uncorroborated)} USER-PROFILE claim(s) lack resume "
                    f"corroboration: {', '.join(names)}"
                )
                violations.append({
                    "policy": "P5_USER_PROFILE_REQUIRES_VERIFICATION",
                    "count": len(uncorroborated),
                })

        # Claim density sanity check — warn when bullet count far exceeds
        # evidence entries (potential uncovered hallucinated claims).
        if resume_draft and evidence_log:
            bullet_count = len(re.findall(r"^\s*[-•*]\s", resume_draft, re.MULTILINE))
            if bullet_count > 0 and len(evidence_log) > 0:
                ratio = bullet_count / len(evidence_log)
                if ratio > 2.0:
                    reasons.append(
                        f"Claim density warning: {bullet_count} bullets vs "
                        f"{len(evidence_log)} evidence entries (ratio {ratio:.1f}x); "
                        "some bullets may lack provenance"
                    )
                    violations.append({
                        "policy": "P0_NO_FABRICATION",
                        "subtype": "claim_density",
                        "bullet_count": bullet_count,
                        "evidence_count": len(evidence_log),
                    })

        # Draft requires verification_questions section
        if action in {"generate_draft", "generate_resume_draft"}:
            if "verification_questions" not in required_sections:
                required_sections.append("verification_questions")

        return PolicyDecision(
            blocked=blocked,
            reasons=reasons,
            required_sections=required_sections,
            selected_profile=selected_profile,
            profile_reasoning=profile_reasoning,
            violations=violations,
        )
