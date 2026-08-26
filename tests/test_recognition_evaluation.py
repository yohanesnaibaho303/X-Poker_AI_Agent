import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from xpoker_agent.evaluation import (
    RecognitionEvaluationCase,
    evaluate_recognition_cases,
    load_recognition_cases,
    write_recognition_report,
)


def _case(
    case_id: str,
    expected: str | None,
    predicted: str | None,
    *,
    dataset_slice: str = "portrait_default",
    latency_ms: float = 10,
) -> RecognitionEvaluationCase:
    return RecognitionEvaluationCase(
        case_id=case_id,
        component="card",
        dataset_slice=dataset_slice,
        expected=expected,
        predicted=predicted,
        accepted=predicted is not None,
        confidence=0.99 if predicted is not None else 0.2,
        latency_ms=latency_ms,
        evidence_sha256=f"{int(case_id):064x}",
    )


def test_regression_report_measures_errors_but_cannot_promote() -> None:
    report = evaluate_recognition_cases(
        [
            _case("1", "As", "As", latency_ms=4),
            _case("2", "Kd", "Kh", latency_ms=8),
            _case("3", "Qc", None, latency_ms=6),
            _case("4", None, None, dataset_slice="unsupported_overlay", latency_ms=12),
        ],
        component_version="card-v1",
        dataset_id="synthetic-regression-v1",
        dataset_role="regression",
        target_accuracy=0.995,
    )

    assert report.overall.total == 4
    assert report.overall.correct == 1
    assert report.overall.false_positives == 1
    assert report.overall.false_negatives == 2
    assert report.overall.p95_latency_ms == 12
    assert report.promotion_eligible is False
    assert report.gate_passed is False
    assert len(report.dataset_sha256) == 64


def test_holdout_report_can_pass_only_at_declared_target() -> None:
    report = evaluate_recognition_cases(
        [_case("1", "As", "As"), _case("2", "Kd", "Kd")],
        component_version="card-v1",
        dataset_id="heldout-v1",
        dataset_role="holdout",
        target_accuracy=1.0,
    )

    assert report.promotion_eligible is True
    assert report.gate_passed is True


def test_evaluation_rejects_mixed_components_and_duplicate_ids() -> None:
    duplicate = [_case("1", "As", "As"), _case("1", "Kd", "Kd")]
    with pytest.raises(ValueError, match="IDs must be unique"):
        evaluate_recognition_cases(
            duplicate,
            component_version="v1",
            dataset_id="bad",
            dataset_role="regression",
            target_accuracy=1.0,
        )

    mixed = [_case("1", "As", "As"), _case("2", "Kd", "Kd")]
    mixed[1].component = "street"
    with pytest.raises(ValueError, match="cannot mix components"):
        evaluate_recognition_cases(
            mixed,
            component_version="v1",
            dataset_id="bad",
            dataset_role="regression",
            target_accuracy=1.0,
        )


def test_case_rejects_accepted_without_prediction() -> None:
    with pytest.raises(ValidationError, match="accepted recognition"):
        RecognitionEvaluationCase(
            case_id="bad",
            component="card",
            dataset_slice="default",
            expected="As",
            predicted=None,
            accepted=True,
            confidence=0.9,
            latency_ms=1,
            evidence_sha256="a" * 64,
        )


def test_dataset_and_report_file_round_trip(tmp_path: Path) -> None:
    cases = [_case("1", "As", "As")]
    dataset_path = tmp_path / "cases.json"
    dataset_path.write_text(
        json.dumps([case.model_dump(mode="json") for case in cases]),
        encoding="utf-8",
    )
    report = evaluate_recognition_cases(
        load_recognition_cases(dataset_path),
        component_version="card-v1",
        dataset_id="regression-v1",
        dataset_role="regression",
        target_accuracy=0.995,
    )
    report_path = tmp_path / "report.json"

    write_recognition_report(report, report_path)

    persisted = json.loads(report_path.read_text(encoding="utf-8"))
    assert persisted["dataset_sha256"] == report.dataset_sha256
    assert persisted["gate_passed"] is False
