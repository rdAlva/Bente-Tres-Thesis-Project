from pathlib import Path
from app.repository.promotion import (
    run_promotion,
    move_to_promoted,
    move_to_review,
)
from app.utils.pdf_extractor import extract_pdfs
from app.nlp.loader import load_corpus

print("detector.py importing...")
def run_detection():
    LOGS = Path(__file__).resolve().parent.parent.parent / "logs"
    RESULTS_FILE = LOGS / "DocumentSimilarity_results.csv"
    SENTENCES_FILE = LOGS / "SimilarSentencesReport.csv"

    if RESULTS_FILE.exists():
        RESULTS_FILE.unlink()

    if SENTENCES_FILE.exists():
        SENTENCES_FILE.unlink()

    print("Extracting PDFs...")
    extract_pdfs()

    print("Loading corpus...")
    (
        uploaded_filenames,
        uploaded_corpus,
        uploaded_original,

        promoted_filenames,
        promoted_corpus,
        promoted_original,
    ) = load_corpus()

    if not uploaded_filenames:
        print("No uploaded documents found.")
        return {
            "uploaded_files": [],
            "total_uploaded": 0,
            "total_repository": len(promoted_filenames),
            "results": [],
        }

    print("Running promotion...")
    all_results = []

    for filename, processed_text, original_text in zip(uploaded_filenames,uploaded_corpus,uploaded_original,):
        print(f"\nChecking {filename}")
        result = run_promotion(
            filename,
            processed_text,
            original_text,
            promoted_filenames,
            promoted_corpus,
            promoted_original,
        )

        is_flagged = len(result["flagged"]) > 0

        if is_flagged:

            print(f"{filename} -> REVIEW")
            move_to_review(filename)

        else:

            print(f"{filename} -> PROMOTED")

            move_to_promoted(filename)

            promoted_filenames.append(filename)
            promoted_corpus.append(processed_text)
            promoted_original.append(original_text)

        all_results.append(result)

    print("Finished!")

    return {
        "uploaded_files": uploaded_filenames,
        "total_uploaded": len(uploaded_filenames),
        "total_repository": len(promoted_filenames),
        "results": all_results,
    }

print("detector.py finished importing.")