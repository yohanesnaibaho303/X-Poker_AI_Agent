# Build Status

- Last updated: 2026-08-24 (Asia/Jakarta)
- Current milestone: Milestone 3 — Visual recognition MVP
- Overall project: 3 of 11 milestones complete
- Current state: Milestone 2 complete; Milestone 3 ready
- Live control: Disabled

## Latest checkpoint

- Detected exactly two X-Poker 10.0 `GLFW30` windows from `X-Poker.exe`.
- Classified the authorized table and sibling lobby from stable X-Poker chrome with 0.95 confidence.
- Created a machine-local, Git-ignored authorization profile using process name, executable SHA-256, class, title pattern, and table visual role.
- Added occlusion-tolerant, client-only `PrintWindow` capture without activating or controlling X-Poker.
- Added deterministic BGRA8 normalization to the first 445×800, 96-DPI portrait layout profile.
- Revalidates process, executable, class, role, dimensions, and aspect ratio before every frame; ambiguous, missing, minimized, or duplicate targets fail closed.
- Added content hashes, monotonic sequence/timestamps, source/canonical geometry, capture latency, stable target fingerprint, and adaptive 5–15 FPS scheduling.
- Recorded and verified a five-frame live local replay: 5/5 frames at 445×800, one target fingerprint, no replay issues, 71.6 ms mean capture latency.
- Raw live frames remain under ignored `data/frames/`; no account balance, player name, club ID, or table ID was committed.
- Current full suite: Ruff passed; 56 Pytest/Hypothesis tests passed.

## Completed project checkpoints

- Milestone 0 — reproducible schemas, configuration, logging, and deterministic simulated hand.
- Milestone 1 — autonomous public-source and component catalog with provenance/licensing boundaries.
- Milestone 2 — authorized X-Poker window discovery, calibration, normalized capture, and replay diagnostics.

## Next

- Build supported-layout detectors for table anchors, seats, board, pot, dealer, and controls.
- Extract privacy-safe labeled crops from local evidence rather than committing raw account/table frames.
- Benchmark lightweight numeric OCR and card recognition paths against X-Poker-specific regions.
- Request controlled spectated hand states from the user only when additional visual states are required.

## Blockers

- None for the start of Milestone 3.

This file is updated at meaningful checkpoints. The detailed checklist remains in `docs/MILESTONES.md`.
