# Build Status

- Last updated: 2026-08-24 (Asia/Jakarta)
- Current milestone: Milestone 3 — Visual recognition MVP
- Overall project: 3 of 11 milestones complete
- Current state: Milestone 2 complete; Milestone 3 vision-foundation checkpoint in progress
- Live control: Disabled

## Latest checkpoint

- Added dependency-free, declared-region BGRA crops and deterministic image primitives.
- Added card-surface geometry with board-row grouping and rejection of multiple board rows or more
  than five visible board slots.
- Added strict chip-amount parsing for integer, grouped, decimal, and compact `K`/`M` formats;
  ambiguous or malformed values fail closed.
- Added impossible duplicate-card rejection and content-hash-deduplicated temporal consensus.
- Added the sub-1-MB Windows Media OCR binding set as a provisional, local-only candidate. The first
  private five-frame replay ran at 16.1 ms median per rule-label crop and retained the distinctive
  Bomb Pot schedule despite damaged small glyphs.
- Numeric probing was fast but not stable across crop/scale variants (`81,500`, `815500`, and
  `813500`); Windows OCR is not promoted for amounts, and the strict parser prevents accepting those
  label-bearing exploratory outputs.
- Registered both user-supplied X-Poker YouTube Shorts with metadata-only provenance; playback was
  unavailable, so no unreviewed visual claims or assets were recorded.
- Audited the five-frame private replay: rule-label classification now rejects its Bomb Pot
  configuration at 0.93 confidence; unknown labels cannot establish standard NLH support.
- Synthetic 200×200 multi-board geometry sample: 36.041 ms median and 37.765 ms p95 over 20 runs.
- Raw live frames remain ignored. Control remains disabled.
- Current full suite: Ruff passed; 83 Pytest/Hypothesis tests passed.

## Completed project checkpoints

- Milestone 0 — reproducible schemas, configuration, logging, and deterministic simulated hand.
- Milestone 1 — autonomous public-source and component catalog with provenance/licensing boundaries.
- Milestone 2 — authorized X-Poker window discovery, calibration, normalized capture, and replay diagnostics.

## Next

- Define and extract privacy-safe X-Poker crops for cards, amounts, seats, controls, and rule labels.
- Benchmark lightweight template recognition against Windows OCR on numeric and card crops.
- Expand Bomb Pot/rule-label rejection tests beyond the first private calibration replay.
- Continue seat, hero, dealer, occupancy, action, and sizing-control detectors.

## Blockers

- No blocker for continued offline/synthetic development.
- Accuracy-gate evaluation needs representative standard NLH table states later; the user does not
  need nine devices and can provide a populated club table as spectator when available.

This file is updated at meaningful checkpoints. The detailed checklist remains in `docs/MILESTONES.md`.
