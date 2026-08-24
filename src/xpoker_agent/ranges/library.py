"""Strict, provenance-bearing preflop range artifacts and deterministic lookup."""

from __future__ import annotations

import json
from decimal import Decimal
from pathlib import Path
from typing import Literal
from uuid import UUID

from pydantic import Field, field_validator, model_validator

from xpoker_agent.models import (
    ComboStrategy,
    Position,
    StrictModel,
    WeightedRange,
    positions_for_table_size,
)
from xpoker_agent.ranges.cards import split_combo
from xpoker_agent.ranges.stack import STACK_BUCKETS_BB, StackDepthMatch, nearest_stack_bucket


class ObservedRangeAction(StrictModel):
    actor_position: Position
    type: Literal["fold", "check", "call", "bet", "raise", "all_in"]
    size_bb: Decimal | None = Field(default=None, gt=0)

    @model_validator(mode="after")
    def validate_size(self) -> ObservedRangeAction:
        sized = self.type in {"bet", "raise", "all_in"}
        if sized != (self.size_bb is not None):
            raise ValueError(
                "bet, raise, and all_in actions require size_bb; other actions forbid it"
            )
        return self

    def key(self) -> str:
        if self.size_bb is None:
            return self.type
        size = format(self.size_bb.normalize(), "f")
        return f"{self.type}@{size}bb"


class PreflopSpotKey(StrictModel):
    variant: Literal["NLH"] = "NLH"
    format: Literal["cash"] = "cash"
    seats: Literal[6, 9] = 9
    rake_percent: Decimal = Decimal("0")
    default_open_size_bb: Decimal = Decimal("2")
    stack_depth_bb: Decimal
    player_position: Position
    players_remaining: int = Field(ge=2, le=9)
    action_sequence: list[ObservedRangeAction] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_authoritative_configuration(self) -> PreflopSpotKey:
        if self.rake_percent != 0:
            raise ValueError("initial range artifacts require zero rake")
        if self.default_open_size_bb != 2:
            raise ValueError("initial range artifacts require the 2 BB default open size")
        if self.stack_depth_bb <= 0:
            raise ValueError("stack depth must be positive")
        if self.player_position not in positions_for_table_size(self.seats):
            raise ValueError("player position is invalid for the configured table size")
        if self.players_remaining > self.seats:
            raise ValueError("players remaining cannot exceed the configured table size")
        if any(
            action.actor_position not in positions_for_table_size(self.seats)
            for action in self.action_sequence
        ):
            raise ValueError("action sequence contains a position invalid for the table size")
        return self

    def canonical_key(self, *, include_stack: bool = True) -> str:
        parts = [
            self.variant,
            self.format,
            f"{self.seats}max",
            "rake0",
            "open2bb",
            self.player_position.value,
            f"remaining{self.players_remaining}",
        ]
        if include_stack:
            parts.append(f"stack{format(self.stack_depth_bb.normalize(), 'f')}bb")
        parts.extend(action.key() for action in self.action_sequence)
        return "|".join(parts)


class RangeArtifact(StrictModel):
    schema_version: Literal["1.0"] = "1.0"
    artifact_id: UUID
    title: str
    spot: PreflopSpotKey
    combos: dict[str, ComboStrategy]
    source_id: UUID
    source_url: str
    source_license: str
    fact_class: Literal["solver_derived", "validated_manual_chart"]
    validation_status: Literal["validated", "unvalidated"]
    assumptions: list[str] = Field(default_factory=list)
    version: str

    @model_validator(mode="after")
    def validate_artifact_stack_bucket(self) -> RangeArtifact:
        if self.spot.stack_depth_bb not in STACK_BUCKETS_BB:
            raise ValueError(
                f"artifact uses unsupported stack bucket: {self.spot.stack_depth_bb} BB"
            )
        return self

    @field_validator("combos")
    @classmethod
    def validate_combo_keys(cls, combos: dict[str, ComboStrategy]) -> dict[str, ComboStrategy]:
        if not combos:
            raise ValueError("range artifact must contain exact combos")
        for combo in combos:
            split_combo(combo)
        return combos

    def to_weighted_range(self, *, player_ref: str, hand_id: UUID) -> WeightedRange:
        if self.validation_status != "validated":
            raise ValueError("unvalidated range artifacts cannot enter strategy lookup")
        return WeightedRange(
            player_ref=player_ref,
            hand_id=hand_id,
            street="preflop",
            spot_key=self.spot.canonical_key(),
            combos={
                combo: strategy.model_copy(deep=True) for combo, strategy in self.combos.items()
            },
            source={
                "artifact_id": str(self.artifact_id),
                "source_id": str(self.source_id),
                "url": self.source_url,
                "license": self.source_license,
                "fact_class": self.fact_class,
                "configuration": self.spot.model_dump(mode="json"),
            },
            assumptions=list(self.assumptions),
            confidence=1.0,
            version=self.version,
        )


class RangeLookup(StrictModel):
    artifact: RangeArtifact
    stack_match: StackDepthMatch


class RangeLibrary:
    def __init__(self, artifacts: list[RangeArtifact]) -> None:
        self.artifacts = tuple(artifacts)
        keys = [artifact.spot.canonical_key() for artifact in artifacts]
        if len(keys) != len(set(keys)):
            raise ValueError("range library contains duplicate canonical spot keys")
        if any(artifact.validation_status != "validated" for artifact in artifacts):
            raise ValueError("strategy range library accepts only validated artifacts")
        self._by_key = dict(zip(keys, artifacts, strict=True))

    @classmethod
    def load_directory(cls, directory: Path) -> RangeLibrary:
        artifacts = [
            RangeArtifact.model_validate_json(path.read_text(encoding="utf-8"))
            for path in sorted(directory.glob("*.json"))
        ]
        return cls(artifacts)

    def lookup(self, requested: PreflopSpotKey) -> RangeLookup:
        exact = self._by_key.get(requested.canonical_key())
        if exact is not None:
            return RangeLookup(
                artifact=exact,
                stack_match=nearest_stack_bucket(requested.stack_depth_bb),
            )
        compatible = [
            artifact
            for artifact in self.artifacts
            if artifact.spot.canonical_key(include_stack=False)
            == requested.canonical_key(include_stack=False)
        ]
        if not compatible:
            raise KeyError(f"no compatible range artifact for {requested.canonical_key()}")
        selected = min(
            compatible,
            key=lambda artifact: (
                abs(artifact.spot.stack_depth_bb - requested.stack_depth_bb),
                artifact.spot.stack_depth_bb,
            ),
        )
        mismatch = abs(selected.spot.stack_depth_bb - requested.stack_depth_bb)
        stack_match = StackDepthMatch(
            requested_bb=requested.stack_depth_bb,
            status="nearest",
            matched_bb=selected.spot.stack_depth_bb,
            absolute_mismatch_bb=mismatch,
            relative_mismatch=mismatch / requested.stack_depth_bb,
        )
        return RangeLookup(artifact=selected, stack_match=stack_match)


def write_artifact(artifact: RangeArtifact, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(artifact.model_dump(mode="json"), indent=2, sort_keys=True) + "\n"
    path.write_text(payload, encoding="utf-8")
