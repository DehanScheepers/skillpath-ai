# scripts/extract_pdf.py
from PyPDF2 import PdfReader
import re, json

reader = PdfReader("2025-engineering.pdf")
text = ""
for p in reader.pages:
    page_text = p.extract_text() or ""
    text += page_text + "\n\n"

# crude splitting: find "Programme" headings or "Curriculum of" / "Programme description"
# adjust regex as needed for the specific PDF structure
program_blocks = re.split(r'\n(?=[A-Z0-9]{2,}\s+\([0-9]+\))', text)  # example split on module codes
# Fallback: save whole text for manual extraction if program_blocks is messy
with open("yearbook_raw.txt","w",encoding="utf-8") as f:
    f.write(text)

print("Raw text saved to yearbook_raw.txt. Now manually or iteratively identify programme blocks.")