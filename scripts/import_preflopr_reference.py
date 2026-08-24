"""Import pinned MIT preflopR charts as reference-only opening priors.

The source explicitly says its charts are not solver-derived. Generated artifacts are therefore
low-confidence reference priors and must never be presented as exact GTO solutions.
"""

from __future__ import annotations

import hashlib
import json
import re
import sys
from decimal import Decimal
from pathlib import Path
from urllib.request import urlopen
from uuid import NAMESPACE_URL, UUID, uuid5

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from xpoker_agent.models import ComboStrategy, Position  # noqa: E402
from xpoker_agent.ranges.cards import RANKS_DESCENDING, all_combos, combo_class  # noqa: E402
from xpoker_agent.ranges.library import (  # noqa: E402
    ObservedRangeAction,
    PreflopSpotKey,
    RangeArtifact,
    write_artifact,
)

SOURCE_COMMIT = "aed511d0451aea33a14f7e9204595fc2211f233f"
SOURCE_CONTENT_SHA256 = "75a8a7288bbe39361313ea4183514784f91ab462f9d4c99d3b9d50a8394b6090"
SOURCE_URL = f"https://github.com/bmorrow10/preflopR/blob/{SOURCE_COMMIT}/preflopR.r"
SOURCE_RAW_URL = f"https://raw.githubusercontent.com/bmorrow10/preflopR/{SOURCE_COMMIT}/preflopR.r"
SOURCE_ID = UUID("00000000-0000-0000-0000-000000000114")

POSITION_SOURCES: dict[int, list[tuple[Position, str]]] = {
    6: [
        (Position.UTG, "6_UTG"),
        (Position.HJ, "6_HJ"),
        (Position.CO, "6_CO"),
        (Position.BTN, "6_BTN"),
        (Position.SB, "6_SB"),
    ],
    9: [
        (Position.UTG, "9_UTG"),
        (Position.UTG_1, "9_UTG+1"),
        (Position.MP, "9_UTG+2"),
        (Position.LJ, "9_MP"),
        (Position.HJ, "9_HJ"),
        (Position.CO, "9_CO"),
        (Position.BTN, "9_BTN"),
        (Position.SB, "9_SB"),
    ],
}


def _download_pinned_source() -> str:
    with urlopen(SOURCE_RAW_URL, timeout=30) as response:  # noqa: S310
        content = response.read()
    actual_sha256 = hashlib.sha256(content).hexdigest()
    if actual_sha256 != SOURCE_CONTENT_SHA256:
        raise ValueError(
            f"pinned source hash mismatch: expected {SOURCE_CONTENT_SHA256}, got {actual_sha256}"
        )
    return content.decode("utf-8-sig")


def _parse_source_ranges(source: str) -> dict[str, set[str]]:
    ranges: dict[str, set[str]] = {}
    lines = source.splitlines()
    index = 0
    while index < len(lines):
        match = re.match(r'^\s*"(?P<key>[69]_[^"]+)"\s*=\s*c\(\s*$', lines[index])
        if match is None:
            index += 1
            continue
        key = match.group("key")
        body: list[str] = []
        index += 1
        while index < len(lines) and lines[index].strip() not in {")", "),"}:
            body.append(lines[index])
            index += 1
        text = "\n".join(body)
        classes: set[str] = set()
        pair_match = re.search(r'pairs_down_to\("(?P<rank>[2-9TJQKA])\1?"\)', text)
        if pair_match:
            minimum_index = RANKS_DESCENDING.index(pair_match.group("rank"))
            classes.update(rank * 2 for rank in RANKS_DESCENDING[: minimum_index + 1])
        classes.update(
            f"{high}{low}s"
            for high, low in re.findall(r'suited\("([2-9TJQKA])","([2-9TJQKA])"\)', text)
        )
        classes.update(
            f"{high}{low}o"
            for high, low in re.findall(r'offsuit\("([2-9TJQKA])","([2-9TJQKA])"\)', text)
        )
        if not classes:
            raise ValueError(f"source range {key} parsed without any hand classes")
        ranges[key] = classes
        index += 1
    expected = {source_key for entries in POSITION_SOURCES.values() for _, source_key in entries}
    missing = expected.difference(ranges)
    if missing:
        raise ValueError(f"pinned source is missing expected ranges: {sorted(missing)}")
    return ranges


def _artifact(
    *, seats: int, position_index: int, position: Position, classes: set[str], source_key: str
) -> RangeArtifact:
    entries = POSITION_SOURCES[seats]
    prior_positions = [prior_position for prior_position, _ in entries[:position_index]]
    spot = PreflopSpotKey(
        seats=seats,
        stack_depth_bb=Decimal("100"),
        player_position=position,
        players_remaining=seats - position_index,
        action_sequence=[
            ObservedRangeAction(actor_position=prior_position, type="fold")
            for prior_position in prior_positions
        ],
    )
    strategies = {
        combo: ComboStrategy(
            weight=1.0,
            actions={"raise@2bb": 1.0} if combo_class(combo) in classes else {"fold": 1.0},
        )
        for combo in all_combos()
    }
    return RangeArtifact(
        artifact_id=uuid5(NAMESPACE_URL, f"{SOURCE_URL}|{spot.canonical_key()}"),
        title=f"preflopR {seats}-max {position.value} reference-only RFI prior",
        spot=spot,
        combos=strategies,
        source_id=SOURCE_ID,
        source_url=SOURCE_URL,
        source_license="MIT",
        fact_class="validated_manual_chart",
        strategy_role="reference_prior",
        validation_status="validated",
        confidence=0.55,
        source_commit=SOURCE_COMMIT,
        source_content_sha256=SOURCE_CONTENT_SHA256,
        assumptions=[
            "Source describes these charts as approximate guidelines and explicitly "
            "not solver-derived.",
            "Source does not specify stack, rake, or open sizing; 100 BB, zero-rake, and "
            "2 BB are target indexing metadata, not source-validated claims.",
            "The source chart is pure raise/fold by 169 class; every exact combo inherits "
            "its class action.",
            f"Imported source range key: {source_key}.",
        ],
        version=f"preflopr-{SOURCE_COMMIT[:12]}-reference-v1",
    )


def _write_manifest(seats: int, artifacts: list[tuple[Path, RangeArtifact]]) -> None:
    entries = []
    for path, artifact in artifacts:
        content = path.read_bytes()
        entries.append(
            {
                "artifact_id": str(artifact.artifact_id),
                "path": path.relative_to(PROJECT_ROOT).as_posix(),
                "content_sha256": hashlib.sha256(content).hexdigest(),
                "position": artifact.spot.player_position.value,
                "strategy_role": artifact.strategy_role,
                "confidence": artifact.confidence,
            }
        )
    payload = {
        "schema_version": "1.0",
        "library_id": f"xpoker-{seats}max-nlh-no-rake-2bb-v1",
        "configuration": {
            "variant": "NLH",
            "format": "cash",
            "seats": seats,
            "rake_percent": 0,
            "default_open_size_bb": 2.0,
            "objective": "chip_ev",
            "stack_buckets_bb": [20, 40, 50, 75, 100, 150, 200],
        },
        "status": "reference_priors_seeded",
        "source_id": str(SOURCE_ID),
        "source_commit": SOURCE_COMMIT,
        "source_content_sha256": SOURCE_CONTENT_SHA256,
        "artifacts": entries,
        "notes": [
            "These are low-confidence reference-only RFI priors, not solver-derived GTO solutions.",
            "BB has no unopened RFI artifact; it receives an action only after earlier "
            "preflop actions.",
            "No incompatible table size is substituted, and every artifact records explicit "
            "mismatch assumptions.",
        ],
    }
    manifest_name = "library_manifest_6max.json" if seats == 6 else "library_manifest.json"
    manifest_path = PROJECT_ROOT / "configs" / "ranges" / manifest_name
    manifest_path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def main() -> None:
    source_ranges = _parse_source_ranges(_download_pinned_source())
    for seats, entries in POSITION_SOURCES.items():
        output_dir = PROJECT_ROOT / "data" / "ranges" / "preflopr_reference" / f"{seats}max"
        output_dir.mkdir(parents=True, exist_ok=True)
        for old_artifact in output_dir.glob("*.json"):
            old_artifact.unlink()
        written: list[tuple[Path, RangeArtifact]] = []
        for position_index, (position, source_key) in enumerate(entries):
            artifact = _artifact(
                seats=seats,
                position_index=position_index,
                position=position,
                classes=source_ranges[source_key],
                source_key=source_key,
            )
            path = output_dir / f"rfi_{position.value.replace('+', 'plus').lower()}_100bb.json"
            write_artifact(artifact, path)
            written.append((path, artifact))
        _write_manifest(seats, written)


if __name__ == "__main__":
    main()
