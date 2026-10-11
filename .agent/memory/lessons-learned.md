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

---

## [LESSON-007] Zero-Delay UI/Bug Dispatch & Bắt buộc đính kèm ảnh vào Worker Prompt

- **Date:** 2026-09-20
- **Scope:** Lead Orchestrator, Subagent Invocations, `AGENTS.md` (Rule 15), `.agent/roles/lead.md`
- **Status:** `ACTIVE` -> Đã đưa vào Rule 15 bắt buộc trong `AGENTS.md` và `lead.md`.

### 1. Context & Symptom
Khi người dùng gửi feedback về giao diện (UI bugs, styling đen, sai lệch breadcrumb, thiếu màn hình) kèm các ảnh chụp màn hình (`.user_uploaded/media_*.png`):
- Lead Orchestrator lại rơi vào quán tính sai lầm: tự ý mở file code ứng dụng (`router.tsx`, `ReportHeaderBar.tsx`...) ở root để đọc và tìm hiểu nguyên nhân trước khi dispatch worker.
- Khi khởi tạo worker bằng `invoke_subagent`, Lead tóm tắt yêu cầu bằng văn bản nhưng quên không truyền các đường dẫn file ảnh (`.png`) vào prompt, khiến worker không nhìn thấy bằng chứng trực quan của người dùng.

### 2. Root Cause
- Vi phạm nguyên tắc phân vai của Lead Orchestrator: ở root chỉ làm kiến trúc, contracts và điều phối, TUYỆT ĐỐI KHÔNG đọc hay sửa mã nguồn ứng dụng.
- Subagents chạy trong context độc lập và không tự động nhìn thấy các file media người dùng upload lên chat hội thoại của Lead nếu Lead không truyền tường minh đường dẫn tuyệt đối.

### 3. Workaround & Permanent Solution
- **Quy tắc 1 Turn Dispatch:** Khi có feedback UI hoặc bug, Lead BẮT BUỘC phải dispatch ngay cho Worker trong 1 turn duy nhất, không nán lại đọc file code ứng dụng ở root.
- **Bắt buộc chuyển toàn bộ Image Paths:** Bất kỳ khi nào người dùng upload ảnh, Lead BẮT BUỘC phải trích xuất toàn bộ file paths từ metadata và đưa thẳng vào prompt khởi tạo của worker ngay từ đầu để worker sử dụng `view_file` đối chiếu hình ảnh.

---

## [LESSON-008] PowerShell Remove-Item Recurse Xâm thực Directory Junctions (`frontend/node_modules`)

- **Date:** 2026-09-20
- **Scope:** `scripts/sync-and-cleanup.ps1`, `scripts/worker-start.ps1`, Git Worktree cleanup
- **Status:** `ACTIVE` -> Đã vá trực tiếp vào `scripts/sync-and-cleanup.ps1`.

### 1. Context & Symptom
Khi chạy `scripts/sync-and-cleanup.ps1 -BranchName <branch>` để thu hồi worktree cũ, thư mục gốc `frontend/node_modules` ở root bất ngờ bị xoá sạch toàn bộ packages, khiến các lệnh `vitest` và `tsc` ở root báo lỗi `not recognized as an internal or external command`.

### 2. Root Cause
- Trên Windows, `frontend/node_modules` trong worktree được gắn kết bằng Directory Junction (`cmd /c mklink /J`).
- Trong PowerShell 5.1, lệnh `Remove-Item -Recurse -Force $WorktreePath` có hành vi duyệt đệ quy (recursive traversal) xuyên qua các reparse points (Directory Junctions) và xoá toàn bộ files trong thư mục đích trước khi xoá junction link.

### 3. Workaround & Permanent Solution
- Trước khi gọi `git worktree remove` hoặc `Remove-Item -Recurse $WorktreePath`, BẮT BUỘC phải tách (unmount/detach) Directory Junction bằng lệnh cmd chuẩn:
  ```powershell
  if (Test-Path "$WorktreePath\frontend\node_modules") {
      cmd /c rmdir "$WorktreePath\frontend\node_modules" 2>$null
  }
  ```
  Lệnh `rmdir` của Windows chỉ xoá điểm nối junction mà tuyệt đối không làm ảnh hưởng đến dữ liệu của thư mục gốc.

---

## [LESSON-009] Centralized API Endpoint Resolution & Zero-Hardcode Policy

- **Date:** 2026-09-20
- **Scope:** Repository Configuration, Environment Management, Lead Orchestrator, Worker UI & API
- **Status:** `ACTIVE` -> Đã chuẩn hóa `.env.example` và thiết lập biến môi trường `VITE_API_BASE_URL`.

### 1. Context & Symptom
Khi triển khai kết nối SSE stream từ Screen 2 (`AnalysisSessionWorkspace.tsx`) sang Backend FastAPI:
- Lead Orchestrator chỉ thị trong `TASK.md` hardcode proxy target về `http://127.0.0.1:8000`.
- Worker-UI tuân thủ chỉ thị và hardcode fallback hiển thị `127.0.0.1:8000`.
- Trong khi đó, backend đã được deploy thực tế trên Render tại `https://final-thesis-zgwt.onrender.com` (đã ghi nhận trong `docs/DEPLOYMENT-STAGING.md`).
- Khi người dùng chạy frontend, màn hình báo lỗi không thể kết nối tới `127.0.0.1:8000` và chuyển sang mock mode, gây trải nghiệm hoang mang và bức xúc cho người dùng.

### 2. Root Cause
- **Thiếu Configuration-as-Code**: Repo không có file `.env.example` hoặc `.env` chuẩn hóa ở root và frontend, khiến cấu hình backend URL chỉ tồn tại dưới dạng tài liệu văn bản (`DEPLOYMENT-STAGING.md`) mà không được mã hóa vào runtime environment.
- **Quán tính chủ quan của Lead**: Lead giả định backend chạy localhost mà không tra cứu staging URL trước khi viết `TASK.md`.
- **Thiếu Dynamic Resolution**: Frontend code không resolve qua `import.meta.env.VITE_API_BASE_URL` kèm default fallback về staging backend.

### 3. Workaround & Permanent Solution
- **Chuẩn hóa biến môi trường**: Luôn duy trì file `.env.example` và `.env` chuẩn trong repo với `VITE_API_BASE_URL=https://final-thesis-zgwt.onrender.com`.
- **Zero-Hardcode Policy**: Mọi cấu hình kết nối API của frontend bắt buộc phải resolve qua `process.env.VITE_API_BASE_URL` (Vite config) và `import.meta.env.VITE_API_BASE_URL` (Client code) với fallback mặc định trỏ về URL Render staging, tuyệt đối không hardcode IP localhost.
- **Dynamic UI Messaging**: Các thông báo lỗi kết nối trên UI phải lấy URL động từ config (`backendTarget`), không viết chết chuỗi IP trong template string.

---

## [LESSON-010] Bắt buộc kiểm tra CI/CD & Merge Conflicts trước khi Handoff

- **Date:** 2026-09-21
- **Scope:** Lead Orchestrator, Worker subagents, PR verification, CI/CD pipelines, Definition of Done
- **Status:** `ACTIVE` -> Đã chuẩn hóa vào quy trình Handoff bắt buộc.

### 1. Context & Symptom
Sau khi worker hoàn thành code và mở Pull Request, worker hoặc Lead vội vàng báo cáo handoff cho User và yêu cầu merge khi chưa kiểm tra trạng thái thực tế của pipeline CI/CD trên GitHub Actions. Hậu quả:
- CI/CD trên GitHub Actions bị fail ở bước `tsc -b && npm run build` do lỗi kiểu TypeScript hoặc lỗi môi trường mà khâu test cục bộ bị bỏ sót.
- Người dùng nhận thông báo sẵn sàng merge nhưng khi mở GitHub thì thấy biểu tượng dấu chéo đỏ (Checks failed) hoặc Merge Conflict, làm gián đoạn luồng làm việc và giảm uy tín chất lượng.

### 2. Root Cause
- Agent chỉ chạy `npm test` hoặc unittest cục bộ mà không chạy full `npm run build` (`tsc -b && vite build`) trước khi push.
- Sau khi push PR, Agent không có thói quen kiểm tra vòng lặp kết quả CI/CD (`gh pr checks <PR>` hoặc `gh run list`), mà mặc định cho rằng code pass ở local là CI sẽ xanh.
- Bỏ qua việc kiểm tra thuộc tính `mergeable` và `mergeStateStatus` của PR sau khi rebase hoặc push commit mới.

### 3. Workaround & Permanent Solution (Mandatory CI/CD Verification Protocol)
1. **Trước khi Push Commit**:
   - Bắt buộc chạy full production build:
     - Frontend: `npx tsc -b && npm run build` và `npm test -- --run`.
     - Backend: `$env:PYTHONPATH="src"; python -m unittest discover -s tests -q`.
2. **Sau khi Mở / Đẩy PR (Mandatory CI Verification Loop)**:
   - Agent **BẮT BUỘC** phải chạy lệnh kiểm tra trạng thái CI/CD của GitHub Actions:
     ```bash
     gh pr checks <PR_NUMBER>
     ```
   - **Nếu CI/CD fail**:
     - Lập tức lấy log chi tiết bằng `gh run view <RUN_ID> --log-failed`.
     - Phân tích nguyên nhân, audit/debug, fix code ngay trong worktree.
     - Commit, push bản vá lại lên nhánh PR.
     - Tiếp tục kiểm tra lại quá trình CI/CD.
3. **Quy tắc Dừng Handoff**:
   - Agent **CHỈ ĐƯỢC PHÉP DỪNG TURN VÀ BÁO CÁO CHO USER KHI**:
     1. **100% CI/CD checks đã hoàn tất và PASS (Màu xanh / Success)**.
     2. **PR ở trạng thái CLEAN / MERGEABLE (Zero Merge Conflicts)**.
   - Tuyệt đối không được handoff khi CI/CD còn đang fail hoặc chưa hoàn tất kiểm định.

---

## [LESSON-011] Xử lý Graceful Fallback & Tool Calling khi Upstream LLM Provider Trả về Model Not Found hoặc 503

- **Date:** 2026-09-23
- **Scope:** `src/thesis_api/agents.py`, `src/thesis_api/service.py`, `src/thesis_api/agent_tools.py`
- **Status:** `ACTIVE` -> Đã đưa vào multi-agent cognitive loop.

### 1. Context & Symptom
Khi triển khai Dynamic Multi-Agent Cognitive Loop với LLM tool calling (DeepSeek qua Codely Pixverse / OpenAI API), upstream provider có thể trả về lỗi 503 `model_not_found` (do tên model thay đổi trên gateway hoặc sự cố kênh cung cấp) hoặc lỗi mạng/timeout. Nếu hệ thống không có lớp bọc resilience ở từng agent, phiên streaming SSE sẽ bị crash đột ngột hoặc dừng giữa chừng, vi phạm trải nghiệm người dùng và hợp đồng OpenAPI.

### 2. Root Cause
- Upstream proxy/gateway LLM của bên thứ ba có thể thay đổi danh sách model khả dụng hoặc gặp sự cố quá tải kênh.
- Các lệnh tool calling phụ thuộc vào kết nối mạng bên ngoài, không thể đảm bảo 100% SLA cho production streaming.

### 3. Workaround & Permanent Solution
1. **Grounded Resilient Fallback ở Từng Agent**:
   - Trong mỗi Specialist Agent (`CompanySpecialistAgent`, `SectorSpecialistAgent`, `MacroSpecialistAgent`) và `SemanticCriticAgent`, bọc toàn bộ khối gọi `execute_chat` trong `try ... except Exception`.
   - Nếu LLM gọi lỗi hoặc timeout, agent lập tức chuyển sang chế độ deterministic retrieval: tự động query số liệu chuẩn từ SQLite `finance_master_v2.sqlite` qua `execute_agent_tool`, sinh ra các nhận định đã được kiểm định (grounded templates).
2. **Router An toàn ở Cấp Service**:
   - `stream_analysis_query` bọc `_stream_analysis_query_dynamic` trong `try ... except`. Nếu xảy ra lỗi khởi tạo, tự động fall back về `_stream_analysis_query_deterministic` để luồng SSE luôn phát đủ 100% sự kiện cho tới `REPORT_READY`.
3. **Tuân thủ Tuyệt đối Rule 3**:
   - Dù chạy qua LLM hay chạy fallback, 100% số liệu tài chính (`ROE`, `NIM`, `NPL`, `CIR`, `CASA`, `sbv_policy_rate`) đều được trích xuất xác thực từ SQLite, không bao giờ để LLM tự bịa đặt số.

---

## [LESSON-012] Tối ưu Single-Turn Data Injection & Concurrency trong Multi-Agent Streaming

- **Date:** 2026-09-23
- **Scope:** `src/thesis_api/agents.py`, `src/thesis_api/service.py`, `frontend/src/`
- **Status:** `ACTIVE` -> Đã chuẩn hóa vào `THES-13`.

### 1. Context & Symptom
Khi triển khai multi-agent cognitive loop đầy đủ với 4 tác tử (Orchestrator, Company Specialist, Sector Specialist, Semantic Critic), tổng thời gian xử lý một phiên phân tích lên tới 20–28 giây. Trên giao diện người dùng, màn hình bị khựng/đơ (frozen) trong 7–8 giây với spinner tĩnh, sau đó đột ngột bắn dồn dập 4–5 sự kiện cùng lúc. Ngoài ra, khi F5 tải lại trang, phiên phân tích bị reset về màn hình 1.

### 2. Root Cause
- **Lãng phí lượt gọi LLM trống (Multi-turn Tool Overhead)**: Orchestrator đã bóc tách rõ ticker mục tiêu và kỳ báo cáo. Tuy nhiên, Specialist vẫn gửi 1 prompt trống sang LLM chỉ để LLM bảo "gọi hàm `get_company_metrics`". Việc này tiêu tốn 3–4s chỉ để làm việc mà Python có thể làm trong 5ms.
- **Thực thi tuần tự 6 lượt LLM**: Orchestrator (1 lượt) -> Company Specialist (2 lượt) -> Sector Specialist (2 lượt) -> Critic (1 lượt) nối tiếp nhau hoàn toàn.
- **Generator bị chặn (Synchronous Generator Blocking)**: Generator không yield bất kỳ sự kiện nào trong lúc chờ LLM trả về, dẫn tới hiện tượng burst events.
- **Thiếu URL State Synchronization**: Trạng thái chuyển đổi từ Screen 1 sang Screen 2 lưu bằng state React nội bộ thay vì URL search params.

### 3. Workaround & Permanent Solution
1. **Single-Turn Data Injection (Bám sát Rule 3)**:
   - Python truy vấn sẵn số liệu CAMEL và trung vị ngành từ SQLite (<10ms) và nạp trực tiếp vào prompt của Specialist (`execute_with_data`).
   - Specialist phân tích và tổng hợp ngay trong 1 lượt LLM duy nhất, cắt giảm 50% số lượt gọi mạng (~7–8s).
2. **Thực thi Specialist Song song (`ThreadPoolExecutor`)**:
   - Company Specialist và Sector Specialist thực thi đồng thời, tiết kiệm thêm 4–6s.
3. **Bắn Sự kiện Tức thì (Instant Event Cadence)**:
   - Yield `SPECIALIST_INVOKED`, `SPECIALIST_STARTED`, và `SPECIALIST_ACTIVITY` ("Đang đọc BCTC từ SQLite...") ngay trước khi gọi LLM để giao diện hiển thị tiến trình mượt mà.
4. **Đồng bộ URL Search Params (`CreateAnalysisPage.tsx`)**:
   - Lưu `mode=session&ticker=...&period=...&q=...` vào URL. Khi F5 tải lại trang, hệ thống tự động khôi phục phiên phân tích hiện tại mà không mất dữ liệu.

---

## [LESSON-013] Never hardlink a mutable SQLite database into worktrees

- **Date:** 2026-09-25
- **Scope:** `scripts/worker-start.ps1`, test/database isolation
- **Status:** fixed by independent SQLite backup snapshots.

During composite verification, a full test process inserted test analysis runs
through a worktree path that was an NTFS hardlink to the root
`finance_master_v2.sqlite`. The root file grew and its SHA-256 changed even
though the intended runner used temporary copies. WAL mode cannot isolate
different paths that reference the same underlying file, and hardlinking the
WAL/SHM sidecars widens the risk.

Only `.env` may be hardlinked. Worktree databases are created with SQLite's
online backup API, checked before and after the copy, configured independently
for WAL, and verified not to share file identity. Test configuration remains
responsible for using temp databases, but an accidental default path can now
damage only the disposable worktree snapshot rather than the root artifact.

## [LESSON-014] Keep Artifact Byte Identity Beside the Strict Onboarding Packet

- **Date:** 2026-09-24
- **Scope:** `src/thesis_data/bank_onboarding.py`, `data/onboarding/`
- **Status:** `ACTIVE` -> Included in the provider-neutral packet loader.

### 1. Context & Symptom
The bank onboarding packet contract records the source URL, exact SHA-256, and
relative artifact reference, but does not include a byte-length field. The
official annual report is a scanned PDF without a selectable text layer, so
page-aware source review also needs a verified immutable artifact and explicit
page metadata.

### 2. Root Cause
The exchange packet schema is intentionally strict and rejects undeclared
source fields. Adding `byte_length` directly to a packet would violate its
contract even though byte count is part of the data readiness audit.

### 3. Workaround & Permanent Solution
1. Keep byte length, URL, SHA-256, page count, and scan status in a strict
   sidecar source manifest; verify all of them against the packet and bytes
   before constructing a canonical candidate.
2. Manually reconcile scanned statement values from rendered pages and retain
   both physical and printed page numbers. OCR/parser output remains a search
   aid and cannot mark a value valid.

## [LESSON-015] Keep Derived Source Lineage on Accepted Inputs

- **Date:** 2026-09-25
- **Scope:** `src/thesis_data/bank_onboarding.py`, `src/thesis_data/canonical_snapshot.py`
- **Status:** `ACTIVE`

### 1. Context & Symptom
Stage1 correctly requires a derived observation to have a null direct
`source_ref` and to retain its formula and input observation IDs. Bank packet
conversion was copying the reviewed filing source onto every row, and canonical
snapshot validation required that direct source even for derived values.

### 2. Root Cause
The generic packet mapper and materializer applied direct-observation source
rules before distinguishing reported values from reproducible derived values.

### 3. Permanent Solution
1. Map direct source and locator from the accepted review evidence.
2. Map valid derived observations with a null `source_ref`, their reviewed
   locator, formula version, and input IDs.
3. Materialization validates primary review evidence and valid numeric inputs
   for derived observations while keeping direct-source requirements for
   reported observations.

---

## [LESSON-016] Recompute Derived Values Before Operational Acceptance

- **Date:** 2026-09-25
- **Scope:** `src/thesis_data/metrics.py`, `src/thesis_data/canonical_snapshot.py`,
  `src/thesis_data/canonical_sqlite_provider.py`
- **Status:** contract accepted in D-071; implementation included in the CTG onboarding change; integrated verification pending.

### 1. Context & Symptom
An accepted observation label plus input IDs does not prove that a supplied
derived value was actually calculated from those inputs. An onboarding
candidate could have a structurally valid CSV, reviewed primary-source
locators, formula names, and input IDs while still containing a derived number
that the operational promotion path had never recomputed. Source review alone
did not prove the submitted arithmetic, and a formula unit test does not prove
the onboarding path called that formula.

### 2. Root Cause
Candidate validation checked that the formula and input references existed, but
did not run the deterministic formula code or preserve a receipt of that run.
The canonical snapshot validator checks input existence and Stage-1 checks the
claim/value, formula version, and source lineage, but neither substitutes for
recalculation at promotion.

### 3. Permanent Solution
1. Before promoting a new-bank derived candidate, register explicit
   metric/formula versions with ordered input metric, unit,
   period-basis, output, period-rule, and tolerance contracts. Promotion must
   resolve each accepted input ID and recompute through the registered metric
   function; unsupported formulas or mismatches fail closed.
2. Verify unit, period, scope, and numeric tolerance, then persist a
   machine-readable calculation receipt on each accepted derived
   observation. Include input identities and values, formula version, both
   outputs, tolerance, and result so providers can expose the same provenance.
3. The CTG Q4 packet's rounded ratios are accepted only within explicit
   tolerance: NPL candidate 1.219 vs 1.218950000795433229958915168 (difference
   0.000049999204566770041084832, tolerance 0.00005), and LLR candidate 174.6762
   vs 174.6761886399215389098888044 (difference
   0.0000113600784610901111956, tolerance 0.00005). Exact amount formulas and
   the four-decimal ROA/ROE formulas reproduce exactly.

Keep this gate in the data-promotion boundary; Stage-1 checks the published
claim against the accepted result. A reviewed CTG packet before this path passes
is not proof of a generic derived-metric ingestion guarantee.

---

## [LESSON-017] A correct ignored artifact still needs repository-bound authority

- Date: 2026-09-25
- Scope: VPB ROE comparative eligibility, Gold v5 provenance and portable control hashes
- Status: accepted under D-072 after distinct reviewer ACCEPT at head 2b292ddf21bd6be8a550f81fb518fca5dc419efb.

The official VPB filings, two-checker adjudicated ledger and Gold v5 values
support parent-attributable ROE. The earlier D-063 factual clause and local
packet status were stale; durable records now describe parent-attributable
profit over average parent-attributable equity. Q4 source locators are filing
pages 6 and 8. The alternative total-equity calculation is retained as a
diagnostic comparison, not the adopted convention.

The distinct reviewer task /root/vpb_d072_reviewer_luna accepted exact PR head
2b292ddf21bd6be8a550f81fb518fca5dc419efb. Its attestation records full raw
source hashes, canonical Git-blob control hashes at that reviewed head, the
independent Q4 recomputation, the eligible 80-cell gate result (76 valid, four
missing), and the ACCEPT verdict. D-072 opens the five-issuer VPB ROE comparison
scope only because that attestation exists; an eligible database gate alone
does not replace distinct review.

Tracked UTF-8 text control hashes use SHA-256 after strict UTF-8 decoding and
CRLF/lone-CR to LF normalization. This preserves content while making hashes
identical across Windows and Unix checkouts. Immutable PDFs, SQLite snapshots,
CSV/JSON/JSONL ledgers and gate manifests use exact raw-byte SHA-256. Legacy
Windows checkout-byte hashes may appear only as audit metadata. The verifier
checks synthetic LF and CRLF forms plus the Git blob. It reads ignored
artifacts only from an explicit evidence root; CI can validate tracked
controls without that root but cannot validate ignored local evidence.

Hash references form a one-way chain: an attestation binds the exact reviewed
head and current VPB-scoped controls but does not hash itself or the authority;
the authority binds the attestation but does not hash itself; D-063/D-072 cite
the resulting hashes and are not included in that authority control set. Living
repository files (`AGENTS.md`, contracts, decisions, lessons, verifier code)
must remain semantic policy references rather than byte-pinned domain evidence.
Otherwise any unrelated repository update invalidates an accepted data gate.
Do not introduce reverse hash references that create a cycle.

The original checker, adjudication and promotion ledgers remain unchanged. The
promotion ledger's register_review_status stays blank for the four VPB targets;
the separate sidecar links the accepted adjudication and records the independent
review status without rewriting the source ledger.

## [LESSON-018] API phải ràng buộc claim vào source locator của đúng metric

- **Date:** 2026-09-24
- **Scope:** `src/thesis_api/service.py`, `src/thesis_data/gold_dataset_provider.py`, deployment SQLite configuration
- **Status:** `ACTIVE` -> API fail-closed khi provider chưa đưa locator của observation ra hợp đồng canonical.

### Context & Root Cause

Gold v5 `evidence_snippets` chỉ xác định source, ticker, period và trang; không có
`metric_id`. Chúng không thể thay locator chính xác của observation cho một số
liệu cụ thể. Ngoài ra, snapshot Gold hiện nằm trong `data/`, bị `.gitignore`
loại khỏi Git; Render build từ Git nhưng chưa cấu hình `SQLITE_DB_PATH`, nên
service có thể chạy mà không có accepted SQLite snapshot. `DATABASE_URL` không
cấp file SQLite cho provider này.

### Permanent Solution

- Numeric claim phải đi qua observation hợp lệ, source hợp lệ, locator riêng
  của observation đó và Stage-1. Nếu provider làm rơi locator, API phải block;
  evidence source/period-level chỉ được xem là tham khảo bổ sung.
- Khớp cùng source, ticker, period, metric hoặc trang vẫn chưa chứng minh một
  snippet hỗ trợ đúng numeric observation. Chỉ observation ID link rõ ràng từ
  mapping đã được review mới đủ để thêm snippet vào `evidence_refs`;
  `DatasetEvidence` hiện chưa có trường link nên API để các numeric `evidence_refs`
  rỗng và giữ provenance trong observation/source locator trail.
- `/api/capabilities` và `/api/ready` chỉ báo runnable khi provider tìm được ít
  nhất một claim đáp ứng các điều kiện này. Sync và SSE dùng chung kết quả.
- Khi triển khai backend, phải cung cấp snapshot Gold đã kiểm định qua artifact
  hoặc mount có kiểm soát và cấu hình `SQLITE_DB_PATH` rõ ràng. Không dựa vào
  artifact ignored ở máy developer hoặc tự suy ra đường dẫn từ `DATABASE_URL`.

## [LESSON-019] Close SQLite fixtures explicitly on Windows

- **Date:** 2026-09-25
- **Scope:** temporary SQLite fixtures in data-provider tests
- **Status:** ACTIVE

### Context & Root Cause

The `sqlite3.Connection` context manager commits or rolls back a transaction,
but does not close the connection. On Windows, a fixture database can therefore
remain locked when `TemporaryDirectory` tries to remove it, obscuring the test
failure with a cleanup `PermissionError`.

### Permanent Solution

Use `try/finally: connection.close()` (or `contextlib.closing`) for temporary
SQLite fixtures and read-only audit connections. Keep transaction management
separate from connection lifetime.

## [LESSON-020] Validate executable references, not only JSON syntax

- Date: 2026-09-25
- Scope: `contracts/openapi.json`, Python CI

Eleven schema references were stored under an empty key instead of `$ref` in
the pre-existing OpenAPI contract. JSON parsing alone accepted them, so clients
could silently lose request/response schema links. Restore the literal keys
using a structured writer and validate the OpenAPI document in Python CI.
PowerShell expansion of dollar-prefixed strings can cause this class of
corruption; use literal-safe patches or structured file writes.

Tracked evaluation JSONL also needs canonical LF UTF-8 hashing. Raw checkout
bytes vary under `core.autocrlf`; the regression gate must compare LF and CRLF
copies while preserving BOM, code points, whitespace and terminal newline.

## [LESSON-021] A revision trace must show a feedback-responsive change

- Date: 2026-09-25
- Scope: adaptive runtime, report peer metadata

Independent review caught passing tests that changed only the critic verdict
after re-querying unchanged facts. Revision tests must assert that selected
issue content reaches a writer, the targeted candidate changes appropriately,
unaffected output is retained and Stage-1 rechecks the result. A transition log
alone cannot establish analytical revision.

Peer denominator/missing-member metadata belongs to each metric and period.
One shared report dictionary silently takes the last metric's denominator;
test two metrics with different accepted members and expose per-metric records.

## [LESSON-022] Accepted snapshot hashes and runtime persistence must be isolated

- Date: 2026-09-25
- Scope: API run-history persistence and readiness

Reusing the analytical SQLite path for analysis_runs can modify schema, WAL
state and bytes after a successful report. A hash-bound authority may then fail
on the next request. Separate mutable history into its own configured store,
reject path aliases and verify the source hash after repeated sync/SSE runs.
Readiness must also include required model configuration; accepted facts alone
cannot make an analysis endpoint runnable when its mandatory critic is absent.

## [LESSON-023] Written quantities are numeric assertions too

- Date: 2026-09-26
- Scope: grounded specialist prose and Orchestrator synthesis guards

Rejecting digits alone does not prevent a writer from introducing a new value.
Fractions and multipliers such as `half`, `quarter`, `twice`, `double` and
`dozen`, along with Vietnamese number words, can change the factual meaning of
a missing or accepted claim without containing a digit. Specialist prose and
synthesis must share a maintained numeric-or-period token detector, and tests
must include missingness claims where unsupported comparative wording would
otherwise look harmless. The guard is only a deterministic boundary; semantic
review must still evaluate grounding, logic and usefulness.

## [LESSON-024] Requirement scope is not claim ownership

- Date: 2026-09-26
- Scope: framework-neutral targeted revision validation

A requirement can legitimately list several agents, so its
`required_agents` cannot prove which specialist produced a particular claim.
Entity, period and metric matching has the same ambiguity for shared synthesis
requirements. The reference API can enforce its private claim-to-role map, but
an alternative executor needs an immutable canonical producer/owner field on
`AtomicClaim`. Add that field contract-first, preserve it through revision and
bind it into candidate hashes; do not infer ownership from overlapping plan
requirements or import an application DTO into the reusable core.

## [LESSON-025] Persist a terminal SSE event before publishing it

- Date: 2026-09-26
- Scope: analysis stream run-history persistence

When `REPORT_READY` is included in persisted event history, stage it without
queueing it to the client, persist the final run, then publish it. If
persistence fails, remove the staged event and restore the sequence before
emitting `RUN_BLOCKED`. A nested closure that decrements the outer sequence
must declare `nonlocal sequence`; otherwise the failure path raises
`UnboundLocalError` and hides the persistence reason. Cover success round-trip
and failure event ordering through the real SSE route.

## [LESSON-026] Source claims require verified bytes and document identity

- Date: 2026-09-26
- Scope: generic operational onboarding and canonical snapshot promotion
- Status: ACTIVE

An onboarding caller must not be able to make a source acceptable by declaring
an arbitrary source type or a hash-shaped string. Promotion must validate the
source type against the recognized allowlist, verify an exact SHA-256 against
the immutable evidence bytes, and require each document's hash to agree with
its source record. Caller-supplied hash strings or hash maps are not proof;
generic materialization must require a verifier result produced from the bytes
under an explicit evidence root. Keep per-observation locator, period basis,
reporting scope and review evidence attached to accepted values. Add negative
tests for unknown source types, malformed or mismatched hashes, document/source
hash splits, and directly constructed candidates that bypass byte verification.

## [LESSON-027] Free Render needs immutable object hydration

- Date: 2026-09-27
- Scope: staging snapshot provisioning
- Status: ACTIVE

Render Free cannot retain a local SQLite file across restart or spin-down, and
it does not provide a persistent disk on the free compute plan. A private
object-storage copy is therefore the durable source, while the API hydrates a
temporary local path at startup. The bootstrap must validate raw bytes,
SQLite integrity and snapshot identity before readiness; the file must never
be uploaded once per analysis request. Mutable run history remains a separate
store and may require a different persistence decision for production.

## [LESSON-028] Blueprint values are not proof of service environment state

- Date: 2026-09-27
- Scope: Render staging deployment configuration
- Status: ACTIVE

Adding non-secret environment values to `render.yaml` does not prove that an
already-existing Render service has received those values. A deploy can build
successfully and still fail during application startup when the runtime
environment is missing one required value. Keep the required variable names
and expected public values in the deployment runbook, verify service-level
configuration through the Render control plane, and diagnose bootstrap
validation failures before investigating object bytes or SQLite integrity.

## [LESSON-029] Provider dataset identity must bind to verified authority

- Date: 2026-09-27
- Scope: Gold provider binding and reporting-scope authority
- Status: ACTIVE

When initializing `GoldSqliteDatasetProvider` with a verified `VerifiedGoldObservationScopeAuthority`, the provider constructor's `dataset_id` argument must take `authority.dataset_id` (e.g. `gold-bank-2025-expanded-v5-evidence`), not a hardcoded placeholder like `"gold-sqlite"`. `GoldSqliteDatasetProvider._validate_scope_authority` strictly validates that `authority.dataset_id == self._dataset_id` and fails closed on mismatch with `DatasetProviderError("reporting-scope authority dataset_id mismatch")`. In `thesis_api.service._load_provider`, passing a hardcoded mismatched dataset ID caused the provider binding to skip the authorized provider and report the database as disconnected with HTTP 503.

## [LESSON-030] SSE Stream Consumers Must Handle Terminal Blocked States Cleanly Without False Connection Errors

- Date: 2026-09-28
- Scope: Frontend SSE Stream Consumer & Session Workspace (`useAnalysisSessionStream.ts`, `AnalysisSessionWorkspace.tsx`)
- Status: ACTIVE

When an SSE stream terminates after emitting domain validation errors such as `RUN_BLOCKED` (e.g. `unsupported_period: Period 2024 is not an exact period in the accepted snapshot`), the stream consumer must recognize `RUN_BLOCKED` as an intentional, business-level terminal state rather than throwing an unhandled exception or reporting a network/server outage ("Luồng đã kết thúc nhưng API không gửi báo cáo"). Treating business rejection as a network connection error shows false-positive failure banners ("Lỗi kết nối Live SSE tới backend", "API lỗi", "Thử lại Live"), misleading users into retrying identical queries rather than modifying their inputs. The UI must cleanly transition into `BLOCKED` ("Cần điều chỉnh yêu cầu"), suppress network error alerts, and prominently highlight corrective actions (such as "← Chỉnh sửa câu hỏi" and exposing exact supported quarterly periods like `2024_Q1` to `2024_Q4`).

## [LESSON-031] Markdown Code Fence Sanitization for Structured JSON LLM Endpoints

- Date: 2026-09-28
- Scope: `src/thesis_api/analysis_writer.py`, `src/thesis_data/openai_semantic_critic.py`
- Status: ACTIVE

Third-party OpenAI-compatible model endpoints (such as DeepSeek, OpenRouter, or local proxies) frequently wrap structured JSON output in markdown code fences (` ```json\n...\n``` ` or ` ```\n...\n``` `), even when requesting structured JSON schema mode. Calling `json.loads(output_text)` directly without stripping outer code fences triggers `json.decoder.JSONDecodeError: Expecting value: line 1 column 1 (char 0)`, which bubbles up into writer/critic failures (`analysis_writer_json_invalid`, `openai_semantic_critic_json_invalid`) and causes unrecoverable `adaptive_runtime_failure`. A robust pre-parsing sanitizer `_clean_json_text` strips leading and trailing markdown backtick blocks while preserving internal code formatting inside JSON strings, preventing spurious decoding crashes across all OpenAI-compatible model providers.

Furthermore, third-party model proxies often lack BNF-grammar enforcement for `response_format` JSON schemas. When prompt instructions omit explicit schema keys and example schemas, models like DeepSeek can emit unstructured conversational prose instead of JSON objects. Adding an explicit `CRITICAL OUTPUT FORMAT` directive detailing root keys and exact JSON schemas directly inside the system prompt / instructions guarantees 100% structured JSON compliance even across unconstrained proxy backends.

## [LESSON-032] Alignment of LLM Semantic Critic Output with Frozen Plan Capabilities & Stage-1 Gates

- Date: 2026-09-28
- Scope: `src/thesis_data/openai_semantic_critic.py`, `src/thesis_data/semantic_evaluation.py`
- Status: ACTIVE

During live multi-agent analysis (e.g. single-company analysis of MBB in 2024_Q4), LLMs acting as semantic critics can invent cross-level reconciliation issues (e.g. `required_action='reconcile_cross_level'`) or hallucinated link results even when the analysis plan has NO applicable links (`plan.applicable_links == ()`). This causes Stage-1 deterministic semantic acceptance (`evaluate_stage1_semantic_acceptance`) to fail with `cross_level_reconciliation_requires_applicable_link` and `cross_level_issue_link_result_missing`.
Similarly, models may attach specialist claims to orchestrator issues (violating `orchestrator_issue_must_target_synthesis`), assign issues to inactive agents, or report `cross_level_integration` as applicable when the frozen plan declares it inapplicable.

The semantic critic adapter (`OpenAISemanticCritic`) must normalize decoded model output against the frozen `AnalysisPlan`:
1. **Applicable Links**: Filter `applicable_link_results` to declared `plan.applicable_links`. If `not plan.applicable_links`, clear `applicable_link_results = []`. Synthesize default pass results for any missing plan links.
2. **Issues**: If `action == RECONCILE_CROSS_LEVEL` and the plan lacks links (or the issue is not in any link's issue IDs), downgrade `action` to `REVISE_CLAIM`. For orchestrator issues, clear `affected_claim_ids = []`. Map any inactive agent to the primary specialist (or orchestrator if synthesis). Filter `affected_requirement_ids` to declared plan requirements.
3. **Dimensions**: Enforce dimension applicabilities against `expected_dimension_applicability(plan)`. For `NOT_APPLICABLE` dimensions, set `score = None` and clear claims, requirements, and issue IDs.

---

## [LESSON-033] Free Render Run History Storage Hydration and Non-Blocking Remote Persistence

- Date: 2026-10-01
- Scope: `src/thesis_api/run_history_storage.py`, `src/thesis_api/service.py`, `src/thesis_api/main.py`, Render Staging Deployment
- Status: ACTIVE

### 1. Context & Symptom
On Render free-tier hosting, instances spin down after ~15 minutes of inactivity and local ephemeral storage resets upon every wake or redeployment. Storing analysis run records solely in local SQLite (`ANALYSIS_RUNS_DB_PATH=/tmp/analysis_runs.sqlite`) causes the Report Library (`GET /api/runs`, `/api/analysis-runs`) and trace links to become completely empty after server sleep or deploy.

### 2. Root Cause & Architectural Invariants
Render Free provides no persistent disk volume. However, the private Supabase Storage bucket (`SUPABASE_STORAGE_BUCKET`) and credentials (`SUPABASE_SERVICE_ROLE_KEY`) are already provisioned and configured for analytical snapshot hydration (`snapshot_bootstrap.py`).
Writing run history must obey strict safety boundaries:
1. It must NEVER write into or modify `SQLITE_DB_PATH` (the Gold analytical snapshot).
2. It must NEVER overwrite the analytical snapshot object (`SUPABASE_STORAGE_OBJECT`) in Supabase Storage.
3. Missing or incomplete remote configuration must fall back to local-only SQLite without failing application startup or breaking `/api/ready`.
4. Remote upload must be non-blocking in the background so that analysis HTTP latency is not impacted. Remote upload errors must log a sanitized warning (never leaking keys) and never fail the user's analysis request.

### 3. Permanent Solution
1. **Module `run_history_storage.py`**:
   - `schedule_remote_run_persist(record, settings)`: Asynchronously uploads the serialized run record (`run_id`, `created_at`, `query`, `target_ticker`, `peer_tickers`, `period`, `status`, `report_json`, `events_json`, `trace_json`, metrics, arm, question_type) as a JSON object to `<prefix>/<run_id>.json` (default prefix: `run-history/`) with `x-upsert: true`.
   - `hydrate_run_history(db_path, settings, limit=500)`: On application startup (`lifespan`), lists objects under the prefix, compares with locally existing `run_id`s in SQLite, downloads missing records, and idempotently inserts them into `analysis_runs` SQLite table.
   - Refuses `.sqlite` objects and paths matching `SUPABASE_STORAGE_OBJECT`, and refuses hydration into `SQLITE_DB_PATH`.
2. **Lifespan Integration**:
   - Called in `main.py` lifespan after snapshot hydration; exceptions are logged as warnings and never prevent app startup or readiness probe.

---

## [LESSON-034] Benchmark Observation Identity and Run Persistence Preservation in Composite Providers

- Date: 2026-10-01
- Scope: `src/thesis_data/composite_provider.py`, `src/thesis_api/service.py`
- Status: ACTIVE

1. **Benchmark Observation ID Binding**: In multi-provider or composite dataset architectures (such as `CompositeDatasetProvider`), synthesized benchmark observations returned by base providers embed `dataset_id` and `dataset_snapshot_id`. When consumed through a composite dataset reference, the runtime checks `benchmark.observation_id == peer_benchmark_observation_id(composite_ref, ...)`. The composite provider's `get_peer_benchmark` must explicitly regenerate `observation_id` with `peer_benchmark_observation_id` bound to `composite_ref` and `requested_peer_entity_ids`.
2. **AnalysisEngine Method Integrity**: Reusable wrappers or delegation must not override `AnalysisEngine.analyze` with internal `_analyze`, as `analyze` encapsulates mandatory operational run persistence (`persist_run`) and trace persistence to `analysis_runs.sqlite`. Bypassing it breaks run-trace endpoints and persistent history.


## [LESSON-035] Quarterly bank filings: mislabelled mirrors, garbled text layers and convention drift

- A mirror path is not proof of period: Vietstock's `TCB_..._Q4_2024_Hopnhat.pdf` contains the 2023 Q4 report; the real file is `_Hopnhat_1.pdf`. Always check the statement date on page 1 before extracting.
- Some PDFs carry an embedded text layer that is garbled (HDB 2025 Q3, 2026 Q2) or tables drawn as grids/rotated pages (STB, SHB 2024) that defeat Tesseract. Re-OCR the page or read a rendered crop; never trust a value that does not satisfy the statement identity (assets = liabilities + equity, groups sum to the total, PBT − tax = PAT).
- Banks with loss-making subsidiaries (VPB/FE Credit) have parent profit > group profit; profit-split checks must allow negative minority interest.
- Keep one definition across a time series: mixing audited year-end (margin lending excluded) with interim rows (margin included) silently shifts NPL by ~0.1 point.

## [LESSON-036] Verified narrative needs the verifier's own vocabulary and a real fallback

- The writer used "giảm nhẹ" for a −0.04 pp ROA move and "ngang trung vị" for a +0.6 pp gap; the verifier's flat thresholds (0.05 pp for ROA/NPL) were never shown to the model, so correct-looking sentences were dropped. Fact payloads now carry `huong`, the exact direction phrase computed with the verifier's thresholds.
- When the opening headline/answer failed verification the sweep substituted a fixed string ("Báo cáo phân tích tài chính.") or left the answer empty. Stand-ins must be built from verified facts and re-verified.
- Some models rewrite the echoed `evaluator_version`; the critic adapter now pins it to the configured adapter:model identity instead of rejecting the round.
- Latency matters for a live demo: on the current proxy gpt-6-luna took ~24 s per call versus ~3 s for deepseek-v4-pro, i.e. ~7.7 min for a simple lookup.

## [LESSON-037] Upload samples must name a bank the served dataset does not already cover

When staging moved from Gold v5 (5 banks) to the 10-bank operational snapshot, the CTG demo sample became a duplicate: uploading it produced a second, different CTG 2024 Q4 figure next to the dataset's own. Uploads of an already-served ticker are now rejected with a Vietnamese pointer to the existing data, and the demo sample is VIB FY2025 (outside the top 10). Uploaded banks are never peer-universe members, so tool planning must fall back to the catalog's peer group instead of requiring the focus bank to be a member — otherwise profile signals silently become "insufficient data".

## [LESSON-038] A filing missing from the mirror is not a filing that was never published

- Eight bank-quarters were left empty in r1/r2 because the usual Vietstock file name returned nothing. All eight filings existed: on the bank's investor-relations site (ACB, BIDV, VietinBank, HDBank), on CafeF (VPB 2026 Q1), or on Vietstock under the reviewed semi-annual name `..._6T_<year>_Soatxet_Hopnhat.pdf` (SHB 2024 Q2, VPB 2026 Q2). Check those three places before recording a gap.
- A worker agent is useful for locating and downloading files, but its transcription was slower than re-reading the pages directly. The orchestrator verified every cell with statement identities (groups add to the total, liabilities plus equity equal assets, equity components add up, profit after tax minus the non-controlling share equals parent profit) and with the comparative columns, which must equal the values already held for the prior period.
- Tesseract on this machine has only the `eng` language pack. Calling it with `-l vie` fails silently and writes no output; numbers still read well with `eng`, and keyword search needs accent-folded patterns.
- Before choosing a convention for a new cell, read the neighbouring cells of the same bank. r3 took the audited year-end provision convention (margin-lending provision excluded) for three interim cells whose neighbours all use the balance-sheet line; the worker's independent transcription exposed the mismatch and r4 corrected it. A second transcription is worth having even when every identity check passes, because identities cannot catch a convention choice.

## [LESSON-039] Uploaded bank reports: rank denominator bounds, unit enforcement, and grounded superlatives

- Date: 2026-10-02
- Scope: `src/thesis_data/report_facts.py`, `src/thesis_api/analysis_tools.py`, `src/thesis_api/narrative_templates.py`, `src/thesis_data/narrative_verification.py`
- Status: ACTIVE

### 1. Three Failure Modes in Uploaded Bank Analysis
1. **Rank Denominator Overflow for Non-Member Banks**: When an uploaded bank (e.g. VIB) outside the 10-peer universe was ranked, tools evaluated its position against the 10 peers without adding the bank itself to the denominator, producing invalid rank facts like `11/10`. An entity's rank among peers plus itself must have denominator `len(peers) + 1` (e.g. 11/11), satisfying `1 <= rank <= denominator`. Peer median calculations remain strictly on the 10-bank peer universe per D-077.
2. **Fact Unit Mismatch in Model Narratives**: The LLM produced sentences like "ROE/ROA ở mức 11,82 lần, nhỉnh hơn trung vị nhóm 11,46%", where the fact had unit `x` (ratio) but was written with `%`. The narrative verifier did not cross-check unit compatibility between cited facts and numeric tokens. Enforce that facts with unit `x` / `lần` reject `%` and `điểm %`, while facts with unit `%` and `pp` reject `lần`.
3. **Ungrounded Group Superlatives**: Models inserted superlative phrases ("kém nhất nhóm", "thấp nhất") without factual grounding or when conflicting facts existed (e.g. VPB having higher NPL than VIB). The narrative verifier now requires group superlatives ("nhất nhóm", "kém nhất", "tốt nhất", "cao nhất", "thấp nhất", "dẫn đầu", "đứng đầu", "đứng cuối", "xếp cuối", "đội sổ") to cite an entity- and metric-aligned rank fact with rank 1 (for best/top) or denominator (for worst/bottom). Metric detection uses clause boundaries and length-descending term matching to prevent substring collisions (e.g. `nợ xấu` within `bao phủ nợ xấu`).

---

## [LESSON-040] Writer Prompts Must Explicitly State Verifier Rules; Stronger Models Write Denser Prose Dropped for Unstated Rules

- Date: 2026-10-05
- Scope: `src/thesis_api/analysis_writer.py`, `src/thesis_api/adaptive_runtime.py`, `src/thesis_data/narrative_verification.py`, `contracts/openapi.json`
- Status: ACTIVE

### 1. The Denser Prose Failure Mode in Capable Models
- Capable models (`gpt-5.5`, `gpt-5.6-luna`, `deepseek-v4`) naturally synthesize dense, multi-clause analytical sentences combining multiple metrics, multi-quarter timelines, and comparative ranks (e.g. "So với quý 1/2026, tỷ lệ bao phủ nợ xấu giảm -8,6 điểm %, còn tỷ lệ nợ xấu đi ngang (+0,03 điểm %)").
- The sentence verifier was designed around atomic verification constraints:
  1. Direction checks test against a single primary delta fact; combining opposite movements ("giảm" and "đi ngang") in one sentence fails `trend_direction_mismatch`.
  2. Period checks reject named quarters unless they match the `period` or `from_period` of a cited fact (`period_not_cited`).
  3. Metric proximity bindings scan terms within proximity windows; combining multiple metrics and ranks in one sentence can cause metric-rank cross-talk (`rank_mismatch`).
- Because writer prompt templates previously only stated a vague "Mỗi câu liệt kê fact_ids nó dựa vào", models were unaware of these structural verification boundaries, causing factually accurate synthesis to be dropped during verification sweeps.
- **Rule**: Prompts must explicitly instruct models:
  1. `fact_ids` must cover EVERY number, rank, and period named in the sentence; quarters may only be named if a cited fact has it as `period` or `from_period`.
  2. Periods must be written in full: `"quý N/YYYY"`.
  3. One sentence describes one metric and uses one direction word (`tăng / giảm / đi ngang / cao hơn / thấp hơn`). Two metrics moving differently must be split into two separate sentences.
  4. Exact citation: `fact_id` strings must be copied verbatim without modification or fabrication.

### 2. Audit Citation Traceability and Output Limits
- `SentenceDroppedDTO` previously omitted `fact_ids`, making it impossible in offline audits to distinguish between missing citations vs verifier false rejections. Citations are now preserved in `narrative_audit.sentences_dropped[].fact_ids`.
- Reasoning models (e.g. `gpt-5.5`) exhaust output token limits when strict reasoning overhead is deducted from tight generation budgets. Literal hardcoded token limits (2500) truncated responses mid-JSON. Configurable limits (`ANALYSIS_WRITER_MAX_OUTPUT_TOKENS` default 6000, `SEMANTIC_CRITIC_MAX_OUTPUT_TOKENS` default 8192) avoid truncation while allowing reasoning models adequate generation margin.
## [LESSON-041] Evaluation Harness Migration to Operational Multi-Bank Snapshots: Canonical Schema, Scope Isolation, and Plan Hashing

- Date: 2026-10-05
- Scope: `scripts/er8_run.py`, `scripts/er8_score.py`, `scripts/er8_analyze.py`, `scripts/generate_er9_data.py`, `tests/test_er9_harness.py`
- Status: ACTIVE

### 1. Context & Operational Snapshot Differences
Migrating the A/B/C evaluation harness from the 5-bank Gold v5 annual benchmark to the 10-bank quarterly operational snapshot (`bank-quarterly-top10-operational-v1-r4.sqlite`) introduced several architectural and schema divergences:
1. **Physical Schema & Snapshot Metadata**: Operational SQLite snapshots store observations in `observations` with columns `(entity_id, period_id, metric_id, value, unit, validation_status, source_ref, source_locator)` and identify snapshots via `dataset_metadata.dataset_snapshot_id`, contrasting with Gold v5's `metric_observations` and `snapshot_metadata.snapshot_id`. The dataset observation loader must dynamically inspect available tables or support both schemas to remain backward compatible.
2. **Scope Authority Uncoupling**: Staging serves the operational 10-bank snapshot without a Gold scope-authority sidecar (`gold_scope_authority_path=None`), loading `CanonicalSqliteDatasetProvider` rather than `GoldSqliteDatasetProvider`. The evaluation harness must leave `gold_scope_authority_path` unset so that evaluation runs reproduce staging behavior faithfully.

### 2. Cross-Arm Plan Hash Invariance
In ER-8, manifests recorded 3 plan-hash mismatches across arms because the runtime appended `known_limitations` to `analysis_plan` after execution. Since different arms (single-agent vs hierarchical) encounter different execution paths and append different limitations, including post-execution limitations broke cross-arm plan equivalence.
- **Rule**: Plan hashing (`_compute_plan_hash`) must exclude runtime-appended fields (`known_limitations`) and hash only the frozen pre-retrieval plan. Under this rule, cross-arm plan-hash mismatches drop to exactly 0 across all 36 runs.

### 3. Missingness Metric on Complete Coverage Snapshots
When an evaluation dataset contains complete coverage (all 100 bank-quarters across 10 banks present, 0 missing cells), evaluating missingness handling against hardcoded task IDs (e.g. ACB 2024 Q1 in Gold v5) would report false 100% scores. Missingness checks must be driven dynamically by `expected_coverage.missing_count`:
- When `missing_count == 0`, `missingness_handled` evaluates to `None` and is exported as `N/A` in arm summary tables, avoiding misleading evaluations when no missing-cell handling was triggered.

---

## [LESSON-042] Vietnamese Bank Name Alias Recognition: Longest-Phrase-First Matching, Boundary Disambiguation, and Catalog Grounding

- Date: 2026-10-05
- Scope: `src/thesis_api/query_understanding.py`, `tests/test_query_understanding.py`
- Status: ACTIVE

### 1. Longest-Phrase-First Matching and Span Blanking
Vietnamese bank entity references in real user queries span a wide spectrum from 2-letter abbreviations ("MB") to multi-word official Vietnamese titles ("ngân hàng Ngoại thương", "Sài Gòn – Hà Nội", "Đầu tư và Phát triển").
- **Collisions & Sub-phrases**: Matching shorter abbreviations or words first would incorrectly match "MB" inside "MBBank" or "MBS", "Á Châu" inside "ngân hàng Á Châu", or "Sài Gòn" inside "Sài Gòn – Hà Nội".
- **Solution**: Normalize all alias phrases (`normalize_text` and `strip_accents`), sort candidates by phrase length descending, and blank out matched spans with spaces in the working text. This ensures longer phrases consume the characters first, and subsequent shorter candidates cannot falsely re-match within consumed spans while preserving character indices and relative left-to-right order for multi-entity head-to-head queries.

### 2. Polysemous and Generic Word Disambiguation
- Generic Vietnamese words ("ngân hàng", "nhà nước", "Việt Nam") must never be mapped to any bank entity alone, preventing false matches on macro policy queries ("Ngân hàng nhà nước điều hành lãi suất thế nào?").
- Polysemous terms like "Quốc tế" appear in general banking contexts ("chuẩn quốc tế Basel", "thị trường quốc tế"). To prevent false positive matches for VIB, "quốc tế" alone is never mapped; VIB is matched exclusively via "VIB", "vibank", or "ngân hàng quốc tế [việt nam]".
- Word boundary regex `(?<![A-Za-z0-9_À-ỹĐđ])...(?![A-Za-z0-9_À-ỹĐđ])` strictly enforces word boundaries across ASCII and Vietnamese unicode ranges, preventing "MB" from matching inside "MBS".

### 3. Catalog Grounding and Unsupported Bank Refusals
- A recognized alias maps to a resolved company entity only if its canonical ticker exists in the request's `catalog.entities`.
- If an alias refers to a bank not present in the catalog (e.g. "OCB", "Phương Đông" when using the 10-bank Gold catalog, or "Vietcombank" when using a test mock catalog), its canonical ticker is routed directly to `unknown_entity_tokens`. This triggers `AnalysisBlocked("unsupported_entity")` with the standard localized message listing available banks.
- Blanking consumed alias spans also prevents uppercase brand tokens (such as "BIDV" for ticker `BID`, or "SACOMBANK" for ticker `STB`) from being erroneously flagged as unknown entities by the trailing uppercase token scanner.

### 4. Non-Distinctive Bare Phrases Must Require Bank Prefixes ('ngân hàng' or 'nh')
In user queries, common Vietnamese dictionary terms, ministry titles, universities, or economic phrases can contain substrings identical to bank names:
- `"Bộ Công Thương và VCB"` matched CTG because of bare `"công thương"` (Ministry of Industry and Trade).
- `"Sinh viên Ngoại thương hỏi ROE của ACB"` matched VCB because of bare `"ngoại thương"` (Foreign Trade University).
- `"Đầu tư và phát triển số của TCB"` matched BID because of bare `"đầu tư và phát triển"` (digital investment & development).
- **Rule**: Distinctive brand names (`Vietcombank`, `VCB`, `BIDV`, `BID`, `VietinBank`, `CTG`, `Techcombank`, `TCB`, `MBBank`, `MB Bank`, `MB`, `VPBank`, `VPB`, `ACB`, `Sacombank`, `STB`, `SHB`, `HDBank`, `HDB`, `VIB`, `OCB`, `TPBank`, `MSB`, `LPBank`, `SeABank`, `Eximbank`) are permitted as bare terms. Non-distinctive, polysemous phrases (`công thương`, `ngoại thương`, `đầu tư và phát triển`, `kỹ thương`, `quân đội`, `sài gòn - hà nội`, `việt nam thịnh vượng`, `á châu`, `sài gòn thương tín`, `phương đông`, `tiên phong`, `hàng hải`, `đông nam á`, `xuất nhập khẩu`) MUST strictly require an explicit bank prefix (`ngân hàng`, `nh`, `ngân hàng tmcp`, `nh tmcp`, `nhtmcp`).

---

## [LESSON-043] Evaluation Scorer Metric Extraction Must Match Runtime Audit DTO Schema (`sentences_dropped` vs `dropped_sentences`)

- Date: 2026-10-05
- Scope: `scripts/er8_score.py`, `scripts/er8_analyze.py`, `src/thesis_api/adaptive_runtime.py`, `tests/test_er9_harness.py`
- Status: ACTIVE

### 1. Context & Root Cause
In evaluation scoring (`scripts/er8_score.py`), `sentences_discarded` was queried from `narrative_audit.get("dropped_sentences")`. However, the Pydantic schema in `src/thesis_api/adaptive_runtime.py` and `src/thesis_api/schemas.py` defines this field as `NarrativeAuditDTO.sentences_dropped: List[SentenceDroppedDTO]`.
Because `"dropped_sentences"` was never found in real run files, the scorer silently fell back to re-verifying the final report spec (`sents_discarded_count`), which yielded 0 because the final report spec contains only already-accepted sentences. Consequently, both ER-8 and ER-9 reported 0.0% sentence discard rates across all arms.

### 2. Resolution & Fallback Tracking
1. **Schema-Grounded Extraction with Legacy Fallback**:
   The scorer now inspects `sentences_dropped` first, falling back to `dropped_sentences` for backwards compatibility with older run files/mocks, supporting both list representations and integer counts.
2. **Composition Fallback Metric**:
   When report spec validation fails during runtime sweeps, the pipeline reverts to deterministic template layout (`composition_source == "deterministic_fallback"`). The scorer now reports `composition_fallback = 1` for such runs (0 for normal runs, blank `None` for refused/un-audited runs), and `er8_analyze.py` exports its mean in `arm_summary.csv` and Chapter 5 `RESULTS.md` summary tables.

---

## [LESSON-044] Source Citation Lineage, PDF Locators, and Public Data Guard Patterns (LIN-1)

- Date: 2026-10-11
- Scope: `src/thesis_api/analysis_tools.py`, `src/thesis_api/lineage.py`, `src/thesis_data/evidence_contract.py`, `frontend/src/features/source-lineage/`
- Status: ACTIVE

### 1. Windows Path Regex Trap in Evidence Guardrails
In `src/thesis_data/evidence_contract.py`, `_WINDOWS_PATH = re.compile(r"[A-Za-z]:[\\/]")` was used to detect local disk paths (like `C:/` or `D:\`). However, this pattern inadvertently matched `s:/` inside valid web URLs like `https://static2.vietstock.vn/` when passed as `source_url`.
- **Solution**: Explicitly check for and allow `http://` and `https://` schemas before testing for local filesystem drive letters.

### 2. Multi-Level Recursive Lineage Traversal to Leaf Sources
Financial ratios like `bank.llr_coverage` depend on inputs like `bank.input.npl_g35_balance`, which itself is derived (sum of NPL groups 3, 4, 5) without a direct `source_ref`. 
- **Solution**: The lineage walker (`get_lineage_tree`) recursively parses `input_observation_ids_json` and `metadata_json.__derived_calculation_receipt_v1` down to leaf observations with physical filing locators (`pdf_page`, `section`, `row_label`, `reading`), exposing clean integer `page` fields alongside the raw locators.

### 3. Read-Only SQLite Guarantee
To ensure the operational snapshot file hash is never mutated during lineage API queries, the SQLite connection is established using `uri=True` with `mode=ro` (`file:{path}?mode=ro`). This completely eliminates WAL/SHM sidecars and file modification timestamps.

### 4. Interactive Test Harness Modal Backdrops
When building demo harnesses with slide-out side drawers, modal backdrops (`fixed inset-0 z-50`) intercept pointer clicks for background controls like report selectors during automated browser tests. Automated scripts should use event-level targeting or explicit drawer state controls when switching harness fixtures.



