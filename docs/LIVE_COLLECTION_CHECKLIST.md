# Automated Live Collection Checklist — Milestone 3 Holdout

- Target Gate: Milestone 3 Holdout Promotion (Exit Criteria)
- Progress: 4/6 gates satisfied (66.7%)

## Real-Time Collection Checklist

During live authorized sessions, frames are automatically indexed and matched against
the remaining criteria without requiring manual screenshot sorting or labeling.

### [ ] card_recognition: cards_52_coverage
- **Description**: Evidence for all 52 card rank/suit combinations across hero and board
- **Status**: PENDING
- **Observed**: 42/52
- **Target Missing Evidence**: `3d, 4c, 4d, 4h, 4s, 7s, 9s, Td, Th, Jh`

### [ ] dealer_detection: dealer_button_9_seats
- **Description**: Dealer button observation for all 9 seats (0-8)
- **Status**: PENDING
- **Observed**: 8/9
- **Target Missing Evidence**: `seat_2`

### [x] seat_occupancy: seat_occupancy_9_seats
- **Description**: Occupied and empty observations for all 9 seats
- **Status**: SATISFIED
- **Observed**: 9/9

### [x] numeric_ocr: numeric_pot_stack_blinds
- **Description**: Native chips OCR proof for pot, blind posts, and starting/active stacks
- **Status**: SATISFIED
- **Observed**: 3/3

### [x] action_control: action_control_states
- **Description**: Pre-action, decision (Fold/Call/Raise and Check/Bet), and ambiguous overlay evidence
- **Status**: SATISFIED
- **Observed**: 3/3

### [x] performance: latency_p95_decision_window
- **Description**: End-to-end recognition diagnostic latency p95 <= 200 ms
- **Status**: SATISFIED
- **Observed**: 1/1

## Automated Session Ingestion Command

When a new live session or recording is captured, run:

```powershell
.\.venv\Scripts\python.exe scripts\live_collection_checklist.py --incoming <session_dir_or_status_json>
```

This will instantly report which missing items were captured without manual organization.
