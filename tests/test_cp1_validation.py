from __future__ import annotations

import re
from pathlib import Path

from fastapi.testclient import TestClient

from app import logging_config
from app.agent import AgentResult
from app.main import app
from scripts import validate_logs


def test_fresh_cp1_logs_reach_full_validator_score(
    monkeypatch,
    tmp_path: Path,
    capsys,
) -> None:
    log_path = tmp_path / "logs.jsonl"
    monkeypatch.setattr(logging_config, "LOG_PATH", log_path)
    monkeypatch.setattr(validate_logs, "LOG_PATH", log_path)
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

    payloads = (
        {
            "user_id": "student-one@vinuni.edu.vn",
            "session_id": "session-01",
            "feature": "qa",
            "message": "Contact student-one@vinuni.edu.vn",
        },
        {
            "user_id": "student-two",
            "session_id": "session-02",
            "feature": "summary",
            "message": "Call 090 123 4567",
        },
    )

    with TestClient(app) as client:
        responses = [client.post("/chat", json=payload) for payload in payloads]

    assert all(response.status_code == 200 for response in responses)
    validate_logs.main()
    output = capsys.readouterr().out

    assert "Records with missing required fields: 0" in output
    assert "Records with missing enrichment (context): 0" in output
    match = re.search(r"Unique correlation IDs found: (\d+)", output)
    assert match and int(match.group(1)) >= 2
    assert "Potential PII leaks detected: 0" in output
    assert "Estimated Score: 100/100" in output
