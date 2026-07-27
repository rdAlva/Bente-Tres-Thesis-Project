from pathlib import Path
import shutil

from app.utils.pdf_extractor import extract_pdfs

# --------------------------------------------------
# Paths
# --------------------------------------------------

SCRIPT_DIR = Path(__file__).resolve().parent

UPLOAD_PDF = SCRIPT_DIR.parent / "static" / "file"
UPLOAD_TXT = SCRIPT_DIR.parent / "utils" / "txtFileUpload"

PROMOTED_PDF = SCRIPT_DIR.parent.parent / "corpus" / "promoted"
PROMOTED_TXT = SCRIPT_DIR.parent.parent / "corpus" / "promoted"


def upload_repository():

    """
    Upload trusted documents directly into the repository.

    Returns:
        uploaded_files (list)
    """

    print("\n======================================")
    print("REPOSITORY UPLOAD")
    print("======================================")

    # Convert PDFs into TXT files
    extract_pdfs()

    uploaded_files = []

    for txt_file in UPLOAD_TXT.glob("*.txt"):

        pdf_name = txt_file.stem + ".pdf"

        pdf_file = UPLOAD_PDF / pdf_name

        print(f"Adding {pdf_name} to repository...")

        # Move TXT

        shutil.move(
            str(txt_file),
            str(PROMOTED_TXT / txt_file.name)
        )

        # Move PDF

        if pdf_file.exists():

            shutil.move(
                str(pdf_file),
                str(PROMOTED_PDF / pdf_name)
            )

        uploaded_files.append(pdf_name)

    print("Repository upload completed.")

    return uploaded_files