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
from xpoker_agent.strategy.resolver import PreflopStrategyResolver, StrategyResolution

HAND_ID = UUID("60000000-0000-0000-0000-000000000001")


def _button_spot(stack: str = "100") -> PreflopSpotKey:
    return PreflopSpotKey(
        seats=6,
        stack_depth_bb=Decimal(stack),
        player_position=Position.BTN,
        players_remaining=3,
        action_sequence=[
            ObservedRangeAction(actor_position=position, type="fold")
            for position in (Position.UTG, Position.HJ, Position.CO)
        ],
    )


def _gto_artifact(stack: str = "100") -> RangeArtifact:
    reference = load_seeded_reference_library(6).lookup(_button_spot()).artifact
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


def test_reference_prior_is_returned_separately_when_gto_is_unavailable() -> None:
    resolver = PreflopStrategyResolver(reference_library=load_seeded_reference_library(6))

    result = resolver.resolve(_button_spot(), player_ref="hero", hand_id=HAND_ID)

    assert result.match.status == "unavailable"
    assert result.strategy is None
    assert result.reference_prior is not None
    assert result.reference_prior.source["strategy_role"] == "reference_prior"
    assert "not GTO" in result.match.assumptions[-1]


def test_reference_library_cannot_be_installed_as_gto_library() -> None:
    with pytest.raises(ValueError, match="non-GTO"):
        PreflopStrategyResolver(gto_library=load_seeded_reference_library(6))


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

    result = resolver.resolve(_button_spot("90"), player_ref="hero", hand_id=HAND_ID)

    assert result.match.status == "abstracted"
    assert result.match.distance["absolute_mismatch_bb"] == "10"
    assert result.match.confidence == pytest.approx(0.8)
    assert result.strategy is not None


def test_unavailable_unopened_bb_spot_has_no_fake_reference_fallback() -> None:
    resolver = PreflopStrategyResolver(reference_library=load_seeded_reference_library(6))
    spot = PreflopSpotKey(
        seats=6,
        stack_depth_bb=Decimal("100"),
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
        load_seeded_reference_library(6)
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
