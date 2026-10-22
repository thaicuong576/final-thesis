# Bảng so sánh từng câu hỏi qua 4 cấu hình (A, B, C, D)

Bảng tổng hợp chi tiết 10 câu phân tích (T01–T10) và 2 câu kiểm thử từ chối (R1, R2) qua 4 cấu hình:
- **Cấu hình A**: Single-agent (Một tác tử)
- **Cấu hình B**: Hierarchical no critique (Phân tầng không phản biện)
- **Cấu hình C**: Hierarchical with critique (Phân tầng có phản biện)
- **Cấu hình D**: Template-only (Chỉ dùng câu mẫu, không gọi mô hình, 0 token)

| Mã câu | A: Độ phủ | A: Token | A: Thời gian (s) | B: Độ phủ | B: Token | B: Thời gian (s) | C: Độ phủ | C: Token | C: Thời gian (s) | D: Độ phủ | D: Token | D: Thời gian (s) |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| T01 | 1,00 | 5.997 | 18,11 | 1,00 | 15.057 | 49,97 | 0,75 | 100.009 | 150,78 | 0,25 | 0 | 5,98 |
| T02 | 1,00 | 10.360 | 21,89 | 1,00 | 21.750 | 39,75 | 1,00 | 46.932 | 96,39 | 0,25 | 0 | 2,30 |
| T03 | 1,00 | 1.994 | 4,86 | 1,00 | 3.506 | 13,90 | 1,00 | 7.311 | 19,30 | 1,00 | 0 | 0,27 |
| T04 | 0,75 | 7.250 | 31,17 | 0,75 | 14.395 | 40,83 | 0,75 | 69.481 | 217,42 | 0,50 | 0 | 1,26 |
| T05 | 0,75 | 5.547 | 17,58 | 1,00 | 11.644 | 26,69 | 1,00 | 25.505 | 74,23 | 0,50 | 0 | 1,25 |
| T06 | 1,00 | 4.431 | 12,64 | 1,00 | 7.279 | 12,56 | 1,00 | 69.543 | 96,62 | 1,00 | 0 | 2,23 |
| T07 | 1,00 | 4.954 | 16,38 | 1,00 | 10.270 | 36,89 | 1,00 | 51.541 | 90,76 | 1,00 | 0 | 2,45 |
| T08 | 0,62 | 11.081 | 37,23 | 0,38 | 21.965 | 52,58 | 0,62 | 50.341 | 140,00 | 0,38 | 0 | 2,38 |
| T09 | 1,00 | 5.624 | 24,19 | 1,00 | 8.012 | 24,84 | 1,00 | 40.321 | 100,05 | 0,50 | 0 | 1,49 |
| T10 | 1,00 | 4.285 | 19,88 | 1,00 | 7.653 | 39,70 | 1,00 | 14.404 | 46,05 | 1,00 | 0 | 0,67 |

### Các câu hỏi kiểm thử từ chối (Rejection Tasks)

| Mã câu | Nội dung kiểm thử | A: Trạng thái / Token | B: Trạng thái / Token | C: Trạng thái / Token | D: Trạng thái / Token |
| :--- | :--- | :---: | :---: | :---: | :---: |
| R1 | Từ chối kỳ chưa có (2026_Q3 ngoài snapshot) | error (0 tok) | error (0 tok) | error (0 tok) | error (0 tok) |
| R2 | Từ chối thực thể ngoài danh mục (OCB ngoài Top 10) | error (0 tok) | error (0 tok) | error (0 tok) | error (0 tok) |

> **Ghi chú**: Số thập phân sử dụng dấu phẩy (`,`) theo chuẩn trình bày tiếng Việt.
> R1 và R2 được từ chối hợp lệ tại cổng kiểm soát trước khi suy luận ở cả 4 cấu hình.
