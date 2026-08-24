# Build Status

- Last updated: 2026-08-24 (Asia/Jakarta)
- Current milestone: Milestone 8 — live monitoring application
- Overall project: 5 of 11 milestones complete
- Current state: Milestone 8 synthetic-replay dashboard checkpoint complete; live-session exit gate,
  Milestone 6 source-data integration, and M3/M4 promotion gates remain pending
- Live control: Disabled

## Latest checkpoint

- Added the canonical 52-card, 1,326-combo, and 169-class NLH range universe with strict physical
  combo keys and a stable SHA-256 fingerprint.
- Added structured weights, action frequencies, blocker removal, filtering, class aggregation,
  normalized combo probabilities, and Bayesian action conditioning.
- Added dependency-free five/seven-card evaluation and verified all 2,598,960 five-card hands against
  exact category totals.
- Added exact weighted and seeded Monte Carlo equity for heads-up and multiway states, including ties
  and explicit exact-state limits.
- Added Decimal effective-stack, pot-odds, call-EV, SPR, MDF, bluff-frequency, and bet-EV metrics.
- Added versioned exact/nearest/interpolated stack-bucket matching with visible mismatch.
- Added strict range artifacts and canonical position/action/sizing spot keys. Imports reject wrong
  seats, rake, open size, stack bucket, missing validation, duplicate spots, or missing provenance.
- Added deterministic 13-by-13 range-matrix projection that retains blockers, exact combo mass,
  mixed actions, missing strategy mass, equity, EV, provenance, confidence, and version.
- Added explicit X-Poker 6-max and 9-max configuration support across game schemas, canonical hand
  state, clockwise reconstruction, hand-boundary validation, API inspection, and range spot keys.
  The current calibrated portrait layout is labeled 6-max; a representative 9-max layout remains
  required before 9-max perception can be promoted.
- Seeded isolated 6-max and 9-max position-specific RFI reference-prior libraries from a pinned
  MIT source. All 13 artifacts contain all 1,326 exact combos, hash-verified provenance, explicit
  prior folds, confidence 0.55, and warnings that the charts are approximate/not solver-derived.
- Added a hard `reference_prior` versus `gto_solution` artifact-role boundary so the bootstrap
  ranges cannot be presented as exact GTO.
- Added the Milestone 6 preflop strategy resolver: exact/nearest GTO matches require a
  `gto_solution` artifact; absent GTO returns `unavailable` while any reference prior is exposed in
  a separate field. Stack abstraction reports distance and reduces confidence deterministically.
- Completed Milestone 7 opponent modeling with Beta-Binomial sufficient counts and approximate 95%
  posterior intervals sliced by position, street, and size.
- Added immutable profile updates, baseline/inferred/exploit range snapshots, deterministic
  log-odds nodelock experiments, sample-shrunk/capped hero action adjustments, and supplied-EV
  best-response analysis with explicit non-solver assumptions.
- Added user-selectable 6-max/9-max session setup and BB/native-chip display modes. Exact native
  values format as grouped numbers, K, or M by threshold and remain unnormalized until a blind exists.
- Audited public solver candidates; current configuration-matched GTO artifacts remain unavailable.
  Approximate reference priors are never promoted to GTO. Control remains disabled.
- Added the local React/TypeScript monitoring dashboard with 6-max/9-max selection, BB/native-chip
  controls, reconstructed table state, legal action history, health, replay transport, and a
  position-specific 169-class reference-prior matrix.
- Added schema-versioned FastAPI/WebSocket monitoring snapshots and events, bounded subscriber
  queues, retained history, gap detection/recovery, and deterministic 6-max/9-max replay sources.
- Verified complete 14-transition six-max and nine-max browser replays with no console errors;
  strategy and capture absence remain explicit and table control stays unavailable.
- Added deterministic replay seek/step controls, pot odds, required equity, effective stack, SPR,
  snapshot latency, and inspectable legality/strategy/control decision gates. Equity and EV remain
  explicitly unavailable without a validated opponent range.
- Added a 20-session, 300-snapshot bounded-stream soak regression with exact drop telemetry.
- Added authorized one-shot X-Poker capture diagnostics with an in-memory/no-store frame, five
  declared-region overlays, 0.95 table-role confidence, and privacy-scoped rule/pot OCR.
- Added scheduled-versus-active Bomb Pot classification. A positive countdown leaves the current
  hand in standard NLH; an active single-board Bomb Pot requires observed forced contributions,
  skips preflop action, and enters the shared NLH state machine on the flop. Ambiguous modes,
  contribution amounts, multi-board hands, and Omaha remain quarantined.
- Added a dedicated `xpoker-windows-10-portrait-9max-v1` profile with nine canonical seat anchors.
  Live frames validated five occupied/four empty before play and three occupied/six empty during
  play after widening the plus-anchor search for side-seat movement.
- Removed mutable room titles from the default authorization gate. Capture still requires the
  allowlisted X-Poker executable hash and process, GLFW window class, supported geometry, and a
  high-confidence visual table role; PID/HWND remain session-scoped evidence.
- Added an in-memory continuous observation loop with a 30-sample bound, target-fingerprint lock,
  freshness/error telemetry, manual start/stop, and fail-closed stopping after three consecutive
  failures. Ambiguous modes clear consensus and are never accepted as stable state.
- Connected deterministic nine-max board geometry to live diagnostics. A nested bright component
  regression prevents rank-like shapes inside a card from becoming a false sixth card; the live
  active Bomb Pot frame now resolves as one row with five card surfaces while its mode remains
  quarantined because the loop began after forced contributions.
- Added privacy-scoped seat-panel OCR. Empty seats bypass OCR; raw player names/text are never
  retained; only a text hash and structured `Break`/stack candidates leave the adapter. Every
  numeric stack remains unaccepted until temporal and accounting gates agree.
- Validated the candidate path on the authorized active nine-max layout: the observer remained
  target-stable with zero capture failures and extracted multiple stack candidates while refusing
  unclear panels. This is calibration evidence, not an OCR-accuracy promotion.
- Locked continuous capture to the exact authorized PID/HWND after the initial executable-hash,
  process, class, geometry, and visual-table gate. In-hand animations can no longer make the table
  disappear, while any actual window/process identity change still stops observation.
- Added consecutive-frame pot and stack consensus. A changed amount must independently repeat for
  three distinct frames; an ambiguous current crop clears its prior consensus.
- Calibrated in-play `OPEN` seats, stylized pot-label OCR aliases, and upscaled per-seat action-badge
  crops. Live evidence reached eight occupied seats and produced fail-closed Fold, Check, Bet, and
  All-in candidates; temporally stable badges are exposed separately from canonical events.
- Structured X-Poker's active `Bomb Pot(4)` label as a forced-contribution candidate, while run-it-
  multiple-times overlays correctly quarantine false board geometry until the overlay disappears.
- Added consecutive board-count consensus and bounded exactly-once derived action candidates. A
  badge is eligible only after a clear frame, stable hand mode, supported/stable board street, and
  three distinct matching frames; candidates remain ineligible for canonical state until amount,
  order, dealer, and pot validation pass.
- Live validation produced one non-duplicated seat-2 preflop Call candidate and advanced the hand
  epoch on a stable postflop-to-preflop board transition. The candidate was correctly labeled
  non-canonical with accounting pending.
- Added a dependency-free, X-Poker-specific board-card candidate recognizer using a versioned
  18-by-26 glyph-mask artifact covering all thirteen ranks. Suit classification follows the
  observed X-Poker palette (black spades, red hearts, blue diamonds, green clubs).
- The artifact stores only derived card-glyph masks, source-frame hashes, intended use, and license
  boundary; it contains no player names or raw table pixels. Rank distance/margin, suit confidence,
  assumptions, and provenance remain inspectable.
- On two newly observed labeled boards, the first pass correctly recognized five of seven cards and
  failed closed on standard 2 and 6 glyphs; adding only those cropped glyphs made offline replay
  seven of seven. This is calibration, not held-out promotion evidence.
- Added three-frame per-slot card consensus and physical-card uniqueness. One subsequent unlabeled
  live flop reached stable `Jc Kc Td`; a chat overlay prevented visual labeling, so it is not counted
  as accuracy evidence.
- Added deterministic dealer-button component detection and nearest-seat mapping for the portrait
  layout. It matched the visually labeled dealer seat on five saved authorized frames spanning
  seats 0, 2, 4, 5, and 6, then reached five-frame live consensus on seat 4.
- Dealer observations remain candidates until three distinct frames agree; missing or multiple
  marker-shaped components clear consensus. Position assignment is still withheld from canonical
  state until the hand-boundary gate agrees.
- Added three-frame seat-status consensus for seated, open, and Break states. Live evidence resolved
  a seven-player active ring and intentionally withheld position names because the configured
  9-max ring was partial; six-max ranges were not silently substituted.
- Added deterministic full-ring position mapping for both selected 6-max and 9-max configurations.
  BTN follows dealer consensus, then SB/BB and the authoritative early-position sequence clockwise.
- Added bounded, hashed stable-stack-decrease candidates. Live observations derived decreases of
  2, 6, 8, 32, and 35 native units across provisional streets, all explicitly non-canonical until
  action and pot reconciliation.
- Changed action-badge arming from a global clear requirement to per-seat clearing so one lingering
  badge cannot block unrelated seats; exactly-once keys remain unchanged.
- Replaced repeated full-image seat-anchor scans with row/column prefix sums, reducing the measured
  per-frame seat-status pass from about 692 ms to 68 ms on the authorized portrait layout. This
  allowed the observer to retain short-lived badges while the user played normally.
- Added fail-closed action-amount reconciliation. A call, bet, raise, or all-in receives an amount
  only when exactly one same-seat stack decrease within eight frames maps back to exactly that one
  action in the same hand epoch and compatible street. Fold/check are explicitly amount-free;
  shared matches remain ambiguous and missing matches remain pending.
- Live validation on the authorized 9-max table captured 185 frames across three provisional hand
  epochs with zero failures and produced six mutually unique provisional matches: Call 2 and 4,
  plus Bet 4, 3, 6, and 2 native units. None are canonical events yet because legal order and pot
  accounting remain outstanding gates.
- Current full suite: Ruff passed; 260 Pytest/Hypothesis tests, 11 TypeScript tests, and the
  production dashboard build passed. Table control remains disabled.
- Added deterministic provisional clockwise-order validation. Each visual action now carries the
  stable dealer and active-seat context present when it was emitted. Preflop starts after the BB;
  postflop starts left of the dealer; folds and all-ins leave the actionable ring. Missing
  intervening actions stay pending, context changes are inconsistent, and no action is inferred.
- Replaced the prior one-action-per-seat/type key with a bounded per-hand occurrence ordinal. A
  badge must still clear and regain three-frame consensus, but valid repeated calls or raises by
  the same seat on one street now receive distinct deterministic event IDs.

## Completed project checkpoints

- Milestone 0 — reproducible schemas, configuration, logging, and deterministic simulated hand.
- Milestone 1 — autonomous public-source and component catalog with provenance/licensing boundaries.
- Milestone 2 — authorized X-Poker window discovery, calibration, normalized capture, and replay diagnostics.
- Milestone 5 — exact-combo ranges, deterministic poker math, matrix projection, stack abstraction,
  and isolated provenance-bearing 6-max/9-max reference priors.
- Milestone 7 — uncertainty-bearing opponent profiles, bounded exploit adjustments, nodelock-like
  range experiments, and synthetic regression evaluation.

## In-progress checkpoint

- Milestone 8 — local dashboard, session/chip controls, schema-versioned replay stream, bounded
  delivery, health/state/action/math inspection, replay scrubbing, decision audit, synthetic soak,
  and reference-prior visualization are implemented.

## Next

- Connect recorded/live capture, perception evidence, and reconstructed observations to the monitor.
- Record complete scheduled standard hands and an active single-board Bomb Pot from the authorized
  spectated table for temporal contribution and hand-mode calibration.
- Feed only mutually unique action/amount matches that also pass clockwise order and pot/stack
  accounting into the existing deterministic hand-state reducer.
- Expand held-out board-card replay coverage across every rank/suit and lighting/result-overlay
  state; keep low-margin cards unknown until the ≥99.9% card gate is measured and passed.
- Combine dealer consensus with stable occupied/Break states to derive provisional 6-max/9-max
  positions, then validate clockwise action order before creating canonical events.
- Reconcile mutually unique same-seat action/stack pairs with pot deltas; reject rather than infer
  a wager when the observer starts mid-action or temporal evidence arrives outside the match window.
- Continue gradual 3-to-9-player live captures to validate every occupied seat panel, player state,
  stack/bet crop, dealer marker, and clockwise action transition.
- Add opponent-range, poker-math, exact/abstracted strategy, exploit-frequency, provenance, and
  decision-trace views as those upstream results become available.
- Continue Milestone 6 solution import/resolution while keeping reference priors ineligible for exact-GTO results.
- Source or independently generate configuration-matched 6-max and 9-max no-rake 2 BB solutions.
- Add exact/nearest strategy-node lookup, quantitative mismatch, and replay comparisons.
- Connect the completed exploit layer to real reconstructed observations and resolved strategy EVs
  during Milestone 8 integration.
- Continue M3/M4 promotion evaluation in parallel when representative standard NLH replays exist.

## Blockers

- No blocker for continued offline/synthetic development.
- M3/M4 promotion needs representative complete standard NLH hands later; the user does not need
  nine devices and can provide a populated club table as spectator when available.
- The currently authorized spectated table is usable for capture/OCR calibration. Its positive
  Bomb Pot countdown does not quarantine intervening standard NLH hands; active-hand promotion
  still requires a recorded temporal sequence proving the contribution and board transitions.
- Nine-max visual evidence is now available from the authorized running table. Promotion still
  requires labeled/temporally validated complete-hand evidence across all seats and action states.

This file is updated at meaningful checkpoints. The detailed checklist remains in `docs/MILESTONES.md`.
