# Kịch bản trình diễn 5 phút

## 0:00–0:30 — Bài toán

“Em xây dựng một hệ thống mẫu để phân tích nhóm ngân hàng dựa trên nguồn có
truy nguyên. Câu hỏi không chỉ là mô hình viết hay, mà là mỗi con số có đúng
kỳ, đúng định nghĩa và có nguồn hay không. Em cũng đo xem khi khối lượng công
việc lớn hơn thì đa tác tử có đáng dùng hơn một tác tử hay không.”

## 0:30–1:10 — Đầu vào

Mở giao diện báo cáo xem trước. Chỉ vào phần phạm vi: ACB, TCB, VPB, MBB, VCB;
bốn quý năm 2024; NPL, tỷ lệ bao phủ, ROA, ROE. Nói rõ đây là bản chụp Gold đã
đóng băng, không phải quá trình thu thập trực tiếp. Có 80 ô mục tiêu, trong đó
76 ô hợp lệ và 4 ô thiếu có lý do.

## 1:10–2:00 — Đầu ra người dùng đọc được

Chỉ vào kết luận chính: “TCB dẫn đầu ROA và MBB dẫn đầu ROE; VPB là điểm bất
thường về rủi ro tín dụng; VCB có đệm tín dụng tốt nhất.” Sau đó chỉ vào bảng
quý 4 để cho thấy nhận định có thể kiểm tra bằng số cụ thể, không dừng ở đoạn
văn tổng quát.

## 2:00–2:50 — Bằng chứng và giới hạn

Mở một nhận định, ví dụ VPB có NPL quý 4 cao nhất. Chỉ vào giá trị, kỳ, vị trí
nguồn và mã bằng chứng. Nói: “Giao diện không tự tạo bằng chứng. Nó đọc bằng
chứng đã được gắn sẵn trong hợp đồng báo cáo.” Mở phần giới hạn: 4 ô thiếu vẫn
là thiếu; một phần bằng chứng là ghi chú tính toán đã rà soát; PDF bản quét/văn
bản hỗn hợp vẫn còn hạn chế.

## 2:50–3:40 — Quy trình tác tử

Chuyển sang trang kiến trúc. Giải thích tầng dữ liệu tính số và giữ dấu vết
nguồn; tầng bằng chứng lấy đoạn thông tin theo ngân hàng/kỳ; tầng tác tử có
nhánh một tác tử hoặc các vai trò vĩ mô/ngành/doanh nghiệp; bộ điều phối kiểm
tra rồi mới tổng hợp. Phản biện chỉ có tối đa hai lần xác minh và không tự biến
tín hiệu thành mâu thuẫn.

## 3:40–4:30 — Kết quả so sánh

Mở trang kết quả. Nói: “Em lập 75 lượt chạy dự kiến. 61 lượt hoàn tất, 14 lượt
thất bại và em không thay bằng đầu ra giả. Chấm mù có 244 dòng.” Chỉ vào điểm
chuyển lợi thế ở 3 ngân hàng: đa tác tử phân cấp không phản biện tăng chất lượng
**+0,05**, nhưng chi phí bằng **2,622757 lần** và độ trễ bằng **1,698339 lần**
một tác tử. Nhánh phản biện giới hạn chưa đạt điểm chuyển lợi thế.

## 4:30–5:00 — Kết luận và xin ý kiến

“Kết luận của em có điều kiện: câu hỏi nhỏ dùng một tác tử; báo cáo nhiều ngân
hàng và cần nhiều góc nhìn có thể dùng đa tác tử phân cấp không phản biện; phản
biện nên bật khi có bất thường và đủ ngân sách. Em xin thầy xác nhận phạm vi này
đủ làm kết quả chính, sau đó em hoàn thiện văn phong và chạy một lượt kiểm tra
độ bền, giữ nguyên Gold, bộ câu hỏi, mô hình và tiêu chí.”

## Nếu thầy hỏi về ứng dụng

“Giao diện hiện là bản xem trước chỉ đọc để chứng minh luồng đầu vào → xử lý →
đầu ra và khả năng truy nguyên bằng chứng. Em cố ý không làm đăng nhập, dữ liệu
thời gian thực hay máy chủ vận hành vì các phần đó không giúp trả lời câu hỏi
nghiên cứu hiện tại.”
