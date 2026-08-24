# Milestone 5 Evaluation — Range and Poker-Math Foundation

- Date: 2026-08-24
- Result: Complete
- Control status: Disabled

## Implemented foundation

- Canonical 52-card deck, 1,326 exact starting combinations, and 169 preflop classes.
- Weighted combo ranges, action conditioning, blockers, filters, and deterministic matrix projection.
- Exhaustively verified five-card evaluation across all 2,598,960 physical five-card hands.
- Exact and seeded Monte Carlo heads-up/multiway equity with explicit exact-state limits.
- Decimal pot odds, EV, effective stacks, SPR, MDF, fold equity, and side-pot accounting.
- Versioned stack matching across 20, 40, 50, 75, 100, 150, and 200 BB.

## Seed library evaluation

- Pinned `bmorrow10/preflopR` commit: `aed511d0451aea33a14f7e9204595fc2211f233f`.
- Verified upstream MIT license and raw-source SHA-256.
- Generated five 6-max and eight 9-max unopened-position artifacts; BB correctly has no RFI node.
- Each artifact contains all 1,326 combos with a pure source-chart raise/fold action.
- Manifests hash every generated artifact and loaders fail on hash, ID, role, confidence, seat, or
  position mismatch.
- Nine-player upstream position names are explicitly translated to the project position model.

## Strategy boundary

The source explicitly says the charts are approximate and not solver-derived, and does not specify
stack, rake, or open size. Therefore every imported artifact is `reference_prior`, confidence 0.55,
with explicit mismatch assumptions. None is eligible to be called exact GTO. Milestone 6 remains
responsible for configuration-matched solver-derived strategy.

## Verification

- Ruff: passed.
- Pytest/Hypothesis: 187 tests passed.
- Generated schema publication: passed.
- Git whitespace validation: passed.
