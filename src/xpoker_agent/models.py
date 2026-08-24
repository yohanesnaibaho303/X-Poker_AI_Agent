"""Versioned canonical models shared across module boundaries."""

from __future__ import annotations

import re
from datetime import datetime
from decimal import Decimal
from enum import StrEnum
from typing import Any, Literal
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

SCHEMA_VERSION = "1.0"
CARD_PATTERN = re.compile(r"^(?:[2-9TJQKA])[cdhs]$")


class StrictModel(BaseModel):
    """Base model that rejects unknown input and serializes enums by value."""

    model_config = ConfigDict(extra="forbid", validate_assignment=True)


class GameVariant(StrEnum):
    NLH = "NLH"


class GameFormat(StrEnum):
    CASH = "cash"


class Objective(StrEnum):
    CHIP_EV = "chip_ev"


class Position(StrEnum):
    UTG = "UTG"
    UTG_1 = "UTG+1"
    MP = "MP"
    LJ = "LJ"
    HJ = "HJ"
    CO = "CO"
    BTN = "BTN"
    SB = "SB"
    BB = "BB"


class OperatingMode(StrEnum):
    OBSERVE = "observe"
    ANALYZE = "analyze"
    RECOMMEND = "recommend"
    ARMED_TEST_CONTROL = "armed_test_control"


class TableStatus(StrEnum):
    UNAVAILABLE = "unavailable"
    READY = "ready"
    WAITING_FOR_HAND = "waiting_for_hand"
    IN_HAND = "in_hand"
    HAND_COMPLETE = "hand_complete"


class Street(StrEnum):
    NONE = "none"
    PREFLOP = "preflop"
    FLOP = "flop"
    TURN = "turn"
    RIVER = "river"
    SHOWDOWN = "showdown"


class ParticipationStatus(StrEnum):
    EMPTY = "empty"
    SEATED = "seated"
    ACTIVE = "active"
    FOLDED = "folded"
    ALL_IN = "all_in"
    SITTING_OUT = "sitting_out"
    ON_BREAK = "on_break"
    DISCONNECTED = "disconnected"


class EventCategory(StrEnum):
    BETTING_ACTION = "betting_action"
    LIFECYCLE = "lifecycle"
    FORCED_WAGER = "forced_wager"
    DEALING = "dealing"
    SETTLEMENT = "settlement"


EVENT_TYPES: dict[EventCategory, set[str]] = {
    EventCategory.BETTING_ACTION: {"fold", "check", "call", "bet", "raise", "all_in"},
    EventCategory.LIFECYCLE: {"hand_started", "showdown_started", "hand_completed"},
    EventCategory.FORCED_WAGER: {"blind_posted"},
    EventCategory.DEALING: {
        "dealer_assigned",
        "hole_cards_observed",
        "board_cards_observed",
    },
    EventCategory.SETTLEMENT: {"pot_awarded"},
}


class RakeConfig(StrictModel):
    kind: Literal["none"] = "none"
    percent: Decimal = Decimal("0")
    cap_bb: Decimal = Decimal("0")

    @model_validator(mode="after")
    def require_zero_rake(self) -> RakeConfig:
        if self.percent != 0 or self.cap_bb != 0:
            raise ValueError("initial configuration requires zero rake")
        return self


class GameConfig(StrictModel):
    schema_version: Literal["1.0"] = SCHEMA_VERSION
    config_id: str
    variant: GameVariant = GameVariant.NLH
    format: GameFormat = GameFormat.CASH
    seats: Literal[9] = 9
    rake: RakeConfig = Field(default_factory=RakeConfig)
    default_open_size_bb: Decimal = Decimal("2.0")
    objective: Objective = Objective.CHIP_EV
    positions: list[Position]
    enabled_special_rules: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_initial_game(self) -> GameConfig:
        expected = list(Position)
        if self.positions != expected:
            raise ValueError(f"positions must be in authoritative order: {expected}")
        if self.default_open_size_bb != Decimal("2.0"):
            raise ValueError("initial default open size must be 2.0 BB")
        if self.enabled_special_rules:
            raise ValueError("special rules are disabled in the initial configuration")
        return self


class RuntimeConfig(StrictModel):
    schema_version: Literal["1.0"] = SCHEMA_VERSION
    mode: OperatingMode = OperatingMode.OBSERVE
    host: str = "127.0.0.1"
    port: int = Field(default=8765, ge=1, le=65535)
    capture_fps_min: int = Field(default=5, ge=1, le=60)
    capture_fps_max: int = Field(default=15, ge=1, le=60)
    controller_enabled: Literal[False] = False
    evidence_retention: Literal["failures_and_actions"] = "failures_and_actions"

    @model_validator(mode="after")
    def validate_runtime(self) -> RuntimeConfig:
        if self.capture_fps_min > self.capture_fps_max:
            raise ValueError("capture_fps_min cannot exceed capture_fps_max")
        if self.mode is OperatingMode.ARMED_TEST_CONTROL:
            raise ValueError("Armed Test Control is unavailable in Milestone 0")
        return self


class Alternative(StrictModel):
    value: str
    score: float = Field(ge=0, le=1)


class Confidence(StrictModel):
    score: float = Field(ge=0, le=1)
    calibration_id: str
    alternatives: list[Alternative] = Field(default_factory=list)
    stable_frames: int = Field(default=1, ge=1)


class EvidenceRef(StrictModel):
    evidence_id: UUID = Field(default_factory=uuid4)
    frame_id: UUID
    frame_sequence: int = Field(ge=0)
    captured_at: datetime
    artifact_path: str | None = None
    content_sha256: str = Field(min_length=64, max_length=64)
    region_xywh: tuple[float, float, float, float] | None = None

    @field_validator("region_xywh")
    @classmethod
    def validate_region(
        cls, value: tuple[float, float, float, float] | None
    ) -> tuple[float, float, float, float] | None:
        if value is not None and any(number < 0 or number > 1 for number in value):
            raise ValueError("normalized region values must be within [0, 1]")
        return value


class Provenance(StrictModel):
    source_id: UUID = Field(default_factory=uuid4)
    url: str
    source_type: str
    title: str
    publisher: str | None = None
    published_at: datetime | None = None
    accessed_at: datetime
    license: str
    license_url: str | None = None
    intended_use: str
    fact_class: Literal[
        "rule",
        "mathematical_fact",
        "solver_derived",
        "heuristic",
        "player_opinion",
        "interface_observation",
    ]
    confidence: float = Field(ge=0, le=1)
    notes: str | None = None


class Producer(StrictModel):
    component: str
    version: str


class Observation(StrictModel):
    schema_version: Literal["1.0"] = SCHEMA_VERSION
    observation_id: UUID = Field(default_factory=uuid4)
    kind: str
    subject: dict[str, Any]
    value: dict[str, Any]
    confidence: Confidence
    evidence: list[UUID] = Field(default_factory=list)
    layout_version: str
    producer: Producer


class ObservationBatch(StrictModel):
    schema_version: Literal["1.0"] = SCHEMA_VERSION
    batch_id: UUID = Field(default_factory=uuid4)
    frame_id: UUID
    frame_sequence: int = Field(ge=0)
    target_identity: str
    observations: list[Observation]
    processing_latency_ms: float = Field(ge=0)
    health_flags: list[str] = Field(default_factory=list)


class EventAmount(StrictModel):
    to_bb: Decimal | None = Field(default=None, ge=0)
    added_bb: Decimal = Field(default=Decimal("0"), ge=0)


class HandEvent(StrictModel):
    schema_version: Literal["1.0"] = SCHEMA_VERSION
    event_id: UUID = Field(default_factory=uuid4)
    hand_id: UUID
    sequence: int = Field(ge=1)
    category: EventCategory
    type: str
    actor_seat: int | None = Field(default=None, ge=0, le=8)
    street: Street = Street.NONE
    amount: EventAmount | None = None
    cards: list[str] = Field(default_factory=list)
    dealer_seat: int | None = Field(default=None, ge=0, le=8)
    winner_seat: int | None = Field(default=None, ge=0, le=8)
    pot_index: int | None = Field(default=None, ge=0)
    input_observations: list[UUID] = Field(default_factory=list)
    confidence: Confidence
    assumptions: list[str] = Field(default_factory=list)

    @field_validator("cards")
    @classmethod
    def validate_cards(cls, cards: list[str]) -> list[str]:
        if len(cards) != len(set(cards)):
            raise ValueError("event cards must be unique")
        if any(not CARD_PATTERN.match(card) for card in cards):
            raise ValueError("cards must use rank plus lowercase suit, for example As or Td")
        return cards

    @model_validator(mode="after")
    def validate_event_shape(self) -> HandEvent:
        if self.type not in EVENT_TYPES[self.category]:
            raise ValueError(f"{self.type!r} is not valid for category {self.category}")
        needs_actor = self.category in {EventCategory.BETTING_ACTION, EventCategory.FORCED_WAGER}
        if needs_actor and self.actor_seat is None:
            raise ValueError("betting actions and forced wagers require actor_seat")
        if self.type == "dealer_assigned" and self.dealer_seat is None:
            raise ValueError("dealer_assigned requires dealer_seat")
        if self.type in {"hole_cards_observed", "board_cards_observed"} and not self.cards:
            raise ValueError(f"{self.type} requires cards")
        if self.type == "hole_cards_observed" and self.actor_seat is None:
            raise ValueError("hole_cards_observed requires actor_seat")
        if self.type == "pot_awarded" and (
            self.winner_seat is None or self.amount is None or self.pot_index is None
        ):
            raise ValueError("pot_awarded requires winner_seat, pot_index, and amount")
        if self.type != "pot_awarded" and self.pot_index is not None:
            raise ValueError("pot_index is valid only for pot_awarded")
        if self.type == "pot_awarded" and self.amount is not None and self.amount.added_bb <= 0:
            raise ValueError("pot_awarded requires a positive award amount")
        if self.type in {"call", "bet", "raise", "all_in", "blind_posted"} and (
            self.amount is None or self.amount.added_bb <= 0
        ):
            raise ValueError(f"{self.type} requires a positive added amount")
        return self


class SeatState(StrictModel):
    seat: int = Field(ge=0, le=8)
    position: Position | None = None
    participation: ParticipationStatus
    starting_stack_bb: Decimal = Field(ge=0)
    stack_bb: Decimal = Field(ge=0)
    committed_by_street_bb: dict[Street, Decimal] = Field(default_factory=dict)
    cards: list[str] = Field(default_factory=list)

    @field_validator("cards")
    @classmethod
    def validate_cards(cls, cards: list[str]) -> list[str]:
        if len(cards) != len(set(cards)) or any(not CARD_PATTERN.match(card) for card in cards):
            raise ValueError("seat cards must be unique valid card codes")
        return cards


class ValidationState(StrictModel):
    legal: bool = True
    issues: list[str] = Field(default_factory=list)


class PotLayer(StrictModel):
    pot_index: int = Field(ge=0)
    amount_bb: Decimal = Field(gt=0)
    remaining_bb: Decimal = Field(ge=0)
    cap_per_player_bb: Decimal = Field(gt=0)
    contributing_seats: list[int]
    eligible_seats: list[int]

    @model_validator(mode="after")
    def validate_layer(self) -> PotLayer:
        if self.remaining_bb > self.amount_bb:
            raise ValueError("pot-layer remainder cannot exceed its original amount")
        if len(self.contributing_seats) != len(set(self.contributing_seats)):
            raise ValueError("pot-layer contributors must be unique")
        if len(self.eligible_seats) != len(set(self.eligible_seats)):
            raise ValueError("pot-layer eligible seats must be unique")
        if not set(self.eligible_seats).issubset(self.contributing_seats):
            raise ValueError("eligible seats must have contributed to the pot layer")
        return self


class HandState(StrictModel):
    schema_version: Literal["1.0"] = SCHEMA_VERSION
    state_id: UUID = Field(default_factory=uuid4)
    hand_id: UUID
    revision: int = Field(default=0, ge=0)
    last_event_sequence: int = Field(default=0, ge=0)
    config_version: str
    table_status: TableStatus = TableStatus.WAITING_FOR_HAND
    street: Street = Street.NONE
    dealer_seat: int | None = Field(default=None, ge=0, le=8)
    hero_seat: int = Field(ge=0, le=8)
    hero_position: Position | None = None
    hero_cards: list[str] = Field(default_factory=list)
    board: list[str] = Field(default_factory=list)
    seats: list[SeatState]
    pot_main_bb: Decimal = Field(default=Decimal("0"), ge=0)
    pot_layers: list[PotLayer] = Field(default_factory=list)
    current_bet_bb: Decimal = Field(default=Decimal("0"), ge=0)
    minimum_raise_increment_bb: Decimal = Field(default=Decimal("0"), ge=0)
    last_aggressor_seat: int | None = Field(default=None, ge=0, le=8)
    next_to_act_seat: int | None = Field(default=None, ge=0, le=8)
    acted_seats: list[int] = Field(default_factory=list)
    raise_locked_seats: list[int] = Field(default_factory=list)
    initial_total_chips_bb: Decimal = Field(default=Decimal("0"), ge=0)
    available_actions: list[str] = Field(default_factory=list)
    event_ids: list[UUID] = Field(default_factory=list)
    validation: ValidationState = Field(default_factory=ValidationState)

    @model_validator(mode="after")
    def validate_state(self) -> HandState:
        if len(self.seats) != 9 or {seat.seat for seat in self.seats} != set(range(9)):
            raise ValueError("hand state must contain exactly seats 0 through 8")
        known_cards = self.board + [card for seat in self.seats for card in seat.cards]
        if len(known_cards) != len(set(known_cards)):
            raise ValueError("physical cards must be unique across the state")
        expected_board = {
            Street.NONE: 0,
            Street.PREFLOP: 0,
            Street.FLOP: 3,
            Street.TURN: 4,
            Street.RIVER: 5,
        }
        if self.street in expected_board and len(self.board) != expected_board[self.street]:
            expected = expected_board[self.street]
            raise ValueError(f"street {self.street} requires {expected} board cards")
        if self.initial_total_chips_bb:
            reconstructed_total = self.pot_main_bb + sum(
                (seat.stack_bb for seat in self.seats), start=Decimal("0")
            )
            if reconstructed_total != self.initial_total_chips_bb:
                raise ValueError(
                    "chip conservation failed: stacks plus pot do not equal the initial total"
                )
        if [layer.pot_index for layer in self.pot_layers] != list(range(len(self.pot_layers))):
            raise ValueError("pot layers must use contiguous zero-based indices")
        if sum((layer.remaining_bb for layer in self.pot_layers), start=Decimal("0")) != (
            self.pot_main_bb
        ):
            raise ValueError("pot-layer remainders must equal the reconstructed pot")
        if len(self.acted_seats) != len(set(self.acted_seats)) or any(
            seat < 0 or seat > 8 for seat in self.acted_seats
        ):
            raise ValueError("acted_seats must contain unique seat numbers from zero through eight")
        if len(self.raise_locked_seats) != len(set(self.raise_locked_seats)) or any(
            seat < 0 or seat > 8 for seat in self.raise_locked_seats
        ):
            raise ValueError(
                "raise_locked_seats must contain unique seat numbers from zero through eight"
            )
        return self


class ComboStrategy(StrictModel):
    weight: float = Field(ge=0, le=1)
    actions: dict[str, float] = Field(default_factory=dict)
    equity: float | None = Field(default=None, ge=0, le=1)
    ev_bb: dict[str, float] = Field(default_factory=dict)

    @field_validator("actions")
    @classmethod
    def validate_actions(cls, actions: dict[str, float]) -> dict[str, float]:
        if any(value < 0 or value > 1 for value in actions.values()):
            raise ValueError("action frequencies must be within [0, 1]")
        if actions and abs(sum(actions.values()) - 1.0) > 1e-9:
            raise ValueError("action frequencies must sum to one")
        return actions


class WeightedRange(StrictModel):
    schema_version: Literal["1.0"] = SCHEMA_VERSION
    range_id: UUID = Field(default_factory=uuid4)
    player_ref: str
    hand_id: UUID
    street: Street
    spot_key: str
    combos: dict[str, ComboStrategy]
    blocked_cards: list[str] = Field(default_factory=list)
    source: dict[str, Any]
    assumptions: list[str] = Field(default_factory=list)
    confidence: float = Field(ge=0, le=1)
    version: str


class StrategyMatch(StrictModel):
    schema_version: Literal["1.0"] = SCHEMA_VERSION
    match_id: UUID = Field(default_factory=uuid4)
    status: Literal["exact", "abstracted", "unavailable"]
    requested_spot: dict[str, Any]
    matched_spot: dict[str, Any] | None = None
    distance: dict[str, Any] = Field(default_factory=dict)
    source_artifact_id: UUID | None = None
    confidence: float = Field(ge=0, le=1)
    assumptions: list[str] = Field(default_factory=list)


class SelectedAction(StrictModel):
    type: Literal["fold", "check", "call", "bet", "raise", "all_in"]
    size_bb: Decimal | None = Field(default=None, ge=0)


class DecisionConfidence(StrictModel):
    overall: float = Field(ge=0, le=1)
    control_eligible: Literal[False] = False


class DecisionEnvelope(StrictModel):
    schema_version: Literal["1.0"] = SCHEMA_VERSION
    decision_id: UUID = Field(default_factory=uuid4)
    idempotency_token: UUID = Field(default_factory=uuid4)
    state_id: UUID
    state_revision: int = Field(ge=0)
    state_valid_until_frame: int = Field(ge=0)
    mode: Literal[OperatingMode.OBSERVE, OperatingMode.ANALYZE, OperatingMode.RECOMMEND]
    hero_combo: str
    baseline_actions: dict[str, float]
    adjusted_actions: dict[str, float]
    selected_action: SelectedAction
    random_seed: int
    random_draw: float = Field(ge=0, lt=1)
    strategy_match_id: UUID
    calculation_ids: list[UUID] = Field(default_factory=list)
    confidence: DecisionConfidence
    assumptions: list[str] = Field(default_factory=list)
    created_at: datetime


class PreflightCheck(StrictModel):
    name: str
    passed: bool
    detail: str | None = None


class ActionAttempt(StrictModel):
    schema_version: Literal["1.0"] = SCHEMA_VERSION
    attempt_id: UUID = Field(default_factory=uuid4)
    decision_id: UUID
    idempotency_token: UUID
    authorization_profile_id: str
    preflight_checks: list[PreflightCheck]
    target_window_fingerprint: str
    intended_control_region: tuple[float, float, float, float] | None = None
    input_at: datetime | None = None
    verification_deadline: datetime | None = None
    observed_transition_event_id: UUID | None = None
    outcome: Literal["blocked", "executed_verified", "executed_unverified", "cancelled"]
    evidence: list[UUID] = Field(default_factory=list)
    disarm_reason: str | None = None

    @model_validator(mode="after")
    def enforce_milestone_zero_control_boundary(self) -> ActionAttempt:
        if self.outcome in {"executed_verified", "executed_unverified"}:
            raise ValueError("executed action attempts are unavailable in Milestone 0")
        if self.input_at is not None:
            raise ValueError("Milestone 0 action attempts cannot contain an input timestamp")
        return self
