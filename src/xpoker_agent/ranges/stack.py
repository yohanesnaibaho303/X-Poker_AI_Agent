"""Versioned stack-bucket matching with explicit mismatch metrics."""

from __future__ import annotations

from decimal import Decimal
from typing import Literal

from pydantic import Field

from xpoker_agent.models import StrictModel

STACK_BUCKETS_BB = tuple(Decimal(value) for value in ("20", "40", "50", "75", "100", "150", "200"))


class StackDepthMatch(StrictModel):
    requested_bb: Decimal = Field(gt=0)
    status: Literal["exact", "nearest", "interpolated"]
    matched_bb: Decimal | None = Field(default=None, gt=0)
    lower_bb: Decimal | None = Field(default=None, gt=0)
    upper_bb: Decimal | None = Field(default=None, gt=0)
    upper_weight: Decimal | None = Field(default=None, ge=0, le=1)
    absolute_mismatch_bb: Decimal = Field(ge=0)
    relative_mismatch: Decimal = Field(ge=0)
    policy_id: Literal["stack-buckets-v1"] = "stack-buckets-v1"


def nearest_stack_bucket(requested_bb: Decimal) -> StackDepthMatch:
    if requested_bb <= 0:
        raise ValueError("requested stack depth must be positive")
    matched = min(STACK_BUCKETS_BB, key=lambda bucket: (abs(bucket - requested_bb), bucket))
    mismatch = abs(matched - requested_bb)
    return StackDepthMatch(
        requested_bb=requested_bb,
        status="exact" if mismatch == 0 else "nearest",
        matched_bb=matched,
        absolute_mismatch_bb=mismatch,
        relative_mismatch=mismatch / requested_bb,
    )


def interpolation_bracket(requested_bb: Decimal) -> StackDepthMatch:
    if requested_bb <= 0:
        raise ValueError("requested stack depth must be positive")
    if requested_bb in STACK_BUCKETS_BB:
        return nearest_stack_bucket(requested_bb)
    lower = [bucket for bucket in STACK_BUCKETS_BB if bucket < requested_bb]
    upper = [bucket for bucket in STACK_BUCKETS_BB if bucket > requested_bb]
    if not lower or not upper:
        return nearest_stack_bucket(requested_bb)
    lower_bb, upper_bb = max(lower), min(upper)
    upper_weight = (requested_bb - lower_bb) / (upper_bb - lower_bb)
    nearest_mismatch = min(requested_bb - lower_bb, upper_bb - requested_bb)
    return StackDepthMatch(
        requested_bb=requested_bb,
        status="interpolated",
        lower_bb=lower_bb,
        upper_bb=upper_bb,
        upper_weight=upper_weight,
        absolute_mismatch_bb=nearest_mismatch,
        relative_mismatch=nearest_mismatch / requested_bb,
    )
