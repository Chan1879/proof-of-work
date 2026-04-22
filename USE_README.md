# Proof of Work Usage Guide

This guide covers the day-to-day workflow for using the Proof of Work MCP server to prepare job descriptions, build tailored resumes, answer verification questions, and organize your files.

For setup, installation, Docker, local development, and connecting the MCP server in VS Code, see [README.md](README.md).

---

## What This Guide Covers

Use this guide when you want to:

- Prepare your resume workspace
- Add source resumes and job descriptions
- Run the MCP tools in the right order
- Answer follow-up questions and verification prompts
- Create reusable user instructions for repeated workflows
- Insert a page break when exporting or formatting resume content

---

## Recommended Workspace

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
|   |-- company-role-YYYY-MM.txt   # Recommended for most users
|   `-- company-role-YYYY-MM.md    # Also supported
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

### Job Description Files

Job descriptions should be stored as plain text content. Any text-based file type works.

- Recommended examples: `.txt`, `.md`
- Best default for most users: `.txt`
- Markdown is supported, but plain text is usually easier when you are copying and pasting from job boards, emails, or ATS portals

The important part is the content, not the extension. Keep the job description as close to the original posting as possible.

Recommended naming examples:

- `job-descriptions/acme-sre-2026-03.txt`
- `job-descriptions/acme-sre-2026-03.md`

---

## Core Workflow

1. Fill out `source/master-profile.md` with all relevant experience.
2. Add a job description file under `job-descriptions/`.
3. Run `analyze_jd` to extract requirements and priorities.
4. Run `map_resume` to map evidence and identify gaps.
5. Run `draft_resume` to generate a tagged draft and verification questions.
6. Resolve all verification items.
7. Run `finalize` to generate final output.
8. Save outputs under `tailored/company-role-YYYY-MM/`.
9. Use `faq` any time for guidance on structure, naming, types, workflow, tools, verification tags, and policies.

---

## Tool Workflow

```text
  analyze_jd -> map_resume -> draft_resume -> finalize

  identify_user + manage_skills can be used before or during the workflow
  faq can be used at any time
```

### Tool Summary

#### `analyze_jd`

- Purpose: Extract and prioritize requirements from 1-3 job descriptions.
- Key inputs: `job_descriptions`, `target_level`, optional `role_focus`, `resume_type`, `audience`
- Key outputs: `requirements`, `must_have`, `nice_to_have`, `selected_profile`, `workspace_setup`, `interactive`

#### `map_resume`

- Purpose: Map resume evidence to requirements with confidence and provenance.
- Key inputs: `resume_text`, `requirements`, optional `master_profile`, `resume_type`, `audience`
- Key outputs: `matches`, `partials`, `missing`, `domain_shift_score`, `selected_profile`, `interactive`

#### `draft_resume`

- Purpose: Produce a draft resume and verification checklist.
- Key inputs: `resume_source`, `mapping_result`, `target_role`, optional `target_company`, `resume_type`, `audience`, `output_format`
- Key outputs: `resume_draft`, `evidence_log`, `verification_questions`, `unresolved_verification_count`, `workspace_setup`, `suggested_path`, `interactive`

#### `finalize`

- Purpose: Finalize only after required verification is complete.
- Key inputs: `resume_draft`, `verification_answers`, `unresolved_verification_count`, optional `selected_profile`
- Key outputs: `status`, `resume_final`, `blocked_reasons`, `suggested_output`

#### `identify_user`

- Purpose: Identify the current user so skills and preferences can persist across sessions.

#### `manage_skills`

- Purpose: Add, list, or remove supplemental skills that can strengthen mapping and drafting.

#### `faq`

- Purpose: Answer usage questions about this MCP server.

---

## Example Questions To Expect

The server may surface follow-up questions during the workflow. Typical questions include:

- Do you have experience with these nice-to-have skills from the job description?
- Do you have direct or adjacent experience for these must-have requirements?
- Can you provide more evidence, metrics, or context for these partial matches?
- Do you have volunteer work, special programs, or side projects that help fill the gaps?
- Can you verify this stretch claim, or should it be reworded?
- Approximately how many years of experience do you have with this skill?

These questions are normal. They are part of the truth and verification flow, not an error.

---

## Example Prompts

Use prompts like these with your MCP-capable client or Copilot agent:

- `Help me get started with Proof of Work and set up my resume workspace.`
- `Show me what to put in master-profile.md for a senior platform engineer resume.`
- `Analyze this job description and tell me the must-have and nice-to-have requirements.`
- `Map my current resume to this job description and show me the biggest gaps.`
- `Draft a tailored resume for this Staff SRE role and keep anything uncertain clearly marked.`
- `I am changing careers. Help me frame transferable experience conservatively.`
- `List the verification questions I still need to answer before finalizing.`
- `Help me create user instructions for how I want resumes tailored in this workspace.`

---

## Example FAQ Questions

These can stay useful in the main README, but they are duplicated here so the usage guide stands on its own:

- "How do I build a resume?" (returns step-by-step guide with templates)
- "How do I get started?" (same: workspace setup plus preparation steps)
- "What should I put in my master profile?" (content guidance, ACR bullet format)
- "What if I'm missing requirements?" (gap strategies, transferable skills)
- "I'm changing careers" (domain shift handling, cross-domain framing)
- "Can I reuse my profile for multiple jobs?" (multi-application workflow)
- "What output format should I use?" (md, txt, docx, pdf plus ATS guidance)
- "What folder structure works best to create resumes with this MCP?"
- "What types of resumes can be built?"
- "How should I name the files I want to use?"
- "What does each tool do?"
- "What policy rules can block finalization?"

---

## Creating User Instructions

Create user instructions when you want consistent tailoring across multiple resume iterations or multiple job applications.

Good user instructions usually cover:

- Preferred tone: conservative, balanced, or aggressive
- What to emphasize: leadership, platform depth, delivery speed, business impact, people management, domain expertise
- What to avoid: overclaiming, weak buzzwords, long summaries, overly technical detail, specific industries you do not want emphasized
- Formatting preferences: one page versus multi-page, concise versus detailed bullets, section order, output format
- Evidence preferences: prioritize verified claims, minimize stretch claims, ask before inferring adjacent experience

Example user instruction prompt:

```text
Create user instructions for this workspace that tell the agent to keep claims conservative, prefer verified evidence, highlight platform reliability and incident response work, avoid overstating leadership, and ask before turning adjacent experience into a core qualification.
```

If you reuse the same style often, keep those instructions near your resume workspace so the agent can apply them consistently.

---

## One-Line HTML Page Break

Use this one-liner when you need a hard page break in HTML output:

```html
<div style="page-break-before: always;"></div>
```

---

## Verification Tags

- `VERIFIED`: Directly supported by source evidence
- `INFERRED`: Reasonable inference from adjacent evidence
- `STRETCH`: Plausible but needs user confirmation
- `USER-VERIFY`: Must be resolved before finalization

`finalize` is blocked while unresolved verification items remain.

---

## Supported Resume Types

- `tech`: Engineering, platform, developer, and infrastructure roles
- `non_tech`: Business, operations, HR, finance, and sales roles
- `hybrid`: Mixed technical and business leadership roles
- `executive`: Director, VP, and organization-level leadership roles

---

## Practical Guidance

- Keep your master profile broad and detailed. It is your evidence source, not your final resume.
- Keep job descriptions close to the original source text.
- Do not skip verification questions if you want truthful final output.
- Use `.txt` for job descriptions when you want the simplest copy-paste workflow.
- Use `.md` when you want to add notes, headings, or source metadata around the pasted job description.

For installation, server startup, Docker usage, and MCP connection setup, go back to [README.md](README.md).
