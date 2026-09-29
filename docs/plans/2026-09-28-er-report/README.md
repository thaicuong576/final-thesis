# Plan: Báo cáo kiểu equity research + luồng điều phối minh bạch

Ngày lập: 2026-09-28 · Base: `main` @ `8fe93848c5204ad872ba2bde9bc485d2f62c0444`
Người lập plan và review: Claude (Lead) · Người code: Antigravity · Người duyệt merge: chủ repo

## 1. Vì sao có plan này

Review ngày 28/09 (chạy thật trên staging, không dựa vào docs trạng thái) cho kết quả:

- 12 câu hỏi thử, chỉ 2 câu chạy xong, và cả 2 đều là loại 1 ngân hàng × 1 chỉ tiêu × 1 quý. So sánh peer 0/3, trend 0/2. Mọi câu hỏi viết tự nhiên ("quý 4/2024", "năm 2024", "tỷ lệ nợ xấu") đều bị chặn. 3 câu gợi ý mẫu trên trang chủ cũng bị backend từ chối.
- Khi chạy được thì report chỉ có 1 con số, kèm một đoạn tổng hợp tiếng Anh tự nhận là không có diễn giải. Có lúc còn lộ nguyên câu trong prompt ra output (`analysis_writer.py:121`).
- Nguyên nhân gốc: synthesis bị cấm dùng số, tên ngân hàng, kỳ, từ xu hướng, từ nguyên nhân và cả chữ số tiếng Việt ("một", "năm"…). Vi phạm 1 từ là hủy cả run. Critic còn xóa luôn phần diễn giải.
- `cross_level_critique` luôn rỗng. Report page không render phần synthesis. Run thất bại không được lưu.

## 2. Đích đến

```
Người dùng hỏi bằng tiếng Việt tự nhiên, nhiều dạng câu hỏi
  → Điều phối viên (model) xác định dạng câu hỏi và chọn phép phân tích từ danh mục;
    code kiểm và đóng băng kế hoạch (model lỗi thì dùng kế hoạch theo luật)
  → Agent con chạy công cụ phân tích do code tính (tra cứu, vị thế nhóm, xếp hạng,
    diễn biến, đối đầu, phân rã ROE/ROA) → fact và dataset có nguồn
  → Agent con viết nhận định, mỗi câu phải trích fact_id
  → Bộ kiểm tra: mỗi số, hạng, xu hướng, so sánh trong câu phải khớp đúng fact được trích
  → Điều phối viên lắp report từ danh mục khối (câu trả lời, tiêu đề, luận điểm, mục, 8 loại hình, lưu ý)
    theo câu hỏi và insight; code kiểm hình có hợp dữ liệu không
  → Phản biện: bắt câu nói quá, report chưa trả lời đúng câu hỏi, hình thừa, mâu thuẫn giữa các tầng; sửa tối đa 2 vòng
  → Report kiểu equity research nhưng hình dạng thay đổi theo câu hỏi; người dùng mở "Quá trình phân tích" để xem từng bước
```

Dạng câu hỏi được bật: tra cứu, hồ sơ doanh nghiệp, xếp hạng, diễn biến, đối đầu. Để sau: chủ đề toàn nhóm, quan hệ giữa 2 chỉ tiêu (đã có trong contract, đang tắt).

Mockup chuẩn: [`mockups.html`](mockups.html) (mở bằng trình duyệt). Màn D là hồ sơ doanh nghiệp; màn E là 4 dạng còn lại. **Mockup minh họa hình dạng, không phải khuôn cố định**: số khối, loại hình và thứ tự do điều phối viên chọn trong giới hạn của ER-4 §4.

## 3. Nguyên tắc bất biến (vi phạm = PR bị trả lại)

1. **Code tính, LLM diễn giải.** Mọi con số trong report đến từ fact do code tính, có `input_observation_ids` và `formula_version`. LLM không tính toán.
2. **Kiểm, không cấm.** Câu có số sai, gán sai chỉ tiêu, xu hướng sai chiều, hoặc có từ nguyên nhân thì **bị loại riêng câu đó** và ghi vào audit. Không bao giờ hủy cả run vì một câu văn. Không thêm regex cấm từ để "chữa" output của model.
3. **Không hard-code 5 ngân hàng.** Không có literal `ACB|TCB|VPB|MBB|VCB` trong `src/thesis_data/*` (CI kiểm). Metadata chỉ tiêu (nhãn tiếng Việt, chiều tốt/xấu, số thập phân) nằm trong registry ở tầng application (`src/thesis_api/metric_presentation.py`).
4. **Tuân `docs/ARCHITECTURAL-GUARDRAILS.md`.** Core (`src/thesis_data`) không import sqlite3/openai/langgraph và không biết tới UI.
5. **Chỉ hiện agent đang chạy** (guardrail §6). Agent bị bỏ qua chỉ xuất hiện trong chi tiết bước "Lập kế hoạch", không vẽ thẻ riêng.
6. **UI theo `.agent/rules/design/`.** Font sans (IBM Plex Sans đang dùng), không dùng serif. Accent amber `--accent` cho chuỗi chính (ngân hàng mục tiêu), các chuỗi khác trung tính. `mockups.html` đã tuân hai điểm 5–6; nếu có ảnh mockup cũ nào khác (thẻ Macro nét đứt, tiêu đề serif) thì bỏ qua ảnh đó.
7. **Thiếu dữ liệu thì hiện là thiếu**, không ước tính, không coi là 0.
8. **Không có mock trong đường chạy production.** Fixture chỉ nằm trong test.
9. **Không khuyến nghị mua/bán**, không giá mục tiêu.
10. Không sửa các file thesis nguồn trong `docs/Khoá luận…`. Không commit secret. Không ghi vào DB Gold.

## 4. Danh sách PR và thứ tự

| PR | File spec | Phạm vi | Phụ thuộc |
|---|---|---|---|
| ER-1 | [PR-1-contract.md](PR-1-contract.md) | Decision D-075; contract: question type, fact, dataset, ReportSpec, trace; 7 fixture | — |
| ER-2 | [PR-2-query-understanding.md](PR-2-query-understanding.md) | Resolver tiếng Việt, planner (model + luật), danh mục công cụ, lỗi thân thiện, gợi ý | ER-1 |
| ER-3 | [PR-3-facts-exhibits.md](PR-3-facts-exhibits.md) | Hộp công cụ phân tích: fact, dataset, tín hiệu, ứng viên mâu thuẫn | ER-2 |
| ER-4 | [PR-4-narrative-critique.md](PR-4-narrative-critique.md) | Câu có trích fact, bộ kiểm tra câu, lắp report theo khối, phản biện, revision, công tắc arm | ER-3 |
| ER-5 | [PR-5-run-trace.md](PR-5-run-trace.md) | Lưu và phát trace từng bước, lưu run thất bại, đếm token | ER-4 |
| ER-6 | [PR-6-ui-ask-session-trace.md](PR-6-ui-ask-session-trace.md) | Màn hỏi tối giản, màn điều phối, màn quá trình | ER-1 (fixture), ER-5 (nối thật) |
| ER-7 | [PR-7-ui-report.md](PR-7-ui-report.md) | Trình render report theo khối + 8 loại hình | ER-1 (fixture), ER-4 (nối thật) |
| ER-8 | [PR-8-evaluation.md](PR-8-evaluation.md) | Protocol v2, harness A/B/C, chấm tất định, gói chấm mù, phân tích | ER-4, ER-5 |

Có thể làm song song: sau khi ER-1 merge, nhánh backend (ER-2 → ER-5) và nhánh frontend (ER-7, ER-6) chạy song song. Frontend dùng fixture JSON theo contract, đặt trong `frontend/src/test/fixtures/`.

**Nếu thiếu thời gian, cắt theo thứ tự:**
1. planner bằng model (chạy `planner_mode="rules_only"`; kế hoạch theo luật vẫn đủ 5 dạng);
2. lọc theo agent ở ER-6 và tooltip ở ER-7;
3. chart `grouped_bar` và `scatter` (dataset vẫn còn, chỉ render bằng bảng);
4. ứng viên `counter_trend`.

Không cắt: bộ kiểm tra câu và `validate_report_spec` (ER-4), fact có provenance (ER-3), resolver tiếng Việt và kế hoạch theo luật (ER-2), bố cục mặc định theo dạng câu hỏi (ER-4 §3).

## 5. Quy trình cho Antigravity (mỗi PR)

1. `git fetch origin` rồi tạo worktree từ `origin/main` mới nhất:
   `powershell -File scripts/worker-start.ps1 -BranchName feat/er-<n>-<slug>`
2. Đọc: `AGENTS.md`, file spec của PR, `mockups.html` (nếu là UI), và các file được liệt kê trong spec.
3. Làm đúng phạm vi spec. Thấy spec sai hoặc thiếu thì **dừng, ghi vào mô tả PR mục "Deviations"**, không tự ý mở rộng.
4. Chạy đủ kiểm tra (chạy trong worktree):
   ```
   $env:PYTHONPATH="src"; $env:PYTHONUTF8="1"
   python scripts/check_openapi_contract.py
   python scripts/check_architecture_guardrails.py
   python -m unittest discover -s tests -q
   cd frontend; npm run lint; npm test -- --run; npm run build
   ```
5. Commit theo Conventional Commits. Tiêu đề PR: `feat(<api|ui|data|contracts>): [ER-<n>] <mô tả>`.
6. Mô tả PR bắt buộc có:
   ```
   Base SHA:
   Branch:
   Commit SHA:
   Spec: docs/plans/2026-09-28-er-report/PR-<n>-*.md
   Checklist spec: (copy checklist cuối file spec, đánh dấu từng mục)
   Changed files:
   Tests: (lệnh + kết quả)
   Deviations: (khác spec ở đâu, vì sao)
   Known failures:
   ```
7. Chờ CI xanh (`gh pr checks <n>`). CI đỏ thì tự sửa. **Không merge.** Báo chủ repo để gọi Claude review.

## 6. Cách Claude review

Claude sẽ checkout nhánh PR, chạy lại toàn bộ lệnh ở §5.4, đối chiếu checklist của spec và chạy các câu hỏi trong [acceptance-questions.md](acceptance-questions.md) (offline với fake writer/critic, hoặc staging nếu PR đã deploy). Kết quả trả về dạng: `APPROVE` hoặc `CHANGES REQUESTED` kèm danh sách sửa có file:dòng.

## 7. Ngoài phạm vi

- Chạy đánh giá A/B/C và cập nhật protocol đánh giá. Làm sau khi ER-4 merge, bằng một plan riêng. ER-4 phải giữ được khả năng cấu hình arm (xem spec ER-4 §9).
- Thêm dữ liệu mới (P/B, P/E, NIM, CASA, CAR, vĩ mô).
- Bật 2 dạng câu hỏi `sector_theme` và `relationship` (contract đã có, công cụ `dispersion`/`relationship` có thể làm sau).
- Cho agent con tự gọi thêm công cụ ngoài kế hoạch (tool-calling nhiều vòng). Hiện tại điều phối viên chọn công cụ một lần khi lập kế hoạch.
