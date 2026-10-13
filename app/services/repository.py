from pathlib import Path
import shutil

from app.utils.pdf_extractor import extract_pdfs
from app.nlp.preprocessing import preprocess_text
from app.storage.supabase_storage import upload_file


# --------------------------------------------------
# Paths
# --------------------------------------------------

SCRIPT_DIR = Path(__file__).resolve().parent

UPLOAD_PDF = SCRIPT_DIR.parent / "static" / "file"
UPLOAD_TXT = SCRIPT_DIR.parent / "utils" / "txtFileUpload"

PROMOTED_PDF = SCRIPT_DIR.parent.parent / "corpus" / "promoted"
PROMOTED_TXT = SCRIPT_DIR.parent.parent / "corpus" / "promoted"
PROCESSED_TXT = SCRIPT_DIR.parent.parent / "corpus" / "processed"

MAX_SUPABASE_FILE_SIZE = 50 * 1024 * 1024  # 50 MB


def upload_repository():

    """
    Upload trusted documents directly into the repository.

    Local copies are retained for the current runtime/cache,
    while persistent copies are uploaded to Supabase Storage.

    Returns:
        uploaded_files (list)
    """

    print("\n======================================")
    print("REPOSITORY UPLOAD")
    print("======================================")

    # --------------------------------------------------
    # Convert uploaded PDFs into TXT files
    # --------------------------------------------------

    extract_pdfs()

    # --------------------------------------------------
    # Make sure local processed corpus exists
    # --------------------------------------------------

    PROCESSED_TXT.mkdir(
        parents=True,
        exist_ok=True
    )

    uploaded_files = []

    # --------------------------------------------------
    # Process every extracted TXT
    # --------------------------------------------------

    for txt_file in UPLOAD_TXT.glob("*.txt"):

        pdf_name = txt_file.stem + ".pdf"
        pdf_file = UPLOAD_PDF / pdf_name

        print(f"\nAdding {pdf_name} to repository...")

        try:

            # ------------------------------------------
            # Prepare destination paths
            # ------------------------------------------

            promoted_txt_file = PROMOTED_TXT / txt_file.name
            processed_file = PROCESSED_TXT / txt_file.name
            promoted_pdf_file = PROMOTED_PDF / pdf_name

            # ------------------------------------------
            # Check PDF size before cloud upload
            # ------------------------------------------

            if pdf_file.exists():

                pdf_size = pdf_file.stat().st_size

                if pdf_size > MAX_SUPABASE_FILE_SIZE:

                    print(
                        f"[ERROR] {pdf_name} is larger than "
                        f"the Supabase Free 50 MB file limit."
                    )

                    print(
                        f"Size: "
                        f"{pdf_size / (1024 * 1024):.2f} MB"
                    )

                    print(
                        f"Skipping {pdf_name}."
                    )

                    continue

            # ------------------------------------------
            # Move original TXT locally
            # ------------------------------------------

            shutil.move(
                str(txt_file),
                str(promoted_txt_file)
            )

            print(
                f"Promoted TXT locally: {txt_file.name}"
            )

            # ------------------------------------------
            # Move original PDF locally
            # ------------------------------------------

            if pdf_file.exists():

                shutil.move(
                    str(pdf_file),
                    str(promoted_pdf_file)
                )

                print(
                    f"Promoted PDF locally: {pdf_name}"
                )

            # ------------------------------------------
            # Preprocess trusted document ONCE
            # ------------------------------------------

            processed_text = preprocess_text(
                promoted_txt_file
            )

            processed_file.write_text(
                processed_text,
                encoding="utf-8"
            )

            print(
                f"Processed TXT locally: {txt_file.name}"
            )

            # ------------------------------------------
            # Upload persistent original TXT
            # ------------------------------------------

            upload_file(
                promoted_txt_file,
                f"promoted/{txt_file.name}",
                overwrite=True
            )

            print(
                f"Uploaded to Supabase: "
                f"promoted/{txt_file.name}"
            )

            # ------------------------------------------
            # Upload persistent processed TXT
            # ------------------------------------------

            upload_file(
                processed_file,
                f"processed/{txt_file.name}",
                overwrite=True
            )

            print(
                f"Uploaded to Supabase: "
                f"processed/{txt_file.name}"
            )

            # ------------------------------------------
            # Upload persistent PDF
            # ------------------------------------------

            if promoted_pdf_file.exists():

                upload_file(
                    promoted_pdf_file,
                    f"promoted/{pdf_name}",
                    overwrite=True
                )

                print(
                    f"Uploaded to Supabase: "
                    f"promoted/{pdf_name}"
                )

            # ------------------------------------------
            # Only count document after all cloud
            # uploads succeed
            # ------------------------------------------

            uploaded_files.append(pdf_name)

            print(
                f"[SUCCESS] Repository upload complete: "
                f"{pdf_name}"
            )

        except Exception as e:

            print(
                f"[ERROR] Failed to persist {pdf_name}: {e}"
            )

            print(
                "The local repository copy remains in place, "
                "but the Supabase upload was not completed."
            )

    print("\nRepository upload completed.")

    return uploaded_files