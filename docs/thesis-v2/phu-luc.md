# PHỤ LỤC

## Phụ lục A. Sản phẩm trực tuyến

Địa chỉ: https://fin-ai.eddiephung.me

Tên đăng nhập: admin

Mật khẩu: {{DEMO_PASSWORD}}

Tài khoản này chỉ dùng cho bản trình bày của khóa luận.

### A.1. Thao tác thử nhanh

*Bảng A.1: Các thao tác thử nhanh.*

| Thao tác | Cách làm | Kết quả mong đợi |
|---|---|---|
| Tra cứu một con số | Nhập "Tỷ lệ nợ xấu của ACB quý 2/2026 là bao nhiêu?" | Thẻ trả lời kèm số trang báo cáo gốc |
| Xếp hạng | Nhập "Ngân hàng nào có tỷ lệ bao phủ nợ xấu cao nhất quý 2/2026?" | Báo cáo xếp hạng mười ngân hàng |
| Xu hướng | Nhập "ROE của BID thay đổi thế nào trong năm 2026?" | Biểu đồ theo quý so với trung vị nhóm |
| So sánh | Nhập "So sánh ACB và CTG quý 2/2026" | Bảng đối chiếu từng chỉ tiêu |
| Tra cứu vĩ mô | Nhập "Lãi suất tái cấp vốn hiện nay là bao nhiêu?" | Thẻ trả lời lãi suất tái cấp vốn 4,5% (kỳ quý 2/2026, QĐ 1123/QĐ-NHNN) |
| Tra cứu toàn ngành (không nêu kỳ) | Nhập "Tỷ lệ nợ xấu toàn hệ thống là bao nhiêu?" | Thẻ trả lời tỷ lệ nợ xấu 4,55% (kỳ quý 3/2024, ghi chú số mới nhất có sẵn do chưa có quý 2/2026) |
| Từ chối kỳ vĩ mô chưa có số | Nhập "Tỷ lệ nợ xấu toàn hệ thống quý 2/2026 là bao nhiêu?" | Thông báo từ chối nêu rõ chưa có số liệu cho quý 2/2026 và chỉ ra kỳ gần nhất có số là quý 3/2024 |
| Từ chối | Nhập câu hỏi về ngân hàng hoặc kỳ chưa có, hoặc yêu cầu không phải phân tích | Thông báo kèm dữ liệu hiện có |
| Thêm ngân hàng | Trang Dữ liệu, chọn "Mẫu VIB 2025 hợp lệ", bấm "Kiểm tra và tải lên", rồi "Hỏi về VIB" | Báo cáo có ghi chú số liệu do người dùng cung cấp |
| Thêm ngân hàng từ PDF | Làm theo mục A.2 | Bảng số liệu trích xuất, kiểm tra tự động, rồi hỏi về ngân hàng vừa nạp |

### A.2. Quy trình nạp ngân hàng mới từ báo cáo tài chính PDF

Quy trình này dành cho người muốn tự kiểm tra bước số hóa và gồm các bước: mở trang "Dữ liệu" và chọn thẻ nạp từ PDF; tải lên báo cáo tài chính hợp nhất đã kiểm toán và khai báo mã ngân hàng, năm tài chính, phạm vi báo cáo; chờ hệ thống đọc tệp; xem bảng số liệu trích xuất, trong đó mỗi ô có số trang nguồn để mở xem; sửa hoặc chọn lại ô sai; xác nhận các ô đã khớp phép kiểm số học; nhập vào cơ sở dữ liệu và xem bốn chỉ tiêu được tính lại; cuối cùng đặt câu hỏi về ngân hàng vừa nạp. Việc đọc là bán tự động: mô hình chỉ chọn dòng ứng viên trên trang, con số được lấy từ chính dòng đó bằng chương trình, và người dùng phải xem lại và xác nhận. Ngân hàng tải lên có nhãn riêng và không vào trung vị nhóm hay xếp hạng. Có thể thử nhanh bằng bộ mẫu dựng sẵn ở Bước 1.

## Phụ lục B. Bộ dữ liệu

Bộ dữ liệu vận hành mười ngân hàng niêm yết lớn nhất (ACB, BID, CTG, HDB, MBB, SHB, STB, TCB, VCB, VPB), mười quý từ
quý 1/2024 đến quý 2/2026. Bộ dữ liệu gồm 1.735 quan sát: 1.335 số liệu đầu vào được đọc từ 101 tài liệu báo cáo tài chính hợp nhất của từng ngân hàng với 452 trang trích dẫn nguồn riêng biệt (mỗi dòng ghi trang nguồn và đường dẫn tới tệp báo cáo gốc), cùng 400 giá trị của bốn chỉ tiêu (tỷ lệ nợ xấu, tỷ lệ bao phủ nợ xấu, ROA, ROE) được tính lại từ các số liệu đầu vào theo công thức được định danh phiên bản. Bảng B.1 tóm tắt 101 báo cáo gốc theo ngân hàng; danh sách đầy đủ từng báo cáo (ngân hàng, kỳ, loại báo cáo, đường dẫn, mã băm SHA-256 đầy đủ) nằm trong tệp CSV `phu-luc-b1-nguon-bao-cao.csv` của kho mã. Các tệp PDF báo cáo gốc và nguồn của dữ liệu vĩ mô, ngành được lưu trong gói dữ liệu gốc trên Google Drive: https://drive.google.com/file/d/1vvcdw82zMq_hxKsZ0pisYOIIla_C-iPZ/view?usp=sharing (xem Phụ lục C). Mã SHA-256 là một dãy 64 ký tự do thuật toán băm tính ra từ toàn bộ nội dung của tệp, đóng vai trò dấu vân tay: nếu tệp thay đổi dù chỉ một ký tự thì mã đổi hoàn toàn, nên người đọc có thể tính mã của tệp tải về và so với mã trong bảng để biết đó có đúng là tệp đã dùng hay không.

Bên cạnh mười ngân hàng, bộ dữ liệu mở rộng thực thể "Việt Nam" (`VN`) gồm 187 quan sát (163 quan sát sơ cấp hợp lệ và 24 quan sát thứ cấp chờ kiểm định) của 20 chỉ tiêu kinh tế vĩ mô và toàn ngành qua 15 quý (từ quý 4/2022 đến quý 2/2026), có đối soát nguồn gốc từ Ngân hàng Nhà nước và Tổng cục Thống kê (Cục Thống kê). Khác với chuỗi ngân hàng đầy đủ theo quý, các chỉ tiêu ngành áp dụng cơ chế xác định kỳ linh hoạt (`as-of-latest`) khi phân tích.

*Bảng B.1: Tóm tắt 101 báo cáo tài chính hợp nhất gốc của bộ dữ liệu.*

| Ngân hàng | Số báo cáo | Kỳ báo cáo | Nơi đăng tải | Mã băm SHA-256 (báo cáo đầu tiên, 12 ký tự) |
|:---:|:---:|:---:|---|:---:|
| ACB | 10 | Q1/2024 đến Q2/2026 | static2.vietstock.vn, acb.com.vn | fc106a3ea36d |
| BID | 10 | Q1/2024 đến Q2/2026 | static2.vietstock.vn, www.bidv.com.vn | c987344424e1 |
| CTG | 10 | Q1/2024 đến Q2/2026 | static2.vietstock.vn, investor.vietinbank.vn | a06c48abd7f2 |
| HDB | 10 | Q1/2024 đến Q2/2026 | static2.vietstock.vn, cdn.hdbank.com.vn | cade0869cd8b |
| MBB | 10 | Q1/2024 đến Q2/2026 | static2.vietstock.vn | 7412b541b626 |
| SHB | 10 | Q1/2024 đến Q2/2026 | static2.vietstock.vn | e1b0e4db622d |
| STB | 10 | Q1/2024 đến Q2/2026 | static2.vietstock.vn | 0ac492f8c7e3 |
| TCB | 11 | Q4/2023 đến Q2/2026 | static2.vietstock.vn | b37d5e9a854d |
| VCB | 10 | Q1/2024 đến Q2/2026 | static2.vietstock.vn | 66fe3ece1d34 |
| VPB | 10 | Q1/2024 đến Q2/2026 | static2.vietstock.vn, www.vpbank.com.vn, cafefnew.mediacdn.vn | c70fe8fffe29 |

Để đối chiếu với Chương 5: các thực nghiệm so sánh A/B/C chạy trên một bản dựng trước của bộ dữ liệu; bản dựng cuối cùng chỉ khác ở nhãn đọc của các dòng lợi nhuận STB và không đổi giá trị nào.

## Phụ lục C. Mã nguồn và kết quả thực nghiệm

Mã nguồn được công khai tại https://github.com/thaicuong576/final-thesis (bản phát hành `milestone/thesis-submission-2026-10`, kèm bộ dữ liệu SQLite dùng cho thực nghiệm). Dữ liệu gốc gồm 101 báo cáo tài chính PDF của mười ngân hàng và nguồn của 187 dòng dữ liệu vĩ mô, ngành được lưu trong một tệp nén trên Google Drive: https://drive.google.com/file/d/1vvcdw82zMq_hxKsZ0pisYOIIla_C-iPZ/view?usp=sharing. Kết quả của các thực nghiệm được lưu cùng mã nguồn dưới dạng tệp do chương trình ghi lại; Bảng C.1 liệt kê nội dung từng nhóm (tên thư mục trong ngoặc là tên thư mục trong kho mã).

*Bảng C.1: Kết quả thực nghiệm được lưu.*

| Thực nghiệm | Nội dung |
|---|---|
| Thực nghiệm chính (ba cấu hình) | 36 lượt chạy, điểm chấm, biểu đồ (`experiments/er9`) |
| Cấu hình D (không gọi mô hình) | 12 lượt chạy, điểm chấm, bảng từng câu hỏi, bản đồ nhiệt (`experiments/er9d`) |
| Chạy lại A/B/C trên `gpt-5.6-luna` | 36 lượt chạy, điểm chấm, bảng từng câu hỏi (`experiments/er9-luna`) |
| Độ nhạy của bộ kiểm chứng | 1.210 câu đột biến, kết quả theo loại lỗi, trước (`experiments/mut1`) và sau khi thêm quy tắc, ba bộ seed (`experiments/mut2`) |
| Mô hình phổ thông không công cụ | Câu trả lời gốc, quy tắc chấm và kết quả (`experiments/e6-pure-llm`) |
| Chỉ mục kết quả | Bảng số liệu, lệnh chạy lại và phiên bản mã nguồn của từng thực nghiệm |

## Phụ lục D. Khảo sát người dùng thăm dò

### D.1. Phiếu khảo sát

Phiếu khảo sát được thực hiện bằng Google Forms; nội dung trình bày ở Bảng D.1. Phiếu nêu rõ khảo sát ẩn danh, tự nguyện, mất khoảng 4-5 phút.

*Bảng D.1: Phiếu khảo sát người dùng.*

| Câu | Nội dung | Lựa chọn |
|:---:|---|---|
| 1 | Vai trò hiện tại | Sinh viên tài chính/kinh tế · Nhân viên phân tích (CTCK, quỹ, ngân hàng) · Cán bộ tín dụng/quản trị rủi ro · Nhà đầu tư cá nhân · Khác |
| 2 | Số năm kinh nghiệm làm việc hoặc đầu tư | Chưa có · Dưới 1 năm · 1-3 năm · Trên 3 năm |
| 3 | Tần suất tra số liệu tài chính của ngân hàng | Hàng tuần · Hàng tháng · Theo quý · Hiếm khi · Chưa bao giờ |
| 4 | Nguồn lấy số liệu (chọn nhiều) | Báo cáo tài chính PDF gốc · Nền tảng dữ liệu · Trang tin tài chính · Bảng tính tự lập · Chatbot AI · Khác |
| 5 | Thời gian tìm và đối chiếu số liệu của một ngân hàng trong một quý | Dưới 15 phút · 15-30 · 30-60 · Trên 60 phút · Tôi không tự làm việc này |
| 6 | Khó khăn lớn nhất (tối đa 2) | Tìm đúng số · Kiểm tra số có đúng không · Các nguồn cho số khác nhau · So sánh với nhóm ngân hàng · Viết nhận định từ số liệu · Không gặp khó khăn · Khác |
| 7 | Đã từng dùng chatbot AI để tra số liệu tài chính chưa | Chưa · Rồi, chưa phát hiện số sai · Rồi, đã gặp số sai · Rồi, nhưng không rõ số có đúng không |
| 8 | Mức tin tưởng vào số liệu do AI trả lời | Thang 1 (hoàn toàn không tin) đến 5 (hoàn toàn tin) |
| 9 | Điều kiện để dùng kết quả do AI tạo ra (tối đa 2) | Truy được tới trang báo cáo gốc · Có kiểm tra tự động trước khi hiển thị · Có người duyệt lại · Nêu rõ giới hạn của kết quả · Nguồn/thương hiệu uy tín · Không đặt điều kiện gì · Khác |
| 10 | Thời gian chờ tối đa chấp nhận được cho một báo cáo | Dưới 10 giây · Dưới 30 giây · Dưới 1 phút · Dưới 3 phút · Lâu hơn cũng được |
| 11 | Chi phí tối đa chấp nhận cho mỗi báo cáo | Chỉ chấp nhận miễn phí · Dưới 1.000 đồng · Dưới 10.000 đồng · Có thể cao hơn nếu rất chính xác |
| 12 | (Không bắt buộc) Một lần AI hoặc nguồn số liệu đưa số sai và hậu quả | Câu trả lời mở |

### D.2. Kết quả khảo sát

*Bảng D.2: Kết quả khảo sát (n = 15, 16-22/10/2026).*

| Câu | Kết quả (số người) |
|---|---|
| 1. Vai trò | Sinh viên 9; nhà đầu tư cá nhân 2; nhân viên phân tích 3; cán bộ tín dụng 1 |
| 2. Kinh nghiệm | Chưa có 5; dưới 1 năm 3; 1-3 năm 4; trên 3 năm 3 |
| 3. Tần suất | Hàng tuần 5; hàng tháng 5; theo quý 4; hiếm khi 1; chưa bao giờ 0 |
| 4. Nguồn | Trang tin 8; nền tảng dữ liệu 8; chatbot AI 7; bảng tính 7; PDF gốc 6 |
| 5. Thời gian | Dưới 15 phút 1; 15-30 phút 4; 30-60 phút 6; trên 60 phút 2; không tự làm 2 |
| 6. Khó khăn | Kiểm tra số có đúng không 8; các nguồn khác nhau 7; tìm đúng số 6; so sánh nhóm 4; viết nhận định 2; không khó khăn 2 |
| 7. Dùng chatbot AI | Chưa 3; rồi, chưa phát hiện số sai 3; rồi, đã gặp số sai 5; rồi, không rõ 4 |
| 8. Tin tưởng (1-5) | Mức 1: 1; mức 2: 5; mức 3: 7; mức 4: 2; mức 5: 0; trung vị 3 |
| 9. Điều kiện | Truy tới trang gốc 11; có người duyệt lại 6; kiểm tra tự động 5; nêu rõ giới hạn 5; không đặt điều kiện 2 |
| 10. Thời gian chờ | Dưới 10 giây 2; dưới 30 giây 4; dưới 1 phút 6; dưới 3 phút 3 |
| 11. Chi phí | Chỉ miễn phí 4; dưới 1.000 đồng 4; dưới 10.000 đồng 4; cao hơn nếu rất chính xác 3 |
| 12. Câu mở | 3 phản hồi (xem D.3) |

Các câu 4, 6 và 9 cho chọn nhiều nên tổng lớn hơn 15. Một phản hồi chọn đồng thời "Tìm đúng số" và "Không gặp khó khăn" (câu 6), "Nêu rõ giới hạn" và "Không đặt điều kiện gì" (câu 9); phản hồi này được giữ lại, và các kết luận chính (câu 8, 9, 10) không đổi khi loại nó. Dữ liệu thô được lưu trong Google Sheets của tác giả và có thể cung cấp theo yêu cầu.

### D.3. Câu trả lời mở

Ba câu trả lời được trích nguyên văn, không kèm thông tin nhận diện: "Chatbot đưa ROE của ngân hàng khác nhưng nói rất tự tin."; "Hai trang cho hai con số nợ xấu khác nhau, không biết tin trang nào."; "Số trên các nền tảng lệch định nghĩa ROE nên phải mở lại báo cáo gốc."
