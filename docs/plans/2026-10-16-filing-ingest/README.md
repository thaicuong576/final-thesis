# INGEST — Đường ống nạp báo cáo tài chính PDF (2026-10-16)

Yêu cầu của người dùng: sản phẩm phải là một webapp mà người dùng đưa vào **báo cáo tài chính (PDF) của một ngân hàng**, hệ thống OCR, trích xuất, sàng lọc, kiểm tra, rồi nhập vào cơ sở dữ liệu vận hành để trả lời câu hỏi. Hiện chỉ có luồng CSV (UPLOAD-1, D-077). Quyết định D-086 cho phép đường ống này với điều kiện mọi số liệu trích ra là **ứng viên** cho tới khi qua kiểm tra tự động và được người dùng xác nhận.

## Sự thật đo được (quyết định thiết kế)

- Cả 10 báo cáo kiểm toán FY2025 (`data/raw/official/bank-2025-top10-v1/`) và 2 mẫu ngân hàng mới (`data/raw/official/sample-new-bank/OCB_FY2025.pdf`, `VIB_FY2025.pdf`) đều là **bản scan, không có lớp chữ** (0–2 trang có chữ). Vì vậy OCR là bắt buộc, không phải phương án dự phòng.
- E5: OCR đọc đúng chữ số (652/700 giá trị xuất hiện trong văn bản trang OCR), nhưng quy tắc khớp nhãn dòng ngây thơ chỉ đúng 52%. Phần khó là cấu trúc bảng và ngữ nghĩa kế toán, nên đường ống phải có tầng kiểm tra đẳng thức kế toán và bước người dùng xác nhận.
- Dữ liệu chuẩn để đo: `data/onboarding/top10-2025/<MÃ>-2025q4.csv` (10 chỉ tiêu đầu vào, kỳ 2025_Q4 và kỳ trước 2024_Q4, kèm trang PDF và dòng nguồn) ứng với PDF cùng tên trong `data/raw/official/bank-2025-top10-v1/`.
- Máy phát triển có Tesseract ở `C:\Program Files\Tesseract-OCR\tesseract.exe` (chỉ có `eng.traineddata`, đủ cho chữ số và nhãn đã bỏ dấu). Render (Python native) không có Tesseract: việc triển khai OCR lên production (Docker) là cổng riêng của người dùng, không thuộc các PR này.

## Phạm vi v1

- Báo cáo tài chính **năm** (kiểm toán, hợp nhất hoặc riêng lẻ do người dùng khai): kỳ mục tiêu `<năm>_Q4`, kỳ trước `<năm-1>_Q4` lấy từ cột so sánh. Báo cáo giữa niên độ (quý) và chuyển đổi đa kỳ nằm ngoài v1, ghi rõ trong giao diện.
- 10 đầu vào của UPLOAD-1: nợ nhóm 3, 4, 5, dư nợ cho vay khách hàng gộp, dự phòng rủi ro cho vay, lợi nhuận sau thuế, tổng tài sản, lợi nhuận thuộc cổ đông công ty mẹ, tổng vốn chủ sở hữu, lợi ích cổ đông không kiểm soát. Từ đó hệ thống tính lại NPL, bao phủ nợ xấu, ROA, ROE bằng đường UPLOAD-1 sẵn có.
- Đơn vị chuẩn: tỷ đồng (billion_vnd). Đọc đơn vị từ tiêu đề trang ("Đơn vị: triệu đồng" / "VND"), quy đổi bằng phép chia có kiểm tra.

## Chuỗi PR (tuần tự)

1. **INGEST-1** (`PR-1-ingest-extract.md`): nhận PDF, lưu, OCR từng trang (lớp chữ nếu có, không thì Tesseract), phân loại trang báo cáo, trích 10 đầu vào × 2 kỳ ra dòng ứng viên có số trang. Kèm script đo độ chính xác trên 10 báo cáo chuẩn. Backend, contract OpenAPI.
2. **INGEST-2**: tầng kiểm tra (đẳng thức kế toán, thang đo, nhất quán hai kỳ), API sửa dòng và xác nhận, chuyển dòng đã xác nhận qua đường UPLOAD-1 để tạo snapshot vận hành (`upload_id`).
3. **INGEST-3**: giao diện từng bước (Tải PDF → Đang đọc → Kiểm tra → Xác nhận → Hỏi đáp) có xem trang gốc cạnh dòng trích xuất, sửa số, bộ mẫu dựng sẵn để trình diễn.
4. Cổng người dùng: triển khai OCR trên Render (Docker) và chụp lại ảnh luận văn; cập nhật chương 3-4-5-6.

Ràng buộc chung: không sửa Gold v5; tầng lõi `src/thesis_data` không import sqlite/openai/subprocess trực tiếp ngoài lớp adapter đã có; không cho mô hình ngôn ngữ tạo số liệu; mọi dòng ứng viên có `page`, `source` (`text_layer` hoặc `ocr`) và không được dùng để phân tích trước khi `confirm`.
