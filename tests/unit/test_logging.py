from __future__ import annotations

import json
import logging

from issue_tracker.logging import JsonFormatter


def test_json_formatter_emits_stable_fields_and_suppresses_unapproved_extras():
    record = logging.LogRecord("issue_tracker.test", logging.INFO, __file__, 10, "request complete", (), None)
    record.event = "http_request"
    record.method = "GET"
    record.route = "/issues/{issue_id}"
    record.status_code = 200
    record.duration_ms = 12.34
    record.password = "super-secret"

    line = JsonFormatter(
        app="issue-tracker",
        service="app",
        source="app-log",
        environment="uat",
    ).format(record)

    payload = json.loads(line)
    assert payload["app"] == "issue-tracker"
    assert payload["service"] == "app"
    assert payload["source"] == "app-log"
    assert payload["environment"] == "uat"
    assert payload["event"] == "http_request"
    assert payload["route"] == "/issues/{issue_id}"
    assert "password" not in payload
    assert "super-secret" not in line
