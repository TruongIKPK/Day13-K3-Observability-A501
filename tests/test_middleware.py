from __future__ import annotations

import re

from fastapi import FastAPI, Request
from fastapi.testclient import TestClient

from app.middleware import CorrelationIdMiddleware


def build_app() -> FastAPI:
    app = FastAPI()
    app.add_middleware(CorrelationIdMiddleware)

    @app.get("/")
    async def root(request: Request) -> dict[str, str]:
        return {"correlation_id": request.state.correlation_id}

    return app


def test_middleware_propagates_valid_correlation_id() -> None:
    with TestClient(build_app()) as client:
        response = client.get("/", headers={"x-request-id": "req-DEADBEEF"})

    assert response.status_code == 200
    assert response.json()["correlation_id"] == "req-deadbeef"
    assert response.headers["x-request-id"] == "req-deadbeef"
    assert int(response.headers["x-response-time-ms"]) >= 0


def test_middleware_replaces_invalid_correlation_id() -> None:
    with TestClient(build_app()) as client:
        response = client.get("/", headers={"x-request-id": "customer-email@example.com"})

    correlation_id = response.headers["x-request-id"]
    assert correlation_id != "customer-email@example.com"
    assert re.fullmatch(r"req-[0-9a-f]{8}", correlation_id)
