## 4.7. Minh họa sản phẩm theo luồng sử dụng

Mục này đi qua sản phẩm theo đúng thứ tự một chuyên viên phân tích sử dụng nó: xem dữ liệu đang có, đặt câu hỏi, theo dõi các tác tử làm việc, đọc báo cáo, kiểm tra lại quá trình phân tích và mở lại báo cáo cũ. Toàn bộ ảnh được chụp từ phiên bản đang vận hành tại https://fin-ai.eddiephung.me, dùng bộ dữ liệu vận hành mười ngân hàng từ quý 1/2024 đến quý 2/2026 (mục 3.2.5) và mô hình ngôn ngữ thật.

### 4.7.1. Xem dữ liệu hiện có

Trước khi hỏi, người dùng có thể mở trang Dữ liệu để biết hệ thống đang có những ngân hàng, kỳ và chỉ tiêu nào. Bảng độ phủ cho thấy từng ngân hàng ở từng quý có đủ số liệu hay không; các ô chưa có báo cáo được đánh dấu rõ thay vì bị điền ước tính. Thông tin trên trang được lấy trực tiếp từ máy chủ, nên luôn khớp với bộ dữ liệu mà hệ thống thực sự dùng để phân tích.

![](docs/thesis-v2/screenshots/01-du-lieu.png)

Hình 4.5: Trang Dữ liệu – bảng độ phủ mười ngân hàng theo từng quý

### 4.7.2. Đặt câu hỏi

Màn hình chính chỉ có một ô nhập câu hỏi bằng tiếng Việt tự nhiên, kèm dòng tóm tắt dữ liệu hiện có và năm câu hỏi gợi ý tương ứng với năm dạng câu hỏi. Người dùng không cần chọn ngân hàng, kỳ hay chỉ tiêu từ danh sách; hệ thống tự nhận ra các thông tin này từ câu hỏi.

![](docs/thesis-v2/screenshots/02-man-hoi.png)

Hình 4.6: Màn hình đặt câu hỏi với các câu hỏi gợi ý

### 4.7.3. Theo dõi các tác tử làm việc

Sau khi gửi câu hỏi, người dùng thấy ngay điều phối viên xác định dạng câu hỏi và giao việc cho các chuyên viên (doanh nghiệp, nhóm ngành). Mỗi thẻ cho biết chuyên viên đang làm gì và đã trả về bao nhiêu số liệu có nguồn. Bên dưới là dòng thời gian các bước, cập nhật trực tiếp trong lúc hệ thống chạy, nhờ đó người dùng không phải chờ trong im lặng.

![](docs/thesis-v2/screenshots/03-dieu-phoi.png)

Hình 4.7: Màn hình điều phối – các tác tử nhận việc và trả kết quả theo thời gian thực

### 4.7.4. Đọc báo cáo

Khi hoàn tất, hệ thống mở báo cáo được trình bày theo phong cách báo cáo phân tích đầu tư. Phần đầu gồm tiêu đề nêu kết luận chính, trạng thái kiểm định và phạm vi dữ liệu. Mỗi câu nhận định có số chú thích nhỏ dẫn tới tài liệu gốc (báo cáo tài chính của ngân hàng, kèm số trang). Cột bên phải tóm tắt tín hiệu so với nhóm theo từng khía cạnh.

![](docs/thesis-v2/screenshots/04-bao-cao-ho-so.png)

Hình 4.8: Báo cáo hồ sơ doanh nghiệp của ACB – tiêu đề, nhận định và tín hiệu so với nhóm

Phần thân báo cáo kết hợp nhận định với biểu đồ. Với câu hỏi về sức khỏe tài chính, hệ thống dùng bảng màu thứ hạng giữa các ngân hàng trong nhóm, biểu đồ tương quan giữa nợ xấu và bao phủ nợ xấu, và các biểu đồ nhỏ theo từng quý. Các phát hiện đáng chú ý giữa các cấp (ví dụ sinh lời trên nhóm nhưng đệm dự phòng dưới nhóm) được đặt trong khối lưu ý riêng.

![](docs/thesis-v2/screenshots/05-bao-cao-bieu-do.png)

Hình 4.9: Biểu đồ và khối lưu ý trong báo cáo hồ sơ doanh nghiệp

### 4.7.5. Kiểm tra lại quá trình phân tích

Ở cuối báo cáo, liên kết "Xem quá trình phân tích" mở toàn bộ các bước mà hệ thống đã thực hiện: điều phối viên giao việc gì, mỗi chuyên viên trả về gì, bộ kiểm tra số liệu xác nhận bao nhiêu con số khớp dữ liệu gốc, và bộ phản biện yêu cầu sửa những gì. Người dùng có thể lọc theo từng tác tử và mở chi tiết từng bước. Tính năng này giúp người đọc tự đánh giá mức độ tin cậy của báo cáo thay vì phải tin vào kết quả cuối cùng.

![](docs/thesis-v2/screenshots/06-qua-trinh.png)

Hình 4.10: Màn hình quá trình phân tích – các bước của từng tác tử, kết quả kiểm tra số liệu và yêu cầu của bộ phản biện

### 4.7.6. Báo cáo thay đổi theo dạng câu hỏi

Báo cáo không dùng một khuôn cố định. Với câu hỏi tra cứu một con số, hệ thống trả về thẻ trả lời ngắn gồm con số chính, diễn biến so với quý trước và nguồn.

![](docs/thesis-v2/screenshots/07-tra-cuu.png)

Hình 4.11: Thẻ trả lời cho câu hỏi tra cứu "Tỷ lệ nợ xấu của VCB quý 4/2024 là bao nhiêu?"

Với câu hỏi về xu hướng, báo cáo tập trung vào biểu đồ đường theo quý và so sánh diễn biến của ngân hàng với trung vị nhóm.

![](docs/thesis-v2/screenshots/08-xu-huong.png)

Hình 4.12: Báo cáo xu hướng ROE của VPB năm 2024

Với câu hỏi so sánh hai ngân hàng, báo cáo dùng bảng đối chiếu từng chỉ tiêu, đánh dấu bên tốt hơn theo đúng chiều của chỉ tiêu (với nợ xấu, thấp hơn là tốt hơn).

![](docs/thesis-v2/screenshots/09-so-sanh.png)

Hình 4.13: Báo cáo so sánh ACB và TCB quý 4/2024

Với câu hỏi xếp hạng, báo cáo dùng biểu đồ thanh xếp theo thứ tự, có đường trung vị nhóm để người đọc thấy ngay khoảng cách giữa các ngân hàng.

![](docs/thesis-v2/screenshots/10-xep-hang.png)

Hình 4.14: Báo cáo xếp hạng cho câu hỏi "Ngân hàng nào có tỷ lệ bao phủ nợ xấu cao nhất quý 4/2024?"

### 4.7.7. Khi câu hỏi nằm ngoài phạm vi dữ liệu

Nếu người dùng hỏi về một ngân hàng hoặc một kỳ chưa có trong dữ liệu đã kiểm chứng, hệ thống từ chối ngay, trước khi gọi mô hình ngôn ngữ, và giải thích bằng tiếng Việt kèm danh sách dữ liệu đang có. Hệ thống không cố trả lời bằng thông tin không được kiểm chứng.

![](docs/thesis-v2/screenshots/11-tu-choi.png)

Hình 4.15: Thông báo khi câu hỏi về một ngân hàng chưa có trong bộ dữ liệu

### 4.7.8. Mở lại báo cáo cũ

Mọi lượt phân tích, kể cả lượt bị từ chối, đều được lưu lại. Trang Thư viện báo cáo cho phép mở lại báo cáo và quá trình phân tích của các lần hỏi trước.

![](docs/thesis-v2/screenshots/12-thu-vien.png)

Hình 4.16: Thư viện báo cáo
