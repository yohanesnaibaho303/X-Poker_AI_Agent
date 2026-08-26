"""Deterministic 13-by-13 projection of exact-combo weighted ranges."""

from __future__ import annotations

from pydantic import Field, model_validator

from xpoker_agent.models import StrictModel, WeightedRange
from xpoker_agent.ranges.cards import (
    RANKS_DESCENDING,
    expand_hand_class,
    matrix_coordinates,
    split_combo,
)


class RangeMatrixCell(StrictModel):
    hand_class: str
    row: int = Field(ge=0, le=12)
    column: int = Field(ge=0, le=12)
    possible_combos: int = Field(ge=0, le=12)
    included_combos: int = Field(ge=0, le=12)
    combo_weight: float = Field(ge=0.0)
    inclusion_frequency: float = Field(ge=0.0, le=1.0)
    action_mix: dict[str, float] = Field(default_factory=dict)
    unassigned_action_frequency: float = Field(ge=0.0, le=1.0)
    equity: float | None = Field(default=None, ge=0.0, le=1.0)
    ev_chips: dict[str, float] = Field(default_factory=dict)

    @model_validator(mode="after")
    def validate_projection(self) -> RangeMatrixCell:
        if self.included_combos > self.possible_combos:
            raise ValueError("included combos cannot exceed physically possible combos")
        action_total = sum(self.action_mix.values()) + self.unassigned_action_frequency
        if self.combo_weight > 0 and abs(action_total - 1.0) > 1e-9:
            raise ValueError("assigned and unassigned action frequencies must sum to one")
        return self


class RangeMatrix(StrictModel):
    player_ref: str
    spot_key: str
    ranks: list[str]
    blocked_cards: list[str]
    cells: list[RangeMatrixCell]
    source: dict[str, object]
    confidence: float = Field(ge=0.0, le=1.0)
    version: str

    @model_validator(mode="after")
    def validate_grid(self) -> RangeMatrix:
        coordinates = {(cell.row, cell.column) for cell in self.cells}
        if len(self.cells) != 169 or len(coordinates) != 169:
            raise ValueError("range matrix must contain every cell in a unique 13-by-13 grid")
        return self


def project_range_matrix(weighted_range: WeightedRange) -> RangeMatrix:
    """Project exact combos without discarding blockers, mixed actions, equity, or EV."""
    blocked = set(weighted_range.blocked_cards)
    cells: list[RangeMatrixCell] = []
    for row in range(13):
        for column in range(13):
            hand_class = _class_at(row, column)
            possible = [
                combo
                for combo in expand_hand_class(hand_class)
                if blocked.isdisjoint(split_combo(combo))
            ]
            strategies = [
                weighted_range.combos[combo]
                for combo in possible
                if combo in weighted_range.combos and weighted_range.combos[combo].weight > 0
            ]
            combo_weight = sum(strategy.weight for strategy in strategies)
            actions = sorted({action for strategy in strategies for action in strategy.actions})
            action_mix = {
                action: sum(
                    strategy.weight * strategy.actions.get(action, 0.0) for strategy in strategies
                )
                / combo_weight
                for action in actions
            }
            assigned = sum(action_mix.values())
            equity_mass = sum(
                strategy.weight * strategy.equity
                for strategy in strategies
                if strategy.equity is not None
            )
            equity_weight = sum(
                strategy.weight for strategy in strategies if strategy.equity is not None
            )
            ev_actions = sorted({action for strategy in strategies for action in strategy.ev_chips})
            ev_chips = {
                action: sum(
                    strategy.weight * strategy.ev_chips[action]
                    for strategy in strategies
                    if action in strategy.ev_chips
                )
                / sum(strategy.weight for strategy in strategies if action in strategy.ev_chips)
                for action in ev_actions
            }
            cells.append(
                RangeMatrixCell(
                    hand_class=hand_class,
                    row=row,
                    column=column,
                    possible_combos=len(possible),
                    included_combos=len(strategies),
                    combo_weight=combo_weight,
                    inclusion_frequency=(combo_weight / len(possible) if possible else 0.0),
                    action_mix=action_mix,
                    unassigned_action_frequency=(1.0 - assigned if combo_weight else 0.0),
                    equity=(equity_mass / equity_weight if equity_weight else None),
                    ev_chips=ev_chips,
                )
            )
    return RangeMatrix(
        player_ref=weighted_range.player_ref,
        spot_key=weighted_range.spot_key,
        ranks=list(RANKS_DESCENDING),
        blocked_cards=list(weighted_range.blocked_cards),
        cells=cells,
        source=dict(weighted_range.source),
        confidence=weighted_range.confidence,
        version=weighted_range.version,
    )


def _class_at(row: int, column: int) -> str:
    row_rank = RANKS_DESCENDING[row]
    column_rank = RANKS_DESCENDING[column]
    if row == column:
        hand_class = row_rank * 2
    elif row < column:
        hand_class = f"{row_rank}{column_rank}s"
    else:
        hand_class = f"{column_rank}{row_rank}o"
    if matrix_coordinates(hand_class) != (row, column):
        raise AssertionError("hand-class matrix convention is inconsistent")
    return hand_class
