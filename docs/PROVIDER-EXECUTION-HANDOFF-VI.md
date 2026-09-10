# Handoff chạy provider thật — pilot Gold

Ngày cập nhật: 2026-09-06

## Trạng thái

Pilot Gold đã đủ điều kiện về dữ liệu và đã chạy xong provider-backed pilot
theo lựa chọn explicit của người dùng: exact model `gpt-5.6-luna`, Responses
API function calling, closed-world Gold tools, và ba arm công bằng.

Kết quả execution: **39/39 jobs**, 13 jobs mỗi arm, `failure_count=0`, secret
scan `PASS`. Đây là bằng chứng pipeline chạy được, không phải kết luận
multi-agent superiority; phần so sánh chất lượng vẫn chờ blind rubric review.

## Input đã cố định

- Snapshot: `gold-bank-2025-pilot-v1-adjudicated-v2`
- Gold database: `data/processed/gold-bank-2025-pilot-v1-adjudicated-v2.sqlite`
- Question set: `pilot-2024-bank-core-qa-v1` (13 câu bank-focused)
- Gold-bound plan: `experiments/runs/baseline-plan-core-gold-v1.json` (39 jobs)
- Source policy dự kiến: `primary-only-v1`, chỉ dùng accepted Gold observations
  và evidence đã được liên kết.
- Missing policy: `value=null` + lý do; không đoán, không zero-fill, không
  silent impute; missing không vào mẫu số numeric accuracy/average nhưng phải
  được báo cáo và chấm riêng.

## Cấu hình đã chốt và artifact execution

1. `provider_id=openai`, `adapter_id=openai-responses-tool-calling-v1`,
   `model_id=gpt-5.6-luna`.
2. Local key được đọc từ file `.env` ngoài repository qua biến
   `OPENAI_API_KEY`; giá trị không được ghi vào artifact/log.
3. Cấu hình execution:

   - `environment=provider_backed`;
   - `network_access=enabled`;
   - `api_key_env_var` trỏ tới tên biến môi trường local;
   - `model_id` và `source_policy_id` khớp từng `ExperimentRunConfig`;
   - timeout, output-token limit và telemetry policy.

4. Real transport đã được inject trong `src/thesis_data/openai_transport.py`;
   tool loop bị giới hạn, role-scoped, read-only và fail-closed.
5. Smoke artifact:
   `experiments/outputs/provider/smoke-gpt-5.6-luna-20260906T082632Z/smoke.json`.
6. Full artifact:
   `experiments/outputs/provider/full-gpt-5.6-luna-20260906T085022Z/`.
7. Report:
   `reports/provider-gpt-5.6-luna-20260906T085022Z.md` và `.json`.

Không commit API key, giá trị endpoint riêng tư, request body chứa secret hoặc
provider exception text vào repository, SQLite, manifest hay thesis report.

## Trình tự đã thực thi

1. Validate provider config và Gold-bound plan trước khi dispatch.
2. Chạy smoke test trước.
3. Kiểm tra manifest có snapshot/question/model/prompt/source-policy binding,
   telemetry, timing, cost và tool trace.
4. Chạy đủ 39 jobs cho cả ba arm; các job retry được ghi riêng nhưng vẫn giữ
   cùng job identity và không có failure còn lại.
5. Bước tiếp theo là review output blind và chấm cùng rubric: factual correctness, calculation
   correctness, evidence/citation completeness, missing/conflict handling,
   cross-level consistency, latency, model calls và cost.

Ba arm phải dùng cùng Gold snapshot, facts/evidence, question set, source
policy, model/configuration và output contract. Nếu một arm lỗi transport hoặc
schema, ghi failure riêng; không thay bằng offline fixture và không loại job
âm thầm.

## Lệnh tái lập / resume

```powershell
$env:PYTHONPATH='src'
python scripts/run_openai_baseline.py --mode full `
  --config experiments/config/openai-gpt-5.6-luna.json `
  --output-dir experiments/outputs/provider/full-gpt-5.6-luna-<UTC>
```

Resume a partial directory with `--resume-dir`; the runner skips completed
job IDs and writes only missing-job retry manifests.

## Không được suy diễn từ checkpoint hiện tại

Gold promotion và execution pass không chứng minh provider response quality hay
multi-agent superiority. Report hiện có operational latency/cost và mechanical
numeric claim checks. Kết luận chất lượng cuối cùng phải dựa trên blind rubric,
missing/conflict scoring và review completeness; không dùng tool-call count làm
proxy cho chất lượng.
