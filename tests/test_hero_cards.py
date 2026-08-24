import json

from xpoker_agent.capture.frames import CapturedFrame
from xpoker_agent.config import PROJECT_ROOT
from xpoker_agent.vision.hero_cards import classify_hero_suit, match_hero_rank_signature


def test_enrolled_hero_rank_masks_match_only_their_declared_position() -> None:
    path = (
        PROJECT_ROOT
        / "data"
        / "card_templates"
        / "xpoker_portrait_hero_rank_templates_v1.json"
    )
    payload = json.loads(path.read_text(encoding="utf-8"))

    assert payload["schema_version"] == "1.0"
    assert "not held-out accuracy evidence" in payload["intended_use"]
    assert len(payload["templates"]) == 13
    for template in payload["templates"]:
        rank, distance, margin = match_hero_rank_signature(
            bytes.fromhex(template["signature"]), template["position"]
        )
        assert rank == template["rank"]
        assert distance == 0
        assert margin >= 0.025
        assert len(template["source_frame_sha256"]) == 64


def test_hero_rank_matcher_rejects_wrong_shape_and_position() -> None:
    rank, distance, _ = match_hero_rank_signature(bytes(59), "left")

    assert rank is None
    assert distance > 0.12


def test_orientation_scoped_suit_ignores_the_overlapped_neighbor_color() -> None:
    width, height = 47, 66
    pixels = bytearray(bytes((255, 255, 255, 255)) * width * height)
    for y in range(10, 26):
        for x in range(0, 18):
            offset = ((height - 1 - y) * width + x) * 4
            pixels[offset : offset + 4] = bytes((200, 50, 30, 255))
        for x in range(30, 46):
            offset = ((height - 1 - y) * width + x) * 4
            pixels[offset : offset + 4] = bytes((30, 30, 30, 255))
    frame = CapturedFrame(width, height, bytes(pixels))

    assert classify_hero_suit(frame, "left")[0] == "d"
    assert classify_hero_suit(frame, "right")[0] == "s"
