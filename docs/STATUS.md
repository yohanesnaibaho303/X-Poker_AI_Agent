# Build Status

- Last updated: 2026-08-24 (Asia/Jakarta)
- Current milestone: Milestone 5 — Range and poker-math foundation
- Overall project: 3 of 11 milestones complete
- Current state: Milestone 5 deterministic range/math checkpoint in progress; M3/M4 promotion gates
  remain pending
- Live control: Disabled

## Latest checkpoint

- Added the canonical 52-card, 1,326-combo, and 169-class NLH range universe with strict physical
  combo keys and a stable SHA-256 fingerprint.
- Added structured weights, action frequencies, blocker removal, filtering, class aggregation,
  normalized combo probabilities, and Bayesian action conditioning.
- Added dependency-free five/seven-card evaluation and verified all 2,598,960 five-card hands against
  exact category totals.
- Added exact weighted and seeded Monte Carlo equity for heads-up and multiway states, including ties
  and explicit exact-state limits.
- Added Decimal effective-stack, pot-odds, call-EV, SPR, MDF, bluff-frequency, and bet-EV metrics.
- Added versioned exact/nearest/interpolated stack-bucket matching with visible mismatch.
- Added strict range artifacts and canonical position/action/sizing spot keys. Imports reject wrong
  seats, rake, open size, stack bucket, missing validation, duplicate spots, or missing provenance.
- Added deterministic 13-by-13 range-matrix projection that retains blockers, exact combo mass,
  mixed actions, missing strategy mass, equity, EV, provenance, confidence, and version.
- Added explicit X-Poker 6-max and 9-max configuration support across game schemas, canonical hand
  state, clockwise reconstruction, hand-boundary validation, API inspection, and range spot keys.
  The current calibrated portrait layout is labeled 6-max; a representative 9-max layout remains
  required before 9-max perception can be promoted.
- Audited public solver candidates; available MIT material was heads-up or otherwise incompatible.
  The isolated 6-max and 9-max library manifests remain empty rather than seeded with false GTO data.
- No strategy frequencies were invented or imported. Control remains disabled.
- Current full suite: Ruff passed; 157 Pytest/Hypothesis tests passed.

## Completed project checkpoints

- Milestone 0 — reproducible schemas, configuration, logging, and deterministic simulated hand.
- Milestone 1 — autonomous public-source and component catalog with provenance/licensing boundaries.
- Milestone 2 — authorized X-Poker window discovery, calibration, normalized capture, and replay diagnostics.

## Next

- Source or independently generate isolated 6-max and 9-max no-rake 2 BB libraries without
  substituting heads-up, raked, tournament, or differently sized charts.
- Expand equity performance reports and connect pot-layer settlement calculations.
- Continue M3/M4 promotion evaluation in parallel when representative standard NLH replays exist.

## Blockers

- No blocker for continued offline/synthetic development.
- M3/M4 promotion needs representative complete standard NLH hands later; the user does not need
  nine devices and can provide a populated club table as spectator when available.
- Nine-max perception promotion additionally needs representative nine-max visual evidence; this
  does not block six-max calibration or shared-engine development.

This file is updated at meaningful checkpoints. The detailed checklist remains in `docs/MILESTONES.md`.
