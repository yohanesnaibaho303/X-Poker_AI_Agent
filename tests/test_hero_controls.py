from decimal import Decimal

from xpoker_agent.vision.controls import parse_hero_action_controls


def test_pre_action_toggles_are_not_legal_actions() -> None:
    result = parse_hero_action_controls("F/C   Check   Call Any")

    assert result.mode == "pre_action"
    assert result.available_actions == []
    assert result.pre_action_toggles == ["fold_or_check", "call_any"]
    assert result.ocr_text_sha256 is not None


def test_current_decision_controls_include_call_amount() -> None:
    result = parse_hero_action_controls("Fold  Call 4  Raise")

    assert result.mode == "decision"
    assert result.available_actions == ["fold", "call", "raise"]
    assert result.call_amount_native == Decimal("4")


def test_empty_control_text_is_absent() -> None:
    result = parse_hero_action_controls("")

    assert result.mode == "absent"
    assert result.confidence == 0.0
