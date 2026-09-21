"""Tests for the automated M3 live collection checklist."""

from scripts.live_collection_checklist import (
    ALL_CARDS,
    compute_checklist,
    generate_markdown_checklist,
)


def test_compute_checklist_identifies_pending_cards_and_dealers() -> None:
    evidence = {
        "cards": ["Ah", "Kd", "Qc"],
        "dealers": [0, 1, 3],
        "seats": list(range(9)),
        "actions": ["pre_action", "decision"],
        "numeric_channels": ["pot", "stack", "blind"],
    }
    checklist = compute_checklist(evidence)

    assert checklist["checklist_version"] == "1.0"
    assert checklist["total_categories"] == 6
    # Cards: 3/52 (pending), dealers: 3/9 (pending), seats: 9/9 (passed)
    # numeric: 3/3 (passed), actions: 2/3 (passed), latency: 1/1 (passed)
    assert checklist["satisfied_categories"] == 4
    assert checklist["completion_percentage"] == 66.7

    card_item = next(item for item in checklist["items"] if item["id"] == "cards_52_coverage")
    assert card_item["satisfied"] is False
    assert len(card_item["missing"]) == 49
    assert "Ah" not in card_item["missing"]
    assert "As" in card_item["missing"]

    dealer_item = next(item for item in checklist["items"] if item["id"] == "dealer_button_9_seats")
    assert dealer_item["satisfied"] is False
    assert "seat_2" in dealer_item["missing"]


def test_compute_checklist_passes_when_all_targets_met() -> None:
    full_evidence = {
        "cards": list(ALL_CARDS),
        "dealers": list(range(9)),
        "seats": list(range(9)),
        "actions": ["pre_action", "decision", "absent"],
        "numeric_channels": ["pot", "stack", "blind"],
    }
    checklist = compute_checklist(full_evidence)

    assert checklist["satisfied_categories"] == 6
    assert checklist["completion_percentage"] == 100.0
    assert all(item["satisfied"] for item in checklist["items"])


def test_generate_markdown_checklist_renders_valid_markdown() -> None:
    evidence = {
        "cards": ["As"],
        "dealers": [0],
        "seats": [0],
        "actions": ["pre_action"],
        "numeric_channels": ["pot"],
    }
    checklist = compute_checklist(evidence)
    md = generate_markdown_checklist(checklist)

    assert "# Automated Live Collection Checklist" in md
    assert "### [ ] card_recognition: cards_52_coverage" in md
    assert "### [x] performance: latency_p95_decision_window" in md
