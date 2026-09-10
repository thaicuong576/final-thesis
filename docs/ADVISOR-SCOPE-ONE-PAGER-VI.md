# Bản một trang xin duyệt phạm vi khóa luận

## Đề xuất ngắn gọn

Xây dựng một prototype phân tích tài chính có truy nguyên nguồn cho ngân hàng
niêm yết Việt Nam, sau đó đánh giá công bằng ba cách tổ chức tác vụ:

1. một tác tử;
2. phân cấp Vĩ mô/Nhóm ngành/Doanh nghiệp không phản biện;
3. phân cấp Vĩ mô/Nhóm ngành/Doanh nghiệp có phản biện giới hạn.

Phần đối sánh chính có thể dùng 13 câu hỏi lõi về ngân hàng (39 lượt chạy qua ba
nhánh); câu hỏi vĩ mô tới ngân hàng được giữ làm phần mở rộng và chỉ tổng hợp khi
có Gold vĩ mô đúng kỳ. Điều này không bỏ tác tử Vĩ mô khỏi prototype, chỉ tránh để
một nguồn vĩ mô chưa hoàn thiện khóa toàn bộ đánh giá kiến trúc.

Mục tiêu không phải chứng minh multi-agent luôn tốt hơn, mà đo xem việc phân rã
và kiểm tra chéo có cải thiện độ đúng, độ đầy đủ bằng chứng và xử lý bất nhất
đủ để bù chi phí/độ trễ hay không.

## Quyết định cần duyệt ngay

Thầy chỉ cần duyệt hợp đồng nghiên cứu và quy tắc cổng phạm vi: dùng thử nghiệm
48 ô để kiểm tra tính khả thi trước, giữ 36 ô làm phương án dự phòng nếu một chỉ
số không thể so sánh, và chỉ mở 80/200 ô sau khi có Gold cùng số liệu về khối lượng
công việc. Không cần duyệt trước một cơ sở dữ liệu 200 ô chưa kiểm chứng hoặc cam
kết rằng đa tác tử sẽ tốt hơn một tác tử.

Quy tắc dữ liệu thiếu đi kèm phạm vi: không đoán, không tự điền, không điền số
0/nội suy âm thầm; ghi `missing` kèm lý do; chỉ dùng phương án dự phòng đã được
duyệt trước; loại missing khỏi mẫu số độ chính xác/trung bình số nhưng phải báo rõ
số ô missing, xung đột và mẫu số thực tế; đánh giá riêng việc tác tử xử lý dữ liệu thiếu.

Sau khi được duyệt, nhóm có thể tiếp tục đối chiếu dữ liệu, dựng kết quả xác định
và viết Chương 1–4 song song. Checker B của thử nghiệm gốc, phần bổ sung ROE,
phân xử và Gold thử nghiệm đều đã xong; đường cơ sở chạy qua nhà cung cấp mô hình
chỉ mở sau khi thầy xác nhận phạm vi/mốc chốt, cấu hình nhà cung cấp/mô hình được
ghi nhận và trạng thái sẵn sàng chuyển thành `READY_FOR_BASELINE`.

## Phạm vi đề nghị

### Giai đoạn khả thi trước

- ACB, TCB, VPB;
- bốn quý năm 2024;
- bốn chỉ số lõi: NPL nhóm 3–5, tỷ lệ bao phủ nợ xấu, ROA, ROE;
- CIR và NIM chỉ đưa vào nếu định nghĩa và nguồn của các ngân hàng khớp nhau.

Đây là thử nghiệm để kiểm tra nền tảng dữ liệu, không phải cam kết cuối cùng về số
lượng ngân hàng.

### Trạng thái dữ liệu tại thời điểm xin duyệt

Bản chụp ứng viên v4 có tuyến chính thức cho thử nghiệm và thêm ba ứng viên ROE ACB
Q2--Q4 với truy nguyên đầu vào/công thức/trang. Phần bổ sung độc lập đã chấp nhận
cả ba; sổ cái v2 và Gold snapshot riêng đã được nâng cấp với `44/48` ô hợp lệ và
`4/48` ô missing có lý do, mỗi chỉ số `11/12`. Một bản PDF Q1 trên máy chủ phụ đã
được phát hiện nhưng không được đưa vào Gold vì không đáp ứng quy tắc truy nguyên
nguồn chính. Vì vậy 48 ô là **phạm vi của thử nghiệm Gold**, không phải tuyên bố
cơ sở dữ liệu mở rộng 200 ô đã đầy đủ.

### Quy tắc mở rộng

- Thử nghiệm đạt: giữ 48 ô cho đường cơ sở đầu tiên; chỉ mở lên 80 ô (5 ngân hàng × 4 quý × 4 chỉ số) nếu khối lượng rà soát đo được là chấp nhận được và thầy muốn mở rộng.
- Thử nghiệm đạt và nguồn mở rộng ổn định: cân nhắc 200 ô (5 ngân hàng × 8 quý × 5 chỉ số).
- Thử nghiệm không đạt: giữ tập lớn nhất có nguồn chính thức và chỉ số có thể so sánh;
  ô thiếu để null kèm lý do, không điền bằng dữ liệu nhà cung cấp.

## Vì sao không cam kết 200 ô ngay

Hiện cơ sở dữ liệu trung gian có 200 dòng ứng viên nhưng chưa có dòng Gold nào được
chấp nhận. Bảy PDF chính thức ACB/VPB đã kiểm tra đều chỉ là bản quét; sau đó tìm được
4 bộ tài liệu tra cứu hồ sơ của VPBank có lớp văn bản và 4 bộ tài liệu hiệu quả có
lớp văn bản, nhưng KPI trên các bộ tài liệu hiệu quả đang là số liệu riêng lẻ
(`RIÊNG LẺ`). TCB có KPI chính thức dạng văn bản nhưng vẫn cần kiểm tra định nghĩa,
cơ sở kỳ và người chấm.
Do đó, số dòng hiện có phản ánh khả năng thu thập, không phản ánh chất lượng
hoặc độ đầy đủ của dữ liệu luận văn.

## Trạng thái dựng song song

Mốc dựng có kiểm soát hiện đã đạt với 200 kiểm thử hồi quy, gồm ranh giới
truy vấn/bằng chứng, chạy lại ngoại tuyến 3 nhánh, ranh giới phản hồi có cấu trúc
từ nhà cung cấp, dựng lời nhắc xác định, truy nguyên bản kê lượt chạy và vị trí
nguồn phục vụ phân xử. Đây là bằng chứng về hạ tầng kết nối; không phải kết quả
tài chính hay so sánh hiệu năng. Rà soát Gold thử nghiệm và phần bổ sung ROE ACB
đã hoàn tất; thực thi qua nhà cung cấp mô hình vẫn chưa chạy.

## Điều kiện để bắt đầu thí nghiệm

- Mỗi giá trị có nguồn, mã băm, vị trí trích dẫn, đơn vị và cơ sở kỳ.
- Mỗi chỉ số có định nghĩa và công thức được duyệt.
- Có ít nhất 40 nhãn chỉ số/bằng chứng được kiểm tra độc lập.
- Các xung đột quan trọng được giải thích hoặc loại khỏi Gold.
- Có bản chụp Gold riêng; dữ liệu trung gian không bị ghi đè.
- Cả ba nhánh dùng cùng bản chụp, câu hỏi, công cụ, mô hình/cấu hình và hợp đồng
  đầu ra.

Trước khi đạt các điều kiện này, nhóm vẫn được phép hoàn thiện tầng truy vấn/bằng
chứng xác định, bộ dữ liệu mô phỏng ngoại tuyến, bản kê lượt chạy, hợp đồng lời
nhắc và viết Chương 1–4. Đường cơ sở chạy qua nhà cung cấp mô hình chỉ bắt đầu sau
`READY_FOR_BASELINE`; phần so sánh lõi đầu tiên gồm 13 câu hỏi tập trung vào ngân
hàng (39 lượt chạy), còn phần vĩ mô là phần mở rộng có điều kiện.

## Nội dung xin thầy xác nhận

1. Thầy có đồng ý hướng “prototype ứng dụng + so sánh có kiểm soát” không?
2. Thầy có đồng ý dùng thử nghiệm 48 ô làm cổng quyết định trước khi mở rộng không?
3. Nếu dữ liệu không đủ cho một chỉ số, thầy có đồng ý loại chỉ số đó và ghi rõ
   giới hạn thay vì dùng số từ nhà cung cấp chưa kiểm chứng không?
4. Thầy có yêu cầu bắt buộc về số ngân hàng, số quý hoặc chỉ số nào không?
5. Thầy có đồng ý tách phần vĩ mô tới ngân hàng thành phần mở rộng có điều kiện,
   trong khi đối sánh chính vẫn so sánh ba nhánh trên các câu hỏi ngân hàng/nhóm
   ngành/bằng chứng không?

## Cam kết về kết quả

Kết quả “đa tác tử không cải thiện” vẫn là kết quả hợp lệ. Luận văn sẽ báo
cả độ đúng, bằng chứng, lỗi hợp đồng, độ trễ, số lần gọi và chi phí; không dùng
độ trôi chảy của văn bản làm tiêu chí chính.
