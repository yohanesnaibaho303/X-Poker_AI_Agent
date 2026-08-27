"""Create a versioned reconstruction report from a frozen JSON case set."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from xpoker_agent.evaluation.reconstruction import (  # noqa: E402
    ReconstructionEvaluationCase,
    evaluate_reconstruction_cases,
)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("dataset", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--reducer-version", required=True)
    parser.add_argument("--dataset-id", required=True)
    parser.add_argument("--dataset-role", required=True, choices=("regression", "holdout"))
    parser.add_argument("--target-accuracy", type=float, default=0.98)
    args = parser.parse_args()
    payload = json.loads(args.dataset.read_text(encoding="utf-8"))
    if not isinstance(payload, list):
        raise ValueError("reconstruction dataset must be a JSON array")
    cases = [ReconstructionEvaluationCase.model_validate(item) for item in payload]
    report = evaluate_reconstruction_cases(
        cases,
        reducer_version=args.reducer_version,
        dataset_id=args.dataset_id,
        dataset_role=args.dataset_role,
        target_accuracy=args.target_accuracy,
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(report.model_dump(mode="json"), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
