# ADR 0006 — Reference priors are not GTO solutions

- Status: Accepted
- Date: 2026-08-24

## Context

Milestone 5 needs position-specific 6-max and 9-max ranges to exercise exact-combo lookup and matrix
rendering. Public sources with matching no-rake, 2 BB, multi-player solver output were not available
under a verified reusable license. The MIT-licensed `preflopR` repository provides both table sizes,
but explicitly describes its charts as approximate and not solver-derived. It also omits stack, rake,
and opening-size configuration.

## Decision

Import the pinned charts as low-confidence `reference_prior` artifacts only. Preserve every exact
combo, provenance hash, position translation, and mismatch assumption. Never treat these artifacts
as `gto_solution` data. Require a role boundary in the range artifact schema and carry artifact
confidence into weighted ranges and matrix projections.

## Consequences

- Milestone 5 can deterministically render position-specific ranges for both table sizes.
- The application can bootstrap transparent priors without inventing or mislabeling solver output.
- Milestone 6 remains responsible for configuration-matched solver-derived strategy integration.
- BB has no unopened RFI prior because it cannot face an unopened decision after all earlier seats
  fold; its range depends on observed prior action.

## Alternatives rejected

- Relabeling approximate charts as GTO: rejected as false provenance.
- Substituting heads-up or 2.5 BB solver output: rejected as configuration-incompatible.
- Copying from proprietary chart products: rejected without authorized export or reuse terms.
