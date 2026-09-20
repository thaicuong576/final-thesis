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

---

## [LESSON-004] Thiết lập `PYTHONPATH` khi chạy Unittest trên Windows PowerShell

- **Date:** 2026-09-19
- **Scope:** `tests/`, `scripts/`, Auditor & Worker test verification
- **Status:** `ACTIVE` -> Đã đưa vào `04-definition-of-done.md`.

### 1. Context & Symptom
Khi thực thi lệnh test backend trên Windows PowerShell bằng cú pháp inline Unix `PYTHONPATH=src python -m unittest ...`, PowerShell báo lỗi cú pháp hoặc gán biến thất bại, dẫn đến `ModuleNotFoundError: No module named 'thesis_data'` và hàng chục test bị lỗi giả định (false negatives). Tương tự, nếu bọc `powershell -Command "$env:PYTHONPATH='src'..."` trong chuỗi con thì biến môi trường có thể bị mất scope nếu không dùng đúng định dạng.

### 2. Root Cause
PowerShell không hỗ trợ cú pháp gán biến môi trường inline trên cùng dòng như Bash (`VAR=val command`). PowerShell yêu cầu gán biến môi trường thông qua `$env:NAME = "value"` phân tách bằng dấu chấm phẩy `;`.

### 3. Workaround & Permanent Solution
- Lệnh chuẩn xác trên Windows PowerShell là:
  ```powershell
  $env:PYTHONPATH="src"; python -m unittest discover -s tests -q
  ```
- Trên Bash / Linux / macOS:
  ```bash
  PYTHONPATH=src python -m unittest discover -s tests -q
  ```
- Toàn bộ 499 tests backend đều vượt qua (PASS) với 0 failures và 0 errors khi `PYTHONPATH` được cấu hình chính xác.

---

## [LESSON-005] Giới hạn tần suất giám sát Subagent & Tận dụng Reactive Wakeup (Tối thiểu 3 phút / lần)

- **Date:** 2026-09-19
- **Scope:** Lead Orchestrator, `AGENTS.md` (Rule 16), `.agent/roles/lead.md`
- **Status:** `ACTIVE` -> Đã đưa vào `AGENTS.md` và `lead.md`.

### 1. Context & Symptom
Khi điều phối các subagents thực thi song song trong các Git Worktree, Lead Orchestrator có xu hướng chạy liên tục các lệnh đọc log thời gian thực (`Get-Content transcript.jsonl -Tail`) với tần suất dày đặc (vài giây một lần) để theo dõi worker. Việc này gây lãng phí tài nguyên terminal, làm rối loạn output tool call của người dùng và tạo cảm giác spam không cần thiết.

### 2. Root Cause
- Sự sốt ruột của Lead Agent muốn cập nhật trạng thái ngay cho User.
- Chưa tận dụng triệt để kiến trúc sự kiện bất đồng bộ (**Reactive Wakeup**) vốn có của hệ thống AI harness, nơi tiến trình cha sẽ tự động được resume/đánh thức khi subagent hoàn tất hoặc gửi tin nhắn.

### 3. Workaround & Permanent Solution
- **Chế độ mặc định (Reactive Wakeup):** Sau khi dispatch worker qua `invoke_subagent` hoặc gửi chỉ thị qua `send_message`, Lead Agent PHẢI dừng gọi tool để nhường quyền điều khiển, đợi hệ thống tự động wakeup khi worker hoàn thành.
- **Quy tắc Rate-Limit (User-Mandated):** Nếu trong các trường hợp đặc biệt cần theo dõi tiến trình của worker, khoảng thời gian giữa 2 lần kiểm tra BẮT BUỘC phải **ít nhất 3 phút (>= 180 giây)**. Nghiêm cấm mọi hành vi polling dồn dập dưới 3 phút.

---

## [LESSON-006] Windows PowerShell & Linear API UTF-8 Encoding Pitfall (Lỗi vỡ font Tiếng Việt)

- **Date:** 2026-09-20
- **Scope:** Linear MCP / GraphQL API, Windows PowerShell, `scripts/`
- **Status:** `ACTIVE` -> Đã chuẩn hoá script tương tác Linear và cập nhật vào cẩm nang phòng ngừa.

### 1. Context & Symptom
Khi gửi request tạo hoặc cập nhật Linear Issue có nội dung Tiếng Việt có dấu (ví dụ: description hoặc title) thông qua lệnh PowerShell `Invoke-RestMethod` hoặc chạy script Python in console mặc định trên Windows, toàn bộ ký tự Tiếng Việt bị biến thành dấu chấm hỏi `?` hoặc ký tự rác `\ufffd` (ví dụ: `C?p nh?t .agent/roles/lead.md v?i quy trnh qu?n tr? PDLC m?i`).

### 2. Root Cause
- Windows PowerShell 5.1 mặc định encode request body bằng bảng mã ANSI (Windows-1252 / ISO-8859-1) thay vì UTF-8 trừ khi được chỉ định tường minh.
- Console `stdout` của Python trên Windows cũng mặc định dùng `cp1252`, gây lỗi `UnicodeEncodeError` khi in các chuỗi UTF-8 phức tạp ra console.
- Khi gọi `Invoke-RestMethod`, nếu chỉ đặt header `Content-Type: application/json` mà không có `charset=utf-8` hoặc không gửi mảng byte UTF-8 trực tiếp, chuỗi Unicode sẽ bị ép kiểu sang ANSI, làm mất toàn bộ dấu Tiếng Việt.

### 3. Workaround & Permanent Solution
- **Khi dùng Python tương tác Linear GraphQL:**
  - Luôn mã hoá payload rõ ràng bằng `.encode("utf-8")`.
  - Header: `{"Content-Type": "application/json; charset=utf-8", "Authorization": TOKEN}`.
  - Khi in output console trên Windows, set `$env:PYTHONIOENCODING="utf-8"` hoặc serialize an toàn để tránh lỗi cp1252 của console Windows.
- **Khi dùng PowerShell:**
  - Bắt buộc truyền body dưới dạng UTF-8 byte array:
    ```powershell
    $bodyBytes = [System.Text.Encoding]::UTF8.GetBytes($jsonString)
    Invoke-RestMethod -Uri $uri -Method Post -ContentType "application/json; charset=utf-8" -Body $bodyBytes
    ```
- **Khắc phục ngay:** Đã viết script Python chuẩn UTF-8 để cập nhật lại toàn bộ description của ticket `THES-6` trên Linear về đúng tiếng Việt chuẩn chỉnh, sắc nét.

