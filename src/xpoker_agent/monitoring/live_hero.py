"""Fail-closed deterministic hero calculations from accepted live observations."""

from __future__ import annotations

from decimal import Decimal, InvalidOperation
from functools import lru_cache
from typing import Literal

from xpoker_agent.models import (
    EventCategory,
    ParticipationStatus,
    Position,
    Street,
    StrictModel,
    positions_for_table_size,
)
from xpoker_agent.poker_math import (
    effective_stack,
    pot_odds_required_equity,
    stack_to_pot_ratio,
)
from xpoker_agent.ranges.cards import canonical_combo, combo_class
from xpoker_agent.ranges.library import (
    ObservedRangeAction,
    PreflopSpotKey,
    load_seeded_gto_library,
)
from xpoker_agent.strategy.resolver import (
    ComboActionResult,
    PreflopStrategyResolver,
    StrategyComboResult,
)
from xpoker_agent.vision.models import LiveObservationStatus


class LiveHeroCalculation(StrictModel):
    hero_seat: int | None = None
    hero_seat_confidence: float = 0.0
    hero_position: Position | None = None
    dealt_player_count: int = 0
    range_seat_mismatch: int = 0
    cards: list[str]
    hand_class: str | None = None
    hero_stack_chips: Decimal | None = None
    pot_chips: Decimal | None = None
    call_amount_chips: Decimal | None = None
    effective_stack_chips: Decimal | None = None
    required_equity: Decimal | None = None
    spr: Decimal | None = None
    action_surface: Literal["absent", "pre_action", "decision", "ambiguous"] = (
        "ambiguous"
    )
    legal_actions: list[str] = []
    strategy_status: Literal["exact", "abstracted", "unavailable"] = "unavailable"
    strategy_role: Literal["gto_solution", "none"] = "none"
    strategy_confidence: float = 0.0
    strategy_source_artifact_id: str | None = None
    strategy_equity: float | None = None
    strategy_actions: list[ComboActionResult] = []
    strategy_assumptions: list[str] = []
    recommended_action: str | None = None
    recommendation_ready: bool = False
    recommendation_issues: list[str] = []
    ready: bool
    issues: list[str]
    assumptions: list[str]


def _accepted_decimal(value: str | None) -> Decimal | None:
    if value is None:
        return None
    try:
        return Decimal(value)
    except InvalidOperation:
        return None


def _call_amount(status: LiveObservationStatus) -> Decimal | None:
    controls = status.hero_control_consensus
    if (
        not controls.accepted
        or controls.value is None
        or not controls.value.startswith("decision:")
    ):
        return None
    token = controls.value.rsplit(":", maxsplit=1)[-1]
    return _accepted_decimal(token) if token else Decimal("0")


def _legal_actions(status: LiveObservationStatus) -> list[str]:
    controls = status.hero_control_consensus
    if not controls.accepted or not controls.value.startswith("decision:"):
        return []
    return [action for action in controls.value.split(":", maxsplit=2)[1].split(",") if action]


@lru_cache(maxsize=1)
def _strategy_resolver() -> PreflopStrategyResolver:
    return PreflopStrategyResolver(gto_library=load_seeded_gto_library())


def _resolve_strategy(
    status: LiveObservationStatus, cards: list[str], legal_actions: list[str]
) -> tuple[StrategyComboResult | None, list[str]]:
    prefix = status.canonical_hand
    if prefix is None:
        return None, ["canonical_hand_not_ready"]
    state = prefix.state
    if state.street is not Street.PREFLOP:
        return None, ["live_gto_artifact_unavailable_for_street"]
    if state.next_to_act_seat != state.hero_seat:
        return None, ["hero_not_next_to_act"]
    if state.hero_position is None or state.hero_position != status.detected_hero_position:
        return None, ["canonical_hero_position_mismatch"]
    if state.hero_cards != cards:
        return None, ["canonical_hero_cards_mismatch"]
    occupied_positions = {
        seat.position for seat in state.seats if seat.starting_stack_chips > 0
    }
    if None in occupied_positions or not 3 <= len(occupied_positions) <= 9:
        return None, ["canonical_starting_ring_unavailable"]
    position_order = positions_for_table_size(9)
    positions_before_hero = position_order[: position_order.index(state.hero_position)]
    observed_folds: list[Position] = []
    for event in prefix.events:
        if event.category is not EventCategory.BETTING_ACTION or event.street is not Street.PREFLOP:
            continue
        if event.type != "fold" or event.actor_seat is None:
            return None, ["live_gto_artifact_supports_unopened_preflop_only"]
        position = state.seats[event.actor_seat].position
        if position is None:
            return None, ["canonical_action_position_missing"]
        observed_folds.append(position)
    if observed_folds != [
        position for position in positions_before_hero if position in occupied_positions
    ]:
        return None, ["canonical_unopened_action_sequence_incomplete"]
    action_sequence = [
        ObservedRangeAction(actor_position=position, type="fold")
        for position in positions_before_hero
    ]

    active = sum(
        seat.participation in {ParticipationStatus.ACTIVE, ParticipationStatus.ALL_IN}
        for seat in state.seats
    )
    spot = PreflopSpotKey(
        stack_depth_chips=state.seats[state.hero_seat].starting_stack_chips,
        player_position=state.hero_position,
        players_remaining=active,
        action_sequence=action_sequence,
    )
    resolution = _strategy_resolver().resolve(
        spot, player_ref="hero", hand_id=state.hand_id
    )
    if resolution.strategy is None:
        return None, ["compatible_gto_strategy_unavailable"]
    result = _strategy_resolver().summarize_combo(
        resolution, canonical_combo(cards[0], cards[1])
    )
    if len(occupied_positions) < 9:
        result = result.model_copy(
            update={
                "confidence": result.confidence * len(occupied_positions) / 9,
                "assumptions": [
                    *result.assumptions,
                    f"Mapped {len(occupied_positions)} dealt players to the nearest 9-max RFI "
                    "abstraction by treating absent earlier positions as folded; dead-card effects "
                    "are unavailable.",
                ],
            }
        )
    if any(action.action.split("@", 1)[0] not in legal_actions for action in result.actions):
        return None, ["strategy_actions_conflict_with_live_controls"]
    return result, []


def build_live_hero_calculation(status: LiveObservationStatus) -> LiveHeroCalculation:
    issues: list[str] = []
    seat = status.detected_hero_seat
    if seat is None:
        issues.append("hero_seat_not_detected")
    cards = list(status.recognized_hero_cards) if status.hero_cards_accepted else []
    hand_class: str | None = None
    if len(cards) == 2:
        hand_class = combo_class(canonical_combo(cards[0], cards[1]))
    else:
        issues.append("hero_cards_not_detected")
    if status.detected_hero_position is None:
        issues.append("hero_position_not_resolved")
    action_surface: Literal["absent", "pre_action", "decision", "ambiguous"] = "ambiguous"
    if status.hero_control_consensus.accepted and status.hero_control_consensus.value:
        action_surface = status.hero_control_consensus.value.split(":", 1)[0]  # type: ignore[assignment]
    if action_surface != "decision":
        issues.append("hero_decision_surface_not_active")
    legal_actions = _legal_actions(status)

    stack_values = {
        item.seat: _accepted_decimal(item.consensus.value)
        for item in status.seat_stack_consensus
        if item.consensus.accepted
    }
    hero_stack = stack_values.get(seat) if seat is not None else None
    if hero_stack is None:
        issues.append("hero_stack_not_stable")
    pot = (
        _accepted_decimal(status.pot_consensus.value)
        if status.pot_consensus.accepted
        else None
    )
    if pot is None:
        issues.append("pot_not_stable")
    call = _call_amount(status)

    opponent_stacks_chips = [
        amount
        for opponent, amount in stack_values.items()
        if amount is not None
        and opponent != seat
        and opponent in status.active_seats
    ]
    effective_chips = (
        effective_stack(hero_stack, *opponent_stacks_chips)
        if hero_stack is not None and opponent_stacks_chips
        else None
    )
    required_equity = (
        pot_odds_required_equity(pot, call)
        if pot is not None and call is not None and call > 0
        else None
    )
    spr = (
        stack_to_pot_ratio(effective_chips, pot)
        if effective_chips is not None and pot is not None and pot > 0
        else None
    )
    strategy = None
    recommendation_issues: list[str] = []
    if len(cards) == 2 and action_surface == "decision":
        try:
            strategy, recommendation_issues = _resolve_strategy(status, cards, legal_actions)
        except (KeyError, ValueError):
            recommendation_issues = ["compatible_gto_strategy_unavailable"]
    else:
        recommendation_issues = ["hero_decision_context_not_ready"]
    strategy_actions = strategy.actions if strategy is not None else []
    recommended_action = (
        max(strategy_actions, key=lambda action: (action.frequency, action.action)).action
        if strategy_actions
        else None
    )

    return LiveHeroCalculation(
        hero_seat=seat,
        hero_seat_confidence=status.hero_seat_confidence,
        hero_position=status.detected_hero_position,
        dealt_player_count=len(status.active_seats),
        range_seat_mismatch=max(0, status.table_size - len(status.active_seats)),
        cards=cards,
        hand_class=hand_class,
        hero_stack_chips=hero_stack,
        pot_chips=pot,
        call_amount_chips=call,
        effective_stack_chips=effective_chips,
        required_equity=required_equity,
        spr=spr,
        action_surface=action_surface,
        legal_actions=legal_actions,
        strategy_status=strategy.match_status if strategy is not None else "unavailable",
        strategy_role=strategy.strategy_role if strategy is not None else "none",
        strategy_confidence=strategy.confidence if strategy is not None else 0.0,
        strategy_source_artifact_id=(
            strategy.source_artifact_id if strategy is not None else None
        ),
        strategy_equity=strategy.equity if strategy is not None else None,
        strategy_actions=strategy_actions,
        strategy_assumptions=strategy.assumptions if strategy is not None else [],
        recommended_action=recommended_action,
        recommendation_ready=strategy is not None,
        recommendation_issues=recommendation_issues,
        ready=not issues,
        issues=issues,
        assumptions=[
            "Hero is mapped only from stable local hole-card or action-control evidence.",
            "Effective stack uses the shallowest stable active opponent stack.",
            "Equity and EV remain unavailable until weighted opponent ranges are validated.",
        ],
    )
