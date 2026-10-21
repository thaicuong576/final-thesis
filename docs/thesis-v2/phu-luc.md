# PHỤ LỤC

## Phụ lục A. Sản phẩm trực tuyến

Địa chỉ: https://fin-ai.eddiephung.me

Tên đăng nhập: admin

Mật khẩu: Kltn@2026

Tài khoản này chỉ dùng cho bản trình bày của khóa luận.

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
quý 1/2024 đến quý 2/2026. Bộ dữ liệu gồm 1.735 quan sát: 1.335 số liệu đầu vào được đọc từ 101 tài liệu báo cáo tài chính hợp nhất của từng ngân hàng với 452 trang trích dẫn nguồn riêng biệt (mỗi dòng ghi trang nguồn và đường dẫn tới tệp báo cáo gốc), cùng 400 giá trị của bốn chỉ tiêu (tỷ lệ nợ xấu, tỷ lệ bao phủ nợ xấu, ROA, ROE) được tính lại từ các số liệu đầu vào theo công thức được định danh phiên bản. Bảng B.1 tóm tắt 101 báo cáo gốc theo ngân hàng; danh sách đầy đủ từng báo cáo (ngân hàng, kỳ, loại báo cáo, đường dẫn, mã băm SHA-256 đầy đủ) nằm trong tệp `docs/thesis-v2/phu-luc-b1-nguon-bao-cao.csv`.

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

Mã nguồn nằm trong một kho riêng tư và được cung cấp theo yêu cầu. Kết quả của các thực nghiệm được lưu cùng mã nguồn dưới dạng tệp do chương trình ghi lại; Bảng C.1 liệt kê nội dung từng nhóm.

*Bảng C.1: Kết quả thực nghiệm được lưu.*

| Thực nghiệm | Nội dung |
|---|---|
| Thực nghiệm chính (ba cấu hình) | 36 lượt chạy, điểm chấm, biểu đồ (`experiments/er9`) |
| Cấu hình D (không gọi mô hình) | 12 lượt chạy, điểm chấm, bảng từng câu hỏi, bản đồ nhiệt (`experiments/er9d`) |
| Chạy lại A/B/C trên `gpt-5.6-luna` | 36 lượt chạy, điểm chấm, bảng từng câu hỏi (`experiments/er9-luna`) |
| Độ nhạy của bộ kiểm chứng | 1.210 câu đột biến, kết quả theo loại lỗi, trước (`experiments/mut1`) và sau khi thêm quy tắc, ba bộ hạt (`experiments/mut2`) |
| Mô hình phổ thông không công cụ | Câu trả lời gốc, quy tắc chấm và kết quả (`experiments/e6-pure-llm`) |
| So sánh mô hình | Năm mô hình (ba của OpenAI, hai của DeepSeek); ba lần chạy lặp của `gpt-5.6-luna` |
| Chỉ mục kết quả | Bảng số liệu, lệnh chạy lại và phiên bản mã nguồn của từng thực nghiệm |
