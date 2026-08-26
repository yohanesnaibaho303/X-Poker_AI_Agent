"""Strict, provenance-bearing preflop range artifacts and deterministic lookup."""

from __future__ import annotations

import hashlib
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
from xpoker_agent.ranges.stack import STACK_BUCKETS_CHIPS, StackDepthMatch, nearest_stack_bucket

PROJECT_ROOT = Path(__file__).resolve().parents[3]


class ObservedRangeAction(StrictModel):
    actor_position: Position
    type: Literal["fold", "check", "call", "bet", "raise", "all_in"]
    size_chips: Decimal | None = Field(default=None, gt=0)

    @model_validator(mode="after")
    def validate_size(self) -> ObservedRangeAction:
        sized = self.type in {"bet", "raise", "all_in"}
        if sized != (self.size_chips is not None):
            raise ValueError(
                "bet, raise, and all_in actions require size_chips; other actions forbid it"
            )
        return self

    def key(self) -> str:
        if self.size_chips is None:
            return self.type
        size = format(self.size_chips.normalize(), "f")
        return f"{self.type}@{size}chips"


class PreflopSpotKey(StrictModel):
    variant: Literal["NLH"] = "NLH"
    format: Literal["cash"] = "cash"
    seats: Literal[9] = 9
    rake_percent: Decimal = Decimal("0")
    native_small_blind: Decimal = Decimal("1")
    native_big_blind: Decimal = Decimal("2")
    stack_depth_chips: Decimal
    player_position: Position
    players_remaining: int = Field(ge=2, le=9)
    action_sequence: list[ObservedRangeAction] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_authoritative_configuration(self) -> PreflopSpotKey:
        if self.rake_percent != 0:
            raise ValueError("initial range artifacts require zero rake")
        if self.native_small_blind != 1 or self.native_big_blind != 2:
            raise ValueError("range artifacts require native blinds SB 1 and BB 2")
        if self.stack_depth_chips <= 0:
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
        if any(action.type == "bet" for action in self.action_sequence):
            raise ValueError("preflop voluntary aggression must use raise, not bet")
        previous_voluntary_action = False
        for action in self.action_sequence:
            if (
                action.type == "raise"
                and not previous_voluntary_action
                and action.size_chips is not None
                and action.size_chips <= self.native_big_blind
            ):
                raise ValueError(
                    "an opening raise must exceed the 2-chip forced big blind"
                )
            if action.type != "fold":
                previous_voluntary_action = True
        return self

    def canonical_key(self, *, include_stack: bool = True) -> str:
        parts = [
            self.variant,
            self.format,
            f"{self.seats}max",
            "rake0",
            "blinds1-2chips",
            self.player_position.value,
            f"remaining{self.players_remaining}",
        ]
        if include_stack:
            parts.append(f"stack{format(self.stack_depth_chips.normalize(), 'f')}chips")
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
    strategy_role: Literal["reference_prior", "gto_solution"]
    validation_status: Literal["validated", "unvalidated"]
    confidence: float = Field(ge=0, le=1)
    source_commit: str | None = None
    source_content_sha256: str | None = Field(default=None, min_length=64, max_length=64)
    assumptions: list[str] = Field(default_factory=list)
    version: str

    @model_validator(mode="after")
    def validate_artifact_stack_bucket(self) -> RangeArtifact:
        if self.spot.stack_depth_chips not in STACK_BUCKETS_CHIPS:
            raise ValueError(
                f"artifact uses unsupported native-chip stack bucket: {self.spot.stack_depth_chips}"
            )
        if self.strategy_role == "gto_solution" and self.fact_class != "solver_derived":
            raise ValueError("GTO solution artifacts must be solver-derived")
        return self

    @field_validator("combos")
    @classmethod
    def validate_combo_keys(cls, combos: dict[str, ComboStrategy]) -> dict[str, ComboStrategy]:
        if not combos:
            raise ValueError("range artifact must contain exact combos")
        for combo, strategy in combos.items():
            split_combo(combo)
            if not set(strategy.ev_chips).issubset(strategy.actions):
                raise ValueError(f"combo {combo} has EV for an unavailable action")
            for action in set(strategy.actions) | set(strategy.ev_chips):
                if "@" not in action:
                    if action in {"bet", "raise"}:
                        raise ValueError(
                            f"combo {combo} monetary action must include an exact native-chip size"
                        )
                    continue
                action_type, size_token = action.split("@", maxsplit=1)
                if action_type not in {"bet", "raise", "all_in"} or not size_token.endswith(
                    "chips"
                ):
                    raise ValueError(
                        f"combo {combo} action sizing must use action@<amount>chips"
                    )
                try:
                    size = Decimal(size_token.removesuffix("chips"))
                except ArithmeticError as error:
                    raise ValueError(
                        f"combo {combo} action has an invalid native-chip amount"
                    ) from error
                if not size.is_finite() or size <= 0:
                    raise ValueError(
                        f"combo {combo} action must have a positive finite native-chip amount"
                    )
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
                "strategy_role": self.strategy_role,
                "source_commit": self.source_commit,
                "source_content_sha256": self.source_content_sha256,
                "configuration": self.spot.model_dump(mode="json"),
            },
            assumptions=list(self.assumptions),
            confidence=self.confidence,
            version=self.version,
        )


class RangeLookup(StrictModel):
    artifact: RangeArtifact
    stack_match: StackDepthMatch


class RangeManifestEntry(StrictModel):
    artifact_id: UUID
    path: str
    content_sha256: str = Field(min_length=64, max_length=64)
    position: Position
    strategy_role: Literal["reference_prior", "gto_solution"]
    confidence: float = Field(ge=0, le=1)


class RangeLibraryManifest(StrictModel):
    schema_version: Literal["1.0"] = "1.0"
    library_id: str
    configuration: dict[str, object]
    status: Literal["reference_priors_seeded", "gto_solutions_seeded"]
    source_id: UUID
    source_commit: str
    source_content_sha256: str = Field(min_length=64, max_length=64)
    artifacts: list[RangeManifestEntry]
    notes: list[str]


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
                stack_match=nearest_stack_bucket(requested.stack_depth_chips),
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
                abs(artifact.spot.stack_depth_chips - requested.stack_depth_chips),
                artifact.spot.stack_depth_chips,
            ),
        )
        mismatch = abs(selected.spot.stack_depth_chips - requested.stack_depth_chips)
        stack_match = StackDepthMatch(
            requested_chips=requested.stack_depth_chips,
            status="nearest",
            matched_chips=selected.spot.stack_depth_chips,
            absolute_mismatch_chips=mismatch,
            relative_mismatch=mismatch / requested.stack_depth_chips,
        )
        return RangeLookup(artifact=selected, stack_match=stack_match)


def write_artifact(artifact: RangeArtifact, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(artifact.model_dump(mode="json"), indent=2, sort_keys=True) + "\n"
    path.write_text(payload, encoding="utf-8")


def load_seeded_reference_library() -> RangeLibrary:
    """Load and hash-verify the 9-max native-chip reference prior library."""
    table_size = 9
    manifest_path = PROJECT_ROOT / "configs" / "ranges" / "library_manifest.json"
    manifest = RangeLibraryManifest.model_validate_json(manifest_path.read_text(encoding="utf-8"))
    if manifest.configuration.get("seats") != table_size:
        raise ValueError("range manifest table size does not match the requested library")
    if manifest.status != "reference_priors_seeded":
        raise ValueError("reference range manifest is not seeded")
    artifacts: list[RangeArtifact] = []
    for entry in manifest.artifacts:
        path = (PROJECT_ROOT / entry.path).resolve()
        if not path.is_relative_to(PROJECT_ROOT):
            raise ValueError("range artifact path escapes the project root")
        content = path.read_bytes()
        if hashlib.sha256(content).hexdigest() != entry.content_sha256:
            raise ValueError(f"range artifact hash mismatch: {entry.path}")
        artifact = RangeArtifact.model_validate_json(content)
        if artifact.artifact_id != entry.artifact_id:
            raise ValueError(f"range artifact ID mismatch: {entry.path}")
        if artifact.spot.seats != table_size or artifact.strategy_role != "reference_prior":
            raise ValueError(f"range artifact has incompatible scope: {entry.path}")
        if artifact.spot.player_position != entry.position:
            raise ValueError(f"range artifact position mismatch: {entry.path}")
        if artifact.confidence != entry.confidence:
            raise ValueError(f"range artifact confidence mismatch: {entry.path}")
        artifacts.append(artifact)
    expected_positions = set(positions_for_table_size(table_size)) - {Position.BB}
    actual_positions = {artifact.spot.player_position for artifact in artifacts}
    if actual_positions != expected_positions:
        raise ValueError(
            "reference library must contain every non-BB unopened position exactly once"
        )
    return RangeLibrary(artifacts)
