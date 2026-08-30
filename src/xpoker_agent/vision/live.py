"""Privacy-scoped diagnostics for an explicitly authorized X-Poker table."""

from __future__ import annotations

import asyncio

from xpoker_agent.capture.frames import CapturedFrame, normalize_frame
from xpoker_agent.capture.layout import load_layout_profile
from xpoker_agent.capture.models import CaptureFrameRecord, LayoutProfile
from xpoker_agent.capture.profile import load_target_profile
from xpoker_agent.capture.recording import capture_authorized_frame
from xpoker_agent.vision.actions import action_badge_region, parse_action_badge
from xpoker_agent.vision.card_faces import recognize_card_face
from xpoker_agent.vision.cards import classify_board_geometry, detect_card_slots
from xpoker_agent.vision.controls import parse_hero_action_controls
from xpoker_agent.vision.dealer import detect_dealer_button
from xpoker_agent.vision.hero_cards import detect_hero_cards
from xpoker_agent.vision.models import (
    LiveCaptureDiagnostic,
    SeatOccupancyObservation,
    WindowsOcrResult,
)
from xpoker_agent.vision.panels import parse_seat_panel
from xpoker_agent.vision.pots import parse_pot_label
from xpoker_agent.vision.primitives import crop_frame, crop_layout_region, normalized_box
from xpoker_agent.vision.rules import classify_rule_label
from xpoker_agent.vision.seats import classify_seat_occupancy
from xpoker_agent.vision.windows_ocr import recognize_text


def build_live_capture_diagnostic(
    *,
    frame: CapturedFrame,
    record: CaptureFrameRecord,
    layout: LayoutProfile,
    rule_ocr: WindowsOcrResult,
    pot_ocr: WindowsOcrResult,
    seat_observations: list[SeatOccupancyObservation] | None = None,
    panel_ocr: dict[int, WindowsOcrResult] | None = None,
    action_ocr: dict[int, WindowsOcrResult] | None = None,
    controls_ocr: WindowsOcrResult | None = None,
) -> LiveCaptureDiagnostic:
    classification = classify_rule_label(rule_ocr.text)
    current_hand_mode = (
        "standard_nlh"
        if classification.supported_standard_nlh
        else (
            "single_board_bomb_pot"
            if classification.supported_single_board_bomb_pot
            else "ambiguous"
        )
    )
    visible_regions = {
        name: (region.x, region.y, region.width, region.height)
        for name, region in layout.regions.items()
        if name in {"board", "hero_cards", "pot", "rule_label", "seat_ring", "actions"}
    }
    visible_regions.update(
        {
            f"seat_{calibration.seat}_anchor": (
                calibration.anchor_region.x,
                calibration.anchor_region.y,
                calibration.anchor_region.width,
                calibration.anchor_region.height,
            )
            for calibration in layout.seat_anchors
        }
    )
    seat_observations = seat_observations or classify_seat_occupancy(frame, layout)
    panel_ocr = panel_ocr or {}
    action_ocr = action_ocr or {}
    seat_panels = []
    for observation in seat_observations:
        result = panel_ocr.get(observation.seat)
        seat_panels.append(parse_seat_panel(observation, result.text if result else None))
    seat_actions = [
        parse_action_badge(
            observation,
            action_ocr[observation.seat].text if observation.seat in action_ocr else None,
        )
        for observation in seat_observations
    ]
    board_crop = crop_layout_region(frame, layout, "board")
    board_slots = detect_card_slots(board_crop)
    board_geometry = classify_board_geometry(board_slots)
    board_cards = []
    if not board_geometry.unsupported and len(board_slots) in {3, 4, 5}:
        board_cards = [
            recognize_card_face(crop_frame(board_crop, slot.box)) for slot in board_slots
        ]
    return LiveCaptureDiagnostic(
        captured_at=record.captured_at,
        frame_sequence=record.sequence,
        content_sha256=record.content_sha256,
        layout_id=layout.layout_id,
        table_size=layout.table_size,
        frame_width=frame.width,
        frame_height=frame.height,
        target_hwnd=record.target_hwnd,
        target_process_id=record.target_process_id,
        target_fingerprint=record.target_fingerprint,
        capture_latency_ms=record.capture_latency_ms,
        ocr_latency_ms=(
            rule_ocr.processing_latency_ms
            + pot_ocr.processing_latency_ms
            + (controls_ocr.processing_latency_ms if controls_ocr else 0.0)
            + sum(result.processing_latency_ms for result in panel_ocr.values())
            + sum(result.processing_latency_ms for result in action_ocr.values())
        ),
        visual_role_confidence=record.visual_role_confidence,
        current_hand_supported=(
            (
                classification.supported_standard_nlh
                or classification.supported_single_board_bomb_pot
            )
            and classification.small_blind_native == 1
            and classification.big_blind_native == 2
        ),
        current_hand_mode=current_hand_mode,
        standard_nlh_supported=classification.supported_standard_nlh,
        single_board_bomb_pot_supported=classification.supported_single_board_bomb_pot,
        special_rule=classification.special_rule,
        bomb_pot_state=classification.bomb_pot_state,
        hands_until_bomb=classification.hands_until_bomb,
        bomb_pot_interval_hands=classification.bomb_pot_interval_hands,
        bomb_pot_forced_contribution_native=(classification.bomb_pot_forced_contribution_native),
        small_blind_native=classification.small_blind_native,
        big_blind_native=classification.big_blind_native,
        blind_confidence=classification.blind_confidence,
        rule_confidence=classification.confidence,
        mode_reason=classification.reason,
        matched_signals=classification.matched_signals,
        rule_text=rule_ocr.text,
        pot_text=pot_ocr.text,
        pot=parse_pot_label(pot_ocr.text),
        board_rows=board_geometry.board_rows,
        board_card_slots=board_geometry.card_slots,
        board_geometry_supported=not board_geometry.unsupported,
        board_geometry_confidence=board_geometry.confidence,
        board_geometry_reasons=board_geometry.reasons,
        board_cards=board_cards,
        hero_cards=detect_hero_cards(frame, layout),
        dealer=detect_dealer_button(frame, layout),
        regions=visible_regions,
        seat_observations=seat_observations,
        seat_panels=seat_panels,
        seat_actions=seat_actions,
        hero_action_controls=parse_hero_action_controls(
            controls_ocr.text if controls_ocr else None
        ),
    )


def _scaled_pot_crop(frame: CapturedFrame, layout: LayoutProfile) -> CapturedFrame:
    crop = crop_layout_region(frame, layout, "pot")
    return normalize_frame(crop, crop.width * 4, crop.height * 4)


async def diagnose_captured_frame(
    *, frame: CapturedFrame, record: CaptureFrameRecord, layout: LayoutProfile
) -> LiveCaptureDiagnostic:
    """Run the same privacy-scoped recognition path for live or recorded evidence."""
    seat_observations = classify_seat_occupancy(frame, layout)
    rule_crop = crop_layout_region(frame, layout, "rule_label")
    pot_crop = _scaled_pot_crop(frame, layout)
    controls_crop = crop_layout_region(frame, layout, "actions")
    controls_crop = normalize_frame(
        controls_crop, controls_crop.width * 2, controls_crop.height * 2
    )
    panel_seats = [
        observation.seat for observation in seat_observations if observation.status != "empty"
    ]
    panel_crops = [
        crop_frame(
            frame,
            normalized_box(frame, layout.seat_anchors[seat].player_panel_region),
        )
        for seat in panel_seats
    ]
    action_crops = []
    for seat in panel_seats:
        crop = crop_frame(
            frame,
            normalized_box(frame, action_badge_region(layout.seat_anchors[seat])),
        )
        action_crops.append(normalize_frame(crop, crop.width * 5, crop.height * 5))
    results = await asyncio.gather(
        recognize_text(rule_crop),
        recognize_text(pot_crop),
        recognize_text(controls_crop),
        *(recognize_text(crop) for crop in panel_crops),
        *(recognize_text(crop) for crop in action_crops),
    )
    rule_ocr, pot_ocr, controls_ocr, *seat_results = results
    panel_results = seat_results[: len(panel_seats)]
    action_results = seat_results[len(panel_seats) :]
    panel_ocr = dict(zip(panel_seats, panel_results, strict=True))
    action_ocr = dict(zip(panel_seats, action_results, strict=True))
    return build_live_capture_diagnostic(
        frame=frame,
        record=record,
        layout=layout,
        rule_ocr=rule_ocr,
        pot_ocr=pot_ocr,
        seat_observations=seat_observations,
        panel_ocr=panel_ocr,
        action_ocr=action_ocr,
        controls_ocr=controls_ocr,
    )


async def diagnose_authorized_table(
    *,
    table_size: int = 9,
    sequence: int = 0,
    locked_hwnd: int | None = None,
    locked_process_id: int | None = None,
) -> tuple[LiveCaptureDiagnostic, CapturedFrame]:
    profile = load_target_profile()
    layout = load_layout_profile(table_size=table_size)
    frame, record = capture_authorized_frame(
        sequence,
        profile,
        layout,
        locked_hwnd=locked_hwnd,
        locked_process_id=locked_process_id,
    )
    diagnostic = await diagnose_captured_frame(frame=frame, record=record, layout=layout)
    return diagnostic, frame
