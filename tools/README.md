# tools/ — MCP Tool Plugins

This directory contains the 7 MCP tools that are dynamically loaded by `server.py` at startup. Each file exports a `TOOL_DEF` dict that registers the tool with FastMCP.

## Tool Workflow

```
  ┌─────────────┐     ┌──────────────┐     ┌──────────────┐     ┌──────────┐
  │ analyze_jd  │────►│  map_resume  │────►│ draft_resume │────►│ finalize │
  │  (Step 1)   │     │   (Step 2)   │     │   (Step 3)   │     │ (Step 4) │
  └─────────────┘     └──────────────┘     └──────────────┘     └──────────┘
                                                                       │
  ┌───────────────┐   ┌───────────────┐                          Blocked until
  │ identify_user │   │ manage_skills │                          all [USER-VERIFY]
  │   (setup)     │   │   (setup)     │                          items resolved
  └───────────────┘   └───────────────┘

  ┌─────┐
  │ faq │  ← Available at any time
  └─────┘
```

## Tool Reference

### `analyze_jd` — Analyze Job Descriptions

Extract and prioritize requirements from 1–3 job descriptions. First step in the 4-tool workflow. Auto-selects a resume profile (tech, non_tech, hybrid, executive) based on the JD content.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `job_descriptions` | `list[str]` | Yes | 1–3 job description texts (each ≥ 50 chars) |
| `target_level` | `str` | Yes | Senior, Staff, Principal, or VP |
| `role_focus` | `str` | No | Keyword focus area (e.g. "cloud", "security") |
| `resume_type` | `str` | No | Resume profile override (default: auto-select) |
| `audience` | `str` | No | hiring_manager, recruiter, executive_panel, or ats |

**Returns:** `requirements`, `must_have`, `nice_to_have`, `selected_profile`, `workspace_setup`, `interactive`

### `map_resume` — Map Resume Evidence to Requirements

Map resume/profile evidence to JD requirements with provenance tags and confidence scores. Computes a `domain_shift_score` (0–1) to detect career pivots. Loads supplemental skills from user profile for additional evidence.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `resume_text` | `str` | Yes | Full resume text (≥ 100 chars) |
| `requirements` | `list[str]` | Yes | Requirement strings from analyze_jd |
| `master_profile` | `str` | No | Master profile content for richer matching |
| `resume_type` | `str` | No | Resume profile override |
| `audience` | `str` | No | Target audience |

**Returns:** `matches`, `partials`, `missing`, `domain_shift_score`, `selected_profile`, `interactive`

### `draft_resume` — Generate Tagged Draft

Generate a draft resume with claim provenance tags (`[VERIFIED]`, `[INFERRED]`, `[STRETCH]`, `[USER-VERIFY]`) and verification questions. Loads supplemental skills from user profile.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `resume_source` | `str` | Yes | Original resume text to build from |
| `mapping_result` | `dict` | Yes | Output from map_resume |
| `target_role` | `str` | Yes | Target job title |
| `target_company` | `str` | No | Target company name |
| `resume_type` | `str` | No | Resume profile override |
| `audience` | `str` | No | Target audience |
| `output_format` | `str` | No | md, txt, docx, or pdf |

**Returns:** `resume_draft`, `evidence_log`, `verification_questions`, `unresolved_verification_count`, `workspace_setup`, `suggested_path`, `interactive`

### `finalize` — Finalize Resume

Final gate in the workflow. Blocks finalization if unresolved `[USER-VERIFY]` items remain. Server-side recomputes unresolved count from `verification_answers` to prevent bypass.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `resume_draft` | `str` | Yes | Draft resume text to finalize |
| `verification_answers` | `list[dict]` | Yes | Answered verification items (question, status, value) |
| `unresolved_verification_count` | `int` | Yes | Client-reported unresolved count |
| `selected_profile` | `str` | No | Resume profile (default: tech) |

**Returns:** `status` (finalized/blocked), `resume_final`, `blocked_reasons`, `suggested_output`

### `identify_user` — User Identification

Identify the current user or enable anonymous mode. Creates/reopens a private data directory for persistent skills, preferences, and history.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `user_name` | `str` | No | User's name (empty = anonymous mode) |

**Returns:** `user_name`, `user_slug`, `is_anonymous`, `stored_skills_count`, `message`

### `manage_skills` — Supplemental Skill Management

CRUD for supplemental skills stored in the user's profile. Skills persist across sessions and are injected into `map_resume` / `draft_resume` as additional evidence. Requires user identification first.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `action` | `str` | Yes | `add`, `list`, or `remove` |
| `skills` | `list[dict]` | For `add` | Skill dicts: name, proficiency, years_experience, context, category |
| `skill_names` | `list[str]` | For `remove` | Skill names to delete |

**Returns:** `status`, `action`, `skills`, `count`, `message`

### `faq` — Knowledge Base

Answer common questions about the MCP server covering workspace layout, resume types, naming conventions, workflow, tools, verification tags, and policy rules. When asked about folder structure, includes a `workspace_setup` object with template content.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `question` | `str` | Yes | The question to answer |
| `context` | `dict` | No | Optional context hints |

**Returns:** `answer`, `topic`, `related_topics`, `workspace_setup` (for folder/workspace questions)

---

## Writing a Custom Tool

Each tool file must export a `TOOL_DEF` dict:

```python
def my_handler(param1: str, param2: int = 0) -> dict[str, Any]:
    """Tool handler — does the work and returns a result dict."""
    payload = {"param1": param1, "param2": param2}
    # Validate input against contracts
    # Build result dict
    # Return via engine.session.finalize_tool_response()
    ...

TOOL_DEF = {
    "name": "my_tool",                      # MCP tool name
    "description": "What this tool does.",   # Shown to the client
    "handler": my_handler,                   # Callable
}
```

`server.py` scans the tools directory for `*.py` files, imports each, extracts `TOOL_DEF`, and registers the handler with FastMCP. The tool's parent directory is added to `sys.path` so imports like `from engine.audit import log_event` work.
