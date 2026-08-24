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
    positions_for_table_size,
)
from xpoker_agent.reconstruction.pots import build_pot_layers


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
    table_size: int = 9,
) -> HandState:
    if table_size not in {6, 9}:
        raise ValueError("table_size must be 6 or 9")
    valid_seats = set(range(table_size))
    if not set(occupied_stacks_bb).issubset(valid_seats) or not set(positions).issubset(
        valid_seats
    ):
        raise ValueError("occupied stacks and positions must fit the configured table size")
    allowed_positions = set(positions_for_table_size(table_size))
    if not set(positions.values()).issubset(allowed_positions):
        raise ValueError("position is invalid for the configured table size")
    if len(positions.values()) != len(set(positions.values())):
        raise ValueError("positions must be unique")
    if not set(positions).issubset(occupied_stacks_bb):
        raise ValueError("positions can be assigned only to occupied seats")
    if hero_seat not in occupied_stacks_bb:
        raise ValueError("hero_seat must be occupied")
    seats = []
    for seat_number in range(table_size):
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
        table_size=table_size,
        hero_seat=hero_seat,
        hero_position=positions.get(hero_seat),
        seats=seats,
        initial_total_chips_bb=sum(occupied_stacks_bb.values(), start=Decimal("0")),
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
        if seat_number >= len(state.seats):
            raise StateTransitionError("event references a seat outside the configured table size")
        return state.seats[seat_number]

    def _on_hand_started(self, state: HandState, event: HandEvent) -> None:
        del event
        if state.table_status is not TableStatus.WAITING_FOR_HAND:
            raise StateTransitionError("a hand can start only from its fresh waiting state")
        state.table_status = TableStatus.IN_HAND
        state.street = Street.PREFLOP
        state.board = []
        state.hero_cards = []
        state.pot_main_bb = Decimal("0")
        state.pot_layers = []
        state.current_bet_bb = Decimal("0")
        state.minimum_raise_increment_bb = Decimal("0")
        state.last_aggressor_seat = None
        state.next_to_act_seat = None
        state.acted_seats = []
        state.raise_locked_seats = []
        for seat in state.seats:
            if seat.participation is ParticipationStatus.SEATED:
                seat.participation = ParticipationStatus.ACTIVE

    def _on_dealer_assigned(self, state: HandState, event: HandEvent) -> None:
        self._require_in_hand(state)
        dealer = self._seat(state, event.dealer_seat)
        if dealer.participation is ParticipationStatus.EMPTY:
            raise StateTransitionError("dealer must be assigned to an occupied seat")
        state.dealer_seat = event.dealer_seat

    def _debit(self, state: HandState, event: HandEvent) -> tuple[SeatState, Decimal]:
        self._require_in_hand(state)
        if event.street is not state.street:
            raise StateTransitionError("chip commitment street does not match current state")
        seat = self._seat(state, event.actor_seat)
        if seat.participation is not ParticipationStatus.ACTIVE:
            raise StateTransitionError("only an active player can commit chips")
        if event.amount is None:
            raise StateTransitionError("chip commitment requires an amount")
        added = event.amount.added_bb
        committed = seat.committed_by_street_bb.get(state.street, Decimal("0"))
        if event.amount.to_bb is None:
            raise StateTransitionError("chip commitment requires the resulting total amount")
        if event.amount.to_bb != committed + added:
            raise StateTransitionError("added amount does not match resulting street commitment")
        if added > seat.stack_bb:
            raise StateTransitionError("chip commitment exceeds remaining stack")
        seat.stack_bb -= added
        seat.committed_by_street_bb[state.street] = (
            seat.committed_by_street_bb.get(state.street, Decimal("0")) + added
        )
        # These fields form one invariant and are validated together on the returned state.
        object.__setattr__(state, "pot_main_bb", state.pot_main_bb + added)
        object.__setattr__(state, "pot_layers", build_pot_layers(state.seats))
        return seat, committed + added

    def _on_blind_posted(self, state: HandState, event: HandEvent) -> None:
        if state.street is not Street.PREFLOP:
            raise StateTransitionError("blinds can be posted only preflop")
        if state.dealer_seat is None:
            raise StateTransitionError("dealer must be assigned before blinds")
        seat, resulting_total = self._debit(state, event)
        state.current_bet_bb = max(state.current_bet_bb, resulting_total)
        state.minimum_raise_increment_bb = max(state.minimum_raise_increment_bb, resulting_total)
        if seat.stack_bb == 0:
            seat.participation = ParticipationStatus.ALL_IN
        state.next_to_act_seat = self._next_actionable_after(state, event.actor_seat)

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
        if state.next_to_act_seat is not None:
            raise StateTransitionError("board cannot advance before the betting round closes")
        transition = {
            (Street.PREFLOP, 3): Street.FLOP,
            (Street.FLOP, 1): Street.TURN,
            (Street.TURN, 1): Street.RIVER,
        }.get((state.street, len(event.cards)))
        if transition is None:
            raise StateTransitionError("illegal board-card count or street transition")
        if event.street is not transition:
            raise StateTransitionError("board event street does not match resulting street")
        known = set(state.board)
        known.update(card for seat in state.seats for card in seat.cards)
        if known.intersection(event.cards):
            raise StateTransitionError("board cards duplicate known physical cards")
        state.board.extend(event.cards)
        state.street = transition
        state.current_bet_bb = Decimal("0")
        state.minimum_raise_increment_bb = Decimal("0")
        state.last_aggressor_seat = None
        state.acted_seats = []
        state.raise_locked_seats = []
        state.next_to_act_seat = self._next_actionable_after(state, state.dealer_seat)

    def _betting_actor(self, state: HandState, event: HandEvent) -> SeatState:
        self._require_in_hand(state)
        if event.street is not state.street:
            raise StateTransitionError("betting action street does not match current state")
        seat = self._seat(state, event.actor_seat)
        if seat.participation is not ParticipationStatus.ACTIVE:
            raise StateTransitionError("betting action requires an active player")
        if state.next_to_act_seat is None:
            raise StateTransitionError("betting action is illegal after the round has closed")
        if event.actor_seat != state.next_to_act_seat:
            raise StateTransitionError(
                f"out-of-turn action: expected seat {state.next_to_act_seat}, "
                f"got seat {event.actor_seat}"
            )
        return seat

    @staticmethod
    def _next_actionable_after(state: HandState, seat_number: int | None) -> int | None:
        if seat_number is None:
            return None
        table_size = len(state.seats)
        for offset in range(1, table_size + 1):
            candidate = (seat_number + offset) % table_size
            if state.seats[candidate].participation is ParticipationStatus.ACTIVE:
                return candidate
        return None

    def _advance_action(self, state: HandState, actor_seat: int, *, reset: bool = False) -> None:
        state.acted_seats = [actor_seat] if reset else [*state.acted_seats, actor_seat]
        state.acted_seats = list(dict.fromkeys(state.acted_seats))
        actionable = [
            seat for seat in state.seats if seat.participation is ParticipationStatus.ACTIVE
        ]
        round_closed = len(actionable) <= 1 or all(
            seat.seat in state.acted_seats
            and seat.committed_by_street_bb.get(state.street, Decimal("0")) == state.current_bet_bb
            for seat in actionable
        )
        state.next_to_act_seat = (
            None if round_closed else self._next_actionable_after(state, actor_seat)
        )

    def _on_fold(self, state: HandState, event: HandEvent) -> None:
        self._betting_actor(state, event).participation = ParticipationStatus.FOLDED
        state.pot_layers = build_pot_layers(state.seats)
        self._advance_action(state, event.actor_seat)

    def _on_check(self, state: HandState, event: HandEvent) -> None:
        seat = self._betting_actor(state, event)
        committed = seat.committed_by_street_bb.get(state.street, Decimal("0"))
        if committed != state.current_bet_bb:
            raise StateTransitionError("cannot check while facing a wager")
        self._advance_action(state, event.actor_seat)

    def _on_call(self, state: HandState, event: HandEvent) -> None:
        seat = self._betting_actor(state, event)
        committed = seat.committed_by_street_bb.get(state.street, Decimal("0"))
        required = state.current_bet_bb - committed
        if required <= 0:
            raise StateTransitionError("call requires an outstanding wager")
        if required >= seat.stack_bb:
            raise StateTransitionError("stack-exhausting call must use the all_in action")
        _, resulting_total = self._debit(state, event)
        if resulting_total != state.current_bet_bb:
            raise StateTransitionError("call must match the current wager")
        self._advance_action(state, event.actor_seat)

    def _on_bet(self, state: HandState, event: HandEvent) -> None:
        seat = self._betting_actor(state, event)
        if state.current_bet_bb != 0:
            raise StateTransitionError("bet is illegal when a wager already exists; use raise")
        if event.amount is not None and event.amount.added_bb == seat.stack_bb:
            raise StateTransitionError("stack-exhausting bet must use the all_in action")
        _, resulting_total = self._debit(state, event)
        state.current_bet_bb = resulting_total
        state.minimum_raise_increment_bb = resulting_total
        state.last_aggressor_seat = event.actor_seat
        self._advance_action(state, event.actor_seat, reset=True)

    def _on_raise(self, state: HandState, event: HandEvent) -> None:
        seat = self._betting_actor(state, event)
        if state.current_bet_bb == 0:
            raise StateTransitionError("raise requires an existing wager; use bet")
        if event.actor_seat in state.raise_locked_seats:
            raise StateTransitionError("raising was not reopened after a short all-in")
        if event.amount is None or event.amount.to_bb is None:
            raise StateTransitionError("raise requires a resulting total amount")
        if event.amount.added_bb == seat.stack_bb:
            raise StateTransitionError("stack-exhausting raise must use the all_in action")
        increment = event.amount.to_bb - state.current_bet_bb
        if increment < state.minimum_raise_increment_bb:
            raise StateTransitionError("raise is smaller than the minimum full-raise increment")
        _, resulting_total = self._debit(state, event)
        if resulting_total <= state.current_bet_bb:
            raise StateTransitionError("raise must exceed the current wager")
        state.current_bet_bb = resulting_total
        state.minimum_raise_increment_bb = increment
        state.last_aggressor_seat = event.actor_seat
        state.raise_locked_seats = []
        self._advance_action(state, event.actor_seat, reset=True)

    def _on_all_in(self, state: HandState, event: HandEvent) -> None:
        seat = self._betting_actor(state, event)
        previous_bet = state.current_bet_bb
        if (
            event.amount is not None
            and event.amount.to_bb is not None
            and event.amount.to_bb > previous_bet
            and event.actor_seat in state.raise_locked_seats
        ):
            raise StateTransitionError("raising was not reopened after a short all-in")
        previously_acted = list(state.acted_seats)
        _, resulting_total = self._debit(state, event)
        if seat.stack_bb != 0:
            raise StateTransitionError("all-in action must commit the player's entire stack")
        seat.participation = ParticipationStatus.ALL_IN
        state.pot_layers = build_pot_layers(state.seats)
        if resulting_total > previous_bet:
            increment = resulting_total - previous_bet
            state.current_bet_bb = resulting_total
            if previous_bet == 0 or increment >= state.minimum_raise_increment_bb:
                state.minimum_raise_increment_bb = (
                    resulting_total if previous_bet == 0 else increment
                )
                state.last_aggressor_seat = event.actor_seat
                state.raise_locked_seats = []
                self._advance_action(state, event.actor_seat, reset=True)
                return
            state.raise_locked_seats = list(
                dict.fromkeys([*state.raise_locked_seats, *previously_acted])
            )
        self._advance_action(state, event.actor_seat)

    def _on_showdown_started(self, state: HandState, event: HandEvent) -> None:
        del event
        self._require_in_hand(state)
        if state.street is not Street.RIVER:
            raise StateTransitionError("showdown can start only after the river")
        state.street = Street.SHOWDOWN

    def _on_pot_awarded(self, state: HandState, event: HandEvent) -> None:
        self._require_in_hand(state)
        if state.next_to_act_seat is not None:
            raise StateTransitionError("pot cannot be awarded before betting closes")
        if event.amount is None or event.winner_seat is None or event.pot_index is None:
            raise StateTransitionError("pot award requires winner, pot index, and amount")
        award = event.amount.added_bb
        if event.pot_index >= len(state.pot_layers):
            raise StateTransitionError("pot award references an unknown pot layer")
        layer = state.pot_layers[event.pot_index]
        if event.winner_seat not in layer.eligible_seats:
            raise StateTransitionError("winner is not eligible for the referenced pot layer")
        if award > layer.remaining_bb:
            raise StateTransitionError("pot award exceeds the referenced pot-layer remainder")
        winner = self._seat(state, event.winner_seat)
        if winner.participation is ParticipationStatus.EMPTY:
            raise StateTransitionError("pot cannot be awarded to an empty seat")
        winner.stack_bb += award
        layer.remaining_bb -= award
        state.pot_main_bb -= award

    def _on_hand_completed(self, state: HandState, event: HandEvent) -> None:
        del event
        self._require_in_hand(state)
        if state.pot_main_bb != 0:
            raise StateTransitionError("hand cannot complete before the pot is fully awarded")
        state.table_status = TableStatus.HAND_COMPLETE
