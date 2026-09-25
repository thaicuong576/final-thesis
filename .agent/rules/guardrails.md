# SYSTEM & WORKSPACE GUARDRAILS

## 1. Zero Root Code Modification (Bất biến)
- Thư mục gốc (`final-thesis/`) CHỈ dùng cho:
  1. Lead Orchestrator cập nhật `contracts/`.
  2. Quản trị môi trường chung (`.venv`, `node_modules`, `.env`).
  3. Git merge và đồng bộ nhánh `main`.
- Tuyệt đối KHÔNG viết code tính năng, sửa đổi file trong `src/`, `frontend/`, `data/` trực tiếp tại thư mục gốc.

## 2. Git Worktree Mandate
- Mọi worker BẮT BUỘC hoạt động bên trong `.worktrees/<branch-name>/`.
- Khởi tạo worktree bằng script:
  - Bash: `bash scripts/worker-start.sh feat/<domain>-<task-name>`
  - PowerShell (Windows): `.\scripts\worker-start.ps1 -BranchName feat/<domain>-<task-name>`
- Trước khi code, phải verify lệnh `pwd` hoặc `(Get-Location).Path` nằm trong thư mục con của `.worktrees/`.

## 3. Single Source of Truth (Contracts)
- Mọi API route, DB table, UI component phải tuân thủ nghiêm ngặt các file trong `contracts/`:
  - `contracts/schema.sql`: Định nghĩa bảng và kiểu dữ liệu SQLite chuẩn từ `finance_master_v2.sqlite`.
  - `contracts/openapi.json`: Chuẩn request/response API.
  - `contracts/mock-data.json`: Dữ liệu mẫu dùng cho UI testing và mock response.
- Worker chỉ có quyền ĐỌC `contracts/`. Nếu phát sinh nhu cầu sửa schema, phải báo cáo lại cho Orchestrator.

## 4. Definition of Done (DoD)
- Code đi kèm unit test tương ứng:
  - Backend/Core: Chạy `$env:PYTHONPATH='src'; python -m unittest discover -s tests -q` (hoặc `pytest` nếu cài đặt).
  - Frontend: Chạy `npm test -- --run` (Vitest).
- Đảm bảo toàn bộ test nội bộ của module PASS 100%.
- Kiểm tra guardrails hệ thống: `python scripts/check_architecture_guardrails.py` phải trả về `PASS`.
- Commit theo chuẩn Conventional Commits (`feat(api): ...`, `feat(ui): ...`, `test: ...`).
- Push branch lên remote: `git push -u origin <branch-name>` và tạo PR (hoặc báo user duyệt).

## 5. SQLite Concurrency & Schema Migration Invariants
- **WAL Mode Mandate:** File database `finance_master_v2.sqlite` bắt buộc chạy ở chế độ WAL. Worker Data khi ghi dữ liệu không được phép ngắt WAL mode.
- **No Shared Mutable SQLite Files:** Không hardlink database, WAL hoặc SHM giữa
  root và worktree. Worktree dùng SQLite backup snapshot độc lập; test chỉ ghi
  vào worktree/temp copy và phải xác nhận hash artifact nguồn không đổi.
- **Contract-First Schema Evolution:**
  - Nếu chỉ thêm/sửa dữ liệu (DML: INSERT, UPDATE): Worker Data tự do thực thi trong worktree.
  - Nếu thay đổi cấu trúc bảng/cột/index (DDL: CREATE TABLE, ALTER TABLE): BẮT BUỘC cập nhật `contracts/schema.sql` trước và được review duyệt. Không bao giờ chạy migration ngầm trên SQLite mà chưa có diff trên `contracts/schema.sql`.

## 6. Environment & Secret Invariants
- File `.env` tại worktree là Hardlink trỏ về root `.env`.
- Bất kỳ worker nào bổ sung biến môi trường mới BẮT BUỘC phải khai báo tên biến và giá trị mẫu vào file `.env.example` (file này được Git track). Tuyệt đối không commit giá trị secret thật lên Git.
