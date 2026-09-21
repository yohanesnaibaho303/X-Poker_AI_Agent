"""Inventory local M3 evidence and build an optional action-control regression set."""

from __future__ import annotations

import argparse
import hashlib
import json
import struct
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from xpoker_agent.evaluation import (  # noqa: E402
    RecognitionEvaluationCase,
    evaluate_recognition_cases,
    write_recognition_report,
)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while chunk := handle.read(1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest()


def _bmp_dimensions(path: Path) -> tuple[int, int] | None:
    with path.open("rb") as handle:
        header = handle.read(26)
    if len(header) < 26 or header[:2] != b"BM":
        return None
    width, height = struct.unpack_from("<ii", header, 18)
    return width, abs(height)


def _load_json(path: Path) -> dict[str, Any] | None:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        return None
    return payload if isinstance(payload, dict) else None


def audit_evidence(frames_dir: Path) -> dict[str, Any]:
    files = sorted(path for path in frames_dir.rglob("*") if path.is_file())
    records: list[dict[str, Any]] = []
    hashes: defaultdict[str, list[str]] = defaultdict(list)
    dimensions: Counter[str] = Counter()
    layouts: Counter[str] = Counter()
    recognized_cards: set[str] = set()
    dealer_seats: set[int] = set()
    seat_states: defaultdict[int, set[str]] = defaultdict(set)
    action_types: set[str] = set()
    action_surfaces: set[str] = set()
    hand_modes: set[str] = set()
    numeric_channels: set[str] = set()
    replay_p95: list[float] = []

    for path in files:
        relative = path.relative_to(frames_dir).as_posix()
        digest = _sha256(path)
        hashes[digest].append(relative)
        record: dict[str, Any] = {
            "path": relative,
            "bytes": path.stat().st_size,
            "sha256": digest,
        }
        if path.suffix.casefold() == ".bmp":
            size = _bmp_dimensions(path)
            if size is not None:
                record["dimensions"] = f"{size[0]}x{size[1]}"
                dimensions[record["dimensions"]] += 1
        records.append(record)

        if path.suffix.casefold() != ".json":
            continue
        payload = _load_json(path)
        if payload is None:
            continue
        if isinstance(payload.get("layout_id"), str):
            layouts[payload["layout_id"]] += 1
        for key in ("source_layout_id", "evaluation_layout_id"):
            if isinstance(payload.get(key), str):
                layouts[payload[key]] += 1
        if isinstance(payload.get("p95_total_latency_ms"), int | float):
            replay_p95.append(float(payload["p95_total_latency_ms"]))
        for frame in payload.get("frames", []):
            if not isinstance(frame, dict):
                continue
            recognized_cards.update(frame.get("hero_cards", []))
            recognized_cards.update(frame.get("board_cards", []))
            surface = frame.get("hero_action_surface")
            if isinstance(surface, str):
                action_surfaces.add(surface)
            mode = frame.get("current_hand_mode")
            if isinstance(mode, str):
                hand_modes.add(mode)

        status = payload.get("final_status")
        if not isinstance(status, dict):
            continue
        recognized_cards.update(status.get("recognized_hero_cards", []))
        recognized_cards.update(status.get("recognized_board_cards", []))
        mode = status.get("current_hand_mode")
        if isinstance(mode, str):
            hand_modes.add(mode)
        dealer = status.get("dealer_consensus", {})
        if dealer.get("accepted") and str(dealer.get("value", "")).isdigit():
            dealer_seats.add(int(dealer["value"]))
        for item in status.get("seat_status_consensus", []):
            consensus = item.get("consensus", {})
            if consensus.get("accepted") and isinstance(consensus.get("value"), str):
                seat_states[int(item["seat"])].add(consensus["value"])
        for item in status.get("derived_action_candidates", []):
            if isinstance(item.get("action"), str):
                action_types.add(item["action"])
        controls = status.get("hero_control_consensus", {})
        if controls.get("accepted") and isinstance(controls.get("value"), str):
            action_surfaces.add(controls["value"].split(":", 1)[0])
        if status.get("pot_consensus", {}).get("accepted"):
            numeric_channels.add("pot")
        if any(
            item.get("consensus", {}).get("accepted")
            for item in status.get("seat_stack_consensus", [])
        ):
            numeric_channels.add("stack")
        if status.get("blind_consensus", {}).get("accepted"):
            numeric_channels.add("blind")

    duplicate_groups = [paths for paths in hashes.values() if len(paths) > 1]
    ranks = sorted({card[0] for card in recognized_cards if len(card) == 2})
    suits = sorted({card[1] for card in recognized_cards if len(card) == 2})
    return {
        "schema_version": "1.0",
        "scope": "offline_m3_local_evidence",
        "files": records,
        "summary": {
            "file_count": len(files),
            "total_bytes": sum(record["bytes"] for record in records),
            "extension_counts": dict(
                sorted(Counter(path.suffix.casefold() or "none" for path in files).items())
            ),
            "unique_content_count": len(hashes),
            "duplicate_file_count": sum(len(group) - 1 for group in duplicate_groups),
            "duplicate_group_count": len(duplicate_groups),
            "bmp_dimensions": dict(sorted(dimensions.items())),
            "layouts": dict(sorted(layouts.items())),
        },
        "duplicate_groups": sorted(duplicate_groups, key=lambda group: group[0]),
        "observed_coverage": {
            "recognized_cards": sorted(recognized_cards),
            "ranks": ranks,
            "suits": suits,
            "dealer_seats": sorted(dealer_seats),
            "seat_states_by_seat": {
                str(seat): sorted(states) for seat, states in sorted(seat_states.items())
            },
            "action_types": sorted(action_types),
            "hero_action_surfaces": sorted(action_surfaces),
            "hand_modes": sorted(hand_modes),
            "numeric_channels": sorted(numeric_channels),
            "replay_p95_latency_ms": sorted(replay_p95),
        },
        "gate_gaps": [
            "No frozen unseen holdout partition exists; current evidence is calibration "
            "or regression only.",
            "Card evidence does not establish >=99.5% held-out whole-card accuracy "
            "across all ranks, suits, lighting, and overlays.",
            "Numeric evidence does not establish >=99.0% held-out exact accuracy for "
            "stacks, bets, pots, and side pots.",
            "Seat/action evidence does not establish held-out coverage for every seat, "
            "dealer location, player state, timer, active-player marker, and sizing control.",
            "Recorded exact-layout replay p95 remains above the 200 ms decision-window budget.",
            "Showdown cards and side pots lack sufficient labeled evidence.",
        ],
        "limitations": [
            "Coverage is inferred only from structured privacy-safe records and file "
            "metadata; it is not ground truth.",
            "Raw OCR text and player identity are intentionally excluded.",
            "Observed coverage cannot satisfy a promotion gate without independently "
            "labeled holdout cases.",
        ],
    }


def build_action_control_regression(
    replay_path: Path, expected_surface: str
) -> list[RecognitionEvaluationCase]:
    payload = _load_json(replay_path)
    if payload is None or not payload.get("layout_exact"):
        raise ValueError("action-control regression requires an exact-layout replay report")
    cases: list[RecognitionEvaluationCase] = []
    for frame in payload.get("frames", []):
        predicted = frame.get("hero_action_surface")
        cases.append(
            RecognitionEvaluationCase(
                case_id=f"{payload['replay_id']}:{int(frame['sequence']):06d}",
                component="action_control",
                dataset_slice="portrait_9max_pre_action",
                expected=expected_surface,
                predicted=predicted if isinstance(predicted, str) else None,
                accepted=isinstance(predicted, str),
                confidence=0.0,
                latency_ms=float(frame["total_latency_ms"]),
                evidence_sha256=frame["content_sha256"],
            )
        )
    if not cases:
        raise ValueError("action-control regression replay contains no frames")
    return cases


def _write_json(payload: Any, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("frames_dir", type=Path)
    parser.add_argument("audit_output", type=Path)
    parser.add_argument("--pre-action-replay", type=Path)
    parser.add_argument("--cases-output", type=Path)
    parser.add_argument("--report-output", type=Path)
    args = parser.parse_args()

    _write_json(audit_evidence(args.frames_dir), args.audit_output)
    optional = (args.pre_action_replay, args.cases_output, args.report_output)
    if any(optional):
        if not all(optional):
            parser.error("all regression output arguments are required together")
        cases = build_action_control_regression(args.pre_action_replay, "pre_action")
        _write_json([case.model_dump(mode="json") for case in cases], args.cases_output)
        report = evaluate_recognition_cases(
            cases,
            component_version="hero-action-surface-v1",
            dataset_id="xpoker-portrait-9max-pre-action-regression-v1",
            dataset_role="regression",
            target_accuracy=1.0,
        )
        report = report.model_copy(
            update={
                "limitations": [
                    *report.limitations,
                    "Ground truth is limited to one manually observed pre-action sequence.",
                    "Per-frame confidence was not retained by the source replay and is "
                    "reported as 0.0.",
                    "Total diagnostic latency includes capture and all recognition work, "
                    "not action controls alone.",
                ]
            }
        )
        write_recognition_report(report, args.report_output)


if __name__ == "__main__":
    main()
