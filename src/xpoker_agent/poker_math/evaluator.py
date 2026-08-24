"""Dependency-free exact five-to-seven-card NLH hand evaluator."""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from itertools import combinations

from xpoker_agent.ranges.cards import RANKS_ASCENDING, validate_card

CATEGORY_NAMES = (
    "high_card",
    "one_pair",
    "two_pair",
    "three_of_a_kind",
    "straight",
    "flush",
    "full_house",
    "four_of_a_kind",
    "straight_flush",
)
_RANK_VALUE = {rank: index + 2 for index, rank in enumerate(RANKS_ASCENDING)}


@dataclass(frozen=True, order=True)
class HandRank:
    category: int
    tiebreak: tuple[int, ...]

    @property
    def name(self) -> str:
        return CATEGORY_NAMES[self.category]


def _straight_high(values: set[int]) -> int | None:
    if 14 in values:
        values = {*values, 1}
    ordered = sorted(values)
    run = 1
    best: int | None = None
    for previous, current in zip(ordered, ordered[1:], strict=False):
        run = run + 1 if current == previous + 1 else 1
        if run >= 5:
            best = current
    return best


def evaluate_five(cards: tuple[str, ...] | list[str]) -> HandRank:
    if len(cards) != 5:
        raise ValueError("five-card evaluation requires exactly five cards")
    validated = [validate_card(card) for card in cards]
    if len(validated) != len(set(validated)):
        raise ValueError("physical cards must be unique")
    values = [_RANK_VALUE[card[0]] for card in validated]
    counts = Counter(values)
    grouped = sorted(((count, value) for value, count in counts.items()), reverse=True)
    flush = len({card[1] for card in validated}) == 1
    straight_high = _straight_high(set(values))
    if flush and straight_high is not None:
        return HandRank(8, (straight_high,))
    if grouped[0][0] == 4:
        quad = grouped[0][1]
        kicker = max(value for value in values if value != quad)
        return HandRank(7, (quad, kicker))
    if grouped[0][0] == 3 and grouped[1][0] == 2:
        return HandRank(6, (grouped[0][1], grouped[1][1]))
    if flush:
        return HandRank(5, tuple(sorted(values, reverse=True)))
    if straight_high is not None:
        return HandRank(4, (straight_high,))
    if grouped[0][0] == 3:
        trips = grouped[0][1]
        kickers = sorted((value for value in values if value != trips), reverse=True)
        return HandRank(3, (trips, *kickers))
    pairs = sorted((value for value, count in counts.items() if count == 2), reverse=True)
    if len(pairs) == 2:
        kicker = max(value for value in values if value not in pairs)
        return HandRank(2, (pairs[0], pairs[1], kicker))
    if len(pairs) == 1:
        pair = pairs[0]
        kickers = sorted((value for value in values if value != pair), reverse=True)
        return HandRank(1, (pair, *kickers))
    return HandRank(0, tuple(sorted(values, reverse=True)))


def evaluate_best(cards: tuple[str, ...] | list[str]) -> HandRank:
    if not 5 <= len(cards) <= 7:
        raise ValueError("best-hand evaluation requires five, six, or seven cards")
    validated = tuple(validate_card(card) for card in cards)
    if len(validated) != len(set(validated)):
        raise ValueError("physical cards must be unique")
    return max(evaluate_five(list(selection)) for selection in combinations(validated, 5))

