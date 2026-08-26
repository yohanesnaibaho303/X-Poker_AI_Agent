import asyncio
import hashlib
from datetime import UTC, datetime
from pathlib import Path

import pytest

from xpoker_agent.capture.frames import CapturedFrame
from xpoker_agent.capture.models import CaptureFrameRecord, CaptureReplayManifest, LayoutProfile
from xpoker_agent.vision.live import build_live_capture_diagnostic
from xpoker_agent.vision.models import WindowsOcrResult
from xpoker_agent.vision.replay import diagnose_capture_replay


def _record(frame: CapturedFrame, artifact_path: str) -> CaptureFrameRecord:
    return CaptureFrameRecord(
        sequence=0,
        captured_at=datetime.now(UTC),
        monotonic_ns=1,
        authorization_profile_id="offline-test",
        target_hwnd=1,
        target_process_id=2,
        target_fingerprint="a" * 64,
        layout_id="xpoker-windows-10-portrait-v1",
        source_width=frame.width,
        source_height=frame.height,
        source_dpi=96,
        width=frame.width,
        height=frame.height,
        dpi=96,
        content_sha256=hashlib.sha256(frame.bgra_bottom_up).hexdigest(),
        capture_latency_ms=2,
        visual_role_confidence=0.99,
        artifact_path=artifact_path,
    )


def test_recorded_replay_runs_same_diagnostic_boundary_without_raw_text(
    tmp_path: Path,
) -> None:
    from xpoker_agent.capture.layout import load_layout_profile

    layout = load_layout_profile()
    frame = CapturedFrame(
        layout.canonical_width,
        layout.canonical_height,
        b"\x00" * layout.canonical_width * layout.canonical_height * 4,
    )
    artifact = tmp_path / "frame.bmp"
    frame.write_bmp(artifact)
    record = _record(frame, "frame.bmp")
    manifest = CaptureReplayManifest(
        replay_id="offline-replay",
        authorization_profile_id="offline-test",
        layout_id=layout.layout_id,
        started_at=datetime.now(UTC),
        frames=[record],
    )
    manifest_path = tmp_path / "manifest.json"
    manifest_path.write_text(manifest.model_dump_json(), encoding="utf-8")

    async def runner(
        captured: CapturedFrame,
        observed: CaptureFrameRecord,
        supported_layout: LayoutProfile,
    ):
        return build_live_capture_diagnostic(
            frame=captured,
            record=observed,
            layout=supported_layout,
            rule_ocr=WindowsOcrResult(
                text="Bomb Pot: After 2 hands Blinds: 1/2",
                lines=[],
                processing_latency_ms=3,
                language_tag="en-US",
            ),
            pot_ocr=WindowsOcrResult(
                text="POT 4",
                lines=[],
                processing_latency_ms=2,
                language_tag="en-US",
            ),
        )

    report = asyncio.run(
        diagnose_capture_replay(manifest_path, runner=runner, artifact_root=tmp_path)
    )

    assert report.frame_count == 1
    assert report.frames[0].current_hand_supported is True
    assert report.promotion_eligible is False
    assert report.controller_enabled is False
    assert "Bomb Pot" not in report.model_dump_json()


def test_recorded_replay_rejects_tampered_frame(tmp_path: Path) -> None:
    from xpoker_agent.capture.layout import load_layout_profile

    layout = load_layout_profile()
    frame = CapturedFrame(1, 1, b"\x00\x00\x00\x00")
    (tmp_path / "frame.bmp").write_bytes(CapturedFrame(1, 1, b"\x01\x00\x00\x00").to_bmp())
    manifest = CaptureReplayManifest(
        replay_id="tampered",
        authorization_profile_id="offline-test",
        layout_id=layout.layout_id,
        started_at=datetime.now(UTC),
        frames=[_record(frame, "frame.bmp")],
    )
    path = tmp_path / "manifest.json"
    path.write_text(manifest.model_dump_json(), encoding="utf-8")

    with pytest.raises(ValueError, match="hash mismatch"):
        asyncio.run(diagnose_capture_replay(path, artifact_root=tmp_path))
