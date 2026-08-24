# Research Acquisition and Provenance Policy

## Purpose

Public research bootstraps the X-Poker component catalog and poker knowledge base. It does not replace calibration against the explicitly authorized running instance, establish asset-reuse rights, or turn educational claims into validated strategy data.

## Source record requirements

Every source must be registered before a retained derivative is used. Required fields are URL, source type, title/publisher, access date, license or unknown-license status, intended use, fact classification, confidence, and notes. Registry loading rejects malformed records and duplicate IDs or URLs.

## Permitted source classes

- Official X-Poker listings, documentation, public pages, and public support material.
- Publicly accessible videos, transcripts, articles, screenshots, and reviews.
- Open-source repositories with verified license metadata.
- Authoritative NLH rules and mathematical references.
- Properly licensed solver output, independently generated solutions, legitimate APIs, or user-authorized exports.

Public accessibility does not imply permission to redistribute an asset. Store metadata and links by default. Retain frames, transcript excerpts, or other derivatives only when their use is permitted and necessary; record the relevant license/use basis and content hash.

## Acquisition workflow

1. Register the source and classify its intended use.
2. Check access restrictions, license, robots/site terms where applicable, and whether an official API/export exists.
3. Capture metadata before content processing.
4. Extract only the minimum material needed for component research.
5. Hash retained artifacts and link them to their source record.
6. Deduplicate before dataset splitting.
7. Label version, layout, theme, orientation, game type, street, visible components, and confidence.
8. Quarantine uncertain-license assets from training and redistribution.

Do not bypass authentication, paywalls, technical restrictions, or access controls. Do not assume GTO Wizard solution data is extractable. Do not collect unrelated personal, account, club, or financial information.

## Fact classification

- `rule`: rules from an authoritative rules source.
- `mathematical_fact`: independently reproducible arithmetic or theorem.
- `solver_derived`: output tied to exact solver configuration and artifact provenance.
- `heuristic`: advice or approximation not established as exact strategy.
- `player_opinion`: subjective experience or claim.
- `interface_observation`: visible application structure or behavior.

YouTube advice, reviews, articles, and language-model synthesis may provide hypotheses or interface evidence but are not validated numerical GTO strategy.

## License boundaries

- PokerGPT: MIT; attribution and license obligations apply to any reused code.
- `dickreuter/Poker`: GPL-3.0; architecture may be studied, but direct code reuse is prohibited unless a separate compatible-license decision is accepted.
- GTO Wizard: proprietary reference-only by default; use numerical data only through legitimate authorized access/export with recorded configuration.
- X-Poker imagery and UI assets: presumed proprietary unless an explicit license states otherwise; use minimal research derivatives and do not redistribute by default.

## Promotion to datasets or strategy artifacts

A source record alone does not authorize model training or numerical strategy use. Promotion requires a reviewed asset manifest, license/use basis, content hashes, dataset split, intended component, and evaluation plan. Strategy promotion additionally requires exact game configuration and independent validation.
