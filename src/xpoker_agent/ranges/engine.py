"""Deterministic combination-level weighted range operations."""

from __future__ import annotations

from collections.abc import Callable, Iterable
from uuid import UUID

from xpoker_agent.models import ComboStrategy, Street, WeightedRange
from xpoker_agent.ranges.cards import (
    all_combos,
    combo_class,
    split_combo,
    validate_card,
)


def uniform_range(
    *,
    player_ref: str,
    hand_id: UUID,
    street: Street,
    spot_key: str,
    source: dict[str, object],
    version: str,
) -> WeightedRange:
    return WeightedRange(
        player_ref=player_ref,
        hand_id=hand_id,
        street=street,
        spot_key=spot_key,
        combos={combo: ComboStrategy(weight=1.0) for combo in all_combos()},
        source=source,
        confidence=1.0,
        version=version,
    )


def normalized_combo_probabilities(weighted_range: WeightedRange) -> dict[str, float]:
    total = sum(
        weighted_range.combos[combo].weight for combo in sorted(weighted_range.combos)
    )
    if total <= 0:
        raise ValueError("cannot normalize a range with zero total weight")
    return {
        combo: weighted_range.combos[combo].weight / total
        for combo in sorted(weighted_range.combos)
        if weighted_range.combos[combo].weight > 0
    }


def apply_blockers(weighted_range: WeightedRange, blocked_cards: Iterable[str]) -> WeightedRange:
    blockers = tuple(sorted({validate_card(card) for card in blocked_cards}))
    blocker_set = set(blockers)
    combos = {
        combo: strategy.model_copy(deep=True)
        for combo, strategy in weighted_range.combos.items()
        if blocker_set.isdisjoint(split_combo(combo))
    }
    combined_blockers = sorted(set(weighted_range.blocked_cards).union(blockers))
    return weighted_range.model_copy(
        deep=True,
        update={"combos": combos, "blocked_cards": combined_blockers},
    )


def filter_combos(
    weighted_range: WeightedRange,
    predicate: Callable[[str, ComboStrategy], bool],
) -> WeightedRange:
    combos = {
        combo: strategy.model_copy(deep=True)
        for combo, strategy in weighted_range.combos.items()
        if predicate(combo, strategy)
    }
    return weighted_range.model_copy(deep=True, update={"combos": combos})


def condition_on_action(weighted_range: WeightedRange, action: str) -> WeightedRange:
    posterior_mass = {
        combo: strategy.weight * strategy.actions.get(action, 0.0)
        for combo, strategy in weighted_range.combos.items()
    }
    total = sum(posterior_mass[combo] for combo in sorted(posterior_mass))
    if total <= 0:
        raise ValueError(f"action {action!r} has zero probability mass in the range")
    combos = {
        combo: strategy.model_copy(update={"weight": posterior_mass[combo] / total})
        for combo, strategy in weighted_range.combos.items()
        if posterior_mass[combo] > 0
    }
    return weighted_range.model_copy(deep=True, update={"combos": combos})


def aggregate_classes(
    weighted_range: WeightedRange, *, normalize: bool = False
) -> dict[str, float]:
    masses: dict[str, float] = {}
    for combo in sorted(weighted_range.combos):
        hand_class = combo_class(combo)
        masses[hand_class] = masses.get(hand_class, 0.0) + weighted_range.combos[combo].weight
    if normalize:
        total = sum(masses.values())
        if total <= 0:
            raise ValueError("cannot normalize class masses with zero total weight")
        masses = {hand_class: mass / total for hand_class, mass in masses.items()}
    return dict(sorted(masses.items()))


def action_frequency(weighted_range: WeightedRange, action: str) -> float:
    probabilities = normalized_combo_probabilities(weighted_range)
    return sum(
        probabilities[combo] * weighted_range.combos[combo].actions.get(action, 0.0)
        for combo in sorted(probabilities)
    )
