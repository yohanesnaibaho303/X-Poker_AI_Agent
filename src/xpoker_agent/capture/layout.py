"""Versioned X-Poker layout-profile loading."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Literal

from xpoker_agent.capture.models import LayoutProfile
from xpoker_agent.config import PROJECT_ROOT

DEFAULT_LAYOUT_PROFILE = PROJECT_ROOT / "configs" / "layouts" / "xpoker_windows_10_portrait.json"
NINE_MAX_LAYOUT_PROFILE = (
    PROJECT_ROOT / "configs" / "layouts" / "xpoker_windows_10_portrait_9max.json"
)


def load_layout_profile(
    path: Path | None = None, *, table_size: Literal[6, 9] = 9
) -> LayoutProfile:
    selected = path or (NINE_MAX_LAYOUT_PROFILE if table_size == 9 else DEFAULT_LAYOUT_PROFILE)
    with selected.open("r", encoding="utf-8") as handle:
        payload = json.load(handle)
    return LayoutProfile.model_validate(payload)
