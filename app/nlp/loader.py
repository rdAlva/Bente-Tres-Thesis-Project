# from pathlib import Path
# from app.nlp.preprocessing import preprocess_text
# from app.utils.pdf_extractor import extract_pdfs

# SCRIPT_DIR = Path(__file__).resolve().parent

# directory_path = SCRIPT_DIR.parent / "utils" / "txtFileUpload"
# corpus_path = SCRIPT_DIR.parent.parent / "corpus" / "promoted"


# def load_corpus():
#     """
#     Ensures all uploaded PDFs are converted to text before loading the corpus.
#     Returns:
#         corpus (list[str])
#         filenames (list[str])
#     """

#     # Convert any newly uploaded PDFs into .txt files.
#     # Existing .txt files are skipped by extract_pdfs().
#     extract_pdfs()

#     corpus = []
#     filenames = []

#     for folder in [directory_path, corpus_path]:

#         if not folder.exists():
#             continue

#         for txt_file in folder.glob("*.txt"):

#             processed_text = preprocess_text(txt_file)

#             # Ignore empty documents
#             if processed_text.strip():

#                 corpus.append(processed_text)
#                 filenames.append(txt_file.name)

#     return corpus, filenames

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

    corpus = []
    filenames = []

    # --------------------------------------------------------------
    # Load TXT files from upload folder and promoted corpus
    # --------------------------------------------------------------
    for folder in [directory_path, corpus_path]:

        if not folder.exists():
            print(f"[WARNING] Folder does not exist: {folder}")
            continue

        for txt_file in folder.glob("*.txt"):

            try:

                processed_text = preprocess_text(txt_file)

                # Skip empty documents
                if not processed_text.strip():
                    print(f"[WARNING] Empty document skipped: {txt_file.name}")
                    continue

                corpus.append(processed_text)
                filenames.append(txt_file.name)

            except FileNotFoundError:
                print(f"[ERROR] File not found: {txt_file.name}")
                logging.exception("File not found.")

            except PermissionError:
                print(f"[ERROR] Permission denied: {txt_file.name}")
                logging.exception("Permission denied.")

            except UnicodeDecodeError:
                print(f"[ERROR] Encoding error in: {txt_file.name}")
                logging.exception("Encoding error.")

            except Exception as e:
                print(f"[ERROR] Failed to process {txt_file.name}: {e}")
                logging.exception(e)

    return corpus, filenames