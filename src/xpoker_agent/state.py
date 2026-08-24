"""Deterministic NLH reconstruction reducer for validated canonical events."""

from __future__ import annotations

from decimal import Decimal
from uuid import NAMESPACE_URL, UUID, uuid5

from xpoker_agent.models import (
    HandEvent,
    HandState,
    ParticipationStatus,
    Position,
    SeatState,
    Street,
    TableStatus,
)


class StateTransitionError(ValueError):
    """Raised when an event cannot legally advance the current state."""


def _state_id(hand_id: UUID, revision: int) -> UUID:
    return uuid5(NAMESPACE_URL, f"xpoker-agent:{hand_id}:state:{revision}")


def create_initial_state(
    hand_id: UUID,
    config_version: str,
    hero_seat: int,
    occupied_stacks_bb: dict[int, Decimal],
    positions: dict[int, Position],
) -> HandState:
    if hero_seat not in occupied_stacks_bb:
        raise ValueError("hero_seat must be occupied")
    seats = []
    for seat_number in range(9):
        occupied = seat_number in occupied_stacks_bb
        stack = occupied_stacks_bb.get(seat_number, Decimal("0"))
        seats.append(
            SeatState(
                seat=seat_number,
                position=positions.get(seat_number),
                participation=(
                    ParticipationStatus.SEATED if occupied else ParticipationStatus.EMPTY
                ),
                starting_stack_bb=stack,
                stack_bb=stack,
            )
        )
    return HandState(
        state_id=_state_id(hand_id, 0),
        hand_id=hand_id,
        config_version=config_version,
        hero_seat=hero_seat,
        hero_position=positions.get(hero_seat),
        seats=seats,
    )


class HandStateReducer:
    """Pure-looking reducer: each event returns a validated deep copy of state."""

    def apply(self, state: HandState, event: HandEvent) -> HandState:
        if event.hand_id != state.hand_id:
            raise StateTransitionError("event hand_id does not match state")
        if event.sequence != state.last_event_sequence + 1:
            raise StateTransitionError(
                f"expected event sequence {state.last_event_sequence + 1}, got {event.sequence}"
            )

        next_state = state.model_copy(deep=True)
        next_state.revision += 1
        next_state.state_id = _state_id(next_state.hand_id, next_state.revision)
        next_state.last_event_sequence = event.sequence
        next_state.event_ids.append(event.event_id)

        handler = getattr(self, f"_on_{event.type}", None)
        if handler is None:
            raise StateTransitionError(f"unsupported event type: {event.type}")
        handler(next_state, event)
        return HandState.model_validate(next_state.model_dump())

    @staticmethod
    def _require_in_hand(state: HandState) -> None:
        if state.table_status is not TableStatus.IN_HAND:
            raise StateTransitionError("event requires an active hand")

    @staticmethod
    def _seat(state: HandState, seat_number: int | None) -> SeatState:
        if seat_number is None:
            raise StateTransitionError("event requires a seat")
        return state.seats[seat_number]

    def _on_hand_started(self, state: HandState, event: HandEvent) -> None:
        del event
        if state.table_status not in {TableStatus.WAITING_FOR_HAND, TableStatus.HAND_COMPLETE}:
            raise StateTransitionError("hand can start only while waiting or after completion")
        state.table_status = TableStatus.IN_HAND
        state.street = Street.PREFLOP
        state.board = []
        state.hero_cards = []
        state.pot_main_bb = Decimal("0")
        for seat in state.seats:
            if seat.participation is ParticipationStatus.SEATED:
                seat.participation = ParticipationStatus.ACTIVE

    def _on_dealer_assigned(self, state: HandState, event: HandEvent) -> None:
        self._require_in_hand(state)
        state.dealer_seat = event.dealer_seat

    def _debit(self, state: HandState, event: HandEvent) -> None:
        self._require_in_hand(state)
        if event.street is not state.street:
            raise StateTransitionError("chip commitment street does not match current state")
        seat = self._seat(state, event.actor_seat)
        if seat.participation is not ParticipationStatus.ACTIVE:
            raise StateTransitionError("only an active player can commit chips")
        if event.amount is None:
            raise StateTransitionError("chip commitment requires an amount")
        added = event.amount.added_bb
        if added > seat.stack_bb:
            raise StateTransitionError("chip commitment exceeds remaining stack")
        seat.stack_bb -= added
        seat.committed_by_street_bb[state.street] = (
            seat.committed_by_street_bb.get(state.street, Decimal("0")) + added
        )
        state.pot_main_bb += added

    def _on_blind_posted(self, state: HandState, event: HandEvent) -> None:
        if state.street is not Street.PREFLOP:
            raise StateTransitionError("blinds can be posted only preflop")
        self._debit(state, event)

    def _on_hole_cards_observed(self, state: HandState, event: HandEvent) -> None:
        self._require_in_hand(state)
        if state.street is not Street.PREFLOP or len(event.cards) != 2:
            raise StateTransitionError("hole cards require exactly two cards preflop")
        seat = self._seat(state, event.actor_seat)
        seat.cards = list(event.cards)
        if event.actor_seat == state.hero_seat:
            state.hero_cards = list(event.cards)

    def _on_board_cards_observed(self, state: HandState, event: HandEvent) -> None:
        self._require_in_hand(state)
        transition = {
            (Street.PREFLOP, 3): Street.FLOP,
            (Street.FLOP, 1): Street.TURN,
            (Street.TURN, 1): Street.RIVER,
        }.get((state.street, len(event.cards)))
        if transition is None:
            raise StateTransitionError("illegal board-card count or street transition")
        if event.street is not transition:
            raise StateTransitionError("board event street does not match resulting street")
        known = set(state.hero_cards + state.board)
        if known.intersection(event.cards):
            raise StateTransitionError("board cards duplicate known physical cards")
        state.board.extend(event.cards)
        state.street = transition

    def _betting_actor(self, state: HandState, event: HandEvent) -> SeatState:
        self._require_in_hand(state)
        if event.street is not state.street:
            raise StateTransitionError("betting action street does not match current state")
        seat = self._seat(state, event.actor_seat)
        if seat.participation is not ParticipationStatus.ACTIVE:
            raise StateTransitionError("betting action requires an active player")
        return seat

    def _on_fold(self, state: HandState, event: HandEvent) -> None:
        self._betting_actor(state, event).participation = ParticipationStatus.FOLDED

    def _on_check(self, state: HandState, event: HandEvent) -> None:
        self._betting_actor(state, event)

    def _on_call(self, state: HandState, event: HandEvent) -> None:
        self._debit(state, event)

    def _on_bet(self, state: HandState, event: HandEvent) -> None:
        self._debit(state, event)

    def _on_raise(self, state: HandState, event: HandEvent) -> None:
        self._debit(state, event)

    def _on_all_in(self, state: HandState, event: HandEvent) -> None:
        seat = self._betting_actor(state, event)
        self._debit(state, event)
        if seat.stack_bb != 0:
            raise StateTransitionError("all-in action must commit the player's entire stack")
        seat.participation = ParticipationStatus.ALL_IN

    def _on_showdown_started(self, state: HandState, event: HandEvent) -> None:
        del event
        self._require_in_hand(state)
        if state.street is not Street.RIVER:
            raise StateTransitionError("showdown can start only after the river")
        state.street = Street.SHOWDOWN

    def _on_pot_awarded(self, state: HandState, event: HandEvent) -> None:
        self._require_in_hand(state)
        if event.amount is None or event.winner_seat is None:
            raise StateTransitionError("pot award requires winner and amount")
        award = event.amount.added_bb
        if award > state.pot_main_bb:
            raise StateTransitionError("pot award exceeds reconstructed pot")
        winner = self._seat(state, event.winner_seat)
        winner.stack_bb += award
        state.pot_main_bb -= award

    def _on_hand_completed(self, state: HandState, event: HandEvent) -> None:
        del event
        self._require_in_hand(state)
        if state.pot_main_bb != 0:
            raise StateTransitionError("hand cannot complete before the pot is fully awarded")
        state.table_status = TableStatus.HAND_COMPLETE
