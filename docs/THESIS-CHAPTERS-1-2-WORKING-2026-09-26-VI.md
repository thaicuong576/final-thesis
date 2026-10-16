# Thiết kế và đánh giá hệ thống Multi-Agent hỗ trợ tổng hợp thông tin và phân tích cơ bản các ngân hàng niêm yết tại Việt Nam

## CHƯƠNG 1. GIỚI THIỆU
### 1.1. Bối cảnh nghiên cứu
Phân tích tài chính là quá trình sử dụng dữ liệu và thông tin liên quan để đánh giá tình hình hoạt động, hiệu quả, vị thế cũng như triển vọng của doanh nghiệp nhằm hỗ trợ các quyết định kinh tế. Theo khung phân tích của Viện CFA, các báo cáo tài chính cần được đặt trong mối tương quan với mô hình kinh doanh, đặc thù ngành, đối thủ cạnh tranh và môi trường kinh tế để hình thành những nhận định phù hợp với mục tiêu của người phân tích (CFA Institute, 2026b).

Cũng theo các tài liệu hướng dẫn của tổ chức này, phạm vi thông tin cần huy động không cố định mà biến thiên theo từng yêu cầu cụ thể (CFA Institute, 2026a, 2026b). Một truy vấn đánh giá biến động tỷ suất sinh lời qua các quý chủ yếu đòi hỏi dữ liệu nội tại của doanh nghiệp; bài toán định vị vị thế tương đối cần mở rộng sang dữ liệu của nhóm so sánh; còn các vấn đề liên quan đến lãi suất hay chính sách tiền tệ lại đòi hỏi bối cảnh kinh tế vĩ mô. Việc sử dụng quá ít thông tin dẫn đến nguy cơ bỏ sót các yếu tố trọng yếu; ngược lại, đưa toàn bộ dữ liệu vào mọi trường hợp chỉ làm quá trình phân tích trở nên cồng kềnh mà không mang lại giá trị gia tăng tương xứng. Vì vậy, một hệ thống hỗ trợ phân tích hiệu quả cần xác định được phạm vi thông tin vừa đủ cho từng câu hỏi thay vì áp dụng một quy trình cứng nhắc cho mọi yêu cầu.

Dữ liệu tài chính còn nhạy với ngữ cảnh. Một giá trị chỉ có nghĩa khi gắn với doanh nghiệp, kỳ báo cáo, chỉ tiêu, đơn vị, phạm vi và phương pháp tính: hai giá trị cùng gọi là ROE có thể không tương đương nếu được tính trên các kỳ khác nhau hoặc với cách xác định vốn chủ sở hữu bình quân khác nhau; số liệu theo quý, lũy kế và cả năm cũng không dùng thay thế cho nhau được (CFA Institute, 2026b). Cùng với đó, kết luận chỉ đáng tin khi người dùng có thể kiểm tra lại giá trị gốc, kỳ, nguồn và cách tính đứng sau nó. Khi dữ liệu không tồn tại, trạng thái thiếu phải được nêu rõ thay vì bị thay bằng một giá trị giả định, vì giá trị lấp chỗ trống có thể lan sang các phép tính và kết luận tiếp theo.

Song song, mô hình ngôn ngữ lớn mở ra khả năng hỗ trợ nhiều nhiệm vụ tài chính, với cách triển khai phụ thuộc vào yêu cầu về dữ liệu, tài nguyên và chất lượng đầu ra của từng trường hợp (Li và cộng sự, 2023). Tuy nhiên, văn bản lưu loát không đồng nghĩa với thông tin chính xác: mô hình có thể tạo ra nội dung không được dữ liệu đầu vào hỗ trợ dù vẫn mạch lạc (Ji và cộng sự, 2023). Trong phân tích tài chính, điều này biểu hiện thành sai số liệu, thông tin không có trong nguồn hoặc kết luận vượt quá bằng chứng. Do đó, ứng dụng mô hình ngôn ngữ vào phân tích tài chính không đơn thuần là bài toán tạo lập văn bản tự động, mà còn là bài toán chọn đúng thông tin, kiểm soát dữ liệu và giữ cho các phát biểu quan trọng có thể kiểm tra lại.

### 1.2. Vấn đề nghiên cứu
Vấn đề thứ nhất là đưa dữ liệu từ trạng thái thô sang trạng thái dùng được cho phân tích. Dữ liệu đến từ báo cáo tài chính, báo cáo thường niên, dữ liệu ngành và các nguồn bên thứ ba (CFA Institute, 2026b), với cấu trúc, đơn vị và kỳ báo cáo khác nhau; nhiều báo cáo của ngân hàng Việt Nam còn là bản quét nên việc trích xuất có thể sai. Thu thập được một con số chưa đủ để coi đó là đầu vào đáng tin: dữ liệu cần được chuẩn hóa, kiểm tra và gắn với nguồn trước khi sử dụng.

Vấn đề thứ hai là xác định phạm vi phân tích phù hợp với từng yêu cầu (CFA Institute, 2026a). Nếu luôn dùng mọi nhóm thông tin, chi phí xử lý tăng và báo cáo chứa nội dung thừa; nếu phạm vi quá hẹp, câu trả lời thiếu thông tin cần thiết. Bài toán vì vậy nằm ở việc xác định đúng loại thông tin cần dùng trước khi phân tích bắt đầu.

Vấn đề thứ ba là độ tin cậy của đầu ra do AI tạo ra (Ji và cộng sự, 2023). Một báo cáo có thể có số liệu đúng nhưng so sánh không phù hợp, hoặc lập luận hợp lý nhưng dựa trên một giá trị sai. Hai nhóm lỗi này khác nhau: sai số liệu, tham chiếu không tồn tại hay dùng dữ liệu ngoài phạm vi có thể kiểm tra trực tiếp bằng quy tắc; còn mức độ được bằng chứng hỗ trợ và tính đầy đủ của câu trả lời cần được xem xét ở mức nội dung.

Để giải quyết đồng thời bài toán phạm vi thông tin và kiểm soát chất lượng đầu ra, các kiến trúc hệ thống dựa trên mô hình ngôn ngữ hiện nay thường hướng tới việc phân rã nhiệm vụ cho nhiều tác tử (agent) chuyên biệt, kết hợp với cơ chế tự phản biện và hiệu chỉnh. Tuy nhiên, trong miền phân tích tài chính, việc phức tạp hóa kiến trúc không mặc nhiên đồng nghĩa với hiệu quả thực tiễn. Sự gia tăng về số bước điều phối và các vòng lặp kiểm duyệt kéo theo chi phí tính toán lớn, độ trễ cao và nguy cơ sai lệch thông tin qua các bước trung gian. Khoảng trống nghiên cứu là thiếu các đánh giá định lượng có kiểm soát nhằm xác định xem đến mức độ phức tạp nào thì kiến trúc đa tác tử và cơ chế phản biện thực sự mang lại giá trị gia tăng về độ chính xác lẫn độ bao phủ thông tin so với một tác tử đơn lẻ. Trong khóa luận này, “tác tử” là cách gọi chung của agent; trong ngữ cảnh nghiệp vụ của hệ thống, các tác tử chuyên trách được gọi là “chuyên viên”.

Từ đó, vấn đề nghiên cứu được xác định như sau: *làm thế nào xây dựng một hệ thống phân tích tài chính có thể xác định các thành phần phân tích cần thiết cho từng yêu cầu, sử dụng dữ liệu và bằng chứng có khả năng truy nguyên, phối hợp các thành phần phù hợp, đồng thời kiểm tra và sửa đổi kết quả trước khi tạo báo cáo cuối cùng?*

### 1.3. Mục tiêu và câu hỏi nghiên cứu
Mục tiêu tổng quát của khóa luận là thiết kế, triển khai và đánh giá một hệ thống hỗ trợ phân tích tài chính có khả năng lựa chọn các thành phần phân tích phù hợp với từng yêu cầu, sử dụng dữ liệu và bằng chứng có khả năng truy nguyên, đồng thời kiểm tra chất lượng đầu ra trước khi cung cấp báo cáo cho người sử dụng. Bốn mục tiêu cụ thể gồm:

1. Xây dựng quy trình tiếp nhận và chuẩn hóa dữ liệu, trong đó mỗi giá trị giữ thông tin về doanh nghiệp, kỳ, chỉ tiêu, đơn vị, nguồn và trạng thái kiểm chứng.
2. Thiết kế kiến trúc gồm các thành phần chuyên trách cho phân tích doanh nghiệp, phân tích ngành và nhóm so sánh, phân tích vĩ mô, với bộ điều phối chỉ huy động thành phần mà câu hỏi và dữ liệu thực sự cần.
3. Xây dựng cơ chế kiểm soát chất lượng hai lớp: những gì kiểm tra được bằng quy tắc (số liệu, tham chiếu, phạm vi, dữ liệu thiếu) được kiểm tra trước; mức độ được bằng chứng hỗ trợ và tính đầy đủ được đánh giá ở bước riêng, và chỉ phần đầu ra có vấn đề được sửa.
4. Đánh giá các cách tổ chức hệ thống trong cùng điều kiện dữ liệu và câu hỏi, xét đồng thời chất lượng báo cáo và chi phí vận hành (thời gian, số lượt gọi mô hình, token, tỷ lệ hoàn thành).

Từ các mục tiêu trên, khóa luận này tập trung giải quyết ba câu hỏi nghiên cứu:

Câu hỏi nghiên cứu thứ nhất. Hệ thống đa tác tử phân cấp, thích ứng theo yêu cầu cần được thiết kế như thế nào để hỗ trợ tổng hợp thông tin và phân tích cơ bản ngân hàng, đồng thời duy trì khả năng truy nguyên từ nhận định tới dữ liệu và nguồn?

Câu hỏi nghiên cứu thứ hai. Trên cùng bộ câu hỏi, snapshot dữ liệu, phiên bản mô hình và prompt, công cụ, chính sách bằng chứng và hợp đồng đầu ra, cấu hình đa tác tử thích ứng B khác cấu hình một tác tử A như thế nào về độ chính xác của dữ kiện và phép tính, tính đầy đủ của bằng chứng, tính đúng đắn của trích dẫn, tính nhất quán giữa các cấp và tính hữu ích; đồng thời khác nhau ra sao về tỷ lệ hoàn thành, độ trễ, số lượt gọi, token và chi phí?

Câu hỏi nghiên cứu thứ ba. Trong cùng điều kiện so sánh, việc bổ sung phản biện ngữ nghĩa và tối đa hai vòng sửa đổi có mục tiêu trong C làm thay đổi chất lượng báo cáo và chi phí vận hành so với B như thế nào, khi mỗi phiên bản sau sửa đổi đều phải qua bước kiểm tra số liệu theo quy tắc lần nữa?

Trong thực nghiệm, cấu hình A là một tác tử; B là hệ thống đa tác tử phân cấp, thích ứng theo yêu cầu nhưng không có vòng phản biện; C giữ nguyên B và bổ sung phản biện ngữ nghĩa cùng tối đa hai vòng sửa đổi, mỗi phiên bản sửa đều được kiểm tra số liệu lại. Câu hỏi nghiên cứu thứ hai đối chiếu A với B, câu hỏi nghiên cứu thứ ba đối chiếu B với C, và không giả định trước cấu hình nào tốt hơn.

### 1.4. Phạm vi và đóng góp của nghiên cứu
Nghiên cứu này lấy phân tích ngân hàng niêm yết Việt Nam làm trường hợp ứng dụng. Dữ liệu gồm mười ngân hàng niêm yết có tổng tài sản lớn nhất (ACB, BID, CTG, HDB, MBB, SHB, STB, TCB, VCB, VPB), mười quý từ quý 1/2024 đến quý 2/2026, với bốn chỉ tiêu: tỷ lệ nợ xấu, tỷ lệ bao phủ nợ xấu, ROA và ROE. Cả hệ thống triển khai và thực nghiệm ở Chương 5 dùng chung bộ dữ liệu này. Nhóm mười ngân hàng là phạm vi đối sánh có giới hạn, không đại diện thống kê cho toàn ngành; mọi thống kê nhóm nêu rõ số ngân hàng làm mẫu số. Phân tích vĩ mô chỉ được thực hiện khi bộ dữ liệu có quan sát vĩ mô đã kiểm chứng; bộ dữ liệu hiện tại chưa có nên hệ thống không tạo số liệu vĩ mô.

Về chức năng, nghiên cứu tập trung vào quá trình từ dữ liệu đã kiểm tra đến báo cáo phân tích. Hệ thống không thay thế chuyên viên phân tích, không tư vấn đầu tư và không đánh giá quá trình suy nghĩ nội bộ của mô hình; đối tượng đánh giá là dữ liệu được dùng, phát biểu phân tích, bằng chứng, hành động sửa đổi, báo cáo cuối cùng và giao diện mà chuyên viên dùng để đặt câu hỏi, theo dõi và đọc báo cáo. Về kiến trúc, lõi phân tích được tách khỏi cách lưu trữ dữ liệu và giao diện, để việc đổi nguồn dữ liệu hay môi trường triển khai hạn chế tối đa việc sửa logic phân tích, kiểm tra và báo cáo.

Công trình nghiên cứu này có ba đóng góp chính. Về ứng dụng, nghiên cứu xây dựng một sản phẩm đã triển khai, đi từ dữ liệu đã kiểm tra đến báo cáo có khả năng truy nguyên. Về thiết kế, nghiên cứu đề xuất kiến trúc kết hợp dữ liệu chuẩn hóa, lập kế hoạch theo câu hỏi, tác tử chuyên trách, kiểm tra theo quy tắc, phản biện có giới hạn và sửa đổi có mục tiêu, trong đó trọng tâm là chọn đúng thành phần và giữ khả năng kiểm tra lại, không phải số lượng tác tử. Về đánh giá, nghiên cứu so sánh kiến trúc một tác tử với các cấu hình đa tác tử trong cùng điều kiện, xét cả chất lượng lẫn chi phí, và đo trực tiếp độ tin cậy của các cơ chế kiểm soát: độ nhạy của bộ kiểm tra câu theo từng loại lỗi, sự phụ thuộc của kết quả vào mô hình ngôn ngữ, khả năng chống chịu trước câu hỏi đối kháng và mức độ khó của bước số hóa từ báo cáo gốc.

Bố cục của khóa luận gồm sáu chương: Chương 1 giới thiệu; Chương 2 trình bày cơ sở lý luận và nguyên tắc thiết kế; Chương 3 mô tả phương pháp, dữ liệu, thiết kế thực nghiệm và các thực nghiệm bổ sung; Chương 4 trình bày kiến trúc, triển khai và sản phẩm; Chương 5 trình bày kết quả và thảo luận; Chương 6 kết luận, nêu hạn chế và hướng phát triển.

## CHƯƠNG 2. CƠ SỞ LÝ LUẬN VÀ NGUYÊN TẮC THIẾT KẾ HỆ THỐNG
Chương này giải thích vì sao bài toán cần kiểm soát dữ liệu và phạm vi phân tích, khi nào chia việc cho nhiều tác tử có lợi, và vì sao đầu ra của mô hình ngôn ngữ cần được kiểm tra trước khi thành báo cáo. Từ đó, chương rút ra sáu nguyên tắc thiết kế cho hệ thống.

### 2.1. Đặc điểm của bài toán phân tích tài chính
Phân tích tài chính phục vụ một mục tiêu hoặc quyết định cụ thể; khung phân tích báo cáo tài chính của CFA Institute bắt đầu từ việc xác định mục đích và bối cảnh, rồi mới thu thập dữ liệu, xử lý và kết luận (CFA Institute, 2026b). Vì vậy, phạm vi thông tin không cố định: câu hỏi về biến động sinh lời cần dữ liệu doanh nghiệp, câu hỏi về vị thế tương đối cần dữ liệu nhóm so sánh, và chỉ khi câu hỏi liên quan tới lãi suất hay chính sách thì thông tin vĩ mô mới cần thiết. Phân tích ngành và phân tích nhóm so sánh cũng khác nhau: phân tích ngành xét đặc điểm chung của lĩnh vực, còn phân tích nhóm so sánh đặt doanh nghiệp cạnh một tập đối thủ cụ thể; kết luận phải phản ánh đúng loại dữ liệu đã dùng.

Dữ liệu tài chính còn phải được hiểu trong ngữ cảnh. Theo khung khái niệm của IFRS Foundation, thông tin tài chính hữu ích phải liên quan và phản ánh trung thực hiện tượng kinh tế, và được tăng cường bởi khả năng so sánh và khả năng kiểm chứng (IFRS Foundation, 2018). De Franco và cộng sự (2011) cho thấy báo cáo tài chính có khả năng so sánh cao hơn gắn với mức độ theo dõi của nhà phân tích và độ chính xác dự báo cao hơn. Với hệ thống tự động, điều này có nghĩa một con số không được xử lý như giá trị đứng độc lập: nó phải gắn với doanh nghiệp, kỳ, chỉ tiêu, đơn vị, nguồn và cách tính, và hai giá trị chỉ được so sánh khi có cơ sở để coi là tương thích.

Khả năng kiểm chứng có thể thực hiện gián tiếp, chẳng hạn bằng cách kiểm tra đầu vào và tính lại theo cùng phương pháp (IFRS Foundation, 2018). Với hệ thống phân tích, nguyên tắc này trở thành yêu cầu giữ liên kết giữa nhận định và dữ liệu làm căn cứ: một giá trị tính toán giữ được đầu vào và công thức đã dùng. Dữ liệu thiếu cũng phải giữ nguyên ý nghĩa: giá trị không có trong nguồn không đồng nghĩa với số không và không phải căn cứ để tự ước tính.

Từ đó rút ra hai nguyên tắc đầu tiên. **Nguyên tắc 1:** phạm vi phân tích được xác định từ câu hỏi, không dùng một chuỗi phân tích cố định cho mọi trường hợp. **Nguyên tắc 2:** dữ liệu được biểu diễn có cấu trúc và truy nguyên được, để mỗi giá trị được dùng đúng ngữ cảnh.

### 2.2. Cơ sở của việc sử dụng hệ thống đa tác tử
Khi một nhiệm vụ gồm nhiều phần việc cần thông tin hoặc công cụ khác nhau, có thể phân rã nhiệm vụ và giao cho các tác tử có trách nhiệm riêng, với một thành phần điều phối kết hợp kết quả. Chẳng hạn, MetaGPT chia việc phát triển phần mềm thành nhiều vai trò theo quy trình phối hợp chuẩn hóa (Hong và cộng sự, 2024), và tương tự, ChatDev tổ chức các tác tử chuyên trách cho thiết kế, lập trình và kiểm thử (Qian và cộng sự, 2024). Kết quả ở miền phần mềm không chứng minh trực tiếp hiệu quả trong phân tích tài chính, nhưng cho thấy cơ chế có ích: khi mỗi thành phần chỉ xử lý một phạm vi hẹp, trách nhiệm với kết quả trung gian rõ hơn và lỗi có thể được kiểm tra theo từng phần.

Đa tác tử cũng phát sinh chi phí phối hợp. MultiAgentBench coi chất lượng phối hợp là một khía cạnh đánh giá riêng và khảo sát nhiều cấu trúc như chuỗi, cây, sao và đồ thị (Zhu và cộng sự, 2025). Giao tiếp nhiều hơn không có nghĩa là phối hợp tốt hơn: cấu trúc giao tiếp thưa có thể đạt kết quả tương đương hoặc tốt hơn với chi phí thấp hơn đáng kể (Li và cộng sự, 2024). Choi và cộng sự (2025) còn cho thấy phần lớn mức cải thiện của tranh luận đa tác tử trên các bài kiểm tra họ khảo sát đến từ cơ chế bỏ phiếu, không phải từ việc tranh luận. Câu hỏi phù hợp vì vậy không phải "nhiều tác tử có tốt hơn một tác tử không", mà là trong loại nhiệm vụ nào chuyên môn hóa đem lại đủ lợi ích để bù chi phí.

Trong hệ thống đề xuất, bộ điều phối trước hết xác định câu hỏi cần loại phân tích nào: câu hỏi chỉ về một ngân hàng có thể chỉ cần tác tử doanh nghiệp; câu hỏi so sánh với nhóm thì thêm tác tử ngành; tác tử vĩ mô chỉ tham gia khi câu hỏi thực sự liên quan tới bối cảnh kinh tế. Từ đó rút ra **Nguyên tắc 3:** chỉ huy động tác tử khi nhiệm vụ tương ứng thực sự cần; và **Nguyên tắc 4:** trách nhiệm và phạm vi của từng tác tử được xác định rõ để giảm tương tác thừa và cho phép kiểm tra theo từng phần.

### 2.3. Cơ sở của việc kiểm tra và sửa đổi kết quả AI
Mô hình ngôn ngữ có thể tạo ra phát biểu sai trong khi câu trả lời vẫn lưu loát; SelfCheckGPT dùng sự thiếu nhất quán giữa các lần phản hồi để phát hiện một phần các phát biểu không có căn cứ (Manakul và cộng sự, 2023). Trong phân tích tài chính, nhiều lỗi không cần mô hình khác đánh giá: một tỷ lệ có thể đối chiếu trực tiếp với dữ liệu đã kiểm chứng, một tham chiếu có thể được kiểm tra là có tồn tại hay không, và doanh nghiệp, kỳ, chỉ tiêu của phát biểu có thể so với yêu cầu ban đầu. Những điều kiện này phù hợp để kiểm tra bằng quy tắc. Nhưng một báo cáo đúng từng con số vẫn có thể dùng số đúng để hỗ trợ một kết luận không phù hợp, hoặc chưa trả lời đủ câu hỏi; đó là chất lượng diễn giải, khác với tính đúng của dữ kiện.

Để cải thiện độ tin cậy của đầu ra, nhiều nghiên cứu gần đây đề xuất tách bạch bước tạo nội dung và bước xác minh thành các pha độc lập. Chẳng hạn, phương pháp Chain-of-Verification của Dhuliawala và cộng sự (2024) yêu cầu mô hình tự lập và trả lời các câu hỏi kiểm chứng trước khi viết câu trả lời cuối, qua đó giảm đáng kể hiện tượng ảo giác (hallucination) trên nhiều dạng nhiệm vụ. Tương tự, Madaan và cộng sự (2023) với khung Self-Refine cho thấy vòng lặp tạo bản nháp, nhận xét và chỉnh sửa đạt chất lượng cao hơn so với việc tạo câu trả lời trong một lượt duy nhất. Tuy nhiên, việc phụ thuộc hoàn toàn vào khả năng tự phản biện của mô hình vẫn tiềm ẩn rủi ro: Liang và cộng sự (2024) chỉ ra hiện tượng suy thoái tư duy (Degeneration-of-Thought), xảy ra khi mô hình trở nên bảo thủ với nhận định ban đầu của chính nó và khó nghĩ theo hướng khác. Do đó, phản biện bằng mô hình ngôn ngữ không nên thay thế các bước đối chiếu dữ liệu có thể thực hiện trực tiếp bằng quy tắc.

Trong khuôn khổ đề tài này, hệ thống được thiết kế theo cách tiếp cận hai lớp: lớp thứ nhất kiểm tra bằng quy tắc độ chính xác số liệu, tham chiếu, phạm vi và dữ liệu thiếu; chỉ khi đạt, lớp thứ hai mới đánh giá mức độ được bằng chứng hỗ trợ, tính đầy đủ và giới hạn của suy luận. Một vấn đề được phát hiện chỉ có giá trị khi dẫn tới thay đổi cụ thể, như bổ sung bằng chứng, thu hẹp kết luận hoặc loại bỏ câu, và việc sửa nên tập trung vào đúng thành phần có lỗi. Từ đó rút ra **Nguyên tắc 5:** những gì kiểm tra được bằng dữ liệu và quy tắc phải được kiểm tra trước khi đánh giá nội dung; và **Nguyên tắc 6:** phản biện và sửa đổi có giới hạn và chỉ nhắm vào phần đầu ra có vấn đề.

### 2.4. Các nguyên tắc thiết kế rút ra cho hệ thống
Bảng 2.1 tóm tắt sáu nguyên tắc và hàm ý của chúng với hệ thống.

*Bảng 2.1: Nguyên tắc thiết kế và hàm ý đối với hệ thống.*

| Cơ sở của vấn đề | Nguyên tắc thiết kế | Hàm ý đối với hệ thống |
|---|---|---|
| Mỗi yêu cầu cần phạm vi thông tin khác nhau | 1. Xác định phạm vi từ câu hỏi | Lập kế hoạch và kiểm tra dữ liệu có hỗ trợ hay không trước khi phân tích. |
| Giá trị tài chính phụ thuộc kỳ, định nghĩa, đơn vị, nguồn | 2. Dữ liệu có cấu trúc, truy nguyên được | Mỗi giá trị giữ ngân hàng, kỳ, chỉ tiêu, đơn vị, phạm vi báo cáo, nguồn, vị trí trong nguồn và công thức nếu là chỉ tiêu tính ra. |
| Không phải yêu cầu nào cũng cần mọi tác tử | 3. Chỉ huy động tác tử cần thiết | Chọn tác tử doanh nghiệp, ngành hoặc vĩ mô theo câu hỏi và dữ liệu sẵn có. |
| Chuyên môn hóa tạo chi phí phối hợp | 4. Trách nhiệm từng tác tử rõ ràng | Bộ điều phối giao việc; mỗi tác tử chỉ trả kết quả thuộc phần việc được giao. |
| Mô hình có thể nêu sai số liệu; số đúng vẫn có thể đi kèm lập luận yếu | 5. Kiểm tra dữ kiện trước, đánh giá nội dung sau | Đối chiếu số liệu, nguồn, phạm vi bằng quy tắc; sau đó mới đánh giá bằng chứng, độ đầy đủ và logic. |
| Phản biện vô ích nếu đầu ra không đổi | 6. Sửa đổi có giới hạn, đúng chỗ | Mỗi vấn đề gắn với câu và tác tử cụ thể; chỉ sửa phần bị ảnh hưởng rồi kiểm tra lại. |

Các nguyên tắc này dẫn tới một quy trình bắt đầu từ câu hỏi: xác định phạm vi và kiểm tra dữ liệu, chọn tác tử, tổng hợp kết quả liên quan, đối chiếu các phát biểu với dữ liệu, rồi đánh giá nội dung và chỉ sửa phần có vấn đề. Cơ sở lý luận không cho phép khẳng định trước rằng kiến trúc đa tác tử hay cơ chế phản biện luôn tốt hơn, vì lợi ích đi kèm chi phí và phụ thuộc vào nhiệm vụ. Vì vậy, Chương 3 xây dựng phương pháp so sánh các cấu hình trong cùng điều kiện dữ liệu và câu hỏi.

## TÀI LIỆU THAM KHẢO

CFA Institute. (2026a). *Company analysis: Past and present* [Refresher reading, 2026 CFA Program curriculum, Level I, Equity Investments]. https://www.cfainstitute.org/insights/professional-learning/refresher-readings/2026/company-analysis-past-and-present

CFA Institute. (2026b). *Introduction to financial statement analysis* [Refresher reading, 2026 CFA Program curriculum, Level I, Financial Statement Analysis]. https://www.cfainstitute.org/insights/professional-learning/refresher-readings/2026/introduction-financial-statement-analysis

Choi, H. K., Zhu, X., & Li, S. (2025). *Debate or vote: Which yields better decisions in multi-agent large language models?* arXiv. https://doi.org/10.48550/arXiv.2508.17536

De Franco, G., Kothari, S. P., & Verdi, R. S. (2011). The benefits of financial statement comparability. *Journal of Accounting Research, 49*(4), 895–931. https://doi.org/10.1111/j.1475-679X.2011.00415.x

Dhuliawala, S., Komeili, M., Xu, J., Raileanu, R., Li, X., Celikyilmaz, A., & Weston, J. (2024). Chain-of-verification reduces hallucination in large language models. In *Findings of the Association for Computational Linguistics: ACL 2024* (pp. 3563–3578). Association for Computational Linguistics. https://doi.org/10.18653/v1/2024.findings-acl.212

Hevner, A. R., March, S. T., Park, J., & Ram, S. (2004). Design science in information systems research. *MIS Quarterly, 28*(1), 75–105. https://doi.org/10.2307/25148625

Hong, S., Zhuge, M., Chen, J., Zheng, X., Cheng, Y., Wang, J., Zhang, C., Wang, Z., Yau, S., Lin, Z., Zhou, L., Ran, C., Xiao, L., Wu, C., & Schmidhuber, J. (2024). MetaGPT: Meta programming for a multi-agent collaborative framework. In *International Conference on Learning Representations 2024 (ICLR 2024)* (pp. 23247–23275). https://proceedings.iclr.cc/paper_files/paper/2024/hash/6507b115562bb0a305f1958ccc87355a-Abstract-Conference.html

IFRS Foundation. (2018). *Conceptual framework for financial reporting*. https://www.ifrs.org/issued-standards/list-of-standards/conceptual-framework/

Ji, Z., Lee, N., Frieske, R., Yu, T., Su, D., Xu, Y., Ishii, E., Bang, Y. J., Madotto, A., & Fung, P. (2023). Survey of hallucination in natural language generation. *ACM Computing Surveys, 55*(12), Article 248. https://doi.org/10.1145/3571730

Li, Y., Du, Y., Zhang, J., Hou, L., Grabowski, P., Li, Y., & Ie, E. (2024). Improving multi-agent debate with sparse communication topology. In *Findings of the Association for Computational Linguistics: EMNLP 2024* (pp. 7281–7294). Association for Computational Linguistics. https://doi.org/10.18653/v1/2024.findings-emnlp.427

Li, Y., Wang, S., Ding, H., & Chen, H. (2023). Large language models in finance: A survey. In *Proceedings of the Fourth ACM International Conference on AI in Finance* (pp. 374–382). Association for Computing Machinery. https://doi.org/10.1145/3604237.3626869

Liang, T., He, Z., Jiao, W., Wang, X., Wang, Y., Wang, R., Yang, Y., Shi, S., & Tu, Z. (2024). Encouraging divergent thinking in large language models through multi-agent debate. In *Proceedings of the 2024 Conference on Empirical Methods in Natural Language Processing* (pp. 17889–17904). Association for Computational Linguistics. https://doi.org/10.18653/v1/2024.emnlp-main.992

Madaan, A., Tandon, N., Gupta, P., Hallinan, S., Gao, L., Wiegreffe, S., Alon, U., Dziri, N., Prabhumoye, S., Yang, Y., Gupta, S., Majumder, B. P., Hermann, K., Welleck, S., Yazdanbakhsh, A., & Clark, P. (2023). Self-Refine: Iterative refinement with self-feedback. In A. Oh, T. Naumann, A. Globerson, K. Saenko, M. Hardt, & S. Levine (Eds.), *Advances in neural information processing systems* (Vol. 36, pp. 46534–46594). Curran Associates. https://proceedings.neurips.cc/paper_files/paper/2023/hash/91edff07232fb1b55a505a9e9f6c0ff3-Abstract-Conference.html

Manakul, P., Liusie, A., & Gales, M. (2023). SelfCheckGPT: Zero-resource black-box hallucination detection for generative large language models. In *Proceedings of the 2023 Conference on Empirical Methods in Natural Language Processing* (pp. 9004–9017). Association for Computational Linguistics. https://doi.org/10.18653/v1/2023.emnlp-main.557

Qian, C., Liu, W., Liu, H., Chen, N., Dang, Y., Li, J., Yang, C., Chen, W., Su, Y., Cong, X., Xu, J., Li, D., Liu, Z., & Sun, M. (2024). ChatDev: Communicative agents for software development. In *Proceedings of the 62nd Annual Meeting of the Association for Computational Linguistics (Volume 1: Long Papers)* (pp. 15174–15186). Association for Computational Linguistics. https://doi.org/10.18653/v1/2024.acl-long.810

Zhu, K., Du, H., Hong, Z., Yang, X., Guo, S., Wang, Z., Wang, Z., Qian, C., Tang, R., Ji, H., & You, J. (2025). MultiAgentBench: Evaluating the collaboration and competition of LLM agents. In *Proceedings of the 63rd Annual Meeting of the Association for Computational Linguistics (Volume 1: Long Papers)* (pp. 8580–8622). Association for Computational Linguistics. https://doi.org/10.18653/v1/2025.acl-long.421
