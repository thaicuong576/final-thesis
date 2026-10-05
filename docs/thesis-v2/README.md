# Hồ sơ Biên soạn Khóa luận tốt nghiệp (Phiên bản v2 - Kiến trúc Báo cáo Thích ứng)

Thư mục này chứa toàn bộ bản thảo hoàn chỉnh của **Chương 3 (Phương pháp nghiên cứu)** và **Chương 4 (Thiết kế và triển khai hệ thống)** được viết lại toàn diện theo kiến trúc hệ thống hiện tại của repository (sau quyết định kiến trúc D-075 và kế hoạch nâng cấp hệ thống báo cáo `2026-09-28-er-report`).

---

## 1. Danh mục tệp và Trạng thái hoàn thành

| Đường dẫn tệp | Mô tả nội dung | Trạng thái kỹ thuật |
|---|---|:---:|
| [`chuong-3-phuong-phap.md`](chuong-3-phuong-phap.md) | **Chương 3: Phương pháp nghiên cứu**<br/>• Cách tiếp cận Design Science Research (DSR) và case study 6 bước.<br/>• Ánh xạ chi tiết 3 câu hỏi nghiên cứu (RQ1, RQ2, RQ3).<br/>• Pipeline 4 trạng thái dữ liệu (Raw $\to$ Candidate $\to$ Operational $\to$ Gold).<br/>• Nguyên tắc "Code tính số, mô hình ngôn ngữ diễn giải".<br/>• Snapshot Gold v5: 5 ngân hàng (VCB, MBB, TCB, VPB, ACB) × 4 quý 2024 × 4 chỉ tiêu CAMEL (80 ô mục tiêu, 76 hợp lệ, 4 ô ACB Q1 thiếu dữ liệu).<br/>• Ca kiểm thử mở rộng VietinBank (CTG FY2024 Q4) chứng minh tính chuyển giao ngoài Gold.<br/>• Thiết kế thực nghiệm A/B/C với kế hoạch đóng băng dùng chung (`rules_only plan`).<br/>• Bộ 12 câu hỏi chuẩn hóa v2 (T01–T10 + R1/R2) và hệ thống chỉ số chấm tất định. | **HOÀN THÀNH**<br/>(Sẵn sàng tích hợp) |
| [`chuong-4-thiet-ke-trien-khai.md`](chuong-4-thiet-ke-trien-khai.md) | **Chương 4: Thiết kế và triển khai hệ thống**<br/>• Ranh giới phân tầng: Tầng lõi nghiệp vụ độc lập (`src/thesis_data`) vs Tầng ứng dụng phân tích (`src/thesis_api`).<br/>• Quy tắc bảo vệ kiến trúc (Architectural Guardrails), cấm phụ thuộc thư viện AI/SQLite và cấm hard-code 5 ngân hàng trong core.<br/>• Phân lập lưu trữ: DB phân tích chỉ đọc (`SQLITE_DB_PATH`) vs DB lịch sử mutable (`ANALYSIS_RUNS_DB_PATH`).<br/>• Luồng xử lý một lượt phân tích 8 bước chi tiết (Hiểu câu hỏi $\to$ Kế hoạch đóng băng $\to$ 11 loại Fact & Dataset $\to$ Tín hiệu & Mâu thuẫn liên tầng $\to$ Chuyên viên viết câu có trích Fact $\to$ Bộ kiểm tra câu xác định luận 11 luật $\to$ Lắp ráp ReportSpec theo khối $\to$ Phản biện ngữ nghĩa & Sửa đổi $\le 2$ vòng).<br/>• Hệ thống giám sát: Lưu vết tuần tự `TraceStep` và thông báo lỗi thân thiện tiếng Việt `AnalysisBlocked`.<br/>• Thiết kế giao diện tham chiếu 4 màn hình và 8 loại biểu đồ trực quan hóa.<br/>• Kiến trúc triển khai đám mây: FastAPI trên Render, nạp snapshot tự động kiểm tra mã băm từ Supabase Storage, frontend trên Vercel (`https://fin-ai.eddiephung.me`).<br/>• Chiến lược kiểm thử: 907 bài test đơn vị tự động, script kiểm soát ranh giới và CI/CD. | **HOÀN THÀNH**<br/>(Sẵn sàng tích hợp) |
| [`figures/hinh-3-1-quy-trinh-dsr.mmd`](figures/hinh-3-1-quy-trinh-dsr.mmd) | Sơ đồ Mermaid: Quy trình nghiên cứu 6 bước theo khung Design Science Research. | Hoàn thành |
| [`figures/hinh-3-2-pipeline-du-lieu.mmd`](figures/hinh-3-2-pipeline-du-lieu.mmd) | Sơ đồ Mermaid: Pipeline 4 trạng thái dữ liệu và các cổng kiểm soát nguồn. | Hoàn thành |
| [`figures/hinh-3-3-thiet-ke-thuc-nghiem-abc.mmd`](figures/hinh-3-3-thiet-ke-thuc-nghiem-abc.mmd) | Sơ đồ Mermaid: Thiết kế thực nghiệm so sánh ba cấu hình A/B/C với kế hoạch đóng băng dùng chung. | Hoàn thành |
| [`figures/hinh-4-1-kien-truc-phan-tang.mmd`](figures/hinh-4-1-kien-truc-phan-tang.mmd) | Sơ đồ Mermaid: Kiến trúc phân tầng và các ranh giới hệ thống (Client, Application, Core, Storage). | Hoàn thành |
| [`figures/hinh-4-2-luong-phan-tich-end-to-end.mmd`](figures/hinh-4-2-luong-phan-tich-end-to-end.mmd) | Sơ đồ Mermaid: Luồng xử lý một lượt phân tích thích ứng từ câu hỏi đến báo cáo. | Hoàn thành |
| [`figures/hinh-4-3-kiem-tra-cau-van.mmd`](figures/hinh-4-3-kiem-tra-cau-van.mmd) | Sơ đồ Mermaid: Quy trình kiểm tra câu văn xác định luận qua 11 quy tắc. | Hoàn thành |
| [`figures/hinh-4-4-kien-truc-trien-khai.mmd`](figures/hinh-4-4-kien-truc-trien-khai.mmd) | Sơ đồ Mermaid: Sơ đồ kiến trúc triển khai trên nền tảng đám mây (Render, Supabase, Vercel). | Hoàn thành |

---

## 2. Điểm kết nối dữ liệu phục vụ Chương 5 (Kết quả và Thảo luận)

Thực nghiệm đã được thực hiện vào ngày 30/09/2026 và kết quả được lưu tại `experiments/er8/RESULTS.md` cũng như Chương 5, bao gồm các dữ liệu định lượng sau:

1. **Ma trận kết quả thực thi và tỷ lệ hoàn thành (Completion Matrix):**
   - Số lượt chạy thành công (`COMPLETED`) / bị chặn hợp lệ (`BLOCKED`) / lỗi (`FAILED`) trên 12 nhiệm vụ (T01–T10, R1–R2) cho cả 3 cấu hình A, B, C.
2. **Độ chính xác dữ kiện và tính toàn vẹn số học (Factual Accuracy):**
   - Tỷ lệ các con số trong câu văn được giữ lại khớp 100% với Fact được trích dẫn;
   - Tỷ lệ Fact tái tính toán khớp hoàn toàn với dữ liệu gốc Gold v5.
3. **Hiệu quả xử lý trường hợp biên (Boundary & Missingness Controls):**
   - Kết quả xử lý ca thiếu dữ liệu ACB Q1/2024 trong T03 và T08 (xác nhận tỷ lệ bịa đặt số liệu = 0%);
   - Kết quả từ chối yêu cầu ngoài phạm vi R1 (kỳ 2025_Q1) và R2 (ngân hàng ngoài Gold CTG).
4. **Hiệu suất của Bộ kiểm tra câu văn xác định luận (Narrative Verifier Audit):**
   - Tổng số câu văn được sinh ra bởi từng cấu hình;
   - Số lượng và tỷ lệ câu văn bị loại bỏ (`DroppedSentence`);
   - Phân bố các mã lỗi vi phạm phổ biến nhất (`causal_language`, `trend_direction_mismatch`, `comparison_direction_mismatch`, `number_mismatch`).
5. **Hiệu quả của vòng lặp phản biện ngữ nghĩa và sửa đổi (Critic & Revision in Arm C):**
   - Số lượng vấn đề `CritiqueIssue` được phát hiện;
   - Số vòng sửa đổi thực tế trung bình trên mỗi phiên phân tích;
   - Tỷ lệ câu văn được cải thiện thành công và vượt qua bộ kiểm tra sau khi sửa đổi.
6. **Chi phí tài nguyên và đánh đổi vận hành (Operational Cost & Latency):**
   - Thời gian xử lý trung bình một yêu cầu (giây) của từng cấu hình;
   - Tổng số lượt gọi API mô hình ngôn ngữ;
   - Tổng lượng token đầu vào (prompt tokens) và token đầu ra (completion tokens);
   - Chi phí tài chính trung bình cho mỗi bản báo cáo phân tích (USD).
7. **Phân tích so sánh cặp đối chiếu:**
   - So sánh cặp B trừ A để trả lời định lượng cho RQ2;
   - So sánh cặp C trừ B để trả lời định lượng cho RQ3.

---

## 3. Quy tắc tích hợp khi đóng bản nộp cuối

- Không sửa đổi các tệp khóa luận nguồn trong `docs/Khoá luận tốt nghiệp - Cường - GVHD_ Lê Văn.md`.
- Khi đóng bản nộp sáu chương hoàn chỉnh, nội dung Chương 3 và Chương 4 từ thư mục này sẽ thay thế hoàn toàn các bản nháp làm việc cũ (`THESIS-CHAPTER-3-WORKING-*.md` và `THESIS-CHAPTER-4-WORKING-*.md`), đảm bảo sự đồng nhất tuyệt đối với hệ thống mã nguồn thực tế.
