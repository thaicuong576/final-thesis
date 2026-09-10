# User-facing analysis output contract v2

`ReportView` v1 chỉ là transport view cho metric matrix. Contract này định
nghĩa output mà người dùng thực sự đọc: kết luận, claim, data reference,
evidence, diễn giải và giới hạn.

## Input

- Một run manifest có thể là `success` hoặc `partial`.
- Một Gold snapshot đã freeze.
- Scope issuer, period và metric được khai báo trong manifest.

## Top-level output

```text
contract_version: analysis-report-v2
report_type: bank_comparative_analysis
title: string
run: RunView
scope: ScopeView
executive_summary: ExecutiveSummary
comparisons: list[ComparisonView]
profiles: list[IssuerProfile]
claims: list[AnalysisClaim]
matrix: ReportView.matrix
data_quality: DataQualityView
limitations: list[string]
evidence_policy: EvidencePolicy
```

## AnalysisClaim

Mỗi claim phải có đủ các trường sau:

```text
claim_id: string                  # unique trong report
claim_type: string
priority: high | normal | low
origin: model | deterministic_reference
title: string
claim: string                     # phát biểu có thể kiểm tra
interpretation: string            # claim có ý nghĩa gì trong scope này
limitation: string                # không được bỏ trống
support: evidence_backed | source_locator_only | partially_supported
data_refs: list[DataRef]           # ít nhất một ref
evidence_ids: list[string]
source_ids: list[string]
```

`DataRef` phải trỏ đến đúng một ô trong `matrix`:

```text
ticker: string
period: string
metric_id: string
value: number | null
display_value: string
status: valid | missing | ...
observation_id: string | null
source_id: string | null
source_locator: string | null
evidence_ids: list[string]
```

## Support levels

- `evidence_backed`: mọi ref là valid và có evidence snippet page/quote phù
  hợp với locator.
- `source_locator_only`: mọi ref là valid, có source locator, nhưng chưa có
  quote snippet đủ để gọi là evidence-backed.
- `partially_supported`: có ref missing/unaccepted hoặc thiếu source/locator.

Không được tự gắn `evidence_backed` chỉ vì source hoặc period có một snippet
bất kỳ. Snippet phải được lọc theo metric locator khi tài liệu có trang.

## Invariants

1. Số liệu trong `matrix` và `data_refs` lấy từ Gold snapshot, không lấy từ
   prose của model.
2. Claim chỉ được tham chiếu đến ô nằm trong cùng report scope.
3. Claim không có `interpretation` hoặc `limitation` là invalid.
4. Missing/conflict giữ nguyên trạng thái và lý do; không zero-fill, nội suy
   hoặc chọn variant không được duyệt.
5. Claim không được tự suy diễn quan hệ nhân quả hoặc biến thành khuyến nghị
   đầu tư nếu scope không yêu cầu và không có bằng chứng riêng.
6. `model_findings` được giữ riêng trong `data_quality`; chúng không tự động
   trở thành claim đã được chứng minh.
7. Report phải nói rõ `partial` khi Gold snapshot có ô missing/unaccepted.
8. UI chỉ đọc JSON contract này; không truy cập SQLite, không tính lại metric.

## Benchmark standard

Single-agent và mỗi arm multi-agent phải xuất cùng contract v2. So sánh theo:

- correctness của claim so với Gold/data references;
- evidence support và citation correctness;
- chất lượng interpretation và limitation;
- coverage/missing-data discipline;
- cost, token, latency, timeout và failure rate.

Một report đẹp nhưng claim không truy vết được không được tính là output tốt.
Một report nhiều claim nhưng thiếu interpretation/limitation cũng không đạt
contract.

## Current implementation

- Builder: `src/thesis_data/analysis_report.py`.
- Validator: `src/thesis_data/analysis_report_validation.py`.
- Renderer: `scripts/render_analysis_report_v2.py`.
- Sample: `reports/application-analysis-v2/analysis-report.md`.
