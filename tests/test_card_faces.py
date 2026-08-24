import json

from xpoker_agent.capture.frames import CapturedFrame
from xpoker_agent.config import PROJECT_ROOT
from xpoker_agent.vision.card_faces import (
    classify_suit,
    match_rank_signature,
    recognize_card_face,
)


def test_rank_template_artifact_covers_all_ranks_and_self_matches() -> None:
    path = PROJECT_ROOT / "data/card_templates/xpoker_portrait_rank_templates_v1.json"
    payload = json.loads(path.read_text(encoding="utf-8"))
    assert {item["rank"] for item in payload["templates"]} == set("A23456789TJQK")
    for item in payload["templates"]:
        rank, distance, margin = match_rank_signature(bytes.fromhex(item["signature"]))
        assert rank == item["rank"]
        assert distance == 0
        assert margin >= 0.025


def _solid_with_patch(color: tuple[int, int, int, int]) -> CapturedFrame:
    width, height = 45, 66
    pixels = bytearray(bytes((255, 255, 255, 255)) * width * height)
    for y in range(10, 20):
        for x in range(5, 15):
            offset = ((height - 1 - y) * width + x) * 4
            pixels[offset : offset + 4] = bytes(color)
    return CapturedFrame(width, height, bytes(pixels))


def test_suit_color_classifier_uses_xpoker_palette() -> None:
    assert classify_suit(_solid_with_patch((30, 30, 200, 255)))[0] == "h"
    assert classify_suit(_solid_with_patch((200, 50, 30, 255)))[0] == "d"
    assert classify_suit(_solid_with_patch((30, 160, 30, 255)))[0] == "c"


def test_card_candidate_retains_only_the_derived_rank_mask_for_calibration() -> None:
    result = recognize_card_face(_solid_with_patch((30, 30, 200, 255)))

    assert result.derived_rank_signature_hex is not None
    assert len(result.derived_rank_signature_hex) == 118
