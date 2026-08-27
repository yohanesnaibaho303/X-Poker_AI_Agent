import json
import subprocess
import sys

from xpoker_agent.evaluation.reconstruction import load_reconstruction_cases


def test_reconstruction_evaluator_writes_holdout_gate_report(tmp_path) -> None:
    dataset = tmp_path / "cases.json"
    output = tmp_path / "report.json"
    dataset.write_text(
        json.dumps(
            [
                {
                    "case_id": "hand-1",
                    "replay_sha256": "1" * 64,
                    "dataset_slice": "standard_nlh",
                    "supported": True,
                    "exact_match": True,
                    "safely_stopped": False,
                    "latency_ms": 10,
                }
            ]
        ),
        encoding="utf-8",
    )
    assert load_reconstruction_cases(dataset)[0].case_id == "hand-1"
    subprocess.run(
        [
            sys.executable,
            "scripts/evaluate_reconstruction.py",
            str(dataset),
            str(output),
            "--reducer-version",
            "test",
            "--dataset-id",
            "holdout-test",
            "--dataset-role",
            "holdout",
        ],
        check=True,
    )
    assert json.loads(output.read_text(encoding="utf-8"))["gate_passed"] is True
