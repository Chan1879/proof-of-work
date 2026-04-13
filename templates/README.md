# templates/ — User-Facing Markdown Templates

These markdown templates are served through tool responses and used to seed the user's local resume workspace. The server reads them at runtime via `helpers/naming.py` and includes their content in `workspace_setup.template_content` so the client agent can write them to disk.

## Files

### `master-profile-template.md`

The comprehensive "everything" resume template. Users fill this once with ALL experience — every role, skill, certification, and project — even items that wouldn't appear on a single targeted resume. This serves as the evidence source for `map_resume` and `draft_resume`.

**Destination:** `resume-workspace/source/master-profile.md`

**Key sections:** Contact, Professional Summary, Core Competencies (Technical + Leadership), Professional Experience (every role with Action + Context + Result bullets), Certifications, Education, Additional (side projects, open source, publications, volunteer work).

### `jd-template.md`

Template for storing individual job descriptions. Users copy this file for each new job application, rename it to `company-role-YYYY-MM.md`, and paste the full JD text.

**Destination:** `resume-workspace/job-descriptions/template.md`

**Key sections:** Source (URL, date, status), Job Details (company, role, level, location, compensation), Full Job Description (unedited paste), Your Notes (motivation, referral info, emphasis preferences).

### `resume-source-template.md`

Base resume template for a specific resume type (tech, hybrid, executive, non-tech). Users create a curated subset of the master profile pre-shaped for one category. MCP tools further tailor it per JD.

**Destination:** `resume-workspace/source/resume-{type}.md`

**Key sections:** Contact, Professional Summary (targeted to resume type), Technical Skills (curated), Professional Experience (relevant roles only), Education, Certifications.

## How Templates Are Used

1. **Workspace setup** — When a tool returns `workspace_setup.template_content`, the client agent writes these files to the user's local workspace.
2. **FAQ tool** — Asking "how do I get started?" or "help with master profile" returns the template content for manual copy.
3. **Direct reference** — The naming module reads templates via `_read_template(filename)` and includes them in response payloads.
