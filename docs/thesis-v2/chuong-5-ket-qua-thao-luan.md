# CHƯƠNG 5. KẾT QUẢ VÀ THẢO LUẬN

Chương này trình bày kết quả kiểm tra kỹ thuật, kết quả thực nghiệm so sánh ba cấu hình A, B, C trên bộ dữ liệu mười ngân hàng, và bốn thực nghiệm bổ sung đo độ tin cậy của chính các cơ chế kiểm soát: độ nhạy của bộ kiểm chứng câu, so sánh giữa các mô hình ngôn ngữ, kiểm tra đối kháng và đo khả năng số hóa từ báo cáo gốc. Mọi số liệu được lấy từ các tệp kết quả do chương trình ghi lại (danh mục các tệp này ở Phụ lục C); không có số nào được nhập tay.

## 5.1. Kết quả kiểm tra kỹ thuật

Phiên bản dùng cho thực nghiệm A/B/C có hơn 900 bài kiểm thử tự động phía máy chủ và 188 bài phía giao diện, tất cả đều đạt trên hệ thống tích hợp liên tục. Sau các nâng cấp ở mục 5.12 (đếm ngày 13/10/2026), bộ kiểm thử đã tăng lên 1.020 bài phía máy chủ (5 bài bị bỏ qua có chủ đích) và 235 bài phía giao diện, vẫn đạt toàn bộ. Các bài kiểm thử dùng mô hình và dữ liệu giả lập nên chỉ chứng minh hệ thống chạy đúng với các kịch bản đã mô tả. Vì vậy, hệ thống còn được chạy với mô hình thật trên bản triển khai: các luồng ở mục 4.5, gồm tra cứu, hồ sơ doanh nghiệp, so sánh, xếp hạng, xu hướng và tải lên ngân hàng mới, cho kết quả đúng ở các lần chạy thử.

Việc chạy thật cũng bộc lộ những điều kiểm thử giả lập không phát hiện. Thứ nhất, nhiều câu nhận định đúng bị loại vì prompt chưa nêu đủ quy tắc của bộ kiểm tra, được khắc phục bằng cách ghi rõ các quy tắc này vào prompt (mục 4.2.4). Thứ hai, ở phiên bản dùng cho thực nghiệm, câu hỏi hoàn toàn ngoài phạm vi (yêu cầu sáng tác thơ, dự báo giá vàng) **không** bị từ chối mà vẫn nhận một báo cáo ngành, vì bộ lập kế hoạch mặc định về kế hoạch xếp hạng khi câu hỏi không nêu ngân hàng nào (mục 5.9). Lỗi này đã được sửa sau đánh giá (mục 5.12); phần từ chối câu hỏi ở kỳ hoặc ngân hàng không có dữ liệu thì hoạt động đúng ngay từ đầu.

## 5.2. Thiết lập thực nghiệm

Bảng 5.1 liệt kê toàn bộ các thực nghiệm đã chạy và câu hỏi mà mỗi thực nghiệm trả lời. Hai phiên bản của hệ thống được dùng: phiên bản ban đầu, dùng cho thực nghiệm chính, thực nghiệm độ nhạy, so sánh mô hình và kiểm tra đối kháng; và phiên bản sau nâng cấp (mục 5.12), dùng cho lần chạy lặp và kiểm tra đối kháng sau sửa.

*Bảng 5.1: Danh mục thực nghiệm.*

| Thực nghiệm | Trả lời câu hỏi nào | Mô hình | Phiên bản | Cấu hình, số câu × số lần | Token |
|---|---|---|---|---|---|
| Thực nghiệm chính | A, B, C khác nhau thế nào (câu hỏi nghiên cứu thứ hai và thứ ba) | DeepSeek V4 Pro | Ban đầu | 3 cấu hình, 12 câu × 1 | 454.706 |
| Độ nhạy bộ kiểm chứng | Bộ kiểm chứng câu bắt được bao nhiêu loại lỗi cài vào | không gọi mô hình | — (chạy trên kết quả thực nghiệm chính) | 1.210 câu đột biến từ 129 câu đã được chấp nhận ở thực nghiệm chính | 0 |
| So sánh mô hình | Kết quả có phụ thuộc mô hình không | `gpt-5.4-nano`, `gpt-5.4-mini`, `gpt-5.6-luna` (OpenAI); DeepSeek V4 Flash, DeepSeek V4 Pro | Ban đầu | chỉ cấu hình B, 12 câu × 1 | 650.495 |
| Lặp lại so sánh mô hình | Kết quả của `gpt-5.6-luna` có ổn định khi chạy lại trên phiên bản sau nâng cấp không | `gpt-5.6-luna` | Sau nâng cấp | chỉ cấu hình B, 12 câu × 3 lần | 359.298 |
| Kiểm tra đối kháng | Hệ thống chống chịu thế nào trước câu hỏi đối kháng | `gpt-5.6-luna` | Ban đầu | 3 cấu hình, 15 câu × 1 | 462.802 |
| Kiểm tra đối kháng sau sửa | Sửa lỗi ngoài phạm vi có hiệu quả và không gây lùi không | `gpt-5.6-luna` | Sau nâng cấp | 3 cấu hình, tập con 8 câu × 1 | 210.080 |
| Số hóa từ báo cáo gốc | Khó khăn của số hóa nằm ở nhận dạng ký tự hay ở cấu trúc bảng | không gọi mô hình | — | 885 số liệu đầu vào đã chấp nhận | 0 |

Thực nghiệm chính được chạy ngày 05/10/2026 trên bộ dữ liệu mười ngân hàng đã khóa mã băm (mục 3.2.3), với mô hình DeepSeek V4 Pro. Mười hai câu hỏi ở Bảng 3.4 được chạy một lần trên mỗi cấu hình, tạo thành 36 lượt; thứ tự được xáo trộn theo một giá trị cố định để có thể lặp lại, và sáu lượt chạy đồng thời. Tổng lượng văn bản mô hình xử lý trong thực nghiệm chính là 454.706 token cho 36 lượt chạy. Sau khi chạy, hệ thống xác nhận cả mười hai câu hỏi có kế hoạch giống hệt nhau giữa ba cấu hình. Việc chấm điểm do chương trình thực hiện theo các chỉ số ở mục 3.3.4.


## 5.3. Kết quả thực nghiệm tổng hợp giữa ba cấu hình

*Bảng 5.2: Kết quả tổng hợp theo cấu hình (12 lượt mỗi cấu hình).*

| Chỉ số | A – một tác tử | B – phân cấp | C – phân cấp có phản biện |
|---|:---:|:---:|:---:|
| Trả lời được (10 câu phân tích) | 10/10 | 10/10 | 10/10 |
| Từ chối đúng (R1, R2) | 2/2 | 2/2 | 2/2 |
| Hoàn thành trọn vẹn, không ghi chú giới hạn (trên 12 lượt; hai lượt từ chối không tính) | 7 (58,3%) | 9 (75,0%) | 4 (33,3%) |
| Con số trong câu được giữ khớp với dữ kiện được trích | 100% | 100% | 100% |
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

Cả ba cấu hình đạt 100% ở chỉ số khớp số và 100% truy được về số liệu gốc. Kết quả này không phản ánh năng lực khác nhau giữa các cấu hình mà là hệ quả của thiết kế: mọi con số do công cụ tính bằng mã nguồn, và câu chỉ vào báo cáo khi bộ kiểm tra xác nhận số, thứ hạng, kỳ và chiều so sánh khớp với dữ kiện được trích; câu không khớp bị loại và được ghi lại kèm lý do.

Con số 100% là hệ quả của định nghĩa: chỉ số khớp số được đo trên các câu đã qua chính bộ kiểm chứng áp dụng quy tắc đó, nên nó không phải bằng chứng độc lập về chất lượng của mô hình viết. Nó cho biết mọi con số trong câu được giữ đều trùng với một dữ kiện đã tính và trích dẫn, nhưng **không** cho biết con số gắn đúng tên chỉ tiêu, đúng kỳ hay đúng ngân hàng. Mục 5.7 đo điểm này: một câu giữ nguyên con số đúng nhưng đổi tên chỉ tiêu vẫn lọt qua bộ kiểm chứng ở 20,8% số trường hợp thử.

Để thấy hệ thống thực sự viết ra gì, xét câu T03 ("Tỷ lệ bao phủ nợ xấu của HDB trong quý 1/2026 là bao nhiêu?") ở cấu hình B. Mô hình trả về hai câu được chấp nhận, mỗi câu kèm mã dữ kiện làm căn cứ: "Tỷ lệ bao phủ nợ xấu của HDB đạt 50,0% (hạng 10/10) trong quý 1/2026" (căn cứ: giá trị quan sát và thứ hạng của HDB) và "Trung vị tỷ lệ bao phủ nợ xấu nhóm 10 ngân hàng là 89,6% trong quý 1/2026" (căn cứ: trung vị nhóm). Các câu thể hiện đúng mức phân tích của hệ thống: nêu số, thứ hạng và vị thế so với nhóm, không giải thích nguyên nhân.

R1 (quý 3/2026) và R2 (OCB) bị từ chối đúng ở cả ba cấu hình, trước khi gọi mô hình phân tích, với thông báo tiếng Việt, danh sách dữ liệu đang có và câu hỏi gợi ý thay thế. Mười câu phân tích đều có báo cáo hợp lệ ở cả ba cấu hình. Các lượt chạy được chạy đồng thời nên thời gian tuyệt đối phụ thuộc tải của máy chủ mô hình; chỉ nên so sánh tương đối giữa các cấu hình.

## 5.4. Đánh giá hiệu quả của kiến trúc đa tác tử phân cấp so với tác tử đơn

Bảng 5.3 so sánh từng cặp cấu hình trên cùng câu hỏi. Khoảng trong ngoặc vuông là khoảng tin cậy 95%, ước lượng bằng cách lấy mẫu lại 1.000 lần từ chính các cặp câu hỏi; với 12 cặp và một lần chạy, các khoảng này chỉ mang tính tham khảo, và khoảng chứa 0 nghĩa là chưa đủ bằng chứng về khác biệt.

*Bảng 5.3: Chênh lệch giữa các cặp cấu hình (trung bình và khoảng tin cậy 95%).*

| Chỉ số | B − A | C − B | C − A |
|---|---|---|---|
| Độ phủ chỉ tiêu | +0,047 [−0,037; +0,146] | −0,063 [−0,208; +0,083] | −0,016 [−0,141; +0,089] |
| Phát hiện liên tầng mỗi lượt | 0 [0; 0] | +0,33 [0; +1,00] | +0,33 [0; +1,00] |
| Token mỗi lượt | +4.467 [+2.540; +6.317] | +17.604 [+9.164; +29.644] | +22.072 [+12.711; +34.890] |
| Thời gian xử lý (giây) | +10,0 [+5,6; +14,7] | +35,4 [+21,5; +48,3] | +45,3 [+27,7; +62,0] |

So với một tác tử, cấu hình B có độ phủ chỉ tiêu cao hơn khoảng 5 điểm phần trăm và tỷ lệ hoàn thành trọn vẹn cao hơn (9 so với 7 lượt), nhưng khoảng tin cậy của độ phủ chứa 0 nên đây mới là dấu hiệu, chưa phải kết luận. Ở cấp câu hỏi, lợi thế của B rõ nhất ở câu xu hướng của CTG (T04: 1,0 so với 0,5) và so sánh MBB – TCB (T09: 1,0 so với 0,75), nơi các chuyên viên viết riêng cho từng chỉ tiêu; ngược lại, ở hồ sơ STB (T02) A đạt độ phủ cao hơn B (0,75 so với 0,5). B cũng ít phải dùng bố cục dựng sẵn hơn (1 so với 3 báo cáo), vì điều phối viên của B nhận các câu đã được chuyên viên viết và kiểm tra, còn tác tử đơn của A phải tự viết và tự lắp toàn bộ báo cáo trong một lần gọi.

Cái giá của B là chi phí: khoảng 2,2 lần token và thêm khoảng 10 giây mỗi lượt, với khoảng tin cậy không chứa 0. Độ chính xác của con số và khả năng truy vết không khác nhau vì cùng đi qua công cụ tính toán và bộ kiểm tra câu. Tỷ lệ câu bị loại của A và B tương đương (15,4% và 17,0%), nhưng khác về lý do: A chủ yếu bị loại vì nêu xu hướng khi không có dữ kiện thay đổi (5 trên 8 câu), còn B chủ yếu vì chiều xu hướng không khớp ngưỡng đi ngang (5 trên 9 câu).

**Trả lời câu hỏi nghiên cứu thứ hai:** trong thực nghiệm này, B có độ phủ chỉ tiêu cao hơn A khoảng 5 điểm phần trăm và 9 so với 7 báo cáo hoàn thành trọn vẹn trên 12 lượt, với chi phí khoảng gấp đôi; độ chính xác của con số như nhau vì cùng đi qua bộ kiểm chứng. Tuy nhiên khoảng tin cậy của độ phủ chứa 0 và mẫu rất nhỏ, nên thực nghiệm chưa đủ để kết luận B tốt hơn A. Độ ổn định giữa các lần chạy không đo được vì mỗi cặp chỉ chạy một lần, và mức nhiễu giữa các lần chạy có thể ngang với chênh lệch A – B: một lần chạy khác của cùng mô hình DeepSeek V4 Pro (mục 5.8) loại 14 trên 56 câu (25%) so với 9 trên 53 (17%) của B ở thực nghiệm chính. Ngoài ra A và B khác nhau cả về chuyên môn hóa lẫn số lượt gọi mô hình (0,8 so với 2,1 mỗi lượt), nên không tách được hai tác động. Kết quả của B cũng thay đổi đáng kể khi đổi mô hình (mục 5.8).

## 5.5. Đánh giá tác động của cơ chế phản biện và sửa đổi có mục tiêu

Bổ sung phản biện và tối đa hai vòng sửa đổi không làm tăng độ phủ; ngược lại, độ phủ trung bình của C thấp hơn B khoảng 6 điểm phần trăm (khoảng tin cậy chứa 0). Số phát hiện liên tầng được nêu tăng gấp đôi (0,67 so với 0,33 mỗi lượt), phù hợp với việc bộ phản biện được yêu cầu kiểm tra các mâu thuẫn liên tầng đã có được nêu trong báo cáo hay chưa. Chi phí tăng mạnh: token gấp 3,1 lần B và 6,8 lần A, thêm khoảng 35 giây mỗi lượt so với B; riêng hồ sơ BID (T01) dùng 85.187 token cho một lượt.

Nguyên nhân độ phủ giảm thấy rõ khi xem các câu bị loại. C bị loại 22 trên 63 câu, trong đó 12 câu bị loại vì còn vấn đề phản biện chưa giải quyết sau hai vòng sửa. Chỉ 4 trên 12 lượt của C hoàn thành trọn vẹn. Các vấn đề còn mở khi kết thúc chủ yếu thuộc loại "tổng hợp chưa đầy đủ" (8 trên 9 vấn đề, 7 ở mức nghiêm trọng), tức bộ phản biện yêu cầu báo cáo nói thêm về các chỉ tiêu khác, ví dụ ở hồ sơ BID: báo cáo "đã bỏ sót hoàn toàn" tỷ lệ nợ xấu và bao phủ nợ xấu. Khi câu viết lại vẫn không đạt, câu bị loại, nên chính yêu cầu "nói đầy đủ hơn" lại làm báo cáo mất câu và giảm độ phủ (T01: 0,5 so với 0,75 của B; T10: 0,5 so với 1,0).

**Trả lời câu hỏi nghiên cứu thứ ba:** trong điều kiện của thực nghiệm, phản biện và sửa đổi làm chi phí tăng khoảng ba lần so với B, không cải thiện độ chính xác hay độ phủ đo được, và làm báo cáo nêu nhiều phát hiện liên tầng hơn. Bộ phản biện hiện tại hoạt động với tiêu chuẩn kiểm duyệt rất khắt khe: nó phát hiện đúng những chỗ báo cáo chưa đầy đủ, nhưng cơ chế sửa câu đơn lẻ chưa đủ để đáp ứng yêu cầu ở mức cả báo cáo, và những gì sửa không được thì bị loại bỏ.

![](experiments/er9/analysis/figure_er9_pairwise_diff.png)

Hình 5.2: Chênh lệch giữa các cặp cấu hình với khoảng tin cậy 95%

## 5.6. Phân tích theo dạng câu hỏi và cơ chế kiểm tra câu

Báo cáo thay đổi hình dạng theo dạng câu hỏi: câu tra cứu nhận thẻ trả lời một khối; hồ sơ doanh nghiệp tạo báo cáo dài nhất (5–7 khối, trung bình 5,8) với bản đồ nhiệt thứ hạng, biểu đồ tương quan và khối lưu ý; xếp hạng, xu hướng và so sánh trực diện tạo báo cáo 2–4 khối. Yêu cầu về báo cáo thích ứng theo câu hỏi thay vì một khuôn cố định vì vậy được đáp ứng.

Trên toàn thực nghiệm, 39 câu bị loại. Lý do phổ biến nhất là còn vấn đề phản biện chưa giải quyết (12 câu, chỉ ở C), chiều xu hướng không khớp ngưỡng đi ngang (11), thứ hạng không khớp (6) và nêu xu hướng khi không trích dữ kiện thay đổi (6); chỉ 2 câu bị loại vì con số không khớp. Sáu báo cáo dùng bố cục dựng sẵn thay vì bố cục do mô hình đề xuất; câu xu hướng của SHB (T05) rơi vào trường hợp này ở cả ba cấu hình vì mô hình đặt biểu đồ vào trong khối mục, trái với đặc tả báo cáo. Câu hỏi T08 (đánh đổi của VPB qua năm 2025 so với nhóm) có độ phủ thấp ở cả ba cấu hình (0,13–0,38), vì hệ thống chỉ hỗ trợ xu hướng nhiều kỳ cho riêng một ngân hàng, chưa hỗ trợ so sánh nhóm qua nhiều kỳ; báo cáo nêu rõ giới hạn này thay vì tự suy ra số liệu nhóm.

## 5.7. Kiểm định độ nhạy của bộ kiểm chứng câu nhận định

Mục 5.3 cho thấy cả ba cấu hình đều đạt 100% khớp số, nhưng con số này chỉ có ý nghĩa nếu bộ kiểm chứng thật sự bắt được câu sai. Thực nghiệm độ nhạy bộ kiểm chứng đo điều đó bằng đột biến: từ 129 câu đã được bộ kiểm chứng chấp nhận ở thực nghiệm chính, chương trình cài vào mỗi câu một lỗi thuộc một trong 12 loại (đổi số theo hướng nhỏ, đổi số theo hướng lớn, đảo hai chữ số, đổi kỳ, đổi ngân hàng, đảo chiều, đổi chỉ tiêu, thêm số không có nguồn, thêm quan hệ nhân quả hoặc khuyến nghị…), tạo 1.210 câu đột biến, rồi cho bộ kiểm chứng chạy lại. 129 câu gốc không đột biến vẫn được chấp nhận; vì các câu này vốn được chọn từ những câu đã qua bộ kiểm chứng, đây chỉ là kiểm tra tính nhất quán, không phải phép đo tỷ lệ bác bỏ nhầm.

*Bảng 5.4: Tỷ lệ bộ kiểm chứng bắt được từng loại lỗi cài vào (số liệu thô, khoảng tin cậy Wilson 95%).*

| Loại lỗi | Số câu thử | Bắt được | Tỷ lệ | Khoảng tin cậy 95% |
|---|:---:|:---:|:---:|:---:|
| Đổi số nhỏ / lớn / đảo chữ số | 96 câu mỗi loại | 96 | 100% | [96,2%; 100%] |
| Đổi thứ hạng | 46 | 46 | 100% | [92,3%; 100%] |
| Đổi mẫu số | 52 | 52 | 100% | [93,1%; 100%] |
| Số không có nguồn / nhân quả / khuyến nghị | 129 câu mỗi loại | 129 | 100% | [97,1%; 100%] |
| Đổi kỳ | 118 | 98 | 83,1% | [75,3%; 88,8%] |
| Đổi ngân hàng | 123 | 106 | 86,2% | [79,0%; 91,2%] |
| Đảo chiều | 76 | 67 | 88,2% | [79,0%; 93,6%] |
| **Đổi chỉ tiêu** | 120 | 95 | **79,2%** | [71,1%; 85,5%] |

Bộ kiểm chứng bắt tuyệt đối các lỗi về con số, thứ hạng và mẫu số, và các câu thêm khẳng định không có nguồn, nhân quả hay khuyến nghị. Nó bỏ sót đáng kể các lỗi **ngữ nghĩa** mà con số vẫn đúng: một câu giữ nguyên "50,0%" nhưng đổi "tỷ lệ bao phủ nợ xấu" thành "tỷ lệ nợ xấu" vẫn được chấp nhận ở 25 trên 120 lần thử. Đây là điểm yếu thật của thiết kế hiện tại và là cơ sở cho hạn chế ở mục 5.14.

Để hiểu các câu lọt lưới, tác giả xem lại thủ công 71 câu đột biến không bị bắt. Có 37 câu (52%) là đột biến tự quy chiếu, ví dụ "TCB vượt trội TCB" hay "giảm từ quý 2/2026 đến quý 2/2026", loại lỗi mà một mô hình thật hiếm khi viết ra nhưng bộ kiểm chứng cũng chưa có quy tắc loại bỏ. Nếu bỏ nhóm này, tỷ lệ bắt được trên các đột biến có nghĩa là 94,2% (đổi kỳ, n = 104), 100% (đổi ngân hàng, n = 102) và 95,7% (đảo chiều, n = 70), còn đổi chỉ tiêu giữ nguyên 79,2%. Cách phân loại này do tác giả thực hiện sau khi đã thấy kết quả, theo một quy tắc kinh nghiệm chứ không phải gán nhãn mù, nên số liệu thô ở Bảng 5.4 là kết quả chính; số điều chỉnh chỉ để chỉ ra điểm yếu còn lại tập trung ở đổi chỉ tiêu.

## 5.8. Đánh giá mức độ phụ thuộc vào mô hình ngôn ngữ lớn

Thực nghiệm chính chỉ dùng một mô hình. Thực nghiệm so sánh mô hình chạy lại cấu hình B (phân cấp, không phản biện) trên cùng 12 câu hỏi với năm mô hình (ba của OpenAI, hai của DeepSeek), mỗi mô hình một lần, trên cùng phiên bản ban đầu của hệ thống, nhằm xem kết luận có phụ thuộc mô hình hay không.

*Bảng 5.5: Cấu hình B trên năm mô hình (một lần chạy, phiên bản ban đầu).*

| Mô hình | Số khớp / đã kiểm | Độ phủ trung bình (lượt hoàn thành) | Câu bị loại / được viết | Từ chối đúng | Truy vết | Token |
|---|:---:|:---:|:---:|:---:|:---:|:---:|
| `gpt-5.4-nano` | 45/45 | 0,812 | 16/59 (27,1%) | 2/2 | 1,000 | 100.106 |
| `gpt-5.4-mini` | 69/69 | 0,800 | 14/62 (22,6%) | 2/2 | 1,000 | 102.225 |
| `gpt-5.6-luna` | 91/91 | 0,931 | 1/55 (1,8%) | 2/2 | 1,000 | 118.802 |
| DeepSeek V4 Flash | 46/46 | 0,725 | 3/48 (6,3%) | 2/2 | 1,000 | 219.356 |
| DeepSeek V4 Pro | 32/32 | 0,725 | 14/56 (25,0%) | 2/2 | 1,000 | 110.006 |

Độ khớp số, truy vết và từ chối đúng không đổi theo mô hình, vì các đảm bảo này đến từ lớp kiểm soát chứ không từ mô hình. Thứ thay đổi là **hiệu suất viết**: độ phủ dao động từ 0,725 đến 0,931 và tỷ lệ câu bị loại từ 1,8% đến 27,1%, tức mô hình yếu hơn vẫn an toàn nhưng báo cáo ngắn và thiếu hơn. Chênh lệch về token giữa các mô hình không tương ứng với chênh lệch về độ phủ: `gpt-5.6-luna` dùng ít token hơn DeepSeek V4 Flash nhưng có độ phủ cao hơn nhiều. Hai mô hình DeepSeek được chạy cùng giao thức và cùng mã nguồn; DeepSeek V4 Pro cũng là mô hình của thực nghiệm chính A/B/C, nên lần chạy này cho thấy mức nhiễu giữa các lần chạy của cùng một mô hình (14/56 câu bị loại, so với 9/53 của B ở thực nghiệm chính).

Để kiểm tra độ ổn định, `gpt-5.6-luna` được chạy thêm ba lần trên phiên bản sau nâng cấp (sau các nâng cấp ở mục 5.12). Vì mã nguồn khác lần đầu, đây là kiểm tra ổn định chứ không phải phép lặp thuần túy.

Ba lần chạy mới cho độ phủ 0,900, 0,925 và 0,925 (trung bình 0,917), tỷ lệ câu bị loại 7,1%, 5,1% và 7,3% (so với 1,8% của lần chạy cũ), từ chối đúng 2/2 và truy vết 1,0 ở cả ba lần. Mọi con số được kiểm đều khớp (302/302) và truy vết luôn đạt 1,0. Kết luận về mô hình `gpt-5.6-luna` vì vậy ổn định, nhưng tỷ lệ câu bị loại 1,8% của lần chạy đầu nằm ở mức thấp nhất; giá trị tiêu biểu hơn là 5–7%. Với ba lần chạy, báo cáo trung bình và khoảng nhỏ nhất – lớn nhất, không đưa khoảng tin cậy.

## 5.9. Kiểm định khả năng chống chịu trước các truy vấn đối kháng

Kiểm tra đối kháng chạy mười lăm câu hỏi đối kháng thuộc bảy nhóm lên cả ba cấu hình với `gpt-5.6-luna`: chèn chỉ dẫn vào câu hỏi (3 câu), hỏi thực thể hoặc kỳ không tồn tại (2 + 2), mồi bịa số (3), xin lời khuyên mua bán (2), tiền đề sai (1) và ngoài phạm vi (2). Kết quả kỳ vọng là hệ thống từ chối hoặc nêu rõ giới hạn, và không đưa ra con số không có nguồn, khuyến nghị đầu tư hay khẳng định theo tiền đề sai.

*Bảng 5.6: Kiểm tra đối kháng trước và sau sửa lỗi ngoài phạm vi.*

| Lần | Mã | Số câu × cấu hình | Đạt kỳ vọng mỗi cấu hình | Nhóm ngoài phạm vi | Chèn chỉ dẫn, bịa số, khuyến nghị, tiền đề sai |
|---|---|:---:|:---:|:---:|:---:|
| Kiểm tra đối kháng | Ban đầu | 15 × 3 | 13/15 (86,7%) | 0/2 | 0 vi phạm |
| Kiểm tra đối kháng sau sửa | Sau nâng cấp | 8 × 3 | 8/8 | 2/2 | 0 vi phạm |

Trước khi sửa, cả ba cấu hình giữ vững mọi nhóm tấn công, trừ nhóm ngoài phạm vi: yêu cầu sáng tác thơ và dự báo giá vàng không bị từ chối mà vẫn nhận báo cáo ngành, vì bộ lập kế hoạch mặc định về kế hoạch xếp hạng khi không có ngân hàng nào được nêu. Sau khi thêm cổng phạm vi (mục 5.12), cả hai câu bị từ chối ở cả ba cấu hình.

Lần chạy sau sửa chỉ là tập con tám câu (hai câu ngoài phạm vi và một câu đại diện của mỗi nhóm còn lại), nên chỉ cho biết sửa lỗi có hiệu quả và không gây lùi ở các nhóm được lấy mẫu, chưa phải một lần chạy lại toàn bộ. Ba cấu hình cũng cho kết quả giống hệt nhau ở mọi nhóm: khả năng chống chịu nằm ở lớp kiểm tra xác định dùng chung (hiểu câu hỏi, kiểm tra dữ liệu, bộ kiểm chứng câu), không phải ở việc phân cấp hay phản biện. Điều này củng cố kết luận của mục 5.3 và 5.4 rằng độ an toàn do kiến trúc kiểm soát mang lại chứ không do cấu hình tác tử. Cổng phạm vi hiện là bộ lọc theo dấu hiệu từ khóa và ý định phân tích, không phải bộ phân loại ý định; các câu mơ hồ hoặc diễn đạt lạ có thể bị chặn nhầm hoặc lọt qua.

## 5.10. Đánh giá thách thức trong quy trình số hóa báo cáo tài chính gốc

Hệ thống nhận số liệu từ báo cáo tài chính gốc dạng PDF, trong đó phần lớn là bản quét. Thực nghiệm này đo xem khó khăn nằm ở nhận dạng ký tự hay ở cấu trúc bảng, không gọi mô hình ngôn ngữ. Với 885 số liệu đầu vào đã được chấp nhận và có trang nguồn, thực nghiệm đo khả năng số hóa hỏi hai câu: (a) giá trị đã được chấp nhận có xuất hiện nguyên văn trong văn bản của đúng trang đó không; (b) một bộ trích xuất đơn giản (tìm dòng có nhãn gần nhất rồi lấy số ở cột tương ứng) có lấy đúng giá trị không.

*Bảng 5.7: Giá trị có mặt trên trang và độ đúng của bộ trích xuất đơn giản.*

| Phép đo | Số liệu | Kết quả |
|---|:---:|:---:|
| (a) Trang có lớp văn bản: giá trị xuất hiện nguyên văn | 185 | 178 (96%) |
| (a) Trang quét, nhận dạng Tesseract: giá trị xuất hiện nguyên văn | 700 | 652 (93%) |
| (b) Bộ trích xuất đơn giản: lấy đúng | 885 | 463 (52%) |
| (b) Không tìm thấy dòng | 885 | 236 (27%) |
| (b) Lấy sai hàng hoặc cột | 885 | 185 (21%) |
| (b) Thiếu cột để lấy | 885 | 1 |

Nhận dạng ký tự khó là nguyên nhân chính của sai sót: 93–96% giá trị xuất hiện nguyên văn trên đúng trang. Phép đo này chỉ cho biết chuỗi số có mặt trên trang, chưa chứng minh ô đó được đọc đúng vị trí, nên đây là chỉ dấu chứ không phải kết luận. Khó khăn rõ hơn nằm ở cấu trúc: bộ trích xuất đơn giản chọn đúng hàng và đúng cột chỉ khoảng một nửa số lần, và vì là một đối chứng yếu, kết quả 52% không đại diện cho các bộ trích xuất tốt hơn. Bộ trích xuất đạt 88–96% với các chỉ tiêu đứng một dòng riêng như tổng tài sản hay nợ nhóm 4, nhóm 5, nhưng chỉ 27% với lợi nhuận sau thuế và 0% với tổng vốn chủ sở hữu, vì báo cáo kết quả kinh doanh có cả cột quý lẫn cột lũy kế và vốn chủ sở hữu thường xuất hiện như một dòng tổng của mục. Kết quả này ủng hộ quyết định thiết kế giữ giá trị trích xuất ở trạng thái "ứng viên" cho đến khi được đối chiếu với đẳng thức kế toán và tính lại theo công thức được định danh phiên bản, và cho thấy quy trình số hóa của khóa luận là quy trình bán tự động có tác tử AI hỗ trợ, trong đó thẩm định độc lập là hướng mở rộng chứ chưa được thực hiện.

## 5.11. Ca STB quý 4/2025: bất thường trong dữ liệu và vai trò của hồ sơ gốc

Khi đối soát dữ liệu quý của mười ngân hàng, một bất thường được nêu: lợi nhuận sau thuế lũy kế của STB giảm từ 8.691,6 tỷ đồng (đến hết quý 3/2025) xuống 5.939,1 tỷ đồng (đến hết quý 4/2025), tức giảm 2.752,5 tỷ đồng. Lợi nhuận lũy kế trong năm thường không giảm, nên đây có thể là lỗi nhập hoặc nhầm cột. Đối chiếu với báo cáo tài chính hợp nhất đã kiểm toán và báo cáo quý 4 cho thấy con số 5.939,1 tỷ đồng là đúng: STB ghi nhận lỗ sau thuế 2.752,5 tỷ đồng riêng trong quý 4/2025, sau khi trích lập dự phòng rủi ro tín dụng 9.232,2 tỷ đồng trong quý. Dữ liệu vì thế không bị sửa.

Điều thay đổi là quy trình: bộ dựng snapshot được bổ sung kiểm tra tính đơn điệu của lợi nhuận lũy kế trong năm, và chỉ chấp nhận một khoản lỗ quý khi nó nằm trong danh sách ngoại lệ đã được kiểm chứng kèm trang nguồn. Kiểm tra bất biến kế toán là cách rẻ để đưa các điểm đáng ngờ ra để soát, còn quyết định cuối cùng thuộc về hồ sơ gốc chứ không thuộc về kết quả của quy tắc kiểm tra. Quá trình trích xuất và đối chiếu dữ liệu từ báo cáo gốc được thực hiện bán tự động, với sự kiểm tra của tác giả thông qua các ràng buộc đẳng thức kế toán; tuy nhiên, chưa có chuyên gia độc lập thứ hai thẩm định chéo.

## 5.12. Nâng cấp sau đánh giá

Sau khi thực nghiệm chính (05/10/2026) và các thực nghiệm bổ sung đã chạy trên phiên bản ban đầu, sản phẩm được nâng cấp thêm. Các nâng cấp dưới đây xảy ra sau các số liệu ở mục 5.3–5.10 và không được tính trong chúng, trừ lần chạy lặp và kiểm tra đối kháng sau sửa chạy trên phiên bản sau nâng cấp.

Các hạng mục nâng cấp gồm năm nhóm. Một là phát trực tiếp bản nháp của chuyên viên và kết luận của bộ kiểm chứng lên màn hình theo dõi. Hai là khung trượt tra cứu nguồn, hiển thị trang PDF, các hàng dữ liệu và đường truy vết của từng con số. Ba là bối cảnh thị trường như giá cổ phiếu và hệ số P/B so với ROE, gắn nhãn riêng để không trộn với số liệu báo cáo. Bốn là kiểm tra tính đơn điệu của lợi nhuận lũy kế (mục 5.11). Năm là cổng phạm vi, từ chối câu hỏi không có thực thể, chỉ tiêu hoặc ý định phân tích ngân hàng (mục 5.9). Ngoài cổng phạm vi, các nâng cấp này không làm đổi kết quả phân tích. Dữ liệu thị trường nằm ngoài phạm vi dữ liệu của Chương 3 và không được đánh giá.

## 5.13. Thảo luận

Thứ nhất, độ tin cậy về con số của báo cáo không đến từ việc chọn cấu hình tác tử nào, mà đến từ kiến trúc kiểm soát bao quanh mô hình: tính toán bằng mã nguồn, dữ kiện có nguồn và kiểm tra từng câu. Ba quan sát cùng chỉ về điều này, dù chúng không độc lập hoàn toàn vì cùng dựa vào một cơ chế kiểm soát: ba cấu hình có cùng độ khớp số (mục 5.3), ba mô hình khác nhau có cùng độ khớp số và truy vết (mục 5.8), và ba cấu hình chống chịu y hệt nhau trước câu hỏi đối kháng (mục 5.9). Với phân tích tài chính, nơi một con số sai làm mất giá trị của cả báo cáo, đây là kết luận có ý nghĩa thực tiễn.

Thứ hai, chính kiến trúc kiểm soát đó có giới hạn mà thực nghiệm độ nhạy bộ kiểm chứng đo được. Bộ kiểm chứng bảo đảm con số khớp với dữ kiện và bắt tốt lỗi về số, thứ hạng và mẫu số, nhưng bỏ sót khoảng một phần năm các câu giữ nguyên con số và đổi tên chỉ tiêu. Vì vậy khẳng định "mọi con số đều đúng" phải đi kèm khẳng định "nhưng việc con số gắn đúng chỉ tiêu, kỳ và ngân hàng mới được kiểm một phần". Giảm khoảng trống này, ví dụ bằng quy tắc kiểm tra nhãn chỉ tiêu theo cặp (chỉ tiêu, giá trị), là việc ưu tiên cho phiên bản sau.

Thứ ba, chuyên môn hóa (B) cải thiện độ đầy đủ với chi phí vừa phải, còn phản biện (C) tốn kém và trong thiết kế hiện tại có thể làm báo cáo ngắn đi. Với người phân tích dùng hệ thống theo thời gian thực, B là điểm cân bằng hợp lý; C chỉ nên dùng khi bộ phản biện được giới hạn vào các vấn đề quy tắc không kiểm được và được phép bổ sung câu mới thay vì chỉ sửa hoặc loại câu cũ. Việc đổi mô hình làm thay đổi độ đầy đủ nhiều hơn việc đổi cấu hình trong thực nghiệm so sánh mô hình, nên kết luận về B và C không nên được hiểu là độc lập với mô hình.

Thứ tư, một thực nghiệm thử trước đó trên bộ Gold v5 (năm ngân hàng, bốn quý năm 2024, ngày 30/9/2026) cho cùng xu hướng: B có độ phủ cao hơn A, C không cải thiện độ phủ và chi phí tăng theo thứ tự A < B < C. Cuối cùng, chất lượng câu phụ thuộc nhiều vào việc prompt nêu đủ quy tắc của bộ kiểm tra: trong lần chạy thử với các mô hình khác, tỷ lệ câu được giữ của cùng mô hình tăng từ khoảng 49% lên 84% sau khi ghi rõ quy tắc vào prompt, nên cách đúng là dạy mô hình viết câu đơn giản, mỗi câu một chỉ tiêu và một chiều, thay vì nới lỏng quy tắc.

## 5.14. Các yếu tố ảnh hưởng tới tính hợp lệ của kết quả

Về hợp lệ nội tại, mỗi cặp câu hỏi – cấu hình trong thực nghiệm chính chỉ chạy một lần trong khi đầu ra của mô hình không cố định, và các lượt chạy đồng thời nên thời gian xử lý chịu ảnh hưởng của tải máy chủ. Phép lặp ba lần ở mục 5.8 chỉ có cho một mô hình và một cấu hình, và chạy trên mã đã thay đổi. Về hợp lệ cấu trúc, các chỉ số tự động đo độ khớp số, truy vết, độ phủ và chi phí nhưng không đo trực tiếp chất lượng diễn giải và tính hữu ích; không có chuyên gia chấm. Thực nghiệm độ nhạy bộ kiểm chứng cho thấy bộ kiểm chứng bỏ sót khoảng 21% các câu đổi tên chỉ tiêu, nên chỉ số khớp số không loại trừ được lỗi này. Việc phân loại các đột biến lọt lưới ở mục 5.7 do chính người thiết kế thực hiện sau khi đã thấy kết quả.

Về hợp lệ bên ngoài, dữ liệu gồm mười ngân hàng niêm yết lớn nhất và bốn nhóm chỉ tiêu; A/B/C chạy trên một mô hình, cấu hình B được kiểm trên ba mô hình OpenAI và hai mô hình DeepSeek với mỗi mô hình một lần, và kiểm tra đối kháng chạy trên một mô hình với mười lăm câu, không đủ để khái quát. Bộ dữ liệu đủ 100/100 ô nên thực nghiệm chính không kiểm tra tình huống thiếu số liệu.

Về quy trình, người phát triển đồng thời là người thiết kế thực nghiệm; bộ câu hỏi, quy tắc chấm và kế hoạch được cố định trước khi chạy nhưng rủi ro thiên lệch trong cách đặt câu hỏi vẫn còn. Một số lượt chạy phải loại bỏ vì lỗi cấu hình hoặc lỗi hạ tầng của dịch vụ mô hình; các lượt này được tách riêng và không dùng trong bất kỳ bảng kết quả nào. Prompt và quy tắc kiểm tra được hiệu chỉnh qua các lần chạy thử trước thực nghiệm chính rồi cố định; lỗi ngoài phạm vi được sửa rồi kiểm lại trên các câu đã thấy, chưa trên câu ngoài phạm vi mới. Cuối cùng, các lỗi của chính hệ thống được phát hiện trong khi đánh giá (câu ngoài phạm vi không bị từ chối) đã được sửa sau khi có kết quả; kết quả kiểm tra đối kháng sau sửa vì vậy chỉ chứng minh lỗi đã được khắc phục trong tập câu đã thử, không phải hệ thống miễn nhiễm với mọi câu ngoài phạm vi.
