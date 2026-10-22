# CHƯƠNG 5. KẾT QUẢ VÀ THẢO LUẬN

Chương này trình bày kết quả kiểm tra kỹ thuật và kết quả so sánh các cấu hình A, B, C với đối chứng D (không gọi mô hình) trên bộ dữ liệu mười ngân hàng. Tiếp theo là các thực nghiệm bổ sung về độ nhạy của bộ kiểm chứng, độ phụ thuộc vào mô hình, khả năng chống chịu đối kháng và khả năng số hóa từ báo cáo gốc. Phần cuối bàn về tính khả thi, chi phí và điều kiện áp dụng.

Các số liệu thực nghiệm được tính từ tệp kết quả do chương trình ghi lại (Phụ lục C). Có hai ngoại lệ do tác giả thực hiện: phép chấm câu trả lời của mô hình phổ thông (mục 1.3) và phép phân loại thủ công các đột biến không bị phát hiện (mục 5.7).

## 5.1. Kết quả kiểm tra kỹ thuật

Phiên bản dùng cho thực nghiệm A/B/C có hơn 900 bài kiểm thử tự động phía máy chủ và 188 bài phía giao diện, tất cả đều đạt trên hệ thống tích hợp liên tục; sau các nâng cấp ở mục 5.12, con số này là 1.020 và 235 bài, vẫn đạt toàn bộ. Các bài kiểm thử dùng mô hình và dữ liệu giả lập nên chỉ chứng minh hệ thống chạy đúng với các kịch bản đã mô tả; nên hệ thống còn được chạy với mô hình thật trên bản triển khai ở các luồng của mục 4.5, cho kết quả đúng ở các lần chạy thử.

Việc chạy thật bộc lộ hai điều mà kiểm thử giả lập không phát hiện: nhiều câu đúng bị loại vì chỉ dẫn cho mô hình chưa nêu đủ quy tắc của bộ kiểm chứng (mục 4.2.4), và ở phiên bản dùng cho thực nghiệm, câu hỏi ngoài phạm vi (sáng tác thơ, dự báo giá vàng) không bị từ chối mà vẫn nhận báo cáo ngành (mục 5.9). Lỗi này đã được sửa sau đánh giá (mục 5.12).

## 5.2. Thiết lập thực nghiệm

Bảng 5.1 liệt kê toàn bộ các thực nghiệm đã chạy và câu hỏi mà mỗi thực nghiệm trả lời. Hai phiên bản của hệ thống được dùng: phiên bản ban đầu, dùng cho thực nghiệm chính, cấu hình D lần đầu, so sánh mô hình và kiểm tra đối kháng; và phiên bản sau nâng cấp (mục 5.12), dùng cho lần chạy lặp, kiểm tra đối kháng sau sửa và, sau khi thêm hai quy tắc kiểm tra mới (mục 4.2.5), cho lần chạy lại A/B/C trên `gpt-5.6-luna` và phép đo độ nhạy lần hai.

*Bảng 5.1: Danh mục thực nghiệm.*

| Thực nghiệm | Trả lời câu hỏi | Mô hình | Số câu × số lần | Token |
|---|---|---|---|---|
| Thực nghiệm chính | A, B, C khác nhau thế nào | DeepSeek V4 Pro | 3 cấu hình, 12 × 1 | 454.706 |
| Cấu hình D | Độ phủ khi không dùng mô hình | không gọi mô hình | D, 12 × 1, hai lần | 0 |
| Chạy lại A/B/C | Kết luận giữ trên mô hình mạnh hơn không | `gpt-5.6-luna` | 3 cấu hình, 12 × 1 | 658.442 |
| Độ nhạy bộ kiểm chứng | Bắt được bao nhiêu loại lỗi, trước và sau hai quy tắc mới | không gọi mô hình | 3 bộ × 1.210 câu đột biến | 0 |
| So sánh mô hình | Kết quả có phụ thuộc mô hình không | ba mô hình OpenAI, hai mô hình DeepSeek | chỉ B, 12 × 1 | 650.495 |
| Lặp lại so sánh mô hình | `gpt-5.6-luna` có ổn định không | `gpt-5.6-luna` | chỉ B, 12 × 3 | 359.298 |
| Kiểm tra đối kháng | Chống chịu câu hỏi đối kháng | `gpt-5.6-luna` | 3 cấu hình, 15 × 1 | 462.802 |
| Đối kháng sau sửa | Sửa lỗi ngoài phạm vi có hiệu quả không | `gpt-5.6-luna` | 3 cấu hình, 8 × 1 | 210.080 |
| Số hóa từ báo cáo gốc | Khó ở nhận dạng ký tự hay cấu trúc bảng | không gọi mô hình | 885 số liệu | 0 |
| Mô hình phổ thông không công cụ (mục 1.3) | Người dùng gặp gì khi hỏi thẳng mô hình phổ thông | `gpt-5.6-luna` | 10 × 1 | 14.060 |


## 5.3. Kết quả thực nghiệm tổng hợp giữa các cấu hình

*Bảng 5.2: Kết quả tổng hợp theo cấu hình (mô hình DeepSeek V4 Pro, 12 lượt mỗi cấu hình).*

| Chỉ số | A - một tác tử | B - phân cấp | C - phân cấp có phản biện | D - chỉ dùng câu mẫu |
|---|:---:|:---:|:---:|:---:|
| Hoàn thành trọn vẹn, không ghi chú giới hạn (trên 10 câu phân tích; hai câu từ chối không tính) | 7/10 (70,0%) | 9/10 (90,0%) | 4/10 (40,0%) | 10/10 (100,0%) |
| Con số trong câu được giữ khớp với dữ kiện được trích | 100,0% | 100,0% | 100,0% | 100,0% |
| Truy được về số liệu gốc | 100,0% | 100,0% | 100,0% | 100,0% |
| Độ phủ chỉ tiêu bắt buộc (trung bình 12 lượt) | 0,797 | 0,844 | 0,781 | 0,698 |
| Độ phủ chỉ tiêu bắt buộc (trung bình 10 câu phân tích) | 0,756 | 0,812 | 0,738 | 0,637 |
| Câu bị loại / câu được viết | 8/52 (15,4%) | 9/53 (17,0%) | 22/63 (34,9%) | 6/60 (10,0%) |
| Phát hiện chéo trung bình mỗi lượt | 0,33 | 0,33 | 0,67 | 0,42 |
| Thời gian xử lý trung bình (12 lượt) | 17,5 giây | 27,5 giây | 62,9 giây | 3,8 giây |
| Thời gian xử lý trung bình (10 câu phân tích) | 20,8 giây | 32,8 giây | 75,3 giây | 4,5 giây |
| Số lượt gọi mô hình trung bình (12 lượt) | 0,8 | 2,1 | 4,4 | 0 |
| Token trung bình mỗi lượt (12 lượt) | 3.784 | 8.252 | 25.856 | 0 |

![](experiments/er9/analysis/figure_er9_cost_latency.png)

Hình 5.1: Chi phí vận hành theo cấu hình A, B, C (thời gian xử lý và token)

Cấu hình D là đối chứng không có mô hình: cùng kế hoạch, dữ kiện và bộ kiểm chứng câu như ba cấu hình kia, nhưng mọi câu lấy từ mẫu câu dựng sẵn từ dữ kiện (mục 4.2.4). Kế hoạch của D trùng mã băm với A, B, C ở cả 12 câu. Cả bốn cấu hình đạt 100% khớp số và 100% truy được về số liệu gốc. Kết quả này do thiết kế: mọi con số do mã tính, và câu chỉ vào báo cáo khi bộ kiểm chứng xác nhận số, thứ hạng, kỳ và chiều so sánh. Vì chỉ số được đo trên các câu đã qua chính bộ kiểm chứng, nó không phải bằng chứng độc lập về chất lượng của mô hình viết và không phân biệt được các cách tổ chức tác tử (D không có mô hình cũng đạt 100%). Chỉ số cũng không cho biết con số có gắn đúng tên chỉ tiêu, kỳ hay ngân hàng hay không. Mục 5.7 đo điểm này: lỗi đổi tên chỉ tiêu bị bỏ sót ở 20,8% số trường hợp thử, còn 0,8% sau khi bổ sung quy tắc nhãn chỉ tiêu.

**Cấu hình D cho biết mô hình đóng góp gì.** D có độ phủ thấp nhất (0,637 trên 10 câu phân tích so với 0,756 của A và 0,812 của B) nhưng không tốn token và chạy trong khoảng 4 giây; so với B, D hòa 6 câu, thua 4 và không thắng câu nào (Bảng 5.3). D ngang B ở các câu chỉ cần một chỉ tiêu hoặc một thứ hạng (T03, T06, T07, T10) và kém hẳn ở các câu cần nhiều chỉ tiêu cùng lúc (T01, T02, T09), vì mỗi mẫu câu chỉ nêu một dữ kiện. Giá trị của mô hình ở đây là gom nhiều chỉ tiêu vào một câu mạch lạc, không phải độ chính xác của con số. D đạt tỷ lệ hoàn thành trọn vẹn cao nhất (10/10) vì không có câu nào cần sửa, nên chỉ số này không đo chất lượng. Các chỉ số tự động cũng không đo độ trôi chảy hay mức dễ đọc, nên chưa thể dựa vào phép so sánh D với B để cho rằng mô hình là không cần thiết.

R1 (quý 3/2026) và R2 (OCB) bị từ chối đúng ở cả bốn cấu hình, trước khi gọi mô hình phân tích, với thông báo tiếng Việt, danh sách dữ liệu đang có và câu hỏi gợi ý. Các lượt chạy đồng thời nên thời gian tuyệt đối chịu ảnh hưởng của tải máy chủ; chỉ nên so sánh tương đối.

## 5.4. Đánh giá hiệu quả của kiến trúc đa tác tử phân cấp so với tác tử đơn

Với 10 câu phân tích và một lần chạy mỗi cặp, độ phủ chỉ nhận một vài giá trị rời rạc (0,125 mỗi bước), nên khóa luận không ước lượng khoảng tin cậy mà trình bày từng câu và đếm số câu thắng, hòa, thua. Bảng 5.3 là độ phủ theo từng câu và cấu hình; token và thời gian trung bình ở Bảng 5.2 (số liệu từng câu nằm trong tệp kết quả, Phụ lục C).

*Bảng 5.3: Độ phủ chỉ tiêu bắt buộc theo từng câu phân tích và cấu hình (DeepSeek V4 Pro).*

| Câu | Dạng câu hỏi | A | B | C | D |
|---|---|:---:|:---:|:---:|:---:|
| T01 | Hồ sơ doanh nghiệp | 0,75 | 0,75 | 0,50 | 0,25 |
| T02 | Hồ sơ doanh nghiệp | 0,75 | 0,50 | 1,00 | 0,25 |
| T03 | Tra cứu | 1,00 | 1,00 | 1,00 | 1,00 |
| T04 | Xu hướng | 0,50 | 1,00 | 0,50 | 0,50 |
| T05 | Xu hướng | 0,50 | 0,50 | 0,75 | 0,50 |
| T06 | Xếp hạng | 1,00 | 1,00 | 1,00 | 1,00 |
| T07 | Xếp hạng | 1,00 | 1,00 | 1,00 | 1,00 |
| T08 | Hồ sơ nhiều kỳ | 0,31 | 0,38 | 0,12 | 0,38 |
| T09 | So sánh trực diện | 0,75 | 1,00 | 1,00 | 0,50 |
| T10 | So sánh trực diện | 1,00 | 1,00 | 0,50 | 1,00 |

Về độ phủ, B thắng 3, hòa 6, thua 1 so với A: B hơn ở T04 (1,0 so với 0,5), T08 (0,38 so với 0,31) và T09 (1,0 so với 0,75), nơi các chuyên viên viết riêng cho từng chỉ tiêu; A hơn ở hồ sơ STB (T02: 0,75 so với 0,50). Chênh lệch này nhỏ: với một lần chạy và 10 câu, một câu đổi kết quả đã làm đổi cán cân, nên đây là dấu hiệu chứ chưa phải kết luận.

Cái giá của B là chi phí: tiêu tốn nhiều token hơn A ở cả 10 câu (khoảng 2,2 lần) và thêm khoảng 12 giây mỗi lượt, trong khi độ chính xác của con số và khả năng truy nguyên nguồn không khác nhau vì cùng đi qua công cụ tính toán và bộ kiểm chứng câu.

**Trả lời câu hỏi nghiên cứu thứ hai:** trong thực nghiệm chính với DeepSeek V4 Pro, B có độ phủ cao hơn A (0,812 so với 0,756 trên 10 câu phân tích; thắng 3, hòa 6, thua 1) và hoàn thành trọn vẹn 9 so với 7 báo cáo, với chi phí khoảng gấp đôi. Có hai ràng buộc khi đọc kết quả này. A và B khác nhau ở hai yếu tố cùng lúc, là chuyên môn hóa và số lượt gọi mô hình (0,8 so với 2,1 mỗi lượt), nên không tách được tác động riêng. Ngoài ra, độ phủ của B thay đổi theo mô hình nhiều hơn chênh lệch giữa B và A: trên gpt-5.6-luna, độ phủ của A, B, C đều là 0,912 (mục 5.8). Mỗi cặp chỉ chạy một lần và mức nhiễu giữa các lần chạy có thể ngang chênh lệch A - B (một lần chạy khác của DeepSeek V4 Pro loại 14/56 câu so với 9/53 của B), nên thực nghiệm chưa đủ để kết luận B tốt hơn A.

## 5.5. Đánh giá tác động của cơ chế phản biện và sửa đổi có mục tiêu

Bổ sung phản biện và tối đa hai vòng sửa đổi không làm tăng độ phủ: C đạt 0,738 so với 0,812 của B (10 câu phân tích), thắng 2, hòa 4, thua 4 câu (Bảng 5.3), trong khi số phát hiện chéo tăng gấp đôi (0,67 so với 0,33 mỗi lượt). Chi phí tăng mạnh: token gấp 3,1 lần B và 6,8 lần A, thêm khoảng 42 giây mỗi lượt; riêng hồ sơ BID (T01) dùng 85.187 token cho một lượt.

Độ phủ giảm vì câu bị loại: C bị loại 22/63 câu, trong đó 12 câu vì còn vấn đề phản biện chưa giải quyết sau hai vòng sửa, nên chỉ 4/10 câu phân tích hoàn thành trọn vẹn. Các vấn đề còn mở chủ yếu là "tổng hợp chưa đầy đủ" (8/9): bộ phản biện yêu cầu nói thêm về chỉ tiêu khác (ví dụ báo cáo BID "đã bỏ sót hoàn toàn" tỷ lệ nợ xấu), và khi câu viết lại vẫn không đạt thì câu bị loại, làm báo cáo mất câu (T01: 0,5 so với 0,75 của B; T10: 0,5 so với 1,0).

Trên `gpt-5.6-luna` (mục 5.8), độ phủ của C vẫn bằng B và A (0,912), nhưng chỉ 2/10 câu hoàn thành trọn vẹn (B: 10/10), 30/85 câu bị loại (B: 1/50), token gấp 3,9 lần và thời gian gấp 3,0 lần B.

**Trả lời câu hỏi nghiên cứu thứ ba:** ở cả hai mô hình, phản biện và sửa đổi làm chi phí tăng ba đến bốn lần so với B, không cải thiện độ phủ, làm giảm tỷ lệ hoàn thành trọn vẹn và làm báo cáo nêu nhiều phát hiện chéo hơn. Bộ phản biện phát hiện đúng những chỗ báo cáo chưa đầy đủ, nhưng cơ chế sửa câu đơn lẻ chưa đủ để đáp ứng yêu cầu ở mức cả báo cáo, và những gì sửa không được thì bị loại bỏ.

## 5.6. Phân tích theo dạng câu hỏi và cơ chế kiểm tra câu

Báo cáo thay đổi hình dạng theo dạng câu hỏi: câu tra cứu nhận thẻ trả lời một khối; hồ sơ doanh nghiệp tạo báo cáo dài nhất (5-7 khối); xếp hạng, xu hướng và so sánh trực diện tạo báo cáo 2-4 khối.

Trên toàn thực nghiệm, 39 câu bị loại; lý do phổ biến nhất là còn vấn đề phản biện chưa giải quyết (12 câu, chỉ ở C), chiều xu hướng không khớp ngưỡng đi ngang (11), thứ hạng không khớp (6) và nêu xu hướng khi không trích dữ kiện thay đổi (6); chỉ 2 câu bị loại vì con số không khớp. Câu T08 (đánh đổi của VPB qua năm 2025 so với nhóm) có độ phủ thấp ở cả ba cấu hình (0,13-0,38) vì hệ thống chỉ hỗ trợ xu hướng nhiều kỳ cho một ngân hàng, chưa hỗ trợ so sánh nhóm qua nhiều kỳ; báo cáo nêu rõ giới hạn này thay vì tự suy ra số liệu nhóm.

Nhật ký của mười lượt phân tích ở cấu hình B cho thấy lượng việc được huy động thay đổi theo dạng câu hỏi: câu tra cứu (T03) và xếp hạng (T06, T07) chỉ gọi một công cụ và một chuyên viên; câu so sánh (T09, T10) gọi một hoặc hai công cụ; câu xu hướng (T04, T05, T08) gọi hai công cụ (xu hướng và vị thế so với nhóm) nên cần cả hai chuyên viên; hồ sơ doanh nghiệp (T01, T02) gọi ba công cụ. So với một quy trình cố định luôn gọi cả hai chuyên viên và ba công cụ (20 lượt giao việc, 30 lần gọi công cụ cho mười câu), B dùng 15 lượt giao việc và 18 lần gọi công cụ. Đây là phép so với một quy trình giả định, không phải thực nghiệm riêng về tính thích ứng, nên yêu cầu FR4 và nguyên tắc NT3 chỉ được kiểm một phần.

## 5.7. Kiểm định độ nhạy của bộ kiểm chứng câu nhận định

Con số 100% khớp số ở mục 5.3 chỉ có ý nghĩa nếu bộ kiểm chứng thật sự phát hiện được câu sai. Thực nghiệm độ nhạy đo điều đó bằng đột biến, không gọi mô hình. Từ 129 câu đã được chấp nhận ở thực nghiệm chính, chương trình cài vào mỗi câu một lỗi thuộc một trong 12 loại (đổi số nhỏ, đổi số lớn, đảo chữ số, đổi kỳ, đổi ngân hàng, đảo chiều, đổi chỉ tiêu, đổi thứ hạng, đổi mẫu số, thêm số không nguồn, thêm quan hệ nhân quả, thêm khuyến nghị). Kết quả là 1.210 câu đột biến, được cho bộ kiểm chứng chạy lại.

Phép đo được làm hai lần, trước và sau khi thêm hai quy tắc ở mục 4.2.5. Quy tắc nhãn chỉ tiêu khớp cụm dài nhất trước và bắt buộc trùng chỉ tiêu của dữ kiện. Quy tắc thứ hai loại câu tự so sánh, tức câu có cùng ngân hàng hoặc cùng kỳ ở hai vế. Hai quy tắc được đề xuất sau khi lần đo đầu cho thấy điểm yếu, nên kết quả "sau" có nguy cơ tự chỉnh rồi tự chấm. Để hạn chế, bộ cũ được đo lại trên cùng 1.210 câu, và hai bộ mới được sinh bằng seed khác (7 và 2026) từ cùng 129 câu gốc.

Mã nguồn đã đổi so với bản dùng cho thực nghiệm chính (có hai quy tắc mới và một dòng nhắc quy tắc trong chỉ dẫn cho mô hình), nên kết quả A/B/C ở mục 5.3 vẫn là kết quả trước thay đổi này.

*Bảng 5.4: Tỷ lệ bộ kiểm chứng phát hiện được từng loại lỗi cài vào, trước và sau khi thêm hai quy tắc (bộ đột biến seed 42, khoảng tin cậy Wilson 95%).*

| Loại lỗi | Số câu thử | Trước | Sau | Khoảng tin cậy sau |
|---|:---:|:---:|:---:|:---:|
| Đổi số nhỏ / lớn / đảo chữ số | 96 câu mỗi loại | 100,0% | 100,0% | [96,2%; 100,0%] |
| Đổi thứ hạng | 46 | 100,0% | 100,0% | [92,3%; 100,0%] |
| Đổi mẫu số | 52 | 100,0% | 100,0% | [93,1%; 100,0%] |
| Số không có nguồn / nhân quả / khuyến nghị | 129 câu mỗi loại | 100,0% | 100,0% | [97,1%; 100,0%] |
| Đổi kỳ | 118 | 83,0% | 94,9% | [89,4%; 97,7%] |
| Đổi ngân hàng | 123 | 86,2% | 100,0% | [97,0%; 100,0%] |
| Đảo chiều | 76 | 88,2% | 96,0% | [89,0%; 98,7%] |
| **Đổi chỉ tiêu** | 120 | **79,2%** | **99,2%** | [95,4%; 99,9%] |
| **Tổng** | **1.210** | **94,1% (1.139)** | **99,2% (1.200)** | |

Trước khi thêm quy tắc, bộ kiểm chứng phát hiện tuyệt đối lỗi về con số, thứ hạng, mẫu số và các câu thêm khẳng định không nguồn, nhân quả hay khuyến nghị. Tuy nhiên, bộ kiểm chứng bỏ sót 71/1.210 đột biến, tập trung ở lỗi ngữ nghĩa mà số vẫn đúng: câu giữ nguyên "50,0%" nhưng đổi "tỷ lệ bao phủ nợ xấu" thành "tỷ lệ nợ xấu" vẫn được chấp nhận ở 25/120 lần. Xem lại thủ công, 37 trong số 71 câu bị bỏ sót (52%) là đột biến tạo câu tự so sánh với chính nó (ví dụ "TCB vượt trội TCB"), loại lỗi mô hình thật hiếm khi viết. Việc phân loại này do tác giả thực hiện sau khi thấy kết quả, nên số liệu thô là kết quả chính.

Sau khi thêm hai quy tắc, số đột biến bị bỏ sót giảm từ 71 xuống 10, không còn đột biến tự so sánh nào: sáu câu đổi kỳ sang một kỳ khác vẫn hợp lệ với dữ kiện được trích, ba câu đảo chiều mệnh đề phụ và một câu nhiều chỉ tiêu có cả hai nhãn bị đổi cùng nằm trong dữ kiện trích dẫn. Trên hai bộ mới, tỷ lệ phát hiện chung sau khi thêm quy tắc là 98,8% (seed 7) và 99,0% (seed 2026), so với 93,8% và 93,6% trước đó; riêng đổi chỉ tiêu đạt 99,2% ở cả hai. Kết quả giống nhau ở các seed khác cho thấy cải thiện không phụ thuộc vào một lần chọn câu cụ thể, nhưng các toán tử đột biến vẫn là những toán tử đã dẫn tới hai quy tắc (ở đổi chỉ tiêu, các seed khác nhau cho kết quả trước thay đổi gần như y hệt), nên đây chưa phải thử nghiệm trên loại lỗi mới; khả năng phát hiện các lỗi ngữ nghĩa kiểu khác chưa được đo.

**Tỷ lệ loại nhầm.** 129 câu gốc không đột biến vẫn được chấp nhận (129/129), và 171 câu đã chấp nhận ở các lần chạy `gpt-5.6-luna` trước đó cũng vậy: 300/300 câu hợp lệ do mô hình viết (0,0%, khoảng tin cậy Wilson 95% đến khoảng 1,3%). Đây là các câu viết theo quy tắc cũ; riêng cấu hình D, quy tắc nhãn loại nhầm sáu dòng chú thích hình mẫu (mục 5.8).

## 5.8. Đánh giá mức độ phụ thuộc vào mô hình ngôn ngữ lớn

Thực nghiệm chính chỉ dùng một mô hình. Thực nghiệm này chạy lại cấu hình B trên cùng 12 câu với năm mô hình, mỗi mô hình một lần, trên phiên bản ban đầu của hệ thống.

*Bảng 5.5: Cấu hình B trên năm mô hình (một lần chạy, phiên bản ban đầu).*

| Mô hình | Số khớp / đã kiểm | Độ phủ trung bình (lượt hoàn thành) | Câu bị loại / được viết | Từ chối đúng | Truy vết | Token |
|---|:---:|:---:|:---:|:---:|:---:|:---:|
| `gpt-5.4-nano` | 45/45 | 0,812 | 16/59 (27,1%) | 2/2 | 1,000 | 100.106 |
| `gpt-5.4-mini` | 69/69 | 0,800 | 14/62 (22,6%) | 2/2 | 1,000 | 102.225 |
| `gpt-5.6-luna` | 91/91 | 0,931 | 1/55 (1,8%) | 2/2 | 1,000 | 118.802 |
| DeepSeek V4 Flash | 46/46 | 0,725 | 3/48 (6,3%) | 2/2 | 1,000 | 219.356 |
| DeepSeek V4 Pro | 32/32 | 0,725 | 14/56 (25,0%) | 2/2 | 1,000 | 110.006 |

Độ khớp số, khả năng truy nguyên và việc từ chối đúng không đổi theo mô hình, vì chúng do lớp kiểm soát quyết định. Thứ thay đổi là hiệu suất viết: độ phủ từ 0,725 đến 0,931 và tỷ lệ câu bị loại từ 1,8% đến 27,1%, tức mô hình yếu hơn vẫn an toàn nhưng báo cáo ngắn và thiếu hơn; token không tương ứng với độ phủ (`gpt-5.6-luna` dùng ít token hơn DeepSeek V4 Flash nhưng phủ cao hơn nhiều). DeepSeek V4 Pro cũng là mô hình của thực nghiệm chính nên lần chạy này cho thấy mức nhiễu giữa các lần chạy của cùng một mô hình (14/56 câu bị loại so với 9/53 của B).

Để kiểm tra độ ổn định, `gpt-5.6-luna` được chạy thêm ba lần trên phiên bản sau nâng cấp (mã nguồn khác lần đầu): độ phủ 0,900, 0,925 và 0,925, tỷ lệ câu bị loại 7,1%, 5,1% và 7,3% (so với 1,8% của lần đầu, nên giá trị tiêu biểu hơn là 5-7%), từ chối đúng 2/2, truy nguyên 1,0 và 302/302 số khớp ở cả ba lần.

**Chạy lại cả ba cấu hình trên gpt-5.6-luna.** Để kiểm tra kết luận về A, B, C có giữ khi đổi mô hình, cả ba cấu hình được chạy lại trên `gpt-5.6-luna` (22/10/2026), 12 câu một lần mỗi cấu hình (36 lượt, 658.442 token), cùng giao thức, dữ liệu khóa và bộ chấm. Mã nguồn lần này là phiên bản sau nâng cấp (mục 5.12) có thêm hai quy tắc kiểm tra mới (mục 4.2.5), nên hai lần chạy khác nhau ở cả mô hình lẫn mã nguồn. D cũng được chạy lại trên mã mới. Không câu nào của A, B, C bị loại bởi hai quy tắc mới.

*Bảng 5.6: Kết quả tổng hợp theo cấu hình (mô hình gpt-5.6-luna, mã nguồn sau nâng cấp và sau khi thêm quy tắc, 12 lượt mỗi cấu hình).*

| Chỉ số | A - một tác tử | B - phân cấp | C - phân cấp có phản biện | D - chỉ dùng câu mẫu |
|---|:---:|:---:|:---:|:---:|
| Hoàn thành trọn vẹn (trên 10 câu phân tích) | 10/10 | 10/10 | 2/10 | 10/10 |
| Con số trong câu được giữ khớp với dữ kiện | 100,0% | 100,0% | 100,0% | 100,0% |
| Độ phủ chỉ tiêu bắt buộc (trung bình 12 lượt) | 0,927 | 0,927 | 0,927 | 0,698 |
| Độ phủ chỉ tiêu bắt buộc (trung bình 10 câu phân tích) | 0,912 | 0,912 | 0,912 | 0,637 |
| Câu bị loại / câu được viết | 0/67 (0,0%) | 1/50 (2,0%) | 30/85 (35,3%) | 12/63 (19,0%) |
| Phát hiện chéo trung bình mỗi lượt | 0,50 | 0,42 | 1,00 | 0,42 |
| Thời gian xử lý trung bình (12 lượt) | 17,2 giây | 28,3 giây | 86,1 giây | 1,7 giây |
| Thời gian xử lý trung bình (10 câu phân tích) | 20,4 giây | 33,8 giây | 103,2 giây | 2,0 giây |
| Số lượt gọi mô hình trung bình (12 lượt) | 0,8 | 2,1 | 5,6 | 0 |
| Token trung bình mỗi lượt (12 lượt) | 5.127 | 10.128 | 39.616 | 0 |

Bảng 5.7 là độ phủ theo từng câu ở lần chạy này.

*Bảng 5.7: Độ phủ chỉ tiêu bắt buộc theo từng câu phân tích và cấu hình (gpt-5.6-luna).*

| Câu | Dạng câu hỏi | A | B | C | D |
|---|---|:---:|:---:|:---:|:---:|
| T01 | Hồ sơ doanh nghiệp | 1,00 | 1,00 | 0,75 | 0,25 |
| T02 | Hồ sơ doanh nghiệp | 1,00 | 1,00 | 1,00 | 0,25 |
| T03 | Tra cứu | 1,00 | 1,00 | 1,00 | 1,00 |
| T04 | Xu hướng | 0,75 | 0,75 | 0,75 | 0,50 |
| T05 | Xu hướng | 0,75 | 1,00 | 1,00 | 0,50 |
| T06 | Xếp hạng | 1,00 | 1,00 | 1,00 | 1,00 |
| T07 | Xếp hạng | 1,00 | 1,00 | 1,00 | 1,00 |
| T08 | Hồ sơ nhiều kỳ | 0,63 | 0,38 | 0,63 | 0,38 |
| T09 | So sánh trực diện | 1,00 | 1,00 | 1,00 | 0,50 |
| T10 | So sánh trực diện | 1,00 | 1,00 | 1,00 | 1,00 |

Độ phủ của A, B và C bằng nhau ở 7/10 câu (bằng nhau từng đôi A - B ở 8 câu). Điều này có thể do bộ câu hỏi chưa đủ khó để phân biệt các cấu hình (đa số câu chỉ cần một đến hai chỉ tiêu), không nhất thiết do các cấu hình tương đương.

Trên mô hình mạnh hơn, các kết luận về A, B và C thay đổi. Độ phủ của A, B và C bằng nhau (0,912 trên 10 câu): B thắng A ở một câu (T05), thua ở một câu (T08) và hòa ở tám câu, nên lợi thế của B ở thực nghiệm chính không còn. A cho kết quả ổn định hơn, với 10/10 báo cáo hoàn thành trọn vẹn và không câu nào bị loại (0/67), so với 7/10 và 8/52 ở DeepSeek V4 Pro. C vẫn có chi phí cao nhất và tỷ lệ hoàn thành thấp nhất: 2/10 báo cáo hoàn thành trọn vẹn, 35,3% câu bị loại, token gấp 3,9 lần B và 7,7 lần A. Độ chính xác của con số, thứ tự chi phí A < B < C và việc C không cải thiện độ phủ không đổi ở cả hai mô hình.

D giữ độ phủ 0,698. Trên mã mới, D bị loại 12/63 câu thay vì 6/60, vì quy tắc nhãn chỉ tiêu loại sáu dòng chú thích hình chung chung nêu hai chỉ tiêu nhưng chỉ trích dẫn dữ kiện của một chỉ tiêu. Đây là loại nhầm các dòng không chứa nhận định nào, không đổi độ phủ nhưng cần xử lý nếu dùng quy tắc thật. Vì chỉ có hai mô hình, một lần chạy mỗi cấu hình và hai phiên bản mã nguồn, các kết luận trên chỉ là quan sát.

## 5.9. Kiểm định khả năng chống chịu trước các truy vấn đối kháng

Kiểm tra đối kháng chạy mười lăm câu thuộc bảy nhóm (chèn chỉ dẫn, thực thể hoặc kỳ không tồn tại, mồi bịa số, xin lời khuyên mua bán, tiền đề sai, ngoài phạm vi) lên cả ba cấu hình với `gpt-5.6-luna`. Kỳ vọng là hệ thống từ chối hoặc nêu rõ giới hạn, và không đưa số không nguồn, khuyến nghị đầu tư hay khẳng định theo tiền đề sai.

*Bảng 5.8: Kiểm tra đối kháng trước và sau sửa lỗi ngoài phạm vi.*

| Lần | Mã | Số câu × cấu hình | Đạt kỳ vọng mỗi cấu hình | Nhóm ngoài phạm vi | Chèn chỉ dẫn, bịa số, khuyến nghị, tiền đề sai |
|---|---|:---:|:---:|:---:|:---:|
| Kiểm tra đối kháng | Ban đầu | 15 × 3 | 13/15 (86,7%) | 0/2 | 0 vi phạm |
| Kiểm tra đối kháng sau sửa | Sau nâng cấp | 8 × 3 | 8/8 | 2/2 | 0 vi phạm |

Trước khi sửa, cả ba cấu hình giữ vững mọi nhóm tấn công trừ nhóm ngoài phạm vi: yêu cầu sáng tác thơ và dự báo giá vàng vẫn nhận báo cáo ngành vì bộ lập kế hoạch mặc định về kế hoạch xếp hạng khi không có ngân hàng nào được nêu. Sau khi thêm cổng phạm vi (mục 5.12), cả hai câu bị từ chối ở cả ba cấu hình.

Lần chạy sau sửa chỉ là tập con tám câu nên chỉ cho biết sửa lỗi có hiệu quả và không gây lùi ở các nhóm được lấy mẫu. Ba cấu hình cho kết quả giống hệt nhau ở mọi nhóm, nên khả năng chống chịu nằm ở lớp kiểm tra xác định dùng chung, không ở việc phân cấp hay phản biện. Cổng phạm vi hiện là bộ lọc theo từ khóa và ý định phân tích nên câu mơ hồ có thể bị chặn nhầm hoặc không bị chặn.

## 5.10. Đánh giá thách thức trong quy trình số hóa báo cáo tài chính gốc

Hệ thống nhận số liệu từ báo cáo tài chính gốc dạng PDF, phần lớn là bản quét. Thực nghiệm này, không gọi mô hình, đo với 885 số liệu đầu vào đã chấp nhận và có trang nguồn (tập con giải thích sau Bảng 5.9): (a) giá trị có xuất hiện nguyên văn trong văn bản của đúng trang không; (b) một bộ trích xuất đơn giản (tìm dòng có nhãn gần nhất rồi lấy số ở cột tương ứng) có lấy đúng giá trị không.

*Bảng 5.9: Giá trị có mặt trên trang và độ đúng của bộ trích xuất đơn giản.*

| Phép đo | Số liệu | Kết quả |
|---|:---:|:---:|
| (a) Trang có lớp văn bản: giá trị xuất hiện nguyên văn | 185 | 178 (96,2%) |
| (a) Trang quét, nhận dạng Tesseract: giá trị xuất hiện nguyên văn | 700 | 652 (93,1%) |
| (b) Bộ trích xuất đơn giản: lấy đúng | 885 | 463 (52,3%) |
| (b) Không tìm thấy dòng | 885 | 236 (26,7%) |
| (b) Lấy sai hàng hoặc cột | 885 | 185 (20,9%) |
| (b) Thiếu cột để lấy | 885 | 1 (0,1%) |

Con số 885 là tập con của dữ liệu đầu vào, không phải toàn bộ. Bộ dữ liệu cuối có 1.735 quan sát, gồm 1.335 số liệu đầu vào đọc từ báo cáo gốc và 400 giá trị chỉ tiêu do chương trình tính lại (4 chỉ tiêu × 100 ô ngân hàng - quý). Thực nghiệm này lấy 1.123 dòng trong tệp đầu vào của dữ liệu quý; trong đó có 150 dòng không có trang hoặc tệp PDF cục bộ để đối chiếu (số liệu năm tài chính và số liệu so sánh) và 88 dòng có trang chưa được nhận dạng ký tự, nên còn 885 dòng (1.123 − 150 − 88). Còn lại 212 quan sát đầu vào của bộ dữ liệu cuối không nằm trong tệp đầu vào quý và không được đo ở đây. Vì vậy 885 là mẫu đo được, đại diện cho khoảng 66% số liệu đầu vào (885/1.335).

Nhận dạng ký tự không phải nguyên nhân chính của sai sót: 93-96% giá trị xuất hiện nguyên văn trên đúng trang. Con số này chỉ cho biết chuỗi số có mặt, chưa chứng minh ô được đọc đúng vị trí.

Khó khăn rõ hơn nằm ở cấu trúc bảng. Bộ trích xuất đơn giản chọn đúng hàng và cột chỉ khoảng một nửa số lần (đây là đối chứng yếu, không đại diện cho bộ trích xuất tốt hơn). Nó đạt 88-96% với các chỉ tiêu đứng một dòng riêng như tổng tài sản hay nợ nhóm 4, 5, nhưng chỉ 27% với lợi nhuận sau thuế và 0% với tổng vốn chủ sở hữu. Nguyên nhân là báo cáo kết quả kinh doanh có cả cột quý lẫn lũy kế, còn vốn chủ sở hữu thường là một dòng tổng của mục.

Kết quả ủng hộ việc giữ giá trị trích xuất ở trạng thái "ứng viên" cho đến khi được đối chiếu với đẳng thức kế toán và tính lại theo công thức. Quy trình số hóa vì thế là bán tự động có tác tử AI hỗ trợ, và thẩm định độc lập là hướng mở rộng chưa thực hiện.

## 5.11. Ca STB quý 4/2025: bất thường trong dữ liệu và vai trò của hồ sơ gốc

Khi đối soát dữ liệu quý, lợi nhuận sau thuế lũy kế của STB giảm từ 8.691,6 tỷ đồng (đến hết quý 3/2025) xuống 5.939,1 tỷ đồng (đến hết quý 4/2025), điều bất thường vì lợi nhuận lũy kế trong năm thường không giảm. Đối chiếu với báo cáo tài chính hợp nhất đã kiểm toán cho thấy con số 5.939,1 là đúng: STB lỗ sau thuế 2.752,5 tỷ đồng riêng trong quý 4/2025 sau khi trích lập dự phòng rủi ro tín dụng 9.232,2 tỷ đồng. Dữ liệu vì thế không bị sửa.

Điều thay đổi là quy trình. Bộ dựng bộ dữ liệu được bổ sung kiểm tra tính đơn điệu của lợi nhuận lũy kế trong năm, và chỉ chấp nhận một khoản lỗ quý khi nó nằm trong danh sách ngoại lệ đã kiểm chứng kèm trang nguồn. Việc kiểm tra các quan hệ kế toán giúp phát hiện những số liệu cần rà soát với chi phí thấp. Tuy nhiên, các dấu hiệu bất thường chỉ là căn cứ để kiểm tra thêm; việc xác nhận giá trị phải dựa trên báo cáo tài chính gốc. Việc đối chiếu hiện do tác giả thực hiện, chưa có chuyên gia độc lập thứ hai.

## 5.12. Nâng cấp sau đánh giá

Sau thực nghiệm chính (05/10/2026), sản phẩm được nâng cấp thêm; các nâng cấp không được tính trong số liệu ở mục 5.3-5.10, trừ lần chạy lặp và kiểm tra đối kháng sau sửa. Chúng gồm: phát trực tiếp bản nháp của chuyên viên và kết luận của bộ kiểm chứng lên màn hình theo dõi; khung trượt tra cứu nguồn hiển thị trang PDF và đường truy nguồn của từng con số; bối cảnh thị trường (giá cổ phiếu, P/B so với ROE) gắn nhãn riêng, nằm ngoài phạm vi dữ liệu của Chương 3 và không được đánh giá; kiểm tra tính đơn điệu của lợi nhuận lũy kế (mục 5.11); và cổng phạm vi từ chối câu hỏi không có thực thể, chỉ tiêu hoặc ý định phân tích ngân hàng (mục 5.9). Ngoài cổng phạm vi, các nâng cấp này không làm đổi kết quả phân tích.

## 5.13. Thảo luận

Trong các cấu hình được thử nghiệm, độ khớp số liệu và khả năng truy nguyên nguồn đều được duy trì nhờ lớp kiểm soát dùng chung (tính toán bằng mã, dữ kiện có nguồn, kiểm tra từng câu), bất kể cấu hình có dùng mô hình ngôn ngữ hay không. Bốn cấu hình, kể cả D, có cùng độ khớp số và khả năng truy nguyên (mục 5.3); ba mô hình khác nhau cũng vậy (mục 5.8); và ba cấu hình chống chịu như nhau trước câu hỏi đối kháng (mục 5.9). Để đối chiếu, mô hình phổ thông không có lớp kiểm soát này (mục 1.3) không nêu được nguồn nào trong mười câu giống hệt, và chỉ 8 trong 19 con số được nêu là đúng (một lần chạy, chỉ mang tính minh họa).

Lớp kiểm soát vẫn có giới hạn mà thực nghiệm độ nhạy đo được. Ở lần đo đầu, bộ kiểm chứng bỏ sót 20,8% các câu giữ nguyên con số và đổi tên chỉ tiêu; hai quy tắc bổ sung đưa tỷ lệ phát hiện chung từ 94,1% lên 99,2% và riêng lỗi đổi chỉ tiêu từ 79,2% lên 99,2%, không loại nhầm câu hợp lệ nào do mô hình viết, nhưng loại nhầm sáu dòng chú thích hình mẫu ở D. Hai quy tắc được thiết kế sau khi thấy kết quả của chính các toán tử đột biến, nên chưa phải bằng chứng về khả năng phát hiện lỗi chưa từng thử.

Giá trị của mô hình và của cách tổ chức tác tử phụ thuộc vào mô hình. D cho thấy một phần đáng kể độ phủ (0,637 trên 10 câu phân tích, so với 0,756-0,812 của A và B ở DeepSeek V4 Pro và 0,912 ở `gpt-5.6-luna`) đạt được không cần mô hình, nhất là ở các câu tra cứu, xếp hạng và so sánh một chỉ tiêu; mô hình bổ sung khả năng gom nhiều chỉ tiêu và diễn đạt mạch lạc, điều bộ chấm tự động chưa đo trực tiếp. Chuyên môn hóa (B) cải thiện nhẹ độ đầy đủ ở DeepSeek V4 Pro nhưng không còn lợi thế ở `gpt-5.6-luna`, còn phản biện (C) tốn gấp ba đến bốn lần B ở cả hai mô hình và giảm tỷ lệ hoàn thành trọn vẹn.

B hoặc một tác tử đơn A trên mô hình mạnh là điểm cân bằng hợp lý; C chỉ nên dùng khi bộ phản biện được giới hạn vào các vấn đề quy tắc không kiểm được và được phép bổ sung câu mới. Kết quả cho thấy tỷ lệ câu được giữ có liên quan đến mức độ đầy đủ của các quy tắc trong chỉ dẫn dành cho mô hình. Vì vậy, một hướng cải thiện là yêu cầu mô hình viết mỗi câu về một chỉ tiêu và một chiều so sánh, thay vì nới lỏng quy tắc kiểm tra.

Đối chiếu với khảo sát ở mục 1.2, kết quả thực nghiệm đáp ứng một phần kỳ vọng của người dùng. Về nguồn, 11 trong 15 người coi khả năng truy tới trang báo cáo gốc là điều kiện để dùng kết quả do AI tạo ra, và hệ thống đạt điều này cho mọi con số trong các lượt đã chạy (100% truy được về số liệu gốc ở bốn cấu hình). Kiểm tra tự động trước khi hiển thị chỉ được 5 người chọn, nên giá trị của bộ kiểm chứng đối với người dùng nằm ở độ tin cậy gián tiếp hơn là ở một tính năng họ chủ động đòi hỏi. Về độ trễ, cấu hình A (khoảng 21 giây) nằm trong mức chờ chấp nhận được của 13 người nhưng chưa đáp ứng 2 người cần dưới 10 giây; cấu hình B (33 đến 34 giây) chỉ đáp ứng 9 người, và cấu hình C (75 đến 103 giây) chỉ đáp ứng 3 người. Về chi phí, năm trong sáu tổ hợp mô hình và cấu hình có chi phí dưới 1.000 đồng mỗi báo cáo, nhưng đây là chi phí gọi mô hình chứ không phải giá người dùng phải trả, chưa gồm chi phí chuẩn bị dữ liệu, và 4 người chỉ chấp nhận công cụ miễn phí. Các thời gian này được đo khi các lượt chạy đồng thời nên chỉ có giá trị tham khảo.

## 5.14. Các yếu tố ảnh hưởng tới tính hợp lệ của kết quả

Các giới hạn chung về dữ liệu, thiết kế thực nghiệm, chấm điểm và khảo sát đã nêu ở mục 3.4; mục này chỉ bổ sung những yếu tố phát sinh khi chạy.

Về hợp lệ nội tại, các lượt chạy đồng thời nên thời gian xử lý chịu ảnh hưởng của tải máy chủ; phép lặp ba lần ở mục 5.8 chỉ có cho một mô hình và một cấu hình; phép so sánh DeepSeek V4 Pro với `gpt-5.6-luna` khác nhau ở cả mô hình lẫn phiên bản mã nguồn nên không tách được tác động riêng của mô hình; hai quy tắc kiểm tra mới được thiết kế sau khi thấy kết quả độ nhạy nên khoảng cách 79,2% và 99,2% cần đọc kèm hạn chế này.

Về hợp lệ cấu trúc, các chỉ số tự động không đo chất lượng diễn giải. Phép đối chiếu mô hình phổ thông ở mục 1.3 chỉ là một lần chạy, một mô hình, không bật tìm kiếm web, do tác giả chấm bằng tay theo quy tắc đặt trước.

Về hợp lệ bên ngoài, cấu hình B được kiểm trên ba mô hình OpenAI và hai mô hình DeepSeek với mỗi mô hình một lần, và kiểm tra đối kháng chạy trên một mô hình với mười lăm câu, không đủ để khái quát.

Về quy trình, người phát triển đồng thời là người thiết kế thực nghiệm; một số lượt chạy lỗi hạ tầng được tách riêng và không dùng trong bảng nào; lỗi ngoài phạm vi được sửa rồi kiểm lại trên các câu đã thấy, chưa trên câu mới. Khi chạy cấu hình D lần đầu trên mã mới, hai mã lý do loại câu của quy tắc mới chưa được khai báo trong đặc tả dữ liệu nên một lượt phân tích dừng với lỗi; lỗi đã được sửa sau khi có kết quả.

## 5.15. Tính khả thi, chi phí vận hành và điều kiện áp dụng

### 5.15.1. Chi phí vận hành

Chi phí mô hình của một báo cáo được tính từ token đầu vào và đầu ra thực tế của mười lượt phân tích, nhân với đơn giá công bố. Theo trang bảng giá của DeepSeek (2026), `deepseek-v4-pro` tính 1,32 USD cho một triệu token đầu vào (không trúng bộ nhớ đệm) và 3,96 USD cho một triệu token đầu ra trong giờ cao điểm, bằng một nửa ngoài giờ cao điểm; `gpt-5.6-luna` tính 0,20 và 1,20 USD ở mức Standard (OpenAI, 2026b). Bảng 5.10 dùng đơn giá giờ cao điểm và không tính bộ nhớ đệm, tức cận trên, với tỷ giá 25.201 đồng một USD (tỷ giá trung tâm ngày 30/6/2026, số liệu ở trạng thái chờ kiểm định nên chỉ dùng để quy đổi quy mô).

*Bảng 5.10: Chi phí mô hình ước tính cho một báo cáo (mười câu phân tích).*

| Mô hình | Cấu hình | Token đầu vào | Token đầu ra | Chi phí (USD) | Chi phí (đồng) |
|---|---|:---:|:---:|:---:|:---:|
| DeepSeek V4 Pro | A - một tác tử | 3.915 | 626 | 0,0077 | 193 |
| DeepSeek V4 Pro | B - phân cấp | 8.644 | 1.258 | 0,0164 | 413 |
| DeepSeek V4 Pro | C - phân cấp có phản biện | 28.206 | 2.822 | 0,0484 | 1.220 |
| `gpt-5.6-luna` | A - một tác tử | 4.389 | 1.764 | 0,0030 | 76 |
| `gpt-5.6-luna` | B - phân cấp | 9.258 | 2.895 | 0,0053 | 134 |
| `gpt-5.6-luna` | C - phân cấp có phản biện | 38.284 | 9.254 | 0,0188 | 473 |
| Không gọi mô hình | D - chỉ dùng câu mẫu | 0 | 0 | 0 | 0 |

Chi phí mô hình mỗi báo cáo vì vậy chỉ từ vài chục đến hơn một nghìn đồng, và chưa so được với chi phí con người vì khóa luận chưa đo giờ công; khác biệt chính là thời gian chờ (từ khoảng 21 giây ở A đến khoảng 75 giây ở C với DeepSeek V4 Pro; từ 20 đến 103 giây với `gpt-5.6-luna`). Nhiều khả năng chi phí lớn hơn nằm ở khâu chuẩn bị dữ liệu: mỗi quý mới cần đọc báo cáo của mười ngân hàng, khoảng 130 số đầu vào (1.335 chia mười quý), phần lớn là bản quét phải đối soát từng ô (mục 5.10). Khóa luận chưa đo giờ công cho việc này nên không quy ra tiền.

Theo khảo sát ở mục 1.2, trong 13 người tự tra số liệu, 8 người mất từ 30 phút trở lên cho một ngân hàng một quý (trung vị thuộc nhóm 30-60 phút, tự khai). Hệ thống trả lời trong khoảng 21 đến 34 giây ở cấu hình A và B, nhưng chỉ trên bộ dữ liệu đã chuẩn bị sẵn; thời gian chuẩn bị dữ liệu cho ngân hàng hoặc quý mới không nằm trong con số này nên hai số liệu không so sánh trực tiếp được.

### 5.15.2. Điều kiện áp dụng thực tế

Hệ thống chỉ tin cậy khi các điều kiện sau được giữ. Báo cáo tài chính hợp nhất gốc của từng ngân hàng cho kỳ cần hỏi phải có; hệ thống từ chối kỳ hoặc ngân hàng chưa có dữ liệu thay vì ước tính. Dữ liệu phải được cập nhật mỗi quý theo quy trình ở mục 3.2, với người thứ hai đối soát độc lập (chưa có ở khóa luận này, mục 5.11). Phạm vi hiện hẹp (mười ngân hàng, bốn chỉ tiêu); mở rộng nghĩa là thêm công thức, quy tắc kiểm tra và đối soát lại. Kết quả phụ thuộc mô hình (mục 5.8), nên khi nhà cung cấp đổi phiên bản hoặc giá phải chạy lại bộ câu hỏi chuẩn trước khi dùng tiếp.

### 5.15.3. Rủi ro và giảm thiểu

*Bảng 5.11: Rủi ro khi áp dụng và biện pháp giảm thiểu.*

| Rủi ro | Mức độ | Khả năng | Biện pháp |
|---|---|---|---|
| Số liệu đầu vào đọc sai từ báo cáo quét | Cao | Trung bình: chuỗi số xuất hiện trên trang 93-96%, bộ trích xuất đơn giản chỉ đúng 52% (mục 5.10) | Giữ số ở trạng thái ứng viên, đối chiếu đẳng thức kế toán, bổ sung người thẩm định thứ hai |
| Câu giữ số đúng nhưng gắn sai tên chỉ tiêu | Trung bình | Có đo: bộ kiểm chứng bỏ sót 20,8% câu đổi chỉ tiêu (mục 5.7) | Quy tắc kiểm tra nhãn chỉ tiêu; người dùng đọc kèm bảng số liệu và nguồn |
| Nhà cung cấp đổi phiên bản hoặc giá mô hình | Trung bình | Cao: kết quả đã khác nhau giữa các mô hình (mục 5.8) | Ghi phiên bản mô hình trong mỗi lượt chạy; chạy lại bộ câu hỏi chuẩn trước khi đổi |
| Câu hỏi ngoài phạm vi không bị cổng từ khóa chặn | Trung bình | Trung bình: cổng chỉ dựa trên từ khóa (mục 5.9) | Mở rộng bộ câu đối kháng; thông báo từ chối nêu rõ phạm vi hỗ trợ |
| Người dùng coi báo cáo là khuyến nghị đầu tư | Cao | Trung bình | Hệ thống từ chối xin lời khuyên mua bán; mỗi báo cáo ghi rõ chỉ tổng hợp số liệu |
| Dịch vụ gián đoạn do hạ tầng miễn phí | Thấp | Trung bình | Bản trình diễn dùng hạ tầng miễn phí; khi dùng thật cần hạ tầng trả phí và sao lưu |

### 5.15.4. Khuyến nghị áp dụng

Hệ thống phù hợp để nhà phân tích và cán bộ đối sánh tra nhanh số liệu hợp nhất, xu hướng và vị thế của mười ngân hàng, với điều kiện mỗi con số được đọc kèm trang nguồn. Nên dùng B làm mặc định, hoặc A trên mô hình mạnh; chỉ dùng C khi có người xem xét kết quả. Không dùng để đưa khuyến nghị mua bán, dự báo, hay cho ngân hàng và chỉ tiêu ngoài bộ dữ liệu; không coi báo cáo là bản cuối khi chưa kiểm tra lại số liệu quan trọng với báo cáo gốc. Mọi quy đổi lợi ích ra tiền, nếu có, chỉ là kịch bản giả định của tác giả.