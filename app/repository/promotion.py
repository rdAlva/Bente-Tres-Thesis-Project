import pandas as pd
from pathlib import Path
import shutil
from app.nlp.similarity import compare_uploaded_document
from app.nlp.preprocessing import preprocess_text
from app.nlp.preprocessing import preprocess_text
from app.storage.supabase_storage import (
    upload_file,
    delete_file,
)

# Path to files
SCRIPT_DIR = Path(__file__).resolve().parent

#Move Original Files Path
source_pathTxt = SCRIPT_DIR.parent / "utils" / "txtFileUpload"
source_pathPdf = SCRIPT_DIR.parent / "static" / "file"
#Move New Files Path

destinationFlag_path = SCRIPT_DIR.parent.parent / "corpus" / "review"
destinationProm_path = SCRIPT_DIR.parent.parent / "corpus" / "promoted"
destinationProcessed_path = SCRIPT_DIR.parent.parent / "corpus" / "processed"
source_logs = SCRIPT_DIR.parent.parent / "logs"

destinationProcessed_path = (
    SCRIPT_DIR.parent.parent
    / "corpus"
    / "processed"
)

# # THRESHOLD VALUE
# threshold = 0.35

def run_promotion(
    uploaded_filename,
    uploaded_processed,
    uploaded_original,

    promoted_filenames,
    promoted_processed,
    promoted_original,

    threshold,
):
    print(f"run_promotion() received threshold = {threshold:.2f}")
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

    if df_sentences.empty:
        df_sentences = pd.DataFrame(columns=[
            "document_1",
            "document_2",
            "sentence_similarity",
            "sentence_from_doc1",
            "sentence_from_doc2",
            "sentence_from_doc1_html",
            "sentence_from_doc2_html",
        ])

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
    promoted_txt_file = destinationProm_path / filename

    try:

        # --------------------------------------------------
        # Move TXT locally
        # --------------------------------------------------

        if txt_file.exists():

            shutil.move(
                str(txt_file),
                str(promoted_txt_file)
            )

            print(
                f"Promoted TXT locally: {filename}"
            )

        else:
            print(
                f"[WARNING] TXT not found for promotion: "
                f"{filename}"
            )
            return

        # --------------------------------------------------
        # Create processed repository copy locally
        # --------------------------------------------------

        destinationProcessed_path.mkdir(
            parents=True,
            exist_ok=True
        )

        processed_text = preprocess_text(
            promoted_txt_file
        )

        processed_file = (
            destinationProcessed_path / filename
        )

        processed_file.write_text(
            processed_text,
            encoding="utf-8"
        )

        print(
            f"Processed TXT locally: {filename}"
        )

        # --------------------------------------------------
        # Persist TXT + processed TXT to Supabase
        # --------------------------------------------------

        upload_file(
            promoted_txt_file,
            f"promoted/{filename}",
            overwrite=True
        )

        upload_file(
            processed_file,
            f"processed/{filename}",
            overwrite=True
        )

        print(
            f"Persisted repository TXT files to Supabase: "
            f"{filename}"
        )

        # --------------------------------------------------
        # Move/upload PDF
        # --------------------------------------------------

        pdf_name = Path(filename).stem + ".pdf"

        pdf_file = source_pathPdf / pdf_name
        promoted_pdf_file = destinationProm_path / pdf_name

        if pdf_file.exists():

            shutil.move(
                str(pdf_file),
                str(promoted_pdf_file)
            )

            print(
                f"Promoted PDF locally: {pdf_name}"
            )

            upload_file(
                promoted_pdf_file,
                f"promoted/{pdf_name}",
                overwrite=True
            )

            print(
                f"Persisted repository PDF to Supabase: "
                f"{pdf_name}"
            )

    except Exception as e:

        print(
            f"[ERROR] Failed to promote {filename}: {e}"
        )

        raise

def move_to_review(filename):

    txt_file = source_pathTxt / filename
    review_txt_file = destinationFlag_path / filename

    try:

        # --------------------------------------------------
        # Move TXT locally
        # --------------------------------------------------

        if txt_file.exists():

            shutil.move(
                str(txt_file),
                str(review_txt_file)
            )

            print(
                f"Moved TXT to review locally: {filename}"
            )

        else:
            print(
                f"[WARNING] TXT not found for review: "
                f"{filename}"
            )
            return

        # --------------------------------------------------
        # Persist review TXT to Supabase
        # --------------------------------------------------

        upload_file(
            review_txt_file,
            f"review/{filename}",
            overwrite=True
        )

        print(
            f"Persisted review TXT to Supabase: "
            f"{filename}"
        )

        # --------------------------------------------------
        # Move/upload PDF
        # --------------------------------------------------

        pdf_name = Path(filename).stem + ".pdf"

        pdf_file = source_pathPdf / pdf_name
        review_pdf_file = destinationFlag_path / pdf_name

        if pdf_file.exists():

            shutil.move(
                str(pdf_file),
                str(review_pdf_file)
            )

            print(
                f"Moved PDF to review locally: {pdf_name}"
            )

            upload_file(
                review_pdf_file,
                f"review/{pdf_name}",
                overwrite=True
            )

            print(
                f"Persisted review PDF to Supabase: "
                f"{pdf_name}"
            )

    except Exception as e:

        print(
            f"[ERROR] Failed to move {filename} to review: {e}"
        )

        raise



