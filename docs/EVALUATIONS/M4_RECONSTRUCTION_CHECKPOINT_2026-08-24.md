# Milestone 4 Reconstruction Checkpoint

## Scope

This is the first Milestone 4 implementation checkpoint. It is developed behind disabled control
while Milestone 3 recognition accuracy remains unpromoted. Inputs are canonical validated events
from deterministic fixtures, not raw live OCR output.

## Implemented invariants

- SQLite event storage is append-only through database `UPDATE` and `DELETE` rejection triggers.
- Events are unique by event ID and hand sequence and form a per-hand SHA-256 chain over canonical
  JSON payloads.
- Stored events round-trip to strict `HandEvent` models and replay to byte-equivalent final state.
- Dealer assignment must precede blinds and must reference an occupied seat.
- Every chip commitment includes both added chips and resulting street commitment; the two must
  reconcile exactly.
- Checks while facing a wager, calls that do not match, bets into an existing wager, raises without
  an existing wager, sub-minimum non-all-in raises, and stack-exhausting non-all-in actions fail.
- Short all-in raises are represented without lowering the full-raise increment.
- The reducer tracks the next actionable seat, rejects out-of-turn actions, and prevents street
  advancement before the betting round closes.
- Main and side pots are constructed at all-in contribution caps with explicit contributors,
  eligible seats, original amounts, and remaining amounts.
- Pot awards name a pot layer; ineligible winners and over-awards are rejected. Repeated awards can
  represent split pots while preserving exact chip conservation.
- A short all-in can increase the call target without lowering the minimum full-raise increment;
  players who already acted are explicitly raise-locked until action is legitimately reopened.
- Known physical cards are unique across every observed seat and board.
- Player stacks plus reconstructed pot must equal the initial table-chip total after every event.
- Multi-event database appends are atomic. Invalid replay stops at the last valid revision and emits
  a compact quarantine record containing the failure reason and failed-event payload hash.
- Canonical JSON hand-history export is byte-deterministic for identical inputs.
- Heads-up tests verify button/small-blind first action preflop and the other seat's first action
  postflop within the nine-seat coordinate model.
- Cross-hand validation requires a new hand identity, stable configuration and dealt-seat set, a
  completed previous hand, and clockwise dealer movement to the next dealt seat.
- Failed replay quarantine records persist idempotently under a content-derived filename.

The subsequent dual-table-size amendment generalized canonical seats, clockwise action rotation,
and boundary validation to explicit six-seat and nine-seat configurations. The original nine-seat
results above remain historical checkpoint evidence.

## Verification

- Full project suite: 104 Pytest/Hypothesis tests.
- Deterministic simulated hand: 14 canonical events, 15 states, exact replay equivalence.
- Event-store tests cover round-trip, hash-chain verification, non-contiguous sequence rejection,
  and database mutation rejection.
- Property testing covers blind posting and chip conservation over generated amounts.

## Not yet complete

- Odd-chip assignment rules and cumulative short-raise reopening rules.
- Blind-role labels and odd-chip/cumulative-short-raise house-rule details.
- Observation-to-event inference, frame-evidence bundles, and human-readable text export.
- Recorded complete-hand evaluation and the 98% exact reconstruction gate.
