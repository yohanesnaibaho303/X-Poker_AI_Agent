import pytest

from xpoker_agent.capture.layout import load_layout_profile
from xpoker_agent.capture.models import NormalizedRect
from xpoker_agent.controller import OfflineController, SafetyGateInput, calibrate_actions


def test_offline_calibration_is_versioned_and_scoped_to_actions_region() -> None:
    layout = load_layout_profile()
    region = layout.regions["actions"]
    calibration = calibrate_actions(
        layout,
        {
            "call": NormalizedRect(
                x=region.x, y=region.y, width=region.width / 2, height=region.height
            )
        },
        version="1",
    )
    assert calibration.calibration_id == f"{layout.layout_id}:1"
    with pytest.raises(ValueError, match="outside"):
        calibrate_actions(
            layout, {"call": NormalizedRect(x=0, y=0, width=0.1, height=0.1)}, version="1"
        )


def test_calibrated_simulation_blocks_unmapped_actions() -> None:
    layout = load_layout_profile()
    region = layout.regions["actions"]
    calibration = calibrate_actions(
        layout,
        {
            "call": NormalizedRect(
                x=region.x, y=region.y, width=region.width / 2, height=region.height
            )
        },
        version="1",
    )
    gates = SafetyGateInput(
        manually_armed=True, identity_match=True, confidence=0.99, legal=True, fresh=True
    )
    result = OfflineController().execute_calibrated(
        calibration,
        gates,
        idempotency_token="x",
        action="raise",
        expected_transition="raise",
        observed_transition="raise",
    )
    assert result.outcome == "blocked"
    assert result.audit[0].name == "calibrated_target"
