# Offline Progress — 2026-08-27

## Verified commands

Executed from the repository root with the pinned project dependencies:

- `python -m ruff check .` — passed.
- `python -m pytest` — 354 tests passed.
- `npm --prefix apps/monitor run check` — TypeScript check, 9 dashboard tests, and Vite production build passed.
- `python -m compileall -q src tests scripts` — passed.

## Implemented offline coverage

- Synthetic 9-max NLH replay supports 3–9 dealt players with explicit preflop folds,
  contiguous deterministic event sequences, and reducer legality checks.
- Synthetic monitoring links reconstructed state to a seeded opponent range, poker math,
  equity/EV, resolved strategy, exploit output, and an explicit decision-trace audit entry.
- Controller simulation covers versioned action calibration, manual arming, emergency-stop
  latching, identity/confidence/legality/freshness gates, idempotency, simulated execution,
  post-action verification, and audit retention. It sends no OS input.
- Reconstruction evaluation has a reusable case loader and CLI. Holdout reports remain
  ineligible until supplied with real labeled complete-hand replays.

## Promotion blockers

- M3 requires a frozen, labeled held-out visual/OCR dataset with per-slice accuracy and latency.
- M4 requires frozen, labeled complete standard-NLH replay cases; the current recorded replay
  is regression evidence only and cannot satisfy the 98% promotion gate.
- No live table or live control was used or enabled.
