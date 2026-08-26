"""Versioned stack-bucket matching with explicit mismatch metrics."""

from __future__ import annotations

from decimal import Decimal
from typing import Literal

from pydantic import Field

from xpoker_agent.models import StrictModel

STACK_BUCKETS_CHIPS = tuple(
    Decimal(value) for value in ("40", "80", "100", "150", "200", "300", "400")
)


class StackDepthMatch(StrictModel):
    requested_chips: Decimal = Field(gt=0)
    status: Literal["exact", "nearest", "interpolated"]
    matched_chips: Decimal | None = Field(default=None, gt=0)
    lower_chips: Decimal | None = Field(default=None, gt=0)
    upper_chips: Decimal | None = Field(default=None, gt=0)
    upper_weight: Decimal | None = Field(default=None, ge=0, le=1)
    absolute_mismatch_chips: Decimal = Field(ge=0)
    relative_mismatch: Decimal = Field(ge=0)
    policy_id: Literal["native-stack-buckets-v1"] = "native-stack-buckets-v1"


def nearest_stack_bucket(requested_chips: Decimal) -> StackDepthMatch:
    if requested_chips <= 0:
        raise ValueError("requested stack depth must be positive")
    matched = min(STACK_BUCKETS_CHIPS, key=lambda bucket: (abs(bucket - requested_chips), bucket))
    mismatch = abs(matched - requested_chips)
    return StackDepthMatch(
        requested_chips=requested_chips,
        status="exact" if mismatch == 0 else "nearest",
        matched_chips=matched,
        absolute_mismatch_chips=mismatch,
        relative_mismatch=mismatch / requested_chips,
    )


def interpolation_bracket(requested_chips: Decimal) -> StackDepthMatch:
    if requested_chips <= 0:
        raise ValueError("requested stack depth must be positive")
    if requested_chips in STACK_BUCKETS_CHIPS:
        return nearest_stack_bucket(requested_chips)
    lower = [bucket for bucket in STACK_BUCKETS_CHIPS if bucket < requested_chips]
    upper = [bucket for bucket in STACK_BUCKETS_CHIPS if bucket > requested_chips]
    if not lower or not upper:
        return nearest_stack_bucket(requested_chips)
    lower_chips, upper_chips = max(lower), min(upper)
    upper_weight = (requested_chips - lower_chips) / (upper_chips - lower_chips)
    nearest_mismatch = min(requested_chips - lower_chips, upper_chips - requested_chips)
    return StackDepthMatch(
        requested_chips=requested_chips,
        status="interpolated",
        lower_chips=lower_chips,
        upper_chips=upper_chips,
        upper_weight=upper_weight,
        absolute_mismatch_chips=nearest_mismatch,
        relative_mismatch=nearest_mismatch / requested_chips,
    )
