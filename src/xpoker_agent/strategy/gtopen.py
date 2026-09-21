"""Import owner-authorized GTOpen preflop nodes without copying solver code."""

from __future__ import annotations

import hashlib
import json
from decimal import Decimal
from typing import Literal
from uuid import NAMESPACE_URL, uuid5

from pydantic import BaseModel, ConfigDict, Field, model_validator

from xpoker_agent.models import ComboStrategy, Position, positions_for_table_size
from xpoker_agent.ranges.cards import expand_hand_class
from xpoker_agent.ranges.library import ObservedRangeAction, PreflopSpotKey, RangeArtifact

SOURCE_URL = "https://github.com/MatthewPDingle/GTOpen"
SOURCE_ID = uuid5(NAMESPACE_URL, SOURCE_URL)
SOURCE_LICENSE = "Owner-authorized private educational use"
MODEL_ABSTRACTION = (
    "GTOpen 169-class multiway preflop equilibrium over a pairwise-equity "
    "and raw postflop-realization model"
)
POSITIONS = positions_for_table_size(9)
RANKS_ASCENDING = "23456789TJQKA"


class GTOpenAction(BaseModel):
    model_config = ConfigDict(extra="ignore")

    kind: Literal["fold", "check", "call", "raise", "jam"]
    to: Decimal = Field(ge=0)


class GTOpenNode(BaseModel):
    model_config = ConfigDict(extra="ignore")

    kind: Literal["action"]
    actor: int = Field(ge=0, le=7)
    actor_pos: Position
    positions: list[Position]
    pot: Decimal
    actions: list[GTOpenAction]
    strategy: list[float]

    @model_validator(mode="after")
    def validate_root_sequence_node(self) -> GTOpenNode:
        if self.positions != POSITIONS or self.actor_pos != POSITIONS[self.actor]:
            raise ValueError("GTOpen node positions do not match authoritative 9-max order")
        if self.pot != 3:
            raise ValueError("GTOpen node must contain exact SB 1 plus BB 2 pot")
        if len(self.strategy) != len(self.actions) * 169:
            raise ValueError("GTOpen strategy must contain one 169-class vector per action")
        return self


class GTOpenStatus(BaseModel):
    model_config = ConfigDict(extra="ignore")

    state: Literal["done"]
    iteration: int = Field(gt=0)
    gaps: list[float]
    gap_total: float = Field(ge=0)


def _class_label(index: int) -> str:
    row, column = divmod(index, 13)
    if row == column:
        return RANKS_ASCENDING[row] * 2
    if row > column:
        return f"{RANKS_ASCENDING[row]}{RANKS_ASCENDING[column]}s"
    return f"{RANKS_ASCENDING[column]}{RANKS_ASCENDING[row]}o"


def _action_key(action: GTOpenAction) -> str:
    kind = "all_in" if action.kind == "jam" else action.kind
    if kind in {"raise", "all_in"}:
        return f"{kind}@{format(action.to.normalize(), 'f')}chips"
    return kind


def import_gtopen_rfi_node(
    node_payload: dict[str, object],
    status_payload: dict[str, object],
    *,
    source_commit: str,
    authorization_note: str,
    stack_chips: Decimal = Decimal("200"),
    maximum_gap: float = 0.01,
) -> RangeArtifact:
    node = GTOpenNode.model_validate(node_payload)
    status = GTOpenStatus.model_validate(status_payload)
    if status.gap_total > maximum_gap:
        raise ValueError(f"GTOpen convergence gap {status.gap_total} exceeds {maximum_gap}")
    if len(status.gaps) != 9:
        raise ValueError("GTOpen status must report all nine player gaps")
    action_keys = [_action_key(action) for action in node.actions]
    if len(action_keys) != len(set(action_keys)):
        raise ValueError("GTOpen node contains duplicate canonical actions")

    combos: dict[str, ComboStrategy] = {}
    for class_index in range(169):
        frequencies = [
            node.strategy[action_index * 169 + class_index]
            for action_index in range(len(node.actions))
        ]
        total = sum(frequencies)
        if total <= 0:
            raise ValueError(f"GTOpen class {_class_label(class_index)} has no strategy mass")
        actions = {
            key: frequency / total for key, frequency in zip(action_keys, frequencies, strict=True)
        }
        for combo in expand_hand_class(_class_label(class_index)):
            combos[combo] = ComboStrategy(weight=1, actions=actions)

    raw_payload = json.dumps(
        {"node": node_payload, "status": status_payload},
        sort_keys=True,
        separators=(",", ":"),
    ).encode()
    source_hash = hashlib.sha256(raw_payload).hexdigest()
    spot = PreflopSpotKey(
        stack_depth_chips=stack_chips,
        player_position=node.actor_pos,
        players_remaining=9 - node.actor,
        action_sequence=[
            ObservedRangeAction(actor_position=position, type="fold")
            for position in POSITIONS[: node.actor]
        ],
    )
    artifact_id = uuid5(SOURCE_ID, f"{source_commit}:{spot.canonical_key()}:{source_hash}")
    return RangeArtifact(
        artifact_id=artifact_id,
        title=f"GTOpen 9-max {node.actor_pos.value} model-derived RFI solution",
        spot=spot,
        combos=combos,
        source_id=SOURCE_ID,
        source_url=SOURCE_URL,
        source_license=SOURCE_LICENSE,
        fact_class="solver_derived",
        strategy_role="gto_solution",
        validation_status="validated",
        model_abstraction=MODEL_ABSTRACTION,
        confidence=0.35,
        source_commit=source_commit,
        source_content_sha256=source_hash,
        assumptions=[
            authorization_note,
            "All source inputs used native chips directly: SB 1, BB 2, stack 200, "
            "pot 3, raise to 4.",
            "The action tree allows one raise, no limps, no all-ins, no ante, and zero rake.",
            "GTOpen solves 169 hand classes; every physical combo inherits its class frequency.",
            "Multiway showdown equity and postflop realization are model approximations; "
            "this is not a full-game exact equilibrium.",
            "Per-action EV and equity are unavailable from this GTOpen node export.",
            f"Reported convergence gap was {status.gap_total} after {status.iteration} iterations.",
        ],
        version=f"gtopen-{source_commit[:12]}-native-rfi-v1",
    )
