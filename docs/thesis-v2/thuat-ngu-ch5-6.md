# Thuật ngữ đã lược ở Chương 5 và Chương 6

| Thuật ngữ gốc | Xuất hiện ở mục | Giải thích dễ hiểu | Diễn đạt đã dùng trong bài | Gợi ý |
|---|---|---|---|---|
| Snapshot Gold v5 (`gold-bank-2025-expanded-v5-evidence`) | 5.2, 6.1 | Bản chụp cố định của bộ dữ liệu đã kiểm chứng, không thay đổi trong suốt thực nghiệm | bộ dữ liệu Gold v5 | Giữ tên "Gold v5"; tên kỹ thuật đầy đủ chỉ cần ở phụ lục |
| SHA-256 `1b1b5c09…ce73` | 5.2 | Mã kiểm tra tính toàn vẹn của tệp dữ liệu; tệp đổi một byte thì mã đổi | được khóa bằng mã kiểm tra | Phụ lục (bảng cấu hình thực nghiệm) |
| `deepseek-v4-pro-0813`, nhà cung cấp tương thích OpenAI | 5.2 | Tên phiên bản mô hình ngôn ngữ và cách gọi mô hình qua giao thức chuẩn | mô hình ngôn ngữ DeepSeek V4 Pro | Phụ lục; có thể nhắc tên đầy đủ một lần trong 3.3 |
| Seed 20260930 | 5.2 | Giá trị cố định để xáo trộn thứ tự chạy mà vẫn lặp lại được | xáo trộn ngẫu nhiên theo một giá trị cố định | Phụ lục |
| Token | 5.2, 5.3, 6.1 | Đơn vị đo khối lượng văn bản mô hình đọc và viết; cũng là cơ sở tính chi phí | "token (đơn vị đo khối lượng văn bản…)" ở lần đầu, sau đó "lượng văn bản mô hình phải xử lý" | Nên giữ "token" trong bảng số liệu vì là đơn vị đo chuẩn |
| `rules_only` | 5.2 | Chế độ lập kế hoạch chỉ theo luật cố định, không để mô hình đề xuất | kế hoạch phân tích được lập theo luật cố định | Bỏ khỏi bài |
| `known_limitations`, mã băm kế hoạch | 5.2 | Trường ghi chú giới hạn do hệ thống thêm sau khi chạy; mã băm dùng để so kế hoạch giữa các cấu hình | hệ thống kiểm tra lại và xác nhận kế hoạch giống hệt nhau | Phụ lục (nếu hội đồng hỏi về tính công bằng) |
| `completed` / `accepted_with_limitations` | 5.2, 5.3 | Hai trạng thái kết thúc của báo cáo: hoàn tất không ghi chú, và hoàn tất kèm ghi chú giới hạn | "hoàn thành trọn vẹn" và "trả lời được (có thể kèm ghi chú giới hạn)" | Bỏ khỏi bài |
| Bootstrap | 5.4 | Kỹ thuật ước lượng khoảng tin cậy bằng cách lấy mẫu lại nhiều lần từ chính dữ liệu | lấy mẫu lại 1.000 lần từ chính các cặp nhiệm vụ | Có thể nhắc tên "bootstrap" trong ngoặc một lần nếu hội đồng quen thống kê |
| MAJOR / MINOR (mức nghiêm trọng của phản biện) | 5.5 | Hai mức độ vấn đề do bộ phản biện gán | nghiêm trọng / mức nhẹ | Bỏ khỏi bài |
| Staging, Render | 5.1.2 | Môi trường chạy thử trên mạng và dịch vụ máy chủ đang dùng | phiên bản đang vận hành trên mạng | Chương 4 (phần triển khai) đã nêu; không cần lặp lại |
| Kiểm tra hợp đồng OpenAPI, `check_architecture_guardrails.py`, `src/thesis_data/` | 5.1.1 | Hai bước tự động kiểm tra định dạng dữ liệu trao đổi và ranh giới kiến trúc | kiểm tra định dạng dữ liệu trao đổi / phần lõi không bị gắn chặt | Phụ lục kỹ thuật |
| Stage-1 | (1.3, RQ3) | Lớp kiểm tra số liệu theo quy tắc chạy trước mọi bước đánh giá nội dung | "kiểm tra số liệu theo quy tắc" | Chương 1 (do bạn viết) còn dùng "Stage-1" trong RQ3 — nên đổi thành diễn đạt thường |
| `experiments/er8/` và tên tệp hình | 5 | Thư mục lưu kết quả thực nghiệm | "các tệp kết quả được lưu lại cùng mã nguồn" | Phụ lục (đường dẫn để tái lập) |
