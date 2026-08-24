from xpoker_agent.vision.action_order import validate_action_order
from xpoker_agent.vision.models import DerivedActionCandidate


def _action(
    *,
    event: str,
    frame: int,
    seat: int,
    street: str,
    action: str,
    dealer: int | None = 0,
    active: list[int] | None = None,
) -> DerivedActionCandidate:
    return DerivedActionCandidate(
        event_id=event * 64,
        hand_epoch=2,
        frame_sequence=frame,
        seat=seat,
        street=street,
        action=action,
        confidence=0.95,
        dealer_seat=dealer,
        active_seats=list(range(9)) if active is None else active,
    )


def test_gap_free_preflop_actions_form_a_clockwise_prefix() -> None:
    result = validate_action_order(
        [
            _action(event="a", frame=10, seat=3, street="preflop", action="call"),
            _action(event="b", frame=12, seat=4, street="preflop", action="call"),
            _action(event="c", frame=14, seat=5, street="preflop", action="fold"),
        ],
        table_size=9,
    )[0]

    assert result.status == "prefix_consistent"
    assert result.expected_start_seat == 3
    assert result.expected_next_seat == 6
    assert result.canonical_event_accepted is False


def test_missing_intervening_action_stays_pending_without_inference() -> None:
    result = validate_action_order(
        [_action(event="a", frame=10, seat=3, street="flop", action="bet")],
        table_size=9,
    )[0]

    assert result.status == "pending"
    assert result.expected_start_seat == 1
    assert result.issues == ["unobserved_intervening_action_expected_seat_1_before_3"]


def test_changed_table_context_is_inconsistent() -> None:
    result = validate_action_order(
        [
            _action(event="a", frame=10, seat=1, street="flop", action="check"),
            _action(
                event="b",
                frame=12,
                seat=2,
                street="flop",
                action="bet",
                active=list(range(8)),
            ),
        ],
        table_size=9,
    )[0]

    assert result.status == "inconsistent"
    assert result.issues == ["dealer_or_active_seat_context_changed_within_street"]
