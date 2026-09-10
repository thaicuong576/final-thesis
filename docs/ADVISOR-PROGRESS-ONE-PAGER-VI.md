# Tóm tắt tiến độ khóa luận — bản gửi thầy

## Đề tài

**Thiết kế và đánh giá hệ thống mẫu phân tích tài chính dựa trên nguồn dữ liệu
có truy nguyên bằng kiến trúc một tác tử và đa tác tử phân cấp.**

## Vấn đề

Một báo cáo phân tích ngân hàng không chỉ cần trả lời bằng văn bản. Báo cáo cần
giữ đúng kỳ báo cáo, định nghĩa chỉ số, nguồn chứng minh, dữ liệu thiếu/mâu
thuẫn và khả năng kiểm tra lại. Khi câu hỏi mở rộng từ một ngân hàng sang nhiều
ngân hàng, nhiều quý và nhiều góc nhìn, cần kiểm tra xem việc phân rã thành
nhiều tác tử có thực sự đáng để đổi lấy chi phí và độ trễ hay không.

## Câu hỏi nghiên cứu

Trên cùng bản chụp dữ liệu, câu hỏi, chính sách nguồn, mô hình và hợp đồng đầu
ra, quy trình đa tác tử phân cấp theo các góc nhìn vĩ mô/ngành/doanh nghiệp có
cải thiện chất lượng báo cáo đủ để bù thêm độ trễ, token, số lần gọi mô hình và
chi phí so với một tác tử hay không? Nếu có, điểm chuyển lợi thế xuất hiện ở
khối lượng công việc nào?

## Dữ liệu và hệ thống

- 5 ngân hàng: ACB, TCB, VPB, MBB, VCB.
- 4 quý năm 2024 và 4 chỉ số: NPL nhóm 3–5, tỷ lệ bao phủ nợ xấu, ROA, ROE.
- 80 ô mục tiêu: 76 ô hợp lệ, 4 ô thiếu có lý do.
- 76/76 quan sát hợp lệ có bằng chứng theo trang đã được rà soát; tổng cộng 116
  đoạn bằng chứng.
- Mã nguồn tính chỉ số, kỳ, thống kê nhóm so sánh và tín hiệu bất thường.
- Tác tử truy xuất, giải thích, phản biện và tổng hợp từ ngữ cảnh được giới hạn.
- Đầu ra có nhận định, bằng chứng, giới hạn, chất lượng dữ liệu và số liệu vận
  hành.

## Thiết kế so sánh

| Nhánh | Cách xử lý |
|---|---|
| Một tác tử | Một tác tử nhận cùng thông tin/bằng chứng và tạo báo cáo |
| Đa tác tử phân cấp, không phản biện | Các vai trò vĩ mô/ngành/doanh nghiệp chạy rồi được điều phối tổng hợp |
| Đa tác tử phân cấp, phản biện giới hạn | Như nhánh trên, có thêm kiểm tra theo tín hiệu và tối đa 2 lần xác minh |

Toàn bộ thang đo có 75 bản ghi chạy dự kiến theo 5 mức số lượng ngân hàng, 3
nhánh và 5 lần lặp. Có 61 báo cáo hoàn tất, 14 lượt thất bại và đều được giữ
trong số liệu vận hành. Chấm mù được thực hiện trên 61 đầu ra, tổng cộng 244
dòng, theo bốn chiều: tính đúng, tính hữu ích, bằng chứng và giới hạn.

## Kết quả chính

Đa tác tử phân cấp không phản biện có điểm chuyển lợi thế đầu tiên ở **3 ngân
hàng** trong khối lượng công việc đã đăng ký:

- mức tăng chất lượng đã chuẩn hóa: **+0,05**;
- số lần lặp cho kết quả dương: **3/5**;
- chi phí so với một tác tử: **2,622757 lần**;
- độ trễ so với một tác tử: **1,698339 lần**;
- tỷ lệ thất bại của hai nhánh trong cặp so sánh: **0%**.

Đây là điểm chuyển lợi thế quan sát được trong giao thức cố định, không phải
định luật đa tác tử luôn tốt hơn. Ở 1–2 ngân hàng, lợi ích chưa rõ. Ở 4–5 ngân
hàng, các đầu ra hoàn tất của nhánh phân cấp có điểm cao nhưng tỷ lệ thất bại
làm phép so sánh chưa đầy đủ. Nhánh phản biện giới hạn chưa đạt điểm chuyển
lợi thế.

## Ý nghĩa ứng dụng

Một tác tử phù hợp với câu hỏi nhỏ vì rẻ và nhanh. Đa tác tử phân cấp không phản
biện là ứng viên cho báo cáo nhiều ngân hàng cần nhiều góc nhìn độc lập. Phản
biện nên được bật có điều kiện khi có bất thường và còn đủ ngân sách ngữ cảnh/
chi phí. Sản phẩm mẫu chỉ đọc báo cáo đã tạo, cho phép mở chi tiết nhận định và
bằng chứng, đồng thời hiển thị giới hạn; giao diện không tự tính chỉ số hoặc gọi
mô hình.

## Giới hạn cần thầy xác nhận

Phạm vi hiện tại còn nhỏ, chỉ có 4 quý và 4 chỉ số. Có 14/75 lượt gọi mô hình
thất bại, gồm 9 lỗi giới hạn ngữ cảnh, 2 lỗi lược đồ/kiểm tra hợp lệ và 3 lỗi
kết nối API. Chi phí và độ trễ phụ thuộc `gpt-5.6-luna` cùng hạ tầng tại thời
điểm chạy. Một phần bằng chứng là ghi chú tính toán đã được rà soát thay vì
trích dẫn nguyên văn; PDF dạng bản quét/văn bản hỗn hợp vẫn là hạn chế. Mở rộng
8 quý, 200 ô, dữ liệu vĩ mô hoặc ngành chứng khoán chỉ là hướng phát triển sau
khi rà soát nguồn và được duyệt phạm vi.

## Xin ý kiến thầy trong buổi gặp

1. Chấp nhận phạm vi hiện tại làm kết quả chính của hệ thống mẫu ứng dụng.
2. Chấp nhận cách diễn đạt điểm chuyển lợi thế có điều kiện, kèm thất bại và
   đánh đổi.
3. Cho phép hoàn thiện văn phong báo cáo/giao diện và chạy thêm một lượt kiểm tra
   độ bền sau buổi gặp.

Tài liệu tổng hợp nằm tại `docs/ADVISOR-ARTIFACT-INDEX-VI.md`.
