# PR-1 — INGEST-1: nhận PDF báo cáo tài chính, OCR, phân loại trang, trích dòng ứng viên

Nhánh: `feat/ingest-extract`. Tiêu đề PR: `feat(api): [INGEST-1] filing PDF intake, OCR and candidate row extraction`.
Marker hoàn thành: `DONE-INGEST1`. Đọc trước: `docs/plans/2026-10-16-filing-ingest/README.md`, D-082, D-086 trong `docs/DECISIONS.md`, `docs/ARCHITECTURAL-GUARDRAILS.md`, và UPLOAD-1 (`docs/plans/2026-10-01-new-bank-upload/`, `src/thesis_data/user_upload.py`).

## Mục tiêu

Một người dùng tải lên PDF báo cáo tài chính **năm** của một ngân hàng; backend đọc từng trang (lớp chữ hoặc OCR), xác định trang bảng cân đối kế toán, báo cáo kết quả kinh doanh và thuyết minh phân loại nợ, rồi trả về các **dòng ứng viên** cho 10 đầu vào × 2 kỳ, mỗi dòng có số trang, nhãn dòng gốc, văn bản gốc và đơn vị đã quy đổi. Chưa phân tích, chưa kiểm tra đẳng thức (INGEST-2), chưa giao diện (INGEST-3).

## Thiết kế

Logic thuần ở `src/thesis_data/filing_extract.py` (không I/O, không subprocess): nhận danh sách văn bản trang, trả về phân loại trang và dòng ứng viên. Phần I/O (đọc PDF bằng PyMuPDF, dựng ảnh trang, gọi Tesseract) ở một adapter trong `src/thesis_api/` (ví dụ `filing_ocr.py`), có giao diện `PageTextProvider` để test thay bằng văn bản giả.

1. **Đọc trang:** nếu trang có lớp chữ (≥ 200 ký tự) dùng lớp chữ, `source="text_layer"`; nếu không, dựng ảnh ở 200 dpi bằng PyMuPDF và chạy Tesseract `-l eng --psm 6` (đường dẫn từ `shutil.which("tesseract")`, rồi `C:\Program Files\Tesseract-OCR\tesseract.exe`, hoặc biến `TESSERACT_CMD`), `source="ocr"`. Nếu không tìm thấy Tesseract và có trang scan: trạng thái `failed` với `error_code="ocr_unavailable"` và thông báo tiếng Việt, không giả vờ đọc được. Có thể đọc song song vài trang (thread pool nhỏ, tối đa 4) và lưu kết quả từng trang vào thư mục của filing để chạy lại không phải OCR lần nữa.
2. **Phân loại trang** bằng từ khóa tiếng Việt đã bỏ dấu (tái dùng cách `fold` của `scripts/e5_naive_extract.py`, nhưng chuyển vào module lõi, không import từ `scripts/`): bảng cân đối kế toán ("bao cao tinh hinh tai chinh", "can doi ke toan", tổng tài sản, tổng nợ phải trả, vốn chủ sở hữu), kết quả kinh doanh ("ket qua hoat dong kinh doanh", "loi nhuan sau thue", "co dong cua ngan hang / cong ty me", "loi ich cua co dong thieu so"), thuyết minh chất lượng nợ ("phan loai no", "theo chat luong no", nhóm 3, 4, 5, "du phong rui ro"). Mỗi trang có thể thuộc nhiều loại; trả danh sách số trang theo loại, kèm điểm số. Bỏ qua trang mục lục (nhiều số trang, ít số tiền).
3. **Trích dòng ứng viên:** với mỗi đầu vào có danh sách nhãn đồng nghĩa (đặt thành bảng cấu hình dữ liệu trong module, ví dụ "Cho vay khách hàng", "Dự phòng rủi ro cho vay khách hàng", "Lợi nhuận sau thuế", "Cổ đông của Ngân hàng / công ty mẹ", "Lợi ích của cổ đông thiểu số / không kiểm soát", "Tổng tài sản", "Tổng vốn chủ sở hữu", "Nợ dưới tiêu chuẩn / nghi ngờ / có khả năng mất vốn"), tìm dòng trong các trang đúng loại, lấy các số trên dòng đó (chỉ số có dạng nhóm ba chữ số, dấu ngoặc là âm, loại các mã số thuyết minh), chọn cột kỳ này và cột kỳ trước **theo tiêu đề cột của trang** (ví dụ "31/12/2025" và "31/12/2024", hoặc "Năm nay" và "Năm trước"); nếu không đọc được tiêu đề cột thì để `status="needs_review"` thay vì đoán theo vị trí. Nợ nhóm 3/4/5 và dư nợ lấy theo cột "Tổng cộng"/dư nợ gộp, không lấy cột của loại cho vay riêng. Khi nhiều dòng cùng khớp nhãn (tổng phụ), chọn dòng khớp nhãn chặt nhất trong đúng trang loại và ghi các lựa chọn khác vào `alternatives` (tối đa 3).
4. **Đơn vị:** đọc "Đơn vị: triệu đồng / nghìn đồng / đồng / tỷ đồng" ở đầu trang hoặc tiêu đề bảng; quy đổi sang tỷ đồng bằng `Decimal`; không đọc được đơn vị thì dòng `needs_review` và nêu rõ. Báo cáo ngân hàng Việt thường tính bằng triệu đồng.
5. **Kỳ:** `period_id` mục tiêu lấy từ tham số `fiscal_year` do người dùng khai (bắt buộc, ví dụ 2025 → `2025_Q4`, kỳ trước `2024_Q4`); nếu văn bản trang cho thấy ngày báo cáo khác (ví dụ "31/12/2024" ở cột chính) thì cảnh báo `period_mismatch`. Phạm vi báo cáo `reporting_scope` do người dùng khai (`consolidated` hoặc `separate`), không suy đoán.

## API (cập nhật `contracts/openapi.json`, schema Pydantic ở `thesis_api`)

- `POST /api/onboarding/filings` (multipart: `file` PDF tối đa 40 MB, `entity_id` mã 3 chữ, `display_name` tùy chọn, `fiscal_year`, `reporting_scope`). Lưu PDF vào `USER_UPLOADS_DIR/filings/<filing_id>/source.pdf`, tính SHA-256, trả `202` với `{filing_id, status:"processing"}`; công việc chạy nền (thread), cập nhật tiến độ `{pages_done, page_count}`. Từ chối: không phải PDF (kiểm tra magic bytes, không tin đuôi tệp), quá lớn, PDF mã hóa/hỏng, `entity_id` đã thuộc Gold (giống UPLOAD-1).
- `GET /api/onboarding/filings/{filing_id}`: `{status: processing|ready|failed, error_code?, message_vi?, filename, sha256, page_count, progress:{pages_done,page_count}, text_layer_pages, ocr_pages, statement_pages:{balance_sheet:[..], income_statement:[..], loan_quality_note:[..]}, unit_detected, rows:[{row_id, metric_id, period_role:"target"|"prior", period_id, value_billion_vnd (chuỗi decimal), raw_text, row_label, page, source:"text_layer"|"ocr", status:"candidate"|"needs_review"|"missing", issues:[{code,message_vi}], alternatives:[...]}], limitations_vi}`.
- `GET /api/onboarding/filings/{filing_id}/pages/{n}.png`: ảnh trang 120 dpi (n từ 1; trả 404 nếu ngoài khoảng; cache).
- `GET /api/onboarding/filings` liệt kê gần đây. Chỉ nhận định dạng tên an toàn cho `filing_id` (`fl-` + 12 hex), từ chối mọi biến thể đường dẫn.
- Các đường này nằm sau cổng đăng nhập (AUTH-1) như mọi `/api/*` trừ danh sách công khai hiện có; không thêm vào danh sách công khai. Không đưa vào `analysis` — chưa có đường nào dùng dòng ứng viên cho phân tích.

## Đo độ chính xác (bắt buộc, trung thực)

`scripts/ingest_eval.py`: với mỗi trong 10 ngân hàng, chạy đường ống trên `data/raw/official/bank-2025-top10-v1/<MÃ>_2025_audited_consolidated.pdf` (năm 2025, hợp nhất; đường dẫn tuyệt đối vì thư mục này bị git bỏ qua: `<thư mục gốc kho mã>/data/raw/official/bank-2025-top10-v1/`), so với `data/onboarding/top10-2025/<MÃ>-2025q4.csv` (giá trị kỳ 2025_Q4 và 2024_Q4). Báo cáo: số dòng đúng / sai / thiếu / cần xem lại trên tổng 200 ô (10 ngân hàng × 10 đầu vào × 2 kỳ; chỉ tính ô có trong CSV chuẩn), tỷ lệ trang tìm đúng so với `pdf_page` trong CSV chuẩn, thời gian OCR mỗi trang và cả tệp. Ghi `experiments/ingest/RESULTS.md` kèm `rows.json`. **Không chỉnh bộ quy tắc theo từng ngân hàng để đẩy số**: có thể thêm nhãn đồng nghĩa tổng quát, nhưng kết quả báo cáo phải trung thực kể cả khi thấp; liệt kê nguyên nhân sai theo nhóm (không tìm thấy dòng, sai cột, sai đơn vị, OCR sai chữ số). Đây là bằng chứng cho luận văn (mục thực nghiệm mới), nên không che số.

## Kiểm thử

Test đơn vị không phụ thuộc Tesseract hay file PDF thật: dùng văn bản trang giả (có và không có tiêu đề cột, đơn vị triệu/nghìn, số âm trong ngoặc, dòng tổng phụ trùng nhãn, trang mục lục), và một PDF tổng hợp nhỏ dựng bằng PyMuPDF trong test (có lớp chữ) cho đường API end-to-end (`202` → `ready`). Test từ chối: không phải PDF, vượt dung lượng, `entity_id` thuộc Gold, `filing_id` đường dẫn độc hại, thiếu `fiscal_year`. Test có Tesseract (nếu tìm thấy) được đánh dấu bỏ qua khi thiếu để CI xanh. CI chạy `python -m unittest discover -s tests -q`.

Chạy: `PYTHONPATH=src python -m unittest discover -s tests`, `python scripts/check_architecture_guardrails.py`, `python scripts/check_openapi_contract.py`. Thêm `PyMuPDF` vào `requirements.txt` và `requirements-render.txt` (kiểm tra bản wheel Linux) và `pytesseract` là **không cần**: gọi `subprocess` tới `tesseract` trong adapter. Ghi LESSON mới vào `.agent/memory/lessons-learned.md` cho điều bất ngờ gặp phải.

## Ngoài phạm vi

Không giao diện, không đẳng thức kế toán, không `confirm`, không thay đổi Render/Docker, không dùng mô hình ngôn ngữ để đọc số. Không tạo release, tag hay bình luận thử.

## Bàn giao

Khối bàn giao (Base SHA, Branch, Commit SHA, PR, file đổi, test kèm số thật, bảng độ chính xác thật), `gh pr checks` xanh, dòng cuối đúng `DONE-INGEST1`.
