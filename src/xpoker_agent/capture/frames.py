"""Dependency-free read-only capture of an authorized window client area."""

from __future__ import annotations

import ctypes
import os
import struct
from collections.abc import Callable
from ctypes import wintypes
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from xpoker_agent.capture.models import WindowCandidate

SRCCOPY = 0x00CC0020
BI_RGB = 0
DIB_RGB_COLORS = 0
PW_CLIENTONLY = 0x00000001
PW_RENDERFULLCONTENT = 0x00000002


class BITMAPINFOHEADER(ctypes.Structure):
    _fields_ = [
        ("biSize", wintypes.DWORD),
        ("biWidth", wintypes.LONG),
        ("biHeight", wintypes.LONG),
        ("biPlanes", wintypes.WORD),
        ("biBitCount", wintypes.WORD),
        ("biCompression", wintypes.DWORD),
        ("biSizeImage", wintypes.DWORD),
        ("biXPelsPerMeter", wintypes.LONG),
        ("biYPelsPerMeter", wintypes.LONG),
        ("biClrUsed", wintypes.DWORD),
        ("biClrImportant", wintypes.DWORD),
    ]


class BITMAPINFO(ctypes.Structure):
    _fields_ = [("bmiHeader", BITMAPINFOHEADER), ("bmiColors", wintypes.DWORD * 3)]


@dataclass(frozen=True)
class CapturedFrame:
    width: int
    height: int
    bgra_bottom_up: bytes

    def to_bmp(self) -> bytes:
        expected_size = self.width * self.height * 4
        if len(self.bgra_bottom_up) != expected_size:
            raise ValueError("BGRA payload size does not match frame dimensions")
        pixel_offset = 54
        file_header = struct.pack(
            "<2sIHHI", b"BM", pixel_offset + expected_size, 0, 0, pixel_offset
        )
        dib_header = struct.pack(
            "<IiiHHIIiiII",
            40,
            self.width,
            self.height,
            1,
            32,
            BI_RGB,
            expected_size,
            0,
            0,
            0,
            0,
        )
        return file_header + dib_header + self.bgra_bottom_up

    def write_bmp(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(self.to_bmp())

    @classmethod
    def from_bmp(cls, payload: bytes) -> CapturedFrame:
        if len(payload) < 54 or payload[:2] != b"BM":
            raise ValueError("capture artifact is not a supported BMP")
        pixel_offset = struct.unpack_from("<I", payload, 10)[0]
        width = struct.unpack_from("<i", payload, 18)[0]
        height = struct.unpack_from("<i", payload, 22)[0]
        bits_per_pixel = struct.unpack_from("<H", payload, 28)[0]
        compression = struct.unpack_from("<I", payload, 30)[0]
        if width <= 0 or height <= 0 or bits_per_pixel != 32 or compression != BI_RGB:
            raise ValueError("capture artifact must be a bottom-up 32-bit uncompressed BMP")
        pixels = payload[pixel_offset:]
        frame = cls(width=width, height=height, bgra_bottom_up=pixels)
        frame.to_bmp()
        return frame


def classify_xpoker_window(
    frame: CapturedFrame,
) -> tuple[Literal["unknown", "lobby", "table"], float]:
    """Classify the stable top-left lobby-back or table-menu chrome."""
    if frame.width < 100 or frame.height < 200:
        return "unknown", 0.0

    x_start = round(frame.width * 0.018)
    x_end = round(frame.width * 0.158)
    y_start = round(frame.height * 0.019)
    y_end = round(frame.height * 0.081)
    row_runs: list[int] = []
    bright_pixels = 0
    for y_top_down in range(y_start, y_end):
        y_bottom_up = frame.height - 1 - y_top_down
        current_run = 0
        longest_run = 0
        for x in range(x_start, x_end):
            offset = (y_bottom_up * frame.width + x) * 4
            blue, green, red, _ = frame.bgra_bottom_up[offset : offset + 4]
            bright = red >= 150 and green >= 150 and blue >= 150
            bright_pixels += int(bright)
            current_run = current_run + 1 if bright else 0
            longest_run = max(longest_run, current_run)
        row_runs.append(longest_run)

    maximum_run = max(row_runs, default=0)
    table_run_threshold = max(8, round(frame.width * 0.035))
    required_table_rows = max(2, round(frame.height * 0.005))
    long_run_rows = sum(run >= table_run_threshold for run in row_runs)
    if long_run_rows >= required_table_rows:
        confidence = min(
            1.0,
            0.9
            + 0.05 * (maximum_run / table_run_threshold - 1)
            + 0.05 * (long_run_rows / required_table_rows - 1),
        )
        return "table", confidence

    lobby_run_ceiling = max(6, round(frame.width * 0.025))
    if bright_pixels >= 20 and maximum_run <= lobby_run_ceiling:
        return "lobby", 0.95
    return "unknown", 0.0


def normalize_frame(frame: CapturedFrame, width: int, height: int) -> CapturedFrame:
    """Normalize a BGRA frame to canonical dimensions using deterministic nearest-neighbor."""
    if width <= 0 or height <= 0:
        raise ValueError("normalized dimensions must be positive")
    if (frame.width, frame.height) == (width, height):
        return frame

    x_source = [min(frame.width - 1, x * frame.width // width) for x in range(width)]
    rows: list[bytes] = []
    for y_bottom_up in range(height):
        source_y = min(frame.height - 1, y_bottom_up * frame.height // height)
        source_offset = source_y * frame.width * 4
        row = bytearray(width * 4)
        for x, source_x in enumerate(x_source):
            source_pixel = source_offset + source_x * 4
            row[x * 4 : x * 4 + 4] = frame.bgra_bottom_up[source_pixel : source_pixel + 4]
        rows.append(bytes(row))
    return CapturedFrame(width=width, height=height, bgra_bottom_up=b"".join(rows))


def _validate_candidate(candidate: WindowCandidate) -> tuple[int, int]:
    if os.name != "nt":
        raise OSError("Win32 client capture is available only on Windows")
    if candidate.minimized or not candidate.visible:
        raise ValueError("window must be visible and not minimized")
    width = candidate.client_rect.width
    height = candidate.client_rect.height
    if width <= 0 or height <= 0:
        raise ValueError("window client area is empty")
    return width, height


def _capture_bitmap(
    width: int,
    height: int,
    render: Callable[[ctypes.WinDLL, ctypes.WinDLL, int, int], bool],
) -> CapturedFrame:
    user32 = ctypes.WinDLL("user32", use_last_error=True)
    gdi32 = ctypes.WinDLL("gdi32", use_last_error=True)
    screen_dc = user32.GetDC(0)
    if not screen_dc:
        raise ctypes.WinError(ctypes.get_last_error())

    memory_dc = gdi32.CreateCompatibleDC(screen_dc)
    bitmap = gdi32.CreateCompatibleBitmap(screen_dc, width, height)
    if not memory_dc or not bitmap:
        if bitmap:
            gdi32.DeleteObject(bitmap)
        if memory_dc:
            gdi32.DeleteDC(memory_dc)
        user32.ReleaseDC(0, screen_dc)
        raise ctypes.WinError(ctypes.get_last_error())

    old_object = gdi32.SelectObject(memory_dc, bitmap)
    try:
        if not render(user32, gdi32, screen_dc, memory_dc):
            raise OSError("Windows did not render the X-Poker client")

        byte_count = width * height * 4
        pixels = ctypes.create_string_buffer(byte_count)
        info = BITMAPINFO(
            bmiHeader=BITMAPINFOHEADER(
                biSize=ctypes.sizeof(BITMAPINFOHEADER),
                biWidth=width,
                biHeight=height,
                biPlanes=1,
                biBitCount=32,
                biCompression=BI_RGB,
                biSizeImage=byte_count,
            )
        )
        scanlines = gdi32.GetDIBits(
            memory_dc,
            bitmap,
            0,
            height,
            pixels,
            ctypes.byref(info),
            DIB_RGB_COLORS,
        )
        if scanlines != height:
            raise OSError(f"GetDIBits returned {scanlines} of {height} scanlines")
        return CapturedFrame(width=width, height=height, bgra_bottom_up=pixels.raw)
    finally:
        gdi32.SelectObject(memory_dc, old_object)
        gdi32.DeleteObject(bitmap)
        gdi32.DeleteDC(memory_dc)
        user32.ReleaseDC(0, screen_dc)


def capture_visible_client(candidate: WindowCandidate) -> CapturedFrame:
    """Copy visible screen pixels without activating or interacting with the window."""
    width, height = _validate_candidate(candidate)

    def render(_: ctypes.WinDLL, gdi32: ctypes.WinDLL, screen_dc: int, memory_dc: int) -> bool:
        return bool(
            gdi32.BitBlt(
                memory_dc,
                0,
                0,
                width,
                height,
                screen_dc,
                candidate.client_rect.left,
                candidate.client_rect.top,
                SRCCOPY,
            )
        )

    return _capture_bitmap(width, height, render)


def capture_occluded_client(candidate: WindowCandidate) -> CapturedFrame:
    """Ask Windows to render a client area without activating or exposing the window."""
    width, height = _validate_candidate(candidate)

    def render(user32: ctypes.WinDLL, _: ctypes.WinDLL, __: int, memory_dc: int) -> bool:
        return bool(
            user32.PrintWindow(
                candidate.hwnd,
                memory_dc,
                PW_CLIENTONLY | PW_RENDERFULLCONTENT,
            )
        )

    return _capture_bitmap(width, height, render)
