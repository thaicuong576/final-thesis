# Báo cáo Đánh giá Thực nghiệm A/B/C (ER-8)

Tài liệu này tổng hợp kết quả chạy thử nghiệm A/B/C trên bộ dữ liệu kiểm chứng Gold v5 (`gold-bank-2025-expanded-v5-evidence`), phục vụ phân tích thực nghiệm tại **Chương 5** của khóa luận tốt nghiệp.

> **Ghi chú tiến độ:** Báo cáo này được tạo bởi công cụ đánh giá tự động (harness & deterministic scorer). Dữ liệu mẫu dưới đây phản ánh kết quả chạy offline / dry-run phục vụ nghiệm thu bộ công cụ; phiên bản chính thức sẽ được kích hoạt khi chạy model trực tiếp theo ngân sách được duyệt.

---

## 1. Thiết kế Thí nghiệm và Các Nhánh So Sánh (Arms)

Thực nghiệm so sánh 3 kiến trúc xử lý trên cùng một câu hỏi và cùng một ảnh chụp dữ liệu (Gold v5):

- **Arm A (`single_agent`)**: Mô hình đơn lẻ, đóng vai trò đường cơ sở (baseline). Điều phối viên tổng hợp trực tiếp báo cáo từ tập dữ kiện tất định, không có sự tham gia của các chuyên viên độc lập và không có vòng phản biện ngữ nghĩa.
- **Arm B (`hierarchical_no_critique`)**: Kiến trúc phân tầng thích ứng theo loại câu hỏi. Các chuyên viên chuyên trách (doanh nghiệp, ngành, liên kết tầng) lập luận và trích xuất câu phân tích; kiểm chứng câu tự động; điều phối viên ghép khối báo cáo, không có vòng phản biện.
- **Arm C (`hierarchical_with_critique`)**: Kiến trúc phân tầng đầy đủ. Cùng điều phối viên và chuyên viên như Arm B, bổ sung thêm chuyên viên phản biện ngữ nghĩa (Semantic Critic) với tối đa 2 vòng tái lập luận và sửa đổi có định hướng.

### Ràng buộc thực nghiệm công bằng:
1. **Lập kế hoạch đồng nhất**: Cả 3 arm vận hành với chế độ `planner_mode="rules_only"`, đảm bảo cấu trúc phân rã công việc (plan) hoàn toàn tất định và giống hệt nhau giữa 3 arm cho cùng một câu hỏi.
2. **Ngân sách token và kiểm soát dừng**: Giới hạn tối đa 3.000.000 tokens cho toàn bộ lượt chạy, dừng khẩn cấp nếu vượt ngưỡng.
3. **Mẫu số bất biến**: Mọi lượt chạy thất bại hoặc bị từ chối đều được lưu vết đầy đủ trong trace và tính vào mẫu số đánh giá tỷ lệ thành công.

---

## 2. Bảng Tổng Hợp Kết Quả Giữa Các Arm

| Chỉ số Đánh giá | Arm A (Single-Agent) | Arm B (Phân tầng - Không phản biện) | Arm C (Phân tầng - Có phản biện) |
|---|:---:|:---:|:---:|
| **Số lượt chạy** | 1 | 1 | 1 |
| **Tỷ lệ thành công thức nghiệm** | 100.0% | 100.0% | 100.0% |
| **Tính đúng số (Numeric Correctness)** | 0.0% | 0.0% | 0.0% |
| **Truy vết nguồn (Traceability)** | 100.0% | 100.0% | 100.0% |
| **Độ phủ chỉ tiêu (Coverage)** | 50.0% | 50.0% | 50.0% |
| **Tỷ lệ câu bị loại (Discard Rate)** | 0.0% | 0.0% | 0.0% |
| **Số liên kết tầng phát hiện** | 1.00 | 1.00 | 1.00 |
| **Thời gian thực thi trung bình (ms)** | 1875 | 1469 | 1421 |
| **Số lần gọi mô hình (Calls)** | 0.0 | 0.0 | 0.0 |
| **Tổng Tokens tiêu thụ** | 0 | 0 | 0 |
| **Số vòng sửa đổi (Revisions)** | 0.0 | 0.0 | 0.0 |

---

## 3. Phân Tích Chênh Lệch Theo Cặp (Pairwise Differences)

Khoảng tin cậy 95% được ước tính qua phương pháp phi tham số Bootstrap (1.000 lần lặp lại trên các cặp cùng tác vụ và lần lặp). Do quy mô mẫu thực nghiệm có giới hạn, các phân tích này mang tính khám phá (exploratory).


### Chênh lệch cặp: C - B

| Chỉ số | Chênh lệch trung bình | 95% Bootstrap CI | Ghi chú |
|---|:---:|:---:|:---:|
| Tỷ lệ thành công thức nghiệm | +0.0000 | [+0.0000, +0.0000] | Khám phá |
| Tính đúng số | +0.0000 | [+0.0000, +0.0000] | Khám phá |
| Độ phủ chỉ tiêu | +0.0000 | [+0.0000, +0.0000] | Khám phá |
| Truy vết observation | +0.0000 | [+0.0000, +0.0000] | Khám phá |
| Tỷ lệ câu bị loại | +0.0000 | [+0.0000, +0.0000] | Khám phá |
| Số liên kết tầng | +0.0000 | [+0.0000, +0.0000] | Khám phá |
| Tổng token tiêu thụ | +0.0000 | [+0.0000, +0.0000] | Khám phá |
| Thời gian xử lý (ms) | -48.0000 | [-48.0000, -48.0000] | Khám phá |

### Chênh lệch cặp: B - A

| Chỉ số | Chênh lệch trung bình | 95% Bootstrap CI | Ghi chú |
|---|:---:|:---:|:---:|
| Tỷ lệ thành công thức nghiệm | +0.0000 | [+0.0000, +0.0000] | Khám phá |
| Tính đúng số | +0.0000 | [+0.0000, +0.0000] | Khám phá |
| Độ phủ chỉ tiêu | +0.0000 | [+0.0000, +0.0000] | Khám phá |
| Truy vết observation | +0.0000 | [+0.0000, +0.0000] | Khám phá |
| Tỷ lệ câu bị loại | +0.0000 | [+0.0000, +0.0000] | Khám phá |
| Số liên kết tầng | +0.0000 | [+0.0000, +0.0000] | Khám phá |
| Tổng token tiêu thụ | +0.0000 | [+0.0000, +0.0000] | Khám phá |
| Thời gian xử lý (ms) | -406.0000 | [-406.0000, -406.0000] | Khám phá |

### Chênh lệch cặp: C - A

| Chỉ số | Chênh lệch trung bình | 95% Bootstrap CI | Ghi chú |
|---|:---:|:---:|:---:|
| Tỷ lệ thành công thức nghiệm | +0.0000 | [+0.0000, +0.0000] | Khám phá |
| Tính đúng số | +0.0000 | [+0.0000, +0.0000] | Khám phá |
| Độ phủ chỉ tiêu | +0.0000 | [+0.0000, +0.0000] | Khám phá |
| Truy vết observation | +0.0000 | [+0.0000, +0.0000] | Khám phá |
| Tỷ lệ câu bị loại | +0.0000 | [+0.0000, +0.0000] | Khám phá |
| Số liên kết tầng | +0.0000 | [+0.0000, +0.0000] | Khám phá |
| Tổng token tiêu thụ | +0.0000 | [+0.0000, +0.0000] | Khám phá |
| Thời gian xử lý (ms) | -454.0000 | [-454.0000, -454.0000] | Khám phá |

---

## 4. Các Biểu Đồ Minh Họa Phục Vụ Chương 5

Các đồ thị phân tích đã được xuất tại thư mục `experiments/er8/analysis/`:

1. **Tỷ lệ hoàn thành & Tính đúng số giữa các arm**: `figure_er8_completion_accuracy.png`
2. **Chi phí tokens & Thời gian thực thi**: `figure_er8_cost_latency.png`
3. **So sánh chênh lệch cặp với khoảng tin cậy Bootstrap**: `figure_er8_pairwise_diff.png`

---

## 5. Hạn Chế Của Đợt Đánh Giá

1. **Chấm điểm tất định**: Phiên bản này ưu tiên tính khách quan, đo lường tự động trên bằng chứng số liệu và bộ kiểm chứng câu; chưa bao gồm gói chấm mù định tính từ chuyên gia con người.
2. **Quy mô tập tác vụ**: Gồm 12 câu hỏi tiêu biểu đại diện cho 5 loại hình câu hỏi chính (hồ sơ, xu hướng, xếp hạng, đối đầu, thiếu dữ liệu/từ chối).
3. **Lập kế hoạch tất định**: Chế độ `planner_mode="rules_only"` giúp đảm bảo tính tương đương giữa các arm nhưng làm giảm bớt tính tự do thích ứng của mô hình ngôn ngữ lớn ở tầng lập kế hoạch.
