import time
from datetime import datetime
from pathlib import Path
from app.repository.promotion import (
    run_promotion,
    move_to_promoted,
    move_to_review,
)
from app.utils.pdf_extractor import extract_pdfs
from app.nlp.loader import load_corpus

print("detector.py importing...")
def run_detection(threshold):
    overall_start = time.perf_counter()
    run_timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print("=" * 60)
    print(f"Using similarity threshold: {threshold:.2f}")
    print("=" * 60)
    LOGS = Path(__file__).resolve().parent.parent.parent / "logs"
    PROCESSING_LOG = LOGS / "processing_log.txt"
    RESULTS_FILE = LOGS / "DocumentSimilarity_results.csv"
    SENTENCES_FILE = LOGS / "SimilarSentencesReport.csv"

    if RESULTS_FILE.exists():
        RESULTS_FILE.unlink()

    if SENTENCES_FILE.exists():
        SENTENCES_FILE.unlink()

    print("Extracting PDFs...")
    pdf_start = time.perf_counter()
    extract_pdfs()
    pdf_time = time.perf_counter() - pdf_start

    print("Loading corpus...")
    corpus_start = time.perf_counter()
    (
        uploaded_filenames,
        uploaded_corpus,
        uploaded_original,

        promoted_filenames,
        promoted_corpus,
        promoted_original,
    ) = load_corpus()
    corpus_time = time.perf_counter() - corpus_start

    if not uploaded_filenames:
        print("No uploaded documents found.")
        return {
            "uploaded_files": [],
            "total_uploaded": 0,
            "total_repository": len(promoted_filenames),
            "results": [],
        }


    print("Running promotion...")
    promotion_start = time.perf_counter()
    all_results = []

    for filename, processed_text, original_text in zip(uploaded_filenames,uploaded_corpus,uploaded_original,):
        print(f"\nChecking {filename} (Threshold = {threshold:.2f})")
        result = run_promotion(
            filename,
            processed_text,
            original_text,
            promoted_filenames,
            promoted_corpus,
            promoted_original,
            threshold,
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

    promotion_time = time.perf_counter() - promotion_start
    print("Finished!")
    overall_time = time.perf_counter() - overall_start

    with open(PROCESSING_LOG, "a", encoding="utf-8") as log:
        log.write("=" * 70 + "\n")
        log.write(f"Detection Run : {run_timestamp}\n")
        log.write(f"Threshold     : {threshold:.2f}\n")
        log.write(f"Uploaded Docs : {len(uploaded_filenames)}\n")
        log.write(f"Repository Docs : {len(promoted_filenames)}\n")
        log.write("\n")

        log.write(f"PDF Extraction : {pdf_time:.3f} sec\n")
        log.write(f"Corpus Loading : {corpus_time:.3f} sec\n")
        log.write(f"Promotion      : {promotion_time:.3f} sec\n")
        log.write(f"TOTAL TIME     : {overall_time:.3f} sec\n")

        log.write("=" * 70 + "\n\n")

    return {
        "uploaded_files": uploaded_filenames,
        "total_uploaded": len(uploaded_filenames),
        "total_repository": len(promoted_filenames),
        "results": all_results,
    }

print("detector.py finished importing.")