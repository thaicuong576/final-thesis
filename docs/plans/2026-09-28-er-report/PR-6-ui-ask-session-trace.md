# ER-6 · UI: màn hỏi tối giản, màn điều phối, màn quá trình

Nhánh: `feat/er-6-ui-ask-session` · PR: `feat(ui): [ER-6] lean ask screen, orchestrator session and process trace`

Mục tiêu: người dùng nhìn là biết phải làm gì (hỏi), thấy điều phối viên giao việc cho agent con, và có thể mở từng bước để xem agent làm gì. Bố cục theo `mockups.html` màn **A, B, C**, trừ hai điểm ở README §3.5–3.6: không vẽ thẻ cho agent bị bỏ qua, không dùng serif.

Có thể bắt đầu ngay sau ER-1, dùng fixture `er-trace-acb-2024q4.json`. Nối dữ liệu thật khi ER-5 đã merge.

Đọc trước: `.agent/rules/design/README.md`, `03-layout-and-navigation.md`, `04-components-and-states.md`, `06-interactions-and-behaviors.md`, `07-motion-accessibility-contract.md`; `frontend/src/pages/create-analysis/CreateAnalysisPage.tsx`; `frontend/src/features/analysis-session/*`; `frontend/src/features/create-analysis/model/streamRequest.ts`.

## 1. Màn A: Hỏi (`/analysis`)

Giữ `WorkspaceShell`. Nội dung trang chỉ còn:
1. Tiêu đề trang "Bạn muốn phân tích gì?" (page title 24px/700 theo type scale).
2. Một `textarea` (3 dòng, tự giãn) với placeholder là câu gợi ý đầu tiên từ backend. Nút primary "Phân tích" nằm góc phải dưới ô. Enter gửi, Shift+Enter xuống dòng. **Bỏ** dòng hướng dẫn Ctrl+Enter.
3. Một dòng 13px màu `--text-secondary`: "Dữ liệu hiện có: {entities} · {Q1–Q4/2024} · {shortLabel các chỉ tiêu}", lấy từ `/api/capabilities`, kèm link "Chi tiết" tới `/data`.
4. "Thử hỏi": các câu lấy từ `capabilities.suggestedQuestions` (ER-2), mỗi câu một dạng câu hỏi (tra cứu, xếp hạng, diễn biến, so sánh, hồ sơ), để người dùng thấy hệ thống hỏi được nhiều kiểu. Nếu ER-2 chưa merge thì ẩn khối này, **không** tự sinh câu ở client. Bấm vào thì điền câu vào ô, không tự gửi.
5. "Báo cáo gần đây": tối đa 5 dòng từ `/api/runs?limit=5`, mỗi dòng gồm câu hỏi, ngày, và trạng thái bằng chữ (không chỉ dùng màu): "Hoàn tất", "Có giới hạn", "Bị chặn". Bấm vào mở report, hoặc mở trace nếu bị chặn.

**Xóa khỏi trang** (xóa hẳn component nếu không còn nơi dùng):
- `ActiveDatasetCard` (cả hai bản), `ActiveDatasetContextCard`, `DatasetSelectorSheet`;
- chip ngân hàng, chip quý, `RequestInterpretationCard`, `ScopeMismatchAlert`, `ScopeAdjustmentDrawer`;
- `SuggestedQuestions` bản cũ (sinh "trong năm 2024" với mã chỉ tiêu);
- link "Mẫu minh họa" và mọi đường mở mock report;
- mọi nhãn "API: …", mọi snapshot id.

`streamRequest.ts`: **bỏ toàn bộ việc chặn ở client** (kỳ, chỉ tiêu, capability). Request chỉ còn `{ query }`. Backend là nơi quyết định duy nhất. `intentParser.ts` không còn dùng cho việc gửi; xóa nếu không còn import.

Lỗi (`RUN_BLOCKED` hoặc `status = "error"`): hiện ngay dưới ô nhập một khối cảnh báo có `error.message` và 3 `error.suggestions` dạng link bấm để điền. Giữ nguyên câu người dùng đã gõ.

## 2. Màn B: Phiên phân tích (`/session` hoặc cùng trang, như hiện tại)

Dựng từ **luồng `TRACE_STEP`** (ER-5). Không dùng các event cũ, không dùng `MockAnalysisSessionDriver`.

Component mới trong `frontend/src/features/analysis-session/components/`:
- `OrchestratorBoard`:
  - Thẻ **Điều phối viên** rộng toàn khung, trên cùng.
  - Hàng thẻ agent con: **chỉ những agent có trong `plan.detail.agents` với `decision = "run"`**, cộng thẻ "Phản biện" nếu arm có critic.
  - Nối thẻ Điều phối với các thẻ con bằng đường kẻ SVG 1px `--border-default`.
  - Dưới tên mỗi agent con ghi các phép phân tích được giao (label của tool trong plan), ví dụ "Xếp hạng bao phủ · 5 ngân hàng". Thẻ Điều phối viên hiện dòng "Dạng câu hỏi: {nhãn}" sau step plan.
  - Mỗi thẻ có nhãn trạng thái bằng chữ + màu: Chờ / Đang làm / Xong / Đang sửa. Có một dòng mô tả là `summary` của step gần nhất có actor đó.
  - Quy tắc trạng thái:
    - `assign` tới agent thì agent đó "Đang làm";
    - `tool_result` hoặc `draft` từ agent thì "Xong";
    - `critique_issue` gửi tới agent thì "Đang sửa";
    - `revision` từ agent thì "Xong";
    - Điều phối viên "Xong" khi có `report_ready`.
- `ProcessTrace` (dùng lại ở ER-7): xem §3.
- Đồng hồ `mm:ss` góc phải, theo `t_ms` của step cuối.
- Khi có `report_ready`: hiện nút primary "Mở báo cáo" và tự chuyển sang report sau 1,5 giây nếu người dùng không tương tác (tôn trọng `prefers-reduced-motion`: không animate).
- Mất kết nối SSE: hiện "Mất kết nối. Thử lại" cùng nút thử lại. Không tự dựng event giả.

Các component cũ không còn dùng (`OrchestratorThread`, `SpecialistSessionSheet`, `InlineSpecialistInvocationCard`, `ObservableActivityTimeline`, `ReviewFeedbackBlock`, `RevisionRoundBlock`, `SpecialistArtifactSummaryBlock`, `projector.ts`, `mock/*`): xóa nếu không còn import từ production. Test chỉ dùng mock thì xóa cùng test đó, **ghi danh sách vào PR**.

## 3. Màn C: `ProcessTrace`

Props: `steps: TraceStep[]`, `live: boolean`.
- Đầu khối: tiêu đề "Quá trình phân tích" và meta "{số agent} agent · {số vòng phản biện} vòng phản biện · {thời lượng}", cùng link "Mở tất cả" / "Thu gọn".
- Hàng chip lọc: "Tất cả" + mỗi actor có trong steps, mỗi chip kèm chấm màu. Màu actor lấy từ bảng màu trung tính + 3 hue của data-vis (Company, Sector, Phản biện), có tên bằng chữ, không chỉ màu.
- Mỗi step là một dòng: `mm:ss` (mono 12px) · chấm màu actor · **"{Actor} → {Recipient}"** (500) · summary · chevron. Bấm để mở hoặc đóng. `aria-expanded`. Dùng được bằng bàn phím (Enter/Space).
- Mặc định mở sẵn các step `critique_issue` và `revision`. Khi `live` thì tự cuộn tới step mới **chỉ khi** người dùng đang ở cuối danh sách.
- Nội dung mở ra theo `kind` (ER-1 §2.7):
  - `plan`: "Dạng câu hỏi: {nhãn}", `rationale`, bảng Phép phân tích | Agent (từ `tools`), và bảng Agent | Quyết định | Lý do. Ghi "Kế hoạch theo luật" khi `planner_source = "rules"`.
  - `assign`: khối trích dẫn (viền trái 2px) chứa `task`.
  - `tool_result`: tên phép phân tích, bảng Nội dung | Giá trị | Nguồn (số chú thích) từ `facts`, danh sách dataset tạo ra, và danh sách ô thiếu.
  - `draft`: danh sách câu nháp.
  - `compose`: danh sách khối của report theo thứ tự (loại khối và tiêu đề); ghi "Bố cục mặc định" khi `composition_source = "deterministic_fallback"`.
  - `verify`: "{matched}/{checked} số khớp dữ liệu gốc", kèm danh sách câu bị loại và lý do.
  - `critique_issue`: bảng Loại | Mức độ | Yêu cầu, "Câu bị bắt:" (trích dẫn), "Căn cứ:" `evidence`.
  - `revision`: câu cũ gạch ngang màu `--danger`, câu mới màu `--success`, **kèm nhãn chữ "Trước"/"Sau"** để không phụ thuộc màu.
  - `cross_level_finding`: bảng Tầng | Tín hiệu.
  - `blocked`: message tiếng Việt.
- Không hiện ID kỹ thuật (fact_id, observation_id) ở đây.

## 4. Test (vitest + testing-library)

- `AskPage`: không còn chip hay snapshot id; gửi request chỉ có `{query}`; lỗi hiện message và gợi ý từ fixture `er-error-unsupported-period.json`; bấm gợi ý thì điền vào ô.
- `OrchestratorBoard`: từ fixture trace, chỉ có thẻ Company, Sector, Phản biện (**không có Macro**); trạng thái cuối cùng đều "Xong".
- `ProcessTrace`: lọc theo Company chỉ còn step có Company; mở step revision thấy "Trước"/"Sau"; điều khiển được bằng bàn phím.
- `useTraceStream`: parse SSE `TRACE_STEP` từ chuỗi mẫu; bỏ qua event cũ không lỗi.

## 5. Kiểm tra thủ công (ghi vào PR, kèm ảnh chụp)
- Desktop 1440px và mobile 390px: không cuộn ngang; thẻ agent xuống hàng trên mobile.
- Chế độ bàn phím: Tab tới được ô nhập, nút, chip lọc, từng dòng trace.

## Checklist review
- [ ] Màn A chỉ còn 5 phần ở §1; client không chặn gì.
- [ ] Gợi ý đến từ backend và đều chạy được (đối chiếu acceptance-questions phần A).
- [ ] Không vẽ thẻ cho agent bị bỏ qua.
- [ ] Không còn import mock trong production (`grep -rn "mock" src/pages src/features --include=*.tsx` chỉ còn test).
- [ ] Trace mở được từng bước, có nhãn chữ cho mọi trạng thái màu.
- [ ] Lint, test, build pass. Có ảnh desktop và mobile.
