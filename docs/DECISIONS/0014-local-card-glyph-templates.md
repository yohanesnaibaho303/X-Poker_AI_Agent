# Decision 0014 — Local X-Poker card-glyph templates

## Status

Accepted as a calibration candidate on 2026-08-24.

## Decision

Use a dependency-free local template matcher as the first X-Poker board-card candidate. Reduce
authorized card-only crops to versioned 18-by-26 binary rank masks and discard the crop. Store only
the mask, source-frame SHA-256, slot, provenance, intended use, and license boundary. Determine suit
from X-Poker's observed black/red/blue/green palette.

Require a bounded rank distance, a margin over the second-best rank, deterministic suit confidence,
three distinct stable frames per slot, and physical-card uniqueness. Any failed sub-gate returns an
unknown card. Do not use this artifact as evidence that the card-accuracy promotion threshold has
passed.

## Consequences

- Runtime recognition adds no OpenCV, neural-runtime, or remote-image dependency.
- The artifact contains no raw table pixels or player identity data.
- New visual variants can be added with explicit hashed provenance and replay evaluation.
- A held-out labeled rank/suit dataset remains mandatory before M3 promotion or control eligibility.
