"""X-Poker-specific angled hero-card geometry and bounded template matching."""

from __future__ import annotations

import json
from functools import lru_cache

from xpoker_agent.capture.frames import CapturedFrame
from xpoker_agent.capture.models import LayoutProfile
from xpoker_agent.config import PROJECT_ROOT
from xpoker_agent.vision.card_faces import classify_suit, rank_signature
from xpoker_agent.vision.models import CardFaceObservation, HeroCardsObservation, PixelBox
from xpoker_agent.vision.primitives import (
    bright_neutral_mask,
    connected_components,
    crop_frame,
    crop_layout_region,
)

_TEMPLATE_PATH = (
    PROJECT_ROOT / "data" / "card_templates" / "xpoker_portrait_hero_rank_templates_v1.json"
)
_BIT_COUNT = 18 * 26


@lru_cache(maxsize=1)
def _templates() -> dict[str, tuple[tuple[str, bytes], ...]]:
    payload = json.loads(_TEMPLATE_PATH.read_text(encoding="utf-8"))
    if payload.get("schema_version") != "1.0" or (payload["width"], payload["height"]) != (
        18,
        26,
    ):
        raise ValueError("unsupported X-Poker hero-rank template artifact")
    grouped: dict[str, list[tuple[str, bytes]]] = {"left": [], "right": []}
    for item in payload["templates"]:
        grouped[item["position"]].append((item["rank"], bytes.fromhex(item["signature"])))
    return {position: tuple(items) for position, items in grouped.items()}


def match_hero_rank_signature(
    signature: bytes, position: str
) -> tuple[str | None, float, float]:
    if position not in {"left", "right"}:
        raise ValueError("hero-card position must be left or right")
    if len(signature) != (_BIT_COUNT + 7) // 8:
        raise ValueError("hero-card rank signature has the wrong size")
    distances: dict[str, float] = {}
    for rank, template in _templates()[position]:
        distance = sum(
            (left ^ right).bit_count()
            for left, right in zip(signature, template, strict=True)
        ) / _BIT_COUNT
        distances[rank] = min(distances.get(rank, 1.0), distance)
    ordered = sorted(distances.items(), key=lambda item: (item[1], item[0]))
    rank, distance = ordered[0]
    margin = ordered[1][1] - distance if len(ordered) > 1 else 0.0
    if distance > 0.08 or margin < 0.025:
        return None, distance, margin
    return rank, distance, margin


def classify_hero_suit(
    card_crop: CapturedFrame, position: str
) -> tuple[str | None, float]:
    """Exclude the adjacent overlapped card before applying palette evidence."""
    if position not in {"left", "right"}:
        raise ValueError("hero-card position must be left or right")
    focus_width = min(26, card_crop.width)
    left = 0 if position == "left" else card_crop.width - focus_width
    focused = crop_frame(
        card_crop,
        PixelBox(
            left=left,
            top=0,
            right=left + focus_width,
            bottom=card_crop.height,
        ),
    )
    return classify_suit(focused)


def detect_hero_cards(frame: CapturedFrame, layout: LayoutProfile) -> HeroCardsObservation:
    crop = crop_layout_region(frame, layout, "hero_cards")
    surfaces = [
        box
        for box in connected_components(bright_neutral_mask(crop), minimum_area=250)
        if 55 <= box.width <= 90 and 45 <= box.height <= 90
    ]
    if len(surfaces) != 1:
        return HeroCardsObservation(
            geometry_supported=False,
            confidence=0.0,
            reason="expected one merged two-card hero surface",
        )
    surface = surfaces[0]
    if surface.width < 60:
        return HeroCardsObservation(
            geometry_supported=False,
            confidence=0.0,
            reason="hero surface is too narrow for two overlapped cards",
        )
    boxes = [
        PixelBox(
            left=surface.left,
            top=surface.top,
            right=min(surface.right, surface.left + 47),
            bottom=surface.bottom,
        ),
        PixelBox(
            left=max(surface.left, surface.right - 47),
            top=surface.top,
            right=surface.right,
            bottom=surface.bottom,
        ),
    ]
    observations: list[CardFaceObservation] = []
    for position, box in zip(("left", "right"), boxes, strict=True):
        card_crop = crop_frame(crop, box)
        signature = rank_signature(card_crop)
        rank, distance, margin = match_hero_rank_signature(signature, position)
        suit, suit_confidence = classify_hero_suit(card_crop, position)
        if rank is None or suit is None:
            observations.append(
                CardFaceObservation(
                    card=None,
                    derived_rank_signature_hex=signature.hex(),
                    confidence=0.0,
                    rank_distance=distance,
                    rank_margin=margin,
                    reason="hero rank or suit is outside the enrolled acceptance margin",
                )
            )
        else:
            observations.append(
                CardFaceObservation(
                    card=f"{rank}{suit}",
                    derived_rank_signature_hex=signature.hex(),
                    confidence=min(suit_confidence, 1.0 - distance * 2.5),
                    rank_distance=distance,
                    rank_margin=margin,
                    reason="single-frame angled hero-card candidate; temporal gate pending",
                )
            )
    cards = [item.card for item in observations if item.card is not None]
    if len(cards) == 2 and len(set(cards)) != 2:
        observations = [
            item.model_copy(
                update={
                    "card": None,
                    "confidence": 0.0,
                    "reason": "duplicate physical hero-card candidate",
                }
            )
            for item in observations
        ]
    return HeroCardsObservation(
        geometry_supported=True,
        cards=observations,
        confidence=min((item.confidence for item in observations), default=0.0),
        reason="two overlapped X-Poker hero-card surfaces isolated",
    )
