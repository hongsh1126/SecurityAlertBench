from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import pandas as pd
from sklearn.model_selection import train_test_split

from .config import ExperimentConfig


@dataclass(frozen=True)
class DataSplits:
    train: pd.DataFrame
    validation: pd.DataFrame
    test: pd.DataFrame


def load_and_validate_data(path: Path, config: ExperimentConfig) -> pd.DataFrame:
    if not path.exists():
        raise FileNotFoundError(f"Dataset does not exist: {path}")
    frame = pd.read_csv(path)
    required = {
        config.id_column,
        config.timestamp_column,
        config.target_column,
        *config.feature_columns,
    }
    missing = sorted(required.difference(frame.columns))
    if missing:
        raise ValueError(f"Missing required columns: {missing}")
    if frame.empty:
        raise ValueError("Dataset is empty")
    if frame[config.id_column].isna().any():
        raise ValueError("Alert IDs must not be missing")
    if frame[config.id_column].duplicated().any():
        count = int(frame[config.id_column].duplicated().sum())
        raise ValueError(f"Duplicate alert IDs detected: {count}")
    if frame[config.target_column].isna().any():
        raise ValueError("Target labels must not be missing")
    actual_labels = set(frame[config.target_column].astype(str).unique())
    unexpected = sorted(actual_labels.difference(config.allowed_labels))
    if unexpected:
        raise ValueError(f"Unexpected target labels: {unexpected}")
    missing_labels = sorted(set(config.allowed_labels).difference(actual_labels))
    if missing_labels:
        raise ValueError(f"Configured labels absent from dataset: {missing_labels}")
    label_counts = frame[config.target_column].value_counts()
    if int(label_counts.min()) < 5:
        raise ValueError("Each label requires at least five rows for stratified splitting")
    for feature in config.feature_columns:
        if frame[feature].isna().all():
            raise ValueError(f"Feature is entirely missing: {feature}")
    timestamps = pd.to_datetime(frame[config.timestamp_column], errors="coerce", utc=True)
    if timestamps.isna().any():
        raise ValueError("Invalid timestamps detected")
    validated = frame.copy()
    validated[config.timestamp_column] = timestamps
    return validated


def stratified_split(frame: pd.DataFrame, config: ExperimentConfig) -> DataSplits:
    train_validation, test = train_test_split(
        frame,
        test_size=config.test_size,
        random_state=config.random_seed,
        stratify=frame[config.target_column],
    )
    relative_validation_size = config.validation_size / (1 - config.test_size)
    train, validation = train_test_split(
        train_validation,
        test_size=relative_validation_size,
        random_state=config.random_seed,
        stratify=train_validation[config.target_column],
    )
    id_sets = [
        set(split[config.id_column]) for split in (train, validation, test)
    ]
    if id_sets[0] & id_sets[1] or id_sets[0] & id_sets[2] or id_sets[1] & id_sets[2]:
        raise RuntimeError("Alert ID leakage detected across splits")
    return DataSplits(
        train=train.reset_index(drop=True),
        validation=validation.reset_index(drop=True),
        test=test.reset_index(drop=True),
    )

