import asyncio
from datetime import UTC, datetime

from xpoker_agent.capture.frames import CapturedFrame
from xpoker_agent.vision.live_observation import LiveObservationService
from xpoker_agent.vision.models import LiveCaptureDiagnostic


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
        rule_confidence=0.99,
        mode_reason="test fixture",
        rule_text="Bomb Pot: After 5 hands",
        pot_text="POT 10",
        board_rows=1,
        board_card_slots=3,
        board_geometry_supported=True,
        board_geometry_confidence=0.99,
        regions={},
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
        assert status.target_stable is True
        assert await service.stop() is True
        assert service.status().running is False

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
