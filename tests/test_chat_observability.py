from __future__ import annotations

import json
from pathlib import Path

from fastapi.testclient import TestClient

from app import logging_config
from app.agent import AgentResult
from app.main import app
from app.pii import hash_user_id


def test_chat_response_log_exposes_quality_for_dashboard(
    monkeypatch, tmp_path: Path
) -> None:
    log_path = tmp_path / "logs.jsonl"
    monkeypatch.setattr(logging_config, "LOG_PATH", log_path)
    monkeypatch.setattr(
        "app.main.agent.run",
        lambda **_: AgentResult(
            answer="Observable response",
            latency_ms=25,
            tokens_in=10,
            tokens_out=20,
            cost_usd=0.001,
            quality_score=0.8,
        ),
    )

    with TestClient(app) as client:
        response = client.post(
            "/chat",
            headers={"x-request-id": "req-deadbeef"},
            json={
                "user_id": "student-01",
                "session_id": "session-01",
                "feature": "qa",
                "message": "Explain observability",
            },
        )

    assert response.status_code == 200
    assert response.json()["correlation_id"] == "req-deadbeef"
    assert response.headers["x-request-id"] == "req-deadbeef"
    assert int(response.headers["x-response-time-ms"]) >= 0
    events = [json.loads(line) for line in log_path.read_text(encoding="utf-8").splitlines()]
    api_events = [event for event in events if event.get("service") == "api"]
    response_event = next(event for event in events if event["event"] == "response_sent")
    assert response_event["quality_score"] == response.json()["quality_score"]
    for event in api_events:
        assert event["correlation_id"] == "req-deadbeef"
        assert event["user_id_hash"] == hash_user_id("student-01")
        assert event["session_id"] == "session-01"
        assert event["feature"] == "qa"
        assert event["model"]
        assert event["env"]
        assert "student-01" not in json.dumps(event)
