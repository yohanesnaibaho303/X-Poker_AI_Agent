from xpoker_agent.capture.models import AuthorizedTargetProfile, PixelRect, WindowCandidate
from xpoker_agent.capture.profile import looks_like_xpoker, match_authorized_target
from xpoker_agent.capture.windows import executable_sha256


def candidate(*, title: str = "X-Poker", process_name: str = "xpoker.exe") -> WindowCandidate:
    return WindowCandidate(
        hwnd=101,
        process_id=202,
        process_name=process_name,
        executable_path=f"C:\\AuthorizedTest\\{process_name}",
        executable_sha256="a" * 64,
        title=title,
        window_class="QtWindow",
        window_rect=PixelRect(left=0, top=0, right=900, bottom=700),
        client_rect=PixelRect(left=8, top=30, right=892, bottom=692),
        visible=True,
        minimized=False,
        dpi=96,
        visual_role="table",
        visual_role_confidence=0.99,
    )


def profile(*, enabled: bool = True) -> AuthorizedTargetProfile:
    return AuthorizedTargetProfile(
        profile_id="authorized-xpoker-test",
        enabled=enabled,
        allowed_process_names=["xpoker.exe"],
        allowed_executable_sha256=["a" * 64],
        title_patterns=[r"(?i)^x-poker"],
        allowed_window_classes=["QtWindow"],
        notes="test profile",
    )


def test_only_xpoker_identity_is_discovered() -> None:
    assert looks_like_xpoker(candidate())
    assert not looks_like_xpoker(candidate(title="PokerStars", process_name="pokerstars.exe"))
    assert not looks_like_xpoker(candidate(title="GGPoker", process_name="ggpoker.exe"))
    assert not looks_like_xpoker(
        candidate(title="X-Poker_AI_Agent - Visual Studio Code", process_name="Code.exe")
    )


def test_disabled_profile_fails_closed() -> None:
    result = match_authorized_target(candidate(), profile(enabled=False))

    assert result.eligible is False
    assert "authorization profile is disabled" in result.reasons


def test_explicit_xpoker_profile_matches() -> None:
    result = match_authorized_target(candidate(), profile())

    assert result.eligible is True
    assert result.reasons == []


def test_room_title_is_not_a_stable_authorization_requirement() -> None:
    result = match_authorized_target(candidate(title="24 aug"), profile())

    assert result.eligible is True


def test_title_can_still_be_enabled_as_an_optional_extra_gate() -> None:
    strict_profile = profile().model_copy(update={"require_title_match": True})
    result = match_authorized_target(candidate(title="24 aug"), strict_profile)

    assert result.eligible is False
    assert "window title does not match" in result.reasons[0]


def test_other_poker_clients_never_match() -> None:
    result = match_authorized_target(
        candidate(title="GGPoker", process_name="ggpoker.exe"), profile()
    )

    assert result.eligible is False
    assert "candidate does not identify as X-Poker" in result.reasons
    assert "process name is not allowlisted" in result.reasons


def test_minimized_xpoker_window_is_not_capture_ready() -> None:
    window = candidate()
    window.minimized = True

    result = match_authorized_target(window, profile())

    assert result.eligible is False
    assert "window is not visible and capture-ready" in result.reasons


def test_lobby_window_never_matches_table_profile() -> None:
    window = candidate()
    window.visual_role = "lobby"
    window.visual_role_confidence = 0.99

    result = match_authorized_target(window, profile())

    assert result.eligible is False
    assert "window is not visually classified as the authorized table" in result.reasons


def test_executable_hash_is_deterministic(tmp_path) -> None:
    executable = tmp_path / "xpoker-test.exe"
    executable.write_bytes(b"authorized test fixture")

    assert executable_sha256(str(executable)) == (
        "71d4bfce569e8649ce1b4a240eab1f9996431cedfedbfd01d358ccd031012ca7"
    )
