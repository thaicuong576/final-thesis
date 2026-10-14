# PR-1 — Cổng đăng nhập: phần máy chủ (AUTH-1)

Nhánh: `feat/auth-api`. Tiêu đề PR: `feat(api): [AUTH-1] shared-credential login gate for the analysis API`.
Marker hoàn thành: `DONE-AUTH1`.

## Mục tiêu và ràng buộc

Rào toàn bộ API bằng **một tài khoản và mật khẩu cố định** (một người dùng chung, không phân quyền, không đổi
cấu trúc lưu trữ). Mục đích là tránh bị gọi bừa tốn token, không phải quản lý nhiều người dùng.

- Chỉ ở **tầng ứng dụng** (`src/thesis_api`). Không đụng `src/thesis_data`, không đổi snapshot, không đổi
  `analysis_runs`. `docs/ARCHITECTURAL-GUARDRAILS.md` xếp "authentication and deployment concerns" vào tầng ứng dụng.
- **Bí mật không bao giờ vào repo, log, ảnh chụp, test hay thông báo lỗi.** Test dùng giá trị giả sinh ngay trong test.
- Mặc định **tắt** (`AUTH_ENABLED=false`) để CI, chạy cục bộ và các script đánh giá không đổi hành vi. Khi bật mà thiếu
  cấu hình thì **từ chối khởi động** (fail closed), không âm thầm chạy mở.

## Cấu hình (settings.py, biến môi trường)

| Biến | Ý nghĩa |
|---|---|
| `AUTH_ENABLED` | `true` để bật cổng; mặc định `false` |
| `APP_LOGIN_USER` | tên đăng nhập cố định |
| `APP_LOGIN_PASSWORD` | mật khẩu cố định (`SecretStr`) |
| `AUTH_TOKEN_SECRET` | khóa ký token (`SecretStr`, tối thiểu 32 ký tự) |
| `AUTH_TOKEN_TTL_HOURS` | thời hạn token, mặc định 12 |

Khi `AUTH_ENABLED=true` mà thiếu hoặc yếu bất kỳ biến bắt buộc nào, ứng dụng ném lỗi cấu hình lúc khởi động
và `/api/ready` không bao giờ xanh. Chỉ công bố trạng thái `auth_required: true|false`, không bao giờ công bố giá trị.

## Hành vi

1. `GET /api/auth/status` (công khai) trả `{"required": bool}`.
2. `POST /api/auth/login` (công khai) nhận `{"username","password"}` và trả `200 {"access_token","token_type":"bearer","expires_at"}`.
   - So sánh bằng `hmac.compare_digest` cho cả tên và mật khẩu, không cho biết cái nào sai.
   - Sai: `401` với thông báo tiếng Việt chung, mã `invalid_credentials`.
   - Giới hạn tần suất theo IP trong bộ nhớ: tối đa 5 lần sai trong 60 giây, sau đó `429` (`too_many_attempts`).
3. Token không trạng thái, ký HMAC-SHA256 bằng thư viện chuẩn (không thêm phụ thuộc mới), gồm thời điểm hết hạn;
   kiểm tra chữ ký bằng so sánh thời gian hằng và kiểm tra hết hạn.
4. Khi bật cổng, mọi đường `/api/*` yêu cầu `Authorization: Bearer <token>`, **trừ** các đường công khai:
   `/api/version`, `/api/ready`, `/api/auth/status`, `/api/auth/login`, `/api/onboarding/samples/*`
   (tệp mẫu tổng hợp, tải qua liên kết thường) và mọi yêu cầu `OPTIONS` (CORS preflight). Thiếu hoặc sai token:
   `401` `{"detail": ..., "code": "auth_required"}`, kể cả với `/api/analyze/stream`.
   `/api/version` và `/api/ready` phải công khai vì Render và cron-job.org gọi chúng.
5. Một điểm chặn duy nhất (middleware hoặc dependency toàn cục), không rải kiểm tra từng endpoint.
6. Không đổi hợp đồng của các endpoint hiện có ngoài việc thêm phản hồi `401` và sơ đồ bảo mật.

## Hợp đồng và tài liệu

- Cập nhật `contracts/openapi.json`: thêm `components.securitySchemes.bearerAuth`, hai endpoint `/api/auth/*`, phản hồi 401/429.
  Chạy `python scripts/check_openapi_contract.py` cho tới khi PASS.
- `docs/DECISIONS.md`: thêm quyết định kế tiếp (lý do: kiểm soát chi phí token cho bản demo, một thông tin đăng nhập chung,
  không phân quyền; giới hạn: không có người dùng riêng, không thu hồi từng token, giới hạn tần suất theo bộ nhớ một tiến trình).
- `AGENTS.md`: ghi cờ cấu hình và các đường công khai vào mục hợp đồng API công khai; `.agent/memory/lessons-learned.md` nếu có điều bất ngờ.

## Kiểm thử (unittest, ngoại tuyến)

Đăng nhập đúng/sai; giới hạn tần suất; token giả mạo, hết hạn; mọi nhóm đường được bảo vệ trả 401 khi không có token và
hành vi cũ khi có; đường công khai không cần token; `AUTH_ENABLED=false` không đổi hành vi; bật mà thiếu cấu hình thì
khởi động lỗi; không có chuỗi mật khẩu hay token trong log (bắt log và kiểm tra). Chạy toàn bộ
`PYTHONPATH=src python -m unittest discover -s tests -q` (chậm khoảng 5 phút; chạy các file liên quan trước).

## Ngoài phạm vi

- Không làm giao diện (PR-2). Không đặt giá trị bí mật thật ở bất cứ đâu; người dùng tự đặt biến môi trường trên Render.
- Không đổi phân quyền dữ liệu, lịch sử lượt chạy hay thư mục tải lên.
- Không tạo release, tag hay bình luận thử trên GitHub.

## Bàn giao

Đẩy nhánh, mở PR, chờ `gh pr checks` xanh hoàn toàn rồi kết thúc bằng khối bàn giao (Base SHA, Branch, Commit SHA, PR,
file đổi, test kèm số thật, lỗi đã biết, trạng thái cây làm việc) và dòng cuối đúng `DONE-AUTH1`.
