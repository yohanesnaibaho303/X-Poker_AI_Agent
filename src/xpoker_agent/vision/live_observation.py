"""Bounded continuous observation of one authorized X-Poker table."""

from __future__ import annotations

import asyncio
import hashlib
from collections import deque
from collections.abc import Awaitable, Callable
from contextlib import suppress
from datetime import UTC, datetime
from decimal import Decimal
from typing import Literal

from xpoker_agent.capture.frames import CapturedFrame
from xpoker_agent.vision.action_order import validate_action_order
from xpoker_agent.vision.hand_boundary import validate_live_hand_boundary
from xpoker_agent.vision.live import diagnose_authorized_table
from xpoker_agent.vision.models import (
    ActionAmountReconciliation,
    ActionPotReconciliation,
    DerivedActionCandidate,
    LiveCaptureDiagnostic,
    LiveHandBoundaryValidation,
    LiveObservationStatus,
    LiveReconstructionReadiness,
    PotDeltaCandidate,
    SeatActionConsensus,
    SeatStackConsensus,
    SeatStatusConsensus,
    StackDeltaCandidate,
    TemporalConsensus,
    TemporalSample,
)
from xpoker_agent.vision.positions import assign_full_ring_positions
from xpoker_agent.vision.temporal import consensus

CaptureCallable = Callable[
    [int, int], Awaitable[tuple[LiveCaptureDiagnostic, CapturedFrame]]
]


class TargetIdentityChanged(RuntimeError):
    pass


class LiveObservationService:
    def __init__(
        self,
        capture: CaptureCallable | None = None,
        *,
        maximum_samples: int = 30,
        maximum_consecutive_failures: int = 3,
    ) -> None:
        if maximum_samples < 3:
            raise ValueError("live observation requires at least three bounded samples")
        if maximum_consecutive_failures < 1:
            raise ValueError("failure threshold must be positive")
        self._capture = capture
        self._samples: deque[TemporalSample] = deque(maxlen=maximum_samples)
        self._blind_samples: deque[TemporalSample] = deque(maxlen=maximum_samples)
        self._pot_samples: deque[TemporalSample] = deque(maxlen=maximum_samples)
        self._last_high_confidence_pot_sample: TemporalSample | None = None
        self._board_samples: deque[TemporalSample] = deque(maxlen=maximum_samples)
        self._card_samples: dict[int, deque[TemporalSample]] = {
            index: deque(maxlen=maximum_samples) for index in range(5)
        }
        self._hero_card_samples: dict[int, deque[TemporalSample]] = {
            index: deque(maxlen=maximum_samples) for index in range(2)
        }
        self._stack_samples: dict[int, deque[TemporalSample]] = {
            seat: deque(maxlen=maximum_samples) for seat in range(9)
        }
        self._action_samples: dict[int, deque[TemporalSample]] = {
            seat: deque(maxlen=maximum_samples) for seat in range(9)
        }
        self._hero_control_samples: deque[TemporalSample] = deque(
            maxlen=maximum_samples
        )
        self._maximum_consecutive_failures = maximum_consecutive_failures
        self._capture_lock = asyncio.Lock()
        self._stop_event = asyncio.Event()
        self._task: asyncio.Task[None] | None = None
        self._table_size: Literal[6, 9] = 9
        self._interval_ms = 500
        self._started_at: datetime | None = None
        self._stopped_at: datetime | None = None
        self._latest_sequence = 0
        self._frames_attempted = 0
        self._frames_succeeded = 0
        self._frames_failed = 0
        self._consecutive_failures = 0
        self._session_target_fingerprint: str | None = None
        self._session_hwnd: int | None = None
        self._session_process_id: int | None = None
        self._target_stable = True
        self._last_error: str | None = None
        self._mode_consensus = TemporalConsensus(
            accepted=False,
            confidence=0.0,
            stable_frames=0,
            reason="no_samples",
        )
        self._blind_consensus = self._empty_consensus("no_samples")
        self._pot_consensus = self._empty_consensus("no_samples")
        self._board_consensus = self._empty_consensus("no_samples")
        self._board_card_consensus: list[TemporalConsensus] = []
        self._recognized_board_cards: list[str] = []
        self._board_cards_accepted = False
        self._board_cards_reason = "no_postflop_board"
        self._hero_card_consensus: list[TemporalConsensus] = []
        self._recognized_hero_cards: list[str] = []
        self._hero_cards_accepted = False
        self._hero_cards_reason = "hero_cards_unobserved"
        self._dealer_samples: deque[TemporalSample] = deque(maxlen=maximum_samples)
        self._dealer_consensus = self._empty_consensus("no_samples")
        self._epoch_dealer_evidence: int | None = None
        self._status_samples: dict[int, deque[TemporalSample]] = {
            seat: deque(maxlen=maximum_samples) for seat in range(9)
        }
        self._seat_status_consensus: list[SeatStatusConsensus] = []
        self._active_seats: list[int] = []
        self._epoch_active_evidence: list[int] = []
        self._provisional_positions = {}
        self._positions_reason = "seat_statuses_unresolved"
        self._stack_consensus = [
            SeatStackConsensus(
                seat=seat,
                player_status="ambiguous",
                consensus=self._empty_consensus("no_samples"),
            )
            for seat in range(9)
        ]
        self._action_consensus = [
            SeatActionConsensus(
                seat=seat, consensus=self._empty_consensus("no_samples")
            )
            for seat in range(9)
        ]
        self._hero_control_consensus = self._empty_consensus("no_samples")
        self._hand_epoch = 0
        self._previous_epoch_dealer: int | None = None
        self._previous_epoch_active_seats: list[int] = []
        self._hand_boundary_validation = LiveHandBoundaryValidation(
            hand_epoch=0,
            status="pending",
            issues=["prior_hand_context_unavailable"],
            reason="observer has not witnessed a complete hand boundary",
        )
        self._last_accepted_board_count: int | None = None
        self._action_armed_seats: set[int] = set()
        self._action_occurrence_counts: dict[tuple[int, str, int, str], int] = {}
        self._derived_actions: deque[DerivedActionCandidate] = deque(maxlen=50)
        self._last_accepted_stacks: dict[int, Decimal] = {}
        self._stack_deltas: deque[StackDeltaCandidate] = deque(maxlen=50)
        self._last_accepted_pot: Decimal | None = None
        self._pot_deltas: deque[PotDeltaCandidate] = deque(maxlen=50)
        self.latest_diagnostic: LiveCaptureDiagnostic | None = None
        self.latest_frame: CapturedFrame | None = None

    @property
    def running(self) -> bool:
        return self._task is not None and not self._task.done()

    async def start(self, *, table_size: Literal[6, 9], interval_ms: int) -> bool:
        if interval_ms < 1:
            raise ValueError("capture interval must be positive")
        if self.running:
            return False
        self._table_size = table_size
        self._interval_ms = interval_ms
        self._started_at = datetime.now(UTC)
        self._stopped_at = None
        self._latest_sequence = 0
        self._frames_attempted = 0
        self._frames_succeeded = 0
        self._frames_failed = 0
        self._consecutive_failures = 0
        self._session_target_fingerprint = None
        self._session_hwnd = None
        self._session_process_id = None
        self._target_stable = True
        self._last_error = None
        self._samples.clear()
        self._blind_samples.clear()
        self._pot_samples.clear()
        self._last_high_confidence_pot_sample = None
        self._board_samples.clear()
        for samples in self._card_samples.values():
            samples.clear()
        for samples in self._hero_card_samples.values():
            samples.clear()
        for samples in self._stack_samples.values():
            samples.clear()
        for samples in self._action_samples.values():
            samples.clear()
        self._hero_control_samples.clear()
        self._mode_consensus = TemporalConsensus(
            accepted=False,
            confidence=0.0,
            stable_frames=0,
            reason="no_samples",
        )
        self._blind_consensus = self._empty_consensus("no_samples")
        self._pot_consensus = self._empty_consensus("no_samples")
        self._board_consensus = self._empty_consensus("no_samples")
        self._board_card_consensus = []
        self._recognized_board_cards = []
        self._board_cards_accepted = False
        self._board_cards_reason = "no_postflop_board"
        self._hero_card_consensus = []
        self._recognized_hero_cards = []
        self._hero_cards_accepted = False
        self._hero_cards_reason = "hero_cards_unobserved"
        self._dealer_samples.clear()
        self._dealer_consensus = self._empty_consensus("no_samples")
        self._epoch_dealer_evidence = None
        for samples in self._status_samples.values():
            samples.clear()
        self._seat_status_consensus = []
        self._active_seats = []
        self._epoch_active_evidence = []
        self._provisional_positions = {}
        self._positions_reason = "seat_statuses_unresolved"
        self._stack_consensus = [
            SeatStackConsensus(
                seat=seat,
                player_status="ambiguous",
                consensus=self._empty_consensus("no_samples"),
            )
            for seat in range(9)
        ]
        self._action_consensus = [
            SeatActionConsensus(
                seat=seat, consensus=self._empty_consensus("no_samples")
            )
            for seat in range(9)
        ]
        self._hero_control_consensus = self._empty_consensus("no_samples")
        self._hand_epoch = 0
        self._previous_epoch_dealer = None
        self._previous_epoch_active_seats = []
        self._hand_boundary_validation = LiveHandBoundaryValidation(
            hand_epoch=0,
            status="pending",
            issues=["prior_hand_context_unavailable"],
            reason="observer has not witnessed a complete hand boundary",
        )
        self._last_accepted_board_count = None
        self._action_armed_seats.clear()
        self._action_occurrence_counts.clear()
        self._derived_actions.clear()
        self._last_accepted_stacks.clear()
        self._stack_deltas.clear()
        self._last_accepted_pot = None
        self._pot_deltas.clear()
        self.latest_diagnostic = None
        self.latest_frame = None
        self._stop_event = asyncio.Event()
        self._task = asyncio.create_task(self._run(), name="xpoker-live-observation")
        return True

    async def stop(self) -> bool:
        if not self.running:
            return False
        self._stop_event.set()
        assert self._task is not None
        await self._task
        return True

    async def inspect_once(
        self, *, table_size: Literal[6, 9]
    ) -> LiveCaptureDiagnostic:
        async with self._capture_lock:
            sequence = self._latest_sequence + 1
            self._frames_attempted += 1
            try:
                if self._capture is None:
                    diagnostic, frame = await diagnose_authorized_table(
                        table_size=table_size,
                        sequence=sequence,
                        locked_hwnd=self._session_hwnd,
                        locked_process_id=self._session_process_id,
                    )
                else:
                    diagnostic, frame = await self._capture(table_size, sequence)
                self._record_success(diagnostic, frame)
            except (OSError, RuntimeError, ValueError) as error:
                self._record_failure(error)
                raise
            return diagnostic

    def _record_success(
        self, diagnostic: LiveCaptureDiagnostic, frame: CapturedFrame
    ) -> None:
        if self._session_target_fingerprint is None:
            self._session_target_fingerprint = diagnostic.target_fingerprint
            self._session_hwnd = diagnostic.target_hwnd
            self._session_process_id = diagnostic.target_process_id
        elif diagnostic.target_fingerprint != self._session_target_fingerprint:
            self._target_stable = False
            raise TargetIdentityChanged("authorized X-Poker target identity changed during capture")
        self._latest_sequence = diagnostic.frame_sequence
        self._frames_succeeded += 1
        self._consecutive_failures = 0
        self._last_error = None
        self.latest_diagnostic = diagnostic
        self.latest_frame = frame
        if diagnostic.current_hand_mode == "ambiguous":
            self._samples.clear()
            self._mode_consensus = TemporalConsensus(
                accepted=False,
                confidence=0.0,
                stable_frames=0,
                reason="current_mode_ambiguous",
            )
        else:
            self._mode_consensus = self._append_consecutive(
                self._samples,
                TemporalSample(
                    frame_sequence=diagnostic.frame_sequence,
                    content_sha256=diagnostic.content_sha256,
                    value=diagnostic.current_hand_mode,
                    confidence=diagnostic.blind_confidence,
                ),
            )
        self._record_numeric_observations(diagnostic)

    @staticmethod
    def _empty_consensus(reason: str) -> TemporalConsensus:
        return TemporalConsensus(
            accepted=False,
            confidence=0.0,
            stable_frames=0,
            reason=reason,
        )

    @staticmethod
    def _append_consecutive(
        samples: deque[TemporalSample], sample: TemporalSample
    ) -> TemporalConsensus:
        if samples and samples[-1].value != sample.value:
            samples.clear()
        samples.append(sample)
        return consensus(list(samples))

    def _record_numeric_observations(self, diagnostic: LiveCaptureDiagnostic) -> None:
        if (
            diagnostic.small_blind_native is None
            or diagnostic.big_blind_native is None
        ):
            self._blind_samples.clear()
            self._blind_consensus = self._empty_consensus("current_blinds_ambiguous")
        else:
            self._blind_consensus = self._append_consecutive(
                self._blind_samples,
                TemporalSample(
                    frame_sequence=diagnostic.frame_sequence,
                    content_sha256=diagnostic.content_sha256,
                    value=(
                        f"{diagnostic.small_blind_native}/"
                        f"{diagnostic.big_blind_native}"
                    ),
                    confidence=diagnostic.rule_confidence,
                ),
            )
        previous_board_value = self._board_samples[-1].value if self._board_samples else None
        if not diagnostic.board_geometry_supported or diagnostic.board_card_slots not in {
            0,
            3,
            4,
            5,
        }:
            self._board_samples.clear()
            self._board_consensus = self._empty_consensus("current_board_ambiguous")
        else:
            self._board_consensus = self._append_consecutive(
                self._board_samples,
                TemporalSample(
                    frame_sequence=diagnostic.frame_sequence,
                    content_sha256=diagnostic.content_sha256,
                    value=str(diagnostic.board_card_slots),
                    confidence=max(0.9, diagnostic.board_geometry_confidence),
                ),
            )
            if previous_board_value != str(diagnostic.board_card_slots):
                for samples in self._card_samples.values():
                    samples.clear()
            if self._board_consensus.accepted:
                board_count = int(self._board_consensus.value or "0")
                if (
                    self._last_accepted_board_count is not None
                    and self._last_accepted_board_count >= 3
                    and board_count == 0
                ):
                    self._previous_epoch_dealer = self._epoch_dealer_evidence
                    self._previous_epoch_active_seats = list(
                        self._epoch_active_evidence
                    )
                    self._epoch_dealer_evidence = None
                    self._epoch_active_evidence = []
                    self._hand_epoch += 1
                    self._dealer_samples.clear()
                    self._dealer_consensus = self._empty_consensus(
                        "new_hand_dealer_unresolved"
                    )
                    self._hand_boundary_validation = validate_live_hand_boundary(
                        hand_epoch=self._hand_epoch,
                        table_size=diagnostic.table_size,
                        previous_dealer_seat=self._previous_epoch_dealer,
                        current_dealer_seat=None,
                        previous_active_seats=self._previous_epoch_active_seats,
                        current_active_seats=[],
                    )
                    self._action_armed_seats.clear()
                    self._action_occurrence_counts.clear()
                    for samples in self._hero_card_samples.values():
                        samples.clear()
                    self._hero_card_consensus = []
                    self._recognized_hero_cards = []
                    self._hero_cards_accepted = False
                    self._hero_cards_reason = "new_hand_epoch"
                self._last_accepted_board_count = board_count

        self._record_board_cards(diagnostic)
        self._record_hero_cards(diagnostic)
        if diagnostic.dealer.seat is None:
            self._dealer_samples.clear()
            self._dealer_consensus = self._empty_consensus("current_dealer_ambiguous")
        else:
            self._dealer_consensus = self._append_consecutive(
                self._dealer_samples,
                TemporalSample(
                    frame_sequence=diagnostic.frame_sequence,
                    content_sha256=diagnostic.content_sha256,
                    value=str(diagnostic.dealer.seat),
                    confidence=diagnostic.dealer.confidence,
                ),
            )
            if self._dealer_consensus.accepted and self._dealer_consensus.value is not None:
                self._epoch_dealer_evidence = int(self._dealer_consensus.value)
        self._record_seat_statuses(diagnostic)

        if diagnostic.pot.value_native is None:
            self._pot_samples.clear()
            self._pot_consensus = self._empty_consensus("current_pot_ambiguous")
            self._last_accepted_pot = None
            self._last_high_confidence_pot_sample = None
        else:
            current_raw_pot = TemporalSample(
                frame_sequence=diagnostic.frame_sequence,
                content_sha256=diagnostic.content_sha256,
                value=str(diagnostic.pot.value_native),
                confidence=diagnostic.pot.confidence,
            )
            previous_raw_pot = self._last_high_confidence_pot_sample
            if diagnostic.pot.confidence >= 0.95:
                if (
                    previous_raw_pot is not None
                    and diagnostic.frame_sequence - previous_raw_pot.frame_sequence <= 2
                    and Decimal(current_raw_pot.value) > Decimal(previous_raw_pot.value)
                ):
                    street_by_cards = {
                        0: "preflop",
                        3: "flop",
                        4: "turn",
                        5: "river",
                    }
                    raw_street = (
                        street_by_cards.get(
                            int(self._board_consensus.value or "-1"), "unknown"
                        )
                        if self._board_consensus.accepted
                        else "unknown"
                    )
                    previous_value = Decimal(previous_raw_pot.value)
                    current_value = Decimal(current_raw_pot.value)
                    encoded = (
                        f"{diagnostic.target_fingerprint}:{self._hand_epoch}:pot-raw:"
                        f"{diagnostic.frame_sequence}:{previous_value}:{current_value}"
                    ).encode()
                    self._pot_deltas.append(
                        PotDeltaCandidate(
                            event_id=hashlib.sha256(encoded).hexdigest(),
                            hand_epoch=self._hand_epoch,
                            frame_sequence=diagnostic.frame_sequence,
                            street=raw_street,
                            previous_pot_native=previous_value,
                            current_pot_native=current_value,
                            increase_native=current_value - previous_value,
                            evidence_mode="cross_signal_single_frame",
                            confidence=min(
                                previous_raw_pot.confidence,
                                current_raw_pot.confidence,
                            ),
                            reason=(
                                "consecutive high-confidence pot observations; "
                                "independent action and stack signals required"
                            ),
                        )
                    )
                self._last_high_confidence_pot_sample = current_raw_pot
            else:
                self._last_high_confidence_pot_sample = None
            self._pot_consensus = self._append_consecutive(
                self._pot_samples,
                TemporalSample(
                    frame_sequence=diagnostic.frame_sequence,
                    content_sha256=diagnostic.content_sha256,
                    value=str(diagnostic.pot.value_native),
                    confidence=diagnostic.pot.confidence,
                ),
            )
        if self._pot_consensus.accepted and self._pot_consensus.value is not None:
            current_pot = Decimal(self._pot_consensus.value)
            previous_pot = self._last_accepted_pot
            if previous_pot is not None and current_pot > previous_pot:
                street_by_cards = {0: "preflop", 3: "flop", 4: "turn", 5: "river"}
                pot_street = (
                    street_by_cards.get(
                        int(self._board_consensus.value or "-1"), "unknown"
                    )
                    if self._board_consensus.accepted
                    else "unknown"
                )
                encoded = (
                    f"{diagnostic.target_fingerprint}:{self._hand_epoch}:pot:"
                    f"{diagnostic.frame_sequence}:{previous_pot}:{current_pot}"
                ).encode()
                event_id = hashlib.sha256(encoded).hexdigest()
                equivalent_index = next(
                    (
                        index
                        for index, delta in enumerate(self._pot_deltas)
                        if delta.hand_epoch == self._hand_epoch
                        and delta.previous_pot_native == previous_pot
                        and delta.current_pot_native == current_pot
                    ),
                    None,
                )
                if equivalent_index is not None:
                    existing = self._pot_deltas[equivalent_index]
                    self._pot_deltas[equivalent_index] = existing.model_copy(
                        update={
                            "street": pot_street,
                            "evidence_mode": "stable_endpoints",
                            "confidence": self._pot_consensus.confidence,
                            "reason": "three-frame stable pot endpoints",
                        }
                    )
                elif not any(delta.event_id == event_id for delta in self._pot_deltas):
                    self._pot_deltas.append(
                        PotDeltaCandidate(
                            event_id=event_id,
                            hand_epoch=self._hand_epoch,
                            frame_sequence=diagnostic.frame_sequence,
                            street=pot_street,
                            previous_pot_native=previous_pot,
                            current_pot_native=current_pot,
                            increase_native=current_pot - previous_pot,
                            evidence_mode="stable_endpoints",
                            confidence=self._pot_consensus.confidence,
                        )
                    )
            if previous_pot != current_pot:
                self._last_accepted_pot = current_pot

        by_seat = {panel.seat: panel for panel in diagnostic.seat_panels}
        stack_consensus: list[SeatStackConsensus] = []
        for seat in range(diagnostic.table_size):
            panel = by_seat.get(seat)
            samples = self._stack_samples[seat]
            if panel is None or panel.stack_native is None or panel.status != "seated":
                samples.clear()
                state = panel.status if panel is not None else "ambiguous"
                result = self._empty_consensus("current_stack_ambiguous")
            else:
                state = panel.status
                result = self._append_consecutive(
                    samples,
                    TemporalSample(
                        frame_sequence=diagnostic.frame_sequence,
                        content_sha256=diagnostic.content_sha256,
                        value=str(panel.stack_native),
                        confidence=panel.confidence,
                    ),
                )
            stack_consensus.append(
                SeatStackConsensus(seat=seat, player_status=state, consensus=result)
            )
        self._stack_consensus = stack_consensus
        street_by_cards = {0: "preflop", 3: "flop", 4: "turn", 5: "river"}
        stack_street = (
            street_by_cards.get(int(self._board_consensus.value or "-1"), "unknown")
            if self._board_consensus.accepted
            else "unknown"
        )
        for item in stack_consensus:
            result = item.consensus
            if not result.accepted or result.value is None:
                continue
            current = Decimal(result.value)
            previous = self._last_accepted_stacks.get(item.seat)
            if previous is not None and current < previous:
                encoded = (
                    f"{diagnostic.target_fingerprint}:{self._hand_epoch}:stack:"
                    f"{item.seat}:{previous}:{current}"
                ).encode()
                event_id = hashlib.sha256(encoded).hexdigest()
                if not any(delta.event_id == event_id for delta in self._stack_deltas):
                    self._stack_deltas.append(
                        StackDeltaCandidate(
                            event_id=event_id,
                            hand_epoch=self._hand_epoch,
                            frame_sequence=diagnostic.frame_sequence,
                            seat=item.seat,
                            street=stack_street,
                            previous_stack_native=previous,
                            current_stack_native=current,
                            committed_native=previous - current,
                        )
                    )
            if previous != current:
                self._last_accepted_stacks[item.seat] = current
        by_action_seat = {action.seat: action for action in diagnostic.seat_actions}
        action_consensus: list[SeatActionConsensus] = []
        for seat in range(diagnostic.table_size):
            observation = by_action_seat.get(seat)
            samples = self._action_samples[seat]
            if observation is None or observation.action is None:
                samples.clear()
                result = self._empty_consensus("current_action_absent")
            else:
                result = self._append_consecutive(
                    samples,
                    TemporalSample(
                        frame_sequence=diagnostic.frame_sequence,
                        content_sha256=diagnostic.content_sha256,
                        value=observation.action,
                        confidence=observation.confidence,
                    ),
                )
            action_consensus.append(SeatActionConsensus(seat=seat, consensus=result))
        self._action_consensus = action_consensus
        controls = diagnostic.hero_action_controls
        if controls.mode in {"absent", "ambiguous"}:
            self._hero_control_samples.clear()
            self._hero_control_consensus = self._empty_consensus(
                f"current_hero_controls_{controls.mode}"
            )
        else:
            control_value = ":".join(
                (
                    controls.mode,
                    ",".join(controls.available_actions),
                    ",".join(controls.pre_action_toggles),
                    str(controls.call_amount_native or ""),
                )
            )
            self._hero_control_consensus = self._append_consecutive(
                self._hero_control_samples,
                TemporalSample(
                    frame_sequence=diagnostic.frame_sequence,
                    content_sha256=diagnostic.content_sha256,
                    value=control_value,
                    confidence=controls.confidence,
                ),
            )
        visible_by_seat = {
            action.seat: action.action for action in diagnostic.seat_actions
        }
        for seat in range(diagnostic.table_size):
            if visible_by_seat.get(seat) is None:
                self._action_armed_seats.add(seat)
        if (
            self._board_consensus.accepted
            and self._mode_consensus.accepted
        ):
            street_by_cards = {0: "preflop", 3: "flop", 4: "turn", 5: "river"}
            street = street_by_cards.get(int(self._board_consensus.value or "-1"))
            if street is not None:
                for action in action_consensus:
                    result = action.consensus
                    if not result.accepted or result.value is None:
                        continue
                    if action.seat not in self._action_armed_seats:
                        continue
                    occurrence_key = (
                        self._hand_epoch,
                        street,
                        action.seat,
                        result.value,
                    )
                    occurrence = self._action_occurrence_counts.get(occurrence_key, 0) + 1
                    encoded = (
                        f"{diagnostic.target_fingerprint}:{self._hand_epoch}:"
                        f"{street}:{action.seat}:{result.value}:{occurrence}"
                    ).encode()
                    self._derived_actions.append(
                        DerivedActionCandidate(
                            event_id=hashlib.sha256(encoded).hexdigest(),
                            hand_epoch=self._hand_epoch,
                            frame_sequence=diagnostic.frame_sequence,
                            seat=action.seat,
                            street=street,
                            action=result.value,
                            confidence=result.confidence,
                            occurrence=occurrence,
                            dealer_seat=(
                                int(self._dealer_consensus.value)
                                if self._dealer_consensus.accepted
                                and self._dealer_consensus.value is not None
                                else None
                            ),
                            active_seats=list(self._active_seats),
                        )
                    )
                    self._action_occurrence_counts[occurrence_key] = occurrence
                    self._action_armed_seats.discard(action.seat)

    def _record_board_cards(self, diagnostic: LiveCaptureDiagnostic) -> None:
        expected = diagnostic.board_card_slots
        if (
            not diagnostic.board_geometry_supported
            or expected not in {3, 4, 5}
            or len(diagnostic.board_cards) != expected
            or any(card.card is None for card in diagnostic.board_cards)
        ):
            for samples in self._card_samples.values():
                samples.clear()
            self._board_card_consensus = []
            self._recognized_board_cards = []
            self._board_cards_accepted = False
            self._board_cards_reason = (
                "no_postflop_board" if expected == 0 else "current_cards_ambiguous"
            )
            return
        results: list[TemporalConsensus] = []
        for index, card in enumerate(diagnostic.board_cards):
            assert card.card is not None
            results.append(
                self._append_consecutive(
                    self._card_samples[index],
                    TemporalSample(
                        frame_sequence=diagnostic.frame_sequence,
                        content_sha256=diagnostic.content_sha256,
                        value=card.card,
                        confidence=card.confidence,
                    ),
                )
            )
        values = [result.value for result in results if result.accepted and result.value]
        self._board_card_consensus = results
        self._board_cards_accepted = len(values) == expected and len(set(values)) == expected
        self._recognized_board_cards = values if self._board_cards_accepted else []
        if self._board_cards_accepted:
            self._board_cards_reason = "temporal and card-uniqueness gates passed"
        elif len(values) == expected:
            self._board_cards_reason = "duplicate physical card candidate"
        else:
            self._board_cards_reason = "insufficient stable card frames"

    def _record_hero_cards(self, diagnostic: LiveCaptureDiagnostic) -> None:
        observation = diagnostic.hero_cards
        valid_single_frame = (
            observation.geometry_supported
            and len(observation.cards) == 2
            and all(card.card is not None for card in observation.cards)
        )
        if not valid_single_frame:
            if self._hero_cards_accepted:
                self._hero_cards_reason = "accepted earlier in the current hand epoch"
                return
            for samples in self._hero_card_samples.values():
                samples.clear()
            self._hero_card_consensus = []
            self._recognized_hero_cards = []
            self._hero_cards_accepted = False
            self._hero_cards_reason = observation.reason
            return
        results: list[TemporalConsensus] = []
        for index, card in enumerate(observation.cards):
            assert card.card is not None
            results.append(
                self._append_consecutive(
                    self._hero_card_samples[index],
                    TemporalSample(
                        frame_sequence=diagnostic.frame_sequence,
                        content_sha256=diagnostic.content_sha256,
                        value=card.card,
                        confidence=card.confidence,
                    ),
                )
            )
        self._hero_card_consensus = results
        if not all(result.accepted and result.value for result in results):
            self._recognized_hero_cards = []
            self._hero_cards_accepted = False
            self._hero_cards_reason = "hero card slots require three consecutive frames"
            return
        cards = [result.value for result in results if result.value is not None]
        known_board = set(self._recognized_board_cards if self._board_cards_accepted else [])
        if len(cards) != 2 or len(set(cards)) != 2 or known_board.intersection(cards):
            self._recognized_hero_cards = []
            self._hero_cards_accepted = False
            self._hero_cards_reason = "hero cards violate physical-card uniqueness"
            return
        self._recognized_hero_cards = cards
        self._hero_cards_accepted = True
        self._hero_cards_reason = "three-frame hero-card consensus and uniqueness passed"

    def _record_seat_statuses(self, diagnostic: LiveCaptureDiagnostic) -> None:
        panels = {panel.seat: panel for panel in diagnostic.seat_panels}
        status_results: list[SeatStatusConsensus] = []
        for occupancy in diagnostic.seat_observations:
            panel = panels.get(occupancy.seat)
            if occupancy.status == "empty":
                value = "empty"
                confidence = occupancy.confidence
            elif panel is not None and panel.status == "on_break":
                value = "on_break"
                confidence = panel.confidence
            elif occupancy.status == "occupied":
                value = "seated"
                confidence = occupancy.confidence
            else:
                value = None
                confidence = 0.0
            samples = self._status_samples[occupancy.seat]
            if value is None:
                samples.clear()
                result = self._empty_consensus("current_seat_status_ambiguous")
            else:
                result = self._append_consecutive(
                    samples,
                    TemporalSample(
                        frame_sequence=diagnostic.frame_sequence,
                        content_sha256=diagnostic.content_sha256,
                        value=value,
                        confidence=confidence,
                    ),
                )
            status_results.append(
                SeatStatusConsensus(seat=occupancy.seat, consensus=result)
            )
        self._seat_status_consensus = status_results
        if len(status_results) != diagnostic.table_size or not all(
            item.consensus.accepted for item in status_results
        ):
            self._active_seats = []
            self._provisional_positions = {}
            self._positions_reason = "seat_statuses_unresolved"
            return
        self._active_seats = [
            item.seat for item in status_results if item.consensus.value == "seated"
        ]
        self._epoch_active_evidence = list(self._active_seats)
        if not self._dealer_consensus.accepted or self._dealer_consensus.value is None:
            self._provisional_positions = {}
            self._positions_reason = "dealer_unresolved"
            return
        if self._hand_epoch > 0:
            self._hand_boundary_validation = validate_live_hand_boundary(
                hand_epoch=self._hand_epoch,
                table_size=diagnostic.table_size,
                previous_dealer_seat=self._previous_epoch_dealer,
                current_dealer_seat=int(self._dealer_consensus.value),
                previous_active_seats=self._previous_epoch_active_seats,
                current_active_seats=self._active_seats,
            )
        try:
            self._provisional_positions = assign_full_ring_positions(
                table_size=diagnostic.table_size,
                dealer_seat=int(self._dealer_consensus.value),
                active_seats=set(self._active_seats),
            )
            self._positions_reason = "full-ring dealer and active-seat gates passed"
        except ValueError:
            self._provisional_positions = {}
            self._positions_reason = "partial_ring_position_naming_unavailable"

    def _record_failure(self, error: Exception) -> None:
        self._frames_failed += 1
        self._consecutive_failures += 1
        self._last_error = str(error)

    async def _run(self) -> None:
        try:
            while not self._stop_event.is_set():
                try:
                    await self.inspect_once(table_size=self._table_size)
                except TargetIdentityChanged:
                    break
                except (OSError, RuntimeError, ValueError):
                    if self._consecutive_failures >= self._maximum_consecutive_failures:
                        break
                with suppress(TimeoutError):
                    await asyncio.wait_for(
                        self._stop_event.wait(), timeout=self._interval_ms / 1000
                    )
        finally:
            self._stopped_at = datetime.now(UTC)

    def status(self) -> LiveObservationStatus:
        latest_at = self.latest_diagnostic.captured_at if self.latest_diagnostic else None
        latest_age_ms = None
        if latest_at is not None:
            latest_age_ms = max(0.0, (datetime.now(UTC) - latest_at).total_seconds() * 1000)
        return LiveObservationStatus(
            running=self.running,
            table_size=self._table_size,
            interval_ms=self._interval_ms,
            started_at=self._started_at,
            stopped_at=self._stopped_at,
            latest_sequence=self._latest_sequence,
            frames_attempted=self._frames_attempted,
            frames_succeeded=self._frames_succeeded,
            frames_failed=self._frames_failed,
            consecutive_failures=self._consecutive_failures,
            latest_captured_at=latest_at,
            latest_age_ms=latest_age_ms,
            target_fingerprint=self._session_target_fingerprint,
            target_stable=self._target_stable,
            current_hand_mode=(
                self.latest_diagnostic.current_hand_mode
                if self.latest_diagnostic
                else "ambiguous"
            ),
            current_hand_supported=(
                self.latest_diagnostic.current_hand_supported
                if self.latest_diagnostic
                else False
            ),
            mode_consensus=self._mode_consensus,
            blind_consensus=self._blind_consensus,
            board_consensus=self._board_consensus,
            board_card_consensus=self._board_card_consensus,
            recognized_board_cards=self._recognized_board_cards,
            board_cards_accepted=self._board_cards_accepted,
            board_cards_reason=self._board_cards_reason,
            hero_card_consensus=self._hero_card_consensus,
            recognized_hero_cards=self._recognized_hero_cards,
            hero_cards_accepted=self._hero_cards_accepted,
            hero_cards_reason=self._hero_cards_reason,
            dealer_consensus=self._dealer_consensus,
            seat_status_consensus=self._seat_status_consensus,
            active_seats=self._active_seats,
            provisional_positions=self._provisional_positions,
            positions_reason=self._positions_reason,
            pot_consensus=self._pot_consensus,
            seat_stack_consensus=self._stack_consensus,
            seat_action_consensus=self._action_consensus,
            hero_control_consensus=self._hero_control_consensus,
            hand_epoch=self._hand_epoch,
            hand_boundary_validation=self._hand_boundary_validation,
            reconstruction_readiness=self._reconstruction_readiness(),
            derived_action_candidates=list(self._derived_actions),
            stack_delta_candidates=list(self._stack_deltas),
            pot_delta_candidates=list(self._pot_deltas),
            action_amount_reconciliations=self._reconcile_action_amounts(),
            action_pot_reconciliations=self._reconcile_action_pot(),
            action_order_validations=validate_action_order(
                list(self._derived_actions), table_size=self._table_size
            ),
            last_error=self._last_error,
        )

    def _reconcile_action_amounts(self) -> list[ActionAmountReconciliation]:
        amount_actions = {"call", "bet", "raise", "all_in"}
        candidate_deltas: dict[str, list[StackDeltaCandidate]] = {}
        reverse_count: dict[str, int] = {}
        for action in self._derived_actions:
            if action.action not in amount_actions:
                continue
            matches = [
                delta
                for delta in self._stack_deltas
                if delta.hand_epoch == action.hand_epoch
                and delta.seat == action.seat
                and abs(delta.frame_sequence - action.frame_sequence) <= 8
                and (delta.street == "unknown" or delta.street == action.street)
            ]
            candidate_deltas[action.event_id] = matches
            for delta in matches:
                reverse_count[delta.event_id] = reverse_count.get(delta.event_id, 0) + 1
        results: list[ActionAmountReconciliation] = []
        for action in self._derived_actions:
            if action.action not in amount_actions:
                results.append(
                    ActionAmountReconciliation(
                        action_event_id=action.event_id,
                        seat=action.seat,
                        action=action.action,
                        amount_native=Decimal("0"),
                        status="not_required",
                        reason="fold/check has no committed amount; order validation pending",
                    )
                )
                continue
            matches = candidate_deltas.get(action.event_id, [])
            if len(matches) == 1 and reverse_count[matches[0].event_id] == 1:
                delta = matches[0]
                results.append(
                    ActionAmountReconciliation(
                        action_event_id=action.event_id,
                        delta_event_id=delta.event_id,
                        seat=action.seat,
                        action=action.action,
                        amount_native=delta.committed_native,
                        status="matched",
                        reason="mutually unique same-seat temporal stack delta",
                    )
                )
            elif matches:
                results.append(
                    ActionAmountReconciliation(
                        action_event_id=action.event_id,
                        seat=action.seat,
                        action=action.action,
                        status="ambiguous",
                        reason="multiple actions or deltas share the temporal match window",
                    )
                )
            else:
                results.append(
                    ActionAmountReconciliation(
                        action_event_id=action.event_id,
                        seat=action.seat,
                        action=action.action,
                        status="pending",
                        reason="no mutually unique same-seat stack delta in the match window",
                    )
                )
        return results

    def _reconstruction_readiness(self) -> LiveReconstructionReadiness:
        issues: list[str] = []
        if self._hand_boundary_validation.status != "validated":
            issues.append("hand_boundary_not_validated")
        if not self._mode_consensus.accepted:
            issues.append("hand_mode_not_stable")
        elif self._mode_consensus.value == "single_board_bomb_pot":
            issues.append("bomb_pot_contributions_not_reconstructed")
        big_blind: Decimal | None = None
        if not self._blind_consensus.accepted or self._blind_consensus.value is None:
            issues.append("native_blinds_not_stable")
        else:
            _, big_token = self._blind_consensus.value.split("/", maxsplit=1)
            big_blind = Decimal(big_token)
        if not self._dealer_consensus.accepted:
            issues.append("dealer_not_stable")
        if len(self._active_seats) < 2:
            issues.append("active_seat_ring_not_stable")
        stable_stack_seats = {
            item.seat
            for item in self._stack_consensus
            if item.consensus.accepted and item.consensus.value is not None
        }
        if not set(self._active_seats).issubset(stable_stack_seats):
            issues.append("active_stacks_not_stable")
        if 0 in self._active_seats and not self._hero_cards_accepted:
            issues.append("hero_cards_not_stable")
        if (
            self._board_consensus.accepted
            and self._board_consensus.value in {"3", "4", "5"}
            and not self._board_cards_accepted
        ):
            issues.append("board_cards_not_stable")

        current_actions = [
            action for action in self._derived_actions if action.hand_epoch == self._hand_epoch
        ]
        current_ids = {action.event_id for action in current_actions}
        amount_by_id = {
            item.action_event_id: item for item in self._reconcile_action_amounts()
        }
        pot_by_id = {item.action_event_id: item for item in self._reconcile_action_pot()}
        eligible_ids: list[str] = []
        for action in current_actions:
            amount = amount_by_id.get(action.event_id)
            pot = pot_by_id.get(action.event_id)
            if amount is None or amount.status not in {"matched", "not_required"}:
                issues.append(f"action_amount_unresolved:{action.event_id}")
                continue
            if pot is None or pot.status not in {"matched", "not_required"}:
                issues.append(f"action_pot_unresolved:{action.event_id}")
                continue
            eligible_ids.append(action.event_id)
        order_results = [
            result
            for result in validate_action_order(
                list(self._derived_actions), table_size=self._table_size
            )
            if result.hand_epoch == self._hand_epoch
        ]
        if current_ids and (
            not order_results
            or any(result.status != "prefix_consistent" for result in order_results)
        ):
            issues.append("clockwise_action_order_incomplete")
        issues = list(dict.fromkeys(issues))
        return LiveReconstructionReadiness(
            hand_epoch=self._hand_epoch,
            ready=not issues,
            big_blind_native=big_blind,
            eligible_action_event_ids=eligible_ids,
            issues=issues,
            reason=(
                "all provisional gates passed; canonical event construction may begin"
                if not issues
                else "one or more fail-closed reconstruction gates remain"
            ),
        )

    def _reconcile_action_pot(self) -> list[ActionPotReconciliation]:
        amount_results = {
            result.action_event_id: result for result in self._reconcile_action_amounts()
        }
        action_by_id = {action.event_id: action for action in self._derived_actions}
        exact_matches: dict[str, list[PotDeltaCandidate]] = {}
        nearby: dict[str, list[PotDeltaCandidate]] = {}
        reverse_count: dict[str, int] = {}
        for event_id, amount_result in amount_results.items():
            action = action_by_id[event_id]
            if amount_result.status != "matched" or amount_result.amount_native is None:
                continue
            candidates = [
                delta
                for delta in self._pot_deltas
                if delta.hand_epoch == action.hand_epoch
                and abs(delta.frame_sequence - action.frame_sequence) <= 8
                and (delta.street == "unknown" or delta.street == action.street)
            ]
            nearby[event_id] = candidates
            exact_matches[event_id] = [
                delta
                for delta in candidates
                if delta.increase_native == amount_result.amount_native
            ]
            for delta in exact_matches[event_id]:
                reverse_count[delta.event_id] = reverse_count.get(delta.event_id, 0) + 1

        results: list[ActionPotReconciliation] = []
        for event_id, amount_result in amount_results.items():
            action = action_by_id[event_id]
            if amount_result.status == "not_required":
                results.append(
                    ActionPotReconciliation(
                        action_event_id=event_id,
                        seat=action.seat,
                        action=action.action,
                        amount_native=Decimal("0"),
                        status="not_required",
                        reason="fold/check requires no chip or pot increase",
                    )
                )
                continue
            if amount_result.status != "matched":
                results.append(
                    ActionPotReconciliation(
                        action_event_id=event_id,
                        stack_delta_event_id=amount_result.delta_event_id,
                        seat=action.seat,
                        action=action.action,
                        amount_native=amount_result.amount_native,
                        status="pending" if amount_result.status == "pending" else "ambiguous",
                        reason="a unique stack amount is required before pot reconciliation",
                    )
                )
                continue
            matches = exact_matches.get(event_id, [])
            if len(matches) == 1 and reverse_count[matches[0].event_id] == 1:
                pot_delta = matches[0]
                results.append(
                    ActionPotReconciliation(
                        action_event_id=event_id,
                        stack_delta_event_id=amount_result.delta_event_id,
                        pot_delta_event_id=pot_delta.event_id,
                        seat=action.seat,
                        action=action.action,
                        amount_native=amount_result.amount_native,
                        status="matched",
                        reason="mutually unique equal stack decrease and pot increase",
                    )
                )
            elif matches:
                results.append(
                    ActionPotReconciliation(
                        action_event_id=event_id,
                        stack_delta_event_id=amount_result.delta_event_id,
                        seat=action.seat,
                        action=action.action,
                        amount_native=amount_result.amount_native,
                        status="ambiguous",
                        reason="multiple actions or pot deltas share the exact temporal match",
                    )
                )
            elif nearby.get(event_id):
                results.append(
                    ActionPotReconciliation(
                        action_event_id=event_id,
                        stack_delta_event_id=amount_result.delta_event_id,
                        seat=action.seat,
                        action=action.action,
                        amount_native=amount_result.amount_native,
                        status="mismatch",
                        reason="nearby stable pot increase does not equal the stack decrease",
                    )
                )
            else:
                results.append(
                    ActionPotReconciliation(
                        action_event_id=event_id,
                        stack_delta_event_id=amount_result.delta_event_id,
                        seat=action.seat,
                        action=action.action,
                        amount_native=amount_result.amount_native,
                        status="pending",
                        reason="no stable pot increase in the temporal match window",
                    )
                )
        return results
