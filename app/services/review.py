from pathlib import Path
import pandas as pd

from app.nlp.loader import load_raw_document
from app.storage.supabase_storage import download_text


# --------------------------------------------------
# Paths
# --------------------------------------------------

SCRIPT_DIR = Path(__file__).resolve().parent

UPLOAD_FOLDER = SCRIPT_DIR.parent / "utils" / "txtFileUpload"
PROMOTED_FOLDER = SCRIPT_DIR.parent.parent / "corpus" / "promoted"
REVIEW_FOLDER = SCRIPT_DIR.parent.parent / "corpus" / "review"

LOGS_FOLDER = SCRIPT_DIR.parent.parent / "logs"

RESULTS_FILE = LOGS_FOLDER / "DocumentSimilarity_results.csv"
SENTENCES_FILE = LOGS_FOLDER / "SimilarSentencesReport.csv"

# Expected columns of SimilarSentencesReport.csv. Older reports may
# have been written without a header row, so the reader falls back
# to these names when the header is missing.
SENTENCE_REPORT_COLUMNS = [
    "document_1",
    "document_2",
    "sentence_similarity",
    "sentence_from_doc1",
    "sentence_from_doc2",
    "sentence_from_doc1_html",
    "sentence_from_doc2_html",
]


def load_persistent_document(
    filename,
    storage_folder,
    local_folder
):
    """
    Load a persistent document from Supabase Storage.

    Falls back to the local filesystem when the Supabase
    object cannot be retrieved. The local fallback is useful
    during development and provides resilience while the
    migration is still in progress.
    """

    safe_filename = Path(filename).name

    storage_path = (
        f"{storage_folder}/{safe_filename}"
    )

    # --------------------------------------------------
    # Primary source: Supabase Storage
    # --------------------------------------------------

    try:

        text = download_text(storage_path)

        if text is not None and text.strip():

            return text

    except Exception as e:

        print(
            f"[WARNING] Failed to load "
            f"{storage_path} from Supabase: {e}"
        )

    # --------------------------------------------------
    # Development/runtime fallback: local filesystem
    # --------------------------------------------------

    try:

        local_text = load_raw_document(
            safe_filename,
            local_folder
        )

        if local_text:

            print(
                f"[REVIEW] Using local fallback for "
                f"{safe_filename}"
            )

            return local_text

    except Exception as e:

        print(
            f"[WARNING] Failed local fallback for "
            f"{safe_filename}: {e}"
        )

    return ""


def load_review_report(filename):
    """
    Loads the review information for one uploaded document.

    Returns
    -------
    dict
    """

    report = {
        "document": filename,
        "summary": None,
        "matches": [],

        "uploaded_text": "",
        "repository_text": "",

        "uploaded_html": "",
        "repository_html": "",
    }

    # --------------------------------------------------
    # Read overall similarity report
    # --------------------------------------------------

    if RESULTS_FILE.exists():

        try:

            df_results = pd.read_csv(
                RESULTS_FILE
            )

            document_rows = df_results[
                df_results["doc1"] == filename
            ]

            if not document_rows.empty:

                # Highest ranked match
                top_match = document_rows.iloc[0]

                repository_filename = (
                    str(top_match["doc2"])
                )

                report["summary"] = {

                    "repository_document":
                        repository_filename,

                    "combined_score":
                        top_match["combined_score"],

                    "decision":
                        top_match["decision"],

                    "cosine_score":
                        top_match["cosine_score"],

                    "jaccard_unigram":
                        top_match["jaccard_unigram"],

                    "jaccard_bigram":
                        top_match["jaccard_bigram"],

                    "jaccard_trigram":
                        top_match["jaccard_trigram"]

                }

                # --------------------------------------------------
                # Load uploaded document from persistent review storage
                # --------------------------------------------------

                uploaded_text = load_persistent_document(
                    filename,
                    "review",
                    REVIEW_FOLDER
                )

                # --------------------------------------------------
                # Load matched repository document from persistent
                # promoted storage
                # --------------------------------------------------

                repository_text = load_persistent_document(
                    repository_filename,
                    "promoted",
                    PROMOTED_FOLDER
                )

                report["uploaded_text"] = uploaded_text
                report["repository_text"] = repository_text

        except Exception as e:

            print(
                f"Error reading similarity results: {e}"
            )

    # --------------------------------------------------
    # Read sentence similarity report
    # --------------------------------------------------

    if SENTENCES_FILE.exists():

        try:

            df_sentences = pd.read_csv(
                SENTENCES_FILE
            )

            # Legacy headerless reports: the first data row would be
            # consumed as the header, so document_1 would not exist.
            if "document_1" not in df_sentences.columns:

                df_sentences = pd.read_csv(
                    SENTENCES_FILE,
                    names=SENTENCE_REPORT_COLUMNS,
                )

            matches = df_sentences[
                df_sentences["document_1"] == filename
            ]

            report["matches"] = matches.to_dict(
                orient="records"
            )

            # --------------------------------------------------
            # Build highlighted document view
            # --------------------------------------------------

            from app.nlp.similarity import highlight_document

            uploaded_matches = [
                row["sentence_from_doc1"]
                for _, row in matches.iterrows()
            ]

            repository_matches = [
                row["sentence_from_doc2"]
                for _, row in matches.iterrows()
            ]

            report["uploaded_html"] = (
                highlight_document(
                    report["uploaded_text"],
                    uploaded_matches
                )
            )

            report["repository_html"] = (
                highlight_document(
                    report["repository_text"],
                    repository_matches
                )
            )

        except Exception as e:

            print(
                f"Error reading sentence report: {e}"
            )

    # --------------------------------------------------
    # Always return the report
    # --------------------------------------------------

    return report