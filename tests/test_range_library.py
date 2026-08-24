import json
from decimal import Decimal
from pathlib import Path
from uuid import UUID

import pytest
from pydantic import ValidationError

from xpoker_agent.models import ComboStrategy, Position
from xpoker_agent.ranges.engine import condition_on_observed_action
from xpoker_agent.ranges.library import (
    ObservedRangeAction,
    PreflopSpotKey,
    RangeArtifact,
    RangeLibrary,
    write_artifact,
)

ARTIFACT_ID = UUID("40000000-0000-0000-0000-000000000001")
SOURCE_ID = UUID("40000000-0000-0000-0000-000000000002")
HAND_ID = UUID("40000000-0000-0000-0000-000000000003")
PROJECT_ROOT = Path(__file__).resolve().parents[1]


def _spot(stack: str = "100", *, raise_size: str = "2") -> PreflopSpotKey:
    return PreflopSpotKey(
        stack_depth_bb=Decimal(stack),
        player_position=Position.UTG,
        players_remaining=9,
        action_sequence=[
            ObservedRangeAction(
                actor_position=Position.UTG,
                type="raise",
                size_bb=Decimal(raise_size),
            )
        ],
    )


def _artifact(stack: str = "100", *, validation_status: str = "validated") -> RangeArtifact:
    return RangeArtifact(
        artifact_id=ARTIFACT_ID,
        title="Synthetic format-validation range",
        spot=_spot(stack),
        combos={
            "AsAh": ComboStrategy(
                weight=1.0,
                actions={"fold": 0.25, "raise@2bb": 0.75},
            ),
            "KsKh": ComboStrategy(
                weight=0.5,
                actions={"fold": 0.75, "raise@2bb": 0.25},
            ),
        },
        source_id=SOURCE_ID,
        source_url="https://example.invalid/synthetic-range-fixture",
        source_license="Test fixture only; not strategy data",
        fact_class="solver_derived",
        validation_status=validation_status,
        assumptions=["synthetic values test the artifact format only"],
        version="test-v1",
    )


def test_spot_key_encodes_authoritative_configuration_action_and_size() -> None:
    key = _spot().canonical_key()

    assert key == "NLH|cash|9max|rake0|open2bb|UTG|remaining9|stack100bb|raise@2bb"
    assert _spot(raise_size="2.5").canonical_key() != key


def test_artifact_rejects_wrong_seat_count_rake_open_or_stack_bucket() -> None:
    with pytest.raises(ValidationError):
        PreflopSpotKey(
            seats=6,
            stack_depth_bb=Decimal("100"),
            player_position=Position.UTG,
            players_remaining=6,
        )
    with pytest.raises(ValidationError, match="zero rake"):
        PreflopSpotKey(
            rake_percent=Decimal("0.05"),
            stack_depth_bb=Decimal("100"),
            player_position=Position.UTG,
            players_remaining=9,
        )
    with pytest.raises(ValidationError, match="2 BB"):
        PreflopSpotKey(
            default_open_size_bb=Decimal("2.5"),
            stack_depth_bb=Decimal("100"),
            player_position=Position.UTG,
            players_remaining=9,
        )
    with pytest.raises(ValidationError, match="unsupported stack bucket"):
        _artifact("90")


def test_unvalidated_artifacts_cannot_enter_library_or_weighted_range() -> None:
    artifact = _artifact(validation_status="unvalidated")

    with pytest.raises(ValueError, match="unvalidated"):
        artifact.to_weighted_range(player_ref="UTG", hand_id=HAND_ID)
    with pytest.raises(ValueError, match="only validated"):
        RangeLibrary([artifact])


def test_exact_and_nearest_stack_lookup_report_mismatch() -> None:
    artifact_75 = _artifact("75").model_copy(update={"artifact_id": UUID(int=75)})
    artifact_100 = _artifact("100").model_copy(update={"artifact_id": UUID(int=100)})
    library = RangeLibrary([artifact_75, artifact_100])

    exact = library.lookup(_spot("100"))
    nearest = library.lookup(_spot("90"))

    assert exact.stack_match.status == "exact"
    assert nearest.artifact.spot.stack_depth_bb == 100
    assert nearest.stack_match.status == "nearest"
    assert nearest.stack_match.absolute_mismatch_bb == 10


def test_artifact_round_trip_and_action_sizing_conditioning(tmp_path) -> None:
    artifact = _artifact()
    path = tmp_path / "ranges" / "utg-100.json"
    write_artifact(artifact, path)
    library = RangeLibrary.load_directory(path.parent)
    loaded = library.lookup(_spot()).artifact
    weighted = loaded.to_weighted_range(player_ref="UTG", hand_id=HAND_ID)

    posterior = condition_on_observed_action(
        weighted,
        ObservedRangeAction(
            actor_position=Position.UTG,
            type="raise",
            size_bb=Decimal("2"),
        ),
    )

    assert loaded.model_dump(mode="json") == artifact.model_dump(mode="json")
    assert posterior.combos["AsAh"].weight == pytest.approx(6.0 / 7.0)
    assert posterior.combos["KsKh"].weight == pytest.approx(1.0 / 7.0)


def test_library_rejects_duplicate_canonical_spots() -> None:
    with pytest.raises(ValueError, match="duplicate canonical"):
        RangeLibrary([_artifact(), _artifact().model_copy(update={"artifact_id": UUID(int=99)})])


def test_seed_manifest_refuses_incompatible_strategy_substitution() -> None:
    manifest = json.loads(
        (PROJECT_ROOT / "configs" / "ranges" / "library_manifest.json").read_text(encoding="utf-8")
    )

    assert manifest["configuration"] == {
        "variant": "NLH",
        "format": "cash",
        "seats": 9,
        "rake_percent": 0,
        "default_open_size_bb": 2.0,
        "objective": "chip_ev",
        "stack_buckets_bb": [20, 40, 50, 75, 100, 150, 200],
    }
    assert manifest["status"] == "awaiting_validated_strategy_artifacts"
    assert manifest["artifacts"] == []
