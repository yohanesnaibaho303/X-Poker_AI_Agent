import json
import logging

from xpoker_agent.logging import JsonFormatter


def test_json_formatter_includes_audit_context() -> None:
    record = logging.LogRecord("test", logging.INFO, __file__, 1, "message", (), None)
    record.hand_id = "hand-1"
    record.decision_id = "decision-1"

    payload = json.loads(JsonFormatter().format(record))

    assert payload["level"] == "INFO"
    assert payload["message"] == "message"
    assert payload["hand_id"] == "hand-1"
    assert payload["decision_id"] == "decision-1"
