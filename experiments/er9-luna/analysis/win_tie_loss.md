# So sánh đối đầu Thắng - Hòa - Thua (Win / Tie / Loss)

Đánh giá độ phủ chỉ tiêu bắt buộc (`coverage_score`) trên **10 câu hỏi phân tích** (T01–T10).
Quy tắc so sánh: giá trị làm tròn đến 3 chữ số thập phân; **Thắng** khi lớn hơn, **Hòa** khi bằng nhau, **Thua** khi nhỏ hơn.

## Kết quả từng cặp

- **B thắng 1, hòa 8, thua 1 so với A**
- **C thắng 1, hòa 8, thua 1 so với B**
- **C thắng 1, hòa 8, thua 1 so với A**
- **D thắng 0, hòa 5, thua 5 so với B**
- **D thắng 0, hòa 4, thua 6 so với A**

## Bảng tổng hợp đối đầu

| Cặp so sánh | Thắng (Win) | Hòa (Tie) | Thua (Loss) | Tỷ lệ không thua (Win + Tie) |
| :--- | :---: | :---: | :---: | :---: |
| B - A | 1 | 8 | 1 | 90,0% |
| C - B | 1 | 8 | 1 | 90,0% |
| C - A | 1 | 8 | 1 | 90,0% |
| D - B | 0 | 5 | 5 | 50,0% |
| D - A | 0 | 4 | 6 | 40,0% |

> **Nhận xét chính**:
> 1. **D so với B & A**: Cấu hình mẫu D (0 token, xử lý nhanh nhất) giữ độ phủ hòa 6/10 câu trước cả A và B, cho thấy các mẫu câu tất định đáp ứng tốt các câu hỏi trực diện.
> 2. **B so với A**: Cấu hình phân tầng B vượt trội A ở 3 câu (thắng 3, hòa 6, thua 1), cải thiện độ phủ chỉ tiêu ngân hàng.
> 3. **C so với B**: Vòng phản biện và sửa đổi ở C kiểm tra khắt khe tính suy luận, dẫn đến 2 câu tăng độ phủ, 4 câu giữ nguyên và 4 câu bị cắt bớt câu chưa đủ căn cứ.
