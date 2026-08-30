"""Lightweight OCR adapter backed by the Windows-installed recognition engine."""

from __future__ import annotations

import os
import time
from functools import cache

from xpoker_agent.capture.frames import CapturedFrame
from xpoker_agent.vision.models import WindowsOcrResult
from xpoker_agent.vision.primitives import validate_frame


@cache
def _ocr_engine():
    from winrt.windows.media.ocr import OcrEngine  # noqa: PLC0415

    engine = OcrEngine.try_create_from_user_profile_languages()
    if engine is None:
        raise OSError("Windows has no OCR language available for the user profile")
    return engine


def _top_down_bgra(frame: CapturedFrame) -> bytes:
    validate_frame(frame)
    row_size = frame.width * 4
    return b"".join(
        frame.bgra_bottom_up[y * row_size : (y + 1) * row_size]
        for y in range(frame.height - 1, -1, -1)
    )


async def recognize_text(frame: CapturedFrame) -> WindowsOcrResult:
    """Recognize a privacy-scoped crop without sending pixels off the machine."""
    if os.name != "nt":
        raise OSError("Windows Media OCR is available only on Windows")
    from winrt.windows.graphics.imaging import (  # noqa: PLC0415
        BitmapAlphaMode,
        BitmapPixelFormat,
        SoftwareBitmap,
    )
    from winrt.windows.storage.streams import Buffer  # noqa: PLC0415

    pixels = _top_down_bgra(frame)
    buffer = Buffer(len(pixels))
    buffer.length = len(pixels)
    memoryview(buffer)[:] = pixels
    bitmap = SoftwareBitmap(
        BitmapPixelFormat.BGRA8,
        frame.width,
        frame.height,
        BitmapAlphaMode.IGNORE,
    )
    bitmap.copy_from_buffer(buffer)
    engine = _ocr_engine()
    started = time.perf_counter_ns()
    try:
        result = await engine.recognize_async(bitmap)
    finally:
        bitmap.close()
    latency_ms = (time.perf_counter_ns() - started) / 1_000_000
    return WindowsOcrResult(
        text=result.text,
        lines=[line.text for line in result.lines],
        processing_latency_ms=latency_ms,
        language_tag=engine.recognizer_language.language_tag,
    )
