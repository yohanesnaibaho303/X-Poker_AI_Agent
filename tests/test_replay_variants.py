import asyncio
import hashlib
from datetime import UTC, datetime

from xpoker_agent.capture.frames import CapturedFrame
from xpoker_agent.capture.layout import load_layout_profile
from xpoker_agent.capture.models import CaptureFrameRecord, CaptureReplayManifest
from xpoker_agent.vision.live import build_live_capture_diagnostic
from xpoker_agent.vision.models import WindowsOcrResult
from xpoker_agent.vision.replay import diagnose_capture_replay


def test_recognition_replay_handles_deterministic_lighting_and_overlay_variants(tmp_path) -> None:
    layout = load_layout_profile()
    pixel_count = layout.canonical_width * layout.canonical_height
    variants = {
        "baseline": b"\x20\x20\x20\xff" * pixel_count,
        "bright": b"\xc0\xc0\xc0\xff" * pixel_count,
        "overlay": b"\x20\x20\x20\xff" * (pixel_count - 4) + b"\xff\x00\xff\xff" * 4,
    }
    records = []
    for sequence, (name, pixels) in enumerate(variants.items()):
        frame = CapturedFrame(layout.canonical_width, layout.canonical_height, pixels)
        artifact = tmp_path / f"{name}.bmp"
        frame.write_bmp(artifact)
        records.append(
            CaptureFrameRecord(
                sequence=sequence,
                captured_at=datetime.now(UTC),
                monotonic_ns=sequence + 1,
                authorization_profile_id="offline-variants",
                target_hwnd=1,
                target_process_id=2,
                target_fingerprint="a" * 64,
                layout_id=layout.layout_id,
                source_width=frame.width,
                source_height=frame.height,
                source_dpi=96,
                width=frame.width,
                height=frame.height,
                dpi=96,
                content_sha256=hashlib.sha256(frame.bgra_bottom_up).hexdigest(),
                capture_latency_ms=1,
                visual_role_confidence=0.99,
                artifact_path=artifact.name,
            )
        )
    manifest_path = tmp_path / "manifest.json"
    manifest_path.write_text(
        CaptureReplayManifest(
            replay_id="variants",
            authorization_profile_id="offline-variants",
            layout_id=layout.layout_id,
            started_at=datetime.now(UTC),
            frames=records,
        ).model_dump_json(),
        encoding="utf-8",
    )

    async def runner(frame, record, supported_layout):
        return build_live_capture_diagnostic(
            frame=frame,
            record=record,
            layout=supported_layout,
            rule_ocr=WindowsOcrResult(
                text="", lines=[], processing_latency_ms=1, language_tag="en-US"
            ),
            pot_ocr=WindowsOcrResult(
                text="", lines=[], processing_latency_ms=1, language_tag="en-US"
            ),
        )

    report = asyncio.run(
        diagnose_capture_replay(manifest_path, runner=runner, artifact_root=tmp_path)
    )
    assert report.frame_count == 3
    assert len({frame.content_sha256 for frame in report.frames}) == 3
    assert report.controller_enabled is False
