# ER-4 · Agent viết câu có trích fact, lắp report theo khối, kiểm từng câu, phản biện

Nhánh: `feat/er-4-adaptive-report` · PR: `feat(api): [ER-4] verified narrative, block-composed adaptive report, sentence-level critique`

PR quan trọng nhất. Thay luật "cấm số" bằng "kiểm từng câu" (D-075 C). Report được lắp từ khối theo câu hỏi (D-075 D).

Đọc trước:
- D-075; ER-1 §2.5–2.6; ER-2 §2; ER-3;
- `src/thesis_api/analysis_writer.py`;
- `adaptive_runtime.py` `_AdaptiveRun` (~841–1240, 1529–1670);
- `src/thesis_data/semantic_critic.py`, `revision_controller.py`, `openai_semantic_critic.py` (`_CRITIC_INSTRUCTIONS`, `_normalize_critic_output`);
- `src/thesis_data/schema.py` (`CritiqueIssue` và các enum).

## 1. Luồng trong `_AdaptiveRun.execute`

```
plan (ER-2) → claim kỳ neo + Stage-1 (giữ nguyên) → chạy tools (ER-3)
→ [song song] Company.write_findings(kết quả tool của company) ; Sector.write_findings(kết quả tool của sector)
→ verify từng câu
→ Orchestrator.compose_report(câu đã qua kiểm, datasets, signals, ứng viên mâu thuẫn) → ReportSpec
→ validate_report_spec + verify câu mới của orchestrator
→ Critic vòng 1 → issue theo sentence_id / block + xác nhận hoặc bác ứng viên mâu thuẫn
→ revision có mục tiêu → verify lại → Critic vòng 2 (tối đa 2 vòng)
→ report_version = "er-report-v1"
```

- Atomic claim **không bị LLM viết lại**. `claim_text` là câu deterministic. Bỏ `_invoke_specialist_writer`.
- Dạng `lookup`: bỏ Sector.write_findings nếu không có tool của sector. Orchestrator có thể lắp `answer_card` chỉ từ câu của Company.
- Agent chỉ nhận fact của tool thuộc về mình (ER-2 §2 cột agent). Orchestrator nhận mọi fact đã được trích trong câu của agent con, cộng fact của signals và ứng viên mâu thuẫn.

## 2. Bộ kiểm tra câu, core, file mới `src/thesis_data/narrative_verification.py`

Thêm vào `APPLICATION_CORE_FILES`. Thuần hàm, không literal ticker, không import openai.

```python
@dataclass(frozen=True)
class NarrativeSentence: sentence_id: str; author: str; text: str; fact_ids: tuple[str, ...]; source: str; revision: int = 0
@dataclass(frozen=True)
class SentenceVerdict: ok: bool; reason_code: str | None; reason: str | None; numbers_checked: int; numbers_matched: int
@dataclass(frozen=True)
class VerificationContext:
    facts: Mapping[str, Fact]; plan_entities: frozenset[str]; catalog_entities: frozenset[str]
    metric_terms: Mapping[str, tuple[str, ...]]   # metric_id -> tên và synonym (từ registry, truyền vào)
    hi_words: Mapping[str, tuple[str, ...]]; lo_words: Mapping[str, tuple[str, ...]]
    directions: Mapping[str, str]; flat_pp: Mapping[str, float]; anchor_year: int
    lexicon: NarrativeLexicon = VI_LEXICON
def verify_sentence(s, ctx) -> SentenceVerdict
def verify_all(sentences, ctx) -> tuple[list[NarrativeSentence], list[DroppedSentence], AuditCounts]
```

Thứ tự kiểm: sau NFC + casefold, khớp **nguyên từ**, dừng ở lỗi đầu tiên.
1. `fact_ids` rỗng → `missing_fact_citation`. Có fact_id không tồn tại → `unknown_fact`.
2. **Nguyên nhân:** vì, bởi vì, bởi, do, do đó, nhờ, nhờ vào, dẫn đến, dẫn tới, khiến, gây ra, kéo theo, xuất phát từ, vì vậy. **Loại trừ** "lý do", "tự do", "do dự". Vi phạm → `causal_language`.
   Lưu ý: "hàm ý", "đi cùng", "gắn với" **không** phải từ nhân quả.
3. **Khuyến nghị đầu tư:** mua, bán, nắm giữ, khuyến nghị, giá mục tiêu, nên đầu tư, định giá hấp dẫn. **Loại trừ** "bán lẻ", "bán buôn", "mua bán nợ". Vi phạm → `investment_advice`.
4. **Thực thể:** ticker trong câu thuộc catalog nhưng ngoài `plan_entities` → `entity_not_in_plan`.
5. **Kỳ:** quý N/YYYY, quý N năm YYYY, quý N, QN/YYYY, QN, năm YYYY, YYYY. Mỗi kỳ phải thuộc `period`/`from_period` của fact được trích; "quý N" không có năm thì hiểu là `anchor_year`. Sai → `period_not_cited`. Gỡ token kỳ khỏi câu sau khi kiểm.
6. **Đếm:** "N/M chỉ tiêu", "N trên M chỉ tiêu" phải khớp một fact `lead_count` (value=N, denominator=M). Sai → `count_mismatch`. Gỡ token.
7. **Hạng:** hạng N/M, thứ N/M, N/M (M không phải năm); cao/thấp nhất; cao/thấp thứ n; tốt/kém nhất; dẫn đầu; đứng cuối; nhóm đầu; nhóm cuối; cùng hi_words/lo_words của metric (ví dụ "dày nhất", "mỏng nhất"). Chữ số thứ tự: nhì/hai=2, ba=3, tư/bốn=4, năm=5.
   - Cần ít nhất một fact `peer_rank` được trích khớp:
     - cao/hi_word so với `rank_desc`;
     - thấp/lo_word so với `denominator + 1 − rank_desc`;
     - tốt/dẫn đầu so với `rank_better`;
     - kém/đứng cuối so với `denominator + 1 − rank_better`;
     - nhóm đầu nghĩa là `rank_better ≤ max(1, round(M/3))`; nhóm cuối là phần đối xứng;
     - `N/M` cần `value == N` và `denominator == M`.
   - Sai → `rank_mismatch`. Gỡ token.
8. **Số lượng thực thể:** "(số|một…mười) (ngân hàng|thành viên)" phải bằng `denominator` của một fact được trích. Sai → `number_mismatch`.
9. **Số còn lại** `(\d+(?:[.,]\d+)?)` kèm hậu tố. `,` hoặc `.` là dấu thập phân. `d` = số chữ số sau dấu. Khớp nếu `|x − v| ≤ 0.5·10^(−d) + 1e−9`.
   - `%` → so với fact `value`/`peer_median` (đơn vị %).
   - `điểm %`, `điểm phần trăm`, `pp`, `điểm` → so với `gap_to_median|delta|median_delta|pairwise_gap|spread`, dùng **trị tuyệt đối**.
   - `lần`, `x` → so với `ratio_to_median|derived_ratio`.
   - Số không hậu tố → so với fact bất kỳ được trích.
   - Sai loại đơn vị → `unit_mismatch`. Không khớp → `number_mismatch`.
   - **Gán đúng chỉ tiêu và thực thể:** nếu trong 6 từ trước số có tên/synonym metric X, fact khớp phải có `metric_id == X` (hoặc là derived_ratio có X trong công thức). Nếu có ticker Y ngay trước số, fact khớp phải có `entity_id == Y`; median và spread bỏ qua điều kiện này. Sai → `number_mismatch`.
10. **Xu hướng:** tăng, tăng lên, đi lên, giảm, giảm xuống, đi xuống, đi ngang, ổn định, không đổi, cải thiện, xấu đi, suy giảm, liên tục, thu hẹp, nới rộng, ngược chiều, ngược xu hướng.
    - Cần delta/median_delta (hoặc ≥ 2 gap cùng metric khác kỳ, cho thu hẹp/nới rộng) → nếu không có: `trend_without_delta`.
    - tăng: δ > flat. giảm: δ < −flat. đi ngang/ổn định/không đổi: |δ| ≤ flat.
    - cải thiện / xấu đi: dựa trên δ đã chỉnh theo chiều tốt.
    - "tăng/giảm liên tục": **mọi** delta liên tiếp được trích của metric đó cùng dấu và vượt flat.
    - thu hẹp: |gap kỳ sau| < |gap kỳ trước|; nới rộng: ngược lại.
    - ngược chiều/ngược xu hướng: delta và median_delta trái dấu, cả hai vượt flat.
    - Chọn δ theo metric được nhắc gần nhất. Sai → `trend_direction_mismatch`.
11. **So sánh:** cao hơn, thấp hơn, dày hơn, mỏng hơn, vượt, nhỉnh hơn, dẫn ở, trên trung vị, dưới trung vị, tốt hơn, kém hơn, bằng/ngang trung vị, ngang nhóm.
    - Cần gap, pairwise_gap, hoặc hai fact value cùng metric.
    - Hướng đúng theo dấu thô (cao/dày/vượt/trên) hoặc theo chiều tốt (tốt/kém/nhỉnh/dẫn).
    - bằng/ngang: |gap| ≤ flat.
    - Sai → `comparison_direction_mismatch`.

**Ngoài danh sách trên không có luật cấm nào khác.**

### 2.1 Test core `tests/test_narrative_verification.py` (bắt buộc)
Dùng fact giả mô phỏng số thật (bảng C của acceptance-questions). Mỗi dòng là một test:
- "ROE 21,7%, cao thứ hai trong 5 ngân hàng, hơn trung vị nhóm 3,1 điểm %." → ok
- "ROE 21,8%" → ok (±0,05); "ROE 21,80%" → number_mismatch; "ROE 1,51%" (trích cả fact NPL) → number_mismatch
- "Nợ xấu cải thiện so với quý 3" với δ = +0,0001 → trend_direction_mismatch
- "Nợ xấu đi ngang từ quý 2 (1,50%)" trích [value Q2, delta Q2→Q3, delta Q3→Q4] → ok; chỉ trích [value Q4] → period_not_cited
- "Bao phủ giảm 2,5 điểm % so với quý 3, ngược xu hướng nhóm" → ok
- "VCB có đệm dự phòng dày nhất, gấp 2,4 lần trung vị nhóm" → ok; "gấp 2,5 lần" → number_mismatch
- "ROE của VPB tăng liên tục qua 4 quý" trích 3 delta dương → ok; khi một delta âm → trend_direction_mismatch
- "Khoảng cách với trung vị thu hẹp từ 9,4 xuống 7,2 điểm %" trích gap Q1 và gap Q4 → ok
- "TCB nhỉnh hơn ở 3/4 chỉ tiêu" → ok; "4/4 chỉ tiêu" → count_mismatch
- "ROE/ROA của ACB khoảng 10,3 lần, hàm ý đòn bẩy vốn cao hơn" → ok (không phải nhân quả)
- "ROE cao nhờ chi phí thấp" → causal_language; "lý do chính…" → không bị
- "Nên mua ACB" → investment_advice; "mảng bán lẻ" → không bị
- "Tỷ lệ nợ xấu của E1 là một điểm đáng chú ý trong năm 2024" → ok
- "quý 4/2024" không bị hiểu là hạng 4/2024

## 3. Mẫu deterministic, file mới `src/thesis_api/narrative_templates.py`

- `period_vi`, `fmt` (dấu phẩy); `describe_fact(fact)`, ví dụ "ROE của ACB so với trung vị 5 ngân hàng, quý 4/2024"; `display_fact(fact)`, ví dụ "+3,1 điểm %", "2,4 lần", "hạng 2/5", "3/4 chỉ tiêu".
- Câu fallback cho mỗi loại fact và mỗi dạng câu hỏi. **Mọi câu fallback phải qua verifier** (có test).
- `default_report_spec(question_type, tool_results, signals, findings)` là bố cục mặc định, dùng khi model lỗi hoặc spec không hợp lệ:

| dạng | khối mặc định |
|---|---|
| lookup | answer_card: answer (value) + câu bối cảnh (hạng, delta nếu có) |
| company_profile | headline (từ signals) · key_points (mỗi nhóm tín hiệu 1 ý) · figure scatter (nếu có) · figure rank_heatmap · figure small_multiples (nếu có trend) · callout cho mỗi finding confirmed |
| ranking | headline ("{hạng 1} có {label} {cao/thấp} nhất, gấp {ratio} lần trung vị") · figure ranked_bar · key_points (spread, hạng chót) · callout cross_metric_extreme |
| trend | headline (delta đầu → cuối, hạng kỳ cuối) · figure line_trend · key_points (delta, gap đầu/cuối) |
| head_to_head | headline (lead_count) · figure comparison_table · callout decomposition (nếu có) |

## 4. Danh mục khối và kiểm spec, core, file mới `src/thesis_data/report_spec.py`

Thêm vào `APPLICATION_CORE_FILES`. Model Pydantic của các khối (ER-1 §2.5) và `validate_report_spec(spec, datasets, facts) -> (spec_sạch, blocks_dropped)`:

- Bảng tương thích chart ↔ dataset:
  - kpi_strip ← kpi (1–6 ô);
  - ranked_bar ← ranked_list (≥ 3 dòng hợp lệ);
  - line_trend ← series (≥ 2 kỳ);
  - small_multiples ← series_multi (≥ 2 metric, ≥ 2 kỳ);
  - scatter ← paired (≥ 3 điểm hợp lệ ở cả hai trục);
  - rank_heatmap ← peer_table (≥ 3 thực thể, ≥ 2 metric);
  - grouped_bar, comparison_table ← comparison_table hoặc peer_table (2–5 thực thể).

  Chart không tương thích thì **đổi** sang chart đầu tiên trong `allowed_charts` của dataset; không có thì bỏ khối.
- `dataset_id` hay `fact_id` không tồn tại → bỏ khối.
- Giới hạn: ≤ 4 figure, ≤ 5 key point, ≤ 3 section, ≤ 3 callout, ≤ 12 khối. Vượt thì cắt phần cuối.
- `figure_no` đánh lại liên tục theo thứ tự.
- `answer_card` phải có đúng 1 khối `answer`. `note` phải có `headline` và ít nhất 1 khối nội dung.
- Không đạt thì dùng `default_report_spec`, `composition_source = "deterministic_fallback"`.
- Mỗi figure phải có `takeaway`. Takeaway không qua verifier thì vẫn giữ figure nhưng bỏ takeaway, vì hình là dữ liệu chứ không phải nhận định.

## 5. Writer (`src/thesis_api/analysis_writer.py`), viết lại

Xóa `write_specialist`, `synthesize` và mọi hướng dẫn cấm của THES-15 đến THES-22. Thêm:
```python
def write_findings(self, *, role, question, question_type, facts, datasets_summary, candidates, max_sentences=4) -> list[dict]
def compose_report(self, *, question, question_type, sentences, datasets_summary, signals, findings, facts) -> dict  # ReportSpec thô
def rewrite_sentence(self, *, role, question, sentence, issue, facts) -> dict
```
Fact đưa cho model **luôn kèm chuỗi hiển thị** để model chép lại: `{"fact_id","mo_ta","hien_thi"}`. `datasets_summary` = `{dataset_id, title, shape, allowed_charts, n_rows}`, không đưa toàn bộ số.

**Prompt write_findings** (hằng số trong code):
```
Bạn là chuyên viên phân tích {"doanh nghiệp" | "so sánh nhóm ngành"} trong một nhóm phân tích ngân hàng.
Câu hỏi: {question} (dạng: {question_type_label}).
Viết tối đa {max_sentences} câu nhận định tiếng Việt trả lời trực tiếp câu hỏi, chỉ dựa trên các fact được cung cấp. Ưu tiên insight quan trọng nhất trước.
Quy tắc:
1. Mỗi câu liệt kê fact_ids nó dựa vào, chỉ dùng fact_id có trong danh sách.
2. Khi nêu số, chép đúng chuỗi "hien_thi". Không tự tính, không tự làm tròn, không thêm số khác.
3. Chỉ nói tăng/giảm/liên tục/thu hẹp khi có fact thay đổi; chỉ nói cao hơn/thấp hơn/nhỉnh hơn khi có fact chênh lệch; chỉ nói "nhất/hạng" khi có fact hạng.
4. Không giải thích nguyên nhân (vì, do, nhờ, dẫn đến, khiến). Được dùng "hàm ý" cho phép phân rã như ROE/ROA. Không khuyến nghị mua/bán.
5. Câu tối đa 30 từ, giọng báo cáo phân tích, dùng tên chỉ tiêu tiếng Việt, không dùng mã như bank.roe.
6. Nếu có "ung_vien_mau_thuan", được nêu dữ kiện liên quan nhưng không kết luận nguyên nhân.
Trả về JSON: {"sentences":[{"text":"…","fact_ids":["…"]}]}
```

**Prompt compose_report**:
```
Bạn là điều phối viên, dựng báo cáo phân tích kiểu equity research bằng tiếng Việt cho câu hỏi: {question} (dạng: {question_type_label}).
Bạn có: các câu nhận định đã được kiểm chứng (sentence_id), danh sách dataset có thể vẽ (dataset_id, allowed_charts), tín hiệu, phát hiện liên tầng.
Hãy chọn và sắp xếp các khối để trả lời câu hỏi rõ nhất, đưa kết luận lên đầu:
- Câu hỏi tra cứu: dùng kind "answer_card" với khối "answer" và tối đa 1 hình.
- Còn lại: kind "note", bắt đầu bằng "headline" (tối đa 16 từ, mở đầu bằng mã ngân hàng hoặc chủ đề và dấu hai chấm, là một nhận định).
- Mỗi hình chọn chart trong allowed_charts của dataset, có title ngắn và 1 câu takeaway kèm fact_ids.
- Chỉ đưa hình thật sự hỗ trợ một luận điểm; không đưa hình trùng ý.
- Ưu tiên dùng lại sentence_id. Chỉ viết câu mới khi thật cần, và câu mới phải kèm fact_ids.
- Phát hiện liên tầng đã xác nhận nên được đưa vào callout.
Quy tắc số, xu hướng, nguyên nhân, khuyến nghị: giống chuyên viên. Giới hạn: tối đa 4 hình, 5 luận điểm, 3 callout.
Trả về JSON đúng schema ReportSpec, trong đó câu có thể là {"sentence_id":"…"} (dùng lại) hoặc {"text":"…","fact_ids":[…]} (câu mới).
```

**Prompt rewrite_sentence**: đưa câu gốc, issue (mô tả tiếng Việt, fact căn cứ) và fact được phép; yêu cầu viết lại 1 câu theo cùng quy tắc. Trả `{"text","fact_ids"}`.

Sau khi parse JSON, **không** validate bằng regex; mọi kiểm tra đi qua verifier và `validate_report_spec`.

## 6. Critic

Core (chỉ thêm, không phá):
- `CritiqueIssue` thêm `affected_sentence_ids: tuple[str, ...] = ()` và `affected_block_index: int | None = None`.
- `SemanticRoundContext`, `RevisionRequest` thêm `narrative: tuple[NarrativeSentence, ...] = ()`, `report_spec: dict | None = None`, `cross_level_candidates: tuple = ()`. `candidate_hash` băm cả narrative và spec khi có.
- `RevisionResult` thêm `revised_narrative` và `revised_report_spec` (optional). Đường mới trả `revised_claims` = claims cũ.
- `synthesis_summary` của đường mới là `None`, nên luật cấm số cũ trong `validate_synthesis_summary` không chạm tới và **không cần sửa**.

`openai_semantic_critic.py`:
- Xóa hướng dẫn "synthesis strictly qualitative" và phần lọc issue "missing numbers" (THES-22).
- Payload thêm câu hỏi, question_type, narrative (kèm mô tả và hiển thị của fact), report_spec rút gọn (thứ tự khối, title, chart), và ứng viên mâu thuẫn.
- Hướng dẫn (viết tiếng Việt trong prompt):
  1. Số liệu đã được code kiểm; không kiểm lại phép tính.
  2. Kiểm **trả lời đúng câu hỏi**: khối đầu tiên có trả lời trực tiếp không. Không thì issue `incomplete_synthesis` cho orchestrator.
  3. Kiểm **diễn giải**: có nói quá hoặc nói thiếu không; có khái quát thành "toàn ngành" trong khi đây là mẫu N ngân hàng không; có bỏ sót lưu ý quan trọng không. Issue `unsupported_claim` kèm `affected_sentence_ids`.
  4. Kiểm **hình**: hình không hỗ trợ luận điểm nào, hoặc trùng ý → issue `incomplete_synthesis` cho orchestrator, kèm `affected_block_index`, `required_action=REMOVE_CLAIM`.
  5. Mỗi ứng viên mâu thuẫn: `confirmed` kèm 1–2 câu tiếng Việt có fact_ids, hoặc `dismissed` kèm lý do.
  6. Có finding confirmed mà báo cáo không nhắc → issue `cross_level_contradiction` cho orchestrator (`RECONCILE_CROSS_LEVEL`).
  7. Mỗi issue có `description` tiếng Việt, `evidence_refs` = fact_ids, `required_action` ∈ {REVISE_CLAIM, REMOVE_CLAIM, ADD_LIMITATION, RECONCILE_CROSS_LEVEL}.
- Câu của finding confirmed **cũng phải qua verifier**; không qua thì coi như dismissed với lý do "không kiểm chứng được".

## 7. Revision

- Issue có `affected_sentence_ids` → tác giả câu gọi `rewrite_sentence`, rồi verify. Qua thì thay câu và ghi before/after; không qua thì loại câu.
- `REMOVE_CLAIM` trên câu → loại câu. Trên khối → bỏ khối.
- `ADD_LIMITATION` → thêm `description` vào limitations.
- `incomplete_synthesis` / `RECONCILE_CROSS_LEVEL` → orchestrator gọi lại `compose_report` kèm issue và findings, rồi validate và verify lại.
- Hết 2 vòng mà còn issue OPEN trên câu nào → loại câu đó (`unresolved_critique`).
- Khối rỗng thì bỏ. Spec không còn hợp lệ thì dùng `default_report_spec`.

## 8. Dựng response
- `report_version`, `question_type`, `report_spec` (đã validate), `datasets` (chỉ những dataset được khối tham chiếu, cộng dataset của cột tín hiệu), `facts` (chỉ fact được trích hoặc là input của fact được trích), `signals` (company_profile), `cross_level_findings` (confirmed), `narrative_audit`.
- `source_notes`: đánh số theo thứ tự fact xuất hiện lần đầu trong các khối, gộp theo `source_id`. Fact median/rank/gap/ratio trỏ về nguồn của các input.
- `synthesis_summary = None`. `company_insights[0].assessment` = text headline hoặc câu answer (nếu có focus entity).
- `status`:
  - `completed`: critic ACCEPT và `composition_source = "model"`;
  - `accepted_with_limitations`: có câu bị loại vì unresolved, critic lỗi, writer lỗi, hoặc phải dùng fallback.
- **Run chỉ thất bại khi:** plan bị chặn, provider lỗi, hoặc Stage-1 fail. Model lỗi thì dùng fallback kèm limitation "Một phần diễn giải do hệ thống tạo tự động vì mô hình không phản hồi."

## 9. Công tắc arm A/B/C (không hiện ra UI)
`Settings.analysis_arm` (env `ANALYSIS_ARM`), mặc định `hierarchical_with_critique`:
- `single_agent`: một lần `compose_report` với toàn bộ fact của mọi tool (không có findings của chuyên viên), cùng verifier, không critic.
- `hierarchical_no_critique`: bỏ critic và revision.
- `hierarchical_with_critique`: đầy đủ.

Cả 3 dùng chung plan đã đóng băng, tools, fact, verifier và danh mục khối. Ghi `arm` vào trace và run record.

## 10. Dọn code cũ (bắt buộc)

Xóa khỏi `adaptive_runtime.py`: `_WRITER_PERIOD_LITERAL_RE`, `_WRITER_PERIOD_WORD_RE`, `_WRITER_NUMERAL_WORD_RE`, `_WRITER_TEMPORAL_CHANGE_RE`, `_WRITER_CAUSAL_RE`, `_allowed_numbers` (kể cả hack nhóm 3/4/5), `_validate_writer_prose`, `_validate_synthesis_prose`, `_invoke_specialist_writer`, `_write_synthesis`, `_specialist_outputs`, cùng mọi nhánh gọi chúng.

`grep -rn "analysis_writer_unsupported\|analysis_synthesis_fact_reference_rejected\|analysis_writer_period_reference_rejected" src` phải ra 0.

Test cần viết lại (tìm bằng `grep -n "write_specialist\|synthesize\|analysis_writer_\|analysis_synthesis_" tests/*.py`):
- Các fake writer trong `tests/test_api_analyze.py` → đổi sang 3 method mới.
- Các test writer_rounded / writer_unsupported / writer_swapped (~880–940) → thành test verifier loại câu tương ứng.
- Test critic của THES-18/21/22 → theo §6.
- `tests/test_phase3bb_revision_controller.py` → thêm case có `affected_sentence_ids` và có `revised_report_spec`.

**Không xóa test nào mà không có test thay thế cùng ý. Liệt kê cặp cũ → mới trong mô tả PR.**

## 11. Test end-to-end offline `tests/test_api_er_report.py`

Dùng provider giả mô phỏng bảng C, `planner_mode="rules_only"`, fake writer và fake critic có kịch bản:
1. 5 câu B1–B5 của acceptance-questions: mỗi câu ra đúng `kind`, loại khối và loại chart như bảng C; mọi câu trong report qua `verify_sentence` (verify lại toàn bộ).
2. Writer trả câu sai ("Nợ xấu cải thiện…") → bị loại, audit ghi lý do, report vẫn completed.
3. `compose_report` trả chart sai dataset → bị đổi sang chart hợp lệ, `blocks_dropped` hoặc ghi đổi.
4. `compose_report` trả rác → `default_report_spec`, `accepted_with_limitations`.
5. Critic vòng 1 bắt 1 câu → rewrite qua kiểm → vòng 2 chấp nhận; có before/after.
6. Critic bắt 1 hình trùng ý → khối bị bỏ ở spec cuối.
7. Writer raise → fallback, không lỗi.
8. 3 arm chạy được, `arm` đúng.

**Kiểm với model thật (dán vào PR):** Gold v5 + model của staging, `planner_mode="model_with_fallback"`, 5 câu B1–B5. Dán JSON rút gọn: question_type, planner_source, danh sách khối, headline/answer, narrative_audit, thời gian, số lần gọi model.

## Checklist review
- [ ] `narrative_verification.py`, `report_spec.py` là core, pass guardrail check, có đủ test §2.1.
- [ ] Không còn regex cấm từ; grep §10 ra 0.
- [ ] Mỗi dạng câu hỏi ra hình dạng report khác nhau như bảng C (test 11.1).
- [ ] Không đường nào hủy run vì câu văn, spec hay model lỗi.
- [ ] Mọi câu trong report pass verifier.
- [ ] Cross-level findings xuất hiện ở profile ACB và ranking bao phủ.
- [ ] Công tắc arm hoạt động.
- [ ] Test cũ bị xóa đều có test thay thế.
- [ ] Output model thật tiếng Việt, có số, không lộ prompt.
