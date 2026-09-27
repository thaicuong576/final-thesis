# Prompt Contract v1 — arm register (pre-freeze)

**Ngày đăng ký:** 2026-09-27
**Mã phiên bản:** `prompt-contract-v1`
**Trạng thái:** `pre-freeze`

Tài liệu này là sổ đăng ký cho phiên bản prompt được các tài liệu hợp đồng và bộ câu hỏi ứng viên tham chiếu. Đây là kiểm soát tái lập cho thiết kế thực nghiệm; không phải bằng chứng provider thật đã sẵn sàng, snapshot đã được chấp nhận, hoặc điểm A/B/C cuối cùng đã được tạo. Không gọi một run là kết quả đánh giá cuối cùng chỉ vì `prompt_version` có mặt trong task spec.

## 1. Identity và fingerprint

Mọi `ExperimentRunConfig` phải ghi `prompt_version: prompt-contract-v1`, arm/prompt-set ID, question-set version/hash, rubric version, model/provider configuration, source policy, accepted snapshot identity/hash, seed, repetitions, budget và retry policy khi protocol được freeze. Mỗi model call phải ghi `RunCallTrace.prompt_sha256` cho bytes prompt đã render thực tế.

`prompt_sha256` là fingerprint của bytes sau khi template, system instructions, role instructions và context layout được render theo quy ước của run. Fingerprint không thay thế kiểm tra chất lượng ngữ nghĩa, provenance hoặc Stage-1. Nếu template/context thay đổi, phải tạo version hoặc register entry mới.

## 2. Invariants chung cho cả ba arm

Trong một so sánh hợp lệ, các arm dùng cùng accepted facts, snapshot, question set, rubric, output contract và source/evidence policy. Mỗi request giữ nguyên query-derived plan, entity/metric/period scope và missingness contract.

Prompt chung yêu cầu agent:

1. chỉ dùng observation/source evidence đã accepted và locator có thể resolve;
2. phân biệt `missing` với zero, không bịa dữ liệu, kỳ, issuer, denominator hoặc scope;
3. không tự tính số liệu từ prose khi derived observation phải do code tính;
4. giữ provenance theo ID/cấu trúc output contract, không nối claim với evidence bằng array order hoặc encoded claim ID;
5. nêu excluded member/cell và lý do khi plan không đủ coverage;
6. trả output có cấu trúc để Stage-1 kiểm tra trước khi diễn giải;
7. không đưa secret, hidden chain-of-thought hoặc thông tin ngoài evidence vào report.

Arm A không được bỏ qua output-contract validation. Khác biệt giữa arms là topology và vai trò được gọi, không phải quyền dùng dữ liệu khác nhau.

## 3. Arm register

| Arm | Prompt-set ID | Đường đi đăng ký | Critique/revision |
|---|---|---|---|
| A — `single_agent` | `prompt-contract-v1.single-agent` | Một agent nhận request plan và accepted evidence context rồi tạo report theo output contract; không tách specialist/orchestrator thành các call độc lập. | Không semantic critic, không targeted revision; Stage-1/contract validation vẫn bắt buộc. |
| B — `hierarchical_no_critique` | `prompt-contract-v1.hierarchical-no-critique` | Planner cố định request-derived plan; specialist phù hợp capability (Company/Sector/Macro) viết phần; orchestrator tổng hợp phần và lineage. | Không semantic critic và không revision round; Stage-1 chạy trên candidate. |
| C — `hierarchical_bounded_critique` | `prompt-contract-v1.hierarchical-bounded-critique` | Giống B đến candidate đầu tiên. Sau Stage-1, semantic critic tạo issue/action có cấu trúc; writer bị ảnh hưởng chạy lại; orchestrator tổng hợp. | Tối đa hai targeted revision rounds; mỗi candidate sau revision phải qua Stage-1 lại. Re-fetch hoặc đổi verdict đơn thuần không phải revision. |

Arm B và C giữ cùng plan, accepted facts, specialist scope và output contract trước khi C thêm critic/revision. Arm A chỉ khác ở single output path; không được dùng để đổi snapshot hoặc question set.

## 4. Role prompt register

Register mô tả các vai trò logic; prompt bytes triển khai thực tế phải được render và hash trong run manifest trước freeze.

| Vai trò | Trách nhiệm bắt buộc | Arm |
|---|---|---|
| `planner` | Đóng băng plan: mode, entity/member set, metrics, ordered periods, final anchor, expected cells; từ chối query ngoài budget/capability. | B, C; A dùng cùng plan contract trong context. |
| `company_writer` | Viết claim Company từ context và gắn observation/source-trail IDs. | B, C khi plan có Company. |
| `sector_writer` | Viết benchmark/peer claims theo member set và denominator eligible; nêu excluded members. | B, C khi plan có Sector/Peer. |
| `macro_writer` | Chỉ viết Macro khi provider có capability và observation accepted; nếu không fail closed. | B, C khi plan có Macro. |
| `orchestrator_synthesis` | Tổng hợp outputs, bảo toàn scope, lineage, missingness và expected-cell completeness. | B, C. |
| `semantic_critic` | Kiểm candidate theo query, evidence, scope, completeness, output contract; phát issue/action có cấu trúc. | Chỉ C. |
| `revision_writer` | Sửa đúng issue/action bằng accepted context; không biến re-fetch hoặc đổi verdict thành revision. | Chỉ C, tối đa 2 rounds. |

Đây là contract identifiers, không khẳng định mọi role đã nối với live model trong checkout hiện tại. Readiness phải được chứng minh bằng runtime probe và provider configuration hợp lệ.

## 5. Context và thứ tự call tối thiểu

Trước model call, run phải lưu `question_set_hash`, accepted `snapshot_id`/hash, source policy, rubric, model/provider identity, arm, prompt version và query-derived plan.

- A: plan + accepted context → single-agent output → Stage-1.
- B: plan → eligible specialists → orchestrator synthesis → Stage-1.
- C: plan → specialists → initial synthesis → Stage-1 → critic/action → targeted writer(s) → synthesis → Stage-1, tối đa hai rounds.

SSE/run-history events phải phản ánh chuyển trạng thái thực tế. `REPORT_READY` chỉ dành cho accepted runtime result; gate fail phải kết thúc ở trạng thái blocked/error tương ứng.

## 6. Freeze checklist

Trước khi gọi kết quả là A/B/C scoring evidence, phải lưu và kiểm tra:

- bytes/template mỗi prompt-set và quy tắc render;
- `prompt_version`, arm ID và `prompt_sha256` của từng call;
- output contract/schema và Stage-1 version;
- model/provider name và version, không ghi secret value;
- immutable question-set hash, rubric version và ordered task list;
- accepted snapshot ID/hash, evidence manifest và source policy;
- repetitions, randomization seed, retry/timeout policy, token/cost budget;
- critic/revision configuration và giới hạn hai rounds cho C;
- readiness/provider probe, log lỗi và quyết định freeze được review trong run manifest.

Thiếu một mục là blocker của protocol freeze và scoring, không phải lý do suy đoán default. Bộ task ứng viên hiện vẫn `final_protocol_freeze_ready: false` và có runtime blockers; tài liệu này không thay đổi trạng thái đó.

## 7. Boundary và references

Prompt định hướng retrieval, explanation, critique và synthesis. Code/provider chịu trách nhiệm arithmetic, acceptance, provenance resolution và snapshot boundary. Mock/offline fixture chỉ chứng minh plumbing, không phải live validation.

Tài liệu liên quan:

- [`docs/DATA-CONTRACT.md`](DATA-CONTRACT.md) — `ExperimentRunConfig`, `AgentCallRequest`, `RunCallTrace`;
- [`docs/ARCHITECTURE.md`](ARCHITECTURE.md) — prompt version, call trace, agent boundaries;
- [`docs/EVALUATION-PROTOCOL-V1-DRAFT.md`](EVALUATION-PROTOCOL-V1-DRAFT.md) — pre-freeze, arms, scoring gates;
- [`experiments/README.md`](../experiments/README.md) — arm definitions và run requirements;
- [`data/evaluation/p4-task-specs-v1.json`](../data/evaluation/p4-task-specs-v1.json) — candidate controls, không phải final freeze;
- [`docs/DECISIONS.md`](DECISIONS.md) — provenance/scope decisions.

Việc tài liệu này có mặt chỉ sửa một missing control artifact. Tại ngày đăng ký, live accepted snapshot/readiness, live model/provider execution, teacher walkthrough đạt pass và final A/B/C scoring vẫn là các cổng độc lập chưa được chứng minh.
