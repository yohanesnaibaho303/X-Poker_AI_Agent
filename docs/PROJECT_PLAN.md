# X-Poker AI Agent — Full Project Plan

## 1. Project Objective

Build an autonomous Windows-based AI agent for an authorized private X-Poker test table. The agent will learn the X-Poker interface from public references, observe the running application, reconstruct poker hands, calculate Game Theory Optimal (GTO) and exploitative strategies, display live monitoring, and ultimately interact with the authorized test table.

The first supported configuration is:

```yaml
game:
  variant: NLH
  format: cash
  supported_seats: [6, 9]
  rake: 0
  default_open_size_bb: 2.0
  objective: chip_ev
  supported_hand_modes: [standard_nlh, single_board_bomb_pot]
```

`2 BB` is treated as the default preflop open size. Effective stack depth will be detected dynamically for every hand.

At session setup, the user selects either 6-max or 9-max and chooses BB or native-chip display.
Native chips remain exact internally. Values below 100,000 display as grouped numbers such as
`10,000`; values from 100,000 to below 1,000,000 display as K, such as `200K`; values from 1,000,000
upward display as M, such as `1M`. Native chips convert to BB only after the blind is entered or
reliably detected.

X-Poker single-board NLH Bomb Pot is supported as a separate detected hand mode. Scheduled Bomb Pot
text does not make ordinary intervening hands unsupported. When a Bomb Pot hand is active, all
participating seats make observed forced contributions, preflop betting is skipped, and NLH action
begins on the flop. Contribution amounts are reconstructed from observations and pot/stack
invariants rather than inferred from a displayed configuration range. Double-board, Omaha,
ambiguous-board, and uncertain-contribution states remain quarantined.

## 2. Product Vision

The final agent should operate as an inspectable perception–reasoning–action system:

```text
Public videos, articles and repositories
                    ↓
          Research and knowledge agent
                    ↓
      X-Poker visual component catalog
                    ↓
       Authorized X-Poker window capture
                    ↓
       Vision, OCR and temporal tracking
                    ↓
          Validated NLH hand state
                    ↓
     Hero and opponent weighted ranges
                    ↓
   Poker math + GTO + exploitative engine
                    ↓
 Monitoring dashboard and explanations
                    ↓
 Authorized test-table control and verification
```

The agent must not be a black box. Each observation and recommendation must include its source, assumptions, confidence, and relevant calculations.

## 3. Core Requirements

### 3.1 Autonomous research

The research agent will:

- Find public X-Poker gameplay videos, tutorials, reviews, screenshots, and articles.
- Extract available transcripts and source metadata.
- Identify video segments containing useful table states.
- Sample representative frames and remove duplicates.
- Classify material by X-Poker version, layout, theme, orientation, game type, and street.
- Research NLH rules, GTO concepts, range construction, solver output, and exploitative theory.
- Inspect relevant open-source poker projects for reusable architectural ideas.
- Maintain provenance and licensing information for every external source.
- Distinguish mathematical facts, solver-derived results, heuristics, and player opinions.

Public material will bootstrap the system. Exact geometry and recognition will later be calibrated automatically from the running authorized X-Poker instance; the user will not need to prepare screenshots manually.

### 3.2 X-Poker application monitoring

The application will:

- Detect the X-Poker process or its Android emulator window.
- Identify the correct authorized test-table window.
- Treat room titles as mutable metadata rather than stable identity. Authorization combines the
  allowlisted X-Poker executable hash, process name, window class, supported geometry, and visual
  table role; PID/HWND are session-scoped because they change after restart.
- Capture only the required table region.
- Handle window movement, resizing, display scaling, and supported themes.
- Detect whether a hand is active.
- Process frames at an adjustable rate.
- Record recognition evidence and state transitions for debugging.
- Avoid retaining unrelated personal or account information.

### 3.3 Visual recognition

The vision system must recognize:

- Table boundaries and layout.
- Hero seat and all occupied seats.
- Player names where required for test profiles.
- Player stack sizes and current bets.
- Hero hole cards.
- Flop, turn, and river cards.
- Revealed opponent cards at showdown.
- Pot size and side pots.
- Dealer, small-blind, and big-blind indicators.
- Active-player highlight and action timer.
- Fold, check, call, bet, raise, and all-in events.
- Available action buttons.
- Bet input, slider, and preset sizing controls.
- Sit-out, disconnected, empty-seat, and folded states.
- Multiway and heads-up states within supported six-seat and nine-seat tables.
- All nine canonical seat anchors in the portrait 9-max layout, with deterministic
  occupied/empty/ambiguous classification independent of player names.

The implementation will use a hybrid approach:

- Stable-region geometry for fixed elements.
- Template matching for stable icons.
- OCR specialized for stack, bet, and pot displays.
- Card-specific rank and suit recognition.
- Object detection for variable components.
- Temporal tracking across consecutive frames.
- Poker-rule validation to reject impossible readings.

Every recognized value will carry a confidence score and evidence reference.

## 4. Initial NLH Game Model

### 4.1 Positions

The supported position models are:

```text
6-max: UTG → HJ → CO → BTN → SB → BB

9-max: UTG → UTG+1 → MP → LJ → HJ → CO → BTN → SB → BB
```

The engine will derive actual position from the dealer button and occupied seats. It must correctly handle tables with temporarily empty or sitting-out seats.

### 4.2 Cash-game assumptions

- Strategy objective is chip EV.
- No tournament ICM, bounty, or payout pressure is applied.
- Rake is zero for the initial authorized setup.
- Default opening size is 2 BB.
- Nonstandard opening sizes must still be detected and represented.
- Antes, straddles, bomb pots, and special rules are disabled unless detected and explicitly supported.
- Effective stack is calculated separately for every relevant player pair.

### 4.3 Stack-depth buckets

The initial strategy index will support:

```text
20 BB, 40 BB, 50 BB, 75 BB, 100 BB, 150 BB, 200 BB
```

Observed depths between buckets will use a documented nearest-solution or interpolation policy. The dashboard must show when an exact solution is unavailable.

## 5. Hand-State Reconstruction

The state model separates four concepts that must not be collapsed into one flat list:

### 5.1 Table and hand lifecycle

```text
table_status: unavailable | ready | waiting_for_hand | in_hand | hand_complete
street:       none | preflop | flop | turn | river | showdown
```

### 5.2 Player participation status

```text
empty | seated | active | folded | all_in | sitting_out | on_break | disconnected
```

These are persistent statuses observed or derived for each seat. `sitting_out`, `on_break`, and `disconnected` are table/session statuses and are not poker betting actions.

### 5.3 Betting actions

```text
fold | check | call | bet | raise | all_in
```

These are the canonical decisions made by a player during a betting round. The system records the actor, street, amount where applicable, and supporting evidence. `all_in` also changes the player's participation status to `all_in` while the hand continues.

X-Poker's persistent `F/C`, `Check`, and `Call Any` widgets are pre-action toggles, not proof that
the hero is currently facing a legal decision. Perception must classify the control surface as
`absent`, `pre_action`, `decision`, or `ambiguous`. Only an unchanged `decision` surface observed in
at least three distinct frames may supply candidate legal actions; pre-action toggles never do.
Raw control-region OCR is not retained: diagnostics store the parsed state and a normalized-text
SHA-256 fingerprint for replay correlation.

Current-frame rule-label OCR is distinct from retained reconstruction context. Once three stable
frames establish the hand mode, that evidence remains attached to the current provisional hand
through temporary overlays. Stable native blinds remain attached to the capture session. A
contradictory stable mode before a validated boundary or changed blinds during one session is a
sticky fail-closed conflict, not an automatic replacement.

### 5.4 Lifecycle and dealing events

The application still records non-action events required to reconstruct and validate a complete hand:

```text
HAND_STARTED
DEALER_ASSIGNED
BLIND_POSTED
BOMB_ANTE_POSTED
HOLE_CARDS_OBSERVED
BOARD_CARDS_OBSERVED
SHOWDOWN_STARTED
POT_AWARDED
HAND_COMPLETED
```

These are internal reconstruction events, not player actions or player statuses. Board-card events carry the resulting street rather than using separate `FLOP_DEALT`, `TURN_DEALT`, and `RIVER_DEALT` action-like labels.

The state engine will validate:

- Legal action order.
- Street progression.
- Unique physical cards.
- Stack and bet changes.
- Pot accounting.
- Minimum raise rules.
- All-in and side-pot behavior.
- Heads-up and multiway transitions.
- Dealer and blind movement between hands.
- Standard versus single-board Bomb Pot hand mode, including complete observed forced
  contributions before a Bomb Pot flop and no preflop Bomb Pot actions.
- Exact small- and big-blind posts at the first two active seats clockwise from a validated dealer.
  A post requires an equal stack decrease or a three-frame numeric-only seat badge within twelve
  frames of the witnessed boundary. Matching independent channels corroborate one another; an
  aggregated blind-plus-action decrease is not split or inferred.

Representative structured state:

```json
{
  "variant": "NLH",
  "format": "cash",
  "seats": 9,
  "rake": 0,
  "street": "flop",
  "hero_position": "BTN",
  "hero_cards": ["As", "Kd"],
  "board": ["Qs", "Jh", "2c"],
  "pot_bb": 9.5,
  "effective_stack_bb": 96.0,
  "action_history": [],
  "available_actions": ["fold", "call", "raise"],
  "confidence": {}
}
```

## 6. Range Engine

Ranges are first-class structured data and will never exist only as prose inside a language-model prompt.

### 6.1 Range representation

For NLH, the engine will support:

- All 1,326 exact two-card starting combinations.
- The standard 169-class preflop matrix.
- Combination weights from `0.0` to `1.0`.
- Card removal and blocker effects.
- Weighted frequencies for every legal action.
- Equity and EV per exact combination when available.
- Range metadata, assumptions, source, and confidence.

Example:

```json
{
  "spot": "BTN_vs_BB_SRP_100BB",
  "player": "BTN",
  "street": "flop",
  "board": ["Qs", "7h", "2s"],
  "combos": {
    "AsKs": {
      "weight": 1.0,
      "actions": {
        "check": 0.28,
        "bet_33": 0.72
      },
      "equity": 0.61,
      "ev": {
        "check": 8.12,
        "bet_33": 8.26
      }
    }
  }
}
```

### 6.2 Preflop range library

Separate initial libraries will cover six-max and nine-max, no-rake, 2 BB opening trees:

Milestone 5 may bootstrap clearly labeled, low-confidence reference priors for rendering and opponent
initialization. Such priors are not GTO solutions and cannot satisfy Milestone 6 strategy matching.

- Open-raise ranges for every position.
- Big-blind and small-blind defence ranges.
- Cold-call ranges.
- Three-bet and four-bet ranges.
- Responses to three-bets and four-bets.
- Squeeze ranges.
- Isolation ranges if limping is enabled later.
- All-in and call-off ranges by effective stack.
- Heads-up and multiway branches.

Ranges must be indexed by position, stack depth, previous actions, sizing, players remaining, and card removal.

### 6.3 Dynamic opponent ranges

Each opponent starts with a position- and configuration-based prior. The prior is updated after every observed action.

```text
Position-based starting prior
            ↓
Observed preflop action and size
            ↓
Board and card-removal filtering
            ↓
Postflop action and sizing update
            ↓
Showdown evidence and profile update
```

The opponent model will preserve:

- Baseline GTO range.
- Current inferred range.
- Exploit-adjusted range.
- Combination weights.
- Sample size.
- Confidence interval.
- Evidence and last update.

## 7. Poker Mathematics Engine

The deterministic mathematics layer will implement:

- Five- and seven-card hand evaluation.
- Exact enumeration when computationally reasonable.
- Monte Carlo equity for larger state spaces.
- Multiway equity.
- Pot odds and required equity.
- Expected value.
- Effective stacks.
- Stack-to-pot ratio.
- Fold equity.
- Minimum defence frequency.
- Range versus range equity.
- Equity distribution.
- Range advantage and nut advantage.
- Bet-size normalization in pot and BB units.
- Side-pot accounting.

This layer will have exhaustive unit and property-based tests. A language model will not perform arithmetic that deterministic code can calculate reliably.

## 8. GTO Strategy Layer

### 8.1 Reference systems

The following initial references will guide research and architecture:

- [GTO Wizard](https://app.gtowizard.com/) — range matrices, mixed strategies, EV/equity presentation, solution navigation, range comparison, custom solving, training workflows, and nodelocking concepts.
- [PokerGPT](https://github.com/HarperJonesGPT/PokerGPT) — compact reference for screen reading, OCR, state organization, monitoring, and action separation. It is MIT-licensed.
- [dickreuter/Poker](https://github.com/dickreuter/Poker) — reference for configurable table templates, OpenCV/neural recognition, Monte Carlo calculation, strategy editing, and table mapping. It is GPL-3.0.

GTO Wizard is a conceptual and interface reference unless legitimate programmatic access or an authorized export method is available. Proprietary solution data will not be assumed to be freely downloadable.

The project will independently implement its core architecture. Direct GPL code reuse will be avoided unless the entire derivative licensing decision is made deliberately.

### 8.2 Strategy sources

GTO strategy may come from:

- Properly licensed precomputed solutions.
- Our own solver runs.
- Compatible open-source solver outputs.
- User-authorized exports.
- Manually validated range charts.
- Research material used as conceptual guidance rather than numerical truth.

Every strategy object will record its origin and configuration.

### 8.3 Solution matching

The resolver will match the observed hand using:

```text
NLH
→ cash
→ detected 6-max or 9-max configuration
→ no rake
→ positions and players remaining
→ effective stack
→ 2 BB or observed opening size
→ complete preflop action
→ board and street
→ pot geometry
→ available bet sizes
```

If no exact solution exists, the system must:

1. Select the nearest compatible abstraction.
2. Quantify the mismatch.
3. Reduce confidence.
4. Display the assumptions.
5. Avoid presenting an approximation as an exact GTO result.

### 8.4 Strategy presentation

The interface will support:

- A 13×13 preflop range matrix.
- Combination-level postflop ranges.
- Color-coded actions.
- Mixed-action frequencies.
- Equity, EV, and EV loss.
- Range comparison.
- Hand-category and draw filters.
- Decision-tree navigation.
- Highlighting the observed hero combination.
- Range and nut-advantage graphs.

## 9. Exploitative Strategy Layer

The exploitative engine will compare observed behavior with the selected GTO baseline.

Tracked statistics may include:

- VPIP.
- Preflop raise frequency.
- Open frequency by position.
- Three-bet, four-bet, and squeeze frequency.
- Fold to three-bet.
- Continuation-bet frequency by street and size.
- Fold to continuation bet.
- Check-raise frequency.
- Aggression frequency by street.
- Bet-size patterns.
- Showdown frequency and revealed range composition.

The system will support nodelock-like analysis:

- Lock or estimate an opponent's action frequencies.
- Recalculate or approximate a best response.
- Identify overfolding, overcalling, underbluffing, overbluffing, and sizing imbalances.
- Separate player-specific evidence from population assumptions.
- Scale deviations by sample size and uncertainty.

Example output:

```text
GTO baseline:
  Bet 33% pot: 72%
  Check: 28%

Observed opponent model:
  Folds to small flop bets 11% more than baseline
  Confidence: medium

Exploit adjustment:
  Bet 33% pot: 84%
  Check: 16%
```

## 10. Monitoring Dashboard

The desktop dashboard will show:

- Session controls for selecting 6-max or 9-max and choosing BB or automatically compacted native-chip display.

- Live captured table.
- Recognition bounding boxes and confidence.
- Reconstructed hand state.
- Player positions and effective stacks.
- Pot and action history.
- Hero range matrix.
- Estimated opponent ranges.
- GTO action-frequency chart.
- Exploit-adjusted action chart.
- Equity, EV, pot odds, and required equity.
- Suggested action and sizing.
- Exact solution or abstraction status.
- Explanation and assumptions.
- Source provenance.
- Event log. The already implemented replay view is optional diagnostic tooling and will not be
  expanded or treated as an MVP product requirement.
- System health, latency, and current operating mode.

The dashboard will provide distinct modes:

```text
Observe → Analyze → Recommend → Armed Test Control
```

## 11. Authorized Test-Table Controller

Control will be added only after perception, state reconstruction, and strategy meet their evaluation thresholds.

The controller will:

- Verify the authorized table identity before activation.
- Require manual arming for a test session.
- Provide an immediate emergency stop.
- Require stable state across multiple frames.
- Reject ambiguous or low-confidence actions.
- Prevent duplicate clicks.
- Convert abstract sizing to the closest supported X-Poker control.
- Enter custom sizes when required and supported.
- Click the selected action.
- Verify that the resulting table state matches the expected transition.
- Stop if the window, table, game configuration, or state becomes inconsistent.
- Record each decision, click target, result, and confidence for replay.

Mixed strategies will use a seeded randomizer so tests can be reproduced exactly.

## 12. Continuous Learning and Evaluation

The system will not modify production behavior merely because it encounters a new screenshot. Improvement follows a controlled loop:

```text
Low-confidence or failed observation
                ↓
       Candidate review dataset
                ↓
 Label, validate or derive synthetic variants
                ↓
        Train or adjust one component
                ↓
 Run regression and holdout evaluations
                ↓
 Promote only if quality improves
```

Separate evaluation suites will cover:

| Component | Initial target |
|---|---:|
| Card rank and suit recognition | ≥99.5% |
| Stack, bet, and pot OCR | ≥99% on supported layouts |
| Street detection | ≥99.9% |
| Completed-hand reconstruction | ≥98% |
| Poker mathematics tests | 100% |
| Range lookup determinism | 100% |
| Action-target accuracy | 100% in calibration suite |
| Duplicate-action prevention | 100% |
| Unsupported or ambiguous state | Always stop or fall back |

End-to-end evaluations will replay complete recorded hands without controlling the live window.

## 13. Technical Architecture

### 13.1 Recommended initial stack

- Python 3.12 for capture, vision, state, simulation, and strategy services.
- OpenCV for image processing and template matching.
- ONNX Runtime or PyTorch for learned recognition models.
- OCR engine selected after an X-Poker-specific benchmark.
- FastAPI for the local service boundary.
- SQLite initially, with a migration path to PostgreSQL if required.
- React and TypeScript for the monitoring dashboard.
- WebSocket events for live state and recognition updates.
- Pytest for unit, property, regression, and replay tests.
- Structured JSON logging with screenshot/frame references.

The project will prefer deterministic local components for time-critical observation and poker mathematics. Language models will be used for research, knowledge synthesis, explanations, and bounded agent orchestration—not as the only source of game state or numerical strategy.

### 13.2 Proposed repository layout

```text
xpoker-agent/
├── apps/
│   ├── monitor/                 # React monitoring dashboard
│   └── trainer/                 # Replay and simulated-table UI
├── services/
│   ├── research/                # Source discovery and ingestion
│   ├── capture/                 # Windows/emulator window capture
│   ├── vision/                  # Cards, OCR and component detection
│   ├── state/                   # Hand-state reconstruction
│   ├── ranges/                  # Weighted NLH range engine
│   ├── poker_math/              # Equity, EV and hand evaluation
│   ├── strategy/                # GTO lookup and abstraction
│   ├── exploit/                 # Opponent models and adjustments
│   └── controller/              # Authorized test interaction
├── data/
│   ├── catalog/                 # Source and license registry
│   ├── transcripts/             # Permitted transcript material
│   ├── frames/                  # Research and calibration frames
│   ├── labels/                  # Visual annotations
│   ├── hands/                   # Reconstructed hand histories
│   ├── ranges/                  # Versioned range data
│   └── solutions/               # Licensed/generated solver data
├── models/                      # Versioned recognition artifacts
├── configs/
│   ├── game/                    # 6-max and 9-max NLH configurations
│   ├── layouts/                 # X-Poker layouts and themes
│   └── runtime/                 # Capture and controller settings
├── tests/
│   ├── unit/
│   ├── replay/
│   ├── vision/
│   ├── strategy/
│   └── end_to_end/
└── docs/
```

## 14. Delivery Phases

### Milestone 0 — Requirements and reproducibility

- Create the repository and development environment.
- Encode the initial 6-max and 9-max NLH, 2 BB, no-rake configurations.
- Define table-state, event, range, decision, and provenance schemas.
- Add deterministic tests and structured logs.
- Produce one command to start the development system.

**Exit criterion:** Schemas and configuration load successfully, and a simulated hand can be represented end to end.

### Milestone 1 — Autonomous reference research

- Build the source registry.
- Collect public X-Poker references and poker-strategy resources.
- Process accessible transcripts and representative frames.
- Classify sources and record licensing/provenance.
- Produce the initial X-Poker component catalog.
- Document findings from PokerGPT and dickreuter/Poker.

**Exit criterion:** A reviewable catalog exists with representative examples of every critical table component.

### Milestone 2 — Window capture and calibration

- Detect and capture the authorized X-Poker window.
- Normalize window dimensions and DPI.
- Locate the table and primary regions.
- Create the first supported layout profile.
- Add capture replay and diagnostics.

**Exit criterion:** Stable normalized frames can be collected automatically from the authorized instance.

### Milestone 3 — Visual recognition MVP

- Detect seats, hero cards, board, pot, stacks, bets, dealer, and controls.
- Add confidence scoring and temporal smoothing.
- Build visual regression tests from held-out frames.

**Exit criterion:** Recognition meets its initial per-component targets on the supported layout.

### Milestone 4 — Complete hand reconstruction

- Implement the NLH state machine.
- Validate action order, pot accounting, stack movement, and card uniqueness.
- Export completed hands in an internal canonical format.
- Keep deterministic recorded-hand tests for safety; a user-facing replay viewer is not required
  for MVP completion.

**Exit criterion:** At least 98% of supported recorded test hands reconstruct correctly from start to completion.

### Milestone 5 — Range and poker-math foundation

- Implement 1,326-combination weighted ranges.
- Implement the 169-class range matrix.
- Add blocker-aware filtering and action updates.
- Implement equity, EV, pot odds, and multiway calculations.
- Seed separate six-max and nine-max, no-rake, 2 BB range libraries.

**Exit criterion:** Range and mathematical tests pass, and the dashboard can show position-specific preflop ranges.

### Milestone 6 — GTO strategy integration

- Import or generate validated strategy data.
- Implement exact and nearest-solution lookup.
- Display mixed frequencies, EV, equity, and abstraction distance.
- Compare decisions with reference solutions.

**Exit criterion:** Replayed test spots produce deterministic, source-backed strategy results.

### Milestone 7 — Exploitative modeling

- Track opponent observations and sample sizes.
- Maintain baseline and inferred ranges.
- Add confidence-scaled exploit adjustments.
- Support nodelock-like experiments and best-response analysis.

**Exit criterion:** Synthetic opponent profiles produce explainable and regression-tested adjustments.

### Milestone 8 — Live monitoring application

- Connect capture, vision, state, ranges, strategy, and dashboard.
- Add health monitoring and latency measurement.
- Show recommendations with confidence and assumptions.
- Record full decision traces.
- Prioritize an automatic live-hero path: detect the local hole cards and hero seat, resolve the
  position, normalize accepted stack/pot/call evidence to BB, and display deterministic pot odds,
  effective stack, SPR, and the matching provenance-bearing range. Full replay and complete
  opponent-history presentation are not on the MVP critical path.
- Resolve 3-to-9-handed positions from the actually dealt clockwise ring. A selected 9-max table
  remains 9-max range scope when temporarily short-handed; expose the seat-count mismatch rather
  than silently substituting six-max ranges.

**Exit criterion:** The authorized table can be monitored continuously for complete sessions without state corruption.

**Current checkpoint (2026-08-24):** The local React/TypeScript dashboard and FastAPI/WebSocket
boundary run complete deterministic 6-max and 9-max synthetic hand replays. Schema-versioned
snapshots, bounded event delivery, gap recovery, session/chip controls, reconstructed state, action
history, replay scrubbing, health/latency, deterministic pot odds and SPR, reference-prior ranges,
decision gates, assumptions, and fail-closed strategy/control status are inspectable. A 20-session,
300-snapshot synthetic soak regression protects stream/state integrity. The authorized capture path
now shows an in-memory, no-store table frame with declared-region overlays, table-role confidence,
privacy-scoped rule/pot OCR, scheduled-versus-active Bomb Pot classification, and explicit
ambiguous/unsupported-mode quarantine. The milestone remains in
progress until component recognition and standard-NLH reconstruction output, opponent ranges,
resolved strategy/equity/EV views, and complete authorized-session evidence pass their gates.

The authorized 9-max calibration profile now contains all nine canonical seat anchors. Live idle
and playing frames validate empty-plus versus occupied-panel classification as population changes;
the first playing checkpoint correctly classified three occupied and six empty seats, a five-card
board, pot text, and the scheduled Bomb Pot countdown. This is calibration evidence, not yet an M3
accuracy promotion.

The capture boundary also supports a bounded continuous observer. It retains only the latest frame
and 30 mode samples in memory, locks the target fingerprint for the session, stops after three
consecutive capture failures or any target-identity change, and exposes freshness, failure counts,
seat occupancy, single-board geometry, and non-ambiguous temporal consensus. Ambiguous observations
can never become accepted consensus. The loop now emits bounded provisional action and stack-delta
candidates, but it does not yet emit canonical betting actions or completed hands.

Seat-panel OCR is now connected as a privacy-scoped candidate channel. Empty seats skip OCR, raw
panel text and player names are not retained, and only hashed evidence plus structured player-state
and native-stack candidates cross the adapter boundary. A single numeric observation is never
accepted; temporal stability, stack movement, pot accounting, and hand-state legality remain
required before it can update canonical state.

Continuous capture now performs full visual authorization once, then locks the exact executable,
PID, HWND, class, aspect, and layout fingerprint for the observation session. This preserves the
authorized boundary through table animations; a replaced process/window still fails closed. Live
diagnostics also expose consecutive-frame pot/stack consensus and privacy-scoped action-badge
candidates. These observations remain outside canonical hand state until exactly-once event
derivation passes action-order, amount-delta, pot-accounting, and board-transition validation.

The live observer now derives a bounded, deterministic candidate stream from stable action badges.
It arms only after a badge-clear frame, keys each candidate by target/hand epoch/street/seat/action,
and cannot emit the same key twice. Supported board counts establish the provisional street and a
stable postflop-to-zero transition advances the provisional hand epoch. These are explicitly not
`HandEvent` records; dealer, amount, action order, and accounting gates are still required.

Board-card recognition now has an X-Poker-specific, dependency-free candidate path. Versioned
low-resolution glyph masks cover all ranks without storing raw table/player pixels; deterministic
palette evidence supplies suit candidates. Rank distance, second-rank margin, suit confidence,
three-frame slot consensus, and physical-card uniqueness all fail closed independently. This
calibration path cannot satisfy the card-accuracy exit gate until a larger held-out labeled replay
set passes it.

Hero-card recognition uses a separate declared layout region and orientation-specific artifact
because X-Poker overlaps and angles the two bottom cards. The detector requires exactly one merged
card surface, splits deterministic left/right crops, applies a stricter 0.08 rank distance plus
second-rank margin, classifies the local suit palette, and requires three distinct frames and
physical uniqueness. Enrolled artifacts store only 18-by-26 masks and source hashes. Enrollment
self-matches and visually checked live examples are calibration evidence, not held-out accuracy.
Single-frame diagnostics may expose that fixed-size derived rank mask so a visually labeled
authorized frame can be enrolled before it changes. This is calibration metadata only—not raw
card/table pixels, a canonical observation, or held-out accuracy evidence.

The same privacy-scoped rule crop supplies native small/big blind candidates. Both values must parse
with `0 < SB < BB` and repeat for three distinct frames. Until that consensus passes, native stacks,
commitments, and pots remain unnormalized and cannot enter BB-based range, equity, or EV logic.
Blind-token confidence is tracked independently from Bomb-Pot/mode confidence so unrelated OCR
damage cannot suppress a clear blind value or make an ambiguous hand mode appear supported.

A live hand epoch is not a canonical hand boundary by itself. On a stable postflop-to-zero board
transition, the observer snapshots the prior dealer and active-seat set, clears dealer consensus,
then requires three fresh frames showing the button on the next dealt seat with an unchanged ring.
The old marker remains pending; a skipped dealer or changed ring is rejected. An observer that began
mid-hand must wait for this witnessed boundary before constructing a canonical initial state.
The prior epoch uses its last accepted dealer/ring evidence, so a transient result overlay at the
board reset cannot erase established context; current-frame outputs still clear while occluded.

The live status combines these prerequisites into an explicit reducer-readiness result. Every
unresolved boundary, mode, blind, dealer, ring, starting/current stack, card, amount, pot, or
clockwise-order gate is listed, and only action IDs passing all provisional reconciliation layers
are eligible. A validated standard-hand boundary snapshots pre-blind starting stacks. When every
gate passes, the observer builds deterministic canonical events and feeds the entire prefix through
the existing hand-state reducer; exact current stack and pot agreement is mandatory. A rejected
prefix is exposed with its reducer error and remains non-canonical. This path never enables control.
Direct-flop Bomb Pot boundaries still fail closed because their initial forced contributions and
pre-contribution stacks have not yet been reconstructed exactly.

Fast-changing pot labels may produce a lower-trust transition from two consecutive 0.95+ OCR
observations even when neither value repeats three times. That transition remains non-canonical and
is eligible only for exact cross-signal reconciliation with a stable action badge and same-seat stack
decrease. A later three-frame endpoint result upgrades the candidate instead of duplicating it.

Dealer-button detection now uses the calibrated X-Poker white-marker component geometry and maps a
single candidate to the nearest versioned seat anchor. Three distinct frames are required before a
dealer seat is exposed. The detector fails closed when the marker is absent or non-unique; position
assignment still waits for a validated hand boundary and active-seat set.

Seat participation now reaches independent temporal consensus for seated, open, and Break states.
Position naming is available only when every configured 6-max or 9-max seat is actively dealt; a
partial ring exposes its active-seat indexes but does not silently substitute a different position
or range set. Stable stack decreases are retained as bounded native-chip candidates with hand epoch,
street, seat, before/after values, and provenance hash. They remain outside canonical state until a
same-seat legal action and pot change reconcile.

Action badges are armed independently per seat, preventing a lingering badge elsewhere on the table
from suppressing a new action. The seat-status pass uses row/column prefix sums and measured about
68 ms per authorized portrait frame versus about 692 ms before optimization. Amount-bearing actions
are paired only with a mutually unique same-seat stack decrease within eight frames, the same hand
epoch, and a compatible street. Shared matches remain ambiguous, missing matches remain pending,
and fold/check are explicitly amount-free. Live play produced six such provisional matches across
three hand epochs with zero capture failures; legal order and pot accounting still block canonical
event promotion.

Every derived action also snapshots the accepted dealer and active-seat context. A deterministic
validator checks a gap-free clockwise prefix from the first legal preflop or postflop seat, removing
folded and all-in seats from the remaining ring. Unobserved intervening actions remain pending and a
context change within one street is inconsistent; neither case is repaired by inference. Badge-clear
rearming uses a bounded per-hand occurrence ordinal, so the same seat may legally produce the same
action type more than once on one street without duplicate event IDs.

Stable pot increases now form a separate bounded candidate stream. A wager passes the provisional
accounting layer only when its mutually unique stack decrease equals a mutually unique pot increase
from the same hand epoch, compatible street, and eight-frame window. A nearby unequal increase is a
mismatch, missing evidence remains pending, and an ambiguous pot crop clears the accepted baseline
so the system cannot bridge an unobserved interval. These results remain non-canonical until the
full legal reducer can reproduce the street totals and resulting pot.

### Milestone 9 — Authorized control

- Add action-target mapping and calibration.
- Add arming, emergency stop, stable-state gating, and duplicate prevention.
- Add action execution and post-click verification.
- Run exclusively against the authorized private test table.

**Exit criterion:** A controlled test suite completes supported simulated and authorized test hands with verified actions and no duplicate inputs.

### Milestone 10 — Hardening and demonstration

- Improve unsupported-state handling.
- Package the Windows runtime.
- Create a reproducible hackathon demonstration.
- Document installation, configuration, architecture, limitations, and evaluation results.

**Exit criterion:** A new authorized test machine can install and reproduce the demonstration from documented steps.

## 15. Primary Risks and Mitigations

| Risk | Mitigation |
|---|---|
| Public video frames differ from the installed X-Poker version | Use them for bootstrapping, then automatically calibrate against the authorized running instance |
| OCR silently reads the wrong amount | Temporal consensus, pot accounting, format validation, and confidence gating |
| A visually correct frame produces an illegal hand state | Poker-rule state machine rejects impossible transitions |
| Nearest GTO solution is materially different | Report abstraction distance and reduce confidence |
| Exploit model overreacts to a small sample | Bayesian priors, confidence intervals, and capped deviations |
| Mixed strategy cannot be reproduced during debugging | Seeded randomization and complete decision logs |
| External strategy material is mistaken for authoritative data | Provenance, source classification, and solver validation |
| Open-source license contamination | Maintain a license registry and use clean-room reimplementation where appropriate |
| X-Poker theme or layout changes | Versioned layout profiles and automated calibration |
| Duplicate or incorrect control input | Stable-frame gating, idempotency token, action verification, and emergency stop |

## 16. Definition of the First Useful Version

The first useful version will:

1. Detect the authorized X-Poker window.
2. Support explicitly classified six-max and nine-max NLH table layouts.
3. Recognize hero cards, board, seats, positions, stacks, bets, pot, and available actions.
4. Reconstruct complete hands.
5. Display recognition confidence and replay evidence.
6. Show hero and estimated opponent ranges.
7. Calculate equity, EV, and pot odds.
8. Produce source-backed GTO and confidence-scaled exploitative recommendations.
9. Log every observation and decision.
10. Keep control disabled until all required acceptance thresholds are satisfied.

## 17. Build Order

The recommended execution order is:

```text
Project foundation
→ autonomous research
→ capture and calibration
→ visual recognition
→ hand reconstruction
→ range engine
→ poker mathematics
→ GTO strategy
→ exploitative strategy
→ monitoring dashboard
→ authorized control
→ hardening and packaging
```

This sequence keeps each layer independently testable and prevents a strategy or control error from hiding a perception failure.
