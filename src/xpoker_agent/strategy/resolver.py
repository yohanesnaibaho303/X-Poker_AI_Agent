"""Fail-closed strategy resolution with a hard GTO/reference-prior boundary."""

from __future__ import annotations

from uuid import UUID

from pydantic import Field, model_validator

from xpoker_agent.models import StrategyMatch, StrictModel, WeightedRange
from xpoker_agent.ranges.library import PreflopSpotKey, RangeLibrary, RangeLookup


class ComboActionResult(StrictModel):
    action: str
    frequency: float = Field(ge=0, le=1)
    ev_chips: float | None = None
    ev_loss_chips: float | None = Field(default=None, ge=0)


class StrategyComboResult(StrictModel):
    combo: str
    match_status: str
    strategy_role: str
    equity: float | None = Field(default=None, ge=0, le=1)
    actions: list[ComboActionResult]
    confidence: float = Field(ge=0, le=1)
    source_artifact_id: str | None = None
    assumptions: list[str]


class ComboActionComparison(StrictModel):
    action: str
    baseline_frequency: float = Field(ge=0, le=1)
    candidate_frequency: float = Field(ge=0, le=1)
    frequency_delta: float = Field(ge=-1, le=1)
    baseline_ev_chips: float | None = None
    candidate_ev_chips: float | None = None
    ev_delta_chips: float | None = None


class StrategyComboComparison(StrictModel):
    combo: str
    baseline_role: str
    candidate_role: str
    equity_delta: float | None = Field(default=None, ge=-1, le=1)
    actions: list[ComboActionComparison]
    assumptions: list[str]


def compare_combo_results(
    baseline: StrategyComboResult, candidate: StrategyComboResult
) -> StrategyComboComparison:
    if baseline.combo != candidate.combo:
        raise ValueError("strategy comparison requires the same exact combination")
    baseline_actions = {item.action: item for item in baseline.actions}
    candidate_actions = {item.action: item for item in candidate.actions}
    actions = []
    for action in sorted(set(baseline_actions) | set(candidate_actions)):
        left = baseline_actions.get(action)
        right = candidate_actions.get(action)
        left_frequency = left.frequency if left is not None else 0.0
        right_frequency = right.frequency if right is not None else 0.0
        left_ev = left.ev_chips if left is not None else None
        right_ev = right.ev_chips if right is not None else None
        actions.append(
            ComboActionComparison(
                action=action,
                baseline_frequency=left_frequency,
                candidate_frequency=right_frequency,
                frequency_delta=right_frequency - left_frequency,
                baseline_ev_chips=left_ev,
                candidate_ev_chips=right_ev,
                ev_delta_chips=(
                    right_ev - left_ev
                    if left_ev is not None and right_ev is not None
                    else None
                ),
            )
        )
    return StrategyComboComparison(
        combo=baseline.combo,
        baseline_role=baseline.strategy_role,
        candidate_role=candidate.strategy_role,
        equity_delta=(
            candidate.equity - baseline.equity
            if baseline.equity is not None and candidate.equity is not None
            else None
        ),
        actions=actions,
        assumptions=[
            "Frequency deltas are candidate minus baseline for the same exact combination.",
            "EV and equity deltas remain unavailable unless both inputs provide them.",
        ],
    )


class StrategyResolution(StrictModel):
    match: StrategyMatch
    strategy: WeightedRange | None = None
    reference_prior: WeightedRange | None = None

    @model_validator(mode="after")
    def preserve_strategy_role_boundary(self) -> StrategyResolution:
        if (
            self.strategy is not None
            and self.strategy.source.get("strategy_role") != "gto_solution"
        ):
            raise ValueError("resolved GTO strategy must come from a gto_solution artifact")
        if (
            self.reference_prior is not None
            and self.reference_prior.source.get("strategy_role") != "reference_prior"
        ):
            raise ValueError("reference fallback must come from a reference_prior artifact")
        if self.match.status == "unavailable" and self.strategy is not None:
            raise ValueError("an unavailable strategy match cannot contain a GTO strategy")
        if self.match.status != "unavailable" and self.strategy is None:
            raise ValueError("an available strategy match requires a GTO strategy")
        return self


class PreflopStrategyResolver:
    def __init__(
        self,
        *,
        gto_library: RangeLibrary | None = None,
        reference_library: RangeLibrary | None = None,
    ) -> None:
        if gto_library is not None and any(
            artifact.strategy_role != "gto_solution" for artifact in gto_library.artifacts
        ):
            raise ValueError("GTO library contains a non-GTO artifact")
        if reference_library is not None and any(
            artifact.strategy_role != "reference_prior" for artifact in reference_library.artifacts
        ):
            raise ValueError("reference library contains a non-reference artifact")
        self.gto_library = gto_library
        self.reference_library = reference_library

    def resolve(
        self, requested: PreflopSpotKey, *, player_ref: str, hand_id: UUID
    ) -> StrategyResolution:
        reference = self._reference_fallback(requested, player_ref=player_ref, hand_id=hand_id)
        lookup = self._lookup(self.gto_library, requested)
        if lookup is None:
            return StrategyResolution(
                match=StrategyMatch(
                    status="unavailable",
                    requested_spot=requested.model_dump(mode="json"),
                    confidence=0.0,
                    assumptions=[
                        "No validated configuration-compatible GTO solution artifact is available.",
                        *(
                            ["A low-confidence reference prior is shown separately and is not GTO."]
                            if reference is not None
                            else []
                        ),
                    ],
                ),
                reference_prior=reference,
            )

        artifact = lookup.artifact
        exact = lookup.stack_match.status == "exact" and artifact.model_abstraction is None
        confidence = artifact.confidence
        assumptions = list(artifact.assumptions)
        distance: dict[str, object] = {}
        if lookup.stack_match.status != "exact":
            relative = float(lookup.stack_match.relative_mismatch)
            confidence *= max(0.0, 1.0 - relative)
            distance = lookup.stack_match.model_dump(mode="json")
            assumptions.append(
                f"Used {lookup.stack_match.matched_chips} native-chip solution for "
                f"{lookup.stack_match.requested_chips} native-chip request."
            )
        if artifact.model_abstraction is not None:
            distance["model_abstraction"] = artifact.model_abstraction
            assumptions.append(
                "Strategy is configuration-matched but abstracted by its source solver model."
            )
        strategy = artifact.to_weighted_range(player_ref=player_ref, hand_id=hand_id)
        return StrategyResolution(
            match=StrategyMatch(
                status="exact" if exact else "abstracted",
                requested_spot=requested.model_dump(mode="json"),
                matched_spot=artifact.spot.model_dump(mode="json"),
                distance=distance,
                source_artifact_id=artifact.artifact_id,
                confidence=confidence,
                assumptions=assumptions,
            ),
            strategy=strategy,
            reference_prior=reference,
        )

    @staticmethod
    def summarize_combo(resolution: StrategyResolution, combo: str) -> StrategyComboResult:
        selected = resolution.strategy or resolution.reference_prior
        if selected is None:
            raise KeyError("no strategy or reference prior is available for combo lookup")
        strategy = selected.combos.get(combo)
        if strategy is None or strategy.weight <= 0:
            raise KeyError(f"combo is absent from the resolved range: {combo}")
        complete_ev = bool(strategy.actions) and set(strategy.ev_chips) == set(strategy.actions)
        best_ev = max(strategy.ev_chips.values()) if complete_ev else None
        actions = [
            ComboActionResult(
                action=action,
                frequency=frequency,
                ev_chips=strategy.ev_chips.get(action),
                ev_loss_chips=(
                    max(0.0, best_ev - strategy.ev_chips[action])
                    if best_ev is not None
                    else None
                ),
            )
            for action, frequency in sorted(strategy.actions.items())
        ]
        role = str(selected.source.get("strategy_role", "unknown"))
        return StrategyComboResult(
            combo=combo,
            match_status=resolution.match.status,
            strategy_role=role,
            equity=strategy.equity,
            actions=actions,
            confidence=min(resolution.match.confidence or selected.confidence, selected.confidence),
            source_artifact_id=selected.source.get("artifact_id"),
            assumptions=[*resolution.match.assumptions, *selected.assumptions],
        )

    @staticmethod
    def _lookup(library: RangeLibrary | None, requested: PreflopSpotKey) -> RangeLookup | None:
        if library is None:
            return None
        try:
            return library.lookup(requested)
        except KeyError:
            return None

    def _reference_fallback(
        self, requested: PreflopSpotKey, *, player_ref: str, hand_id: UUID
    ) -> WeightedRange | None:
        lookup = self._lookup(self.reference_library, requested)
        if lookup is None:
            return None
        prior = lookup.artifact.to_weighted_range(player_ref=player_ref, hand_id=hand_id)
        if lookup.stack_match.status != "exact":
            prior.assumptions.append(
                f"Reference prior indexed at {lookup.stack_match.matched_chips} native chips for "
                f"{lookup.stack_match.requested_chips} native-chip request."
            )
            prior.confidence *= max(0.0, 1.0 - float(lookup.stack_match.relative_mismatch))
        return prior
