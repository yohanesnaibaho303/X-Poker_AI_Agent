# ADR 0005: Canonical exact-combo range and deterministic math core

- Status: Accepted
- Date: 2026-08-24

## Context

M5 requires reproducible weighted NLH ranges and poker arithmetic. Combo identity, card ordering,
normalization, seeded simulation, and stack abstraction must not depend on prompt text, dictionary
insertion accidents, third-party evaluator behavior, or unstated solver substitutions.

## Decision

- Use rank order `2..A` and suit order `c,d,h,s` for the canonical 52-card deck.
- Store every physical starting hand as one high-card-ordinal-first four-character key such as
  `AsKd`; reverse spellings are invalid rather than aliases.
- Project exact combos deterministically to the standard pair/suited/offsuit 169 classes.
- Keep combination weights and action frequencies in the existing strict structured models.
- Apply observed actions by Bayesian likelihood multiplication and explicit normalization.
- Implement five/seven-card ranking, exact enumeration, seeded Monte Carlo, and chip-EV metrics in
  dependency-free deterministic Python.
- Version stack matching over `20, 40, 50, 75, 100, 150, 200 BB`; ties choose the shallower bucket,
  while interpolation reports both endpoints, its weight, and mismatch.

## Consequences

- The exact 1,326-combo/169-class universe has a stable serialized SHA-256 fingerprint.
- Known blockers physically remove combos before range or equity calculations.
- Exact equity refuses workloads beyond an explicit state limit instead of silently changing to
  Monte Carlo. Sampled equity always records its seed and trial count.
- This decision defines representation and mathematics only. It does not provide or claim GTO
  frequencies; numerical preflop libraries still require validated provenance and configuration.

