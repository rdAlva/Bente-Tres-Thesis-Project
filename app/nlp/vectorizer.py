# from pathlib import Path
# from sklearn.feature_extraction.text import TfidfVectorizer
# from app.nlp.preprocessing import preprocess_text
# from app.nlp.loader import load_corpus

# # Path to txt files
# SCRIPT_DIR = Path(__file__).resolve().parent
# directory_path = SCRIPT_DIR.parent / "utils" / "txtFileUpload"
# corpus_path = SCRIPT_DIR.parent.parent / "corpus" / "promoted"

# corpus = []
# filenames = []

# # Read ALL txt files
# corpus, filenames = load_corpus()

# # TF-IDF
# vectorizer = TfidfVectorizer()

# tfidf_matrix = vectorizer.fit_transform(corpus)

# # # Vocabulary
# # print("\nVocabulary:")
# # print(vectorizer.vocabulary_)

# # Feature names
# feature_names = vectorizer.get_feature_names_out()

# # print("\nWords and IDF Scores:")
# # for i, doc in enumerate(corpus):
# #     print(f"\n{filenames[i]}")
# #     row = tfidf_matrix[i].toarray()[0]
# #     for col in row.nonzero()[0]:
# #         print(feature_names[col], row[col])

from sklearn.feature_extraction.text import TfidfVectorizer
from app.nlp.loader import load_corpus

corpus, filenames = load_corpus()

if not corpus:
    raise ValueError(
        "No valid documents were found. "
        "Ensure PDFs exist in app/static/file or TXT files exist in txtFileUpload."
    )

vectorizer = TfidfVectorizer()

tfidf_matrix = vectorizer.fit_transform(corpus)

feature_names = vectorizer.get_feature_names_out()


