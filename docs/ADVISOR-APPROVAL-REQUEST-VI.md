# Nội dung xin thầy duyệt — phạm vi thử nghiệm và quy tắc dữ liệu thiếu

## Tin nhắn đề xuất gửi thầy

Thưa thầy, sau khi kiểm tra khả năng thu thập và đối chiếu dữ liệu, em đề xuất
chốt phạm vi thử nghiệm trước khi chạy thực nghiệm:

- ACB, TCB, VPB;
- 4 quý năm 2024;
- 4 chỉ số lõi: NPL nhóm 3–5, tỷ lệ bao phủ nợ xấu, ROA và ROE;
- so sánh 3 nhánh: một tác tử, phân cấp không phản biện và phân cấp có phản biện
  giới hạn.

Em xin thầy duyệt thêm quy tắc dữ liệu thiếu: nếu một ô không có số liệu đủ đáng
tin thì không đoán hoặc tự điền; ghi `missing` kèm lý do cụ thể; chỉ dùng nguồn
thay thế nếu đã được duyệt trước; không đưa ô missing vào mẫu số độ chính xác/
trung bình số một cách âm thầm; đồng thời phải báo rõ số ô missing, xung đột và
mẫu số thực tế. Việc tác tử trả lời “chưa đủ dữ liệu” đúng sẽ được đánh giá
riêng, không trộn với độ chính xác của các ô có số.

200 dòng ứng viên hiện chỉ là dữ liệu trung gian/đối chiếu. Sau thử nghiệm 48 ô,
nếu độ phủ nguồn và khối lượng công việc phù hợp, em mới xin mở rộng lên 80 hoặc
200 ô.

Rà soát độc lập và phân xử cho 48 ô thử nghiệm gốc đã hoàn tất. Phần bổ sung độc lập
cho 3 ô ROE ACB Q2--Q4 cũng đã hoàn tất; Gold snapshot v2 đã pass các gate với
44 ô hợp lệ và 4 ô missing có lý do. Em chỉ chạy mô hình thật và so sánh ba nhánh
sau khi thầy chốt phạm vi/mốc chốt và dự án đạt `READY_FOR_BASELINE`.

## Các quyết định cần phản hồi

- [ ] Duyệt thử nghiệm ACB/TCB/VPB × 4 quý 2024 × 4 chỉ số lõi.
- [ ] Duyệt quy tắc dữ liệu thiếu như trên.
- [ ] Duyệt việc giữ 36 ô làm phương án dự phòng có điều kiện.
- [ ] Duyệt việc chỉ mở 80/200 ô sau khi thử nghiệm tạo được Gold và có số liệu
      về khối lượng công việc.
- [ ] Duyệt ba nhánh và các tiêu chí so sánh: độ chính xác, bằng chứng, xử lý
      thiếu/xung đột, độ trễ và chi phí.

## Trạng thái hiện tại cần nói rõ

- Bản chụp ứng viên chính thức: 55 dòng đang chờ + 2 ô thiếu giữ chỗ.
- 48 ô mục tiêu của thử nghiệm đã được lập danh mục; Gold snapshot v2 có 44 ô hợp
  lệ và 4 ô missing có lý do.
- Checker A và Checker B đã rà soát đủ 48/48; phân xử tạo 41 ô được chấp nhận và 7
  ô thiếu có lý do cho thử nghiệm gốc; phần bổ sung ROE ACB `3/3` được chấp nhận và chọn
  trong ledger v2.
- Kiểm tra Gold và cổng đầu vào đường cơ sở đã đạt; thực thi qua nhà cung cấp mô hình
  chưa được chạy.
- Thực thi qua nhà cung cấp mô hình chưa được chạy.

Thầy chưa được xem là đã duyệt cho đến khi có phản hồi lưu được trong project.
