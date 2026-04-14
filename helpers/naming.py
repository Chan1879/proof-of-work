"""Output naming utilities for MCP resume tools.

Generates suggested directory paths, filenames, and workspace-setup
blocks that the LLM client can relay to the user.  The server never
writes output files itself — these are advisory suggestions only.
"""
from __future__ import annotations

import re
from datetime import datetime, timezone
from pathlib import Path


# Subfolder convention (indirect — avoids "one-pager", "final", etc.)
VARIANT_DIRS = {
    "v1": "First iteration",
    "brief": "Condensed format",
    "detailed": "Full-length format",
    "exec": "Executive summary variant",
}

# ---------------------------------------------------------------------------
# Template loading — read template files shipped with the server
# ---------------------------------------------------------------------------
_TEMPLATES_DIR = Path(__file__).resolve().parent.parent / "templates"


def _read_template(name: str) -> str:
    """Read a template file from the ``templates/`` directory.

    Args:
        name: Filename of the template (e.g. ``"jd-template.md"``).

    Returns:
        Template content as a string, or ``""`` if the file does not exist.
    """
    path = _TEMPLATES_DIR / name
    if path.is_file():
        return path.read_text(encoding="utf-8")
    return ""


# ---------------------------------------------------------------------------
# Canonical workspace structure — the ONLY layout the client should create
# ---------------------------------------------------------------------------

WORKSPACE_STRUCTURE = {
    "root": "resume-workspace",
    "directories": [
        "source",
        "job-descriptions",
        "tailored",
        "archive",
        "archive/old-resumes",
    ],
    "seed_files": {
        "source/master-profile.md": "master-profile-template.md",
        "job-descriptions/template.md": "jd-template.md",
    },
    "directory_descriptions": {
        "source": (
            "Base resumes and master-profile.md — the comprehensive "
            "'everything' resume used by map_resume"
        ),
        "job-descriptions": (
            "One .md file per job description, named company-role-YYYY-MM.md. "
            "Copy template.md for each new JD."
        ),
        "tailored": (
            "One subfolder per application named company-role-YYYY-MM/, "
            "containing jd-analysis.md, mapping.md, draft.md, final.md"
        ),
        "archive": "Older resume versions kept for reference",
        "archive/old-resumes": "Previous resume versions",
    },
}


def build_full_workspace_setup() -> dict:
    """Return the canonical workspace setup with explicit agent instructions.

    This is the AUTHORITATIVE workspace layout.  The client agent MUST use
    this structure — not invent numbered folders, nested hierarchies, or
    alternative naming.  The response includes:

    - ``directories``: exact folder list to create
    - ``seed_files``: files to populate from ``template_content``
    - ``template_content``: actual file contents keyed by destination path
    - ``agent_instructions``: explicit directives the client agent must follow
    """
    templates: dict[str, str] = {}
    for dest, tpl_name in WORKSPACE_STRUCTURE["seed_files"].items():
        content = _read_template(tpl_name)
        if content:
            templates[dest] = content

    return {
        "recommended_root": WORKSPACE_STRUCTURE["root"],
        "directories": WORKSPACE_STRUCTURE["directories"],
        "directory_descriptions": WORKSPACE_STRUCTURE["directory_descriptions"],
        "seed_files": list(WORKSPACE_STRUCTURE["seed_files"].keys()),
        "template_content": templates,
        "default_filename": "resume.md",
        "action_required": "ask_user_then_create",
        "agent_instructions": (
            "IMPORTANT — follow this priority order exactly:\n"
            "\n"
            "PRIMARY PATH — offer workspace folder creation first:\n"
            "1. Ask: 'Would you like me to create the resume-workspace folder "
            "structure on your computer now? I can set up all the folders and "
            "seed files in one step.'\n"
            "\n"
            "2. If YES — create ONLY the folders listed in 'directories' under "
            "'recommended_root':\n"
            "   resume-workspace/\n"
            "   ├── source/\n"
            "   ├── job-descriptions/\n"
            "   ├── tailored/\n"
            "   └── archive/\n"
            "       └── old-resumes/\n"
            "\n"
            "3. Then write seed files from 'template_content':\n"
            "   - source/master-profile.md        ← write content from template_content\n"
            "   - job-descriptions/template.md     ← write content from template_content\n"
            "\n"
            "4. After folders and files are created, direct the user to open\n"
            "   source/master-profile.md and follow the template guidance to\n"
            "   fill in their experience. DO NOT ask them to paste content in chat.\n"
            "\n"
            "SECONDARY PATH — only if user declines folder creation:\n"
            "5. If NO or user cannot create folders — offer to show the template\n"
            "   content inline in chat so they can copy it manually:\n"
            "   'No problem — here is the master-profile template you can copy:'\n"
            "   Then paste the content of template_content['source/master-profile.md'].\n"
            "\n"
            "NEVER do these things:\n"
            "   DO NOT ask the user to paste their resume or profile content in chat\n"
            "   before offering folder creation.\n"
            "   DO NOT create numbered folders (01-input/, etc.) or extras\n"
            "   (templates/, workflow/, qa/).\n"
            "   DO NOT invent alternative folder layouts.\n"
            "\n"
            "Tool outputs go in tailored/company-role-YYYY-MM/ subfolders:\n"
            "   - jd-analysis.md  (from analyze_jd)\n"
            "   - mapping.md      (from map_resume)\n"
            "   - draft.md        (from draft_resume)\n"
            "   - final.md        (from finalize)\n"
        ),
    }


def _slugify(text: str, max_len: int = 40) -> str:
    """Convert *text* to a lower-case, hyphen-separated filesystem-safe slug.

    Args:
        text: Input string (e.g. a company name or role title).
        max_len: Maximum slug length (default 40).

    Returns:
        Sanitised slug string.
    """
    text = text.lower().strip()
    text = re.sub(r"[^a-z0-9]+", "-", text)
    text = text.strip("-")
    if len(text) > max_len:
        text = text[:max_len].rstrip("-")
    return text


def suggest_output_path(
    target_role: str,
    target_company: str = "",
    date: datetime | None = None,
) -> dict[str, str]:
    """Return a suggested output directory name and file stem.

    Args:
        target_role: Target job title.
        target_company: Optional company name.
        date: Optional date (defaults to UTC now).

    Returns:
        Dict with keys ``root`` (e.g. ``"acme-infra-eng-2026.03"``),
        ``file_stem`` (``"resume"``), and ``extension`` (``".md"``).
    """
    date = date or datetime.now(timezone.utc)
    date_part = date.strftime("%Y.%m")

    parts: list[str] = []
    if target_company:
        parts.append(_slugify(target_company, 15))
    parts.append(_slugify(target_role, 20))
    parts.append(date_part)

    return {
        "root": "-".join(parts),
        "file_stem": "resume",
        "extension": ".md",
    }


def build_workspace_setup(
    target_role: str,
    target_company: str = "",
    date: datetime | None = None,
) -> dict:
    """Build a ``workspace_setup`` block for embedding in tool responses.

    The LLM client is expected to:
    1.  Check if ``recommended_root`` exists on the local filesystem.
    2.  If not, ask the user whether to create it (with the listed
        subdirectories).
    3.  Proceed only after the directory tree is confirmed.

    This function combines the canonical workspace layout with the
    per-application output path.
    """
    path_info = suggest_output_path(target_role, target_company, date)
    root = path_info["root"]

    # Start with the full canonical workspace setup
    full_setup = build_full_workspace_setup()

    # Add per-application output path info
    full_setup["application_output"] = {
        "tailored_subfolder": f"tailored/{root}/",
        "files": {
            "jd-analysis.md": "Output from analyze_jd",
            "mapping.md": "Output from map_resume",
            "draft.md": "Output from draft_resume",
            "final.md": "Output from finalize",
        },
        "variant_subdirectories": {k: v for k, v in VARIANT_DIRS.items()},
        "default_filename": f"{path_info['file_stem']}{path_info['extension']}",
    }

    return full_setup
