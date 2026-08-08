from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = PROJECT_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from security_alert_bench import load_config, run_experiment  # noqa: E402


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Train and evaluate a security alert baseline.")
    parser.add_argument("--config", type=Path, default=PROJECT_ROOT / "configs/baseline.yaml")
    return parser.parse_args()


def main() -> int:
    try:
        args = parse_args()
        config_path = args.config if args.config.is_absolute() else PROJECT_ROOT / args.config
        run_dir = run_experiment(load_config(config_path, PROJECT_ROOT))
    except (FileNotFoundError, FileExistsError, KeyError, TypeError, ValueError, RuntimeError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    summary = json.loads((run_dir / "dataset_summary.json").read_text(encoding="utf-8"))
    print(f"Experiment complete: {run_dir}")
    print(json.dumps(summary["test_metrics"], indent=2))
    if summary["smoke_test_only"]:
        print("WARNING: These metrics come from synthetic smoke data and are not real-world evidence.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

