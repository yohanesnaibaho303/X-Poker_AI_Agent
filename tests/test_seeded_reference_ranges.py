from decimal import Decimal
from uuid import UUID

import pytest

from xpoker_agent.models import Position
from xpoker_agent.ranges.cards import expand_hand_class
from xpoker_agent.ranges.library import (
    ObservedRangeAction,
    PreflopSpotKey,
    load_seeded_reference_library,
)
from xpoker_agent.ranges.matrix import project_range_matrix


@pytest.mark.parametrize(("table_size", "artifact_count"), [(9, 8)])
def test_seeded_reference_libraries_are_isolated_and_complete_without_bb(
    table_size: int, artifact_count: int
) -> None:
    library = load_seeded_reference_library()

    assert len(library.artifacts) == artifact_count
    assert {artifact.spot.seats for artifact in library.artifacts} == {table_size}
    assert {artifact.strategy_role for artifact in library.artifacts} == {"reference_prior"}
    assert all(artifact.confidence == 0.55 for artifact in library.artifacts)
    assert Position.BB not in {artifact.spot.player_position for artifact in library.artifacts}


def test_nine_max_button_prior_expands_to_all_exact_combos_and_renders_actions() -> None:
    library = load_seeded_reference_library()
    spot = PreflopSpotKey(
        seats=9,
        stack_depth_chips=Decimal("200"),
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

    artifact = library.lookup(spot).artifact
    weighted = artifact.to_weighted_range(
        player_ref="hero",
        hand_id=UUID("50000000-0000-0000-0000-000000000001"),
    )
    matrix = project_range_matrix(weighted)

    assert len(artifact.combos) == 1326
    assert artifact.combos["AsAh"].actions == {"raise@4chips": 1.0}
    assert artifact.combos[expand_hand_class("72o")[0]].actions == {"fold": 1.0}
    assert len(matrix.cells) == 169
    assert matrix.confidence == 0.55
    assert matrix.source["strategy_role"] == "reference_prior"


def test_nine_max_position_translation_and_prior_folds_are_explicit() -> None:
    library = load_seeded_reference_library()
    middle = next(
        artifact
        for artifact in library.artifacts
        if artifact.spot.player_position is Position.UTG_2
    )
    lojack = next(
        artifact for artifact in library.artifacts if artifact.spot.player_position is Position.LJ
    )

    assert middle.assumptions[-1] == "Imported source range key: 9_UTG+2."
    assert lojack.assumptions[-1] == "Imported source range key: 9_MP."
    assert [action.actor_position for action in lojack.spot.action_sequence] == [
        Position.UTG,
        Position.UTG_1,
        Position.UTG_2,
    ]
    assert lojack.spot.players_remaining == 6
