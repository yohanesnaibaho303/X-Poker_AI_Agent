# Initial Open-Source Repository Findings

These notes are clean-room architectural observations. They do not copy implementation code and do not validate any repository's strategy logic for this project's authoritative 6-max or 9-max cash NLH, zero-rake, 2 BB configurations.

## PokerGPT

- Registry source: `00000000-0000-0000-0000-000000000103`
- Repository: `https://github.com/HarperJonesGPT/PokerGPT`
- License: MIT
- Observed target: fixed six-player PokerStars cash table on Windows

### Useful architectural observations

- Screen reading, current game state, hero information, action selection, action execution, and monitoring UI are represented as recognizable responsibilities.
- The project combines pixel-region reading with Tesseract OCR for cards, amounts, dealer marker, and player actions.
- It exposes observed state through a GUI and keeps mouse execution in a distinguishable action component.
- Its documented limitations show the cost of fixed window size, resolution, and exact visual setup.

### Boundaries for this project

- Do not inherit its six-player assumptions, PokerStars geometry, strategy prompts, or language-model-led decisions.
- Use its module list only as corroboration for separating perception, state, monitoring, and action.
- Any later MIT-code reuse requires attribution, review, tests, and confirmation that deterministic alternatives are not preferable.
- X-Poker calibration must tolerate supported DPI/window changes rather than requiring one hard-coded screen arrangement.

## dickreuter/Poker

- Registry source: `00000000-0000-0000-0000-000000000104`
- Repository: `https://github.com/dickreuter/Poker`
- License: GPL-3.0
- Observed targets: PokerStars, PartyPoker, GGPoker, and user-mapped tables on Windows

### Useful architectural observations

- Table layouts can be represented by configurable templates and search regions rather than one global pixel map.
- The documented mapping workflow uses anchors, cropped regions, per-component templates, and many screenshots.
- The repository combines OpenCV recognition, optional neural recognition, data augmentation, Monte Carlo equity, editable strategy parameters, and result analysis.
- Its operating notes highlight DPI scaling, visibility, window interference, CPU/OCR cost, and the danger of testing control before correct operation is verified.

### Boundaries for this project

- No GPL implementation code, templates, models, or derived source will be incorporated unless a separate compatible-licensing ADR is accepted.
- Implement layout profiles, calibration, recognition, poker math, and control gating independently from requirements and public behavior.
- Do not inherit heuristic/genetic strategy as GTO truth.
- Improve on manual mapping by bootstrapping from public material and calibrating against the authorized running instance.
- Keep capture/perception evaluation separate from action control and require replay gates before any authorized live test.

## Resulting design decisions

1. Preserve the existing strict module split and typed observation/state boundary.
2. Use versioned normalized layout profiles with anchors and component-specific regions.
3. Benchmark specialized OCR and templates before adding learned inference.
4. Store raw evidence references and component/model versions with every observation.
5. Keep strategy numerical sources independent from perception repositories.
6. Keep the controller absent until later milestones; recommendations never imply permission to act.

## preflopR

- Registry source: `00000000-0000-0000-0000-000000000114`
- Repository: `https://github.com/bmorrow10/preflopR`
- Pinned commit: `aed511d0451aea33a14f7e9204595fc2211f233f`
- License: MIT
- Coverage used: 6-player and 9-player unopened raise/fold reference charts

### Boundaries for this project

- Upstream explicitly describes the charts as approximate guidelines and not solver-derived.
- Upstream does not establish stack depth, rake, or open sizing; project target metadata is an
  indexing assumption and not a claim about the upstream chart.
- Imported artifacts have `strategy_role=reference_prior` and confidence 0.55.
- These priors may initialize range displays and opponent priors but must never be labeled exact GTO.
- Milestone 6 still requires generated, licensed, or authorized configuration-matched solutions.
