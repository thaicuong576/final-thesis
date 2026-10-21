# CHƯƠNG 5. KẾT QUẢ VÀ THẢO LUẬN

Chương này trình bày kết quả kiểm tra kỹ thuật, kết quả thực nghiệm so sánh các cấu hình A, B, C và đối chứng D (không gọi mô hình) trên bộ dữ liệu mười ngân hàng, và các thực nghiệm bổ sung đo độ tin cậy của chính các cơ chế kiểm soát và độ phụ thuộc vào mô hình: độ nhạy của bộ kiểm chứng câu trước và sau khi bổ sung quy tắc, so sánh giữa các mô hình ngôn ngữ kể cả chạy lại A/B/C trên mô hình mạnh hơn, kiểm tra đối kháng và đo khả năng số hóa từ báo cáo gốc. Cuối chương đánh giá tính khả thi, chi phí và điều kiện áp dụng. Mọi số liệu được lấy từ các tệp kết quả do chương trình ghi lại (danh mục các tệp này ở Phụ lục C); không có số nào được nhập tay.

## 5.1. Kết quả kiểm tra kỹ thuật

Phiên bản dùng cho thực nghiệm A/B/C có hơn 900 bài kiểm thử tự động phía máy chủ và 188 bài phía giao diện, tất cả đều đạt trên hệ thống tích hợp liên tục. Sau các nâng cấp ở mục 5.12 (đếm ngày 13/10/2026), bộ kiểm thử đã tăng lên 1.020 bài phía máy chủ (5 bài bị bỏ qua có chủ đích) và 235 bài phía giao diện, vẫn đạt toàn bộ. Các bài kiểm thử dùng mô hình và dữ liệu giả lập nên chỉ chứng minh hệ thống chạy đúng với các kịch bản đã mô tả. Vì vậy, hệ thống còn được chạy với mô hình thật trên bản triển khai: các luồng ở mục 4.5, gồm tra cứu, hồ sơ doanh nghiệp, so sánh, xếp hạng, xu hướng và tải lên ngân hàng mới, cho kết quả đúng ở các lần chạy thử.

Việc chạy thật cũng bộc lộ những điều kiểm thử giả lập không phát hiện. Thứ nhất, nhiều câu nhận định đúng bị loại vì prompt chưa nêu đủ quy tắc của bộ kiểm tra, được khắc phục bằng cách ghi rõ các quy tắc này vào prompt (mục 4.2.4). Thứ hai, ở phiên bản dùng cho thực nghiệm, câu hỏi hoàn toàn ngoài phạm vi (yêu cầu sáng tác thơ, dự báo giá vàng) **không** bị từ chối mà vẫn nhận một báo cáo ngành, vì bộ lập kế hoạch mặc định về kế hoạch xếp hạng khi câu hỏi không nêu ngân hàng nào (mục 5.9). Lỗi này đã được sửa sau đánh giá (mục 5.12); phần từ chối câu hỏi ở kỳ hoặc ngân hàng không có dữ liệu thì hoạt động đúng ngay từ đầu.

## 5.2. Thiết lập thực nghiệm

Bảng 5.1 liệt kê toàn bộ các thực nghiệm đã chạy và câu hỏi mà mỗi thực nghiệm trả lời. Hai phiên bản của hệ thống được dùng: phiên bản ban đầu, dùng cho thực nghiệm chính, cấu hình D lần đầu, so sánh mô hình và kiểm tra đối kháng; và phiên bản sau nâng cấp (mục 5.12), dùng cho lần chạy lặp, kiểm tra đối kháng sau sửa và, sau khi thêm hai quy tắc kiểm tra mới (mục 4.2.5), cho lần chạy lại A/B/C trên `gpt-5.6-luna` và phép đo độ nhạy lần hai.

*Bảng 5.1: Danh mục thực nghiệm.*

| Thực nghiệm | Trả lời câu hỏi nào | Mô hình | Phiên bản | Cấu hình, số câu × số lần | Token |
|---|---|---|---|---|---|
| Thực nghiệm chính | A, B, C khác nhau thế nào (câu hỏi nghiên cứu thứ hai và thứ ba) | DeepSeek V4 Pro | Ban đầu | 3 cấu hình, 12 câu × 1 | 454.706 |
| Cấu hình D | Phần độ phủ đạt được khi không dùng mô hình | không gọi mô hình | Ban đầu (cùng thực nghiệm chính) và sau quy tắc mới | D, 12 câu × 1, hai lần | 0 |
| Chạy lại A/B/C | Kết luận về A, B, C có giữ khi dùng mô hình mạnh hơn | `gpt-5.6-luna` | Sau nâng cấp và sau quy tắc mới | 3 cấu hình, 12 câu × 1 | 658.442 |
| Độ nhạy bộ kiểm chứng | Bộ kiểm chứng câu bắt được bao nhiêu loại lỗi cài vào, trước và sau hai quy tắc mới | không gọi mô hình | Ban đầu và sau quy tắc mới | 3 bộ × 1.210 câu đột biến từ 129 câu đã được chấp nhận ở thực nghiệm chính | 0 |
| So sánh mô hình | Kết quả có phụ thuộc mô hình không | `gpt-5.4-nano`, `gpt-5.4-mini`, `gpt-5.6-luna` (OpenAI); DeepSeek V4 Flash, DeepSeek V4 Pro | Ban đầu | chỉ cấu hình B, 12 câu × 1 | 650.495 |
| Lặp lại so sánh mô hình | Kết quả của `gpt-5.6-luna` có ổn định khi chạy lại trên phiên bản sau nâng cấp không | `gpt-5.6-luna` | Sau nâng cấp | chỉ cấu hình B, 12 câu × 3 lần | 359.298 |
| Kiểm tra đối kháng | Hệ thống chống chịu thế nào trước câu hỏi đối kháng | `gpt-5.6-luna` | Ban đầu | 3 cấu hình, 15 câu × 1 | 462.802 |
| Kiểm tra đối kháng sau sửa | Sửa lỗi ngoài phạm vi có hiệu quả và không gây lùi không | `gpt-5.6-luna` | Sau nâng cấp | 3 cấu hình, tập con 8 câu × 1 | 210.080 |
| Số hóa từ báo cáo gốc | Khó khăn của số hóa nằm ở nhận dạng ký tự hay ở cấu trúc bảng | không gọi mô hình | — | 885 số liệu đầu vào đã chấp nhận | 0 |
| Mô hình phổ thông không công cụ (mục 1.6) | Người dùng gặp gì khi hỏi thẳng một mô hình phổ thông | `gpt-5.6-luna` | — | 10 câu × 1 | 14.060 |
Thực nghiệm chính được chạy ngày 05/10/2026 trên bộ dữ liệu mười ngân hàng đã khóa mã băm (mục 3.2.3), với mô hình DeepSeek V4 Pro. Mười hai câu hỏi ở Bảng 3.4 được chạy một lần trên mỗi cấu hình, tạo thành 36 lượt; thứ tự được xáo trộn theo một giá trị cố định để có thể lặp lại, và sáu lượt chạy đồng thời. Tổng lượng văn bản mô hình xử lý trong thực nghiệm chính là 454.706 token cho 36 lượt chạy. Sau khi chạy, hệ thống xác nhận cả mười hai câu hỏi có kế hoạch giống hệt nhau giữa ba cấu hình. Việc chấm điểm do chương trình thực hiện theo các chỉ số ở mục 3.3.4.


## 5.3. Kết quả thực nghiệm tổng hợp giữa các cấu hình

*Bảng 5.2: Kết quả tổng hợp theo cấu hình (mô hình DeepSeek V4 Pro, 12 lượt mỗi cấu hình).*

| Chỉ số | A – một tác tử | B – phân cấp | C – phân cấp có phản biện | D – chỉ dùng câu mẫu |
|---|:---:|:---:|:---:|:---:|
| Trả lời được (10 câu phân tích) | 10/10 | 10/10 | 10/10 | 10/10 |
| Từ chối đúng (R1, R2) | 2/2 | 2/2 | 2/2 | 2/2 |
| Hoàn thành trọn vẹn, không ghi chú giới hạn (trên 10 câu phân tích; hai câu từ chối không tính) | 7/10 (70,0%) | 9/10 (90,0%) | 4/10 (40,0%) | 10/10 (100,0%) |
| Con số trong câu được giữ khớp với dữ kiện được trích | 100,0% | 100,0% | 100,0% | 100,0% |
| Truy được về số liệu gốc | 100,0% | 100,0% | 100,0% | 100,0% |
| Độ phủ chỉ tiêu bắt buộc (trung bình 12 lượt) | 0,797 | 0,844 | 0,781 | 0,698 |
| Độ phủ chỉ tiêu bắt buộc (trung bình 10 câu phân tích) | 0,756 | 0,812 | 0,738 | 0,637 |
| Câu bị loại / câu được viết | 8/52 (15,4%) | 9/53 (17,0%) | 22/63 (34,9%) | 6/60 (10,0%) |
| Báo cáo dùng bố cục dựng sẵn (trên 10) | 3 | 1 | 2 | 10 (luôn dựng sẵn) |
| Phát hiện liên tầng trung bình mỗi lượt | 0,33 | 0,33 | 0,67 | 0,42 |
| Thời gian xử lý trung bình | 17,5 giây | 27,5 giây | 62,9 giây | 3,8 giây |
| Số lượt gọi mô hình trung bình | 0,8 | 2,1 | 4,4 | 0 |
| Token trung bình mỗi lượt | 3.784 | 8.252 | 25.856 | 0 |
| Số vòng sửa đổi trung bình | 0,00 | 0,00 | 1,25 | 0,00 |

![](experiments/er9/analysis/figure_er9_cost_latency.png)

Hình 5.1: Chi phí vận hành theo cấu hình A, B, C (thời gian xử lý và token)

Cấu hình D là đối chứng không có mô hình: cùng kế hoạch cố định, cùng dữ kiện đã tính và cùng bộ kiểm chứng câu như ba cấu hình kia, nhưng mọi câu lấy từ mẫu câu dựng sẵn từ dữ kiện (mục 4.2.4), không có lượt gọi mô hình nào. D được chạy một lần trên 12 câu, và kế hoạch của D trùng mã băm với kế hoạch của A, B, C ở cả 12 câu. Cả bốn cấu hình đạt 100% ở chỉ số khớp số và 100% truy được về số liệu gốc. Kết quả này không phản ánh năng lực khác nhau giữa các cấu hình mà là hệ quả của thiết kế: mọi con số do công cụ tính bằng mã nguồn, và câu chỉ vào báo cáo khi bộ kiểm tra xác nhận số, thứ hạng, kỳ và chiều so sánh khớp với dữ kiện được trích; câu không khớp bị loại và được ghi lại kèm lý do. Chính vì D, vốn không có mô hình, cũng đạt 100% ở hai chỉ số này nên hai chỉ số đó không phân biệt được các cách tổ chức tác tử.

Con số 100% là hệ quả của định nghĩa: chỉ số khớp số được đo trên các câu đã qua chính bộ kiểm chứng áp dụng quy tắc đó, nên nó không phải bằng chứng độc lập về chất lượng của mô hình viết. Nó cho biết mọi con số trong câu được giữ đều trùng với một dữ kiện đã tính và trích dẫn, nhưng **không** cho biết con số gắn đúng tên chỉ tiêu, đúng kỳ hay đúng ngân hàng. Mục 5.7 đo điểm này: ở thực nghiệm lần đầu, một câu giữ nguyên con số đúng nhưng đổi tên chỉ tiêu vẫn lọt qua bộ kiểm chứng ở 20,8% số trường hợp thử; sau khi bổ sung quy tắc nhãn chỉ tiêu, tỷ lệ này còn 0,8%.

**Cấu hình D cho biết mô hình đóng góp gì.** D có độ phủ thấp nhất (0,698 trên 12 lượt, 0,637 trên 10 câu phân tích, so với 0,756 của A và 0,812 của B) nhưng không tốn token và chạy trong khoảng 4 giây. Trên mỗi câu, D hòa với B ở 6 câu, thua ở 4 câu và không thắng câu nào (Bảng 5.3). D ngang B ở các câu chỉ cần một chỉ tiêu hoặc một thứ hạng (T03, T06, T07, T10), nơi một mẫu câu là đủ; D thua nặng ở các câu cần nói nhiều chỉ tiêu cùng lúc, như hồ sơ doanh nghiệp (T01, T02: 0,25 so với 0,75 và 0,50) và so sánh hai ngân hàng (T09: 0,50 so với 1,00), vì mỗi mẫu câu chỉ nêu một dữ kiện. Giá trị của mô hình ở thực nghiệm này vì vậy là khả năng gom nhiều chỉ tiêu vào một câu hoặc một đoạn có mạch lạc, không phải độ chính xác của con số. Hai điều cần nói thêm. Một là D đạt tỷ lệ hoàn thành trọn vẹn cao nhất (10/10) vì không có câu nào cần sửa, nên "hoàn thành trọn vẹn" không phải thước đo chất lượng. Hai là các chỉ số tự động ở đây không đo độ trôi chảy, mức dễ đọc hay tính hữu ích của câu, đúng là những thứ mô hình ngôn ngữ có thể đem lại; vì vậy phép so sánh D với B chưa đủ để kết luận mô hình không đáng chi phí. Việc đo các khía cạnh đó cần người đọc chấm, và chỉ được thực hiện ở quy mô thăm dò (mục 5.6).

Để thấy hệ thống thực sự viết ra gì, xét câu T03 ("Tỷ lệ bao phủ nợ xấu của HDB trong quý 1/2026 là bao nhiêu?") ở cấu hình B. Mô hình trả về hai câu được chấp nhận, mỗi câu kèm mã dữ kiện làm căn cứ: "Tỷ lệ bao phủ nợ xấu của HDB đạt 50,0% (hạng 10/10) trong quý 1/2026" (căn cứ: giá trị quan sát và thứ hạng của HDB) và "Trung vị tỷ lệ bao phủ nợ xấu nhóm 10 ngân hàng là 89,6% trong quý 1/2026" (căn cứ: trung vị nhóm). Các câu thể hiện đúng mức phân tích của hệ thống: nêu số, thứ hạng và vị thế so với nhóm, không giải thích nguyên nhân.

R1 (quý 3/2026) và R2 (OCB) bị từ chối đúng ở cả bốn cấu hình, trước khi gọi mô hình phân tích, với thông báo tiếng Việt, danh sách dữ liệu đang có và câu hỏi gợi ý thay thế. Mười câu phân tích đều có báo cáo hợp lệ ở cả bốn cấu hình. Các lượt chạy được chạy đồng thời nên thời gian tuyệt đối phụ thuộc tải của máy chủ mô hình; chỉ nên so sánh tương đối giữa các cấu hình.

## 5.4. Đánh giá hiệu quả của kiến trúc đa tác tử phân cấp so với tác tử đơn

Với 10 câu phân tích và một lần chạy mỗi cặp, độ phủ chỉ nhận một vài giá trị rời rạc (0,125 mỗi bước), nên khóa luận không ước lượng khoảng tin cậy mà trình bày từng câu và đếm số câu thắng, hòa, thua. Bảng 5.3 là độ phủ theo từng câu và cấu hình, Bảng 5.4 là token và thời gian, và Hình 5.2 là bản đồ nhiệt của Bảng 5.3.

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

*Bảng 5.4: Token và thời gian xử lý theo từng câu phân tích và cấu hình (DeepSeek V4 Pro).*

| Câu | Token A | Token B | Token C | Giây A | Giây B | Giây C | Giây D |
|---|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| T01 | 4.623 | 11.661 | 85.187 | 26,5 | 44,2 | 114,6 | 15,0 |
| T02 | 9.279 | 18.953 | 25.474 | 34,1 | 39,4 | 61,8 | 5,0 |
| T03 | 1.667 | 2.884 | 5.829 | 14,5 | 16,0 | 32,5 | 0,4 |
| T04 | 4.737 | 11.932 | 32.543 | 17,6 | 40,0 | 99,5 | 2,8 |
| T05 | 4.632 | 10.641 | 37.638 | 17,4 | 37,6 | 103,9 | 2,8 |
| T06 | 3.961 | 7.537 | 26.361 | 26,8 | 35,9 | 49,2 | 5,2 |
| T07 | 3.331 | 6.652 | 27.036 | 16,8 | 26,2 | 52,0 | 5,3 |
| T08 | 7.549 | 18.373 | 27.895 | 18,9 | 43,0 | 83,3 | 5,0 |
| T09 | 3.362 | 5.870 | 18.377 | 16,9 | 24,0 | 64,6 | 2,6 |
| T10 | 2.272 | 4.517 | 23.933 | 18,5 | 21,4 | 91,4 | 1,3 |

D không có mô hình nên ở mọi câu có 0 token và không có cột riêng cho token.

![](experiments/er9d/analysis/figure_er9_perquestion_heatmap.png)

Hình 5.2: Bản đồ nhiệt độ phủ chỉ tiêu theo câu hỏi và cấu hình (DeepSeek V4 Pro)

Về độ phủ, B thắng 3, hòa 6, thua 1 so với A. B hơn A ở câu xu hướng của CTG (T04: 1,0 so với 0,5), so sánh MBB – TCB (T09: 1,0 so với 0,75) và hồ sơ nhiều kỳ của VPB (T08: 0,38 so với 0,31), nơi các chuyên viên viết riêng cho từng chỉ tiêu; ngược lại, ở hồ sơ STB (T02) A đạt độ phủ cao hơn B (0,75 so với 0,50). B cũng ít phải dùng bố cục dựng sẵn hơn (1 so với 3 báo cáo), vì điều phối viên của B nhận các câu đã được chuyên viên viết và kiểm tra, còn tác tử đơn của A phải tự viết và tự lắp toàn bộ báo cáo trong một lần gọi. Chênh lệch này không lớn: với một lần chạy và 10 câu, một câu đổi kết quả đã làm đổi cán cân, nên đây là dấu hiệu chứ chưa phải kết luận.

Cái giá của B là chi phí: B tốn nhiều token hơn A ở cả 10 câu (trung bình khoảng 2,2 lần) và thêm khoảng 10 giây mỗi lượt. Độ chính xác của con số và khả năng truy vết không khác nhau vì cùng đi qua công cụ tính toán và bộ kiểm tra câu. Tỷ lệ câu bị loại của A và B tương đương (15,4% và 17,0%), nhưng khác về lý do: A chủ yếu bị loại vì nêu xu hướng khi không có dữ kiện thay đổi (5 trên 8 câu), còn B chủ yếu vì chiều xu hướng không khớp ngưỡng đi ngang (5 trên 9 câu).

**Trả lời câu hỏi nghiên cứu thứ hai:** trong thực nghiệm chính với DeepSeek V4 Pro, B có độ phủ chỉ tiêu cao hơn A (0,812 so với 0,756 trên 10 câu; thắng 3, hòa 6, thua 1) và 9 so với 7 báo cáo hoàn thành trọn vẹn trên 10 câu phân tích, với chi phí khoảng gấp đôi; độ chính xác của con số như nhau vì cùng đi qua bộ kiểm chứng. Lợi thế này nhỏ và không bền: khi chạy lại cả ba cấu hình trên mô hình mạnh hơn (`gpt-5.6-luna`, mục 5.8), độ phủ của A và B bằng nhau (0,912 trên 10 câu) và chỉ còn một câu thắng và một câu thua ở mỗi bên. Vì vậy thực nghiệm chưa đủ để kết luận B tốt hơn A, và kết luận phụ thuộc vào mô hình. Độ ổn định giữa các lần chạy không đo được ở thực nghiệm chính vì mỗi cặp chỉ chạy một lần, và mức nhiễu giữa các lần chạy có thể ngang với chênh lệch A – B: một lần chạy khác của cùng mô hình DeepSeek V4 Pro (mục 5.8) loại 14 trên 56 câu (25%) so với 9 trên 53 (17%) của B ở thực nghiệm chính. Ngoài ra A và B khác nhau cả về chuyên môn hóa lẫn số lượt gọi mô hình (0,8 so với 2,1 mỗi lượt), nên không tách được hai tác động.

## 5.5. Đánh giá tác động của cơ chế phản biện và sửa đổi có mục tiêu

Bổ sung phản biện và tối đa hai vòng sửa đổi không làm tăng độ phủ: độ phủ trung bình của C là 0,781 so với 0,844 của B (12 lượt), C thắng 2, hòa 4, thua 4 câu so với B (Bảng 5.3). Số phát hiện liên tầng được nêu tăng gấp đôi (0,67 so với 0,33 mỗi lượt), phù hợp với việc bộ phản biện được yêu cầu kiểm tra các mâu thuẫn liên tầng đã có được nêu trong báo cáo hay chưa. Chi phí tăng mạnh: token gấp 3,1 lần B và 6,8 lần A, thêm khoảng 35 giây mỗi lượt so với B; riêng hồ sơ BID (T01) dùng 85.187 token cho một lượt (Bảng 5.4).

Nguyên nhân độ phủ giảm thấy rõ khi xem các câu bị loại. C bị loại 22 trên 63 câu, trong đó 12 câu bị loại vì còn vấn đề phản biện chưa giải quyết sau hai vòng sửa. Chỉ 4 trên 10 câu phân tích của C hoàn thành trọn vẹn (hai câu từ chối không thể hoàn thành một báo cáo nên không nằm trong mẫu số). Các vấn đề còn mở khi kết thúc chủ yếu thuộc loại "tổng hợp chưa đầy đủ" (8 trên 9 vấn đề, 7 ở mức nghiêm trọng), tức bộ phản biện yêu cầu báo cáo nói thêm về các chỉ tiêu khác, ví dụ ở hồ sơ BID: báo cáo "đã bỏ sót hoàn toàn" tỷ lệ nợ xấu và bao phủ nợ xấu. Khi câu viết lại vẫn không đạt, câu bị loại, nên chính yêu cầu "nói đầy đủ hơn" lại làm báo cáo mất câu và giảm độ phủ (T01: 0,5 so với 0,75 của B; T10: 0,5 so với 1,0).

Kết quả này được xác nhận khi chạy lại trên `gpt-5.6-luna` (mục 5.8): độ phủ của C vẫn bằng của B và A (0,912 trên 10 câu), nhưng chỉ 2 trên 10 câu phân tích của C hoàn thành trọn vẹn (so với 10 trên 10 của B), 30 trên 85 câu bị loại (35,3%, so với 1 trên 50 của B), token gấp 3,9 lần và thời gian gấp 3,0 lần B.

**Trả lời câu hỏi nghiên cứu thứ ba:** ở cả hai mô hình, phản biện và sửa đổi làm chi phí tăng khoảng ba đến bốn lần so với B, không cải thiện độ chính xác hay độ phủ đo được, làm giảm tỷ lệ hoàn thành trọn vẹn và làm báo cáo nêu nhiều phát hiện liên tầng hơn. Bộ phản biện hiện tại hoạt động với tiêu chuẩn kiểm duyệt rất khắt khe: nó phát hiện đúng những chỗ báo cáo chưa đầy đủ, nhưng cơ chế sửa câu đơn lẻ chưa đủ để đáp ứng yêu cầu ở mức cả báo cáo, và những gì sửa không được thì bị loại bỏ.

## 5.6. Phân tích theo dạng câu hỏi, cơ chế kiểm tra câu và chấm mù thăm dò

Báo cáo thay đổi hình dạng theo dạng câu hỏi: câu tra cứu nhận thẻ trả lời một khối; hồ sơ doanh nghiệp tạo báo cáo dài nhất (5–7 khối, trung bình 5,8) với bản đồ nhiệt thứ hạng, biểu đồ tương quan và khối lưu ý; xếp hạng, xu hướng và so sánh trực diện tạo báo cáo 2–4 khối. Yêu cầu về báo cáo thích ứng theo câu hỏi thay vì một khuôn cố định vì vậy được đáp ứng.

Trên toàn thực nghiệm, 39 câu bị loại. Lý do phổ biến nhất là còn vấn đề phản biện chưa giải quyết (12 câu, chỉ ở C), chiều xu hướng không khớp ngưỡng đi ngang (11), thứ hạng không khớp (6) và nêu xu hướng khi không trích dữ kiện thay đổi (6); chỉ 2 câu bị loại vì con số không khớp. Sáu báo cáo dùng bố cục dựng sẵn thay vì bố cục do mô hình đề xuất; câu xu hướng của SHB (T05) rơi vào trường hợp này ở cả ba cấu hình vì mô hình đặt biểu đồ vào trong khối mục, trái với đặc tả báo cáo. Câu hỏi T08 (đánh đổi của VPB qua năm 2025 so với nhóm) có độ phủ thấp ở cả ba cấu hình (0,13–0,38), vì hệ thống chỉ hỗ trợ xu hướng nhiều kỳ cho riêng một ngân hàng, chưa hỗ trợ so sánh nhóm qua nhiều kỳ; báo cáo nêu rõ giới hạn này thay vì tự suy ra số liệu nhóm.

Dữ liệu nhật ký của mười lượt phân tích ở cấu hình B cho thấy lượng việc được huy động thay đổi theo dạng câu hỏi (Bảng 2.4 ở mục 2.6): câu tra cứu và câu xếp hạng chỉ gọi một công cụ và một chuyên viên, câu xu hướng gọi hai công cụ và cả chuyên viên doanh nghiệp lẫn chuyên viên ngành, còn hồ sơ doanh nghiệp gọi ba công cụ. So với một quy trình cố định luôn gọi cả hai chuyên viên và ba công cụ (20 lượt giao việc và 30 lần gọi công cụ cho mười câu), cấu hình B dùng 15 lượt giao việc và 18 lần gọi công cụ. Đây là phép so với một quy trình giả định, không phải một thực nghiệm riêng về tính thích ứng, nên chỉ cho thấy hệ thống chỉ huy động phần việc câu hỏi cần chứ chưa chứng minh phần việc đó tạo ra báo cáo tốt hơn.

**Chấm mù thăm dò.** Các chỉ số tự động không đo độ trôi chảy hay mức dễ đọc, nên tác giả chuẩn bị một phép chấm mù ở quy mô thăm dò: năm câu đại diện (T01, T04, T06, T08, T09), mỗi câu có đầu ra của bốn cấu hình A, B, C và D chạy trên `gpt-5.6-luna` (20 bản), che nhãn cấu hình và trộn thứ tự; người chấm cho điểm 1–5 ở ba tiêu chí đúng, đủ và dễ đọc.

[CHẤM MÙ: chờ kết quả từ người chấm. Điền số người chấm, điểm trung bình theo cấu hình và tỷ lệ cặp chấm trùng điểm; ghi rõ "n = số người chấm, thăm dò, không có ý nghĩa thống kê".]

## 5.7. Kiểm định độ nhạy của bộ kiểm chứng câu nhận định

Mục 5.3 cho thấy cả ba cấu hình đều đạt 100% khớp số, nhưng con số này chỉ có ý nghĩa nếu bộ kiểm chứng thật sự bắt được câu sai. Thực nghiệm độ nhạy đo điều đó bằng đột biến: từ 129 câu đã được bộ kiểm chứng chấp nhận ở thực nghiệm chính, chương trình cài vào mỗi câu một lỗi thuộc một trong 12 loại (đổi số theo hướng nhỏ, đổi số theo hướng lớn, đảo hai chữ số, đổi kỳ, đổi ngân hàng, đảo chiều, đổi chỉ tiêu, đổi thứ hạng, đổi mẫu số, thêm số không có nguồn, thêm quan hệ nhân quả hoặc khuyến nghị), tạo 1.210 câu đột biến, rồi cho bộ kiểm chứng chạy lại. Thực nghiệm được làm hai lần: trước và sau khi bổ sung hai quy tắc kiểm tra mới (mục 4.2.5): quy tắc nhãn chỉ tiêu và quy tắc loại câu tự so sánh. Cả hai lần không gọi mô hình (0 token).

**Hai quy tắc mới.** Quy tắc nhãn chỉ tiêu nhận diện tên chỉ tiêu trong câu, khớp cụm dài nhất trước để "bao phủ nợ xấu" không bị nhận nhầm thành "nợ xấu", rồi bắt buộc tên đó trùng với chỉ tiêu của dữ kiện được trích dẫn. Quy tắc loại câu tự so sánh loại câu có cùng một ngân hàng hoặc cùng một kỳ ở cả hai vế (ví dụ "TCB vượt trội TCB", "từ quý 2/2026 đến quý 2/2026"). Hai quy tắc này được đề xuất sau khi thực nghiệm lần đầu cho thấy điểm yếu, nên cần đọc kết quả "sau" với cảnh giác về việc tự chỉnh rồi tự chấm; để hạn chế, bộ đột biến cũ được đo lại trên cùng 1.210 câu, đồng thời hai bộ mới được sinh bằng hai hạt ngẫu nhiên khác (7 và 2026) từ cùng 129 câu gốc. Mã nguồn đã đổi so với bản dùng cho thực nghiệm chính: phép đo "sau" chạy trên mã nguồn có hai quy tắc mới và có thêm một dòng nhắc quy tắc ở các prompt viết câu (mục 4.2.4); kết quả A/B/C ở mục 5.3 vẫn là kết quả trước thay đổi này.

*Bảng 5.5: Tỷ lệ bộ kiểm chứng bắt được từng loại lỗi cài vào, trước và sau khi thêm hai quy tắc (bộ đột biến hạt 42, khoảng tin cậy Wilson 95%).*

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

Trước khi thêm quy tắc, bộ kiểm chứng bắt tuyệt đối các lỗi về con số, thứ hạng và mẫu số và các câu thêm khẳng định không có nguồn, nhân quả hay khuyến nghị, nhưng bỏ sót 71 trên 1.210 đột biến, tập trung ở lỗi ngữ nghĩa mà con số vẫn đúng: một câu giữ nguyên "50,0%" nhưng đổi "tỷ lệ bao phủ nợ xấu" thành "tỷ lệ nợ xấu" vẫn được chấp nhận ở 25 trên 120 lần thử. Tác giả xem lại thủ công 71 câu lọt lưới và thấy 37 câu (52%) là đột biến tự quy chiếu, loại lỗi mà một mô hình thật hiếm khi viết ra. Việc phân loại này do tác giả thực hiện sau khi đã thấy kết quả, nên số liệu thô là kết quả chính.

Sau khi thêm hai quy tắc, số đột biến lọt giảm từ 71 xuống 10, trong đó không còn đột biến tự quy chiếu nào. Mười đột biến còn lại là sáu câu đổi kỳ sang một kỳ khác vẫn hợp lệ với các dữ kiện đã trích dẫn, ba câu đảo chiều mệnh đề phụ (ví dụ "ngược chiều trung vị nhóm tăng" thành "ngược chiều trung vị nhóm giảm") và một câu nhiều chỉ tiêu có cả hai nhãn bị đổi cùng nằm trong dữ kiện trích dẫn. Trên hai bộ đột biến mới (hạt 7 và 2026), tỷ lệ bắt chung sau khi thêm quy tắc là 98,8% (1.196/1.210) và 99,0% (1.198/1.210), so với 93,8% và 93,6% trước đó; riêng đổi chỉ tiêu đạt 99,2% (119/120) ở cả hai. Kết quả giống nhau ở hạt khác cho thấy cải thiện không phụ thuộc vào một lần chọn câu ngẫu nhiên cụ thể, nhưng cần lưu ý rằng các toán tử đột biến vẫn là những toán tử đã dẫn tới việc đề xuất hai quy tắc (và ở toán tử đổi chỉ tiêu, các hạt khác nhau cho kết quả trước thay đổi gần như y hệt), nên đây chưa phải thử nghiệm trên loại lỗi mới. Khả năng bắt các lỗi ngữ nghĩa kiểu khác (câu đúng từng ý nhưng kết luận sai hàm ý) vẫn chưa được đo.

**Tỷ lệ bác bỏ nhầm.** 129 câu gốc không đột biến vẫn được chấp nhận sau khi thêm quy tắc (129/129). Ngoài ra bộ kiểm chứng mới được chạy lại trên 171 câu đã được chấp nhận ở thực nghiệm lặp trên `gpt-5.6-luna` và các lần chạy so sánh mô hình (thư mục `experiments/e2r`): cả 171 câu vẫn được chấp nhận. Tổng cộng 300 trên 300 câu hợp lệ được chấp nhận, tức không có bác bỏ nhầm trong phạm vi các câu này (0,0%, khoảng tin cậy Wilson 95% đến khoảng 1,3%). Đây là tỷ lệ đo trên các câu mà mô hình đã được hướng dẫn viết theo quy tắc cũ; trên câu do mô hình viết sau khi biết quy tắc mới, tỷ lệ bác bỏ nhầm sẽ được đo ở lần chạy lại ở mục 5.8.

## 5.8. Đánh giá mức độ phụ thuộc vào mô hình ngôn ngữ lớn

Thực nghiệm chính chỉ dùng một mô hình. Thực nghiệm so sánh mô hình chạy lại cấu hình B (phân cấp, không phản biện) trên cùng 12 câu hỏi với năm mô hình (ba của OpenAI, hai của DeepSeek), mỗi mô hình một lần, trên cùng phiên bản ban đầu của hệ thống, nhằm xem kết luận có phụ thuộc mô hình hay không.

*Bảng 5.6: Cấu hình B trên năm mô hình (một lần chạy, phiên bản ban đầu).*

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

**Chạy lại cả ba cấu hình trên `gpt-5.6-luna`.** Thực nghiệm chính chỉ dùng một mô hình, nên để kiểm tra kết luận về A, B, C có giữ khi đổi mô hình hay không, cả ba cấu hình được chạy lại trên `gpt-5.6-luna` (ngày 22/10/2026), 12 câu một lần mỗi cấu hình (36 lượt, 658.442 token), cùng giao thức, cùng bộ dữ liệu khóa và cùng bộ chấm. Mã nguồn lần này là phiên bản sau nâng cấp (mục 5.12) và có thêm hai quy tắc kiểm tra mới (mục 4.2.5), nên so sánh hai mô hình là so sánh trên hai phiên bản mã nguồn khác nhau, không phải phép đổi mô hình thuần túy. Cấu hình D cũng được chạy lại trên mã nguồn mới (không gọi mô hình). Kế hoạch của 12 câu trùng mã băm giữa A, B và C. Không câu nào của A, B, C bị loại bởi hai quy tắc mới.

*Bảng 5.7: Kết quả tổng hợp theo cấu hình (mô hình `gpt-5.6-luna`, mã nguồn sau nâng cấp và sau khi thêm quy tắc, 12 lượt mỗi cấu hình).*

| Chỉ số | A – một tác tử | B – phân cấp | C – phân cấp có phản biện | D – chỉ dùng câu mẫu |
|---|:---:|:---:|:---:|:---:|
| Trả lời được (10 câu phân tích) | 10/10 | 10/10 | 10/10 | 10/10 |
| Từ chối đúng (R1, R2) | 2/2 | 2/2 | 2/2 | 2/2 |
| Hoàn thành trọn vẹn (trên 10 câu phân tích) | 10/10 | 10/10 | 2/10 | 10/10 |
| Con số trong câu được giữ khớp với dữ kiện | 100,0% | 100,0% | 100,0% | 100,0% |
| Độ phủ chỉ tiêu bắt buộc (trung bình 12 lượt) | 0,927 | 0,927 | 0,927 | 0,698 |
| Độ phủ chỉ tiêu bắt buộc (trung bình 10 câu phân tích) | 0,912 | 0,912 | 0,912 | 0,637 |
| Câu bị loại / câu được viết | 0/67 (0,0%) | 1/50 (2,0%) | 30/85 (35,3%) | 12/63 (19,0%) |
| Phát hiện liên tầng trung bình mỗi lượt | 0,50 | 0,42 | 1,00 | 0,42 |
| Thời gian xử lý trung bình | 17,2 giây | 28,3 giây | 86,1 giây | 1,7 giây |
| Số lượt gọi mô hình trung bình | 0,8 | 2,1 | 5,6 | 0 |
| Token trung bình mỗi lượt | 5.127 | 10.128 | 39.616 | 0 |
| Số vòng sửa đổi trung bình | 0,00 | 0,00 | 1,50 | 0,00 |

Trên mô hình mạnh hơn, ba kết luận thay đổi so với DeepSeek V4 Pro. Thứ nhất, độ phủ của A, B và C bằng nhau (0,912 trên 10 câu); B thắng A ở một câu (T05: 1,00 so với 0,75), thua ở một câu (T08: 0,38 so với 0,62) và hòa ở tám câu, nên lợi thế của B ở thực nghiệm chính không còn. Thứ hai, A trở nên đáng tin hơn: hoàn thành trọn vẹn 10/10 và không câu nào bị loại (0/67), trong khi ở DeepSeek V4 Pro A hoàn thành 7/10 và bị loại 8/52 câu. Thứ ba, C vẫn là cấu hình tệ nhất về chi phí và về hoàn thành: chỉ 2/10 báo cáo hoàn thành trọn vẹn, 35,3% câu bị loại, token gấp 3,9 lần B và gấp 7,7 lần A, không được lợi gì về độ phủ. Điều không đổi ở cả hai mô hình là độ chính xác của con số (100% khớp, 100% truy vết), thứ tự chi phí A < B < C và việc C không cải thiện độ phủ. Cấu hình D, vì không dùng mô hình, giữ nguyên độ phủ 0,698 và vẫn kém ba cấu hình có mô hình ở các câu cần nhiều chỉ tiêu (thắng 0, hòa 5, thua 5 so với B; thắng 0, hòa 4, thua 6 so với A). Trên mã nguồn mới, D bị loại 12 trên 63 câu thay vì 6 trên 60 như trước: sáu câu thêm đều là dòng chú thích hình chung chung (ví dụ "Biểu đồ thể hiện Tương quan Bao phủ và Nợ xấu · Q2/2026") nêu hai chỉ tiêu nhưng chỉ trích dẫn dữ kiện của một chỉ tiêu, bị quy tắc nhãn chỉ tiêu loại. Đó là bác bỏ nhầm theo nghĩa các dòng này không chứa nhận định phân tích nào, và không làm đổi độ phủ; nhưng nó cho thấy quy tắc nhãn chỉ tiêu có thể loại cả những câu mẫu hợp lệ, một điểm cần xử lý nếu đưa quy tắc vào dùng thật.

Hai mô hình cho ba bài học về cách đọc thực nghiệm. Một là kết luận "cấu hình nào tốt hơn" không độc lập với mô hình: ở mô hình yếu hơn, chia việc cho nhiều tác tử có lợi nhỏ; ở mô hình mạnh hơn, một tác tử viết đủ tốt và cấu hình đơn giản nhất rẻ nhất. Hai là phản biện kèm sửa đổi không bù được chi phí của nó ở cả hai mô hình. Ba là độ chính xác của con số đến từ lớp kiểm soát, không từ mô hình hay cấu hình. Vì chỉ có hai mô hình, một lần chạy mỗi cấu hình và hai phiên bản mã nguồn khác nhau, các kết luận trên là quan sát, không phải kết luận thống kê.


## 5.9. Kiểm định khả năng chống chịu trước các truy vấn đối kháng

Kiểm tra đối kháng chạy mười lăm câu hỏi đối kháng thuộc bảy nhóm lên cả ba cấu hình với `gpt-5.6-luna`: chèn chỉ dẫn vào câu hỏi (3 câu), hỏi thực thể hoặc kỳ không tồn tại (2 + 2), mồi bịa số (3), xin lời khuyên mua bán (2), tiền đề sai (1) và ngoài phạm vi (2). Kết quả kỳ vọng là hệ thống từ chối hoặc nêu rõ giới hạn, và không đưa ra con số không có nguồn, khuyến nghị đầu tư hay khẳng định theo tiền đề sai.

*Bảng 5.8: Kiểm tra đối kháng trước và sau sửa lỗi ngoài phạm vi.*

| Lần | Mã | Số câu × cấu hình | Đạt kỳ vọng mỗi cấu hình | Nhóm ngoài phạm vi | Chèn chỉ dẫn, bịa số, khuyến nghị, tiền đề sai |
|---|---|:---:|:---:|:---:|:---:|
| Kiểm tra đối kháng | Ban đầu | 15 × 3 | 13/15 (86,7%) | 0/2 | 0 vi phạm |
| Kiểm tra đối kháng sau sửa | Sau nâng cấp | 8 × 3 | 8/8 | 2/2 | 0 vi phạm |

Trước khi sửa, cả ba cấu hình giữ vững mọi nhóm tấn công, trừ nhóm ngoài phạm vi: yêu cầu sáng tác thơ và dự báo giá vàng không bị từ chối mà vẫn nhận báo cáo ngành, vì bộ lập kế hoạch mặc định về kế hoạch xếp hạng khi không có ngân hàng nào được nêu. Sau khi thêm cổng phạm vi (mục 5.12), cả hai câu bị từ chối ở cả ba cấu hình.

Lần chạy sau sửa chỉ là tập con tám câu (hai câu ngoài phạm vi và một câu đại diện của mỗi nhóm còn lại), nên chỉ cho biết sửa lỗi có hiệu quả và không gây lùi ở các nhóm được lấy mẫu, chưa phải một lần chạy lại toàn bộ. Ba cấu hình cũng cho kết quả giống hệt nhau ở mọi nhóm: khả năng chống chịu nằm ở lớp kiểm tra xác định dùng chung (hiểu câu hỏi, kiểm tra dữ liệu, bộ kiểm chứng câu), không phải ở việc phân cấp hay phản biện. Điều này củng cố kết luận của mục 5.3 và 5.4 rằng độ an toàn do kiến trúc kiểm soát mang lại chứ không do cấu hình tác tử. Cổng phạm vi hiện là bộ lọc theo dấu hiệu từ khóa và ý định phân tích, không phải bộ phân loại ý định; các câu mơ hồ hoặc diễn đạt lạ có thể bị chặn nhầm hoặc lọt qua.

## 5.10. Đánh giá thách thức trong quy trình số hóa báo cáo tài chính gốc

Hệ thống nhận số liệu từ báo cáo tài chính gốc dạng PDF, trong đó phần lớn là bản quét. Thực nghiệm này đo xem khó khăn nằm ở nhận dạng ký tự hay ở cấu trúc bảng, không gọi mô hình ngôn ngữ. Với 885 số liệu đầu vào đã được chấp nhận và có trang nguồn (xem giải thích tập con ở đoạn sau Bảng 5.9), thực nghiệm đo khả năng số hóa hỏi hai câu: (a) giá trị đã được chấp nhận có xuất hiện nguyên văn trong văn bản của đúng trang đó không; (b) một bộ trích xuất đơn giản (tìm dòng có nhãn gần nhất rồi lấy số ở cột tương ứng) có lấy đúng giá trị không.

*Bảng 5.9: Giá trị có mặt trên trang và độ đúng của bộ trích xuất đơn giản.*

| Phép đo | Số liệu | Kết quả |
|---|:---:|:---:|
| (a) Trang có lớp văn bản: giá trị xuất hiện nguyên văn | 185 | 178 (96,2%) |
| (a) Trang quét, nhận dạng Tesseract: giá trị xuất hiện nguyên văn | 700 | 652 (93,1%) |
| (b) Bộ trích xuất đơn giản: lấy đúng | 885 | 463 (52,3%) |
| (b) Không tìm thấy dòng | 885 | 236 (26,7%) |
| (b) Lấy sai hàng hoặc cột | 885 | 185 (20,9%) |
| (b) Thiếu cột để lấy | 885 | 1 (0,1%) |

Con số 885 là tập con của dữ liệu đầu vào, không phải toàn bộ. Bộ dữ liệu cuối có 1.735 quan sát, gồm 1.335 số liệu đầu vào đọc từ báo cáo gốc và 400 giá trị chỉ tiêu do chương trình tính lại (4 chỉ tiêu × 100 ô ngân hàng – quý). Thực nghiệm này lấy 1.123 dòng trong tệp đầu vào của dữ liệu quý; trong đó có 150 dòng không có trang hoặc tệp PDF cục bộ để đối chiếu (số liệu năm tài chính và số liệu so sánh) và 88 dòng có trang chưa được nhận dạng ký tự, nên còn 885 dòng (1.123 − 150 − 88). Còn lại 212 quan sát đầu vào của bộ dữ liệu cuối không nằm trong tệp đầu vào quý và không được đo ở đây. Vì vậy 885 là mẫu đo được, đại diện cho khoảng 66% số liệu đầu vào (885 trên 1.335), không phải kết quả cho toàn bộ dữ liệu.

Nhận dạng ký tự khó là nguyên nhân chính của sai sót: 93–96% giá trị xuất hiện nguyên văn trên đúng trang. Phép đo này chỉ cho biết chuỗi số có mặt trên trang, chưa chứng minh ô đó được đọc đúng vị trí, nên đây là chỉ dấu chứ không phải kết luận. Khó khăn rõ hơn nằm ở cấu trúc: bộ trích xuất đơn giản chọn đúng hàng và đúng cột chỉ khoảng một nửa số lần, và vì là một đối chứng yếu, kết quả 52% không đại diện cho các bộ trích xuất tốt hơn. Bộ trích xuất đạt 88–96% với các chỉ tiêu đứng một dòng riêng như tổng tài sản hay nợ nhóm 4, nhóm 5, nhưng chỉ 27% với lợi nhuận sau thuế và 0% với tổng vốn chủ sở hữu, vì báo cáo kết quả kinh doanh có cả cột quý lẫn cột lũy kế và vốn chủ sở hữu thường xuất hiện như một dòng tổng của mục. Kết quả này ủng hộ quyết định thiết kế giữ giá trị trích xuất ở trạng thái "ứng viên" cho đến khi được đối chiếu với đẳng thức kế toán và tính lại theo công thức được định danh phiên bản, và cho thấy quy trình số hóa của khóa luận là quy trình bán tự động có tác tử AI hỗ trợ, trong đó thẩm định độc lập là hướng mở rộng chứ chưa được thực hiện.

## 5.11. Ca STB quý 4/2025: bất thường trong dữ liệu và vai trò của hồ sơ gốc

Khi đối soát dữ liệu quý của mười ngân hàng, một bất thường được nêu: lợi nhuận sau thuế lũy kế của STB giảm từ 8.691,6 tỷ đồng (đến hết quý 3/2025) xuống 5.939,1 tỷ đồng (đến hết quý 4/2025), tức giảm 2.752,5 tỷ đồng. Lợi nhuận lũy kế trong năm thường không giảm, nên đây có thể là lỗi nhập hoặc nhầm cột. Đối chiếu với báo cáo tài chính hợp nhất đã kiểm toán và báo cáo quý 4 cho thấy con số 5.939,1 tỷ đồng là đúng: STB ghi nhận lỗ sau thuế 2.752,5 tỷ đồng riêng trong quý 4/2025, sau khi trích lập dự phòng rủi ro tín dụng 9.232,2 tỷ đồng trong quý. Dữ liệu vì thế không bị sửa.

Điều thay đổi là quy trình: bộ dựng snapshot được bổ sung kiểm tra tính đơn điệu của lợi nhuận lũy kế trong năm, và chỉ chấp nhận một khoản lỗ quý khi nó nằm trong danh sách ngoại lệ đã được kiểm chứng kèm trang nguồn. Kiểm tra bất biến kế toán là cách rẻ để đưa các điểm đáng ngờ ra để soát, còn quyết định cuối cùng thuộc về hồ sơ gốc chứ không thuộc về kết quả của quy tắc kiểm tra. Quá trình trích xuất và đối chiếu dữ liệu từ báo cáo gốc được thực hiện bán tự động, với sự kiểm tra của tác giả thông qua các ràng buộc đẳng thức kế toán; tuy nhiên, chưa có chuyên gia độc lập thứ hai thẩm định chéo.

## 5.12. Nâng cấp sau đánh giá

Sau khi thực nghiệm chính (05/10/2026) và các thực nghiệm bổ sung đã chạy trên phiên bản ban đầu, sản phẩm được nâng cấp thêm. Các nâng cấp dưới đây xảy ra sau các số liệu ở mục 5.3–5.10 và không được tính trong chúng, trừ lần chạy lặp và kiểm tra đối kháng sau sửa chạy trên phiên bản sau nâng cấp.

Các hạng mục nâng cấp gồm năm nhóm. Một là phát trực tiếp bản nháp của chuyên viên và kết luận của bộ kiểm chứng lên màn hình theo dõi. Hai là khung trượt tra cứu nguồn, hiển thị trang PDF, các hàng dữ liệu và đường truy vết của từng con số. Ba là bối cảnh thị trường như giá cổ phiếu và hệ số P/B so với ROE, gắn nhãn riêng để không trộn với số liệu báo cáo. Bốn là kiểm tra tính đơn điệu của lợi nhuận lũy kế (mục 5.11). Năm là cổng phạm vi, từ chối câu hỏi không có thực thể, chỉ tiêu hoặc ý định phân tích ngân hàng (mục 5.9). Ngoài cổng phạm vi, các nâng cấp này không làm đổi kết quả phân tích. Dữ liệu thị trường nằm ngoài phạm vi dữ liệu của Chương 3 và không được đánh giá.

## 5.13. Thảo luận

Thứ nhất, độ tin cậy về con số của báo cáo không đến từ việc chọn cấu hình tác tử nào, mà đến từ kiến trúc kiểm soát bao quanh mô hình: tính toán bằng mã nguồn, dữ kiện có nguồn và kiểm tra từng câu. Các quan sát cùng chỉ về điều này, dù chúng không độc lập hoàn toàn vì cùng dựa vào một cơ chế kiểm soát: bốn cấu hình, kể cả D không dùng mô hình, có cùng độ khớp số và truy vết (mục 5.3); ba mô hình khác nhau cho cùng độ khớp số và truy vết (mục 5.8); và ba cấu hình chống chịu y hệt nhau trước câu hỏi đối kháng (mục 5.9). Đối chiếu với một mô hình phổ thông không có lớp kiểm soát này (mục 1.6) làm rõ giá trị đó: trong mười câu hỏi giống hệt, mô hình nêu 19 con số, chỉ 8 đúng, và không câu trả lời nào có nguồn để kiểm. Với phân tích tài chính, nơi một con số sai làm mất giá trị của cả báo cáo, đây là kết luận có ý nghĩa thực tiễn.

Thứ hai, chính kiến trúc kiểm soát đó có giới hạn mà thực nghiệm độ nhạy đo được. Ở lần đo đầu, bộ kiểm chứng bắt tốt lỗi về số, thứ hạng và mẫu số nhưng bỏ sót khoảng một phần năm các câu giữ nguyên con số và đổi tên chỉ tiêu (20,8%). Hai quy tắc bổ sung (nhãn chỉ tiêu và loại câu tự so sánh) đưa tỷ lệ bắt chung từ 94,1% lên 99,2% và riêng lỗi đổi chỉ tiêu từ 79,2% lên 99,2%, trên cả bộ cũ lẫn hai bộ mới; không có bác bỏ nhầm trên 300 câu hợp lệ do mô hình viết, nhưng có sáu dòng chú thích hình mẫu bị loại nhầm ở cấu hình D (mục 5.8). Tuy vậy, hai quy tắc được thiết kế sau khi thấy kết quả của chính các toán tử đột biến, nên đây chưa phải bằng chứng về khả năng bắt các lỗi chưa từng được thử. Khẳng định "mọi con số đều đúng" vì vậy vẫn phải đi kèm khẳng định "việc con số gắn đúng chỉ tiêu, kỳ và ngân hàng được kiểm bằng quy tắc, đã đo trên các loại lỗi giả lập nhất định".

Thứ ba, giá trị của mô hình và của cách tổ chức tác tử phụ thuộc vào mô hình. Cấu hình D cho thấy một phần đáng kể độ phủ (0,637 trên 10 câu, so với 0,756 đến 0,812 của A và B ở DeepSeek V4 Pro và 0,912 ở `gpt-5.6-luna`) đạt được không cần mô hình, nhất là ở các câu tra cứu, xếp hạng và so sánh một chỉ tiêu; mô hình bổ sung khả năng gom nhiều chỉ tiêu và diễn đạt mạch lạc, hai thứ mà bộ chấm tự động chưa đo trực tiếp. Chuyên môn hóa (B) cải thiện nhẹ độ đầy đủ ở DeepSeek V4 Pro nhưng không còn lợi thế ở `gpt-5.6-luna`, còn phản biện (C) tốn gấp ba đến bốn lần B ở cả hai mô hình, làm giảm tỷ lệ hoàn thành trọn vẹn và không cải thiện độ phủ. Với người phân tích dùng hệ thống theo thời gian thực, B hoặc một tác tử đơn A trên mô hình mạnh là điểm cân bằng hợp lý; C chỉ nên dùng khi bộ phản biện được giới hạn vào các vấn đề quy tắc không kiểm được và được phép bổ sung câu mới thay vì chỉ sửa hoặc loại câu cũ. Việc đổi mô hình làm thay đổi kết quả nhiều hơn việc đổi cấu hình, nên kết luận về A, B và C không nên được hiểu là độc lập với mô hình.

Thứ tư, một thực nghiệm thử trước đó trên bộ Gold v5 (năm ngân hàng, bốn quý năm 2024, ngày 30/9/2026) cho cùng xu hướng chi phí A < B < C và cho thấy C không cải thiện độ phủ; riêng việc B có độ phủ cao hơn A không giữ được khi đổi mô hình, như trên. Cuối cùng, chất lượng câu phụ thuộc nhiều vào việc prompt nêu đủ quy tắc của bộ kiểm tra: trong lần chạy thử với các mô hình khác, tỷ lệ câu được giữ của cùng mô hình tăng từ khoảng 49% lên 84% sau khi ghi rõ quy tắc vào prompt, nên cách đúng là dạy mô hình viết câu đơn giản, mỗi câu một chỉ tiêu và một chiều, thay vì nới lỏng quy tắc.

## 5.14. Các yếu tố ảnh hưởng tới tính hợp lệ của kết quả

Về hợp lệ nội tại, mỗi cặp câu hỏi – cấu hình trong thực nghiệm chính chỉ chạy một lần trong khi đầu ra của mô hình không cố định, và các lượt chạy đồng thời nên thời gian xử lý chịu ảnh hưởng của tải máy chủ. Phép lặp ba lần ở mục 5.8 chỉ có cho một mô hình và một cấu hình, và chạy trên mã đã thay đổi. Phép so sánh DeepSeek V4 Pro với `gpt-5.6-luna` cho A, B, C khác nhau ở cả mô hình lẫn phiên bản mã nguồn (thêm hai quy tắc kiểm tra và một dòng nhắc quy tắc trong prompt), nên không tách được tác động của riêng mô hình. Về hợp lệ cấu trúc, các chỉ số tự động đo độ khớp số, truy vết, độ phủ và chi phí nhưng không đo trực tiếp chất lượng diễn giải và tính hữu ích; chỉ có phép chấm mù thăm dò quy mô nhỏ (mục 5.6), không có chuyên gia chấm đầy đủ. Hai quy tắc kiểm tra mới được thiết kế sau khi thấy kết quả độ nhạy, nên kết quả "sau" có nguy cơ tự chỉnh rồi tự chấm; khoảng cách giữa 79,2% và 99,2% ở lỗi đổi chỉ tiêu cần đọc kèm hạn chế này và kết quả trên hai bộ hạt khác. Việc phân loại các đột biến lọt lưới ở mục 5.7 ở lần đo đầu do chính người thiết kế thực hiện sau khi đã thấy kết quả. Phép đối chiếu mô hình phổ thông ở mục 1.6 chỉ là một lần chạy, một mô hình, không bật tìm kiếm web, do tác giả chấm bằng tay theo quy tắc đặt trước.

Về hợp lệ bên ngoài, dữ liệu gồm mười ngân hàng niêm yết lớn nhất và bốn nhóm chỉ tiêu; A/B/C chạy trên hai mô hình, cấu hình B được kiểm trên ba mô hình OpenAI và hai mô hình DeepSeek với mỗi mô hình một lần, và kiểm tra đối kháng chạy trên một mô hình với mười lăm câu, không đủ để khái quát. Bộ dữ liệu đủ 100/100 ô nên thực nghiệm chính không kiểm tra tình huống thiếu số liệu.

Về quy trình, người phát triển đồng thời là người thiết kế thực nghiệm; bộ câu hỏi, quy tắc chấm và kế hoạch được cố định trước khi chạy nhưng rủi ro thiên lệch trong cách đặt câu hỏi vẫn còn. Một số lượt chạy phải loại bỏ vì lỗi cấu hình hoặc lỗi hạ tầng của dịch vụ mô hình; các lượt này được tách riêng và không dùng trong bất kỳ bảng kết quả nào. Prompt và quy tắc kiểm tra được hiệu chỉnh qua các lần chạy thử trước thực nghiệm chính rồi cố định; lỗi ngoài phạm vi được sửa rồi kiểm lại trên các câu đã thấy, chưa trên câu ngoài phạm vi mới. Cuối cùng, các lỗi của chính hệ thống được phát hiện trong khi đánh giá (câu ngoài phạm vi không bị từ chối; hai mã lý do mới của bộ kiểm chứng chưa được đăng ký trong hợp đồng dữ liệu nên làm sập một lượt phân tích khi chạy cấu hình D lần đầu trên mã mới) đã được sửa sau khi có kết quả; kết quả sau sửa chỉ chứng minh lỗi đã được khắc phục trong tập câu đã thử, không phải hệ thống miễn nhiễm với mọi lỗi khác.

## 5.15. Tính khả thi, chi phí vận hành và điều kiện áp dụng

### 5.15.1. Chi phí vận hành

Chi phí mô hình của một báo cáo được tính từ số token đầu vào và đầu ra thực tế của mười lượt phân tích ở thực nghiệm chính (mô hình DeepSeek V4 Pro), nhân với đơn giá công bố của nhà cung cấp. Theo trang bảng giá của DeepSeek (DeepSeek, 2026), `deepseek-v4-pro` tính 1,32 USD cho một triệu token đầu vào (không trúng bộ nhớ đệm) và 3,96 USD cho một triệu token đầu ra trong giờ cao điểm, bằng một nửa ngoài giờ cao điểm. Để ước lượng an toàn, Bảng 5.10 dùng đơn giá giờ cao điểm và không tính bộ nhớ đệm, tức là cận trên. Với `gpt-5.6-luna`, trang bảng giá của OpenAI (OpenAI, 2026) ghi 0,20 USD cho một triệu token đầu vào và 1,20 USD cho một triệu token đầu ra ở mức Standard. Tỷ giá quy đổi là 25.201 đồng một USD, tỷ giá trung tâm Ngân hàng Nhà nước công bố ngày 30/6/2026 (số liệu này nằm trong bộ dữ liệu vĩ mô của sản phẩm ở trạng thái chờ kiểm định, nên chỉ dùng để quy đổi quy mô chi phí).

*Bảng 5.10: Chi phí mô hình ước tính cho một báo cáo (mười câu phân tích).*

| Mô hình | Cấu hình | Token đầu vào | Token đầu ra | Chi phí (USD) | Chi phí (đồng) |
|---|---|:---:|:---:|:---:|:---:|
| DeepSeek V4 Pro | A – một tác tử | 3.915 | 626 | 0,0077 | 193 |
| DeepSeek V4 Pro | B – phân cấp | 8.644 | 1.258 | 0,0164 | 413 |
| DeepSeek V4 Pro | C – phân cấp có phản biện | 28.206 | 2.822 | 0,0484 | 1.220 |
| `gpt-5.6-luna` | A – một tác tử | 4.389 | 1.764 | 0,0030 | 76 |
| `gpt-5.6-luna` | B – phân cấp | 9.258 | 2.895 | 0,0053 | 134 |
| `gpt-5.6-luna` | C – phân cấp có phản biện | 38.284 | 9.254 | 0,0188 | 473 |
| Không gọi mô hình | D – chỉ dùng câu mẫu | 0 | 0 | 0 | 0 |

Chi phí mô hình của một báo cáo vì vậy chỉ ở mức từ vài chục đến hơn một nghìn đồng, và chênh lệch giữa các cấu hình nhỏ so với chi phí con người; khác biệt chính là thời gian chờ (từ khoảng 21 giây ở A đến khoảng 75 giây ở C trên mười lượt phân tích của DeepSeek V4 Pro; từ 20 đến 103 giây ở `gpt-5.6-luna`). Chi phí lớn nằm ở chuẩn bị dữ liệu: mỗi quý mới cần đọc báo cáo hợp nhất của mười ngân hàng, tức khoảng 130 số đầu vào (1.335 số đầu vào chia cho mười quý), trong đó phần lớn là bản quét phải đối soát từng ô (mục 5.10). Khóa luận chưa đo số giờ công cho việc này nên không quy ra tiền.

### 5.15.2. Đối chiếu thời gian với làm thủ công

[ĐO TAY: chờ. Ba câu T03 (tra cứu), T09 (so sánh hai ngân hàng) và T01 (hồ sơ) được tác giả tự làm tay từ báo cáo gốc, bấm giờ, n = 3, một người đo, chỉ tham khảo; so với thời gian của hệ thống ở Bảng 5.2.]

### 5.15.3. Điều kiện áp dụng thực tế

Hệ thống chỉ tin cậy khi các điều kiện sau được giữ. Một là có báo cáo tài chính hợp nhất gốc của từng ngân hàng cho kỳ cần hỏi; hệ thống từ chối kỳ hoặc ngân hàng chưa có dữ liệu thay vì ước tính (R1, R2, mục 5.3). Hai là dữ liệu được cập nhật mỗi quý theo quy trình ở mục 3.2, và cần người thứ hai đối soát độc lập vì ở khóa luận này chưa có chuyên gia thẩm định chéo (mục 5.11). Ba là phạm vi hiện có hẹp: mười ngân hàng và bốn chỉ tiêu; mở rộng thêm ngân hàng hay chỉ tiêu (vốn, thanh khoản, biên lãi) nghĩa là thêm công thức, thêm quy tắc kiểm tra và đối soát lại toàn bộ. Bốn là phụ thuộc vào nhà cung cấp mô hình: kết quả thay đổi theo mô hình (mục 5.8) và theo từng lần chạy, nên khi nhà cung cấp đổi phiên bản hoặc giá thì phải chạy lại bộ câu hỏi chuẩn để kiểm tra trước khi dùng tiếp.

### 5.15.4. Rủi ro và giảm thiểu

*Bảng 5.11: Rủi ro khi áp dụng và biện pháp giảm thiểu.*

| Rủi ro | Mức độ | Khả năng | Biện pháp |
|---|---|---|---|
| Số liệu đầu vào đọc sai từ báo cáo quét | Cao | Trung bình: chuỗi số xuất hiện trên trang 93–96%, bộ trích xuất đơn giản chỉ đúng 52% (mục 5.10) | Giữ số ở trạng thái ứng viên, đối chiếu đẳng thức kế toán, bổ sung người thẩm định thứ hai |
| Câu giữ số đúng nhưng gắn sai tên chỉ tiêu | Trung bình | Có đo: bộ kiểm chứng bỏ sót 20,8% câu đổi chỉ tiêu (mục 5.7) | Quy tắc kiểm tra nhãn chỉ tiêu; người dùng đọc kèm bảng số liệu và nguồn |
| Nhà cung cấp đổi phiên bản hoặc giá mô hình | Trung bình | Cao: kết quả đã khác nhau giữa các mô hình (mục 5.8) | Ghi phiên bản mô hình trong mỗi lượt chạy; chạy lại bộ câu hỏi chuẩn trước khi đổi |
| Câu hỏi ngoài phạm vi lọt qua cổng từ khóa | Trung bình | Trung bình: cổng chỉ dựa trên từ khóa (mục 5.9) | Mở rộng bộ câu đối kháng; thông báo từ chối nêu rõ phạm vi hỗ trợ |
| Người dùng coi báo cáo là khuyến nghị đầu tư | Cao | Trung bình | Hệ thống từ chối xin lời khuyên mua bán; mỗi báo cáo ghi rõ chỉ tổng hợp số liệu |
| Dịch vụ gián đoạn do hạ tầng miễn phí | Thấp | Trung bình | Bản trình diễn dùng hạ tầng miễn phí; khi dùng thật cần hạ tầng trả phí và sao lưu |

### 5.15.5. Khuyến nghị áp dụng

Hệ thống phù hợp để nhà phân tích và cán bộ đối sánh tra nhanh số liệu hợp nhất, xu hướng và vị thế của mười ngân hàng, với điều kiện mỗi con số được đọc kèm trang nguồn. Nên dùng cấu hình B làm mặc định vì độ phủ cao nhất với chi phí vừa phải; chỉ dùng C khi có người xem xét kết quả. Không nên dùng để đưa khuyến nghị mua bán, để dự báo, hay cho ngân hàng và chỉ tiêu ngoài bộ dữ liệu. Không nên coi báo cáo là bản cuối khi chưa kiểm tra lại số liệu quan trọng với báo cáo gốc. Trước khi mở rộng phạm vi hoặc đổi mô hình, cần chạy lại bộ câu hỏi chuẩn và bộ kiểm tra đột biến. Mọi quy đổi lợi ích ra tiền, nếu có, chỉ là kịch bản giả định của tác giả chứ không phải số đo.
