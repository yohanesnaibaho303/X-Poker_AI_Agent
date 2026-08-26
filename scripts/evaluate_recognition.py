"""Create a versioned recognition report from a frozen JSON case set."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from xpoker_agent.evaluation import (  # noqa: E402
    evaluate_recognition_cases,
    load_recognition_cases,
    write_recognition_report,
)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("dataset", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--component-version", required=True)
    parser.add_argument("--dataset-id", required=True)
    parser.add_argument(
        "--dataset-role",
        required=True,
        choices=("calibration", "regression", "holdout"),
    )
    parser.add_argument("--target-accuracy", required=True, type=float)
    args = parser.parse_args()
    report = evaluate_recognition_cases(
        load_recognition_cases(args.dataset),
        component_version=args.component_version,
        dataset_id=args.dataset_id,
        dataset_role=args.dataset_role,
        target_accuracy=args.target_accuracy,
    )
    write_recognition_report(report, args.output)


if __name__ == "__main__":
    main()
