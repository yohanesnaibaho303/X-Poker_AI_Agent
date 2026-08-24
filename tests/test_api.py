from xpoker_agent.api import (
    capture_status,
    controller_status,
    game_config,
    health,
    preview_session_setup,
    research_assets,
    research_components,
    research_sources,
    simulation_hand,
    supported_game_configs,
)
from xpoker_agent.capture.profile import EXAMPLE_PROFILE, load_target_profile
from xpoker_agent.models import SessionSetupRequest
from xpoker_agent.simulation import run_simulated_hand


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

    six_max = game_config(6)
    assert six_max["seats"] == 6
    assert six_max["positions"] == ["UTG", "HJ", "CO", "BTN", "SB", "BB"]


def test_supported_game_configs_are_explicit_and_isolated() -> None:
    result = supported_game_configs()

    assert result["supported_table_sizes"] == [6, 9]
    assert [config["seats"] for config in result["configurations"]] == [6, 9]


def test_session_preview_accepts_table_size_and_chip_notation() -> None:
    result = preview_session_setup(
        SessionSetupRequest(
            table_size=6,
            chip_display_mode="native",
            stack_input="200000",
            big_blind_native_chips="2000",
        )
    )

    assert result["table_size"] == 6
    assert result["stack"]["display_mode"] == "native"
    assert result["stack"]["display_text"] == "200K"
    assert result["stack"]["exact_native_chips"] == "200000"
    assert result["stack"]["amount_bb"] == "100"
    assert result["ready_for_strategy"] is True


def test_simulation_endpoint_returns_full_trace() -> None:
    result = simulation_hand()
    assert len(result["events"]) == 14
    assert len(result["states"]) == 15
    assert result["states"][-1]["table_status"] == "hand_complete"


def test_six_max_simulation_uses_six_canonical_seat_slots() -> None:
    states, events = run_simulated_hand(6)

    assert len(states[0].seats) == 6
    assert states[-1].table_status == "hand_complete"
    assert len(events) == 14


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
    assert result["count"] == 16
    assert len(result["content_sha256"]) == 64


def test_research_components_expose_verification_gaps() -> None:
    result = research_components()
    assert result["count"] == 12
    assert result["unresolved_critical"] == 0


def test_research_assets_expose_license_review_queue() -> None:
    result = research_assets()
    assert result["count"] == 4
    assert result["pending_review"] == 1
