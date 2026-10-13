from sklearn.feature_extraction.text import TfidfVectorizer

def build_vectorizer(corpus):
    if not corpus:
        raise ValueError(
            "No valid documents were found. "
            "Ensure PDFs exist in app/static/file or TXT files exist in txtFileUpload."
        )

    vectorizer = TfidfVectorizer()

    tfidf_matrix = vectorizer.fit_transform(corpus)

    feature_names = vectorizer.get_feature_names_out()

    return vectorizer, tfidf_matrix, feature_names

