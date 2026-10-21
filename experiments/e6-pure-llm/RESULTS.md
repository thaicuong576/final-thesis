# E6: mô hình ngôn ngữ phổ thông, không công cụ, không dữ liệu (cấu hình "LLM thuần")

Chạy bằng `run.py` cùng thư mục; câu trả lời gốc ở `answers.jsonl`.

- Mô hình: `gpt-5.6-luna` (OpenAI, qua cổng API của dự án), một lần cho mỗi câu, không bật tìm kiếm web, không công cụ, không dữ liệu, không bộ kiểm chứng. Cấu hình sinh mặc định của nhà cung cấp.
- Ngày hỏi: 2026-10-21. 10 câu phân tích T01–T10 đúng nguyên văn Bảng 3.4. Tổng 14.060 token.
- Đối chiếu với bộ dữ liệu đã khóa `bank-quarterly-top10-operational-v1-r4` (mười ngân hàng).

## Quy tắc chấm (đặt trước khi chấm)
- Mỗi con số hoặc khoảng số mô hình nêu cho một ngân hàng, kỳ, chỉ tiêu có trong bộ dữ liệu là một "số được nêu". Chấm **đúng** nếu giá trị đã khóa nằm trong khoảng mô hình nêu, hoặc (với số đơn) lệch không quá 5% giá trị đã khóa; ngược lại **sai**. Số về chỉ tiêu hay ngân hàng không có trong bộ dữ liệu là **không kiểm được**.
- Khẳng định định tính (ví dụ "VCB thường có chất lượng tài sản tốt hơn") không đếm vào số được nêu.
- Câu xếp hạng (T06, T07): thứ hạng có khớp bộ dữ liệu không. "Nguồn kiểm được": câu trả lời có nêu tài liệu, trang hoặc đường dẫn mà người đọc kiểm được không.

## Kết quả theo câu

| Câu | Số được nêu | Đúng | Sai | Không kiểm được | Ghi chú đối chiếu (giá trị đã khóa) |
|---|:---:|:---:|:---:|:---:|---|
| T01 BID so với nhóm | 0 | 0 | 0 | 0 | Nói chung chung, không có số, nói chưa có số liệu quý 2/2026 |
| T02 STB quý 4/2025 | 0 | 0 | 0 | 0 | Không có số; bộ dữ liệu: nợ xấu 6,41%, bao phủ 49,97%, ROA 0,71% |
| T03 bao phủ HDB quý 1/2026 | 1 | 0 | 1 | 0 | Nêu "khoảng 70%"; đã khóa 50,0% |
| T04 xu hướng CTG 2025 | 5 | 4 | 1 | 0 | Đúng: nợ xấu cuối 2024 ~1,2% (1,25), cuối 2025 1,1–1,3% (1,10), bao phủ cuối 2024 ~170% (170,75), giữa năm 120–140% (136,82; 134,76). Sai: nợ xấu nửa đầu 2025 "1,4–1,6%" (1,55 rồi 1,31) |
| T05 ROA, ROE của SHB 2025 | 8 | 1 | 7 | 0 | ROA đã khóa 1,25; 1,39; 1,48; 1,46: nêu 1,4; 1,5; 1,5–1,6; 1,6 (đúng chỉ quý 3). ROE đã khóa 16,08; 18,04; 19,12; 18,95: nêu 21–22; 22–23; 23–24; 24 (cả bốn sai, lệch 4–6 điểm phần trăm) |
| T06 nợ xấu thấp nhất quý 2/2026 | 1 | 0 | 0 | 1 | Nêu BAB (~0,3%), ngân hàng ngoài bộ dữ liệu, không kiểm được; trong mười ngân hàng, đã khóa là VCB 0,61% |
| T07 xếp hạng ROE quý 4/2025 | 0 | 0 | 0 | 0 | Từ chối đưa thứ hạng, nêu công thức và xin dữ liệu |
| T08 VPB 2025 | 0 | 0 | 0 | 0 | Toàn định tính |
| T09 MBB so với TCB | 0 | 0 | 0 | 0 | Nói không có dữ liệu quý 2/2026, so sánh định tính |
| T10 VCB hay CTG | 4 | 3 | 1 | 0 | Kết luận VCB tốt hơn: đúng. Đúng: VCB nợ xấu dưới 1% (0,58), VCB bao phủ trên 200% (258,29), CTG nợ xấu 1,1–1,3% (1,10). Sai: CTG bao phủ "170–180%" (158,83) |
| **Tổng** | **19** | **8 (42,1%)** | **10 (52,6%)** | **1 (5,3%)** | |

- Thứ hạng: T06 không khớp (nêu ngân hàng ngoài bộ dữ liệu); T07 không đưa thứ hạng; chỉ có kết luận so sánh T10 đúng.
- Nguồn kiểm được: 0/10 câu trả lời nêu tài liệu, trang hay đường dẫn.
- 5/10 câu trả lời (T01, T02, T07, T08, T09) không nêu con số nào; ở T01, T07, T09 mô hình tự nói chưa có số liệu.

## Giới hạn
Một lần chạy, một mô hình, không bật tìm kiếm web; bản thân kết quả không đại diện cho mọi chatbot phổ thông (một chatbot có tìm kiếm web hoặc tải tệp có thể tốt hơn). Chấm bằng tay theo quy tắc trên bởi người thiết kế thực nghiệm. Chỉ mang tính minh họa. Điều đáng chú ý không phải mô hình sai hết (8/19 số đúng, kể cả một số khá chính xác) mà là người dùng không có cách nào phân biệt số đúng với số sai và không có nguồn để kiểm.
