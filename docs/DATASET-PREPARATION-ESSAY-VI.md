# Đề cương viết lại phần Chuẩn bị Dataset

> Tài liệu này là bản đề cương và định hướng biên soạn bằng tiếng Việt cho phần “Chuẩn bị Dataset”. Tệp luận văn nguồn vẫn là tài liệu tham chiếu chỉ đọc và không bị thay thế.

## 1. Mục tiêu và phạm vi xây dựng dataset

Dataset được xây dựng để cung cấp nền tảng dữ liệu có thể tái lập cho việc phân tích định lượng và định tính đối với các doanh nghiệp niêm yết thuộc ngành Ngân hàng và Chứng khoán tại Việt Nam. Dataset không chỉ là tập hợp các tệp tải về, mà là một hệ thống gồm dữ liệu nguồn bất biến, thông tin nguồn, dữ liệu đã chuẩn hóa, các chỉ số phái sinh, bằng chứng văn bản và các kết quả kiểm định chất lượng.

Phạm vi ban đầu gồm mười ngân hàng VCB, BID, CTG, TCB, MBB, ACB, VPB, HDB, STB và LPB, cùng sáu công ty chứng khoán SSI, VND, HCM, VCI, TCBS và MBS. Phạm vi thời gian cần được chốt thành một cửa sổ cố định gồm tám quý, hoặc một khoảng tám đến mười hai quý nếu thiết kế nghiên cứu yêu cầu. Dữ liệu theo ngày được sử dụng ở tần suất cuối ngày; dữ liệu trong ngày không phải yêu cầu của phiên bản MVP.

Dataset được chia thành dữ liệu tham chiếu, dữ liệu tài chính định kỳ, dữ liệu thị trường, dữ liệu vĩ mô và chính sách, tài liệu sự kiện hoặc văn bản phi cấu trúc, dữ liệu dẫn xuất và dữ liệu kiểm định. Việc phân chia này giúp hệ thống phân biệt giữa sự kiện được công bố, số liệu có thể tính toán và kết luận do tác tử sinh ra.

## 2. Chiến lược nguồn và thứ tự ưu tiên

Nguồn chính được ưu tiên theo thứ tự: báo cáo và công bố chính thức của doanh nghiệp; Ngân hàng Nhà nước Việt Nam; Tổng cục Thống kê; HOSE, HNX và SSC; sau đó mới đến các nhà cung cấp dữ liệu thương mại hoặc API công khai. Vietcap IQ, VNDIRECT và KBS/vnstock có thể được sử dụng như nguồn tăng tốc để thu thập dữ liệu có cấu trúc, nhưng không tự động trở thành nguồn chân lý cuối cùng.

Yahoo Finance, MSN Finance, GitHub, World Bank và DBnomics/IMF chỉ nên được gắn nhãn đối chiếu hoặc dự phòng. Báo cáo nghiên cứu của SSI, Vietcap và MBS có giá trị bổ sung bối cảnh, giả thuyết và diễn giải ngành, nhưng không được dùng để thay thế số liệu tài chính gốc.

Mỗi lần thu thập phải ghi nhận địa chỉ nguồn, thời điểm truy xuất, nhà phát hành, mã cổ phiếu, kỳ dữ liệu, loại tài liệu, phương thức truy cập, giấy phép hoặc hạn chế sử dụng, đường dẫn lưu trữ và mã băm nội dung. Khả năng tải được dữ liệu phải được tách biệt với việc dữ liệu đã được kiểm tra và chấp nhận.

## 3. Đánh giá độ phủ và tình trạng hiện tại

Độ phủ phải được tính từ manifest theo từng mã, từng kỳ, từng loại dữ liệu và từng trường quan trọng. Không nên dùng các tỷ lệ ước tính như bằng chứng hoàn thành nếu chưa có bản ghi truy xuất và kiểm tra tương ứng.

Snapshot hiện tại đã có dữ liệu báo cáo tài chính từ Vietcap cho mười lăm trên mười sáu mã, gồm bảng cân đối kế toán, báo cáo kết quả kinh doanh, báo cáo lưu chuyển tiền tệ và một số chuỗi tỷ số. KBS cung cấp dữ liệu cuối ngày cho mười lăm mã, bao gồm MBS. VCI và Yahoo có độ phủ thấp hơn và được dùng để đối chiếu. TCBS hiện chưa có độ phủ có thể sử dụng ổn định trong các nguồn cấu trúc đã kiểm tra.

Kho Zenodo đã cung cấp bốn mươi ba trên bốn mươi tám báo cáo thường niên mục tiêu giai đoạn 2023-2025. HDB và STB còn thiếu báo cáo năm 2023, trong khi TCBS chưa có hồ sơ trong chỉ mục đã sử dụng. Gói dữ liệu đầy đủ có kích thước khoảng 56,58 GiB nên không được tải nguyên gói vì vượt giới hạn lưu trữ của dự án.

World Bank và DBnomics/IMF đã cung cấp các chuỗi vĩ mô dự phòng với quy mô nhỏ. Tuy nhiên, dữ liệu SBV, GSO, HOSE và HNX chính thức vẫn cần được thu thập hoặc đối chiếu trước khi đưa vào gold dataset.

## 4. Thu thập dữ liệu định lượng

Luồng dữ liệu định lượng bắt đầu bằng việc lưu nguyên phản hồi từ API. Sau đó, dữ liệu được chuyển đổi thành các bản ghi có mã cổ phiếu, ngành, kỳ báo cáo, đơn vị, giá trị, nguồn và trạng thái chất lượng.

Đối với ngân hàng, các trường trọng tâm gồm tài sản, dư nợ, tiền gửi, thu nhập lãi thuần, chi phí hoạt động, nợ xấu, dự phòng, NIM, CASA, CIR, LDR và CAR. Đối với công ty chứng khoán, các trường trọng tâm gồm vốn chủ sở hữu, dư nợ margin, doanh thu môi giới, thu nhập cho vay, tài sản FVTPL, tài sản HTM và các cấu phần doanh thu liên quan.

Dữ liệu thị trường gồm giá mở cửa, cao nhất, thấp nhất, đóng cửa, khối lượng và giá trị giao dịch theo ngày. ADTV, vốn hóa và các chỉ số thanh khoản là dữ liệu dẫn xuất, chỉ được tính sau khi xác định rõ đơn vị và ý nghĩa của giá trị giao dịch.

## 5. Thu thập tài liệu và dữ liệu phi cấu trúc

Luồng tài liệu gồm báo cáo thường niên, báo cáo tài chính đã kiểm toán, thuyết minh báo cáo tài chính, văn bản SBV, báo cáo GSO, công bố HOSE/HNX và báo cáo nghiên cứu ngành. Tài liệu gốc được giữ nguyên, kiểm tra mã băm và gắn thông tin định danh trước khi phân tích.

Sau bước kiểm tra lớp văn bản, số trang và khả năng trích xuất bảng, tài liệu có thể được phân đoạn theo ngữ nghĩa để phục vụ tìm kiếm. Mỗi đoạn văn bản phải giữ được mã nguồn, tài liệu, trang, năm tài chính, kỳ báo cáo, mã cổ phiếu, loại tài liệu và tên phần. Vector database chỉ phục vụ truy xuất bằng chứng; nó không thay thế dữ liệu số có cấu trúc.

## 6. Chuẩn hóa dữ liệu

Tất cả chu kỳ phải được đưa về quy ước thống nhất như `2024_Q4` hoặc `FY2024`, đồng thời giữ lại ngày công bố và ngày truy xuất khi các ngày này có ý nghĩa khác nhau. Quy trình phải phân biệt kỳ quý, số liệu lũy kế từ đầu năm, số liệu cả năm, báo cáo hợp nhất và báo cáo riêng.

Đơn vị tiền tệ, quy mô nghìn hoặc triệu, phần trăm, tỷ lệ và cách làm tròn phải được ghi rõ. Giá trị thiếu phải được giữ là thiếu, không được tự động chuyển thành số không. Các giá trị ước tính, mâu thuẫn hoặc không hợp lệ phải có trạng thái chất lượng riêng.

## 7. Tính chỉ số và benchmark

Mọi chỉ số phái sinh phải được tính bằng mã nguồn xác định, có công thức, đơn vị, kỳ tính và quy tắc xử lý thiếu dữ liệu. NIM, CASA, NPL, LLR, CIR, LDR và CAR của ngân hàng cần được kiểm tra với thuyết minh và quy định phù hợp. Margin/equity, FVTPL, doanh thu môi giới và các chỉ số của công ty chứng khoán cũng phải được kiểm tra theo đúng định nghĩa kế toán hoặc quy định áp dụng.

Sau khi dữ liệu doanh nghiệp được xác nhận, hệ thống mới tính trung vị, trung bình, độ lệch chuẩn, percentile, ADTV và các benchmark ngành. Quy tắc chiều của percentile, cách xử lý giá trị ngoại lệ và cách tổng hợp hai sàn phải được ghi nhận trước khi chạy đánh giá.

## 8. Kiểm định và xây dựng gold dataset

Kiểm định gồm kiểm tra tính hợp lệ của schema, đơn vị, kỳ dữ liệu, trùng lặp, tính nhất quán số học, sự thay đổi bất thường và khác biệt giữa các nguồn. Một mẫu đại diện gồm ngân hàng và công ty chứng khoán phải được đối chiếu với báo cáo chính thức và tài liệu có số trang.

Gold dataset là tập quan sát đã được chuẩn hóa, có nguồn, có trạng thái chất lượng và được con người kiểm tra. Nó phải đi kèm báo cáo độ phủ, báo cáo thiếu dữ liệu, danh sách mâu thuẫn, quyết định xử lý và lệnh tái lập. Dữ liệu vendor chưa đối chiếu không được gọi là gold data.

## 9. Lưu trữ và tái lập

Kiến trúc lưu trữ được tổ chức theo các lớp:

```text
API JSON và PDF gốc
        ↓
Manifest nguồn và mã băm
        ↓
SQLite hoặc Parquet đã chuẩn hóa
        ↓
Gold dataset và báo cáo chất lượng
        ↓
Vector store cho tài liệu
```

JSON và PDF ở lớp raw phải bất biến để có thể chạy lại bộ phân tích khi công thức hoặc bộ phân tích thay đổi. SQLite phù hợp cho truy vấn và liên kết dữ liệu; Parquet phù hợp cho các bảng phân tích lớn; CSV chỉ nên dùng cho xuất dữ liệu và kiểm tra thủ công.

## 10. Kiểm soát rủi ro

Các rủi ro chính gồm API ngừng hoạt động, API thay đổi schema, dữ liệu vendor thay đổi, sai lệch OCR, bảng PDF khó đọc, kỳ báo cáo không đồng bộ, giới hạn top-10 của dữ liệu thị phần môi giới, hạn chế giấy phép và thiếu dữ liệu TCBS.

Biện pháp kiểm soát gồm chụp snapshot cục bộ, lưu mã băm, ghi nhận phiên bản và thời điểm truy xuất, kiểm tra thủ công mẫu PDF, tách nguồn chính khỏi nguồn đối chiếu, ghi nhận giá trị thiếu và giữ giới hạn dữ liệu dự án dưới 30 GB.

## 11. Điều kiện chuyển sang kiến trúc tác tử

Việc thu thập đủ các tệp còn thiếu là điều kiện cần nhưng chưa đủ để chuyển sang xây dựng workflow tác tử. Trước khi đánh giá hệ thống phân tích tài chính, cần hoàn thành tối thiểu các bước sau:

1. Chốt cửa sổ quý, vũ trụ mã và cách xử lý TCBS.
2. Chốt định nghĩa và công thức của các metric.
3. Hoàn thành manifest và kiểm tra độ phủ theo mã, kỳ và trường.
4. Chuẩn hóa dữ liệu và đối chiếu mẫu với nguồn chính thức.
5. Tạo gold dataset có nhãn chất lượng và bằng chứng trang.
6. Kiểm thử `MetricObservation`, `EvidenceSnippet`, `AgentPayload` và các contract liên quan.
7. Tạo fixture tái lập cho baseline và các câu hỏi đánh giá.
8. Ghi nhận báo cáo chất lượng, missingness và các mâu thuẫn còn mở.

Nếu “kiến trúc tác tử” chỉ có nghĩa là thiết kế interface, schema, adapter, router và test fixture, có thể chuẩn bị một skeleton giới hạn trước khi gold dataset hoàn tất. Nếu có nghĩa là chạy workflow thật, sinh phân tích tài chính hoặc tuyên bố kết quả đánh giá, thì chưa đủ cho đến khi các điều kiện trên được đáp ứng.

## 12. Kết luận

Dataset hiện tại đã đủ để chứng minh khả năng thu thập và xây dựng nền tảng staging. Dataset chưa đủ để chứng minh tính đúng đắn của sản phẩm phân tích. Vì vậy, thứ tự phù hợp là hoàn thiện các gap chính, chuẩn hóa và kiểm định, tạo gold dataset, sau đó mới xây dựng và đánh giá workflow Macro Agent, Sector Agent, Company Agent và Master Orchestrator trên cùng một snapshot có thể tái lập.
