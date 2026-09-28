# ER-2 · Hiểu câu hỏi: dạng câu hỏi, kế hoạch công cụ, lỗi thân thiện

Nhánh: `feat/er-2-question-planner` · PR: `feat(api): [ER-2] question-type planner with tool plan and Vietnamese resolver`

Mục tiêu: mọi câu trong [acceptance-questions.md](acceptance-questions.md) phần A ra đúng `question_type` và đúng kế hoạch công cụ. Câu ngoài phạm vi trả lỗi tiếng Việt kèm gợi ý. PR này **chỉ lập kế hoạch**; công cụ chạy ở ER-3, phần văn và bố cục ở ER-4.

Đọc trước: `src/thesis_api/adaptive_runtime.py` (từ đầu tới hết `_plan_request`, dòng ~101–740), `src/thesis_api/service.py` (dòng 95–380), D-074, D-075.

## 1. Registry chỉ tiêu, file mới `src/thesis_api/metric_presentation.py`

Cấu hình tầng application: được biết metric id của bộ dữ liệu ngân hàng, **không** chứa ticker.

```python
@dataclass(frozen=True)
class MetricPresentation:
    metric_id: str; label: str; short_label: str; unit: str
    direction: Literal["higher_is_better", "lower_is_better", "neutral"]
    decimals: int; delta_decimals: int; flat_threshold_pp: float
    group: str; group_label: str
    synonyms: tuple[str, ...]      # có dấu; so khớp sau normalize (bỏ dấu + casefold)
    superlative_hi: tuple[str, ...]  # từ chỉ "cao" riêng, ví dụ ("dày",) cho bao phủ
    superlative_lo: tuple[str, ...]  # ("mỏng",)
```

| metric_id | label | short | dir | dec | Δdec | flat | group / label | synonyms tối thiểu | hi / lo |
|---|---|---|---|---|---|---|---|---|---|
| bank.npl_g35 | Tỷ lệ nợ xấu (nhóm 3–5) | Nợ xấu | lower | 2 | 2 | 0.05 | asset_quality / Chất lượng nợ | nợ xấu, tỷ lệ nợ xấu, npl, npl_g35 | cao / thấp |
| bank.llr_coverage | Tỷ lệ bao phủ nợ xấu | Bao phủ | higher | 1 | 1 | 1.0 | provisioning / Đệm dự phòng | bao phủ nợ xấu, tỷ lệ bao phủ, bao phủ, dự phòng, đệm dự phòng, llr, coverage | dày, cao / mỏng, thấp |
| bank.roa | ROA | ROA | higher | 2 | 2 | 0.05 | profitability / Sinh lời | roa, sinh lời trên tài sản | cao / thấp |
| bank.roe | ROE | ROE | higher | 1 | 1 | 0.5 | profitability / Sinh lời | roe, sinh lời trên vốn | cao / thấp |

Thêm sẵn (chưa có dữ liệu): nim, casa, car, cir, ldr.

- Chủ đề, tức cụm từ gọi cả nhóm chỉ tiêu:
  - "chất lượng tài sản", "chất lượng tín dụng", "rủi ro tín dụng", "chất lượng nợ" → asset_quality + provisioning;
  - "sinh lời", "hiệu quả", "lợi nhuận" → profitability;
  - "sức khỏe tài chính", "tổng quan", "toàn diện" → tất cả.
- Công thức phái sinh:
  ```python
  DERIVED = {"derived.roe_over_roa": DerivedFormula(numerator="bank.roe", denominator="bank.roa",
             label="ROE/ROA (đòn bẩy ngầm định)", unit="x", decimals=1, formula_version="roe-over-roa-v1")}
  ```
- Cặp scatter mặc định: `[("bank.npl_g35","bank.llr_coverage"), ("bank.roe","bank.npl_g35")]`.
- Metric lạ: fallback `label = display_name`, `direction = "neutral"`, `decimals = 2`.

`get_capabilities` trả thêm cho mỗi metric: `label, shortLabel, unit, direction, decimals, group, groupLabel`. Trả thêm `suggestedQuestions` (§6) và `questionTypes` (chỉ các dạng đã bật).

## 2. Dạng câu hỏi và danh mục công cụ

| question_type | Số thực thể | Công cụ mặc định (luật) | Trạng thái |
|---|---|---|---|
| lookup | 1–3 | `lookup(entities, metrics, anchor)` | bật |
| company_profile | 1 | `peer_position(target, metrics, anchor)`, `trend(target, metrics, context)`, `decomposition([target], anchor)` nếu có ROE và ROA | bật |
| ranking | 0–1 (1 = làm nổi bật) | `ranking(metric, anchor, context_metrics)` với metric là chỉ tiêu đầu tiên; context_metrics là tối đa 2 chỉ tiêu khác nhóm | bật |
| trend | 1 | `trend(target, metrics, periods)`, `peer_position(target, metrics, anchor)` | bật |
| head_to_head | 2–3 | `head_to_head(entities, metrics, anchor)`, `decomposition(entities, anchor)` nếu có ROE và ROA | bật |
| sector_theme | 0 | `ranking` cho từng metric của chủ đề + `dispersion(metric, anchor)` | mở rộng, **tắt** |
| relationship | 0 | `relationship(metric_x, metric_y, anchor)` | mở rộng, **tắt** |

Dạng đang tắt: planner không được chọn. Nếu luật suy ra dạng này thì chuyển về dạng gần nhất: sector_theme → ranking của chỉ tiêu đầu tiên; relationship → ranking của metric_x kèm context_metrics=[metric_y].

Danh mục công cụ (tên, tham số, agent phụ trách) là hằng số trong `src/thesis_api/analysis_tools_catalog.py`. ER-3 cài đặt thân hàm.

| tool | agent | params |
|---|---|---|
| lookup | company | entities[1..3], metrics[1..4], period |
| peer_position | sector | entity, metrics[1..4], period |
| ranking | sector | metric, period, highlight_entity?, context_metrics[0..2] |
| trend | company | entity, metrics[1..4], periods[2..4] |
| head_to_head | sector | entities[2..3], metrics[1..4], period |
| decomposition | company | entities[1..3], period, formula |
| dispersion | sector | metric, period (mở rộng) |
| relationship | sector | metric_x, metric_y, period (mở rộng) |

## 3. Resolver deterministic, file mới `src/thesis_api/query_understanding.py`

```python
@dataclass(frozen=True)
class ResolvedQuery:
    entities: tuple[str, ...]          # theo thứ tự xuất hiện
    unknown_entity_tokens: tuple[str, ...]  # chuỗi giống ticker nhưng không có trong catalog
    explicit_periods: tuple[str, ...]  # rỗng nếu câu không nêu
    year_only: int | None
    anchor_period: str                 # suy ra, hoặc kỳ mới nhất nếu không nêu
    context_periods: tuple[str, ...]   # cùng năm, <= anchor, tăng dần, tối đa 4
    explicit_metrics: tuple[str, ...]; topic_metrics: tuple[str, ...]
    flags: frozenset[str]   # lookup, superlative, comparison, trend, macro, why, relationship
    defaults_applied: tuple[str, ...]

def resolve_query(query: str, catalog) -> ResolvedQuery   # hàm thuần, raise AnalysisBlocked
```

- **Chuẩn hóa:** NFC, casefold, `–—` → `-`, gộp khoảng trắng. Có thêm bản bỏ dấu (`đ` → `d`). Khớp trên cả hai bản.
- **Kỳ** (theo thứ tự ưu tiên):
  - dải: "từ quý 1 đến quý 4/2024", "Q1–Q4/2024", "quý 1-4/2024", "2024_Q1 đến 2024_Q4";
  - quý: "quý 4/2024", "quý 4 năm 2024", "Q4/2024", "Q4 2024", "Q4-2024", "4Q24", "2024Q4", "2024_Q4";
  - "cuối năm 2024" → Q4;
  - chỉ có năm ("năm 2024", "trong 2024") → `year_only`, anchor = kỳ mới nhất của năm trong catalog;
  - không nêu → anchor = kỳ mới nhất của catalog, `defaults_applied += period_defaulted_to_latest`.

  Kỳ không có trong catalog thì raise `unsupported_period`.
- **Chỉ tiêu:** khớp synonym (bảng §1) → `explicit_metrics`; khớp chủ đề → `topic_metrics`. Metric có trong registry nhưng không có trong catalog thì raise `unsupported_metric`.
- **Thực thể:** dùng `_catalog_entity_matches` nhưng giữ thứ tự xuất hiện. Token 3–4 chữ in hoa không có trong catalog → `unknown_entity_tokens`.
- **Cờ (`flags`):**
  - `lookup`: "bao nhiêu", "là mấy", "giá trị", "con số";
  - `superlative`: "nào", "nhất", "top", "xếp hạng", "đứng thứ", "dẫn đầu";
  - `comparison`: "so sánh", "so với", "cùng nhóm", "ngành", "trung vị", "peer";
  - `trend`: "diễn biến", "xu hướng", "thay đổi", "qua các quý", có dải kỳ, hoặc `year_only`;
  - `macro` (sửa `_MACRO_TERMS` ở `service.py`: **bỏ** "tín dụng" và "lãi suất" đứng một mình): "vĩ mô", "lãi suất điều hành", "chính sách tiền tệ", "nhnn", "ngân hàng nhà nước", "sbv", "lạm phát", "cpi", "tăng trưởng tín dụng toàn ngành", "truyền dẫn";
  - `why`: "vì sao", "tại sao", "nguyên nhân";
  - `relationship`: "có đi cùng", "tương quan", "quan hệ giữa", "liên quan giữa".

## 4. Planner: model đề xuất, code kiểm và đóng băng

File mới `src/thesis_api/analysis_planner.py`.

### 4.1 Kế hoạch theo luật (luôn có, dùng làm fallback và làm chuẩn test)
`rules_plan(resolved, catalog) -> PlanSpec`:
1. `unknown_entity_tokens` và không có entity hợp lệ → raise `unsupported_entity`.
2. Chọn dạng:
   - `lookup` và có ≥1 entity → **lookup**;
   - `superlative` và ≤1 entity → **ranking**;
   - ≥2 entity → **head_to_head**;
   - `trend` và 1 entity → **trend**;
   - 1 entity → **company_profile**;
   - 0 entity: có `relationship` và 2 metric thì relationship (đang tắt nên chuyển theo §2); ngược lại thì ranking;
   - 0 entity mà chỉ có `macro` → raise `unsupported_macro_scope`.
3. Chỉ tiêu:
   - có `explicit_metrics` thì dùng đúng những metric đó;
   - không có thì dùng `topic_metrics`;
   - không có nữa thì: ranking dùng metric đầu tiên của catalog; lookup raise `metric_required`; các dạng còn lại dùng tất cả.
4. Kỳ:
   - trend dùng `explicit_periods`/năm/context (tối đa 4);
   - lookup, ranking, head_to_head dùng anchor;
   - company_profile dùng anchor + context.
5. Công cụ: theo bảng §2.
6. Macro: có cờ `macro` và có phần doanh nghiệp thì thêm agent macro với `decision="skip"` và lý do "Chưa có dữ liệu vĩ mô đã kiểm định"; thêm limitation.
7. Có cờ `why`: thêm limitation "Dữ liệu hiện có không đủ để kết luận nguyên nhân; báo cáo chỉ mô tả và so sánh." Nếu có ROE và ROA thì đảm bảo có tool `decomposition`.

### 4.2 Kế hoạch do model đề xuất
`model_plan(question, resolved, catalog, tools_catalog) -> PlanSpec | None`: gọi model 1 lần, JSON schema strict. Prompt (hằng số):
```
Bạn là điều phối viên của một nhóm phân tích ngân hàng. Đọc câu hỏi và lập kế hoạch.
Chọn đúng một question_type trong danh sách được bật, chọn công cụ trong danh mục (tối đa 5 lần gọi) với tham số hợp lệ,
và viết 1 câu tiếng Việt giải thích lựa chọn (rationale).
Ràng buộc:
- Chỉ dùng ngân hàng, kỳ, chỉ tiêu có trong "catalog".
- Nếu "da_nhan_dien" đã có ngân hàng/kỳ/chỉ tiêu tường minh thì phải giữ nguyên, không thay, không bỏ.
- Được thêm công cụ bổ trợ nếu giúp trả lời sâu hơn (ví dụ decomposition khi hỏi về sinh lời), không thêm công cụ vô ích.
- Không lập kế hoạch cho dữ liệu không có (vĩ mô, định giá).
Trả về JSON: {"question_type":"…","focus_entity":…,"entities":[…],"metrics":[…],"anchor_period":"…","periods":[…],
"tools":[{"tool":"…","params":{…}}],"rationale":"…"}
```
Payload gồm: câu hỏi, `ResolvedQuery` (đã nhận diện), catalog rút gọn (id và nhãn tiếng Việt), danh mục dạng câu hỏi đang bật, danh mục công cụ.

### 4.3 Kiểm và chọn
`validate_plan(spec, resolved, catalog) -> list[str]` trả danh sách lỗi:
- id nằm ngoài catalog;
- dạng đang tắt;
- số entity không khớp dạng (§2);
- có tool không thuộc danh mục, hoặc tham số sai kiểu hay sai số lượng;
- vượt 5 tool;
- đổi hay bỏ entity/kỳ/metric tường minh của resolver;
- kỳ của trend ít hơn 2.

`plan_question(...)`:
- `model_plan` hợp lệ thì dùng, `planner_source="model"`;
- ngược lại dùng `rules_plan`, `planner_source="rules"`, ghi lý do fallback (danh sách lỗi hoặc "model_error") vào plan.
- `Settings.planner_mode` ∈ `model_with_fallback` (mặc định) | `rules_only` (dùng cho test offline và khi cần tiết kiệm).

### 4.4 Đóng băng thành AnalysisPlan
`build_analysis_plan(spec, catalog, dataset_ref) -> AnalysisPlan` (thay nội dung chính của `_plan_request` cho request không có `periods` tường minh):
- `scope.entities` = mọi entity mà các tool dùng tới (ranking: toàn universe; thêm universe id nếu dùng median). `periods` = `(anchor,)`. `company_metric_ids` = union metrics.
- Requirements: mỗi `(entity, metric, anchor)` mà tool dùng → một `FACTUAL_OBSERVATION` (`VALUE_OR_ACCEPTED_MISSINGNESS`). `required_agents` = agent của tool. Mỗi median ở anchor → một `COMPARISON`.
- Kỳ ngữ cảnh **không** thành requirement (D-075 B). Lưu `context_periods` và `tools` vào `AnalysisPlanDTO` (field mới optional: `question_type`, `planner_source`, `rationale_vi`, `tools`, `context_periods`) và vào payload `PLAN_CREATED`.
- `applicable_links`: company → peer benchmark cho mỗi metric có median (giữ logic hiện có).
- Request có `periods` tường minh: giữ nguyên đường D-074 cũ, không qua planner.

## 5. Đường cũ cần gỡ hoặc giữ
- `_is_comparison_requested`, `_has_macro_request`, `_check_single_period`: không còn dùng cho request không có `periods`; xóa nếu không còn nơi gọi.
- Luật `multi_period_unsupported` cho câu tự nhiên: bỏ (dải kỳ chỉ là context). Giữ cho request có `periods` tường minh kèm so sánh.
- `target_entity_ambiguous`: bỏ; nhiều thực thể giờ là head_to_head.

## 6. Lỗi thân thiện và gợi ý, file mới `src/thesis_api/messages_vi.py`

- `MESSAGES`: mọi code `AnalysisBlocked` cũ và mới, gồm `unsupported_period`, `unsupported_metric`, `unsupported_entity`, `metric_required`, `unsupported_macro_scope`, `provider_failure`, `adaptive_runtime_failure`, `analysis_writer_unconfigured`, `semantic_provider_unconfigured`. Placeholder `{periods}`, `{metrics}`, `{entities}` được điền từ catalog.
- `suggestions_for(catalog) -> list[str]`: 5 câu, mỗi câu một dạng đang bật, sinh **từ catalog** (thực thể thứ 1, 2, 3…, kỳ mới nhất, chỉ tiêu theo nhóm). Không hard-code ticker. Mẫu:
  - lookup: `Tỷ lệ nợ xấu của {e1} quý {q}/{y} là bao nhiêu?`
  - ranking: `Ngân hàng nào có {label viết thường của metric higher_is_better đầu tiên} cao nhất quý {q}/{y}?`
  - trend: `ROE của {e2} thay đổi thế nào trong năm {y}?`
  - head_to_head: `So sánh {e1} và {e3} quý {q}/{y}`
  - company_profile: `Sức khỏe tài chính của {e1} so với các ngân hàng cùng nhóm, quý {q}/{y}`
- `_error_report` điền `error = ErrorInfoDTO(code, message, suggestions[:3])`. Giữ `limitations[0] = "<code>: <detail>"` như cũ.
- Có test: mọi câu gợi ý đi qua `rules_plan` phải ra đúng dạng tương ứng và không raise.

## 7. Test

`tests/test_query_understanding.py` (catalog giả với thực thể trung tính `BANK_A`…`BANK_E`, kỳ 2024_Q1..Q4, 4 metric):
- Đủ các mẫu kỳ ở §3, có bản không dấu.
- Kỳ ngoài catalog → `unsupported_period`, message có "Q1–Q4/2024".
- Synonym và chủ đề; "chất lượng tín dụng" không bật macro.
- Mã lạ ("BANK_Z", hoặc "HDB" trong câu tiếng Việt) → `unsupported_entity`, message liệt kê thực thể.

`tests/test_analysis_planner.py`:
- `rules_plan` cho mọi câu phần A (thay ticker bằng thực thể trung tính) ra đúng dạng, metrics, kỳ, tools như bảng.
- `model_plan` với fake model:
  - trả plan hợp lệ → dùng, `planner_source="model"`;
  - đổi entity tường minh → bị từ chối, fallback về luật kèm lý do;
  - chọn dạng đang tắt → fallback;
  - model raise → fallback.
- `build_analysis_plan`: ranking có requirement cho cả 5 thực thể; context periods không thành requirement.

`tests/test_api_analyze.py`: test tích hợp chạy mọi câu phần A với `planner_mode="rules_only"` và provider test. Assert `status != "error"` (ở PR này report vẫn là dạng cũ; chỉ kiểm plan).

Test cũ cần sửa, và chỉ những chỗ này:
- `tests/test_api_analyze.py` ~1140–1151: tách câu tự nhiên (giờ chạy được) khỏi request có `periods` tường minh (vẫn bị chặn).
- `tests/test_api_stream.py::test_unsupported_macro_scope_is_blocked_without_claim_or_revision_events`: có target nên không còn bị chặn; đổi assert và thêm test macro không có target vẫn bị chặn.
- `tests/test_api_trend_runtime.py` ~415–434: dùng `periods` tường minh nên giữ nguyên.

## Checklist review
- [ ] Không literal ticker trong `query_understanding.py`, `analysis_planner.py`, `messages_vi.py`, `metric_presentation.py`, `analysis_tools_catalog.py`.
- [ ] Mọi câu phần A ra đúng dạng và tools bằng luật; model plan bị kiểm và có fallback.
- [ ] Planner không đổi được entity/kỳ/metric tường minh.
- [ ] Dạng đang tắt không bao giờ được chọn.
- [ ] Lỗi có message tiếng Việt và gợi ý sinh từ catalog; gợi ý chạy được.
- [ ] Đường D-074 (`periods` tường minh) không đổi.
