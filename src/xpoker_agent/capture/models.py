"""Typed X-Poker-only window discovery and authorization records."""

from __future__ import annotations

import re
from datetime import datetime
from typing import Literal

from pydantic import Field, field_validator, model_validator

from xpoker_agent.models import StrictModel


class PixelRect(StrictModel):
    left: int
    top: int
    right: int
    bottom: int

    @property
    def width(self) -> int:
        return max(0, self.right - self.left)

    @property
    def height(self) -> int:
        return max(0, self.bottom - self.top)

    @model_validator(mode="after")
    def validate_edges(self) -> PixelRect:
        if self.right < self.left or self.bottom < self.top:
            raise ValueError("rectangle edges are inverted")
        return self


class WindowCandidate(StrictModel):
    hwnd: int = Field(ge=1)
    process_id: int = Field(ge=0)
    process_name: str | None = None
    executable_path: str | None = None
    executable_sha256: str | None = None
    title: str
    window_class: str
    window_rect: PixelRect
    client_rect: PixelRect
    visible: bool
    minimized: bool
    dpi: int | None = Field(default=None, ge=48, le=960)
    visual_role: Literal["unknown", "lobby", "table"] = "unknown"
    visual_role_confidence: float = Field(default=0.0, ge=0.0, le=1.0)

    @field_validator("executable_sha256")
    @classmethod
    def validate_hash(cls, value: str | None) -> str | None:
        if value is not None and not re.fullmatch(r"[0-9a-fA-F]{64}", value):
            raise ValueError("executable_sha256 must contain 64 hexadecimal characters")
        return value.lower() if value else None


class AuthorizedTargetProfile(StrictModel):
    schema_version: Literal["1.0"] = "1.0"
    profile_id: str
    enabled: bool = False
    allowed_process_names: list[str] = Field(default_factory=list)
    allowed_executable_sha256: list[str] = Field(default_factory=list)
    title_patterns: list[str] = Field(default_factory=lambda: [r"(?i)x[- ]?poker"])
    allowed_window_classes: list[str] = Field(default_factory=list)
    required_visual_role: Literal["table"] = "table"
    minimum_visual_role_confidence: float = Field(default=0.9, ge=0.0, le=1.0)
    notes: str

    @field_validator("allowed_process_names")
    @classmethod
    def normalize_names(cls, values: list[str]) -> list[str]:
        return [value.casefold() for value in values]

    @field_validator("allowed_executable_sha256")
    @classmethod
    def validate_hashes(cls, values: list[str]) -> list[str]:
        if any(not re.fullmatch(r"[0-9a-fA-F]{64}", value) for value in values):
            raise ValueError("allowed executable hashes must be SHA-256 hex strings")
        return [value.lower() for value in values]

    @field_validator("title_patterns")
    @classmethod
    def validate_patterns(cls, values: list[str]) -> list[str]:
        for value in values:
            re.compile(value)
        return values

    @model_validator(mode="after")
    def require_explicit_identity_when_enabled(self) -> AuthorizedTargetProfile:
        if self.enabled and not self.allowed_process_names:
            raise ValueError("enabled profiles require an explicit process-name allowlist")
        if self.enabled and not self.title_patterns:
            raise ValueError("enabled profiles require at least one X-Poker title pattern")
        return self


class TargetMatch(StrictModel):
    candidate_hwnd: int
    eligible: bool
    reasons: list[str]


class NormalizedRect(StrictModel):
    x: float = Field(ge=0.0, le=1.0)
    y: float = Field(ge=0.0, le=1.0)
    width: float = Field(gt=0.0, le=1.0)
    height: float = Field(gt=0.0, le=1.0)

    @model_validator(mode="after")
    def remain_inside_frame(self) -> NormalizedRect:
        if self.x + self.width > 1.0 or self.y + self.height > 1.0:
            raise ValueError("normalized rectangle extends outside the frame")
        return self


class LayoutAnchor(StrictModel):
    anchor_id: str
    detector: Literal["horizontal_menu_lines"]
    region: NormalizedRect
    minimum_confidence: float = Field(ge=0.0, le=1.0)


class LayoutProfile(StrictModel):
    schema_version: Literal["1.0"] = "1.0"
    layout_id: str
    runtime_target: Literal["X-Poker"] = "X-Poker"
    table_size: Literal[6, 9]
    app_version_label: str
    orientation: Literal["portrait"] = "portrait"
    canonical_width: int = Field(gt=0)
    canonical_height: int = Field(gt=0)
    calibration_dpi: int = Field(ge=48, le=960)
    color_format: Literal["BGRA8"] = "BGRA8"
    regions: dict[str, NormalizedRect]
    anchors: list[LayoutAnchor]

    @model_validator(mode="after")
    def validate_layout(self) -> LayoutProfile:
        if self.canonical_height <= self.canonical_width:
            raise ValueError("portrait layout height must exceed width")
        required_regions = {"client", "table_surface", "board", "pot", "seat_ring", "actions"}
        if not required_regions.issubset(self.regions):
            missing = sorted(required_regions - self.regions.keys())
            raise ValueError(f"layout is missing required regions: {missing}")
        if not self.anchors:
            raise ValueError("layout requires at least one stable anchor")
        return self


class CaptureFrameRecord(StrictModel):
    schema_version: Literal["1.0"] = "1.0"
    sequence: int = Field(ge=0)
    captured_at: datetime
    monotonic_ns: int = Field(ge=0)
    authorization_profile_id: str
    target_fingerprint: str = Field(min_length=64, max_length=64)
    layout_id: str
    source_width: int = Field(gt=0)
    source_height: int = Field(gt=0)
    source_dpi: int = Field(ge=48, le=960)
    width: int = Field(gt=0)
    height: int = Field(gt=0)
    dpi: int = Field(ge=48, le=960)
    color_format: Literal["BGRA8"] = "BGRA8"
    backend: Literal["print_window"] = "print_window"
    content_sha256: str = Field(min_length=64, max_length=64)
    capture_latency_ms: float = Field(ge=0.0)
    visual_role_confidence: float = Field(ge=0.0, le=1.0)
    artifact_path: str | None = None


class CaptureReplayManifest(StrictModel):
    schema_version: Literal["1.0"] = "1.0"
    replay_id: str
    runtime_target: Literal["X-Poker"] = "X-Poker"
    authorization_profile_id: str
    layout_id: str
    started_at: datetime
    frames: list[CaptureFrameRecord]
