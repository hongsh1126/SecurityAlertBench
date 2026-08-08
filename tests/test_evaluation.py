import numpy as np

from security_alert_bench.evaluation import binary_metrics


def test_false_positive_rate_uses_benign_denominator() -> None:
    truth = np.array(["benign", "benign", "malicious", "malicious"])
    predictions = np.array(["benign", "malicious", "malicious", "benign"])
    metrics = binary_metrics(truth, predictions, "malicious", ("benign", "malicious"))
    assert metrics["false_positive_rate"] == 0.5
    assert metrics["true_negatives"] == 1
    assert metrics["false_positives"] == 1

