from xpoker_agent.vision.pots import parse_pot_label


def test_pot_label_parses_supported_native_formats() -> None:
    assert parse_pot_label("POT 40").value_native == 40
    assert parse_pot_label("Pot: 81,500").value_native == 81500
    assert parse_pot_label("POT 1,200,000").value_native == 1200000
    alias = parse_pot_label("par 16")
    assert alias.value_native == 16
    assert alias.confidence == 0.8


def test_pot_label_rejects_missing_or_multiple_amounts() -> None:
    assert parse_pot_label("POT").value_native is None
    assert parse_pot_label("POT 40 / 80").value_native is None
    assert parse_pot_label("40").value_native is None
    assert parse_pot_label("POT 1.2M").value_native is None
