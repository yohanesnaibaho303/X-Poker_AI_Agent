"""Fail-closed clockwise ordering checks for provisional visual actions."""

from __future__ import annotations

from collections import defaultdict

from xpoker_agent.vision.models import ActionOrderValidation, DerivedActionCandidate


def _next_active_after(seat: int, active: set[int], table_size: int) -> int | None:
    for offset in range(1, table_size + 1):
        candidate = (seat + offset) % table_size
        if candidate in active:
            return candidate
    return None


def validate_action_order(
    actions: list[DerivedActionCandidate], *, table_size: int
) -> list[ActionOrderValidation]:
    """Validate only observable clockwise prefixes; never fill a missing action."""
    if table_size != 9:
        raise ValueError("only the 9-max table layout is supported")
    grouped: dict[tuple[int, str], list[DerivedActionCandidate]] = defaultdict(list)
    for action in actions:
        grouped[(action.hand_epoch, action.street)].append(action)

    results: list[ActionOrderValidation] = []
    street_order = {"preflop": 0, "flop": 1, "turn": 2, "river": 3}
    for (hand_epoch, street), candidates in sorted(
        grouped.items(), key=lambda item: (item[0][0], street_order[item[0][1]])
    ):
        candidates.sort(key=lambda item: (item.frame_sequence, item.occurrence))
        event_ids = [item.event_id for item in candidates]
        observed_seats = [item.seat for item in candidates]
        contexts = {(item.dealer_seat, tuple(item.active_seats)) for item in candidates}
        if len(contexts) != 1:
            results.append(
                ActionOrderValidation(
                    hand_epoch=hand_epoch,
                    street=street,
                    action_event_ids=event_ids,
                    observed_seats=observed_seats,
                    status="inconsistent",
                    issues=["dealer_or_active_seat_context_changed_within_street"],
                    reason="provisional action context changed within one betting street",
                )
            )
            continue
        dealer_seat, active_tuple = next(iter(contexts))
        active = set(active_tuple)
        if dealer_seat is None or dealer_seat not in active or len(active) < 2:
            results.append(
                ActionOrderValidation(
                    hand_epoch=hand_epoch,
                    street=street,
                    action_event_ids=event_ids,
                    observed_seats=observed_seats,
                    status="pending",
                    issues=["stable_dealer_and_active_seats_required"],
                    reason="clockwise order cannot start without a stable table context",
                )
            )
            continue

        expected = _next_active_after(dealer_seat, active, table_size)
        if street == "preflop":
            small_blind = expected
            big_blind = (
                _next_active_after(small_blind, active, table_size)
                if small_blind is not None
                else None
            )
            expected = (
                _next_active_after(big_blind, active, table_size) if big_blind is not None else None
            )
        start = expected
        issues: list[str] = []
        for candidate in candidates:
            if candidate.seat not in active:
                issues.append(f"seat_{candidate.seat}_not_in_active_context")
                continue
            if expected is not None and candidate.seat != expected:
                issues.append(
                    f"unobserved_intervening_action_expected_seat_{expected}_before_{candidate.seat}"
                )
            if candidate.action in {"fold", "all_in"}:
                active.discard(candidate.seat)
            expected = _next_active_after(candidate.seat, active, table_size)

        results.append(
            ActionOrderValidation(
                hand_epoch=hand_epoch,
                street=street,
                action_event_ids=event_ids,
                observed_seats=observed_seats,
                expected_start_seat=start,
                expected_next_seat=expected,
                status="pending" if issues else "prefix_consistent",
                issues=issues,
                reason=(
                    "observed actions form a gap-free clockwise prefix"
                    if not issues
                    else "one or more intervening actions were not observed; no inference made"
                ),
            )
        )
    return results
