"""Comprehensive fail-closed regression tests covering all safety and integrity invariants."""

import pytest
from pydantic import ValidationError

from xpoker_agent.vision.cards import (
    classify_board_geometry,
    validate_unique_cards,
)
from xpoker_agent.vision.controls import parse_hero_action_controls
from xpoker_agent.vision.models import (
    CardRecognition,
    CardSlotCandidate,
    PixelBox,
    SeatOccupancyObservation,
)
from xpoker_agent.vision.numbers import parse_chip_amount
from xpoker_agent.vision.panels import parse_seat_panel
from xpoker_agent.vision.pots import parse_pot_label
from xpoker_agent.vision.rules import classify_rule_label

# ---------------------------------------------------------------------------
# 1. Missing and Duplicate Cards
# ---------------------------------------------------------------------------


def test_duplicate_physical_cards_fail_closed() -> None:
    cards = [
        CardRecognition(card="Ah", confidence=0.99),
        CardRecognition(card="Ks", confidence=0.98),
        CardRecognition(card="Ah", confidence=0.97),
    ]
    duplicates = validate_unique_cards(cards)
    assert duplicates == ["duplicate_physical_card:Ah"]


def test_cross_location_duplicate_cards_fail_closed() -> None:
    hero = [
        CardRecognition(card="Ah", confidence=0.99),
        CardRecognition(card="Kd", confidence=0.99),
    ]
    board = [
        CardRecognition(card="Ah", confidence=0.99),
        CardRecognition(card="Qc", confidence=0.98),
        CardRecognition(card="Js", confidence=0.97),
    ]
    duplicates = validate_unique_cards(hero + board)
    assert duplicates == ["duplicate_physical_card:Ah"]


def test_quadruple_duplicate_cards_fail_closed() -> None:
    cards = [
        CardRecognition(card="Ts", confidence=0.95),
        CardRecognition(card="Ts", confidence=0.95),
        CardRecognition(card="Ts", confidence=0.95),
        CardRecognition(card="Ts", confidence=0.95),
    ]
    duplicates = validate_unique_cards(cards)
    assert duplicates == ["duplicate_physical_card:Ts"]


def test_card_recognition_rejects_malformed_card_codes() -> None:
    invalid_codes = ["", "A", "10s", "ah", "AS", "H7", "Kx", "1s", "0d", "Jz"]
    for code in invalid_codes:
        with pytest.raises(ValidationError):
            CardRecognition(card=code, confidence=0.9)


def test_board_geometry_rejects_row_with_more_than_five_cards() -> None:
    candidates = [
        CardSlotCandidate(
            box=PixelBox(left=i * 30, top=10, right=i * 30 + 25, bottom=45),
            confidence=0.9,
            row_index=0,
        )
        for i in range(6)
    ]
    result = classify_board_geometry(candidates)
    assert result.unsupported is True
    assert "too_many_board_cards" in result.reasons


def test_board_geometry_rejects_ambiguous_scattered_slots() -> None:
    candidates = [
        CardSlotCandidate(
            box=PixelBox(left=10, top=10, right=35, bottom=45),
            confidence=0.9,
            row_index=0,
        ),
    ]
    result = classify_board_geometry(candidates)
    assert result.unsupported is True
    assert "ambiguous_board_geometry" in result.reasons


# ---------------------------------------------------------------------------
# 2. Corrupt and Ambiguous Amounts
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "corrupt_text",
    [
        "100K",
        "1.5M",
        "2B",
        "1,00",
        "1,000,00",
        "1.2.3",
        "-50",
        "5O0",  # letter O instead of 0
        "$100",
        "100 chips",
        "NaN",
        "Inf",
        "",
        "   ",
        "10.00.00",
        "1,23,456",
    ],
)
def test_chip_amount_parser_fails_closed_on_corrupt_amounts(corrupt_text: str) -> None:
    with pytest.raises(ValueError):
        parse_chip_amount(corrupt_text, confidence=0.5)


@pytest.mark.parametrize(
    "corrupt_pot",
    [
        "POT 4K",
        "POT 1.5M",
        "POT -20",
        "POT 1,00",
        "POT",
        "POT O",
        "POT ABC",
        "MAIN POT 50K",
        "POT $500",
    ],
)
def test_pot_label_parser_fails_closed_on_corrupt_pots(corrupt_pot: str) -> None:
    result = parse_pot_label(corrupt_pot)
    assert result.value_native is None
    assert result.confidence == 0.0


@pytest.mark.parametrize(
    "corrupt_panel",
    [
        "Player1\n100K",
        "User\n$500",
        "Hero\n1.2.3",
        "Fish\n-100",
        "Empty",
        "",
    ],
)
def test_seat_panel_parser_fails_closed_on_corrupt_stack(corrupt_panel: str) -> None:
    occ = SeatOccupancyObservation(
        seat=0,
        status="occupied",
        confidence=0.9,
        dark_panel_fraction=0.5,
        plus_horizontal_pixels=0,
        plus_vertical_pixels=0,
    )
    result = parse_seat_panel(occ, corrupt_panel)
    assert result.accepted is False
    assert result.stack_native is None
    assert result.status == "ambiguous"


# ---------------------------------------------------------------------------
# 3. Conflicting and Malformed Action Controls
# ---------------------------------------------------------------------------


def test_conflicting_check_and_call_fails_closed() -> None:
    result = parse_hero_action_controls("Check Call 10 Fold")
    assert result.mode == "ambiguous"
    assert "conflicting action controls" in result.reason


def test_conflicting_bet_and_raise_fails_closed() -> None:
    result = parse_hero_action_controls("Bet 10 Raise 20 Fold")
    assert result.mode == "ambiguous"
    assert "conflicting action controls" in result.reason


def test_conflicting_check_and_fold_without_fc_toggle_fails_closed() -> None:
    result = parse_hero_action_controls("Check Fold")
    assert result.mode == "ambiguous"
    assert "conflicting action controls" in result.reason


@pytest.mark.parametrize(
    "corrupt_call_text",
    [
        "Fold Call 4K Raise",
        "Fold Call -10 Raise",
        "Fold Call 1,00 Raise",
        "Fold Call 10.5.2 Raise",
        "Fold Call XYZ Raise",
    ],
)
def test_corrupt_call_amount_in_decision_controls_fails_closed(corrupt_call_text: str) -> None:
    result = parse_hero_action_controls(corrupt_call_text)
    assert result.mode == "ambiguous"
    assert result.call_amount_native is None


def test_unrecognized_action_surface_text_fails_closed() -> None:
    result = parse_hero_action_controls("Click Here To Win Free Money")
    assert result.mode == "ambiguous"
    assert result.confidence == 0.0


# ---------------------------------------------------------------------------
# 4. Unsupported Overlays and Hand Modes
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "unsupported_rule",
    [
        "Double Board Bomb Pot: After 2 hands Blinds: 1/2",
        "Omaha Pot Limit Blinds: 1/2",
        "PLO5 Blinds: 1/2",
        "Short Deck Holdem Blinds: 1/2",
        "Pineapple Blinds: 1/2",
        "Tournament Level 1 Blinds: 100/200",
        "Blinds: 2/4",  # Non-authoritative blinds
        "Blinds: 5/10",
        "Blinds: 10/20",
        "Bomb Pot: Every 5 hands (2-4) Blinds: 2/4",  # Valid Bomb Pot schedule but wrong blinds
        "Bomb Pot(-4) Blinds: 1/2",  # Negative forced contribution
        "Bomb Pot(4K) Blinds: 1/2",  # Compact contribution format
        "Unrecognized Text Blah Blah",
        "",
    ],
)
def test_unsupported_or_corrupt_game_modes_fail_closed(unsupported_rule: str) -> None:
    result = classify_rule_label(unsupported_rule)
    is_valid_hand = (
        (result.supported_standard_nlh or result.supported_single_board_bomb_pot)
        and result.small_blind_native == 1
        and result.big_blind_native == 2
    )
    assert is_valid_hand is False


def test_multiple_board_rows_fail_closed_geometry() -> None:
    row0 = [
        CardSlotCandidate(
            box=PixelBox(left=i * 30, top=20, right=i * 30 + 25, bottom=55),
            confidence=0.9,
            row_index=0,
        )
        for i in range(3)
    ]
    row1 = [
        CardSlotCandidate(
            box=PixelBox(left=i * 30, top=70, right=i * 30 + 25, bottom=105),
            confidence=0.9,
            row_index=1,
        )
        for i in range(3)
    ]
    result = classify_board_geometry(row0 + row1)
    assert result.unsupported is True
    assert "multiple_board_rows" in result.reasons
    assert result.board_rows == 2
