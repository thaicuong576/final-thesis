# CHƯƠNG 5. KẾT QUẢ VÀ THẢO LUẬN

Chương này trình bày kết quả theo ba bước, từ kiểm tra kỹ thuật tới sử dụng thực tế: (i) kiểm thử tự động của hệ thống, (ii) chạy hệ thống đã đưa lên mạng với mô hình ngôn ngữ thật trên năm câu hỏi mẫu, và (iii) thực nghiệm so sánh ba cấu hình A, B, C trên cùng bộ câu hỏi, cùng bộ dữ liệu và cùng mô hình. Mọi số liệu trong chương được lấy từ các tệp kết quả được lưu lại cùng mã nguồn; không có số liệu nào được nhập tay hoặc ước lượng lại.

## 5.1. Kết quả nghiệm thu kỹ thuật

### 5.1.1. Kiểm thử tự động

Ở phiên bản dùng cho thực nghiệm, phần xử lý phía máy chủ có 839 bài kiểm thử tự động và phần giao diện có 139 bài, tất cả đều chạy thành công. Mỗi khi mã nguồn thay đổi, hệ thống còn tự kiểm tra hai điều: định dạng dữ liệu trao đổi giữa giao diện và máy chủ không bị thay đổi ngoài ý muốn, và phần lõi xử lý dữ liệu không bị gắn chặt vào một cơ sở dữ liệu, một mô hình ngôn ngữ hay một danh sách ngân hàng cụ thể. Các bài kiểm thử dùng mô hình và dữ liệu giả lập để chạy nhanh và cho kết quả ổn định.

Kiểm thử chỉ chứng minh hệ thống vận hành đúng với các kịch bản đã được mô tả. Vì vậy, ngoài kiểm thử, hệ thống còn được chạy lặp lại với mô hình ngôn ngữ thật và dữ liệu Gold v5 thật (mục 5.1.2). Quá trình này đã phát hiện nhiều lỗi mà kiểm thử giả lập không bộc lộ, được trình bày ở mục 5.5.

### 5.1.2. Chạy hệ thống đang vận hành trên năm câu hỏi mẫu

Năm câu hỏi mẫu B1–B5 đại diện cho năm dạng câu hỏi hệ thống hỗ trợ. Chúng được gửi tới phiên bản đang chạy trên mạng (giao diện tại https://fin-ai.eddiephung.me) sau khi phiên bản cuối được cập nhật. Bảng 5.1 tóm tắt kết quả.

Bảng 5.1: Kết quả chạy năm câu hỏi mẫu trên phiên bản đang vận hành

| Mã | Câu hỏi | Dạng câu hỏi | Trạng thái | Người lắp báo cáo | Thời gian |
|---|---|---|---|---|---|
| B1 | Sức khỏe tài chính của ACB so với các ngân hàng cùng nhóm, quý 4/2024 | Hồ sơ doanh nghiệp | Có giới hạn | Mô hình ngôn ngữ | 127 giây |
| B2 | Ngân hàng nào có đệm dự phòng dày nhất quý 4/2024? | Xếp hạng | Có giới hạn | Mẫu dự phòng | 92 giây |
| B3 | ROE của VPB thay đổi thế nào trong năm 2024? | Xu hướng | Có giới hạn | Mô hình ngôn ngữ | 130 giây |
| B4 | So sánh ACB và TCB quý 4/2024 | So sánh trực tiếp | Có giới hạn | Mô hình ngôn ngữ | 66 giây |
| B5 | Tỷ lệ nợ xấu của VCB quý 4/2024 là bao nhiêu? | Tra cứu | Hoàn thành | Mô hình ngôn ngữ | 41 giây |

Cả năm câu hỏi đều nhận được báo cáo hợp lệ. Bốn báo cáo do mô hình ngôn ngữ sắp xếp; báo cáo còn lại dùng bố cục dự phòng có sẵn vì bản của mô hình không đạt kiểm tra cấu trúc. Mọi con số xuất hiện trong báo cáo đều khớp với dữ liệu Gold v5 gốc, ví dụ tỷ lệ nợ xấu của VCB quý 4/2024 là 0,96% (giá trị lưu trữ 0,9636%), tỷ lệ bao phủ nợ xấu của VCB là 223,3%, gấp 2,4 lần trung vị năm ngân hàng. Điểm chưa đạt là độ trễ: hai câu hỏi phức tạp nhất vượt 120 giây do cấu hình đầy đủ gọi mô hình nhiều lần (viết câu, lắp báo cáo, phản biện hai vòng). Giao diện hiển thị tiến trình từng bước theo thời gian thực nên người dùng vẫn theo dõi được quá trình, nhưng đây là hạn chế về trải nghiệm cần ghi nhận.

## 5.2. Thiết lập thực nghiệm A/B/C

Thực nghiệm được chạy ngày 30/9/2026 trên bộ dữ liệu Gold v5 (được khóa bằng mã kiểm tra để bảo đảm không thay đổi), với mô hình ngôn ngữ DeepSeek V4 Pro. Thứ tự chạy được xáo trộn ngẫu nhiên theo một giá trị cố định để có thể lặp lại, và mỗi cặp nhiệm vụ – cấu hình được chạy một lần. Mười hai nhiệm vụ gồm mười nhiệm vụ phân tích (T01–T10) và hai nhiệm vụ kiểm soát từ chối (R1: kỳ không có trong dữ liệu; R2: ngân hàng ngoài nhóm Gold), tạo thành 36 lượt chạy. Tổng lượng văn bản mô hình xử lý là 474.265 token (đơn vị đo khối lượng văn bản của mô hình ngôn ngữ), trong giới hạn 3.000.000 token đặt trước.

Để so sánh công bằng, ba cấu hình dùng chung một kế hoạch phân tích được lập theo luật cố định. Sau khi chạy, hệ thống kiểm tra lại và xác nhận cả mười hai nhiệm vụ có kế hoạch giống hệt nhau giữa ba cấu hình. Việc chấm điểm do chương trình thực hiện theo quy tắc cố định, không dùng người chấm hay mô hình chấm; các chỉ số đã được mô tả ở mục 3.3.4.

Trước khi phân tích, cách chấm được điều chỉnh ở hai điểm và các điều chỉnh này đều được ghi lại: (1) chỉ số "hoàn thành" được tách thành "trả lời được" (báo cáo hợp lệ, có thể kèm ghi chú giới hạn) và "hoàn thành trọn vẹn" (không có ghi chú giới hạn nào). Cách tính ban đầu chỉ đếm trường hợp thứ hai nên đã đánh giá sai rằng cấu hình C không trả lời được câu nào, trong khi cả mười báo cáo của C đều hợp lệ; (2) số vòng sửa đổi được lấy từ bản tóm tắt sửa đổi thay vì đếm trong nhật ký.

## 5.3. Kết quả tổng hợp

Bảng 5.2 trình bày giá trị trung bình theo cấu hình trên 12 lượt chạy mỗi cấu hình. Hình 5.1 và Hình 5.2 minh họa độ chính xác, độ phủ và chi phí.

Bảng 5.2: Kết quả tổng hợp theo cấu hình (12 lượt chạy mỗi cấu hình)

| Chỉ số | A – một tác tử | B – phân cấp | C – phân cấp có phản biện |
|---|---|---|---|
| Trả lời được (10 nhiệm vụ phân tích) | 10/10 | 10/10 | 10/10 |
| Từ chối đúng (R1, R2) | 2/2 | 2/2 | 2/2 |
| Hoàn thành trọn vẹn, không ghi chú giới hạn (trên 12) | 9 (75,0%) | 9 (75,0%) | 0 (0,0%) |
| Tính đúng số | 100% | 100% | 100% |
| Truy được về số liệu gốc | 100% | 100% | 100% |
| Độ phủ chỉ tiêu bắt buộc | 0,708 | 0,818 | 0,813 |
| Tỷ lệ câu bị loại khỏi báo cáo | 1,7% | 2,8% | 0,0% |
| Phát hiện liên tầng trung bình mỗi lượt | 0,33 | 0,42 | 0,58 |
| Thời gian xử lý trung bình | 15,7 giây | 32,5 giây | 83,1 giây |
| Số lượt gọi mô hình trung bình | 0,8 | 2,1 | 5,1 |
| Token trung bình mỗi lượt | 3.950 | 8.534 | 27.038 |
| Số vòng sửa đổi trung bình | 0 | 0 | 1,5 |

![](experiments/er8/analysis/figure_er8_completion_accuracy.png)

Hình 5.1: Tỷ lệ thành công theo giao thức và tính đúng số theo cấu hình

![](experiments/er8/analysis/figure_er8_cost_latency.png)

Hình 5.2: Chi phí vận hành theo cấu hình (thời gian xử lý và token)

Kết quả nổi bật đầu tiên là cả ba cấu hình đều đạt 100% tính đúng số và 100% khả năng truy vết. Kết quả này không phản ánh sự khác biệt về năng lực của mô hình giữa các cấu hình, mà là hệ quả trực tiếp của thiết kế: mọi con số trong báo cáo đều được tính bởi các công cụ tất định dưới dạng dữ kiện có nguồn, và mọi câu văn chỉ được đưa vào báo cáo khi bộ kiểm tra câu xác nhận các con số, thứ hạng, kỳ và chiều so sánh khớp với dữ kiện được trích dẫn. Nói cách khác, kiến trúc chuyển rủi ro "sai số" của mô hình ngôn ngữ thành rủi ro "câu bị loại", và rủi ro này được ghi nhận minh bạch trong nhật ký kiểm tra của từng báo cáo.

Hai nhiệm vụ kiểm soát R1 và R2 bị từ chối đúng ở cả ba cấu hình, trước khi gọi mô hình phân tích, với thông báo tiếng Việt và gợi ý câu hỏi thay thế. Nhiệm vụ T03 (tỷ lệ nợ xấu của ACB quý 1/2024, một ô không có số liệu đã kiểm chứng trong Gold v5) được trả lời ở cả ba cấu hình bằng cách nêu rõ giới hạn dữ liệu thay vì ước tính. Trong nhiệm vụ đa kỳ T08, ô thiếu của ACB quý 1/2024 cũng được xử lý tương tự.

## 5.4. Trả lời RQ2: cấu hình phân cấp B so với một tác tử A

Bảng 5.3 so sánh từng cặp cấu hình trên cùng nhiệm vụ. Khoảng trong ngoặc vuông là khoảng tin cậy 95%, được ước lượng bằng cách lấy mẫu lại 1.000 lần từ chính các cặp nhiệm vụ. Vì chỉ có 12 cặp và mỗi cặp chạy một lần, các khoảng này chỉ mang tính tham khảo: khoảng chứa số 0 nghĩa là chưa đủ bằng chứng để khẳng định có khác biệt.

Bảng 5.3: Chênh lệch giữa các cặp cấu hình (trung bình và khoảng tin cậy 95%)

| Chỉ số | B − A | C − B | C − A |
|---|---|---|---|
| Độ phủ chỉ tiêu | +0,109 [−0,010; +0,240] | −0,005 [−0,089; +0,063] | +0,104 [0,000; +0,229] |
| Phát hiện liên tầng mỗi lượt | +0,083 [0,000; +0,250] | +0,167 [−0,333; +0,917] | +0,250 [−0,250; +1,000] |
| Token mỗi lượt | +4.583 [+2.451; +6.787] | +18.505 [+11.293; +25.572] | +23.088 [+14.325; +31.716] |
| Thời gian xử lý (giây) | +16,9 [+9,3; +24,1] | +50,6 [+33,5; +67,6] | +67,5 [+45,3; +87,0] |

![](experiments/er8/analysis/figure_er8_pairwise_diff.png)

Hình 5.3: Chênh lệch giữa các cặp cấu hình với khoảng tin cậy 95%

So với một tác tử, cấu hình phân cấp B có độ phủ chỉ tiêu cao hơn khoảng 11 điểm phần trăm (0,818 so với 0,708) và nêu nhiều phát hiện liên tầng hơn một chút. Chênh lệch về độ phủ nhất quán về hướng nhưng khoảng tin cậy vẫn chạm giá trị 0, nên chỉ có thể xem là dấu hiệu tích cực chứ chưa phải kết luận chắc chắn. Nguồn gốc của chênh lệch có thể nhận thấy ở cấp nhiệm vụ: trong các nhiệm vụ T02, T04 và T05, A chỉ đề cập một phần chỉ tiêu được yêu cầu (độ phủ 0,38–0,50), trong khi các chuyên viên của B viết nhận định riêng cho phần doanh nghiệp và phần so sánh nhóm, nhờ đó các chỉ tiêu được bao quát đầy đủ hơn (0,75–1,00). Ngược lại, ở T01 A đạt độ phủ cao hơn B, cho thấy lợi thế của B không xuất hiện ở mọi nhiệm vụ.

Cái giá của B là chi phí: B dùng khoảng 2,2 lần token và gấp đôi thời gian so với A (thêm khoảng 4.600 token và 17 giây mỗi lượt, khoảng tin cậy không chứa 0). Về độ chính xác và khả năng truy vết, hai cấu hình không khác nhau vì cả hai cùng đi qua các công cụ tất định và bộ kiểm tra câu. Tỷ lệ câu bị loại của B (2,8%) cao hơn A (1,7%) chủ yếu do các chuyên viên viết nhiều câu hơn, trong đó có câu mô tả xu hướng mà không trích dữ kiện thay đổi, và bị bộ kiểm tra loại theo luật.

Như vậy, với trường hợp nghiên cứu này, chuyên môn hóa nhiệm vụ mang lại cải thiện vừa phải về độ đầy đủ của báo cáo với chi phí tăng khoảng gấp đôi, trong khi độ chính xác của số liệu được bảo đảm như nhau bởi cơ chế kiểm tra chung.

## 5.5. Trả lời RQ3: bổ sung phản biện và sửa đổi (C so với B)

Việc bổ sung phản biện ngữ nghĩa và tối đa hai vòng sửa đổi không làm tăng độ phủ (0,813 so với 0,818, chênh lệch không đáng kể) và không thay đổi độ chính xác số liệu vốn đã tuyệt đối ở B. Số phát hiện liên tầng được nêu trong báo cáo có xu hướng tăng (0,58 so với 0,42 mỗi lượt), phù hợp với việc bộ phản biện được giao nhiệm vụ kiểm tra các mâu thuẫn liên tầng đã xác nhận có được nêu trong báo cáo hay không; tuy nhiên khoảng tin cậy rộng và chứa 0.

Chi phí của C tăng mạnh: token gấp 3,2 lần B và gấp 6,8 lần A; thời gian xử lý trung bình 83 giây, tức thêm khoảng 51 giây so với B. Trung bình mỗi lượt C thực hiện 1,5 vòng sửa đổi (1,8 vòng trên các lượt có báo cáo), cho thấy bộ phản biện gần như luôn nêu vấn đề cần sửa.

Đáng chú ý nhất, không lượt chạy nào của C đạt trạng thái hoàn thành trọn vẹn: cả mười báo cáo đều kết thúc với ít nhất một vấn đề phản biện chưa được giải quyết và được ghi thành giới hạn. Phân tích 20 vấn đề mà bộ phản biện nêu trong các lượt C cho thấy 15 vấn đề thuộc loại "tổng hợp chưa đầy đủ", 3 vấn đề "nhận định chưa được hỗ trợ" và 2 vấn đề "mâu thuẫn liên tầng"; 15 vấn đề được bộ phản biện đánh giá là nghiêm trọng và 5 vấn đề ở mức nhẹ. Nhiều vấn đề mang tính yêu cầu bổ sung ngữ cảnh (ví dụ nêu rõ giá trị trung vị khi đã nêu chênh lệch, hoặc nhắc đến một phát hiện liên tầng chưa xuất hiện) hơn là chỉ ra sai sót. Điều này cho thấy trong thiết kế hiện tại, bộ phản biện đóng vai trò của một người biên tập khó tính: nó làm báo cáo đầy đủ hơn ở một số chiều nhưng hiếm khi đưa báo cáo về trạng thái "không còn góp ý", và mỗi vòng góp ý có chi phí đáng kể.

Quá trình phát triển cũng cho thấy phản biện ngữ nghĩa là thành phần nhạy cảm nhất của hệ thống. Trong các lần chạy thật trước khi hoàn thiện, bộ phản biện từng tự kiểm tra lại phép tính và hiểu sai chiều tốt của chỉ tiêu (với tỷ lệ nợ xấu, giá trị thấp hơn là tốt hơn), dẫn đến bác bỏ một nhận định đúng như "TCB nhỉnh hơn ACB ở 3/4 chỉ tiêu"; đồng thời áp dụng các yêu cầu của phiên bản quy trình cũ. Các lỗi này được khắc phục bằng cách truyền chiều tốt của từng chỉ tiêu cho bộ phản biện, quy định rõ rằng số liệu và phép so sánh đã được mã nguồn kiểm tra, và chỉ để các vấn đề nghiêm trọng mới được loại bỏ câu văn. Kinh nghiệm này củng cố nguyên tắc cốt lõi của khóa luận: phần có thể kiểm tra bằng quy tắc nên được kiểm tra bằng mã nguồn, còn mô hình ngôn ngữ chỉ nên đánh giá những gì quy tắc không kiểm được.

Trả lời RQ3: trong điều kiện của thực nghiệm, phản biện và sửa đổi có mục tiêu làm chi phí tăng khoảng ba lần so với B, không cải thiện độ chính xác hay độ phủ đo được bằng các chỉ số tất định, và có dấu hiệu làm báo cáo nêu nhiều phát hiện liên tầng hơn. Giá trị của C vì vậy nằm ở chất lượng diễn giải — phần mà các chỉ số tất định của thực nghiệm này không đo trực tiếp — và cần được đánh giá thêm bằng chấm điểm của chuyên gia.

## 5.6. Phân tích theo loại câu hỏi và cơ chế kiểm tra câu

Báo cáo được lắp theo khối và thay đổi hình dạng theo loại câu hỏi. Câu hỏi tra cứu tạo thẻ trả lời gồm một khối trả lời (1–2 khối), trong khi hồ sơ doanh nghiệp tạo báo cáo dài nhất với trung bình 6–6,5 khối, gồm tiêu đề, các luận điểm, nhiều biểu đồ (bản đồ nhiệt thứ hạng, biểu đồ tán xạ, biểu đồ nhỏ theo kỳ) và các khối lưu ý cho phát hiện liên tầng. Câu hỏi xếp hạng và so sánh trực tiếp tạo báo cáo 3–5 khối với biểu đồ xếp hạng hoặc bảng so sánh. Như vậy yêu cầu ban đầu về báo cáo thích ứng theo câu hỏi, thay vì một khuôn cố định, được đáp ứng.

Trong 30 lượt phân tích, 27 báo cáo được mô hình điều phối lắp ráp và 3 báo cáo dùng bố cục tất định dự phòng (mỗi cấu hình một lượt). Bộ kiểm tra câu và bước phản biện loại tổng cộng 79 câu trong toàn bộ thực nghiệm (A: 15, B: 24, C: 40). Các lý do phổ biến nhất là câu nêu xu hướng không khớp hoặc không có dữ kiện thay đổi đi kèm (33 câu), con số không khớp với dữ kiện được trích dẫn (19 câu) và thứ hạng không khớp (7 câu). Ở cấu hình C, thêm 10 câu bị loại vì còn vấn đề phản biện chưa giải quyết. Mỗi câu bị loại được ghi lại cùng mã lý do trong nhật ký kiểm tra của báo cáo, nên người dùng và người đánh giá có thể thấy rõ phần nào đã bị loại và vì sao.

## 5.7. Thảo luận

Kết quả cho thấy ba nhận xét chính. Thứ nhất, độ tin cậy về số liệu của báo cáo không đến từ việc chọn cấu hình tác tử nào, mà đến từ kiến trúc kiểm soát bao quanh mô hình ngôn ngữ: tính toán tất định, dữ kiện có nguồn và kiểm tra từng câu. Đây là kết luận có ý nghĩa thực tiễn đối với các ứng dụng phân tích tài chính, nơi một con số sai có thể làm mất giá trị của cả báo cáo.

Thứ hai, chuyên môn hóa (B) cải thiện độ đầy đủ với chi phí vừa phải, trong khi phản biện (C) có chi phí lớn nhưng lợi ích chưa đo được bằng chỉ số tất định. Với người dùng cuối như chuyên viên phân tích, cấu hình B là điểm cân bằng hợp lý cho tương tác thời gian thực; cấu hình C phù hợp hơn cho các báo cáo không yêu cầu phản hồi nhanh và cần mức rà soát cao hơn.

Thứ ba, quá trình đưa mô hình ngôn ngữ thật vào hệ thống bộc lộ nhiều vấn đề mà kiểm thử giả lập không phát hiện: mô hình trả kết quả sai khuôn dữ liệu yêu cầu, chèn mã định danh dữ kiện vào câu văn, hoặc tạo kế hoạch thiếu trường bắt buộc. Hệ thống được hoàn thiện theo hướng "suy giảm an toàn": khi một phần của mô hình không đạt kiểm tra, hệ thống giữ phần đã được kiểm chứng và bổ sung khối tất định, thay vì bỏ toàn bộ báo cáo hoặc báo lỗi cho người dùng.

## 5.8. Các yếu tố ảnh hưởng tới tính hợp lệ của kết quả

Kết quả cần được diễn giải trong các giới hạn sau. Về hợp lệ nội tại, mỗi cặp nhiệm vụ – cấu hình chỉ được chạy một lần, trong khi đầu ra của mô hình ngôn ngữ không cố định; các lần chạy thử trong quá trình phát triển cho thấy cùng một câu hỏi có thể lúc được mô hình lắp báo cáo, lúc dùng bố cục dự phòng. Về hợp lệ cấu trúc, các chỉ số tất định đo độ chính xác, truy vết, độ phủ và chi phí nhưng không đo trực tiếp chất lượng diễn giải và tính hữu ích; phần chấm điểm mù của chuyên gia được dự kiến trong thiết kế ban đầu đã không được thực hiện do giới hạn thời gian. Về hợp lệ bên ngoài, dữ liệu chỉ gồm năm ngân hàng, bốn quý của năm 2024 và bốn chỉ tiêu, và chỉ một mô hình ngôn ngữ được dùng; kết quả không đại diện cho toàn ngành ngân hàng hay cho các mô hình khác. Cuối cùng, người phát triển đồng thời là người thiết kế thực nghiệm, nên dù bộ câu hỏi, luật chấm và kế hoạch được cố định trước khi chạy, vẫn tồn tại rủi ro thiên lệch trong cách đặt câu hỏi.
