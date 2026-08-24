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
seats: 9
rake: 0
default_open_size_bb: 2.0
objective: chip_ev
```

`2 BB` means the default preflop open size. Detect effective stack depth dynamically.

Use these nine-max positions:

```text
UTG, UTG+1, MP, LJ, HJ, CO, BTN, SB, BB
```

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
- Never silently substitute six-max, tournament, raked, or non-2-BB ranges for the initial configuration.
- When an exact strategy solution is unavailable, report the nearest abstraction and quantify the mismatch.
- Preserve unrelated user changes in the worktree.

## Documentation

- Keep `docs/PROJECT_PLAN.md` as the primary project plan.
- Update the plan when requirements or milestones materially change.
- Document commands, dependencies, supported layouts, data provenance, model versions, limitations, and evaluation results.
- Keep a short decision record for major architecture or licensing choices.
