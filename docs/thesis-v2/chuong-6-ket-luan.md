# CHƯƠNG 6. KẾT LUẬN, HẠN CHẾ VÀ HƯỚNG PHÁT TRIỂN

## 6.1. Kết luận

Nghiên cứu này đã thiết kế, triển khai và đánh giá một hệ thống đa tác tử phân cấp, thích ứng theo câu hỏi, hỗ trợ tổng hợp thông tin và phân tích cơ bản mười ngân hàng niêm yết lớn nhất Việt Nam qua mười quý từ 2024 đến quý 2/2026. Hệ thống nhận câu hỏi tiếng Việt, lập và khóa kế hoạch phân tích, tính dữ kiện bằng mã nguồn có nguồn gốc rõ ràng, để các tác tử chuyên trách viết nhận định có trích dẫn, kiểm tra từng câu bằng quy tắc, tổng hợp báo cáo theo khối phù hợp với câu hỏi, và tùy cấu hình, phản biện rồi sửa đổi có mục tiêu. Toàn bộ quá trình được ghi lại và xem được trên giao diện tại https://fin-ai.eddiephung.me. Khoảng trống mà khóa luận nhắm tới (mục 1.3) là việc nối nhận định do AI viết với trang báo cáo gốc và kiểm từng câu bằng quy tắc, điều mà các công cụ hiện có không thấy công bố; và khi hỏi một mô hình phổ thông không công cụ, điểm đáng chú ý hơn tỷ lệ sai là không câu trả lời nào nêu được nguồn để người dùng kiểm tra.

**Kết luận ngắn.** (1) Lớp kiểm soát (mã tính số, truy nguồn, kiểm từng câu) cho độ khớp số và truy vết như nhau ở mọi cấu hình và mô hình. (2) Lợi thế của đa tác tử phân cấp so với một tác tử chỉ thấy ở DeepSeek V4 Pro và biến mất ở `gpt-5.6-luna`. (3) Phản biện và sửa đổi làm chi phí tăng ba đến bốn lần mà không cải thiện độ phủ. Vì vậy câu trả lời cho các câu hỏi nghiên cứu mang tính điều kiện theo mô hình, và tính thích ứng mới được kiểm một phần.

**Điều hệ thống làm được.** Đóng góp chính của khóa luận là lớp kiểm soát bao quanh mô hình, và lớp này hoạt động giống hệt ở mọi cấu hình tác tử: mọi con số do mã tính và truy được về trang báo cáo gốc (100% ở bốn cấu hình, hai mô hình); mỗi câu được kiểm bằng quy tắc trước khi vào báo cáo, và bộ kiểm bắt 99,2% lỗi cài vào sau khi bổ sung quy tắc; câu hỏi ngoài phạm vi hoặc chưa có dữ liệu bị từ chối đúng (R1, R2 ở mọi cấu hình); chi phí mô hình mỗi báo cáo chỉ từ vài chục đến hơn một nghìn đồng. Việc so sánh các cấu hình tác tử dưới đây vì vậy là một bài học thiết kế bên trong một hệ thống đã an toàn về số liệu, chứ không phải đánh giá về độ tin cậy của sản phẩm.

**Trả lời câu hỏi nghiên cứu thứ nhất (thiết kế).** Hệ thống giữ được khả năng truy nguyên khi tách rõ ba vai trò: mã nguồn tính mọi con số, mô hình ngôn ngữ chỉ diễn giải trên dữ kiện đã tính, và bộ kiểm tra theo quy tắc quyết định câu nào được vào báo cáo; kế hoạch được khóa trước khi truy xuất, mỗi câu bắt buộc trích dẫn dữ kiện, và phần không đạt kiểm tra được thay bằng khối dựng sẵn đã kiểm chứng.
- *Kết quả:* cả bốn cấu hình, kể cả D không gọi mô hình, đạt 100% khớp số và 100% truy được về số liệu gốc; bộ kiểm chứng bắt 99,2% đột biến giả lập sau khi thêm quy tắc (94,1% trước đó; riêng lỗi đổi chỉ tiêu từ 79,2% lên 99,2%).
- *Mức chắc chắn:* 100% là hệ quả của định nghĩa (đo trên câu đã qua bộ kiểm chứng), không phải bằng chứng về chất lượng mô hình viết; hai quy tắc mới được thiết kế sau khi thấy kết quả nên chưa chứng minh bắt loại lỗi chưa thử, và chúng loại nhầm sáu dòng chú thích hình mẫu.
- *Điều kiện:* mười ngân hàng, bốn chỉ tiêu, đột biến giả lập; kết quả giữ nguyên ở hai mô hình ngôn ngữ.

**Trả lời câu hỏi nghiên cứu thứ hai (B so với A).**
- *Kết quả:* với DeepSeek V4 Pro, B có độ phủ cao hơn A (0,812 so với 0,756 trên 10 câu phân tích; thắng 3, hòa 6, thua 1) và hoàn thành trọn vẹn 9/10 so với 7/10, với chi phí khoảng 2,2 lần token. Với `gpt-5.6-luna`, độ phủ của A, B, C đều là 0,912 trên 10 câu và A hoàn thành 10/10.
- *Mức chắc chắn:* mỗi cặp chỉ chạy một lần mỗi mô hình, chưa có ý nghĩa thống kê; A và B khác nhau ở hai yếu tố cùng lúc (chuyên môn hóa và số lượt gọi mô hình) nên không tách được tác động; độ phủ của B thay đổi theo mô hình nhiều hơn chênh lệch giữa B và A.
- *Điều kiện:* lợi thế của B gắn với DeepSeek V4 Pro; với mô hình mạnh hơn, cấu hình một tác tử rẻ nhất là đủ. Cấu hình D cho thấy mô hình đem lại thêm khoảng 0,12 đến 0,27 điểm độ phủ trên 10 câu, chủ yếu ở các câu cần nhiều chỉ tiêu.

**Trả lời câu hỏi nghiên cứu thứ ba (C so với B).**
- *Kết quả:* ở cả hai mô hình, phản biện và tối đa hai vòng sửa đổi làm chi phí tăng ba đến bốn lần và thêm 35 đến 58 giây mỗi lượt, không cải thiện độ phủ, và chỉ 4/10 (DeepSeek V4 Pro) hoặc 2/10 (`gpt-5.6-luna`) báo cáo hoàn thành trọn vẹn, vì bộ phản biện chỉ được sửa từng câu nên yêu cầu ở mức cả báo cáo thường không đáp ứng và câu liên quan bị loại.
- *Mức chắc chắn:* một lần chạy mỗi mô hình, hai phiên bản mã nguồn khác nhau, chưa có ý nghĩa thống kê.
- *Điều kiện:* kết luận áp dụng cho bộ phản biện hiện tại và bộ 12 câu hỏi đã dùng để hiệu chỉnh.

**Khuyến nghị rút ra.** Có thể chạy mặc định bằng cấu hình rẻ (A trên mô hình mạnh, hoặc B) và tránh C trừ khi có người xem xét kết quả. Mức đáp ứng từng yêu cầu ở Bảng 2.1: các yêu cầu FR1, FR4, FR5 và NFR3 mới được kiểm một phần (xem 3.4 và 5.14).

## 6.2. Đóng góp của khóa luận

Về thực tiễn, khóa luận cung cấp một hệ thống đã triển khai gồm: bộ dữ liệu mười ngân hàng × mười quý với 400 giá trị chỉ tiêu, mỗi giá trị truy được tới trang báo cáo tài chính gốc và có bản ghi truy vết phép tính; quy trình tiếp nhận ngân hàng mới có kiểm tra nguồn và tính lại chỉ tiêu, dùng được ngay trên giao diện web; giao diện hỏi – theo dõi quá trình – đọc báo cáo kiểu phân tích đầu tư; và bộ công cụ đánh giá có thể chạy lại. Về phương pháp, khóa luận đề xuất cách "kiểm từng câu thay vì cấm số": mô hình được nêu số nhưng mỗi con số, thứ hạng, kỳ, tên chỉ tiêu và chiều so sánh phải khớp dữ kiện được trích, và câu không đạt bị loại riêng thay vì hủy cả lượt phân tích. Về phân tích bài toán, khóa luận so sánh các công cụ hiện có theo tài liệu công bố, lập bảng yêu cầu truy vết từ người dùng tới thiết kế và kiểm chứng, và minh họa bằng số liệu giới hạn của mô hình phổ thông không có lớp kiểm soát. Về đánh giá, khóa luận cung cấp bằng chứng định lượng về quan hệ giữa độ phức tạp kiến trúc và chi phí trong một bài toán phân tích tài chính cụ thể, với một đối chứng không dùng mô hình và hai mô hình ngôn ngữ, và đo trực tiếp độ tin cậy của chính các cơ chế kiểm soát: độ nhạy của bộ kiểm chứng theo từng loại lỗi trước và sau khi cải tiến, khả năng chống chịu trước câu hỏi đối kháng (kèm lỗi thật được phát hiện và sửa), và mức độ khó của bước số hóa từ báo cáo gốc.

## 6.3. Hạn chế

Các hạn chế chi tiết nằm ở mục 3.4 và 5.14; bốn hạn chế lớn nhất là: (1) dữ liệu chỉ gồm mười ngân hàng và bốn chỉ tiêu, số liệu do tác giả đối soát với sự hỗ trợ của công cụ và chưa có người thứ hai kiểm tra, bước số hóa còn bán thủ công (một bộ trích xuất đơn giản chỉ lấy đúng 52% giá trị); (2) thực nghiệm chỉ chạy một lần mỗi cặp trên hai mô hình và hai phiên bản mã nguồn, nên chỉ là quan sát, không có ý nghĩa thống kê; (3) chấm điểm phần lớn tự động, chất lượng diễn giải chưa được chuyên gia đánh giá, và hai quy tắc kiểm tra mới được thiết kế sau khi thấy kết quả nên chưa chứng minh bắt loại lỗi khác; (4) tính thích ứng của kế hoạch và phân tích vĩ mô chưa được thực nghiệm kiểm riêng, và phân tích còn ở mức thuật lại số liệu, chưa giải thích nguyên nhân.

## 6.4. Hướng phát triển

Bảng 6.1 sắp xếp các hướng phát triển theo thời gian kèm mục tiêu đo được. Đây là mục tiêu đề xuất của tác giả, không phải kết quả đã đạt.

*Bảng 6.2: Hướng phát triển theo giai đoạn và mục tiêu đo được.*

| Giai đoạn | Việc chính | Mục tiêu đo được |
|---|---|---|
| Ngắn hạn (1 đến 3 tháng) | Xử lý bác bỏ nhầm của quy tắc nhãn chỉ tiêu với chú thích hình; dùng bộ câu hỏi giữ lại do người ngoài đặt (held-out); đưa người thứ hai đối soát độc lập một phần số liệu; hoàn tất khảo sát và chấm mù với nhiều người hơn | Không câu hợp lệ nào, kể cả câu mẫu, bị loại nhầm trên bộ kiểm soát 300 câu cộng câu mẫu; người thứ hai đối soát tối thiểu 10% số đầu vào và báo tỷ lệ khớp; khảo sát từ 30 người |
| Trung hạn (3 đến 6 tháng) | Thêm ngân hàng niêm yết và chỉ tiêu (NIM, CASA, CIR); lặp A/B/C nhiều lần trên nhiều mô hình; cải thiện bộ phản biện (chỉ góp ý vào điều quy tắc không kiểm được, cho phép thêm câu) | Từ 20 ngân hàng và 7 chỉ tiêu; mỗi cấu hình chạy ít nhất 3 lần trên ít nhất 3 mô hình; C hoàn thành trọn vẹn không thấp hơn B và token không quá hai lần B |
| Dài hạn (6 đến 12 tháng) | Bổ sung truy xuất văn bản (RAG) cho phần định tính tách khỏi số liệu đã kiểm chứng; mở rộng sang ngành chứng khoán; kiểm tra bằng chuyên gia và bộ lỗi ngữ nghĩa mới | Chuyên gia chấm mù từ 5 người trên cùng bộ câu hỏi, báo độ đồng thuận; bộ lỗi ngữ nghĩa kiểu mới được thử và báo tỷ lệ bắt; độ trễ trung vị dưới 30 giây ở cấu hình mặc định |

Mở rộng dữ liệu bao gồm thêm các kỳ trước năm 2024 và mở rộng chuỗi vĩ mô, ngành (lạm phát cơ bản, tỷ giá, nợ xấu toàn hệ thống) khi có nguồn công bố theo quý, kèm một thực nghiệm riêng đánh giá nhánh vĩ mô. Để giảm độ trễ, có thể chạy song song các chuyên viên, lưu tạm kết quả công cụ và dùng mô hình nhỏ hơn cho các bước đơn giản. Vì tầng lõi không phụ thuộc mã ngân hàng hay cấu trúc cơ sở dữ liệu cụ thể, hệ thống có thể mở rộng sang ngành khác như chứng khoán.
