"""Lightweight deterministic X-Poker card-face candidates."""

from __future__ import annotations

import json
from functools import lru_cache

from xpoker_agent.capture.frames import CapturedFrame, normalize_frame
from xpoker_agent.config import PROJECT_ROOT
from xpoker_agent.vision.models import CardFaceObservation

_TEMPLATE_PATH = PROJECT_ROOT / "data" / "card_templates" / "xpoker_portrait_rank_templates_v1.json"
_BIT_COUNT = 18 * 26


def _pixels_top_down(frame: CapturedFrame) -> list[tuple[int, int, int]]:
    pixels: list[tuple[int, int, int]] = []
    for y in range(frame.height):
        y_bottom = frame.height - 1 - y
        for x in range(frame.width):
            offset = (y_bottom * frame.width + x) * 4
            blue, green, red, _ = frame.bgra_bottom_up[offset : offset + 4]
            pixels.append((red, green, blue))
    return pixels


def rank_signature(card: CapturedFrame) -> bytes:
    normalized = normalize_frame(card, 45, 66)
    pixels = _pixels_top_down(normalized)
    brightness = sorted(sum(pixel) // 3 for pixel in pixels)
    background = brightness[int(len(brightness) * 0.9)]
    bits: list[bool] = []
    for output_y in range(26):
        for output_x in range(18):
            x = 2 + output_x * 41 // 18
            y = 2 + output_y * 62 // 26
            red, green, blue = pixels[y * 45 + x]
            bits.append(
                (red + green + blue) / 3 < background - 35
                or max(red, green, blue) - min(red, green, blue) > 45
            )
    packed = bytearray((_BIT_COUNT + 7) // 8)
    for index, value in enumerate(bits):
        if value:
            packed[index // 8] |= 1 << (7 - index % 8)
    return bytes(packed)


@lru_cache(maxsize=1)
def _templates() -> tuple[tuple[str, bytes], ...]:
    payload = json.loads(_TEMPLATE_PATH.read_text(encoding="utf-8"))
    if payload.get("schema_version") != "1.0" or (payload["width"], payload["height"]) != (
        18,
        26,
    ):
        raise ValueError("unsupported X-Poker card-rank template artifact")
    templates = tuple(
        (item["rank"], bytes.fromhex(item["signature"])) for item in payload["templates"]
    )
    if {rank for rank, _ in templates} != set("A23456789TJQK"):
        raise ValueError("card-rank templates must cover all thirteen ranks")
    return templates


def match_rank_signature(signature: bytes) -> tuple[str | None, float, float]:
    if len(signature) != (_BIT_COUNT + 7) // 8:
        raise ValueError("card-rank signature has the wrong size")
    by_rank: dict[str, float] = {}
    for rank, template in _templates():
        distance = sum(
            (left ^ right).bit_count() for left, right in zip(signature, template, strict=True)
        )
        by_rank[rank] = min(by_rank.get(rank, 1.0), distance / _BIT_COUNT)
    ordered = sorted(by_rank.items(), key=lambda item: (item[1], item[0]))
    winner, distance = ordered[0]
    margin = ordered[1][1] - distance
    if distance > 0.12 or margin < 0.025:
        return None, distance, margin
    return winner, distance, margin


def classify_suit(card: CapturedFrame) -> tuple[str | None, float]:
    normalized = normalize_frame(card, 45, 66)
    counts = {"h": 0, "d": 0, "c": 0}
    dark = 0
    for red, green, blue in _pixels_top_down(normalized):
        dark += int(max(red, green, blue) < 95)
        if red >= 110 and red > green * 1.3 and red > blue * 1.2:
            counts["h"] += 1
        elif blue >= 85 and blue > red * 1.2 and blue > green * 1.1:
            counts["d"] += 1
        elif green >= 85 and green > red * 1.2 and green > blue * 1.05:
            counts["c"] += 1
    ordered = sorted(counts.items(), key=lambda item: (-item[1], item[0]))
    suit, count = ordered[0]
    runner_up = ordered[1][1]
    if count >= 8 and count >= runner_up + 4:
        return suit, min(0.99, 0.8 + (count - runner_up) / 200)
    if dark >= 30 and count < 8:
        return "s", 0.85
    return None, 0.0


def recognize_card_face(card: CapturedFrame) -> CardFaceObservation:
    signature = rank_signature(card)
    rank, distance, margin = match_rank_signature(signature)
    suit, suit_confidence = classify_suit(card)
    if rank is None or suit is None:
        return CardFaceObservation(
            card=None,
            derived_rank_signature_hex=signature.hex(),
            confidence=0.0,
            rank_distance=distance,
            rank_margin=margin,
            reason="rank or suit is below the calibrated acceptance margin",
        )
    rank_confidence = min(0.99, 1.0 - distance * 2.5)
    return CardFaceObservation(
        card=f"{rank}{suit}",
        derived_rank_signature_hex=signature.hex(),
        confidence=min(rank_confidence, suit_confidence),
        rank_distance=distance,
        rank_margin=margin,
        reason="single-frame card candidate; temporal and uniqueness gates pending",
    )
