from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

import yaml


@dataclass(frozen=True)
class ExperimentConfig:
    dataset_path: Path
    output_dir: Path
    target_column: str
    id_column: str
    timestamp_column: str
    positive_label: str
    allowed_labels: tuple[str, ...]
    numeric_features: tuple[str, ...]
    categorical_features: tuple[str, ...]
    test_size: float = 0.20
    validation_size: float = 0.20
    random_seed: int = 42
    max_iterations: int = 1000

    @property
    def feature_columns(self) -> tuple[str, ...]:
        return self.numeric_features + self.categorical_features

    def validate(self) -> None:
        if not 0 < self.test_size < 1:
            raise ValueError("test_size must be between 0 and 1")
        if not 0 < self.validation_size < 1:
            raise ValueError("validation_size must be between 0 and 1")
        if self.test_size + self.validation_size >= 1:
            raise ValueError("test_size + validation_size must be less than 1")
        if self.positive_label not in self.allowed_labels:
            raise ValueError("positive_label must be present in allowed_labels")
        if len(self.allowed_labels) != 2:
            raise ValueError("The stage-one evaluator supports exactly two labels")
        if not self.feature_columns:
            raise ValueError("At least one feature is required")
        if len(set(self.feature_columns)) != len(self.feature_columns):
            raise ValueError("Feature names must be unique")
        forbidden = {self.target_column, self.id_column, self.timestamp_column}
        leaked = forbidden.intersection(self.feature_columns)
        if leaked:
            raise ValueError(f"Leakage-prone columns configured as features: {sorted(leaked)}")
        if self.max_iterations <= 0:
            raise ValueError("max_iterations must be positive")

    def to_json_dict(self) -> dict[str, Any]:
        values = asdict(self)
        values["dataset_path"] = str(values["dataset_path"])
        values["output_dir"] = str(values["output_dir"])
        return values


def load_config(path: Path, project_root: Path | None = None) -> ExperimentConfig:
    values = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    if not isinstance(values, dict):
        raise ValueError("Configuration must be a YAML mapping")
    root = project_root or path.resolve().parents[1]
    for key in ("dataset_path", "output_dir"):
        configured_path = Path(values[key])
        values[key] = configured_path if configured_path.is_absolute() else root / configured_path
    for key in ("allowed_labels", "numeric_features", "categorical_features"):
        values[key] = tuple(values[key])
    config = ExperimentConfig(**values)
    config.validate()
    return config

