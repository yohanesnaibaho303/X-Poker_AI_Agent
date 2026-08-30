from decimal import Decimal

import pytest

from xpoker_agent.controller import (
    OfflineController,
    SafetyGateInput,
    evaluate_safety_gates,
    plan_raise_sizing,
    simulate_action,
)


def test_raise_sizing_uses_plus_or_minus_to_reach_exact_native_price() -> None:
    plus = plan_raise_sizing(Decimal("18"), Decimal("21"))
    assert (plus.adjustment, plus.presses, plus.expected_displays) == (
        "plus",
        3,
        [Decimal("19"), Decimal("20"), Decimal("21")],
    )

    minus = plan_raise_sizing(Decimal("18"), Decimal("16"), step_native=Decimal("0.50"))
    assert minus.adjustment == "minus"
    assert minus.expected_displays[-1] == Decimal("16")

    with pytest.raises(ValueError, match="not reachable"):
        plan_raise_sizing(Decimal("18"), Decimal("18.25"), step_native=Decimal("0.50"))


def test_offline_controller_stays_blocked_until_every_gate_passes() -> None:
    result = evaluate_safety_gates(
        SafetyGateInput(
            manually_armed=True, identity_match=True, confidence=0.99, legal=True, fresh=True
        )
    )
    assert result.passed is True
    assert result.outcome == "ready"

    stopped = evaluate_safety_gates(
        SafetyGateInput(
            manually_armed=True,
            emergency_stop=True,
            identity_match=True,
            confidence=0.99,
            legal=True,
            fresh=True,
        )
    )
    assert stopped.passed is False
    assert {check.name for check in stopped.checks if not check.passed} == {"emergency_stop_clear"}


def test_duplicate_and_low_confidence_are_independent_blockers() -> None:
    result = evaluate_safety_gates(
        SafetyGateInput(
            manually_armed=True,
            identity_match=True,
            confidence=0.5,
            legal=True,
            fresh=True,
            duplicate=True,
        )
    )
    assert result.passed is False
    assert {check.name for check in result.checks if not check.passed} == {
        "confidence",
        "duplicate_prevention",
    }


def test_simulated_action_requires_verifiable_transition_and_never_clicks() -> None:
    gates = SafetyGateInput(
        manually_armed=True, identity_match=True, confidence=0.99, legal=True, fresh=True
    )
    verified = simulate_action(
        gates,
        idempotency_token="a",
        action="call",
        expected_transition="call:2",
        observed_transition="call:2",
    )
    assert verified.outcome == "executed_verified"
    assert verified.verified is True

    mismatch = simulate_action(
        gates,
        idempotency_token="b",
        action="call",
        expected_transition="call:2",
        observed_transition="raise:4",
    )
    assert mismatch.outcome == "blocked"
    assert mismatch.verified is False
    assert any(
        not check.passed for check in mismatch.audit if check.name == "post_action_verification"
    )


def test_offline_controller_blocks_reused_idempotency_token_and_logs_both_attempts() -> None:
    controller = OfflineController()
    gates = SafetyGateInput(
        manually_armed=True, identity_match=True, confidence=0.99, legal=True, fresh=True
    )
    first = controller.execute(
        gates,
        idempotency_token="same",
        action="check",
        expected_transition="check",
        observed_transition="check",
    )
    second = controller.execute(
        gates,
        idempotency_token="same",
        action="check",
        expected_transition="check",
        observed_transition="check",
    )
    assert first.verified is True
    assert second.verified is False
    assert len(controller.audit_log) == 2


def test_emergency_stop_latches_for_subsequent_attempts() -> None:
    controller = OfflineController()
    gates = SafetyGateInput(
        manually_armed=True, identity_match=True, confidence=0.99, legal=True, fresh=True
    )
    controller.emergency_stop()
    result = controller.execute(
        gates,
        idempotency_token="stop",
        action="check",
        expected_transition="check",
        observed_transition="check",
    )
    assert result.outcome == "blocked"
    assert any(check.name == "emergency_stop_clear" and not check.passed for check in result.audit)
