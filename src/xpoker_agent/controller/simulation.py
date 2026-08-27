"""Offline controller safety gates; deliberately performs no input."""

from __future__ import annotations

from pydantic import Field

from xpoker_agent.capture.models import LayoutProfile, NormalizedRect
from xpoker_agent.models import PreflightCheck, StrictModel


class SafetyGateInput(StrictModel):
    manually_armed: bool = False
    emergency_stop: bool = False
    identity_match: bool = False
    confidence: float = Field(ge=0, le=1)
    confidence_threshold: float = Field(default=0.95, ge=0, le=1)
    legal: bool = False
    fresh: bool = False
    duplicate: bool = False


class SafetyGateResult(StrictModel):
    passed: bool
    checks: list[PreflightCheck]
    outcome: str = "blocked"


class ActionCalibration(StrictModel):
    calibration_id: str
    layout_id: str
    version: str
    targets: dict[str, NormalizedRect]


def calibrate_actions(
    layout: LayoutProfile, targets: dict[str, NormalizedRect], *, version: str
) -> ActionCalibration:
    """Create a versioned offline calibration from declared layout regions."""
    if not targets:
        raise ValueError("at least one action target is required")
    action_region = layout.regions["actions"]
    for name, target in targets.items():
        if target.x < action_region.x or target.y < action_region.y:
            raise ValueError(f"target {name!r} is outside the action region")
        if (
            target.x + target.width > action_region.x + action_region.width
            or target.y + target.height > action_region.y + action_region.height
        ):
            raise ValueError(f"target {name!r} is outside the action region")
    return ActionCalibration(
        calibration_id=f"{layout.layout_id}:{version}",
        layout_id=layout.layout_id,
        version=version,
        targets=targets,
    )


class SimulatedActionResult(StrictModel):
    idempotency_token: str
    action: str
    outcome: str
    audit: list[PreflightCheck]
    verified: bool = False


def evaluate_safety_gates(gates: SafetyGateInput) -> SafetyGateResult:
    checks = [
        PreflightCheck(name="manual_arming", passed=gates.manually_armed),
        PreflightCheck(name="emergency_stop_clear", passed=not gates.emergency_stop),
        PreflightCheck(name="target_identity", passed=gates.identity_match),
        PreflightCheck(name="confidence", passed=gates.confidence >= gates.confidence_threshold),
        PreflightCheck(name="state_legality", passed=gates.legal),
        PreflightCheck(name="state_freshness", passed=gates.fresh),
        PreflightCheck(name="duplicate_prevention", passed=not gates.duplicate),
    ]
    passed = all(check.passed for check in checks)
    return SafetyGateResult(passed=passed, checks=checks, outcome="ready" if passed else "blocked")


def simulate_action(
    gates: SafetyGateInput,
    *,
    idempotency_token: str = "offline-token",
    action: str,
    expected_transition: str,
    observed_transition: str | None,
) -> SimulatedActionResult:
    """Record a simulated attempt; this function never sends input."""
    safety = evaluate_safety_gates(gates)
    checks = list(safety.checks)
    if not action:
        checks.append(PreflightCheck(name="action_present", passed=False))
    else:
        checks.append(PreflightCheck(name="action_present", passed=True))
    verified = safety.passed and bool(action) and observed_transition == expected_transition
    checks.append(PreflightCheck(name="post_action_verification", passed=verified))
    return SimulatedActionResult(
        idempotency_token=idempotency_token,
        action=action,
        outcome="executed_verified" if verified else "blocked",
        audit=checks,
        verified=verified,
    )


class OfflineController:
    """Stateful simulation harness; it has no OS input implementation."""

    def __init__(self) -> None:
        self._tokens: set[str] = set()
        self._stopped = False
        self.audit_log: list[SimulatedActionResult] = []

    def emergency_stop(self) -> None:
        self._stopped = True

    def execute(
        self,
        gates: SafetyGateInput,
        *,
        idempotency_token: str,
        action: str,
        expected_transition: str,
        observed_transition: str | None,
    ) -> SimulatedActionResult:
        duplicate = idempotency_token in self._tokens
        result = simulate_action(
            gates.model_copy(
                update={
                    "duplicate": gates.duplicate or duplicate,
                    "emergency_stop": gates.emergency_stop or self._stopped,
                }
            ),
            idempotency_token=idempotency_token,
            action=action,
            expected_transition=expected_transition,
            observed_transition=observed_transition,
        )
        self._tokens.add(idempotency_token)
        self.audit_log.append(result)
        return result

    def execute_calibrated(
        self,
        calibration: ActionCalibration,
        gates: SafetyGateInput,
        *,
        idempotency_token: str,
        action: str,
        expected_transition: str,
        observed_transition: str | None,
    ) -> SimulatedActionResult:
        if action not in calibration.targets:
            result = SimulatedActionResult(
                idempotency_token=idempotency_token,
                action=action,
                outcome="blocked",
                audit=[PreflightCheck(name="calibrated_target", passed=False)],
            )
            self.audit_log.append(result)
            return result
        result = self.execute(
            gates,
            idempotency_token=idempotency_token,
            action=action,
            expected_transition=expected_transition,
            observed_transition=observed_transition,
        )
        result.audit.append(PreflightCheck(name="calibrated_target", passed=True))
        return result
