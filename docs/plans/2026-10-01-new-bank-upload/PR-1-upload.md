# UPLOAD-1 — Người dùng tải CSV số liệu một ngân hàng mới rồi hỏi về ngân hàng đó

Mục tiêu: giảng viên nhận một file CSV số liệu BCTC của một ngân hàng chưa có trong hệ thống (ví dụ CTG), tải lên webapp, xem kết quả kiểm tra, rồi đặt câu hỏi và nhận báo cáo dựa trên dữ liệu vừa tải cùng dữ liệu Gold v5 của hệ thống. Hạn: xong trong ngày 2026-10-01.

## Nguyên tắc bắt buộc (không được vi phạm)
- Không ghi, không sửa snapshot Gold v5 (`SQLITE_DB_PATH`). Dữ liệu tải lên nằm ở kho riêng, tách khỏi Gold và tách khỏi `ANALYSIS_RUNS_DB_PATH`.
- Code tính chỉ tiêu: NPL (nhóm 3–5 / dư nợ), bao phủ nợ xấu (dự phòng / nợ nhóm 3–5), ROA, ROE được **tính lại** từ các dòng số liệu gốc bằng công thức có phiên bản đang dùng trong `src/thesis_data/bank_onboarding.py` (`_validate_packet_calculations`) / `operational_onboarding.py`. Nếu CSV có ghi giá trị chỉ tiêu do ngân hàng công bố, so với giá trị tính lại theo dung sai hiện có; lệch thì từ chối dòng đó kèm lý do.
- Mỗi dòng phải có `source_locator` (tối thiểu trang) và `source_url`; thiếu thì từ chối. Không suy đoán phạm vi hợp nhất/riêng lẻ: phải khai `reporting_scope`.
- Ngân hàng tải lên **không** được đưa vào trung vị / xếp hạng nhóm Gold. So sánh với nhóm = so với trung vị 5 ngân hàng Gold. Chế độ mặc định (không tải lên) phải hoạt động y hệt hiện tại (R2 "CTG" vẫn bị từ chối khi không có dữ liệu tải lên).
- Mọi báo cáo dùng dữ liệu tải lên phải có nhãn giới hạn: "Số liệu {BANK} do người dùng cung cấp; hệ thống đã kiểm tra cấu trúc, nguồn và tính lại chỉ tiêu, chưa được duyệt độc lập như bộ Gold."
- Tầng lõi `src/thesis_data` không import sqlite/openai và không hard-code mã ngân hàng (chạy `scripts/check_architecture_guardrails.py`).
- Cập nhật `contracts/openapi.json` cho endpoint mới và chạy `scripts/check_openapi_contract.py`.

## Định dạng CSV
Giống `data/onboarding/ctg-2024-audited-2024q4-v1-reconciliation.csv` nhưng các cột review là tuỳ chọn:
`observation_id` (tuỳ chọn, tự sinh nếu trống), `entity_id` (bắt buộc, mã CK 3 chữ, mọi dòng giống nhau; hoặc lấy từ tham số form), `metric_id`, `value`, `unit`, `period_id`, `period_basis`, `reporting_scope`, `source_locator`, `source_url`, `source_sha256` (tuỳ chọn).
- Dòng bắt buộc: các `bank.input.*` cần cho 4 chỉ tiêu tại kỳ mục tiêu và kỳ trước (để tính bình quân ROA/ROE), đúng như bộ CTG (18 dòng input). Dòng `bank.npl_g35|bank.llr_coverage|bank.roa|bank.roe` là tuỳ chọn (giá trị công bố để đối chiếu).
- Giới hạn: tối đa 200 dòng, 256 KB, UTF-8 (chấp nhận BOM).
- Người tải lên được ghi làm reviewer (`reviewer_id="uploader"`, `review_decision="user_supplied"`).

## Backend (`src/thesis_api`, logic thuần ở `src/thesis_data`)
1. `POST /api/onboarding/uploads` (multipart: `file`, tuỳ chọn `entity_id`, `display_name`): parse → chuyển thành packet → kiểm tra (tái dùng `bank_onboarding` / `onboarding_validation` / `operational_onboarding`, không viết lại công thức) → trả `{upload_id, entity_id, status: accepted|rejected, period_id, metrics: [{metric_id, computed_value, reported_value, status}], row_issues: [{row, field, message_vi}], limitations_vi}`. Nếu accepted: dựng snapshot vận hành vào thư mục riêng (`USER_UPLOADS_DIR`, mặc định `/tmp/user_uploads`), lưu kèm manifest.
2. `GET /api/onboarding/uploads` và `GET /api/onboarding/uploads/{upload_id}`: danh sách / chi tiết.
3. `GET /api/onboarding/template.csv`: file mẫu (header + các metric_id bắt buộc, cột trống) ; `GET /api/onboarding/samples/{name}.csv`: `ctg-2024q4` (chính là CSV CTG đã đối chiếu, chuyển sang định dạng upload) và `ctg-2024q4-loi` (bản cố ý lỗi: 1 dòng thiếu trang nguồn, 1 dòng sai đơn vị, 1 giá trị công bố lệch).
4. `AnalysisRequest` thêm trường tuỳ chọn `upload_id`. Khi có: provider = tổ hợp chỉ-đọc (Gold v5 + snapshot tải lên) ở tầng ứng dụng; danh mục thực thể nhận thêm mã ngân hàng tải lên; nhóm so sánh/trung vị vẫn là 5 ngân hàng Gold. Hỗ trợ dạng câu hỏi: lookup, company_profile, head_to_head (ngân hàng tải lên với một ngân hàng Gold). Dạng khác với ngân hàng tải lên → từ chối rõ ràng bằng tiếng Việt. Kỳ khác kỳ tải lên → thiếu số liệu rõ ràng, không đoán.
5. Stage-1/nguồn: số liệu tải lên là quan sát được chấp nhận ở mức "user_supplied_validated", có locator + url, nên ghi chú nguồn trong báo cáo hiện "BANK · <tiêu đề nguồn> · tr. N".
6. Test: CSV CTG mẫu → accepted, 4 chỉ tiêu khớp packet CTG hiện có; CSV lỗi → rejected với đúng 3 lỗi; phân tích "Tỷ lệ nợ xấu của CTG quý 4/2024" với upload_id → báo cáo accepted có nhãn giới hạn; không có upload_id → vẫn unsupported_entity; trung vị nhóm không đổi khi có upload; Gold file hash không đổi sau toàn bộ luồng.

## Frontend (`frontend/`, tuân thủ `.agent/rules/design/`)
- Trang "Dữ liệu": thêm mục "Thêm ngân hàng mới từ tệp CSV": nút tải file mẫu, hai file ví dụ (CTG hợp lệ, CTG có lỗi), vùng chọn/kéo thả tệp, nút "Kiểm tra và tải lên".
- Hiển thị kết quả: bảng 4 chỉ tiêu (giá trị tính lại, giá trị công bố, trạng thái), danh sách lỗi theo dòng bằng tiếng Việt, nhãn giới hạn. Nếu accepted: nút "Hỏi về {BANK}" mở màn hỏi với ngân hàng tải lên được chọn (gửi `upload_id`) và gợi ý 3 câu hỏi mẫu.
- Màn hỏi: hiện chip "Đang dùng thêm dữ liệu tải lên: CTG (Q4/2024)" có nút bỏ chọn. Báo cáo hiển thị nhãn giới hạn ở đầu.
- Test component cho luồng tải lên (mock API).

## Kiểm tra trước khi mở PR
`PYTHONPATH=src python -m unittest discover -s tests`, `python scripts/check_architecture_guardrails.py`, `python scripts/check_openapi_contract.py`, trong `frontend/`: `npm run lint`, `npm test`, `npm run build`. Ghi quyết định vào `docs/DECISIONS.md` (D-076: dữ liệu người dùng tải lên là tầng vận hành tách khỏi Gold, không vào trung vị nhóm) và cập nhật `AGENTS.md` mục API contract một đoạn ngắn.
