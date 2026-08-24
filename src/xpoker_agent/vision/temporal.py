"""Fail-closed temporal consensus for noisy visual observations."""

from __future__ import annotations

from xpoker_agent.vision.models import TemporalConsensus, TemporalSample


def consensus(
    samples: list[TemporalSample],
    *,
    minimum_frames: int = 3,
    minimum_confidence: float = 0.9,
    minimum_margin: float = 0.2,
) -> TemporalConsensus:
    if minimum_frames < 1:
        raise ValueError("minimum_frames must be positive")
    if not samples:
        return TemporalConsensus(
            accepted=False,
            confidence=0.0,
            stable_frames=0,
            reason="no_samples",
        )
    # A repeated capture is not independent evidence and must not raise confidence.
    by_content: dict[str, TemporalSample] = {}
    for sample in samples:
        existing = by_content.get(sample.content_sha256)
        if existing is None or sample.frame_sequence > existing.frame_sequence:
            by_content[sample.content_sha256] = sample
    ordered = sorted(by_content.values(), key=lambda sample: sample.frame_sequence)
    totals: dict[str, float] = {}
    counts: dict[str, int] = {}
    for sample in ordered:
        totals[sample.value] = totals.get(sample.value, 0.0) + sample.confidence
        counts[sample.value] = counts.get(sample.value, 0) + 1
    ranking = sorted(totals, key=lambda value: (-totals[value], value))
    winner = ranking[0]
    total_weight = sum(totals.values())
    confidence = totals[winner] / total_weight if total_weight else 0.0
    runner_up = totals[ranking[1]] / total_weight if len(ranking) > 1 and total_weight else 0.0
    stable_frames = 0
    for sample in reversed(ordered):
        if sample.value != winner:
            break
        stable_frames += 1
    alternatives = ranking[1:]
    reason = None
    if counts[winner] < minimum_frames or stable_frames < minimum_frames:
        reason = "insufficient_stable_frames"
    elif confidence < minimum_confidence:
        reason = "confidence_below_threshold"
    elif confidence - runner_up < minimum_margin:
        reason = "ambiguous_alternatives"
    return TemporalConsensus(
        accepted=reason is None,
        value=winner if reason is None else None,
        confidence=confidence,
        stable_frames=stable_frames,
        alternatives=alternatives,
        reason=reason,
    )
