import os
from pathlib import Path
import re

import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from app.nlp.vectorizer import tfidf_matrix
from app.nlp.vectorizer import filenames
from app.nlp.ngrams import generate_ngrams, corpus , filenames

#Cosine-Similarity
similarity = cosine_similarity(tfidf_matrix)

def cosine_similarity_score(similarity_score):
    if similarity_score == 1.0:
        return "Identical"
    elif similarity_score >= 0.8:
        return "very similar"
    elif similarity_score >= 0.5:
        return "moderately similar"
    elif similarity_score >= 0.2:
        return "weak similarity"
    elif similarity_score >= 0.0:
        return "no similarity"
    else:
        print("Error")

def jaccard_similarity1(txt1, txt2, n=1):
    ngrams1 = set(generate_ngrams(txt1, n))
    ngrams2 = set(generate_ngrams(txt2, n))

    intersection = len(ngrams1.intersection(ngrams2))
    union = len(ngrams1.union(ngrams2))

    if union == 0:
        return 0

    return intersection / union
def jaccard_similarity2(txt1, txt2, n=2):
    ngrams1 = set(generate_ngrams(txt1, n))
    ngrams2 = set(generate_ngrams(txt2, n))

    intersection = len(ngrams1.intersection(ngrams2))
    union = len(ngrams1.union(ngrams2))

    if union == 0:
        return 0

    return intersection / union

def jaccard_similarity3(txt1, txt2, n=3):
    ngrams1 = set(generate_ngrams(txt1, n))
    ngrams2 = set(generate_ngrams(txt2, n))

    intersection = len(ngrams1.intersection(ngrams2))
    union = len(ngrams1.union(ngrams2))

    if union == 0:
        return 0

    return intersection / union

def jaccard_similarity_score(J_score):
    if 0.0 <= J_score <=0.2:
        return "no similarity"
    elif 0.2 < J_score <= 0.5:
        return "weak similarity"
    elif 0.5 < J_score <= 0.8:
        return "very similar"
    elif 0.8 < J_score <= 1.0:
        return "Identical"
    else:
        print("Error")

def get_similar_sentences(doc1, doc2, threshold):

    sentences1 = [s.strip() for s in re.split(r'[.!?]+', doc1) if s.strip()]
    sentences2 = [s.strip() for s in re.split(r'[.!?]+', doc2) if s.strip()]

    matches = []

    for s1 in sentences1:
        for s2 in sentences2:

            try:
                vectorizer = TfidfVectorizer()

                tfidf = vectorizer.fit_transform([s1, s2])

                score = cosine_similarity(tfidf)[0][1]

                if score >= threshold:
                    matches.append({
                        "sentence1": s1,
                        "sentence2": s2,
                        "score": round(score, 4)
                    })

            except ValueError:
                continue

    return sorted(matches, key=lambda x: x["score"], reverse=True)


SCRIPT_DIR = Path(__file__).resolve().parent
source_logs = SCRIPT_DIR.parent.parent / "logs"

def rank_document_pairs(filenames, similarity_matrix,corpus, threshold ,n_gram=2):
    """
    Ranks all document pairs by combined similarity score.
    Returns flagged and non-flagged pairs separately.
    """
    ranked_pairs = []
    similarity_report = []

    for i in range(len(filenames)):
        for j in range(i + 1, len(filenames)):

            # get scores
            cosine_score = similarity_matrix[i][j]
            j1 = jaccard_similarity1(corpus[i], corpus[j], n=1)
            j2 = jaccard_similarity2(corpus[i], corpus[j], n=2)
            j3 = jaccard_similarity3(corpus[i], corpus[j], n=3)

            # combined average score
            combined_score = (cosine_score + j1 + j2 + j3) / 4
            # promotion decision
            if combined_score >= threshold :
                decision = "WITHHOLD"
                flagged  = True
            else:
                decision = "PROMOTE"
                flagged  = False

            if flagged:
                similar_sentences = get_similar_sentences(
                    corpus[i],
                    corpus[j],
                    threshold
                )

                for match in similar_sentences:
                    similarity_report.append({
                        "document_1": filenames[i],
                        "document_2": filenames[j],
                        "sentence_similarity": match["score"],
                        "sentence_from_doc1": match["sentence1"],
                        "sentence_from_doc2": match["sentence2"]
                    })

            ranked_pairs.append({
                "rank":           0,          # filled after sorting
                "doc1":           filenames[i],
                "doc2":           filenames[j],
                "cosine_score":   round(cosine_score, 4),
                "jaccard_unigram": round(j1, 4),
                "jaccard_bigram":  round(j2, 4),
                "jaccard_trigram": round(j3, 4),
                "combined_score": round(combined_score, 4),
                "cosine_label":   cosine_similarity_score(cosine_score),
                "jaccard_label":  jaccard_similarity_score(combined_score),
                "decision":       decision,
                "flagged":        flagged,
            })

    # sort by combined score highest to lowest
    ranked_pairs.sort(key=lambda x: x["combined_score"], reverse=True)

    # assign rank numbers
    for index, pair in enumerate(ranked_pairs):
        pair["rank"] = index + 1

    # separate flagged and non-flagged
    flagged_pairs    = [p for p in ranked_pairs if p["flagged"]]
    non_flagged_pairs = [p for p in ranked_pairs if not p["flagged"]]



    return ranked_pairs, flagged_pairs, non_flagged_pairs, similarity_report

print(" ")
print("Cosine-Similarity")
for i in range(len(filenames)):
    for j in range(i + 1, len(filenames)):
        similarity_score = similarity[i][j]
        result = cosine_similarity_score(similarity_score)
        print(f"{i+1} {filenames[i]} = {j+1} {filenames[j]} => {similarity_score:.4f}")
        print(f"RESULT: {result}")

print(" ")
print("Jaccard-Similarity UNIGRAMS")
for i in range(len(filenames)):
    for j in range(i + 1, len(filenames)):
        J_score = jaccard_similarity1(corpus[i], corpus[j], n=1)
        result = jaccard_similarity_score(J_score)
        print(f"{i+1} {filenames[i]} = {j+1} {filenames[j]} => {J_score:.4f}")
        print(f"RESULT: {result}")
print(" ")
print("Jaccard-Similarity BIGRAMS")
for i in range(len(filenames)):
    for j in range(i + 1, len(filenames)):
        J_score = jaccard_similarity2(corpus[i], corpus[j], n=2)
        result = jaccard_similarity_score(J_score)
        print(f"{i+1} {filenames[i]} = {j+1} {filenames[j]} => {J_score:.4f}")
        print(f"RESULT: {result}")
print(" ")
print("Jaccard-Similarity TRIGRAMS")
for i in range(len(filenames)):
    for j in range(i + 1, len(filenames)):
        J_score = jaccard_similarity3(corpus[i], corpus[j], n=3)
        result = jaccard_similarity_score(J_score)
        print(f"{i+1} {filenames[i]} = {j+1} {filenames[j]} => {J_score:.4f}")
        print(f"RESULT: {result}")
