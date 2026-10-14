# PR-1 — Màn hình agent: hiển thị diễn giải của từng agent và nút mở báo cáo (AGENT-VIEW-1)

Nhánh: `feat/agent-view`. Tiêu đề PR: `feat(ui): [AGENT-VIEW-1] per-agent explanations and report call-to-action`.
Marker hoàn thành: `DONE-AGENTVIEW1`.

## Bối cảnh (ảnh chụp màn hình do người dùng cung cấp)

Màn hình phân tích (`/analysis?q=...`) hiện có hàng thẻ agent, khối chi tiết của agent đang chọn ở dưới bên trái
("Điều phối viên: Kế hoạch phân tích") và "Nhật ký trao đổi" bên phải. Ba vấn đề cần sửa:

1. Khối chi tiết bên trái chỉ có kế hoạch của Điều phối viên; các agent còn lại (Chuyên viên ngành, Chuyên viên doanh nghiệp, Phản biện)
   gần như trống, nên thầy cô không thấy agent đã làm và nghĩ gì. Cần hiển thị **diễn giải của từng agent** ngay dưới thẻ/ở khối chi tiết bên trái.
2. Từ "tác tử" trên giao diện phải đổi thành **"agent"**.
3. Khi lượt chạy hoàn tất không có nút nào rõ ràng để mở báo cáo. Cần một nút **"Mở báo cáo"** nổi bật.

## Ràng buộc (BẮT BUỘC)

- **Không hiển thị chuỗi suy nghĩ thô của mô hình** (chain-of-thought, scratchpad, lời nhắc hệ thống). `docs/ARCHITECTURAL-GUARDRAILS.md`
  (quanh dòng 264) và D-080 cấm điều này. "Diễn giải" ở đây là **đầu ra có cấu trúc đã được công bố** của mỗi agent: lý do chọn kế hoạch
  (`rationale`), công cụ đã gọi và số liệu trả về, bản nháp nhận định của chuyên viên, kết luận của bộ kiểm tra số liệu từng câu, vấn đề và yêu cầu sửa của
  Phản biện, quyết định chấp nhận hay loại câu. Không thêm sự kiện máy chủ mới nào nếu các sự kiện hiện có (SSE-1) đã đủ; chỉ trình bày lại.
  Nếu một thông tin muốn hiển thị chưa có trong sự kiện hiện có thì ghi lại là hạn chế, không tự bịa nội dung.
- Mọi chữ hiển thị là kết quả thật của lượt chạy, không viết sẵn câu "suy nghĩ" giả. Trạng thái chưa có dữ liệu thì ghi rõ "chưa có".
- Tuân thủ `.agent/rules/design/`. Không đổi phía máy chủ, hợp đồng OpenAPI, hay luồng sự kiện.
- Giữ nguyên hành vi xác thực (token, `apiFetch`). Chỉ sửa trong `frontend/`.

## Yêu cầu

1. **Khối chi tiết theo agent (bên trái, dưới hàng thẻ):** khi chọn một agent (mặc định agent đang làm hoặc agent cuối), hiển thị:
   - Điều phối viên: dạng câu hỏi, kế hoạch (ngân hàng, chỉ tiêu, kỳ), lý do chọn kế hoạch, các công cụ đã giao.
   - Chuyên viên (ngành, doanh nghiệp, …): các phép phân tích đã chạy kèm số liệu trả về; các nhận định đã viết (bản nháp) kèm trạng thái
     từng câu (đạt/loại và lý do ngắn); số liệu có nguồn.
   - Kiểm tra số liệu: số câu đã kiểm, số khớp, các câu bị loại và lý do.
   - Phản biện: từng vòng, các vấn đề đã nêu (loại, mức độ, yêu cầu sửa) và kết quả sau sửa.
   Bố cục dạng các mục có tiêu đề rõ ràng, có thể gập/mở, đọc được trong 5 giây. Không cuộn dài một khối chữ.
2. **Thẻ agent ở hàng trên:** thêm một dòng tóm tắt ngắn do dữ liệu thật tạo ra (ví dụ "Viết 4 nhận định, 1 bị loại") dưới trạng thái của thẻ.
3. **Đổi tên:** thay "tác tử" bằng "agent" trong mọi chuỗi giao diện (tiêu đề "Luồng xử lý giữa các agent", "Nhấn vào agent để xem chi tiết", v.v.),
   kể cả test và nhãn truy cập. Giữ tên riêng các agent hiện có ("Điều phối viên", "Chuyên viên ngành"...) nếu chưa có quyết định đổi.
4. **Nút "Mở báo cáo":** khi lượt chạy hoàn tất (có báo cáo), hiển thị nút chính, nổi bật ở phần đầu khối tiêu đề của màn hình (cạnh trạng thái "Đã hoàn tất"),
   và lặp lại ở cuối "Nhật ký trao đổi" nếu hợp lý. Bấm mở báo cáo tương ứng (`/reports/<id>`). Lượt bị từ chối hoặc lỗi thì không hiện.
   Nếu hiện giờ có tự chuyển sang báo cáo thì giữ hành vi đó; chỉ thêm nút, không đổi luồng.
5. Trạng thái đang chạy: hiển thị tiến triển trực tiếp trong khối chi tiết khi dữ liệu về, không nhấp nháy hay đổi vị trí gây khó đọc.

## Kiểm thử

Vitest cho: khối chi tiết từng loại agent với dữ liệu mẫu (có và không có dữ liệu), tóm tắt trên thẻ, nút "Mở báo cáo" (hiện khi hoàn tất, ẩn khi từ chối/lỗi),
chuỗi "agent" và không còn "tác tử" trong thành phần của màn hình này. Chạy `npm run lint`, `npm test`, `npm run build` trong `frontend/`.
Chụp ảnh màn hình (đang chạy, hoàn tất, từ chối) bằng trình duyệt thật bằng dữ liệu đã lưu và kiểm tra bằng mắt rằng không còn vùng trống lớn.

## Ngoài phạm vi

Không hiển thị suy nghĩ thô của mô hình. Không đổi máy chủ. Không đổi chương luận văn. Không tạo release, tag hay bình luận thử.

## Bàn giao

Đẩy nhánh, mở PR, chờ `gh pr checks` xanh, rồi kết thúc bằng khối bàn giao (Base SHA, Branch, Commit SHA, PR, file đổi, test kèm số thật, lỗi đã biết, hạn chế
về dữ liệu chưa có) và dòng cuối đúng `DONE-AGENTVIEW1`.
