from decimal import Decimal
from uuid import UUID

import pytest
from pydantic import ValidationError

from xpoker_agent.models import ComboStrategy, Position, Street
from xpoker_agent.strategy.nodes import (
    StrategyNodeAction,
    StrategyNodeArtifact,
    StrategyNodeKey,
    StrategyNodeLibrary,
)


def _key(*, stack: str = "196", pot: str = "9", board: list[str] | None = None):
    return StrategyNodeKey(
        street=Street.TURN,
        hero_position=Position.BTN,
        opponent_positions=[Position.BB],
        players_remaining=2,
        effective_stack_chips=Decimal(stack),
        pot_chips=Decimal(pot),
        board=board or ["Kd", "Qc", "7h", "2s"],
        action_sequence=[
            StrategyNodeAction(
                actor_position=Position.BTN,
                street=Street.PREFLOP,
                action="raise",
                size_chips=Decimal("4"),
            ),
            StrategyNodeAction(
                actor_position=Position.BB,
                street=Street.PREFLOP,
                action="call",
            ),
            StrategyNodeAction(
                actor_position=Position.BB,
                street=Street.FLOP,
                action="check",
            ),
            StrategyNodeAction(
                actor_position=Position.BTN,
                street=Street.FLOP,
                action="check",
            ),
        ],
        available_actions=["check", "bet@6chips"],
    )


def _artifact(*, stack: str = "196", pot: str = "9") -> StrategyNodeArtifact:
    return StrategyNodeArtifact(
        artifact_id=UUID(f"70000000-0000-0000-0000-{int(stack):012d}"),
        node=_key(stack=stack, pot=pot),
        combos={
            "AsAh": ComboStrategy(
                weight=1,
                actions={"check": 0.25, "bet@6chips": 0.75},
                equity=0.81,
                ev_chips={"check": 8.2, "bet@6chips": 8.5},
            )
        },
        source={"kind": "synthetic_solver_fixture", "license": "test-only"},
        confidence=0.9,
        assumptions=["Synthetic test fixture; not production GTO data."],
        version="test-node-v1",
    )


def test_full_node_exact_lookup_is_deterministic() -> None:
    library = StrategyNodeLibrary([_artifact()])

    first = library.lookup(_key())
    second = library.lookup(_key())

    assert first == second
    assert first.distance.status == "exact"
    assert first.distance.combined_relative_mismatch == 0
    assert first.confidence == 0.9


def test_nearest_node_quantifies_stack_and_pot_mismatch() -> None:
    library = StrategyNodeLibrary([_artifact()])

    result = library.lookup(_key(stack="200", pot="10"))

    assert result.distance.status == "nearest"
    assert result.distance.stack_mismatch_chips == 4
    assert result.distance.pot_mismatch_chips == 1
    assert result.distance.combined_relative_mismatch == Decimal("0.06")
    assert result.confidence == pytest.approx(0.846)


def test_node_lookup_never_abstracts_across_board_or_action_tree() -> None:
    library = StrategyNodeLibrary([_artifact()])

    with pytest.raises(KeyError, match="configuration-compatible"):
        library.lookup(_key(board=["Kd", "Qc", "7h", "3s"]))


def test_node_rejects_bb_sizing_and_board_blocked_combo() -> None:
    payload = _key().model_dump(mode="json")
    payload["available_actions"] = ["check", "bet@3bb"]
    with pytest.raises(ValidationError, match="action sizing"):
        StrategyNodeKey.model_validate(payload)

    artifact = _artifact().model_dump(mode="json")
    artifact["combos"] = {
        "KhKd": {
            "weight": 1,
            "actions": {"check": 0.5, "bet@6chips": 0.5},
            "equity": 0.8,
            "ev_chips": {"check": 8, "bet@6chips": 9},
        }
    }
    with pytest.raises(ValidationError, match="conflicts with the board"):
        StrategyNodeArtifact.model_validate(artifact)
