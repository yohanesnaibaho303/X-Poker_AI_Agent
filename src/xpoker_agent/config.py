"""Configuration loading with strict validation and no implicit substitutions."""

from __future__ import annotations

import json
from pathlib import Path

from xpoker_agent.models import GameConfig, RuntimeConfig

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_GAME_CONFIG = PROJECT_ROOT / "configs" / "game" / "initial_9max_nlh.json"
SIX_MAX_GAME_CONFIG = PROJECT_ROOT / "configs" / "game" / "initial_6max_nlh.json"
GAME_CONFIGS = {6: SIX_MAX_GAME_CONFIG, 9: DEFAULT_GAME_CONFIG}
DEFAULT_RUNTIME_CONFIG = PROJECT_ROOT / "configs" / "runtime" / "default.json"


def _read_json(path: Path) -> dict[str, object]:
    with path.open("r", encoding="utf-8") as handle:
        result = json.load(handle)
    if not isinstance(result, dict):
        raise ValueError(f"configuration root must be an object: {path}")
    return result


def load_game_config(path: Path | None = None, *, table_size: int = 9) -> GameConfig:
    if path is None:
        try:
            path = GAME_CONFIGS[table_size]
        except KeyError as error:
            raise ValueError("table_size must be 6 or 9") from error
    return GameConfig.model_validate(_read_json(path))


def load_runtime_config(path: Path = DEFAULT_RUNTIME_CONFIG) -> RuntimeConfig:
    return RuntimeConfig.model_validate(_read_json(path))
