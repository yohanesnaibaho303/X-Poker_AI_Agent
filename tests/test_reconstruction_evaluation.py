import pytest
from pydantic import ValidationError

from xpoker_agent.evaluation.reconstruction import (
    ReconstructionEvaluationCase,
    evaluate_reconstruction_cases,
)


def _case(
    case_id: str,
    *,
    supported: bool = True,
    exact_match: bool = True,
    safely_stopped: bool = False,
) -> ReconstructionEvaluationCase:
    return ReconstructionEvaluationCase(
        case_id=case_id,
        replay_sha256=f"{int(case_id):064x}",
        dataset_slice="standard",
        supported=supported,
        exact_match=exact_match,
        safely_stopped=safely_stopped,
        latency_ms=float(case_id),
    )


def test_regression_replay_cannot_promote_even_when_exact() -> None:
    report = evaluate_reconstruction_cases(
        [_case("1"), _case("2", supported=False, exact_match=False, safely_stopped=True)],
        reducer_version="1.0",
        dataset_id="synthetic",
        dataset_role="regression",
    )

    assert report.metrics.exact_accuracy == 1
    assert report.metrics.unsupported_safe_rate == 1
    assert report.promotion_eligible is False
    assert report.gate_passed is False


def test_holdout_requires_exact_accuracy_and_full_unsupported_safety() -> None:
    passed = evaluate_reconstruction_cases(
        [_case("1"), _case("2", supported=False, exact_match=False, safely_stopped=True)],
        reducer_version="1.0",
        dataset_id="holdout",
        dataset_role="holdout",
    )
    unsafe = evaluate_reconstruction_cases(
        [_case("1"), _case("2", supported=False, exact_match=False, safely_stopped=False)],
        reducer_version="1.0",
        dataset_id="holdout-unsafe",
        dataset_role="holdout",
    )

    assert passed.gate_passed is True
    assert unsafe.gate_passed is False


def test_reconstruction_outcome_rejects_contradictions() -> None:
    with pytest.raises(ValidationError, match="both match and stop"):
        _case("1", safely_stopped=True)


def test_reconstruction_dataset_rejects_duplicate_ids() -> None:
    with pytest.raises(ValueError, match="unique"):
        evaluate_reconstruction_cases(
            [_case("1"), _case("1")],
            reducer_version="1.0",
            dataset_id="duplicate",
            dataset_role="regression",
        )
