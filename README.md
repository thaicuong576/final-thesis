# Hệ thống đa tác tử hỗ trợ tổng hợp thông tin và phân tích cơ bản các ngân hàng niêm yết tại Việt Nam

Mã nguồn đi kèm khóa luận tốt nghiệp *"Thiết kế và đánh giá hệ thống đa tác tử hỗ trợ tổng hợp thông tin và phân tích cơ bản các ngân hàng niêm yết tại Việt Nam"* (Trường Đại học Kinh tế TP. Hồ Chí Minh, Trường Công nghệ và Thiết kế, Viện Đổi mới sáng tạo). Tác giả: Phùng Thái Cường. Giảng viên hướng dẫn: Lê Văn. Bản thử nghiệm trực tuyến: <https://fin-ai.eddiephung.me> (có màn hình đăng nhập; tài khoản dùng thử nằm trong Phụ lục A của khóa luận).

Kho mã này vừa là sản phẩm được mô tả trong khóa luận, vừa là nơi lưu dữ liệu đầu vào, mã chạy thực nghiệm và kết quả thô để người đọc kiểm tra lại các con số ở Chương 5.

## 1. Mục đích và phạm vi

Khóa luận hỏi: cách tổ chức hệ thống đa tác tử nào cho báo cáo phân tích ngân hàng mà mỗi con số truy được về trang báo cáo tài chính gốc, và cách tổ chức đó tốn thêm bao nhiêu so với một tác tử đơn. Ba câu hỏi nghiên cứu được trả lời bằng so sánh các cấu hình:

| Cấu hình | Mô tả |
|---|---|
| A | Một tác tử, cùng dữ liệu, công cụ tính toán và bộ kiểm chứng |
| B | Đa tác tử phân cấp: điều phối viên giao việc cho chuyên viên doanh nghiệp, ngành, vĩ mô |
| C | B cộng bộ phản biện ngữ nghĩa và tối đa hai vòng sửa đổi có mục tiêu |
| D | Đối chứng không gọi mô hình: câu nhận định lấy từ mẫu câu dựng sẵn |

Phạm vi dữ liệu: 10 ngân hàng niêm yết lớn nhất (ACB, BID, CTG, HDB, MBB, SHB, STB, TCB, VCB, VPB), 10 quý từ quý 1/2024 đến quý 2/2026, 4 chỉ tiêu (tỷ lệ nợ xấu, tỷ lệ bao phủ nợ xấu, ROA, ROE), tức 100 ô ngân hàng - quý và 400 giá trị chỉ tiêu. Bộ dữ liệu có 1.735 quan sát (1.335 số liệu đầu vào đọc từ báo cáo gốc, 400 giá trị tính lại), mỗi quan sát có vị trí trang nguồn. Hệ thống không thay thế người phân tích và không đưa khuyến nghị đầu tư.

## 2. Những gì đã có, và mức độ kiểm chứng

| Thành phần | Trạng thái |
|---|---|
| Bộ dữ liệu vận hành 10 ngân hàng × 10 quý, có trang nguồn và bản ghi phép tính | Đã triển khai, đối soát thủ công, dùng cho thực nghiệm chính |
| Gold v5 (5 ngân hàng, năm tài chính 2025), bộ chuẩn đối chiếu độc lập | Đã triển khai; không dùng để tính trung vị của nhóm 10 ngân hàng |
| API phân tích (một kỳ cho doanh nghiệp, ngành, nhóm so sánh; xu hướng 2 đến 4 kỳ cho một ngân hàng), kế hoạch khóa trước khi truy xuất | Đã triển khai, có kiểm thử tự động |
| Bộ kiểm chứng từng câu bằng quy tắc xác định (số, thứ hạng, kỳ, nhãn chỉ tiêu, chiều so sánh, tự so sánh) | Đã triển khai; độ nhạy đo bằng đột biến giả lập |
| Phản biện ngữ nghĩa và sửa đổi có mục tiêu (cấu hình C) | Đã triển khai, đã đánh giá |
| Giao diện web (hỏi, theo dõi tác tử, đọc báo cáo, tra cứu trang nguồn, thư viện báo cáo), luồng SSE | Đã triển khai |
| Tải lên CSV của ngân hàng mới, tính lại chỉ tiêu và so sánh với nhóm | Đã triển khai, mới thử với một ngân hàng mẫu |
| Cổng đăng nhập dùng chung (tùy chọn, `AUTH_ENABLED`) | Đã triển khai |
| Đọc báo cáo PDF thành dữ liệu ứng viên (OCR, LlamaParse) | Thử nghiệm: kết quả chỉ là ứng viên, không đưa vào bộ dữ liệu phân tích khi chưa đối soát |
| Bối cảnh thị trường (giá cổ phiếu, P/B qua API SSI) | Tùy chọn, hiển thị tách riêng, không nằm trong phạm vi đánh giá |
| Chuyên viên vĩ mô | Có dữ liệu vĩ mô theo quý nhưng chưa được thực nghiệm đánh giá riêng |
| Xu hướng nhiều kỳ cho nhóm so sánh hoặc vĩ mô | Chưa hỗ trợ |
| Bộ câu hỏi độc lập do người ngoài đặt, chấm bởi chuyên gia, khảo sát lớn hơn | Chưa thực hiện (xem khóa luận, mục 6.3 và 6.4) |

## 3. Kiến trúc

```text
Trình duyệt (React) ──HTTP/SSE──▶ thesis_api (FastAPI)  ──▶ thesis_data (lõi phân tích)
                                   │ lập kế hoạch, điều phối      │ công thức, quy tắc kiểm chứng,
                                   │ gọi mô hình ngôn ngữ         │ hợp đồng dữ liệu, trạng thái dữ liệu
                                   ▼                              ▼
                              lịch sử lượt chạy (SQLite)     snapshot dữ liệu (SQLite, chỉ đọc)
```

Luồng một lượt phân tích: câu hỏi tiếng Việt → kế hoạch phân tích được khóa trước khi truy xuất → công cụ tính các dữ kiện (mã tính mọi con số, mô hình không tự tính) → chuyên viên viết nhận định có trích dẫn dữ kiện → bộ kiểm chứng kiểm từng câu (câu sai bị loại riêng) → (cấu hình C) phản biện và sửa → báo cáo kèm số trang nguồn. Dữ liệu đi qua bốn trạng thái: nguồn thô, ứng viên, vận hành, khóa bằng mã băm. Mô tả đầy đủ ở Chương 3 và 4 của khóa luận, và ở `docs/ARCHITECTURE.md`, `docs/DATA-CONTRACT.md`, `docs/ARCHITECTURAL-GUARDRAILS.md`.

## 4. Công nghệ

- Python 3.11, FastAPI, Pydantic v2, SQLite, PyMuPDF, SDK tương thích OpenAI (dùng cho các nhà cung cấp OpenAI và DeepSeek), LangGraph (bộ điều khiển sửa đổi có giới hạn).
- Giao diện: React 19, TypeScript, Vite, Tailwind CSS, TanStack Query (`frontend/`).
- Triển khai thử nghiệm: Render (API), Supabase Storage riêng tư (snapshot, lịch sử lượt chạy), Vercel (giao diện). Cấu hình trong `render.yaml`, `vercel.json`.
- Kiểm tra liên tục: GitHub Actions (`.github/workflows/`).

## 5. Cấu trúc thư mục

| Đường dẫn | Nội dung |
|---|---|
| `src/thesis_data/` | Lõi phân tích: hợp đồng dữ liệu, công thức chỉ tiêu, bộ kiểm chứng, biên nhận tính toán |
| `src/thesis_api/` | API FastAPI, lập kế hoạch, điều phối, công cụ, tích hợp mô hình, lịch sử lượt chạy |
| `frontend/` | Giao diện web và kiểm thử giao diện |
| `contracts/` | OpenAPI, lược đồ SQLite, lược đồ gói nhập ngân hàng mới |
| `data/` | Đầu vào đã chép (`onboarding/`), bộ dữ liệu đánh giá (`evaluation/`), tài liệu nguồn công khai (`raw/`), biên bản đối soát (`reconciliation/`). Các tệp SQLite sinh ra không nằm trong Git |
| `experiments/` | Câu hỏi, thang chấm, kết quả thô và phân tích của các thực nghiệm (xem `experiments/RESULTS-INDEX.md`) |
| `scripts/` | Dựng snapshot, chạy và chấm thực nghiệm, kiểm tra hợp đồng, dựng bản Word khóa luận |
| `tests/` | Kiểm thử Python (chạy bằng `unittest`) |
| `docs/` | Đặc tả, kiến trúc, quyết định thiết kế, giao thức đánh giá; bản thảo khóa luận ở `docs/thesis-v2/` (xem `docs/README.md`) |
| `AGENTS.md`, `.agent/`, `.fleet/` | Quy tắc và nhật ký của quy trình phát triển có tác tử AI hỗ trợ; không cần cho việc chạy hệ thống |

## 6. Cài đặt và chạy

Yêu cầu: Python 3.11 và Node.js 24 (theo cấu hình CI).

**Bước 1. Môi trường Python**

```bash
python -m venv .venv && source .venv/bin/activate      # Windows: .venv\Scripts\activate
pip install -r requirements-test.txt
export PYTHONPATH=src                                  # Windows PowerShell: $env:PYTHONPATH="src"
```

**Bước 2. Dựng snapshot dữ liệu.** Các tệp SQLite không nằm trong Git (chỉ có dữ liệu đầu vào). Dựng snapshot 10 ngân hàng × 10 quý từ tệp đầu vào đã chép:

```bash
mkdir -p data/processed
python scripts/build_quarterly_snapshot.py \
  --inputs data/onboarding/quarterly-top10/inputs.csv \
  --macro-inputs data/onboarding/macro-sector/inputs.csv \
  --names data/onboarding/top10-2025/banks.json \
  --out data/processed/bank-quarterly-top10-operational-v1.sqlite
```

Lưu ý: bản dựng lại cho cùng 1.735 giá trị với bản `r4` dùng ở khóa luận (đã so từng ô), nhưng tệp SQLite không trùng từng byte vì có siêu dữ liệu dựng. Các thực nghiệm ghim mã băm của bản `r4`; tệp `r4` và Gold v5 được đính kèm ở bản phát hành của kho mã (xem mục 8).

**Bước 3. Cấu hình.** Sao chép `.env.example` thành `.env` rồi điền. Tối thiểu để chạy cục bộ: `SQLITE_DB_PATH` (snapshot chỉ đọc), `ANALYSIS_RUNS_DB_PATH` (một tệp khác để ghi lịch sử), `EXPECTED_DATASET_SNAPSHOT_ID`, `EXPECTED_SQLITE_SHA256`, và `OPENAI_API_KEY`, `OPENAI_BASE_URL`, `OPENAI_MODEL` nếu muốn gọi mô hình thật. Không commit `.env`.

**Bước 4. Chạy API và giao diện**

```bash
uvicorn thesis_api.main:app --reload --port 8000        # kiểm tra: GET /api/health, /api/ready
cd frontend && npm ci && npm run dev                    # đặt VITE_API_BASE_URL trỏ tới API
```

Khi thiếu cấu hình bộ viết hoặc bộ phản biện, `/api/ready` báo chưa sẵn sàng và các lệnh phân tích bị chặn trước khi truy xuất; đây là hành vi có chủ đích.

## 7. Kiểm thử

Giống CI:

```bash
python scripts/check_openapi_contract.py
python scripts/check_architecture_guardrails.py
python -m unittest discover -s tests -q
python scripts/eval_regression.py
python -m compileall -q src scripts tests
cd frontend && npm run lint && npm test -- --run && npm run build
```

Kiểm thử dùng mô hình và dữ liệu giả lập; chúng chứng minh hệ thống chạy đúng các kịch bản đã mô tả, không chứng minh chất lượng khi dùng mô hình thật. Một số kiểm thử cần các tệp SQLite sinh ra ở bước 2 và sẽ bỏ qua hoặc báo thiếu nếu chưa dựng.

## 8. Tái lập thực nghiệm

Kết quả thô (từng lượt chạy dạng JSON, bảng điểm, bảng tổng hợp, biểu đồ) đã nằm trong `experiments/`; mục lục ở `experiments/RESULTS-INDEX.md`, số liệu dùng trong khóa luận ở Chương 5 và Phụ lục C. Chương 5 tính từ các tệp này nên có thể kiểm tra lại mà không gọi mô hình.

| Thực nghiệm | Thư mục | Ghi chú |
|---|---|---|
| A/B/C trên DeepSeek V4 Pro, 12 câu hỏi | `experiments/er9/` | Chấm tất định bằng `scripts/er9_score.py`, phân tích bằng `scripts/er9_analyze.py` |
| Cấu hình D (đối chứng không mô hình) | `experiments/er9d/` | |
| A/B/C và D trên gpt-5.6-luna | `experiments/er9-luna/`, `experiments/er9-luna-d/` | Chạy lại trên mô hình khác và mã nguồn đã thêm hai quy tắc kiểm chứng |
| Độ nhạy bộ kiểm chứng bằng đột biến | `experiments/mut1/` (trước), `experiments/mut2/` (sau, hai seed bổ sung); mã `scripts/verifier_mutation.py` | |
| So sánh năm mô hình | `experiments/e2/`, `experiments/e2r/` | |
| Kiểm tra đối kháng | `experiments/e3/` | |
| Đo số hóa báo cáo gốc | `experiments/e5/` | |
| Mô hình phổ thông không có công cụ (minh họa) | `experiments/e6-pure-llm/` | Một lần chạy, một mô hình |
| Phiếu chấm mù | `experiments/blind-grading/` | |

Chạy lại bằng mô hình thật cần khóa API, tốn token (công cụ đặt trần mặc định 3 triệu token mỗi đợt) và không cho cùng kết quả từng chữ vì đầu ra của mô hình thay đổi giữa các lần chạy. Chạy thử không gọi mô hình: `python scripts/er9_run.py --dry-run`. Các tệp SQLite sinh ra khi chạy được Git bỏ qua.

## 9. Giới hạn đã biết

Danh sách đầy đủ ở mục 3.4, 5.7.3 và 6.3 của khóa luận. Điểm chính:

- Dữ liệu chỉ có 10 ngân hàng và 4 chỉ tiêu; số liệu do tác giả đối soát với sự hỗ trợ của công cụ, chưa có người thứ hai kiểm tra.
- Mỗi cặp câu hỏi - cấu hình chạy một lần trên mỗi mô hình, nên kết quả là quan sát, không có ý nghĩa thống kê. Lợi thế của cấu hình B so với A xuất hiện ở DeepSeek V4 Pro và không còn ở gpt-5.6-luna.
- Các chỉ số tự động (khớp số, truy nguồn) đo trên các câu đã qua bộ kiểm chứng nên phản ánh thiết kế, không phản ánh năng lực mô hình. Hai quy tắc kiểm chứng được thêm sau khi thấy kết quả độ nhạy; tỷ lệ phát hiện 99,2% chưa chứng minh cho loại lỗi khác.
- Bộ 12 câu hỏi vừa dùng để hiệu chỉnh vừa dùng để đánh giá. Khảo sát người dùng chỉ có 15 người, chọn thuận tiện.
- Phân tích chỉ ở mức thuật lại số liệu, xu hướng và vị thế so với nhóm; không giải thích nguyên nhân và không dự báo.

## 10. Dữ liệu và bản quyền của bên thứ ba

Báo cáo tài chính, thông tư, quyết định và báo cáo vĩ mô trong `data/raw/` là tài liệu công khai do các tổ chức phát hành giữ bản quyền; chúng được lưu để kiểm tra nguồn và không thuộc giấy phép của kho mã. Mọi giá trị trong bộ dữ liệu ghi mã băm SHA-256 và số trang của tài liệu nguồn.

## 11. Giấy phép và trích dẫn

Mã nguồn theo giấy phép MIT (`LICENSE`). Khi dùng, vui lòng trích dẫn theo `CITATION.cff`:

> Phùng Thái Cường (2026). *Thiết kế và đánh giá hệ thống đa tác tử hỗ trợ tổng hợp thông tin và phân tích cơ bản các ngân hàng niêm yết tại Việt Nam*. Khóa luận tốt nghiệp, Trường Đại học Kinh tế TP. Hồ Chí Minh.

Đóng góp: xem `CONTRIBUTING.md`.
