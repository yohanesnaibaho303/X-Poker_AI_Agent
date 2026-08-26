"""Fail-closed authorized capture, adaptive scheduling, and replay diagnostics."""

from __future__ import annotations

import argparse
import hashlib
import json
import time
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from xpoker_agent.capture.frames import (
    CapturedFrame,
    capture_occluded_client,
    classify_xpoker_window,
    normalize_frame,
)
from xpoker_agent.capture.layout import load_layout_profile
from xpoker_agent.capture.models import (
    AuthorizedTargetProfile,
    CaptureFrameRecord,
    CaptureReplayManifest,
    LayoutProfile,
    WindowCandidate,
)
from xpoker_agent.capture.profile import load_target_profile, match_authorized_target
from xpoker_agent.capture.windows import discover_xpoker_windows
from xpoker_agent.config import PROJECT_ROOT, load_runtime_config


@dataclass
class AdaptiveFrameScheduler:
    minimum_fps: int
    maximum_fps: int
    current_fps: int
    unchanged_frames: int = 0

    @classmethod
    def create(cls, minimum_fps: int, maximum_fps: int) -> AdaptiveFrameScheduler:
        if not 1 <= minimum_fps <= maximum_fps:
            raise ValueError("frame-rate bounds are invalid")
        return cls(minimum_fps, maximum_fps, maximum_fps)

    def observe(self, *, content_changed: bool, capture_latency_ms: float) -> None:
        if content_changed:
            self.unchanged_frames = 0
            self.current_fps = min(self.maximum_fps, self.current_fps + 2)
            return
        self.unchanged_frames += 1
        budget_ms = 1000 / self.current_fps
        if capture_latency_ms > budget_ms * 0.8:
            self.current_fps = max(self.minimum_fps, self.current_fps - 2)
        elif self.unchanged_frames >= self.current_fps * 2:
            self.current_fps = max(self.minimum_fps, self.current_fps - 1)
            self.unchanged_frames = 0

    @property
    def interval_seconds(self) -> float:
        return 1 / self.current_fps


def select_authorized_table(
    profile: AuthorizedTargetProfile,
    *,
    locked_hwnd: int | None = None,
    locked_process_id: int | None = None,
) -> WindowCandidate:
    locked = locked_hwnd is not None or locked_process_id is not None
    if locked and (locked_hwnd is None or locked_process_id is None):
        raise ValueError("locked target requires both HWND and process ID")
    candidates = discover_xpoker_windows(classify_visual_role=not locked)
    if locked:
        candidates = tuple(
            candidate.model_copy(
                update={"visual_role": "table", "visual_role_confidence": 1.0}
            )
            for candidate in candidates
            if candidate.hwnd == locked_hwnd
            and candidate.process_id == locked_process_id
        )
    eligible = [
        candidate
        for candidate in candidates
        if match_authorized_target(candidate, profile).eligible
    ]
    if len(eligible) != 1:
        raise RuntimeError(f"expected exactly one authorized X-Poker table; found {len(eligible)}")
    return eligible[0]


def target_fingerprint(candidate: WindowCandidate, layout: LayoutProfile) -> str:
    identity = {
        "runtime_target": "X-Poker",
        "process_name": (candidate.process_name or "").casefold(),
        "executable_sha256": candidate.executable_sha256,
        "window_class": candidate.window_class,
        "process_id": candidate.process_id,
        "hwnd": candidate.hwnd,
        "visual_role": candidate.visual_role,
        "layout_id": layout.layout_id,
    }
    encoded = json.dumps(identity, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(encoded).hexdigest()


def capture_authorized_frame(
    sequence: int,
    profile: AuthorizedTargetProfile,
    layout: LayoutProfile,
    *,
    locked_hwnd: int | None = None,
    locked_process_id: int | None = None,
) -> tuple[CapturedFrame, CaptureFrameRecord]:
    started_ns = time.monotonic_ns()
    candidate = select_authorized_table(
        profile,
        locked_hwnd=locked_hwnd,
        locked_process_id=locked_process_id,
    )
    observed_ratio = candidate.client_rect.width / candidate.client_rect.height
    canonical_ratio = layout.canonical_width / layout.canonical_height
    if abs(observed_ratio - canonical_ratio) / canonical_ratio > 0.025:
        raise RuntimeError("authorized table aspect ratio is outside the supported layout")

    captured = capture_occluded_client(candidate)
    normalized = normalize_frame(captured, layout.canonical_width, layout.canonical_height)
    role, confidence = classify_xpoker_window(normalized)
    locked = locked_hwnd is not None and locked_process_id is not None
    if not locked and (
        role != "table" or confidence < profile.minimum_visual_role_confidence
    ):
        raise RuntimeError("authorized table identity was lost before capture")
    captured_at = datetime.now(UTC)
    latency_ms = (time.monotonic_ns() - started_ns) / 1_000_000
    digest = hashlib.sha256(normalized.bgra_bottom_up).hexdigest()
    record = CaptureFrameRecord(
        sequence=sequence,
        captured_at=captured_at,
        monotonic_ns=started_ns,
        authorization_profile_id=profile.profile_id,
        target_hwnd=candidate.hwnd,
        target_process_id=candidate.process_id,
        target_fingerprint=target_fingerprint(candidate, layout),
        layout_id=layout.layout_id,
        source_width=captured.width,
        source_height=captured.height,
        source_dpi=candidate.dpi or layout.calibration_dpi,
        width=normalized.width,
        height=normalized.height,
        dpi=layout.calibration_dpi,
        content_sha256=digest,
        capture_latency_ms=latency_ms,
        visual_role_confidence=confidence,
    )
    return normalized, record


def record_capture_replay(count: int, output_dir: Path) -> CaptureReplayManifest:
    if count <= 0:
        raise ValueError("capture replay requires at least one frame")
    output_dir = output_dir.resolve()
    profile = load_target_profile()
    layout = load_layout_profile()
    runtime = load_runtime_config()
    scheduler = AdaptiveFrameScheduler.create(runtime.capture_fps_min, runtime.capture_fps_max)
    started_at = datetime.now(UTC)
    replay_id = started_at.strftime("xpoker-capture-%Y%m%dT%H%M%S.%fZ")
    replay_dir = output_dir / replay_id
    replay_dir.mkdir(parents=True, exist_ok=False)
    records: list[CaptureFrameRecord] = []
    previous_hash: str | None = None

    for sequence in range(count):
        loop_started = time.monotonic()
        frame, record = capture_authorized_frame(sequence, profile, layout)
        artifact = replay_dir / f"frame-{sequence:06d}.bmp"
        frame.write_bmp(artifact)
        record.artifact_path = artifact.relative_to(PROJECT_ROOT).as_posix()
        records.append(record)
        scheduler.observe(
            content_changed=record.content_sha256 != previous_hash,
            capture_latency_ms=record.capture_latency_ms,
        )
        previous_hash = record.content_sha256
        remaining = scheduler.interval_seconds - (time.monotonic() - loop_started)
        if sequence + 1 < count and remaining > 0:
            time.sleep(remaining)

    manifest = CaptureReplayManifest(
        replay_id=replay_id,
        authorization_profile_id=profile.profile_id,
        layout_id=layout.layout_id,
        started_at=started_at,
        frames=records,
    )
    manifest_path = replay_dir / "manifest.json"
    manifest_path.write_text(manifest.model_dump_json(indent=2), encoding="utf-8")
    return manifest


def verify_capture_replay(manifest_path: Path) -> list[str]:
    manifest, legacy_fields = load_capture_replay(manifest_path)
    issues: list[str] = []
    if legacy_fields:
        issues.append(
            "legacy manifest identity/source fields unavailable: "
            + ", ".join(sorted(legacy_fields))
        )
    for record in manifest.frames:
        if record.artifact_path is None:
            issues.append(f"frame {record.sequence} has no artifact")
            continue
        artifact = PROJECT_ROOT / record.artifact_path
        try:
            frame = CapturedFrame.from_bmp(artifact.read_bytes())
        except (OSError, ValueError) as error:
            issues.append(f"frame {record.sequence} cannot be read: {error}")
            continue
        digest = hashlib.sha256(frame.bgra_bottom_up).hexdigest()
        if digest != record.content_sha256:
            issues.append(f"frame {record.sequence} content hash mismatch")
        if (frame.width, frame.height) != (record.width, record.height):
            issues.append(f"frame {record.sequence} dimensions mismatch")
    return issues


def load_capture_replay(manifest_path: Path) -> tuple[CaptureReplayManifest, set[str]]:
    """Load current manifests or preserve older local evidence with explicit missing-field flags."""
    payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    legacy_fields: set[str] = set()
    for frame in payload.get("frames", []):
        for field, fallback in (
            ("target_hwnd", 1),
            ("target_process_id", 1),
            ("source_width", frame.get("width")),
            ("source_height", frame.get("height")),
            ("source_dpi", frame.get("dpi")),
        ):
            if field not in frame:
                legacy_fields.add(field)
                frame[field] = fallback
    return CaptureReplayManifest.model_validate(payload), legacy_fields


def main() -> None:
    parser = argparse.ArgumentParser(description="Record authorized X-Poker client frames")
    parser.add_argument("--frames", type=int, default=3)
    parser.add_argument("--output", type=Path, default=PROJECT_ROOT / "data" / "frames")
    args = parser.parse_args()
    manifest = record_capture_replay(args.frames, args.output)
    print(
        json.dumps(
            {
                "replay_id": manifest.replay_id,
                "frame_count": len(manifest.frames),
                "layout_id": manifest.layout_id,
                "mean_capture_latency_ms": sum(
                    frame.capture_latency_ms for frame in manifest.frames
                )
                / len(manifest.frames),
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
