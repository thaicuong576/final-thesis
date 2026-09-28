# ER-5 · Trace từng bước: phát trực tiếp, lưu lại, mở lại được

Nhánh: `feat/er-5-run-trace` · PR: `feat(api): [ER-5] persist and stream structured agent trace for every run`

Mục tiêu: màn "Quá trình phân tích" có dữ liệu thật, cả lúc đang chạy (SSE) lẫn sau khi xong (`GET /api/runs/{id}/trace`). Run thất bại cũng được lưu để giải thích vì sao bị chặn.

Đọc trước: ER-1 §2.7; `src/thesis_api/service.py` (`analyze`, `persist_run`, `stream_analysis_query` ~1100–1310); `src/thesis_api/database.py`; `src/thesis_api/main.py`; `contracts/run-store-schema.sql`.

## 1. Thu thập trace trong runtime

- `_AdaptiveRun` có `self.trace_steps: list[TraceStepDTO]` và method:
  ```python
  def _trace(self, kind, actor, summary, detail, recipient=None) -> None
  ```
  `seq` tăng dần. `t_ms` tính từ lúc bắt đầu run (`time.monotonic`). Mỗi lần gọi `_trace` thì emit SSE `TRACE_STEP` với payload là step đó (qua `emit` hiện có).
- `summary` **do code sinh bằng tiếng Việt**, không dùng LLM. Hàm `summaries_vi.py` (file mới) có một hàm cho mỗi kind.

Điểm gọi `_trace`, theo đúng thứ tự thời gian:

| Thời điểm | kind | actor → recipient | summary mẫu |
|---|---|---|---|
| Sau khi plan được đóng băng | plan | orchestrator | "Dạng câu hỏi: Xếp hạng. Gọi Sector với 1 phép phân tích" |
| Trước khi chạy tool của mỗi agent | assign | orchestrator → company/sector | "Giao việc: xếp hạng bao phủ nợ xấu · 5 ngân hàng" |
| Sau mỗi tool | tool_result | company/sector → orchestrator | "Trả 5/5 số liệu có nguồn, trung vị và khoảng cách đầu–cuối" |
| Sau `write_findings` của mỗi role | draft | company/sector → orchestrator | "Gửi 3 nhận định nháp" |
| Sau verify | verify | verifier | "12/12 số khớp dữ liệu gốc; loại 1 câu" |
| Sau `compose_report` và validate | compose | orchestrator | "Dựng ghi chú sàng lọc: tiêu đề, 1 hình, 2 luận điểm, 1 lưu ý" |
| Gửi critic | assign | orchestrator → critic | "Gửi bản nháp để kiểm tra chéo (vòng 1)" |
| Mỗi issue | critique_issue | critic → tác giả câu hoặc orchestrator | "Yêu cầu sửa 1 câu không có căn cứ" |
| Mỗi finding confirmed | cross_level_finding | critic → orchestrator | "Phát hiện 1 điểm cần lưu ý giữa các chỉ tiêu" |
| Mỗi câu hoặc khối được sửa | revision / compose | tác giả → orchestrator | "Đã sửa theo phản biện" |
| Critic chấp nhận | accept | critic → orchestrator | "Vòng 2: chấp nhận, không còn vấn đề mở" |
| Kết thúc | report_ready hoặc blocked | orchestrator hoặc system | "Báo cáo sẵn sàng" hoặc message lỗi tiếng Việt |

`detail` đúng schema ER-1 §2.7. Plan step có `question_type`, `planner_source`, `rationale` và danh sách tool có `label` tiếng Việt, để người dùng thấy điều phối viên đã quyết định gì và vì sao. `tool_result.detail.facts[].display_value` dùng `display_fact`. `source_note_no` được điền sau khi đánh số nguồn (ER-4 §8): cập nhật step trong list trước khi lưu. **Không** đưa prompt, raw model output hay reasoning vào detail.

Plan bị chặn trước khi tạo `_AdaptiveRun` (ví dụ `unsupported_period`): `service.py` tự tạo 1 step `blocked` (actor `system`) để run vẫn có trace.

## 2. Đếm chi phí (phục vụ Chương 5)

Wrapper quanh client LLM ghi lại cho mỗi lần gọi: `role`, `latency_ms`, `input_tokens`, `output_tokens` (lấy từ `response.usage` nếu có; không có thì `null`, **không ước tính**). Tổng hợp vào run record: `model_calls`, `input_tokens`, `output_tokens`, `duration_ms`, `arm`. Trace step `report_ready.detail` thêm `{"model_calls":…, "duration_ms":…}`.

## 3. Lưu run

`database.py`:
- `ensure_analysis_runs_table`: tạo bảng như contract. Thêm migration idempotent: đọc `PRAGMA table_info(analysis_runs)`, rồi `ALTER TABLE ADD COLUMN` cho `trace_json`, `error_code`, `duration_ms`, `model_calls`, `input_tokens`, `output_tokens`, `arm`, `question_type` nếu thiếu. Cập nhật `contracts/run-store-schema.sql` cho khớp (cột mới vào `CREATE TABLE`, kèm ghi chú migration).
- `save_analysis_run(...)`: thêm tham số tương ứng.
- `get_analysis_run_trace(db_path, run_id) -> dict | None`.

`service.py`:
- `persist_run` **lưu cả run lỗi**: `status="error"`, `error_code`, `report_json` là error report, `trace_json`. Bỏ điều kiện `if plan is None or report.status == "error": return`.
- `analyze()` (không stream) cũng lưu trace (hiện đang lưu `events=[]`).
- SSE: giữ event cũ. Thêm `TRACE_STEP`. Event `REPORT_READY`/`RUN_BLOCKED` giữ như cũ.
- Lưu run thất bại mà lỗi DB thì chỉ log warning; **không** đổi kết quả trả cho người dùng.

`main.py`: thêm `GET /api/runs/{run_id}/trace` trả `RunTraceDTO`; không có thì 404. `GET /api/runs` trả thêm `status`, `error_code`, `duration_ms` để trang danh sách phân biệt được run lỗi.

## 4. Test

`tests/test_run_trace.py`:
- Run offline happy path (fake writer/critic của ER-4): trace có đủ các kind theo đúng thứ tự ở bảng §1 (plan → assign → tool_result → draft → verify → compose → … → report_ready); `seq` liên tục; `t_ms` không giảm.
- Có revision: có step `critique_issue` và `revision` với `before != after`.
- Run bị chặn ở ER-2: được lưu với `status="error"`, trace có 1 step `blocked` mang message tiếng Việt.
- `GET /api/runs/{id}/trace` trả đúng; id không tồn tại thì 404.
- Migration: tạo DB với schema cũ (không có cột mới), gọi `ensure_analysis_runs_table`, có đủ cột, dữ liệu cũ còn nguyên.
- SSE: stream có `TRACE_STEP` trước `REPORT_READY`; số `TRACE_STEP` của stream bằng số step được lưu.
- Không step nào có key `prompt`, `instructions`, `raw_output`, `reasoning` (quét đệ quy).

Test cũ có thể phải sửa: các test assert "run lỗi không được lưu" (tìm bằng `grep -n "persist" tests/*.py`) → đổi thành assert run lỗi được lưu với `status="error"`.

## Checklist review
- [ ] Trace đủ bước và đúng thứ tự trên run thật (dán trace JSON của câu B1 và B2 vào PR).
- [ ] Run lỗi được lưu và có trace giải thích.
- [ ] Không có prompt hay reasoning trong trace.
- [ ] Token/latency lấy từ `usage` thật, thiếu thì để null.
- [ ] Migration idempotent, không phá DB run cũ.
- [ ] `contracts/run-store-schema.sql` và openapi khớp code.
