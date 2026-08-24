# Decision 0013 — Exactly-once temporal action candidates

## Status

Accepted on 2026-08-24.

## Decision

Derive a bounded action-candidate stream only when hand mode and a legal board-card count have
three-frame consensus. Arm derivation after observing a badge-clear frame, then require an action
badge itself to repeat across three distinct frame hashes. Key candidates by authorized target,
provisional hand epoch, street, seat, and action so repeated display frames cannot duplicate them.

Keep every derived item explicitly outside the canonical `HandEvent` stream. Promotion requires
dealer and position evidence, amount/bet deltas, legal action order, and pot/stack reconciliation.

## Consequences

- Persistent X-Poker Fold/Check/Call/Bet/Raise/All-in labels create at most one candidate per street.
- Starting observation mid-hand does not emit badges already visible at startup.
- Unsupported run-it-multiple-times overlays clear board consensus and prevent derivation.
- A provisional epoch can support monitoring, but cannot by itself establish a legal hand boundary.
