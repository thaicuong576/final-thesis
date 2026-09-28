# ER-3 · Hộp công cụ phân tích: fact và dataset do code tính

Nhánh: `feat/er-3-analysis-tools` · PR: `feat(api): [ER-3] deterministic analysis tools producing facts and datasets`

Mục tiêu: mỗi công cụ trong danh mục ER-2 §2 chạy được và trả `facts` và `datasets` có provenance. Sau các tool, code tự tính `signals` và ứng viên mâu thuẫn liên tầng. Chưa đổi phần văn; phần văn làm ở ER-4.

Đọc trước:
- `src/thesis_data/dataset_provider.py`: `aggregate_peer_median`, protocol provider;
- `src/thesis_data/dataset_contract.py`: `CanonicalObservation`, `DatasetSource`;
- `adaptive_runtime.py`: `_AdaptiveRun.execute`, `_fetch_direct`, `_fetch_benchmarks` (~1255–1530);
- ER-1 §2.3–2.4, ER-2 §2.

## 1. Core thuần hàm, file mới `src/thesis_data/report_facts.py`

Là file core: không import sqlite3/openai/langgraph, không literal ticker, không biết nhãn tiếng Việt. Thêm vào `APPLICATION_CORE_FILES` của `scripts/check_architecture_guardrails.py`.

- `Fact`: dataclass khớp ER-1 §2.3.
- `FORMULA`:
  ```
  value: fact-value-v1
  peer_median: peer-median-v1
  peer_rank: peer-rank-competition-v1
  gap_to_median: gap-to-median-pp-v1
  delta: delta-pp-v1
  median_delta: median-delta-pp-v1
  pairwise_gap: pairwise-gap-pp-v1
  spread: spread-pp-v1
  ratio_to_median: ratio-to-median-v1
  lead_count: lead-count-v1
  derived_ratio: dùng formula_version của công thức, ví dụ roe-over-roa-v1
  ```
- Hàm (mỗi hàm có docstring 1 dòng và test):
  - `value_fact(obs)`: chỉ nhận obs VALID. `fact:value:{e}:{p}:{m}`.
  - `median_fact(median_obs, universe_id)`: từ `aggregate_peer_median`; median gồm cả mục tiêu, đúng như `_fetch_benchmarks` đang làm. `denominator` = số hợp lệ.
  - `rank_facts(obs_list, universe_id, direction)`: xếp hạng kiểu 1-2-2-4, chỉ trên obs VALID.
    - `rank_desc = 1 + #(giá trị lớn hơn hẳn)`;
    - `rank_better` = `rank_desc` nếu higher, `1 + #(nhỏ hơn hẳn)` nếu lower, `None` nếu neutral.
  - `gap_fact(value, median)`, `delta_fact(from_obs, to_obs)` (trả `None` nếu thiếu), `median_delta_fact(m_from, m_to)`.
  - `pairwise_gap_fact(a_value, b_value)`: `fact:pairwise_gap:{a}:{b}:{p}:{m}`.
  - `spread_fact(obs_list)`: max − min, denominator = số hợp lệ; `input_observation_ids` = obs của max và min.
  - `ratio_to_median_fact(value, median)`: median = 0 thì `None`.
  - `derived_ratio_fact(num_obs, den_obs, formula_id, formula_version)`: mẫu 0 hoặc thiếu thì `None`. `metric_id = formula_id`.
  - `lead_count_fact(a, b, metric_facts, directions, flat_pp)`:
    - `value` = số metric a tốt hơn b vượt ngưỡng;
    - `denominator` = số metric cả hai đều hợp lệ;
    - `input_fact_ids` = các pairwise_gap.
  - `classify_signals(...)` và `detect_cross_level_candidates(...)`: xem §3.

## 2. Công cụ, file mới `src/thesis_api/analysis_tools.py`

```python
@dataclass
class ToolContext:
    provider; dataset_ref; catalog; universe_id: str | None
    universe_members: tuple[str, ...]; presentation   # registry ER-2 §1
    cache: dict   # (entity, period, metric) -> obs | None, dùng chung cho mọi tool trong 1 run

@dataclass
class ToolResult:
    tool: str; agent: str; label: str   # label tiếng Việt cho trace, ví dụ "Xếp hạng bao phủ · 5 ngân hàng"
    facts: list[Fact]; datasets: list[DatasetDTO]; missing: list[MissingCell]

TOOLS: dict[str, Callable[[ToolContext, dict], ToolResult]]
```

Mọi obs lấy qua `ctx.cache` bằng `provider.get_entity_metrics` (gộp theo entity để tránh gọi lặp). Ô thiếu vào `missing` và dataset với `status="missing"`, **không bao giờ là 0**.

| tool | facts | dataset (shape → charts cho phép) |
|---|---|---|
| lookup | value cho mỗi (entity, metric). **Bối cảnh:** nếu có universe thì thêm rank + median; nếu có kỳ liền trước thì thêm delta | `kpi` → kpi_strip |
| peer_position | value, median, rank, gap, ratio_to_median cho mỗi metric | `peer_table` gồm mọi thành viên × metrics tại kỳ → rank_heatmap, comparison_table. Nếu có cặp scatter mặc định thì thêm `paired` → scatter |
| ranking | value + rank cho mọi thành viên; median; spread; ratio_to_median của hạng 1 và hạng chót; với `context_metrics`: value + rank của hạng 1 và hạng chót ở từng metric đó | `ranked_list` sắp theo `rank_desc` (reference_line = median) → ranked_bar, comparison_table |
| trend | value mỗi kỳ; delta liên tiếp; delta đầu → cuối (`from_period` = kỳ hợp lệ đầu tiên); nếu có universe: median mỗi kỳ, median_delta liên tiếp, gap mỗi kỳ; rank tại kỳ cuối | `series` (entity + median theo kỳ; 1 metric) → line_trend; nếu ≥ 2 metric: `series_multi` (mọi thành viên, highlight entity) → small_multiples |
| head_to_head | value; pairwise_gap mỗi cặp (entity đầu so với từng entity còn lại); lead_count mỗi cặp **theo cả hai chiều** (A hơn B và B hơn A); median nếu có universe | `comparison_table` → comparison_table, grouped_bar |
| decomposition | derived_ratio cho mỗi entity (và median các ratio nếu có universe, dùng `aggregate`-kiểu median trên ratio, formula `peer-median-v1`) | `kpi` → kpi_strip |
| dispersion *(mở rộng)* | median, spread, outlier (ratio ≥ 2 hoặc ≤ 0,5 so với median) | `ranked_list` |
| relationship *(mở rộng)* | value hai metric mọi thành viên; rank hai metric | `paired` → scatter |

`dataset_id` deterministic, ví dụ `ds-{tool}-{metric|multi}-{period|range}-{entity|all}`. `allowed_charts` điền theo cột cuối. `highlight_entity_ids` = focus entity (ranking: hạng 1 nếu không có highlight).

Sau mọi tool, tổng hợp:
- `signals` (chỉ khi dạng là company_profile hoặc trend có universe);
- `cross_level_candidates` (§3);
- `source_index`: `observation_id` → `{source_id, title, url, locator}` qua `provider.get_source`.
  - `title = "{entity} · BCTC {hợp nhất|riêng lẻ} {Qn}/{YYYY}"` theo `reporting_scope`;
  - scope không rõ thì bỏ chữ "hợp nhất/riêng lẻ", **không suy đoán** (D-073);
  - `locator = humanize_locator(...)` (§4).

## 3. Tín hiệu và ứng viên mâu thuẫn (core)

- `classify_signals(target, facts, metric_groups, directions, flat_pp)`:
  - Mỗi metric: gap đã chỉnh theo chiều tốt > flat là better, < −flat là worse, còn lại in_line; không có gap thì insufficient.
  - Mỗi nhóm: ≥1 better và 0 worse → above_peers; ≥1 worse và 0 better → below_peers; có cả hai → mixed; toàn in_line → in_line; toàn insufficient → insufficient_data.
- `detect_cross_level_candidates(facts, signals, flat_pp, directions)`:
  - `divergent_signals`: có nhóm above và nhóm below (profile).
  - `counter_trend`: ở cặp kỳ liên tiếp cuối, delta của entity và median_delta trái dấu, cả hai vượt flat.
  - `cross_metric_extreme`: một entity ở vị trí cực (`rank_better` = 1 hoặc = denominator) ở ≥ 2 metric thuộc nhóm khác nhau. Ghi `pattern` = `consistent` (cùng cực) hoặc `tradeoff` (một đầu, một cuối).
    - Ví dụ ranking bao phủ Q4/2024: VPB chót ở cả bao phủ và nợ xấu (consistent); VCB đầu ở bao phủ và nợ xấu (consistent); VCB đầu ở bao phủ nhưng chót ở ROA (tradeoff).

  Ứng viên chưa phải kết luận; Phản biện xác nhận ở ER-4.

## 4. `humanize_locator(raw)` (trong `analysis_tools.py`)
Parse chuỗi `k:v;k:v`.
- `printed_page:21` → `tr. 21`; `printed_pages:2_and_3_and_7` → `tr. 2, 3, 7`.
- `section:…` → bỏ gạch dưới, giữ nguyên chữ.
- Bỏ các key `extraction`, `denominator`, `groups`, `row`, `pdf_page(s)`.
- Ghép bằng ` · `. Không parse được thì trả chuỗi gốc.

Test 2 mẫu thật:
- `pdf_pages:29;printed_page:21;section:note_5_customer_loans;row:loan_quality;denominator:dư_nợ_cho_vay;groups:3|4|5;extraction:visual_transcription` → `tr. 21 · note 5 customer loans`
- `pdf_page:17;printed_page:15;section:Phân tích chất lượng nợ cho vay;extraction:visual_check` → `tr. 15 · Phân tích chất lượng nợ cho vay`

## 5. Nối vào runtime
- `_AdaptiveRun.execute`, sau Stage-1 trên claim của kỳ neo: chạy lần lượt `plan.tools` (agent company và sector chạy song song theo nhóm tool). Gom `ToolResult`.
- `verify_fact_inputs(provider, dataset_ref, facts)`: resolve mọi input observation, yêu cầu VALID và đúng entity/period/metric. Fact sai thì loại, cùng mọi fact phụ thuộc qua `input_fact_ids`, và thêm limitation.
- Tool lỗi thì **không** hủy run: bỏ kết quả tool đó, ghi limitation "Không thực hiện được phép phân tích {label}.", log warning.
- `_render_report` gán `question_type`, `facts`, `datasets`, `signals`. Chưa gán `report_version`/`report_spec` (để ER-4 làm).

## 6. Test

`tests/test_report_facts.py` (core, entity `E1..E5`):
- median chẵn/lẻ khớp `aggregate_peer_median`;
- rank có hòa; đảo chiều theo direction; neutral;
- delta/pairwise/spread/ratio đúng dấu; trường hợp chia 0;
- `lead_count` bỏ qua metric thiếu;
- `classify_signals` đủ 5 verdict;
- 3 loại ứng viên mâu thuẫn, mỗi loại có một tình huống dương và một tình huống âm.

`tests/test_analysis_tools.py` (provider giả có ô thiếu Q1 của entity mục tiêu):
- mỗi tool trả đúng shape và `allowed_charts`;
- ô thiếu là missing;
- median tại anchor khớp claim Sector;
- `humanize_locator`;
- `verify_fact_inputs` loại fact phụ thuộc;
- tool raise thì run vẫn chạy.

**Kiểm với số Gold v5 thật (bắt buộc, dán output vào PR).** Chạy local với snapshot Gold v5 trong worktree, `planner_mode="rules_only"`, rồi so với bảng C trong [acceptance-questions.md](acceptance-questions.md). Số lệch thì dừng và báo, **không sửa công thức cho khớp**.

## Checklist review
- [ ] `report_facts.py` nằm trong danh sách core và pass guardrail check.
- [ ] Mọi fact có `formula_version` và `input_observation_ids` không rỗng.
- [ ] Mỗi tool có test riêng; dataset đúng shape; ô thiếu không thành 0.
- [ ] Số thật khớp bảng C cho cả 5 câu.
- [ ] Tool lỗi không làm hỏng run.
