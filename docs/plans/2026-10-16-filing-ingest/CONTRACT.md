# CONTRACT — API nạp báo cáo tài chính PDF (INGEST-1/2/3), chốt 2026-10-16

Nguồn sự thật chung cho backend (INGEST-1, INGEST-2) và giao diện (INGEST-3). Mọi đường nằm sau cổng đăng nhập AUTH-1 (Bearer), không thêm vào danh sách công khai. Giá trị tiền luôn là **chuỗi decimal, đơn vị tỷ đồng** (`"764.791"`), không dùng số thực JSON. Thông báo cho người dùng bằng tiếng Việt trong trường `*_vi`. Backend là bên sở hữu schema; nếu cần đổi, sửa file này trong cùng PR và báo orchestrator.

## Vòng đời

`processing` (đọc và OCR từng trang) → `ready` (có dòng ứng viên và kiểm tra) → người dùng sửa/xác nhận dòng → `confirm` → tạo `upload_id` (đường UPLOAD-1) → hỏi đáp bằng `AnalysisRequest.upload_id` như hiện nay. `failed` là trạng thái cuối khi lỗi.

## Endpoint

| Phương thức, đường | Việc | INGEST |
|---|---|---|
| `POST /api/onboarding/filings` multipart `file` (PDF ≤ 40 MB), `entity_id`, `fiscal_year`, `reporting_scope` (`consolidated`\|`separate`), `display_name?` | tạo filing, chạy nền; `202 {filing_id, status:"processing"}` | 1 |
| `GET /api/onboarding/filings` | danh sách gần đây `[FilingSummary]` | 1 |
| `GET /api/onboarding/filings/{filing_id}` | chi tiết `Filing` (poll mỗi 2 s khi `processing`) | 1 |
| `GET /api/onboarding/filings/{filing_id}/pages/{n}.png` | ảnh trang 120 dpi, n từ 1 | 1 |
| `PUT /api/onboarding/filings/{filing_id}/rows/{row_id}` body `{value_billion_vnd: string\|null, confirmed: boolean}` | người dùng sửa số và/hoặc xác nhận một dòng; trả `{row, validation}` (kiểm tra chạy lại toàn bộ) | 2 |
| `POST /api/onboarding/filings/{filing_id}/confirm` body `{}` | tạo snapshot vận hành từ các dòng đã xác nhận; `200` trả `UploadResponse` hiện có (có `upload_id`, `status:"accepted"`, `metrics[]`, `limitations_vi`); `409` nếu `validation.ready_to_confirm=false`; `422` nếu snapshot bị từ chối (kèm `row_issues`) | 2 |
| `GET /api/onboarding/filing-samples` | bộ mẫu dựng sẵn để trình diễn `[{sample_id, title_vi, entity_id, fiscal_year, page_count, note_vi}]` | 2 |
| `POST /api/onboarding/filing-samples/{sample_id}/open` | tạo filing đã `ready` ngay từ kết quả dựng sẵn (không OCR); trả `Filing` | 2 |

Lỗi dùng khung hiện có `{detail: ...}`; mã trạng thái 400 (đầu vào sai), 401, 404, 409, 413, 422.

## Kiểu dữ liệu

```
FilingSummary { filing_id, entity_id, display_name, fiscal_year, status, created_at, filename }

Filing {
  filing_id: "fl-" + 12 hex
  status: "processing" | "ready" | "failed"
  error_code?: "ocr_unavailable" | "not_a_pdf" | "encrypted" | "no_statements_found" | "provider_error"
  message_vi?: string
  filename, sha256, page_count, entity_id, display_name, fiscal_year, reporting_scope
  ocr_provider: "text_layer" | "tesseract" | "llamaparse" | "mixed" | "sample"
  progress: { pages_done: int, page_count: int }
  statement_pages: { balance_sheet: int[], income_statement: int[], loan_quality_note: int[] }
  unit_detected: "billion_vnd" | "million_vnd" | "thousand_vnd" | "vnd" | null
  rows: Row[]                       // 10 đầu vào x 2 kỳ = tối đa 20, luôn đủ 20 phần tử (thiếu → status "missing")
  validation: Validation
  limitations_vi: string[]
}

Row {
  row_id: string                    // ví dụ "bank.input.total_assets:target"
  metric_id: "bank.input.npl_group_3_balance" | "bank.input.npl_group_4_balance" | "bank.input.npl_group_5_balance"
           | "bank.input.gross_customer_loans" | "bank.input.loan_loss_provisions" | "bank.input.profit_after_tax"
           | "bank.input.total_assets" | "bank.input.parent_attributable_profit" | "bank.input.total_equity"
           | "bank.input.non_controlling_interests"
  label_vi: string                  // tên hiển thị tiếng Việt của chỉ tiêu
  period_role: "target" | "prior"
  period_id: string                 // "2025_Q4" | "2024_Q4"
  value_billion_vnd: string | null
  extracted_value_billion_vnd: string | null   // giá trị máy trích, không đổi khi người dùng sửa
  raw_text: string | null           // chuỗi số gốc trên trang, ví dụ "686.777.352"
  row_label: string | null          // nhãn dòng gốc trên trang
  page: int | null
  source: "text_layer" | "ocr" | "llamaparse" | "user" | null
  status: "candidate" | "needs_review" | "missing"
  edited: boolean
  confirmed: boolean
  issues: Issue[]
  alternatives: { value_billion_vnd: string, raw_text: string, row_label: string, page: int }[]   // tối đa 3
}

Issue { code, severity: "error" | "warning" | "info", message_vi }

Validation {
  status: "pass" | "warn" | "fail"
  ready_to_confirm: boolean         // true khi không còn lỗi chặn và mọi dòng cần dùng đã `confirmed`
  blocking_reasons_vi: string[]
  checks: { code, severity, message_vi, row_ids: string[], expected?: string, actual?: string }[]
}
```

Mã kiểm tra (`code`) cố định để giao diện dịch/nhóm: `missing_required`, `unit_unknown`, `period_mismatch`, `magnitude_range`, `pat_equals_parent_plus_nci`, `npl_sum_le_loans`, `provisions_range`, `assets_gt_loans`, `assets_gt_equity`, `equity_ge_nci`, `yoy_change`, `value_in_page_text`, `column_not_identified`.

Quy tắc: dòng `needs_review` hoặc `missing` phải được người dùng nhập/sửa rồi `confirmed=true` mới được tính là sẵn sàng; dòng `candidate` cũng cần `confirmed=true` (xác nhận là hành động có chủ ý, không tự động). Lỗi `error` chặn `ready_to_confirm`; `warning` thì không chặn nhưng hiển thị.

## Giao diện (INGEST-3) chỉ được dựa vào hợp đồng này

Giao diện gọi qua `apiFetch`; chưa có backend thì dùng dữ liệu giả tuân thủ đúng kiểu ở trên (fixture lấy số thực của ACB 2025 từ `data/onboarding/top10-2025/ACB-2025q4.csv`) và chặn mạng trong Playwright. Khi INGEST-1/2 đã merge, chạy lại với backend thật.
