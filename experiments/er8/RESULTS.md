# Báo cáo Đánh giá Thực nghiệm A/B/C (ER-8)

Tài liệu này tổng hợp kết quả chạy thử nghiệm A/B/C trên bộ dữ liệu kiểm chứng Gold v5 (`gold-bank-2025-expanded-v5-evidence`), phục vụ phân tích thực nghiệm tại **Chương 5** của khóa luận tốt nghiệp.

> **Nguồn dữ liệu:** Chạy thật với mô hình `deepseek-v4-pro-0813` ngày 2026-09-30, seed 20260930, 1 lần lặp, tổng 474265 token. Kế hoạch dùng chung giữa 3 arm được kiểm bằng hash (bỏ trường known_limitations do runtime cộng thêm sau khi chạy).

---

## 1. Thiết kế Thí nghiệm và Các Nhánh So Sánh (Arms)

Thực nghiệm so sánh 3 kiến trúc xử lý trên cùng một câu hỏi và cùng một ảnh chụp dữ liệu (ER-8):

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
| **Số lượt chạy** | 12 | 12 | 12 |
| **Trả lời được (completed + có giới hạn)** | 83.3% | 83.3% | 83.3% |
| **Hoàn thành sạch (không giới hạn)** | 75.0% | 75.0% | 0.0% |
| **Tỷ lệ thành công thức nghiệm** | 100.0% | 100.0% | 100.0% |
| **Tính đúng số (Numeric Correctness)** | 100.0% | 96.5% | 100.0% |
| **Truy vết nguồn (Traceability)** | 100.0% | 100.0% | 100.0% |
| **Độ phủ chỉ tiêu (Coverage)** | 70.8% | 81.8% | 81.2% |
| **Tỷ lệ câu bị loại (Discard Rate)** | 15.4% | 20.7% | 33.4% |
| **Tỷ lệ fallback bố cục (Composition Fallback)** | 10.0% | 10.0% | 10.0% |
| **Số liên kết tầng phát hiện** | 0.33 | 0.42 | 0.58 |
| **Thời gian thực thi trung bình (ms)** | 15670 | 32521 | 83142 |
| **Số lần gọi mô hình (Calls)** | 0.8 | 2.1 | 5.1 |
| **Tổng Tokens tiêu thụ** | 3950 | 8534 | 27038 |
| **Số vòng sửa đổi (Revisions)** | 0.0 | 0.0 | 1.5 |

---

## 3. Phân Tích Chênh Lệch Theo Cặp (Pairwise Differences)

Khoảng tin cậy 95% được ước tính qua phương pháp phi tham số Bootstrap (1.000 lần lặp lại trên các cặp cùng tác vụ và lần lặp). Do quy mô mẫu thực nghiệm có giới hạn, các phân tích này mang tính khám phá (exploratory).


### Chênh lệch cặp: C - B

| Chỉ số | Chênh lệch trung bình | 95% Bootstrap CI | Ghi chú |
|---|:---:|:---:|:---:|
| Tỷ lệ thành công thức nghiệm | +0.0000 | [+0.0000, +0.0000] | Khám phá |
| Tính đúng số | +0.0353 | [+0.0000, +0.0985] | Khám phá |
| Độ phủ chỉ tiêu | -0.0052 | [-0.0885, +0.0625] | Khám phá |
| Truy vết observation | +0.0000 | [+0.0000, +0.0000] | Khám phá |
| Tỷ lệ câu bị loại | +0.1263 | [+0.0271, +0.2511] | Khám phá |
| Tỷ lệ fallback bố cục | +0.0000 | [+0.0000, +0.0000] | Khám phá |
| Số liên kết tầng | +0.1667 | [-0.3333, +0.9167] | Khám phá |
| Tổng token tiêu thụ | +18504.5000 | [+11293.0000, +25572.3333] | Khám phá |
| Thời gian xử lý (ms) | +50621.0833 | [+33510.4167, +67558.6667] | Khám phá |

### Chênh lệch cặp: B - A

| Chỉ số | Chênh lệch trung bình | 95% Bootstrap CI | Ghi chú |
|---|:---:|:---:|:---:|
| Tỷ lệ thành công thức nghiệm | +0.0000 | [+0.0000, +0.0000] | Khám phá |
| Tính đúng số | -0.0353 | [-0.0985, +0.0000] | Khám phá |
| Độ phủ chỉ tiêu | +0.1094 | [-0.0104, +0.2396] | Khám phá |
| Truy vết observation | +0.0000 | [+0.0000, +0.0000] | Khám phá |
| Tỷ lệ câu bị loại | +0.0533 | [-0.0174, +0.1303] | Khám phá |
| Tỷ lệ fallback bố cục | +0.0000 | [-0.3000, +0.3000] | Khám phá |
| Số liên kết tầng | +0.0833 | [+0.0000, +0.2500] | Khám phá |
| Tổng token tiêu thụ | +4583.1667 | [+2450.8333, +6786.8333] | Khám phá |
| Thời gian xử lý (ms) | +16850.5833 | [+9265.5833, +24147.7500] | Khám phá |

### Chênh lệch cặp: C - A

| Chỉ số | Chênh lệch trung bình | 95% Bootstrap CI | Ghi chú |
|---|:---:|:---:|:---:|
| Tỷ lệ thành công thức nghiệm | +0.0000 | [+0.0000, +0.0000] | Khám phá |
| Tính đúng số | +0.0000 | [+0.0000, +0.0000] | Khám phá |
| Độ phủ chỉ tiêu | +0.1042 | [+0.0000, +0.2292] | Khám phá |
| Truy vết observation | +0.0000 | [+0.0000, +0.0000] | Khám phá |
| Tỷ lệ câu bị loại | +0.1797 | [+0.0367, +0.3342] | Khám phá |
| Tỷ lệ fallback bố cục | +0.0000 | [-0.3000, +0.3000] | Khám phá |
| Số liên kết tầng | +0.2500 | [-0.2500, +1.0000] | Khám phá |
| Tổng token tiêu thụ | +23087.6667 | [+14324.9167, +31716.4167] | Khám phá |
| Thời gian xử lý (ms) | +67471.6667 | [+45307.2500, +86965.5833] | Khám phá |

---

## 4. Các Biểu Đồ Minh Họa Phục Vụ Chương 5

Các đồ thị phân tích đã được xuất tại thư mục `experiments/er8/analysis`:

1. **Tỷ lệ hoàn thành & Tính đúng số giữa các arm**: `figure_er8_completion_accuracy.png`
2. **Chi phí tokens & Thời gian thực thi**: `figure_er8_cost_latency.png`
3. **So sánh chênh lệch cặp với khoảng tin cậy Bootstrap**: `figure_er8_pairwise_diff.png`

---

## 5. Hạn Chế Của Đợt Đánh Giá

1. **Chấm điểm tất định**: Phiên bản này ưu tiên tính khách quan, đo lường tự động trên bằng chứng số liệu và bộ kiểm chứng câu; chưa bao gồm gói chấm mù định tính từ chuyên gia con người.
2. **Quy mô tập tác vụ**: Gồm 12 câu hỏi tiêu biểu đại diện cho 5 loại hình câu hỏi chính (hồ sơ, xu hướng, xếp hạng, đối đầu, từ chối ngoài phạm vi).
3. **Lập kế hoạch tất định**: Chế độ `planner_mode="rules_only"` giúp đảm bảo tính tương đương giữa các arm nhưng làm giảm bớt tính tự do thích ứng của mô hình ngôn ngữ lớn ở tầng lập kế hoạch.
