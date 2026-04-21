# Changelog

All notable changes to this project will be documented here.

---

## [Unreleased] — 2026-04-20

### Bug Fixes

- **`tools/faq.py`** — Fixed critical syntax error where a second `_README_CONTENT = """..."""` assignment was injected inside `_KB["resume_types"]["answer"]`, making the module unparseable. Restored `resume_types` with the correct four-profile description and re-added the missing `master_profile` KB entry.
- **`tools/identify_user.py`** — Replaced direct `contracts.validate_output()` + `return result` with `session_state.finalize_tool_response()`. Tool was bypassing all policy evaluation (P0–P5) on every response.
- **`tools/manage_skills.py`** — Same fix across all four code paths: anonymous gate, list, add, and remove. All paths now route through `finalize_tool_response()`.
- **`engine/session.py`** — Removed dead `@property` decorator applied to the module-level function `_session_proxy()`. At module level `@property` creates a descriptor object but never acts as one; the decorator was a no-op and has been removed.
- **`engine/audit.py`** — Silent `except OSError: pass` in `log_event()` replaced with `logger.warning(...)` so audit write failures are visible in container logs.

### Changes

- **`tools/faq.py`** — Updated module-level `_README_CONTENT` string: added `.txt` JD file guidance, expanded Policy Rules table to P0–P5, added pointer to `USE_README.md`.
- **`helpers/user_store.py`** — `get_skills()` now filters out malformed non-dict entries from `skills.json` before returning. `remove_skills()` applies the same guard to prevent `AttributeError` when iterating a corrupted store.

### Documentation

- **`engine/README.md`** — Updated `policy_engine.py` section: heading `P0–P4` → `P0–P5`, "five policy tiers" → "six policy tiers", added P5 (User Data Isolation) row to the tier table.
- **`policies/README.md`** — Corrected "Defines 5 policy tiers (P0–P5)" → "Defines 6 policy tiers (P0–P5)".
- **`docker/README.md`** — Fixed broken anchor `#writing-a-custom-tool` → `#tool-plugins` (section was renamed when `tools/README.md` was trimmed).
- **`README.md`** — Refactored to build/setup focus; "How To Use" section now points to `USE_README.md`. Policy table updated with P5 row.
- **`tools/README.md`** — Trimmed to developer plugin reference only; all user-facing workflow content moved to `USE_README.md`.
- **`USE_README.md`** *(new)* — Root user-facing workflow guide covering workspace layout, JD file guidance (`.txt` recommended), 9-step workflow, example questions and prompts, user instructions, HTML page break, verification tags, and supported resume types.

### Removed

- **`docs/`** — Deleted stale planning documents (`current.md`, `desired.md`). Content superseded by `USE_README.md` and `helpers/naming.py` `WORKSPACE_STRUCTURE`. Directory was gitignored and unreferenced.
- **`docker/vdrive-empty/`** — Deleted unreferenced empty directory (contained only `.gitkeep`; not mounted or used anywhere).

### Breaking Changes

- **Policy pipeline now enforced for `identify_user` and `manage_skills`.** Both tools previously bypassed policy evaluation entirely. Callers that depended on always receiving a success payload regardless of policy state will now receive `{"status": "blocked", ...}` when a policy rule fires.

---
