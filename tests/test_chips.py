from decimal import Decimal

import pytest

from xpoker_agent.chips import (
    create_session_setup,
    format_native_chips,
    parse_user_chip_value,
)
from xpoker_agent.models import ChipDisplayMode


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("100", "100"),
        ("10000", "10,000"),
        ("99999", "99,999"),
        ("100000", "100K"),
        ("200000", "200K"),
        ("999999", "999.999K"),
        ("1000000", "1M"),
        ("1500000", "1.5M"),
    ],
)
def test_native_chip_format_thresholds(value: str, expected: str) -> None:
    assert format_native_chips(Decimal(value)) == expected


def test_bb_mode_accepts_bb_suffix_or_plain_value() -> None:
    suffixed = parse_user_chip_value("100BB", display_mode=ChipDisplayMode.BB)
    plain = parse_user_chip_value("100", display_mode=ChipDisplayMode.BB)

    assert suffixed.amount_bb == plain.amount_bb == Decimal("100")
    assert suffixed.display_text == plain.display_text == "100BB"


@pytest.mark.parametrize(
    ("raw", "native", "display"),
    [
        ("100", Decimal("100"), "100"),
        ("10,000", Decimal("10000"), "10,000"),
        ("200K", Decimal("200000"), "200K"),
        ("1M", Decimal("1000000"), "1M"),
    ],
)
def test_native_mode_preserves_exact_value_and_applies_compact_display(
    raw: str, native: Decimal, display: str
) -> None:
    result = parse_user_chip_value(raw, display_mode=ChipDisplayMode.NATIVE)

    assert result.exact_native_chips == native
    assert result.display_text == display


def test_native_chip_input_converts_only_with_explicit_big_blind() -> None:
    result = parse_user_chip_value(
        "200K",
        display_mode=ChipDisplayMode.NATIVE,
        big_blind_native_chips=Decimal("2000"),
    )

    assert result.exact_native_chips == Decimal("200000")
    assert result.amount_bb == Decimal("100")


@pytest.mark.parametrize(
    ("raw", "mode"),
    [
        ("0", ChipDisplayMode.NATIVE),
        ("-1", ChipDisplayMode.NATIVE),
        ("100 B", ChipDisplayMode.NATIVE),
        ("BB100", ChipDisplayMode.BB),
        ("1.2.3", ChipDisplayMode.NATIVE),
        ("", ChipDisplayMode.NATIVE),
        ("100BB", ChipDisplayMode.NATIVE),
        ("200K", ChipDisplayMode.BB),
    ],
)
def test_user_chip_input_fails_closed_on_ambiguous_or_cross_mode_values(
    raw: str, mode: ChipDisplayMode
) -> None:
    with pytest.raises(ValueError, match="chip input|display mode"):
        parse_user_chip_value(raw, display_mode=mode)


@pytest.mark.parametrize("table_size", [6, 9])
def test_session_setup_selects_an_isolated_table_configuration(table_size: int) -> None:
    setup = create_session_setup(
        table_size=table_size,
        chip_display_mode=ChipDisplayMode.BB,
        stack_input="100",
    )

    assert setup.table_size == table_size
    assert f"{table_size}max" in setup.game_config_id
    assert setup.ready_for_strategy is True


def test_native_session_setup_waits_for_blind_conversion() -> None:
    setup = create_session_setup(
        table_size=6,
        chip_display_mode=ChipDisplayMode.NATIVE,
        stack_input="200000",
    )

    assert setup.ready_for_strategy is False
    assert setup.stack.display_text == "200K"
    assert setup.blocking_reason is not None
