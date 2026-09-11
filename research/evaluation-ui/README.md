# Blind human evaluation UI

Đây là công cụ chấm mù phục vụ research evaluation, không phải user-facing
product UI.

Reviewer chấm bốn chiều: Correctness, Usefulness, Evidence và Limitation.
Tool không được biết experiment arm hoặc private identity map; nó chỉ nạp
blind packets và review queue do người chấm cung cấp. Tool không gọi model.

## Chạy local

```powershell
python -m http.server 8765 --directory research/evaluation-ui
```

Mở `http://127.0.0.1:8765/review.html`, rồi chọn:

- `reports/analysis-report-v2-human-review-gold-v5-20260909/blind-packets.jsonl`
- `reports/analysis-report-v2-human-review-gold-v5-20260909/human-review-queue.csv`

Sau khi chấm xong, tải CSV và kiểm tra bằng
`scripts/validate_analysis_report_v2_human_queue.py --require-complete`.
