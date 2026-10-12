# Kế hoạch: final-thesis

To-do nằm ở GitHub Issues của repo này. File này chỉ giữ mục tiêu, phạm vi và các mốc. Sửa file qua PR; người dùng merge là đã duyệt.

Soạn 2026-10-13 từ AGENTS.md, handoff và trạng thái phiên trước; mục đánh dấu (đoán) cần người dùng xác nhận.

## Mục tiêu
Nộp khóa luận có sức thuyết phục về kỹ thuật tác tử (phần khung kiểm soát quanh mô hình), kèm webapp thật cho hội đồng thử: báo cáo có truy vết nguồn, xem xử lý trực tiếp, bối cảnh thị trường hiển thị riêng ngoài phân tích đã kiểm chứng.

## Phạm vi
- Làm: viết lại chương 3-6 của bản gọn thêm các thực nghiệm E1 (đột biến bộ kiểm chứng), E2 (nhiều mô hình OpenAI), E3 (red-team), E5 (đo OCR/số hóa); cổng đánh giá CI (E4); dọn sản phẩm sau đánh giá.
- Không làm: mở rộng lên 15 ngân hàng, RAG, nhập dữ liệu OCR vào snapshot phân tích khi chưa có đối soát.

## Các mốc
| Mốc | Xong khi | Issue |
| :--- | :--- | :--- |
| M1 Số liệu thực nghiệm chốt | bảng E1, E2, E3, E5 nằm trong repo, có lệnh tái chạy | (chưa tạo) |
| M2 Chương 5 | số liệu chương 5 khớp M1, ghi rõ giới hạn và phần nâng cấp sau đánh giá | (chưa tạo) |
| M3 Chương 3, 4, 6 | khớp chương 5; dựng Word, đếm trang thật bằng Word, mục tiêu 65-68 trang | (chưa tạo) |
| M4 Webapp trực tiếp | Vercel và Render phản ánh `main`; hàng giá trong báo cáo vừa tạo đã nhìn tận mắt | (chưa tạo) |

## Rủi ro và câu hỏi mở
- Mã sản phẩm hiện khác bản đã đánh giá ER-9 (SSE-1, LIN-1, MKT-1/2): chương 5 phải nêu.
- E3: ba nhánh giống nhau; câu hỏi ngoài phạm vi không bị từ chối (planner mặc định kế hoạch ngành).
- (đoán) có nên bỏ hàng DeepSeek khỏi bảng E2 để chỉ còn mô hình OpenAI.
- Người dùng còn việc: xoay khóa gateway và khóa Render, dời `env.txt` khỏi OneDrive, 4 trường `[ĐIỀN]` ở bìa, F9 trong Word, đọc lại chương 1-2.
