# PHỤ LỤC

## Phụ lục A. Sản phẩm trực tuyến

Địa chỉ: https://fin-ai.eddiephung.me

Tên đăng nhập: [ĐIỀN]

Mật khẩu: [ĐIỀN]

Tài khoản này chỉ dùng cho bản trình bày của khóa luận.

*Bảng A.1: Các thao tác thử nhanh.*

| Thao tác | Cách làm | Kết quả mong đợi |
|---|---|---|
| Tra cứu một con số | Nhập "Tỷ lệ nợ xấu của ACB quý 2/2026 là bao nhiêu?" | Thẻ trả lời kèm số trang báo cáo gốc |
| Xếp hạng | Nhập "Ngân hàng nào có tỷ lệ bao phủ nợ xấu cao nhất quý 2/2026?" | Báo cáo xếp hạng mười ngân hàng |
| Xu hướng | Nhập "ROE của BID thay đổi thế nào trong năm 2026?" | Biểu đồ theo quý so với trung vị nhóm |
| So sánh | Nhập "So sánh ACB và CTG quý 2/2026" | Bảng đối chiếu từng chỉ tiêu |
| Từ chối | Nhập câu hỏi về ngân hàng hoặc kỳ chưa có, hoặc yêu cầu không phải phân tích | Thông báo kèm dữ liệu hiện có |
| Thêm ngân hàng | Trang Dữ liệu, chọn "Mẫu VIB 2025 hợp lệ", bấm "Kiểm tra và tải lên", rồi "Hỏi về VIB" | Báo cáo có ghi chú số liệu do người dùng cung cấp |

## Phụ lục B. Bộ dữ liệu

Bộ dữ liệu vận hành mười ngân hàng niêm yết lớn nhất (ACB, BID, CTG, HDB, MBB, SHB, STB, TCB, VCB, VPB), mười quý từ
quý 1/2024 đến quý 2/2026. Số liệu đầu vào được đọc từ báo cáo tài chính hợp nhất của từng ngân hàng; mỗi dòng ghi trang nguồn và
đường dẫn tới tệp báo cáo gốc. Bốn chỉ tiêu (tỷ lệ nợ xấu, tỷ lệ bao phủ nợ xấu, ROA, ROE) được tính lại từ
các số liệu này theo công thức được định danh phiên bản, cho 400 giá trị.

Để đối chiếu với Chương 5: các thực nghiệm so sánh A/B/C chạy trên một bản dựng trước của bộ dữ liệu; bản dựng cuối cùng chỉ khác ở nhãn đọc của các dòng lợi nhuận STB và không đổi giá trị nào.

## Phụ lục C. Mã nguồn và kết quả thực nghiệm

Mã nguồn nằm trong một kho riêng tư và được cung cấp theo yêu cầu. Kết quả của các thực nghiệm được lưu cùng mã nguồn dưới dạng tệp do chương trình ghi lại; Bảng C.1 liệt kê nội dung từng nhóm.

*Bảng C.1: Kết quả thực nghiệm được lưu.*

| Thực nghiệm | Nội dung |
|---|---|
| Thực nghiệm chính (ba cấu hình) | 36 lượt chạy, điểm chấm, biểu đồ |
| Độ nhạy của bộ kiểm chứng | 1.210 câu đột biến, kết quả theo loại lỗi |
| So sánh mô hình | Ba mô hình OpenAI; ba lần chạy lặp của `gpt-5.6-luna` |
| Kiểm tra đối kháng | Trước và sau khi thêm cổng phạm vi |
| Số hóa từ báo cáo gốc | Mã đo và kết quả |
| Chỉ mục kết quả | Bảng số liệu, lệnh chạy lại và phiên bản mã nguồn của từng thực nghiệm |
