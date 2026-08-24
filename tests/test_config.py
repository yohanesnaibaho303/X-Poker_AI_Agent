import json
from decimal import Decimal

import pytest
from pydantic import ValidationError

from xpoker_agent.config import load_game_config, load_runtime_config
from xpoker_agent.models import GameConfig, OperatingMode, Position, RuntimeConfig


def test_authoritative_game_configuration_loads() -> None:
    config = load_game_config()

    assert config.variant == "NLH"
    assert config.format == "cash"
    assert config.seats == 9
    assert config.rake.percent == 0
    assert config.default_open_size_bb == Decimal("2.0")
    assert config.objective == "chip_ev"
    assert config.positions == list(Position)


def test_runtime_is_observe_only_and_controller_disabled() -> None:
    runtime = load_runtime_config()

    assert runtime.mode is OperatingMode.OBSERVE
    assert runtime.controller_enabled is False


def test_six_max_configuration_is_rejected() -> None:
    payload = load_game_config().model_dump(mode="json")
    payload["seats"] = 6

    with pytest.raises(ValidationError):
        GameConfig.model_validate(payload)


def test_non_two_bb_default_is_rejected() -> None:
    payload = load_game_config().model_dump(mode="json")
    payload["default_open_size_bb"] = "2.5"

    with pytest.raises(ValidationError, match="2.0 BB"):
        GameConfig.model_validate(payload)


def test_armed_mode_is_rejected_even_when_loaded_from_json() -> None:
    payload = json.loads(load_runtime_config().model_dump_json())
    payload["mode"] = "armed_test_control"

    with pytest.raises(ValidationError, match="unavailable"):
        RuntimeConfig.model_validate(payload)
