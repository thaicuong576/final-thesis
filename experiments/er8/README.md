# Thư mục Thực nghiệm Đánh giá A/B/C (ER-8)

Thư mục này lưu trữ cấu hình, dữ liệu thực nghiệm và kết quả phân tích so sánh 3 kiến trúc xử lý (Arm A: Single-Agent, Arm B: Phân tầng không phản biện, Arm C: Phân tầng có phản biện) phục vụ phân tích thực nghiệm tại **Chương 5** của khóa luận tốt nghiệp.

## Cấu trúc thư mục

```text
experiments/er8/
├── README.md               # Tài liệu mô tả cấu trúc thư mục thực nghiệm (file này)
├── runs/                   # Chứa các file kết quả chi tiết từng lượt chạy: er8-<task>-<arm>-r<rep>.json
├── manifest.json           # Bản kê tổng kết đợt chạy, ràng buộc hash câu hỏi và siêu dữ liệu
├── scores/
│   └── deterministic.csv   # Bảng điểm tất định 32 trường chỉ số theo PR-8 §5
├── analysis/
│   ├── arm_summary.csv     # Bảng tổng hợp các chỉ số trung bình theo từng Arm
│   ├── pairwise_diffs.csv  # Bảng chênh lệch theo cặp (C-B, B-A, C-A) kèm 95% Bootstrap CI
│   ├── figure_er8_completion_accuracy.png # Đồ thị tỷ lệ thành công và tính đúng số
│   ├── figure_er8_cost_latency.png        # Đồ thị chi phí tokens và độ trễ
│   └── figure_er8_pairwise_diff.png       # Đồ thị so sánh cặp với khoảng tin cậy
├── RESULTS.md              # Báo cáo tổng kết tiếng Việt định dạng phục vụ Chương 5
└── dry-run/                # Thư mục chạy kiểm thử offline cục bộ (được cấu hình .gitignore)
```

## Các lệnh thực thi chính

1. **Chạy thực nghiệm (Runner)**:
   ```bash
   # Chạy offline kiểm tra (dry-run ghi vào experiments/er8/dry-run/):
   python scripts/er8_run.py --dry-run

   # Chạy thực nghiệm thật (đọc cấu hình từ .env, kiểm tra preflight model trước khi chạy):
   python scripts/er8_run.py --reps 1 --max-tokens 3000000
   ```

2. **Chấm điểm tất định (Scorer)**:
   ```bash
   python scripts/er8_score.py
   ```

3. **Phân tích và xuất báo cáo (Analyzer)**:
   ```bash
   python scripts/er8_analyze.py
   ```

> **Lưu ý:** Kết quả thực nghiệm chính thức từ mô hình thật sẽ được tạo và commit trong PR riêng sau khi kích hoạt lượt chạy trực tiếp theo ngân sách được duyệt.
