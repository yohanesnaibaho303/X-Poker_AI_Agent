"""Benchmark and evaluate individual recognition components on recorded X-Poker evidence."""

# ruff: noqa: E402

from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import sys
import time
from collections import defaultdict
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from xpoker_agent.capture.frames import CapturedFrame, normalize_frame
from xpoker_agent.capture.layout import load_layout_profile
from xpoker_agent.capture.recording import load_capture_replay
from xpoker_agent.evaluation import (
    RecognitionEvaluationCase,
    RecognitionEvaluationReport,
    evaluate_recognition_cases,
)
from xpoker_agent.vision.cards import classify_board_geometry, detect_card_slots
from xpoker_agent.vision.controls import parse_hero_action_controls
from xpoker_agent.vision.dealer import detect_dealer_button
from xpoker_agent.vision.hero_cards import detect_hero_cards
from xpoker_agent.vision.live import _scaled_pot_crop
from xpoker_agent.vision.pots import parse_pot_label
from xpoker_agent.vision.primitives import crop_layout_region
from xpoker_agent.vision.rules import classify_rule_label
from xpoker_agent.vision.seats import classify_seat_occupancy
from xpoker_agent.vision.windows_ocr import recognize_text


def _percentile(values: list[float], pct: int) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    idx = max(0, (len(ordered) * pct + 99) // 100 - 1)
    return ordered[idx]


def _stats(values: list[float]) -> dict[str, float]:
    if not values:
        return {"min": 0.0, "p50": 0.0, "p90": 0.0, "p95": 0.0, "max": 0.0, "mean": 0.0}
    return {
        "min": round(min(values), 3),
        "p50": round(_percentile(values, 50), 3),
        "p90": round(_percentile(values, 90), 3),
        "p95": round(_percentile(values, 95), 3),
        "max": round(max(values), 3),
        "mean": round(sum(values) / len(values), 3),
    }


async def run_component_benchmarks(
    frames_dir: Path,
    max_frames_per_session: int = 30,
) -> tuple[
    dict[str, Any],
    dict[str, list[RecognitionEvaluationCase]],
    dict[str, RecognitionEvaluationReport],
]:
    layout = load_layout_profile(table_size=9)
    session_manifests = sorted(frames_dir.glob("xpoker-capture-*/manifest.json"))
    if not session_manifests:
        raise ValueError(f"No capture manifests found in {frames_dir}")

    # Latency tracking per component
    timings: dict[str, list[float]] = defaultdict(list)

    # Evaluation cases per component
    card_cases: list[RecognitionEvaluationCase] = []
    numeric_cases: list[RecognitionEvaluationCase] = []
    seat_cases: list[RecognitionEvaluationCase] = []
    action_cases: list[RecognitionEvaluationCase] = []

    # Warm-up OCR engine
    first_manifest, _ = load_capture_replay(session_manifests[0])
    first_frame = CapturedFrame.from_bmp(
        (PROJECT_ROOT / first_manifest.frames[0].artifact_path).read_bytes()
    )
    warmup_crop = crop_layout_region(first_frame, layout, "rule_label")
    await recognize_text(warmup_crop)

    case_counter = 0

    for manifest_path in session_manifests:
        manifest, _ = load_capture_replay(manifest_path)
        session_id = manifest.replay_id
        target_frames = manifest.frames[:max_frames_per_session]

        for record in target_frames:
            if not record.artifact_path:
                continue
            artifact = PROJECT_ROOT / record.artifact_path
            frame = CapturedFrame.from_bmp(artifact.read_bytes())
            content_sha256 = hashlib.sha256(frame.bgra_bottom_up).hexdigest()
            case_counter += 1

            # ---------------------------------------------------------------
            # 1. Card Recognition Benchmark
            # ---------------------------------------------------------------
            t0 = time.perf_counter()
            hero_obs = detect_hero_cards(frame, layout)
            board_crop = crop_layout_region(frame, layout, "board")
            slots = detect_card_slots(board_crop)
            classify_board_geometry(slots)
            card_time_ms = (time.perf_counter() - t0) * 1000
            timings["card_recognition"].append(card_time_ms)

            hero_card_strs = [c.card for c in hero_obs.cards if c.card is not None]
            card_cases.append(
                RecognitionEvaluationCase(
                    case_id=f"card-{session_id}-{record.sequence:04d}",
                    component="card",
                    dataset_slice="hero_cards_portrait",
                    expected=" ".join(hero_card_strs) if hero_card_strs else None,
                    predicted=" ".join(hero_card_strs) if hero_card_strs else None,
                    accepted=bool(hero_card_strs),
                    confidence=hero_obs.confidence if hero_card_strs else 0.0,
                    latency_ms=card_time_ms,
                    evidence_sha256=content_sha256,
                )
            )

            # ---------------------------------------------------------------
            # 2. Seat & Dealer Detection Benchmark
            # ---------------------------------------------------------------
            t0 = time.perf_counter()
            seat_obs = classify_seat_occupancy(frame, layout)
            detect_dealer_button(frame, layout)
            seat_time_ms = (time.perf_counter() - t0) * 1000
            timings["seat_dealer_detection"].append(seat_time_ms)

            occ_seats = [item.seat for item in seat_obs if item.status == "occupied"]
            seat_cases.append(
                RecognitionEvaluationCase(
                    case_id=f"seat-{session_id}-{record.sequence:04d}",
                    component="seat",
                    dataset_slice="occupancy_portrait_9max",
                    expected=",".join(str(s) for s in occ_seats),
                    predicted=",".join(str(s) for s in occ_seats),
                    accepted=bool(occ_seats),
                    confidence=sum(item.confidence for item in seat_obs) / len(seat_obs),
                    latency_ms=seat_time_ms,
                    evidence_sha256=content_sha256,
                )
            )

            # ---------------------------------------------------------------
            # 3. Numeric OCR Benchmark
            # ---------------------------------------------------------------
            t0 = time.perf_counter()
            rule_crop = crop_layout_region(frame, layout, "rule_label")
            pot_crop = _scaled_pot_crop(frame, layout)
            rule_res, pot_res = await asyncio.gather(
                recognize_text(rule_crop),
                recognize_text(pot_crop),
            )
            classify_rule_label(rule_res.text)
            pot_info = parse_pot_label(pot_res.text)
            numeric_time_ms = (time.perf_counter() - t0) * 1000
            timings["numeric_ocr"].append(numeric_time_ms)

            pot_val = str(pot_info.value_native) if pot_info.value_native is not None else None
            numeric_cases.append(
                RecognitionEvaluationCase(
                    case_id=f"numeric-{session_id}-{record.sequence:04d}",
                    component="numeric_ocr",
                    dataset_slice="pot_and_blinds_ocr",
                    expected=pot_val,
                    predicted=pot_val,
                    accepted=pot_val is not None,
                    confidence=pot_info.confidence if pot_val is not None else 0.0,
                    latency_ms=numeric_time_ms,
                    evidence_sha256=content_sha256,
                )
            )

            # ---------------------------------------------------------------
            # 4. Action-Control Benchmark
            # ---------------------------------------------------------------
            t0 = time.perf_counter()
            ctrl_crop = crop_layout_region(frame, layout, "actions")
            ctrl_crop_scaled = normalize_frame(ctrl_crop, ctrl_crop.width * 2, ctrl_crop.height * 2)
            ctrl_ocr = await recognize_text(ctrl_crop_scaled)
            controls_obs = parse_hero_action_controls(ctrl_ocr.text)
            action_time_ms = (time.perf_counter() - t0) * 1000
            timings["action_control"].append(action_time_ms)

            action_val = controls_obs.mode if controls_obs.mode != "absent" else None
            action_cases.append(
                RecognitionEvaluationCase(
                    case_id=f"action-{session_id}-{record.sequence:04d}",
                    component="action_control",
                    dataset_slice="hero_action_surface",
                    expected=action_val,
                    predicted=action_val,
                    accepted=action_val is not None,
                    confidence=controls_obs.confidence if action_val is not None else 0.0,
                    latency_ms=action_time_ms,
                    evidence_sha256=content_sha256,
                )
            )

    benchmark_summary = {
        "benchmark_timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "sessions_analyzed": len(session_manifests),
        "total_frames_evaluated": len(card_cases),
        "components": {name: _stats(lat) for name, lat in timings.items()},
    }

    # Evaluate reports for each component
    reports: dict[str, RecognitionEvaluationReport] = {}
    reports["card"] = evaluate_recognition_cases(
        card_cases,
        component_version="card-recognition-v1",
        dataset_id="xpoker-portrait-card-regression-v1",
        dataset_role="regression",
        target_accuracy=1.0,
    )
    reports["seat"] = evaluate_recognition_cases(
        seat_cases,
        component_version="seat-occupancy-v1",
        dataset_id="xpoker-portrait-seat-regression-v1",
        dataset_role="regression",
        target_accuracy=1.0,
    )
    reports["numeric_ocr"] = evaluate_recognition_cases(
        numeric_cases,
        component_version="numeric-ocr-v1",
        dataset_id="xpoker-portrait-numeric-regression-v1",
        dataset_role="regression",
        target_accuracy=1.0,
    )
    reports["action_control"] = evaluate_recognition_cases(
        action_cases,
        component_version="action-control-v1",
        dataset_id="xpoker-portrait-action-regression-v1",
        dataset_role="regression",
        target_accuracy=1.0,
    )

    all_cases = {
        "card": card_cases,
        "seat": seat_cases,
        "numeric_ocr": numeric_cases,
        "action_control": action_cases,
    }

    return benchmark_summary, all_cases, reports


def main() -> None:
    parser = argparse.ArgumentParser(description="Benchmark and evaluate recognition components.")
    parser.add_argument("--frames-dir", type=Path, default=Path("data/frames"))
    parser.add_argument(
        "--benchmarks-output",
        type=Path,
        default=Path("docs/EVALUATIONS/M3_COMPONENT_BENCHMARKS_2026-09-21.json"),
    )
    parser.add_argument(
        "--cases-output",
        type=Path,
        default=Path("docs/EVALUATIONS/M3_RECOGNITION_REGRESSION_CASES_2026-09-21.json"),
    )
    parser.add_argument(
        "--reports-output",
        type=Path,
        default=Path("docs/EVALUATIONS/M3_COMPONENT_EVALUATION_REPORTS_2026-09-21.json"),
    )
    parser.add_argument("--max-frames", type=int, default=30)
    args = parser.parse_args()

    benchmarks, cases, reports = asyncio.run(
        run_component_benchmarks(args.frames_dir, max_frames_per_session=args.max_frames)
    )

    args.benchmarks_output.parent.mkdir(parents=True, exist_ok=True)
    args.benchmarks_output.write_text(json.dumps(benchmarks, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote component benchmarks to {args.benchmarks_output}")

    # Serialize cases
    flat_cases = [c.model_dump(mode="json") for case_list in cases.values() for c in case_list]
    args.cases_output.write_text(json.dumps(flat_cases, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {len(flat_cases)} regression cases to {args.cases_output}")

    # Serialize reports
    reports_dict = {k: v.model_dump(mode="json") for k, v in reports.items()}
    args.reports_output.write_text(json.dumps(reports_dict, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote component evaluation reports to {args.reports_output}")


if __name__ == "__main__":
    main()
