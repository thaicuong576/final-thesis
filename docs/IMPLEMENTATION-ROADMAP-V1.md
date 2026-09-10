# Implementation roadmap v1

Mục tiêu: làm một luồng phân tích ngành dùng được, rồi đo khi nào multi-agent đáng dùng.

## 1. Wireframe

Đã ghi tại `docs/APP-WIREFRAME-NOTE-V1.md`. Chỉ chốt màn hình và thông tin cần thấy; chưa khóa công nghệ UI.

## 2. Output contract

`ReportView`/`OUTPUT-CONTRACT-V1` được giữ làm transport layer và đánh dấu superseded. Output user-facing hiện dùng `analysis-report-v2` tại `docs/OUTPUT-CONTRACT-V2.md`: claim, evidence, interpretation, limitation, data refs và support level.

## 3. Evidence/output layer

Đã thêm `src/thesis_data/report_view.py`. Số liệu lấy từ Gold; source locator và evidence snippet được gắn lại ở lớp report. Missing vẫn là `null`.

## 4. Report end-to-end

Đã thêm `scripts/render_analysis_report_v2.py` và `scripts/validate_analysis_report.py`. Một run manifest có thể sinh `analysis-report.json`, `analysis-report.md` và `analysis-report.html`; report có executive summary, comparison, issuer profiles, claim-level provenance, evidence và limitation.

## 5. UI mỏng

Đã thêm `app/index.html`. UI chỉ đọc `app/data/analysis-report.json`; không tính metric, không gọi model, không truy cập SQLite. UI phát triển song song sau khi v2 contract ổn định, nên không quyết định architecture phía dưới.

## 6. Database mở rộng

Gold đã được mở rộng từ pilot 48 ô lên snapshot 80 ô:

- `data/processed/gold-bank-2025-expanded-v4.sqlite`
- Evidence-complete evaluation input: `data/processed/gold-bank-2025-expanded-v5-evidence.sqlite`.
- 5 ngân hàng: ACB, MBB, TCB, VCB, VPB.
- 4 quý năm 2024 và 4 metric lõi.
- 76 ô hợp lệ, 4 ô missing có lý do; không tự điền missing.
- 76/76 ô hợp lệ có page-aware human-reviewed derivation-note evidence; v4 được giữ nguyên bất biến.

Candidate lớn hơn hiện có: `data/processed/normalized_candidate_bank-2025-v1.sqlite`.

- 5 ngân hàng.
- 8 quý từ 2024_Q1 đến 2025_Q4.
- 5 metric, gồm thêm CIR.
- 200 target rows.
- Tất cả còn `pending_validation`, chưa dùng cho Gold hoặc kết luận thesis.

Audit candidate bằng `scripts/audit_scaling_candidate.py`. Candidate 200 ô hiện chỉ có nguồn accelerator/vendor và chưa có evidence snippet, nên chưa thể promote.

Nguồn tài liệu để mở rộng tiếp đã được inventory tại `reports/data-foundation/annual-report-target-inventory-v1.md`: 15 annual-report PDF cho 5 ngân hàng, đủ 2023–2025. Đây là nguồn document-ready, chưa phải quarterly Gold; cần trích xuất page-level, chuẩn hóa định nghĩa và review trước khi nhập.

## 7. Benchmark

Đã chạy full `analysis-report-v2` trên Gold v5 với 75 manifests (5 mức số
issuer × 3 arm × 5 repetitions), rồi blind-score 61 report hoàn tất trên 4
dimension, tổng cộng 244 dòng. Integrated report:
`reports/analysis-report-v2-final-evaluation-gold-v5-20260909-v3/final-evaluation.md`.

Kết quả: crossover đầu tiên quan sát được ở **3 issuers** cho
`hierarchical_no_critique`: quality gain chuẩn hóa `+0.05`, positive
repetitions `3/5`, cost `2.622757x` và latency `1.698339x` single-agent; cả hai
arm có failure rate `0%` ở workload này. Bounded critique không đạt crossover.
Ở 4–5 issuers, provider failure rate làm comparison operationally incomplete,
nên không được tuyên bố là crossover dù các report sống sót có điểm chất lượng
cao.

14/75 provider jobs fail và được giữ nguyên trong operational telemetry: 9
context-budget, 2 schema, 3 API connection. Đây là kết quả reliability cần
giải thích trong thesis, không được che bằng output thay thế.

Smoke comparison đầu tiên theo `analysis-report-v2` đã chạy thật trên cùng workload 5 issuer:

- `reports/application-analysis-benchmark-v2-smoke/benchmark.md`
- Cả ba arm pass contract và publish 120/120 task references.
- Single-agent: $0.0221614, 80.312 s, 1/5 claims evidence-backed.
- Hierarchical no-critique: $0.0823832, 170.422 s, 2/5 claims evidence-backed.
- Hierarchical bounded-critique: $0.1034700, 198.016 s, 3/6 claims evidence-backed.

Đây là smoke history; không dùng thay cho full evaluation ở trên. Kết luận hiện
tại phải lấy từ final evaluation artifact và failure-aware aggregation.

## Nguyên tắc phạm vi

UI có thể được phát triển song song ở dạng read-only. Không để UI quyết định schema database hoặc logic agent. Benchmark không dùng candidate pending.

## Bước tiếp theo sau evaluation

1. Chuyển `analysis-report-v2` từ audit/benchmark output thành decision-grade
   product report: executive signal, peer comparison, trend/anomaly, risk
   interpretation, confidence/evidence, limitation và action to follow up.
2. Giữ UI mỏng đọc đúng report contract; không để UI tạo ra insight hoặc sửa
   số liệu.
3. Sau khi chốt report value, chạy một robustness rerun có kiểm soát với SOP
   context-bounded/parallel đã sửa, giữ nguyên Gold, câu hỏi, model và rubric;
   mục tiêu là đo reliability recovery, không làm lại toàn bộ scope tuỳ ý.
4. Chỉ mở rộng sang 8 quý/200 cells sau khi có evidence/review cho candidate và
   advisor chốt scope; không dùng candidate pending để làm kết luận hiện tại.
