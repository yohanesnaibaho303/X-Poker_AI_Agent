"""Authorized-target profile loading and fail-closed X-Poker matching."""

from __future__ import annotations

import json
import re
from pathlib import Path

from xpoker_agent.capture.models import AuthorizedTargetProfile, TargetMatch, WindowCandidate
from xpoker_agent.config import PROJECT_ROOT

EXAMPLE_PROFILE = PROJECT_ROOT / "configs" / "capture" / "authorized_target.example.json"
LOCAL_PROFILE = PROJECT_ROOT / "configs" / "capture" / "authorized_target.local.json"


def load_target_profile(path: Path | None = None) -> AuthorizedTargetProfile:
    selected = path or (LOCAL_PROFILE if LOCAL_PROFILE.exists() else EXAMPLE_PROFILE)
    with selected.open("r", encoding="utf-8") as handle:
        payload = json.load(handle)
    return AuthorizedTargetProfile.model_validate(payload)


def looks_like_xpoker(candidate: WindowCandidate) -> bool:
    process_stem = Path(candidate.process_name or "").stem
    process_match = re.fullmatch(r"(?i)x[-_ ]?poker", process_stem) is not None
    title_match = (
        re.fullmatch(
            r"(?i)\s*x[- ]?poker(?:\s*[-–—:|]\s*(?:holdem|home game|table|nlh).*)?\s*",
            candidate.title,
        )
        is not None
    )
    return process_match or title_match


def match_authorized_target(
    candidate: WindowCandidate, profile: AuthorizedTargetProfile
) -> TargetMatch:
    reasons: list[str] = []
    if not profile.enabled:
        reasons.append("authorization profile is disabled")
    if not looks_like_xpoker(candidate):
        reasons.append("candidate does not identify as X-Poker")

    process_name = (candidate.process_name or "").casefold()
    if process_name not in profile.allowed_process_names:
        reasons.append("process name is not allowlisted")

    if profile.require_title_match and not any(
        re.search(pattern, candidate.title) for pattern in profile.title_patterns
    ):
        reasons.append("window title does not match the authorized X-Poker pattern")

    if (
        profile.allowed_window_classes
        and candidate.window_class not in profile.allowed_window_classes
    ):
        reasons.append("window class is not allowlisted")

    if (
        profile.allowed_executable_sha256
        and candidate.executable_sha256 not in profile.allowed_executable_sha256
    ):
        reasons.append("executable hash is not allowlisted")

    if candidate.visual_role != profile.required_visual_role:
        reasons.append("window is not visually classified as the authorized table")
    elif candidate.visual_role_confidence < profile.minimum_visual_role_confidence:
        reasons.append("table visual-role confidence is below the authorization threshold")

    if not candidate.visible or candidate.minimized:
        reasons.append("window is not visible and capture-ready")
    if candidate.client_rect.width <= 0 or candidate.client_rect.height <= 0:
        reasons.append("window has an empty client area")

    return TargetMatch(candidate_hwnd=candidate.hwnd, eligible=not reasons, reasons=reasons)
