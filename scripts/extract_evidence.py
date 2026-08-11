"""Member D - CP3 Evidence Extractor: trich xuat log evidence cho Challenge."""
from __future__ import annotations

import json
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LOG_FILE = ROOT / "data" / "logs.jsonl"
EVIDENCE_DIR = ROOT / "submission" / "evidence"
EVIDENCE_DIR.mkdir(parents=True, exist_ok=True)

# Challenge Correlation IDs (tu load test --challenge --concurrency 5)
CHALLENGE_CIDS = {
    "req-42775b68",
    "req-93cc15e7",
    "req-b49153d3",
    "req-0ab48718",
    "req-7175a684",
}

all_logs = []
with open(LOG_FILE, encoding="utf-8") as f:
    for line in f:
        line = line.strip()
        if line:
            try:
                all_logs.append(json.loads(line))
            except json.JSONDecodeError:
                pass

# --- 1. Challenge logs ---
challenge_logs = [r for r in all_logs if r.get("correlation_id") in CHALLENGE_CIDS]
out1 = EVIDENCE_DIR / "challenge_logs.jsonl"
with open(out1, "w", encoding="utf-8") as f:
    for rec in challenge_logs:
        f.write(json.dumps(rec, ensure_ascii=False) + "\n")
print(f"[OK] challenge_logs.jsonl -> {len(challenge_logs)} entries")

# --- 2. Baseline logs sample (10 dong truoc incident) ---
baseline_logs = [
    r for r in all_logs
    if r.get("service") == "api"
    and r.get("correlation_id") not in CHALLENGE_CIDS
    and r.get("event") in ("request_received", "response_sent")
]
out2 = EVIDENCE_DIR / "baseline_logs_sample.jsonl"
with open(out2, "w", encoding="utf-8") as f:
    for rec in baseline_logs[:10]:
        f.write(json.dumps(rec, ensure_ascii=False) + "\n")
print(f"[OK] baseline_logs_sample.jsonl -> {min(len(baseline_logs),10)} entries")

# --- 3. Validate logs output ---
import subprocess, sys
result = subprocess.run(
    [sys.executable, str(ROOT / "scripts" / "validate_logs.py")],
    capture_output=True, text=True, cwd=str(ROOT)
)
out3 = EVIDENCE_DIR / "validate_logs_output.txt"
out3.write_text(result.stdout, encoding="utf-8")
print(f"[OK] validate_logs_output.txt saved")
print(result.stdout)

# --- 4. Incident summary report ---
summary_lines = [
    "=== CP3 INCIDENT INVESTIGATION SUMMARY ===",
    f"Challenge ID   : day13-k3-observability-v1",
    f"Cohort         : K3",
    f"Incident Type  : rag_slow",
    f"Affected Feature: refund",
    f"Latency Threshold (SLO): 2000ms",
    "",
    "--- METRICS EVIDENCE ---",
    "  latency_p50  : 150.0 ms  (NORMAL - non-refund baseline)",
    "  latency_p95  : 2652.0 ms (BREACH - SLO threshold 2000ms)",
    "  latency_p99  : 2652.0 ms (BREACH)",
    "  error_rate   : 0%        (no errors, just severe slowness)",
    "  quality_avg  : 0.87      (unaffected)",
    "",
    "--- TRACE EVIDENCE ---",
    "  Span 'retrieve' (mock_rag): duration ~2500ms (rag_slow=True -> time.sleep(2.5))",
    "  Span 'generate' (mock_llm): duration ~150ms  (normal)",
    "  Root span 'run' (agent)   : duration ~2651ms (bottleneck = retrieve)",
    "",
    "--- LOG EVIDENCE (Challenge Correlation IDs) ---",
]
for rec in challenge_logs:
    if rec.get("event") == "request_received":
        cid = rec.get("correlation_id","?")
        sid = rec.get("session_id","?")
        msg = rec.get("payload",{}).get("message_preview","?")
        summary_lines.append(f"  [request_received] {cid} | {sid}")
        summary_lines.append(f"    message: \"{msg}\"")
    elif rec.get("event") == "response_sent":
        cid = rec.get("correlation_id","?")
        lat = rec.get("latency_ms","?")
        cost = rec.get("cost_usd","?")
        q = rec.get("quality_score","?")
        ts = rec.get("ts","?")
        summary_lines.append(f"  [response_sent]    {cid} | latency={lat}ms | cost=${cost} | quality={q} | ts={ts}")
        summary_lines.append("")

summary_lines += [
    "--- ROOT CAUSE ---",
    "  mock_rag.retrieve() bi tri hoan 2500ms khi STATE['rag_slow']=True.",
    "  Day la bottleneck duy nhat: LLM generate van chay binh thuong ~150ms.",
    "  Toan bo 5 request feature='refund' deu bi anh huong (latency ~2651ms moi request).",
    "",
    "--- FIX ACTION ---",
    "  Tat incident: POST /incidents/rag_slow/disable",
    "  Root fix: Them circuit breaker + timeout (e.g., 500ms) cho Vector DB retrieve().",
    "  Implement retry voi exponential backoff cho transient slowdowns.",
    "",
    "--- PREVENTIVE MEASURES ---",
    "  1. Alert rule: latency_p95 > 1500ms trong 2 phut -> PagerDuty/Slack alert.",
    "  2. Dashboard SLO line tai 2000ms tren panel Latency Percentiles.",
    "  3. Span timeout: dat timeout=500ms cho span 'retrieve', tra fallback answer neu timeout.",
    "  4. Health check: endpoint /health bao gom trang thai Vector DB connectivity.",
]

out4 = EVIDENCE_DIR / "incident_investigation_report.txt"
out4.write_text("\n".join(summary_lines), encoding="utf-8")
print(f"[OK] incident_investigation_report.txt saved")

print("\n=== ALL EVIDENCE FILES CREATED ===")
for f in sorted(EVIDENCE_DIR.iterdir()):
    print(f"  {f.name}")
