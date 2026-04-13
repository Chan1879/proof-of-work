# policies/ — Policy Rules & JSON Schema Contracts

This directory contains the two configuration files that govern all tool behavior: the policy rule engine's YAML configuration and the JSON Schema contracts for tool input/output validation.

## Files

### `policy-rules.yaml` — Policy Rule Engine Configuration

Defines 5 policy tiers (P0–P5) with 25+ rules for truth safety, verification gates, workflow ordering, resume quality, ATS formatting, and user data isolation.

#### Policy Tiers

| Tier | Name | Severity | Purpose |
|------|------|----------|---------|
| **P0** | Truth Safety | Hard | Every claim must carry a provenance tag; no fabrication allowed. Low-confidence `[STRETCH]`/`[INFERRED]` claims below the confidence floor must be escalated to `[USER-VERIFY]`. |
| **P1** | Verification Gate | Soft | `finalize` is blocked while unresolved `[USER-VERIFY]` items exist. Profile consistency is checked across tool calls. |
| **P2** | Workflow Order | Hard | `analyze_jd` must run before `finalize` (two-stage flow). Domain-shift alert triggered at score ≥ 0.35. |
| **P3** | Quality | Soft | Action + Context + Result bullet format enforced. Seniority alignment, profile-specific signals, and volunteer section suggestions. |
| **P4** | ATS Format | Soft | Markdown tables, images, and HTML tags forbidden in final output. Sections must match the selected resume profile. |
| **P5** | User Data Isolation | Hard | Anonymous users cannot access `/data/users/`. Per-user skill scope enforced. `[USER-PROFILE]` claims require resume corroboration before finalize. |

#### Configurable Guardrails

```yaml
guardrails:
  low_confidence_floor: 0.4     # Claims below this confidence must be USER-VERIFY
  min_evidence_entries: 1        # Minimum evidence_log entries per draft
  user_profile_corroboration_floor: 0.7   # USER-PROFILE claims need this confidence
  claim_density_ratio: 2.0       # Warn if bullets-to-evidence ratio exceeds this
```

#### Resume Profiles

Four profiles are defined, each with `required_sections`, `optional_sections`, and `prefer_signals`:

- **tech** — Software engineers, architects, DevOps, data engineers
- **non_tech** — Business, operations, HR, finance, sales roles
- **hybrid** — Product managers, engineering managers, technical leads
- **executive** — VPs, Directors, C-suite targeting board/org-level roles

#### Customizing Rules

Each rule in the `policies` list has this structure:

```yaml
- id: P0_NO_FABRICATION
  class: P0
  severity: hard
  when: "evidence_log entry missing resume_evidence"
  then: "block"
  action: "Every evidence_log entry must cite source text"
```

- `severity: hard` — Blocks the tool response entirely.
- `severity: soft` — Adds a warning to `reasons` but does not block (unless combined with other violations).
- `when` — Condition description (evaluated programmatically in `policy_engine.py`).
- `then` — Action to take: `block`, `warn`, `require_section`.

### `tool-contracts.json` — JSON Schema Contracts

Defines input and output schemas for all 7 MCP tools using standard [JSON Schema](https://json-schema.org/) syntax. The `ContractRegistry` in `engine/contracts.py` loads this file and validates every tool invocation.

#### Structure

```json
{
  "tools": [
    {
      "name": "analyze_job_description",
      "description": "...",
      "input_schema": { ... },
      "output_schema": { ... }
    },
    ...
  ],
  "$defs": {
    "workspace_setup": { ... },
    "interactive": { ... },
    "mappings": { ... }
  }
}
```

- **`tools[]`** — Array of 7 tool definitions with `input_schema` and `output_schema`.
- **`$defs`** — Shared schema fragments (reusable via `$ref`).
- **Input schemas** — Define required parameters, type constraints, enums, min/max lengths.
- **Output schemas** — Define required response fields so clients get a predictable shape.

#### Validation Flow

1. Tool handler receives arguments.
2. `ContractRegistry.validate_input(tool_name, payload)` — Validates against `input_schema`. Raises `ContractValidationError` on failure.
3. Tool builds result dict.
4. `ContractRegistry.validate_output(tool_name, result)` — Validates against `output_schema` (only for non-blocked responses).
