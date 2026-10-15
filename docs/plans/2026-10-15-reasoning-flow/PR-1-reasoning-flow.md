# PR-1 — Màn hình phân tích: dòng suy luận theo thời gian (FLOW-1)

Nhánh: `feat/reasoning-flow`. Tiêu đề PR: `feat(ui): [FLOW-1] timeline-style reasoning flow for the analysis screen`.
Marker hoàn thành: `DONE-FLOW1`. Thay thế cách trình bày của AGENT-VIEW-1 (PR #171); dữ liệu và reducer của #171 được tái dùng.

## Vấn đề (QC của người dùng, ảnh chụp màn hình)

Màn hình hiện xếp các hộp có tiêu đề (Kế hoạch phân tích, Lý do chọn kế hoạch, Nhiệm vụ và công cụ đã giao…) và hàng thẻ agent, nhiều hộp chỉ chứa chữ giữ chỗ
("Đang phân tích câu hỏi và lập kế hoạch…", "Đang xác định căn cứ lập kế hoạch…"). Hậu quả: đọc rời rạc, nhiều khoảng trống, thẻ agent tràn xuống hàng thứ hai
có một thẻ lẻ, ba vùng song song (thẻ, khối chi tiết, nhật ký) tranh sự chú ý. Người dùng muốn một **dòng chảy theo thời gian như một cuộc trò chuyện**, không ép
từng phản hồi vào hộp.

## Thiết kế mục tiêu

Một cột duy nhất, đọc từ trên xuống: **"Dòng suy luận"**.

1. **Mỗi mục là một dòng thời gian, không có hộp.** Cột trái hẹp là mốc thời gian `mm:ss` (chữ đơn cách, màu phụ) và một chấm màu theo agent nối bằng đường dọc mảnh.
   Bên phải là phần nội dung ở dạng văn xuôi: tên agent in đậm, rồi câu diễn giải. Không viền hộp, không tiêu đề phần, không mũi tên gập/mở cho nội dung chính.
2. **Giọng văn kể chuyện, tiếng Việt, ngôi thứ nhất của từng agent**, được ghép từ **trường dữ liệu thật** của sự kiện (không bịa suy nghĩ). Ví dụ (mẫu ghép, không hard-code câu):
   - Điều phối viên: "Mình đọc câu hỏi: đây là so sánh đối đầu giữa ACB và TCB, quý 2/2026. Mình sẽ giao cho Chuyên viên doanh nghiệp tra 4 chỉ tiêu." (từ PLAN_CREATED: dạng câu hỏi, thực thể, kỳ, chỉ tiêu, `rationale` nếu có).
   - Chuyên viên: "Đã lấy 22 số liệu có nguồn." rồi **bản nháp nhận định hiện ra ngay tại chỗ, chảy theo từng đoạn** (WRITER_DRAFT_DELTA) dưới dạng khối trích dẫn bên trái có đường kẻ mảnh, kèm con trỏ nhấp nháy khi đang viết.
   - Kiểm tra số liệu: ngay dưới câu nháp, đánh dấu từng câu `✓ khớp dữ kiện` hoặc `✗ bị loại: <lý do>` khi SENTENCE_VERDICT tới; câu bị loại gạch ngang và lý do ngắn bên dưới.
   - Phản biện: "Mình yêu cầu sửa: <vấn đề>." rồi "Đã sửa, kiểm tra lại: …" (REVIEW_FEEDBACK_CREATED, REVISION_*).
   - Kết thúc: một dòng "Báo cáo sẵn sàng" kèm nút **Mở báo cáo**.
3. **Chỉ hiển thị cái đã xảy ra.** Tuyệt đối không có hộp hay dòng giữ chỗ cho bước chưa tới. Cái duy nhất "chưa xong" là **một dòng trực tiếp ở cuối**: chấm nhấp nháy, tên agent đang làm, việc đang làm
   (từ SPECIALIST_ACTIVITY/TOOL_STARTED) và đồng hồ chạy; dòng này thay thế mọi chữ giữ chỗ.
4. **Bản nháp chảy tại chỗ, không nhảy bố cục.** Nội dung mới nối vào cuối mục đang viết; chỉ tự cuộn khi người dùng đang ở cuối. Khi người dùng cuộn lên, hiện một nút nổi nhỏ "Xuống mục mới nhất".
5. **Chi tiết phụ gập gọn ngay trong dòng**, không thành hộp: "Xem số liệu (22)" mở danh sách ngắn các giá trị đã lấy (chỉ tiêu, ngân hàng, kỳ, giá trị, nguồn); "Xem kế hoạch" mở kế hoạch có cấu trúc (dạng câu hỏi, ngân hàng, kỳ, chỉ tiêu). Mặc định gập.
6. **Thanh agent trên cùng thu gọn:** thay hàng thẻ lớn bằng một hàng chip nhỏ (tên agent, chấm trạng thái, số lượng ngắn như "4 nhận định"), nằm một hàng, có thể cuộn ngang trên điện thoại.
   Bấm chip để lọc dòng thời gian theo agent đó (bấm lần nữa để bỏ lọc). Agent không tham gia không hiện. Không còn hàng thẻ thứ hai với thẻ lẻ.
7. **Đầu trang:** tiêu đề câu hỏi, nhãn dạng câu hỏi, đồng hồ, thanh tiến độ 6 giai đoạn mảnh. Nút **Mở báo cáo** ở đầu khi hoàn tất (giữ từ #171) và ở dòng kết thúc.
8. **Bỏ** cột "Nhật ký trao đổi" riêng bên phải và khối chi tiết theo agent bên dưới thẻ: tất cả gộp vào dòng thời gian. Từ chối/lỗi: một mục cuối với lý do bằng văn xuôi và các câu hỏi gợi ý, không hộp đỏ lớn.
9. Phong cách theo `.agent/rules/design/` (màu, chữ, khoảng cách); ưu tiên khoảng trắng dọc đều, một cỡ chữ nội dung, tên agent là nhấn mạnh duy nhất; không gradient, không bóng đổ nặng, không thẻ lồng thẻ.
10. Điện thoại 390 px: một cột, mốc thời gian chuyển lên trên tên agent nếu thiếu chỗ; chip agent cuộn ngang.
11. Truy cập: vùng dòng thời gian là `role="log"` với `aria-live="polite"` (không đọc từng đoạn delta, gom theo câu), nhãn rõ cho nút; tôn trọng `prefers-reduced-motion` (không con trỏ nhấp nháy, không cuộn mượt).

## Ràng buộc

- **Không hiển thị suy nghĩ thô của mô hình** (D-080, `docs/ARCHITECTURAL-GUARDRAILS.md`). Mọi chữ là diễn giải ghép từ trường dữ liệu thật hoặc bản nháp/kết luận đã công bố. Không thêm câu "tôi đang suy nghĩ…" giả.
- Không đổi máy chủ, hợp đồng OpenAPI hay sự kiện. Tái dùng reducer, `useTraceStream` và kiểu dữ liệu của #171; chỉ đổi lớp trình bày và, nếu cần, bộ chọn dữ liệu.
- Giữ nguyên xác thực (`apiFetch`), nút Mở báo cáo và chuỗi "agent" (không "tác tử").
- Chỉ sửa trong `frontend/` và tài liệu của PR.

## Kiểm thử và bằng chứng

- Vitest: reducer thành dòng thời gian từ chuỗi sự kiện có thứ tự (từng phần), không có mục giữ chỗ, dòng "đang làm" thay đúng agent, lọc theo chip, nút "Xuống mục mới nhất", từ chối/lỗi, hoàn tất có CTA.
- Dùng **bản ghi SSE thật** `C:/Users/ASUS/AppData/Local/Temp/orch/sse/real-run-acb-tcb.json` (mảng {t, event, data}; 68 sự kiện, 88 giây) làm nguồn phát lại có độ trễ; và các báo cáo đã lưu `local_B1..B5.json` cho dạng câu hỏi khác.
- Chụp ảnh bằng trình duyệt thật ở 1440 px và 390 px tại ba thời điểm của một lượt phát lại (≈3 s lập kế hoạch, ≈20 s đang viết có bản nháp dở, hoàn tất), và một ảnh từ chối. **Tự xem từng ảnh** và nêu thẳng điểm còn xấu.
- `npm run lint`, `npm test`, `npm run build`; CI xanh.

## Bàn giao

Khối bàn giao thường lệ (Base SHA, Branch, Commit SHA, PR, file đổi, test kèm số thật, hạn chế) rồi dòng cuối đúng `DONE-FLOW1`.
