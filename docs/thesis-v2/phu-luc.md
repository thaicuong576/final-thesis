# PHỤ LỤC

## Phụ lục A. Sản phẩm trực tuyến

**Địa chỉ:** https://fin-ai.eddiephung.me

**Đăng nhập:** tên đăng nhập `[ĐIỀN]`, mật khẩu `[ĐIỀN]`. Tài khoản này chỉ dùng cho bản trình bày của khóa luận.

Lần mở đầu tiên có thể mất khoảng một phút vì máy chủ miễn phí cần khởi động lại sau thời gian nghỉ; các lần sau phản hồi bình thường.

*Bảng A.1: Các thao tác thử nhanh.*

| Thao tác | Cách làm | Kết quả mong đợi |
|---|---|---|
| Tra cứu một con số | Nhập "Tỷ lệ nợ xấu của ACB quý 2/2026 là bao nhiêu?" | Thẻ trả lời kèm số trang báo cáo gốc |
| Xếp hạng | Nhập "Ngân hàng nào có tỷ lệ bao phủ nợ xấu cao nhất quý 2/2026?" | Báo cáo xếp hạng mười ngân hàng |
| Xu hướng | Nhập "ROE của BID thay đổi thế nào trong năm 2026?" | Biểu đồ theo quý so với trung vị nhóm |
| So sánh | Nhập "So sánh ACB và CTG quý 2/2026" | Bảng đối chiếu từng chỉ tiêu |
| Từ chối | Nhập câu hỏi về ngân hàng hoặc kỳ chưa có, hoặc yêu cầu không phải phân tích | Thông báo kèm dữ liệu hiện có |
| Thêm ngân hàng | Trang Dữ liệu, chọn "Mẫu VIB 2025 hợp lệ", bấm "Kiểm tra và tải lên", rồi "Hỏi về VIB" | Báo cáo có ghi chú số liệu do người dùng cung cấp |

## Phụ lục B. Bộ dữ liệu

Bộ dữ liệu vận hành mười ngân hàng niêm yết lớn nhất (ACB, BID, CTG, HDB, MBB, SHB, STB, TCB, VCB, VPB), mười quý từ
quý 1/2024 đến quý 2/2026. Số liệu đầu vào được đọc từ báo cáo tài chính hợp nhất của từng ngân hàng; mỗi dòng ghi trang nguồn,
đường dẫn tới tệp báo cáo và mã băm SHA-256 của tệp đó. Bốn chỉ tiêu (tỷ lệ nợ xấu, tỷ lệ bao phủ nợ xấu, ROA, ROE) được tính lại từ
các số liệu này bằng công thức có phiên bản, cho 400 giá trị.

**Tệp số liệu đầu vào:** `inputs.csv`, 1.123 dòng, tải tại `[ĐIỀN: LIÊN KẾT TẢI]`.

**Mã băm SHA-256 của tệp:** `365b433be1a160d6867aa321e2bc0bd4bc69a418dfaa82e4898cedefb82d92fe`.

*Bảng B.1: Các cột của tệp số liệu đầu vào.*

| Cột | Ý nghĩa |
|---|---|
| `entity_id` | Mã ngân hàng |
| `metric_id` | Mã số liệu đầu vào (10 loại: dư nợ cho vay, nợ nhóm 3, 4, 5, dự phòng, tổng tài sản, vốn chủ sở hữu, lợi ích cổ đông không kiểm soát, lợi nhuận sau thuế, lợi nhuận thuộc cổ đông ngân hàng mẹ) |
| `period_id` | Kỳ báo cáo (ví dụ `2025_Q4`) |
| `value`, `unit` | Giá trị và đơn vị (tỷ đồng) |
| `period_basis` | Cách tính kỳ (số dư cuối kỳ hoặc lũy kế từ đầu năm) |
| `source_locator` | Trang, mục và dòng của số liệu trong báo cáo gốc |
| `source_url`, `source_sha256` | Đường dẫn và mã băm của tệp báo cáo gốc |

Hai lưu ý để đối chiếu với Chương 5. Thứ nhất, bản triển khai đang chạy dùng phiên bản dựng `r4` (mã băm tệp
`2a18845feb8dddd83ace39a4ea56fc5d5fbe4a3cb0fcccdfce374a48627f560a`); tệp số liệu đầu vào ở trên tương ứng bản dựng `r5`, chỉ khác ở nhãn đọc
của các dòng lợi nhuận STB và không đổi giá trị nào. Thứ hai, thực nghiệm so sánh A/B/C ở Chương 5 chạy trên bản dựng `r4`.

## Phụ lục C. Mã nguồn và kết quả thực nghiệm

Mã nguồn nằm trong một kho riêng tư; bản chụp ứng với khóa luận là commit `[ĐIỀN: MÃ COMMIT]`, cung cấp theo yêu cầu.
Các thư mục chính:

*Bảng C.1: Kết quả thực nghiệm lưu cùng mã nguồn.*

| Thực nghiệm | Thư mục | Nội dung |
|---|---|---|
| A/B/C (ER-9) | `experiments/er9` | 36 lượt chạy, điểm chấm, biểu đồ |
| E1 – đột biến bộ kiểm chứng | `experiments/mut1` | 1.210 câu đột biến, kết quả theo loại lỗi |
| E2 – nhiều mô hình | `experiments/e2`, `experiments/e2r` | Ba mô hình OpenAI; ba lần chạy lại của `gpt-5.6-luna` |
| E3 – đối kháng | `experiments/e3` | Trước và sau khi thêm cổng phạm vi |
| E5 – số hóa | `experiments/e5`, `scripts/e5_*.py` | Mã và kết quả đo |
| Chỉ mục kết quả | `experiments/RESULTS-INDEX.md` | Bảng số liệu, lệnh chạy lại và phiên bản mã nguồn của từng thực nghiệm |
