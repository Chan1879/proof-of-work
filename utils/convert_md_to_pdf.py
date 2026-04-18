from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
import sys

def markdown_to_pdf(md_file, pdf_file):
    # Read the markdown file
    with open(md_file, 'r') as f:
        content = f.read()

    # Simple conversion: treat as text, split by lines
    lines = content.split('\n')
    story = []
    styles = getSampleStyleSheet()

    for line in lines:
        if line.startswith('# '):
            story.append(Paragraph(line[2:], styles['Heading1']))
        elif line.startswith('## '):
            story.append(Paragraph(line[3:], styles['Heading2']))
        elif line.startswith('### '):
            story.append(Paragraph(line[4:], styles['Heading3']))
        elif line.startswith('- '):
            story.append(Paragraph('• ' + line[2:], styles['Normal']))
        elif line.strip() == '':
            story.append(Spacer(1, 12))
        else:
            story.append(Paragraph(line, styles['Normal']))

    # Create PDF
    doc = SimpleDocTemplate(pdf_file, pagesize=letter)
    doc.build(story)

if __name__ == '__main__':
    if len(sys.argv) != 3:
        print("Usage: python convert_md_to_pdf.py input.md output.pdf")
        sys.exit(1)
    markdown_to_pdf(sys.argv[1], sys.argv[2])
