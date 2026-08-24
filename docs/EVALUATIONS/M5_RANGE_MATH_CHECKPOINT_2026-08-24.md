# Milestone 5 Range and Math Checkpoint

## Scope

This checkpoint covers the dependency-free exact-combo range core, hand evaluator, equity engines,
chip-EV metrics, and stack abstraction. Following the table-size scope amendment, the same engine
supports isolated 6-max and 9-max spot keys. It does not claim that either GTO range library has been
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

- Validated, properly sourced 6-max and 9-max no-rake 2 BB preflop range artifacts.
- Larger equity performance/calibration reports and side-pot equity settlement integration.

## Strategy-source audit

The strict range-artifact schema now encodes variant, format, seat count, rake, 2 BB open size,
position, players remaining, stack depth, complete sized action sequence, exact combo strategies,
validation status, license, provenance, assumptions, and version. Exact lookup is preferred; nearest
stack lookup returns quantitative mismatch rather than silently substituting.

Public solver research found MIT-licensed heads-up engines with useful deterministic architecture and
HU blueprints, including `amaster97/poker_solver`, but not a validated nine-max, zero-rake, 2 BB
artifact set matching the project. The versioned library manifest therefore remains explicitly empty.
No HU, six-max, raked, tournament, 2.5 BB, or simplified chart has been mislabeled as authoritative.

## Range-matrix projection

The exact-combo model now projects deterministically to the conventional 13-by-13, 169-class grid.
Every cell preserves its physically possible and included combo counts, blocker-adjusted inclusion
frequency, mixed action frequencies, explicitly unassigned action mass, weighted equity, per-action
EV, source, confidence, and version. Three regression tests verify layout, blocker behavior, weighted
aggregation, inspection metadata, and byte-stable serialization.
