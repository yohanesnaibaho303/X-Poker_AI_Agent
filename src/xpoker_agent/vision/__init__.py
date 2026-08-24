"""Visual observation and OCR boundary."""

from xpoker_agent.vision.cards import (
    classify_board_geometry,
    detect_card_slots,
    validate_unique_cards,
)
from xpoker_agent.vision.numbers import parse_chip_amount
from xpoker_agent.vision.rules import classify_rule_label
from xpoker_agent.vision.temporal import consensus
from xpoker_agent.vision.windows_ocr import recognize_text

__all__ = [
    "classify_board_geometry",
    "classify_rule_label",
    "consensus",
    "detect_card_slots",
    "parse_chip_amount",
    "recognize_text",
    "validate_unique_cards",
]
