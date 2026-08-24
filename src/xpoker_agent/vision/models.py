"""Strict, confidence-bearing models for deterministic visual recognition."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Literal
from uuid import UUID

from pydantic import Field, model_validator

from xpoker_agent.models import CARD_PATTERN, HandEvent, HandState, Position, StrictModel


class PixelBox(StrictModel):
    """Top-down, half-open pixel coordinates."""

    left: int = Field(ge=0)
    top: int = Field(ge=0)
    right: int = Field(ge=1)
    bottom: int = Field(ge=1)

    @property
    def width(self) -> int:
        return self.right - self.left

    @property
    def height(self) -> int:
        return self.bottom - self.top

    @model_validator(mode="after")
    def validate_edges(self) -> PixelBox:
        if self.right <= self.left or self.bottom <= self.top:
            raise ValueError("pixel box must have positive area")
        return self


class CardSlotCandidate(StrictModel):
    box: PixelBox
    confidence: float = Field(ge=0.0, le=1.0)
    row_index: int = Field(default=0, ge=0)


class UnsupportedVisualState(StrictModel):
    unsupported: bool
    reasons: list[
        Literal[
            "multiple_board_rows",
            "too_many_board_cards",
            "ambiguous_board_geometry",
        ]
    ]
    confidence: float = Field(ge=0.0, le=1.0)
    board_rows: int = Field(ge=0)
    card_slots: int = Field(ge=0)


class CardRecognition(StrictModel):
    card: str
    confidence: float = Field(ge=0.0, le=1.0)
    alternatives: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_card_codes(self) -> CardRecognition:
        values = [self.card, *self.alternatives]
        if any(not CARD_PATTERN.fullmatch(value) for value in values):
            raise ValueError("recognized cards must use rank plus lowercase suit")
        if len(values) != len(set(values)):
            raise ValueError("card alternatives must be unique")
        return self


class CardFaceObservation(StrictModel):
    card: str | None = None
    derived_rank_signature_hex: str | None = Field(
        default=None, min_length=118, max_length=118
    )
    confidence: float = Field(ge=0.0, le=1.0)
    rank_distance: float = Field(ge=0.0, le=1.0)
    rank_margin: float = Field(ge=0.0, le=1.0)
    accepted: Literal[False] = False
    reason: str

    @model_validator(mode="after")
    def validate_optional_card(self) -> CardFaceObservation:
        if self.card is not None and not CARD_PATTERN.fullmatch(self.card):
            raise ValueError("card candidate must use rank plus lowercase suit")
        return self


class HeroCardsObservation(StrictModel):
    geometry_supported: bool
    cards: list[CardFaceObservation] = Field(default_factory=list)
    confidence: float = Field(ge=0.0, le=1.0)
    reason: str


class DealerButtonObservation(StrictModel):
    seat: int | None = Field(default=None, ge=0, le=8)
    confidence: float = Field(ge=0.0, le=1.0)
    box: PixelBox | None = None
    accepted: Literal[False] = False
    reason: str


class TemporalSample(StrictModel):
    frame_sequence: int = Field(ge=0)
    content_sha256: str = Field(min_length=64, max_length=64)
    value: str
    confidence: float = Field(ge=0.0, le=1.0)


class TemporalConsensus(StrictModel):
    accepted: bool
    value: str | None = None
    confidence: float = Field(ge=0.0, le=1.0)
    stable_frames: int = Field(ge=0)
    alternatives: list[str] = Field(default_factory=list)
    reason: str | None = None


class NumericRecognition(StrictModel):
    raw_text: str
    value: Decimal = Field(ge=0)
    confidence: float = Field(ge=0.0, le=1.0)
    format_id: Literal["integer", "decimal", "grouped", "compact"]


class WindowsOcrResult(StrictModel):
    text: str
    lines: list[str]
    processing_latency_ms: float = Field(ge=0.0)
    engine_id: Literal["windows.media.ocr"] = "windows.media.ocr"
    language_tag: str


class RuleLabelClassification(StrictModel):
    supported_standard_nlh: bool
    supported_single_board_bomb_pot: bool = False
    special_rule: Literal["bomb_pot"] | None = None
    bomb_pot_state: Literal["none", "scheduled", "active", "ambiguous"] = "none"
    hands_until_bomb: int | None = Field(default=None, ge=0)
    bomb_pot_interval_hands: int | None = Field(default=None, ge=1)
    bomb_pot_forced_contribution_native: Decimal | None = Field(default=None, gt=0)
    small_blind_native: Decimal | None = Field(default=None, gt=0)
    big_blind_native: Decimal | None = Field(default=None, gt=0)
    blind_confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    confidence: float = Field(ge=0.0, le=1.0)
    matched_signals: list[str] = Field(default_factory=list)
    reason: str

    @model_validator(mode="after")
    def validate_blinds(self) -> RuleLabelClassification:
        values = (self.small_blind_native, self.big_blind_native)
        if (values[0] is None) != (values[1] is None):
            raise ValueError("small and big blinds must be observed together")
        if values[0] is not None and values[1] is not None and values[0] >= values[1]:
            raise ValueError("small blind must be less than big blind")
        if values[0] is None and self.blind_confidence != 0:
            raise ValueError("blind confidence requires observed blind values")
        if values[0] is not None and self.blind_confidence == 0:
            raise ValueError("observed blinds require positive confidence")
        return self


class SeatOccupancyObservation(StrictModel):
    seat: int = Field(ge=0, le=8)
    status: Literal["occupied", "empty", "ambiguous"]
    confidence: float = Field(ge=0.0, le=1.0)
    dark_panel_fraction: float = Field(ge=0.0, le=1.0)
    plus_horizontal_pixels: int = Field(ge=0)
    plus_vertical_pixels: int = Field(ge=0)


class SeatPanelObservation(StrictModel):
    seat: int = Field(ge=0, le=8)
    status: Literal["empty", "seated", "on_break", "ambiguous"]
    stack_native: Decimal | None = Field(default=None, ge=0)
    stack_token: str | None = None
    confidence: float = Field(ge=0.0, le=1.0)
    accepted: Literal[False] = False
    ocr_text_sha256: str | None = Field(default=None, min_length=64, max_length=64)
    reason: str


class PotObservation(StrictModel):
    value_native: Decimal | None = Field(default=None, ge=0)
    token: str | None = None
    confidence: float = Field(ge=0.0, le=1.0)
    accepted: Literal[False] = False
    reason: str


class SeatStackConsensus(StrictModel):
    seat: int = Field(ge=0, le=8)
    player_status: Literal["empty", "seated", "on_break", "ambiguous"]
    consensus: TemporalConsensus


class SeatActionObservation(StrictModel):
    seat: int = Field(ge=0, le=8)
    action: Literal["fold", "check", "call", "bet", "raise", "all_in"] | None
    badge_amount_native: Decimal | None = Field(default=None, ge=0)
    confidence: float = Field(ge=0.0, le=1.0)
    accepted: Literal[False] = False
    ocr_text_sha256: str | None = Field(default=None, min_length=64, max_length=64)
    reason: str


class SeatActionConsensus(StrictModel):
    seat: int = Field(ge=0, le=8)
    consensus: TemporalConsensus


class HeroActionControlsObservation(StrictModel):
    mode: Literal["absent", "pre_action", "decision", "ambiguous"]
    available_actions: list[
        Literal["fold", "check", "call", "bet", "raise", "all_in"]
    ] = Field(default_factory=list)
    pre_action_toggles: list[Literal["fold_or_check", "call_any"]] = Field(
        default_factory=list
    )
    call_amount_native: Decimal | None = Field(default=None, ge=0)
    confidence: float = Field(ge=0.0, le=1.0)
    accepted: Literal[False] = False
    ocr_text_sha256: str | None = Field(default=None, min_length=64, max_length=64)
    reason: str


class SeatStatusConsensus(StrictModel):
    seat: int = Field(ge=0, le=8)
    consensus: TemporalConsensus


class DerivedActionCandidate(StrictModel):
    event_id: str = Field(min_length=64, max_length=64)
    hand_epoch: int = Field(ge=0)
    frame_sequence: int = Field(ge=0)
    seat: int = Field(ge=0, le=8)
    street: Literal["preflop", "flop", "turn", "river"]
    action: Literal["fold", "check", "call", "bet", "raise", "all_in"]
    confidence: float = Field(ge=0.0, le=1.0)
    occurrence: int = Field(default=1, ge=1)
    dealer_seat: int | None = Field(default=None, ge=0, le=8)
    active_seats: list[int] = Field(default_factory=list)
    canonical_event_accepted: Literal[False] = False
    reason: str = "temporal badge candidate; amount/order validation pending"


class SeatBadgeAmountCandidate(StrictModel):
    event_id: str = Field(min_length=64, max_length=64)
    hand_epoch: int = Field(ge=0)
    frame_sequence: int = Field(ge=0)
    seat: int = Field(ge=0, le=8)
    amount_native: Decimal = Field(ge=0)
    confidence: float = Field(ge=0.0, le=1.0)
    canonical_event_accepted: Literal[False] = False
    reason: str = "temporal numeric-badge candidate; semantic role pending"


class StackDeltaCandidate(StrictModel):
    event_id: str = Field(min_length=64, max_length=64)
    hand_epoch: int = Field(ge=0)
    frame_sequence: int = Field(ge=0)
    seat: int = Field(ge=0, le=8)
    street: Literal["preflop", "flop", "turn", "river", "unknown"]
    previous_stack_native: Decimal = Field(ge=0)
    current_stack_native: Decimal = Field(ge=0)
    committed_native: Decimal = Field(gt=0)
    canonical_event_accepted: Literal[False] = False
    reason: str = "stable stack decrease; action and pot reconciliation pending"


class PotDeltaCandidate(StrictModel):
    event_id: str = Field(min_length=64, max_length=64)
    hand_epoch: int = Field(ge=0)
    frame_sequence: int = Field(ge=0)
    street: Literal["preflop", "flop", "turn", "river", "unknown"]
    previous_pot_native: Decimal = Field(ge=0)
    current_pot_native: Decimal = Field(gt=0)
    increase_native: Decimal = Field(gt=0)
    evidence_mode: Literal["stable_endpoints", "cross_signal_single_frame"] = (
        "stable_endpoints"
    )
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    canonical_event_accepted: Literal[False] = False
    reason: str = "stable pot increase; action and stack reconciliation pending"


class ActionAmountReconciliation(StrictModel):
    action_event_id: str = Field(min_length=64, max_length=64)
    delta_event_id: str | None = Field(default=None, min_length=64, max_length=64)
    seat: int = Field(ge=0, le=8)
    action: Literal["fold", "check", "call", "bet", "raise", "all_in"]
    amount_native: Decimal | None = Field(default=None, ge=0)
    status: Literal["not_required", "matched", "pending", "ambiguous"]
    canonical_event_accepted: Literal[False] = False
    reason: str


class ActionPotReconciliation(StrictModel):
    action_event_id: str = Field(min_length=64, max_length=64)
    stack_delta_event_id: str | None = Field(default=None, min_length=64, max_length=64)
    pot_delta_event_id: str | None = Field(default=None, min_length=64, max_length=64)
    seat: int = Field(ge=0, le=8)
    action: Literal["fold", "check", "call", "bet", "raise", "all_in"]
    amount_native: Decimal | None = Field(default=None, ge=0)
    status: Literal["not_required", "matched", "pending", "ambiguous", "mismatch"]
    canonical_event_accepted: Literal[False] = False
    reason: str


class ActionOrderValidation(StrictModel):
    hand_epoch: int = Field(ge=0)
    street: Literal["preflop", "flop", "turn", "river"]
    action_event_ids: list[str] = Field(default_factory=list)
    observed_seats: list[int] = Field(default_factory=list)
    expected_start_seat: int | None = Field(default=None, ge=0, le=8)
    expected_next_seat: int | None = Field(default=None, ge=0, le=8)
    status: Literal["prefix_consistent", "pending", "inconsistent"]
    issues: list[str] = Field(default_factory=list)
    canonical_event_accepted: Literal[False] = False
    reason: str


class LiveHandBoundaryValidation(StrictModel):
    hand_epoch: int = Field(ge=0)
    previous_dealer_seat: int | None = Field(default=None, ge=0, le=8)
    current_dealer_seat: int | None = Field(default=None, ge=0, le=8)
    expected_dealer_seat: int | None = Field(default=None, ge=0, le=8)
    previous_active_seats: list[int] = Field(default_factory=list)
    current_active_seats: list[int] = Field(default_factory=list)
    status: Literal["pending", "validated", "rejected"]
    issues: list[str] = Field(default_factory=list)
    canonical_event_accepted: Literal[False] = False
    reason: str


class BlindPostReconciliation(StrictModel):
    hand_epoch: int = Field(ge=0)
    seat: int = Field(ge=0, le=8)
    blind_kind: Literal["small_blind", "big_blind"]
    amount_native: Decimal = Field(gt=0)
    stack_delta_event_id: str | None = Field(default=None, min_length=64, max_length=64)
    badge_amount_event_id: str | None = Field(default=None, min_length=64, max_length=64)
    status: Literal["matched", "pending", "ambiguous"]
    canonical_event_accepted: Literal[False] = False
    reason: str


class LiveReconstructionReadiness(StrictModel):
    hand_epoch: int = Field(ge=0)
    ready: bool
    big_blind_native: Decimal | None = Field(default=None, gt=0)
    eligible_action_event_ids: list[str] = Field(default_factory=list)
    issues: list[str] = Field(default_factory=list)
    canonical_events_emitted: bool = False
    reason: str


class LiveCanonicalHandPrefix(StrictModel):
    hand_epoch: int = Field(ge=1)
    hand_id: UUID
    events: list[HandEvent]
    state: HandState
    source_action_event_ids: list[str] = Field(default_factory=list)
    complete: Literal[False] = False
    reason: str = "validated live canonical hand prefix"


class LiveCaptureDiagnostic(StrictModel):
    schema_version: Literal["1.0"] = "1.0"
    captured_at: datetime
    frame_sequence: int = Field(ge=0)
    content_sha256: str = Field(min_length=64, max_length=64)
    layout_id: str
    table_size: Literal[6, 9]
    frame_width: int = Field(gt=0)
    frame_height: int = Field(gt=0)
    target_hwnd: int = Field(ge=1)
    target_process_id: int = Field(ge=1)
    target_fingerprint: str = Field(min_length=64, max_length=64)
    capture_latency_ms: float = Field(ge=0.0)
    ocr_latency_ms: float = Field(ge=0.0)
    visual_role_confidence: float = Field(ge=0.0, le=1.0)
    current_hand_supported: bool
    current_hand_mode: Literal["standard_nlh", "single_board_bomb_pot", "ambiguous"]
    standard_nlh_supported: bool
    single_board_bomb_pot_supported: bool
    special_rule: Literal["bomb_pot"] | None = None
    bomb_pot_state: Literal["none", "scheduled", "active", "ambiguous"]
    hands_until_bomb: int | None = Field(default=None, ge=0)
    bomb_pot_interval_hands: int | None = Field(default=None, ge=1)
    bomb_pot_forced_contribution_native: Decimal | None = Field(default=None, gt=0)
    small_blind_native: Decimal | None = Field(default=None, gt=0)
    big_blind_native: Decimal | None = Field(default=None, gt=0)
    blind_confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    rule_confidence: float = Field(ge=0.0, le=1.0)
    mode_reason: str
    matched_signals: list[str] = Field(default_factory=list)
    rule_text: str
    pot_text: str
    pot: PotObservation
    board_rows: int = Field(ge=0)
    board_card_slots: int = Field(ge=0)
    board_geometry_supported: bool
    board_geometry_confidence: float = Field(ge=0.0, le=1.0)
    board_geometry_reasons: list[str] = Field(default_factory=list)
    board_cards: list[CardFaceObservation] = Field(default_factory=list)
    hero_cards: HeroCardsObservation
    dealer: DealerButtonObservation
    regions: dict[str, tuple[float, float, float, float]]
    seat_observations: list[SeatOccupancyObservation] = Field(default_factory=list)
    seat_panels: list[SeatPanelObservation] = Field(default_factory=list)
    seat_actions: list[SeatActionObservation] = Field(default_factory=list)
    hero_action_controls: HeroActionControlsObservation


class LiveObservationStartRequest(StrictModel):
    table_size: Literal[6, 9] = 9
    interval_ms: int = Field(default=500, ge=200, le=5000)


class LiveObservationStatus(StrictModel):
    schema_version: Literal["1.0"] = "1.0"
    running: bool
    table_size: Literal[6, 9]
    interval_ms: int = Field(ge=1)
    started_at: datetime | None = None
    stopped_at: datetime | None = None
    latest_sequence: int = Field(ge=0)
    frames_attempted: int = Field(ge=0)
    frames_succeeded: int = Field(ge=0)
    frames_failed: int = Field(ge=0)
    consecutive_failures: int = Field(ge=0)
    latest_captured_at: datetime | None = None
    latest_age_ms: float | None = Field(default=None, ge=0.0)
    target_fingerprint: str | None = Field(default=None, min_length=64, max_length=64)
    target_stable: bool
    current_hand_mode: Literal["standard_nlh", "single_board_bomb_pot", "ambiguous"]
    current_hand_supported: bool
    mode_consensus: TemporalConsensus
    epoch_mode_consensus: TemporalConsensus
    blind_consensus: TemporalConsensus
    session_blind_consensus: TemporalConsensus
    board_consensus: TemporalConsensus
    board_card_consensus: list[TemporalConsensus] = Field(default_factory=list)
    recognized_board_cards: list[str] = Field(default_factory=list)
    board_cards_accepted: bool = False
    board_cards_reason: str
    hero_card_consensus: list[TemporalConsensus] = Field(default_factory=list)
    recognized_hero_cards: list[str] = Field(default_factory=list)
    hero_cards_accepted: bool = False
    hero_cards_reason: str
    detected_hero_seat: int | None = Field(default=None, ge=0, le=8)
    hero_seat_confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    hero_seat_reason: str
    detected_hero_position: Position | None = None
    dealer_consensus: TemporalConsensus
    seat_status_consensus: list[SeatStatusConsensus] = Field(default_factory=list)
    active_seats: list[int] = Field(default_factory=list)
    provisional_positions: dict[int, Position] = Field(default_factory=dict)
    positions_reason: str
    pot_consensus: TemporalConsensus
    seat_stack_consensus: list[SeatStackConsensus] = Field(default_factory=list)
    seat_action_consensus: list[SeatActionConsensus] = Field(default_factory=list)
    hero_control_consensus: TemporalConsensus
    hand_epoch: int = Field(ge=0)
    hand_boundary_validation: LiveHandBoundaryValidation
    blind_post_reconciliations: list[BlindPostReconciliation] = Field(
        default_factory=list
    )
    hand_starting_stacks_native: dict[int, Decimal] = Field(default_factory=dict)
    reconstruction_readiness: LiveReconstructionReadiness
    canonical_hand: LiveCanonicalHandPrefix | None = None
    canonical_reconstruction_error: str | None = None
    derived_action_candidates: list[DerivedActionCandidate] = Field(default_factory=list)
    seat_badge_amount_candidates: list[SeatBadgeAmountCandidate] = Field(
        default_factory=list
    )
    stack_delta_candidates: list[StackDeltaCandidate] = Field(default_factory=list)
    pot_delta_candidates: list[PotDeltaCandidate] = Field(default_factory=list)
    action_amount_reconciliations: list[ActionAmountReconciliation] = Field(
        default_factory=list
    )
    action_pot_reconciliations: list[ActionPotReconciliation] = Field(default_factory=list)
    action_order_validations: list[ActionOrderValidation] = Field(default_factory=list)
    last_error: str | None = None
    controller_enabled: Literal[False] = False
