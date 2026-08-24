"""Lossless parsing and normalization of user-entered X-Poker chip values."""

from __future__ import annotations

import re
from decimal import Decimal, InvalidOperation

from xpoker_agent.config import load_game_config
from xpoker_agent.models import ChipDisplayMode, ChipValue, SessionSetup

_USER_CHIP_PATTERN = re.compile(
    r"^(?P<number>(?:\d{1,3}(?:,\d{3})+|\d+)(?:\.\d+)?)"
    r"(?P<suffix>BB|K|M)?$",
    re.IGNORECASE,
)


def parse_user_chip_value(
    raw_input: str,
    *,
    display_mode: ChipDisplayMode,
    big_blind_native_chips: Decimal | None = None,
) -> ChipValue:
    """Parse a BB or native value while keeping native chips exact internally."""
    text = raw_input.strip()
    if not text or any(character.isspace() for character in text):
        raise ValueError("chip input contains empty or embedded whitespace")
    match = _USER_CHIP_PATTERN.fullmatch(text)
    if match is None:
        raise ValueError(f"unsupported or ambiguous chip input: {raw_input!r}")
    try:
        number = Decimal(match.group("number").replace(",", ""))
    except InvalidOperation as error:
        raise ValueError(f"invalid chip input: {raw_input!r}") from error
    if number <= 0:
        raise ValueError("chip input must be positive")
    if big_blind_native_chips is not None and big_blind_native_chips <= 0:
        raise ValueError("big_blind_native_chips must be positive")

    suffix = (match.group("suffix") or "").upper()
    if display_mode is ChipDisplayMode.BB:
        if suffix not in {"", "BB"}:
            raise ValueError("BB display mode accepts a plain value or BB suffix")
        return ChipValue(
            raw_input=raw_input,
            display_mode=ChipDisplayMode.BB,
            display_text=f"{_plain_decimal(number)}BB",
            amount_bb=number,
            exact_native_chips=(
                number * big_blind_native_chips if big_blind_native_chips is not None else None
            ),
        )

    if suffix == "BB":
        raise ValueError("native display mode does not accept a BB suffix")
    multiplier = {
        "": Decimal("1"),
        "K": Decimal("1000"),
        "M": Decimal("1000000"),
    }[suffix]
    exact_native_chips = number * multiplier
    return ChipValue(
        raw_input=raw_input,
        display_mode=ChipDisplayMode.NATIVE,
        display_text=format_native_chips(exact_native_chips),
        amount_bb=(
            exact_native_chips / big_blind_native_chips
            if big_blind_native_chips is not None
            else None
        ),
        exact_native_chips=exact_native_chips,
    )


def _plain_decimal(value: Decimal) -> str:
    text = format(value, "f")
    return text.rstrip("0").rstrip(".") if "." in text else text


def format_native_chips(value: Decimal) -> str:
    """Format exact native chips using the X-Poker-oriented 100K/1M thresholds."""
    if value < 0:
        raise ValueError("native chip value cannot be negative")
    if value >= Decimal("1000000"):
        return f"{_plain_decimal(value / Decimal('1000000'))}M"
    if value >= Decimal("100000"):
        return f"{_plain_decimal(value / Decimal('1000'))}K"
    text = format(value, ",f")
    if "." in text:
        text = text.rstrip("0").rstrip(".")
    return text


def create_session_setup(
    *,
    table_size: int,
    chip_display_mode: ChipDisplayMode,
    stack_input: str,
    big_blind_native_chips: Decimal | None = None,
) -> SessionSetup:
    """Resolve a user session without silently guessing a native-chip-to-BB conversion."""
    game = load_game_config(table_size=table_size)
    stack = parse_user_chip_value(
        stack_input,
        display_mode=chip_display_mode,
        big_blind_native_chips=big_blind_native_chips,
    )
    ready = stack.amount_bb is not None
    return SessionSetup(
        table_size=game.seats,
        game_config_id=game.config_id,
        stack=stack,
        big_blind_native_chips=big_blind_native_chips,
        ready_for_strategy=ready,
        blocking_reason=(
            None
            if ready
            else "big blind value must be entered or reliably detected before BB strategy lookup"
        ),
    )
