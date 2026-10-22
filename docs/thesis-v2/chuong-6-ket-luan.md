# CHƯƠNG 6. KẾT LUẬN, HẠN CHẾ VÀ HƯỚNG PHÁT TRIỂN

## 6.1. Kết luận

Khóa luận đã thiết kế, triển khai và đánh giá một hệ thống đa tác tử phân cấp, thích ứng theo câu hỏi, hỗ trợ tổng hợp thông tin và phân tích cơ bản mười ngân hàng niêm yết lớn nhất Việt Nam từ quý 1/2024 đến quý 2/2026. Hệ thống nhận câu hỏi tiếng Việt và khóa kế hoạch phân tích trước khi truy xuất. Mã nguồn tính các dữ kiện kèm nguồn gốc, các tác tử chuyên trách viết nhận định có trích dẫn và bộ kiểm chứng kiểm từng câu. Tùy cấu hình, báo cáo còn được phản biện và sửa đổi. Toàn bộ quá trình xem được tại https://fin-ai.eddiephung.me.

Khoảng trống mà khóa luận hướng tới (mục 1.3) là việc nối nhận định do AI viết với trang báo cáo gốc và kiểm từng câu bằng quy tắc; tài liệu giới thiệu các công cụ hiện có không nêu rõ chức năng này. Khảo sát thăm dò 15 người ở mục 1.2 phù hợp với hướng ưu tiên truy nguồn, nhưng không kiểm chứng được nhu cầu về tính thích ứng của kế hoạch.

Ba kết quả chính cần đọc cùng nhau. Lớp kiểm soát cho cùng độ khớp số và khả năng truy nguyên nguồn ở mọi cấu hình và mô hình. Lợi thế của đa tác tử phân cấp so với một tác tử chỉ xuất hiện ở DeepSeek V4 Pro. Phản biện và sửa đổi làm chi phí tăng ba đến bốn lần mà không cải thiện độ phủ. Câu trả lời cho các câu hỏi nghiên cứu vì thế phụ thuộc vào mô hình, và tính thích ứng mới được kiểm một phần.

**Câu hỏi nghiên cứu thứ nhất (thiết kế).** Hệ thống giữ được khả năng truy nguyên nhờ tách ba vai trò: mã nguồn tính mọi con số, mô hình ngôn ngữ chỉ diễn giải trên dữ kiện đã tính, và bộ kiểm chứng quyết định câu nào được vào báo cáo. Kế hoạch được khóa trước khi truy xuất và mỗi câu phải trích dẫn dữ kiện. Phần không đạt kiểm tra được thay bằng khối dựng sẵn. Cả bốn cấu hình, kể cả D không gọi mô hình, đạt 100% khớp số và truy được về số liệu gốc. Chỉ số này đo trên các câu đã qua bộ kiểm chứng nên phản ánh thiết kế, không phản ánh chất lượng mô hình viết. Sau khi thêm hai quy tắc, bộ kiểm chứng phát hiện 99,2% đột biến giả lập (trước đó là 94,1%; riêng lỗi đổi chỉ tiêu tăng từ 79,2% lên 99,2%). Hai quy tắc được thiết kế sau khi thấy kết quả, nên con số này chưa cho biết khả năng phát hiện loại lỗi khác. Các quy tắc cũng còn loại nhầm sáu dòng chú thích hình mẫu.

**Câu hỏi nghiên cứu thứ hai (B so với A).** Với DeepSeek V4 Pro, cấu hình B có độ phủ cao hơn A (0,812 so với 0,756 trên 10 câu phân tích; thắng 3, hòa 6, thua 1) và hoàn thành trọn vẹn 9/10 báo cáo so với 7/10, với lượng token tăng khoảng 2,2 lần. Trên gpt-5.6-luna, độ phủ của A, B và C đều bằng 0,912 và A hoàn thành 10/10 báo cáo với chi phí thấp nhất. Mỗi cặp chỉ chạy một lần, A và B khác nhau đồng thời ở mức chuyên môn hóa và số lượt gọi mô hình, và độ phủ của B thay đổi theo mô hình nhiều hơn chênh lệch giữa B và A. Vì thế chưa đủ cơ sở để kết luận B tốt hơn A. Hai kết quả gợi ý rằng lợi ích của chuyên môn hóa phụ thuộc vào năng lực mô hình: mô hình càng mạnh thì một tác tử đơn càng đủ dùng. Cấu hình D cho thấy mô hình bổ sung khoảng 0,12 đến 0,27 điểm độ phủ trên 10 câu, chủ yếu ở các câu cần nhiều chỉ tiêu.

**Câu hỏi nghiên cứu thứ ba (C so với B).** Ở cả hai mô hình, phản biện và tối đa hai vòng sửa đổi làm chi phí tăng ba đến bốn lần và thêm 42 đến 69 giây mỗi lượt, nhưng độ phủ không cải thiện. Chỉ 4/10 báo cáo của C trên DeepSeek V4 Pro và 2/10 trên gpt-5.6-luna hoàn thành trọn vẹn. Bộ phản biện chỉ sửa từng câu, nên yêu cầu ở mức cả báo cáo thường không được đáp ứng và câu liên quan bị loại. Kết luận này chỉ áp dụng cho bộ phản biện hiện tại và 12 câu hỏi đã dùng để hiệu chỉnh, với một lần chạy mỗi mô hình trên hai phiên bản mã nguồn.

**Khuyến nghị.** Các cấu hình được so sánh bên trong một lớp kiểm soát dùng chung, nên kết quả chỉ cho biết cách tổ chức tác tử ảnh hưởng thế nào đến độ phủ và chi phí. Trong phạm vi đó, có thể chạy mặc định bằng cấu hình rẻ (A trên mô hình mạnh, hoặc B) và chỉ dùng C khi có người xem xét kết quả. Các yêu cầu FR1, FR4, FR5 và NFR3 ở Bảng 2.1 mới được kiểm một phần (mục 3.4 và 5.14).

## 6.2. Đóng góp của khóa luận

Về thực tiễn, khóa luận xây dựng một hệ thống đã triển khai. Hệ thống gồm bộ dữ liệu mười ngân hàng × mười quý với 400 giá trị chỉ tiêu, mỗi giá trị truy được tới trang báo cáo tài chính gốc và có bản ghi phép tính. Hệ thống còn có quy trình tiếp nhận ngân hàng mới (kiểm tra nguồn, tính lại chỉ tiêu) dùng được trên giao diện web, giao diện hỏi - theo dõi quá trình - đọc báo cáo kiểu phân tích đầu tư, và bộ công cụ đánh giá có thể chạy lại.

Về phương pháp, khóa luận đề xuất cách kiểm từng câu thay vì cấm số. Mô hình được nêu số, nhưng mỗi con số, thứ hạng, kỳ, tên chỉ tiêu và chiều so sánh phải khớp dữ kiện được trích. Câu không đạt bị loại riêng, không hủy cả lượt phân tích.

Về phân tích bài toán, khóa luận đối chiếu các công cụ hiện có theo tài liệu giới thiệu sản phẩm, lập bảng yêu cầu truy vết từ người dùng tới thiết kế và kiểm chứng, và minh họa giới hạn của mô hình phổ thông khi không có lớp kiểm soát bằng số liệu thử.

Về đánh giá, khóa luận cung cấp bằng chứng định lượng về quan hệ giữa độ phức tạp kiến trúc và chi phí trong một bài toán phân tích tài chính cụ thể, với một đối chứng không dùng mô hình và hai mô hình ngôn ngữ. Khóa luận cũng đo độ tin cậy của chính các cơ chế kiểm soát: độ nhạy của bộ kiểm chứng theo từng loại lỗi trước và sau cải tiến, khả năng chống chịu câu hỏi đối kháng (kèm lỗi thật được phát hiện và sửa) và độ khó của bước số hóa từ báo cáo gốc.

## 6.3. Hạn chế

Các hạn chế chi tiết nằm ở mục 3.4 và 5.14; bốn hạn chế lớn nhất là: (1) dữ liệu chỉ gồm mười ngân hàng và bốn chỉ tiêu, số liệu do tác giả đối soát với sự hỗ trợ của công cụ và chưa có người thứ hai kiểm tra, bước số hóa còn bán thủ công (một bộ trích xuất đơn giản chỉ lấy đúng 52% giá trị); (2) thực nghiệm chỉ chạy một lần mỗi cặp trên hai mô hình và hai phiên bản mã nguồn, nên chỉ là quan sát, không có ý nghĩa thống kê; (3) chấm điểm phần lớn tự động, chất lượng diễn giải chưa được chuyên gia đánh giá, và hai quy tắc kiểm tra mới được thiết kế sau khi thấy kết quả nên chưa chứng minh phát hiện loại lỗi khác; (4) tính thích ứng của kế hoạch và phân tích vĩ mô chưa được thực nghiệm kiểm riêng, và phân tích còn ở mức thuật lại số liệu, chưa giải thích nguyên nhân.

## 6.4. Hướng phát triển

Bảng 6.1 sắp xếp các hướng phát triển theo thời gian kèm mục tiêu đo được. Đây là mục tiêu đề xuất của tác giả, không phải kết quả đã đạt.

*Bảng 6.1: Hướng phát triển theo giai đoạn và mục tiêu đo được.*

| Giai đoạn | Việc chính | Mục tiêu đo được |
|---|---|---|
| Ngắn hạn (1 đến 3 tháng) | Xử lý loại nhầm của quy tắc nhãn chỉ tiêu với chú thích hình; dùng bộ câu hỏi độc lập do người ngoài đặt (bộ giữ lại, held-out); khảo sát từ 30 người, gồm ít nhất 10 người làm trong ngành, và thử nghiệm người dùng có đo thời gian; đưa người thứ hai đối soát độc lập một phần số liệu | Không câu hợp lệ nào, kể cả câu mẫu, bị loại nhầm trên bộ kiểm soát 300 câu cộng câu mẫu; người thứ hai đối soát tối thiểu 10% số đầu vào và báo tỷ lệ khớp |
| Trung hạn (3 đến 6 tháng) | Thêm ngân hàng niêm yết và chỉ tiêu (NIM, CASA, CIR); lặp A/B/C nhiều lần trên nhiều mô hình; cải thiện bộ phản biện (chỉ góp ý vào điều quy tắc không kiểm được, cho phép thêm câu) | Từ 20 ngân hàng và 7 chỉ tiêu; mỗi cấu hình chạy ít nhất 3 lần trên ít nhất 3 mô hình; C hoàn thành trọn vẹn không thấp hơn B và token không quá hai lần B |
| Dài hạn (6 đến 12 tháng) | Bổ sung truy xuất văn bản (RAG) cho phần định tính tách khỏi số liệu đã kiểm chứng; mở rộng sang ngành chứng khoán; kiểm tra bằng chuyên gia và bộ lỗi ngữ nghĩa mới | Chuyên gia chấm mù từ 5 người trên cùng bộ câu hỏi, báo độ đồng thuận; bộ lỗi ngữ nghĩa kiểu mới được thử và báo tỷ lệ bắt; độ trễ trung vị dưới 30 giây ở cấu hình mặc định |

Mở rộng dữ liệu bao gồm thêm các kỳ trước năm 2024 và mở rộng chuỗi vĩ mô, ngành (lạm phát cơ bản, tỷ giá, nợ xấu toàn hệ thống) khi có nguồn công bố theo quý, kèm một thực nghiệm riêng đánh giá nhánh vĩ mô. Để giảm độ trễ, có thể chạy song song các chuyên viên, lưu tạm kết quả công cụ và dùng mô hình nhỏ hơn cho các bước đơn giản. Vì tầng lõi không phụ thuộc mã ngân hàng hay cấu trúc cơ sở dữ liệu cụ thể, hệ thống có thể mở rộng sang ngành khác như chứng khoán.
