# Yêu cầu và Thiết kế Dashboard

Contract kiểm tra bằng máy nằm tại `config/dashboard.yaml`. Hướng dẫn chi tiết dựng và kiểm tra runtime nằm tại [DASHBOARD_SETUP.md](DASHBOARD_SETUP.md).

Dashboard chính hiển thị đầy đủ 6 nhóm panel giám sát hiệu năng hệ thống:

## 1. Latency Percentiles (Độ trễ hệ thống)
- **Tên Panel:** Latency percentiles
- **Đơn vị:** ms
- **Khoảng thời gian mặc định:** 60 phút
- **Nguồn dữ liệu:** `data/logs.jsonl`
- **Sự kiện (Event):** `response_sent`
- **Trường (Field):** `latency_ms`
- **Phép tổng hợp (Aggregations):** `p50`, `p95`, `p99`
- **Ngưỡng SLO (Threshold):** P95 <= 3000ms
- **Truy vấn (Query):** `event == "response_sent" | percentile(latency_ms, [50, 95, 99])`

## 2. Request Traffic (Lưu lượng truy cập)
- **Tên Panel:** Request traffic
- **Đơn vị:** requests_per_minute
- **Khoảng thời gian mặc định:** 60 phút
- **Nguồn dữ liệu:** `data/logs.jsonl`
- **Sự kiện (Event):** `request_received`
- **Trường (Field):** `event`
- **Phép tổng hợp (Aggregations):** `count`, `rate_per_minute`
- **Ngưỡng SLO (Threshold):** rate_per_minute >= 1 (Hệ thống có tải tối thiểu)
- **Truy vấn (Query):** `event == "request_received" | count() by 1m`

## 3. Error Rate and Breakdown (Tỷ lệ và phân tích lỗi)
- **Tên Panel:** Error rate and breakdown
- **Đơn vị:** percent
- **Khoảng thời gian mặc định:** 60 phút
- **Nguồn dữ liệu:** `data/logs.jsonl`
- **Sự kiện (Event):** `request_received`, `request_failed`
- **Trường (Field):** `error_type`
- **Phép tổng hợp (Aggregations):** `error_rate_pct`, `count_by_value`
- **Ngưỡng SLO (Threshold):** error_rate_pct <= 2%
- **Truy vấn (Query):** `count(event == "request_failed") / count(event == "request_received") * 100; count_by(error_type)`

## 4. Cost Over Time (Chi phí tích lũy)
- **Tên Panel:** Cost over time
- **Đơn vị:** usd
- **Khoảng thời gian mặc định:** 60 phút
- **Nguồn dữ liệu:** `data/logs.jsonl`
- **Sự kiện (Event):** `response_sent`
- **Trường (Field):** `cost_usd`
- **Phép tổng hợp (Aggregations):** `sum_by_minute`, `total`
- **Ngưỡng SLO (Threshold):** total <= $2.5 USD
- **Truy vấn (Query):** `event == "response_sent" | sum(cost_usd) by 1m; sum(cost_usd)`

## 5. Input and Output Tokens (Lượng Token tiêu thụ)
- **Tên Panel:** Input and output tokens
- **Đơn vị:** tokens
- **Khoảng thời gian mặc định:** 60 phút
- **Nguồn dữ liệu:** `data/logs.jsonl`
- **Sự kiện (Event):** `response_sent`
- **Trường (Field):** `tokens_in`, `tokens_out`
- **Phép tổng hợp (Aggregations):** `sum_by_field`
- **Ngưỡng SLO (Threshold):** sum_by_field <= 50,000 tokens
- **Truy vấn (Query):** `event == "response_sent" | sum(tokens_in), sum(tokens_out)`

## 6. Quality Proxy (Chất lượng phản hồi)
- **Tên Panel:** Quality proxy
- **Đơn vị:** score_0_to_1
- **Khoảng thời gian mặc định:** 60 phút
- **Nguồn dữ liệu:** `data/logs.jsonl`
- **Sự kiện (Event):** `response_sent`
- **Trường (Field):** `quality_score`
- **Phép tổng hợp (Aggregations):** `mean`
- **Ngưỡng SLO (Threshold):** mean >= 0.75
- **Truy vấn (Query):** `event == "response_sent" | mean(quality_score)`

---

## Kiểm tra tính hợp lệ của Dashboard Contract:
```bash
python scripts/validate_dashboard.py
```
