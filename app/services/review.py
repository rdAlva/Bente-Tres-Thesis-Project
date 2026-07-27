from pathlib import Path
from app.nlp.loader import load_raw_document
import pandas as pd

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
    }

    # --------------------------------------------------
    # Read overall similarity report
    # --------------------------------------------------

    if RESULTS_FILE.exists():

        try:

            df_results = pd.read_csv(RESULTS_FILE)

            document_rows = df_results[
                df_results["doc1"] == filename
            ]

            if not document_rows.empty:

                # Highest ranked match
                top_match = document_rows.iloc[0]

                report["summary"] = {

                    "repository_document": top_match["doc2"],

                    "combined_score": top_match["combined_score"],

                    "decision": top_match["decision"],

                    "cosine_score": top_match["cosine_score"],

                    "jaccard_unigram": top_match["jaccard_unigram"],

                    "jaccard_bigram": top_match["jaccard_bigram"],

                    "jaccard_trigram": top_match["jaccard_trigram"]

                }

                uploaded_text = load_raw_document(
                    filename,
                    REVIEW_FOLDER
                )

                repository_text = load_raw_document(
                    top_match["doc2"],
                    PROMOTED_FOLDER
                )

                report["uploaded_text"] = uploaded_text
                report["repository_text"] = repository_text


        except Exception as e:

            print(f"Error reading similarity results: {e}")

    # --------------------------------------------------
    # Read sentence similarity report
    # --------------------------------------------------

    if SENTENCES_FILE.exists():

        try:

            df_sentences = pd.read_csv(SENTENCES_FILE)

            matches = df_sentences[
                df_sentences["document_1"] == filename
            ]

            report["matches"] = matches.to_dict(
                orient="records"
            )

            # -------------------------------
            # Build highlighted document view
            # -------------------------------

            from app.nlp.similarity import highlight_document

            uploaded_matches = [
                row["sentence_from_doc1"]
                for _, row in matches.iterrows()
            ]

            repository_matches = [
                row["sentence_from_doc2"]
                for _, row in matches.iterrows()
            ]

            report["uploaded_html"] = highlight_document(
                report["uploaded_text"],
                uploaded_matches
            )

            report["repository_html"] = highlight_document(
                report["repository_text"],
                repository_matches
            )

        except Exception as e:

            print(f"Error reading sentence report: {e}")

        return report