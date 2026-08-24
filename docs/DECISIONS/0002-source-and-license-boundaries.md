# ADR 0002: Source provenance and license boundaries

- Status: Accepted
- Date: 2026-08-24

## Context

The project will study public X-Poker material, GTO educational resources, GTO Wizard, PokerGPT, and `dickreuter/Poker`. These sources have different licenses and levels of strategic authority. Incorrect reuse could contaminate licensing or falsely present opinions and proprietary data as validated GTO solutions.

## Decision

Every external source and retained asset records URL, source type, license, intended use, access date, confidence, and fact classification. PokerGPT may be studied and reused within its MIT terms with attribution where required. `dickreuter/Poker` is treated as GPL-3.0 architectural reference only; direct GPL code incorporation requires a separate deliberate compatibility decision. GTO Wizard is a conceptual and UI reference unless legitimate APIs, licensed data, or authorized exports are available.

YouTube advice, articles, and language-model synthesis are not validated numerical GTO data. Numerical strategy must come from properly licensed precomputed solutions, independently generated solver output, compatible open-source output, authorized exports, or manually validated charts with recorded provenance.

## Consequences

- Research ingestion requires provenance and license validation from the beginning.
- Clean-room notes must separate observed ideas and requirements from copied implementation.
- Some useful sources may remain reference-only.
- Strategy results remain inspectable and cannot silently overstate authority.

## Alternatives considered

- Copying available open-source implementations regardless of license: rejected because it risks incompatible derivative licensing.
- Treating public educational content as validated GTO data: rejected because authority, configuration, and accuracy are insufficient.

