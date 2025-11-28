import fitz  # PyMuPDF library
import re
import json
import os
from typing import List, Dict, Any

# --- CONFIGURATION ---
PDF_PATH = "pdf_extract/engineering_edited.pdf"  # 🚨 UPDATE THIS PATH!
OUTPUT_JSON_PATH = "structured_modules_engineering.json"

# Example Regex: Finds 2-4 capital letters followed by 3-4 digits (e.g., CS101, EE4200)
# Adjust this regex to exactly match your module codes!
MODULE_CODE_PATTERN = r'\b([A-Z]{2,4}\d{3,4})\b'

# --- CORE FUNCTIONS ---

def extract_text_from_pdf(pdf_path: str) -> str:
    """Extracts all text from a PDF file."""
    try:
        doc = fitz.open(pdf_path)
        full_text = ""
        for page in doc:
            full_text += page.get_text()
        return full_text
    except Exception as e:
        print(f"Error opening or reading PDF: {e}")
        return ""


def structure_modules(full_text: str) -> List[Dict[str, Any]]:
    """
    Splits the full text into individual module records using a regex pattern.
    """

    # 1. Use the pattern to find all module codes and their starting positions.
    matches = list(re.finditer(MODULE_CODE_PATTERN, full_text))

    if not matches:
        print(f"ERROR: No module codes found using pattern: {MODULE_CODE_PATTERN}")
        return []

    structured_data = []

    # 2. Iterate through matches to define the boundaries of each module's description.
    for i in range(len(matches)):
        start_index = matches[i].start()

        # The description ends either at the start of the next module or the end of the document.
        end_index = matches[i + 1].start() if i + 1 < len(matches) else len(full_text)

        module_code = matches[i].group(1)
        # The description is the text block between the module code and the next module code.
        description = full_text[start_index:end_index].strip()

        # Simple method to guess the module name (often the first line after the code)
        first_line = description.split('\n')[0].replace(module_code, '').strip()
        module_name = first_line if len(first_line) > 5 and len(first_line) < 100 else f"Module {module_code}"

        structured_data.append({
            "code": module_code,
            "name": module_name,
            # We use the full text chunk for the AI input later
            "description_text": description,
        })

    print(f"Successfully extracted and structured {len(structured_data)} modules.")
    return structured_data


def save_to_json(data: List[Dict[str, Any]], path: str):
    """Saves the final structured list to a JSON file."""
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=4, ensure_ascii=False)
    print(f"Data saved successfully to {path}")


def main():
    """Main execution flow."""
    print(f"Starting PDF ingestion from {PDF_PATH}...")

    if not os.path.exists(PDF_PATH):
        print(f"FATAL: PDF file not found at {PDF_PATH}. Please update PDF_PATH.")
        return

    raw_text = extract_text_from_pdf(PDF_PATH)

    if not raw_text:
        return

    structured_list = structure_modules(raw_text)

    if structured_list:
        save_to_json(structured_list, OUTPUT_JSON_PATH)


if __name__ == "__main__":
    main()