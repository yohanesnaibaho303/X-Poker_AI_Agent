from xpoker_agent.api import (
    capture_status,
    controller_status,
    game_config,
    health,
    research_assets,
    research_components,
    research_sources,
    simulation_hand,
)
from xpoker_agent.capture.profile import EXAMPLE_PROFILE, load_target_profile


def test_health_reports_disabled_controller() -> None:
    result = health()
    assert result["status"] == "ok"
    assert result["mode"] == "observe"
    assert result["controller_enabled"] is False


def test_game_config_endpoint_uses_authoritative_values() -> None:
    result = game_config()
    assert result["variant"] == "NLH"
    assert result["seats"] == 9
    assert result["default_open_size_bb"] == "2.0"


def test_simulation_endpoint_returns_full_trace() -> None:
    result = simulation_hand()
    assert len(result["events"]) == 14
    assert len(result["states"]) == 15
    assert result["states"][-1]["table_status"] == "hand_complete"


def test_controller_endpoint_is_fail_closed() -> None:
    result = controller_status()
    assert result["enabled"] is False
    assert result["available"] is False


def test_capture_status_is_xpoker_only_and_inactive(monkeypatch) -> None:
    monkeypatch.setattr(
        "xpoker_agent.api.load_target_profile",
        lambda: load_target_profile(EXAMPLE_PROFILE),
    )
    result = capture_status()
    assert result["runtime_target"] == "X-Poker"
    assert result["authorization_enabled"] is False
    assert result["eligible_count"] == 0
    assert result["capture_active"] is False


def test_research_sources_are_inspectable() -> None:
    result = research_sources()
    assert result["count"] == 12
    assert len(result["content_sha256"]) == 64


def test_research_components_expose_verification_gaps() -> None:
    result = research_components()
    assert result["count"] == 12
    assert result["unresolved_critical"] == 0


def test_research_assets_expose_license_review_queue() -> None:
    result = research_assets()
    assert result["count"] == 4
    assert result["pending_review"] == 1
