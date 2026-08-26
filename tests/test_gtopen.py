from decimal import Decimal
from uuid import UUID

import pytest

from xpoker_agent.models import Position
from xpoker_agent.ranges.library import ObservedRangeAction, PreflopSpotKey, load_seeded_gto_library
from xpoker_agent.strategy.gtopen import import_gtopen_rfi_node
from xpoker_agent.strategy.resolver import PreflopStrategyResolver


def _node(actor: int = 0) -> dict[str, object]:
    return {
        "kind": "action",
        "actor": actor,
        "actor_pos": ["UTG", "UTG+1", "UTG+2", "LJ", "HJ", "CO", "BTN", "SB"][actor],
        "positions": ["UTG", "UTG+1", "UTG+2", "LJ", "HJ", "CO", "BTN", "SB", "BB"],
        "pot": 3,
        "actions": [{"kind": "fold", "to": 0}, {"kind": "raise", "to": 4}],
        "strategy": [0.75] * 169 + [0.25] * 169,
    }


def _status(gap: float = 0.001) -> dict[str, object]:
    return {"state": "done", "iteration": 100, "gaps": [gap / 9] * 9, "gap_total": gap}


def test_gtopen_import_expands_classes_and_marks_model_abstraction() -> None:
    artifact = import_gtopen_rfi_node(
        _node(actor=5),
        _status(),
        source_commit="a" * 40,
        authorization_note="Owner authorization recorded by the user.",
    )

    assert artifact.spot.player_position.value == "CO"
    assert artifact.spot.stack_depth_chips == Decimal("200")
    assert artifact.spot.players_remaining == 4
    assert len(artifact.spot.action_sequence) == 5
    assert len(artifact.combos) == 1326
    assert artifact.combos["AsAh"].actions == {"fold": 0.75, "raise@4chips": 0.25}
    assert artifact.model_abstraction is not None


def test_gtopen_import_rejects_wrong_scope_or_convergence() -> None:
    wrong_pot = _node()
    wrong_pot["pot"] = 1
    with pytest.raises(ValueError, match="SB 1 plus BB 2"):
        import_gtopen_rfi_node(
            wrong_pot,
            _status(),
            source_commit="a" * 40,
            authorization_note="Owner authorized.",
        )

    with pytest.raises(ValueError, match="convergence gap"):
        import_gtopen_rfi_node(
            _node(),
            _status(0.1),
            source_commit="a" * 40,
            authorization_note="Owner authorized.",
        )


def test_seeded_gtopen_library_is_hash_verified_and_model_abstracted() -> None:
    library = load_seeded_gto_library()

    assert len(library.artifacts) == 8
    assert {artifact.spot.player_position for artifact in library.artifacts} == set(Position) - {
        Position.BB
    }
    assert all(artifact.model_abstraction for artifact in library.artifacts)

    spot = PreflopSpotKey(
        stack_depth_chips=Decimal("200"),
        player_position=Position.BTN,
        players_remaining=3,
        action_sequence=[
            ObservedRangeAction(actor_position=position, type="fold")
            for position in list(Position)[:6]
        ],
    )
    result = PreflopStrategyResolver(gto_library=library).resolve(
        spot,
        player_ref="hero",
        hand_id=UUID("60000000-0000-0000-0000-000000000001"),
    )
    assert result.match.status == "abstracted"
    assert result.strategy is not None
