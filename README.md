# Proof of Work

A policy-driven [Model Context Protocol](https://modelcontextprotocol.io/) (MCP) server that helps AI agents generate **truthful, ATS-optimized, tailored resumes**. Every claim is tagged with provenance, validated against JSON Schema contracts, evaluated by a 5-tier policy engine, and logged for audit — so nothing is fabricated.

![Python 3.12](https://img.shields.io/badge/python-3.12-blue)
![MCP](https://img.shields.io/badge/protocol-MCP-green)
![Docker](https://img.shields.io/badge/docker-ready-blue)
![License: MIT](https://img.shields.io/badge/license-MIT-yellow)

---

## Features

- **7 MCP tools** — Full workflow from JD analysis → resume mapping → draft generation → finalization
- **5-tier policy engine (P0–P4)** — Truth safety, verification gates, workflow ordering, quality enforcement, ATS formatting
- **Claim provenance tags** — Every resume bullet is tagged `[VERIFIED]`, `[INFERRED]`, `[STRETCH]`, or `[USER-VERIFY]`
- **JSON Schema contract validation** — All tool inputs and outputs validated against declared schemas
- **Per-user skill profiles** — Persistent supplemental skills injected as evidence during mapping/drafting
- **Structured audit logging** — JSON-lines log of every policy evaluation and tool invocation
- **Interactive questions** — Tools surface follow-up questions, suggestions, and verification prompts
- **Dynamic tool loading** — Drop custom `.py` tools into the tools directory at runtime

---

## Quick Start

### Docker Compose (recommended)

```bash
git clone https://github.com/YOUR_USERNAME/proof-of-work.git
cd proof-of-work
docker compose -f docker/docker-compose.yml up --build -d
```

The server starts on **port 5359** with Streamable HTTP transport. Connect any MCP-compatible client to `http://localhost:5359/mcp`.

### Local Python

```bash
git clone https://github.com/YOUR_USERNAME/proof-of-work.git
cd proof-of-work
python -m venv venv && source venv/bin/activate  # or venv\Scripts\activate on Windows
pip install -r requirements.txt
python server.py
```

> **Note:** Local mode uses `/data/` for logs and user data by default. Set environment variables (see [Configuration](#configuration)) to override paths.

### Connecting from VS Code (GitHub Copilot)

Once the server is running, add it as an MCP server in VS Code:

1. Open the Command Palette (`Ctrl+Shift+P`) → **MCP: Add Server…**
2. Choose **HTTP (Streamable HTTP)** as the transport type.
3. Enter the server URL: `http://localhost:5359/mcp`
4. Give it a name (e.g. `proof-of-work`) and choose where to save (`User settings` for all workspaces, or `Workspace settings` for this project only).

This creates an entry in your `settings.json`:

```jsonc
// .vscode/settings.json (workspace) or User settings.json
{
  "mcp": {
    "servers": {
      "proof-of-work": {
        "type": "http",
        "url": "http://localhost:5359/mcp"
      }
    }
  }
}
```

After adding, VS Code will show a **Start** button next to the server entry. Click it to connect. The server's 7 tools will then be available to Copilot in Agent mode — open Copilot Chat, switch to **Agent**, and the tools appear automatically.

> **Tip:** You can also create an `.vscode/mcp.json` file in your project root as an alternative to `settings.json`. This is useful for sharing the MCP config with collaborators:
>
> ```json
> {
>   "servers": {
>     "proof-of-work": {
>       "type": "http",
>       "url": "http://localhost:5359/mcp"
>     }
>   }
> }
> ```

---

## Architecture

```
┌──────────────┐    MCP/HTTP     ┌──────────────────────────────────────┐
│  MCP Client  │ ◄──────────────► │  server.py (FastMCP)                 │
│  (AI Agent)  │                  │                                      │
└──────────────┘                  │  ┌──────────┐   ┌────────────────┐  │
                                  │  │ tools/*  │──►│ engine/session  │  │
                                  │  │ (7 tools)│   │  ├─ policy_check│  │
                                  │  └──────────┘   │  ├─ contracts   │  │
                                  │                  │  ├─ audit       │  │
                                  │  ┌──────────┐   │  └─ policy_engine│ │
                                  │  │helpers/* │   └────────────────┘  │
                                  │  │naming    │                       │
                                  │  │questions │   ┌────────────────┐  │
                                  │  │user_store│   │ policies/      │  │
                                  │  └──────────┘   │  rules + schemas│  │
                                  │                  └────────────────┘  │
                                  └──────────────────────────────────────┘
```

**Request flow:** Client calls tool via MCP → Tool validates input (contracts) → Tool builds response scaffold → `engine.session.finalize_tool_response()` runs policy evaluation → Audit event logged → Result returned (or blocked with reasons).

---

## Tools

| Tool | Purpose | Workflow Step |
|------|---------|--------------|
| `analyze_jd` | Extract and prioritize requirements from 1–3 job descriptions | 1 |
| `map_resume` | Map resume evidence to JD requirements with confidence scores | 2 |
| `draft_resume` | Generate tagged draft with provenance labels and verification questions | 3 |
| `finalize` | Produce final resume after all verification items are resolved | 4 |
| `identify_user` | Set user identity for persistent skill profiles | Setup |
| `manage_skills` | Add, list, or remove supplemental skills in user profile | Setup |
| `faq` | Answer questions about workflow, folder layout, policies, etc. | Anytime |

See [tools/README.md](tools/README.md) for detailed documentation on each tool.

---

## Workspace Structure

The server enforces a canonical workspace layout for the client agent:

```
resume-workspace/
├── source/                     ← Base resumes and master profile
│   ├── master-profile.md
│   ├── resume-tech.md
│   └── resume-hybrid.md
├── job-descriptions/           ← One file per job description
│   ├── template.md
│   └── company-role-YYYY-MM.md
├── tailored/                   ← One subfolder per application
│   └── company-role-YYYY-MM/
│       ├── jd-analysis.md
│       ├── mapping.md
│       ├── draft.md
│       └── final.md
└── archive/
    └── old-resumes/
```

See [templates/README.md](templates/README.md) for the template files that seed this workspace.

---

## Configuration

All paths are configurable via environment variables:

| Variable | Default | Description |
|----------|---------|-------------|
| `POLICY_PACK_PATH` | `/app/policies/policy-rules.yaml` | Path to policy rules YAML |
| `CONTRACTS_PATH` | `/app/policies/tool-contracts.json` | Path to JSON Schema contracts |
| `AUDIT_LOG_PATH` | `/data/logs/audit.jsonl` | Path to audit log file |
| `LOG_DIR` | `/data/logs` | Directory for server logs |
| `TOOLS_DIR` | `/data/tools` | Directory to scan for tool plugins |
| `USERS_DIR` | `/data/users` | Per-user data storage root |

---

## Policy Engine

Five policy tiers enforce resume quality and truthfulness:

| Rule | Name | Effect |
|------|------|--------|
| **P0** | Truth Safety | No fabrication — every claim must carry a provenance tag |
| **P1** | Verification Gate | `finalize` blocked while unresolved `[USER-VERIFY]` items exist |
| **P2** | Workflow Order | `analyze_jd` must run before `finalize`; domain-shift alerting |
| **P3** | Quality | Action + Context + Result bullet format; seniority alignment |
| **P4** | ATS Format | No markdown tables/images in final output; sections match profile |

See [policies/README.md](policies/README.md) for the full rule specification.

---

## Project Structure

```
proof-of-work/
├── server.py                    ← Entry point — MCP bootstrap + tool loader
├── entrypoint.sh                ← Docker container bootstrap script
├── requirements.txt             ← Python dependencies
├── LICENSE                      ← MIT license
│
├── engine/                      ← Core infrastructure (policy, contracts, session, audit)
│   ├── __init__.py
│   ├── audit.py                 ← JSON-lines audit logger
│   ├── contracts.py             ← JSON Schema contract validation
│   ├── policy_engine.py         ← P0–P4 policy rule evaluation
│   └── session.py               ← Per-user session state + policy enforcement hub
│
├── helpers/                     ← Utilities consumed by tools
│   ├── __init__.py
│   ├── naming.py                ← Workspace paths, filenames, and directory setup
│   ├── questions.py             ← Interactive question generation
│   └── user_store.py            ← Per-user data persistence (skills, prefs, history)
│
├── tools/                       ← MCP tool plugins (dynamically loaded)
│   ├── analyze_jd.py
│   ├── draft_resume.py
│   ├── faq.py
│   ├── finalize.py
│   ├── identify_user.py
│   ├── manage_skills.py
│   └── map_resume.py
│
├── policies/                    ← Policy rules + JSON Schema contracts
│   ├── policy-rules.yaml
│   └── tool-contracts.json
│
├── templates/                   ← User-facing markdown templates
│   ├── jd-template.md
│   ├── master-profile-template.md
│   └── resume-source-template.md
│
└── docker/                      ← Docker deployment files
    ├── Dockerfile
    ├── docker-compose.yml
    └── healthcheck.sh
```

---

## License

This project is licensed under the [MIT License](LICENSE).

## About the Name

**Proof of Work** — borrowed from crypto, repurposed for resumes. In blockchain, proof-of-work means you burned real compute to earn a token. Here, it means every bullet on your resume is backed by real evidence to earn its place. The server won’t let a claim through without provenance — no fabrication, no embellishment, just proof.

---

# Proof of Work — Reference

MCP server for resume tailoring workflows. This project provides structured tools
to analyze job descriptions, map resume evidence, draft targeted resumes with
claim provenance tags, enforce verification gates, and answer usage questions.

## Recommended Resume Workspace

Use this folder layout for the files you pass into the MCP tools:

```text
resume-workspace/
|
|-- source/                        # Base resumes and master profile
|   |-- master-profile.md          # Comprehensive "everything" resume
|   |-- resume-tech.md
|   |-- resume-hybrid.md
|   `-- resume-executive.md
|
|-- job-descriptions/              # One file per JD
|   |-- template.md
|   `-- company-role-YYYY-MM.md    # e.g. microsoft-sre-2026-03.md
|
|-- tailored/                      # One folder per application
|   `-- company-role-YYYY-MM/
|       |-- jd-analysis.md
|       |-- mapping.md
|       |-- draft.md
|       `-- final.md
|
`-- archive/
        `-- old-resumes/
```

## Tool Workflow

1. Prepare `source/master-profile.md` with all relevant experience.
   Use the template in `templates/master-profile-template.md` as your starting point.
2. Copy `job-descriptions/template.md` → rename to `company-role-YYYY-MM.md` and paste the JD.
   The template is based on `templates/jd-template.md`.
3. Run `analyze_jd` to extract requirements and priorities.
4. Run `map_resume` to map evidence and identify gaps.
5. Run `draft_resume` to generate a tagged draft plus verification questions.
6. Resolve all verification items.
7. Run `finalize` to generate final output.
8. Optionally run `faq` any time for guidance on structure, naming, types,
     workflow, tools, verification tags, and policies.

## MCP Tools

### `analyze_jd`
- Purpose: Extract and prioritize requirements from 1-3 job descriptions.
- Key inputs: `job_descriptions`, `target_level`, optional `role_focus`,
    `resume_type`, `audience`.
- Key outputs: `requirements`, `must_have`, `nice_to_have`, `selected_profile`,
    `workspace_setup`, `interactive`.

### `map_resume`
- Purpose: Map resume evidence to requirements with confidence/provenance.
- Key inputs: `resume_text`, `requirements`, optional `master_profile`,
    `resume_type`, `audience`.
- Key outputs: `matches`, `partials`, `missing`, `domain_shift_score`,
    `selected_profile`, `interactive`.

### `draft_resume`
- Purpose: Produce a draft resume and verification checklist.
- Key inputs: `resume_source`, `mapping_result`, `target_role`, optional
    `target_company`, `resume_type`, `audience`, `output_format`.
- Key outputs: `resume_draft`, `evidence_log`, `verification_questions`,
    `unresolved_verification_count`, `workspace_setup`, `suggested_path`,
    `suggested_filename`, `interactive`.

### `finalize`
- Purpose: Finalize only after required verification is complete.
- Key inputs: `resume_draft`, `verification_answers`,
    `unresolved_verification_count`, optional `selected_profile`.
- Key outputs: `status` (`finalized` or `blocked`), `resume_final`,
    `blocked_reasons`, `suggested_output`.

### `faq`
- Purpose: Answer usage questions about this MCP server.
- Key input: `question` (required), optional `context` object.
- Key outputs: `answer`, `topic`, `related_topics`, and optionally
    `workspace_setup`.
- Special behavior: For folder/workspace questions, `workspace_setup`
    includes `readme_content` so clients can create `resume-workspace/README.md`
    during folder setup.

## Supported Resume Types

- `tech`: Engineering/platform/developer-focused resumes.
- `non_tech`: Business, operations, and non-engineering roles.
- `hybrid`: Mixed technical and business leadership profiles.
- `executive`: Director/VP/C-level strategic profiles.

## Naming Conventions

- Job description files: `company-role-YYYY-MM.md`
- Tailored output folder: `company-role-YYYY.MM`
- Default output filename: `resume.md`

Recommended subfolders for tailored outputs:
- `v1/`: First iteration
- `brief/`: Condensed version
- `detailed/`: Expanded version
- `exec/`: Executive-optimized version

## Verification Tags

- `VERIFIED`: Directly supported by source evidence.
- `INFERRED`: Reasonable inference from adjacent evidence.
- `STRETCH`: Plausible but needs user confirmation.
- `USER-VERIFY`: Must be resolved before finalization.

`finalize` is blocked while unresolved verification items remain.

## Policy Guardrails (P0-P4)

- P0 Truth Safety: No fabrication, provenance tagging required.
- P1 Verification Gate: Finalization blocked on unresolved user verification.
- P2 Workflow Order: Quick-match stage required before finalization.
- P3 Quality: Action + Context + Result style and seniority alignment.
- P4 ATS Format: Final output must remain ATS-safe.

## Local Development

### Python

```bash
pip install -r requirements.txt
python server.py
```

Server transport defaults to Streamable HTTP on port `5359`.

### Docker Compose

```bash
cd docker
docker compose up --build
```

## Template Files

Template files are included in `templates/` and are served through tool
responses so the client agent can create properly formatted seed files.

| Template | Purpose | Destination in workspace |
|----------|---------|--------------------------|
| `master-profile-template.md` | Comprehensive "everything" resume template | `source/master-profile.md` |
| `jd-template.md` | Job description capture template | `job-descriptions/template.md` |
| `resume-source-template.md` | Base resume template per type | `source/resume-{type}.md` |

## Workspace Guardrails

The MCP server enforces a specific folder layout through `workspace_setup`
objects returned by `analyze_jd`, `draft_resume`, and `faq`. Client agents
**must** follow the `agent_instructions` field and create ONLY the documented
structure:

```text
resume-workspace/
├── source/
├── job-descriptions/
├── tailored/
└── archive/
    └── old-resumes/
```

Client agents must NOT create numbered folders (`01-input/`, `02-analysis/`),
extra directories (`templates/`, `workflow/`, `qa/`), or alternative layouts.

## Example FAQ Questions

- "How do I build a resume?" (returns step-by-step guide with templates)
- "How do I get started?" (same — workspace setup + preparation steps 1 & 2)
- "What should I put in my master profile?" (content guidance, ACR bullet format)
- "What if I'm missing requirements?" (gap strategies, transferable skills)
- "I'm changing careers" (domain shift handling, cross-domain framing)
- "Can I reuse my profile for multiple jobs?" (multi-application workflow)
- "What output format should I use?" (md, txt, docx, pdf + ATS guidance)
- "What folder structure works best to create resumes with this MCP?"
- "What types of resumes can be built?"
- "How should I name the files I want to use?"
- "What does each tool do?"
- "What policy rules can block finalization?"
