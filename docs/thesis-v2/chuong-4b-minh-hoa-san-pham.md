## 4.5. Sản phẩm theo luồng sử dụng

Mục này mô tả các bước dùng thử của một người phân tích điển hình trong nhóm chân dung thứ nhất ở Bảng 1.1, đi qua sản phẩm theo thứ tự: xem dữ liệu, đặt câu hỏi, theo dõi các tác tử, đọc báo cáo, kiểm tra lại quá trình và thêm một ngân hàng mới. Các ảnh được chụp ngày 14–15/10/2026 từ bản vận hành tại https://fin-ai.eddiephung.me hoặc từ mã nguồn giao diện hiện hành kết nối với máy chủ đang vận hành, mở lại các báo cáo đã lưu.

**Xem dữ liệu.** Trang Dữ liệu cho biết hệ thống có những ngân hàng, kỳ và chỉ tiêu nào; bảng độ phủ cho thấy từng ngân hàng ở từng quý có đủ số liệu hay không (hiện đủ 100/100 ô), và ô chưa có báo cáo được đánh dấu thay vì điền ước tính. Bên dưới là định nghĩa, công thức từng chỉ tiêu và khu vực tải lên ngân hàng mới.

![](docs/thesis-v2/screenshots/01-du-lieu.png)

Hình 4.4: Trang Dữ liệu – độ phủ mười ngân hàng theo từng quý

Hình 4.4 minh họa yêu cầu FR2 (mỗi giá trị truy được tới nguồn) và NFR1 (số do mã tính); kiểm chứng ở mục 5.3 và 5.10.

**Đặt câu hỏi và theo dõi tác tử.** Màn hình chính chỉ có một ô nhập câu hỏi tiếng Việt cùng các câu hỏi gợi ý; người dùng không cần chọn ngân hàng, kỳ hay chỉ tiêu. Sau khi gửi, người dùng thấy điều phối viên nêu cách hiểu câu hỏi và kế hoạch, giao việc cho các chuyên viên (chỉ những tác tử thực sự tham gia mới hiện ra), bản nháp nhận định chảy ra từng đoạn, bộ kiểm tra xác nhận bao nhiêu số khớp, và bộ phản biện nêu yêu cầu sửa nếu có; nội dung là các kết quả có cấu trúc mà từng tác tử công bố, không phải suy nghĩ thô của mô hình.

![](docs/thesis-v2/screenshots/03-dieu-phoi.png)

Hình 4.5: Dòng suy luận – các tác tử nhận việc, trả kết quả và kiểm tra lẫn nhau theo thời gian thực

Hình 4.5 minh họa yêu cầu FR4 (chỉ huy động tác tử cần thiết) và NFR2 (mọi câu qua kiểm tra); kiểm chứng ở mục 5.6 và 5.7.

**Đọc báo cáo.** Báo cáo trình bày theo phong cách báo cáo phân tích đầu tư: tiêu đề nêu kết luận, trạng thái kiểm định và phạm vi dữ liệu, rồi các nhận định kèm biểu đồ. Mỗi câu có số chú thích dẫn tới báo cáo tài chính gốc kèm số trang; khối tín hiệu tóm tắt vị thế so với nhóm và các phát hiện liên tầng nằm trong khối lưu ý riêng; dòng "Thị trường" (giá đóng cửa, P/B) là bối cảnh tham khảo, có ghi nguồn và tách khỏi số liệu báo cáo tài chính.

![](docs/thesis-v2/screenshots/04-bao-cao-ho-so.png)

Hình 4.6: Báo cáo hồ sơ doanh nghiệp của ACB quý 2/2026

Hình 4.6 minh họa yêu cầu FR4 (báo cáo đổi hình dạng theo dạng câu hỏi) và FR2; kiểm chứng ở mục 5.6 và 5.3.

![](docs/thesis-v2/screenshots/09-so-sanh.png)

Hình 4.7: Báo cáo so sánh trực diện ACB và TCB

Hình 4.7 minh họa yêu cầu FR4 về so sánh trực diện theo chiều tốt của chỉ tiêu; kiểm chứng ở mục 5.6.

**Kiểm tra lại quá trình.** Liên kết "Xem quá trình phân tích" ở cuối báo cáo mở toàn bộ các bước (điều phối viên giao việc gì, chuyên viên trả về gì, bộ kiểm tra xác nhận bao nhiêu số khớp, bộ phản biện yêu cầu sửa gì), để người đọc tự đánh giá mức tin cậy; mọi lượt phân tích, kể cả lượt bị từ chối, được lưu trong Thư viện báo cáo.

![](docs/thesis-v2/screenshots/06-qua-trinh.png)

Hình 4.8: Quá trình phân tích – các bước của từng tác tử, kết quả kiểm tra số liệu và yêu cầu của bộ phản biện

Hình 4.8 minh họa yêu cầu NFR2 (kiểm từng câu theo quy tắc) và khả năng lưu vết; kiểm chứng ở mục 5.7.

**Câu hỏi ngoài phạm vi.** Khi câu hỏi về ngân hàng hoặc kỳ chưa có dữ liệu, hoặc không phải phân tích ngân hàng, hệ thống từ chối trước khi gọi mô hình, nêu dữ liệu đang có và gợi ý câu hỏi có thể hỏi.

![](docs/thesis-v2/screenshots/11-tu-choi.png)

Hình 4.9: Thông báo khi câu hỏi nằm ngoài phạm vi (yêu cầu sáng tác thơ về thị trường ngân hàng)

Hình 4.9 minh họa yêu cầu FR3 (từ chối câu hỏi ngoài phạm vi); kiểm chứng ở mục 5.9.

**Thêm ngân hàng mới.** Trên trang Dữ liệu, người dùng chọn tệp CSV và bấm "Kiểm tra và tải lên". Hệ thống kiểm tra cấu trúc và vị trí nguồn của từng dòng, tự tính lại bốn chỉ tiêu rồi đối chiếu với giá trị người dùng khai (Hình 4.10, tệp mẫu của VIB quý 4/2025: cả bốn chỉ tiêu khớp). Tệp có dòng thiếu vị trí nguồn, sai đơn vị, tỷ lệ khai lệch, hoặc của một ngân hàng đã có sẵn đều bị từ chối kèm dòng sai.

![](docs/thesis-v2/screenshots/13-tai-len.png)

Hình 4.10: Kết quả kiểm tra tệp tải lên của VIB quý 4/2025

Hình 4.10 minh họa yêu cầu FR5 (thêm ngân hàng mới có kiểm tra); kiểm chứng ở mục 5.1 và 5.10, mới thử một ngân hàng mẫu.

Sau khi tệp được chấp nhận, báo cáo ở Hình 4.11 (tỷ lệ nợ xấu của VIB) đặt VIB cạnh nhóm mười ngân hàng: thứ hạng tính trên mười một ngân hàng (hạng 9/11), trung vị nhóm vẫn chỉ tính trên mười ngân hàng đã đối soát, và dải thông báo ghi rõ số liệu do người dùng cung cấp.

![](docs/thesis-v2/screenshots/14-bao-cao-vib.png)

Hình 4.11: Báo cáo về ngân hàng do người dùng tải lên (VIB quý 4/2025)

Hình 4.11 minh họa yêu cầu FR5 và FR2 với dữ liệu do người dùng cung cấp được gắn nhãn riêng; kiểm chứng ở mục 5.1.
