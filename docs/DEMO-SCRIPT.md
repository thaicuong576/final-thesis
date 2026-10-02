# Kịch bản demo sản phẩm (khoảng 10 phút)

Địa chỉ: https://fin-ai.eddiephung.me
Dữ liệu: 10 ngân hàng (ACB, BID, CTG, HDB, MBB, SHB, STB, TCB, VCB, VPB), 10 quý từ quý 1/2024 đến quý 2/2026, 4 chỉ tiêu (nợ xấu, bao phủ nợ xấu, ROA, ROE).

Kịch bản này đã được chạy thử trên bản đang vận hành ngày 02/10/2026. Thời gian ghi bên dưới là thời gian đo được trong lần chạy thử đó.

## Trước khi demo (5 phút)

1. Mở https://fin-ai.eddiephung.me/data trước giờ demo khoảng 2 phút. Máy chủ miễn phí ngủ sau một thời gian không dùng, lần mở đầu có thể mất 30–60 giây.
2. Kiểm tra góc dưới bên trái hiện "BCTC hợp nhất · đã đối chiếu" và "10 ngân hàng · 2024–2026".
3. Tải sẵn tệp mẫu VIB về máy: trên trang Dữ liệu, bấm "Mẫu VIB 2025 hợp lệ".
4. Nếu một lượt phân tích hiện "Mất kết nối", bấm "Thử lại". Lần chạy thử đã gặp tình huống này một lần với câu hỏi xu hướng; chạy lại thì xong sau 66 giây.

## Bước 1. Xem dữ liệu đang có (1 phút)

Mở trang **Dữ liệu**.

Nói:
- Hệ thống chỉ phân tích trên số liệu đã đối chiếu với báo cáo tài chính gốc, tới từng số trang.
- Bảng độ phủ cho thấy 100/100 ô ngân hàng – quý đều đủ bốn chỉ tiêu. Không có ô nào ước tính.
- Phần "Chỉ tiêu và cách tính" ghi rõ công thức. Mô hình ngôn ngữ không tính số; chương trình tính.

## Bước 2. Câu hỏi tra cứu (1 phút)

Vào **Phân tích mới**, gõ:

> Tỷ lệ nợ xấu của VCB quý 4/2024 là bao nhiêu?

Kết quả lần chạy thử: 0,96%, giảm 0,26 điểm % so với quý 3/2024, khoảng 28 giây.

Nói:
- Câu hỏi đơn giản thì báo cáo ngắn: một con số, diễn biến so với quý trước, nguồn.
- Bấm vào số chú thích để thấy nguồn: báo cáo hợp nhất quý 4/2024 của VCB, trang 32, thuyết minh chất lượng nợ.

## Bước 3. Câu hỏi tổng quan một ngân hàng (3 phút)

Gõ:

> Đánh giá sức khỏe tài chính của ACB quý 2/2026 so với nhóm

Lần chạy thử mất khoảng 155 giây, 3 tác tử, 2 vòng phản biện. Trong lúc chờ, chỉ vào màn hình:
- Điều phối viên nhận dạng loại câu hỏi và giao việc cho chuyên viên doanh nghiệp và chuyên viên ngành.
- Mỗi chuyên viên trả về số liệu có nguồn, rồi viết nhận định.
- Bước kiểm tra số liệu đối chiếu từng con số trong câu với dữ liệu gốc.
- Bộ phản biện đọc bản nháp và yêu cầu sửa.

Khi báo cáo mở ra, nói:
- Tiêu đề nêu kết luận. Cột bên phải là tín hiệu so với nhóm theo từng khía cạnh.
- Bảng màu cho thấy thứ hạng của cả 10 ngân hàng ở từng chỉ tiêu.
- Cuối báo cáo, bấm "Xem quá trình phân tích" để thấy bộ phản biện đã yêu cầu sửa gì.

## Bước 4. So sánh hai ngân hàng hoặc xếp hạng (1 phút)

Chọn một trong hai câu, mỗi câu khoảng 60–70 giây:

> So sánh ACB và TCB quý 4/2024

> Ngân hàng nào có tỷ lệ bao phủ nợ xấu cao nhất quý 4/2024?

Nói:
- Báo cáo đổi hình thức theo loại câu hỏi: bảng đối chiếu cho so sánh, biểu đồ thanh cho xếp hạng.
- Với nợ xấu, bên thấp hơn được đánh dấu là tốt hơn. Hệ thống biết chiều của từng chỉ tiêu.

## Bước 5. Thêm một ngân hàng mới (2–3 phút)

Mở lại trang **Dữ liệu**, kéo xuống "Thêm ngân hàng mới từ tệp CSV".

1. Chọn tệp `vib-2025q4.csv` đã tải ở phần chuẩn bị, bấm "Kiểm tra và tải lên".
2. Hệ thống báo đã chấp nhận VIB quý 4/2025 và hiện bốn chỉ tiêu tự tính lại: nợ xấu 2,97%, bao phủ 42,87%, ROA 1,39%, ROE 16,41%.
3. Bấm "Hỏi về VIB", rồi chọn câu gợi ý về sức khỏe tài chính so với nhóm.
4. Báo cáo mất khoảng 3 phút (lần chạy thử: 184 giây). Kết quả lần chạy thử: VIB xếp hạng 11/11 về bao phủ nợ xấu, 9/11 về nợ xấu, 8/11 về ROA và ROE.

Nói:
- VIB không có trong 10 ngân hàng ban đầu. Số liệu lấy từ báo cáo hợp nhất năm 2025 đã kiểm toán.
- Hệ thống không tin con số tỷ lệ trong tệp: nó tính lại từ số liệu gốc và so với số người dùng khai.
- Thứ hạng tính trên 11 ngân hàng (10 ngân hàng trong nhóm cộng VIB).
- VIB được so với trung vị của 10 ngân hàng nhưng không được tính vào trung vị, để một tệp chưa đối soát độc lập không làm lệch chuẩn so sánh.
- Báo cáo ghi rõ đây là dữ liệu do người dùng cung cấp.

Nếu thầy muốn xem trường hợp sai: tải "Mẫu VIB có lỗi (thử nghiệm)". Hệ thống từ chối và chỉ ra dòng sai.

Nếu thầy tải một ngân hàng đã có sẵn (ví dụ CTG): hệ thống từ chối và nhắc hỏi thẳng về ngân hàng đó, vì nếu nhận thì cùng một ngân hàng sẽ có hai bộ số.

## Bước 6. Câu hỏi ngoài phạm vi (30 giây)

Gõ:

> Tỷ lệ nợ xấu của OCB quý 4/2024 là bao nhiêu?

Hệ thống trả lời ngay rằng ngân hàng này chưa có trong dữ liệu và liệt kê các ngân hàng đang có.

Nói:
- Hệ thống từ chối trước khi gọi mô hình ngôn ngữ, nên không có chuyện bịa số.

## Bước 7. Thư viện báo cáo (30 giây)

Mở **Thư viện báo cáo**: mọi lượt hỏi, kể cả lượt bị từ chối, đều được lưu và mở lại được cùng với quá trình phân tích.

## Câu hỏi thầy có thể hỏi

**"Cái này khác gì một dashboard?"**
- Người dùng hỏi bằng tiếng Việt tự nhiên, không chọn bộ lọc.
- Hệ thống tự chọn cách phân tích theo loại câu hỏi và viết nhận định.
- Có một tác tử phản biện đọc lại bản nháp, và mỗi câu chứa con số phải khớp dữ liệu mới được giữ lại.

**"Sao không dùng RAG?"**
- Dữ liệu ở đây là số liệu có cấu trúc. Truy vấn thẳng cho đúng một giá trị kèm trang nguồn.
- Tìm đoạn văn theo độ tương đồng dễ lấy nhầm quý, nhầm ngân hàng, hoặc nhầm báo cáo riêng lẻ với hợp nhất.
- RAG phù hợp cho phần định tính (nhận định của ban điều hành, thuyết minh rủi ro). Đây là hướng phát triển ghi ở Chương 6.

**"Mô hình có bịa số không?"**
- Mô hình không tính và không tự nhớ số. Chương trình tính, mô hình chỉ diễn giải.
- Câu nào chứa con số, thứ hạng hay chiều so sánh không khớp dữ kiện được trích dẫn thì bị loại, và được thay bằng câu mẫu đã kiểm chứng.

**"Dữ liệu lấy ở đâu, ai kiểm tra?"**
- Từ báo cáo tài chính hợp nhất công bố của từng ngân hàng. Mỗi số có trang nguồn và mã băm của đúng tệp PDF.
- Số liệu do công cụ AI đọc và đối chiếu bằng các đẳng thức kế toán (các nhóm nợ cộng đúng tổng, tài sản bằng nợ phải trả cộng vốn chủ). Chưa có người kiểm tra độc lập; đây là hạn chế đã ghi trong luận văn.

**"Kết quả đánh giá A/B/C có dùng bộ dữ liệu 10 ngân hàng này không?"**
- Không. Thực nghiệm ở Chương 5 dùng bộ Gold v5 (5 ngân hàng, năm 2024) được giữ cố định để lặp lại được. Bộ 10 ngân hàng là dữ liệu vận hành cho sản phẩm.

## Điều nên tránh khi demo

- Câu hỏi xu hướng dài hơn bốn quý: hệ thống chỉ nhận từ hai đến bốn kỳ.
- Câu hỏi "vì sao" (nguyên nhân nợ xấu tăng): hệ thống chưa có dữ liệu định tính.
- Hỏi liên tục nhiều câu tổng quan: mỗi câu mất hai đến ba phút.
