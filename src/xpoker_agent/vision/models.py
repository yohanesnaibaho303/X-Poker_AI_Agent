"""Strict, confidence-bearing models for deterministic visual recognition."""

from __future__ import annotations

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
    special_rule: Literal["bomb_pot"] | None = None
    confidence: float = Field(ge=0.0, le=1.0)
    matched_signals: list[str] = Field(default_factory=list)
    reason: str
