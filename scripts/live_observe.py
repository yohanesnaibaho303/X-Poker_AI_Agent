"""Run the existing read-only live observer and print compact status snapshots."""

from __future__ import annotations

import argparse
import asyncio
import json
from pathlib import Path

from xpoker_agent.monitoring.live_hero import build_live_hero_calculation
from xpoker_agent.vision.live_observation import LiveObservationService


async def observe(seconds: int, interval_ms: int, output: Path | None) -> None:
    service = LiveObservationService()
    await service.start(table_size=9, interval_ms=interval_ms)
    evidence = {
        "max_hand_epoch": 0,
        "boundary_validated": False,
        "hero_cards_accepted": False,
        "max_derived_actions": 0,
        "max_amount_matches": 0,
        "max_pot_matches": 0,
        "max_eligible_actions": 0,
        "canonical_hand_observed": False,
        "completed_hand_observed": False,
        "latest_completed_hand": None,
        "max_stack_increases": 0,
        "retained_canonical_hand": None,
        "matched_blind_amounts": [],
        "gto_recommendation_observed": False,
        "latest_gto_recommendation": None,
        "epochs": {},
    }
    try:
        for _ in range(seconds):
            await asyncio.sleep(1)
            sample = service.status()
            hero = build_live_hero_calculation(sample)
            if hero.recommendation_ready:
                evidence["gto_recommendation_observed"] = True
                evidence["latest_gto_recommendation"] = hero.model_dump(mode="json")
            evidence["max_hand_epoch"] = max(evidence["max_hand_epoch"], sample.hand_epoch)
            evidence["boundary_validated"] |= sample.hand_boundary_validation.status == "validated"
            evidence["hero_cards_accepted"] |= sample.hero_cards_accepted
            evidence["max_derived_actions"] = max(
                evidence["max_derived_actions"], len(sample.derived_action_candidates)
            )
            evidence["max_amount_matches"] = max(
                evidence["max_amount_matches"],
                sum(item.status == "matched" for item in sample.action_amount_reconciliations),
            )
            evidence["max_pot_matches"] = max(
                evidence["max_pot_matches"],
                sum(item.status == "matched" for item in sample.action_pot_reconciliations),
            )
            evidence["max_eligible_actions"] = max(
                evidence["max_eligible_actions"],
                len(sample.reconstruction_readiness.eligible_action_event_ids),
            )
            evidence["canonical_hand_observed"] |= sample.canonical_hand is not None
            evidence["max_stack_increases"] = max(
                evidence["max_stack_increases"], len(sample.stack_increase_candidates)
            )
            if sample.latest_completed_hand is not None:
                evidence["completed_hand_observed"] = True
                evidence["latest_completed_hand"] = sample.latest_completed_hand.model_dump(
                    mode="json"
                )
            if sample.retained_canonical_hand is not None:
                evidence["retained_canonical_hand"] = sample.retained_canonical_hand.model_dump(
                    mode="json"
                )
            matched_blinds = {
                str(item.amount_native)
                for item in sample.blind_post_reconciliations
                if item.status == "matched"
            }
            evidence["matched_blind_amounts"] = sorted(
                {*evidence["matched_blind_amounts"], *matched_blinds}
            )
            epoch = evidence["epochs"].setdefault(
                str(sample.hand_epoch),
                {
                    "hand_modes": [],
                    "boundary_validated": False,
                    "hero_cards_accepted": False,
                    "max_derived_actions": 0,
                    "max_amount_matches": 0,
                    "max_pot_matches": 0,
                    "max_eligible_actions": 0,
                    "canonical_hand_observed": False,
                    "canonical_hand": None,
                    "canonical_errors": [],
                    "matched_blind_amounts": [],
                    "fewest_readiness_issues": [],
                },
            )
            epoch["hand_modes"] = sorted({*epoch["hand_modes"], sample.current_hand_mode})
            epoch["boundary_validated"] |= sample.hand_boundary_validation.status == "validated"
            epoch["hero_cards_accepted"] |= sample.hero_cards_accepted
            epoch["max_derived_actions"] = max(
                epoch["max_derived_actions"], len(sample.derived_action_candidates)
            )
            epoch["max_amount_matches"] = max(
                epoch["max_amount_matches"],
                sum(item.status == "matched" for item in sample.action_amount_reconciliations),
            )
            epoch["max_pot_matches"] = max(
                epoch["max_pot_matches"],
                sum(item.status == "matched" for item in sample.action_pot_reconciliations),
            )
            epoch["max_eligible_actions"] = max(
                epoch["max_eligible_actions"],
                len(sample.reconstruction_readiness.eligible_action_event_ids),
            )
            epoch["canonical_hand_observed"] |= sample.canonical_hand is not None
            if sample.canonical_hand is not None:
                epoch["canonical_hand"] = sample.canonical_hand.model_dump(mode="json")
            if sample.canonical_reconstruction_error:
                epoch["canonical_errors"] = sorted(
                    {*epoch["canonical_errors"], sample.canonical_reconstruction_error}
                )
            epoch["matched_blind_amounts"] = sorted(
                {*epoch["matched_blind_amounts"], *matched_blinds}
            )
            issues = sample.reconstruction_readiness.issues
            if not epoch["fewest_readiness_issues"] or len(issues) < len(
                epoch["fewest_readiness_issues"]
            ):
                epoch["fewest_readiness_issues"] = issues
    finally:
        await service.stop()

    status = service.status()
    hero = build_live_hero_calculation(status)
    if output is not None:
        output.write_text(
            json.dumps(
                {"evidence": evidence, "final_status": status.model_dump(mode="json")},
                indent=2,
            ),
            encoding="utf-8",
        )
    print(
        json.dumps(
            {
                "frames_attempted": status.frames_attempted,
                "frames_succeeded": status.frames_succeeded,
                "frames_failed": status.frames_failed,
                "target_stable": status.target_stable,
                "hand_epoch": status.hand_epoch,
                "hand_mode": status.current_hand_mode,
                "hero_cards": status.recognized_hero_cards,
                "hero_cards_accepted": status.hero_cards_accepted,
                "board_cards": status.recognized_board_cards,
                "board_cards_accepted": status.board_cards_accepted,
                "active_seats": status.active_seats,
                "derived_actions": len(status.derived_action_candidates),
                "canonical_hand": status.canonical_hand is not None,
                "completed_hand": status.latest_completed_hand is not None,
                "settlement_reason": status.settlement_reason,
                "canonical_error": status.canonical_reconstruction_error,
                "readiness": status.reconstruction_readiness.model_dump(mode="json"),
                "controller_enabled": status.controller_enabled,
                "live_hero": hero.model_dump(mode="json"),
                "last_error": status.last_error,
                "evidence": evidence,
            },
            indent=2,
        )
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--seconds", type=int, default=60)
    parser.add_argument("--interval-ms", type=int, default=500)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    asyncio.run(observe(args.seconds, args.interval_ms, args.output))


if __name__ == "__main__":
    main()
