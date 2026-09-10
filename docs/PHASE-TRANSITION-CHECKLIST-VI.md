# Checklist chuyển phase — guarded build → baseline

Ngày kiểm tra: 2026-09-05

## Quyết định hiện tại

Project đang ở trạng thái:

```text
GUARDED_BUILD_ALLOWED
BASELINE_EXECUTION_BLOCKED
```

Nghĩa là pilot empirical Gold đã hoàn tất và đủ điều kiện dữ liệu để chuẩn bị
baseline: snapshot có `44/48` ô numeric hợp lệ và `4/48` ô missing có lý do;
mỗi metric đạt `11/12`. Tuy nhiên chưa được chạy provider-backed hoặc đưa ra kết
luận so sánh agent. Cutoff/scope cuối cùng vẫn cần advisor xác nhận, đồng thời
provider/model config và real transport chưa được cung cấp; đây là các cổng
governance/vận hành, không phải thiếu khung kiến trúc.

## Những gì đã đủ để bắt đầu build

- Scope pilot 3 ngân hàng × 4 quý × 4 metric đã được ghi thành artifact.
- Full question set có 14 câu và core question set có 13 câu bank-focused.
- Core plan có 39 jobs; full draft plan có 42 jobs.
- Cả hai plan đều preflight được và còn dùng `PENDING_GOLD_SNAPSHOT`.
- Query/evidence, metric contract, runtime dispatch, anomaly trigger, run
  manifest và batch runner đã có test.
- Batch runner chỉ nhận adapter inject và reject snapshot placeholder.
- Provider-backed batch runner đã yêu cầu provider config tường minh; config
  không chứa secret và mismatch model/source-policy bị fail trước dispatch.
- Structured provider response boundary đã có test độc lập; transport thật,
  secret lookup và network call vẫn nằm sau Gold gate.
- Prompt renderer deterministic đã được nối vào adapter boundary; transport
  nhận prompt canonical thay vì tự dựng lại prompt theo provider.
- Offline fixture transport deterministic hiện cũng đi qua
  `StructuredProviderAdapter`; đây chỉ là plumbing evidence, không phải provider
  evidence hay comparative result.
- Chapters 1–4 đã có working draft và artifact references.

## Ba track làm song song

### Track A — Data foundation (critical path)

1. Checker B hoàn tất độc lập 3 ACB ROE addendum cells từ blind copy riêng.
2. Merge addendum vào v4 ledger, giữ nguyên original 48-cell adjudication.
3. Export lại `GoldLabel` JSONL theo v4 snapshot.
4. Promote versioned Gold snapshot; kết quả là `44/48` valid và `4/48`
   reasoned-missing.
5. Chạy lại readiness và baseline input gate; Gold audit và baseline input gate
   đều pass.
6. Gold-bound core plan 39 jobs đã được tạo và validate, nhưng chưa execute.

Nếu 48-cell pilot không đạt vì ROA hoặc review burden, advisor có thể phê duyệt
fallback 36-cell. Khi đó phải tạo question set/plan/snapshot mới cho đúng ba
metric; không sửa 48-cell artifact tại chỗ.

### Track B — Build

Được làm ngay:

- adapter interface và provider configuration schema;
- secret-free provider config loader và provider-backed pre-dispatch guard;
- deterministic query/evidence tests;
- prompt contract `prompt-contract-v1`, prompt drafts và payload validation;
- offline replay;
- batch runner và manifest/reporting;
- evaluation aggregation.

Chưa được làm:

- provider call trên candidate/staging data;
- dùng fallback macro như official evidence;
- chạy comparative baseline trên dữ liệu chưa Gold;
- publish superiority hoặc “live database” claim.

### Track C — Writing

Được viết ngay:

- Chương 1: problem, scope, research question, contribution, non-goals;
- Chương 2: metric definitions, source-grounded QA, decomposition và critique;
- Chương 3: sampling, source ladder, reconciliation, Gold gate, evaluation arms;
- Chương 4: data plane, evidence plane, agent plane, contracts và provenance.

Chưa viết như kết quả:

- điểm factual/evidence của từng arm;
- claim multi-agent cải thiện;
- latency/cost thực tế của provider;
- độ đầy đủ/live của database.

## Gói khởi động phase tiếp theo

Để chuyển từ data-foundation sang build/evaluation mà không mở scope quá sớm,
thực hiện theo hai mốc sau.

### Mốc A — có thể bắt đầu ngay trong guarded build

Đầu ra tối thiểu cần giữ trong workspace:

1. `docs/SPEC.md`, `docs/DATA-CONTRACT.md`,
   `docs/PROMPT-CONTRACT-VI.md`, question set và scoring rubric cùng chỉ tới
   một research contract;
2. deterministic query/evidence layer tạo cùng một prepared context cho cả
   ba arm;
3. offline fixture v9 chạy được ba arm qua persisted plan, full-batch preflight
   và one-job boundary, ghi prompt version, question-set hash,
   observation/evidence IDs, stable job IDs và call budget; manifest mới của
   builder hiện tại còn ghi prompt fingerprint. Các manifest v2 đã lưu trong
   v9 là artifact legacy và có thể thiếu field additive này; fixture transport
   hiện chạy qua `StructuredProviderAdapter` nhưng vẫn không gọi provider;
4. baseline plan core 39 jobs và full 42-job draft được kiểm tra cấu trúc nhưng
   vẫn giữ `PENDING_GOLD_SNAPSHOT`;
5. Chương 1–4 chỉ mô tả thiết kế, giao thức, scope và giới hạn; chưa chèn số
   liệu hoặc kết luận hiệu năng từ staging.

Mốc A được coi là hoàn thành khi test suite, compile check, question-set
validator, offline fixture và state/event audit đều pass. Nó không mở quyền
gọi provider.

**Trạng thái Mốc A hiện tại:** `PASSED` ngày 2026-09-05. Bằng chứng gồm 195
unittest cases, `compileall`, core question-set/39-job plan validation,
`experiments/runs/offline-fixture-v9/`, regression fingerprint test cho
manifest mới và checkpoint
`guarded-build-moc-a-passed` trong `.agents/project-state/events.jsonl`.
Baseline provider-backed vẫn giữ trạng thái `BLOCKED` cho đến khi scope được
advisor xác nhận và Gold gate chuyển sang `READY_FOR_BASELINE`.

### Mốc B — chỉ mở sau khi Gold gate xanh

Theo đúng thứ tự:

1. nhận snapshot Gold versioned và freeze question-set/configuration/prompt
   hashes;
2. chạy một core job single-agent qua batch boundary;
3. kiểm tra manifest, provenance, contract validity và telemetry;
4. chạy cùng job cho hierarchical-no-critique và bounded-critique;
5. nếu cả ba arm hợp lệ, mới mở toàn bộ 39 core jobs;
6. freeze output, blind-score, aggregate quality/cost/latency và sau đó mới
   viết Chương 5–6 theo kết quả quan sát được.

Nếu bất kỳ bước nào fail, giữ output ở trạng thái failed/not-scorable và sửa
đúng lớp gây lỗi. Không dùng staging data, fallback macro, hoặc thêm agent để
che một lỗi source/definition.

### Quy tắc quyết định sau pilot

- 48 ô và các metric được xác nhận comparable: giữ 48 cho baseline đầu tiên;
- 48 ô đạt nhưng review/OCR quá chậm: giữ 48, không tự động mở lên 80;
- một metric không đạt comparability: dùng fallback đã ghi trong manifest,
  tạo question set/plan tương ứng mới, và ghi limitation;
- chỉ mở 80/200 sau khi pilot có Gold, review throughput và conflict rate đo
  được, đồng thời có xác nhận phạm vi của advisor.

## Entry gate cho baseline thật

Chỉ thay `PENDING_GOLD_SNAPSHOT` bằng snapshot thật khi tất cả điều kiện sau
đúng:

- scope và cutoff đã được duyệt;
- mọi target cell có `accepted` hoặc `missing` với reason;
- coverage lõi đạt ngưỡng hoặc gap có exclusion reason;
- có ít nhất 40 label được kiểm tra độc lập;
- có ít nhất 2 checker ID;
- mỗi target cell có `value_check`;
- conflict nghiêm trọng đã được resolve hoặc exclude;
- source, locator, unit, period basis và formula provenance đầy đủ;
- `readiness-decision.md` là `READY_FOR_BASELINE`;
- core plan preflight pass sau khi hash/snapshot được cập nhật.

## Lệnh kiểm tra trước khi chạy

```powershell
$env:PYTHONPATH='src'
python -m unittest discover -s tests -q
python scripts/validate_question_set.py experiments/question-set-core-v1.json
python scripts/validate_baseline_plan.py `
  experiments/runs/baseline-plan-core-v1.json `
  experiments/question-set-core-v1.json
python scripts/preflight_baseline_plan_inputs.py `
  path/to/gold-snapshot.sqlite `
  experiments/runs/baseline-plan-core-v1.json `
  experiments/question-set-core-v1.json `
  --ticker ACB --ticker TCB --ticker VPB `
  --period 2024_Q1 --period 2024_Q2 --period 2024_Q3 --period 2024_Q4 `
  --metric bank.npl_g35 --metric bank.llr_coverage `
  --metric bank.roa --metric bank.roe `
  --run-id-prefix preflight-v1 `
  --rubric-version rubric-v1 --model-id selected-model `
  --source-policy-id primary-only-v1
python scripts/report_review_progress.py `
  data/reconciliation/gold-bank-2025-pilot-v1/private-review-ai/checker-a.csv `
  data/reconciliation/gold-bank-2025-pilot-v1/review-checker-b-blind-template-v2.csv
```

Kết quả hiện tại phải được đọc là: test/build contract pass, Gold snapshot và
Gold-bound plan preflight đều pass; provider-backed pilot đã chạy xong qua real
transport với exact `gpt-5.6-luna`, đủ 39/39 manifests và zero remaining
failures. Comparative claims vẫn giữ HOLD cho đến khi blind rubric scoring,
missing/conflict scoring và evidence review hoàn tất. Không sửa Gold snapshot
hoặc dùng tool-call count làm quality proxy.

## Evaluation policy

Core aggregate dùng `question-set-core-v1.json` và 39 jobs. Macro-to-bank là
extension 3 jobs, chỉ báo cáo riêng khi `macro.policy_rate` và
`macro.credit_growth` có quan sát chính thức, đúng kỳ, được kiểm tra độc lập và
được promote cùng Gold policy. Nếu không đạt, ghi `not scorable` thay vì thay
bằng DBnomics/IMF fallback.

## Exit condition của phase

Phase chuyển sang baseline khi Gold gate xanh và một core job chạy được qua
`baseline_batch_runner` với adapter đã được chọn, tạo manifest đầy đủ provenance.
Sau đó mới chạy toàn bộ 39 jobs, freeze outputs, chấm blind và viết Chương 5–6
dựa trên kết quả thật.
