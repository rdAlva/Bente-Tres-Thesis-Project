import re
from collections import defaultdict, deque
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from app.nlp.ngrams import generate_ngrams
import html
import nltk
from nltk.tokenize import sent_tokenize

try:
    nltk.data.find("tokenizers/punkt")
except LookupError:
    nltk.download("punkt", quiet=True)

def compute_similarity(tfidf_matrix):
    return cosine_similarity(tfidf_matrix)

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
        return "Error"

def jaccard_similarity(txt1, txt2, n):
    ngrams1 = set(generate_ngrams(txt1, n))
    ngrams2 = set(generate_ngrams(txt2, n))

    intersection = len(ngrams1 & ngrams2)
    union = len(ngrams1 | ngrams2)

    if union == 0:
        return 0.0

    return intersection / union

def jaccard_similarity1(txt1, txt2):
    return jaccard_similarity(txt1, txt2, 1)

def jaccard_similarity2(txt1, txt2):
    return jaccard_similarity(txt1, txt2, 2)

def jaccard_similarity3(txt1, txt2):
    return jaccard_similarity(txt1, txt2, 3)

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
        return "Error"

def highlight_common_words(sentence1, sentence2):
    """
    Highlights words appearing in both sentences.
    Returns HTML strings.
    """

    words1 = sentence1.split()
    words2 = sentence2.split()

    common = {
        word.lower().strip(",.;:!?()[]{}\"'")
        for word in words1
    } & {
        word.lower().strip(",.;:!?()[]{}\"'")
        for word in words2
    }

    highlighted1 = []

    for word in words1:

        clean = word.lower().strip(",.;:!?()[]{}\"'")

        if clean in common:
            highlighted1.append(f"<mark>{word}</mark>")
        else:
            highlighted1.append(word)

    highlighted2 = []

    for word in words2:

        clean = word.lower().strip(",.;:!?()[]{}\"'")

        if clean in common:
            highlighted2.append(f"<mark>{word}</mark>")
        else:
            highlighted2.append(word)

    return (
        " ".join(highlighted1),
        " ".join(highlighted2),
    )

def _normalize_text(document):
    document = document.replace('\r\n', '\n').replace('\r', '\n')
    return document.strip()


def _is_list_line(line):
    return bool(re.match(r'^\s*([*•\u2022\-–—]|\d+[\.)]|[a-zA-Z][\.)])\s+', line))


def _is_table_block(lines):
    if len(lines) < 2:
        return False

    pipe_like = any('|' in line for line in lines)
    tab_like = any('\t' in line for line in lines)
    space_aligned = sum(1 for line in lines if re.search(r' {3,}', line)) >= 2
    return pipe_like or tab_like or space_aligned


def _collapse_paragraph_lines(lines):
    collapsed = []

    for line in lines:
        stripped = line.strip()
        if not stripped:
            continue

        if collapsed and collapsed[-1].endswith('-'):
            collapsed[-1] = collapsed[-1][:-1] + stripped.lstrip()
        else:
            collapsed.append(stripped)

    return ' '.join(collapsed)


def _normalize_match_text(text):
    return re.sub(r'\s+', ' ', text.strip()).lower()


def _normalize_text_with_index(text):
    normalized_chars = []
    index_map = []
    in_space = False

    for index, char in enumerate(text):
        if char.isspace():
            if not in_space:
                normalized_chars.append(' ')
                index_map.append(index)
                in_space = True
        else:
            normalized_chars.append(char.lower())
            index_map.append(index)
            in_space = False

    # Trim leading and trailing normalized spaces to match _normalize_match_text
    if normalized_chars and normalized_chars[0] == ' ':
        normalized_chars.pop(0)
        index_map.pop(0)

    if normalized_chars and normalized_chars[-1] == ' ':
        normalized_chars.pop()
        index_map.pop()

    return ''.join(normalized_chars), index_map


def _build_match_id_map(matched_sentences):
    match_ids = defaultdict(deque)

    for idx, sentence in enumerate(matched_sentences):
        normalized = _normalize_match_text(sentence)
        if normalized:
            match_ids[normalized].append(str(idx))

    return match_ids


def _find_next_match(block_norm, match_ids, start_pos):
    best_key = None
    best_pos = len(block_norm) + 1

    for key, queue in match_ids.items():
        if not queue:
            continue

        idx = block_norm.find(key, start_pos)
        if idx == -1:
            continue

        if idx < best_pos or (idx == best_pos and len(key) > len(best_key or '')):
            best_pos = idx
            best_key = key

    return best_key, best_pos if best_key is not None else -1


def _highlight_text_block(text, match_ids):
    block_norm, index_map = _normalize_text_with_index(text)

    if not block_norm or not any(match_ids.values()):
        return html.escape(text)

    highlights = []
    search_pos = 0

    while True:
        match_key, start = _find_next_match(block_norm, match_ids, search_pos)
        if match_key is None:
            break

        end = start + len(match_key)
        orig_start = index_map[start]
        orig_end = index_map[end - 1] + 1
        match_id = match_ids[match_key].popleft()
        highlights.append((orig_start, orig_end, match_id))
        search_pos = end

    if not highlights:
        return html.escape(text)

    html_output = []
    last = 0

    for orig_start, orig_end, match_id in sorted(highlights, key=lambda x: x[0]):
        html_output.append(html.escape(text[last:orig_start]))
        html_output.append(
            f'<mark class="match-prose" data-match-id="{match_id}">{html.escape(text[orig_start:orig_end])}</mark>'
        )
        last = orig_end

    html_output.append(html.escape(text[last:]))
    return ''.join(html_output)


def _split_document_blocks(document):
    normalized = _normalize_text(document)
    raw_blocks = re.split(r'\n\s*\n+', normalized)
    blocks = []

    for raw_block in raw_blocks:
        lines = raw_block.split('\n')
        cleaned_lines = [line.rstrip() for line in lines if line.strip()]
        if not cleaned_lines:
            continue

        if _is_table_block(cleaned_lines):
            blocks.append(('table', '\n'.join(cleaned_lines)))
        elif any(_is_list_line(line) for line in cleaned_lines):
            blocks.append(('list', '\n'.join(cleaned_lines)))
        else:
            blocks.append(('paragraph', _collapse_paragraph_lines(cleaned_lines)))

    return blocks


def highlight_document(document, matched_sentences):
    """
    Highlights only matched sentences while preserving
    the original document formatting.
    """

    match_ids = _build_match_id_map(matched_sentences)
    blocks = _split_document_blocks(document)
    html_output = []

    for block_type, block_text in blocks:
        block_html = _highlight_text_block(block_text, match_ids)

        if block_type == 'paragraph':
            html_output.append(f'<p class="doc-paragraph">{block_html}</p>')
        elif block_type == 'list':
            html_output.append('<div class="doc-list">' + block_html.replace('\n', '<br>') + '</div>')
        elif block_type == 'table':
            escaped_table = block_html.replace('\n', '<br>')
            html_output.append(f'<div class="doc-table">{escaped_table}</div>')
        else:
            html_output.append(block_html)

    return ''.join(html_output)

def get_similar_sentences(doc1, doc2, threshold):

    sentences1 = [
        s.strip()
        for s in sent_tokenize(doc1)
        if s.strip()
    ]

    sentences2 = [
        s.strip()
        for s in sent_tokenize(doc2)
        if s.strip()
    ]

    if not sentences1 or not sentences2:
        return []

    try:

        vectorizer = TfidfVectorizer()

        tfidf1 = vectorizer.fit_transform(sentences1)
        tfidf2 = vectorizer.transform(sentences2)

        cosine_matrix = cosine_similarity(tfidf1, tfidf2)

    except ValueError:
        return []

    matches = []


    # Build every possible candidate
    candidates = []
    for i, sentence1 in enumerate(sentences1):
        for j, sentence2 in enumerate(sentences2):

            score = float(cosine_matrix[i][j])

            if score >= threshold:
                candidates.append(
                    (score, i, j, sentence1, sentence2)
                )

    best_doc1 = {}
    best_doc2 = {}

    for score, i, j, sentence1, sentence2 in candidates:

        if i not in best_doc1 or score > best_doc1[i][0]:
            best_doc1[i] = (
                score,
                j,
                sentence1,
                sentence2
            )

        if j not in best_doc2 or score > best_doc2[j][0]:
            best_doc2[j] = (
                score,
                i,
                sentence1,
                sentence2
            )

    for i, (score, j, sentence1, sentence2) in best_doc1.items():

        # Is sentence i also the favorite match of sentence j?
        if j not in best_doc2:
            continue

        if best_doc2[j][1] != i:
            continue

        highlight1, highlight2 = highlight_common_words(
            sentence1,
            sentence2
        )

        matches.append({

            "sentence1": sentence1,
            "sentence2": sentence2,

            "sentence1_html": highlight1,
            "sentence2_html": highlight2,

            "score": round(score, 4)

        })
    matches.sort(
        key=lambda x: x["score"],
        reverse=True
    )

    return matches

def rank_document_pairs(filenames, similarity_matrix,corpus, threshold):
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
            j1 = jaccard_similarity1(corpus[i], corpus[j])
            j2 = jaccard_similarity2(corpus[i], corpus[j])
            j3 = jaccard_similarity3(corpus[i], corpus[j])

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
                        "sentence_from_doc2": match["sentence2"],
                        "sentence_from_doc1_html": match["sentence1_html"],
                        "sentence_from_doc2_html": match["sentence2_html"],
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

def compare_uploaded_document(
    uploaded_filename,

    uploaded_processed,
    uploaded_original,

    promoted_filenames,

    promoted_processed,
    promoted_original,

    threshold,
):

    ranked_pairs = []
    similarity_report = []

    processed_documents = [uploaded_processed] + promoted_processed

    vectorizer = TfidfVectorizer()

    tfidf_matrix = vectorizer.fit_transform(processed_documents)

    similarity_matrix = compute_similarity(tfidf_matrix)
    uploaded_unigrams = set(generate_ngrams(uploaded_processed, 1))
    uploaded_bigrams = set(generate_ngrams(uploaded_processed, 2))
    uploaded_trigrams = set(generate_ngrams(uploaded_processed, 3))


    for i in range(len(promoted_processed)):

        cosine_score = similarity_matrix[0][i + 1]

        repo_unigrams = set(generate_ngrams(promoted_processed[i], 1))
        repo_bigrams = set(generate_ngrams(promoted_processed[i], 2))
        repo_trigrams = set(generate_ngrams(promoted_processed[i], 3))

        j1 = len(uploaded_unigrams & repo_unigrams) / len(uploaded_unigrams | repo_unigrams) if (uploaded_unigrams | repo_unigrams) else 0
        j2 = len(uploaded_bigrams & repo_bigrams) / len(uploaded_bigrams | repo_bigrams) if (uploaded_bigrams | repo_bigrams) else 0
        j3 = len(uploaded_trigrams & repo_trigrams) / len(uploaded_trigrams | repo_trigrams) if (uploaded_trigrams | repo_trigrams) else 0

        combined_score = (cosine_score + j1 + j2 + j3) / 4
        print(
            f"{uploaded_filename} vs {promoted_filenames[i]}"
        )
        print(
            f"Cosine={cosine_score:.4f} "
            f"J1={j1:.4f} "
            f"J2={j2:.4f} "
            f"J3={j3:.4f} "
            f"Combined={combined_score:.4f}"
        )
        print("-" * 60)

        if combined_score >= threshold:
            decision = "WITHHOLD"
            flagged = True
        else:
            decision = "PROMOTE"
            flagged = False



        ranked_pairs.append({

            "rank": 0,
            "repo_index": i,
            "doc1": uploaded_filename,
            "doc2": promoted_filenames[i],

            "cosine_score": round(cosine_score, 4),
            "jaccard_unigram": round(j1, 4),
            "jaccard_bigram": round(j2, 4),
            "jaccard_trigram": round(j3, 4),

            "combined_score": round(combined_score, 4),

            "cosine_label": cosine_similarity_score(cosine_score),
            "jaccard_label": jaccard_similarity_score(combined_score),

            "decision": decision,
            "flagged": flagged,
        })

    ranked_pairs.sort(
        key=lambda x: x["combined_score"],
        reverse=True
    )

    # Assign ranks
    for index, pair in enumerate(ranked_pairs):
        pair["rank"] = index + 1

    flagged_pairs = [
        p for p in ranked_pairs
        if p["flagged"]
    ]

    promoted_pairs = [
        p for p in ranked_pairs
        if not p["flagged"]
    ]

    # ----------------------------------------------------
    # Only compare sentences with the BEST matching paper
    # ----------------------------------------------------

    uploaded_document_html = ""
    repository_document_html = ""

    if flagged_pairs:

        top_match = flagged_pairs[0]

        repo_index = top_match["repo_index"]

        similar_sentences = get_similar_sentences(
            uploaded_original,
            promoted_original[repo_index],
            threshold
        )
        matched_doc1 = [
            m["sentence1"]
            for m in similar_sentences
        ]

        matched_doc2 = [
            m["sentence2"]
            for m in similar_sentences
        ]

        uploaded_document_html = highlight_document(
            uploaded_original,
            matched_doc1
        )

        repository_document_html = highlight_document(
            promoted_original[repo_index],
            matched_doc2
        )

        for match in similar_sentences:

            similarity_report.append({

                "document_1": uploaded_filename,

                "document_2": top_match["doc2"],

                "sentence_similarity": match["score"],

                "sentence_from_doc1": match["sentence1"],

                "sentence_from_doc2": match["sentence2"],
                "sentence_from_doc1_html": match["sentence1_html"],
                "sentence_from_doc2_html": match["sentence2_html"]
            })

    return (
        ranked_pairs,
        flagged_pairs,
        promoted_pairs,
        similarity_report,
        uploaded_document_html,
        repository_document_html,
    )