# Build Status

- Last updated: 2026-08-24 (Asia/Jakarta)
- Current milestone: Milestone 4 — Complete hand reconstruction (M3 promotion still pending)
- Overall project: 3 of 11 milestones complete
- Current state: Milestone 4 deterministic reconstruction checkpoint in progress; Milestone 3
  held-out accuracy gates remain pending
- Live control: Disabled

## Latest checkpoint

- Added a SQLite append-only canonical event store with per-hand SHA-256 chains, sequence/event
  uniqueness, canonical JSON round-trip, and database triggers that reject mutation and deletion.
- Exact stored-event replay reproduces the deterministic hand's final state.
- Enforced dealer-before-blinds, exact commitment totals, legal check/call/bet/raise/all-in shapes,
  minimum full raises, and short all-in behavior.
- Added explicit next-to-act tracking, out-of-turn rejection, betting-round closure, and guarded
  street advancement.
- Added full-state chip conservation and physical-card uniqueness across every observed seat and
  board.
- Added contribution-capped main/side-pot layers, eligibility validation, side-pot-specific awards,
  and repeated split awards with exact conservation.
- Added explicit raise locks after short all-ins so previously acted players may respond but cannot
  illegally re-raise when action was not reopened.
- Event batches are atomic; invalid replay stops at the last valid state with a reason and failed
  payload hash. Canonical JSON hand histories are byte-deterministic.
- Added heads-up preflop/postflop order coverage, cross-hand identity/configuration/dealt-seat checks,
  clockwise dealer movement validation, and idempotent quarantine persistence.
- M3 remains fail closed: no recognition output can enter this reducer until its confidence and
  validation boundary passes. Raw live frames remain ignored and control remains disabled.
- Current full suite: Ruff passed; 104 Pytest/Hypothesis tests passed.

## Completed project checkpoints

- Milestone 0 — reproducible schemas, configuration, logging, and deterministic simulated hand.
- Milestone 1 — autonomous public-source and component catalog with provenance/licensing boundaries.
- Milestone 2 — authorized X-Poker window discovery, calibration, normalized capture, and replay diagnostics.

## Next

- Add explicit blind-role observations, cumulative short-raise/odd-chip house-rule details, and
  readable hand-history export.
- Connect validated M3 observation batches to quarantinable event inference with frame evidence.
- Continue the M3 held-out recognition work in parallel; M4 live evaluation remains blocked on it.

## Blockers

- No blocker for continued offline/synthetic development.
- M3/M4 promotion needs representative complete standard NLH hands later; the user does not need
  nine devices and can provide a populated club table as spectator when available.

This file is updated at meaningful checkpoints. The detailed checklist remains in `docs/MILESTONES.md`.
