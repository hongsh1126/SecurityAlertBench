from pathlib import Path

import pandas as pd
import pytest

from security_alert_bench.data import load_and_validate_data, stratified_split
from test_config import make_config


def valid_frame(rows: int = 20) -> pd.DataFrame:
    return pd.DataFrame(
        {
            "alert_id": [f"a-{index}" for index in range(rows)],
            "event_time": pd.date_range("2026-01-01", periods=rows, freq="h", tz="UTC"),
            "bytes_in": range(rows),
            "source": ["edr", "network"] * (rows // 2),
            "label": ["benign", "malicious"] * (rows // 2),
        }
    )


def test_duplicate_alert_ids_are_rejected(tmp_path: Path) -> None:
    frame = valid_frame()
    frame.loc[1, "alert_id"] = frame.loc[0, "alert_id"]
    path = tmp_path / "data.csv"
    frame.to_csv(path, index=False)
    config = make_config(tmp_path, dataset_path=path)
    with pytest.raises(ValueError, match="Duplicate alert IDs"):
        load_and_validate_data(path, config)


def test_stratified_splits_have_no_id_overlap(tmp_path: Path) -> None:
    frame = valid_frame(100)
    path = tmp_path / "data.csv"
    frame.to_csv(path, index=False)
    config = make_config(tmp_path, dataset_path=path)
    splits = stratified_split(load_and_validate_data(path, config), config)
    assert len(splits.train) == 60
    assert len(splits.validation) == 20
    assert len(splits.test) == 20
    assert set(splits.train.alert_id).isdisjoint(splits.test.alert_id)

