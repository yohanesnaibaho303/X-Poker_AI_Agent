# Quality, Performance, and Safety Gates

## 1. Policy

Quality gates are release conditions, not aspirations. Results must identify dataset/replay versions, component versions, machine profile, configuration, command, timestamp, and raw report location. A higher milestone may be developed behind disabled interfaces, but live table control cannot be enabled until all applicable gates pass.

## 2. Correctness targets

| Component | Initial gate | Measurement |
|---|---:|---|
| Card rank and suit recognition | >= 99.5% | Held-out supported-layout card instances; report rank, suit, and whole-card accuracy |
| Stack, bet, and pot OCR | >= 99.0% | Exact parsed-value accuracy on held-out supported layouts |
| Street detection | >= 99.9% | Frame/transition accuracy plus zero illegal progression accepted |
| Completed-hand reconstruction | >= 98.0% | Exact canonical event/state reconstruction on supported recorded hands |
| Poker mathematics | 100% | Unit, property, exhaustive feasible cases, and trusted-vector suite |
| Range lookup determinism | 100% | Same versioned input produces byte-equivalent normalized output |
| Action-target accuracy | 100% | Calibration suite across supported dimensions/DPI/layout states |
| Duplicate-action prevention | 100% | Fault-injection and repeated-message suite |
| Unsupported/ambiguous state | 100% safe response | Always stop, pause, or fall back; never execute |

Accuracy reports include confidence calibration, false-positive/false-negative breakdowns, and performance by layout/theme/region rather than only an aggregate score.

## 3. Control-enablement gates

All must be true before Armed Test Control is available:

- The target is an explicitly authorized private test table and matches its allowlisted identity profile.
- The running game matches the supported nine-seat NLH cash configuration, zero rake, native SB 1 / BB 2, and supported special-rule state.
- Card, OCR, street, reconstruction, targeting, and duplicate-prevention gates pass on frozen evaluation sets.
- Poker mathematics and range determinism gates pass.
- Critical state fields exceed their calibrated thresholds and are stable for the configured number of frames.
- The decision references the current state revision and has not expired.
- The strategy source and abstraction are permitted by control policy.
- Manual session arming and emergency stop are operational.
- Every action is logged before input and verified afterward.
- Fault injection proves that identity loss, stale frames, low confidence, illegal actions, database failure, and verification timeout disarm safely.

Any failing condition blocks or disarms control. Recommendations may continue only when doing so cannot be confused with an executable command.

## 4. Replay and evaluation policy

- Use recorded replay tests before live authorized tests.
- Freeze train/calibration/validation/holdout partitions by content hash.
- Deduplicate public or recorded frames before splitting to avoid leakage.
- Keep solver/range configurations and random seeds versioned.
- Add regression cases for every material recognition, state, math, or control defect.
- Do not promote a component when aggregate accuracy improves but a safety-critical slice materially regresses.
- Store summary reports in version control when small; store large artifacts by manifest and content hash.

## 5. Confidence and ambiguity

- Confidence thresholds are calibrated from held-out data, not chosen only by intuition.
- Critical-field control eligibility uses the minimum or explicit joint policy, never an average that hides a weak field.
- Conflicting cards, amounts, actors, actions, or target identities are ambiguous even if one candidate narrowly wins.
- Temporal consensus requires independent frames; duplicate frames do not increase confidence.
- Nearest-solution mismatch reduces strategy confidence and is visible in the dashboard.

## 6. Performance budgets

These are initial engineering budgets for the supported development machine and one table. They may be revised with benchmark evidence; correctness gates remain fixed unless the authoritative plan changes.

| Metric | Target | Hard behavior |
|---|---:|---|
| Stable-table capture/analysis rate | >= 5 FPS | Adaptive rate may rise around changes |
| Decision-window perception/state p95 | <= 200 ms | Excludes solver generation; measured frame-to-valid-state |
| Cached strategy lookup p95 | <= 50 ms | Exact or indexed nearest lookup |
| Dashboard update rate | 2-10 Hz | Throttled independently from capture |
| Core service memory, excluding optional training | <= 1.5 GB | Investigate regressions; accuracy may justify documented exception |
| Startup to Observe-ready | <= 10 s | Models/templates loaded once |
| Long-session dropped critical events | 0 | Backpressure must degrade display before state integrity |

The lightweight preference order is deterministic geometry/template logic, specialized OCR, ONNX inference, then heavier inference only when benchmarks prove it necessary.

## 7. Reliability and auditability

- A complete hand replay must reproduce the same validated event stream for identical versions and inputs.
- Seeded mixed strategies and Monte Carlo calculations must reproduce their recorded outputs within declared numeric tolerances.
- Every proposed and executed action records state, confidence, source, assumptions, seed, target, and verification result.
- Logs use correlation IDs and never intentionally include unrelated personal/account information.
- Database or audit-write failures prevent control.
- Health states are visible and machine-readable.

## 8. Promotion checklist

For each component promotion, record:

- candidate and previous versions;
- changed code, data, model, configuration, and dependencies;
- test and benchmark commands;
- evaluation datasets and hashes;
- correctness and calibration results;
- latency and memory results;
- known limitations and unsupported slices;
- reviewer/approval and rollback procedure.
