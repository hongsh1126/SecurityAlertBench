from __future__ import annotations

import hashlib
import json
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import joblib
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

from .config import ExperimentConfig
from .data import DataSplits, load_and_validate_data, stratified_split
from .evaluation import save_evaluation_artifacts


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as file:
        for chunk in iter(lambda: file.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def build_pipeline(config: ExperimentConfig) -> Pipeline:
    numeric_pipeline = Pipeline(
        steps=[
            ("imputer", SimpleImputer(strategy="median")),
            ("scaler", StandardScaler()),
        ]
    )
    categorical_pipeline = Pipeline(
        steps=[
            ("imputer", SimpleImputer(strategy="most_frequent")),
            ("encoder", OneHotEncoder(handle_unknown="ignore")),
        ]
    )
    preprocessor = ColumnTransformer(
        transformers=[
            ("numeric", numeric_pipeline, list(config.numeric_features)),
            ("categorical", categorical_pipeline, list(config.categorical_features)),
        ]
    )
    classifier = LogisticRegression(
        class_weight="balanced",
        max_iter=config.max_iterations,
        random_state=config.random_seed,
    )
    return Pipeline(steps=[("preprocessor", preprocessor), ("classifier", classifier)])


def _evaluate_split(
    model: Pipeline,
    split: pd.DataFrame,
    config: ExperimentConfig,
    output_dir: Path,
) -> dict[str, Any]:
    features = split.loc[:, config.feature_columns]
    truth = split[config.target_column]
    started = time.perf_counter()
    predictions = model.predict(features)
    elapsed = time.perf_counter() - started
    class_order = list(model.named_steps["classifier"].classes_)
    positive_index = class_order.index(config.positive_label)
    probabilities = model.predict_proba(features)[:, positive_index]
    return save_evaluation_artifacts(
        y_true=truth,
        y_pred=predictions,
        probabilities=probabilities,
        alert_ids=split[config.id_column],
        output_dir=output_dir,
        positive_label=config.positive_label,
        labels=(config.allowed_labels[0], config.allowed_labels[1]),
        extra_metrics={
            "rows": len(split),
            "prediction_seconds": round(elapsed, 6),
            "milliseconds_per_alert": round((elapsed / len(split)) * 1000, 6),
        },
    )


def run_experiment(config: ExperimentConfig) -> Path:
    frame = load_and_validate_data(config.dataset_path, config)
    splits: DataSplits = stratified_split(frame, config)
    run_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    run_dir = config.output_dir / run_id
    if run_dir.exists():
        raise FileExistsError(f"Run directory already exists: {run_dir}")
    validation_dir = run_dir / "validation"
    test_dir = run_dir / "test"
    run_dir.mkdir(parents=True)

    model = build_pipeline(config)
    model.fit(
        splits.train.loc[:, config.feature_columns],
        splits.train[config.target_column],
    )
    validation_metrics = _evaluate_split(model, splits.validation, config, validation_dir)
    test_metrics = _evaluate_split(model, splits.test, config, test_dir)
    joblib.dump(model, run_dir / "model.joblib")
    (run_dir / "config.json").write_text(
        json.dumps(config.to_json_dict(), indent=2), encoding="utf-8"
    )
    summary = {
        "dataset_path": str(config.dataset_path),
        "dataset_sha256": _sha256(config.dataset_path),
        "rows_total": len(frame),
        "rows_train": len(splits.train),
        "rows_validation": len(splits.validation),
        "rows_test": len(splits.test),
        "label_counts": {str(key): int(value) for key, value in frame[config.target_column].value_counts().items()},
        "validation_metrics": validation_metrics,
        "test_metrics": test_metrics,
        "smoke_test_only": "smoke" in config.dataset_path.name.lower(),
    }
    (run_dir / "dataset_summary.json").write_text(
        json.dumps(summary, indent=2), encoding="utf-8"
    )
    return run_dir

