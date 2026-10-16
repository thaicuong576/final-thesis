# Kế hoạch Đơn giản hóa & Tinh gọn Quy trình Nhập Báo cáo Tài chính PDF (UI-POLISH-1)

## 1. Kết quả kiểm tra hiện trạng (Before Audit)

Bộ ảnh chụp trước khi tinh gọn (`before_*` tại 1440px và 390px):
- `before_01_upload_step_1440.png` & `_390.png`: Quá nhiều khối đóng khung, banner "Phạm vi v1", mô tả dài dòng, cụm nút chọn mẫu cồng kềnh, radio button dạng card to chiếm diện tích.
- `before_02_processing_1440.png` & `_390.png`: Vẫn mang disc số bước, viền nặng.
- `before_03_extracted_clean_1440.png` & `_390.png`: Bảng trích xuất quá nhiều badge lặp đi lặp lại trên từng ô/dòng (nhãn OCR, trạng thái ứng viên, viền lồng nhau).
- `before_04_editing_row_1440.png` & `_390.png`: Hộp sửa số liệu nằm trong card lồng nhau.
- `before_05_rejected_errors_1440.png` & `_390.png`: Khối kiểm tra vi phạm dùng nhiều hộp đỏ/vàng chiếm chỗ thay vì danh sách phân cấp gọn gàng.
- `before_06_confirmed_result_1440.png` & `_390.png`: Kết quả nhập có các box lồng nhau, nút hành động chưa đủ nổi bật và tối giản.
- `before_07_failed_ocr_1440.png` & `_390.png`: Trạng thái lỗi OCR viền nặng, chưa theo phong cách tối giản "quiet, confident, readable".

---

## 2. Kế hoạch tinh giản chi tiết (What will be removed & simplified)

### Mục 1: Upload Step tối giản
- **Loại bỏ**:
  - Banner "Phạm vi v1" (`border border-amber-border/40 bg-surface-secondary/60...`).
  - Đoạn văn mô tả dài dòng; giữ lại đúng 1 câu ngắn gọn dưới tiêu đề.
  - Cụm nút radio card lớn (`grid-cols-2` nặng nề) chọn hợp nhất/riêng lẻ; thay bằng segmented control nhỏ gọn.
  - Cụm nút mẫu cồng kềnh; chuyển thành đường dẫn văn bản nhỏ `hoặc dùng bộ mẫu` nằm ngay dưới dropzone.
- **Giữ lại & Tinh chỉnh**:
  - 1 khu vực thả tệp (dropzone) viền nét đứt thanh mảnh, 1 dòng hướng dẫn duy nhất: "Chọn hoặc kéo thả PDF báo cáo tài chính năm".
  - 3 trường nhập liệu trên 1 hàng phẳng (desktop): Mã ngân hàng, Năm tài chính, Phạm vi (Hợp nhất / Riêng lẻ).

### Mục 2: Luồng các bước (Steps flow)
- **Loại bỏ**:
  - Các hình tròn đánh số bước (`span rounded-full ... 1, 2, 3...`) và tiêu đề "Bước 1", "Bước 2", "Bước 3" cồng kềnh.
  - Các thẻ section card lồng nhau.
  - Không render các bước tương lai chưa kích hoạt.
- **Áp dụng**:
  - Luồng dọc tối giản: Bước đã hoàn thành thu gọn thành 1 dòng phẳng có biểu tượng tích xanh nhẹ nhàng (`CheckCircle2`).
  - Bước hiện tại hiển thị nội dung trực tiếp.
  - Bỏ hàng chip chỉ trang báo cáo không cần thiết trừ khi mang thông tin điều hướng chính.

### Mục 3: Bảng trích xuất dòng số liệu (Extracted Rows Table)
- **Loại bỏ**:
  - Toàn bộ badge lặp lại trên từng ô/dòng (như badge trạng thái "Chờ duyệt", nhãn OCR trên từng dòng).
  - Tên nhà cung cấp OCR được đưa về 1 dòng chú thích nhỏ ở đầu/chân bảng.
  - Biểu tượng sửa (Edit) luôn hiện lộ liễu; chuyển thành icon gọn gàng hiển thị rõ nét hơn khi hover/focus.
- **Giữ lại & Tinh chỉnh**:
  - 1 bảng phẳng sạch sẽ trên desktop / danh sách phẳng trên 390px.
  - Mỗi dòng: Tên chỉ tiêu, 2 giá trị số (Kỳ này & Kỳ trước), liên kết trang nhỏ gọn, chỉ hiển thị dấu cảnh báo khi số liệu KHÔNG hợp lệ.
  - Số liệu căn phải, sử dụng font mono (`tabular-nums`), định dạng số Việt Nam.
  - Đảm bảo đầy đủ phím tắt, checkbox xác nhận, menu phương án thay thế, bộ xem trang (PageImageViewer).

### Mục 4: Khối kiểm tra hợp lệ (Validation Block)
- **Loại bỏ**:
  - Các khối hộp viền đỏ/vàng dày đặc.
- **Áp dụng**:
  - Danh sách gọn gàng: Lỗi chặn (blocking errors) hiển thị trước bằng chữ đỏ trên nền trong suốt, cảnh báo (warnings) hiển thị sau.
  - Tóm tắt trạng thái đúng 1 câu duy nhất.
  - Nút bấm xác nhận nhập số liệu hiển thị trạng thái rõ ràng, dứt khoát.

### Mục 5: Kết quả xác nhận (Confirmed Result)
- **Loại bỏ**:
  - Các hộp lồng nhau (nested card boxes).
- **Áp dụng**:
  - Giữ 4 chỉ tiêu cốt lõi với typography rõ ràng, nhẹ nhàng, số liệu căn chỉnh chuẩn.
  - 1 nút hành động chính duy nhất: "Hỏi về <MÃ>".

### Mục 6: Chuẩn mực thiết kế & Tránh lỗi
- Tuân thủ thiết kế `.agent/rules/design/README.md`.
- Tối đa 2 độ dày chữ (regular & semibold), không chữ in đậm tràn lan.
- Không để lộ snake_case, ID kỹ thuật, từ "tác tử", hoặc emoji.
- Đảm bảo 0 overflow ngang ở 390px.

---

## 3. Đánh giá Sau Thực hiện (After Audit & Verification)

Toàn bộ 14 ảnh chụp màn hình sau tinh gọn (`after_*` tại 1440px và 390px) đã được chụp và lưu tại `docs/plans/2026-10-16-filing-ingest/after-shots/`:
1. `after_01_upload_step_1440.png` & `_390.png`: Dropzone 1 dòng tinh gọn, không còn banner v1, 3 trường thông tin bố trí phẳng, segmented control tối giản, 0 horizontal scroll trên mobile.
2. `after_02_processing_1440.png` & `_390.png`: Bước 1 thu gọn thành 1 dòng xác nhận phẳng với nút đổi tệp; thanh tiến trình thanh mảnh hiển thị % rõ ràng.
3. `after_03_extracted_clean_1440.png` & `_390.png`: Loại bỏ hoàn toàn 20 badge "Đã duyệt" lặp lại; bảng phẳng, số liệu căn phải font mono `tabular-nums`; dòng chỉ số trang inline thanh lịch; xác nhận qua checkbox tự nhiên.
4. `after_04_editing_row_1440.png` & `_390.png`: Hộp nhập liệu trực tiếp tại ô với nút Lưu/Hủy siêu gọn, không còn card lồng card.
5. `after_05_rejected_errors_1440.png` & `_390.png`: Tóm tắt 1 câu, danh sách lỗi phân cấp sạch sẽ (lỗi chặn chữ đỏ trên nền trong suốt, cảnh báo chữ vàng), loại bỏ toàn bộ các hộp đỏ cảnh báo cồng kềnh.
6. `after_06_confirmed_result_1440.png` & `_390.png`: Bảng 4 chỉ tiêu cốt lõi phẳng, chữ "Khớp" xanh lá nhẹ nhàng thay cho badge dày; nút hành động duy nhất "Hỏi về ACB ->".
7. `after_07_failed_ocr_1440.png` & `_390.png`: Trạng thái lỗi OCR tối giản, nút thử lại và nút dùng mẫu rõ ràng, tự tin.

### Bổ sung về ngôn ngữ & vai trò:
- Chuyển toàn bộ đại từ ngôi thứ nhất trong dòng suy luận (`timeline.ts`) sang văn phong phân tích tài chính trung tính, khách quan:
  - `Mình đọc câu hỏi: đây là ...` -> `Hệ thống xác định câu hỏi thuộc dạng ...`
  - `Mình giao việc cho chuyên viên ...` -> `Giao chuyên viên ... tra cứu ...`
  - `Mình yêu cầu sửa (vòng 1): ...` -> `Yêu cầu hiệu chỉnh (vòng 1): ...`
- Chuẩn hóa vai trò người dùng nhìn thấy trong log phân tích và chip agent:
  - `Company` -> `Chuyên viên doanh nghiệp`
  - `Sector` -> `Chuyên viên ngành`
  - `Macro` -> `Chuyên viên vĩ mô`
- Thay thế triệt để cụm từ `so sánh đối đầu` thành `so sánh trực diện` trên toàn bộ giao diện, nhãn, prose, chip và tiêu đề.

### Kết quả kiểm thử:
- Unit tests frontend: 33/33 files passed, 299/299 tests passed (100%).
- Lint: 0 errors, 0 warnings (`npm run lint` clean).
- Build: `npm run build` (`tsc -b && vite build`) thành công trong 3.92s.

