# NF-UNSW-NB15-v2 ordered holdout results

Run configuration: 250,000-row public sample, `Label` target, numeric flow
features, median imputation, 70%/15%/15% ordered split. The file has no explicit
timestamp column, so row order is used as a temporal proxy; this is not a strict
deployment-time evaluation.

| Model | Precision | Malicious recall | F1 | ROC-AUC | PR-AUC | Fit (s) |
|---|---:|---:|---:|---:|---:|---:|
| Random Forest | 0.9487 | 0.9889 | 0.9684 | 0.9997 | 0.9902 | 2.408 |
| XGBoost | 0.9542 | 0.9827 | 0.9682 | 0.9997 | 0.9917 | 1.515 |

XGBoost achieved the best ROC-AUC and PR-AUC, while Random Forest achieved the
best malicious recall by 0.62 percentage points. Both models had nearly equal
F1. These results are software and pipeline validation evidence on a public
sample, not evidence of production detection performance.
