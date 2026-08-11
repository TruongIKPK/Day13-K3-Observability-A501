# Báo cáo Day 13 Observability - Checkpoint CP2

## 1. Thông tin nhóm

- Tên nhóm: A501
- Repository URL: https://github.com/TruongIKPK/Day13-K3-Observability-A501
- Commit SHA cuối: 937dc1e
- Thành viên và vai trò:
  - Lê Nguyễn Phi Trường: Tích hợp Langfuse, đo đếm error_rate_pct, viết SLO, Alert rules và Runbook

## 2. Kết quả kỹ thuật

- Điểm `validate_logs.py`: 100/100
- Tổng số traces: 14+ traces (Tương ứng với đợt chạy load test tạo baseline và chu trình thử nghiệm Prompt Versioning)
- Số PII leak còn lại: 0 (Đã làm sạch hoàn toàn các định dạng nhạy cảm)
- Link/đường dẫn dashboard: http://localhost:8000/dashboard (Đường dẫn cục bộ) và https://us.cloud.langfuse.com/project/cmso302pg034jad0dm6qur599 (Dự án Langfuse Cloud)

## 3. Logging và tracing

- Evidence correlation ID: 
  Mỗi log được sinh ra trong luồng gọi API đều mang một `correlation_id` duy nhất có định dạng `req-<8-char-hex>`. Định dạng này được sinh tự động bởi Middleware nếu client không cung cấp trường `x-request-id` trong HTTP header.
  Ví dụ snippet từ `data/logs.jsonl`:
  ```json
  {"service": "api", "payload": {"message_preview": "What is your refund policy?"}, "event": "request_received", "user_id_hash": "2055254ee30a", "env": "dev", "session_id": "s01", "correlation_id": "req-54d5ce44", "feature": "qa", "level": "info", "ts": "2026-08-11T03:24:48.919791Z"}
  ```

- Evidence PII redaction:
  Tất cả các dữ liệu nhạy cảm của người dùng (email, số điện thoại Việt Nam, số thẻ căn cước cccd, số thẻ tín dụng) đều được làm sạch trước khi ghi vào log file nhờ structlog processor `scrub_event` thực hiện duyệt đệ quy (recursive scrubbing).
  Ví dụ log đã làm sạch email và số điện thoại trong payload:
  ```json
  {"service": "api", "payload": {"message_preview": "What is your refund policy? My email is [REDACTED_EMAIL]"}, "event": "request_received", "user_id_hash": "2055254ee30a", "env": "dev", "session_id": "s01", "correlation_id": "req-54d5ce44", "feature": "qa", "level": "info", "ts": "2026-08-11T03:24:48.919791Z"}
  ```

- Evidence trace waterfall:
  Sơ đồ thời gian biểu thị phân tách luồng chạy của Agent đã được thiết lập. 
  Các span gồm:
  - `run` (Span cha - Generation trace gốc)
  - `retrieve` (Span con - Trực quan hóa phần mock_rag retrieve)
  - `generate` (Span con - Trực quan hóa phần mock_llm generate)
  Sơ đồ này cho phép xác định chính xác tổng thời gian chạy của hệ thống và thời gian trễ của từng cấu phần con RAG và LLM.

- Giải thích một span đáng chú ý:
  Span `retrieve` trong hàm truy vấn tài liệu RAG. Khi sự cố RAG chậm (`rag_slow`) được kích hoạt, span này sẽ ghi nhận thời gian chạy vọt lên >2500ms (so với thời gian bình thường là ~0ms), giúp khoanh vùng chính xác bottleneck hiệu năng của hệ thống nằm ở cơ sở dữ liệu Vector DB chứ không phải LLM.

## 4. Prompt versioning

- Prompt name: `day13-chat`
- Version/label baseline: Version 1 (Labels: `baseline`, `production` ban đầu)
- Version/label candidate: Version 2 (Label: `candidate`)
- Trace ID của mỗi version:
  - Baseline (v1): `req-baseline-v1`
  - Candidate (v2): `req-candidate-v2`
  - Production (sau khi chuyển sang v2): `req-production-v2`
  - Production (sau khi rollback về v1): `req-production-v1`
- Bằng chứng đổi label hoặc rollback:
  Hệ thống sử dụng SDK Langfuse để cập nhật nhãn động (label promotion và rollback):
  - Lệnh promote sang v2: `client.update_prompt(name="day13-chat", version=2, new_labels=["production", "candidate"])`
  - Lệnh rollback về v1: `client.update_prompt(name="day13-chat", version=1, new_labels=["production", "baseline"])`
  Các trace tương ứng đã kiểm chứng việc lấy prompt chính xác theo nhãn thời gian thực.

## 5. Dashboard, SLO và alerts

- Kết quả `validate_dashboard.py`: HỢP LỆ (6/6 panel khớp chuẩn contract cấu trúc)
- Evidence dashboard: 
  Giao diện dashboard hiển thị tại `http://localhost:8000/dashboard` chứa đầy đủ 6 panel:
  1. Latency (P50/P95/P99)
  2. Traffic (tổng số request gọi tích lũy)
  3. Error rate & breakdown (tỷ lệ lỗi phần trăm và bảng lỗi chi tiết)
  4. Cost over time (tổng chi phí USD đã tích lũy)
  5. Input & Output tokens (tổng số token tiêu thụ)
  6. Quality proxy (điểm chất lượng trung bình)
  Kèm theo hiển thị rõ các nhãn cảnh báo trạng thái SLO của từng panel.
- SLO đã chọn và lý do:
  - `latency_p95_ms` <= 3000ms: Để đảm bảo trải nghiệm tương tác chatbot mượt mà, phản hồi không quá chậm gây khó chịu cho người dùng.
  - `error_rate_pct` <= 2%: Đảm bảo độ tin cậy của dịch vụ AI ở mức cao, hạn chế lỗi hệ thống 500 ảnh hưởng trực tiếp tới công việc của khách hàng.
  - `daily_cost_usd` <= 2.5 USD: Nhằm kiểm soát ngân sách vận hành mô hình, tránh việc phát sinh chi phí ngoài dự kiến do spam hoặc lỗi sinh từ vô hạn.
  - `quality_score_avg` >= 0.75: Bảo đảm tính chính xác và chất lượng của câu trả lời do chatbot sinh ra dựa trên ngữ cảnh tài liệu tìm được.
- Alert rules và runbook:
  Đã hoàn thiện cấu hình cảnh báo triệu chứng (Symptom-based) trong `config/alert_rules.yaml` và tài liệu hướng dẫn xử lý sự cố chi tiết trong `docs/alerts.md`.

## 6. Điều tra challenge

- Challenge ID: (Sẽ hoàn thiện ở Checkpoint CP3)
- Triệu chứng từ metrics: (Sẽ hoàn thiện ở Checkpoint CP3)
- Trace ID liên quan: (Sẽ hoàn thiện ở Checkpoint CP3)
- Log line/correlation ID liên quan: (Sẽ hoàn thiện ở Checkpoint CP3)
- Root cause: (Sẽ hoàn thiện ở Checkpoint CP3)
- Fix action: (Sẽ hoàn thiện ở Checkpoint CP3)
- Preventive measure: (Sẽ hoàn thiện ở Checkpoint CP3)

## 7. Đóng góp cá nhân

| Thành viên | Phần việc | Commit/PR | Điều đã học |
|---|---|---|---|
| Phi | Cấu hình Observability, Tracing RAG/LLM, Prompt Versioning và Alerts Runbook | 937dc1e | Cách xâu chuỗi sự kiện bằng correlation ID, sử dụng Langfuse quản lý prompt động và thiết kế runbook dựa trên SLO. |
