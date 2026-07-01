from pathlib import Path
from sklearn.feature_extraction.text import TfidfVectorizer
from app.nlp.preprocessing import preprocess_text

# Path to txt files
SCRIPT_DIR = Path(__file__).resolve().parent
directory_path = SCRIPT_DIR.parent / "utils" / "txtFileUpload"
corpus_path = SCRIPT_DIR.parent.parent / "corpus" / "promoted"

corpus = []
filenames = []

# Read ALL txt files
for txt_file in directory_path.glob("*.txt"):

    processed_text = preprocess_text(txt_file)

    corpus.append(processed_text)
    filenames.append(txt_file.name)

    print(f"Loaded: {txt_file.name}")

for txt_file in corpus_path.glob("*.txt"):

    processed_text = preprocess_text(txt_file)

    corpus.append(processed_text)
    filenames.append(txt_file.name)

    print(f"Loaded: {txt_file.name}")

# TF-IDF
vectorizer = TfidfVectorizer()

tfidf_matrix = vectorizer.fit_transform(corpus)

# # Vocabulary
# print("\nVocabulary:")
# print(vectorizer.vocabulary_)

# Feature names
feature_names = vectorizer.get_feature_names_out()

# print("\nWords and IDF Scores:")

# for i, doc in enumerate(corpus):
#     print(f"\n{filenames[i]}")
#     row = tfidf_matrix[i].toarray()[0]

#     for col in row.nonzero()[0]:

#         print(feature_names[col], row[col])


