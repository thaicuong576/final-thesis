# CHƯƠNG 5. KẾT QUẢ VÀ THẢO LUẬN

Chương này trình bày kết quả kiểm tra kỹ thuật, kết quả thực nghiệm so sánh ba cấu hình A, B, C trên bộ dữ liệu mười ngân hàng, và bốn thực nghiệm bổ sung đo độ tin cậy của chính các cơ chế kiểm soát: độ nhạy của bộ kiểm chứng câu (E1), so sánh giữa các mô hình ngôn ngữ (E2), kiểm tra đối kháng (E3) và đo khả năng số hóa từ báo cáo gốc (E5). Mọi số liệu được lấy từ các tệp kết quả lưu cùng mã nguồn (thư mục `experiments`, tổng hợp tại `experiments/RESULTS-INDEX.md`); không có số nào được nhập tay.

## 5.1. Kết quả kiểm tra kỹ thuật

Phiên bản dùng cho thực nghiệm A/B/C có hơn 900 bài kiểm thử tự động phía máy chủ và 188 bài phía giao diện, tất cả đều đạt trên hệ thống tích hợp liên tục. Tại thời điểm hoàn thiện khóa luận (13/10/2026), bộ kiểm thử đã tăng lên 1.020 bài phía máy chủ (5 bài bị bỏ qua có chủ đích) và 235 bài phía giao diện, vẫn đạt toàn bộ. Các bài kiểm thử dùng mô hình và dữ liệu giả lập nên chỉ chứng minh hệ thống chạy đúng với các kịch bản đã mô tả. Vì vậy, hệ thống còn được chạy với mô hình thật trên bản triển khai: các luồng ở mục 4.5, gồm tra cứu, hồ sơ doanh nghiệp, so sánh, xếp hạng, xu hướng và tải lên ngân hàng mới, cho kết quả đúng ở các lần chạy thử.

Việc chạy thật cũng bộc lộ những điều kiểm thử giả lập không phát hiện. Thứ nhất, nhiều câu nhận định đúng bị loại vì lời nhắc chưa nêu đủ quy tắc của bộ kiểm tra, được khắc phục bằng cách ghi rõ các quy tắc này vào lời nhắc (mục 4.2.4). Thứ hai, và là điểm phải nêu rõ: ở phiên bản dùng cho thực nghiệm, câu hỏi hoàn toàn ngoài phạm vi (yêu cầu sáng tác thơ, dự báo giá vàng) **không** bị từ chối mà vẫn nhận một báo cáo ngành, vì bộ lập kế hoạch mặc định về kế hoạch xếp hạng khi câu hỏi không nêu ngân hàng nào (mục 5.9). Lỗi này đã được sửa sau đánh giá (mục 5.12); phần từ chối câu hỏi ở kỳ hoặc ngân hàng không có dữ liệu thì hoạt động đúng ngay từ đầu.

## 5.2. Thiết lập thực nghiệm

Bảng 5.0 liệt kê toàn bộ các thực nghiệm đã chạy, câu hỏi mỗi thực nghiệm trả lời và nguồn kết quả trong kho mã.

*Bảng 5.0: Danh mục thực nghiệm.*

| Mã | Trả lời câu hỏi nào | Mô hình | Mã nguồn | Cấu hình, số câu × số lần | Token | Nguồn |
|---|---|---|---|---|---|---|
| ER-9 | A, B, C khác nhau thế nào (RQ2, RQ3) | DeepSeek V4 Pro | `5eca302` / `7e36a1a` | 3 cấu hình, 12 câu × 1 | 454.706 | `experiments/er9` |
| E1 | Bộ kiểm chứng câu bắt được bao nhiêu loại lỗi cài vào | không gọi mô hình | — (chạy trên kết quả ER-9) | 1.210 câu đột biến từ 129 câu đã được chấp nhận ở ER-9 | 0 | `experiments/mut1` |
| E2 | Kết quả có phụ thuộc mô hình không | `gpt-5.4-nano`, `gpt-5.4-mini`, `gpt-5.6-luna` (OpenAI) | `06611d9` | chỉ cấu hình B, 12 câu × 1 | 321.133 | `experiments/e2` |
| E2r | Kết quả của `gpt-5.6-luna` có ổn định khi chạy lại trên mã mới không | `gpt-5.6-luna` | `b6344a4` | chỉ cấu hình B, 12 câu × 3 lần | 359.298 | `experiments/e2r` |
| E3 | Hệ thống chống chịu thế nào trước câu hỏi đối kháng | `gpt-5.6-luna` | `06611d9` | 3 cấu hình, 15 câu × 1 | 462.802 | `experiments/e3` |
| E3 sau sửa | Sửa lỗi ngoài phạm vi có hiệu quả và không gây lùi không | `gpt-5.6-luna` | `b6344a4` | 3 cấu hình, tập con 8 câu × 1 | 210.080 | `experiments/e3` |
| E5 | Khó khăn của số hóa nằm ở nhận dạng ký tự hay ở cấu trúc bảng | không gọi mô hình | — | 885 số liệu đầu vào đã chấp nhận | 0 | `experiments/e5` |

Thực nghiệm chính ER-9 được chạy ngày 05/10/2026 trên bộ dữ liệu mười ngân hàng đã khóa mã băm (mục 3.2.3), với mô hình DeepSeek V4 Pro (`deepseek-v4-pro-0813`). Mười hai câu hỏi ở Bảng 3.4 được chạy một lần trên mỗi cấu hình, tạo thành 36 lượt; thứ tự được xáo trộn theo một giá trị cố định để có thể lặp lại, và sáu lượt chạy đồng thời. Tổng lượng văn bản mô hình xử lý là 454.706 token, dưới giới hạn 3.000.000 token đặt trước cho lần chạy. Sau khi chạy, hệ thống xác nhận cả mười hai câu hỏi có kế hoạch giống hệt nhau giữa ba cấu hình. Việc chấm điểm do chương trình thực hiện theo các chỉ số ở mục 3.3.4.

Về chi phí tổng thể: cộng các lượt hợp lệ trong Bảng 5.0 với lượt thử trên bộ Gold v5 ngày 30/09/2026 (474.265 token) và hai mô hình DeepSeek của E2 (329.362 token, mục 5.8), lượng token ghi trong các tệp kết quả hợp lệ là khoảng 2,61 triệu. Ngoài ra, các lượt chạy bị loại vì sai cấu hình (chạy nhầm mô hình, gateway trả lỗi, hết số dư) đã tiêu thêm khoảng 1,50 triệu token (mục 5.14), nâng tổng lượng đã tiêu cho toàn bộ quá trình đánh giá lên khoảng 4,1 triệu. Mỗi lần chạy đều nằm dưới giới hạn 3.000.000 token đặt cho riêng nó, nhưng tổng toàn bộ quá trình vượt con số này; đây là chi phí thật của việc phải làm lại, và được nêu để không đánh giá thấp chi phí vận hành thực nghiệm.

## 5.3. Kết quả tổng hợp (ER-9)

*Bảng 5.1: Kết quả tổng hợp theo cấu hình (12 lượt mỗi cấu hình).*

| Chỉ số | A – một tác tử | B – phân cấp | C – phân cấp có phản biện |
|---|:---:|:---:|:---:|
| Trả lời được (10 câu phân tích) | 10/10 | 10/10 | 10/10 |
| Từ chối đúng (R1, R2) | 2/2 | 2/2 | 2/2 |
| Hoàn thành trọn vẹn, không ghi chú giới hạn (trên 12) | 7 (58,3%) | 9 (75,0%) | 4 (33,3%) |
| Con số trong câu được giữ khớp với dữ kiện được trích | 100% | 100% | 100% |
| Truy được về số liệu gốc | 100% | 100% | 100% |
| Độ phủ chỉ tiêu bắt buộc | 0,797 | 0,844 | 0,781 |
| Câu bị loại / câu được viết | 8/52 (15,4%) | 9/53 (17,0%) | 22/63 (34,9%) |
| Báo cáo dùng bố cục dựng sẵn (trên 10) | 3 | 1 | 2 |
| Phát hiện liên tầng trung bình mỗi lượt | 0,33 | 0,33 | 0,67 |
| Thời gian xử lý trung bình | 17,5 giây | 27,5 giây | 62,9 giây |
| Số lượt gọi mô hình trung bình | 0,8 | 2,1 | 4,4 |
| Token trung bình mỗi lượt | 3.784 | 8.252 | 25.856 |
| Số vòng sửa đổi trung bình | 0 | 0,0 | 1,25 |

![](experiments/er9/analysis/figure_er9_cost_latency.png)

Hình 5.1: Chi phí vận hành theo cấu hình (thời gian xử lý và token)

Cả ba cấu hình đạt 100% ở chỉ số khớp số và 100% truy được về số liệu gốc. Kết quả này không phản ánh năng lực khác nhau giữa các cấu hình mà là hệ quả của thiết kế: mọi con số do công cụ tính bằng mã nguồn, và câu chỉ vào báo cáo khi bộ kiểm tra xác nhận số, thứ hạng, kỳ và chiều so sánh khớp với dữ kiện được trích. Kiến trúc chuyển rủi ro "sai số" của mô hình thành rủi ro "câu bị loại", và mọi câu bị loại được ghi lại kèm lý do.

Cần đọc con số 100% này đúng nghĩa. Nó cho biết mọi con số xuất hiện trong câu được giữ đều trùng với một dữ kiện đã được tính và trích dẫn; nó **không** cho biết mọi con số đều gắn đúng tên chỉ tiêu, đúng kỳ hay đúng ngân hàng. Mục 5.7 đo trực tiếp điểm này: một câu giữ nguyên con số đúng nhưng đổi tên chỉ tiêu vẫn lọt qua bộ kiểm chứng ở 20,8% số trường hợp thử. Nói cách khác, "tính đúng số" ở đây là tính đúng của con số, chưa phải tính đúng của toàn bộ nhận định.

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

Cái giá của B là chi phí: khoảng 2,2 lần token và thêm khoảng 10 giây mỗi lượt, với khoảng tin cậy không chứa 0. Độ chính xác của con số và khả năng truy vết không khác nhau vì cùng đi qua công cụ tính toán và bộ kiểm tra câu. Tỷ lệ câu bị loại của A và B tương đương (15,4% và 17,0%), nhưng khác về lý do: A chủ yếu bị loại vì nêu xu hướng khi không có dữ kiện thay đổi (5 trên 8 câu), còn B chủ yếu vì chiều xu hướng không khớp ngưỡng đi ngang (5 trên 9 câu).

**Trả lời RQ2:** trong trường hợp nghiên cứu này, chuyên môn hóa nhiệm vụ cải thiện vừa phải độ đầy đủ và độ ổn định của báo cáo với chi phí khoảng gấp đôi, trong khi độ chính xác của con số được bảo đảm như nhau bởi cơ chế kiểm tra chung. Kết luận này dựa trên một mô hình và một lần chạy mỗi cặp; mục 5.8 cho thấy kết quả của cấu hình B cũng thay đổi đáng kể khi đổi mô hình.

## 5.5. Trả lời RQ3: bổ sung phản biện và sửa đổi (C so với B)

Bổ sung phản biện và tối đa hai vòng sửa đổi không làm tăng độ phủ; ngược lại, độ phủ trung bình của C thấp hơn B khoảng 6 điểm phần trăm (khoảng tin cậy chứa 0). Số phát hiện liên tầng được nêu tăng gấp đôi (0,67 so với 0,33 mỗi lượt), phù hợp với việc bộ phản biện được yêu cầu kiểm tra các mâu thuẫn liên tầng đã có được nêu trong báo cáo hay chưa. Chi phí tăng mạnh: token gấp 3,1 lần B và 6,8 lần A, thêm khoảng 35 giây mỗi lượt so với B; riêng hồ sơ BID (T01) dùng 85.187 token cho một lượt.

Nguyên nhân độ phủ giảm thấy rõ khi xem các câu bị loại. C bị loại 22 trên 63 câu, trong đó 12 câu bị loại vì còn vấn đề phản biện chưa giải quyết sau hai vòng sửa. Chỉ 4 trên 12 lượt của C hoàn thành trọn vẹn. Các vấn đề còn mở khi kết thúc chủ yếu thuộc loại "tổng hợp chưa đầy đủ" (8 trên 9 vấn đề, 7 ở mức nghiêm trọng), tức bộ phản biện yêu cầu báo cáo nói thêm về các chỉ tiêu khác, ví dụ ở hồ sơ BID: báo cáo "đã bỏ sót hoàn toàn" tỷ lệ nợ xấu và bao phủ nợ xấu. Khi câu viết lại vẫn không đạt, câu bị loại, nên chính yêu cầu "nói đầy đủ hơn" lại làm báo cáo mất câu và giảm độ phủ (T01: 0,5 so với 0,75 của B; T10: 0,5 so với 1,0).

**Trả lời RQ3:** trong điều kiện của thực nghiệm, phản biện và sửa đổi làm chi phí tăng khoảng ba lần so với B, không cải thiện độ chính xác hay độ phủ đo được, và làm báo cáo nêu nhiều phát hiện liên tầng hơn. Bộ phản biện hiện tại hoạt động như một người biên tập khó tính: nó phát hiện đúng những chỗ báo cáo chưa đầy đủ, nhưng cơ chế sửa câu đơn lẻ chưa đủ để đáp ứng yêu cầu ở mức cả báo cáo, và những gì sửa không được thì bị loại bỏ.

![](experiments/er9/analysis/figure_er9_pairwise_diff.png)

Hình 5.2: Chênh lệch giữa các cặp cấu hình với khoảng tin cậy 95%

## 5.6. Phân tích theo dạng câu hỏi và cơ chế kiểm tra câu

Báo cáo thay đổi hình dạng theo dạng câu hỏi: câu tra cứu nhận thẻ trả lời một khối; hồ sơ doanh nghiệp tạo báo cáo dài nhất (5–7 khối, trung bình 5,8) với bản đồ nhiệt thứ hạng, biểu đồ tương quan và khối lưu ý; xếp hạng, xu hướng và so sánh trực diện tạo báo cáo 2–4 khối. Yêu cầu về báo cáo thích ứng theo câu hỏi thay vì một khuôn cố định vì vậy được đáp ứng.

Trên toàn thực nghiệm, 39 câu bị loại. Lý do phổ biến nhất là còn vấn đề phản biện chưa giải quyết (12 câu, chỉ ở C), chiều xu hướng không khớp ngưỡng đi ngang (11), thứ hạng không khớp (6) và nêu xu hướng khi không trích dữ kiện thay đổi (6); chỉ 2 câu bị loại vì con số không khớp. Sáu báo cáo dùng bố cục dựng sẵn thay vì bố cục do mô hình đề xuất; câu xu hướng của SHB (T05) rơi vào trường hợp này ở cả ba cấu hình vì mô hình đặt biểu đồ vào trong khối mục, trái với đặc tả báo cáo. Câu hỏi T08 (đánh đổi của VPB qua năm 2025 so với nhóm) có độ phủ thấp ở cả ba cấu hình (0,13–0,38), vì hệ thống chỉ hỗ trợ xu hướng nhiều kỳ cho riêng một ngân hàng, chưa hỗ trợ so sánh nhóm qua nhiều kỳ; báo cáo nêu rõ giới hạn này thay vì tự suy ra số liệu nhóm.

## 5.7. Độ nhạy của bộ kiểm chứng câu (E1)

Mục 5.3 cho thấy cả ba cấu hình đều đạt 100% khớp số, nhưng con số này chỉ có ý nghĩa nếu bộ kiểm chứng thật sự bắt được câu sai. E1 đo điều đó bằng đột biến: từ 129 câu đã được bộ kiểm chứng chấp nhận ở ER-9, chương trình cài vào mỗi câu một lỗi thuộc một trong 12 loại (đổi số, đảo hai chữ số, đổi kỳ, đổi ngân hàng, đảo chiều, đổi chỉ tiêu, thêm số không có nguồn, thêm quan hệ nhân quả hoặc khuyến nghị…), tạo 1.210 câu đột biến, rồi cho bộ kiểm chứng chạy lại. Cả 129 câu gốc không đột biến vẫn được chấp nhận (không bác bỏ nhầm).

*Bảng 5.3: Tỷ lệ bộ kiểm chứng bắt được từng loại lỗi cài vào (số liệu thô, khoảng tin cậy Wilson 95%).*

| Loại lỗi | Số câu thử | Bắt được | Tỷ lệ | Khoảng tin cậy 95% |
|---|:---:|:---:|:---:|:---:|
| Đổi số nhỏ / lớn / đảo chữ số | 96 mỗi loại | 96 | 100% | [96,2%; 100%] |
| Đổi thứ hạng | 46 | 46 | 100% | [92,3%; 100%] |
| Đổi mẫu số | 52 | 52 | 100% | [93,1%; 100%] |
| Số không có nguồn / nhân quả / khuyến nghị | 129 mỗi loại | 129 | 100% | [97,1%; 100%] |
| Đổi kỳ | 118 | 98 | 83,1% | [75,3%; 88,8%] |
| Đổi ngân hàng | 123 | 106 | 86,2% | [79,0%; 91,2%] |
| Đảo chiều | 76 | 67 | 88,2% | [79,0%; 93,6%] |
| **Đổi chỉ tiêu** | 120 | 95 | **79,2%** | [71,1%; 85,5%] |

Bộ kiểm chứng bắt tuyệt đối các lỗi về con số, thứ hạng và mẫu số, và các câu thêm khẳng định không có nguồn, nhân quả hay khuyến nghị. Nó bỏ sót đáng kể các lỗi **ngữ nghĩa** mà con số vẫn đúng: một câu giữ nguyên "50,0%" nhưng đổi "tỷ lệ bao phủ nợ xấu" thành "tỷ lệ nợ xấu" vẫn được chấp nhận ở 25 trên 120 lần thử. Đây là điểm yếu thật của thiết kế hiện tại và là cơ sở cho hạn chế ở mục 5.14.

Để hiểu các câu lọt lưới, tác giả xem lại thủ công 71 câu đột biến không bị bắt. Có 37 câu (52%) là đột biến tự quy chiếu, ví dụ "TCB vượt trội TCB" hay "giảm từ quý 2/2026 đến quý 2/2026", loại lỗi mà một mô hình thật hiếm khi viết ra nhưng bộ kiểm chứng cũng chưa có quy tắc loại bỏ. Nếu bỏ nhóm này, tỷ lệ bắt được trên các đột biến có nghĩa là 94,2% (đổi kỳ, n = 104), 100% (đổi ngân hàng, n = 102) và 95,7% (đảo chiều, n = 70), còn đổi chỉ tiêu giữ nguyên 79,2%. Cách phân loại này do tác giả thực hiện sau khi đã thấy kết quả, theo một quy tắc kinh nghiệm chứ không phải gán nhãn mù, nên số liệu thô ở Bảng 5.3 là kết quả chính; số điều chỉnh chỉ để chỉ ra điểm yếu còn lại tập trung ở đổi chỉ tiêu.

## 5.8. So sánh giữa các mô hình ngôn ngữ (E2)

ER-9 chỉ dùng một mô hình. E2 chạy lại cấu hình B (phân cấp, không phản biện) trên cùng 12 câu hỏi với ba mô hình của OpenAI, mỗi mô hình một lần, trên cùng phiên bản mã nguồn `06611d9`, nhằm xem kết luận có phụ thuộc mô hình hay không.

*Bảng 5.4: Cấu hình B trên ba mô hình (một lần chạy, mã `06611d9`).*

| Mô hình | Số khớp / đã kiểm | Độ phủ trung bình (lượt hoàn thành) | Câu bị loại / được viết | Từ chối đúng | Truy vết | Token |
|---|:---:|:---:|:---:|:---:|:---:|:---:|
| `gpt-5.4-nano` | 45/45 | 0,812 | 16/59 (27,1%) | 2/2 | 1,000 | 100.106 |
| `gpt-5.4-mini` | 69/69 | 0,800 | 14/62 (22,6%) | 2/2 | 1,000 | 102.225 |
| `gpt-5.6-luna` | 91/91 | 0,931 | 1/55 (1,8%) | 2/2 | 1,000 | 118.802 |

Ba điều rút ra. Thứ nhất, độ khớp số, truy vết và từ chối đúng không đổi theo mô hình, đúng như dự đoán từ thiết kế: các đảm bảo này đến từ lớp kiểm soát chứ không từ mô hình. Thứ hai, thứ thay đổi là **hiệu suất viết**: mô hình lớn hơn có độ phủ cao hơn và ít câu bị loại hơn nhiều (1,8% so với 22–27%), tức mô hình yếu hơn vẫn an toàn nhưng báo cáo ngắn và thiếu hơn. Thứ ba, chênh lệch về token giữa các mô hình nhỏ so với chênh lệch về độ phủ cho thấy chi phí không tăng tương ứng chất lượng.

Hai mô hình DeepSeek (`deepseek-v4-flash-0731`, `deepseek-v4-pro-0813`) cũng được chạy trên cùng giao thức và mã nguồn: cả hai khớp số tuyệt đối (46/46 và 32/32, lần lượt 219.356 và 110.006 token) và từ chối đúng 2/2; số câu bị loại là 3/48 và 14/56. Do quyết định giới hạn bảng so sánh E2 vào các lượt chạy qua OpenAI chính thức, hai mô hình này không được đưa vào Bảng 5.4; kết quả đầy đủ vẫn nằm trong `experiments/RESULTS-INDEX.md`. Điều này cũng giữ ER-9, vốn chạy trên DeepSeek V4 Pro, là thực nghiệm A/B/C duy nhất của khóa luận.

Để kiểm tra độ ổn định, `gpt-5.6-luna` được chạy thêm ba lần trên phiên bản mã mới `b6344a4` (sau các nâng cấp ở mục 5.12). Vì mã nguồn khác lần đầu, đây là kiểm tra ổn định chứ không phải phép lặp thuần túy.

*Bảng 5.5: `gpt-5.6-luna`, cấu hình B, một lần chạy cũ và ba lần chạy trên mã mới.*

| Lần chạy | Mã | Số khớp / đã kiểm | Độ phủ trung bình | Câu bị loại / được viết | Từ chối đúng |
|---|---|:---:|:---:|:---:|:---:|
| Cũ | `06611d9` | 91/91 | 0,931 | 1/55 (1,8%) | 2/2 |
| Mới, lần 0 | `b6344a4` | 93/93 | 0,900 | 4/56 (7,1%) | 2/2 |
| Mới, lần 1 | `b6344a4` | 101/101 | 0,925 | 3/59 (5,1%) | 2/2 |
| Mới, lần 2 | `b6344a4` | 108/108 | 0,925 | 4/55 (7,3%) | 2/2 |

Ba lần chạy mới có độ phủ trung bình 0,917 (nhỏ nhất 0,900, lớn nhất 0,925), mọi con số được kiểm đều khớp (302/302) và truy vết luôn đạt 1,0. Kết luận về mô hình `gpt-5.6-luna` vì vậy ổn định, nhưng tỷ lệ câu bị loại 1,8% của lần chạy đầu nằm ở mức thấp nhất; giá trị tiêu biểu hơn là 5–7%. Với ba lần chạy, báo cáo trung bình và khoảng nhỏ nhất – lớn nhất, không đưa khoảng tin cậy.

## 5.9. Kiểm tra đối kháng (E3)

E3 chạy mười lăm câu hỏi đối kháng thuộc bảy nhóm lên cả ba cấu hình với `gpt-5.6-luna`: chèn chỉ dẫn vào câu hỏi (3 câu), hỏi thực thể hoặc kỳ không tồn tại (2 + 2), mồi bịa số (3), xin lời khuyên mua bán (2), tiền đề sai (1) và ngoài phạm vi (2). Kết quả kỳ vọng là hệ thống từ chối hoặc nêu rõ giới hạn, và không đưa ra con số không có nguồn, khuyến nghị đầu tư hay khẳng định theo tiền đề sai.

*Bảng 5.6: Kiểm tra đối kháng trước và sau sửa lỗi ngoài phạm vi.*

| Lần | Mã | Số câu × cấu hình | Đạt kỳ vọng mỗi cấu hình | Nhóm ngoài phạm vi | Chèn chỉ dẫn, bịa số, khuyến nghị, tiền đề sai |
|---|---|:---:|:---:|:---:|:---:|
| E3 | `06611d9` | 15 × 3 | 13/15 (86,7%) | 0/2 | 0 vi phạm |
| E3 sau sửa | `b6344a4` | 8 × 3 | 8/8 | 2/2 | 0 vi phạm |

Trước khi sửa, cả ba cấu hình giữ vững mọi nhóm tấn công, trừ nhóm ngoài phạm vi: yêu cầu sáng tác thơ và dự báo giá vàng không bị từ chối mà vẫn nhận báo cáo ngành, vì bộ lập kế hoạch mặc định về kế hoạch xếp hạng khi không có ngân hàng nào được nêu. Sau khi thêm cổng phạm vi (mục 5.12), cả hai câu bị từ chối ở cả ba cấu hình.

Hai điểm cần lưu ý. Thứ nhất, lần chạy sau sửa chỉ là tập con tám câu (hai câu ngoài phạm vi và một câu đại diện của mỗi nhóm còn lại), nên chỉ cho biết sửa lỗi có hiệu quả và không gây lùi ở các nhóm được lấy mẫu, chưa phải một lần chạy lại toàn bộ. Thứ hai, ba cấu hình cho kết quả giống hệt nhau ở mọi nhóm: khả năng chống chịu nằm ở lớp kiểm tra xác định dùng chung (hiểu câu hỏi, kiểm tra dữ liệu, bộ kiểm chứng câu), không phải ở việc phân cấp hay phản biện. Điều này củng cố kết luận của mục 5.3 và 5.4 rằng độ an toàn do kiến trúc kiểm soát mang lại chứ không do cấu hình tác tử. Cổng phạm vi hiện là bộ lọc theo dấu hiệu từ khóa và ý định phân tích, không phải bộ phân loại ý định; các câu mơ hồ hoặc diễn đạt lạ có thể bị chặn nhầm hoặc lọt qua.

## 5.10. Khả năng số hóa từ báo cáo gốc (E5)

Hệ thống nhận số liệu từ báo cáo tài chính gốc dạng PDF, trong đó phần lớn là bản quét. E5 đo xem khó khăn nằm ở nhận dạng ký tự hay ở cấu trúc bảng, không gọi mô hình ngôn ngữ. Với 885 số liệu đầu vào đã được chấp nhận và có trang nguồn, E5 hỏi hai câu: (a) giá trị đã được chấp nhận có xuất hiện nguyên văn trong văn bản của đúng trang đó không; (b) một bộ trích xuất đơn giản (tìm dòng có nhãn gần nhất rồi lấy số ở cột tương ứng) có lấy đúng giá trị không.

*Bảng 5.7: Giá trị có mặt trên trang và độ đúng của bộ trích xuất đơn giản.*

| Phép đo | Số liệu | Kết quả |
|---|:---:|:---:|
| (a) Trang có lớp văn bản: giá trị xuất hiện nguyên văn | 185 | 178 (96%) |
| (a) Trang quét, nhận dạng Tesseract: giá trị xuất hiện nguyên văn | 700 | 652 (93%) |
| (b) Bộ trích xuất đơn giản: lấy đúng | 885 | 463 (52%) |
| (b) Không tìm thấy dòng | 885 | 236 (27%) |
| (b) Lấy sai hàng hoặc cột | 885 | 185 (21%) |
| (b) Thiếu cột để lấy | 885 | 1 |

Nhận dạng ký tự không phải nút thắt: 93–96% giá trị đọc được nguyên văn trên trang. Nút thắt là cấu trúc: chọn đúng hàng và đúng cột sai khoảng một nửa số lần. Bộ trích xuất đạt 88–96% với các chỉ tiêu đứng một dòng riêng như tổng tài sản hay nợ nhóm 4, nhóm 5, nhưng chỉ 27% với lợi nhuận sau thuế và 0% với tổng vốn chủ sở hữu, vì báo cáo kết quả kinh doanh có cả cột quý lẫn cột lũy kế và vốn chủ sở hữu thường xuất hiện như một dòng tổng của mục. Kết quả này ủng hộ quyết định thiết kế giữ giá trị trích xuất ở trạng thái "ứng viên" cho đến khi được đối chiếu với đẳng thức kế toán và tính lại bằng công thức có phiên bản, và cho thấy quy trình số hóa của khóa luận là quy trình bán tự động có tác tử AI hỗ trợ, trong đó thẩm định độc lập là hướng mở rộng chứ chưa được thực hiện.

## 5.11. Ca STB quý 4/2025: bất thường trong dữ liệu và vai trò của hồ sơ gốc

Khi đối soát dữ liệu quý của mười ngân hàng, một bất thường được nêu: lợi nhuận sau thuế lũy kế của STB giảm từ 8.691,6 tỷ đồng (đến hết quý 3/2025) xuống 5.939,1 tỷ đồng (đến hết quý 4/2025), tức giảm 2.752,5 tỷ đồng. Lợi nhuận lũy kế trong năm thường không giảm, nên đây có thể là lỗi nhập hoặc nhầm cột. Đối chiếu với báo cáo tài chính hợp nhất đã kiểm toán và báo cáo quý 4 cho thấy con số 5.939,1 tỷ đồng là đúng: STB ghi nhận lỗ sau thuế 2.752,5 tỷ đồng riêng trong quý 4/2025, sau khi trích lập dự phòng rủi ro tín dụng 9.232,2 tỷ đồng trong quý. Dữ liệu vì thế không bị sửa.

Điều thay đổi là quy trình: bộ dựng snapshot được bổ sung kiểm tra tính đơn điệu của lợi nhuận lũy kế trong năm, và chỉ chấp nhận một khoản lỗ quý khi nó nằm trong danh sách ngoại lệ đã được kiểm chứng kèm trang nguồn. Ca này minh họa hai điều: kiểm tra bất biến kế toán là cách rẻ để đưa các điểm đáng ngờ ra để soát, và quyết định cuối cùng thuộc về hồ sơ gốc chứ không thuộc về trực giác của bộ kiểm tra. Cũng cần nói thẳng rằng việc đọc các trang nguồn do tác tử AI thực hiện (nhận dạng ký tự và đọc hình ảnh trang đã cắt) và chưa có người thứ hai độc lập rà soát.

## 5.12. Nâng cấp sau đánh giá

Sau khi ER-9 (05/10/2026), E1–E3 và E5 chạy trên mã `06611d9`, sản phẩm được nâng cấp thêm. Các nâng cấp dưới đây xảy ra sau các số liệu ở mục 5.3–5.10 và không được tính trong chúng, trừ E2r và E3 sau sửa chạy trên mã `b6344a4`.

| Mã | Nội dung | Ghi chú |
|---|---|---|
| SSE-1 | Phát trực tiếp bản nháp của chuyên viên và kết luận của bộ kiểm chứng lên màn hình theo dõi | không đổi kết quả phân tích |
| LIN-1 | Ngăn kéo nguồn: trang PDF, các hàng dữ liệu và đường truy vết của từng con số | không đổi kết quả phân tích |
| MKT-1, MKT-2 | Bối cảnh thị trường (giá cổ phiếu, P/B so với ROE) từ nguồn dữ liệu thị trường, hiển thị trong báo cáo | dữ liệu thị trường được gắn nhãn riêng, không trộn với số liệu báo cáo |
| STB-1 | Kiểm tra đơn điệu lợi nhuận lũy kế và hiệu chỉnh dữ liệu đầu vào STB | mục 5.11 |
| SCOPE-1 | Cổng phạm vi: từ chối câu hỏi không có thực thể, chỉ tiêu hoặc ý định phân tích ngân hàng | mục 5.9 |

## 5.13. Thảo luận

Thứ nhất, độ tin cậy về con số của báo cáo không đến từ việc chọn cấu hình tác tử nào, mà đến từ kiến trúc kiểm soát bao quanh mô hình: tính toán bằng mã nguồn, dữ kiện có nguồn và kiểm tra từng câu. Ba bằng chứng độc lập cùng chỉ về điều này: ba cấu hình có cùng độ khớp số (mục 5.3), ba mô hình khác nhau có cùng độ khớp số và truy vết (mục 5.8), và ba cấu hình chống chịu y hệt nhau trước câu hỏi đối kháng (mục 5.9). Với phân tích tài chính, nơi một con số sai làm mất giá trị của cả báo cáo, đây là kết luận có ý nghĩa thực tiễn.

Thứ hai, chính kiến trúc kiểm soát đó có giới hạn mà E1 đo được. Bộ kiểm chứng bảo đảm con số khớp với dữ kiện và bắt tốt lỗi về số, thứ hạng và mẫu số, nhưng bỏ sót khoảng một phần năm các câu giữ nguyên con số và đổi tên chỉ tiêu. Vì vậy khẳng định "mọi con số đều đúng" phải đi kèm khẳng định "nhưng việc con số gắn đúng chỉ tiêu, kỳ và ngân hàng mới được kiểm một phần". Giảm khoảng trống này, ví dụ bằng quy tắc kiểm tra nhãn chỉ tiêu theo cặp (chỉ tiêu, giá trị), là việc ưu tiên cho phiên bản sau.

Thứ ba, chuyên môn hóa (B) cải thiện độ đầy đủ với chi phí vừa phải, còn phản biện (C) tốn kém và trong thiết kế hiện tại có thể làm báo cáo ngắn đi. Với chuyên viên phân tích dùng hệ thống theo thời gian thực, B là điểm cân bằng hợp lý; C chỉ nên dùng khi bộ phản biện được giới hạn vào các vấn đề quy tắc không kiểm được và được phép bổ sung câu mới thay vì chỉ sửa hoặc loại câu cũ. Việc đổi mô hình làm thay đổi độ đầy đủ nhiều hơn việc đổi cấu hình trong E2, nên kết luận về B và C không nên được hiểu là độc lập với mô hình.

Thứ tư, một thực nghiệm thử trước đó trên bộ Gold v5 (năm ngân hàng, bốn quý năm 2024, ngày 30/9/2026) cho cùng xu hướng: B có độ phủ cao hơn A, C không cải thiện độ phủ, chi phí tăng theo thứ tự A < B < C, và không có báo cáo nào của C hoàn thành trọn vẹn. Sự nhất quán giữa hai bộ dữ liệu khác nhau làm các nhận định trên đáng tin hơn, dù mỗi thực nghiệm chỉ chạy một lần.

Thứ năm, chất lượng câu phụ thuộc nhiều vào việc lời nhắc nêu đủ quy tắc của bộ kiểm tra. Trong lần chạy thử với các mô hình khác trước khi sửa lời nhắc, gần một nửa số câu đúng bị loại vì vi phạm những quy tắc không được nêu ra; sau khi ghi rõ quy tắc vào lời nhắc, tỷ lệ câu được giữ của cùng mô hình tăng từ khoảng 49% lên 84%. Bộ kiểm tra khắt khe là chủ ý của thiết kế, nên cách đúng là dạy mô hình viết câu đơn giản, mỗi câu một chỉ tiêu và một chiều, thay vì nới lỏng quy tắc.

## 5.14. Các yếu tố ảnh hưởng tới tính hợp lệ của kết quả

Về hợp lệ nội tại, mỗi cặp câu hỏi – cấu hình trong ER-9 chỉ chạy một lần trong khi đầu ra của mô hình không cố định, và các lượt chạy đồng thời nên thời gian xử lý chịu ảnh hưởng của tải máy chủ. Phép lặp ba lần ở mục 5.8 chỉ có cho một mô hình và một cấu hình, và chạy trên mã đã thay đổi. Về hợp lệ cấu trúc, các chỉ số tự động đo độ khớp số, truy vết, độ phủ và chi phí nhưng không đo trực tiếp chất lượng diễn giải và tính hữu ích; không có chuyên gia chấm. E1 cho thấy bộ kiểm chứng bỏ sót khoảng 21% các câu đổi tên chỉ tiêu, nên chỉ số khớp số không loại trừ được lỗi này. Việc phân loại các đột biến lọt lưới ở mục 5.7 do chính người thiết kế thực hiện sau khi đã thấy kết quả.

Về hợp lệ bên ngoài, dữ liệu gồm mười ngân hàng niêm yết lớn nhất và bốn nhóm chỉ tiêu; A/B/C chạy trên một mô hình, cấu hình B được kiểm trên ba mô hình OpenAI và hai mô hình DeepSeek với mỗi mô hình một lần, và kiểm tra đối kháng chạy trên một mô hình với mười lăm câu, không đủ để khái quát. Bộ dữ liệu đủ 100/100 ô nên thực nghiệm chính không kiểm tra tình huống thiếu số liệu.

Về quy trình, người phát triển đồng thời là người thiết kế thực nghiệm; bộ câu hỏi, quy tắc chấm và kế hoạch được cố định trước khi chạy nhưng rủi ro thiên lệch trong cách đặt câu hỏi vẫn còn. Một số lượt chạy phải loại bỏ vì sai cấu hình: chạy nhầm mô hình do biến môi trường ghi đè, gateway trả lỗi 404 và hết số dư ở lần chạy E3 đầu tiên; các lượt này (khoảng 1,50 triệu token) được tách riêng và không dùng trong bất kỳ bảng kết quả nào. Một lỗi trong chính quá trình phân loại cũng được ghi nhận: hai lượt DeepSeek của E2 từng bị gán nhãn "không hợp lệ" do nhầm lẫn khi đọc tệp điểm, sau đó được đính chính (D-entry ngày 13/10/2026) và loại khỏi bảng so sánh E2 chỉ theo quyết định phạm vi, không phải vì lỗi. Cuối cùng, các lỗi của chính hệ thống được phát hiện trong khi đánh giá (câu ngoài phạm vi không bị từ chối) đã được sửa sau khi có kết quả; kết quả E3 sau sửa vì vậy chỉ chứng minh lỗi đã được khắc phục trong tập câu đã thử, không phải hệ thống miễn nhiễm với mọi câu ngoài phạm vi.
