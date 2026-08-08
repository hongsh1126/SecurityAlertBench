from pathlib import Path

import pytest

from security_alert_bench.config import ExperimentConfig


def make_config(tmp_path: Path, **overrides) -> ExperimentConfig:
    values = {
        "dataset_path": tmp_path / "data.csv",
        "output_dir": tmp_path / "runs",
        "target_column": "label",
        "id_column": "alert_id",
        "timestamp_column": "event_time",
        "positive_label": "malicious",
        "allowed_labels": ("benign", "malicious"),
        "numeric_features": ("bytes_in",),
        "categorical_features": ("source",),
    }
    values.update(overrides)
    return ExperimentConfig(**values)


def test_config_rejects_target_leakage(tmp_path: Path) -> None:
    config = make_config(tmp_path, numeric_features=("bytes_in", "label"))
    with pytest.raises(ValueError, match="Leakage-prone"):
        config.validate()


def test_config_rejects_invalid_split_sizes(tmp_path: Path) -> None:
    config = make_config(tmp_path, test_size=0.6, validation_size=0.4)
    with pytest.raises(ValueError, match="less than 1"):
        config.validate()

