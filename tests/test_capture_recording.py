import pytest

from xpoker_agent.capture.models import AuthorizedTargetProfile, PixelRect, WindowCandidate
from xpoker_agent.capture.recording import AdaptiveFrameScheduler, select_authorized_table


def test_adaptive_scheduler_stays_within_configured_bounds() -> None:
    scheduler = AdaptiveFrameScheduler.create(5, 15)

    for _ in range(100):
        scheduler.observe(content_changed=False, capture_latency_ms=1000)
    assert scheduler.current_fps == 5

    for _ in range(100):
        scheduler.observe(content_changed=True, capture_latency_ms=1)
    assert scheduler.current_fps == 15


def test_adaptive_scheduler_rejects_invalid_bounds() -> None:
    try:
        AdaptiveFrameScheduler.create(15, 5)
    except ValueError as error:
        assert "bounds" in str(error)
    else:
        raise AssertionError("invalid frame-rate bounds must fail closed")


def authorized_profile() -> AuthorizedTargetProfile:
    return AuthorizedTargetProfile(
        profile_id="test",
        enabled=True,
        allowed_process_names=["X-Poker.exe"],
        allowed_executable_sha256=["a" * 64],
        title_patterns=[r"(?i)x[- ]?poker"],
        allowed_window_classes=["GLFW30"],
        notes="test",
    )


def table_candidate(hwnd: int) -> WindowCandidate:
    return WindowCandidate(
        hwnd=hwnd,
        process_id=1,
        process_name="X-Poker.exe",
        executable_sha256="a" * 64,
        title="X-Poker",
        window_class="GLFW30",
        window_rect=PixelRect(left=0, top=0, right=461, bottom=839),
        client_rect=PixelRect(left=8, top=31, right=453, bottom=831),
        visible=True,
        minimized=False,
        dpi=96,
        visual_role="table",
        visual_role_confidence=0.95,
    )


def test_authorized_selection_requires_exactly_one_table(monkeypatch) -> None:
    monkeypatch.setattr(
        "xpoker_agent.capture.recording.discover_xpoker_windows",
        lambda **_: (table_candidate(1), table_candidate(2)),
    )

    with pytest.raises(RuntimeError, match="exactly one"):
        select_authorized_table(authorized_profile())


def test_authorized_selection_returns_unique_table(monkeypatch) -> None:
    expected = table_candidate(1)
    monkeypatch.setattr(
        "xpoker_agent.capture.recording.discover_xpoker_windows",
        lambda **_: (expected,),
    )

    assert select_authorized_table(authorized_profile()) == expected
