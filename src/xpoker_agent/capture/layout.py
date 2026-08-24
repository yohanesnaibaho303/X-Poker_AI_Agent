"""Versioned X-Poker layout-profile loading."""

from __future__ import annotations

import json
from pathlib import Path

from xpoker_agent.capture.models import LayoutProfile
from xpoker_agent.config import PROJECT_ROOT

DEFAULT_LAYOUT_PROFILE = PROJECT_ROOT / "configs" / "layouts" / "xpoker_windows_10_portrait.json"


def load_layout_profile(path: Path = DEFAULT_LAYOUT_PROFILE) -> LayoutProfile:
    with path.open("r", encoding="utf-8") as handle:
        payload = json.load(handle)
    return LayoutProfile.model_validate(payload)
