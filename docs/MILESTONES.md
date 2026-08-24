# Delivery Milestones and Task List

## How to use this document

`docs/PROJECT_PLAN.md` defines scope and milestone intent. This file is the execution checklist. A task is complete only with tests, documentation, and evidence appropriate to its risk. Do not begin live control work early merely because earlier interfaces have been scaffolded.

## Milestone 0 — Requirements and reproducibility

Goal: establish a lightweight, deterministic foundation that can represent a simulated hand end to end.

- [x] Record architecture and licensing decisions.
- [x] Create Python 3.12 project metadata and locked development dependencies.
- [x] Create the initial module/package boundaries.
- [x] Encode authoritative 6-max and 9-max cash NLH, zero-rake, 2 BB, chip-EV configurations.
- [x] Implement typed, versioned models for provenance, observations, events, hand state, ranges, strategy matches, decisions, and controller audits.
- [x] Generate or publish JSON Schemas for persisted and API-facing records.
- [x] Implement configuration loading and validation with local ignored overrides.
- [x] Add structured JSON logging with correlation, hand, frame, and decision IDs.
- [x] Implement a deterministic simulated-hand fixture and reducer demonstration.
- [x] Add unit and property tests for configuration and schemas.
- [x] Add one command to lint, test, and start the development service.
- [x] Document setup, commands, dependencies, and current limitations.

Exit: configuration and schemas load successfully, tests pass, and one simulated NLH hand is represented from table-ready through completion.

## Milestone 1 — Autonomous reference research

- [x] Implement source and asset provenance registry.
- [x] Define acquisition policies for video, transcript, image, article, and repository sources.
- [x] Research public X-Poker interface material and accessible transcripts.
- [x] Sample permitted representative frames and deduplicate them.
- [x] Classify version, layout, theme, orientation, game, street, and visible components.
- [x] Build the first table-component catalog.
- [x] Study PokerGPT under its MIT license and document reusable architectural ideas.
- [x] Study `dickreuter/Poker` as GPL-3.0 reference and document clean-room boundaries.
- [x] Classify strategy claims by source/fact type and validation status.
- [x] Add catalog validation and provenance tests.

Exit: a reviewable, licensed/provenanced catalog contains representative examples for every critical table component.

## Milestone 2 — Window capture and calibration

- [x] Enumerate X-Poker/emulator candidate windows.
- [x] Implement authorized-target profiles and identity validation.
- [x] Capture client-area frames without unrelated screen regions.
- [x] Normalize DPI, dimensions, color format, and orientation.
- [x] Locate table anchors and version the first layout profile.
- [x] Handle movement, resizing, minimization, and identity loss.
- [x] Add adaptive frame scheduling, hashes, and performance telemetry.
- [x] Create capture recordings and deterministic replay diagnostics.

Exit: stable normalized frames are automatically collected from the authorized instance with target identity and replay evidence.

## Milestone 3 — Visual recognition MVP

- [ ] Build seat, hero, dealer, and occupied-seat detectors.
- [ ] Build card rank/suit recognition for hero, board, and showdown.
- [ ] Benchmark lightweight OCR candidates on X-Poker numeric regions.
- [ ] Recognize stacks, bets, pot, side pots, and numeric formats.
- [ ] Recognize active player, timer, actions, and sizing controls.
- [ ] Add temporal consensus, alternatives, and calibrated confidence.
- [ ] Add impossible-card and amount-format rejection.
- [ ] Build held-out visual regression suites and latency benchmarks.

Exit: supported-layout recognition meets the per-component targets in `docs/QUALITY_GATES.md`.

## Milestone 4 — Complete hand reconstruction

- [x] Implement separate table lifecycle, street, seat-participation, and betting-action models.
- [x] Implement categorized reconstruction events and an append-only event store.
- [x] Implement the NLH state reducer and street/action ordering.
- [x] Validate unique cards, blinds, calls, raises, all-ins, and side pots.
- [x] Reconcile stack, bet, pot, and award accounting.
- [x] Handle heads-up and multiway play within six-seat and nine-seat state models.
- [x] Detect hand boundaries and dealer/blind movement.
- [x] Quarantine ambiguous or impossible hands with evidence.
- [x] Export canonical hand histories and build replay inspection.

Exit: at least 98% of supported recorded hands reconstruct correctly, with unsupported states always stopping or falling back.

## Milestone 5 — Range and poker-math foundation

- [x] Implement canonical 1,326-combination representation and 169-class projection.
- [x] Implement weights, action frequencies, normalization, blockers, and filtering.
- [x] Implement position/action/sizing-based range updates.
- [x] Implement five- and seven-card evaluation with exhaustive tests.
- [x] Implement exact and seeded Monte Carlo equity, including multiway.
- [x] Implement pot odds, EV, fold equity, SPR, MDF, and side-pot calculations.
- [x] Define stack-bucket matching/interpolation policy.
- [x] Seed validated, versioned 6-max and 9-max no-rake 2 BB reference-prior libraries, with
  configuration mismatches explicit and GTO integration reserved for Milestone 6.

Exit: range lookup is deterministic, poker-math tests pass completely, and position-specific ranges render correctly.

## Milestone 6 — GTO strategy integration

- [x] Define provenance-bearing preflop strategy artifact import and validation format.
- [ ] Integrate licensed/generated/authorized solution sources.
- [ ] Implement full spot keys and exact-node lookup.
- [x] Implement preflop exact/nearest-stack resolution and quantitative mismatch metrics.
- [ ] Expose combo actions, frequencies, EV, equity, and EV loss.
- [x] Add source, assumptions, configuration, role, and confidence to every preflop result.
- [ ] Build reference-comparison and replay regression suites.

Exit: replayed spots return deterministic, source-backed results and never present approximations as exact GTO.

## Milestone 7 — Exploitative modeling

- [ ] Define player and population statistic models.
- [ ] Track sufficient counts and uncertainty by position, street, and size.
- [ ] Maintain baseline, inferred, and exploit-adjusted ranges separately.
- [ ] Implement confidence-scaled, capped deviations.
- [ ] Add nodelock-like experiments and best-response analysis.
- [ ] Explain adjustment evidence, sample size, and uncertainty.
- [ ] Test synthetic profiles and small-sample shrinkage.

Exit: synthetic profiles produce stable, explainable, regression-tested adjustments.

## Milestone 8 — Live monitoring application

- [ ] Build the React/TypeScript shell and component design system.
- [ ] Add 6-max/9-max session selection and BB/native chip display controls.
- [ ] Stream schema-versioned snapshots and events over WebSockets.
- [ ] Display capture overlays, confidence, state, action history, and health.
- [ ] Display hero/opponent ranges and GTO/exploit frequencies.
- [ ] Display equity, EV, pot odds, abstraction mismatch, assumptions, and sources.
- [ ] Add replay navigation and decision/audit inspection.
- [ ] Add gap recovery, backpressure, and long-session telemetry.

Exit: complete authorized sessions can be monitored without state corruption and with acceptable resource use.

## Milestone 9 — Authorized control

- [ ] Implement versioned action-target calibration.
- [ ] Implement manual arming, session scope, and emergency stop.
- [ ] Implement table/configuration identity gates.
- [ ] Implement stable-frame, confidence, legality, and freshness gates.
- [ ] Implement idempotency and duplicate-input prevention.
- [ ] Map abstract sizes to verified visible controls.
- [ ] Execute input only in the authorized private test table.
- [ ] Verify resulting state and disarm on mismatch.
- [ ] Audit every blocked, proposed, executed, and verified action.
- [ ] Pass simulated suites before any live authorized test.

Exit: all controller gates pass and supported authorized test hands complete with verified actions and zero duplicate inputs.

## Milestone 10 — Hardening and demonstration

- [ ] Expand unsupported-state detection and recovery.
- [ ] Run endurance, fault-injection, replay, and performance tests.
- [ ] Finalize Windows packaging and dependency/model manifests.
- [ ] Document installation, configuration, architecture, limitations, and evaluations.
- [ ] Produce a reproducible hackathon demonstration on a fresh authorized machine.

Exit: a new authorized test machine can reproduce the documented demonstration.
