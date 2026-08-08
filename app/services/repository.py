from pathlib import Path
import shutil

from app.utils.pdf_extractor import extract_pdfs
from app.nlp.preprocessing import preprocess_text

# --------------------------------------------------
# Paths
# --------------------------------------------------

SCRIPT_DIR = Path(__file__).resolve().parent

UPLOAD_PDF = SCRIPT_DIR.parent / "static" / "file"
UPLOAD_TXT = SCRIPT_DIR.parent / "utils" / "txtFileUpload"

PROMOTED_PDF = SCRIPT_DIR.parent.parent / "corpus" / "promoted"
PROMOTED_TXT = SCRIPT_DIR.parent.parent / "corpus" / "promoted"
PROCESSED_TXT = SCRIPT_DIR.parent.parent / "corpus" / "processed"


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

    # Make sure processed corpus folder exists
    PROCESSED_TXT.mkdir(parents=True, exist_ok=True)

    uploaded_files = []

    for txt_file in UPLOAD_TXT.glob("*.txt"):

        pdf_name = txt_file.stem + ".pdf"

        pdf_file = UPLOAD_PDF / pdf_name

        print(f"Adding {pdf_name} to repository...")

        # ----------------------------------------------
        # Move original TXT into promoted repository
        # ----------------------------------------------

        promoted_txt_file = PROMOTED_TXT / txt_file.name

        shutil.move(
            str(txt_file),
            str(promoted_txt_file)
        )

        # ----------------------------------------------
        # Move original PDF into promoted repository
        # ----------------------------------------------

        if pdf_file.exists():

            shutil.move(
                str(pdf_file),
                str(PROMOTED_PDF / pdf_name)
            )

        # ----------------------------------------------
        # Preprocess trusted document ONCE
        # ----------------------------------------------

        processed_text = preprocess_text(promoted_txt_file)

        processed_file = PROCESSED_TXT / txt_file.name

        processed_file.write_text(
            processed_text,
            encoding="utf-8"
        )

        uploaded_files.append(pdf_name)

    print("Repository upload completed.")

    return uploaded_files