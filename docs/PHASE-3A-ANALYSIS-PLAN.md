# Phase 3A — AnalysisPlan và semantic-evaluation contracts

## Mục đích và giới hạn

Phase 3A đóng băng cấu trúc mà một câu hỏi yêu cầu **trước khi** worker sinh
answer. `AnalysisPlan` không được tái dựng từ prose sau khi có answer. Nó là
một contract bổ sung cho `AtomicClaim`, không thay thế traceability hiện có:

```text
question
  → AnalysisPlan requirement
  → AtomicClaim
  → StructuredAssertion
  → data/evidence provenance
  → rendered report statement
```

Phase này chỉ triển khai Pydantic contracts và deterministic preflight. Chưa
có LLM critic, scoring prompt, provider/model execution, semantic entailment,
revision controller, threshold calibration, UI, hay thay đổi Macro Gold.

Implementation:

- `src/thesis_data/analysis_plan.py`
- `src/thesis_data/semantic_evaluation.py`
- `tests/test_phase3a_contracts.py`

## AnalysisPlan schema

`AnalysisPlan` version hiện tại là `analysis-plan-v2` và gồm:

| Field | Ý nghĩa |
| --- | --- |
| `plan_version` | Version của contract |
| `dataset_id` | Identity của dataset mà request đã chọn |
| `dataset_snapshot_id` | Identity bất biến của snapshot được dùng cho run |
| `query_id` | Identity của câu hỏi |
| `normalized_question` | Câu hỏi đã chuẩn hóa trước generation |
| `scope` | Entities, periods, company metrics, macro indicators và peer universe |
| `requirements[]` | Các đơn vị phải được answer đáp ứng |
| `applicable_links[]` | Chỉ các quan hệ cross-level thực sự áp dụng cho câu hỏi |
| `requested_outputs[]` | Các dạng output được yêu cầu |
| `causal_claim_policy` | Trần suy luận của toàn câu hỏi |

`AnalysisScope` có `entities`, `periods`, `company_metric_ids`,
`macro_indicator_ids` và `comparison_universe`. Requirement và link phải nằm
trong scope; duplicate IDs và out-of-scope references fail closed.

## Requirement types và missing-data policy

Enum requirement được giữ nhỏ và bám vào thesis:

- `factual_observation`
- `comparison`
- `trend`
- `cross_level_relation`
- `limitation_missingness_disclosure`

Mỗi requirement có stable `requirement_id`, mô tả, agent cần tham gia, scope
entity/period/metric, `inference_ceiling`, `fulfillment_policy`,
`missing_data_policy` và `critical`.

Ba fulfillment policy được phép:

- `VALID_VALUE_REQUIRED`: cần một giá trị/claim hợp lệ; missing không thể được
  dùng để hoàn thành requirement.
- `VALUE_OR_ACCEPTED_MISSINGNESS`: chấp nhận một giá trị hợp lệ **hoặc** một
  missingness disclosure có typed reference tới một canonical observation mà
  dataset provider xác nhận là `MISSING` với allowed missing reason. Pending,
  fallback, unaccepted hoặc silently omitted data không thỏa policy này.
- `DISCLOSURE_REQUIRED`: dành riêng cho requirement về limitation/missingness
  disclosure; kiểm tra deterministic chỉ yêu cầu disclosure claim có limitation,
  không biến limitation thành yêu cầu numeric value.

`missing_data_policy` làm rõ cơ chế tương ứng:

- `reject_missing`
- `accepted_missingness`
- `not_applicable` cho requirement disclosure không yêu cầu một observation.

`InferenceCeiling.CAUSAL` bị từ chối khi plan có
`causal_claim_policy=association_only` hoặc `no_causal_inference`.

## Applicable cross-level links

`ApplicableLink` có stable `link_id`, `link_type`, source/target level,
source/target entities, source/target periods, metric IDs và description.

Các link type hiện có:

- `macro_to_company`
- `sector_to_company`
- `company_to_peer_benchmark`

Cross-level score tương lai chỉ được đánh giá trên `link_id` đã khai báo trong
plan. Macro → company hoặc sector → company không được suy ra là bắt buộc cho
mọi câu hỏi; nếu link không nằm trong plan thì divergence giữa hai level không
tự động là contradiction.

## Frozen TCB macro question

`build_tcb_macro_analysis_plan(dataset_ref)` tạo plan deterministic cho
`TCB_macro_to_bank_q4` với:

- entity: `VN`, `TCB`;
- period: `2024_Q4`;
- macro indicators: `macro.policy_rate`, `macro.credit_growth`;
- company metrics: `bank.roa`, `bank.roe`;
- causal policy: `association_only`;
- applicable link: `L1`, macro → company, `VN` → `TCB`.

Stable requirements:

| ID | Nội dung | Policy |
| --- | --- | --- |
| `R1` | Policy-rate fact | `VALID_VALUE_REQUIRED` |
| `R2` | Credit-growth value hoặc accepted missingness disclosure | `VALUE_OR_ACCEPTED_MISSINGNESS` |
| `R3` | TCB ROA | `VALID_VALUE_REQUIRED` |
| `R4` | TCB ROE | `VALID_VALUE_REQUIRED` |
| `R5` | Quan hệ macro context ↔ bank performance | `VALUE_OR_ACCEPTED_MISSINGNESS`, association-only |
| `R6` | Không suy luận causal từ một kỳ | `DISCLOSURE_REQUIRED`, limitation-only |
| `R7` | Disclosure về unavailable observations/limitations | `VALUE_OR_ACCEPTED_MISSINGNESS` |

## Semantic evaluation contracts

`SemanticDimensionResult` có:

- `dimension`
- `score` finite trong `[0,1]`
- `rationale`
- `supporting_claim_ids[]`
- `affected_requirement_ids[]`
- `issue_ids[]`

Sáu dimension frozen là:

| Dimension | Weight |
| --- | ---: |
| Groundedness | 0.30 |
| Cross-level Integration | 0.20 |
| Answer Coverage | 0.20 |
| Logical Soundness | 0.15 |
| Uncertainty & Limitations | 0.10 |
| Analytical Usefulness | 0.05 |

Các weight này là research parameters versioned của project, không phải
universal standards. `StructuredCriticResult` là
`structured-critic-result-v1`, chứa đủ sáu dimension đúng một lần,
`critique_issues[]` dùng lại `CritiqueIssue` hiện có, các nhóm fulfilled /
partially fulfilled / unfulfilled requirement IDs, applicable-link results và
`evaluator_version`.

## Deterministic scaffold

`validate_structured_critic_result()` chỉ kiểm tra những thứ không cần model:

- mọi requirement ID trong result tồn tại trong plan và mỗi requirement được
  phân loại đúng một trạng thái;
- mọi claim ID trỏ tới một `AtomicClaim` canonical;
- mọi link ID trỏ tới `ApplicableLink` đã khai báo và mỗi link khai báo nhận
  đúng một `ApplicableLinkResult`;
- issue references trỏ tới `CritiqueIssue` hiện có;
- duplicate/unknown IDs fail closed;
- accepted missingness chỉ được coi là hợp lệ khi claim có structured
  missingness reference và dataset resolver trả về canonical observation đúng
  entity/period/metric với trạng thái `MISSING`, giá trị null và allowed reason;
  Stage-1 pass vẫn là điều kiện riêng, không thay thế provider resolution;
- numeric claim không thể làm requirement missing-aware hợp lệ nếu numeric
  gate của Stage 1 đã fail.

Các check này không kết luận evidence có semantic entailment hay reasoning có
tốt không. Answer Coverage được tính trong tương lai đối với plan đã đóng
băng, không reconstruct từ answer. Stage 1 vẫn deterministic; Groundedness,
Logical Soundness và các semantic judgments vẫn deferred sang Phase 3B.
