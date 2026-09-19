# Lessons Learned & Knowledge Base

> Kho tri thức tích lũy từ các sự cố, bug thực tế và bài học kinh nghiệm trong quá trình phát triển hệ thống Multi-Agent SDLC.

---

## [LESSON-001] Windows Filesystem Junctions & Hardlinks trong Git Worktree

- **Date:** 2026-09-19
- **Scope:** `scripts/worker-start.ps1`, `scripts/worker-start.sh`
- **Status:** `GRADUATED` -> Đã đưa vào scripts khởi tạo worktree và `guardrails.md` (Mục 6).

### 1. Context & Symptom
Khi khởi tạo Git Worktree trên hệ điều hành Windows, việc copy toàn bộ `frontend/node_modules` (hàng chục nghìn file) gây chậm chạp nghiêm trọng và lãng phí dung lượng ổ đĩa. Đồng thời, nếu dùng `Copy-Item` cho file `.env`, các thay đổi biến môi trường ở root không thể tự động phản ánh vào worktree. Ngoài ra, lệnh `mklink` thông thường (Symlink) trên Windows yêu cầu quyền Administrator hoặc Developer Mode, gây lỗi Permission Denied cho lập trình viên.

### 2. Root Cause
- Windows NTFS xử lý symlink với ràng buộc bảo mật (SeCreateSymbolicLinkPrivilege).
- Duplicate dependencies và configs phá vỡ nguyên lý single-source-of-truth cho runtime context.

### 3. Workaround & Permanent Solution
- **Thư mục (`frontend/node_modules`):** Dùng Directory Junction (`cmd /c mklink /J`). Junction không yêu cầu quyền Admin, trỏ trực tiếp trong bảng phân vùng NTFS.
- **Tập tin cấu hình (`.env`):** Dùng NTFS Hardlink (`cmd /c mklink /H`). Cả root và worktree đều trỏ chung một MFT inode/file record, thay đổi ở một bên lập tức phản ánh sang bên kia mà không cần Admin. Cung cấp fallback `Copy-Item` nếu tạo link thất bại.

---

## [LESSON-002] SQLite WAL Mode & Xử lý Null/Chia cho 0 trong `ratio_observations`

- **Date:** 2026-09-19
- **Scope:** `data/processed/finance_master_v2.sqlite`, `src/thesis_data/`
- **Status:** `GRADUATED` -> Đã cấu hình WAL pragma trên DB và đưa vào `guardrails.md` (Mục 5).

### 1. Context & Symptom
- Nhiều tiến trình Worker (Data, API, Test Suite) cùng đọc/ghi file SQLite dẫn đến lỗi `sqlite3.OperationalError: database is locked`.
- Trong tính toán các chỉ số CAMEL (CIR, NIM, LDR, ROE...), các quý có mẫu số bằng 0 (ví dụ: Tổng thu nhập hoạt động TOI âm hoặc bằng 0, Vốn chủ sở hữu âm hoặc 0) dẫn đến ngoại lệ `ZeroDivisionError` hoặc sinh ra giá trị `NaN`/`Infinity` không hợp lệ trong SQLite.

### 2. Root Cause
- SQLite mặc định sử dụng cơ chế Rollback Journal, khóa toàn bộ database khi có bất kỳ tiến trình nào thực hiện ghi.
- Các ngân hàng gặp khó khăn tài chính hoặc giai đoạn tái cơ cấu có thể có vốn chủ sở hữu âm hoặc thu nhập thuần âm, khiến các công thức tỷ lệ tài chính bị lỗi số học.

### 3. Workaround & Permanent Solution
- **Cơ chế đồng thời:** Bật chế độ `PRAGMA journal_mode=WAL;` (Write-Ahead Logging). Đọc và ghi không chặn lẫn nhau. Đặt `timeout=30.0` và bọc kết nối trong context manager.
- **Xử lý số học:** Mọi phép tính tỷ lệ tài chính bắt buộc kiểm tra mẫu số: nếu `denominator is None or denominator <= 0`, trả về `None` (hoặc `NULL` trong SQLite), tuyệt đối không để văng `ZeroDivisionError` hoặc lưu giá trị rác.

---

## [LESSON-003] Tên Database Chuẩn: `finance_master_v2.sqlite` (Không Phải `camel.db`)

- **Date:** 2026-09-19
- **Scope:** `data/processed/`, `contracts/schema.sql`, `scripts/`
- **Status:** `GRADUATED` -> Đã chuẩn hóa toàn bộ scripts, guardrails và contracts trỏ về `finance_master_v2.sqlite`.

### 1. Context & Symptom
Các prompt ban đầu hoặc tài liệu cũ tham chiếu tới database dưới tên giả định `camel.db` hoặc `data/finance.db`. Khi worker chạy script tìm kiếm file này thì báo lỗi file not found hoặc sinh ra file rỗng làm sai lệch kết quả phân tích.

### 2. Root Cause
Dữ liệu vàng đã được trích xuất, chuẩn hóa và kiểm thử thực tế của luận văn được lưu tại `data/processed/finance_master_v2.sqlite` (chứa đầy đủ các bảng `financial_observations`, `ratio_observations`, `macro_observations`, `source_records`). Tên `camel.db` chỉ là tên minh họa trong ý tưởng ban đầu.

### 3. Workaround & Permanent Solution
- Tên file duy nhất và chuẩn hóa của tầng dữ liệu là: `data/processed/finance_master_v2.sqlite`.
- Toàn bộ DDL schema được dump trực tiếp từ file này vào `contracts/schema.sql`.
- Mọi worker, test suite và bootstrap scripts bắt buộc chỉ sử dụng đường dẫn: `data/processed/finance_master_v2.sqlite`.
