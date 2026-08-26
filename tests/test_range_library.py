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


def _spot(stack: str = "200", *, raise_size: str = "4") -> PreflopSpotKey:
    return PreflopSpotKey(
        stack_depth_chips=Decimal(stack),
        player_position=Position.UTG,
        players_remaining=9,
        action_sequence=[
            ObservedRangeAction(
                actor_position=Position.UTG,
                type="raise",
                size_chips=Decimal(raise_size),
            )
        ],
    )


def _artifact(stack: str = "200", *, validation_status: str = "validated") -> RangeArtifact:
    return RangeArtifact(
        artifact_id=ARTIFACT_ID,
        title="Synthetic format-validation range",
        spot=_spot(stack),
        combos={
            "AsAh": ComboStrategy(
                weight=1.0,
                actions={"fold": 0.25, "raise@4chips": 0.75},
            ),
            "KsKh": ComboStrategy(
                weight=0.5,
                actions={"fold": 0.75, "raise@4chips": 0.25},
            ),
        },
        source_id=SOURCE_ID,
        source_url="https://example.invalid/synthetic-range-fixture",
        source_license="Test fixture only; not strategy data",
        fact_class="solver_derived",
        strategy_role="gto_solution",
        validation_status=validation_status,
        confidence=1.0,
        assumptions=["synthetic values test the artifact format only"],
        version="test-v1",
    )


def test_spot_key_encodes_authoritative_configuration_action_and_size() -> None:
    key = _spot().canonical_key()

    assert key == (
        "NLH|cash|9max|rake0|blinds1-2chips|UTG|remaining9|stack200chips|raise@4chips"
    )
    assert _spot(raise_size="5").canonical_key() != key


def test_artifact_rejects_unsupported_seat_count_rake_open_or_stack_bucket() -> None:
    with pytest.raises(ValidationError):
        PreflopSpotKey(
            seats=7,
            stack_depth_chips=Decimal("100"),
            player_position=Position.UTG,
            players_remaining=6,
        )
    with pytest.raises(ValidationError, match="zero rake"):
        PreflopSpotKey(
            rake_percent=Decimal("0.05"),
            stack_depth_chips=Decimal("100"),
            player_position=Position.UTG,
            players_remaining=9,
        )
    with pytest.raises(ValidationError, match="native blinds"):
        PreflopSpotKey(
            native_big_blind=Decimal("3"),
            stack_depth_chips=Decimal("100"),
            player_position=Position.UTG,
            players_remaining=9,
        )
    with pytest.raises(ValidationError, match="unsupported native-chip stack bucket"):
        _artifact("90")


def test_unvalidated_artifacts_cannot_enter_library_or_weighted_range() -> None:
    artifact = _artifact(validation_status="unvalidated")

    with pytest.raises(ValueError, match="unvalidated"):
        artifact.to_weighted_range(player_ref="UTG", hand_id=HAND_ID)
    with pytest.raises(ValueError, match="only validated"):
        RangeLibrary([artifact])


def test_exact_and_nearest_stack_lookup_report_mismatch() -> None:
    artifact_75 = _artifact("80").model_copy(update={"artifact_id": UUID(int=80)})
    artifact_100 = _artifact("200").model_copy(update={"artifact_id": UUID(int=200)})
    library = RangeLibrary([artifact_75, artifact_100])

    exact = library.lookup(_spot("200"))
    nearest = library.lookup(_spot("180"))

    assert exact.stack_match.status == "exact"
    assert nearest.artifact.spot.stack_depth_chips == 200
    assert nearest.stack_match.status == "nearest"
    assert nearest.stack_match.absolute_mismatch_chips == 20


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
            size_chips=Decimal("4"),
        ),
    )

    assert loaded.model_dump(mode="json") == artifact.model_dump(mode="json")
    assert posterior.combos["AsAh"].weight == pytest.approx(6.0 / 7.0)
    assert posterior.combos["KsKh"].weight == pytest.approx(1.0 / 7.0)


def test_library_rejects_duplicate_canonical_spots() -> None:
    with pytest.raises(ValueError, match="duplicate canonical"):
        RangeLibrary([_artifact(), _artifact().model_copy(update={"artifact_id": UUID(int=99)})])


def test_seed_manifests_publish_reference_priors_without_calling_them_gto() -> None:
    manifest = json.loads(
        (PROJECT_ROOT / "configs" / "ranges" / "library_manifest.json").read_text(encoding="utf-8")
    )

    assert manifest["configuration"] == {
        "variant": "NLH",
        "format": "cash",
        "seats": 9,
        "rake_percent": 0,
        "native_small_blind": 1,
        "native_big_blind": 2,
        "objective": "chip_ev",
        "stack_buckets_chips": [40, 80, 100, 150, 200, 300, 400],
    }
    assert manifest["status"] == "reference_priors_seeded"
    assert len(manifest["artifacts"]) == 8
    assert {entry["strategy_role"] for entry in manifest["artifacts"]} == {"reference_prior"}




def test_six_max_spot_is_rejected() -> None:
    with pytest.raises(ValidationError):
        PreflopSpotKey(
            seats=6,
            stack_depth_chips=Decimal("200"),
            player_position=Position.UTG,
            players_remaining=6,
        )


def test_two_chip_big_blind_cannot_be_encoded_as_opening_raise() -> None:
    with pytest.raises(ValidationError, match="opening raise must exceed"):
        PreflopSpotKey(
            stack_depth_chips=Decimal("200"),
            player_position=Position.UTG,
            players_remaining=9,
            action_sequence=[
                ObservedRangeAction(
                    actor_position=Position.UTG,
                    type="raise",
                    size_chips=Decimal("2"),
                )
            ],
        )


def test_preflop_bet_action_is_rejected_in_favor_of_raise() -> None:
    with pytest.raises(ValidationError, match="must use raise"):
        PreflopSpotKey(
            stack_depth_chips=Decimal("200"),
            player_position=Position.UTG,
            players_remaining=9,
            action_sequence=[
                ObservedRangeAction(
                    actor_position=Position.UTG,
                    type="bet",
                    size_chips=Decimal("4"),
                )
            ],
        )


@pytest.mark.parametrize("action", ["raise@2bb", "raise@200K", "bet", "raise@NaNchips"])
def test_range_artifact_rejects_non_native_or_unsized_monetary_actions(action: str) -> None:
    payload = _artifact().model_dump(mode="json")
    payload["combos"] = {
        "AsAh": {
            "weight": 1.0,
            "actions": {action: 1.0},
            "equity": None,
            "ev_chips": {},
        }
    }

    with pytest.raises(ValidationError, match="native-chip|action sizing|positive finite"):
        RangeArtifact.model_validate(payload)


def test_range_artifact_rejects_ev_for_action_missing_from_strategy() -> None:
    payload = _artifact().model_dump(mode="json")
    payload["combos"] = {
        "AsAh": {
            "weight": 1.0,
            "actions": {"raise@4chips": 1.0},
            "equity": 0.8,
            "ev_chips": {"fold": 0.0, "raise@4chips": 3.5},
        }
    }

    with pytest.raises(ValidationError, match="EV for an unavailable action"):
        RangeArtifact.model_validate(payload)
