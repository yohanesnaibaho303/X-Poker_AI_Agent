import json
from decimal import Decimal

import pytest
from pydantic import ValidationError

from xpoker_agent.config import load_game_config, load_runtime_config
from xpoker_agent.models import (
    GameConfig,
    OperatingMode,
    Position,
    RuntimeConfig,
)


def test_authoritative_game_configuration_loads() -> None:
    config = load_game_config()

    assert config.variant == "NLH"
    assert config.format == "cash"
    assert config.seats == 9
    assert config.rake.percent == 0
    assert config.native_small_blind == Decimal("1")
    assert config.native_big_blind == Decimal("2")
    assert config.objective == "chip_ev"
    assert config.positions == list(Position)
    assert config.enabled_special_rules == ["single_board_bomb_pot"]


def test_runtime_is_observe_only_and_controller_disabled() -> None:
    runtime = load_runtime_config()

    assert runtime.mode is OperatingMode.OBSERVE
    assert runtime.controller_enabled is False


def test_configuration_rejects_wrong_positions() -> None:
    payload = load_game_config().model_dump(mode="json")
    payload["positions"] = list(reversed([position.value for position in Position]))
    with pytest.raises(ValidationError, match="authoritative order"):
        GameConfig.model_validate(payload)


def test_non_one_two_native_blinds_are_rejected() -> None:
    payload = load_game_config().model_dump(mode="json")
    payload["native_big_blind"] = "3"

    with pytest.raises(ValidationError, match="SB 1 and BB 2 native chips"):
        GameConfig.model_validate(payload)


def test_armed_mode_is_rejected_even_when_loaded_from_json() -> None:
    payload = json.loads(load_runtime_config().model_dump_json())
    payload["mode"] = "armed_test_control"

    with pytest.raises(ValidationError, match="unavailable"):
        RuntimeConfig.model_validate(payload)
