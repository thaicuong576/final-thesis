# Thư mục Thực nghiệm Đánh giá A/B/C trên Snapshot 10 Ngân hàng (ER-9)

Thư mục này lưu trữ cấu hình, dữ liệu thực nghiệm và kết quả phân tích so sánh 3 kiến trúc xử lý (Arm A: Single-Agent, Arm B: Phân tầng không phản biện, Arm C: Phân tầng có phản biện) trên snapshot vận hành 10 ngân hàng niêm yết theo quý (`bank-quarterly-top10-operational-v1-r4.sqlite`) phục vụ phân tích thực nghiệm tại **Chương 5** của khóa luận tốt nghiệp.

## Snapshot vận hành mục tiêu

- **Tệp cơ sở dữ liệu**: `data/processed/bank-quarterly-top10-operational-v1-r4.sqlite`
- **SHA-256 tệp gốc (raw bytes)**: `2a18845feb8dddd83ace39a4ea56fc5d5fbe4a3cb0fcccdfce374a48627f560a`
- **Mã định danh snapshot**: `snapshot-42a105f6d7978ef00e972dae40d3f4050dba6102e7b33611a60c521b6f2ce54e`
- **Không gian dữ liệu**: 10 ngân hàng (ACB, BID, CTG, HDB, MBB, SHB, STB, TCB, VCB, VPB), 10 quý (2024_Q1 - 2026_Q2), 100 bank-quarters đầy đủ (0 cell thiếu), 4 chỉ số tài chính cốt lõi (NPL G3-5, LLR, ROA, ROE).
- **Cấu hình phạm vi**: Chạy với `CanonicalSqliteDatasetProvider`, không sử dụng sidecar Gold scope-authority (tương thích môi trường staging).

## Cấu trúc thư mục

```text
experiments/er9/
├── README.md               # Tài liệu hướng dẫn thực nghiệm ER-9 (file này)
├── runs/                   # Chứa các file kết quả chi tiết từng lượt chạy: er9-<task>-<arm>-r<rep>.json
├── manifest.json           # Bản kê tổng kết đợt chạy, ràng buộc hash câu hỏi và siêu dữ liệu
├── scores/
│   └── deterministic.csv   # Bảng điểm tất định 32 trường chỉ số theo PR-8 §5 / PR-9
├── analysis/
│   ├── arm_summary.csv     # Bảng tổng hợp các chỉ số trung bình theo từng Arm
│   ├── pairwise_diffs.csv  # Bảng chênh lệch theo cặp (C-B, B-A, C-A) kèm 95% Bootstrap CI
│   ├── figure_er9_completion_accuracy.png # Đồ thị tỷ lệ thành công và tính đúng số
│   ├── figure_er9_cost_latency.png        # Đồ thị chi phí tokens và độ trễ
│   └── figure_er9_pairwise_diff.png       # Đồ thị so sánh cặp với khoảng tin cậy
├── RESULTS.md              # Báo cáo tổng kết tiếng Việt định dạng phục vụ Chương 5
└── dry-run/                # Thư mục chạy kiểm thử offline cục bộ (được cấu hình git-ignored)
```

## Các lệnh thực thi chính

1. **Chạy kiểm thử offline (Dry-run)**:
   ```bash
   python scripts/er9_run.py --dry-run --concurrency 6
   # hoặc:
   # python scripts/er8_run.py --dry-run --er9 --concurrency 6
   ```

2. **Chấm điểm tất định (Scorer)**:
   ```bash
   python scripts/er9_score.py
   # hoặc:
   # python scripts/er8_score.py --er9
   ```

3. **Phân tích và xuất báo cáo (Analyzer)**:
   ```bash
   python scripts/er9_analyze.py
   # hoặc:
   # python scripts/er8_analyze.py --er9
   ```

4. **Chạy thực nghiệm chính thức (dành cho Orchestrator)**:
   ```bash
   python scripts/er9_run.py --reps 1 --concurrency 6 --max-tokens 3000000
   ```

> **Lưu ý:**
> - Worker chỉ chạy offline dry-run để kiểm thử harness. Tuyệt đối không chạy mô hình thật trong phiên worker.
> - Runner hỗ trợ cờ `--concurrency N` (mặc định đa luồng ghi nhật ký độc lập vào `runs_dbs/{run_id}.sqlite` và gộp vào `runs.sqlite` sau khi hoàn tất).
> - Cờ `--resume` tự động bỏ qua các lượt chạy đã có trạng thái `completed` hoặc `blocked`.
