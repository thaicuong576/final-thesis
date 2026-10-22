# Bảng so sánh từng câu hỏi qua 4 cấu hình (A, B, C, D)

Bảng tổng hợp chi tiết 10 câu phân tích (T01–T10) và 2 câu kiểm thử từ chối (R1, R2) qua 4 cấu hình:
- **Cấu hình A**: Single-agent (Một tác tử)
- **Cấu hình B**: Hierarchical no critique (Phân tầng không phản biện)
- **Cấu hình C**: Hierarchical with critique (Phân tầng có phản biện)
- **Cấu hình D**: Template-only (Chỉ dùng câu mẫu, không gọi mô hình, 0 token)

| Mã câu | A: Độ phủ | A: Token | A: Thời gian (s) | B: Độ phủ | B: Token | B: Thời gian (s) | C: Độ phủ | C: Token | C: Thời gian (s) | D: Độ phủ | D: Token | D: Thời gian (s) |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| T01 | 0,75 | 4.623 | 26,53 | 0,75 | 11.661 | 44,22 | 0,50 | 85.187 | 114,55 | 0,25 | 0 | 14,95 |
| T02 | 0,75 | 9.279 | 34,06 | 0,50 | 18.953 | 39,42 | 1,00 | 25.474 | 61,75 | 0,25 | 0 | 4,98 |
| T03 | 1,00 | 1.667 | 14,47 | 1,00 | 2.884 | 15,97 | 1,00 | 5.829 | 32,45 | 1,00 | 0 | 0,44 |
| T04 | 0,50 | 4.737 | 17,64 | 1,00 | 11.932 | 39,97 | 0,50 | 32.543 | 99,53 | 0,50 | 0 | 2,76 |
| T05 | 0,50 | 4.632 | 17,38 | 0,50 | 10.641 | 37,64 | 0,75 | 37.638 | 103,89 | 0,50 | 0 | 2,80 |
| T06 | 1,00 | 3.961 | 26,77 | 1,00 | 7.537 | 35,88 | 1,00 | 26.361 | 49,19 | 1,00 | 0 | 5,22 |
| T07 | 1,00 | 3.331 | 16,77 | 1,00 | 6.652 | 26,22 | 1,00 | 27.036 | 52,00 | 1,00 | 0 | 5,25 |
| T08 | 0,31 | 7.549 | 18,94 | 0,38 | 18.373 | 43,02 | 0,12 | 27.895 | 83,33 | 0,38 | 0 | 5,01 |
| T09 | 0,75 | 3.362 | 16,91 | 1,00 | 5.870 | 23,95 | 1,00 | 18.377 | 64,64 | 0,50 | 0 | 2,64 |
| T10 | 1,00 | 2.272 | 18,47 | 1,00 | 4.517 | 21,39 | 0,50 | 23.933 | 91,36 | 1,00 | 0 | 1,31 |

### Các câu hỏi kiểm thử từ chối (Rejection Tasks)

| Mã câu | Nội dung kiểm thử | A: Trạng thái / Token | B: Trạng thái / Token | C: Trạng thái / Token | D: Trạng thái / Token |
| :--- | :--- | :---: | :---: | :---: | :---: |
| R1 | Từ chối kỳ chưa có (2026_Q3 ngoài snapshot) | error (0 tok) | error (0 tok) | error (0 tok) | error (0 tok) |
| R2 | Từ chối thực thể ngoài danh mục (OCB ngoài Top 10) | error (0 tok) | error (0 tok) | error (0 tok) | error (0 tok) |

> **Ghi chú**: Số thập phân sử dụng dấu phẩy (`,`) theo chuẩn trình bày tiếng Việt.
> R1 và R2 được từ chối hợp lệ tại cổng kiểm soát trước khi suy luận ở cả 4 cấu hình.
