# SecurityAlertBench

[![Python](https://img.shields.io/badge/Python-3.10%2B-blue.svg)](https://www.python.org/)
[![Tests](https://img.shields.io/badge/tests-pytest-green.svg)](https://pytest.org/)

**Reproducible evaluation for security alert classification.**

SecurityAlertBench is a production-oriented baseline for curating, validating, splitting, training, and evaluating tabular security-alert data. It emphasizes analyst-aligned metrics such as macro F1, malicious-class recall, and false-positive rate rather than accuracy alone.

> The included synthetic dataset is only a smoke test for the software pipeline. Its metrics are not evidence of real-world security performance.

## What This Stage Demonstrates

- Explicit security-alert data contract
- Schema, missing-value, label, duplicate, and leakage checks
- Reproducible stratified train/validation/test splits
- Mixed numeric and categorical preprocessing
- Logistic Regression baseline with class balancing
- Precision, recall, F1, false-positive rate, confusion matrix, and latency
- Machine-readable experiment artifacts
- Unit tests for high-risk data and metric logic
- Temporal NF flow benchmark comparing Random Forest and XGBoost

## Repository Structure

```text
SecurityAlertBench/
├── configs/baseline.yaml
├── scripts/
│   ├── generate_smoke_data.py
│   ├── train_baseline.py
│   └── benchmark_nf_temporal.py
├── src/security_alert_bench/
│   ├── config.py
│   ├── data.py
│   ├── evaluation.py
│   └── training.py
├── tests/
├── data/                 # Local data; ignored by Git
├── artifacts/            # Models and run outputs; ignored by Git
└── reports/              # Generated reports; ignored by Git
```

## Quick Start

Windows PowerShell:

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
```

Generate a deterministic synthetic smoke dataset:

```powershell
python scripts/generate_smoke_data.py --rows 3000
```

Train and evaluate the baseline:

```powershell
python scripts/train_baseline.py --config configs/baseline.yaml
```

Run tests:

```powershell
pytest -q
```

## Public NF IDS temporal benchmark

Place a licensed NF-UNSW-NB15, NF-CSE-CIC-IDS2018, or NF-ToN-IoT CSV under
`data/raw/` (raw data remains local and is not committed). Run:

```powershell
python scripts/benchmark_nf_temporal.py --data data/raw/NF-UNSW-NB15-v2.csv --label-column Label --time-column Timestamp --output reports/nf_unsw_temporal_benchmark.json
```

The adapter sorts rows chronologically, trains on the earliest 70%, reserves the
next 15% as validation, and evaluates on the latest 15%. It compares a
class-balanced Random Forest with histogram XGBoost using numeric flow features,
median imputation, and precision, malicious recall, F1, ROC-AUC, and PR-AUC.
An initial 250,000-row NF-UNSW-NB15-v2 ordered-holdout result is documented in
`reports/nf_unsw_temporal_results.md`; because the file has no timestamp column,
row order is used as a proxy and must not be described as strict temporal
deployment validation.

## Input Data Contract

The default pipeline expects one row per alert and these columns:

| Column | Type | Meaning |
|---|---|---|
| `alert_id` | string | Unique immutable alert identifier |
| `event_time` | datetime | Alert occurrence time |
| `source` | category | Telemetry source, such as EDR or IAM |
| `protocol` | category | Network/application protocol |
| `src_port` | number | Source port |
| `dst_port` | number | Destination port |
| `bytes_in` | number | Inbound byte count |
| `bytes_out` | number | Outbound byte count |
| `failed_logins` | number | Authentication failures in the alert window |
| `duration_seconds` | number | Observed activity duration |
| `label` | category | `benign` or `malicious` |

The model never uses `alert_id`, `event_time`, or `label` as input features. Extend the lists in `configs/baseline.yaml` when adapting a public dataset.

## Generated Artifacts

Each run creates `artifacts/runs/<run-id>/`:

```text
├── config.json
├── dataset_summary.json
├── metrics.json
├── classification_report.csv
├── confusion_matrix.csv
├── confusion_matrix.png
├── predictions.csv
└── model.joblib
```

The first reproducible smoke-run summary is documented in
[`reports/experiment_results.md`](reports/experiment_results.md). It uses
synthetic data only and must not be interpreted as real-world intrusion-
detection performance.

## Metric Interpretation

- **Macro F1:** gives equal weight to benign and malicious classes.
- **Malicious recall:** fraction of malicious alerts successfully detected.
- **False-positive rate:** fraction of benign alerts incorrectly escalated.
- **Accuracy:** included for context but insufficient for imbalanced security data.
- **Latency:** model prediction time in the current environment, not a deployment SLA.

## Leakage Controls

The pipeline fails when:

- alert IDs are duplicated;
- labels are missing or outside the allowed set;
- a configured feature is also an ID, timestamp, or target column;
- a feature column is entirely missing;
- either class is too small for a reliable stratified split.

These checks prevent a high metric caused by accidental target or identity leakage.

## Adapting a Real Dataset

1. Place a CSV under `data/raw/`.
2. Preserve the original file and document its source and license in `data/README.md`.
3. Create a conversion script that maps source fields into the data contract.
4. Update `configs/baseline.yaml` with the converted CSV and feature lists.
5. Run training and review both aggregate metrics and individual errors.

Do not commit proprietary telemetry, credentials, personal data, raw public datasets, or model artifacts.

## How Flow-Level Security Data Is Collected in Practice

The smoke dataset in this repository is synthetic and is not a router log. In a real network, flow-level security data is typically produced through the following pipeline:

```text
Hosts / IoT devices
        -> switches, routers, firewalls, or cloud flow-log services
        -> NetFlow/IPFIX/sFlow exporter
        -> flow collector
        -> Kafka, SIEM, search index, or security data lake
        -> curated ML features and analyst labels
```

Routers and sensors normally summarize packets into one flow record rather than storing every packet payload. A record can contain source and destination addresses and ports, protocol, flow duration, packet and byte counts, TCP flags, retransmission statistics, throughput, and an analyst or scenario-derived label. Common collection and storage technologies include NetFlow/IPFIX, AWS VPC Flow Logs, Kafka, Splunk, Elasticsearch/OpenSearch, and object storage such as S3 or an enterprise data lake.

The public IDS datasets used in the companion JISA research are already aggregated NetFlow V2 records. They are not raw router event logs and they do not contain packet payloads. Their `Label` and `Attack` fields come from the documented attack scenarios or ground truth supplied with each research dataset. In an operational environment, labels are usually produced later from SIEM correlation, EDR evidence, incident investigation, or analyst feedback.

This distinction matters when interpreting results: benchmark CSV metrics demonstrate reproducible model behavior on flow summaries, while production deployment additionally requires collection, retention, privacy controls, label quality, drift monitoring, and analyst feedback loops.

## Roadmap

- Add a documented public security dataset adapter
- Add temporal splitting to simulate future-alert performance
- Compare Logistic Regression, gradient boosting, and a Transformer baseline
- Add MLflow experiment tracking and dataset version hashes
- Add analyst disagreement and calibration metrics
- Add GitHub Actions and containerized training

## Limitations

This first stage is a classical ML baseline, not an LLM system. It does not yet provide LoRA/QLoRA fine-tuning, analyst feedback, model routing, drift monitoring, or online deployment. Those belong to later portfolio stages built on this evaluation foundation.
