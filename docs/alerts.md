# Template Alert và Runbook

Mỗi alert phải dựa trên triệu chứng người dùng hoặc SLO, không dựa trực tiếp vào tên implementation nội bộ.

## Alert 1

- Tên: `high_latency_p95`
- Severity: `warning`
- SLI/SLO liên quan: `latency_p95_ms` (mục tiêu P95 dưới 3 giây)
- Điều kiện và thời gian duy trì: Độ trễ P95 > 3000ms trong 5 phút.
- Ảnh hưởng tới người dùng: Trải nghiệm chatbot của người dùng bị gián đoạn, phản hồi chậm trễ, ảnh hưởng đến độ hài lòng.
- Ba bước kiểm tra đầu tiên:
  1. Kiểm tra dashboard xem có hiện tượng nghẽn mạng hoặc lượng truy cập tăng vọt đột ngột (traffic spike) tại endpoint `/chat` hay không.
  2. Mở Langfuse Dashboard xem trace waterfall của các request chậm để phân tách thời gian: xem thời gian trễ nằm ở phần truy vấn vector (RAG retrieve) hay phần sinh văn bản (LLM generate).
  3. Tìm kiếm trong tệp log `data/logs.jsonl` các dòng có `latency_ms` lớn hơn 3000 để lấy `correlation_id` cụ thể và kiểm tra các sự kiện liên quan.
- Mitigation tạm thời:
  - Nếu đang chạy test hoặc mô phỏng sự cố chậm, tắt incident RAG chậm bằng lệnh: `python scripts/inject_incident.py --scenario rag_slow --disable`.
  - Thiết lập cơ chế fallback bỏ qua tìm kiếm nâng cao (bypass RAG) để phục vụ bằng câu trả lời từ LLM trực tiếp nếu cơ sở dữ liệu vector gặp sự cố nặng.
- Owner: `on-call-engineer`

## Alert 2

- Tên: `elevated_error_rate`
- Severity: `critical`
- SLI/SLO liên quan: `error_rate_pct` (mục tiêu tỷ lệ lỗi dưới 2%)
- Điều kiện và thời gian duy trì: Tỷ lệ lỗi > 5% trong 3 phút.
- Ảnh hưởng tới người dùng: Người dùng liên tiếp gặp lỗi hệ thống (mã phản hồi 500), không thể sử dụng chatbot hoặc không nhận được câu trả lời.
- Ba bước kiểm tra đầu tiên:
  1. Gọi endpoint `/metrics` kiểm tra trường `error_breakdown` để biết loại lỗi chính đang xảy ra (ví dụ: `RuntimeError`).
  2. Lọc tệp log `data/logs.jsonl` tìm các sự kiện `request_failed` có cùng loại lỗi để đọc log payload chi tiết và thông tin stack trace.
  3. Kiểm tra kết nối tới các dịch vụ phụ trợ như Vector DB hoặc LLM API trên Langfuse traces để xác định xem lỗi xuất phát từ hệ thống của chúng ta hay từ nhà cung cấp bên ngoài.
- Mitigation tạm thời:
  - Nếu do lỗi giả lập sự cố, tắt incident bằng lệnh: `python scripts/inject_incident.py --scenario tool_fail --disable`.
  - Cấu hình bắt lỗi ngoại lệ ở tầng API để trả về câu trả lời thân thiện (fallback response) thay vì mã lỗi 500 trực tiếp cho người dùng.
- Owner: `on-call-engineer`

## Alert 3

- Tên: `cost_budget_exceeded`
- Severity: `warning`
- SLI/SLO liên quan: `daily_cost_usd` (mục tiêu chi phí dưới $2.5/ngày)
- Điều kiện và thời gian duy trì: Chi phí tích lũy trong ngày vượt quá $2.5 USD.
- Ảnh hưởng tới người dùng: Không ảnh hưởng trực tiếp ngay lập tức, nhưng có nguy cơ hệ thống bị khóa/ngắt do cạn kiệt ngân sách vận hành, dẫn đến dừng dịch vụ đột ngột.
- Ba bước kiểm tra đầu tiên:
  1. Truy cập `/metrics` để xem tổng chi phí `total_cost_usd` và tổng số token đầu vào/đầu ra (`tokens_in_total`, `tokens_out_total`).
  2. Truy cập Langfuse Dashboard để lọc danh sách các Trace có chi phí (cost) cao bất thường và xem các session ID/user ID tương ứng.
  3. Kiểm tra xem có người dùng nào đang gửi các prompt cực kỳ dài hoặc lặp đi lặp lại (spam/attack) hay có LLM response sinh từ vô hạn (infinite loop) hay không.
- Mitigation tạm thời:
  - Tắt sự cố giả lập tăng chi phí bằng lệnh: `python scripts/inject_incident.py --scenario cost_spike --disable`.
  - Tạm thời giới hạn số lượng token tối đa (`max_tokens`) cho mỗi request LLM hoặc bật chế độ giới hạn tần suất request (rate limiting) đối với các user_id có mức độ tiêu thụ bất thường.
- Owner: `team-lead`
