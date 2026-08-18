# Baseline Experiment Results

## Scope

This report records the first reproducible smoke experiment for SecurityAlertBench. It validates the end-to-end data-generation, validation, preprocessing, training, and evaluation pipeline using 3,000 deterministic **synthetic** security alerts.

The experiment is a software and reproducibility check. It is **not** evidence of performance on real intrusion-detection or enterprise security telemetry.

## Configuration

- Dataset: synthetic security alerts generated with `scripts/generate_smoke_data.py --rows 3000`
- Split: stratified 60% train / 20% validation / 20% test
- Model: class-balanced Logistic Regression
- Feature handling: numeric imputation/scaling and categorical one-hot encoding
- Run ID: `20260818T020306Z`
- Evaluation environment: local Windows virtual environment

## Test-set results

| Metric | Value |
|---|---:|
| Rows | 600 |
| Accuracy | 0.9800 |
| Macro F1 | 0.9622 |
| Malicious precision | 0.9072 |
| Malicious recall | 0.9670 |
| Malicious F1 | 0.9362 |
| False-positive rate | 0.0177 |
| Prediction latency | 0.0041 ms/alert |

Confusion matrix: TN=500, FP=9, FN=3, TP=88.

## Validation-set results

| Metric | Value |
|---|---:|
| Rows | 600 |
| Accuracy | 0.9900 |
| Macro F1 | 0.9811 |
| Malicious precision | 0.9381 |
| Malicious recall | 1.0000 |
| Malicious F1 | 0.9681 |
| False-positive rate | 0.0118 |

## Interpretation

The pipeline successfully completed schema checks, stratified splitting, model fitting, prediction, and security-oriented metric calculation. The test set contained 500 benign and 91 malicious alerts; nine benign alerts were escalated incorrectly and three malicious alerts were missed.

Because the data are synthetic and generated from the same controlled process as the smoke test, these numbers should not be generalized to real-world detection quality. The next valid benchmark is an adapter for a documented public dataset, followed by temporal and attack-family holdout evaluation.

## Reproduce

```powershell
python scripts/generate_smoke_data.py --rows 3000
python scripts/train_baseline.py --config configs/baseline.yaml
pytest -q
```

The raw machine-readable metrics are intentionally kept in the local ignored `artifacts/` directory. Do not commit generated models, raw telemetry, or proprietary data.
