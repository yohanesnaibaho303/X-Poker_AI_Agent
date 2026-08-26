# X-Poker AI Agent Architecture

## 1. Purpose and authority

This document translates `docs/PROJECT_PLAN.md` into implementation boundaries. The project plan and `AGENTS.md` remain authoritative if any conflict appears.

The system is an inspectable Windows agent for an explicitly authorized private X-Poker test table. It begins in observation-only mode. Live control remains unavailable until the quality gates in `docs/QUALITY_GATES.md` pass.

## 2. Architectural principles

- Optimize for low latency, low memory use, and simple deployment without weakening correctness or safety.
- Keep research, capture, perception, state, ranges, poker math, strategy, exploitation, monitoring, and control independently testable.
- Use deterministic code for poker rules, arithmetic, validation, state transitions, range operations, and control gates.
- Use language models only for research, classification, synthesis, explanations, and bounded orchestration.
- Attach configuration, confidence, assumptions, provenance, and evidence references to derived results.
- Preserve raw or replayable evidence for recognition and reconstruction failures.
- Fail closed when cards, amounts, actions, configuration, window identity, or state are ambiguous.
- Never silently substitute six-max, tournament, raked, or wrong-blind or BB-normalized strategy data.

## 3. Logical modules

| Module | Responsibility | Must not own |
|---|---|---|
| `research` | Public-source discovery, ingestion, classification, provenance, licensing | Numerical strategy validation |
| `capture` | Authorized-window discovery, identity checks, DPI normalization, region capture | Poker interpretation |
| `vision` | Layout, card, chip-text, icon, control, and seat observations | Legal hand state |
| `state` | Temporal event derivation and validated NLH hand reconstruction | Pixel recognition or strategy |
| `ranges` | 1,326-combination weights, 169-class views, blockers, action updates | Solver ownership |
| `poker_math` | Evaluation, equity, EV, pot odds, SPR, side pots | Language-model arithmetic |
| `strategy` | Exact/nearest solution lookup, abstraction distance, action frequencies | Hidden approximation |
| `exploit` | Opponent profiles and confidence-scaled adjustments | Unbounded small-sample reactions |
| `monitor` | Inspectable state, evidence, health, recommendations, replay | Core calculations |
| `controller` | Authorized target mapping, arming, execution, verification, emergency stop | Perception or strategy inference |

Dependencies flow downward through explicit schemas:

```text
research ───────────────────────────────┐
capture → vision → state → ranges ──────┼→ strategy → exploit → monitor
                         poker_math ─────┘                         │
                                                                  ↓
                                                        gated controller
```

The controller consumes a frozen, validated decision envelope. It cannot call vision or strategy directly to invent missing data.

## 4. Runtime topology

Start as a modular monolith to minimize process and deployment overhead:

- Python 3.12 application for capture, vision, state, ranges, math, strategy, persistence, and local API.
- FastAPI HTTP endpoints for configuration, replay, evidence, and health.
- WebSocket stream for throttled state and monitoring updates.
- React and TypeScript dashboard built as static assets and served locally.
- SQLite in WAL mode for metadata, events, profiles, decisions, and provenance.
- Filesystem object store for permitted frames, replays, models, range data, and generated solutions.

Split a component into a separate process only when measurement shows isolation or throughput is necessary. Learned inference should use ONNX Runtime by default; PyTorch belongs primarily in offline training workflows.

## 5. Data flow and trust boundaries

1. `capture` proves the window matches the authorized target and emits normalized frames.
2. `vision` emits independent observations with confidence and evidence locations.
3. `state` combines observations across time and accepts only legal, internally consistent transitions.
4. `ranges` and `poker_math` derive structured numerical state.
5. `strategy` resolves an exact solution or a declared approximation with quantified mismatch.
6. `exploit` may adjust the baseline within sample-size and confidence limits.
7. `monitor` exposes the full decision trace.
8. `controller` acts only when authorization, mode, state stability, confidence, and target verification gates all pass.

Raw observations are untrusted. A validated hand state is trusted only for the frame interval and evidence set that produced it. A recommendation is not permission to act.

## 6. Storage boundaries

- SQLite stores identifiers, structured metadata, configuration versions, observations, events, hands, decisions, profiles, and audit records.
- Large binary artifacts remain outside SQLite and are referenced by content hash and relative path.
- Strategy and range artifacts are immutable and versioned.
- Secrets and unrelated account information are neither captured intentionally nor written to logs.
- Research assets record URL, source type, license, intended use, acquisition time, and confidence.

## 7. Performance strategy

- Capture only the table and required regions.
- Use stable geometry, templates, and specialized OCR before general learned models.
- Run cheap detectors first and invoke expensive inference only for changed or uncertain regions.
- Reuse buffers, loaded models, templates, and normalized layout coordinates.
- Use adaptive frame rates: faster around action changes, slower when the table is stable.
- Cache immutable range and solution lookups.
- Throttle dashboard updates independently from the perception loop.
- Measure per-stage latency, memory, dropped frames, and queue depth before optimizing.

Accuracy and fail-closed behavior override resource targets when the two conflict.

## 8. Initial repository boundaries

```text
apps/monitor/             React + TypeScript dashboard
services/research/        source and provenance pipeline
services/capture/         Windows/emulator capture
services/vision/          visual recognition and OCR
services/state/           NLH reconstruction
services/ranges/          weighted ranges
services/poker_math/      deterministic calculations
services/strategy/        GTO lookup and abstraction
services/exploit/         opponent modeling
services/controller/      authorized gated control
configs/                  versioned game, layout, runtime configuration
data/                     catalog and local artifact directories
tests/                    unit, property, replay, vision, strategy, end-to-end
docs/                     specifications, decisions, evaluations
```

Milestone 0 may introduce a shared Python package for canonical schemas and configuration. Shared code must not collapse domain ownership.

