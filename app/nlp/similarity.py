import re
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

try:
    nltk.data.find("tokenizers/punkt_tab")
except LookupError:
    nltk.download("punkt_tab", quiet=True)


def _sent_tokenize_offsets(text):
    """
    Tokenize *text* using the same ``sent_tokenize()`` that
    ``get_similar_sentences()`` uses, and return
    ``(sentences, spans)`` where ``spans[k] = (start, end)``
    are the character offsets of sentence *k* in *text*.

    Each returned sentence is the **exact** substring
    ``text[start:end]`` — no stripping — so the offsets are
    faithful to the original document.

    Sentences that are purely whitespace after tokenization
    are skipped, and their spans are not included.
    """
    raw_sents = sent_tokenize(text)
    spans = []
    sentences = []
    search_from = 0

    for raw in raw_sents:
        stripped = raw.strip()
        if not stripped:
            search_from += len(raw)
            continue

        # Locate the sentence in the document starting from
        # where the previous sentence ended.  We first try an
        # exact (case-sensitive) substring search, then fall
        # back to a case-insensitive normalised search.
        pos = text.find(raw, search_from)
        if pos != -1:
            end = pos + len(raw)
        else:
            # Fallback: search with collapsed whitespace
            norm_target = re.sub(r'\s+', ' ', stripped).lower()
            for candidate_start in range(search_from, len(text)):
                norm_cand = re.sub(
                    r'\s+',
                    ' ',
                    text[candidate_start:candidate_start + len(norm_target) + 50]
                ).lower()
                if norm_target in norm_cand:
                    # Refine: find exact start
                    pos = candidate_start
                    end = candidate_start + len(raw)
                    break
            else:
                # Still not found — skip this sentence
                search_from += len(raw)
                continue

        spans.append((pos, end))
        sentences.append(stripped)
        search_from = end

    return sentences, spans

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


def _extract_sentence_spans(text):
    """
    Tokenize *text* into sentences and return
    ``(sentences, spans)`` where ``spans[k] = (start, end)``
    are the character offsets of sentence *k* in *text*.

    Uses the same ``sent_tokenize()`` that
    ``get_similar_sentences()`` relies on, so the sentence
    indices are consistent.
    """
    return _sent_tokenize_offsets(text)




def _find_sentence_in_text(sentence_text, orig_text, used_spans):
    """
    Locate *sentence_text* inside *orig_text* while avoiding
    positions already occupied by *used_spans*.

    Both the search target and the document are normalised
    (whitespace collapsed, lowered) before searching so that
    multi-line sentences in the CSV can be found even when
    the original text contains ``\\n`` characters within a
    sentence.

    Returns ``(start, end)`` character offsets in the
    **original** (un-normalised) *orig_text*, or ``None``
    if the sentence cannot be found.
    """
    norm_target = re.sub(r'\s+', ' ', sentence_text.strip()).lower()
    norm_doc = re.sub(r'\s+', ' ', orig_text).lower()

    search_from = 0
    while True:
        pos = norm_doc.find(norm_target, search_from)
        if pos == -1:
            return None

        end = pos + len(norm_target)
        overlaps = False
        for used_start, used_end in used_spans:
            if pos < used_end and end > used_start:
                overlaps = True
                break
        if not overlaps:
            return (pos, end)
        search_from = end
    return None




def highlight_document(
    document,
    match_records=None,
    matched_sentences=None,
):
    """
    Produce an HTML representation of *document* with matched
    sentences wrapped in ``<mark>`` elements.

    Parameters
    ----------
    document : str
        The original, unmodified document text.
    match_records : list[dict], optional
        Each dict may contain:

        * ``match_id`` (str | int) – stable pair identifier.
        * ``sentence`` (str) – the sentence text to highlight.
        * ``sentence_index`` (int, optional) – the sentence's
          index in the ``sent_tokenize()`` output for this
          document.  When provided, the sentence's character
          span is looked up directly by index, which is both
          faster and more reliable than text search.

        When *match_records* is provided, character-span
        highlighting is used.
    matched_sentences : list[str], optional
        Legacy plain-text list.  Used only as a fallback when
        *match_records* is not supplied.

    Returns
    -------
    str
        HTML with ``<mark class="match-prose" data-match-id="…">``
        elements around matched sentences.
    """

    if match_records is None and matched_sentences is not None:
        match_records = [
            {"match_id": str(idx), "sentence": s}
            for idx, s in enumerate(matched_sentences)
        ]

    if not match_records:
        return html.escape(document)

    # ---- Build sentence → character-offset map via sent_tokenize ----
    _, sent_spans = _sent_tokenize_offsets(document)

    used_spans = []
    highlights = []

    for rec in match_records:
        sentence_text = rec["sentence"]
        match_id = str(rec["match_id"])
        sentence_index = rec.get("sentence_index")

        span = None

        # 1) Index-based lookup (preferred)
        if sentence_index is not None and isinstance(sentence_index, int):
            if 0 <= sentence_index < len(sent_spans):
                candidate = sent_spans[sentence_index]
                # Verify the span text matches the record's sentence
                span_text = document[candidate[0]:candidate[1]]
                norm_span = re.sub(r'\s+', ' ', span_text.strip()).lower()
                norm_sent = re.sub(r'\s+', ' ', sentence_text.strip()).lower()
                if norm_span == norm_sent:
                    span = candidate

        # 2) Fallback: text search
        if span is None:
            span = _find_sentence_in_text(
                sentence_text, document, used_spans
            )

        if span is not None:
            # Avoid overlapping highlights
            overlaps = any(
                span[0] < u[1] and span[1] > u[0]
                for u in used_spans
            )
            if not overlaps:
                used_spans.append(span)
                highlights.append((span[0], span[1], match_id))

    if not highlights:
        return html.escape(document)

    highlights.sort(key=lambda x: x[0])

    html_parts = []
    last = 0

    for h_start, h_end, m_id in highlights:
        if h_start > last:
            html_parts.append(html.escape(document[last:h_start]))
        html_parts.append(
            '<mark class="match-prose" data-match-id="'
            + html.escape(str(m_id), quote=True)
            + '">'
            + html.escape(document[h_start:h_end])
            + '</mark>'
        )
        last = h_end

    if last < len(document):
        html_parts.append(html.escape(document[last:]))

    raw_html = ''.join(html_parts)

    para_html_parts = []
    search_from = 0

    while search_from < len(raw_html):
        plain_pos = raw_html.find('\n\n', search_from)
        if plain_pos == -1:
            chunk = raw_html[search_from:]
            if chunk.strip():
                para_html_parts.append(
                    '<p class="doc-paragraph">' + chunk + '</p>'
                )
            else:
                para_html_parts.append(chunk)
            break

        chunk = raw_html[search_from:plain_pos]
        if chunk.strip():
            para_html_parts.append(
                '<p class="doc-paragraph">' + chunk + '</p>'
            )
        else:
            para_html_parts.append(chunk)

        blank_end = plain_pos + 2
        while blank_end < len(raw_html) and raw_html[blank_end] == '\n':
            blank_end += 1
        para_html_parts.append(raw_html[plain_pos:blank_end])
        search_from = blank_end

    return ''.join(para_html_parts)

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

    raw_matches = []

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

        raw_matches.append({
            "sentence1_index": i,
            "sentence2_index": j,
            "sentence1": sentence1,
            "sentence2": sentence2,
            "sentence1_html": highlight1,
            "sentence2_html": highlight2,
            "score": round(score, 4),
        })

    raw_matches.sort(
        key=lambda x: x["score"],
        reverse=True
    )

    matches = []
    for match_idx, m in enumerate(raw_matches):
        m["match_id"] = f"match-{match_idx:04d}"
        matches.append(m)

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
                        "match_id": match["match_id"],
                        "sentence1_index": match["sentence1_index"],
                        "sentence2_index": match["sentence2_index"],
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

        uploaded_document_html = highlight_document(
            uploaded_original,
            match_records=[
                {
                    "match_id": m["match_id"],
                    "sentence": m["sentence1"],
                    "sentence_index": m["sentence1_index"],
                }
                for m in similar_sentences
            ],
        )

        repository_document_html = highlight_document(
            promoted_original[repo_index],
            match_records=[
                {
                    "match_id": m["match_id"],
                    "sentence": m["sentence2"],
                    "sentence_index": m["sentence2_index"],
                }
                for m in similar_sentences
            ],
        )

        for match in similar_sentences:

            similarity_report.append({

                "document_1": uploaded_filename,

                "document_2": top_match["doc2"],

                "match_id": match["match_id"],
                "sentence1_index": match["sentence1_index"],
                "sentence2_index": match["sentence2_index"],
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