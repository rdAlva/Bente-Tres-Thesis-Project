import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

import pandas as pd
from app.nlp.similarity import (
    cosine_similarity_score,
    jaccard_similarity1,
    jaccard_similarity2,
    jaccard_similarity3,
    jaccard_similarity_score,
    similarity,
)
from app.nlp.vectorizer import filenames
from app.nlp.ngrams import corpus

# ─────────────────────────────────────────
# GROUND TRUTH
# Member B manually labels each pair
# 1 = similar, 0 = not similar
# ─────────────────────────────────────────
ground_truth = {
    ("Attitudes-of-Filipino-Millenials-towards-luxury-brands.txt", "Case-8.Greenwood-Resources.txt"): 0,
    ("Attitudes-of-Filipino-Millenials-towards-luxury-brands.txt", "DeterminantsofStudentsMotivationonEntrepreneurship-SPCF.txt"): 0,
    ("Attitudes-of-Filipino-Millenials-towards-luxury-brands.txt", "Plagiarized_Variant_Luxury_Brands.txt"): 1,
    ("Attitudes-of-Filipino-Millenials-towards-luxury-brands.txt", "Variant1_PP.txt"): 0,
    ("Attitudes-of-Filipino-Millenials-towards-luxury-brands.txt", "Variant2_HP.txt"): 0,
    ("DeterminantsofStudentsMotivationonEntrepreneurship-SPCF.txt", "Plagiarized_Variant_Luxury_Brands.txt"): 0,
    ("DeterminantsofStudentsMotivationonEntrepreneurship-SPCF.txt", "Variant1_PP.txt"): 0,
    ("DeterminantsofStudentsMotivationonEntrepreneurship-SPCF.txt", "Variant2_HP.txt"): 0,
    ("Case-8.Greenwood-Resources.txt", "DeterminantsofStudentsMotivationonEntrepreneurship-SPCF.txt"): 0,
    ("Case-8.Greenwood-Resources.txt", "Plagiarized_Variant_Luxury_Brands.txt"): 0,
    ("Case-8.Greenwood-Resources.txt", "Variant1_PP.txt"): 0,
    ("Case-8.Greenwood-Resources.txt", "Variant2_HP.txt"): 1,
    ("Plagiarized_Variant_Luxury_Brands.txt", "Variant1_PP.txt"): 0,
    ("Plagiarized_Variant_Luxury_Brands.txt", "Variant2_HP.txt"): 0,
    ("Variant1_PP.txt", "Variant2_HP.txt"): 1,


    # add all your document pairs here
}

# ─────────────────────────────────────────
# COMPUTE METRICS
# ─────────────────────────────────────────
def compute_metrics(predictions, ground_truth):
    TP = TN = FP = FN = 0

    for pair, actual in ground_truth.items():
        predicted = predictions.get(pair, 0)

        if predicted == 1 and actual == 1:
            TP += 1
        elif predicted == 0 and actual == 0:
            TN += 1
        elif predicted == 1 and actual == 0:
            FP += 1
        elif predicted == 0 and actual == 1:
            FN += 1

    precision = TP / (TP + FP) if (TP + FP) > 0 else 0
    recall    = TP / (TP + FN) if (TP + FN) > 0 else 0
    f1        = 2 * (precision * recall) / (precision + recall) if (precision + recall) > 0 else 0
    accuracy  = (TP + TN) / (TP + TN + FP + FN) if (TP + TN + FP + FN) > 0 else 0

    return {
        "TP": TP, "TN": TN, "FP": FP, "FN": FN,
        "Precision": round(precision, 4),
        "Recall":    round(recall, 4),
        "F1-Score":  round(f1, 4),
        "Accuracy":  round(accuracy, 4)
    }

# ─────────────────────────────────────────
# THE SWEEP
# ─────────────────────────────────────────
def run_threshold_sweep():
    thresholds = [0.10,0.11,0.12,0.13,0.14, 0.15,0.20,0.30, 0.40, 0.50, 0.60, 0.70, 0.80, 0.90]
    results = []

    print("\n" + "="*70)
    print("THRESHOLD SENSITIVITY SWEEP RESULTS")
    print("="*70)

    for threshold in thresholds:
        predictions = {}

        for i in range(len(filenames)):
            for j in range(i + 1, len(filenames)):
                pair = (filenames[i], filenames[j])

                # get your cosine score
                cosine_score = similarity[i][j]

                # get jaccard scores using your functions
                j1 = jaccard_similarity1(corpus[i], corpus[j], n=1)
                j2 = jaccard_similarity2(corpus[i], corpus[j], n=2)
                j3 = jaccard_similarity3(corpus[i], corpus[j], n=3)

                # average all scores together
                combined_score = (cosine_score + j1 + j2 + j3) / 4

                # apply threshold
                predictions[pair] = 1 if combined_score >= threshold else 0

        # compute metrics for this threshold
        metrics = compute_metrics(predictions, ground_truth)
        results.append({
            "Threshold": threshold,
            "Precision": metrics["Precision"],
            "Recall":    metrics["Recall"],
            "F1-Score":  metrics["F1-Score"],
            "Accuracy":  metrics["Accuracy"],
            "TP": metrics["TP"],
            "TN": metrics["TN"],
            "FP": metrics["FP"],
            "FN": metrics["FN"],
        })

        print(f"\nThreshold : {threshold}")
        print(f"  Precision : {metrics['Precision']}")
        print(f"  Recall    : {metrics['Recall']}")
        print(f"  F1-Score  : {metrics['F1-Score']}")
        print(f"  Accuracy  : {metrics['Accuracy']}")
        print(f"  TP:{metrics['TP']}  TN:{metrics['TN']}  FP:{metrics['FP']}  FN:{metrics['FN']}")

    # ─────────────────────────────────────────
    # SAVE TO CSV
    # ─────────────────────────────────────────
    df = pd.DataFrame(results)
    os.makedirs("logs", exist_ok=True)
    output_path = "logs/threshold_sweep_results.csv"
    df.to_csv(output_path, index=False)

    # find best threshold
    best = df.loc[df["F1-Score"].idxmax()]

    print("\n" + "="*70)
    print(f"Best Threshold : {best['Threshold']}")
    print(f"Best F1-Score  : {best['F1-Score']}")
    print(f"Results saved  : {output_path}")
    print("="*70)

    return df

# ─────────────────────────────────────────
# RUN
# ─────────────────────────────────────────
if __name__ == "__main__":
    run_threshold_sweep()