# Milestone 5 Range and Math Checkpoint

## Scope

This checkpoint covers the dependency-free exact-combo range core, hand evaluator, equity engines,
chip-EV metrics, and stack abstraction. It does not claim that a 9-max GTO range library has been
sourced or validated.

## Range-universe verification

- Canonical deck: 52 unique cards.
- Exact two-card combinations: 1,326 unique keys.
- Preflop classes: 169 unique pair/suited/offsuit classes.
- Expansion sizes: pair 6, suited non-pair 4, offsuit non-pair 12.
- One blocker leaves 1,275 combos; two blockers leave 1,225.
- Canonical universe JSON: 10,307 bytes.
- SHA-256: `7ce6a7bea3f2d7cb3fd0533f8e1b1a53cc5a4728ad36451023589f8a0cb00fd2`.
- Warm-process serialization sample: 1.634 ms.

## Exhaustive evaluator verification

All 2,598,960 physical five-card hands were enumerated in 19.526 seconds on the development machine.
The resulting category counts were:

| Category | Count |
|---|---:|
| High card | 1,302,540 |
| One pair | 1,098,240 |
| Two pair | 123,552 |
| Three of a kind | 54,912 |
| Straight | 10,200 |
| Flush | 5,108 |
| Full house | 3,744 |
| Four of a kind | 624 |
| Straight flush | 40 |

The sum is exactly 2,598,960. Additional tests cover kickers, wheel straights, category ordering,
duplicate rejection, and best-five selection from seven cards.

## Equity and metrics

- Exact weighted equity supports one or more opponents, card blocking, runout enumeration, ties, and
  fractional multiway pot share.
- Exact enumeration stops when the configured state limit would be exceeded.
- Monte Carlo sampling is deterministic for the same ranges, board, trial count, and random seed.
- Decimal metrics cover effective stack, pot odds, call EV, SPR, MDF, break-even bluff frequency,
  and heads-up bet EV.
- Stack matching reports exact/nearest/interpolated status and quantitative mismatch.

## Verification commands

- Full suite: 142 Pytest/Hypothesis tests passed.
- Ruff passed.
- No new runtime dependency was added.

## Remaining M5 work

- Versioned position/action/sizing spot keys and range-update routing.
- Validated, properly sourced 9-max no-rake 2 BB preflop range artifacts.
- Range-library lookup determinism and mismatch reports.
- Larger equity performance/calibration reports and side-pot equity settlement integration.

