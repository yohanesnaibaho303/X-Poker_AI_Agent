"""Read-only Win32 top-level window enumeration."""

from __future__ import annotations

import ctypes
import hashlib
import os
from ctypes import wintypes
from pathlib import Path

from xpoker_agent.capture.models import PixelRect, WindowCandidate
from xpoker_agent.capture.profile import looks_like_xpoker

PROCESS_QUERY_LIMITED_INFORMATION = 0x1000


def _window_text(user32: ctypes.WinDLL, hwnd: int) -> str:
    length = user32.GetWindowTextLengthW(hwnd)
    buffer = ctypes.create_unicode_buffer(length + 1)
    user32.GetWindowTextW(hwnd, buffer, len(buffer))
    return buffer.value


def _window_class(user32: ctypes.WinDLL, hwnd: int) -> str:
    buffer = ctypes.create_unicode_buffer(256)
    user32.GetClassNameW(hwnd, buffer, len(buffer))
    return buffer.value


def _process_path(kernel32: ctypes.WinDLL, process_id: int) -> str | None:
    handle = kernel32.OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION, False, process_id)
    if not handle:
        return None
    try:
        size = wintypes.DWORD(32768)
        buffer = ctypes.create_unicode_buffer(size.value)
        if not kernel32.QueryFullProcessImageNameW(handle, 0, buffer, ctypes.byref(size)):
            return None
        return buffer.value
    finally:
        kernel32.CloseHandle(handle)


def enumerate_windows() -> tuple[WindowCandidate, ...]:
    if os.name != "nt":
        return ()

    user32 = ctypes.WinDLL("user32", use_last_error=True)
    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    h_desk = user32.OpenDesktopW("default", 0, False, 0x0100 | 0x0040 | 0x0001 | 0x0002)
    if h_desk:
        user32.SetThreadDesktop(h_desk)
    candidates: list[WindowCandidate] = []
    callback_type = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)

    def callback(hwnd: int, _: int) -> bool:
        if not user32.IsWindowVisible(hwnd):
            return True
        title = _window_text(user32, hwnd)
        if not title:
            return True

        process_id = wintypes.DWORD()
        user32.GetWindowThreadProcessId(hwnd, ctypes.byref(process_id))
        executable_path = _process_path(kernel32, process_id.value)
        process_name = Path(executable_path).name if executable_path else None

        window_rect = wintypes.RECT()
        client_rect = wintypes.RECT()
        if not user32.GetWindowRect(hwnd, ctypes.byref(window_rect)):
            return True
        if not user32.GetClientRect(hwnd, ctypes.byref(client_rect)):
            return True
        client_origin = wintypes.POINT(client_rect.left, client_rect.top)
        user32.ClientToScreen(hwnd, ctypes.byref(client_origin))
        client_bounds = PixelRect(
            left=client_origin.x,
            top=client_origin.y,
            right=client_origin.x + client_rect.right,
            bottom=client_origin.y + client_rect.bottom,
        )

        dpi = None
        get_dpi = getattr(user32, "GetDpiForWindow", None)
        if get_dpi is not None:
            dpi_value = int(get_dpi(hwnd))
            dpi = dpi_value or None

        candidates.append(
            WindowCandidate(
                hwnd=int(hwnd),
                process_id=process_id.value,
                process_name=process_name,
                executable_path=executable_path,
                title=title,
                window_class=_window_class(user32, hwnd),
                window_rect=PixelRect(
                    left=window_rect.left,
                    top=window_rect.top,
                    right=window_rect.right,
                    bottom=window_rect.bottom,
                ),
                client_rect=client_bounds,
                visible=True,
                minimized=bool(user32.IsIconic(hwnd)),
                dpi=dpi,
            )
        )
        return True

    callback_ref = callback_type(callback)
    if not user32.EnumWindows(callback_ref, 0):
        error = ctypes.get_last_error()
        if error:
            raise OSError(error, "EnumWindows failed")
    return tuple(candidates)


def executable_sha256(path: str) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def discover_xpoker_windows(*, classify_visual_role: bool = False) -> tuple[WindowCandidate, ...]:
    discovered: list[WindowCandidate] = []
    for candidate in enumerate_windows():
        if not looks_like_xpoker(candidate):
            continue
        if candidate.executable_path:
            try:
                candidate.executable_sha256 = executable_sha256(candidate.executable_path)
            except OSError:
                candidate.executable_sha256 = None
        if classify_visual_role:
            from xpoker_agent.capture.frames import (
                capture_occluded_client,
                classify_xpoker_window,
            )

            try:
                role, confidence = classify_xpoker_window(capture_occluded_client(candidate))
                candidate.visual_role = role
                candidate.visual_role_confidence = confidence
            except (OSError, ValueError):
                candidate.visual_role = "unknown"
                candidate.visual_role_confidence = 0.0
        discovered.append(candidate)
    return tuple(discovered)
