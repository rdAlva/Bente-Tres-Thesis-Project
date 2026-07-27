import pandas as pd
from pathlib import Path
import shutil
from app.nlp.similarity import compare_uploaded_document

# Path to files
SCRIPT_DIR = Path(__file__).resolve().parent

#Move Original Files Path
source_pathTxt = SCRIPT_DIR.parent / "utils" / "txtFileUpload"
source_pathPdf = SCRIPT_DIR.parent / "static" / "file"
#Move New Files Path

destinationFlag_path = SCRIPT_DIR.parent.parent / "corpus" / "review"
destinationProm_path = SCRIPT_DIR.parent.parent / "corpus" / "promoted"
source_logs = SCRIPT_DIR.parent.parent / "logs"

# THRESHOLD VALUE
threshold = 0.35

def run_promotion(
    uploaded_filename,
    uploaded_processed,
    uploaded_original,

    promoted_filenames,
    promoted_processed,
    promoted_original,
):
    (
    all_pairs,
    flagged,
    to_promote,
    similarity_report,
    uploaded_document_html,
    repository_document_html,
) = compare_uploaded_document(
    uploaded_filename,
    uploaded_processed,
    uploaded_original,
    promoted_filenames,
    promoted_processed,
    promoted_original,
    threshold,
)
    print("\n" + "=" * 70)
    print(f"SUMMARY FOR: {uploaded_filename}")
    print("=" * 70)

    print(f"\nFLAGGED PAIRS ({len(flagged)} found):")

    for pair in flagged:

        print(
            f"  Rank {pair['rank']}: "
            f"{pair['doc2']} "
            f"→ {pair['combined_score']} "
            f"({pair['decision']})"
        )

    print(f"\nTO PROMOTE ({len(to_promote)} found):")

    for pair in to_promote:

        print(
            f"  Rank {pair['rank']}: "
            f"{pair['doc2']} "
            f"→ {pair['combined_score']} "
            f"({pair['decision']})"
        )

    print("=" * 70)

    # Save CSV to logs folder
    df_results = pd.DataFrame(all_pairs)
    results_file = source_logs / "DocumentSimilarity_results.csv"

    df_results.to_csv(
        results_file,
        mode="a",
        header=not results_file.exists(),
        index=False
    )

    df_sentences = pd.DataFrame(similarity_report)
    sentences_file = source_logs / "SimilarSentencesReport.csv"

    df_sentences.to_csv(
        sentences_file,
        mode="a",
        header=not sentences_file.exists(),
        index=False
    )

    return {
        "uploaded_filename": uploaded_filename,
        "all_pairs": all_pairs,
        "flagged": flagged,
        "to_promote": to_promote,
        "similarity_report": similarity_report,
        "uploaded_document_html": uploaded_document_html,
        "repository_document_html": repository_document_html,
    }

def move_to_promoted(filename):

    txt_file = source_pathTxt / filename

    if txt_file.exists():
        shutil.move(
            str(txt_file),
            str(destinationProm_path / filename)
        )
        print(f"Promoted TXT: {filename}")

    pdf_name = Path(filename).stem + ".pdf"
    pdf_file = source_pathPdf / pdf_name

    if pdf_file.exists():
        shutil.move(
            str(pdf_file),
            str(destinationProm_path / pdf_name)
        )
        print(f"Promoted PDF: {pdf_name}")

def move_to_review(filename):

    txt_file = source_pathTxt / filename

    if txt_file.exists():
        shutil.move(
            str(txt_file),
            str(destinationFlag_path / filename)
        )
        print(f"Moved TXT: {filename}")

    pdf_name = Path(filename).stem + ".pdf"
    pdf_file = source_pathPdf / pdf_name

    if pdf_file.exists():
        shutil.move(
            str(pdf_file),
            str(destinationFlag_path / pdf_name)
        )
        print(f"Moved PDF: {pdf_name}")



