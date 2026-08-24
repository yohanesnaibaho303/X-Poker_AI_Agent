# ADR 0004: Benchmark Windows OCR as the first text candidate

- Status: Provisional for Milestone 3 evaluation
- Date: 2026-08-24

## Context

The application is Windows-only and X-Poker text appears in small, fixed regions. The base machine
had no Pillow, OpenCV, Tesseract, ONNX Runtime, or Python WinRT projection installed. The project
requires a lightweight local OCR path and must not send authorized table pixels to a remote service.

Microsoft documents `Windows.Media.Ocr.OcrEngine` as an on-device API accepting a `SoftwareBitmap`
and returning positioned lines and words. The required Python WinRT projections are MIT-licensed and
their compressed wheels total less than 1 MB on CPython 3.12 x64. The operating system provides the
recognition engine and language data.

Reference: <https://learn.microsoft.com/en-us/uwp/api/windows.media.ocr.ocrengine>

## Decision

Use Windows Media OCR as the first benchmark candidate behind a small asynchronous adapter. Feed it
only declared privacy-scoped layout crops. Keep deterministic numeric parsing, temporal consensus,
and state validation outside the OCR engine. OCR output alone never establishes control eligibility.

Keep template recognition as the preferred candidate for the limited X-Poker card and numeric glyph
sets. Keep Tesseract and ONNX inference as benchmark fallbacks if Windows OCR cannot meet the held-out
accuracy target. Tesseract is not yet added because its official documentation points Windows users
to third-party binaries, increasing packaging and provenance work.

## Initial evidence

On all five ignored authorized replay frames, a 335×75 rule-label crop scaled to 1340×300 preserved
the distinctive `Pot: After ... hands` phrase despite damaged small glyphs. Median OCR latency was
16.1 ms, and the deterministic classifier mapped all five frames to unsupported Bomb Pot
configuration at 0.93 confidence. This is one replay, not an accuracy benchmark or promotion result.

An exploratory pot-value probe was fast (approximately 4-10 ms) but crop/scale variants produced
both the correct `81,500` and unsafe alternatives such as `815500` and `813500`. Windows OCR is
therefore not selected for numeric values. Fixed-region templates and other candidates must be
compared on held-out exact-value accuracy.

## Consequences

- Seven narrowly scoped Windows-only Python projection packages are pinned at 3.2.1.
- Non-Windows installations skip those packages through environment markers and the adapter raises a
  clear platform error.
- A held-out X-Poker crop dataset is still required before selecting or promoting an OCR engine.
- Windows OCR output is not accepted as a chip amount without deterministic parsing, independent
  temporal evidence, and a promoted recognition configuration.
- Unknown or damaged rule-label output remains unsupported; the system never infers standard NLH
  merely because it failed to read `Bomb Pot`.
