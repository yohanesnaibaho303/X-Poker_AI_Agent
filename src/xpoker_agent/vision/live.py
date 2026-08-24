"""Privacy-scoped diagnostics for an explicitly authorized X-Poker table."""

from __future__ import annotations

import asyncio

from xpoker_agent.capture.frames import CapturedFrame
from xpoker_agent.capture.layout import load_layout_profile
from xpoker_agent.capture.models import CaptureFrameRecord, LayoutProfile
from xpoker_agent.capture.profile import load_target_profile
from xpoker_agent.capture.recording import capture_authorized_frame
from xpoker_agent.vision.models import LiveCaptureDiagnostic, WindowsOcrResult
from xpoker_agent.vision.primitives import crop_layout_region
from xpoker_agent.vision.rules import classify_rule_label
from xpoker_agent.vision.windows_ocr import recognize_text


def build_live_capture_diagnostic(
    *,
    frame: CapturedFrame,
    record: CaptureFrameRecord,
    layout: LayoutProfile,
    rule_ocr: WindowsOcrResult,
    pot_ocr: WindowsOcrResult,
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
        if name in {"board", "pot", "rule_label", "seat_ring", "actions"}
    }
    return LiveCaptureDiagnostic(
        captured_at=record.captured_at,
        layout_id=layout.layout_id,
        frame_width=frame.width,
        frame_height=frame.height,
        target_fingerprint=record.target_fingerprint,
        capture_latency_ms=record.capture_latency_ms,
        ocr_latency_ms=rule_ocr.processing_latency_ms + pot_ocr.processing_latency_ms,
        visual_role_confidence=record.visual_role_confidence,
        current_hand_supported=(
            classification.supported_standard_nlh
            or classification.supported_single_board_bomb_pot
        ),
        current_hand_mode=current_hand_mode,
        standard_nlh_supported=classification.supported_standard_nlh,
        single_board_bomb_pot_supported=classification.supported_single_board_bomb_pot,
        special_rule=classification.special_rule,
        bomb_pot_state=classification.bomb_pot_state,
        hands_until_bomb=classification.hands_until_bomb,
        rule_confidence=classification.confidence,
        mode_reason=classification.reason,
        matched_signals=classification.matched_signals,
        rule_text=rule_ocr.text,
        pot_text=pot_ocr.text,
        regions=visible_regions,
    )


async def diagnose_authorized_table() -> tuple[LiveCaptureDiagnostic, CapturedFrame]:
    profile = load_target_profile()
    layout = load_layout_profile()
    frame, record = capture_authorized_frame(0, profile, layout)
    rule_crop = crop_layout_region(frame, layout, "rule_label")
    pot_crop = crop_layout_region(frame, layout, "pot")
    rule_ocr, pot_ocr = await asyncio.gather(
        recognize_text(rule_crop),
        recognize_text(pot_crop),
    )
    return (
        build_live_capture_diagnostic(
            frame=frame,
            record=record,
            layout=layout,
            rule_ocr=rule_ocr,
            pot_ocr=pot_ocr,
        ),
        frame,
    )
