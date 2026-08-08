from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from sklearn.metrics import (
    accuracy_score,
    classification_report,
    confusion_matrix,
    f1_score,
    precision_score,
    recall_score,
)


def binary_metrics(
    y_true: pd.Series | np.ndarray,
    y_pred: pd.Series | np.ndarray,
    positive_label: str,
    labels: tuple[str, str],
) -> dict[str, float | int]:
    negative_label = next(label for label in labels if label != positive_label)
    negative_first = (negative_label, positive_label)
    matrix = confusion_matrix(y_true, y_pred, labels=negative_first)
    tn, fp, fn, tp = matrix.ravel()
    false_positive_rate = fp / (fp + tn) if fp + tn else 0.0
    return {
        "accuracy": round(float(accuracy_score(y_true, y_pred)), 6),
        "macro_f1": round(float(f1_score(y_true, y_pred, average="macro")), 6),
        "positive_precision": round(float(precision_score(y_true, y_pred, pos_label=positive_label)), 6),
        "positive_recall": round(float(recall_score(y_true, y_pred, pos_label=positive_label)), 6),
        "positive_f1": round(float(f1_score(y_true, y_pred, pos_label=positive_label)), 6),
        "false_positive_rate": round(float(false_positive_rate), 6),
        "true_negatives": int(tn),
        "false_positives": int(fp),
        "false_negatives": int(fn),
        "true_positives": int(tp),
    }


def save_evaluation_artifacts(
    y_true: pd.Series,
    y_pred: np.ndarray,
    probabilities: np.ndarray,
    alert_ids: pd.Series,
    output_dir: Path,
    positive_label: str,
    labels: tuple[str, str],
    extra_metrics: dict[str, Any] | None = None,
) -> dict[str, Any]:
    output_dir.mkdir(parents=True, exist_ok=True)
    negative_label = next(label for label in labels if label != positive_label)
    ordered_labels = (negative_label, positive_label)
    metrics: dict[str, Any] = binary_metrics(y_true, y_pred, positive_label, labels)
    if extra_metrics:
        metrics.update(extra_metrics)
    (output_dir / "metrics.json").write_text(
        json.dumps(metrics, indent=2), encoding="utf-8"
    )

    report = classification_report(
        y_true, y_pred, labels=ordered_labels, output_dict=True, zero_division=0
    )
    pd.DataFrame(report).transpose().to_csv(output_dir / "classification_report.csv")

    matrix = confusion_matrix(y_true, y_pred, labels=ordered_labels)
    pd.DataFrame(matrix, index=ordered_labels, columns=ordered_labels).to_csv(
        output_dir / "confusion_matrix.csv"
    )
    figure, axis = plt.subplots(figsize=(5, 4))
    image = axis.imshow(matrix, cmap="Blues")
    for row in range(matrix.shape[0]):
        for column in range(matrix.shape[1]):
            axis.text(column, row, str(matrix[row, column]), ha="center", va="center")
    axis.set_xticks(range(2), ordered_labels)
    axis.set_yticks(range(2), ordered_labels)
    axis.set_xlabel("Predicted label")
    axis.set_ylabel("True label")
    axis.set_title("Security Alert Confusion Matrix")
    figure.colorbar(image, ax=axis)
    figure.tight_layout()
    figure.savefig(output_dir / "confusion_matrix.png", dpi=160)
    plt.close(figure)

    prediction_frame = pd.DataFrame(
        {
            "alert_id": alert_ids.astype(str),
            "actual_label": y_true.astype(str),
            "predicted_label": y_pred,
            "positive_probability": probabilities,
        }
    )
    prediction_frame["is_error"] = prediction_frame["actual_label"] != prediction_frame["predicted_label"]
    prediction_frame.to_csv(output_dir / "predictions.csv", index=False)
    return metrics

