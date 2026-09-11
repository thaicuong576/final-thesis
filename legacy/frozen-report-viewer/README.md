# Frozen thesis report viewer

Đây là artifact khóa luận lịch sử đã đóng băng, chỉ đọc. Nó không phải
frontend sản phẩm hiện tại; frontend sản phẩm nằm trong `frontend/`.

Dữ liệu hiển thị trong viewer từng được render từ `analysis-report-v2` trên
bản chụp Gold. Viewer không truy cập SQLite trực tiếp và không gọi model. Nó
chỉ được giữ lại cho mục đích tái lập kết quả và làm bằng chứng cho khóa luận.

## Chạy local

Nếu cần tái tạo dữ liệu hiển thị, ghi output vào thư mục `data/` của viewer:

```powershell
$env:PYTHONPATH='src'
python scripts/render_analysis_report.py `
  experiments/outputs/provider/complexity-scaling-5issuer-gold-v4-gpt-5.6-luna-composed-v3-20260909T110000Z/base-failed-job-23.json `
  --db data/processed/gold-bank-2025-expanded-v4.sqlite `
  --output-dir legacy/frozen-report-viewer/data

python scripts/render_analysis_report_v2.py `
  experiments/outputs/provider/complexity-scaling-5issuer-gold-v4-gpt-5.6-luna-composed-v3-20260909T110000Z/base-failed-job-23.json `
  --db data/processed/gold-bank-2025-expanded-v4.sqlite `
  --output-dir legacy/frozen-report-viewer/data
```

Chạy máy chủ từ root repository:

```powershell
python -m http.server 8765 --directory legacy/frozen-report-viewer
```

Mở `http://127.0.0.1:8765/`. Script chụp ảnh lịch sử là
`capture_thesis_ui.cjs` trong cùng thư mục này.
