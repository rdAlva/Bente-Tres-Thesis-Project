import pandas as pd

from app.nlp.similarity import rank_document_pairs
from app.nlp.vectorizer import tfidf_matrix, filenames
from app.nlp.ngrams import corpus
from sklearn.metrics.pairwise import cosine_similarity
from pathlib import Path
import shutil


# Path to files
SCRIPT_DIR = Path(__file__).resolve().parent

#Move Original Files Path
source_pathTxt = SCRIPT_DIR.parent / "utils" / "txtFileUpload"
source_pathPdf = SCRIPT_DIR.parent / "static" / "file"
#Move New Files Path

destinationFlag_path = SCRIPT_DIR.parent.parent / "corpus" / "review"
destinationProm_path = SCRIPT_DIR.parent.parent / "corpus" / "promoted"
source_logs = SCRIPT_DIR.parent.parent / "logs"

# set instructor threshold
threshold = 0.11

# get similarity matrix
similarity_matrix = cosine_similarity(tfidf_matrix)


# get ranked results
all_pairs, flagged, to_promote,similarity_report ,= rank_document_pairs(
    filenames,
    similarity_matrix,
    corpus,
    threshold,
)

# Save CSV to logs folder
df_results = pd.DataFrame(all_pairs)
df_results.to_csv(
    source_logs / "DocumentSimilarity_results.csv",
    index=False)

df_sentences = pd.DataFrame(similarity_report)
df_sentences.to_csv(
    source_logs / "SimilarSentencesReport.csv",
    index=False
    )

# Prevent moving the same file twice
moved_files = set()

print(f"FLAGGED PAIRS ({len(flagged)} found):")

for pair in flagged:
    print(
        f"  Rank {pair['rank']}: "
        f"{pair['doc1']} vs {pair['doc2']} "
        f"→ {pair['combined_score']} ({pair['decision']})"
    )

    for filename in [pair['doc1'], pair['doc2']]:

        if filename in moved_files:
            continue

        txt_file = source_pathTxt / filename

        if txt_file.is_file():
            shutil.move(
                str(txt_file),
                str(destinationFlag_path / filename)
            )
            print(f"Moved TXT: {filename}")

        pdf_name = Path(filename).stem + ".pdf"
        pdf_file = source_pathPdf / pdf_name

        if pdf_file.is_file():
            shutil.move(
                str(pdf_file),
                str(destinationFlag_path / pdf_name)
            )
            print(f"Moved PDF: {pdf_name}")

        moved_files.add(filename)


# print pairs to promote
print(f"\nTO PROMOTE ({len(to_promote)} documents):")

for pair in to_promote:
    print(
        f"  Rank {pair['rank']}: "
        f"{pair['doc1']} vs {pair['doc2']} "
        f"→ {pair['combined_score']} ({pair['decision']})"
    )

    for filename in [pair['doc1'], pair['doc2']]:

        if filename in moved_files:
            continue

        txt_file = source_pathTxt / filename

        if txt_file.is_file():
            shutil.move(
                str(txt_file),
                str(destinationProm_path / filename)
            )
            print(f"Promoted TXT: {filename}")

        pdf_name = Path(filename).stem + ".pdf"
        pdf_file = source_pathPdf / pdf_name

        if pdf_file.is_file():
            shutil.move(
                str(pdf_file),
                str(destinationProm_path / pdf_name)
            )
            print(f"Promoted PDF: {pdf_name}")

        moved_files.add(filename)

