from __future__ import annotations

import argparse
import hashlib
import json
from urllib.request import Request, urlopen

from xpoker_agent.ranges.library import (
    PROJECT_ROOT,
    RangeLibraryManifest,
    RangeManifestEntry,
    write_artifact,
)
from xpoker_agent.strategy.gtopen import SOURCE_ID, import_gtopen_rfi_node


def _json_request(url: str, payload: dict[str, object] | None = None) -> dict[str, object]:
    data = None if payload is None else json.dumps(payload).encode()
    request = Request(url, data=data, headers={"Content-Type": "application/json"})
    with urlopen(request, timeout=30) as response:  # noqa: S310 - fixed local solver URL
        result = json.load(response)
    if not isinstance(result, dict):
        raise ValueError(f"expected JSON object from {url}")
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description="Import owner-authorized GTOpen RFI nodes")
    parser.add_argument("--source-commit", required=True)
    parser.add_argument("--url", default="http://127.0.0.1:3737")
    parser.add_argument(
        "--authorization-note",
        default=(
            "User attested direct authorization from GTOpen owner Matthew PDingle for "
            "private educational use on 2026-08-26."
        ),
    )
    args = parser.parse_args()

    status = _json_request(f"{args.url}/api/preflop/status")
    output_dir = PROJECT_ROOT / "data" / "ranges" / "gtopen" / "9max" / "native_200chips"
    entries = []
    hashes = []
    for actor in range(8):
        node = _json_request(f"{args.url}/api/preflop/node", {"path": [0] * actor})
        artifact = import_gtopen_rfi_node(
            node,
            status,
            source_commit=args.source_commit,
            authorization_note=args.authorization_note,
        )
        path = output_dir / f"rfi_{artifact.spot.player_position.name.lower()}.json"
        write_artifact(artifact, path)
        content_hash = hashlib.sha256(path.read_bytes()).hexdigest()
        hashes.append(content_hash)
        entries.append(
            RangeManifestEntry(
                artifact_id=artifact.artifact_id,
                path=path.relative_to(PROJECT_ROOT).as_posix(),
                content_sha256=content_hash,
                position=artifact.spot.player_position,
                strategy_role="gto_solution",
                confidence=artifact.confidence,
            )
        )

    collection_hash = hashlib.sha256("".join(hashes).encode()).hexdigest()
    manifest = RangeLibraryManifest(
        library_id="gtopen-owner-authorized-9max-native-rfi-v1",
        configuration={
            "variant": "NLH",
            "format": "cash",
            "seats": 9,
            "rake_percent": 0,
            "native_small_blind": 1,
            "native_big_blind": 2,
            "stack_depth_chips": 200,
            "pot_chips": 3,
            "open_raise_chips": 4,
            "model_abstraction": "GTOpen raw preflop terminal model",
        },
        status="gto_solutions_seeded",
        source_id=SOURCE_ID,
        source_commit=args.source_commit,
        source_content_sha256=collection_hash,
        artifacts=entries,
        notes=[
            args.authorization_note,
            "Every artifact is model-abstracted and must never display as exact GTO.",
            "BB has no unopened RFI decision.",
        ],
    )
    manifest_path = PROJECT_ROOT / "configs" / "ranges" / "gtopen_manifest.json"
    manifest_path.write_text(
        json.dumps(manifest.model_dump(mode="json"), indent=2) + "\n", encoding="utf-8"
    )


if __name__ == "__main__":
    main()
