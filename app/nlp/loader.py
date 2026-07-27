from pathlib import Path
import logging

from app.nlp.preprocessing import preprocess_text
from app.utils.pdf_extractor import extract_pdfs

# ------------------------------------------------------------------
# Logging Configuration
# ------------------------------------------------------------------
logging.basicConfig(
    filename="logs/system.log",
    level=logging.ERROR,
    format="%(asctime)s - %(levelname)s - %(message)s"
)

SCRIPT_DIR = Path(__file__).resolve().parent

directory_path = SCRIPT_DIR.parent / "utils" / "txtFileUpload"
corpus_path = SCRIPT_DIR.parent.parent / "corpus" / "promoted"


def load_corpus():
    """
    Ensures all uploaded PDFs are converted to text before loading the corpus.

    Returns:
        corpus (list[str])
        filenames (list[str])
    """

    # --------------------------------------------------------------
    # Convert uploaded PDFs into TXT files
    # --------------------------------------------------------------
    try:
        extract_pdfs()

    except FileNotFoundError:
        print("[ERROR] PDF source folder was not found.")
        logging.exception("PDF source folder not found.")
        return [], []

    except PermissionError:
        print("[ERROR] Permission denied while extracting PDFs.")
        logging.exception("Permission denied during PDF extraction.")
        return [], []

    except Exception as e:
        print(f"[ERROR] Failed during PDF extraction: {e}")
        logging.exception(e)
        return [], []


    uploaded_corpus = []
    uploaded_filenames = []

    promoted_corpus = []
    promoted_filenames = []

    uploaded_original = []
    promoted_original = []

    # --------------------------------------------------------------
    # Load TXT files from upload folder and promoted corpus
    # --------------------------------------------------------------
    if not directory_path.exists():
        print(f"[WARNING] Upload folder not found: {directory_path}")
    for txt_file in sorted(directory_path.glob("*.txt")):
        try:

            original_text = txt_file.read_text(
                encoding="utf-8",
                errors="ignore"
            )

            processed_text = preprocess_text(txt_file)

            if not processed_text.strip():
                continue

            uploaded_original.append(original_text)
            uploaded_corpus.append(processed_text)
            uploaded_filenames.append(txt_file.name)

        except Exception as e:
            print(f"[ERROR] Failed to process {txt_file.name}: {e}")
            logging.exception(e)

    if not corpus_path.exists():
        print(f"[WARNING] Repository folder not found: {corpus_path}")
    for txt_file in sorted(corpus_path.glob("*.txt")):

        try:

            original_text = txt_file.read_text(
                encoding="utf-8",
                errors="ignore"
            )

            processed_text = preprocess_text(txt_file)

            if not processed_text.strip():
                continue

            promoted_original.append(original_text)
            promoted_corpus.append(processed_text)
            promoted_filenames.append(txt_file.name)

        except Exception as e:
            print(f"[ERROR] Failed to process {txt_file.name}: {e}")
            logging.exception(e)

    return (
        uploaded_filenames,
        uploaded_corpus,
        uploaded_original,

        promoted_filenames,
        promoted_corpus,
        promoted_original,
    )

def load_raw_document(filename, folder):
    """
    Loads the original text without preprocessing.
    Used only for displaying in the Review page.
    """

    file_path = folder / filename

    if not file_path.exists():
        return ""

    try:
        return file_path.read_text(encoding="utf-8")

    except Exception as e:
        logging.exception(e)
        return ""