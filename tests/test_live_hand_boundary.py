from xpoker_agent.vision.hand_boundary import validate_live_hand_boundary


def test_live_boundary_requires_next_dealt_dealer_with_unchanged_ring() -> None:
    result = validate_live_hand_boundary(
        hand_epoch=4,
        table_size=9,
        previous_dealer_seat=6,
        current_dealer_seat=0,
        previous_active_seats=[0, 1, 2, 3, 6],
        current_active_seats=[0, 1, 2, 3, 6],
    )

    assert result.status == "validated"
    assert result.expected_dealer_seat == 0
    assert result.issues == []
    assert result.canonical_event_accepted is False


def test_live_boundary_waits_while_old_dealer_marker_remains() -> None:
    result = validate_live_hand_boundary(
        hand_epoch=4,
        table_size=9,
        previous_dealer_seat=6,
        current_dealer_seat=6,
        previous_active_seats=[0, 1, 2, 3, 6],
        current_active_seats=[0, 1, 2, 3, 6],
    )

    assert result.status == "pending"
    assert result.issues == ["dealer_not_advanced_yet"]


def test_live_boundary_rejects_changed_active_ring() -> None:
    result = validate_live_hand_boundary(
        hand_epoch=4,
        table_size=9,
        previous_dealer_seat=6,
        current_dealer_seat=0,
        previous_active_seats=[0, 1, 2, 3, 6],
        current_active_seats=[0, 1, 2, 6],
    )

    assert result.status == "rejected"
    assert "active_seat_set_changed" in result.issues
