"""Offline execution of the production recognition path over capture manifests."""

from __future__ import annotations

import hashlib
import json
from collections import Counter
from collections.abc import Awaitable, Callable
from pathlib import Path
from typing import Literal

from pydantic import Field

from xpoker_agent.capture.frames import CapturedFrame
from xpoker_agent.capture.layout import load_layout_profile
from xpoker_agent.capture.models import CaptureFrameRecord, LayoutProfile
from xpoker_agent.capture.recording import load_capture_replay
from xpoker_agent.config import PROJECT_ROOT
from xpoker_agent.models import StrictModel
from xpoker_agent.vision.live import diagnose_captured_frame
from xpoker_agent.vision.models import LiveCaptureDiagnostic

DiagnosticRunner = Callable[
    [CapturedFrame, CaptureFrameRecord, LayoutProfile], Awaitable[LiveCaptureDiagnostic]
]


class RecognitionReplayFrame(StrictModel):
    sequence: int = Field(ge=0)
    content_sha256: str = Field(min_length=64, max_length=64)
    current_hand_supported: bool
    current_hand_mode: Literal["standard_nlh", "single_board_bomb_pot", "ambiguous"]
    board_cards: list[str]
    hero_cards: list[str]
    hero_action_surface: Literal["absent", "pre_action", "decision", "ambiguous"]
    occupied_seats: int = Field(ge=0, le=9)
    total_latency_ms: float = Field(ge=0)
    processing_latency_ms: float = Field(ge=0)
    ocr_wall_latency_ms: float = Field(ge=0)
    summed_ocr_latency_ms: float = Field(ge=0)


class RecognitionReplayReport(StrictModel):
    schema_version: Literal["1.0"] = "1.0"
    replay_id: str
    manifest_sha256: str = Field(min_length=64, max_length=64)
    source_layout_id: str
    evaluation_layout_id: str
    layout_exact: bool
    frame_count: int = Field(ge=1)
    p95_total_latency_ms: float = Field(ge=0)
    p95_ocr_wall_latency_ms: float = Field(ge=0)
    p95_non_ocr_latency_ms: float = Field(ge=0)
    p95_summed_ocr_latency_ms: float = Field(ge=0)
    frames: list[RecognitionReplayFrame]
    hero_action_surface_counts: dict[str, int]
    max_consecutive_decision_frames: int = Field(ge=0)
    promotion_eligible: Literal[False] = False
    controller_enabled: Literal[False] = False
    limitations: list[str]
    legacy_missing_fields: list[str]


async def _production_runner(
    frame: CapturedFrame, record: CaptureFrameRecord, layout: LayoutProfile
) -> LiveCaptureDiagnostic:
    return await diagnose_captured_frame(frame=frame, record=record, layout=layout)


async def diagnose_capture_replay(
    manifest_path: Path,
    *,
    runner: DiagnosticRunner = _production_runner,
    artifact_root: Path = PROJECT_ROOT,
) -> RecognitionReplayReport:
    raw_manifest = manifest_path.read_bytes()
    manifest, legacy_fields = load_capture_replay(manifest_path)
    if not manifest.frames:
        raise ValueError("recognition replay requires frames")
    layout = load_layout_profile(table_size=9)
    layout_exact = manifest.layout_id == layout.layout_id
    results: list[RecognitionReplayFrame] = []
    for record in manifest.frames:
        if record.artifact_path is None:
            raise ValueError(f"frame {record.sequence} has no artifact path")
        artifact = artifact_root / record.artifact_path
        frame = CapturedFrame.from_bmp(artifact.read_bytes())
        digest = hashlib.sha256(frame.bgra_bottom_up).hexdigest()
        if digest != record.content_sha256:
            raise ValueError(f"frame {record.sequence} content hash mismatch")
        diagnostic = await runner(frame, record, layout)
        processing_latency_ms = (
            diagnostic.processing_latency_ms
            or diagnostic.capture_latency_ms + diagnostic.ocr_latency_ms
        )
        results.append(
            RecognitionReplayFrame(
                sequence=record.sequence,
                content_sha256=digest,
                current_hand_supported=diagnostic.current_hand_supported,
                current_hand_mode=diagnostic.current_hand_mode,
                board_cards=[item.card for item in diagnostic.board_cards if item.card],
                hero_cards=[item.card for item in diagnostic.hero_cards.cards if item.card],
                hero_action_surface=diagnostic.hero_action_controls.mode,
                occupied_seats=sum(
                    item.status == "occupied" for item in diagnostic.seat_observations
                ),
                total_latency_ms=processing_latency_ms,
                processing_latency_ms=processing_latency_ms,
                ocr_wall_latency_ms=diagnostic.ocr_wall_latency_ms,
                summed_ocr_latency_ms=diagnostic.ocr_latency_ms,
            )
        )

    def p95(values: list[float]) -> float:
        ordered = sorted(values)
        return ordered[max(0, (len(ordered) * 95 + 99) // 100 - 1)]

    max_decision_run = 0
    decision_run = 0
    for frame in results:
        decision_run = decision_run + 1 if frame.hero_action_surface == "decision" else 0
        max_decision_run = max(max_decision_run, decision_run)
    return RecognitionReplayReport(
        replay_id=manifest.replay_id,
        manifest_sha256=hashlib.sha256(raw_manifest).hexdigest(),
        source_layout_id=manifest.layout_id,
        evaluation_layout_id=layout.layout_id,
        layout_exact=layout_exact,
        frame_count=len(results),
        p95_total_latency_ms=p95([item.total_latency_ms for item in results]),
        p95_ocr_wall_latency_ms=p95([item.ocr_wall_latency_ms for item in results]),
        p95_non_ocr_latency_ms=p95(
            [max(0.0, item.processing_latency_ms - item.ocr_wall_latency_ms) for item in results]
        ),
        p95_summed_ocr_latency_ms=p95([item.summed_ocr_latency_ms for item in results]),
        frames=results,
        hero_action_surface_counts=dict(Counter(frame.hero_action_surface for frame in results)),
        max_consecutive_decision_frames=max_decision_run,
        limitations=[
            "Recorded replay execution is regression evidence, not labeled holdout accuracy.",
            "Raw OCR text is excluded from this privacy-safe report.",
            *(
                ["Historical manifest fields were unavailable and are not promotion evidence."]
                if legacy_fields
                else []
            ),
            *(
                ["Source layout version differs from the current evaluation layout."]
                if not layout_exact
                else []
            ),
        ],
        legacy_missing_fields=sorted(legacy_fields),
    )


def write_recognition_replay_report(report: RecognitionReplayReport, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report.model_dump(mode="json"), indent=2) + "\n", encoding="utf-8")
