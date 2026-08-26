# AGENTS.md

## Project

This repository contains the X-Poker AI Agent hackathon project. Read `docs/PROJECT_PLAN.md` before making architectural or implementation changes.

## Objective

Build an inspectable Windows-based AI agent for an authorized private X-Poker test table. The system will research public references, recognize the X-Poker interface, reconstruct NLH hands, maintain weighted ranges, calculate GTO and exploitative strategies, display live monitoring, and interact with the authorized test environment after its safety and accuracy gates pass.

## Initial Game Configuration

Treat the following configuration as authoritative unless the user explicitly changes it:

```yaml
variant: NLH
format: cash
supported_seats: [9]
rake: 0
native_small_blind: 1
native_big_blind: 2
objective: chip_ev
supported_hand_modes: [standard_nlh, single_board_bomb_pot]
```

All amounts are represented and displayed in native chips. Authoritative blinds are SB 1 and BB 2.
The 2-chip big blind is a forced blind, not a preflop opening raise. Detect effective stack depth
dynamically in native chips.

Single-board X-Poker NLH Bomb Pot is supported as a distinct per-hand mode. Detect scheduled versus
active Bomb Pot state visually. In an active Bomb Pot hand, every participating player makes an
observed forced contribution, preflop betting is skipped, and normal NLH action begins on the flop.
Never infer the contribution from a table-label range: reconstruct it from observed commitments,
stack deltas, and pot accounting. Double-board, Omaha, ambiguous board count, or uncertain forced
contributions remain unsupported and fail closed.

Use this position order:

```text
9-max: UTG, UTG+1, UTG+2, LJ, HJ, CO, BTN, SB, BB
```

Nine-max is the only supported table size. Retired 6-max profiles, fixtures, ranges, controls, and
documentation must not be loaded or presented as supported behavior.

The final session setup has no table-size or unit selector: it uses 9-max and native chips only.
Native chips remain exact internally and always display as exact grouped numbers (for example
`10,000`, `200,000`, or `1,000,000`). Never abbreviate values as K or M. Never convert native chips
to BB for storage, strategy, calculation, or display.

## Working Principles

- Use `NLH`, not `NLHE`, in project-facing terminology.
- Keep perception, state reconstruction, ranges, poker math, strategy, monitoring, and control as separate modules.
- Prefer deterministic code for poker rules, arithmetic, equity, EV, state validation, and control gating.
- Use language models for research, classification, synthesis, explanations, and bounded orchestration; do not make a language model the sole source of numerical strategy or observed game state.
- Treat weighted ranges as structured combination-level data, not prose embedded in prompts.
- Attach confidence, assumptions, configuration, and provenance to observations and strategy results.
- Preserve raw evidence or replay references for debugging recognition and state errors.
- Fail closed on ambiguous cards, amounts, actions, table identity, or unsupported states.
- Do not enable table control until the acceptance thresholds in the project plan pass.
- Scope active interaction to the explicitly authorized private test environment.
- Do not use mutable club-room titles as the primary window identity. Gate capture with the
  allowlisted X-Poker executable hash, process, window class, supported geometry, and visual table
  role; use PID/HWND only as session-scoped evidence.

## Research and External Sources

- The user does not want to curate screenshots or explain the X-Poker interface manually.
- Autonomously research public videos, accessible transcripts, articles, screenshots, and repositories.
- Use public material to bootstrap the component catalog, then calibrate automatically against the authorized running instance.
- Record the URL, source type, license, intended use, and confidence for every external asset or strategy source.
- Distinguish poker rules, mathematical facts, solver-derived results, heuristics, and player opinions.
- Do not treat YouTube advice or language-model output as validated GTO strategy.
- Do not assume proprietary GTO Wizard solution data is available for extraction. Use legitimate APIs, authorized exports, licensed data, or independently generated solver output.

Initial references:

- `https://app.gtowizard.com/`
- `https://github.com/HarperJonesGPT/PokerGPT`
- `https://github.com/dickreuter/Poker`

PokerGPT is MIT-licensed. `dickreuter/Poker` is GPL-3.0; avoid directly incorporating GPL code unless the project deliberately adopts compatible licensing. Architectural study and clean-room implementation are preferred.

## Implementation Order

Follow this default sequence:

1. Project foundation and schemas.
2. Autonomous research and provenance catalog.
3. X-Poker window capture and layout calibration.
4. Visual recognition and OCR.
5. NLH hand-state reconstruction.
6. Weighted range engine.
7. Deterministic poker mathematics.
8. GTO solution integration and abstraction.
9. Exploitative opponent modeling.
10. Monitoring dashboard.
11. Authorized control with verification.
12. Hardening, evaluation, and packaging.

Do not skip directly to automated control before perception and state reconstruction are independently reliable.

## Quality Requirements

- Add tests with each implementation change.
- Use recorded replay tests before live authorized tests.
- Keep solver/range configuration versioned and reproducible.
- Use seeded randomness for mixed strategies during tests.
- Log every proposed and executed action with its state, confidence, strategy source, random seed, target, and verification result.
- Never silently substitute six-max, tournament, raked, BB-normalized, or wrong-blind ranges for
  the initial 9-max, native-chip, 1/2 configuration.
- When an exact strategy solution is unavailable, report the nearest abstraction and quantify the mismatch.
- Preserve unrelated user changes in the worktree.

## Documentation

- Keep `docs/PROJECT_PLAN.md` as the primary project plan.
- Update the plan when requirements or milestones materially change.
- Document commands, dependencies, supported layouts, data provenance, model versions, limitations, and evaluation results.
- Keep a short decision record for major architecture or licensing choices.
