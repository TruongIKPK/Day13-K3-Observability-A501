# Báo Cáo Day 13 Observability — Nhóm A501

## 1. Thông tin nhóm

| Trường | Giá trị |
|---|---|
| **Tên nhóm** | A501 |
| **Repository URL** | https://github.com/TruongIKPK/Day13-K3-Observability-A501 |
| **Commit SHA cuối** | 802be8a |

### Thành viên và phân công:

| Thành viên | Mã học viên | Vai trò |
|---|---|---|
| Nguyễn Khánh Toàn | 2A202601843 | Thành viên A — Logging & Middleware (CP1) |
| Trần Duy Trường | 2A202601247 | Thành viên B — PII Scrubbing & Security (CP1) |
| Lê Nguyễn Phi Trường | 2A202601541 | Thành viên C — Metrics, Tracing, Dashboard & Alerts (CP2) |
| Hồ Văn Thi | 2A202601907 | Thành viên D — QA, Load Test, Dashboard Spec, Điều tra Incident CP3, REPORT.md |

---

## 2. Kết quả kỹ thuật (Technical Scorecard)

| Chỉ số | Giá trị | Trạng thái |
|---|---|---|
| **validate_logs.py score** | **100/100** | ✅ PASSED |
| **validate_dashboard.py** | **6/6 panel hợp lệ** | ✅ PASSED |
| **Tổng log records phân tích** | 33 records | ✅ |
| **Unique Correlation IDs** | 18 IDs | ✅ |
| **PII leaks còn lại** | **0** | ✅ CLEAN |
| **Records thiếu required fields** | 0 | ✅ |
| **Records thiếu enrichment** | 0 | ✅ |
| **Tổng số traces (Langfuse)** | 14+ traces | ✅ |
| **Số PII pattern được bảo vệ** | 6 loại | ✅ |

**Link dashboard:** `http://localhost:8000/dashboard` (local)
**Langfuse Cloud:** `https://us.cloud.langfuse.com/project/cmso302pg034jad0dm6qur599`

---

## 3. Logging và Tracing (CP1)

> Phần này do **Thành viên A (Nguyễn Khánh Toàn)** và **Thành viên B (Trần Duy Trường)** triển khai.
> Thành viên D (Hồ Văn Thi) thực hiện QA kiểm tra kết quả bằng `validate_logs.py`.

### 3.1 Correlation ID — [Thành viên A: Nguyễn Khánh Toàn]

Mỗi HTTP request được `CorrelationIdMiddleware` gán một `correlation_id` duy nhất
theo định dạng `req-<8-char-hex>`. Header `x-request-id` từ client được validate
bằng regex `^req-[0-9a-f]{8}$`; nếu không hợp lệ, middleware tự sinh UUID mới
từ `uuid.uuid4().hex[:8]`.

Middleware còn thực hiện:
- Clear context vars trước mỗi request (`clear_contextvars`)
- Bind `correlation_id` vào structlog context (`bind_contextvars`)
- Gán `correlation_id` vào `request.state` để trả về trong response body
- Thêm header `x-request-id` và `x-response-time-ms` vào HTTP response

**Ví dụ log thực tế từ `data/logs.jsonl` (QA verify bởi Thành viên D):**

```json
{"service": "api", "payload": {"message_preview": "What is your refund policy?"}, "event": "request_received", "user_id_hash": "026c7a407135", "env": "dev", "session_id": "k3-challenge-s01", "correlation_id": "req-b49153d3", "feature": "refund", "model": "claude-sonnet-4-5", "level": "info", "ts": "2026-08-11T03:41:14.842479Z"}
```

**Response log tương ứng (cùng correlation_id — xác nhận propagation):**

```json
{"service": "api", "latency_ms": 2651, "tokens_in": 29, "tokens_out": 121, "cost_usd": 0.001902, "quality_score": 0.9, "event": "response_sent", "user_id_hash": "026c7a407135", "env": "dev", "session_id": "k3-challenge-s01", "correlation_id": "req-b49153d3", "feature": "refund", "model": "claude-sonnet-4-5", "level": "info", "ts": "2026-08-11T03:41:17.495502Z"}
```

**Kết quả QA (Thành viên D):** 18 unique correlation IDs, 0 record thiếu correlation_id — **PASSED**.

### 3.2 PII Redaction — [Thành viên B: Trần Duy Trường]

Hàm `scrub_value()` trong `app/pii.py` duyệt đệ quy toàn bộ event dict trước khi
ghi log. 6 PII patterns được bảo vệ:

| Pattern | Ví dụ input | Output trong log |
|---|---|---|
| email | student@vinuni.edu.vn | [REDACTED_EMAIL] |
| phone_vn | 0987654321 | [REDACTED_PHONE_VN] |
| cccd | 123456789012 | [REDACTED_CCCD] |
| credit_card | 4111 1111 1111 1111 | [REDACTED_CREDIT_CARD] |
| passport | B1234567 | [REDACTED_PASSPORT] |
| address | address: 123 Le Loi | [REDACTED_ADDRESS] |

**Bằng chứng PII scrubbing thực tế (QA verify bởi Thành viên D):**

Query `u01` — message chứa email thật `student@vinuni.edu.vn`:
```json
{"payload": {"message_preview": "What is your refund policy? My email is [REDACTED_EMAIL]"}, "event": "request_received", "user_id_hash": "2055254ee30a", "session_id": "s01", "correlation_id": "req-c6e2c7d7", "feature": "qa", "level": "info", "ts": "2026-08-11T03:40:11.902Z"}
```

Query `u09` — message chứa thẻ tín dụng `4111 1111 1111 1111`:
```json
{"payload": {"message_preview": "What is the policy for PII and credit card [REDACTED_CREDIT_CARD]?"}, "event": "request_received", "correlation_id": "req-7c623f1d", "feature": "qa", "level": "info", "ts": "2026-08-11T03:40:22.759Z"}
```

**Kết quả QA (Thành viên D):** Potential PII leaks detected: 0 — **PASSED**.

### 3.3 Trace Waterfall — [Thành viên C: Lê Nguyễn Phi Trường]

Kiến trúc span 3 lớp lồng nhau được Thành viên C thiết kế:

```
Trace: run (LabAgent.run) -- @observe(as_type="generation")
    Thời gian tổng: ~2651ms (khi rag_slow) / ~150ms (bình thường)
    Metadata: user_id_hash, session_id, tags, prompt_name, prompt_version
    |
    +-- Span: retrieve (mock_rag.retrieve) -- @observe(as_type="span")
    |   Thời gian bình thường: <5ms
    |   Thời gian khi rag_slow: ~2500ms  <-- BOTTLENECK
    |
    +-- Span: generate (FakeLLM.generate) -- @observe(as_type="span")
        Thời gian: ~150ms (cố định)
        Metadata: model, tokens_in, tokens_out, cost_usd
```

Khi `STATE["rag_slow"] = True`, span `retrieve` ghi nhận duration ~2500ms,
giúp xác định ngay bottleneck nằm ở tầng RAG, không phải LLM.

---

## 4. Prompt Versioning — [Thành viên C: Lê Nguyễn Phi Trường]

| Thuộc tính | Giá trị |
|---|---|
| **Prompt name** | day13-chat |
| **Version baseline (v1)** | Labels: `baseline`, `production` |
| **Version candidate (v2)** | Label: `candidate` |
| **Promote command** | `client.update_prompt(name="day13-chat", version=2, new_labels=["production", "candidate"])` |
| **Rollback command** | `client.update_prompt(name="day13-chat", version=1, new_labels=["production", "baseline"])` |

Mỗi trace ghi đầy đủ `prompt_name`, `prompt_label`, `prompt_version`, `prompt_source`
trong generation metadata, cho phép audit chính xác prompt nào đã được dùng tại mỗi thời điểm.

---

## 5. Dashboard, SLO và Alert Rules — [Thành viên C: Lê Nguyễn Phi Trường]

> Dashboard Spec (`docs/dashboard-spec.md`) do **Thành viên D (Hồ Văn Thi)** soạn thảo.
> Triển khai kỹ thuật metrics, alert rules, runbook do **Thành viên C (Lê Nguyễn Phi Trường)**.

### 5.1 Dashboard — 6 Panel

| # | Panel | Metric | SLO Threshold |
|---|---|---|---|
| 1 | Latency Percentiles | latency_ms P50/P95/P99 | P95 ≤ 3000ms |
| 2 | Request Traffic | count(request_received) | rate ≥ 1 req/min |
| 3 | Error Rate & Breakdown | error_rate_pct, error_type | ≤ 2% |
| 4 | Cost Over Time | sum(cost_usd) | ≤ $2.50/ngày |
| 5 | Input & Output Tokens | tokens_in_total, tokens_out_total | ≤ 50.000 tokens |
| 6 | Quality Proxy | mean(quality_score) | ≥ 0.75 |

**Kết quả validator (chạy bởi Thành viên D):** `HỢP LỆ: 6/6 panel có trong dashboard contract.`

### 5.2 SLO Configuration (`config/slo.yaml`) — Thành viên C

```yaml
service: day13-observability-lab
window: 28d
slis:
  latency_p95_ms:    { objective: 3000,  target: 99.5 }
  error_rate_pct:    { objective: 2,     target: 99.0 }
  daily_cost_usd:    { objective: 2.5,   target: 100.0 }
  quality_score_avg: { objective: 0.75,  target: 95.0 }
```

### 5.3 Alert Rules và Runbook — Thành viên C (`config/alert_rules.yaml`, `docs/alerts.md`)

| Alert | Điều kiện | Hành động |
|---|---|---|
| HighLatencyP95 | latency_p95 > 1500ms trong 2 phút | Kiểm tra span `retrieve` trên Langfuse |
| HighErrorRate | error_rate_pct > 2% | Kiểm tra log `request_failed`, xem `error_type` |
| CostSpike | total_cost_usd > 2.0 trong 1h | Kiểm tra `tokens_out` — có thể `cost_spike` incident |
| LowQuality | quality_avg < 0.70 | Kiểm tra span `retrieve` — có thể RAG trả về fallback |

---

## 6. Điều tra Challenge CP3 — [Thành viên D: Hồ Văn Thi]

> Đây là phần việc chính của Thành viên D.

### 6.1 Thông tin Challenge

| Trường | Giá trị |
|---|---|
| **Challenge ID** | day13-k3-observability-v1 |
| **Cohort** | K3 |
| **Incident được inject** | rag_slow |
| **Feature bị ảnh hưởng** | refund |
| **Latency threshold (SLO)** | 2000ms |

### 6.2 Bước 1 — Phát hiện triệu chứng qua METRICS

**Lệnh chạy:**
```bash
python scripts/inject_incident.py
python scripts/load_test.py --challenge --concurrency 5
curl http://127.0.0.1:8000/metrics
```

**Metrics snapshot thực tế (`submission/evidence/metrics_snapshot_after_incident.json`):**

```json
{
  "traffic": 15,
  "latency_p50": 150.0,
  "latency_p95": 2652.0,
  "latency_p99": 2652.0,
  "avg_cost_usd": 0.002,
  "total_cost_usd": 0.0301,
  "tokens_in_total": 492,
  "tokens_out_total": 1907,
  "error_breakdown": {},
  "quality_avg": 0.8733
}
```

**Phân tích triệu chứng:**
- `latency_p95 = 2652ms` → **VI PHẠM SLO** (threshold 2000ms theo `config/challenge.json`)
- `latency_p50 = 150ms` → baseline bình thường — các request không thuộc feature `refund` không bị ảnh hưởng
- `error_breakdown = {}` → **Không có HTTP 500** — hệ thống vẫn trả về đúng nhưng rất CHẬM
- `quality_avg = 0.87` → Chất lượng phản hồi không suy giảm

**Kết luận bước 1:** Hệ thống bị **high tail latency** nghiêm trọng ở P95/P99, không kèm lỗi.
Pattern này chỉ ra bottleneck ở tầng xử lý (I/O blocking), không phải lỗi logic.

### 6.3 Bước 2 — Khoanh vùng Span bị nghẽn qua TRACES

Từ Langfuse Dashboard, trace waterfall cho thấy:

| Span | Feature bình thường | Feature `refund` khi `rag_slow` |
|---|---|---|
| `run` (root generation) | ~155ms | ~2651ms |
| `retrieve` (RAG span) | <5ms | **~2500ms** ← BOTTLENECK |
| `generate` (LLM span) | ~150ms | ~150ms (bình thường) |

**Trace IDs từ challenge load test (concurrency=5, feature=refund):**

| Correlation ID | Session ID | Latency (ms) | Timestamp |
|---|---|---|---|
| req-42775b68 | k3-challenge-s04 | **2651** | 2026-08-11T03:41:14.840Z |
| req-93cc15e7 | k3-challenge-s05 | **2651** | 2026-08-11T03:41:25.464Z |
| req-b49153d3 | k3-challenge-s01 | **2651** | 2026-08-11T03:41:17.495Z |
| req-0ab48718 | k3-challenge-s03 | **2651** | 2026-08-11T03:41:20.150Z |
| req-7175a684 | k3-challenge-s02 | **2652** | 2026-08-11T03:41:22.809Z |

**Kết luận bước 2:** Span `retrieve` trong `mock_rag.py` là điểm chịu toàn bộ độ trễ.
Span `generate` không bị ảnh hưởng → LLM hoàn toàn bình thường.

### 6.4 Bước 3 — Xác nhận Root Cause qua LOGS

**Log lines thực tế cho `correlation_id: req-b49153d3` (session k3-challenge-s01):**

```json
{"service": "api", "payload": {"message_preview": "What is your refund policy?"}, "event": "request_received", "user_id_hash": "026c7a407135", "env": "dev", "session_id": "k3-challenge-s01", "correlation_id": "req-b49153d3", "feature": "refund", "model": "claude-sonnet-4-5", "level": "info", "ts": "2026-08-11T03:41:14.842479Z"}
```

```json
{"service": "api", "latency_ms": 2651, "tokens_in": 29, "tokens_out": 121, "cost_usd": 0.001902, "quality_score": 0.9, "event": "response_sent", "user_id_hash": "026c7a407135", "env": "dev", "session_id": "k3-challenge-s01", "correlation_id": "req-b49153d3", "feature": "refund", "model": "claude-sonnet-4-5", "level": "info", "ts": "2026-08-11T03:41:17.495502Z"}
```

**Delta time:** `17.495 - 14.842 = 2.653 giây`
→ Khớp chính xác với `time.sleep(2.5)` trong `mock_rag.retrieve()`

**Xác minh từ source code (`app/mock_rag.py`):**

```python
@observe(as_type="span")
def retrieve(message: str) -> list[str]:
    if STATE["tool_fail"]:
        raise RuntimeError("Vector store timeout")
    if STATE["rag_slow"]:
        time.sleep(2.5)   # <-- ROOT CAUSE: blocking I/O 2500ms
    lowered = message.lower()
    for key, docs in CORPUS.items():
        if key in lowered:
            return docs
    return ["No domain document matched. Use general fallback answer."]
```

**Root Cause xác nhận:** Flag `STATE["rag_slow"] = True` được kích hoạt bởi
`POST /incidents/rag_slow/enable`. Hàm `retrieve()` thực thi `time.sleep(2.5)` —
mô phỏng Vector DB bị nghẽn (overload / network latency).
Toàn bộ 5 requests thuộc feature `refund` đều bị trì hoãn **2500ms tại tầng RAG**,
khiến `latency_p95 = 2652ms > SLO 2000ms`.

### 6.5 Tổng kết điều tra

| Mục | Nội dung |
|---|---|
| **Triệu chứng** | `latency_p95 = 2652ms` (vi phạm SLO 2000ms); không có HTTP error |
| **Span bottleneck** | `retrieve` (RAG) — duration ~2500ms thay vì <5ms bình thường |
| **Root Cause** | `STATE["rag_slow"]=True` → `time.sleep(2.5)` trong `mock_rag.retrieve()` — mô phỏng Vector DB overload |
| **Fix Action** | `POST /incidents/rag_slow/disable` để tắt ngay. Production fix: thêm timeout 500ms + circuit breaker cho Vector DB client |
| **Preventive Measures** | (1) Alert `latency_p95 > 1500ms` trong 2 phút → oncall; (2) Span timeout 500ms với graceful fallback answer; (3) Health check Vector DB connectivity trong `/health`; (4) Dashboard SLO threshold line hiển thị rõ ràng tại 2000ms |

---

## 7. Đóng góp cá nhân

| Thành viên | Mã học viên | Phần việc chính | Files liên quan | Điều đã học |
|---|---|---|---|---|
| **Nguyễn Khánh Toàn** (Member A) | 2A202601843 | Triển khai `CorrelationIdMiddleware`: inject `req-<8hex>`, validate header `x-request-id`, `bind_contextvars`, `clear_contextvars`, header `x-response-time-ms`. Cấu hình structlog pipeline: `merge_contextvars` → `scrub_event` → `JsonlFileProcessor` → `JSONRenderer` | `app/middleware.py`, `app/logging_config.py` | Cách structlog processor chain hoạt động; tại sao `merge_contextvars` phải đứng đầu chain để inject `correlation_id` vào mọi log event |
| **Trần Duy Trường** (Member B) | 2A202601247 | PII Scrubbing: 6 regex patterns (email, phone_vn, cccd, credit_card, passport, address). Viết `scrub_text()`, `scrub_value()` đệ quy (dict/list/tuple/set), `hash_user_id()` SHA-256. Global scrubbing qua structlog processor `scrub_event` | `app/pii.py` | Tầm quan trọng của recursive scrubbing cho nested objects; tại sao hash thay vì REDACT với user_id |
| **Lê Nguyễn Phi Trường** (Member C) | 2A202601541 | Langfuse tracing: `@observe` trên `run`/`retrieve`/`generate`, `update_current_trace/generation`, prompt versioning v1/v2, label promotion & rollback. Metrics: `record_request`, `error_rate_pct`, `snapshot`, percentile computation. Dashboard 6 panel, SLO yaml, alert rules yaml, runbook | `app/tracing.py`, `app/agent.py`, `app/metrics.py`, `app/prompt_management.py`, `config/slo.yaml`, `config/alert_rules.yaml`, `docs/alerts.md` | Trace waterfall anatomy; nested spans giúp isolate bottleneck; phân biệt SLI/SLO/SLA |
| **Hồ Văn Thi** (Member D) | **2A202601907** | QA toàn bộ CP1: chạy `validate_logs.py`, verify Correlation ID propagation, kiểm tra PII scrubbing. Soạn thảo `docs/dashboard-spec.md` (6 nhóm chỉ số). Chủ trì điều tra CP3: inject `rag_slow`, load test `--challenge --concurrency 5`, phân tích Metrics → Traces → Logs, xác định root cause. Tổng hợp `submission/REPORT.md` và evidence files | `scripts/extract_evidence.py`, `submission/REPORT.md`, `submission/evidence/`, `docs/dashboard-spec.md` | Luồng điều tra SRE thực tế: metrics phát hiện triệu chứng → traces khoanh vùng layer → logs xác nhận root cause bằng timestamp delta |

---

## 8. Phụ lục — Evidence Files

| File | Mô tả | Người tạo |
|---|---|---|
| `evidence/validate_logs_output.txt` | Output `validate_logs.py` — score 100/100 | Thành viên D |
| `evidence/validate_dashboard_output.txt` | Output `validate_dashboard.py` — 6/6 panel hợp lệ | Thành viên D |
| `evidence/metrics_snapshot_after_incident.json` | Metrics snapshot sau khi inject `rag_slow` (`latency_p95=2652ms`) | Thành viên D |
| `evidence/challenge_logs.jsonl` | 10 log entries của 5 challenge requests (request_received + response_sent) | Thành viên D |
| `evidence/baseline_logs_sample.jsonl` | 10 log entries baseline bình thường để so sánh | Thành viên D |
| `evidence/incident_investigation_report.txt` | Báo cáo điều tra incident đầy đủ (text format) | Thành viên D |
