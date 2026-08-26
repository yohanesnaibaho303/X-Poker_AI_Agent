import json
from uuid import UUID

import pytest

from xpoker_agent.models import ComboStrategy, Street, WeightedRange
from xpoker_agent.ranges.matrix import project_range_matrix

HAND_ID = UUID("50000000-0000-0000-0000-000000000001")


def _range() -> WeightedRange:
    return WeightedRange(
        player_ref="UTG",
        hand_id=HAND_ID,
        street=Street.PREFLOP,
        spot_key="NLH|cash|9max|rake0|open2bb|UTG|remaining9|stack100bb",
        combos={
            "AsAh": ComboStrategy(
                weight=1.0,
                actions={"fold": 0.25, "raise@4chips": 0.75},
                equity=0.8,
                ev_chips={"fold": 0.0, "raise@4chips": 4.0},
            ),
            "AdAc": ComboStrategy(
                weight=0.5,
                actions={"fold": 0.5, "raise@4chips": 0.5},
                equity=0.6,
                ev_chips={"fold": 0.0, "raise@4chips": 2.0},
            ),
            "AsKs": ComboStrategy(weight=1.0, actions={}),
        },
        blocked_cards=["Kh"],
        source={"kind": "synthetic_projection_fixture"},
        confidence=0.9,
        version="test-v1",
    )


def test_matrix_has_stable_169_cell_pair_suited_offsuit_layout() -> None:
    matrix = project_range_matrix(_range())

    assert len(matrix.cells) == 169
    assert matrix.ranks == list("AKQJT98765432")
    assert matrix.cells[0].hand_class == "AA"
    assert matrix.cells[1].hand_class == "AKs"
    assert matrix.cells[13].hand_class == "AKo"
    assert matrix.cells[-1].hand_class == "22"


def test_projection_preserves_combo_mass_mixes_equity_ev_and_empty_actions() -> None:
    matrix = project_range_matrix(_range())
    cells = {cell.hand_class: cell for cell in matrix.cells}
    aces = cells["AA"]

    assert aces.possible_combos == 6
    assert aces.included_combos == 2
    assert aces.combo_weight == 1.5
    assert aces.inclusion_frequency == 0.25
    assert aces.action_mix == pytest.approx({"fold": 1.0 / 3.0, "raise@4chips": 2.0 / 3.0})
    assert aces.unassigned_action_frequency == 0.0
    assert aces.equity == pytest.approx(11.0 / 15.0)
    assert aces.ev_chips["raise@4chips"] == pytest.approx(10.0 / 3.0)
    assert cells["AKs"].possible_combos == 3
    assert cells["AKs"].unassigned_action_frequency == 1.0


def test_projection_is_byte_deterministic_and_carries_inspection_metadata() -> None:
    first = project_range_matrix(_range())
    second = project_range_matrix(_range())

    first_json = json.dumps(first.model_dump(mode="json"), sort_keys=True, separators=(",", ":"))
    second_json = json.dumps(second.model_dump(mode="json"), sort_keys=True, separators=(",", ":"))
    assert first_json == second_json
    assert first.source == {"kind": "synthetic_projection_fixture"}
    assert first.blocked_cards == ["Kh"]
    assert first.confidence == 0.9
