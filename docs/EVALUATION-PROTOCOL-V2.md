# Giao Thức Đánh Giá Thực Nghiệm v2 (Evaluation Protocol v2)

**Trạng thái:** Đóng băng giao thức v2 (Protocol Freeze); áp dụng cho công cụ đánh giá A/B/C tự động (ER-8).  
**Tập dữ liệu chuẩn:** `gold-bank-2025-expanded-v5-evidence`, SHA-256 raw bytes:  
`1B1B5C090D2F8EDE87A4C33EA3EE716F7A54C9DE7C51089F4D3893D7A1FFCE73`.  
**Phạm vi thẩm quyền:** `data/evaluation/gold-v5-reporting-scope-authority-v1.json`, SHA-256 canonical LF UTF-8:  
`fef07af9f3deea7afbaa60ad51c8db740388e88b64bcf843d8ab5ec8f0ad777f`.

---

## 1. Mục Đích và Lý Do Cần Protocol v2

Protocol v1 (`docs/EVALUATION-PROTOCOL-V1-DRAFT.md`) được thiết kế cho kiến trúc nguyên khối cũ (Stage-1 regex và lệnh cấm blanket từ ngữ số liệu). 

Quyết định D-075 đã thay đổi căn bản kiến trúc hệ thống:
1. **Lập kế hoạch thích ứng theo loại câu hỏi** (`lookup`, `company_profile`, `trend`, `ranking`, `head_to_head`) và đóng băng kế hoạch trước khi truy xuất dữ liệu.
2. **Dữ kiện tất định (Typed Facts)**: Mọi số liệu trong báo cáo đều bắt nguồn từ các phép tính tất định có mã phiên bản công thức, liên kết định danh quan sát đầu vào (`input_observation_ids`) và định vị nguồn sơ cấp.
3. **Kiểm chứng từng câu (Sentence Verification)**: Thay vì cấm số liệu bằng regex dẫn đến hủy bỏ cả lượt chạy, bộ kiểm chứng kiểm tra từng câu với dữ kiện được trích dẫn; câu vi phạm bị loại bỏ có ghi vết (`NarrativeAudit`) mà không làm sập báo cáo.
4. **Báo cáo cấu trúc khối (`ReportSpec`) và nhật ký vết (`TraceStep`)**.

Protocol v2 được chuẩn hóa để đo lường trực tiếp trên các đối tượng kiến trúc mới này. File Protocol v1 được giữ nguyên làm chứng tích lịch sử.

---

## 2. Ba Nhánh So Sánh (Experimental Arms)

Thực nghiệm so sánh 3 kiến trúc trên cùng một tập câu hỏi và cùng một cơ sở dữ liệu Gold v5:

| Nhánh (Arm) | Tên kỹ thuật | Mô tả hành vi kiến trúc |
|---|---|---|
| **Arm A** | `single_agent` | **Baseline đơn tác tử**: Điều phối viên nhận tập dữ kiện tất định từ công cụ, không kích hoạt các chuyên viên phân tích ngành/doanh nghiệp riêng biệt, không có vòng phản biện ngữ nghĩa, trực tiếp ghép khối báo cáo. |
| **Arm B** | `hierarchical_no_critique` | **Phân tầng không phản biện**: Kích hoạt các chuyên viên phân tích theo kế hoạch; kiểm chứng câu độc lập; điều phối viên tổng hợp báo cáo; không có vòng phản biện ngữ nghĩa. |
| **Arm C** | `hierarchical_with_critique` | **Phân tầng có phản biện**: Đầy đủ quy trình của Arm B, bổ sung chuyên viên phản biện ngữ nghĩa (Semantic Critic) với tối đa 2 vòng tái lập luận và sửa đổi có định hướng. |

---

## 3. Bộ 12 Câu Hỏi Đánh Giá Chuẩn Hóa

Bộ câu hỏi được lưu tại `data/evaluation/er8-questions-v2.jsonl`, viết bằng tiếng Việt tự nhiên:

| Mã | Loại câu hỏi | Nội dung câu hỏi | Kỳ & Thực thể | Mục đích kiểm chứng |
|---|---|---|---|---|
| **T01** | `company_profile` | Sức khỏe tài chính của MBB trong quý 4/2024 so với các ngân hàng cùng nhóm. | MBB, 2024_Q4 | Phân tích toàn diện 4 chỉ tiêu (NPL, LLR, ROA, ROE) và vị thế tương đối. |
| **T02** | `company_profile` | Đánh giá chất lượng tài sản và khả năng sinh lời của VCB trong quý 4/2024. | VCB, 2024_Q4 | Đánh giá chất lượng tài sản và sinh lời đơn ngân hàng. |
| **T03** | `lookup` (thiếu dữ liệu) | Tỷ lệ nợ xấu của ACB trong quý 1/2024 là bao nhiêu? | ACB, 2024_Q1 | **Kiểm soát thiếu dữ liệu**: ACB Q1 thiếu số liệu chuẩn hóa, hệ thống phải công bố thiếu, cấm bịa số. |
| **T04** | `trend` | Xu hướng nợ xấu và tỷ lệ bao phủ nợ xấu của TCB diễn biến thế nào trong năm 2024? | TCB, 4 quý 2024 | Diễn biến chuỗi thời gian chất lượng tài sản qua 4 quý liên tiếp. |
| **T05** | `trend` | ROA và ROE của MBB thay đổi thế nào qua các quý năm 2024? | MBB, 4 quý 2024 | Diễn biến chuỗi thời gian khả năng sinh lời qua 4 quý liên tiếp. |
| **T06** | `ranking` | Ngân hàng nào có tỷ lệ nợ xấu thấp nhất trong quý 4/2024? | 5 ngân hàng, 2024_Q4 | Xếp hạng nợ xấu trên toàn bộ nhóm 5 ngân hàng Gold. |
| **T07** | `ranking` | Xếp hạng ROE các ngân hàng trong quý 4/2024. | 5 ngân hàng, 2024_Q4 | Xếp hạng tỷ suất sinh lời trên vốn chủ sở hữu. |
| **T08** | `trend` / `company_profile` | ACB đánh đổi chất lượng tài sản và khả năng sinh lời thế nào trong năm 2024 so với các ngân hàng cùng nhóm? | ACB, 4 quý 2024 | Phân tích đa kỳ kết hợp vị thế nhóm; bảo toàn tính thiếu dữ liệu quý 1 của ACB. |
| **T09** | `head_to_head` | So sánh ACB và TCB trong quý 4/2024. | ACB vs TCB, 2024_Q4 | So sánh trực tiếp cặp ngân hàng trên cả 4 chỉ số tài chính. |
| **T10** | `head_to_head` | VCB hay VPB tốt hơn về chất lượng tài sản trong quý 4/2024? | VCB vs VPB, 2024_Q4 | So sánh đối đầu chuyên biệt về nhóm chỉ tiêu chất lượng tài sản. |
| **R1** | `rejection` (từ chối) | Tỷ lệ nợ xấu của VCB trong quý 1/2025 là bao nhiêu? | VCB, 2025_Q1 | **Kiểm soát từ chối**: Kỳ 2025_Q1 nằm ngoài phạm vi snapshot, phải từ chối `unsupported_period`. |
| **R2** | `rejection` (từ chối) | Phân tích tình hình tài chính của CTG trong quý 4/2024. | CTG, 2024_Q4 | **Kiểm soát từ chối**: CTG nằm ngoài nhóm 5 ngân hàng Gold v5, phải từ chối `unsupported_entity`. |

Tập độ phủ kỳ vọng (`data/evaluation/er8-expected-coverage-v2.json`) được sinh tự động bằng script đọc trực tiếp cơ sở dữ liệu Gold v5 ở chế độ chỉ đọc (`mode=ro`), không nhập số thủ công.

---

## 4. Ràng Buộc Công Bằng và Cơ Chế Giữ Kế Hoạch Chung

1. **Plan chung giữa các Arm thông qua `planner_mode="rules_only"`**:
   - Nhằm đảm bảo tính công bằng tuyệt đối giữa các arm mà không làm phức tạp hóa runtime bằng việc tiêm spec giả định (`frozen_spec`), cả 3 arm được cấu hình chạy ở chế độ `planner_mode="rules_only"`.
   - Với cùng một câu hỏi và cùng catalog Gold v5, thuật toán lập kế hoạch tất định sinh ra `AnalysisPlan` giống hệt nhau.
   - Harness tự động tính toán mã băm `plan_hash` (canonical SHA-256) của kế hoạch cho từng lượt chạy và đối chiếu chéo giữa 3 arm. Nếu phát hiện bất kỳ sự sai lệch mã băm nào giữa các arm của cùng một tác vụ, lượt chạy sẽ bị đánh dấu `plan_hash_mismatch` và không hợp lệ.
2. **Sao chép dữ liệu tạm (Isolated Copy)**:
   - Dữ liệu Gold v5 gốc được kiểm tra mã băm SHA-256 trước khi chạy (`1b1b5c09...ce73`).
   - Mỗi phiên thực nghiệm tạo một bản sao độc lập của file SQLite để thực thi, đảm bảo file Gold gốc bất biến tuyệt đối.
3. **Thứ tự thực thi ngẫu nhiên và hạt giống (Seed)**:
   - Thứ tự 36 lượt chạy (12 tác vụ × 3 arm × 1 lần lặp) được xáo trộn ngẫu nhiên dựa trên hạt giống `seed=20260930` được ghi nhận trong manifest.
4. **Kiểm soát ngân sách Token (Token Budget Guard)**:
   - Giới hạn cứng: `--max-tokens 3000000`.
   - Sử dụng tổng `input_tokens + output_tokens` ghi nhận từ bộ theo dõi sử dụng mô hình (`LLMUsageTracker`).
   - Nếu vượt ngưỡng ngân sách, quá trình thực thi lập tức dừng lại, các lượt chạy chưa hoàn tất được ghi trạng thái `aborted_budget` và vẫn được tính vào mẫu số đánh giá.
5. **Chính sách thử lại lỗi mạng (Retry Policy)**:
   - Thử lại tối đa 2 lần (tổng 3 lần gọi) với độ trễ tăng dần, **chỉ áp dụng** cho lỗi mạng hoặc chạm giới hạn tần suất (rate limit 429/connection timeout).
   - Tuyệt đối không thử lại đối với lỗi logic, lỗi xác thực hợp đồng, hoặc yêu cầu bị từ chối nghiệp vụ.
   - Mọi lượt thử lại đều được lưu nhật ký chi tiết trong trường `retries` của file kết quả.

---

## 5. Chỉ Số Đánh Giá Tất Định (Deterministic Scoring)

Bộ chấm điểm tự động (`scripts/er8_score.py`) tính toán trực tiếp từ dữ liệu xuất ra của lượt chạy, không gọi thêm mô hình ngôn ngữ:

1. **Tỷ lệ hoàn thành (Completion)**: Trạng thái kết thúc `completed` (đối với T01–T10) hoặc từ chối chính xác mã lỗi dự kiến (`unsupported_period` cho R1, `unsupported_entity` cho R2).
2. **Tính đúng số (Numeric Correctness)**:
   - Mọi con số xuất hiện trong các câu được chấp nhận ở báo cáo cuối cùng phải khớp với dữ kiện được trích dẫn (cho phép sai số hiển thị làm tròn).
   - Mọi dữ kiện trích dẫn trực tiếp từ quan sát phải khớp hoàn toàn với số liệu gốc trong Gold v5 (sai số cho phép <= 0.01).
3. **Truy vết quan sát (Observation Traceability)**: 100% mã quan sát đầu vào (`input_observation_ids`) phải phân giải được tới bản ghi hợp lệ trong Gold v5 kèm mã định vị nguồn (`source_locator`).
4. **Độ phủ chỉ tiêu (Coverage Score)**: Tỷ lệ các ô số liệu bắt buộc (hoặc khai báo thiếu đúng) được phản ánh trong báo cáo so với danh sách trong `expected-coverage`.
5. **Xử lý thiếu dữ liệu (Missingness Handling)**: Đối với T03 và ACB Q1 trong T08, hệ thống không được bịa ra bất kỳ số liệu nào, đồng thời phải nêu rõ giới hạn dữ liệu không có sẵn.
6. **Kiểm soát từ chối đúng (Correct Rejection)**: R1 và R2 phải bị chặn trước khi gọi chuyên viên phân tích với mã lỗi chuẩn xác.
7. **Tỷ lệ câu bị loại (Discard Rate)**: Tỷ lệ câu phân tích bị bộ kiểm chứng (`SentenceVerifier`) loại bỏ do không trích dẫn dữ kiện, trích dẫn sai số, hoặc vi phạm từ ngữ nguyên nhân/đầu tư.
8. **Số liên kết tầng (Cross-Level Findings)**: Số phát hiện chéo tầng được ghi nhận trong báo cáo.
9. **Chi phí và thời gian**: Thời gian phản hồi (`duration_ms`), số lần gọi mô hình (`model_calls`), tổng token tiêu thụ (`total_tokens`), và số vòng sửa đổi (`revision_rounds`).

---

## 6. Hạn Chế Của Giao Thức v2

1. **Chưa thực hiện chấm mù chuyên gia (Human Blind Review)**: Do áp lực thời gian hoàn thành khóa luận, đợt đánh giá này tập trung toàn bộ vào các chỉ số khách quan, tất định và kiểm chứng toán học/nguồn gốc. Đánh giá chất lượng văn phong định tính từ chuyên viên phân tích tài chính con người được ghi nhận là hướng phát triển tiếp theo.
2. **Quy mô tập tác vụ**: Gồm 12 câu hỏi đại diện chuẩn hóa cho 5 nhóm nghiệp vụ chính của ngân hàng thương mại, 1 lần lặp (36 run).
3. **Cơ chế lập kế hoạch quy tắc**: Chế độ `rules_only` triệt tiêu tính ngẫu nhiên giữa các arm để đảm bảo so sánh kiến trúc công bằng, nhưng chưa khai thác tối đa tính linh hoạt lập kế hoạch mở của LLM.
