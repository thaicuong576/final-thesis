# PR-2 — Cổng đăng nhập: giao diện (AUTH-2)

Nhánh: `feat/auth-ui`. Tiêu đề PR: `feat(ui): [AUTH-2] login page and session handling`.
Marker hoàn thành: `DONE-AUTH2`. Phụ thuộc: PR-1 (AUTH-1) đã merge.

## Mục tiêu

Một trang đăng nhập bên ngoài ứng dụng, dùng thông tin đăng nhập chung do PR-1 kiểm tra. Mọi route còn lại chỉ vào được sau khi
đăng nhập. Phải tuân thủ `.agent/rules/design/` (bố cục, màu, chữ, trạng thái). Toàn bộ chữ tiếng Việt.

## Yêu cầu

1. Route `/login` nằm ngoài khung ứng dụng (không có thanh bên). Trường tên đăng nhập, mật khẩu (có nút hiện/ẩn), nút "Đăng nhập";
   trạng thái đang gửi, lỗi sai thông tin (thông báo chung), lỗi quá nhiều lần (429), lỗi mất kết nối. Hỗ trợ bàn phím và nhãn truy cập.
2. Khi vào ứng dụng, gọi `GET /api/auth/status`. Nếu `required=false` (chạy cục bộ, CI) thì **bỏ qua đăng nhập** và hành vi như cũ.
3. Token lưu trong `sessionStorage` kèm thời điểm hết hạn, bọc trong try/catch (có thể bị chặn); không lưu mật khẩu; không ghi token ra console.
4. Bảo vệ route: chưa đăng nhập thì chuyển tới `/login` và quay lại đúng trang cũ sau khi đăng nhập.
5. Mọi lời gọi `/api/*` (kể cả `fetch` luồng `/api/analyze/stream`) tự gắn `Authorization: Bearer`. Một nơi duy nhất (lớp API client),
   không rải từng nơi. Liên kết tải tệp mẫu vẫn là liên kết thường (đường công khai).
6. Gặp `401` bất kỳ: xóa token, chuyển về `/login` với thông báo "Phiên đã hết hạn, vui lòng đăng nhập lại".
7. Nút "Đăng xuất" ở chân thanh bên (thay vùng tên người dùng cố định nếu hợp lý); sau khi đăng xuất xóa token và về `/login`.
8. Không đổi bố cục các trang hiện có ngoài chân thanh bên. Không gọi API ngoài `/api/auth/*` khi chưa có token.

## Kiểm thử

Vitest: màn hình đăng nhập (đúng, sai, 429, offline), guard chuyển hướng, gắn header, xử lý 401, bỏ qua khi `required=false`, đăng xuất.
Chạy `npm run lint`, `npm test`, `npm run build` trong `frontend/` và chụp hai ảnh (đăng nhập, lỗi) bằng trình duyệt thật để kiểm tra bằng mắt.

## Ngoài phạm vi

Không làm Google/OAuth, không tạo tài khoản, không quản lý người dùng, không đổi phía máy chủ. Không đặt thông tin đăng nhập thật ở đâu cả.

## Bàn giao

Như PR-1; dòng cuối đúng `DONE-AUTH2`.
