# Milestone 3 Vision Foundation Checkpoint

## Scope

This checkpoint covers dependency-free image primitives and safety validation. It is not a
Milestone 3 promotion report and does not claim card or OCR quality-gate accuracy.

## Versioned implementation

- Capture input: canonical X-Poker BGRA8 frames, layout `xpoker-windows-10-portrait-v1`.
- Image primitives: pure Python; no Pillow, OpenCV, Tesseract, ONNX Runtime, or model assets.
- OCR candidate: local Windows Media OCR through narrowly scoped Python WinRT projections.
- Implemented: declared-region crops, top-down pixel boxes, bright-neutral masks, connected
  components, card-surface geometry, board-row grouping, strict chip-number parsing, duplicate-card
  rejection, and content-hash-deduplicated temporal consensus.
- Raw authorized frames remain Git-ignored and are not part of the repository.

## Evidence

Synthetic regression suite:

- One standard board row is accepted by geometry.
- Multiple credible board rows and more than five slots in one row are rejected.
- Duplicate physical card codes are rejected.
- Malformed and ambiguous chip formats are rejected.
- Three independent stable frames can form consensus; repeated identical content cannot inflate
  the stable-frame count.

Local authorized replay audit:

- Dataset: `xpoker-capture-20260824T041923.313808Z` (five private, ignored frames).
- The table displays a Bomb Pot configuration label but no multiple boards are dealt in this replay.
- The board crop yielded zero card-surface candidates. A broad table-surface scan yielded one
  unrelated card-shaped UI component per frame.
- Privacy-scoped 335×75 rule-label crops scaled to 1340×300 produced damaged but usable text
  containing the distinctive `Pot: After ... hands` schedule in all five frames, with 16.1 ms median
  OCR latency.
- The deterministic rule classifier mapped all five frames to unsupported Bomb Pot configuration
  with 0.93 confidence. Unknown label text also remains unsupported and never proves standard NLH.
- Exploratory pot OCR took approximately 4-10 ms, but crop/scale variants alternated among the
  correct `81,500` and unsafe results such as `815500` and `813500`. The candidate is not promoted
  for numeric values; exact parsing would reject label-bearing and malformed output in this stage.
- Conclusion: multi-board geometry is a valid secondary rejection signal after cards are visible;
  rule-label recognition provides the earlier fail-closed signal. A larger held-out set is still
  required before promotion.

## Performance sample

Command environment: project Python 3.12 virtual environment on the authorized development
machine. Dataset: generated 200×200 BGRA fixture containing 11 slots across three rows. Twenty
iterations of mask, components, slot filtering, row assignment, and classification:

| Metric | Result |
|---|---:|
| Median | 36.041 ms |
| p95 | 37.765 ms |
| Maximum | 37.954 ms |

This is an engineering sample, not the final 445×800 perception latency gate. Region cropping is
required before running the primitive to keep the full pipeline within the 200 ms p95 budget.

## Next evaluation work

- Define privacy-safe labeled X-Poker crops for cards, amounts, seats, actions, and rule labels.
- Benchmark template recognition against the provisional Windows OCR candidate on numeric crops.
- Expand Bomb Pot/rule-label evaluation beyond the single private calibration replay.
- Freeze train/calibration/validation/holdout partitions by content hash before reporting accuracy.
