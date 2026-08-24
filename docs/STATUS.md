# Build Status

- Last updated: 2026-08-24 (Asia/Jakarta)
- Current milestone: Milestone 2 — Window capture and calibration
- Overall project: 2 of 11 milestones complete
- Current state: Milestone 1 complete; Milestone 2 ready
- Live control: Disabled

## In progress

- X-Poker-only Windows process/window discovery design.
- Authorized-target profile and fail-closed identity requirements.

## Completed in this milestone

- Confirmed bundled Python 3.12.13 and Node.js runtimes.
- Defined architecture, system design, canonical schemas, milestones, quality gates, and initial ADRs.
- Created the pinned Python project and explicit domain package boundaries.
- Implemented strict configuration and schema models with exported JSON Schemas.
- Implemented exact-decimal structured logging and deterministic hand reconstruction.
- Replayed a simulated NLH hand from waiting state through completion.
- Passed Ruff and 23 Pytest/Hypothesis tests.
- Smoke-tested the local API and verified controller availability remains false.
- Milestone 0 suite: Ruff passed; 25 Pytest/Hypothesis tests passed.
- Implemented the validated, hash-addressed source registry and research acquisition policy.
- Registered the official X-Poker listing, GTO Wizard, PokerGPT, and `dickreuter/Poker` with license/use boundaries.
- Documented clean-room architectural findings for PokerGPT and `dickreuter/Poker`.
- Current full suite: Ruff passed; 36 Pytest/Hypothesis tests passed.
- Added a 12-component provenance-linked catalog; official version 1.12.0 iPhone/iPad screenshots provide representative evidence for every critical component.
- Registered the first public X-Poker setup video; transcript/frame inspection remains pending because retrieval was throttled.
- Added a provenance-linked asset manifest with explicit retention and license-review states.
- Added authoritative NLH rules and GTO interface/educational references without treating them as solution data.

## Next

- Implement X-Poker-only Windows window enumeration and authorized-target profiles.
- Add capture diagnostics without recording unrelated screen regions.
- Ask the user to start the authorized X-Poker instance when live calibration becomes necessary.

## Blockers

- None.

This file is updated at meaningful checkpoints. The detailed checklist remains in `docs/MILESTONES.md`.
