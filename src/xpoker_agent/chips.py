"""Lossless parsing and exact display of native X-Poker chip values."""

from __future__ import annotations

import re
from decimal import Decimal, InvalidOperation

from xpoker_agent.config import load_game_config
from xpoker_agent.models import ChipValue, SessionSetup

_USER_CHIP_PATTERN = re.compile(
    r"^(?P<number>(?:\d{1,3}(?:,\d{3})+|\d+)(?:\.\d+)?)"
    r"$",
)


def parse_user_chip_value(
    raw_input: str,
) -> ChipValue:
    """Parse one positive native-chip number; unit suffixes are forbidden."""
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
    return ChipValue(
        raw_input=raw_input,
        display_text=format_native_chips(number),
        amount_chips=number,
    )


def _plain_decimal(value: Decimal) -> str:
    text = format(value, "f")
    return text.rstrip("0").rstrip(".") if "." in text else text


def format_native_chips(value: Decimal) -> str:
    """Format exact native chips with grouping and no unit abbreviation."""
    if value < 0:
        raise ValueError("native chip value cannot be negative")
    text = format(value, ",f")
    if "." in text:
        text = text.rstrip("0").rstrip(".")
    return text


def create_session_setup(
    *,
    stack_input: str,
) -> SessionSetup:
    """Resolve the fixed 9-max native-chip session setup."""
    game = load_game_config()
    stack = parse_user_chip_value(stack_input)
    return SessionSetup(
        table_size=game.seats,
        game_config_id=game.config_id,
        stack=stack,
        native_small_blind=game.native_small_blind,
        native_big_blind=game.native_big_blind,
    )
