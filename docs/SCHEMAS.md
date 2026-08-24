# Canonical Schemas

## 1. Conventions

- Schemas are versioned and validated at every module boundary.
- IDs use UUIDs; timestamps use UTC RFC 3339; frame ordering uses monotonic sequence numbers.
- Monetary values are stored as exact decimal strings plus normalized BB values where appropriate, never binary floats for accounting.
- Cards use rank plus lowercase suit: `As`, `Td`, `7h`, `2c`.
- Positions are `UTG`, `UTG+1`, `MP`, `LJ`, `HJ`, `CO`, `BTN`, `SB`, `BB`.
- Confidence is in `[0, 1]` and includes a method or calibration version.
- Every derived record identifies input IDs, configuration versions, and producer version.
- Examples are illustrative; implementation should use typed models and generated JSON Schema.

## 2. Shared records

### EvidenceRef

```json
{
  "evidence_id": "uuid",
  "frame_id": "uuid",
  "frame_sequence": 18422,
  "captured_at": "2026-08-24T10:15:30.123Z",
  "artifact_path": "data/frames/...",
  "content_sha256": "hex",
  "region_xywh": [0.10, 0.20, 0.15, 0.08]
}
```

### Confidence

```json
{
  "score": 0.997,
  "calibration_id": "card-rank-v1",
  "alternatives": [{"value": "Ks", "score": 0.002}],
  "stable_frames": 4
}
```

### Provenance

```json
{
  "source_id": "uuid",
  "url": "https://example.invalid/source",
  "source_type": "video",
  "title": "Example",
  "publisher": "Example publisher",
  "published_at": null,
  "accessed_at": "2026-08-24T10:00:00Z",
  "license": "unknown",
  "license_url": null,
  "intended_use": "interface research only",
  "fact_class": "heuristic",
  "confidence": 0.6,
  "notes": "Not validated strategy data"
}
```

`fact_class` is one of `rule`, `mathematical_fact`, `solver_derived`, `heuristic`, `player_opinion`, or `interface_observation`.

## 3. Configuration

### GameConfig

```json
{
  "schema_version": "1.0",
  "variant": "NLH",
  "format": "cash",
  "seats": 9,
  "rake": {"kind": "none", "percent": "0", "cap_bb": "0"},
  "default_open_size_bb": "2.0",
  "objective": "chip_ev",
  "positions": ["UTG", "UTG+1", "MP", "LJ", "HJ", "CO", "BTN", "SB", "BB"],
  "enabled_special_rules": []
}
```

### RuntimeConfig

Contains mode, capture rate bounds, evidence retention, confidence thresholds, component versions, database path, API binding, and controller policy. Authorization secrets or machine-specific identifiers must be stored in an ignored local override.

## 4. Observation layer

### Observation

```json
{
  "schema_version": "1.0",
  "observation_id": "uuid",
  "kind": "stack_amount",
  "subject": {"seat": 4},
  "value": {"amount": "98.50", "unit": "BB"},
  "confidence": {"score": 0.994, "calibration_id": "numeric-ocr-v1", "stable_frames": 3},
  "evidence": ["evidence-id"],
  "layout_version": "xpoker-layout-v1",
  "producer": {"component": "vision", "version": "0.1.0"}
}
```

Observation kinds include table bounds, seat occupancy, player label, stack, current bet, pot, card, dealer marker, active seat, timer, available action, sizing control, street marker, and status state.

### ObservationBatch

Groups observations from a frame sequence and carries target identity, capture metadata, processing latency, and health flags. It is immutable after publication.

## 5. Event and state layer

### HandEvent

```json
{
  "schema_version": "1.0",
  "event_id": "uuid",
  "hand_id": "uuid",
  "sequence": 12,
  "type": "PLAYER_RAISED",
  "actor_seat": 6,
  "street": "preflop",
  "amount": {"to_bb": "6.0", "added_bb": "4.0"},
  "input_observations": ["uuid"],
  "confidence": {"score": 0.998, "calibration_id": "state-v1", "stable_frames": 3},
  "assumptions": []
}
```

Event types follow the canonical list in `docs/PROJECT_PLAN.md`. Events are append-only. Corrections create a new reconstruction version rather than altering an audited history.

### SeatState

Contains seat index, occupancy, player/profile reference, derived position, starting stack, current stack, committed amounts by street, status, cards if legitimately revealed, and field-level evidence/confidence.

### HandState

```json
{
  "schema_version": "1.0",
  "state_id": "uuid",
  "hand_id": "uuid",
  "revision": 8,
  "config_version": "game-9max-nlh-v1",
  "street": "flop",
  "dealer_seat": 3,
  "hero_seat": 3,
  "hero_position": "BTN",
  "hero_cards": ["As", "Kd"],
  "board": ["Qs", "Jh", "2c"],
  "seats": [],
  "pot": {"main_bb": "9.5", "side_pots": [], "accounting_delta_bb": "0"},
  "effective_stacks_bb": {"3:7": "96.0"},
  "available_actions": ["fold", "call", "raise"],
  "event_ids": [],
  "validation": {"legal": true, "issues": []},
  "confidence": {"overall": 0.996, "critical_min": 0.994},
  "evidence": []
}
```

Critical confidence is calculated from cards, amounts, table identity, actor, action, and controls; it is not a simple average that can hide one unsafe field.

## 6. Range layer

### WeightedRange

```json
{
  "schema_version": "1.0",
  "range_id": "uuid",
  "player_ref": "seat:7",
  "hand_id": "uuid",
  "street": "flop",
  "spot_key": "BTN_vs_BB_SRP_100BB",
  "combos": {
    "AsKs": {
      "weight": 1.0,
      "actions": {"check": 0.28, "bet_33": 0.72},
      "equity": 0.61,
      "ev_bb": {"check": 8.12, "bet_33": 8.26}
    }
  },
  "blocked_cards": ["Qs", "Jh", "2c"],
  "source": {"kind": "validated_solution", "artifact_id": "uuid"},
  "assumptions": [],
  "confidence": 0.92,
  "version": "range-model-v1"
}
```

Canonical combo keys sort physical cards deterministically. Illegal or blocked combinations must be absent or carry zero weight. Action frequencies for each represented combo sum to one within a declared tolerance.

## 7. Calculation and strategy layer

### CalculationResult

Records calculation kind, exact inputs, result, algorithm (`exact` or `monte_carlo`), sample count, seed where applicable, error/convergence estimate, duration, and implementation version.

### StrategyMatch

```json
{
  "schema_version": "1.0",
  "match_id": "uuid",
  "status": "abstracted",
  "requested_spot": {},
  "matched_spot": {},
  "distance": {
    "stack_bb": 4.0,
    "open_size_bb": 0.0,
    "pot_geometry": 0.03,
    "unsupported_dimensions": []
  },
  "source_artifact_id": "uuid",
  "confidence": 0.84,
  "assumptions": ["Used 100 BB solution for observed 96 BB effective stack"]
}
```

### DecisionEnvelope

```json
{
  "schema_version": "1.0",
  "decision_id": "uuid",
  "idempotency_token": "uuid",
  "state_id": "uuid",
  "state_revision": 8,
  "state_valid_until_frame": 18430,
  "mode": "recommend",
  "hero_combo": "AsKd",
  "baseline_actions": {"fold": 0.0, "call": 0.35, "raise_75": 0.65},
  "adjusted_actions": {"fold": 0.0, "call": 0.25, "raise_75": 0.75},
  "selected_action": {"type": "raise", "size_bb": "12.5"},
  "randomization": {"seed": 77123, "draw": 0.61},
  "strategy_match_id": "uuid",
  "calculations": ["uuid"],
  "confidence": {"overall": 0.91, "control_eligible": false},
  "assumptions": [],
  "created_at": "2026-08-24T10:15:30.500Z"
}
```

Control eligibility is computed independently from recommendation confidence.

## 8. Controller audit

### ActionAttempt

Records decision and token, authorization profile, preflight checks, target window fingerprint, intended control region, input timestamp, verification deadline, observed transition, outcome, evidence, and disarm reason. Outcomes include `blocked`, `executed_verified`, `executed_unverified`, and `cancelled`.

No executed attempt may be deleted or overwritten.

## 9. Compatibility policy

- Additive optional fields are backward compatible within a major schema version.
- Renames, semantic changes, new required fields, and enum removals require a new major version and migration.
- Stored artifacts retain the schema version used to produce them.
- Replay tests cover supported historical schema versions or document an explicit migration boundary.

