from decimal import Decimal
from uuid import NAMESPACE_URL, UUID, uuid5

import pytest
from pydantic import ValidationError

from xpoker_agent.models import Position, StrategyMatch
from xpoker_agent.ranges.library import (
    ObservedRangeAction,
    PreflopSpotKey,
    RangeArtifact,
    RangeLibrary,
    load_seeded_reference_library,
)
from xpoker_agent.strategy.resolver import (
    PreflopStrategyResolver,
    StrategyResolution,
    compare_combo_results,
)

HAND_ID = UUID("60000000-0000-0000-0000-000000000001")


def _button_spot(stack: str = "200") -> PreflopSpotKey:
    return PreflopSpotKey(
        seats=9,
        stack_depth_chips=Decimal(stack),
        player_position=Position.BTN,
        players_remaining=3,
        action_sequence=[
            ObservedRangeAction(actor_position=position, type="fold")
            for position in (
                Position.UTG,
                Position.UTG_1,
                Position.UTG_2,
                Position.LJ,
                Position.HJ,
                Position.CO,
            )
        ],
    )


def _gto_artifact(stack: str = "200") -> RangeArtifact:
    reference = load_seeded_reference_library().lookup(_button_spot()).artifact
    payload = reference.model_dump(mode="json")
    payload.update(
        {
            "artifact_id": str(uuid5(NAMESPACE_URL, f"test-gto-{stack}")),
            "spot": _button_spot(stack).model_dump(mode="json"),
            "title": "Synthetic configuration-matched GTO resolver fixture",
            "source_url": "https://example.invalid/test-gto-fixture",
            "source_license": "Test fixture only",
            "fact_class": "solver_derived",
            "strategy_role": "gto_solution",
            "confidence": 0.9,
            "assumptions": ["synthetic resolver fixture; not production strategy"],
            "version": "test-gto-v1",
        }
    )
    return RangeArtifact.model_validate(payload)


def _gto_artifact_with_combo_results() -> RangeArtifact:
    artifact = _gto_artifact()
    artifact.combos["AsAh"].actions = {"fold": 0.1, "raise@4chips": 0.9}
    artifact.combos["AsAh"].equity = 0.82
    artifact.combos["AsAh"].ev_chips = {"fold": 0.0, "raise@4chips": 3.5}
    return artifact


def test_reference_prior_is_returned_separately_when_gto_is_unavailable() -> None:
    resolver = PreflopStrategyResolver(reference_library=load_seeded_reference_library())

    result = resolver.resolve(_button_spot(), player_ref="hero", hand_id=HAND_ID)

    assert result.match.status == "unavailable"
    assert result.strategy is None
    assert result.reference_prior is not None
    assert result.reference_prior.source["strategy_role"] == "reference_prior"
    assert "not GTO" in result.match.assumptions[-1]


def test_reference_library_cannot_be_installed_as_gto_library() -> None:
    with pytest.raises(ValueError, match="non-GTO"):
        PreflopStrategyResolver(gto_library=load_seeded_reference_library())


def test_exact_gto_artifact_returns_exact_source_backed_strategy() -> None:
    resolver = PreflopStrategyResolver(gto_library=RangeLibrary([_gto_artifact()]))

    result = resolver.resolve(_button_spot(), player_ref="hero", hand_id=HAND_ID)

    assert result.match.status == "exact"
    assert result.match.confidence == 0.9
    assert result.strategy is not None
    assert result.strategy.source["strategy_role"] == "gto_solution"
    assert str(result.match.source_artifact_id) == result.strategy.source["artifact_id"]


def test_nearest_stack_solution_quantifies_mismatch_and_reduces_confidence() -> None:
    resolver = PreflopStrategyResolver(gto_library=RangeLibrary([_gto_artifact()]))

    result = resolver.resolve(_button_spot("180"), player_ref="hero", hand_id=HAND_ID)

    assert result.match.status == "abstracted"
    assert result.match.distance["absolute_mismatch_chips"] == "20"
    assert result.match.confidence == pytest.approx(0.8)
    assert result.strategy is not None
    assert result.match.assumptions[-1] == (
        "Used 200 native-chip solution for 180 native-chip request."
    )


def test_combo_summary_exposes_frequency_equity_ev_and_ev_loss() -> None:
    resolver = PreflopStrategyResolver(
        gto_library=RangeLibrary([_gto_artifact_with_combo_results()])
    )
    resolution = resolver.resolve(_button_spot(), player_ref="hero", hand_id=HAND_ID)

    result = resolver.summarize_combo(resolution, "AsAh")

    assert result.match_status == "exact"
    assert result.strategy_role == "gto_solution"
    assert result.equity == 0.82
    assert [(item.action, item.frequency) for item in result.actions] == [
        ("fold", 0.1),
        ("raise@4chips", 0.9),
    ]
    assert result.actions[0].ev_chips == 0.0
    assert result.actions[0].ev_loss_chips == 3.5
    assert result.actions[1].ev_loss_chips == 0.0


def test_combo_summary_fails_closed_when_no_strategy_is_available() -> None:
    resolver = PreflopStrategyResolver()
    resolution = resolver.resolve(_button_spot(), player_ref="hero", hand_id=HAND_ID)

    with pytest.raises(KeyError, match="no strategy"):
        resolver.summarize_combo(resolution, "AsAh")


def test_combo_comparison_reports_candidate_minus_baseline_deltas() -> None:
    resolver = PreflopStrategyResolver(
        gto_library=RangeLibrary([_gto_artifact_with_combo_results()])
    )
    resolution = resolver.resolve(_button_spot(), player_ref="hero", hand_id=HAND_ID)
    baseline = resolver.summarize_combo(resolution, "AsAh")
    candidate = baseline.model_copy(deep=True)
    candidate.strategy_role = "reference_prior"
    candidate.equity = 0.78
    candidate.actions[0].frequency = 0.2
    candidate.actions[0].ev_chips = 0.25
    candidate.actions[1].frequency = 0.8
    candidate.actions[1].ev_chips = 3.0

    comparison = compare_combo_results(baseline, candidate)

    assert comparison.equity_delta == pytest.approx(-0.04)
    assert comparison.actions[0].action == "fold"
    assert comparison.actions[0].frequency_delta == pytest.approx(0.1)
    assert comparison.actions[0].ev_delta_chips == pytest.approx(0.25)
    assert comparison.actions[1].frequency_delta == pytest.approx(-0.1)
    assert comparison.actions[1].ev_delta_chips == pytest.approx(-0.5)


def test_combo_comparison_rejects_different_physical_combinations() -> None:
    resolver = PreflopStrategyResolver(
        gto_library=RangeLibrary([_gto_artifact_with_combo_results()])
    )
    resolution = resolver.resolve(_button_spot(), player_ref="hero", hand_id=HAND_ID)
    baseline = resolver.summarize_combo(resolution, "AsAh")
    candidate = baseline.model_copy(update={"combo": "AdAc"})

    with pytest.raises(ValueError, match="same exact combination"):
        compare_combo_results(baseline, candidate)


def test_unavailable_unopened_bb_spot_has_no_fake_reference_fallback() -> None:
    resolver = PreflopStrategyResolver(reference_library=load_seeded_reference_library())
    spot = PreflopSpotKey(
        seats=9,
        stack_depth_chips=Decimal("200"),
        player_position=Position.BB,
        players_remaining=2,
        action_sequence=[
            ObservedRangeAction(actor_position=position, type="fold")
            for position in (Position.UTG, Position.HJ, Position.CO, Position.BTN, Position.SB)
        ],
    )

    result = resolver.resolve(spot, player_ref="hero", hand_id=HAND_ID)

    assert result.match.status == "unavailable"
    assert result.strategy is None
    assert result.reference_prior is None


def test_resolution_model_rejects_reference_prior_in_gto_slot() -> None:
    prior = (
        load_seeded_reference_library()
        .lookup(_button_spot())
        .artifact.to_weighted_range(player_ref="hero", hand_id=HAND_ID)
    )

    with pytest.raises(ValidationError, match="gto_solution"):
        StrategyResolution(
            match=StrategyMatch(
                status="exact",
                requested_spot={},
                matched_spot={},
                source_artifact_id=prior.source["artifact_id"],
                confidence=0.55,
            ),
            strategy=prior,
        )
