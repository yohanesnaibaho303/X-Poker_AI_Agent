import hashlib
import json
import struct

from scripts.audit_m3_evidence import (
    audit_evidence,
    build_action_control_regression,
)


def _bmp(width: int, height: int) -> bytes:
    payload = bytearray(26)
    payload[:2] = b"BM"
    struct.pack_into("<ii", payload, 18, width, height)
    return bytes(payload)


def test_audit_deduplicates_and_builds_action_regression(tmp_path) -> None:
    frames = tmp_path / "frames"
    frames.mkdir()
    image = _bmp(445, 800)
    (frames / "a.bmp").write_bytes(image)
    (frames / "b.bmp").write_bytes(image)
    digest = hashlib.sha256(image).hexdigest()
    replay = {
        "replay_id": "replay-1",
        "layout_exact": True,
        "source_layout_id": "xpoker-windows-10-portrait-9max-v1",
        "evaluation_layout_id": "xpoker-windows-10-portrait-9max-v1",
        "p95_total_latency_ms": 12,
        "frames": [
            {
                "sequence": 0,
                "content_sha256": digest,
                "hero_cards": ["As", "Kd"],
                "board_cards": [],
                "hero_action_surface": "pre_action",
                "current_hand_mode": "standard_nlh",
                "total_latency_ms": 12,
            }
        ],
    }
    replay_path = frames / "replay.json"
    replay_path.write_text(json.dumps(replay), encoding="utf-8")

    audit = audit_evidence(frames)
    cases = build_action_control_regression(replay_path, "pre_action")

    assert audit["summary"]["file_count"] == 3
    assert audit["summary"]["duplicate_file_count"] == 1
    assert audit["summary"]["bmp_dimensions"] == {"445x800": 2}
    assert audit["observed_coverage"]["recognized_cards"] == ["As", "Kd"]
    assert cases[0].predicted == cases[0].expected == "pre_action"
    assert cases[0].confidence == 0
