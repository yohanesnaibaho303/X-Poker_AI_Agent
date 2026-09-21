# Milestone 3 Offline Evidence Audit — 2026-09-21

## Result

The local ignored evidence archive contains 598 files totaling 744,273,756 bytes: 533 BMP files
and 65 JSON records. Content hashing found 512 unique artifacts, 20 duplicate groups, and 86
duplicate copies. No raw frames were added to version control.

Structured records expose broad calibration/regression coverage:

- all six betting actions: fold, check, call, bet, raise, and all-in;
- hero control surfaces for pre-action, decision, and ambiguous states;
- standard NLH, single-board Bomb Pot, and ambiguous hand modes;
- stack, pot, and native-blind numeric channels;
- dealer seats 0, 1, 3, 4, 5, 6, 7, and 8;
- seated/empty evidence for eight seats and seated evidence for every seat;
- 42 distinct predicted cards spanning 12 ranks and all four suits.

This is coverage inventory, not accuracy evidence. The structured predictions do not establish
ground truth.

## Reproducible regression

The documented exact-layout pre-action replay produced a 120-case action-control regression set.
All 120 frames remained `pre_action`, matching the manually observed sequence. Exact regression
accuracy is 100%, with zero false positives and zero false negatives. The report is not promotion
eligible because it is regression evidence from one known sequence. Source replay data did not
retain per-frame confidence, so the report records confidence as unavailable (`0.0`).

Total diagnostic latency for that replay is 275.0952 ms p95. Across all retained replay reports,
the best p95 is 211.0976 ms, still above the 200 ms decision-window budget.

## Evidence still required

The next authorized collection should target only these missing gates:

1. Freeze a new, unseen, content-hash-deduplicated holdout partition before calibration.
2. Label whole-card rank and suit outcomes across all 52 cards, lighting states, result overlays,
   hero, board, and showdown locations. Structured outputs currently contain no `3d`, any rank 4,
   `7s`, `9s`, `Td`, `Th`, or `Jh`; this is a coverage gap, not an error claim.
3. Label exact stack, bet, pot, and side-pot values. Existing structured summaries expose stack,
   pot, and blind channels but do not prove bet or side-pot OCR accuracy.
4. Capture dealer seat 2 and held-out occupied, empty, Break, sitting-out, disconnected, active-
   player, timer, and sizing-control states across the nine-seat layout.
5. Add held-out action-control decisions covering Fold/Call/Raise and Check/Bet equivalents,
   including negative/ambiguous states.
6. Re-run exact-layout latency after profiling until decision-window perception/state reaches
   p95 at or below 200 ms.

The held-out reports must meet 99.5% whole-card accuracy, 99.0% exact numeric accuracy, and safe
rejection requirements before Milestone 3 can exit.

## Artifacts and command

- `M3_OFFLINE_EVIDENCE_AUDIT_2026-09-21.json` — privacy-safe file/hash inventory, duplicates,
  structured coverage, latency summaries, and gate gaps.
- `M3_ACTION_CONTROL_REGRESSION_CASES_2026-09-21.json` — frozen 120-case regression input.
- `M3_ACTION_CONTROL_REGRESSION_2026-09-21.json` — existing evaluator output.

```powershell
.\.venv\Scripts\python.exe scripts\audit_m3_evidence.py data\frames `
  docs\EVALUATIONS\M3_OFFLINE_EVIDENCE_AUDIT_2026-09-21.json `
  --pre-action-replay data\frames\retained-replay-20260826T153413.json `
  --cases-output docs\EVALUATIONS\M3_ACTION_CONTROL_REGRESSION_CASES_2026-09-21.json `
  --report-output docs\EVALUATIONS\M3_ACTION_CONTROL_REGRESSION_2026-09-21.json
```

Table control remained disabled, and no live capture was used.
