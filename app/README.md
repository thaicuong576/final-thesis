# Giao diện báo cáo và bảng chấm mù

Giao diện báo cáo chính đọc `data/analysis-report.json` và
`data/analysis-series.json` theo hợp đồng `analysis-report-v2`.
`analysis-series.json` là dữ liệu trình bày chỉ đọc của cùng bản chụp Gold để vẽ
xu hướng. Ứng dụng kiểm tra hai `snapshot_id` phải khớp. Giao diện không truy
cập SQLite, không tự tính chỉ số và không gọi mô hình.

Tạo lại dữ liệu hiển thị (chỉ dùng khi cần tái tạo tài liệu đầu ra):

```powershell
$env:PYTHONPATH='src'
python scripts/render_analysis_report.py `
  experiments/outputs/provider/complexity-scaling-5issuer-gold-v4-gpt-5.6-luna-composed-v3-20260909T110000Z/base-failed-job-23.json `
  --db data/processed/gold-bank-2025-expanded-v4.sqlite `
  --output-dir app/data

python scripts/render_analysis_report_v2.py `
  experiments/outputs/provider/complexity-scaling-5issuer-gold-v4-gpt-5.6-luna-composed-v3-20260909T110000Z/base-failed-job-23.json `
  --db data/processed/gold-bank-2025-expanded-v4.sqlite `
  --output-dir app/data
```

Chạy local:

```powershell
python -m http.server 8765 --directory app
```

Mở `http://127.0.0.1:8765`.

## Luồng trình diễn

1. Đọc kết luận chính và phạm vi trong báo cáo.
2. Kiểm tra bảng quý 4.
3. Chọn chỉ số/ngân hàng trong phần Xu hướng để xem quý 1 → quý 4.
4. Mở phần Nhận định và bằng chứng để xem vị trí nguồn và giới hạn.

Đây là bản xem trước cục bộ phục vụ trình diễn khóa luận, không phải ứng dụng
đưa vào vận hành thực tế.

## Chấm mù

Mở `http://127.0.0.1:8765/review.html`, sau đó chọn hai file trong:

`reports/analysis-report-v2-human-review-gold-v5-20260909/`

- `blind-packets.jsonl`
- `human-review-queue.csv`

Người chấm chỉ cần chấm 0–4 và ghi `decision basis` (cơ sở quyết định) cho bốn chiều. Bảng chấm
không đọc `private-identity-map.json`, không hiển thị nhánh xử lý/mô hình và
không gọi mô hình. Sau khi hoàn tất, bấm **Tải CSV đã chấm**, rồi dùng file CSV
tải xuống với `scripts/validate_analysis_report_v2_human_queue.py
--require-complete`.
