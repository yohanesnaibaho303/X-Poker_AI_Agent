"""Deterministic main/side-pot construction from canonical seat commitments."""

from __future__ import annotations

from decimal import Decimal

from xpoker_agent.models import ParticipationStatus, PotLayer, SeatState


def total_commitment(seat: SeatState) -> Decimal:
    return sum(seat.committed_by_street_chips.values(), start=Decimal("0"))


def build_pot_layers(seats: list[SeatState]) -> list[PotLayer]:
    """Build layers at all-in caps; ordinary unequal live wagers remain one provisional pot."""
    commitments = {seat.seat: total_commitment(seat) for seat in seats}
    maximum = max(commitments.values(), default=Decimal("0"))
    if maximum == 0:
        return []
    caps = {
        amount
        for seat in seats
        if seat.participation is ParticipationStatus.ALL_IN
        and (amount := commitments[seat.seat]) > 0
        and amount < maximum
    }
    caps.add(maximum)
    layers: list[PotLayer] = []
    previous = Decimal("0")
    for cap in sorted(caps):
        contributors = sorted(
            seat_number for seat_number, commitment in commitments.items() if commitment > previous
        )
        amount = sum(
            (min(commitments[seat_number], cap) - previous for seat_number in contributors),
            start=Decimal("0"),
        )
        if amount <= 0:
            previous = cap
            continue
        eligible = [
            seat_number
            for seat_number in contributors
            if seats[seat_number].participation
            not in {ParticipationStatus.EMPTY, ParticipationStatus.FOLDED}
        ]
        layers.append(
            PotLayer(
                pot_index=len(layers),
                amount_chips=amount,
                remaining_chips=amount,
                cap_per_player_chips=cap,
                contributing_seats=contributors,
                eligible_seats=eligible,
            )
        )
        previous = cap
    return layers
