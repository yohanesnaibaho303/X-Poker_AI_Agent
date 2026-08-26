# Decision 0016 — Owner-authorized GTOpen generation

Date: 2026-08-26

## Decision

Use GTOpen externally to generate private educational preflop strategy evidence. The user attested
direct permission from repository owner Matthew PDingle. Pin every import to the upstream commit,
hash every generated artifact, and retain the authorization statement in provenance.

Owner authorization permits copying or distributing GTOpen source code and binaries for this
private educational project. Reuse only portions that materially reduce development or runtime
cost, preserve upstream attribution and the pinned commit, and avoid vendoring code that the
external generator already provides cleanly. Supply native values directly to the generator:
SB 1, BB 2, stack 200, pot 3, and raise to 4.

## Accuracy boundary

GTOpen's multiway preflop solver uses 169 hand classes, pairwise-equity approximation, and a modeled
postflop terminal value. Expand each class uniformly to its exact physical combinations, but record
that expansion and model boundary on every artifact.

All GTOpen resolver matches are `abstracted`, never `exact`. Confidence is capped at 0.35. Equity
and per-action EV remain unavailable when absent from the source node response.
