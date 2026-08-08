from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate synthetic alerts for pipeline smoke testing.")
    parser.add_argument("--rows", type=int, default=3000)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument(
        "--output",
        type=Path,
        default=PROJECT_ROOT / "data/processed/security_alerts_smoke.csv",
    )
    return parser.parse_args()


def generate(rows: int, seed: int) -> pd.DataFrame:
    if rows < 100:
        raise ValueError("At least 100 rows are required")
    rng = np.random.default_rng(seed)
    malicious = rng.random(rows) < 0.15
    sources = np.where(
        malicious,
        rng.choice(["edr", "iam", "network"], rows, p=[0.50, 0.30, 0.20]),
        rng.choice(["edr", "iam", "network"], rows, p=[0.25, 0.25, 0.50]),
    )
    protocols = rng.choice(["tcp", "udp", "https", "ssh"], rows, p=[0.35, 0.20, 0.35, 0.10])
    failed_logins = rng.poisson(np.where(malicious, 7.0, 0.8))
    bytes_in = rng.lognormal(np.where(malicious, 9.5, 8.0), 1.0)
    bytes_out = rng.lognormal(np.where(malicious, 10.0, 8.2), 1.1)
    frame = pd.DataFrame(
        {
            "alert_id": [f"alert-{index:07d}" for index in range(rows)],
            "event_time": pd.date_range("2026-01-01", periods=rows, freq="5min", tz="UTC"),
            "source": sources,
            "protocol": protocols,
            "src_port": rng.integers(1024, 65536, rows),
            "dst_port": rng.choice([22, 53, 80, 443, 445, 3389, 8080], rows),
            "bytes_in": np.round(bytes_in, 2),
            "bytes_out": np.round(bytes_out, 2),
            "failed_logins": failed_logins,
            "duration_seconds": np.round(rng.exponential(np.where(malicious, 180.0, 45.0)), 2),
            "label": np.where(malicious, "malicious", "benign"),
        }
    )
    missing_indexes = rng.choice(rows, size=max(1, rows // 100), replace=False)
    frame.loc[missing_indexes, "protocol"] = None
    return frame


def main() -> int:
    args = parse_args()
    output = args.output if args.output.is_absolute() else PROJECT_ROOT / args.output
    frame = generate(args.rows, args.seed)
    output.parent.mkdir(parents=True, exist_ok=True)
    frame.to_csv(output, index=False)
    print(f"Synthetic smoke dataset: {output}")
    print(frame["label"].value_counts().to_string())
    print("WARNING: Synthetic metrics are not real-world security evidence.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

