# Review packet cho Checker B — pilot 48 cells

## Mục tiêu

Checker B phải lặp lại việc kiểm tra nguồn và định nghĩa **độc lập** với
Checker A. Reviewer không kiểm tra vendor value đúng hay sai; reviewer kiểm tra
official evidence có đủ để hỗ trợ metric theo metric dictionary hay không.

## Phạm vi

- Issuer: ACB, TCB, VPB.
- Period: `2024_Q1`, `2024_Q2`, `2024_Q3`, `2024_Q4`.
- Metrics: `bank.npl_g35`, `bank.llr_coverage`, `bank.roa`, `bank.roe`.
- Tổng số target cells: 48.

## Điều kiện độc lập bắt buộc

Reviewer B không được mở, đọc, tìm kiếm hoặc xem trước:

- `data/reconciliation/gold-bank-2025-pilot-v1/private-review-ai/checker-a.csv`;
- private Checker-A copy hoặc throughput report;
- merged ledger hoặc gold-label candidate;
- vendor values, vendor locators hoặc normalized vendor snapshot làm điểm bắt đầu.

Reviewer chỉ được dùng:

- file review B riêng tư;
- `data/reconciliation/gold-bank-2025-pilot-v1/blind-source-navigation-index-v3.csv`;
- official raw files và official source manifests;
- `docs/METRIC-DICTIONARY.md`;
- `data/reconciliation/gold-bank-2025-pilot-v1/REVIEWER-GUIDE.md`.

Nếu hai checker dùng cùng một người hoặc cùng một model run thì không được gọi
là independent two-checker review.

## Cách thực hiện

Tạo một bản làm việc riêng, không làm việc trực tiếp trên canonical template:

```powershell
$env:PYTHONPATH='src'
python scripts/build_review_ledger.py `
  data/reconciliation/gold-bank-2025-pilot-v1/register.csv `
  path/to/private-checker-b.csv --reviewer-copy
```

Reviewer tự mở official source, xác định page/table/section, mapping metric,
unit và period basis, rồi điền vào bản riêng. Khi hoàn tất, đặt bản copy đã điền
ở nơi orchestrator có thể đọc được; không gửi kèm Checker-A result.

## Quy tắc quyết định

| Decision | Khi nào dùng | Cần ghi |
|---|---|---|
| `accepted` | Evidence chính thức và mapping đủ rõ | value, unit, period basis, source, locator, definition match |
| `missing` | Không có source được phép hoặc không đủ comparable evidence | value để trống/null và lý do cụ thể |
| `conflicting` | Nguồn/định nghĩa đáng tin mâu thuẫn | các locator và mô tả conflict; không tự chọn một bên |
| `invalid` | File/page/identity/evidence route không hợp lệ | lý do lỗi chất lượng nguồn |

Không được đoán số, zero-fill, impute, sửa dấu bằng absolute value hoặc dùng
vendor value để lấp một ô missing. Nếu PDF scan-only không thể kiểm tra ổn định,
ghi `missing` hoặc `invalid` với lý do thay vì suy diễn từ text extraction.

## Trường bắt buộc trên mỗi dòng

Mỗi 48 dòng phải có `checker_id`, `decision`, `checked_at` và `notes`. Với
`accepted`, phải có `value`, `unit`, `period_basis`, `source_id`,
`source_locator`, `definition_match` và consolidation basis phù hợp. Với
`missing/conflicting/invalid`, notes phải nêu lý do cụ thể.

`checker_id` đề nghị: `checker-B-independent`. Không dùng lại checker identity
của Checker A.

## Kiểm tra hoàn tất

```powershell
python scripts/report_review_progress.py `
  path/to/private-checker-b.csv
```

Điều kiện chuyển lại cho orchestrator:

- đúng 48 target rows;
- 48/48 có decision;
- 48/48 có checker ID và timestamp;
- không có vendor-context columns/values;
- mọi accepted row có source và locator;
- mọi missing/conflicting/invalid row có reason;
- không merge hoặc promote Gold ở phía reviewer.

Orchestrator chỉ merge A/B sau khi B hoàn tất, audit disagreement, adjudicate
conflict và chạy Gold gate. Một bản B hoàn chỉnh vẫn chưa tự động là Gold.
