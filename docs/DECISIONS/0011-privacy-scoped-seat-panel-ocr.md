# Decision 0011 — Privacy-scoped seat-panel OCR

## Status

Accepted on 2026-08-24.

## Decision

Run local OCR only on non-empty declared seat-panel regions. Convert its output immediately into a
bounded structured observation: seat index, player state, optional native-stack token, confidence,
reason, and a SHA-256 evidence fingerprint. Do not retain raw panel text or player names.

Treat every numeric result as a candidate. A single frame can never establish an accepted stack;
acceptance requires temporal repetition and later agreement with stack movement, bets, pot
accounting, and legal hand reconstruction. Ambiguous panels fail closed.

## Consequences

- The live monitor can show candidate coverage without exposing player names.
- Empty seats avoid unnecessary OCR work.
- `Break` is represented independently from an amount and cannot be parsed as a stack.
- OCR mistakes remain visible and quarantined rather than silently entering canonical state.
- Held-out labeled replay evidence is still required before the stack OCR gate can pass.
