# CHƯƠNG 6. KẾT LUẬN, HẠN CHẾ VÀ HƯỚNG PHÁT TRIỂN

## 6.1. Kết luận

Nghiên cứu này đã thiết kế, triển khai và đánh giá một hệ thống đa tác tử phân cấp, thích ứng theo câu hỏi, hỗ trợ tổng hợp thông tin và phân tích cơ bản mười ngân hàng niêm yết lớn nhất Việt Nam qua mười quý từ 2024 đến quý 2/2026. Hệ thống nhận câu hỏi tiếng Việt, lập và khóa kế hoạch phân tích, tính dữ kiện bằng mã nguồn có nguồn gốc rõ ràng, để các tác tử chuyên trách viết nhận định có trích dẫn, kiểm tra từng câu bằng quy tắc, tổng hợp báo cáo theo khối phù hợp với câu hỏi, và tùy cấu hình, phản biện rồi sửa đổi có mục tiêu. Toàn bộ quá trình được ghi lại và xem được trên giao diện tại https://fin-ai.eddiephung.me.

**Trả lời câu hỏi nghiên cứu thứ nhất (thiết kế).** Hệ thống giữ được khả năng truy nguyên khi tách rõ ba vai trò: mã nguồn tính mọi con số, mô hình ngôn ngữ chỉ diễn giải trên dữ kiện đã tính, và bộ kiểm tra theo quy tắc quyết định câu nào được vào báo cáo. Các yếu tố then chốt gồm kế hoạch được khóa trước khi truy xuất dữ liệu; dữ kiện mang phiên bản công thức và mã quan sát đầu vào; mỗi câu bắt buộc trích dẫn dữ kiện; báo cáo lắp từ các khối có kiểm tra cấu trúc; ranh giới tầng lõi – tầng ứng dụng được kiểm tra tự động; và cơ chế cơ chế dự phòng an toàn, trong đó phần không đạt kiểm tra được thay bằng khối dựng sẵn đã kiểm chứng. Trong thực nghiệm, cả ba cấu hình đều đạt 100% khớp số với dữ kiện và 100% truy được về số liệu gốc, và kết quả này giữ nguyên khi đổi mô hình ngôn ngữ (ba mô hình OpenAI, hai mô hình DeepSeek). Phép đo bằng đột biến cho thấy giới hạn của đảm bảo này: bộ kiểm chứng bắt tuyệt đối lỗi về con số, thứ hạng và mẫu số, nhưng bỏ sót khoảng 21% các câu giữ nguyên con số và đổi tên chỉ tiêu, nên "đúng số" chưa đồng nghĩa với "đúng chỉ tiêu, kỳ và ngân hàng".

**Trả lời câu hỏi nghiên cứu thứ hai (B so với A).** Trên cùng câu hỏi, dữ liệu, mô hình và công cụ, cấu hình phân cấp B có độ phủ chỉ tiêu cao hơn (0,844 so với 0,797), nhiều báo cáo hoàn thành trọn vẹn hơn (9 so với 7 trên 12) và ít phải dùng bố cục dựng sẵn hơn, với chi phí khoảng 2,2 lần token và thêm khoảng 10 giây mỗi lượt. Chênh lệch về độ phủ nhất quán về hướng với thực nghiệm thử trên Gold v5 nhưng chưa có ý nghĩa thống kê. Khi đổi mô hình, độ phủ của cấu hình B thay đổi nhiều hơn chênh lệch giữa B và A (0,80–0,93 giữa ba mô hình OpenAI, một lần chạy mỗi mô hình), nên kết luận về B nên được hiểu là gắn với mô hình đã dùng.

**Trả lời câu hỏi nghiên cứu thứ ba (C so với B).** Phản biện và tối đa hai vòng sửa đổi làm chi phí tăng khoảng ba lần và thêm khoảng 35 giây mỗi lượt, không cải thiện độ chính xác hay độ phủ, và làm báo cáo nêu nhiều phát hiện liên tầng hơn. Bộ phản biện phát hiện đúng những chỗ báo cáo chưa đầy đủ, nhưng vì chỉ được sửa từng câu nên các yêu cầu ở mức cả báo cáo thường không được đáp ứng và câu liên quan bị loại; kết quả là chỉ 4 trên 12 lượt của C hoàn thành trọn vẹn.

## 6.2. Đóng góp của khóa luận

Về thực tiễn, khóa luận cung cấp một hệ thống đã triển khai gồm: bộ dữ liệu mười ngân hàng × mười quý với 400 giá trị chỉ tiêu, mỗi giá trị truy được tới trang báo cáo tài chính gốc và có bản ghi truy vết phép tính; quy trình tiếp nhận ngân hàng mới có kiểm tra nguồn và tính lại chỉ tiêu, dùng được ngay trên giao diện web; giao diện hỏi – theo dõi quá trình – đọc báo cáo kiểu phân tích đầu tư; và bộ công cụ đánh giá có thể chạy lại. Về phương pháp, khóa luận đề xuất cách "kiểm từng câu thay vì cấm số": mô hình được nêu số nhưng mỗi con số, thứ hạng, kỳ và chiều so sánh phải khớp dữ kiện được trích, và câu không đạt bị loại riêng thay vì hủy cả lượt phân tích. Về đánh giá, khóa luận cung cấp bằng chứng định lượng về quan hệ giữa độ phức tạp kiến trúc và chi phí trong một bài toán phân tích tài chính cụ thể, trong điều kiện so sánh công bằng giữa các cấu hình, và đo trực tiếp độ tin cậy của chính các cơ chế kiểm soát: độ nhạy của bộ kiểm chứng theo từng loại lỗi, khả năng chống chịu trước câu hỏi đối kháng (kèm một lỗi thật được phát hiện và sửa), và mức độ khó của bước số hóa từ báo cáo gốc.

## 6.3. Hạn chế

**Về dữ liệu.** Dữ liệu gồm mười ngân hàng niêm yết lớn nhất và bốn chỉ tiêu, nên kết quả không suy rộng cho toàn ngành; số liệu do tác giả đối soát với sự hỗ trợ của công cụ, chưa qua kiểm tra độc lập. Dữ liệu vĩ mô chưa có nên nhánh phân tích vĩ mô chưa được đánh giá. Bước số hóa từ báo cáo gốc được thực hiện bán tự động, với sự kiểm tra của tác giả thông qua các ràng buộc đẳng thức kế toán, nhưng chưa có chuyên gia độc lập thứ hai thẩm định chéo: một bộ trích xuất đơn giản chỉ lấy đúng 52% giá trị dù 93–96% giá trị đọc được trên trang. Bộ dữ liệu không có ô thiếu nên khả năng xử lý thiếu số liệu chỉ được kiểm tra bằng kiểm thử tự động. Hệ thống chưa hỗ trợ so sánh nhóm qua nhiều kỳ.

**Về thiết kế kiểm chứng.** Bộ kiểm chứng câu chưa bắt được khoảng một phần năm các lỗi đổi tên chỉ tiêu; kiểm tra đối kháng chỉ gồm mười lăm câu và lỗi câu hỏi ngoài phạm vi được sửa bằng cổng theo dấu hiệu từ khóa, không phải bộ phân loại ý định. Việc chấm điểm hoàn toàn tự động; chất lượng diễn giải và tính hữu ích chưa được chuyên gia đánh giá.

**Về quy trình thực nghiệm và hạ tầng.** Thực nghiệm A/B/C chỉ chạy một lần với một mô hình ngôn ngữ; các kiểm tra bổ sung có thêm mô hình khác và ba lần chạy lặp cho một mô hình, nhưng vẫn ít để có ý nghĩa thống kê, trong khi đầu ra của mô hình thay đổi giữa các lần chạy, và các lượt được chạy đồng thời nên thời gian đo được chịu ảnh hưởng của tải máy chủ. Người phát triển đồng thời là người thiết kế thực nghiệm. Về vận hành, câu hỏi phức tạp ở cấu hình đầy đủ có thể mất hơn một phút, và máy chủ miễn phí dùng cho bản triển khai cần thời gian khởi động sau khi nghỉ.

## 6.4. Hướng phát triển

Thứ nhất, mở rộng dữ liệu: thêm các ngân hàng niêm yết khác qua quy trình tiếp nhận hiện có, đưa người thứ hai đối soát độc lập, thêm các kỳ trước năm 2024, các chỉ tiêu như NIM, CASA, CIR và dữ liệu vĩ mô có đối chiếu kỳ.

Thứ hai, lặp lại thực nghiệm A/B/C nhiều lần và với nhiều mô hình, mở rộng bộ câu hỏi đối kháng, bổ sung quy tắc kiểm tra nhãn chỉ tiêu theo cặp (chỉ tiêu, giá trị) và quy tắc loại câu tự so sánh, và có chuyên gia chấm mù chất lượng diễn giải.

Thứ ba, cải thiện bộ phản biện: giới hạn góp ý vào những gì quy tắc không kiểm được, cho phép bổ sung câu mới khi báo cáo thiếu ý thay vì chỉ sửa hoặc loại câu cũ, chuyển góp ý mức nhẹ thành ghi chú cho người đọc và chỉ bật phản biện cho báo cáo phức tạp.

Thứ tư, giảm độ trễ bằng cách chạy song song các chuyên viên, lưu tạm kết quả công cụ và dùng mô hình nhỏ hơn cho các bước đơn giản.

Thứ năm, bổ sung truy xuất văn bản (RAG) cho phần định tính như nhận định của ban điều hành hay thuyết minh rủi ro, tách riêng khỏi phần số liệu đã kiểm chứng.

Cuối cùng, vì tầng lõi không phụ thuộc mã ngân hàng hay cấu trúc cơ sở dữ liệu cụ thể, hệ thống có thể mở rộng sang ngành khác như chứng khoán.
