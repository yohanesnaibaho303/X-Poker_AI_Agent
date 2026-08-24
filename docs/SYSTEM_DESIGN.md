# X-Poker AI Agent System Design

## 1. Scope

This design describes the first supported system: a Windows application observing a single explicitly authorized private X-Poker test table configured as 9-max cash NLH, zero rake, default 2 BB open, and chip-EV. Effective stacks are calculated dynamically.

## 2. Operating modes

| Mode | Capture | Analyze | Recommend | Input control |
|---|---:|---:|---:|---:|
| Observe | Yes | State only | No | No |
| Analyze | Yes | Yes | No | No |
| Recommend | Yes | Yes | Yes | No |
| Armed Test Control | Yes | Yes | Yes | Gated |

Mode transitions are explicit and audited. Entering Armed Test Control requires manual arming for the session, an authorized-table identity match, current quality-gate approval, and a working emergency stop. Any failed invariant immediately returns the controller to a non-acting state.

## 3. Capture and calibration

### 3.1 Window selection

The capture service enumerates candidate Windows or emulator windows and records process identity, executable path where permitted, title, client bounds, DPI, monitor, and a visual layout fingerprint. The user-authorized target is represented by an allowlisted target profile rather than a loose title match.

### 3.2 Normalization

Frames are transformed into canonical table coordinates. A versioned layout profile contains anchors and normalized regions for seats, board, pot, dealer marker, actions, sizing controls, and status indicators. Movement, resizing, and DPI changes trigger revalidation.

### 3.3 Capture policy

Capture only required table regions. Assign every frame a monotonic sequence, timestamp, target identity, layout version, dimensions, and content hash. Retain frames according to the configured evidence policy; always preserve references needed to replay errors and executed actions.

## 4. Perception pipeline

Each detector returns observations, never hand-state mutations.

```text
normalized frame
  → cheap change detection
  → fixed-region/template detectors
  → card-specific rank/suit recognition
  → specialized numeric OCR
  → learned fallback for variable components
  → temporal consensus
  → observation batch
```

Observations include value, confidence, detector/model version, region, frame evidence, and alternatives. Conflicting high-value observations—especially cards and amounts—are not averaged into a plausible value; they remain ambiguous for state validation.

## 5. Hand-state reconstruction

The state service consumes time-ordered observation batches and emits canonical events:

```text
TABLE_READY → HAND_STARTED → blinds/deal/actions → streets → SHOWDOWN
            → POT_AWARDED → HAND_COMPLETED
```

The reducer validates action order, street progression, card uniqueness, amount monotonicity, minimum raises, stack movement, pot accounting, side pots, all-ins, and occupied-seat changes. It uses multi-frame confirmation for unstable visual values.

An impossible or materially incomplete transition produces an anomaly and pauses state advancement. The previous valid state remains intact; guessed events are forbidden.

## 6. Range and mathematics services

Ranges use exact card combinations as the canonical representation. The 169-class matrix is a derived view. Updates are pure functions over prior weights, known cards, observed action, position, sizing, and a versioned likelihood model.

Poker mathematics exposes deterministic, typed functions. Exact enumeration is preferred when tractable. Monte Carlo uses explicit seeds, sample counts, convergence metadata, and reproducible configuration. Calculation results include inputs and algorithm versions.

## 7. Strategy resolution

The resolver builds a strategy key from game type, seats and players remaining, rake, positions, effective stack, action sequence and sizes, board, pot geometry, and supported actions.

Resolution returns either:

- `exact`: configuration and node match exactly;
- `abstracted`: nearest compatible node plus per-dimension mismatch;
- `unavailable`: no defensible source exists.

An abstracted result lowers confidence and may block control even when it remains useful for analysis. GTO Wizard is a conceptual/UI reference unless legitimate access or authorized exports exist. YouTube advice and language-model output are never stored as validated numerical GTO truth.

## 8. Exploit model

Opponent observations update a versioned profile containing sufficient counts, posterior estimates, uncertainty, and showdown evidence. Adjustments are computed relative to the selected baseline, capped by policy, and shrink toward the baseline as uncertainty grows.

Every exploit recommendation retains both the baseline and adjusted frequencies, the evidence window, sample size, confidence, and adjustment rule. Population priors and player-specific evidence remain separate.

## 9. Monitoring API and dashboard

The API publishes immutable snapshots and append-only events. The dashboard shows:

- normalized capture and recognition overlays;
- table identity, layout, mode, health, and latency;
- canonical state and action history;
- evidence and confidence for each important observation;
- hero and opponent ranges;
- equity, EV, pot odds, and effective stacks;
- baseline and exploit-adjusted strategies;
- exact/abstracted/unavailable status and mismatch;
- complete proposed/executed action audit trail;
- replay controls for recorded hands.

WebSocket messages carry schema versions and sequence numbers. The UI detects gaps and requests a fresh snapshot instead of assuming continuity.

## 10. Controller design

The controller is disabled by default and accepts only a `DecisionEnvelope` referencing a current validated state. Before any input it checks:

1. session is manually armed and not emergency-stopped;
2. window and table match the authorized profile;
3. game configuration matches the supported configuration;
4. state is stable over the required frames and remains current;
5. critical confidence and quality gates pass;
6. proposed action is legal and the sizing maps to a visible supported control;
7. idempotency token has not been used;
8. click target still matches the expected visual control.

After input, it verifies the expected state transition within a deadline. Failure disarms control and records evidence. No retry may produce a duplicate wager without a newly validated state and token.

## 11. Failure handling

| Failure | Required response |
|---|---|
| Authorized target lost or changed | Stop capture/control and require revalidation |
| Ambiguous card or amount | Do not advance state or act |
| Illegal transition or pot mismatch | Quarantine hand and preserve evidence |
| Detector/model crash | Mark component unhealthy and fail closed |
| Strategy missing | Report unavailable; do not invent GTO output |
| Dashboard disconnect | Continue observation if configured; control policy decides whether to disarm |
| Database write failure | Preserve in-memory safety state, stop control, surface health error |
| Post-click verification failure | Disarm and record incident |

## 12. Configuration and reproducibility

All runtime, game, layout, model, range, solver, and gate configurations are versioned. A replay records enough versions and seeded inputs to reproduce state and strategy decisions. Environment-specific authorization details are local and excluded from source control.

