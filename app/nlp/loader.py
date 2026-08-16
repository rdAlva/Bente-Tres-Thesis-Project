import time
from pathlib import Path
import logging

from app.nlp.preprocessing import preprocess_text
from app.utils.pdf_extractor import extract_pdfs
from app.storage.supabase_storage import sync_folder_to_local

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
processed_corpus_path = SCRIPT_DIR.parent.parent / "corpus" / "processed"

RUNTIME_CACHE_PATH = (
    SCRIPT_DIR.parent.parent / "runtime_cache" / "corpus"
)

runtime_promoted_path = RUNTIME_CACHE_PATH / "promoted"
runtime_processed_path = RUNTIME_CACHE_PATH / "processed"


def load_corpus():
    overall_start = time.perf_counter()
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

    uploaded_read_time = 0
    uploaded_preprocess_time = 0

    repo_read_time = 0

    # --------------------------------------------------------------
    # Load TXT files from upload folder and promoted corpus
    # --------------------------------------------------------------
    if not directory_path.exists():
        print(f"[WARNING] Upload folder not found: {directory_path}")
    upload_start = time.perf_counter()
    for txt_file in sorted(directory_path.glob("*.txt")):
        try:
            read_start = time.perf_counter()
            original_text = txt_file.read_text(
                encoding="utf-8",
                errors="ignore"
            )
            uploaded_read_time += time.perf_counter() - read_start

            preprocess_start = time.perf_counter()
            processed_text = preprocess_text(txt_file)
            uploaded_preprocess_time += (
                time.perf_counter() - preprocess_start
            )

            if not processed_text.strip():
                continue

            uploaded_original.append(original_text)
            uploaded_corpus.append(processed_text)
            uploaded_filenames.append(txt_file.name)

        except Exception as e:
            print(f"[ERROR] Failed to process {txt_file.name}: {e}")
            logging.exception(e)
    upload_time = time.perf_counter() - upload_start

    # --------------------------------------------------------------
    # Synchronize persistent repository TXT files from Supabase
    # into the local runtime cache.
    # --------------------------------------------------------------
    try:
        sync_folder_to_local(
            "promoted",
            runtime_promoted_path,
            extensions={".txt"}
        )

        sync_folder_to_local(
            "processed",
            runtime_processed_path,
            extensions={".txt"}
        )

    except Exception as e:
        print(
            f"[ERROR] Failed to synchronize repository "
            f"from Supabase Storage: {e}"
        )
        logging.exception(e)
        return (
            uploaded_filenames,
            uploaded_corpus,
            uploaded_original,
            [],
            [],
            []
        )

    if not corpus_path.exists():
        print(f"[WARNING] Repository folder not found: {corpus_path}")

    if not processed_corpus_path.exists():
        print(
            f"[WARNING] Processed repository folder not found: "
            f"{processed_corpus_path}"
        )

    repo_start = time.perf_counter()

    for txt_file in sorted(runtime_promoted_path.glob("*.txt")):

        try:
            # ----------------------------------------------------------
            # Load original repository text
            # Used for review/highlighting/display
            # ----------------------------------------------------------
            read_start = time.perf_counter()

            original_text = txt_file.read_text(
                encoding="utf-8",
                errors="ignore"
            )

            repo_read_time += time.perf_counter() - read_start

            # ----------------------------------------------------------
            # Load already-processed repository text
            # DO NOT preprocess again
            # ----------------------------------------------------------
            processed_file = runtime_processed_path / txt_file.name

            if not processed_file.exists():
                print(
                    f"[WARNING] Processed file missing for "
                    f"{txt_file.name}: {processed_file}"
                )
                continue

            processed_text = processed_file.read_text(
                encoding="utf-8",
                errors="ignore"
            )

            if not processed_text.strip():
                continue

            promoted_original.append(original_text)
            promoted_corpus.append(processed_text)
            promoted_filenames.append(txt_file.name)

        except Exception as e:
            print(f"[ERROR] Failed to load {txt_file.name}: {e}")
            logging.exception(e)

    repo_time = time.perf_counter() - repo_start
    overall_time = time.perf_counter() - overall_start

    # FOR DEBUGGING PURPOSES, PRINT THE LOADING TIMES AND COUNTS
    # print("\n========== Corpus Loading Breakdown ==========")

    # print(f"Uploaded Files        : {len(uploaded_filenames)}")
    # print(f"Uploaded Read         : {uploaded_read_time:.3f} sec")
    # print(f"Uploaded Preprocess   : {uploaded_preprocess_time:.3f} sec")
    # print(f"Uploaded Total        : {upload_time:.3f} sec")

    # print()

    # print(f"Repository Files      : {len(promoted_filenames)}")
    # print(f"Repository Read       : {repo_read_time:.3f} sec")
    # print(f"Repository Total      : {repo_time:.3f} sec")

    # print()

    # print(f"Overall Loading Time  : {overall_time:.3f} sec")

    # print("==============================================\n")

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