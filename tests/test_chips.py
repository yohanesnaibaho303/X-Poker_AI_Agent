from decimal import Decimal

import pytest

from xpoker_agent.chips import create_session_setup, format_native_chips, parse_user_chip_value


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        (Decimal("10000"), "10,000"),
        (Decimal("200000"), "200,000"),
        (Decimal("1000000"), "1,000,000"),
        (Decimal("1234.5"), "1,234.5"),
    ],
)
def test_native_chip_display_is_exact_and_grouped(value: Decimal, expected: str) -> None:
    assert format_native_chips(value) == expected


@pytest.mark.parametrize("raw", ["100BB", "200K", "1M", "BB100", "100 B", "0", "-1", ""])
def test_native_chip_parser_rejects_units_and_invalid_values(raw: str) -> None:
    with pytest.raises(ValueError):
        parse_user_chip_value(raw)


def test_session_setup_is_fixed_to_nine_max_native_one_two() -> None:
    setup = create_session_setup(stack_input="100,000")
    assert setup.table_size == 9
    assert setup.stack.amount_chips == Decimal("100000")
    assert setup.stack.display_text == "100,000"
    assert setup.native_small_blind == 1
    assert setup.native_big_blind == 2
