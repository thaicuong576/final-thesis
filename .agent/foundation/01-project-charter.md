# Project Charter: Hệ thống Multi-Agent Phân tích Tài chính Ngân hàng

> **Tài liệu nền tảng cấp cao nhất (Spec Zero - Part 1)**  
> **Trạng thái**: Đóng băng (Frozen Foundation)  
> **Phạm vi áp dụng**: Bắt buộc cho toàn bộ các Agent Roles (`Lead`, `Worker-Data`, `Worker-API`, `Worker-UI`, `Auditor`).

---

## 1. TÔN CHỈ TỐI THƯỢNG (NORTH STAR GOAL)

Dự án này là một **kiến trúc phân tích tài chính đa-agent có khả năng tái sử dụng (Reusable Financial Analysis Architecture)**, trong đó hệ thống **không chạy một pipeline cố định** mà lập kế hoạch theo từng yêu cầu phân tích (**Query-Adaptive Planning**) và chỉ kích hoạt những năng lực phân tích thực sự cần thiết.

- **Không phải pipeline tuần tự cưỡng ép**: `Macro Policy Context`, `Sector/Peer Comparison` và `Company Financial Performance (CAMEL)` là các **analytical capabilities độc lập**, không phải ba stage bắt buộc phải chạy trong mọi truy vấn.
- **Mục tiêu then chốt**: Tạo ra các phân tích có thể truy xuất ngược 100% đến dữ liệu và bằng chứng (`AtomicClaim` & `EvidenceTrail`), có kiểm soát chất lượng xác định bằng luật (**Stage 1 Deterministic Acceptance**), có phản biện ngữ nghĩa và hiệu đính có giới hạn (**Stage 2 Semantic Critique & Bounded Revision**), đồng thời giữ ranh giới sạch để frontend, database, orchestration framework hoặc data provider có thể được thay thế mà không phải viết lại analytical core.
- **Vai trò của Web Application**: Chỉ là **Reference Implementation** để chứng minh tính khả thi end-to-end của kiến trúc, không phải bản thân kiến trúc.

> **Tuyên ngôn North Star (Formal Charter Mandate)**:  
> *"A reusable, query-adaptive hierarchical multi-agent financial-analysis architecture in which an Orchestrator plans and composes only the analytical capabilities required by each request, with evidence-grounded outputs, bounded critique/revision, deterministic quality controls, and replaceable enterprise data interfaces, demonstrated through an end-to-end web application for financial analysts."*

### 1.1. Ba Đối tượng Chân lý Runtime Cốt lõi (Three Core Runtime Truth Objects)
Toàn bộ tính tái hiện (reproducibility) và giải trình (explainability) của kiến trúc tựa trên 3 hợp đồng trung tâm:
1. **`AnalysisPlan` (Ràng buộc Thực thi)**: Xác định hệ thống sẽ phân tích cái gì, entities nào, periods nào, và capability nào được phép kích hoạt cho request đó.
2. **`DatasetSnapshot` (Ràng buộc Tri thức/Dữ liệu)**: Xác định tập dữ liệu đóng băng nào được phép coi là sự thật tài chính cho lượt chạy đó.
3. **`AtomicClaim` (Ràng buộc Kết quả Đầu ra)**: Xác định hệ thống đang khẳng định điều gì và assertion đó dựa trên bằng chứng số liệu (`EvidenceSnippet` / `Observation`) cụ thể nào.

### 1.2. Mục tiêu Nghiên cứu Học thuật
Chứng minh bằng thực nghiệm: Hệ thống phân tầng thích ứng truy vấn (Query-Adaptive Hierarchical Workflow with Bounded Critique/Revision) vượt trội so với mô hình **Single-Agent baseline** chạy trên cùng một `DatasetSnapshot` về:
- Độ chính xác thực tế (**factual correctness**).
- Tính truy vết bằng chứng (**evidence traceability**).
- Tính nhất quán xuyên tầng (**cross-level consistency**).
- Giá trị thông tin phân tích (**analytical usefulness**).

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
