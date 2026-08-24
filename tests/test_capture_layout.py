import pytest

from xpoker_agent.capture.layout import load_layout_profile
from xpoker_agent.capture.models import LayoutProfile


def test_first_xpoker_layout_profile_loads() -> None:
    layout = load_layout_profile()

    assert layout.runtime_target == "X-Poker"
    assert layout.table_size == 6
    assert layout.layout_id == "xpoker-windows-10-portrait-v1"
    assert (layout.canonical_width, layout.canonical_height) == (445, 800)
    assert layout.color_format == "BGRA8"
    assert "rule_label" in layout.regions
    assert layout.anchors[0].detector == "horizontal_menu_lines"


def test_layout_rejects_missing_primary_regions() -> None:
    payload = load_layout_profile().model_dump(mode="json")
    del payload["regions"]["pot"]

    with pytest.raises(ValueError, match="missing required regions"):
        LayoutProfile.model_validate(payload)
