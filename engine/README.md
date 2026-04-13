# engine/ — Core Infrastructure

This package contains the server-side enforcement layer that every MCP tool call passes through. It is the backbone of the resume server's safety, validation, and traceability guarantees.

## Modules

### `audit.py` — Structured Audit Logger

Writes JSON-lines to a configurable log path (`AUDIT_LOG_PATH`) so every policy evaluation, tool invocation, and verification event is traceable. For `finalize_resume` events, a SHA-256 content fingerprint of the resume is captured for compliance auditing without bloating every log line.

**Key function:**
- `log_event(event_type, tool_name, payload, decision, user_slug)` — Append a structured JSON record to the audit log.

### `contracts.py` — JSON Schema Contract Validation

Loads `tool-contracts.json` from the policies directory and validates tool payloads against declared schemas. Every tool's input is validated before execution, and every successful output is validated before returning to the client. Shared `$defs` enable schema reuse across tools.

**Key classes:**
- `ContractRegistry` — Loads contracts, exposes `validate_input()` and `validate_output()` methods.
- `ContractValidationError` — Raised when a payload fails schema validation.

### `policy_engine.py` — P0–P4 Policy Rule Engine

Loads `policy-rules.yaml` and evaluates tool actions against five policy tiers:

| Tier | Name | Purpose |
|------|------|---------|
| P0 | Truth Safety | Every claim must carry a provenance tag; no fabrication |
| P1 | Verification Gate | `finalize` blocked while unresolved `[USER-VERIFY]` items exist |
| P2 | Workflow Order | `analyze_jd` must run before `finalize`; domain-shift alerting |
| P3 | Quality | Action + Context + Result bullet format; seniority alignment |
| P4 | ATS Format | No markdown tables/images in final output; sections match profile |

**Key classes/functions:**
- `PolicyEngine` — Loads rules, provides `evaluate()` and `resolve_profile()`.
- `PolicyDecision` — Dataclass returned by `evaluate()`: `blocked`, `reasons`, `required_sections`, `selected_profile`, `violations`.

### `session.py` — Session State & Policy Enforcement Hub

The central integration point. Manages per-user in-memory session state, holds singleton instances of `PolicyEngine`, `ContractRegistry`, and `UserStore`, and exposes the `policy_check()` / `finalize_tool_response()` helpers that every tool handler calls after building its result scaffold.

**Key functions:**
- `get_session(user)` — Return the isolated session dict for a user.
- `set_current_user(ctx)` — Switch the active user context.
- `policy_check(tool_name, payload, result)` — Run policy evaluation, inject metadata, block if needed.
- `finalize_tool_response(tool_name, payload, result)` — Run policy check + output schema validation.

## Request Flow

```
Tool handler builds result dict
        │
        ▼
finalize_tool_response()
        │
        ├── policy_check()
        │       ├── PolicyEngine.evaluate()     → blocked / allowed
        │       ├── Inject profile metadata
        │       └── log_event() → audit.jsonl
        │
        ├── If blocked → return { status: "blocked", blocked_reasons }
        │
        └── ContractRegistry.validate_output()  → schema check
                │
                └── Return validated result to client
```
