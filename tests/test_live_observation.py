import asyncio
from datetime import UTC, datetime
from decimal import Decimal

from xpoker_agent.capture.frames import CapturedFrame
from xpoker_agent.vision.live_observation import LiveObservationService
from xpoker_agent.vision.models import (
    CardFaceObservation,
    DealerButtonObservation,
    DerivedActionCandidate,
    HeroCardsObservation,
    LiveCaptureDiagnostic,
    PotDeltaCandidate,
    PotObservation,
    SeatActionObservation,
    SeatPanelObservation,
    StackDeltaCandidate,
)


def _diagnostic(
    sequence: int,
    *,
    fingerprint: str = "a" * 64,
    mode: str = "standard_nlh",
) -> LiveCaptureDiagnostic:
    return LiveCaptureDiagnostic(
        captured_at=datetime.now(UTC),
        frame_sequence=sequence,
        content_sha256=f"{sequence:064x}",
        layout_id="xpoker-windows-10-portrait-9max-v1",
        table_size=9,
        frame_width=1,
        frame_height=1,
        target_hwnd=123,
        target_process_id=456,
        target_fingerprint=fingerprint,
        capture_latency_ms=1,
        ocr_latency_ms=1,
        visual_role_confidence=0.99,
        current_hand_supported=mode != "ambiguous",
        current_hand_mode=mode,
        standard_nlh_supported=mode == "standard_nlh",
        single_board_bomb_pot_supported=False,
        bomb_pot_state="scheduled",
        hands_until_bomb=5,
        small_blind_native=1,
        big_blind_native=2,
        rule_confidence=0.99,
        mode_reason="test fixture",
        rule_text="Bomb Pot: After 5 hands",
        pot_text="POT 10",
        pot=PotObservation(
            value_native=10,
            token="10",
            confidence=0.95,
            reason="test candidate",
        ),
        board_rows=1,
        board_card_slots=3,
        board_geometry_supported=True,
        board_geometry_confidence=0.99,
        regions={},
        hero_cards=HeroCardsObservation(
            geometry_supported=False,
            confidence=0.0,
            reason="test fixture",
        ),
        dealer=DealerButtonObservation(
            seat=4,
            confidence=0.95,
            reason="test candidate",
        ),
        seat_panels=[
            SeatPanelObservation(
                seat=0,
                status="seated",
                stack_native=100,
                stack_token="100",
                confidence=0.8,
                reason="test candidate",
            )
        ],
    )


def test_live_observation_builds_consensus_and_stops_cleanly() -> None:
    async def scenario() -> None:
        async def capture(_: int, sequence: int):
            return _diagnostic(sequence), CapturedFrame(1, 1, b"\x00" * 4)

        service = LiveObservationService(capture)
        assert await service.start(table_size=9, interval_ms=5) is True
        await asyncio.sleep(0.12)
        status = service.status()

        assert status.running is True
        assert status.frames_succeeded >= 3
        assert status.mode_consensus.accepted is True
        assert status.mode_consensus.value == "standard_nlh"
        assert status.blind_consensus.accepted is True
        assert status.blind_consensus.value == "1/2"
        assert status.pot_consensus.accepted is True
        assert status.pot_consensus.value == "10"
        assert status.seat_stack_consensus[0].consensus.accepted is True
        assert status.seat_stack_consensus[0].consensus.value == "100"
        assert status.target_stable is True
        assert await service.stop() is True
        assert service.status().running is False

    asyncio.run(scenario())


def test_changed_numeric_value_requires_fresh_consecutive_consensus() -> None:
    async def scenario() -> None:
        values = [100, 100, 100, 98, 98]

        async def capture(_: int, sequence: int):
            diagnostic = _diagnostic(sequence)
            value = values[min(sequence - 1, len(values) - 1)]
            diagnostic.seat_panels[0] = diagnostic.seat_panels[0].model_copy(
                update={"stack_native": value, "stack_token": str(value)}
            )
            return diagnostic, CapturedFrame(1, 1, b"\x00" * 4)

        service = LiveObservationService(capture)
        for _ in range(5):
            await service.inspect_once(table_size=9)
        result = service.status().seat_stack_consensus[0].consensus
        assert result.accepted is False
        assert result.stable_frames == 2

        await service.inspect_once(table_size=9)
        result = service.status().seat_stack_consensus[0].consensus
        assert result.accepted is True
        assert result.value == "98"
        assert len(service.status().stack_delta_candidates) == 1
        delta = service.status().stack_delta_candidates[0]
        assert delta.seat == 0
        assert delta.committed_native == 2
        assert delta.canonical_event_accepted is False

    asyncio.run(scenario())


def test_pot_delta_requires_two_stable_endpoints_and_does_not_bridge_ambiguity() -> None:
    async def scenario() -> None:
        values = [10, 10, 10, 16, 16, 16, None, 20, 20, 20]

        async def capture(_: int, sequence: int):
            diagnostic = _diagnostic(sequence)
            value = values[sequence - 1]
            diagnostic.pot = PotObservation(
                value_native=value,
                token=None if value is None else str(value),
                confidence=0.0 if value is None else 0.95,
                reason="test candidate",
            )
            return diagnostic, CapturedFrame(1, 1, b"\x00" * 4)

        service = LiveObservationService(capture)
        for _ in values:
            await service.inspect_once(table_size=9)
        deltas = service.status().pot_delta_candidates

        assert len(deltas) == 1
        assert deltas[0].previous_pot_native == Decimal("10")
        assert deltas[0].current_pot_native == Decimal("16")
        assert deltas[0].increase_native == Decimal("6")
        assert deltas[0].canonical_event_accepted is False

    asyncio.run(scenario())


def test_action_candidate_is_derived_once_after_clear_and_stable_badge() -> None:
    async def scenario() -> None:
        async def capture(_: int, sequence: int):
            diagnostic = _diagnostic(sequence)
            if sequence >= 4:
                diagnostic.seat_actions = [
                    SeatActionObservation(
                        seat=2,
                        action="fold",
                        confidence=0.9,
                        reason="test candidate",
                    )
                ]
            return diagnostic, CapturedFrame(1, 1, b"\x00" * 4)

        service = LiveObservationService(capture)
        for _ in range(8):
            await service.inspect_once(table_size=9)
        status = service.status()

        assert status.board_consensus.accepted is True
        assert status.board_consensus.value == "3"
        assert len(status.derived_action_candidates) == 1
        candidate = status.derived_action_candidates[0]
        assert candidate.seat == 2
        assert candidate.street == "flop"
        assert candidate.action == "fold"
        assert candidate.canonical_event_accepted is False
        reconciliation = status.action_amount_reconciliations[0]
        assert reconciliation.status == "not_required"
        assert reconciliation.amount_native == 0

    asyncio.run(scenario())


def test_cleared_badge_can_emit_a_second_same_action_occurrence() -> None:
    async def scenario() -> None:
        async def capture(_: int, sequence: int):
            diagnostic = _diagnostic(sequence)
            if sequence in {4, 5, 6, 8, 9, 10}:
                diagnostic.seat_actions = [
                    SeatActionObservation(
                        seat=3,
                        action="call",
                        confidence=0.9,
                        reason="test candidate",
                    )
                ]
            return diagnostic, CapturedFrame(1, 1, b"\x00" * 4)

        service = LiveObservationService(capture)
        for _ in range(10):
            await service.inspect_once(table_size=9)
        candidates = service.status().derived_action_candidates

        assert len(candidates) == 2
        assert [candidate.occurrence for candidate in candidates] == [1, 2]
        assert candidates[0].event_id != candidates[1].event_id

    asyncio.run(scenario())


def test_action_amount_reconciliation_requires_a_mutually_unique_delta() -> None:
    async def capture(_: int, sequence: int):
        return _diagnostic(sequence), CapturedFrame(1, 1, b"\x00" * 4)

    service = LiveObservationService(capture)
    action = DerivedActionCandidate(
        event_id="a" * 64,
        hand_epoch=3,
        frame_sequence=20,
        seat=4,
        street="turn",
        action="bet",
        confidence=0.95,
    )
    delta = StackDeltaCandidate(
        event_id="c" * 64,
        hand_epoch=3,
        frame_sequence=22,
        seat=4,
        street="turn",
        previous_stack_native=Decimal("100"),
        current_stack_native=Decimal("94"),
        committed_native=Decimal("6"),
    )
    service._derived_actions.append(action)
    service._stack_deltas.append(delta)

    result = service._reconcile_action_amounts()

    assert len(result) == 1
    assert result[0].status == "matched"
    assert result[0].amount_native == Decimal("6")
    assert result[0].delta_event_id == delta.event_id
    assert result[0].canonical_event_accepted is False

    service._pot_deltas.append(
        PotDeltaCandidate(
            event_id="e" * 64,
            hand_epoch=3,
            frame_sequence=23,
            street="turn",
            previous_pot_native=Decimal("12"),
            current_pot_native=Decimal("18"),
            increase_native=Decimal("6"),
        )
    )
    pot_result = service._reconcile_action_pot()

    assert len(pot_result) == 1
    assert pot_result[0].status == "matched"
    assert pot_result[0].amount_native == Decimal("6")
    assert pot_result[0].pot_delta_event_id == "e" * 64
    assert pot_result[0].canonical_event_accepted is False

    service._derived_actions.append(
        action.model_copy(
            update={
                "event_id": "d" * 64,
                "frame_sequence": 24,
                "action": "raise",
            }
        )
    )
    result = service._reconcile_action_amounts()

    assert [item.status for item in result] == ["ambiguous", "ambiguous"]
    assert all(item.amount_native is None for item in result)
    assert [item.status for item in service._reconcile_action_pot()] == [
        "ambiguous",
        "ambiguous",
    ]


def test_board_cards_require_temporal_consensus_and_physical_uniqueness() -> None:
    async def scenario() -> None:
        async def capture(_: int, sequence: int):
            diagnostic = _diagnostic(sequence)
            diagnostic.board_cards = [
                CardFaceObservation(
                    card=card,
                    confidence=0.85,
                    rank_distance=0.02,
                    rank_margin=0.08,
                    reason="test candidate",
                )
                for card in ("Jh", "2d", "8h")
            ]
            return diagnostic, CapturedFrame(1, 1, b"\x00" * 4)

        service = LiveObservationService(capture)
        for _ in range(3):
            await service.inspect_once(table_size=9)
        status = service.status()

        assert status.board_cards_accepted is True
        assert status.recognized_board_cards == ["Jh", "2d", "8h"]

    asyncio.run(scenario())


def test_hero_cards_require_temporal_consensus_and_persist_within_hand() -> None:
    async def scenario() -> None:
        async def capture(_: int, sequence: int):
            diagnostic = _diagnostic(sequence)
            if sequence <= 3:
                diagnostic.hero_cards = HeroCardsObservation(
                    geometry_supported=True,
                    cards=[
                        CardFaceObservation(
                            card=card,
                            confidence=0.9,
                            rank_distance=0.01,
                            rank_margin=0.08,
                            reason="test candidate",
                        )
                        for card in ("As", "2d")
                    ],
                    confidence=0.9,
                    reason="test candidate",
                )
            return diagnostic, CapturedFrame(1, 1, b"\x00" * 4)

        service = LiveObservationService(capture)
        for _ in range(4):
            await service.inspect_once(table_size=9)
        status = service.status()

        assert status.hero_cards_accepted is True
        assert status.recognized_hero_cards == ["As", "2d"]
        assert status.hero_cards_reason == "accepted earlier in the current hand epoch"

    asyncio.run(scenario())


def test_live_observation_stops_if_target_identity_changes() -> None:
    async def scenario() -> None:
        async def capture(_: int, sequence: int):
            fingerprint = "a" * 64 if sequence == 1 else "b" * 64
            return _diagnostic(sequence, fingerprint=fingerprint), CapturedFrame(1, 1, b"\x00" * 4)

        service = LiveObservationService(capture)
        await service.start(table_size=9, interval_ms=2)
        await asyncio.sleep(0.12)
        status = service.status()

        assert status.running is False
        assert status.target_stable is False
        assert status.frames_succeeded == 1
        assert status.frames_failed == 1
        assert "identity changed" in (status.last_error or "")

    asyncio.run(scenario())


def test_live_observation_stops_after_three_consecutive_capture_failures() -> None:
    async def scenario() -> None:
        async def capture(_: int, __: int):
            raise RuntimeError("authorized table temporarily unavailable")

        service = LiveObservationService(capture)
        await service.start(table_size=9, interval_ms=2)
        await asyncio.sleep(0.12)
        status = service.status()

        assert status.running is False
        assert status.frames_attempted == 3
        assert status.frames_failed == 3
        assert status.consecutive_failures == 3
        assert status.last_error == "authorized table temporarily unavailable"

    asyncio.run(scenario())


def test_ambiguous_mode_never_becomes_accepted_consensus() -> None:
    async def scenario() -> None:
        async def capture(_: int, sequence: int):
            return _diagnostic(sequence, mode="ambiguous"), CapturedFrame(1, 1, b"\x00" * 4)

        service = LiveObservationService(capture)
        await service.start(table_size=9, interval_ms=2)
        await asyncio.sleep(0.12)
        status = service.status()

        assert status.frames_succeeded >= 3
        assert status.mode_consensus.accepted is False
        assert status.mode_consensus.reason == "current_mode_ambiguous"
        await service.stop()

    asyncio.run(scenario())
