# utils/ — Utility Scripts

This directory contains helper scripts for post-processing resumes and other file operations. These are optional tools that support the main MCP resume workflow.

## Scripts

### `convert_md_to_pdf.py`

Convert Markdown resume files to PDF format using reportlab.

**Usage:**
```bash
python utils/convert_md_to_pdf.py <input.md> <output.pdf>
```

**Example:**
```bash
python utils/convert_md_to_pdf.py resume-workspace/tailored/connor-sample-2026-04/final.md resume-workspace/tailored/connor-sample-2026-04/final.pdf
```

**Requirements:**
- `reportlab` (install via `pip install reportlab`)

**What it does:**
- Reads Markdown file with headers (`#`, `##`, `###`)
- Converts bullet points (`-`) to formatted list items
- Preserves spacing and line breaks
- Outputs a single-page or multi-page PDF

---

### `convert_md_to_docx.py`

Convert Markdown resume files to DOCX (Word document) format using python-docx.

**Usage:**
```bash
python utils/convert_md_to_docx.py <input.md> <output.docx>
```

**Example:**
```bash
python utils/convert_md_to_docx.py resume-workspace/tailored/connor-sample-2026-04/final.md resume-workspace/tailored/connor-sample-2026-04/final.docx
```

**Requirements:**
- `python-docx` (install via `pip install python-docx`)

**What it does:**
- Reads Markdown file with headers (`#`, `##`, `###`)
- Converts headers to Word heading styles
- Converts bullet points (`-`) to Word bullet list style
- Preserves spacing and line breaks
- Outputs a native DOCX file that can be opened and edited in Microsoft Word

---

## Contributing

To add a new utility script:
1. Create a new `.py` file in this directory
2. Add a docstring and clear usage instructions
3. Update this README with the script name, purpose, and examples
4. Ensure it has a standalone `if __name__ == '__main__':` entry point
