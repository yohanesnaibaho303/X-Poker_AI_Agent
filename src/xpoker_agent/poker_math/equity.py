"""Exact and seeded multiway equity over structured weighted ranges."""

from __future__ import annotations

import random
from itertools import combinations, product

from pydantic import Field, model_validator

from xpoker_agent.models import StrictModel, WeightedRange
from xpoker_agent.poker_math.evaluator import evaluate_best
from xpoker_agent.ranges.cards import DECK, split_combo, validate_card


class EquityResult(StrictModel):
    equity: float = Field(ge=0.0, le=1.0)
    win_probability: float = Field(ge=0.0, le=1.0)
    tie_probability: float = Field(ge=0.0, le=1.0)
    loss_probability: float = Field(ge=0.0, le=1.0)
    trials: int = Field(ge=1)
    exact: bool
    random_seed: int | None = None

    @model_validator(mode="after")
    def validate_probabilities(self) -> EquityResult:
        total = self.win_probability + self.tie_probability + self.loss_probability
        if abs(total - 1.0) > 1e-9:
            raise ValueError("win, tie, and loss probabilities must sum to one")
        if self.exact and self.random_seed is not None:
            raise ValueError("exact equity cannot contain a random seed")
        if not self.exact and self.random_seed is None:
            raise ValueError("sampled equity requires a random seed")
        return self


def _validate_known(hero_combo: str, board: list[str]) -> tuple[tuple[str, str], tuple[str, ...]]:
    hero = split_combo(hero_combo)
    board_cards = tuple(validate_card(card) for card in board)
    if len(board_cards) > 5:
        raise ValueError("NLH board cannot contain more than five cards")
    known = (*hero, *board_cards)
    if len(known) != len(set(known)):
        raise ValueError("hero and board cards must be physically unique")
    return hero, board_cards


def _legal_candidates(
    weighted_range: WeightedRange, blocked: set[str]
) -> tuple[tuple[str, float], ...]:
    candidates = tuple(
        (combo, strategy.weight)
        for combo, strategy in sorted(weighted_range.combos.items())
        if strategy.weight > 0 and blocked.isdisjoint(split_combo(combo))
    )
    if not candidates:
        raise ValueError("opponent range has no legal positive-weight combos")
    return candidates


def _score_showdown(
    hero: tuple[str, str], opponents: list[tuple[str, str]], board: tuple[str, ...]
) -> tuple[float, bool, bool]:
    ranks = [evaluate_best([*hero, *board])]
    ranks.extend(evaluate_best([*opponent, *board]) for opponent in opponents)
    best = max(ranks)
    winners = [index for index, rank in enumerate(ranks) if rank == best]
    hero_wins = 0 in winners
    share = 1.0 / len(winners) if hero_wins else 0.0
    return share, hero_wins and len(winners) == 1, hero_wins and len(winners) > 1


def exact_equity(
    hero_combo: str,
    opponent_ranges: list[WeightedRange],
    board: list[str],
    *,
    maximum_states: int = 2_000_000,
) -> EquityResult:
    if not opponent_ranges:
        raise ValueError("equity requires at least one opponent range")
    if maximum_states < 1:
        raise ValueError("maximum_states must be positive")
    hero, board_cards = _validate_known(hero_combo, board)
    initially_blocked = set((*hero, *board_cards))
    candidate_sets = [
        _legal_candidates(weighted_range, initially_blocked)
        for weighted_range in opponent_ranges
    ]
    missing_board = 5 - len(board_cards)
    weighted_trials = 0.0
    equity_mass = 0.0
    win_mass = 0.0
    tie_mass = 0.0
    loss_mass = 0.0
    states = 0
    for opponent_selection in product(*candidate_sets):
        opponent_cards = [split_combo(combo) for combo, _ in opponent_selection]
        selected_cards = [card for combo in opponent_cards for card in combo]
        if len(selected_cards) != len(set(selected_cards)) or initially_blocked.intersection(
            selected_cards
        ):
            continue
        selection_weight = 1.0
        for _, weight in opponent_selection:
            selection_weight *= weight
        remaining = [
            card
            for card in DECK
            if card not in initially_blocked and card not in selected_cards
        ]
        for runout in combinations(remaining, missing_board):
            states += 1
            if states > maximum_states:
                raise ValueError("exact equity state count exceeds configured maximum")
            weight = selection_weight
            share, outright, tied = _score_showdown(
                hero, opponent_cards, (*board_cards, *runout)
            )
            weighted_trials += weight
            equity_mass += weight * share
            win_mass += weight * int(outright)
            tie_mass += weight * int(tied)
            loss_mass += weight * int(not outright and not tied)
    if weighted_trials <= 0 or states == 0:
        raise ValueError("no legal exact equity states remain")
    return EquityResult(
        equity=equity_mass / weighted_trials,
        win_probability=win_mass / weighted_trials,
        tie_probability=tie_mass / weighted_trials,
        loss_probability=loss_mass / weighted_trials,
        trials=states,
        exact=True,
    )


def _weighted_choice(
    candidates: tuple[tuple[str, float], ...], rng: random.Random
) -> str:
    total = sum(weight for _, weight in candidates)
    target = rng.random() * total
    cumulative = 0.0
    for combo, weight in candidates:
        cumulative += weight
        if target < cumulative:
            return combo
    return candidates[-1][0]


def monte_carlo_equity(
    hero_combo: str,
    opponent_ranges: list[WeightedRange],
    board: list[str],
    *,
    trials: int,
    random_seed: int,
) -> EquityResult:
    if not opponent_ranges:
        raise ValueError("equity requires at least one opponent range")
    if trials < 1:
        raise ValueError("trials must be positive")
    hero, board_cards = _validate_known(hero_combo, board)
    rng = random.Random(random_seed)
    equity_mass = 0.0
    wins = ties = losses = 0
    for _ in range(trials):
        blocked = set((*hero, *board_cards))
        opponents: list[tuple[str, str]] = []
        for weighted_range in opponent_ranges:
            combo = _weighted_choice(_legal_candidates(weighted_range, blocked), rng)
            cards = split_combo(combo)
            opponents.append(cards)
            blocked.update(cards)
        remaining = [card for card in DECK if card not in blocked]
        runout = rng.sample(remaining, 5 - len(board_cards))
        share, outright, tied = _score_showdown(hero, opponents, (*board_cards, *runout))
        equity_mass += share
        wins += int(outright)
        ties += int(tied)
        losses += int(not outright and not tied)
    return EquityResult(
        equity=equity_mass / trials,
        win_probability=wins / trials,
        tie_probability=ties / trials,
        loss_probability=losses / trials,
        trials=trials,
        exact=False,
        random_seed=random_seed,
    )
