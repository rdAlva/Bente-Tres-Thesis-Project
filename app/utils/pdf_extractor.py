import os
from pathlib import Path
import pymupdf

# Consistent path management using Pathlib
BASE_DIR = Path(__file__).resolve().parent.parent
pdf_folder = BASE_DIR / "static" / "file"
txt_folder = BASE_DIR / "utils" / "txtFileUpload"

# Create destination folder if it doesn't exist
txt_folder.mkdir(parents=True, exist_ok=True)

def extract_pdfs():
    if not pdf_folder.exists():
        print(f"Source folder not found: {pdf_folder}")
        return

    for pdf_path in pdf_folder.glob("*.pdf"):
        txt_path = txt_folder / f"{pdf_path.stem}.txt"

        # Efficiency: Skip files already converted
        if txt_path.exists():
            continue

        try:
            with pymupdf.open(pdf_path) as doc:
                # Use newline joiner for better sentence boundaries in NLP
                text = "\n".join([page.get_text() for page in doc])

            txt_path.write_text(text, encoding="utf-8")
            print(f"Converted: {pdf_path.name} -> {txt_path.name}")

        except Exception as e:
            print(f"Error converting {pdf_path.name}: {e}")

if __name__ == "__main__":
    extract_pdfs()