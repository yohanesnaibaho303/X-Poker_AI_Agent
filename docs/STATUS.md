# Build Status

- Last updated: 2026-08-26 (Asia/Jakarta)
- Current milestone: Milestone 8 — live monitoring application plus 9-max/native-only migration
- Overall project against revised scope: 3 of 11 milestones complete
- Current state: Milestone 6 is complete. Milestone 8 live-observation dashboard integration is in
  progress; its live-session exit gate and M3/M4 promotion gates remain pending.
- Live control: Disabled

## Requirement revision — 2026-08-26

- Supported table size is now 9-max only. Prior 6-max code, profiles, ranges, fixtures, dashboard
  controls, and documentation are legacy removal/migration work, not supported product behavior.
- Storage, calculation, strategy, and display now use exact native chips only; display uses grouped
  numbers and never K/M abbreviations.
- Authoritative blinds are SB 1 and BB 2 native chips. BB 2 is a forced blind, not a default opening
  raise; opening actions must be observed as native-chip amounts.
- Existing milestone completion counts predate this revision. Milestones 0, 5, and 8 require
  migration and regression updates before the revised baseline can be declared complete.

## Latest checkpoint

- Integrated owner-authorized GTOpen as an external preflop generator pinned at commit
  `4aee435bdeb155b25f0c8140e707a8342ce4356f`. Eight 200-chip RFI artifacts cover UTG through SB,
  use native SB 1 / BB 2 and raise-to 4 inputs, expand 169 classes deterministically to all 1,326
  physical combinations, and pass manifest hash validation. Owner authorization permits code and
  binary reuse; current integration keeps the solver external because vendoring adds no benefit.
- GTOpen's multiway terminal model is explicitly recorded on every artifact. Resolver results from
  this library are always `abstracted`, never `exact`; confidence is capped at 0.35 and unavailable
  per-action EV/equity remains unavailable rather than inferred.

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
- Current full suite: Ruff passed; 292 Pytest/Hypothesis tests, 11 TypeScript tests, and the
  production dashboard build passed. Table control remains disabled.
- Added deterministic provisional clockwise-order validation. Each visual action now carries the
  stable dealer and active-seat context present when it was emitted. Preflop starts after the BB;
  postflop starts left of the dealer; folds and all-ins leave the actionable ring. Missing
  intervening actions stay pending, context changes are inconsistent, and no action is inferred.
- Replaced the prior one-action-per-seat/type key with a bounded per-hand occurrence ordinal. A
  badge must still clear and regain three-frame consensus, but valid repeated calls or raises by
  the same seat on one street now receive distinct deterministic event IDs.
- Live validation after loading the order gate reached 538 frames and 11 provisional hand epochs
  with zero capture failures. Five preflop/flop streams formed gap-free clockwise prefixes; 14
  incomplete streets remained pending. A read-only synchronized visual check confirmed the table
  continued changing between point-in-time reads, so disagreements require matching frame hashes
  before they can be labeled recognition errors.
- Added bounded stable-pot-increase candidates and a third fail-closed reconciliation layer. An
  amount-bearing action passes this layer only when its already unique stack decrease equals exactly
  one same-hand, same-street stable pot increase within eight frames, and that pot delta maps back to
  only that action. Different nearby increases are mismatches; missing evidence stays pending;
  ambiguity clears the pot baseline so gaps are never bridged.
- Added an X-Poker-specific hero-card region for both supported portrait layouts. A deterministic
  detector isolates the single merged surface, splits the angled left/right cards, uses a separate
  orientation-scoped rank-mask artifact, and classifies suits from the local palette.
- The hero artifact contains fourteen derived masks across enrolled left/right orientations and only
  source-frame hashes, not table pixels. A live `Kc 8h` frame exposed a false nearest-template
  match at the initial 0.12 distance; the gate was tightened to 0.08 before temporal integration.
  Three distinct frames plus hero/board physical uniqueness are required, and an accepted hand is
  retained only within its provisional hand epoch if the cards disappear after a fold.
- Live hero-priority calibration visually labeled `9s 5c`; the previously unknown left-9 and right-5
  masks were enrolled with the matching authorized frame hash. This expands calibration coverage
  without treating the self-match as held-out accuracy evidence.
- Subsequent live hands labeled `7c 5c` and `7d 6s`. The previously enrolled right-5 recognized on
  the next appearance; two lighting variants for left-7 and the new right-6 mask were added with
  their exact frame hashes.
- A visually labeled `5d 2s` hand exposed adjacent-card color contamination: the old whole-crop
  palette pass labeled the right black spade as a diamond from the overlapping left card. Hero suit
  classification now uses only the orientation-specific outer 26 pixels, with a regression proving
  that neighboring blue pixels cannot override the right-card spade.
- After loading the suit fix, a live `Jh 8d` hand correctly classified the existing right-8 diamond
  while withholding the unknown left-J. The left-J mask was enrolled with its exact frame hash.
- Live validation then reached a complete, visually verified `8c 6h` hero detection: internal seat
  0, BB, four-handed on the selected 9-max layout, 60 BB stack/effective stack, 5.5 BB stable pot,
  and 10.91 SPR. The dashboard now highlights the detected hand class and shows its aggregated 2-BB
  open frequency only when a compatible unopened-position reference prior exists; BB stays unavailable.
- Added privacy-scoped native blind parsing from X-Poker's rule label, including grouped and compact
  chip tokens. Small and big blinds must appear together with `0 < SB < BB`, then repeat for three
  distinct frames before the live status exposes a `SB/BB` normalization basis. Ambiguous OCR clears
  the blind consensus; native stack and pot values are never silently treated as BB.
- Blind-token confidence is independent of Bomb-Pot mode confidence: live OCR damaged the unrelated
  label to `Bomb Fh)t` while retaining a clear `Blinds: 1/2`. The blind channel now remains eligible
  at 0.99 without making the ambiguous hand mode eligible.
- Corrected the live temporal wiring after a reload reproduced the inverse behavior: mode consensus
  now consumes only rule/mode confidence, while blind consensus consumes only native-blind
  confidence. A clear `1/2` observation can therefore remain stable while damaged mode text blocks
  the hand independently.
- Added a live hand-boundary gate layered on the stable postflop-to-zero transition. It snapshots
  the prior dealer and active ring, clears dealer consensus, and requires the button to advance to
  the next dealt seat after three new frames. An unchanged marker stays pending; a skipped dealer or
  changed active-seat set is rejected. The observer's first partial hand cannot establish a boundary.
- Boundary evidence now preserves the last stable dealer and active ring inside each epoch. The
  current-frame consensus still clears on occlusion, but a result animation hiding the button at the
  exact board reset no longer erases the already established prior-hand context.
- Added one inspectable reducer-readiness result for the current epoch. It lists unresolved boundary,
  mode, blind, dealer, active-ring, stack, hero/board card, amount, pot, and clockwise-order gates;
  exposes the accepted native BB only after blind consensus; and enumerates only fully reconciled
  action IDs. It never emits canonical events itself, and the dashboard shows its blocker count.
- Added lower-trust consecutive high-confidence pot-transition candidates for pots that change too
  quickly to repeat three times. They are explicitly non-canonical and become useful only when an
  independently stable action badge and same-seat stack decrease match the exact increase. If both
  endpoints later reach three-frame stability, the same transition is upgraded rather than duplicated.
- Added a privacy-scoped hero-control parser that distinguishes X-Poker pre-action toggles from a
  current Fold/Check/Call/Bet/Raise/All-in decision surface. Raw control OCR is discarded after
  parsing, normalized text is represented only by its SHA-256 fingerprint, and three identical
  frames are required for consensus. A stable pre-action bar remains explicitly non-actionable.
- Added exact forced-blind reconciliation at the first two active seats clockwise from a validated
  dealer. Equal early preflop stack decreases can now be corroborated or replaced by a three-frame
  numeric-only seat badge because X-Poker may overlay the blind on the stack panel. Both signals are
  limited to twelve frames after the witnessed boundary; later changes, duplicate interpretations,
  and aggregated blind-plus-call/raise deltas remain pending or ambiguous. Reducer readiness
  requires both posts explicitly.
- Cross-channel stack validation now quarantines a seat-panel amount when it exactly equals a
  simultaneous numeric-only badge at that seat. This prevents an overlaid blind or wager from being
  misread as the remaining stack and generating a false large decrease; the stack remains unknown
  until the unobscured panel stabilizes again.
- Added a Bomb-Pot-only direct-flop boundary path for tables that never expose three stable empty
  board frames between hands. It requires a changed three-card board, three-frame dealer consensus,
  unchanged active ring, and exact next-dealt-seat button movement; run-it-multiple-times board
  changes with an unchanged dealer do not create a hand boundary.
- Per user direction, no further product work will be spent on replay. The existing replay view
  remains available but optional; small deterministic recorded-hand tests remain internal safety
  infrastructure for recognition and reducer changes.
- Separated current rule-label visibility from retained reconstruction context. Three-frame mode
  evidence now persists for its provisional hand, and three-frame native blinds persist for the
  capture session through temporary overlays. Contradictory stable mode or blind values create a
  sticky fail-closed conflict; the dashboard exposes both current and retained consensus channels.
- Added the first deterministic live-to-canonical bridge for standard NLH. A witnessed boundary now
  snapshots pre-blind starting stacks; accepted blinds, hero cards, legal action candidates, and
  board transitions are reduced into a deterministic hand prefix only when exact stable current
  stacks and pot match the reducer. Rejections remain inspectable and control stays disabled.
- Reprioritized the MVP around automatic hero intelligence. Stable local hole-card or action-control
  evidence now identifies the calibrated X-Poker hero seat without a user-entered seat; exact
  full-ring position evidence automatically selects the reference range. A separate deterministic
  live-hero boundary exposes hand class, BB-normalized hero/pot/call values, effective stack, SPR,
  required equity, confidence, and explicit missing-input issues in the dashboard.
- Added explicit 3-to-9-handed dealt-position mapping that skips empty/Break seats clockwise. A
  short-handed 9-max table retains its selected 9-max reference scope and reports the exact seat
  mismatch instead of silently switching to six-max data.
- Added fixed-size derived rank-mask metadata to card diagnostics so an authorized visually labeled
  live hand can be enrolled before the frame changes. It retains no raw pixels or player identity
  and remains calibration-only evidence outside canonical state.

## Scope migration completed (2026-08-26)

- Product runtime, schemas, APIs, dashboard, simulations, fixtures, and range artifacts now support 9-max only.
- All canonical monetary fields use exact native-chip amounts. BB conversion/display and K/M abbreviations are removed.
- Fixed blinds are SB 1 and BB 2 native chips. The seeded reference-prior open size is 4 native chips.
- Retired 6-max configurations, layouts, manifests, and range artifacts were removed.
- Runtime request schemas and dashboard API calls no longer accept a table-size selector.
- Position, action-order, and hand-boundary helpers reject retired six-seat layouts while retaining
  3-to-9-handed play inside the fixed nine-seat table model.
- Strategy mismatch explanations and the reproducible reference-prior importer now use native-chip
  stack and action keys only.
- Synthetic replay controllers and snapshot builders no longer accept table-size arguments; their
  runtime scope is fixed to the authoritative nine-seat model.
- Monitoring snapshot strategy, exploit, and poker-math payloads are now strict typed contracts.
  The dashboard displays strategy role/confidence/assumptions, opponent-model availability, and
  deterministic replay math without inventing equity or EV.
- Preflop spot validation rejects `bet` actions and rejects encoding the forced 2-chip BB as an
  opening raise. The native synthetic hand regression separately proves blind posts of 1 and 2,
  followed by the observed 4-chip voluntary opening raise.
- Strategy resolution now exposes a strict per-combination result with action frequencies, equity,
  native-chip EV, native-chip EV loss, confidence, source artifact, and assumptions. Missing ranges,
  missing combinations, and incomplete EV data fail closed instead of fabricating values.
- The dashboard reference-range panel now renders selected-hand action-frequency bars and shows
  equity and native-chip EV when present. Reference priors remain visibly separate from GTO results.
- Range artifacts now reject BB/K/M or malformed sizing keys, unsized monetary actions, non-finite
  chip amounts, and EV entries for actions absent from the strategy. Frontend regressions verify
  deterministic action ordering and no fabricated rows when strategy is unavailable.
- Bomb Pot fault injection now explicitly rejects unequal observed contributions unless the short
  contributor is stack-exhausted; no contribution is inferred from a configured label or range.
- Added deterministic exact-combination strategy comparison. It reports candidate-minus-baseline
  frequency, equity, and native-chip EV deltas while leaving missing paired values unavailable.
- Added full nine-max native-chip strategy-node keys, exact and nearest geometry lookup, quantitative
  stack/pot mismatch, board/action-tree isolation, and hash-verified authorized solver export import.
- Added a versioned recognition evaluation runner with content-hashed datasets, per-slice accuracy,
  rejection, confidence, and p95 latency. Calibration/regression fixtures cannot satisfy promotion.
- Monitoring now carries per-combo strategy actions, equity, EV and EV loss plus explicit opponent-
  range state and GTO/exploit comparison. Reference priors remain ineligible for a GTO label.
- The state reducer now requires exact ordered SB 1 and BB 2 forced posts from the correct seats;
  legacy blind sizes, wrong order, wrong seats, extra posts, and amount mismatches fail closed.
- Milestone 10 now has a fail-closed compatibility audit covering the authoritative 9-max SB 1 / BB
  2 configuration, controller lockout, hash-verified reference library, complete parseable schema
  set, and production dashboard entry point. The local API exposes the inspectable audit result;
  missing or malformed artifacts make the combined result fail.
- Added a Windows package builder and offline-readiness runner. The frozen 2026-08-26 report passed
  100 sessions and 1,500 snapshots deterministically at 97.4332 ms p95 against the 200 ms offline
  replay budget, with dependency locks, templates, configurations, and schemas content-hashed.
- Added reconstruction promotion accounting with frozen replay hashes, exact supported-hand rate,
  100% unsupported-state safety, p95 latency, and holdout-only promotion eligibility.
- Removed remaining K/M numeric parsing from vision, pot, action-badge, hero-control, and rule-label
  paths. Compact amounts now fail closed; only exact native-chip numbers are calculated.
- Live diagnostics and reconstruction readiness now require observed native blinds to be exactly
  SB 1 / BB 2. Other blind structures remain visible as evidence but cannot enter reconstruction.
- Compatibility auditing now detects schema drift and retired six-max runtime artifacts, not only
  missing files. Any mismatch fails combined offline readiness.
- Recorded capture manifests can now run through the exact production recognition boundary without
  a live table. Reports verify frame hashes, omit raw OCR text, expose latency and structured outputs,
  and remain explicitly ineligible for holdout promotion until labels are supplied.
- A 12-frame legacy-layout replay completed through production recognition at 498.1948 ms p95.
  This exceeds the 200 ms target and does not pass M3: source layout differs from current calibration,
  identity fields are absent in the historical manifest, and no holdout labels exist. Evidence is
  retained as a failed regression benchmark, not a promotion result.
- Historical notes below describe earlier checkpoints and are retained only as legacy evidence; they are not supported behavior.
## Completed project checkpoints

- Milestone 0 — reproducible schemas, configuration, logging, and deterministic simulated hand.
- Milestone 1 — autonomous public-source and component catalog with provenance/licensing boundaries.
- Milestone 2 — authorized X-Poker window discovery, calibration, normalized capture, and replay diagnostics.
- Milestone 5 — exact-combo ranges, deterministic poker math, matrix projection, stack abstraction,
  and isolated provenance-bearing nine-max native-chip reference priors.
- Milestone 7 — uncertainty-bearing opponent profiles, bounded exploit adjustments, nodelock-like
  range experiments, and synthetic regression evaluation.

## In-progress checkpoint

- Milestone 8 — local dashboard, session/chip controls, schema-versioned replay stream, bounded
  delivery, health/state/action/math inspection, replay scrubbing, decision audit, synthetic soak,
  and reference-prior visualization are implemented.

## Next

- Continue live capture, perception evidence, and reconstructed-observation integration in the monitor.
- Observe complete standard hands and an active single-board Bomb Pot on the authorized table for
  temporal contribution and hand-mode calibration; no new user-facing replay work is required.
- Feed only mutually unique action/amount matches that also pass clockwise order and pot/stack
  accounting into the existing deterministic hand-state reducer.
- Expand held-out board-card evaluation coverage across every rank/suit and lighting/result-overlay
  state; keep low-margin cards unknown until the ≥99.9% card gate is measured and passed.
- Combine dealer consensus with stable occupied/Break states to derive provisional positions for
  3-to-9 dealt players in the fixed nine-seat model, then validate clockwise action order before
  creating canonical events.
- Reconcile mutually unique same-seat action/stack pairs with pot deltas; reject rather than infer
  a wager when the observer starts mid-action or temporal evidence arrives outside the match window.
- Continue gradual 3-to-9-player live captures to validate every occupied seat panel, player state,
  stack/bet crop, dealer marker, and clockwise action transition.
- Add opponent-range, poker-math, exact/abstracted strategy, exploit-frequency, provenance, and
  decision-trace views as those upstream results become available.
- Connect the completed exploit layer to real reconstructed observations and resolved strategy EVs
  during Milestone 8 integration.
- Continue M3/M4 promotion evaluation from representative live standard NLH evidence, retaining
  only minimal internal regression fixtures needed for deterministic safety tests.

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
