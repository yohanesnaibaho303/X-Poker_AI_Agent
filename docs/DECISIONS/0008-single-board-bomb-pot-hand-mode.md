# Decision 0008 — Single-board Bomb Pot is an explicit hand mode

## Status

Accepted on 2026-08-24.

## Decision

Support X-Poker single-board NLH Bomb Pot as a hand mode distinct from standard NLH. A displayed
positive “after N hands” countdown schedules a future Bomb Pot and does not change the current
hand. An active Bomb Pot must reconstruct one observed forced contribution for every participant,
skips blind posting and preflop betting, and enters the shared NLH action state on the flop.

Never derive the actual forced contribution from a displayed configuration range. Use temporal
stack, bet, and pot evidence. Short contributions are legal only when the observed stack is
exhausted. Double-board, Omaha, ambiguous-board, and uncertain-contribution hands fail closed.

## Consequences

- State, events, schemas, diagnostics, and the monitor expose hand mode explicitly.
- Standard preflop range priors do not apply to Bomb Pots; participating players begin postflop
  from the full legal two-card NLH combination universe after blocker removal.
- Existing postflop action, pot-layer, card-uniqueness, and poker-math code remains shared.
- Live temporal evidence is still required before this mode can pass perception/reconstruction
  promotion gates.
