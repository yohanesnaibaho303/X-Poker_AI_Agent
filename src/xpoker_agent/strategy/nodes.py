"""Full native-chip strategy node keys and deterministic exact/nearest lookup."""

from __future__ import annotations

import json
from decimal import Decimal
from typing import Literal
from uuid import UUID

from pydantic import Field, field_validator, model_validator

from xpoker_agent.models import CARD_PATTERN, ComboStrategy, Position, Street, StrictModel
from xpoker_agent.ranges.cards import split_combo
from xpoker_agent.ranges.library import validate_strategy_action_key


class StrategyNodeAction(StrictModel):
    actor_position: Position
    street: Street
    action: Literal["fold", "check", "call", "bet", "raise", "all_in"]
    size_chips: Decimal | None = Field(default=None, gt=0)

    @model_validator(mode="after")
    def validate_size(self) -> StrategyNodeAction:
        requires_size = self.action in {"bet", "raise", "all_in"}
        if requires_size != (self.size_chips is not None):
            raise ValueError("bet, raise, and all_in node actions require size_chips")
        return self


class StrategyNodeKey(StrictModel):
    variant: Literal["NLH"] = "NLH"
    format: Literal["cash"] = "cash"
    seats: Literal[9] = 9
    rake_percent: Decimal = Decimal("0")
    native_small_blind: Decimal = Decimal("1")
    native_big_blind: Decimal = Decimal("2")
    street: Street
    hero_position: Position
    opponent_positions: list[Position]
    players_remaining: int = Field(ge=2, le=9)
    effective_stack_chips: Decimal = Field(gt=0)
    pot_chips: Decimal = Field(ge=0)
    board: list[str] = Field(default_factory=list)
    action_sequence: list[StrategyNodeAction] = Field(default_factory=list)
    available_actions: list[str]

    @field_validator("board")
    @classmethod
    def validate_board_cards(cls, board: list[str]) -> list[str]:
        if len(board) != len(set(board)) or any(not CARD_PATTERN.match(card) for card in board):
            raise ValueError("strategy board must contain unique valid physical cards")
        return board

    @field_validator("available_actions")
    @classmethod
    def validate_action_keys(cls, actions: list[str]) -> list[str]:
        if len(actions) != len(set(actions)):
            raise ValueError("strategy node actions must be unique")
        for action in actions:
            validate_strategy_action_key(action)
        return actions

    @model_validator(mode="after")
    def validate_node_scope(self) -> StrategyNodeKey:
        if self.rake_percent != 0:
            raise ValueError("strategy nodes require zero rake")
        if self.native_small_blind != 1 or self.native_big_blind != 2:
            raise ValueError("strategy nodes require native blinds SB 1 and BB 2")
        expected_board = {
            Street.PREFLOP: 0,
            Street.FLOP: 3,
            Street.TURN: 4,
            Street.RIVER: 5,
        }
        if self.street not in expected_board:
            raise ValueError("strategy nodes support preflop through river only")
        if len(self.board) != expected_board[self.street]:
            raise ValueError("strategy node board does not match its street")
        positions = [self.hero_position, *self.opponent_positions]
        if len(positions) != len(set(positions)):
            raise ValueError("strategy node positions must be unique")
        if len(positions) != self.players_remaining:
            raise ValueError("players_remaining must match hero plus opponent positions")
        if any(action.actor_position not in positions for action in self.action_sequence):
            raise ValueError("strategy action actor must remain in the node position set")
        street_order = {Street.PREFLOP: 0, Street.FLOP: 1, Street.TURN: 2, Street.RIVER: 3}
        if any(
            action.street not in street_order
            or street_order[action.street] > street_order[self.street]
            for action in self.action_sequence
        ):
            raise ValueError("strategy action sequence cannot be ahead of the node street")
        if not self.available_actions:
            raise ValueError("strategy node requires at least one available action")
        return self

    def canonical_key(self, *, include_geometry: bool = True) -> str:
        payload = self.model_dump(mode="json")
        if not include_geometry:
            payload.pop("effective_stack_chips")
            payload.pop("pot_chips")
        return json.dumps(payload, sort_keys=True, separators=(",", ":"))


class StrategyNodeArtifact(StrictModel):
    schema_version: Literal["1.0"] = "1.0"
    artifact_id: UUID
    node: StrategyNodeKey
    combos: dict[str, ComboStrategy]
    source: dict[str, object]
    strategy_role: Literal["gto_solution"] = "gto_solution"
    confidence: float = Field(ge=0, le=1)
    assumptions: list[str] = Field(default_factory=list)
    version: str

    @model_validator(mode="after")
    def validate_combos(self) -> StrategyNodeArtifact:
        if not self.combos:
            raise ValueError("strategy node artifact requires exact combinations")
        board = set(self.node.board)
        for combo, strategy in self.combos.items():
            cards = split_combo(combo)
            if board.intersection(cards):
                raise ValueError(f"strategy combo {combo} conflicts with the board")
            if set(strategy.actions) != set(self.node.available_actions):
                raise ValueError(
                    f"strategy combo {combo} actions must match node available actions"
                )
            if strategy.ev_chips and set(strategy.ev_chips) != set(strategy.actions):
                raise ValueError(f"strategy combo {combo} has incomplete EV coverage")
        return self


class StrategyNodeDistance(StrictModel):
    status: Literal["exact", "nearest"]
    requested_stack_chips: Decimal = Field(gt=0)
    matched_stack_chips: Decimal = Field(gt=0)
    stack_mismatch_chips: Decimal = Field(ge=0)
    stack_relative_mismatch: Decimal = Field(ge=0)
    requested_pot_chips: Decimal = Field(ge=0)
    matched_pot_chips: Decimal = Field(ge=0)
    pot_mismatch_chips: Decimal = Field(ge=0)
    pot_relative_mismatch: Decimal = Field(ge=0)
    combined_relative_mismatch: Decimal = Field(ge=0)


class StrategyNodeLookup(StrictModel):
    artifact: StrategyNodeArtifact
    distance: StrategyNodeDistance
    confidence: float = Field(ge=0, le=1)


class StrategyNodeLibrary:
    def __init__(self, artifacts: list[StrategyNodeArtifact]) -> None:
        if not artifacts:
            raise ValueError("strategy node library cannot be empty")
        keys = [artifact.node.canonical_key() for artifact in artifacts]
        if len(keys) != len(set(keys)):
            raise ValueError("strategy node library contains duplicate exact nodes")
        self.artifacts = tuple(artifacts)
        self._by_key = dict(zip(keys, artifacts, strict=True))

    def lookup(self, requested: StrategyNodeKey) -> StrategyNodeLookup:
        exact = self._by_key.get(requested.canonical_key())
        if exact is not None:
            return StrategyNodeLookup(
                artifact=exact,
                distance=_distance(requested, exact.node),
                confidence=exact.confidence,
            )
        compatible = [
            artifact
            for artifact in self.artifacts
            if artifact.node.canonical_key(include_geometry=False)
            == requested.canonical_key(include_geometry=False)
        ]
        if not compatible:
            raise KeyError("no configuration-compatible strategy node")
        selected = min(
            compatible,
            key=lambda artifact: (
                _distance(requested, artifact.node).combined_relative_mismatch,
                artifact.node.effective_stack_chips,
                artifact.node.pot_chips,
            ),
        )
        distance = _distance(requested, selected.node)
        return StrategyNodeLookup(
            artifact=selected,
            distance=distance,
            confidence=selected.confidence
            * max(0.0, 1.0 - float(distance.combined_relative_mismatch)),
        )


def _distance(requested: StrategyNodeKey, matched: StrategyNodeKey) -> StrategyNodeDistance:
    stack_mismatch = abs(requested.effective_stack_chips - matched.effective_stack_chips)
    pot_mismatch = abs(requested.pot_chips - matched.pot_chips)
    stack_relative = stack_mismatch / requested.effective_stack_chips
    pot_denominator = max(requested.pot_chips, Decimal("1"))
    pot_relative = pot_mismatch / pot_denominator
    combined = (stack_relative + pot_relative) / Decimal("2")
    return StrategyNodeDistance(
        status="exact" if stack_mismatch == 0 and pot_mismatch == 0 else "nearest",
        requested_stack_chips=requested.effective_stack_chips,
        matched_stack_chips=matched.effective_stack_chips,
        stack_mismatch_chips=stack_mismatch,
        stack_relative_mismatch=stack_relative,
        requested_pot_chips=requested.pot_chips,
        matched_pot_chips=matched.pot_chips,
        pot_mismatch_chips=pot_mismatch,
        pot_relative_mismatch=pot_relative,
        combined_relative_mismatch=combined,
    )
