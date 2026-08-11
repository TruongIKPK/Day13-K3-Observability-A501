from __future__ import annotations

import os

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse, HTMLResponse
from structlog.contextvars import bind_contextvars

from .agent import LabAgent
from .incidents import disable, enable, status
from .logging_config import configure_logging, get_logger
from .metrics import record_error, snapshot
from .middleware import CorrelationIdMiddleware
from .pii import hash_user_id, summarize_text
from .schemas import ChatRequest, ChatResponse
from .tracing import tracing_enabled

configure_logging()
log = get_logger()
app = FastAPI(title="Day 13 Observability Lab")
app.add_middleware(CorrelationIdMiddleware)
agent = LabAgent()


@app.on_event("startup")
async def startup() -> None:
    log.info(
        "app_started",
        service=os.getenv("APP_NAME", "day13-observability-lab"),
        env=os.getenv("APP_ENV", "dev"),
        payload={"tracing_enabled": tracing_enabled()},
    )


@app.get("/health")
async def health() -> dict:
    return {"ok": True, "tracing_enabled": tracing_enabled(), "incidents": status()}


@app.get("/metrics")
async def metrics() -> dict:
    return snapshot()


@app.post("/chat", response_model=ChatResponse)
async def chat(request: Request, body: ChatRequest) -> ChatResponse:
    bind_contextvars(
        user_id_hash=hash_user_id(body.user_id),
        session_id=body.session_id,
        feature=body.feature,
        model=agent.model,
        env=os.getenv("APP_ENV", "dev"),
    )
    
    log.info(
        "request_received",
        service="api",
        payload={"message_preview": summarize_text(body.message)},
    )
    try:
        result = agent.run(
            user_id=body.user_id,
            feature=body.feature,
            session_id=body.session_id,
            message=body.message,
        )
        log.info(
            "response_sent",
            service="api",
            latency_ms=result.latency_ms,
            tokens_in=result.tokens_in,
            tokens_out=result.tokens_out,
            cost_usd=result.cost_usd,
            quality_score=result.quality_score,
            payload={"answer_preview": summarize_text(result.answer)},
        )
        return ChatResponse(
            answer=result.answer,
            correlation_id=request.state.correlation_id,
            latency_ms=result.latency_ms,
            tokens_in=result.tokens_in,
            tokens_out=result.tokens_out,
            cost_usd=result.cost_usd,
            quality_score=result.quality_score,
        )
    except Exception as exc:  # pragma: no cover
        error_type = type(exc).__name__
        record_error(error_type)
        log.error(
            "request_failed",
            service="api",
            error_type=error_type,
            payload={"detail": str(exc), "message_preview": summarize_text(body.message)},
        )
        raise HTTPException(status_code=500, detail=error_type) from exc


@app.post("/incidents/{name}/enable")
async def enable_incident(name: str) -> JSONResponse:
    try:
        enable(name)
        log.warning("incident_enabled", service="control", payload={"name": name})
        return JSONResponse({"ok": True, "incidents": status()})
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@app.post("/incidents/{name}/disable")
async def disable_incident(name: str) -> JSONResponse:
    try:
        disable(name)
        log.warning("incident_disabled", service="control", payload={"name": name})
        return JSONResponse({"ok": True, "incidents": status()})
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@app.get("/api/dashboard-data")
async def get_dashboard_data() -> dict:
    from pathlib import Path
    import json
    import statistics
    from collections import Counter
    
    log_file = Path("data/logs.jsonl")
    if not log_file.exists():
        return {
            "traffic": 0,
            "latency_p50": 0.0,
            "latency_p95": 0.0,
            "latency_p99": 0.0,
            "avg_cost_usd": 0.0,
            "total_cost_usd": 0.0,
            "tokens_in_total": 0,
            "tokens_out_total": 0,
            "error_rate_pct": 0.0,
            "error_breakdown": {},
            "quality_avg": 0.0
        }

    latencies = []
    costs = []
    tokens_in = 0
    tokens_out = 0
    quality_scores = []
    errors = Counter()
    requests_received = 0
    requests_failed = 0

    with log_file.open("r", encoding="utf-8") as f:
        for line in f:
            if not line.strip():
                continue
            try:
                rec = json.loads(line)
            except json.JSONDecodeError:
                continue

            event = rec.get("event")
            service = rec.get("service")

            if service == "api":
                if event == "request_received":
                    requests_received += 1
                elif event == "request_failed":
                    requests_failed += 1
                    error_type = rec.get("error_type", "UnknownError")
                    errors[error_type] += 1
                elif event == "response_sent":
                    if "latency_ms" in rec:
                        latencies.append(rec["latency_ms"])
                    if "cost_usd" in rec:
                        costs.append(rec["cost_usd"])
                    if "tokens_in" in rec:
                        tokens_in += rec["tokens_in"]
                    if "tokens_out" in rec:
                        tokens_out += rec["tokens_out"]
                    if "quality_score" in rec:
                        quality_scores.append(rec["quality_score"])

    def get_percentile(values, p):
        if not values:
            return 0.0
        sorted_vals = sorted(values)
        idx = max(0, min(len(sorted_vals) - 1, round((p / 100) * len(sorted_vals) + 0.5) - 1))
        return float(sorted_vals[idx])

    p50 = get_percentile(latencies, 50)
    p95 = get_percentile(latencies, 95)
    p99 = get_percentile(latencies, 99)

    error_rate = (requests_failed / requests_received * 100) if requests_received > 0 else 0.0
    quality_avg = statistics.mean(quality_scores) if quality_scores else 0.0

    return {
        "traffic": requests_received,
        "latency_p50": round(p50, 1),
        "latency_p95": round(p95, 1),
        "latency_p99": round(p99, 1),
        "avg_cost_usd": round(statistics.mean(costs), 4) if costs else 0.0,
        "total_cost_usd": round(sum(costs), 4),
        "tokens_in_total": tokens_in,
        "tokens_out_total": tokens_out,
        "error_rate_pct": round(error_rate, 2),
        "error_breakdown": dict(errors),
        "quality_avg": round(quality_avg, 3)
    }


@app.get("/dashboard", response_class=HTMLResponse)
async def get_dashboard():
    from pathlib import Path
    dashboard_path = Path("app/dashboard.html")
    if not dashboard_path.exists():
        return HTMLResponse("Dashboard HTML file not found", status_code=404)
    return HTMLResponse(dashboard_path.read_text(encoding="utf-8"))
