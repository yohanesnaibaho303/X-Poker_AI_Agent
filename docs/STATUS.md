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
- No strategy frequencies were invented or imported. Control remains disabled.
- Current full suite: Ruff passed; 142 Pytest/Hypothesis tests passed.

## Completed project checkpoints

- Milestone 0 — reproducible schemas, configuration, logging, and deterministic simulated hand.
- Milestone 1 — autonomous public-source and component catalog with provenance/licensing boundaries.
- Milestone 2 — authorized X-Poker window discovery, calibration, normalized capture, and replay diagnostics.

## Next

- Implement versioned position/action/sizing spot keys and deterministic range-update routing.
- Define the validated range-artifact import format and provenance/configuration rejection rules.
- Source or generate the initial 9-max no-rake 2 BB library without substituting six-max, raked, or
  tournament charts.
- Continue M3/M4 promotion evaluation in parallel when representative standard NLH replays exist.

## Blockers

- No blocker for continued offline/synthetic development.
- M3/M4 promotion needs representative complete standard NLH hands later; the user does not need
  nine devices and can provide a populated club table as spectator when available.

This file is updated at meaningful checkpoints. The detailed checklist remains in `docs/MILESTONES.md`.
