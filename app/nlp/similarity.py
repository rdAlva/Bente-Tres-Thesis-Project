from sklearn.metrics.pairwise import cosine_similarity
from vectorizer import tfidf_matrix
from vectorizer import filenames
from ngrams import generate_ngrams, corpus , filenames

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

# Jaccard-Similarity
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
