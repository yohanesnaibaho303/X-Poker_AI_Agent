"""Fail-closed strategy resolution with a hard GTO/reference-prior boundary."""

from __future__ import annotations

from uuid import UUID

from pydantic import model_validator

from xpoker_agent.models import StrategyMatch, StrictModel, WeightedRange
from xpoker_agent.ranges.library import PreflopSpotKey, RangeLibrary, RangeLookup


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
        exact = lookup.stack_match.status == "exact"
        confidence = artifact.confidence
        assumptions = list(artifact.assumptions)
        distance: dict[str, object] = {}
        if not exact:
            relative = float(lookup.stack_match.relative_mismatch)
            confidence *= max(0.0, 1.0 - relative)
            distance = lookup.stack_match.model_dump(mode="json")
            assumptions.append(
                f"Used {lookup.stack_match.matched_chips} native-chip solution for "
                f"{lookup.stack_match.requested_chips} native-chip request."
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
