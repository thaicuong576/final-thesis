# Project Charter: Hệ thống Multi-Agent Phân tích Tài chính Ngân hàng

> **Tài liệu nền tảng cấp cao nhất (Spec Zero - Part 1)**  
> **Trạng thái**: Đóng băng (Frozen Foundation)  
> **Phạm vi áp dụng**: Bắt buộc cho toàn bộ các Agent Roles (`Lead`, `Worker-Data`, `Worker-API`, `Worker-UI`, `Auditor`).

---

## 1. TÔN CHỈ TỐI THƯỢNG (NORTH STAR GOAL)

Xây dựng và thực nghiệm hệ thống **Hierarchical Multi-Agent System** chuyên sâu phân tích và phản biện Báo cáo Tài chính của các Ngân hàng Thương mại Cổ phần niêm yết tại Việt Nam theo khung **CAMEL**, kết hợp đối sánh chéo với toàn ngành (**Peer Benchmark**).

Hệ thống hoạt động theo phương pháp luận phân tầng từ trên xuống (**Top-Down Hierarchical Analysis**):
1. **Macro Level (Vĩ mô)**: Nắm bắt chu kỳ chính sách tiền tệ của Ngân hàng Nhà nước (NHNN), lãi suất điều hành, và mục tiêu tăng trưởng tín dụng toàn hệ thống.
2. **Sector Level (Ngành / Đối thủ)**: Tính toán phân vị và trung vị ngành đối chuẩn (Peer Median Benchmark) để xác định vị thế cạnh tranh.
3. **Company Level (Doanh nghiệp)**: Đi sâu phân tích sức khỏe tài chính nội tại của ngân hàng mục tiêu theo 5 trụ cột CAMEL.
4. **Cross-Level Critique (Phản biện chéo)**: Giám sát mâu thuẫn giữa hiệu quả doanh nghiệp và bối cảnh ngành/vĩ mô thông qua vòng lặp phản biện có kiểm soát (Supervised / Bounded Critique Loop).

Mục tiêu học thuật then chốt của luận văn là **chứng minh bằng thực nghiệm**: Hệ thống Multi-Agent phân tầng có phản biện đạt độ chính xác thực tế (**factual correctness**), tính truy vết bằng chứng (**evidence traceability**) và tính nhất quán xuyên tầng (**cross-level consistency**) vượt trội so với mô hình **Single-Agent baseline** chạy trên cùng một tập dữ liệu đóng băng và cùng một bộ quy tắc.

---

## 2. KHÔNG GIAN ĐỐI TƯỢNG NGHIÊN CỨU (TARGET UNIVERSE)

### 2.1. Nhóm Ngân hàng Mục tiêu (Primary Banking Universe)
Dữ liệu chuẩn hóa trong `finance_master_v2.sqlite` bao gồm 10 ngân hàng thương mại đại diện cho các phân khúc trọng yếu:

| Mã (Ticker) | Phân nhóm phân tích | Đặc điểm trọng tâm theo luận văn |
|---|---|---|
| **ACB** | Bán lẻ thận trọng & An toàn | Chất lượng tài sản cao, NPL thấp, chi phí dự phòng thấp. |
| **TCB** | Bán lẻ tư nhân & Hệ sinh thái | Tỷ lệ CASA dẫn đầu, tỷ trọng cho vay BĐS/doanh nghiệp cao, NIM biến động theo chu kỳ. |
| **MBB** | Ngân hàng Quân đội & Bán lẻ số | Lợi thế CASA mạnh, tệp khách hàng số lớn, chi phí vốn thấp. |
| **VCB** | Ngân hàng Quốc doanh đầu ngành | Quy mô lớn nhất, chất lượng tài sản chuẩn mực, chi phí vốn rẻ nhất hệ thống. |
| **CTG** | Ngân hàng Quốc doanh công thương | Dư nợ sản xuất kinh doanh lớn, trích lập dự phòng quy mô lớn. |
| **BID** | Ngân hàng Quốc doanh quy mô lớn | Mạng lưới rộng, tăng trưởng tín dụng bám sát trần định hướng NHNN. |
| **VPB** | Bán lẻ tiêu dùng & Tăng trưởng | Lợi suất tài sản cao, rủi ro tín dụng tiêu dùng (FE Credit) và đệm vốn lớn. |
| **HDB** | Thương mại cổ phần năng động | Tăng trưởng tín dụng cao, tập trung chuỗi giá trị và nông nghiệp/bán lẻ. |
| **STB** | Ngân hàng tái cơ cấu | Trọng tâm xử lý nợ xấu VAMC và phục hồi năng lực tài chính. |
| **LPB** | Mạng lưới bưu điện & Bán lẻ | Lợi thế mạng lưới huy động vùng sâu, chuyển đổi mô hình ngân hàng số. |

> **Bộ mẫu lõi đối chuẩn (Core Peer Benchmark Sample)**: 5 ngân hàng trọng điểm (`ACB`, `TCB`, `VPB`, `MBB`, `VCB`) là vũ trụ đối sánh chuẩn hóa cho các báo cáo so sánh tự động.

### 2.2. Nhóm Chứng khoán (Extension Universe)
Bao gồm 5 công ty chứng khoán đại diện: `SSI`, `VND`, `HCM`, `VCI`, `MBS`.
- **Nguyên tắc**: Dữ liệu chứng khoán được lưu trữ phục vụ mở rộng nghiên cứu (Extension Material). Tuyệt đối **không gộp lẫn** chỉ số tài chính của công ty chứng khoán vào ma trận trung vị ngành của nhóm ngân hàng.

### 2.3. Khung Thời gian (Temporal Boundaries)
- Dữ liệu lịch sử chuẩn hóa: Giai đoạn **2020 – 2024** (chuỗi quý từ `2020_Q1` đến `2024_Q4`).
- Bộ kỳ đánh giá thực nghiệm (Benchmark Evaluation Quarters): Tập trung `2024_Q1` đến `2024_Q4`.

---

## 3. CÁC SẢN PHẨM CHUYỂN GIAO TRỌNG TÂM (CORE DELIVERABLES)

1. **Deterministic Data Engine (`finance_master_v2.sqlite` & `src/thesis_data/`)**:
   - Cơ sở dữ liệu SQLite chạy chế độ WAL mode, bất biến dữ liệu gốc.
   - Thư viện code Python thuần túy tính toán toàn bộ chỉ số CAMEL và trung vị ngành.
   - Cơ chế truy vết nguồn gốc (Provenance Engine) liên kết mỗi giá trị số với `source_id`, `source_locator`, và trích đoạn BCTC kiểm toán.

2. **Hierarchical Multi-Agent Pipeline (`src/thesis_agents/` & `src/thesis_api/`)**:
   - Kiến trúc LangGraph / StateGraph gồm các tác tử chuyên biệt: Macro Specialist, Sector Specialist, Company Specialist, và Cross-Level Critique Controller.
   - Cơ chế phát hiện mâu thuẫn xuyên tầng (ví dụ: NIM ngân hàng tăng đột biến trong bối cảnh toàn ngành thu hẹp margin).
   - REST API chuẩn hóa (FastAPI) đóng băng theo `contracts/openapi.json`.

3. **Retro Developer Workbench Dashboard (`frontend/`)**:
   - Giao diện React 19, Vite, Tailwind CSS tuân thủ phong cách xúc giác kỹ thuật (Warm Retro Developer Workbench).
   - Ba màn hình cốt lõi:
     - **Screen 1 (Query Composer)**: Tiếp nhận câu hỏi phân tích bằng ngôn ngữ tự nhiên, tự động trích xuất ý định (Intent Parsing) thành phạm vi ngân hàng, kỳ báo cáo và chỉ số.
     - **Screen 2 (Observable Session)**: Hiển thị dòng suy luận trực quan của các tác tử theo thời gian thực (Activity Timeline, Specialist Sheet, Revision Rounds).
     - **Screen 3 (Financial Report View)**: Bảng đối chuẩn Peer Benchmark, biểu đồ CAMEL trực quan, và khối bằng chứng đối soát (Evidence Trail).

4. **Academic Evaluation Framework & Thesis Chapters**:
   - Bộ công cụ đánh giá mù (Blind Human / AI Evaluation UI tại `research/evaluation-ui/`).
   - Bản nháp luận văn hoàn chỉnh (Chương 1–4 về lý thuyết, dữ liệu và kiến trúc; Chương 5 về thực nghiệm và kết quả đối đầu).

---

## 4. RANH GIỚI TUYỆT ĐỐI CẤM (STRICT NON-GOALS)

Để đảm bảo tính khoa học và đạo đức của một luận văn công nghệ tài chính, hệ thống thiết lập 4 điều cấm bất biến:

1. ❌ **KHÔNG LÀM BOT TRADING / ĐẦU CƠ**:
   - Hệ thống không sinh tín hiệu kỹ thuật (Buy/Sell/Hold), không tính RSI/MACD cho giao dịch ngắn hạn, không tích hợp tài khoản chứng khoán để đặt lệnh.
2. ❌ **KHÔNG DỰ ĐOÁN GIÁ CỔ PHIẾU BẰNG MÔ HÌNH HỘP ĐEN**:
   - Hệ thống không sử dụng LSTM/Linear Regression để vẽ đường giá tương lai. Giá trị của hệ thống nằm ở **phân tích cơ bản định lượng và phản biện logic tài chính**.
3. ❌ **KHÔNG SINH TEXT PHÂN TÍCH NẾU THIẾU SỐ LIỆU ĐỊNH LƯỢNG LÀM BẰNG CHỨNG (NO HALLUCINATION)**:
   - Nghiêm cấm LLM tự sáng tác nhận định về tình hình kinh doanh nếu không có ít nhất một quan sát số liệu (`MetricObservation`) hoặc đoạn trích thuyết minh (`EvidenceSnippet`) trong cơ sở dữ liệu làm bằng chứng.
4. ❌ **KHÔNG TỰ ĐỘNG THAY THẾ PHẠM VI DỮ LIỆU THIẾU BẰNG SỐ LIỆU SUY DIỄN (NO SILENT FALLBACK)**:
   - Khi một ngân hàng thiếu số liệu của một kỳ, hệ thống phải công bố trạng thái `MISSING` kèm lý do cụ thể (`reason`), tuyệt đối không tự lấy trung bình ngành đắp vào để làm tròn số.
