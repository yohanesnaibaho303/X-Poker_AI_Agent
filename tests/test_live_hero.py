from decimal import Decimal

from xpoker_agent.models import Position
from xpoker_agent.monitoring.live_hero import build_live_hero_calculation
from xpoker_agent.vision.live_observation import LiveObservationService
from xpoker_agent.vision.models import SeatStackConsensus, TemporalConsensus


def _accepted(value: str, confidence: float = 0.95) -> TemporalConsensus:
    return TemporalConsensus(
        accepted=True,
        value=value,
        confidence=confidence,
        stable_frames=3,
        reason="test consensus",
    )


def test_builds_bb_normalized_live_hero_calculation() -> None:
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
    assert result.hero_stack_bb == Decimal("50")
    assert result.pot_bb == Decimal("3")
    assert result.call_amount_bb == Decimal("1")
    assert result.effective_stack_bb == Decimal("40")
    assert result.required_equity == Decimal("0.25")
    assert result.spr == Decimal("40") / Decimal("3")


def test_withholds_calculation_when_hero_evidence_is_missing() -> None:
    result = build_live_hero_calculation(LiveObservationService().status())

    assert result.ready is False
    assert result.hand_class is None
    assert "hero_seat_not_detected" in result.issues
    assert "hero_cards_not_detected" in result.issues
