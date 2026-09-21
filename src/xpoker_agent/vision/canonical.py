"""Deterministic construction of a reducer-validated live standard-NLH prefix."""

from __future__ import annotations

from decimal import Decimal
from uuid import NAMESPACE_URL, uuid5

from xpoker_agent.models import (
    Confidence,
    EventAmount,
    EventCategory,
    HandEvent,
    HandMode,
    Street,
)
from xpoker_agent.state import HandStateReducer, create_initial_state
from xpoker_agent.vision.models import (
    ActionAmountReconciliation,
    BlindPostReconciliation,
    DerivedActionCandidate,
    LiveCanonicalHandPrefix,
    StackIncreaseCandidate,
)
from xpoker_agent.vision.positions import assign_dealt_positions


def _confidence(score: float, calibration_id: str, stable_frames: int = 3) -> Confidence:
    return Confidence(
        score=score,
        calibration_id=calibration_id,
        stable_frames=max(1, stable_frames),
    )


def build_standard_live_hand_prefix(
    *,
    target_fingerprint: str,
    hand_epoch: int,
    table_size: int,
    hero_seat: int,
    dealer_seat: int,
    starting_stacks_native: dict[int, Decimal],
    current_stacks_native: dict[int, Decimal],
    current_pot_native: Decimal,
    big_blind_native: Decimal,
    blind_posts: list[BlindPostReconciliation],
    hero_cards: list[str],
    board_cards: list[str],
    actions: list[DerivedActionCandidate],
    amount_reconciliations: list[ActionAmountReconciliation],
) -> LiveCanonicalHandPrefix:
    """Build only evidence-complete prefixes; the reducer rejects any missing action."""
    if hand_epoch < 1:
        raise ValueError("canonical live hand requires a witnessed boundary")
    if hero_seat not in starting_stacks_native:
        raise ValueError("hero starting stack is unavailable")
    if set(starting_stacks_native) != set(current_stacks_native):
        raise ValueError("starting and current stack seats differ")
    if big_blind_native <= 0:
        raise ValueError("positive native big blind is required")
    if len(hero_cards) != 2:
        raise ValueError("two accepted hero cards are required")
    if len(board_cards) not in {0, 3, 4, 5}:
        raise ValueError("canonical board must contain 0, 3, 4, or 5 cards")

    hand_id = uuid5(
        NAMESPACE_URL,
        f"xpoker-agent:{target_fingerprint}:live-hand:{hand_epoch}",
    )
    stacks_chips = dict(starting_stacks_native)
    state = create_initial_state(
        hand_id=hand_id,
        config_version=f"game-{table_size}max-nlh-v1",
        hero_seat=hero_seat,
        occupied_stacks_chips=stacks_chips,
        positions=assign_dealt_positions(
            table_size=table_size,
            dealer_seat=dealer_seat,
            active_seats=set(stacks_chips),
        ),
        table_size=table_size,
    )
    reducer = HandStateReducer()
    events: list[HandEvent] = []

    def append_event(
        *,
        category: EventCategory,
        event_type: str,
        calibration_id: str,
        score: float = 1.0,
        stable_frames: int = 3,
        **values: object,
    ) -> None:
        nonlocal state
        sequence = len(events) + 1
        event = HandEvent(
            event_id=uuid5(hand_id, f"event:{sequence}:{event_type}"),
            hand_id=hand_id,
            sequence=sequence,
            category=category,
            type=event_type,
            confidence=_confidence(score, calibration_id, stable_frames),
            **values,
        )
        state = reducer.apply(state, event)
        events.append(event)

    append_event(
        category=EventCategory.LIFECYCLE,
        event_type="hand_started",
        hand_mode=HandMode.STANDARD_NLH,
        calibration_id="live-hand-boundary-v1",
    )
    append_event(
        category=EventCategory.DEALING,
        event_type="dealer_assigned",
        dealer_seat=dealer_seat,
        calibration_id="xpoker-dealer-temporal-v1",
    )
    posts_by_kind = {post.blind_kind: post for post in blind_posts}
    for kind in ("small_blind", "big_blind"):
        post = posts_by_kind.get(kind)
        if post is None or post.status != "matched":
            raise ValueError(f"{kind} post is not uniquely reconciled")
        amount_chips = post.amount_native
        append_event(
            category=EventCategory.FORCED_WAGER,
            event_type="blind_posted",
            actor_seat=post.seat,
            street=Street.PREFLOP,
            amount=EventAmount(to_chips=amount_chips, added_chips=amount_chips),
            calibration_id="live-blind-post-reconciliation-v1",
        )
    append_event(
        category=EventCategory.DEALING,
        event_type="hole_cards_observed",
        actor_seat=hero_seat,
        street=Street.PREFLOP,
        cards=hero_cards,
        calibration_id="xpoker-hero-card-temporal-v1",
    )

    amount_by_id = {result.action_event_id: result for result in amount_reconciliations}
    actions_by_street = {
        street: sorted(
            (action for action in actions if action.street == street),
            key=lambda item: (item.frame_sequence, item.occurrence),
        )
        for street in ("preflop", "flop", "turn", "river")
    }

    def append_actions(street_name: str, street: Street) -> None:
        for action in actions_by_street[street_name]:
            reconciliation = amount_by_id.get(action.event_id)
            if reconciliation is None or reconciliation.status not in {
                "matched",
                "not_required",
            }:
                raise ValueError(f"action amount is unresolved: {action.event_id}")
            amount = None
            if action.action in {"call", "bet", "raise", "all_in"}:
                if reconciliation.amount_native is None:
                    raise ValueError(f"action amount is missing: {action.event_id}")
                added_chips = reconciliation.amount_native
                committed = state.seats[action.seat].committed_by_street_chips.get(
                    street, Decimal("0")
                )
                amount = EventAmount(to_chips=committed + added_chips, added_chips=added_chips)
            append_event(
                category=EventCategory.BETTING_ACTION,
                event_type=action.action,
                actor_seat=action.seat,
                street=street,
                amount=amount,
                score=action.confidence,
                calibration_id="xpoker-action-cross-signal-v1",
                assumptions=[f"visual_candidate:{action.event_id}"],
            )

    append_actions("preflop", Street.PREFLOP)
    if board_cards:
        append_event(
            category=EventCategory.DEALING,
            event_type="board_cards_observed",
            street=Street.FLOP,
            cards=board_cards[:3],
            calibration_id="xpoker-board-card-temporal-v1",
        )
        append_actions("flop", Street.FLOP)
    if len(board_cards) >= 4:
        append_event(
            category=EventCategory.DEALING,
            event_type="board_cards_observed",
            street=Street.TURN,
            cards=[board_cards[3]],
            calibration_id="xpoker-board-card-temporal-v1",
        )
        append_actions("turn", Street.TURN)
    if len(board_cards) == 5:
        append_event(
            category=EventCategory.DEALING,
            event_type="board_cards_observed",
            street=Street.RIVER,
            cards=[board_cards[4]],
            calibration_id="xpoker-board-card-temporal-v1",
        )
        append_actions("river", Street.RIVER)

    for seat, observed_native in current_stacks_native.items():
        if state.seats[seat].stack_chips != observed_native:
            raise ValueError(f"reducer stack does not match live seat {seat}")
    if state.pot_main_chips != current_pot_native:
        raise ValueError("reducer pot does not match the stable live pot")
    return LiveCanonicalHandPrefix(
        hand_epoch=hand_epoch,
        hand_id=hand_id,
        events=events,
        state=state,
        source_action_event_ids=[action.event_id for action in actions],
    )


def complete_single_winner_live_hand(
    prefix: LiveCanonicalHandPrefix,
    stack_increase: StackIncreaseCandidate,
) -> LiveCanonicalHandPrefix:
    """Complete only an exact one-layer, one-winner settlement."""
    if prefix.complete:
        return prefix
    state = prefix.state
    if state.next_to_act_seat is not None:
        raise ValueError("betting is not closed")
    if len(state.pot_layers) != 1:
        raise ValueError("single-pot settlement requires exactly one pot layer")
    if stack_increase.previous_stack_native != state.seats[stack_increase.seat].stack_chips:
        raise ValueError("winner stack baseline does not match the retained hand")
    if stack_increase.increase_native != state.pot_main_chips:
        raise ValueError("stack increase does not equal the complete retained pot")

    reducer = HandStateReducer()
    events = list(prefix.events)
    award = HandEvent(
        event_id=uuid5(prefix.hand_id, f"event:{len(events) + 1}:pot_awarded"),
        hand_id=prefix.hand_id,
        sequence=len(events) + 1,
        category=EventCategory.SETTLEMENT,
        type="pot_awarded",
        winner_seat=stack_increase.seat,
        pot_index=0,
        amount=EventAmount(added_chips=stack_increase.increase_native),
        confidence=_confidence(0.95, "xpoker-stack-settlement-v1"),
        assumptions=[f"visual_candidate:{stack_increase.event_id}"],
    )
    state = reducer.apply(state, award)
    events.append(award)
    completed = HandEvent(
        event_id=uuid5(prefix.hand_id, f"event:{len(events) + 1}:hand_completed"),
        hand_id=prefix.hand_id,
        sequence=len(events) + 1,
        category=EventCategory.LIFECYCLE,
        type="hand_completed",
        confidence=_confidence(1.0, "live-hand-boundary-v1"),
    )
    state = reducer.apply(state, completed)
    events.append(completed)
    return prefix.model_copy(
        update={
            "events": events,
            "state": state,
            "complete": True,
            "reason": "validated single-pot live hand completed at witnessed boundary",
        }
    )
