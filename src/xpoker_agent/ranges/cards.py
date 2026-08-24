"""Canonical NLH cards, 1,326 exact combinations, and 169 preflop classes."""

from __future__ import annotations

from functools import lru_cache
from itertools import combinations

RANKS_ASCENDING = "23456789TJQKA"
RANKS_DESCENDING = RANKS_ASCENDING[::-1]
SUITS_ASCENDING = "cdhs"
DECK = tuple(f"{rank}{suit}" for rank in RANKS_ASCENDING for suit in SUITS_ASCENDING)
_CARD_INDEX = {card: index for index, card in enumerate(DECK)}


def validate_card(card: str) -> str:
    if card not in _CARD_INDEX:
        raise ValueError(f"invalid card code: {card!r}")
    return card


def canonical_combo(card_a: str, card_b: str) -> str:
    validate_card(card_a)
    validate_card(card_b)
    if card_a == card_b:
        raise ValueError("an exact combo requires two distinct physical cards")
    high, low = sorted((card_a, card_b), key=_CARD_INDEX.__getitem__, reverse=True)
    return high + low


def split_combo(combo: str) -> tuple[str, str]:
    if len(combo) != 4:
        raise ValueError(f"exact combo must contain two two-character cards: {combo!r}")
    card_a, card_b = combo[:2], combo[2:]
    if canonical_combo(card_a, card_b) != combo:
        raise ValueError(f"exact combo is not canonical: {combo!r}")
    return card_a, card_b


@lru_cache(maxsize=1)
def all_combos() -> tuple[str, ...]:
    return tuple(
        sorted(
            (canonical_combo(card_a, card_b) for card_a, card_b in combinations(DECK, 2)),
            key=lambda combo: (
                _CARD_INDEX[combo[:2]],
                _CARD_INDEX[combo[2:]],
            ),
            reverse=True,
        )
    )


def combo_class(combo: str) -> str:
    card_a, card_b = split_combo(combo)
    rank_a, suit_a = card_a
    rank_b, suit_b = card_b
    if rank_a == rank_b:
        return rank_a * 2
    return f"{rank_a}{rank_b}{'s' if suit_a == suit_b else 'o'}"


def validate_hand_class(hand_class: str) -> str:
    if len(hand_class) == 2:
        if hand_class[0] != hand_class[1] or hand_class[0] not in RANKS_ASCENDING:
            raise ValueError(f"invalid pair class: {hand_class!r}")
        return hand_class
    if len(hand_class) != 3 or hand_class[2] not in "so":
        raise ValueError(f"invalid non-pair class: {hand_class!r}")
    high, low = hand_class[:2]
    if high not in RANKS_ASCENDING or low not in RANKS_ASCENDING or high == low:
        raise ValueError(f"invalid non-pair class: {hand_class!r}")
    if RANKS_ASCENDING.index(high) < RANKS_ASCENDING.index(low):
        raise ValueError(f"hand class ranks must be high-to-low: {hand_class!r}")
    return hand_class


@lru_cache(maxsize=1)
def all_hand_classes() -> tuple[str, ...]:
    classes: list[str] = []
    for row_index, row_rank in enumerate(RANKS_DESCENDING):
        for column_index, column_rank in enumerate(RANKS_DESCENDING):
            if row_index == column_index:
                classes.append(row_rank * 2)
            elif row_index < column_index:
                classes.append(f"{row_rank}{column_rank}s")
            else:
                classes.append(f"{column_rank}{row_rank}o")
    return tuple(classes)


@lru_cache(maxsize=169)
def expand_hand_class(hand_class: str) -> tuple[str, ...]:
    validate_hand_class(hand_class)
    return tuple(combo for combo in all_combos() if combo_class(combo) == hand_class)


def matrix_coordinates(hand_class: str) -> tuple[int, int]:
    validate_hand_class(hand_class)
    if len(hand_class) == 2:
        index = RANKS_DESCENDING.index(hand_class[0])
        return index, index
    high_index = RANKS_DESCENDING.index(hand_class[0])
    low_index = RANKS_DESCENDING.index(hand_class[1])
    return (high_index, low_index) if hand_class[2] == "s" else (low_index, high_index)

