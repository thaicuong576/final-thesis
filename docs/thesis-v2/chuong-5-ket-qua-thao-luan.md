# CHƯƠNG 5. KẾT QUẢ VÀ THẢO LUẬN

Chương này trình bày kết quả kiểm tra kỹ thuật và kết quả thực nghiệm so sánh ba cấu hình A, B, C trên bộ dữ liệu mười ngân hàng. Mọi số liệu được lấy từ các tệp kết quả lưu cùng mã nguồn (thư mục `experiments/er9`); không có số nào được nhập tay.

## 5.1. Kết quả kiểm tra kỹ thuật

Phiên bản dùng cho thực nghiệm có hơn 900 bài kiểm thử tự động phía máy chủ và 188 bài phía giao diện, tất cả đều đạt trên hệ thống tích hợp liên tục. Các bài kiểm thử dùng mô hình và dữ liệu giả lập nên chỉ chứng minh hệ thống chạy đúng với các kịch bản đã mô tả. Vì vậy, hệ thống còn được chạy với mô hình thật trên bản triển khai: toàn bộ luồng ở mục 4.5, gồm tra cứu, hồ sơ doanh nghiệp, so sánh, xếp hạng, xu hướng, từ chối câu hỏi ngoài phạm vi và tải lên ngân hàng mới, đều cho kết quả đúng. Quá trình chạy thật cũng bộc lộ những lỗi mà kiểm thử giả lập không phát hiện; tiêu biểu là các câu nhận định đúng nhưng bị loại vì lời nhắc chưa nêu đủ quy tắc của bộ kiểm tra, được khắc phục bằng cách ghi rõ các quy tắc này vào lời nhắc (mục 4.2.4).

## 5.2. Thiết lập thực nghiệm

Thực nghiệm được chạy ngày 05/10/2026 trên bộ dữ liệu mười ngân hàng đã khóa mã băm (mục 3.2.3), với mô hình DeepSeek V4 Pro (`deepseek-v4-pro-0813`). Mười hai câu hỏi ở Bảng 3.4 được chạy một lần trên mỗi cấu hình, tạo thành 36 lượt; thứ tự được xáo trộn theo một giá trị cố định để có thể lặp lại, và sáu lượt chạy đồng thời. Tổng lượng văn bản mô hình xử lý là 454.706 token, dưới giới hạn 3.000.000 token đặt trước. Sau khi chạy, hệ thống xác nhận cả mười hai câu hỏi có kế hoạch giống hệt nhau giữa ba cấu hình. Việc chấm điểm do chương trình thực hiện theo các chỉ số ở mục 3.3.4.

## 5.3. Kết quả tổng hợp

*Bảng 5.1: Kết quả tổng hợp theo cấu hình (12 lượt mỗi cấu hình).*

| Chỉ số | A – một tác tử | B – phân cấp | C – phân cấp có phản biện |
|---|:---:|:---:|:---:|
| Trả lời được (10 câu phân tích) | 10/10 | 10/10 | 10/10 |
| Từ chối đúng (R1, R2) | 2/2 | 2/2 | 2/2 |
| Hoàn thành trọn vẹn, không ghi chú giới hạn (trên 12) | 7 (58,3%) | 9 (75,0%) | 4 (33,3%) |
| Tính đúng số | 100% | 100% | 100% |
| Truy được về số liệu gốc | 100% | 100% | 100% |
| Độ phủ chỉ tiêu bắt buộc | 0,797 | 0,844 | 0,781 |
| Câu bị loại / câu được viết | 8/52 (15,4%) | 9/53 (17,0%) | 22/63 (34,9%) |
| Báo cáo dùng bố cục dựng sẵn (trên 10) | 3 | 1 | 2 |
| Phát hiện liên tầng trung bình mỗi lượt | 0,33 | 0,33 | 0,67 |
| Thời gian xử lý trung bình | 17,5 giây | 27,5 giây | 62,9 giây |
| Số lượt gọi mô hình trung bình | 0,8 | 2,1 | 4,4 |
| Token trung bình mỗi lượt | 3.784 | 8.252 | 25.856 |
| Số vòng sửa đổi trung bình | 0 | 0 | 1,25 |

![](experiments/er9/analysis/figure_er9_cost_latency.png)

Hình 5.1: Chi phí vận hành theo cấu hình (thời gian xử lý và token)

Cả ba cấu hình đạt 100% tính đúng số và 100% truy được về số liệu gốc. Kết quả này không phản ánh năng lực khác nhau giữa các cấu hình mà là hệ quả của thiết kế: mọi con số do công cụ tính bằng mã nguồn, và câu chỉ vào báo cáo khi bộ kiểm tra xác nhận số, thứ hạng, kỳ và chiều so sánh khớp với dữ kiện được trích. Kiến trúc chuyển rủi ro "sai số" của mô hình thành rủi ro "câu bị loại", và mọi câu bị loại được ghi lại kèm lý do.

R1 (quý 3/2026) và R2 (OCB) bị từ chối đúng ở cả ba cấu hình, trước khi gọi mô hình phân tích, với thông báo tiếng Việt, danh sách dữ liệu đang có và câu hỏi gợi ý thay thế. Mười câu phân tích đều có báo cáo hợp lệ ở cả ba cấu hình. Các lượt chạy được chạy đồng thời nên thời gian tuyệt đối phụ thuộc tải của máy chủ mô hình; chỉ nên so sánh tương đối giữa các cấu hình.

## 5.4. Trả lời RQ2: phân cấp B so với một tác tử A

Bảng 5.2 so sánh từng cặp cấu hình trên cùng câu hỏi. Khoảng trong ngoặc vuông là khoảng tin cậy 95%, ước lượng bằng cách lấy mẫu lại 1.000 lần từ chính các cặp câu hỏi; với 12 cặp và một lần chạy, các khoảng này chỉ mang tính tham khảo, và khoảng chứa 0 nghĩa là chưa đủ bằng chứng về khác biệt.

*Bảng 5.2: Chênh lệch giữa các cặp cấu hình (trung bình và khoảng tin cậy 95%).*

| Chỉ số | B − A | C − B | C − A |
|---|---|---|---|
| Độ phủ chỉ tiêu | +0,047 [−0,037; +0,146] | −0,063 [−0,208; +0,083] | −0,016 [−0,141; +0,089] |
| Phát hiện liên tầng mỗi lượt | 0 [0; 0] | +0,33 [0; +1,00] | +0,33 [0; +1,00] |
| Token mỗi lượt | +4.467 [+2.540; +6.317] | +17.604 [+9.164; +29.644] | +22.072 [+12.711; +34.890] |
| Thời gian xử lý (giây) | +10,0 [+5,6; +14,7] | +35,4 [+21,5; +48,3] | +45,3 [+27,7; +62,0] |

So với một tác tử, cấu hình B có độ phủ chỉ tiêu cao hơn khoảng 5 điểm phần trăm và tỷ lệ hoàn thành trọn vẹn cao hơn (9 so với 7 lượt), nhưng khoảng tin cậy của độ phủ chứa 0 nên đây mới là dấu hiệu, chưa phải kết luận. Ở cấp câu hỏi, lợi thế của B rõ nhất ở câu xu hướng của CTG (T04: 1,0 so với 0,5) và so sánh MBB – TCB (T09: 1,0 so với 0,75), nơi các chuyên viên viết riêng cho từng chỉ tiêu; ngược lại, ở hồ sơ STB (T02) A đạt độ phủ cao hơn B (0,75 so với 0,5). B cũng ít phải dùng bố cục dựng sẵn hơn (1 so với 3 báo cáo), vì điều phối viên của B nhận các câu đã được chuyên viên viết và kiểm tra, còn tác tử đơn của A phải tự viết và tự lắp toàn bộ báo cáo trong một lần gọi.

Cái giá của B là chi phí: khoảng 2,2 lần token và thêm khoảng 10 giây mỗi lượt, với khoảng tin cậy không chứa 0. Độ chính xác và khả năng truy vết không khác nhau vì cùng đi qua công cụ tính toán và bộ kiểm tra câu. Tỷ lệ câu bị loại của A và B tương đương (15,4% và 17,0%), nhưng khác về lý do: A chủ yếu bị loại vì nêu xu hướng khi không có dữ kiện thay đổi (5 trên 8 câu), còn B chủ yếu vì chiều xu hướng không khớp ngưỡng đi ngang (5 trên 9 câu).

**Trả lời RQ2:** trong trường hợp nghiên cứu này, chuyên môn hóa nhiệm vụ cải thiện vừa phải độ đầy đủ và độ ổn định của báo cáo với chi phí khoảng gấp đôi, trong khi độ chính xác số liệu được bảo đảm như nhau bởi cơ chế kiểm tra chung.

## 5.5. Trả lời RQ3: bổ sung phản biện và sửa đổi (C so với B)

Bổ sung phản biện và tối đa hai vòng sửa đổi không làm tăng độ phủ; ngược lại, độ phủ trung bình của C thấp hơn B khoảng 6 điểm phần trăm (khoảng tin cậy chứa 0). Số phát hiện liên tầng được nêu tăng gấp đôi (0,67 so với 0,33 mỗi lượt), phù hợp với việc bộ phản biện được yêu cầu kiểm tra các mâu thuẫn liên tầng đã có được nêu trong báo cáo hay chưa. Chi phí tăng mạnh: token gấp 3,1 lần B và 6,8 lần A, thêm khoảng 35 giây mỗi lượt so với B; riêng hồ sơ BID (T01) dùng 85.187 token cho một lượt.

Nguyên nhân độ phủ giảm thấy rõ khi xem các câu bị loại. C bị loại 22 trên 63 câu, trong đó 12 câu bị loại vì còn vấn đề phản biện chưa giải quyết sau hai vòng sửa. Chỉ 4 trên 12 lượt của C hoàn thành trọn vẹn. Các vấn đề còn mở khi kết thúc chủ yếu thuộc loại "tổng hợp chưa đầy đủ" (8 trên 9 vấn đề, 7 ở mức nghiêm trọng), tức bộ phản biện yêu cầu báo cáo nói thêm về các chỉ tiêu khác, ví dụ ở hồ sơ BID: báo cáo "đã bỏ sót hoàn toàn" tỷ lệ nợ xấu và bao phủ nợ xấu. Khi câu viết lại vẫn không đạt, câu bị loại, nên chính yêu cầu "nói đầy đủ hơn" lại làm báo cáo mất câu và giảm độ phủ (T01: 0,5 so với 0,75 của B; T10: 0,5 so với 1,0).

**Trả lời RQ3:** trong điều kiện của thực nghiệm, phản biện và sửa đổi làm chi phí tăng khoảng ba lần so với B, không cải thiện độ chính xác hay độ phủ đo được, và làm báo cáo nêu nhiều phát hiện liên tầng hơn. Bộ phản biện hiện tại hoạt động như một người biên tập khó tính: nó phát hiện đúng những chỗ báo cáo chưa đầy đủ, nhưng cơ chế sửa câu đơn lẻ chưa đủ để đáp ứng yêu cầu ở mức cả báo cáo, và những gì sửa không được thì bị loại bỏ.

![](experiments/er9/analysis/figure_er9_pairwise_diff.png)

Hình 5.2: Chênh lệch giữa các cặp cấu hình với khoảng tin cậy 95%

## 5.6. Phân tích theo dạng câu hỏi và cơ chế kiểm tra câu

Báo cáo thay đổi hình dạng theo dạng câu hỏi: câu tra cứu nhận thẻ trả lời một khối; hồ sơ doanh nghiệp tạo báo cáo dài nhất (5–7 khối, trung bình 5,8) với bản đồ nhiệt thứ hạng, biểu đồ tương quan và khối lưu ý; xếp hạng, xu hướng và so sánh trực diện tạo báo cáo 2–4 khối. Yêu cầu về báo cáo thích ứng theo câu hỏi thay vì một khuôn cố định vì vậy được đáp ứng.

Trên toàn thực nghiệm, 39 câu bị loại. Lý do phổ biến nhất là còn vấn đề phản biện chưa giải quyết (12 câu, chỉ ở C), chiều xu hướng không khớp ngưỡng đi ngang (11), thứ hạng không khớp (6) và nêu xu hướng khi không trích dữ kiện thay đổi (6); chỉ 2 câu bị loại vì con số không khớp. Sáu báo cáo dùng bố cục dựng sẵn thay vì bố cục do mô hình đề xuất; câu xu hướng của SHB (T05) rơi vào trường hợp này ở cả ba cấu hình vì mô hình đặt biểu đồ vào trong khối mục, trái với đặc tả báo cáo. Câu hỏi T08 (đánh đổi của VPB qua năm 2025 so với nhóm) có độ phủ thấp ở cả ba cấu hình (0,13–0,38), vì hệ thống chỉ hỗ trợ xu hướng nhiều kỳ cho riêng một ngân hàng, chưa hỗ trợ so sánh nhóm qua nhiều kỳ; báo cáo nêu rõ giới hạn này thay vì tự suy ra số liệu nhóm.

## 5.7. Thảo luận

Thứ nhất, độ tin cậy về số liệu của báo cáo không đến từ việc chọn cấu hình tác tử nào, mà đến từ kiến trúc kiểm soát bao quanh mô hình: tính toán bằng mã nguồn, dữ kiện có nguồn và kiểm tra từng câu. Với phân tích tài chính, nơi một con số sai làm mất giá trị của cả báo cáo, đây là kết luận có ý nghĩa thực tiễn.

Thứ hai, chuyên môn hóa (B) cải thiện độ đầy đủ với chi phí vừa phải, còn phản biện (C) tốn kém và trong thiết kế hiện tại có thể làm báo cáo ngắn đi. Với chuyên viên phân tích dùng hệ thống theo thời gian thực, B là điểm cân bằng hợp lý; C chỉ nên dùng khi bộ phản biện được giới hạn vào các vấn đề quy tắc không kiểm được và được phép bổ sung câu mới thay vì chỉ sửa hoặc loại câu cũ.

Thứ ba, một thực nghiệm thử trước đó trên bộ Gold v5 (năm ngân hàng, bốn quý năm 2024, ngày 30/9/2026) cho cùng xu hướng: B có độ phủ cao hơn A, C không cải thiện độ phủ, chi phí tăng theo thứ tự A < B < C, và không có báo cáo nào của C hoàn thành trọn vẹn. Sự nhất quán giữa hai bộ dữ liệu khác nhau làm các nhận định trên đáng tin hơn, dù mỗi thực nghiệm chỉ chạy một lần.

Thứ tư, chất lượng câu phụ thuộc nhiều vào việc lời nhắc nêu đủ quy tắc của bộ kiểm tra. Trong lần chạy thử với các mô hình khác trước khi sửa lời nhắc, gần một nửa số câu đúng bị loại vì vi phạm những quy tắc không được nêu ra; sau khi ghi rõ quy tắc vào lời nhắc, tỷ lệ câu được giữ của cùng mô hình tăng từ khoảng 49% lên 84%. Bộ kiểm tra khắt khe là chủ ý của thiết kế, nên cách đúng là dạy mô hình viết câu đơn giản, mỗi câu một chỉ tiêu và một chiều, thay vì nới lỏng quy tắc.

## 5.8. Các yếu tố ảnh hưởng tới tính hợp lệ của kết quả

Về hợp lệ nội tại, mỗi cặp câu hỏi – cấu hình chỉ chạy một lần trong khi đầu ra của mô hình không cố định, và các lượt chạy đồng thời nên thời gian xử lý chịu ảnh hưởng của tải máy chủ. Về hợp lệ cấu trúc, các chỉ số tự động đo độ chính xác, truy vết, độ phủ và chi phí nhưng không đo trực tiếp chất lượng diễn giải và tính hữu ích; không có chuyên gia chấm. Bộ dữ liệu đủ 100/100 ô nên thực nghiệm không kiểm tra tình huống thiếu số liệu. Về hợp lệ bên ngoài, dữ liệu gồm mười ngân hàng niêm yết lớn nhất, bốn chỉ tiêu và một mô hình ngôn ngữ, nên kết quả không đại diện cho toàn ngành hay cho các mô hình khác. Cuối cùng, người phát triển đồng thời là người thiết kế thực nghiệm; bộ câu hỏi, quy tắc chấm và kế hoạch được cố định trước khi chạy nhưng rủi ro thiên lệch trong cách đặt câu hỏi vẫn còn.
