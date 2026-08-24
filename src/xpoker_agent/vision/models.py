"""Strict, confidence-bearing models for deterministic visual recognition."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Literal

from pydantic import Field, model_validator

from xpoker_agent.models import CARD_PATTERN, StrictModel


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
    confidence: float = Field(ge=0.0, le=1.0)
    matched_signals: list[str] = Field(default_factory=list)
    reason: str


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
    confidence: float = Field(ge=0.0, le=1.0)
    accepted: Literal[False] = False
    ocr_text_sha256: str | None = Field(default=None, min_length=64, max_length=64)
    reason: str


class SeatActionConsensus(StrictModel):
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
    canonical_event_accepted: Literal[False] = False
    reason: str = "temporal badge candidate; amount/order validation pending"


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
    regions: dict[str, tuple[float, float, float, float]]
    seat_observations: list[SeatOccupancyObservation] = Field(default_factory=list)
    seat_panels: list[SeatPanelObservation] = Field(default_factory=list)
    seat_actions: list[SeatActionObservation] = Field(default_factory=list)


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
    board_consensus: TemporalConsensus
    board_card_consensus: list[TemporalConsensus] = Field(default_factory=list)
    recognized_board_cards: list[str] = Field(default_factory=list)
    board_cards_accepted: bool = False
    board_cards_reason: str
    pot_consensus: TemporalConsensus
    seat_stack_consensus: list[SeatStackConsensus] = Field(default_factory=list)
    seat_action_consensus: list[SeatActionConsensus] = Field(default_factory=list)
    hand_epoch: int = Field(ge=0)
    derived_action_candidates: list[DerivedActionCandidate] = Field(default_factory=list)
    last_error: str | None = None
    controller_enabled: Literal[False] = False
