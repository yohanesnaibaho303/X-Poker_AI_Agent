# ADR 0003: X-Poker-only runtime scope

- Status: Accepted
- Date: 2026-08-24

## Context

PokerStars, GGPoker, PokerGPT, and `dickreuter/Poker` appear in research because they provide public examples of poker-agent architecture, visual mapping, poker rules, and monitoring. They are not requested runtime targets.

## Decision

The application supports only X-Poker for the current project. Runtime process detection, layout profiles, visual models, calibration, state evidence, testing, and eventual authorized control will be X-Poker-specific.

Other poker applications and repositories may be used only as clearly labeled architectural, rules, mathematical, or interface references. Their layouts, assumptions, ranges, strategies, and control mappings cannot be silently imported or treated as X-Poker-compatible.

## Consequences

- Milestone 2 window discovery will allowlist X-Poker and explicitly configured X-Poker emulator instances only.
- The component catalog and future recognition datasets must identify X-Poker provenance.
- No engineering time is allocated to PokerStars, GGPoker, or generic multi-client adapters.
- General poker rules and deterministic mathematics remain reusable domain logic, but observed UI state is always X-Poker-specific.
