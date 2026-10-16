# PR-2 — INGEST-2: kiểm tra kế toán, sửa dòng, xác nhận và nhập vào snapshot vận hành

Nhánh: `feat/ingest-validate`. Tiêu đề PR: `feat(api): [INGEST-2] filing validation, row review and confirmation into operational snapshot`. Marker: `DONE-INGEST2`.
Đọc trước: `README.md`, `CONTRACT.md` (nguồn sự thật cho kiểu dữ liệu), D-086, `src/thesis_data/filing_extract.py` và `src/thesis_api/filing_ocr.py` (INGEST-1 đã merge), `src/thesis_data/user_upload.py` (đường UPLOAD-1) và mã `POST /api/onboarding/uploads` trong `src/thesis_api/main.py`.

## Việc cần làm

1. **Tầng kiểm tra thuần** `src/thesis_data/filing_validate.py` (không I/O): nhận 20 dòng (`Row`) và trả `Validation` đúng `CONTRACT.md`. Các kiểm tra (mã cố định):
   - `missing_required`: thiếu giá trị ở dòng bắt buộc (cả 10 đầu vào × 2 kỳ là bắt buộc, trừ `non_controlling_interests` được phép bằng 0 khi người dùng nhập 0 rõ ràng và xác nhận; thiếu là lỗi).
   - `pat_equals_parent_plus_nci`: lợi nhuận sau thuế = lợi nhuận cổ đông công ty mẹ + lợi ích cổ đông không kiểm soát, dung sai tuyệt đối 0,01 tỷ hoặc 0,01% của PAT (lấy ngưỡng lớn hơn); lệch là `error`.
   - `npl_sum_le_loans`: nợ nhóm 3+4+5 ≤ dư nợ cho vay gộp, và tỷ lệ 3+4+5 / dư nợ nằm trong [0, 0,25]: vượt là `error`, nằm trong [0,10, 0,25] là `warning`.
   - `provisions_range`: 0 ≤ dự phòng ≤ dư nợ cho vay gộp.
   - `assets_gt_loans`, `assets_gt_equity`, `equity_ge_nci`: các bất đẳng thức cơ bản (`error`).
   - `magnitude_range`: tổng tài sản trong [100; 20.000.000] tỷ đồng (bắt lỗi sai đơn vị ×1000/×1e6), các giá trị còn lại không âm trừ lợi nhuận được phép âm (lỗ).
   - `yoy_change`: thay đổi kỳ này so với kỳ trước ngoài [-60%, +150%] cho mọi chỉ tiêu số dư là `warning`.
   - `value_in_page_text`: mọi giá trị chưa chỉnh sửa phải xuất hiện (khớp theo chữ số) trong văn bản trang đã đọc; giá trị do người dùng nhập tay được miễn nhưng gắn `source="user"`.
   - `period_mismatch`, `unit_unknown`, `column_not_identified`: chuyển tiếp từ `issues` của INGEST-1.
   - Quy tắc tổng hợp: `status = fail` nếu có `error`; `warn` nếu chỉ có `warning`; `ready_to_confirm = true` khi không có `error` và cả 20 dòng đều `confirmed`.
2. **Lưu trạng thái chỉnh sửa** trong `meta.json` của filing: `PUT /api/onboarding/filings/{filing_id}/rows/{row_id}` nhận `{value_billion_vnd, confirmed}`, kiểm tra định dạng decimal (chuỗi, tối đa 6 chữ số thập phân, không NaN/âm vô lý), đặt `edited=true` và `source="user"` khi giá trị khác `extracted_value_billion_vnd`, giữ `extracted_*` nguyên, chạy lại kiểm tra toàn bộ và trả `{row, validation}`. Sửa một giá trị làm `confirmed=false` của dòng đó cho tới khi xác nhận lại. Filing không ở `ready` → 409.
3. **`POST /api/onboarding/filings/{filing_id}/confirm`:** chỉ chạy khi `ready_to_confirm`; dựng CSV theo định dạng UPLOAD-1 từ 20 dòng (đủ cột, `source_locator` ghi trang PDF và nhãn dòng, `source_url` và hash đúng ràng buộc hiện có của `user_upload.py`: đọc mã để biết điều kiện, không nới lỏng bộ kiểm tra), rồi gọi lại đúng hàm đã dùng cho upload CSV (`validate_and_parse_upload_csv` và `materialize_user_upload_snapshot`) để tính lại NPL, bao phủ nợ xấu, ROA, ROE bằng công thức có phiên bản. Trả `UploadResponse` hiện có kèm `upload_id`; lưu `upload_id` vào filing để gọi lại không tạo bản trùng (idempotent: lần gọi thứ hai trả cùng kết quả). Nếu snapshot bị từ chối → 422 với `row_issues` dịch về dòng nguồn.
4. Báo cáo dùng dữ liệu này phải mang nhãn giới hạn UPLOAD-1 và nói thêm số liệu được trích từ tệp PDF do người dùng tải lên và xác nhận (một câu trong `limitations_vi`).
5. Cập nhật `contracts/openapi.json` đúng `CONTRACT.md`; nếu cần đổi contract thì sửa tài liệu trong cùng PR và nêu rõ ở bàn giao.

## Kiểm thử

- Test thuần cho từng mã kiểm tra: một ca đạt, một ca lỗi, một ca sát ngưỡng; ca tổng hợp `ready_to_confirm`.
- Test API end-to-end bằng filing tổng hợp (không OCR): sửa dòng → kiểm tra cập nhật; xác nhận khi chưa sẵn sàng → 409; xác nhận đủ → `upload_id`, truy vấn `GET /api/onboarding/uploads/{id}` thấy snapshot; gọi `POST /api/analyze` với `upload_id` đó cho câu hỏi tra cứu NPL của ngân hàng mới và nhận báo cáo có nhãn giới hạn; gọi confirm lần hai idempotent; hash Gold không đổi.
- Test dùng số thực của một ngân hàng (ví dụ ACB 2025 từ `data/onboarding/top10-2025/ACB-2025q4.csv`) làm trường hợp "đạt", rồi cố ý đổi một số để thấy `pat_equals_parent_plus_nci` hoặc `magnitude_range` bắt được.
- `PYTHONPATH=src python -m unittest discover -s tests -q`, `python scripts/check_architecture_guardrails.py`, `python scripts/check_openapi_contract.py`.

## Ngoài phạm vi

Không giao diện, không OCR mới, không bộ mẫu dựng sẵn. Không tạo release, tag hay bình luận thử.

## Bàn giao

Khối bàn giao thường lệ, `gh pr checks` xanh, dòng cuối đúng `DONE-INGEST2`.
