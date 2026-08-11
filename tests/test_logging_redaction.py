from __future__ import annotations

import json
from pathlib import Path

from app import logging_config


def test_scrub_event_redacts_top_level_and_nested_values() -> None:
    event = {
        "event": "contact student@vinuni.edu.vn",
        "session_id": "090 123 4567",
        "payload": {
            "cards": ["4111 1111 1111 1111"],
            "identity": {"passport": "AB1234567"},
        },
        "latency_ms": 125,
    }

    scrubbed = logging_config.scrub_event(None, "info", event)
    rendered = json.dumps(scrubbed, ensure_ascii=False)

    for raw_value in (
        "student@vinuni.edu.vn",
        "090 123 4567",
        "4111 1111 1111 1111",
        "AB1234567",
    ):
        assert raw_value not in rendered
    assert scrubbed["latency_ms"] == 125


def test_logging_pipeline_redacts_rendered_exception(
    monkeypatch,
    tmp_path: Path,
) -> None:
    log_path = tmp_path / "logs.jsonl"
    monkeypatch.setattr(logging_config, "LOG_PATH", log_path)
    logging_config.configure_logging()
    logger = logging_config.get_logger()

    try:
        raise ValueError("Cannot notify student@vinuni.edu.vn")
    except ValueError:
        logger.error(
            "processing_failed",
            service="api",
            correlation_id="req-1234abcd",
            payload={"contacts": [{"phone": "090 123 4567"}]},
            exc_info=True,
        )

    raw_log = log_path.read_text(encoding="utf-8")
    record = json.loads(raw_log)

    assert "student@vinuni.edu.vn" not in raw_log
    assert "090 123 4567" not in raw_log
    assert "REDACTED_EMAIL" in record["exception"]
    assert "REDACTED_PHONE_VN" in record["payload"]["contacts"][0]["phone"]
