## 4.5. Sản phẩm theo luồng sử dụng

Mục này đi qua sản phẩm theo thứ tự một chuyên viên phân tích sử dụng: xem dữ liệu, đặt câu hỏi, theo dõi các tác tử, đọc báo cáo, kiểm tra lại quá trình và thêm một ngân hàng mới. Các ảnh Hình 4.4, 4.6, 4.7 và 4.8 được chụp ngày 14/10/2026 từ mã nguồn giao diện hiện hành, kết nối với máy chủ phân tích đang vận hành (các báo cáo đã lưu trong Thư viện báo cáo, bộ dữ liệu mười ngân hàng, mô hình ngôn ngữ thật); các ảnh còn lại được chụp từ bản vận hành ngày 02/10/2026 và chưa chụp lại.

**Xem dữ liệu.** Trang Dữ liệu cho biết hệ thống có những ngân hàng, kỳ và chỉ tiêu nào. Bảng độ phủ cho thấy từng ngân hàng ở từng quý có đủ số liệu hay không (hiện đủ 100/100 ô); nếu một quý chưa có báo cáo, ô đó được đánh dấu thay vì điền ước tính. Bên dưới là định nghĩa, công thức của từng chỉ tiêu và khu vực tải lên ngân hàng mới. Thông tin được lấy trực tiếp từ máy chủ nên luôn khớp với dữ liệu thực sự dùng để phân tích.

![](docs/thesis-v2/screenshots/01-du-lieu.png)

Hình 4.4: Trang Dữ liệu – độ phủ mười ngân hàng theo từng quý

**Đặt câu hỏi và theo dõi tác tử.** Màn hình chính chỉ có một ô nhập câu hỏi tiếng Việt cùng các câu hỏi gợi ý; người dùng không cần chọn ngân hàng, kỳ hay chỉ tiêu từ danh sách. Sau khi gửi, người dùng thấy điều phối viên xác định dạng câu hỏi và giao việc cho các chuyên viên; chỉ những tác tử thực sự tham gia mới hiện ra. Mỗi thẻ cho biết chuyên viên đang làm gì và đã trả về bao nhiêu số liệu có nguồn, và dòng thời gian các bước cập nhật trực tiếp trong lúc hệ thống chạy.

![](docs/thesis-v2/screenshots/03-dieu-phoi.png)

Hình 4.5: Màn hình điều phối – các tác tử nhận việc và trả kết quả theo thời gian thực

**Đọc báo cáo.** Báo cáo trình bày theo phong cách báo cáo phân tích đầu tư: tiêu đề nêu kết luận, trạng thái kiểm định và phạm vi dữ liệu, rồi các nhận định kèm biểu đồ. Mỗi câu có số chú thích dẫn tới báo cáo tài chính gốc kèm số trang; câu dựa trên nhiều nguồn hiện ba số đầu và gộp phần còn lại thành "+N", danh sách đầy đủ nằm ở mục Nguồn. Khối tín hiệu tóm tắt vị thế so với nhóm theo từng khía cạnh, và các phát hiện liên tầng được đặt trong khối lưu ý riêng. Dòng "Thị trường" dưới các chỉ số chính đưa giá đóng cửa và hệ số P/B vào báo cáo như một bối cảnh tham khảo, có ghi nguồn và phiên giao dịch, tách khỏi số liệu báo cáo tài chính.

![](docs/thesis-v2/screenshots/04-bao-cao-ho-so.png)

Hình 4.6: Báo cáo hồ sơ doanh nghiệp của ACB quý 2/2026

Cách trình bày thay đổi theo dạng câu hỏi: câu tra cứu nhận thẻ trả lời ngắn gồm con số, diễn biến so với quý trước và nguồn; câu xu hướng dùng biểu đồ đường theo quý so với trung vị nhóm; câu xếp hạng dùng biểu đồ thanh có đường trung vị; câu so sánh hai ngân hàng dùng bảng đối chiếu từng chỉ tiêu, đánh dấu bên tốt hơn theo đúng chiều của chỉ tiêu (Hình 4.7).

![](docs/thesis-v2/screenshots/09-so-sanh.png)

Hình 4.7: Báo cáo so sánh trực diện ACB và TCB

**Kiểm tra lại quá trình.** Liên kết "Xem quá trình phân tích" ở cuối báo cáo mở toàn bộ các bước: điều phối viên giao việc gì, mỗi chuyên viên trả về gì, bộ kiểm tra xác nhận bao nhiêu con số khớp dữ liệu gốc và bộ phản biện yêu cầu sửa gì. Người đọc nhờ đó tự đánh giá mức tin cậy của báo cáo thay vì chỉ tin vào kết quả cuối. Mọi lượt phân tích, kể cả lượt bị từ chối, được lưu trong Thư viện báo cáo để mở lại sau.

![](docs/thesis-v2/screenshots/06-qua-trinh.png)

Hình 4.8: Quá trình phân tích – các bước của từng tác tử, kết quả kiểm tra số liệu và yêu cầu của bộ phản biện

**Câu hỏi ngoài phạm vi.** Khi người dùng hỏi về ngân hàng hoặc kỳ chưa có trong dữ liệu, hệ thống từ chối ngay, trước khi gọi mô hình ngôn ngữ, và nêu dữ liệu đang có.

![](docs/thesis-v2/screenshots/11-tu-choi.png)

Hình 4.9: Thông báo khi câu hỏi về một ngân hàng chưa có trong dữ liệu

**Thêm ngân hàng mới.** Trên trang Dữ liệu, người dùng chọn tệp CSV và bấm "Kiểm tra và tải lên". Hệ thống kiểm tra cấu trúc và vị trí nguồn của từng dòng, tự tính lại bốn chỉ tiêu rồi đối chiếu với giá trị người dùng khai (Hình 4.10, tệp mẫu của VIB quý 4/2025: cả bốn chỉ tiêu khớp). Tệp có dòng thiếu vị trí nguồn, sai đơn vị, tỷ lệ khai lệch, hoặc của một ngân hàng đã có sẵn đều bị từ chối kèm dòng sai.

![](docs/thesis-v2/screenshots/13-tai-len.png)

Hình 4.10: Kết quả kiểm tra tệp tải lên của VIB quý 4/2025

Sau khi tệp được chấp nhận, người dùng hỏi về ngân hàng mới như các ngân hàng khác. Báo cáo ở Hình 4.11 đặt VIB cạnh nhóm mười ngân hàng: thứ hạng tính trên mười một ngân hàng (ví dụ hạng 11/11 về bao phủ nợ xấu), còn trung vị nhóm vẫn chỉ tính trên mười ngân hàng đã đối soát, và dải thông báo đầu báo cáo ghi rõ số liệu của VIB do người dùng cung cấp.

![](docs/thesis-v2/screenshots/14-bao-cao-vib.png)

Hình 4.11: Báo cáo về ngân hàng do người dùng tải lên (VIB quý 4/2025)
