# PR-4 — INGEST-4: LlamaParse làm bộ đọc trang có nhận biết bảng, chọn trang đúng, đo độ chính xác

Nhánh: `feat/ingest-llamaparse`. Tiêu đề PR: `feat(api): [INGEST-4] LlamaParse table-aware page reader and page selection`. Marker: `DONE-INGEST4`.
Đọc trước: `README.md`, `CONTRACT.md`, D-086, `experiments/ingest/RESULTS.md` (nền Tesseract 41,3%: 31% dòng không tìm thấy vì Tesseract `eng` làm hỏng dấu tiếng Việt, 24% do không chọn đúng trang thuyết minh nợ nhóm 3-5), `src/thesis_data/filing_extract.py`, `src/thesis_api/filing_ocr.py`.

## Sự thật đã thử

Khóa `LLAMA_CLOUD_API_KEY` có trong `.env` gốc (đọc qua biến môi trường, **không in, không ghi ra log, không commit**). API v1 trả 410; dùng **API v2**: `POST https://api.cloud.llamaindex.ai/api/v2/parse/upload` (multipart: `file`, `configuration` là chuỗi JSON `{"tier":"cost_effective","version":"latest"}`) rồi `GET /api/v2/parse/{id}?expand=markdown` (trạng thái ở `job.status`: PENDING, RUNNING, COMPLETED, FAILED, CANCELLED; kết quả `markdown.pages[].markdown`, bảng ở dạng `<table><tr><th>/<td>` có tiêu đề cột như "31.12.2025 Triệu VND"). Thử trên một trang scan thuyết minh 9.3 của ACB (gói `cost_effective`): mất ~12 giây, các giá trị nhóm 3, 4, 5 và tiêu đề cột đều đúng. Cách gọi: cắt các trang cần gửi thành một PDF nhỏ bằng PyMuPDF rồi tải lên một lần (đã dùng được). Thư viện HTTP: `httpx` (đã là phụ thuộc của `openai`), không thêm SDK mới.

## Việc cần làm

1. **`LlamaParseProvider`** (`src/thesis_api/filing_llamaparse.py`) cắm vào giao diện `PageTextProvider` của INGEST-1: nhận danh sách trang, trả văn bản dạng dòng `nhãn | cột1 | cột2` kèm các dòng tiêu đề cột/đơn vị phía trên (tái dùng bộ phân tích dạng ống đã có), `source="llamaparse"`. Cài đặt trong `Settings`: `llama_cloud_api_key: SecretStr | None` (alias `LLAMA_CLOUD_API_KEY`), `llama_max_pages_per_filing: int = 30`, `ocr_provider` (`auto`|`tesseract`|`llamaparse`, mặc định `auto`: có khóa thì LlamaParse cho các trang đã chọn, không thì Tesseract). Không in khóa, không để khóa vào lỗi trả về. Chuyển bảng HTML sang dòng ống bằng `html.parser` của thư viện chuẩn (không thêm phụ thuộc), giữ số ô, bỏ thẻ định dạng (`<b>`, `<u>`).
2. **Chọn trang trước khi gọi dịch vụ trả tiền (giữ credits):** Giai đoạn A: đọc nhanh mọi trang bằng lớp chữ, hoặc nếu không có lớp chữ thì Tesseract độ phân giải thấp (100 dpi) chỉ để lấy từ khóa (nếu Tesseract không có, như trên Render, dùng LlamaParse gói `cost_effective` cho toàn bộ trang với trần `llama_max_pages_per_filing`, và báo `limitations_vi` nếu bị cắt). Cải tiến `classify_pages`: quét **toàn bộ** các trang để tìm thuyết minh phân loại nợ (từ khóa "theo chất lượng nợ", "nợ dưới tiêu chuẩn", "nợ nghi ngờ", "nợ có khả năng mất vốn") thay cho heuristic hai trang hiện tại; chọn bảng cân đối, kết quả kinh doanh và thuyết minh cho vay + dự phòng; thêm trang kế bên (±1) khi bảng tràn. Giai đoạn B: chỉ gửi các trang đã chọn (tối đa `llama_max_pages_per_filing`) lên LlamaParse.
3. **Bộ nhớ đệm và trần chi phí:** lưu kết quả theo `(sha256 tệp, số trang, gói dịch vụ)` trong thư mục của filing để chạy lại không tốn credits; ghi số trang đã gửi vào `meta.json` và hiển thị trong `Filing.limitations_vi` ("Đã gửi N trang tới dịch vụ OCR"). Khóa thiếu/sai/hết hạn mức/lỗi mạng → quay về Tesseract nếu có, nếu không `failed` với `error_code="provider_error"` và thông báo tiếng Việt, không treo, không lộ chi tiết nội bộ. Thời gian chờ có giới hạn (tối đa 90 giây mỗi lô), thử lại tối đa 2 lần.
4. **Sửa đơn vị theo tiêu đề cột:** với văn bản LlamaParse, lấy đơn vị từ ô tiêu đề cột ("Triệu VND"); trang không rõ thì `needs_review` + `unit_unknown`, không mặc định.
5. **Đo độ chính xác** bằng `scripts/ingest_eval.py --provider llamaparse` (thêm tham số) trên 10 báo cáo chuẩn, so sánh trực tiếp với nền Tesseract (41,3%) trong `experiments/ingest/RESULTS.md` (thêm mục LlamaParse, giữ bảng cũ), kèm số trang đã gửi, thời gian và tổng credits ước tính (ghi rõ nếu API không trả credits). Không chỉnh quy tắc theo từng ngân hàng; phân loại nguyên nhân sai bằng dữ liệu như vòng trước. Chạy trong nền, lưu đệm ở `data/processed/ingest_cache/` (bị git bỏ qua), commit từng bước.
6. Test không cần mạng: dùng phản hồi giả của API (httpx MockTransport hoặc stub của `PageTextProvider`) cho các nhánh thành công, lỗi 401/429/5xx, hết thời gian, bảng HTML thật lấy từ trang thử của ACB (dán một đoạn nhỏ vào fixture). Không gọi dịch vụ thật trong CI.

## Ràng buộc

Không mô hình ngôn ngữ nào đọc hay sửa số. Không sửa Gold. Khóa API chỉ đọc từ môi trường/`.env` qua `Settings`; không bao giờ ghi vào log, test, fixture, ảnh chụp hoặc tài liệu. Thêm `LLAMA_CLOUD_API_KEY` vào `render.yaml` như biến `sync: false` (người dùng đã/sẽ nhập giá trị trên Render). Không đổi runtime Render.

## Bàn giao

Khối bàn giao, bảng so sánh Tesseract và LlamaParse (số thật), `gh pr checks` xanh, dòng cuối đúng `DONE-INGEST4`.
