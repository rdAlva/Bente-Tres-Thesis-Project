# import sys
# import os
# sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

# import pandas as pd
# from app.nlp.similarity import (
#     cosine_similarity_score,
#     jaccard_similarity1,
#     jaccard_similarity2,
#     jaccard_similarity3,
#     jaccard_similarity_score,
#     similarity,
# )
# from app.nlp.vectorizer import filenames
# from app.nlp.ngrams import corpus

# # ─────────────────────────────────────────
# # GROUND TRUTH
# # Member B manually labels each pair
# # 1 = similar, 0 = not similar
# # ─────────────────────────────────────────
# ground_truth = {
#     ("Attitudes-of-Filipino-Millenials-towards-luxury-brands.txt", "Case-8.Greenwood-Resources.txt"): 0,
#     ("Attitudes-of-Filipino-Millenials-towards-luxury-brands.txt", "DeterminantsofStudentsMotivationonEntrepreneurship-SPCF.txt"): 0,
#     ("Attitudes-of-Filipino-Millenials-towards-luxury-brands.txt", "Plagiarized_Variant_Luxury_Brands.txt"): 1,
#     ("Attitudes-of-Filipino-Millenials-towards-luxury-brands.txt", "Variant1_PP.txt"): 0,
#     ("Attitudes-of-Filipino-Millenials-towards-luxury-brands.txt", "Variant2_HP.txt"): 0,
#     ("DeterminantsofStudentsMotivationonEntrepreneurship-SPCF.txt", "Plagiarized_Variant_Luxury_Brands.txt"): 0,
#     ("DeterminantsofStudentsMotivationonEntrepreneurship-SPCF.txt", "Variant1_PP.txt"): 0,
#     ("DeterminantsofStudentsMotivationonEntrepreneurship-SPCF.txt", "Variant2_HP.txt"): 0,
#     ("Case-8.Greenwood-Resources.txt", "DeterminantsofStudentsMotivationonEntrepreneurship-SPCF.txt"): 0,
#     ("Case-8.Greenwood-Resources.txt", "Plagiarized_Variant_Luxury_Brands.txt"): 0,
#     ("Case-8.Greenwood-Resources.txt", "Variant1_PP.txt"): 0,
#     ("Case-8.Greenwood-Resources.txt", "Variant2_HP.txt"): 1,
#     ("Plagiarized_Variant_Luxury_Brands.txt", "Variant1_PP.txt"): 0,
#     ("Plagiarized_Variant_Luxury_Brands.txt", "Variant2_HP.txt"): 0,
#     ("Variant1_PP.txt", "Variant2_HP.txt"): 1,


#     # add all your document pairs here
# }

# # ─────────────────────────────────────────
# # COMPUTE METRICS
# # ─────────────────────────────────────────
# def compute_metrics(predictions, ground_truth):
#     TP = TN = FP = FN = 0

#     for pair, actual in ground_truth.items():
#         predicted = predictions.get(pair, 0)

#         if predicted == 1 and actual == 1:
#             TP += 1
#         elif predicted == 0 and actual == 0:
#             TN += 1
#         elif predicted == 1 and actual == 0:
#             FP += 1
#         elif predicted == 0 and actual == 1:
#             FN += 1

#     precision = TP / (TP + FP) if (TP + FP) > 0 else 0
#     recall    = TP / (TP + FN) if (TP + FN) > 0 else 0
#     f1        = 2 * (precision * recall) / (precision + recall) if (precision + recall) > 0 else 0
#     accuracy  = (TP + TN) / (TP + TN + FP + FN) if (TP + TN + FP + FN) > 0 else 0

#     return {
#         "TP": TP, "TN": TN, "FP": FP, "FN": FN,
#         "Precision": round(precision, 4),
#         "Recall":    round(recall, 4),
#         "F1-Score":  round(f1, 4),
#         "Accuracy":  round(accuracy, 4)
#     }

# # ─────────────────────────────────────────
# # THE SWEEP
# # ─────────────────────────────────────────
# def run_threshold_sweep():
#     thresholds = [0.10,0.11,0.12,0.13,0.14, 0.15,0.20,0.30, 0.40, 0.50, 0.60, 0.70, 0.80, 0.90]
#     results = []

#     print("\n" + "="*70)
#     print("THRESHOLD SENSITIVITY SWEEP RESULTS")
#     print("="*70)

#     for threshold in thresholds:
#         predictions = {}

#         for i in range(len(filenames)):
#             for j in range(i + 1, len(filenames)):
#                 pair = (filenames[i], filenames[j])

#                 # get your cosine score
#                 cosine_score = similarity[i][j]

#                 # get jaccard scores using your functions
#                 j1 = jaccard_similarity1(corpus[i], corpus[j], n=1)
#                 j2 = jaccard_similarity2(corpus[i], corpus[j], n=2)
#                 j3 = jaccard_similarity3(corpus[i], corpus[j], n=3)

#                 # average all scores together
#                 combined_score = (cosine_score + j1 + j2 + j3) / 4

#                 # apply threshold
#                 predictions[pair] = 1 if combined_score >= threshold else 0

#         # compute metrics for this threshold
#         metrics = compute_metrics(predictions, ground_truth)
#         results.append({
#             "Threshold": threshold,
#             "Precision": metrics["Precision"],
#             "Recall":    metrics["Recall"],
#             "F1-Score":  metrics["F1-Score"],
#             "Accuracy":  metrics["Accuracy"],
#             "TP": metrics["TP"],
#             "TN": metrics["TN"],
#             "FP": metrics["FP"],
#             "FN": metrics["FN"],
#         })

#         print(f"\nThreshold : {threshold}")
#         print(f"  Precision : {metrics['Precision']}")
#         print(f"  Recall    : {metrics['Recall']}")
#         print(f"  F1-Score  : {metrics['F1-Score']}")
#         print(f"  Accuracy  : {metrics['Accuracy']}")
#         print(f"  TP:{metrics['TP']}  TN:{metrics['TN']}  FP:{metrics['FP']}  FN:{metrics['FN']}")

#     # ─────────────────────────────────────────
#     # SAVE TO CSV
#     # ─────────────────────────────────────────
#     df = pd.DataFrame(results)
#     os.makedirs("logs", exist_ok=True)
#     output_path = "logs/threshold_sweep_results.csv"
#     df.to_csv(output_path, index=False)

#     # find best threshold
#     best = df.loc[df["F1-Score"].idxmax()]

#     print("\n" + "="*70)
#     print(f"Best Threshold : {best['Threshold']}")
#     print(f"Best F1-Score  : {best['F1-Score']}")
#     print(f"Results saved  : {output_path}")
#     print("="*70)

#     return df

# # ─────────────────────────────────────────
# # RUN
# # ─────────────────────────────────────────
# if __name__ == "__main__":
#     run_threshold_sweep()


import os
import sys
import time
from pathlib import Path

sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

import pandas as pd

from sklearn.metrics import (
    precision_score,
    recall_score,
    accuracy_score,
    f1_score,
    confusion_matrix,
)

from app.nlp.similarity import (
    similarity,
    jaccard_similarity1,
    jaccard_similarity2,
    jaccard_similarity3,
)

from app.nlp.vectorizer import filenames
from app.nlp.ngrams import corpus

# ==========================================================
# CONFIGURATION
# ==========================================================

BASE_DIR = Path(__file__).resolve().parent.parent

GROUND_TRUTH_FILE = BASE_DIR / "evaluation" / "ground_truth.csv"

LOG_DIR = BASE_DIR / "logs"

THRESHOLDS = [
    0.10,
    0.11,
    0.12,
    0.13,
    0.14,
    0.15,
    0.20,
    0.30,
    0.40,
    0.50,
    0.60,
    0.70,
    0.80,
    0.90,
]

LOG_DIR.mkdir(exist_ok=True)

# ==========================================================
# LOAD GROUND TRUTH
# ==========================================================

if not GROUND_TRUTH_FILE.exists():
    raise FileNotFoundError(
        f"Ground truth CSV not found:\n{GROUND_TRUTH_FILE}"
    )

ground_truth_df = pd.read_csv(GROUND_TRUTH_FILE)

required_columns = {"doc1", "doc2", "actual"}

if not required_columns.issubset(ground_truth_df.columns):
    raise ValueError(
        "ground_truth.csv must contain columns:\n"
        "doc1, doc2, actual"
    )

ground_truth = {}

for _, row in ground_truth_df.iterrows():

    pair = (row["doc1"], row["doc2"])

    ground_truth[pair] = int(row["actual"])


# ==========================================================
# COMPUTE METRICS
# ==========================================================

def compute_metrics(predictions):

    y_true = []
    y_pred = []

    for pair, actual in ground_truth.items():

        prediction = predictions.get(pair, 0)

        y_true.append(actual)
        y_pred.append(prediction)

    precision = precision_score(
        y_true,
        y_pred,
        zero_division=0
    )

    recall = recall_score(
        y_true,
        y_pred,
        zero_division=0
    )

    f1 = f1_score(
        y_true,
        y_pred,
        zero_division=0
    )

    accuracy = accuracy_score(
        y_true,
        y_pred,
    )

    tn, fp, fn, tp = confusion_matrix(
        y_true,
        y_pred
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

    summary_results = []
    pairwise_results = []

    print("\n" + "=" * 80)
    print("THRESHOLD SENSITIVITY ANALYSIS")
    print("=" * 80)

    for threshold in THRESHOLDS:

        print(f"\nEvaluating Threshold = {threshold:.2f}")

        start_time = time.perf_counter()

        predictions = {}

        for i in range(len(filenames)):

            for j in range(i + 1, len(filenames)):

                doc1 = filenames[i]
                doc2 = filenames[j]

                cosine_score = similarity[i][j]

                unigram_score = jaccard_similarity1(
                    corpus[i],
                    corpus[j],
                    n=1
                )

                bigram_score = jaccard_similarity2(
                    corpus[i],
                    corpus[j],
                    n=2
                )

                trigram_score = jaccard_similarity3(
                    corpus[i],
                    corpus[j],
                    n=3
                )

                combined_score = (
                    cosine_score +
                    unigram_score +
                    bigram_score +
                    trigram_score
                ) / 4

                prediction = 1 if combined_score >= threshold else 0

                predictions[(doc1, doc2)] = prediction

                actual = ground_truth.get((doc1, doc2))

                if actual is None:
                    actual = ground_truth.get((doc2, doc1))

                pairwise_results.append({

                    "Threshold": threshold,

                    "Document1": doc1,

                    "Document2": doc2,

                    "Cosine": round(cosine_score, 4),

                    "Jaccard_Unigram": round(unigram_score, 4),

                    "Jaccard_Bigram": round(bigram_score, 4),

                    "Jaccard_Trigram": round(trigram_score, 4),

                    "CombinedScore": round(combined_score, 4),

                    "Prediction": prediction,

                    "Actual": actual

                })

        metrics = compute_metrics(predictions)

        elapsed = time.perf_counter() - start_time

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

            "RuntimeSeconds": round(elapsed, 4)

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

    # ==========================================================
    # SAVE SUMMARY RESULTS
    # ==========================================================

    summary_df = pd.DataFrame(summary_results)

    summary_csv = LOG_DIR / "threshold_sweep_results.csv"

    summary_df.to_csv(
        summary_csv,
        index=False
    )

    # ==========================================================
    # SAVE PAIRWISE RESULTS
    # ==========================================================

    pairwise_df = pd.DataFrame(pairwise_results)

    pairwise_csv = LOG_DIR / "pairwise_predictions.csv"

    pairwise_df.to_csv(
        pairwise_csv,
        index=False
    )

    # ==========================================================
    # BEST THRESHOLD
    # ==========================================================

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

        "RuntimeSeconds": best_row["RuntimeSeconds"]

    }])

    best_threshold_csv = LOG_DIR / "best_threshold.csv"

    best_threshold_df.to_csv(
        best_threshold_csv,
        index=False
    )

    # ==========================================================
    # PRINT SUMMARY
    # ==========================================================

    print("\n" + "=" * 80)
    print("THRESHOLD SWEEP COMPLETE")
    print("=" * 80)

    print(f"Best Threshold : {best_row['Threshold']}")
    print(f"Precision     : {best_row['Precision']}")
    print(f"Recall        : {best_row['Recall']}")
    print(f"F1-Score      : {best_row['F1-Score']}")
    print(f"Accuracy      : {best_row['Accuracy']}")
    print(f"Runtime (sec) : {best_row['RuntimeSeconds']}")

    print("\nFiles Generated:")

    print(summary_csv)

    print(pairwise_csv)

    print(best_threshold_csv)

    print("=" * 80)

    return summary_df


# ==========================================================
# MAIN
# ==========================================================

if __name__ == "__main__":

    run_threshold_sweep()