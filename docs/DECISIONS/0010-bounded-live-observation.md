# Decision 0010 — Bounded continuous live observation

## Status

Accepted on 2026-08-24.

## Decision

Run authorized live diagnostics through one in-memory observation service rather than independent
unbounded capture jobs. The service keeps only the latest frame and 30 mode samples, serializes
capture, locks the initial target fingerprint, and exposes explicit start, stop, status, latest
diagnostic, and latest-frame endpoints.

Stop automatically when the target fingerprint changes or after three consecutive capture
failures. Never accept `ambiguous` as temporal mode consensus. Keep controller availability false.

## Consequences

- The dashboard shows capture freshness, frame/failure counts, target stability, mode consensus,
  nine-max occupancy, and board geometry.
- Identical content hashes do not count as independent temporal evidence.
- A rule OCR ambiguity, unsupported board, or mid-hand start remains visible but cannot initialize
  a reconstructed hand.
- The loop intentionally stores no raw frames. Explicit ignored replay capture remains the route for
  permitted offline regression evidence.
- This is the live evidence transport checkpoint, not completed-hand reconstruction promotion.
