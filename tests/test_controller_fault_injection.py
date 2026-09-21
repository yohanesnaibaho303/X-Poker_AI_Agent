"""Comprehensive fault injection and safety gate tests for Milestone 9 controller."""

from decimal import Decimal

import pytest

from xpoker_agent.capture.layout import load_layout_profile
from xpoker_agent.capture.models import NormalizedRect
from xpoker_agent.controller import (
    OfflineController,
    SafetyGateInput,
    calibrate_actions,
    evaluate_safety_gates,
    plan_raise_meter_target,
    plan_raise_sizing,
    simulate_action,
)


def test_safety_gate_all_passing() -> None:
    """When all conditions are met, the safety gate evaluates to ready."""
    gates = SafetyGateInput(
        manually_armed=True,
        emergency_stop=False,
        identity_match=True,
        confidence=0.99,
        confidence_threshold=0.95,
        legal=True,
        fresh=True,
        duplicate=False,
    )
    result = evaluate_safety_gates(gates)
    assert result.passed is True
    assert result.outcome == "ready"
    assert all(check.passed for check in result.checks)


@pytest.mark.parametrize(
    ("override", "expected_failed_check"),
    [
        ({"manually_armed": False}, "manual_arming"),
        ({"emergency_stop": True}, "emergency_stop_clear"),
        ({"identity_match": False}, "target_identity"),
        ({"confidence": 0.94}, "confidence"),
        ({"legal": False}, "state_legality"),
        ({"fresh": False}, "state_freshness"),
        ({"duplicate": True}, "duplicate_prevention"),
    ],
)
def test_individual_safety_gate_fault_injection(
    override: dict[str, object], expected_failed_check: str
) -> None:
    """Each individual safety gate must independently block execution and record its failure."""
    base = {
        "manually_armed": True,
        "emergency_stop": False,
        "identity_match": True,
        "confidence": 0.98,
        "confidence_threshold": 0.95,
        "legal": True,
        "fresh": True,
        "duplicate": False,
    }
    base.update(override)
    gates = SafetyGateInput(**base)
    result = evaluate_safety_gates(gates)
    assert result.passed is False
    assert result.outcome == "blocked"
    failed_names = [check.name for check in result.checks if not check.passed]
    assert expected_failed_check in failed_names


def test_multiple_simultaneous_faults_recorded_in_audit() -> None:
    """When multiple gates fail simultaneously, all failures are recorded in the audit log."""
    gates = SafetyGateInput(
        manually_armed=False,
        emergency_stop=True,
        identity_match=False,
        confidence=0.10,
        legal=False,
        fresh=False,
        duplicate=True,
    )
    result = evaluate_safety_gates(gates)
    assert result.passed is False
    failed_names = {check.name for check in result.checks if not check.passed}
    assert failed_names == {
        "manual_arming",
        "emergency_stop_clear",
        "target_identity",
        "confidence",
        "state_legality",
        "state_freshness",
        "duplicate_prevention",
    }


def test_offline_controller_emergency_stop_latch() -> None:
    """Triggering emergency stop latches the controller into permanently blocked state."""
    controller = OfflineController()
    valid_gates = SafetyGateInput(
        manually_armed=True,
        emergency_stop=False,
        identity_match=True,
        confidence=0.98,
        legal=True,
        fresh=True,
        duplicate=False,
    )

    first = controller.execute(
        valid_gates,
        idempotency_token="tok-1",
        action="fold",
        expected_transition="fold",
        observed_transition="fold",
    )
    assert first.verified is True
    assert first.outcome == "executed_verified"

    controller.emergency_stop()

    second = controller.execute(
        valid_gates,
        idempotency_token="tok-2",
        action="fold",
        expected_transition="fold",
        observed_transition="fold",
    )
    assert second.verified is False
    assert second.outcome == "blocked"
    assert any(c.name == "emergency_stop_clear" and not c.passed for c in second.audit)


def test_idempotency_burst_prevention() -> None:
    """100 repeated execution attempts with the same token must block 99 times."""
    controller = OfflineController()
    valid_gates = SafetyGateInput(
        manually_armed=True,
        emergency_stop=False,
        identity_match=True,
        confidence=0.98,
        legal=True,
        fresh=True,
        duplicate=False,
    )

    results = [
        controller.execute(
            valid_gates,
            idempotency_token="burst-token-001",
            action="call",
            expected_transition="call:2",
            observed_transition="call:2",
        )
        for _ in range(100)
    ]

    assert results[0].verified is True
    assert results[0].outcome == "executed_verified"
    for dup in results[1:]:
        assert dup.verified is False
        assert dup.outcome == "blocked"
        assert any(c.name == "duplicate_prevention" and not c.passed for c in dup.audit)


def test_transition_mismatch_disarms_action() -> None:
    """When observed transition does not match expected transition, action fails verification."""
    gates = SafetyGateInput(
        manually_armed=True, identity_match=True, confidence=0.98, legal=True, fresh=True
    )
    res = simulate_action(
        gates,
        idempotency_token="mismatch-1",
        action="raise",
        expected_transition="raise:4",
        observed_transition="raise:6",  # Mismatch!
    )
    assert res.verified is False
    assert res.outcome == "blocked"
    assert any(c.name == "post_action_verification" and not c.passed for c in res.audit)


def test_empty_action_blocks() -> None:
    """An empty or null action string fails preflight check."""
    gates = SafetyGateInput(
        manually_armed=True, identity_match=True, confidence=0.98, legal=True, fresh=True
    )
    res = simulate_action(
        gates,
        idempotency_token="empty-act",
        action="",
        expected_transition="fold",
        observed_transition="fold",
    )
    assert res.verified is False
    assert res.outcome == "blocked"
    assert any(c.name == "action_present" and not c.passed for c in res.audit)


def test_raise_meter_out_of_bounds_fault_injection() -> None:
    """Meter planning rejects non-positive, inverted, and out-of-range bounds."""
    with pytest.raises(ValueError, match="positive increasing bounds"):
        plan_raise_meter_target(Decimal("0"), Decimal("100"), Decimal("50"))

    with pytest.raises(ValueError, match="positive increasing bounds"):
        plan_raise_meter_target(Decimal("100"), Decimal("50"), Decimal("75"))

    with pytest.raises(ValueError, match="outside the legal meter range"):
        plan_raise_meter_target(Decimal("10"), Decimal("50"), Decimal("55"))

    with pytest.raises(ValueError, match="outside the legal meter range"):
        plan_raise_meter_target(Decimal("10"), Decimal("50"), Decimal("5"))


def test_raise_sizing_invalid_step_fault_injection() -> None:
    """Raise sizing rejects non-positive steps or unreachable targets."""
    with pytest.raises(ValueError, match="positive"):
        plan_raise_sizing(Decimal("10"), Decimal("20"), step_native=Decimal("0"))

    with pytest.raises(ValueError, match="not reachable"):
        plan_raise_sizing(Decimal("10"), Decimal("20"), step_native=Decimal("3"))


def test_calibrated_targets_outside_boundary_rejected() -> None:
    """Targets extending outside the declared layout actions region are rejected."""
    layout = load_layout_profile()
    region = layout.regions["actions"]

    # Target placed above the action region
    with pytest.raises(ValueError, match="outside the action region"):
        calibrate_actions(
            layout,
            {"fold": NormalizedRect(x=region.x, y=region.y - 0.05, width=0.1, height=0.05)},
            version="v1",
        )

    # Target placed inside the frame but outside the action region (actions y starts at 0.76)
    with pytest.raises(ValueError, match="outside the action region"):
        calibrate_actions(
            layout,
            {"fold": NormalizedRect(x=region.x, y=0.50, width=0.2, height=0.05)},
            version="v1",
        )
