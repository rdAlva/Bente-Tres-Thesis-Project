import os
import sys
import time
from pathlib import Path
sys.path.append(os.path.join(os.path.dirname(__file__), ".."))
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics import (
    precision_score,
    recall_score,
    accuracy_score,
    f1_score,
    confusion_matrix,
)
from app.utils.pdf_extractor import extract_pdfs
from app.nlp.loader import load_corpus
from app.nlp.similarity import (
    compute_similarity,
    jaccard_similarity1,
    jaccard_similarity2,
    jaccard_similarity3,
)

# ==========================================================
# CONFIGURATION
# ==========================================================

BASE_DIR = Path(__file__).resolve().parent.parent

GROUND_TRUTH_FILE = (
    BASE_DIR /
    "evaluation" /
    "ground_truth.csv"
)

LOG_DIR = (
    BASE_DIR /
    "logs"
)

LOG_DIR.mkdir(exist_ok=True)

# THRESHOLDS = [
#     0.10,
#     0.11,
#     0.12,
#     0.13,
#     0.14,
#     0.15,
#     0.20,
#     0.30,
#     0.40,
#     0.50,
#     0.60,
#     0.70,
#     0.80,
#     0.90,
# ]

THRESHOLDS = [
    round(i * 0.01, 2)
    for i in range(20, 41)
]

# ==========================================================
# LOAD GROUND TRUTH
# ==========================================================

def load_ground_truth():
    """
    Loads the manually labeled ground truth document pairs.

    Returns
    -------
    dict
        {
            (doc1, doc2): 0 or 1,
            ...
        }
    """

    if not GROUND_TRUTH_FILE.exists():

        raise FileNotFoundError(

            f"Ground truth file not found:\n{GROUND_TRUTH_FILE}"

        )

    ground_truth_df = pd.read_csv(GROUND_TRUTH_FILE)

    required_columns = {

        "doc1",
        "doc2",
        "actual"

    }

    if not required_columns.issubset(ground_truth_df.columns):

        raise ValueError(

            "ground_truth.csv must contain columns:\n"
            "doc1, doc2, actual"

        )

    ground_truth = {}

    for _, row in ground_truth_df.iterrows():

        pair = (

            row["doc1"],
            row["doc2"]

        )

        ground_truth[pair] = int(row["actual"])

    print(

        f"Loaded {len(ground_truth)} labeled document pairs."

    )

    return ground_truth

# ==========================================================
# LOAD EVALUATION CORPUS
# ==========================================================

def load_evaluation_corpus():
    """
    Loads the evaluation corpus using the same
    pipeline as the plagiarism detector.

    Returns
    -------
    filenames : list[str]
    corpus : list[str]
    """

    print("\nExtracting PDFs...")

    extract_pdfs()

    print("Loading corpus...")

    (
        uploaded_filenames,
        uploaded_corpus,
        _,
        _,
        _,
        _,
    ) = load_corpus()

    if not uploaded_filenames:

        raise ValueError(

            "No evaluation documents were found."

        )

    print(

        f"Loaded {len(uploaded_filenames)} documents."

    )

    return uploaded_filenames, uploaded_corpus

# ==========================================================
# BUILD SIMILARITY MATRIX
# ==========================================================

def build_similarity_matrix(corpus):
    """
    Builds the TF-IDF matrix and cosine similarity matrix
    for the evaluation corpus.

    Parameters
    ----------
    corpus : list[str]

    Returns
    -------
    similarity_matrix
    """

    print("\nBuilding TF-IDF matrix...")

    vectorizer = TfidfVectorizer()

    tfidf_matrix = vectorizer.fit_transform(corpus)

    print("Computing cosine similarity matrix...")

    similarity_matrix = compute_similarity(
        tfidf_matrix
    )

    return similarity_matrix

# ==========================================================
# GENERATE PREDICTIONS
# ==========================================================

def generate_predictions(
    filenames,
    corpus,
    similarity_matrix,
    threshold,
):
    """
    Computes predictions for one threshold.

    Returns
    -------
    predictions : dict
        {(doc1, doc2): prediction}

    pairwise_results : list
        Detailed similarity information.
    """

    predictions = {}

    pairwise_results = []

    for i in range(len(filenames)):

        for j in range(i + 1, len(filenames)):

            doc1 = filenames[i]
            doc2 = filenames[j]

            cosine_score = similarity_matrix[i][j]

            j1 = jaccard_similarity1(
                corpus[i],
                corpus[j]
            )

            j2 = jaccard_similarity2(
                corpus[i],
                corpus[j]
            )

            j3 = jaccard_similarity3(
                corpus[i],
                corpus[j]
            )

            combined_score = (
                cosine_score +
                j1 +
                j2 +
                j3
            ) / 4

            prediction = (
                1
                if combined_score >= threshold
                else 0
            )

            predictions[(doc1, doc2)] = prediction

            pairwise_results.append({

                "Threshold": threshold,

                "Document1": doc1,

                "Document2": doc2,

                "Cosine": round(
                    cosine_score,
                    4
                ),

                "Jaccard_Unigram": round(
                    j1,
                    4
                ),

                "Jaccard_Bigram": round(
                    j2,
                    4
                ),

                "Jaccard_Trigram": round(
                    j3,
                    4
                ),

                "CombinedScore": round(
                    combined_score,
                    4
                ),

                "Prediction": prediction,

            })

    return predictions, pairwise_results

# ==========================================================
# COMPUTE METRICS
# ==========================================================

def compute_metrics(
    predictions,
    ground_truth,
):
    """
    Computes evaluation metrics using the
    generated predictions and the ground truth.
    """

    y_true = []

    y_pred = []

    for pair, actual in ground_truth.items():

        prediction = predictions.get(pair)

        if prediction is None:

            prediction = predictions.get(
                (pair[1], pair[0]),
                0
            )

        y_true.append(actual)

        y_pred.append(prediction)

    precision = precision_score(

        y_true,

        y_pred,

        zero_division=0,

    )

    recall = recall_score(

        y_true,

        y_pred,

        zero_division=0,

    )

    f1 = f1_score(

        y_true,

        y_pred,

        zero_division=0,

    )

    accuracy = accuracy_score(

        y_true,

        y_pred,

    )

    tn, fp, fn, tp = confusion_matrix(

        y_true,

        y_pred,

    ).ravel()

    return {

        "TP": tp,

        "TN": tn,

        "FP": fp,

        "FN": fn,

        "Precision": round(precision, 4),

        "Recall": round(recall, 4),

        "F1-Score": round(f1, 4),

        "Accuracy": round(accuracy, 4),

    }

# ==========================================================
# THRESHOLD SWEEP
# ==========================================================

def run_threshold_sweep():

    print("\n" + "=" * 80)
    print("THRESHOLD SENSITIVITY ANALYSIS")
    print("=" * 80)

    # ------------------------------------------------------
    # Load evaluation corpus
    # ------------------------------------------------------

    filenames, corpus = load_evaluation_corpus()
    ground_truth = load_ground_truth()
    print(f"\nLoaded {len(filenames)} documents.")

    # ------------------------------------------------------
    # Build similarity matrix once
    # ------------------------------------------------------

    similarity_matrix = build_similarity_matrix(corpus)

    summary_results = []

    pairwise_results = []

    # ------------------------------------------------------
    # Evaluate each threshold
    # ------------------------------------------------------

    for threshold in THRESHOLDS:

        print(f"\nEvaluating Threshold = {threshold:.2f}")

        start_time = time.perf_counter()

        predictions, pairs = generate_predictions(

            filenames,

            corpus,

            similarity_matrix,

            threshold,

        )

        metrics = compute_metrics(

            predictions,

            ground_truth,

        )

        elapsed = time.perf_counter() - start_time

        # Add threshold to every pair
        pairwise_results.extend(pairs)

        summary_results.append({

            "Threshold": threshold,

            "Precision": metrics["Precision"],

            "Recall": metrics["Recall"],

            "F1-Score": metrics["F1-Score"],

            "Accuracy": metrics["Accuracy"],

            "TP": metrics["TP"],

            "TN": metrics["TN"],

            "FP": metrics["FP"],

            "FN": metrics["FN"],

            "RuntimeSeconds": round(elapsed, 4),

        })

        print(

            f"Precision={metrics['Precision']:.4f} | "

            f"Recall={metrics['Recall']:.4f} | "

            f"F1={metrics['F1-Score']:.4f} | "

            f"Accuracy={metrics['Accuracy']:.4f}"

        )

        print(

            f"TP={metrics['TP']} "

            f"TN={metrics['TN']} "

            f"FP={metrics['FP']} "

            f"FN={metrics['FN']}"

        )

    return summary_results, pairwise_results

# ==========================================================
# SAVE RESULTS
# ==========================================================

def save_results(

    summary_results,

    pairwise_results,

):

    # ----------------------------------------
    # Threshold summary
    # ----------------------------------------

    summary_df = pd.DataFrame(summary_results)

    summary_csv = LOG_DIR / "threshold_sweep_results.csv"

    summary_df.to_csv(

        summary_csv,

        index=False,

    )

    # ----------------------------------------
    # Pairwise predictions
    # ----------------------------------------

    pairwise_df = pd.DataFrame(pairwise_results)

    pairwise_csv = LOG_DIR / "pairwise_predictions.csv"

    pairwise_df.to_csv(

        pairwise_csv,

        index=False,

    )

    # ----------------------------------------
    # Best threshold
    # ----------------------------------------

    best_row = summary_df.loc[

        summary_df["F1-Score"].idxmax()

    ]

    best_threshold_df = pd.DataFrame([{

        "BestThreshold": best_row["Threshold"],

        "Precision": best_row["Precision"],

        "Recall": best_row["Recall"],

        "F1-Score": best_row["F1-Score"],

        "Accuracy": best_row["Accuracy"],

        "TP": best_row["TP"],

        "TN": best_row["TN"],

        "FP": best_row["FP"],

        "FN": best_row["FN"],

        "RuntimeSeconds": best_row["RuntimeSeconds"],

    }])

    best_threshold_csv = LOG_DIR / "best_threshold.csv"

    best_threshold_df.to_csv(

        best_threshold_csv,

        index=False,

    )

    # ----------------------------------------
    # Print summary
    # ----------------------------------------

    print("\n" + "=" * 80)

    print("THRESHOLD SWEEP COMPLETE")

    print("=" * 80)

    print(f"Best Threshold : {best_row['Threshold']}")

    print(f"Precision      : {best_row['Precision']}")

    print(f"Recall         : {best_row['Recall']}")

    print(f"F1-Score       : {best_row['F1-Score']}")

    print(f"Accuracy       : {best_row['Accuracy']}")

    print(f"Runtime (sec)  : {best_row['RuntimeSeconds']}")

    print("\nFiles Generated:")

    print(summary_csv)

    print(pairwise_csv)

    print(best_threshold_csv)

    print("=" * 80)

# ==========================================================
# MAIN
# ==========================================================

if __name__ == "__main__":

    summary_results, pairwise_results = run_threshold_sweep()

    save_results(

        summary_results,

        pairwise_results,

    )