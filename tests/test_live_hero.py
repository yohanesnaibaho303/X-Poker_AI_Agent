from decimal import Decimal

import pytest

from xpoker_agent.models import Position
from xpoker_agent.monitoring.live_hero import build_live_hero_calculation
from xpoker_agent.simulation import run_simulated_hand
from xpoker_agent.vision.live_observation import LiveObservationService
from xpoker_agent.vision.models import (
    LiveCanonicalHandPrefix,
    SeatStackConsensus,
    TemporalConsensus,
)


def _accepted(value: str, confidence: float = 0.95) -> TemporalConsensus:
    return TemporalConsensus(
        accepted=True,
        value=value,
        confidence=confidence,
        stable_frames=3,
        reason="test consensus",
    )


def test_builds_native_chip_live_hero_calculation() -> None:
    status = LiveObservationService().status().model_copy(
        update={
            "active_seats": [0, 1],
            "detected_hero_seat": 0,
            "hero_seat_confidence": 0.95,
            "detected_hero_position": Position.BTN,
            "recognized_hero_cards": ["As", "Kd"],
            "hero_cards_accepted": True,
            "session_blind_consensus": _accepted("1/2"),
            "pot_consensus": _accepted("6"),
            "hero_control_consensus": _accepted("decision:fold,call,raise::2"),
            "seat_stack_consensus": [
                SeatStackConsensus(
                    seat=0, player_status="seated", consensus=_accepted("100")
                ),
                SeatStackConsensus(
                    seat=1, player_status="seated", consensus=_accepted("80")
                ),
            ],
        }
    )

    result = build_live_hero_calculation(status)

    assert result.ready is True
    assert result.hand_class == "AKo"
    assert result.dealt_player_count == 2
    assert result.range_seat_mismatch == 7
    assert result.hero_stack_chips == Decimal("100")
    assert result.pot_chips == Decimal("6")
    assert result.call_amount_chips == Decimal("2")
    assert result.effective_stack_chips == Decimal("80")
    assert result.required_equity == Decimal("0.25")
    assert result.spr == Decimal("40") / Decimal("3")


def test_withholds_calculation_when_hero_evidence_is_missing() -> None:
    result = build_live_hero_calculation(LiveObservationService().status())

    assert result.ready is False
    assert result.hand_class is None
    assert "hero_seat_not_detected" in result.issues
    assert "hero_cards_not_detected" in result.issues


def test_withholds_recommendation_on_pre_action_surface() -> None:
    status = LiveObservationService().status().model_copy(
        update={"hero_control_consensus": _accepted("pre_action:fold_or_check,call_any:")}
    )

    result = build_live_hero_calculation(status)

    assert result.action_surface == "pre_action"
    assert result.ready is False
    assert "hero_decision_surface_not_active" in result.issues


def test_resolves_live_unopened_preflop_gto_actions() -> None:
    states, events = run_simulated_hand(dealt_players=9)
    state_index, state = next(
        (index, item)
        for index, item in enumerate(states)
        if item.next_to_act_seat == item.hero_seat and item.hero_cards
    )
    prefix = LiveCanonicalHandPrefix(
        hand_epoch=1,
        hand_id=state.hand_id,
        events=events[:state_index],
        state=state,
    )
    status = LiveObservationService().status().model_copy(
        update={
            "active_seats": [6, 7, 8],
            "detected_hero_seat": state.hero_seat,
            "hero_seat_confidence": 0.95,
            "detected_hero_position": state.hero_position,
            "recognized_hero_cards": state.hero_cards,
            "hero_cards_accepted": True,
            "hero_control_consensus": _accepted("decision:fold,call,raise::0"),
            "canonical_hand": prefix,
        }
    )

    result = build_live_hero_calculation(status)

    assert result.recommendation_ready is True
    assert result.strategy_status == "abstracted"
    assert result.strategy_role == "gto_solution"
    assert {action.action for action in result.strategy_actions} == {
        "fold",
        "raise@4chips",
    }
    assert result.recommended_action == "raise@4chips"
    assert result.strategy_source_artifact_id is not None
    assert any("abstracted" in item for item in result.strategy_assumptions)


def test_withholds_live_gto_without_canonical_hand() -> None:
    status = LiveObservationService().status().model_copy(
        update={
            "detected_hero_seat": 0,
            "detected_hero_position": Position.BTN,
            "recognized_hero_cards": ["As", "Kd"],
            "hero_cards_accepted": True,
            "hero_control_consensus": _accepted("decision:fold,call,raise::0"),
        }
    )

    result = build_live_hero_calculation(status)

    assert result.recommendation_ready is False
    assert result.strategy_actions == []
    assert result.recommendation_issues == ["canonical_hand_not_ready"]


def test_maps_short_dealt_ring_to_explicit_lower_confidence_nine_max_abstraction() -> None:
    states, events = run_simulated_hand(dealt_players=8)
    state_index, state = next(
        (index, item)
        for index, item in enumerate(states)
        if item.next_to_act_seat == item.hero_seat and item.hero_cards
    )
    status = LiveObservationService().status().model_copy(
        update={
            "detected_hero_seat": state.hero_seat,
            "detected_hero_position": state.hero_position,
            "recognized_hero_cards": state.hero_cards,
            "hero_cards_accepted": True,
            "hero_control_consensus": _accepted("decision:fold,call,raise::0"),
            "canonical_hand": LiveCanonicalHandPrefix(
                hand_epoch=1,
                hand_id=state.hand_id,
                events=events[:state_index],
                state=state,
            ),
        }
    )

    result = build_live_hero_calculation(status)

    assert result.recommendation_ready is True
    assert result.strategy_confidence == pytest.approx(0.35 * 8 / 9)
    assert any("8 dealt players" in item for item in result.strategy_assumptions)
