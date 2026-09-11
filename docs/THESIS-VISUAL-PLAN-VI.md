# Kế hoạch bổ sung bảng và hình cho bản khóa luận

## Mục tiêu

Bổ sung trực tiếp vào bản Word hiện tại các bảng có thể chỉnh sửa, sơ đồ đơn sắc do GPT Image Gen tạo và ảnh chụp ứng dụng thật. Mỗi hình/bảng có số thứ tự theo chương, chú thích nguồn và đoạn văn dẫn giải đúng vị trí. Giữ Times New Roman 13, nội dung căn đều, giãn dòng 1,5, không bìa/header/footer. Giữ lại bản Word trước khi bổ sung.

## Danh mục dự kiến

1. Bảng 3.1: Phạm vi và độ đầy đủ Gold theo ngân hàng, từ snapshot v5.
2. Hình 4.1: Kiến trúc dữ liệu, công cụ, tác tử và báo cáo. Sơ đồ GPT Image Gen đen trắng, phân biệt chuẩn bị dữ liệu với chạy phân tích.
3. Bảng 4.1: Vai trò và phạm vi công cụ trong luồng composite hiện tại. Không đưa Macro Agent vào phạm vi thực nghiệm ngân hàng.
4. Hình 4.2: Ba nhánh thực nghiệm và bước kiểm chứng giới hạn. Sơ đồ GPT Image Gen đen trắng, không mặc định một tác tử chỉ gọi API một lần hoặc mọi worker chạy song song.
5. Hình 5.1: Ảnh màn hình tổng quan/so sánh của ứng dụng local, ghi rõ đây là báo cáo đóng băng và giao diện chỉ đọc.
6. Hình 5.2: Ảnh mở nhận định và dấu vết bằng chứng, chụp giao diện local read-only thật, không dùng ảnh AI để giả làm screenshot.
7. Bảng 6.1: Chất lượng trung bình theo 1–5 ngân hàng và ba nhánh, trên công việc hoàn thành.
8. Bảng 6.2: Số công việc hoàn thành trên năm lượt của từng cấu hình.
9. Bảng 6.3: Chi phí, độ trễ và token ở ba ngân hàng, đọc cùng tỷ lệ hoàn thành. Không diễn giải chi phí ước tính là hóa đơn đầy đủ.

Nếu ảnh chụp quá dày để đọc khi đặt trong trang Word, ưu tiên chụp vùng giao diện liên quan với kích thước đủ lớn. Không thêm ảnh chỉ để trang trí và không thay đổi giao diện nhằm tạo ảnh khác với sản phẩm thực tế.

## Thứ tự thực hiện và kiểm chứng

Đối chiếu mã và kết quả đóng băng → chốt nội dung hình/bảng → tạo sơ đồ và chụp ứng dụng → kiểm tra chữ, mũi tên và nguồn → bổ sung đoạn dẫn và dựng Word → xuất ảnh từng trang → kiểm tra toàn bộ trang, bảng, chú thích và dữ liệu → ghi handoff và cập nhật project state.

Nguồn chính: `src/thesis_data/composite_runner.py`, `src/thesis_data/agent_tools.py`, `docs/OUTPUT-CONTRACT-V2.md`, `reports/analysis-report-v2-final-evaluation-gold-v5-20260909-v4/final-evaluation.md`, `legacy/frozen-report-viewer/data/analysis-report.json` và snapshot Gold v5. Source artifact của giao diện local read-only hiện được archive tại `legacy/frozen-report-viewer/`; lịch sử Hình 5.1 và 5.2 vẫn là screenshot chụp từ giao diện đó, không phải từ React frontend mới.

## Trạng thái khởi đầu

Bản trước có 7 chương, 25 trang, chưa có hình/bảng. Đã kiểm tra ứng dụng local hoạt động. Browser-use CLI không có, dùng trình duyệt/công cụ chụp sẵn có. Skill documents yêu cầu kiểm tra trang sau render. Công cụ render đóng gói trước đó thiếu LibreOffice, có phương án Word COM được giới hạn ở tài liệu tác vụ.

Ngưỡng usage là dưới 20% còn lại của cửa sổ 5 giờ thì chuyển model task sang gpt-5.6-luna với thinking Medium theo lựa chọn mới nhất của người dùng. Lúc bắt đầu goal còn 99%; trong quá trình thực hiện công cụ đọc usage bị mất kết nối nên không xác nhận được ngưỡng mới. Không dùng reset credit.

## Kết quả thực hiện ngày 10 tháng 9 năm 2026

Đã chèn đủ 5 bảng native có thể chỉnh sửa và 4 hình vào `docs/THESIS-DRAFT-VI.docx`. Hai sơ đồ kiến trúc/luồng do GPT Image Gen tạo theo phong cách đơn sắc, rõ nét; hai ảnh còn lại là ảnh chụp trực tiếp giao diện local ở trạng thái chỉ đọc. Bản Word cuối có 33 trang. Kiểm tra cấu trúc xác nhận 5 bảng, 4 hình, Times New Roman 13, nội dung gốc được giữ theo thứ tự, không có header/footer hoặc viền trang. Bản PDF do Word xuất được raster hóa và kiểm tra toàn bộ 33 trang: không có hình bị cắt, hàng bảng bị tách giữa trang, hoặc chú thích không đi cùng đối tượng. Handoff chi tiết nằm tại `.agents/handoffs/2026-09-10-thesis-visuals-word.md`.
