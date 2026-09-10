# Thiết kế và đánh giá hệ thống phân tích ngân hàng niêm yết Việt Nam dựa trên dữ liệu có truy nguyên bằng kiến trúc một tác tử và đa tác tử phân cấp

## Chương 1 Giới thiệu

### Bối cảnh và nhu cầu phân tích

Phân tích ngân hàng niêm yết đòi hỏi người sử dụng đồng thời xem xét chất lượng tín dụng, khả năng hấp thụ tổn thất và hiệu quả sinh lời. Một chỉ tiêu riêng lẻ có thể phản ánh một phần tình trạng của ngân hàng nhưng chưa đủ để hình thành nhận định tổng hợp. Chẳng hạn, tỷ lệ nợ xấu cần được đặt cạnh tỷ lệ bao phủ nợ xấu, trong khi khả năng sinh lời cần được theo dõi qua nhiều kỳ và đối chiếu với các ngân hàng trong cùng phạm vi nghiên cứu. Giá trị của một báo cáo phân tích vì vậy không nằm ở việc tập hợp nhiều con số, mà ở khả năng giải thích quan hệ giữa chúng và chỉ ra những giới hạn của kết luận.

Khó khăn của quá trình này xuất hiện ngay từ khâu chuẩn bị dữ liệu. Báo cáo tài chính, thuyết minh và tài liệu công bố của các ngân hàng không phải lúc nào cũng trình bày chỉ tiêu theo cùng một cách. Hai tỷ lệ có cùng tên có thể sử dụng lợi nhuận riêng quý hoặc lợi nhuận lũy kế, phạm vi riêng lẻ hoặc hợp nhất, số dư cuối kỳ hoặc số dư bình quân. Nếu bỏ qua những khác biệt đó, một bảng so sánh có hình thức đầy đủ vẫn có thể dẫn đến cách diễn giải sai. Do đó, việc chuẩn hóa định nghĩa và lưu lại nguồn gốc số liệu là điều kiện cần trước khi tự động hóa phần phân tích.

Mô hình ngôn ngữ có thể hỗ trợ diễn giải dữ liệu và tổng hợp báo cáo, nhưng khả năng tạo văn bản trôi chảy không đồng nghĩa với khả năng bảo đảm tính đúng đắn của mọi phát biểu. Khi dữ liệu thiếu hoặc bằng chứng không đủ rõ, mô hình có thể tạo ra nhận định vượt quá phạm vi được cung cấp. Một ứng dụng phân tích tài chính cần kiểm soát được hiện tượng này ở cả đầu vào và đầu ra. Trong khóa luận, yêu cầu đó được cụ thể hóa bằng việc tách tính toán chỉ tiêu khỏi diễn giải bằng ngôn ngữ, đồng thời buộc các nhận định quan trọng gắn với dữ liệu và bằng chứng có thể kiểm tra.

### Vấn đề nghiên cứu

Việc phân chia công việc cho nhiều tác tử tạo ra khả năng chuyên môn hóa quá trình phân tích. Một tác tử có thể tập trung vào từng ngân hàng, trong khi tác tử khác kiểm tra bằng chứng, xem xét rủi ro hoặc tổng hợp kết quả. Tuy nhiên, sự phân công này cũng làm phát sinh chi phí trao đổi ngữ cảnh, xử lý đầu ra trung gian và phối hợp giữa các thành phần. Nếu bài toán đủ đơn giản để một tác tử xử lý tốt, kiến trúc phức tạp hơn có thể chỉ làm tăng thời gian và chi phí mà không cải thiện đáng kể chất lượng báo cáo.

Vấn đề cần giải quyết vì vậy không phải là mặc định chứng minh đa tác tử vượt trội. Câu hỏi phù hợp hơn là xác định điều kiện mà lợi ích của việc phân công vượt được chi phí phối hợp. Để trả lời, các kiến trúc phải được đặt trên cùng nền dữ liệu, cùng phạm vi yêu cầu và cùng tiêu chí đánh giá. Nếu một nhánh được cung cấp dữ liệu tốt hơn hoặc công cụ thuận lợi hơn mà không công bố sự khác biệt, kết quả sẽ khó phản ánh đúng giá trị của cách tổ chức tác tử.

Khóa luận tiếp cận vấn đề theo hướng xây dựng ứng dụng có đầu ra sử dụng được, sau đó đánh giá các phương án tổ chức xử lý. Báo cáo cuối phải giúp người đọc nhận ra ngân hàng nào cần xem xét thêm, chỉ tiêu nào tạo nên nhận định đó và nguồn nào có thể dùng để kiểm tra. Việc so sánh kiến trúc chỉ có ý nghĩa khi gắn với chất lượng của sản phẩm này, thay vì chỉ dựa vào số lượng tác tử hoặc mức độ phức tạp của quy trình.

### Mục tiêu và câu hỏi nghiên cứu

Mục tiêu tổng quát của khóa luận là thiết kế và đánh giá một nguyên mẫu phân tích ngân hàng niêm yết Việt Nam trên nền dữ liệu đã được chuẩn hóa và có truy nguyên. Hệ thống sử dụng mã chương trình để truy vấn và tính toán chỉ tiêu, còn mô hình ngôn ngữ đảm nhiệm diễn giải, kiểm tra và tổng hợp. Cách phân chia này nhằm giữ tính nhất quán của số liệu khi thay đổi kiến trúc tác tử.

Trên nền tảng đó, nghiên cứu so sánh ba phương án gồm một tác tử, đa tác tử phân cấp không có vòng phản biện và đa tác tử phân cấp có phản biện giới hạn. Chất lượng báo cáo được xem xét đồng thời với chi phí, độ trễ và khả năng hoàn thành yêu cầu. Nghiên cứu không coi một báo cáo được chấm điểm cao là bằng chứng đầy đủ về hiệu quả nếu phần lớn yêu cầu tương tự không tạo được đầu ra hợp lệ.

Câu hỏi nghiên cứu trung tâm là khi tăng số ngân hàng trong một yêu cầu phân tích, có xuất hiện mức độ phức tạp mà đa tác tử tạo ra cải thiện chất lượng đủ rõ so với một tác tử hay không. Các câu hỏi liên quan tập trung vào vai trò của lớp bằng chứng, tác động của phản biện giới hạn và những nguyên nhân khiến một quy trình không hoàn thành. Kết quả của các câu hỏi này được dùng để đề xuất cách sử dụng kiến trúc phù hợp trong phạm vi đã kiểm chứng.

### Phạm vi nghiên cứu

Phạm vi thực nghiệm chính gồm năm ngân hàng ACB, TCB, VPB, MBB và VCB trong bốn quý năm 2024. Bốn chỉ tiêu được sử dụng là tỷ lệ nợ xấu, tỷ lệ bao phủ nợ xấu, tỷ suất sinh lời trên tổng tài sản và tỷ suất sinh lời trên vốn chủ sở hữu. Sự kết hợp giữa năm ngân hàng, bốn kỳ và bốn chỉ tiêu tạo thành 80 vị trí dữ liệu mục tiêu. Mỗi vị trí tương ứng với một ngân hàng, một kỳ và một chỉ tiêu, không phải một dòng báo cáo hoàn chỉnh.

Bộ dữ liệu sử dụng trong đánh giá có 76 giá trị hợp lệ và bốn vị trí được ghi nhận thiếu dữ liệu, đều thuộc ACB trong quý I năm 2024. Việc công khai các vị trí thiếu là một phần của thiết kế nghiên cứu. Hệ thống không điền số không, suy đoán hoặc sử dụng một tỷ lệ khác định nghĩa để tạo cảm giác đủ dữ liệu. Phạm vi đánh giá này cũng không bao gồm toàn bộ ngành ngân hàng Việt Nam.

Các định hướng mở rộng sang nhiều năm, nhiều chỉ tiêu, doanh nghiệp chứng khoán và phân tích vĩ mô được xem là hướng phát triển. Dữ liệu đang ở khu vực ứng viên hoặc đang chờ đối chiếu không được tính vào kết quả của bộ dữ liệu chuẩn. Tương tự, nguyên mẫu giao diện hiện tại phục vụ đọc và kiểm tra báo cáo đã tạo, chưa được xem là ứng dụng triển khai sản xuất có khả năng xử lý mọi truy vấn tự do.

### Đóng góp và cấu trúc khóa luận

Đóng góp của khóa luận nằm ở sự kết hợp giữa nền dữ liệu có truy nguyên, quy trình tạo báo cáo có kiểm soát và thực nghiệm so sánh kiến trúc trong cùng một bài toán ứng dụng. Kết quả không chỉ ghi nhận những trường hợp đa tác tử cải thiện chất lượng mà còn giữ lại các trường hợp chi phí cao, đầu ra không hợp lệ hoặc không hoàn thành. Những bằng chứng này giúp xác định giới hạn của hệ thống và tránh đề xuất kiến trúc dựa trên các trường hợp thành công được chọn lọc.

Nội dung khóa luận được trình bày trong bảy chương. Sau phần giới thiệu, Chương 2 xác lập các khái niệm và định nghĩa vận hành. Chương 3 trình bày phương pháp nghiên cứu, Chương 4 mô tả thiết kế hệ thống và Chương 5 trình bày triển khai cùng báo cáo ứng dụng. Chương 6 phân tích kết quả thực nghiệm, trước khi Chương 7 tổng hợp kết luận và hướng phát triển.

## Chương 2 Cơ sở khái niệm và định nghĩa vận hành

### Chất lượng tín dụng và tỷ lệ nợ xấu

Trong phạm vi khóa luận, tỷ lệ nợ xấu được sử dụng để phản ánh tỷ trọng dư nợ thuộc nhóm 3, nhóm 4 và nhóm 5 trên tổng dư nợ tương ứng. Chỉ tiêu được tính bằng tổng số dư của ba nhóm nợ chia cho mẫu số dư nợ phù hợp, sau đó nhân với 100. Ý nghĩa của tỷ lệ phụ thuộc vào việc tử số và mẫu số cùng phạm vi. Vì vậy, hệ thống cần lưu lại cấu phần tạo nên tỷ lệ, thay vì chỉ giữ một giá trị phần trăm không có thông tin giải thích.

Yêu cầu về phạm vi đặc biệt quan trọng khi dữ liệu được thu nhận từ các bảng có cấu trúc khác nhau. Một mục cho vay hoặc một khoản điều chỉnh không thuộc định nghĩa đã chọn không thể được bổ sung chỉ vì giúp kết quả gần với tỷ lệ công bố. Việc chấp nhận số liệu phải dựa trên sự phù hợp về nội dung, kỳ báo cáo và phạm vi hợp nhất. Những trường hợp chưa xác định được các điều kiện này cần được giữ ở trạng thái chưa đủ căn cứ.

Tỷ lệ nợ xấu cung cấp tín hiệu về chất lượng tín dụng nhưng không tự giải thích nguyên nhân biến động. Tỷ lệ giảm có thể gắn với thay đổi ở số dư nợ xấu, tăng trưởng mẫu số hoặc những yếu tố khác mà bộ dữ liệu chỉ tiêu chưa phản ánh. Do đó, báo cáo có thể mô tả mức tăng, giảm và vị trí tương đối giữa các ngân hàng, nhưng không được khẳng định nguyên nhân nếu chưa có bằng chứng bổ sung phù hợp.

### Tỷ lệ bao phủ nợ xấu

Tỷ lệ bao phủ nợ xấu được sử dụng để xem xét quy mô dự phòng tương ứng với số dư nợ xấu. Trong định nghĩa vận hành của nghiên cứu, chỉ tiêu được tính bằng số dư dự phòng phù hợp chia cho số dư nợ xấu và nhân với 100. Việc lựa chọn khoản dự phòng phải được ghi nhận rõ, bởi tổng dự phòng trên một phạm vi rộng hơn không nhất thiết tương ứng với số dư nợ xấu đang được dùng làm mẫu số.

Giá trị lớn hoặc nhỏ bất thường cần được kiểm tra từ nguồn thay vì tự động điều chỉnh cho hợp lý về mặt hình thức. Chẳng hạn, khi dữ liệu ứng viên có dấu âm do cách trình bày kế toán hoặc lỗi trích xuất, hệ thống không được tự lấy trị tuyệt đối rồi coi kết quả là đã xác nhận. Quyết định chuẩn hóa phải dựa vào nội dung tài liệu và được lưu lại để người khác có thể kiểm tra.

Khi đặt cạnh tỷ lệ nợ xấu, tỷ lệ bao phủ giúp mô tả thêm trạng thái dự phòng của ngân hàng. Tuy nhiên, một tỷ lệ bao phủ cao không phải bằng chứng độc lập rằng ngân hàng không có rủi ro, cũng như một tỷ lệ thấp không đủ để kết luận ngân hàng mất khả năng đáp ứng nghĩa vụ. Trong báo cáo ứng dụng, hai chỉ tiêu này được dùng để xác định nội dung cần ưu tiên xem xét, không thay thế cho đánh giá đầy đủ về chất lượng tài sản và khả năng an toàn vốn.

### Tỷ suất sinh lời trên tài sản và vốn chủ sở hữu

Tỷ suất sinh lời trên tổng tài sản, viết tắt là ROA, được sử dụng để xem xét lợi nhuận tạo ra trên nền tài sản bình quân. Trong phạm vi hợp nhất của nghiên cứu, tử số là lợi nhuận sau thuế của phạm vi hợp nhất tương ứng. Tỷ suất sinh lời trên vốn chủ sở hữu, viết tắt là ROE, cần giữ sự nhất quán giữa lợi nhuận và vốn chủ sở hữu. Khi nguồn tách được lợi ích của cổ đông không kiểm soát, lợi nhuận thuộc cổ đông công ty mẹ phải được đối chiếu với vốn chủ sở hữu thuộc công ty mẹ.

Việc so sánh theo quý sử dụng lợi nhuận của bốn quý gần nhất, thường được gọi là TTM. Khi nguồn công bố số lũy kế, lợi nhuận TTM có thể được xác định từ lợi nhuận cả năm trước trừ phần lũy kế cùng kỳ năm trước rồi cộng phần lũy kế hiện tại. Phép tính được thực hiện bằng mã chương trình và lưu lại các cấu phần đầu vào. Cách làm này tránh việc mô hình ngôn ngữ tự suy đoán cách quy đổi lợi nhuận hoặc trộn lẫn số riêng quý với số lũy kế.

Mặc dù cùng dùng khoảng lợi nhuận bốn quý gần nhất, các tỷ lệ vẫn có thể khác nhau về cách xác định mẫu số bình quân. Trong dữ liệu nghiên cứu, tỷ lệ công bố của TCB có cách sử dụng bình quân năm mốc quý gần nhất, trong khi một số trường hợp tính toán khác sử dụng bình quân hai mốc. Sự khác biệt này phải được giữ trong thông tin định nghĩa và giới hạn so sánh. Việc một giá trị được chấp nhận vào bộ dữ liệu không đồng nghĩa với việc mọi phương pháp bình quân đã trở nên hoàn toàn đồng nhất.

### Kỳ dữ liệu và khả năng truy nguyên

Một bộ dữ liệu có thể chứa đồng thời đại lượng thời điểm và đại lượng thời kỳ. Dư nợ cuối quý là trạng thái tại một thời điểm, còn lợi nhuận thể hiện kết quả phát sinh trong một khoảng thời gian. Nếu chỉ gắn nhãn quý mà không lưu loại kỳ và khoảng thời gian thực tế, hệ thống dễ thực hiện những phép so sánh sai về bản chất. Vì vậy, kỳ báo cáo trong nghiên cứu đi cùng thông tin về ngày kết thúc, tính chất riêng quý hoặc lũy kế và cơ sở quy đổi khi có tính toán TTM.

Khả năng truy nguyên được hiểu là khả năng đi từ một giá trị hoặc nhận định trong báo cáo trở về nguồn và các bước xử lý đã tạo ra nó. Đối với số liệu đọc trực tiếp, hồ sơ cần chỉ ra tài liệu, trang và nội dung liên quan. Đối với tỷ lệ được tính toán, hồ sơ cần thể hiện cả dữ liệu thành phần, công thức và căn cứ chấp nhận. Một ghi chú tính toán đã được đối chiếu có vai trò khác với một đoạn trích nguyên văn, nên hai loại bằng chứng không được trình bày như nhau.

Chính sách dữ liệu thiếu xác định cách hệ thống ứng xử khi chưa có giá trị đáp ứng định nghĩa. Trong khóa luận, giá trị thiếu được giữ là thiếu và đi kèm lý do có thể kiểm tra. Số không chỉ được sử dụng khi thực sự có căn cứ cho giá trị bằng không. Quy tắc này làm giảm nguy cơ tạo ra xu hướng giả, xếp hạng sai hoặc một báo cáo có vẻ đầy đủ nhưng dựa trên dữ liệu không hợp lệ.

### Tác tử và phân công trong hệ thống phân tích

Tác tử được hiểu là một thành phần sử dụng mô hình ngôn ngữ để thực hiện nhiệm vụ được giao trong giới hạn chỉ dẫn, công cụ và cấu trúc đầu ra xác định. Sự khác biệt giữa các kiến trúc không chỉ nằm ở số lần gọi mô hình. Một tác tử có thể thực hiện nhiều bước truy vấn công cụ trước khi hoàn thành báo cáo. Ngược lại, nhiều lần gọi mô hình chưa đủ để tạo thành hệ thống đa tác tử có phân công rõ ràng nếu các bước không có trách nhiệm và giao diện phối hợp riêng.

Trong kiến trúc phân cấp, bộ phận điều phối xác định phạm vi công việc, phân giao cho các thành phần phân tích và tổng hợp kết quả. Phạm vi công cụ được giới hạn theo trách nhiệm, nhằm tránh việc mọi tác tử đều truy cập toàn bộ dữ liệu và tự thực hiện lại cùng một công việc. Cách tổ chức này cho phép kiểm tra đầu ra trung gian nhưng cũng tạo thêm dữ liệu cần truyền và những điểm có thể phát sinh lỗi.

Phản biện giới hạn là bước xem xét kết quả dựa trên những tiêu chí đã quy định và chỉ cho phép số lượt kiểm chứng nhất định. Nghiên cứu sử dụng giới hạn tối đa hai lượt để kiểm soát thời gian và chi phí. Mục đích của bước này là phát hiện nội dung thiếu căn cứ hoặc chưa thể hiện đúng giới hạn dữ liệu. Trong luồng triển khai được đánh giá, kết quả kiểm chứng được ghi riêng, chưa tự động tạo ra một vòng tổng hợp lại báo cáo.

### Cơ sở đánh giá công bằng

Một so sánh kiến trúc có giá trị cần tránh làm suy yếu nhánh một tác tử bằng cách tước bỏ dữ liệu hoặc công cụ cần thiết. Các nhánh trong nghiên cứu cùng sử dụng nền dữ liệu đã chấp nhận và cùng yêu cầu đầu ra. Những khác biệt về cách đóng gói ngữ cảnh, phân giao công việc hoặc tổng hợp phải được xem là đặc điểm của cấu hình triển khai đang đánh giá.

Theo đó, kết quả thực nghiệm phản ánh hiệu quả của ba quy trình cụ thể, không tách riêng hoàn toàn tác động nhân quả của số lượng tác tử. Khi một kiến trúc gặp giới hạn ngữ cảnh do cách đóng gói dữ liệu, kết quả là bằng chứng về hạn chế của cấu hình đó. Muốn khẳng định hạn chế thuộc bản chất của kiến trúc, nghiên cứu cần thêm các đối chứng kiểm soát cách truy xuất, ngân sách và xử lý lỗi.

## Chương 3 Phương pháp nghiên cứu

### Thiết kế nghiên cứu hướng ứng dụng

Nghiên cứu được tổ chức theo hướng xây dựng một nguyên mẫu có thể tạo báo cáo, sau đó đánh giá nguyên mẫu trên các yêu cầu được xác định trước. Trình tự thực hiện bắt đầu từ chuẩn hóa dữ liệu và bằng chứng, tiếp đến là xây dựng đầu ra có cấu trúc, triển khai các kiến trúc và thực nghiệm so sánh. Việc hoàn thiện nền dữ liệu trước giúp hạn chế tình trạng phải thay đổi định nghĩa chỉ tiêu để phù hợp với kết quả do mô hình tạo ra.

Đầu ra được đánh giá ở hai góc độ gắn với nhau. Góc độ nội dung xem xét báo cáo có đúng, có ích, có căn cứ và có nêu giới hạn hay không. Góc độ vận hành xem xét hệ thống có hoàn thành, cần bao lâu và tiêu thụ bao nhiêu tài nguyên. Một kiến trúc chỉ có thể được đề xuất sử dụng khi lợi ích nội dung được đặt trong quan hệ với điều kiện vận hành thực tế.

### Lựa chọn mẫu và hình thành dữ liệu chuẩn

Bộ dữ liệu chuẩn, gọi là Gold Database trong hệ thống, gồm các giá trị đã trải qua quy trình đối chiếu và được chấp nhận theo định nghĩa nghiên cứu. Giai đoạn thử nghiệm ban đầu gồm ba ngân hàng với 48 vị trí mục tiêu, trong đó có 44 giá trị hợp lệ và bốn vị trí thiếu. Sau quá trình mở rộng, phạm vi chính gồm năm ngân hàng với 80 vị trí, trong đó 76 giá trị hợp lệ. Việc mở rộng được thực hiện trên dữ liệu có trạng thái rõ ràng, không bằng cách coi toàn bộ dữ liệu thu nhận ban đầu là dữ liệu chuẩn.

Phiên bản dùng cho đánh giá cuối có mã gold-bank-2025-expanded-v5-evidence và chứa dữ liệu chỉ tiêu của bốn quý năm 2024. Thành phần năm trong tên phiên bản không được dùng để suy ra kỳ tài chính của dữ liệu. Toàn bộ 76 giá trị hợp lệ có liên kết bằng chứng theo trang đã được đối chiếu, với tổng cộng 116 đoạn hoặc ghi chú bằng chứng. Tỷ lệ đủ giá trị số là 95%, còn tỷ lệ có bằng chứng trên các giá trị hợp lệ là 100%. Hai tỷ lệ trả lời hai câu hỏi khác nhau và không được thay thế cho nhau.

Mẫu nghiên cứu không phải là mẫu ngẫu nhiên đại diện cho toàn ngành. Khi tăng số ngân hàng trong một yêu cầu, thành phần ngân hàng cũng thay đổi. Chẳng hạn, cấp một ngân hàng sử dụng ACB, vốn có dữ liệu thiếu trong quý I. Vì vậy, biến cấp độ phản ánh đồng thời quy mô yêu cầu và đặc điểm dữ liệu của các ngân hàng được bổ sung. Đây là giới hạn quan trọng khi diễn giải kết quả như một quan hệ giữa độ lớn dữ liệu và hiệu quả kiến trúc.

### Thu nhận nguồn và đối chiếu số liệu

Nguồn chính được ưu tiên là tài liệu công bố chính thức phù hợp với kỳ và phạm vi cần nghiên cứu. Quá trình thu nhận lưu lại tài liệu gốc, sau đó trích xuất nội dung phục vụ xác định chỉ tiêu. Kết quả nhận dạng hoặc trích xuất từ PDF được xem là dữ liệu cần kiểm tra, bởi lỗi đọc ký tự, dấu âm, đơn vị hoặc cấu trúc bảng có thể làm thay đổi kết quả tính toán.

Dữ liệu ứng viên được tách khỏi vùng dữ liệu đã chấp nhận. Mỗi trường hợp cần được kiểm tra về định danh ngân hàng, kỳ báo cáo, đơn vị, phạm vi hợp nhất và định nghĩa chỉ tiêu. Đối với giá trị tính toán, việc đối chiếu còn bao gồm các số liệu cấu thành và phép biến đổi. Khi nguồn không đủ để giải quyết một khác biệt, hệ thống giữ lại trạng thái thiếu hoặc chưa chấp nhận, thay vì tự chọn giá trị thuận tiện nhất.

Quyết định chấp nhận được lưu cùng hồ sơ nguồn và phiên bản dữ liệu. Các bước hỗ trợ bằng mô hình hoặc kiểm tra tự động có thể giúp phát hiện vấn đề, nhưng không được tự đổi nhãn thành đã được con người đối chiếu. Việc phân biệt các trạng thái này bảo đảm rằng bằng chứng về độ đầy đủ của dữ liệu không bị nhầm với bằng chứng về mức độ hoàn thành của công cụ kiểm tra.

### Ba nhánh thực nghiệm

Nhánh một tác tử xử lý yêu cầu phân tích bằng một vai trò tổng hợp trên dữ liệu và công cụ được cấp. Tác tử nhận phạm vi cần phân tích, tiếp cận các thông tin đã chuẩn hóa và tạo báo cáo theo hợp đồng đầu ra. Khái niệm một tác tử ở đây không có nghĩa là luôn chỉ có một lời gọi API hoặc đưa toàn bộ cơ sở dữ liệu vào một câu lệnh duy nhất. Số lần gọi và lượng ngữ cảnh thực tế phụ thuộc vào quy trình đã được ghi trong kết quả chạy.

Nhánh đa tác tử phân cấp không phản biện phân chia công việc cho các thành phần chuyên trách rồi tổng hợp đầu ra. Việc phân chia giúp từng thành phần tập trung vào phần việc được giao, đồng thời tạo điều kiện kiểm tra các kết quả trung gian. Nhánh này không sử dụng vòng phản biện lặp sau tổng hợp như cấu hình còn lại, nên chi phí chủ yếu đến từ quá trình phân công, xử lý và kết hợp kết quả.

Nhánh đa tác tử phân cấp có phản biện giới hạn bổ sung bước kiểm chứng theo điều kiện kích hoạt, với tối đa hai lượt. Cấu hình được đưa vào để xem xét chất lượng và chi phí của quy trình có kiểm chứng bổ sung. Tuy nhiên, ở phiên bản triển khai hiện tại, kết quả kiểm chứng được ghi vào lịch sử gọi mà chưa được gán trở lại thành báo cáo tổng hợp cuối. Vì vậy, thực nghiệm chưa đánh giá đầy đủ một cơ chế phản biện có sửa đổi và tổng hợp lại nội dung.

### Cấu trúc thực nghiệm và phân biệt các giai đoạn

Đợt thực nghiệm chính được lập thành 75 công việc, kết hợp năm cấp độ số ngân hàng, ba nhánh kiến trúc và năm lần lặp. Các cấp độ tăng từ một đến năm ngân hàng, trong khi giữ phạm vi bốn quý và bốn chỉ tiêu. Mỗi cấu hình có mã công việc và thông tin truy nguyên để đối chiếu giữa đầu vào, đầu ra, chi phí, lỗi và kết quả chấm.

Các thử nghiệm trước đó phục vụ xây dựng hệ thống và kiểm tra ban đầu không được gộp vào mẫu thực nghiệm chính. Đặc biệt, thiết kế thử nghiệm với 13 câu hỏi và 39 lượt chạy thuộc giai đoạn khác với kế hoạch mở rộng 75 công việc. Việc tách các giai đoạn giúp tránh sử dụng điểm số từ một giao thức để giải thích kết quả của một giao thức khác hoặc làm tăng cỡ mẫu một cách không hợp lệ.

### Chấm báo cáo và tổng hợp kết quả

Chất lượng được chấm trên bốn chiều gồm tính đúng đắn, tính hữu ích, chất lượng bằng chứng và khả năng thể hiện giới hạn. Mỗi chiều sử dụng thang điểm từ 0 đến 4, sau đó được chuẩn hóa để tổng hợp trên thang từ 0 đến 1. Cách chia này giúp phân biệt báo cáo đúng số liệu nhưng ít hữu ích với báo cáo có nhận định hấp dẫn nhưng thiếu căn cứ.

Đợt đánh giá cuối ghi nhận 61 báo cáo hoàn thành, tương ứng 244 dòng chấm cho bốn chiều. Con số 244 không phải số báo cáo độc lập và không được dùng như cỡ mẫu thay thế cho 61. Hồ sơ đánh giá hoàn chỉnh chứng minh các báo cáo đã có kết quả chấm theo quy trình, nhưng không tự chứng minh độ đồng thuận giữa nhiều người chấm. Muốn đưa ra kết luận về độ tin cậy liên đánh giá, cần có thông tin độc lập về người chấm và cách đối chiếu điểm.

Điểm chất lượng trung bình được báo cáo trên các công việc hoàn thành. Để phản ánh thêm độ tin cậy vận hành, nghiên cứu sử dụng điểm điều chỉnh theo tỷ lệ hoàn thành, bằng điểm chất lượng trung bình nhân với tỷ lệ số công việc hoàn thành trên số công việc dự kiến. Chỉ số này đặt giá trị bằng không cho đóng góp đầu ra của công việc không hoàn thành trong phép tổng hợp vận hành, không khẳng định rằng một báo cáo bị lỗi có chất lượng nội dung bằng không. Cách nhìn bổ sung này hạn chế việc đề xuất một cấu hình chỉ dựa trên số ít đầu ra thành công.

### Quy tắc xác định điểm chuyển lợi thế

Điểm chuyển lợi thế được xác định theo một quy tắc vận hành đặt trước trong bộ tổng hợp kết quả. Ở một cấp độ, nhánh đa tác tử cần có mức tăng điểm trung bình ít nhất 0,05 so với nhánh một tác tử, có ít nhất ba trong năm cặp lặp cho kết quả tăng điểm và không làm giảm các chiều bằng chứng, giới hạn theo điều kiện đối chiếu. Khả năng hoàn thành của các công việc cũng được xem xét để tránh kết luận dựa trên những cặp kết quả bị thiếu.

Ngưỡng này giúp đưa ra quyết định nhất quán trong phạm vi thực nghiệm, nhưng không phải kiểm định ý nghĩa thống kê hoặc bằng chứng rằng lợi ích kinh tế chắc chắn lớn hơn chi phí. Với số lần lặp còn hạn chế, một cấp độ đáp ứng quy tắc chỉ được diễn giải là điểm chuyển lợi thế quan sát được của cấu hình hiện tại. Khả năng lặp lại trên ngân hàng, thời kỳ và cách tổ chức ngữ cảnh khác cần được kiểm chứng riêng.

## Chương 4 Thiết kế hệ thống

### Phân chia trách nhiệm xử lý

Hệ thống được thiết kế theo nguyên tắc dữ liệu tài chính phải được xác định trước khi mô hình diễn giải. Lớp lưu trữ quản lý tài liệu và giá trị chuẩn hóa, lớp tính toán tạo kết quả định lượng, lớp bằng chứng cung cấp căn cứ kiểm tra, còn lớp tác tử xây dựng nội dung báo cáo. Sự phân chia này cho phép thay đổi cách tổ chức tác tử mà không phải thay đổi công thức tài chính hoặc quyết định chấp nhận dữ liệu.

Hợp đồng dữ liệu đóng vai trò kết nối các lớp. Mỗi thành phần cần trả về đúng trường thông tin, kiểu giá trị và trạng thái được quy định để bước sau có thể kiểm tra. Một nhận định không thể chỉ tồn tại như câu văn không có liên kết với phạm vi dữ liệu. Tương tự, một số liệu hợp lệ nhưng thiếu thông tin kỳ hoặc định nghĩa không đủ điều kiện để được dùng trong mọi phép so sánh.

### Lớp lưu trữ và tính toán

Dữ liệu được tổ chức thành các vùng có trách nhiệm khác nhau. Tài liệu thô được giữ nguyên để bảo toàn nguồn. Vùng ứng viên lưu kết quả thu nhận và những trường hợp đang chờ đối chiếu. Vùng dữ liệu chuẩn chỉ chứa giá trị đã được chấp nhận cùng trạng thái thiếu được xác định rõ. Việc tách các vùng giúp hệ thống sử dụng được dữ liệu mới trong quá trình kiểm tra mà không làm thay đổi ngầm đầu vào của thực nghiệm đã đóng băng.

Các phép tính chỉ tiêu và so sánh định lượng được thực hiện bằng mã chương trình. Đầu vào của phép tính phải đáp ứng yêu cầu về kỳ, đơn vị và phạm vi. Khi một cấu phần bị thiếu, kết quả phụ thuộc vào cấu phần đó không được tạo ra bằng giả định không có trong giao thức. Quy tắc này áp dụng cả với mức thay đổi theo quý, mức thay đổi giữa đầu và cuối năm và các phép xếp hạng có điều kiện.

So sánh với nhóm ngân hàng cùng phạm vi được tính trên các quan sát hợp lệ. Nếu sử dụng trung vị, báo cáo phải hiểu đó là trung vị của nhóm được chọn trong dữ liệu hiện có, không phải trung vị toàn ngành. Khi thành phần nhóm thay đổi giữa các kỳ do dữ liệu thiếu, sự thay đổi cần được thể hiện để người đọc không hiểu nhầm rằng nền so sánh luôn cố định.

### Lớp bằng chứng

Lớp bằng chứng có nhiệm vụ đưa người đọc từ kết quả phân tích trở về tài liệu có thể kiểm tra. Mỗi bằng chứng chứa thông tin nguồn và vị trí liên quan, đồng thời liên kết với chỉ tiêu hoặc nhận định mà nó hỗ trợ. Thiết kế này giúp trả lời một câu hỏi cụ thể: căn cứ nào cho phép báo cáo nêu giá trị hoặc kết luận đang được trình bày.

Không phải mọi bằng chứng đều là câu trích nguyên văn có sẵn trong PDF. Một tỷ lệ được tính từ các cấu phần có thể cần ghi chú giải thích công thức và liên kết tới nhiều số liệu nguồn. Hệ thống vì vậy phân biệt nội dung trích xuất với nội dung suy ra qua tính toán đã đối chiếu. Nếu chỉ gắn nhãn chung là trích dẫn, người dùng có thể hiểu sai rằng nguồn công bố trực tiếp toàn bộ tỷ lệ và cách diễn giải của báo cáo.

Việc mọi giá trị hợp lệ có liên kết bằng chứng cải thiện khả năng kiểm tra, nhưng không loại bỏ hoàn toàn nguy cơ đọc sai nguồn hoặc lựa chọn định nghĩa chưa phù hợp. Bằng chứng phải có nội dung đủ liên quan, không chỉ là một đường dẫn có thể mở. Đây là lý do chất lượng bằng chứng được giữ thành một chiều đánh giá riêng thay vì suy ra hoàn toàn từ số lượng liên kết.

### Phạm vi truy vấn và công cụ của tác tử

Công cụ truy vấn được giới hạn ở dữ liệu được phép sử dụng trong cấu hình chạy. Tác tử không được tự thay đổi trạng thái chấp nhận, ghi đè số liệu gốc hoặc đưa dữ liệu ứng viên vào báo cáo như thể đã qua đối chiếu. Những giới hạn này giữ ranh giới giữa công việc phân tích và công việc quản trị chất lượng dữ liệu.

Trong kiến trúc phân cấp, các thành phần có phạm vi nhiệm vụ và đầu ra trung gian riêng. Thành phần phân tích cần tập trung vào ngân hàng hoặc góc xem xét được giao, còn thành phần tổng hợp xử lý quan hệ giữa các kết quả đó. Việc giới hạn công cụ và ngữ cảnh theo vai trò nhằm tránh tình trạng mỗi thành phần đều lặp lại toàn bộ quy trình. Tuy nhiên, hiệu quả thực tế vẫn phụ thuộc vào lượng dữ liệu được truyền và mức trùng lặp giữa các bước.

Các phiên bản triển khai có thể khác nhau về việc truy vấn theo nhu cầu hoặc cung cấp ngữ cảnh đã chuẩn bị trước. Do đó, mô tả kiến trúc cần đi cùng cấu hình của đợt chạy cụ thể. Kết quả của một phiên bản không tự chứng minh rằng mọi phiên bản đều truy xuất dữ liệu theo cùng cách, cũng không cho phép diễn giải mọi lượt chạy một tác tử thành một lời gọi duy nhất.

### Kiểm tra đầu ra và phản biện

Đầu ra được kiểm tra theo cấu trúc trước khi được coi là báo cáo hoàn thành. Những nội dung cần kiểm tra gồm phạm vi ngân hàng và kỳ, định danh chỉ tiêu, liên kết bằng chứng và các trường bắt buộc. Một báo cáo không đáp ứng cấu trúc không được lặng lẽ đưa vào phần kết quả hợp lệ chỉ vì văn bản có thể đọc được.

Bước phản biện bổ sung kiểm tra nội dung theo các điều kiện đã xác định. Kết quả của mỗi lượt được lưu trong bản ghi thực nghiệm, còn báo cáo phân cấp cuối vẫn lấy từ đầu ra của bộ phận tổng hợp trước bước kiểm chứng. Khi lời gọi kiểm chứng thất bại, trạng thái thất bại được giữ lại. Cấu hình này có thể làm tăng chi phí và giảm khả năng hoàn thành, nhưng chưa có cơ chế đưa nội dung sửa đổi quay lại bước tổng hợp. Đây là một giới hạn triển khai cần được giữ rõ khi diễn giải hiệu quả của phản biện.

### Khả năng tái lập và kiểm soát ngữ cảnh

Mỗi công việc thực nghiệm gắn với phiên bản dữ liệu, cấu hình nhánh, đầu vào, đầu ra và nhật ký vận hành. Việc đóng băng các thành phần này cho phép truy lại cách một báo cáo được tạo ra và xác định sự thay đổi giữa các đợt chạy. Những công việc không hoàn thành cũng cần có bản ghi, vì chúng là một phần của kết quả vận hành chứ không phải dữ liệu có thể bỏ qua.

Trong cấu hình đánh giá cuối, hệ thống có ngưỡng kiểm soát ngữ cảnh 180.000 ký tự. Đây là giới hạn của cách triển khai và đóng gói hiện tại, không phải số token hay khẳng định về cửa sổ ngữ cảnh tối đa của mô hình. Khi dữ liệu và kết quả trung gian tăng, một nhánh có thể vượt ngưỡng trước khi hoàn tất báo cáo. Vì thế, khả năng mở rộng cần được xem xét ở cả cách truy xuất thông tin, mức lặp ngữ cảnh và tổ chức tổng hợp.

## Chương 5 Triển khai và báo cáo ứng dụng

### Các thành phần triển khai

Nguyên mẫu sử dụng Python cho xử lý dữ liệu và điều phối, SQLite cho dữ liệu có cấu trúc và các tệp JSON cho đầu vào, đầu ra cùng nhật ký thực nghiệm. Báo cáo được chuyển thành dạng Markdown hoặc HTML phục vụ đọc và kiểm tra. Việc tách dữ liệu nội dung khỏi cách trình bày giúp giao diện sử dụng lại kết quả đã được xác thực mà không phải tính lại chỉ tiêu.

Phiên bản dữ liệu dùng trong đánh giá bổ sung lớp bằng chứng theo trang trên nền giá trị đã được xác định trước. Dữ liệu ứng viên trong vùng chuẩn bị, dù có số lượng lớn hơn, không được tính vào độ bao phủ của phiên bản này. Mức hoàn thành dữ liệu được báo cáo nhất quán là 76 trên 80 vị trí, tương ứng 95%. Bốn vị trí thiếu vẫn xuất hiện trong thông tin phạm vi để người đọc hiểu giới hạn của báo cáo.

### Đầu vào và quy trình xử lý một yêu cầu

Một yêu cầu điển hình là phân tích ACB, TCB, VPB, MBB và VCB trong bốn quý năm 2024 theo NPL, Coverage, ROA và ROE. Đầu vào này xác định nhóm ngân hàng, thời gian và bộ chỉ tiêu, nhưng chưa tự xác định toàn bộ dữ liệu cần đọc. Hệ thống chuyển yêu cầu thành phạm vi truy vấn, đối chiếu với phiên bản dữ liệu được phép sử dụng và xác định những phần có hoặc không có thông tin hợp lệ.

Từ các quan sát được chấp nhận, mã chương trình tạo chuỗi chỉ tiêu theo thời gian và các so sánh cần thiết. Những phép tính không đủ đầu vào được giữ ở trạng thái không thể kết luận. Lớp bằng chứng cung cấp căn cứ cho giá trị và nhận định, sau đó nhánh tác tử được lựa chọn diễn giải các kết quả theo hợp đồng báo cáo. Kiểm tra đầu ra bảo đảm rằng văn bản cuối không mở rộng ngầm sang ngân hàng, kỳ hoặc chỉ tiêu ngoài yêu cầu.

Đầu ra cần giúp người đọc hiểu ý nghĩa của kết quả thay vì chỉ trình bày một danh sách số liệu. Báo cáo tổ chức các phát hiện theo câu hỏi phân tích, giải thích con số nào tạo nên phát hiện và chỉ rõ điều gì chưa thể kết luận. Cách tổ chức này cho phép người sử dụng bắt đầu từ nhận định tổng hợp, đi xuống so sánh cụ thể và cuối cùng kiểm tra bằng chứng nguồn.

### Minh họa kết quả phân tích

Trong quý IV năm 2024, VPB có tỷ lệ nợ xấu khoảng 4,1956%, cao nhất trong năm ngân hàng của mẫu, đồng thời tỷ lệ bao phủ nợ xấu khoảng 56,1749%, thấp nhất nhóm này. Sự kết hợp giữa hai chỉ tiêu cho thấy VPB là trường hợp cần ưu tiên xem xét thêm về chất lượng tín dụng và dự phòng trong phạm vi so sánh. Nhận định này dựa trên vị trí tương đối của các tỷ lệ, không đủ để khẳng định nguyên nhân hình thành nợ xấu hoặc đưa ra kết luận đầy đủ về mức độ an toàn của ngân hàng.

Ở cùng kỳ, VCB có tỷ lệ nợ xấu khoảng 0,9636% và tỷ lệ bao phủ khoảng 223,3110%. Hai giá trị đặt VCB ở vị trí khác với VPB khi chỉ xét các chỉ tiêu đã chọn. Tuy vậy, báo cáo không chuyển sự khác biệt này thành khuyến nghị đầu tư, bởi bộ dữ liệu chưa bao gồm định giá, đầy đủ chất lượng tài sản, cơ cấu thu nhập và các yếu tố khác cần thiết cho quyết định đó. Phạm vi kết luận là so sánh các trạng thái chỉ tiêu đã quan sát.

Khả năng sinh lời cung cấp một góc nhìn bổ sung, không nhất thiết tạo ra cùng thứ tự như chất lượng tín dụng. Quý IV năm 2024, ROA của TCB là 2,4%, trong khi ROE của MBB khoảng 22,0939%. Với VPB, ROA tăng từ khoảng 1,2179% ở quý I lên 1,8361% ở quý IV, còn ROE tăng từ khoảng 8,0671% lên 11,4117% giữa hai mốc này. Các số liệu cho thấy sự khác biệt giữa ngân hàng và sự thay đổi giữa đầu và cuối kỳ quan sát, nhưng không tự chứng minh quá trình tăng liên tục trong từng quý hoặc nguyên nhân tạo nên mức thay đổi.

Chuỗi thời gian cũng cần được diễn giải đúng hình dạng thay vì chỉ so sánh hai đầu mút. Chẳng hạn, tỷ lệ nợ xấu của MBB lần lượt khoảng 2,4856%, 1,6360%, 2,2342% và 1,6205% qua bốn quý năm 2024. Mức cuối năm thấp hơn đầu năm nhưng có nhịp tăng trở lại trong quý III. Một báo cáo chỉ viết rằng nợ xấu giảm đều sẽ bỏ qua diễn biến này. Giá trị của phần phân tích là mô tả được sự không liên tục và chỉ ra kỳ cần xem xét thêm, không phải ép dữ liệu thành một xu hướng đơn giản.

Trường hợp ACB minh họa cách hệ thống xử lý thông tin chưa đủ điều kiện so sánh. Dù có nguồn đề cập ROE 23,4% trong quý I năm 2024, giá trị đó chưa được dùng để lấp vị trí thiếu khi chưa đáp ứng định nghĩa TTM, phạm vi lợi nhuận và vốn chủ sở hữu của nghiên cứu. Báo cáo cần thể hiện rõ phần thiếu và không tính mức thay đổi dựa trên giá trị chưa chấp nhận. Cách xử lý này làm đầu ra ít đầy đủ hơn về hình thức nhưng giữ được tính nhất quán của phép so sánh.

### Giao diện và luồng đọc báo cáo

Giao diện nguyên mẫu được tổ chức quanh việc đọc kết quả và kiểm tra căn cứ. Người dùng có thể tiếp cận nhận định tổng hợp, xem các so sánh giữa ngân hàng, theo dõi diễn biến chỉ tiêu và mở phần bằng chứng liên quan. Cấu trúc này phù hợp với một báo cáo phân tích có thể giải thích, thay vì một màn hình chỉ hiển thị chỉ số hoặc trình diễn số lượng tác tử đang chạy.

Ở trạng thái triển khai hiện tại, giao diện đọc báo cáo và chuỗi dữ liệu từ cùng một phiên bản đã đóng băng. Các bộ lọc phục vụ thay đổi phần thông tin được hiển thị, không đồng nghĩa với việc hệ thống đang gọi mô hình để tạo một báo cáo mới. Việc nêu rõ giới hạn này giúp phân biệt nguyên mẫu đọc báo cáo đã có với ứng dụng phân tích theo truy vấn tự do. Khóa luận không dùng giao diện hiện tại làm bằng chứng rằng toàn bộ luồng sản phẩm trực tuyến đã hoàn thiện.

### Kiểm thử và ý nghĩa của bằng chứng kỹ thuật

Ở mốc đóng gói kết quả, hệ thống ghi nhận 329 kiểm thử tự động đã vượt qua. Các kiểm thử hỗ trợ xác nhận những hành vi như xử lý dữ liệu, kiểm tra hợp đồng đầu ra, liên kết bằng chứng và các tình huống biên được đưa vào bộ thử. Đây là bằng chứng về phần hành vi đã kiểm tra tại phiên bản đó, không phải bằng chứng rằng mọi câu trong báo cáo do mô hình tạo ra đều chính xác.

Chất lượng nội dung vẫn cần được đánh giá trên báo cáo thực tế. Một chương trình có thể vượt qua kiểm thử cấu trúc nhưng tạo ra nhận định ít hữu ích, bỏ sót giới hạn hoặc dùng bằng chứng chưa đủ sức hỗ trợ kết luận. Do đó, nghiên cứu kết hợp kiểm thử tự động với chấm báo cáo, đồng thời giữ lại trạng thái thất bại của từng công việc. Hai lớp đánh giá bổ sung cho nhau thay vì thay thế nhau.

## Chương 6 Kết quả thực nghiệm và thảo luận

### Cơ sở số liệu và khả năng hoàn thành

Phần kết quả sử dụng đợt đánh giá cuối được đóng băng ngày 9 tháng 9 năm 2026 trên phiên bản dữ liệu chuẩn có bằng chứng. Cấu hình mô hình được ghi trong hồ sơ thực nghiệm là gpt-5.6-luna. Trong 75 công việc dự kiến, 61 công việc hoàn thành và 14 công việc thất bại. Do đó, các điểm chất lượng phải được đọc cùng số đầu ra thực sự có mặt, không chỉ cùng số lượt chạy được lập kế hoạch.

Nhánh một tác tử hoàn thành lần lượt 5, 5, 5, 5 và 4 công việc ở các cấp từ một đến năm ngân hàng, tổng cộng 24 trên 25. Nhánh phân cấp không phản biện hoàn thành 5, 5, 5, 3 và 3 công việc, tổng cộng 21 trên 25. Nhánh có phản biện giới hạn hoàn thành 5, 4, 2, 4 và 1 công việc, tổng cộng 16 trên 25. Chênh lệch này cho thấy độ tin cậy vận hành là một phần đáng kể của đánh đổi giữa các kiến trúc trong cấu hình hiện tại.

### Kết quả ở yêu cầu một và hai ngân hàng

Ở cấp một ngân hàng, điểm chất lượng trung bình của nhánh một tác tử và nhánh có phản biện cùng là 0,6875, còn nhánh không phản biện đạt 0,7000. Cả ba đều hoàn thành đủ năm lượt. Mức tăng 0,0125 của nhánh không phản biện nhỏ hơn ngưỡng 0,05 đã xác định, trong khi chi phí trung bình tăng từ khoảng 0,019124 USD ở nhánh một tác tử lên 0,046326 USD ở nhánh không phản biện và 0,073262 USD ở nhánh có phản biện. Độ trễ tương ứng khoảng 55,3 giây, 115,0 giây và 187,4 giây. Kết quả này chưa tạo căn cứ để ưu tiên đa tác tử cho cấp yêu cầu đơn giản nhất.

Điểm số tương đối thấp ở cấp một ngân hàng không nên được hiểu là một tác tử yếu hơn ở bài toán ít dữ liệu. Cấp này sử dụng ACB, trong đó bốn chỉ tiêu của quý I được ghi nhận thiếu. Phạm vi dữ liệu và nội dung có thể kết luận vì vậy khác với các cấp bổ sung ngân hàng có dữ liệu đầy đủ hơn. Sự khác biệt giữa các cấp không chỉ đến từ lượng thông tin, nên không thể suy ra một đường tăng chất lượng thuần túy theo số ngân hàng.

Ở cấp hai ngân hàng, nhánh một tác tử và nhánh không phản biện cùng đạt 0,9500 và hoàn thành đủ năm lượt. Nhánh có phản biện đạt 0,953125 trên bốn lượt hoàn thành, nhưng điểm điều chỉnh theo tỷ lệ hoàn thành chỉ còn 0,7625. Chi phí trung bình của các lượt hoàn thành lần lượt khoảng 0,021144 USD, 0,053474 USD và 0,083994 USD, với độ trễ khoảng 66,7 giây, 108,2 giây và 169,5 giây. Chênh lệch rất nhỏ về chất lượng nội dung không bù được bất lợi hoàn thành theo chỉ số vận hành đang sử dụng.

### Điểm chuyển lợi thế quan sát được ở ba ngân hàng

Ở cấp ba ngân hàng, nhánh phân cấp không phản biện đạt điểm chất lượng trung bình 0,9875 so với 0,9375 của nhánh một tác tử. Mức tăng là 0,05, có ba trong năm cặp lặp tăng điểm và cả hai nhánh đều hoàn thành đủ năm công việc. Theo quy tắc đã xác định, đây là cấp đầu tiên ghi nhận điểm chuyển lợi thế của nhánh không phản biện trong đợt thực nghiệm.

Cải thiện tập trung ở tính đúng đắn và chất lượng bằng chứng. Điểm chuẩn hóa về tính đúng đắn tăng từ 0,95 lên 1,00, còn điểm bằng chứng tăng từ 0,85 lên 1,00. Trong khi đó, tính hữu ích của cả hai nhánh đều là 0,95 và khả năng thể hiện giới hạn đều là 1,00. Do vậy, kết quả hỗ trợ nhận định rằng nhánh phân cấp tạo báo cáo đúng và có căn cứ tốt hơn theo phép chấm này, nhưng chưa hỗ trợ khẳng định báo cáo hữu ích hơn đối với người sử dụng.

Nhánh có phản biện đạt chất lượng trung bình 0,96875 trên hai công việc hoàn thành ở cùng cấp. Khi xét toàn bộ năm công việc dự kiến, điểm điều chỉnh chỉ là 0,3875. Điều này cho thấy không thể lấy điểm của hai báo cáo thành công để kết luận rằng phản biện cải thiện hiệu quả chung. Trong cấu hình hiện tại, bước bổ sung chưa tạo được lợi thế có độ tin cậy tương ứng với nhánh không phản biện.

### Đánh đổi về chi phí và độ trễ ở ba ngân hàng

Lợi thế chất lượng của nhánh không phản biện đi kèm mức sử dụng tài nguyên cao hơn. Trên các công việc hoàn thành ở cấp ba ngân hàng, chi phí trung bình của nhánh một tác tử là khoảng 0,033053 USD, còn nhánh không phản biện là 0,081015 USD. Độ trễ trung bình tăng từ khoảng 85,2 giây lên 135,8 giây. Những số liệu này cho thấy mức tăng chất lượng không phải lợi ích miễn phí và cần được cân nhắc theo yêu cầu sử dụng.

Nhật ký token cung cấp thêm căn cứ về khác biệt này. Nhánh một tác tử sử dụng trung bình khoảng 91.014 token đầu vào và 12.375 token đầu ra cho mỗi công việc hoàn thành. Nhánh không phản biện sử dụng khoảng 243.400 token đầu vào và 26.946 token đầu ra. Nhánh có phản biện ghi nhận khoảng 292.188 token đầu vào và 34.960 token đầu ra, với chi phí trung bình khoảng 0,100389 USD và độ trễ khoảng 190,8 giây trên hai công việc thành công. Các lượng token là số tổng hợp theo công việc, không mặc định tương ứng với một lời gọi mô hình duy nhất.

Bộ tổng hợp còn ghi nhận trung bình tỷ số theo từng cặp lặp giữa nhánh không phản biện và một tác tử. Tỷ số chi phí theo cách tính này khoảng 2,622757 lần, còn tỷ số độ trễ khoảng 1,698339 lần. Đây là trung bình của các tỷ số ghép cặp, khác với lấy chi phí hoặc độ trễ trung bình của một nhánh chia cho trung bình của nhánh còn lại. Hai phép tổng hợp có thể cho kết quả khác nhau và cần được nêu đúng để tránh hiểu nhầm số liệu không nhất quán.

Chi phí trong báo cáo được ước tính từ dữ liệu sử dụng ghi nhận theo cơ chế tính của thực nghiệm, chưa phải đối soát hóa đơn nhà cung cấp. Hơn nữa, các giá trị trung bình nêu trên chỉ bao gồm công việc hoàn thành, không đại diện cho toàn bộ chi phí của cả những công việc thất bại. Vì chưa đo trực tiếp thời gian người dùng tiết kiệm được hoặc giá trị của việc giảm lỗi phân tích, nghiên cứu chưa đủ căn cứ kết luận mức tăng 0,05 điểm có hiệu quả kinh tế dương.

### Kết quả ở yêu cầu bốn và năm ngân hàng

Ở cấp bốn ngân hàng, nhánh một tác tử đạt chất lượng 0,9750 và hoàn thành đủ năm công việc. Nhánh không phản biện đạt khoảng 0,979167 trên ba công việc hoàn thành, nên điểm điều chỉnh giảm còn 0,5875. Nhánh có phản biện đạt 1,0000 trên bốn công việc hoàn thành, tương ứng điểm điều chỉnh 0,8000. Chi phí trung bình trên công việc thành công lần lượt khoảng 0,032566 USD, 0,081315 USD và 0,112865 USD. Độ trễ tương ứng khoảng 70,4 giây, 167,9 giây và 198,2 giây. Xét cả khả năng hoàn thành, kết quả không cho thấy lợi thế quan sát ở cấp ba được duy trì tại cấp bốn.

Ở cấp năm ngân hàng, nhánh một tác tử đạt 0,90625 trên bốn công việc hoàn thành, tương ứng điểm điều chỉnh 0,7250. Nhánh không phản biện đạt 1,0000 nhưng chỉ hoàn thành ba công việc, đưa điểm điều chỉnh xuống 0,6000. Nhánh có phản biện cũng đạt 1,0000 nhưng chỉ có một công việc thành công, nên điểm điều chỉnh là 0,2000. Điểm tuyệt đối của nhánh cuối phản ánh một báo cáo được chấm, không chứng minh độ ổn định của cấu hình ở yêu cầu lớn nhất.

Chi phí trung bình ở cấp năm ngân hàng lần lượt khoảng 0,032220 USD, 0,074543 USD và 0,084881 USD, với độ trễ khoảng 64,1 giây, 145,8 giây và 134,3 giây. Việc nhánh có phản biện có độ trễ thành công thấp hơn nhánh không phản biện ở cấp này không đủ để kết luận cấu hình đó nhanh hơn nói chung. Tập quan sát chỉ còn một báo cáo thành công và loại khỏi phép tính trung bình những công việc không hoàn tất. Sự thay đổi thành phần mẫu thành công là một cách giải thích cần được giữ lại khi đọc chi phí và thời gian.

### Nguyên nhân thất bại

Trong 14 công việc thất bại, chín trường hợp liên quan đến ngưỡng ngữ cảnh 180.000 ký tự, hai trường hợp liên quan đến cấu trúc đầu ra và ba trường hợp ghi nhận APIConnectionError. Đây là phân loại theo công việc thất bại, không phải phép cộng mọi nhãn lỗi có thể xuất hiện trong cùng một bản ghi. Một công việc có nhiều thông tin lỗi không được tính thành nhiều thất bại độc lập.

Nhóm lỗi ngữ cảnh chiếm phần lớn cho thấy cách đóng gói thông tin là điểm hạn chế đáng chú ý của phiên bản triển khai. Khi nhiều thành phần cùng nhận dữ liệu hoặc tạo đầu ra trung gian dài, lượng thông tin cần đưa vào các bước sau có thể tăng nhanh hơn lượng dữ liệu gốc. Tuy vậy, việc quan sát lỗi này chưa chứng minh rằng đa tác tử về bản chất không thể xử lý nhiều ngân hàng. Những phương án truy xuất theo nhu cầu, giảm trùng lặp và giới hạn đầu ra trung gian cần được kiểm tra trong thực nghiệm đối chứng riêng.

Lỗi cấu trúc và kết nối phản ánh những rủi ro khác với chất lượng lập luận. Hệ thống đã giữ lại trạng thái thất bại thay vì bỏ qua để báo cáo đủ số lượt thành công. Cách xử lý này làm kết quả vận hành kém thuận lợi hơn về hình thức nhưng cung cấp nền tảng trung thực để cải thiện. Các thay đổi như thử lại có kiểm soát cần ghi nhận chi phí phát sinh và số lần thử, nếu không kết quả mới có thể che khuất nguồn lực thực sự cần để hoàn thành yêu cầu.

### Giới hạn của kết quả và ý nghĩa ứng dụng

Kết quả hỗ trợ một kết luận cục bộ: tại cấp ba ngân hàng, nhánh phân cấp không phản biện đạt quy tắc chuyển lợi thế về chất lượng trong cấu hình đã chạy. Kết quả không hỗ trợ quy tắc rộng hơn rằng mọi yêu cầu từ ba ngân hàng trở lên đều nên dùng đa tác tử. Tỷ lệ thất bại tại cấp bốn và năm trực tiếp cho thấy lợi thế không duy trì đơn điệu khi phạm vi tăng.

Khả năng khái quát còn bị giới hạn bởi năm ngân hàng, một năm dữ liệu, bốn chỉ tiêu và năm lần lặp cho mỗi cấu hình. Thành phần ngân hàng thay đổi cùng cấp độ, cách chấm nội dung có yếu tố phán đoán và bộ dữ liệu vẫn còn khác biệt về một số cơ sở tính bình quân. Các điều kiện này không làm mất giá trị của thực nghiệm, nhưng xác định đúng điều mà thực nghiệm đã kiểm tra. Chúng chưa đủ để kết luận về ưu thế dài hạn của kiến trúc trên nhiều năm, nhiều loại tài liệu hoặc toàn ngành.

Trong phạm vi ứng dụng hiện tại, một tác tử là lựa chọn mặc định hợp lý về khả năng hoàn thành và mức sử dụng tài nguyên. Nhánh phân cấp không phản biện là phương án đáng tiếp tục kiểm chứng ở những yêu cầu cần cải thiện độ đúng và bằng chứng, với cấp ba ngân hàng là trường hợp đã có tín hiệu. Một cơ chế tự chọn kiến trúc theo độ phức tạp vẫn là đề xuất nghiên cứu, chưa phải tính năng có hiệu quả được chứng minh chỉ từ kết quả này.

## Chương 7 Kết luận và hướng phát triển

### Kết luận nghiên cứu

Khóa luận đã xây dựng và đánh giá nguyên mẫu phân tích năm ngân hàng niêm yết Việt Nam trong bốn quý năm 2024 theo bốn chỉ tiêu tài chính. Nền dữ liệu gồm 76 giá trị hợp lệ trên 80 vị trí mục tiêu, có bằng chứng theo trang cho các giá trị được chấp nhận và giữ rõ bốn vị trí thiếu. Hệ thống tách tính toán khỏi diễn giải, đồng thời tổ chức báo cáo để người đọc có thể đi từ nhận định đến dữ liệu và nguồn hỗ trợ.

Thực nghiệm chính gồm 75 công việc, trong đó 61 công việc hoàn thành. Nhánh phân cấp không phản biện đạt điểm chuyển lợi thế quan sát được ở cấp ba ngân hàng, với mức tăng chất lượng 0,05 so với nhánh một tác tử và hoàn thành đầy đủ các lượt tại cấp đó. Cải thiện nằm ở tính đúng đắn và chất lượng bằng chứng, đi kèm chi phí và độ trễ cao hơn. Kết quả không chứng minh mức cải thiện tương ứng về tính hữu ích hoặc hiệu quả kinh tế.

Ở các cấp lớn hơn, tỷ lệ thất bại làm suy giảm hiệu quả vận hành của các nhánh phân cấp. Nhánh có phản biện giới hạn chưa cho thấy lợi ích nhất quán đủ để được ưu tiên trong cấu hình hiện tại. Vì vậy, nghiên cứu không xác nhận giả định rằng tăng độ lớn bài toán tất yếu làm đa tác tử tốt hơn. Điều được xác định là một trường hợp có lợi thế cục bộ cùng những giới hạn kỹ thuật cần giải quyết trước khi mở rộng kết luận.

### Đóng góp của hệ thống

Đóng góp ở tầng dữ liệu là một quy trình phân biệt rõ tài liệu gốc, dữ liệu ứng viên, giá trị đã chấp nhận và dữ liệu thiếu. Việc lưu định nghĩa, kỳ và nguồn giúp các phép so sánh có cơ sở kiểm tra, thay vì chỉ dựa trên sự giống nhau của tên chỉ tiêu. Giá trị của nền tảng này độc lập tương đối với kiến trúc tác tử, bởi cả một tác tử và đa tác tử đều cần sử dụng cùng dữ liệu đáng tin cậy.

Ở tầng ứng dụng, hệ thống hình thành đầu ra có cấu trúc và nguyên mẫu đọc báo cáo gắn với bằng chứng. Người dùng không chỉ nhận các tỷ lệ mà còn có thể xem nhận định được hình thành từ đâu và phần nào còn thiếu căn cứ. Đây là cơ sở để phát triển một công cụ hỗ trợ phân tích, dù nguyên mẫu hiện tại chưa thay thế được quy trình thẩm định tài chính đầy đủ hoặc đáp ứng mọi truy vấn phát sinh.

Ở tầng đánh giá, nghiên cứu đặt chất lượng bên cạnh chi phí, thời gian và khả năng hoàn thành. Việc giữ lại thất bại và phân biệt điểm trên báo cáo thành công với điểm điều chỉnh giúp tránh lựa chọn kiến trúc bằng những kết quả thuận lợi riêng lẻ. Cách tiếp cận này tạo cơ sở cụ thể hơn cho quyết định phát triển tiếp so với việc chỉ khẳng định hệ thống có nhiều tác tử hoặc có bước phản biện.

### Khuyến nghị sử dụng trong phạm vi hiện tại

Một tác tử nên được giữ làm phương án mặc định cho phiên bản hiện tại do có tỷ lệ hoàn thành cao và chi phí thấp hơn trong các cấu hình đã kiểm tra. Nhánh phân cấp không phản biện có thể được chọn để kiểm chứng thêm tại các yêu cầu mà chất lượng bằng chứng được ưu tiên và người sử dụng chấp nhận chi phí tăng. Tuy nhiên, không nên lập ngay quy tắc chuyển sang đa tác tử chỉ dựa trên việc yêu cầu có từ ba ngân hàng trở lên.

Đối với báo cáo hướng tới người dùng, ưu tiên tiếp theo là làm rõ quyết định phân tích mà đầu ra có thể hỗ trợ. Một nhận định cần chỉ ra vấn đề đáng chú ý, dữ liệu nào tạo nên vấn đề và thông tin nào cần đọc thêm trước khi kết luận. Nếu đầu ra chỉ đổi cách trình bày cùng một danh sách số liệu, việc tăng số tác tử chưa tạo thêm giá trị ứng dụng đủ rõ để biện minh cho độ phức tạp.

### Hướng phát triển

Hướng phát triển trước hết là kiểm chứng khả năng khắc phục lỗi vận hành trên cùng nền dữ liệu và giao thức. Những thay đổi về truy xuất theo nhu cầu, loại bỏ ngữ cảnh lặp, giới hạn kết quả trung gian, chạy song song và thử lại cần được tách thành các cấu hình có thể đối chiếu. Chất lượng, chi phí của mọi lần thử và tỷ lệ hoàn thành phải tiếp tục được ghi nhận. Cách làm này giúp phân biệt cải thiện do tổ chức thông tin với cải thiện do tăng ngân sách hoặc thay đổi tiêu chí chấm.

Sau khi độ ổn định được cải thiện, bộ dữ liệu có thể mở rộng theo ngân hàng, năm, chỉ tiêu và số tài liệu cần đọc. Mỗi phần mở rộng vẫn cần định nghĩa, đối chiếu và bằng chứng trước khi đi vào dữ liệu chuẩn. Thiết kế thực nghiệm cũng cần tách rõ tác động của số lượng ngân hàng, độ dài chuỗi thời gian, số góc phân tích và mức độ khó của nguồn. Nếu tăng tất cả cùng lúc, nghiên cứu có thể quan sát khác biệt nhưng khó xác định yếu tố nào làm xuất hiện lợi thế.

Cuối cùng, giá trị ứng dụng cần được kiểm tra trực tiếp với người sử dụng mục tiêu. Những đại lượng phù hợp gồm thời gian tìm được thông tin cần thiết, khả năng kiểm tra một nhận định, số lỗi diễn giải và mức hữu ích của báo cáo đối với nhiệm vụ phân tích cụ thể. Kết hợp các đại lượng này với chi phí và độ trễ sẽ giúp xác định khi nào đa tác tử thực sự đáng dùng. Đây là bước cần thiết để chuyển từ bằng chứng về điểm chất lượng báo cáo sang bằng chứng về lợi ích của ứng dụng.
