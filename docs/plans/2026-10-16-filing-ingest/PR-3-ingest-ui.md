# PR-3 — INGEST-3: giao diện từng bước nạp báo cáo tài chính PDF

Nhánh: `feat/ingest-ui`. Tiêu đề PR: `feat(ui): [INGEST-3] step-by-step filing ingestion wizard`. Marker: `DONE-INGEST3`.
Đọc trước: `README.md` và `CONTRACT.md` cùng thư mục (hợp đồng API đã chốt), `.agent/rules/design/README.md`, `frontend/src/features/onboarding/BankUploadSection.tsx` (luồng CSV hiện có), AGENTS.md mục AUTH-1 (`apiFetch`).

## Mục tiêu

Người dùng (giảng viên) mở trang **Dữ liệu**, chọn "Thêm ngân hàng từ báo cáo tài chính PDF", và đi qua một trình hướng dẫn nhìn thấy được từng giai đoạn của đường ống: không phải hộp đen. Luồng CSV hiện có giữ nguyên (thêm lựa chọn, không thay thế).

## Các bước (một cột, đọc từ trên xuống, bước đã xong thu gọn thành một dòng tóm tắt có thể mở lại)

1. **Tải lên:** chọn/kéo thả PDF; mã ngân hàng 3 chữ, năm tài chính, phạm vi (hợp nhất / riêng lẻ, bắt buộc chọn, không mặc định); dòng nói rõ "v1: báo cáo tài chính năm đã kiểm toán". Nút "Dùng bộ mẫu" mở danh sách `filing-samples` để trình diễn không cần PDF. Hiển thị lỗi 400/413 bằng tiếng Việt.
2. **Đang đọc báo cáo:** thanh tiến độ trang (`progress`), poll 2 s, nhãn "Đang đọc trang 37/100", nêu nguồn đọc (`ocr_provider`: chữ có sẵn, Tesseract, LlamaParse). Trạng thái `failed`: thông báo `message_vi` và cách xử lý theo `error_code` (ví dụ `ocr_unavailable`: "Máy chủ chưa có công cụ OCR", `no_statements_found`).
3. **Các trang tìm thấy:** ba chip (Bảng cân đối kế toán, Kết quả kinh doanh, Thuyết minh chất lượng nợ) kèm số trang; bấm chip mở ảnh trang đó (`pages/{n}.png`) trong khung xem.
4. **Bảng số liệu trích xuất:** 10 chỉ tiêu × 2 kỳ (kỳ này, kỳ trước) dạng bảng gọn, mỗi dòng có: tên chỉ tiêu tiếng Việt, hai ô giá trị (tỷ đồng, định dạng vi-VN), trang nguồn (bấm để xem ảnh trang cạnh bảng), nhãn nguồn (đọc bằng OCR/chữ sẵn có/người dùng nhập), biểu tượng trạng thái (cần xem lại, thiếu, đã xác nhận), và với dòng có `alternatives` một menu chọn giá trị khác. Ô giá trị sửa tại chỗ (gửi `PUT .../rows/{row_id}`); sửa xong, dòng ghi nhãn "đã sửa" và giữ `extracted_value` để so sánh. Xác nhận từng dòng bằng hộp tick, và nút "Xác nhận tất cả dòng đã khớp kiểm tra" chỉ áp cho dòng không có lỗi.
5. **Kiểm tra:** khối kết quả `validation.checks` nhóm theo mức (lỗi chặn, cảnh báo), mỗi mục có mô tả tiếng Việt, bấm vào làm nổi các dòng liên quan (`row_ids`). Hiện rõ lý do khi chưa thể xác nhận (`blocking_reasons_vi`).
6. **Nhập vào hệ thống:** nút "Nhập vào cơ sở dữ liệu" bật khi `ready_to_confirm`; bấm gọi `POST .../confirm`; hiển thị kết quả 4 chỉ tiêu tính lại (dùng lại thành phần bảng kết quả của luồng CSV nếu có thể) và nhãn giới hạn; sau đó nút "Hỏi về {MÃ}" mở màn hỏi với `upload_id` đã chọn như luồng CSV.

Khung xem ảnh trang: ở màn rộng đặt cạnh bảng (bảng trái, ảnh phải, dính khi cuộn); ở điện thoại ảnh mở thành ngăn kéo/toàn màn. Ảnh trang tải chậm có khung chờ, lỗi ảnh có nút thử lại.

## Yêu cầu chất lượng

- Tuân thủ `.agent/rules/design/`; một cột chính; không hộp lồng hộp; không chữ giữ chỗ giả; nhãn tiếng Việt, dùng chữ "agent" nếu cần nhắc, không "tác tử"; không lộ mã kỹ thuật (`bank.input.*`, snake_case) trong chữ hiển thị (có test quét như FLOW-1: `/[a-z]+_[a-z_]+/` không xuất hiện trong văn bản người dùng thấy).
- Trạng thái đầy đủ: chưa chọn tệp, đang tải lên, đang đọc, thất bại, sẵn sàng, đang xác nhận, đã nhập; lỗi mạng và hết phiên (401 đã xử lý ở `apiFetch`).
- Truy cập: nhãn cho điều khiển, thanh tiến độ `role="progressbar"`, điều hướng bàn phím trong bảng, vùng thay đổi `aria-live="polite"`.
- Điện thoại 390 px: không cuộn ngang; bảng chuyển thành danh sách thẻ gọn mỗi chỉ tiêu.

## Dữ liệu giả và bằng chứng

Chưa có backend: viết fixture tuân đúng `CONTRACT.md` (`frontend/src/test/fixtures/filingFixtures.ts`) với số thực ACB 2025 từ `data/onboarding/top10-2025/ACB-2025q4.csv`, gồm các tình huống: đọc xong sạch; một dòng `needs_review` có `alternatives`; một dòng `missing`; lỗi kiểm tra `pat_equals_parent_plus_nci`; `processing` tiến độ; `failed` `ocr_unavailable`. Test Vitest cho từng bước và chuyển bước, sửa ô và chặn nút nhập khi `ready_to_confirm=false`. Ảnh trang giả dùng ảnh PNG nhỏ tạo bằng canvas hoặc tệp trong fixtures.
Chụp ảnh màn hình bằng Playwright (msedge) chặn mạng bằng `page.route` ở 1440 và 390 px cho: bước tải lên, đang đọc, bảng trích xuất có dòng cần xem lại, khối kiểm tra có lỗi, sẵn sàng nhập, kết quả sau nhập. **Tự xem từng ảnh** và sửa chỗ xấu trước khi báo cáo (khoảng trống lớn, thẻ lẻ, chữ cắt, chồng chéo). Lưu ảnh ở `C:/Users/ASUS/AppData/Local/Temp/orch/ingest3/shots/`.

Chạy trong `frontend/`: `npm run lint`, `npm test`, `npm run build`. Không sửa `src/` (backend), không đổi contract; nếu thấy contract thiếu gì, ghi vào bàn giao thay vì tự thêm trường.

## Bàn giao

Khối bàn giao (Base SHA, Branch, Commit SHA, PR, file đổi, test kèm số thật, ảnh kèm một dòng nhận xét thật, hạn chế), `gh pr checks` xanh, dòng cuối đúng `DONE-INGEST3`.
