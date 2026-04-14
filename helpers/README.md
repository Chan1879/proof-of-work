# helpers/ — Utility Modules

Utility modules consumed by MCP tool handlers to generate workspace paths, surface interactive prompts to the user, and manage per-user data persistence.

## Modules

### `naming.py` — Workspace Paths & Directory Setup

Generates suggested directory names, filenames, and `workspace_setup` blocks that the LLM client relays to the user. The server never writes output files itself — these are advisory suggestions only.

**Key functions:**
- `build_full_workspace_setup()` — Return the canonical workspace layout with explicit agent instructions, seed files, and template content.
- `build_workspace_setup(target_role, target_company, date)` — Combines the canonical layout with a per-application output path.
- `suggest_output_path(target_role, target_company, date)` — Return a suggested folder root, file stem, and extension.

**Key constants:**
- `WORKSPACE_STRUCTURE` — The authoritative workspace layout (`source/`, `job-descriptions/`, `tailored/`, `archive/`).
- `VARIANT_DIRS` — Subfolder convention (`v1/`, `brief/`, `detailed/`, `exec/`).

### `questions.py` — Interactive Question Generation

Each public function returns an `interactive` dict for embedding in a tool's response payload. The calling LLM relays questions and suggestions to the user and feeds answers back into the next tool invocation.

**Interactive dict structure:**
```python
{
    "questions":           [...],  # Things that need user answers
    "suggestions":         [...],  # Proactive recommendations
    "verification_needed": [...],  # Stretch claims needing confirmation
}
```

**Key functions:**
- `after_analyze_jd(...)` — Nice-to-have skill questions, ambiguous must-have clarification.
- `after_map_resume(...)` — Gap analysis, volunteer prompts, domain-shift warnings.
- `after_draft_resume(...)` — Verification questions with confidence context.
- `after_skill_add(...)` — Detail-gathering for newly added skills.

### `user_store.py` — Per-User Data Persistence

Manages user identity, skill storage, preferences, and session history. All data is isolated per user under `USERS_DIR/<slug>/`. Anonymous (default) users have no on-disk footprint.

**Key classes:**
- `UserContext` — Immutable dataclass: `slug`, `display_name`, `is_anonymous`, `data_dir`.
- `UserStore` — Manage per-user data directories.
  - `identify(name)` — Resolve a display name to a `UserContext`, creating the user dir if needed.
  - `get_anonymous()` — Return the anonymous singleton.
  - `get_skills(ctx)` / `add_skills(ctx, skills)` / `remove_skills(ctx, names)` — CRUD for supplemental skills.
  - `get_preferences(ctx)` / `save_preferences(ctx, prefs)` — User preference persistence.
  - `get_session_history(ctx, limit)` / `append_session_history(ctx, entry)` — Session event history.

**File I/O:** Thread-safe via a global file lock. Writes use atomic tmp-file → rename to prevent corruption.

**Data layout on disk:**
```
/data/users/<slug>/
├── skills.json         ← Supplemental skills list
├── preferences.json    ← User preferences
└── history.json        ← Session event history
```
