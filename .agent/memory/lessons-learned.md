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

## [LESSON-017] A correct ignored artifact can still conflict with project truth

- **Date:** 2026-09-25
- **Scope:** VPB ROE comparative eligibility and Gold v5 provenance
- **Status:** active pending distinct reviewer confirmation under D-072.

The official VPB filings, two-checker adjudicated ledger and Gold v5 values
support parent-attributable ROE, while D-063's former factual clause said total
equity was used. The raw PDFs, candidate/review ledgers and SQLite snapshot are
local ignored artifacts, so the committed authority record binds their exact
hashes and locators without claiming that the files themselves are committed.

The stale packet README and v1 status manifest were found to contradict the
adjudicated ledger. Their status records are now superseded by Git-bound
records linked to the authority manifest. The original promotion ledger also
has blank `register_review_status` values for the four VPB ROE targets. That
blank is preserved; a status sidecar points to the separate adjudicated ledger
for the accepted checker/adjudication state and makes no new review claim. The
v5 comparative-definition gate returns eligible for its 80-cell scope, but
D-072 keeps VPB excluded until a distinct reviewer confirms the linked records
and gate result. A `valid` row, a recent timestamp or correct local arithmetic
does not replace durable provenance or that independent confirmation.

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
