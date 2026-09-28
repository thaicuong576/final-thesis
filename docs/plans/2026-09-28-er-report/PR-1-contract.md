# ER-1 · Contract và decision (contract-first)

Nhánh: `feat/er-1-contract` · Tiêu đề PR: `feat(contracts): [ER-1] adaptive report, fact, dataset and trace contracts`

Mục tiêu: chốt hình dạng dữ liệu mà backend sẽ trả và frontend sẽ vẽ, **trước khi** viết logic. PR này chỉ thêm schema, tài liệu, type và fixture. Không đổi hành vi runtime.

## 1. Decision D-075 (thêm vào cuối `docs/DECISIONS.md`)

Viết mục `## D-075: Question-adaptive verified reports, deterministic analysis tools and persisted run trace`, bằng tiếng Anh như các decision khác, gồm các ý:

1. **Bối cảnh:** kết quả review staging ngày 2026-09-28 (README §1 của plan này).
2. **A. Dạng câu hỏi và kế hoạch:** Điều phối viên (model) phân loại câu hỏi vào một `question_type` và chọn các công cụ phân tích từ một danh mục đóng. Code kiểm tra kế hoạch với catalog rồi đóng băng trước khi lấy dữ liệu. Model lỗi hoặc kế hoạch không hợp lệ thì dùng kế hoạch theo luật (deterministic). Các arm A/B/C dùng chung kế hoạch đã đóng băng.
3. **B. Công cụ phân tích và fact:** mọi con số được phép nêu là một `Fact` do công cụ deterministic tính từ observation đã accepted, có `formula_version` và `input_observation_ids`.
   - Stage-1 phủ các claim observation tại kỳ neo.
   - Giá trị ở kỳ ngữ cảnh dùng trong fact được kiểm bằng cách resolve từng input observation theo cùng tiêu chí accepted.
   - Công thức phái sinh mới (ví dụ ROE/ROA) phải có trong `docs/METRIC-DICTIONARY.md`.
4. **C. Verified narrative:** thay luật "synthesis không được có số, kỳ, thực thể, từ xu hướng" (D-073/D-074 và các bản vá THES-15 đến THES-22) bằng luật kiểm từng câu:
   - câu phải trích fact;
   - số, hạng, kỳ, thực thể, từ xu hướng và từ so sánh trong câu phải khớp các fact được trích;
   - từ chỉ nguyên nhân và từ khuyến nghị đầu tư vẫn bị cấm;
   - câu sai bị loại và ghi audit; run không thất bại vì câu văn.
5. **D. Report lắp theo khối:** report là một `ReportSpec` gồm các khối trong danh mục đóng (câu trả lời, tiêu đề, luận điểm, mục, hình, lưu ý, bảng). Điều phối viên chọn khối theo câu hỏi và insight. Code kiểm tính tương thích của hình với dữ liệu; spec không hợp lệ thì dùng bố cục mặc định theo dạng câu hỏi.
6. **E. Trace:** mỗi run, kể cả run thất bại, được lưu kèm các `TraceStep` có cấu trúc. Trace không có chain-of-thought hay prompt.
7. **Macro:** câu hỏi có yếu tố vĩ mô nhưng chưa có dữ liệu thì không chặn khi còn phần doanh nghiệp/nhóm trả lời được; ghi limitation.
8. **Đánh giá:** A/B/C dùng chung kế hoạch, công cụ, fact, bộ kiểm tra câu và danh mục khối. Pilot 09/09 là bằng chứng lịch sử, không gán nhãn lại.
9. **Pre-flight guardrail §10:** trả lời đủ 10 câu. Tóm tắt:
   - core mới (`report_facts.py`, `narrative_verification.py`, `report_spec.py`) thuần hàm, không literal ticker;
   - registry chỉ tiêu, công thức phái sinh và nhãn tiếng Việt ở tầng application;
   - không tăng coupling Gold/SQLite.

## 2. `contracts/openapi.json` (viết tay)

Thêm các schema dưới đây vào `components.schemas`. Mọi field mới trên `AnalysisResponse` là **optional**. Tên schema = tên class Pydantic bỏ hậu tố `DTO`.

### 2.1 Metric presentation (item `metrics` của capabilities)
```json
{ "id": "bank.npl_g35", "acronym": "NPL_G35",
  "label": "Tỷ lệ nợ xấu (nhóm 3–5)", "shortLabel": "Nợ xấu",
  "unit": "%", "direction": "lower_is_better", "decimals": 2,
  "group": "asset_quality", "groupLabel": "Chất lượng nợ" }
```
`Capabilities` thêm `suggestedQuestions: string[]` và `questionTypes: [{ "id": "ranking", "label": "Xếp hạng", "example": "…" }]`, chỉ gồm các dạng đã bật.

### 2.2 `QuestionType`
`lookup | company_profile | ranking | trend | head_to_head | sector_theme | relationship`

`sector_theme` và `relationship` là dạng mở rộng; có trong contract nhưng có thể chưa bật (ER-2 §2).

### 2.3 `Fact`
```json
{ "fact_id": "fact:ratio_to_median:VCB:sector:bank:2024_Q4:bank.llr_coverage",
  "fact_type": "ratio_to_median",
  "entity_id": "VCB", "other_entity_id": null, "universe_id": "sector:bank",
  "metric_id": "bank.llr_coverage", "period": "2024_Q4", "from_period": null,
  "value": 2.4208, "unit": "x",
  "rank_better": null, "rank_desc": null, "denominator": null,
  "formula_version": "ratio-to-median-v1",
  "input_observation_ids": ["…"], "input_fact_ids": ["fact:value:…", "fact:median:…"] }
```

| fact_type | value | unit | field bổ sung |
|---|---|---|---|
| value | giá trị observation | đơn vị obs | |
| peer_median | trung vị (gồm cả mục tiêu) | đơn vị obs | denominator |
| peer_rank | rank_better (neutral: rank_desc) | rank | rank_better, rank_desc, denominator |
| gap_to_median | entity − median | pp | |
| delta | v(period) − v(from_period) | pp | from_period |
| median_delta | median(period) − median(from_period) | pp | from_period |
| pairwise_gap | entity − other_entity | pp | other_entity_id |
| spread | max − min trong nhóm | pp | denominator |
| ratio_to_median | entity / median | x | |
| derived_ratio | tử / mẫu theo công thức phái sinh (ví dụ ROE/ROA) | x | `metric_id` = id công thức, ví dụ `derived.roe_over_roa` |
| lead_count | số chỉ tiêu entity tốt hơn other_entity | count | other_entity_id, denominator = số chỉ tiêu so sánh |
| outlier | độ lệch so với trung vị (ratio) | x | dạng mở rộng |

### 2.4 `Dataset` (dữ liệu cho hình và bảng; thay cho `exhibits` cố định)
```json
{ "dataset_id": "ds-ranked-coverage-2024Q4",
  "shape": "ranked_list",
  "title": "Tỷ lệ bao phủ nợ xấu, Q4/2024",
  "produced_by": { "tool": "ranking", "agent": "sector" },
  "metric_ids": ["bank.llr_coverage"], "periods": ["2024_Q4"],
  "highlight_entity_ids": ["VCB"],
  "rows": [ { "entity_id": "VCB", "metric_id": "bank.llr_coverage", "period": "2024_Q4",
              "status": "valid", "value": 223.311, "observation_id": "…",
              "rank_better": 1, "rank_desc": 1, "missing_reason": null } ],
  "reference_lines": [ { "kind": "median", "metric_id": "bank.llr_coverage", "period": "2024_Q4", "value": 92.2484, "fact_id": "…" } ],
  "allowed_charts": ["ranked_bar", "comparison_table"] }
```
- `shape` ∈ `kpi | ranked_list | series | series_multi | peer_table | comparison_table | paired`.
- `rows` luôn là danh sách ô `(entity, metric, period)`, **ô thiếu có `status: "missing"` và `value: null`**.
- `reference_lines` dùng cho đường trung vị (theo kỳ hoặc một kỳ).
- `allowed_charts` do code điền theo bảng tương thích ở ER-4 §4.

### 2.5 `ReportSpec`
```json
{ "kind": "note",
  "note_label": "Ghi chú sàng lọc · Ngân hàng",
  "blocks": [
    { "type": "headline", "sentence": {Sentence} },
    { "type": "figure", "figure_no": 1, "chart": "ranked_bar", "dataset_id": "ds-…",
      "title": "Tỷ lệ bao phủ nợ xấu, Q4/2024", "takeaway": {Sentence} },
    { "type": "key_points", "items": [ { "title": "Khoảng cách lớn", "sentences": [{Sentence}] } ] },
    { "type": "callout", "tone": "notice", "title": "Lưu ý chéo", "finding_id": "x-1", "sentences": [{Sentence}] }
  ] }
```
- `kind` ∈ `answer_card | note`.
- Loại khối (`type`):
  - `answer` = `{value_fact_id, sentences}`, chỉ dùng cho answer_card;
  - `headline` = `{sentence}`;
  - `key_points` = `{items[{title, sentences}]}`;
  - `section` = `{title, sentences}`;
  - `figure` = `{figure_no, chart, dataset_id, title, takeaway}`;
  - `callout` = `{tone: notice|warning, title, finding_id?, sentences}`;
  - `table` = `{dataset_id, title}`.
- `chart` ∈ `kpi_strip | ranked_bar | line_trend | small_multiples | scatter | rank_heatmap | grouped_bar | comparison_table`.
- Code tự thêm các phần không do model quyết: masthead, cột tín hiệu (chỉ company_profile), nguồn, giới hạn, miễn trừ, link quá trình. Các phần này **không** nằm trong `blocks`.

`Sentence`:
```json
{ "sentence_id": "s-3", "text": "…", "fact_ids": ["…"],
  "author": "sector", "source": "model", "revision": 0 }
```
- `author` ∈ `orchestrator | company | sector | macro | critic | system`.
- `source` ∈ `model | deterministic_fallback`.

### 2.6 Trường mới trên `AnalysisResponse`
`report_version` (= `"er-report-v1"`), `question_type`, `report_spec`, `datasets[]`, `facts[]`, `signals[]`, `cross_level_findings[]`, `narrative_audit`, `source_notes[]`, `error`.

- `Signal`: `{group, label, verdict, metric_ids, fact_ids}`. `verdict` ∈ `above_peers | in_line | below_peers | mixed | insufficient_data`.
- `CrossLevelFinding`: `{finding_id, kind, severity, text, fact_ids, status}`.
  - `kind` ∈ `divergent_signals | counter_trend | cross_metric_extreme`;
  - `severity` ∈ `notice | warning`;
  - `status` ∈ `confirmed | dismissed`.
- `NarrativeAudit`: `{sentences_checked, sentences_accepted, sentences_dropped[{sentence_id, author, text, reason_code, reason}], numbers_checked, numbers_matched, blocks_dropped[{type, reason}], composition_source: "model"|"deterministic_fallback"}`.
- `reason_code` ∈ `missing_fact_citation | unknown_fact | number_mismatch | unit_mismatch | rank_mismatch | count_mismatch | period_not_cited | entity_not_in_plan | trend_without_delta | trend_direction_mismatch | comparison_direction_mismatch | causal_language | investment_advice | unresolved_critique`.
- `SourceNote`: `{note_no, source_id, title, url, locator, fact_ids}`.
- `ErrorInfo` (khi `status = "error"`): `{code, message, suggestions[]}`.

### 2.7 Trace
`TraceStep`:
```json
{ "step_id": "t-7", "seq": 7, "t_ms": 26140, "actor": "critic", "recipient": "company",
  "kind": "critique_issue", "summary": "Yêu cầu sửa 1 câu không có căn cứ", "detail": {} }
```
- `actor`/`recipient` ∈ `orchestrator | company | sector | macro | critic | verifier | system`.
- `kind` ∈ `plan | assign | tool_result | draft | verify | compose | critique_issue | cross_level_finding | revision | accept | report_ready | blocked`.

| kind | detail |
|---|---|
| plan | `{question_type, planner_source: "model"\|"rules", rationale, entities, metric_ids, anchor_period, periods, tools: [{tool, agent, label}], agents: [{agent, decision: "run"\|"skip", reason}], defaults_applied}` |
| assign | `{task, tools: [label]}` |
| tool_result | `{tool, label, facts: [{fact_id, label, display_value, source_note_no}], datasets: [{dataset_id, title}], missing: [{entity_id, metric_id, period, reason}]}` |
| draft | `{sentences: [{sentence_id, text, fact_ids}]}` |
| verify | `{sentences_checked, numbers_checked, numbers_matched, dropped: [{sentence_id, text, reason_code, reason}]}` |
| compose | `{kind, blocks: [{type, title}], composition_source}` |
| critique_issue | `{issue_id, round, issue_type, severity, target_sentence_id, target_text, evidence, evidence_fact_ids, required_action}` |
| cross_level_finding | `{finding_id, kind, text, fact_ids}` |
| revision | `{round, sentence_id, before, after, verified}` |
| accept | `{round, open_issues}` |
| report_ready | `{report_id, duration_ms, model_calls}` |
| blocked | `{code, message}` |

`RunTrace`: `{run_id, status, query, created_at, duration_ms, arm, steps[]}`.

### 2.8 Paths
Bổ sung các path còn thiếu: `GET /api/capabilities`, `GET /api/runs`, `GET /api/runs/{run_id}`, `GET /api/runs/{run_id}/trace` (mới), `GET /api/reports/{report_id}`. Mô tả SSE của `/api/analyze/stream`: thêm event `TRACE_STEP`, payload là `TraceStep`.

## 3. Tài liệu
- `docs/DATA-CONTRACT.md`: thêm mục "Report v2 (er-report-v1)" mô tả question type, công cụ và fact, dataset (hiển thị nguyên giá trị observation, không qua model), ReportSpec và luật khối, verified sentence, trace. Dẫn chiếu D-075.
- `docs/METRIC-DICTIONARY.md`: thêm `derived.roe_over_roa` (ROE/ROA, đơn vị "lần"). Ghi rõ đây là xấp xỉ bội số vốn chủ sở hữu bình quân, chỉ đúng khi ROE và ROA cùng cơ sở annualize và bình quân; chỉ mô tả, không suy nhân quả.

## 4. `contracts/run-store-schema.sql`
Thêm các cột `trace_json TEXT`, `error_code TEXT`, `duration_ms INTEGER`, `model_calls INTEGER`, `input_tokens INTEGER`, `output_tokens INTEGER`, `arm TEXT`, `question_type TEXT`. Ghi chú: migration idempotent làm ở ER-5; run lỗi cũng được lưu; `target_ticker`/`period` có thể rỗng.

## 5. Pydantic DTO (`src/thesis_api/schemas.py`)
Class cho mọi schema ở §2, dùng `Literal[...]` cho enum. Khối trong `ReportSpec` là **discriminated union** theo `type`. Thêm các field optional trên `AnalysisResponse` (§2.6).

## 6. TypeScript types và fixture
- Type tương ứng trong `frontend/src/features/equity-report/model/types.ts` (thư mục mới) và `frontend/src/features/analysis-session/model/types.ts`. **Giữ snake_case** y như JSON.
- Fixture trong `frontend/src/test/fixtures/`, **dùng đúng số Gold v5** (bảng ở `acceptance-questions.md` §C):

| File | Câu hỏi | Nội dung bắt buộc |
|---|---|---|
| `er-lookup-vcb-npl-2024q4.json` | Tỷ lệ nợ xấu của VCB quý 4/2024 là bao nhiêu? | answer_card; answer 0,96%; câu bối cảnh có hạng và delta |
| `er-ranking-coverage-2024q4.json` | Ngân hàng nào có đệm dự phòng dày nhất quý 4/2024? | ranked_bar; ratio_to_median 2,4; callout VPB (bao phủ thấp nhất, nợ xấu cao nhất) |
| `er-trend-vpb-roe-2024.json` | ROE của VPB thay đổi thế nào trong năm 2024? | line_trend có đường trung vị; delta 4 kỳ; gap Q1 và Q4 |
| `er-h2h-acb-tcb-2024q4.json` | So sánh ACB và TCB quý 4/2024 | comparison_table; lead_count 3/4; derived_ratio ROE/ROA của cả hai |
| `er-profile-acb-2024q4.json` | Sức khỏe tài chính của ACB so với các ngân hàng cùng nhóm, quý 4/2024 | scatter + rank_heatmap + small_multiples; signals; 2 cross-level findings; 1 câu bị loại; ACB Q1 missing |
| `er-trace-acb-2024q4.json` | (trace của report profile) | đủ các kind theo thứ tự ở ER-5 |
| `er-error-unsupported-period.json` | Tỷ lệ nợ xấu của ACB quý 4/2023 | error + 3 gợi ý |

Fixture chỉ import từ test.

## 7. Test
`tests/test_contract_er_report.py`:
1. openapi.json có đủ schema ở §2 và path ở §2.8; pass `check_openapi_contract.py`.
2. Mỗi DTO mới có tập property khớp với schema cùng tên (bỏ `DTO`) trong openapi.
3. `AnalysisResponse` cũ, không có field mới, vẫn validate được.
4. Mọi fixture report validate bằng `AnalysisResponse`; fixture trace validate bằng `RunTraceDTO`.
5. Mọi `dataset_id` trong `report_spec` của fixture đều tồn tại trong `datasets`; mọi `fact_id` của câu đều tồn tại trong `facts`.

Frontend: `npm run build` pass.

## Checklist review
- [ ] D-075 đủ 9 ý và trả lời 10 câu pre-flight.
- [ ] openapi pass script; có `/api/runs/{run_id}/trace` và `TRACE_STEP`.
- [ ] Field mới đều optional; test cũ không phải sửa; diff `adaptive_runtime.py`/`service.py` = 0.
- [ ] 7 fixture đúng số Gold v5, có ô thiếu và câu bị loại ở fixture profile.
- [ ] `derived.roe_over_roa` có trong METRIC-DICTIONARY kèm giới hạn.
