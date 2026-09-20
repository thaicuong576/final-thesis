# Definition of Done (DoD) & Acceptance Criteria

> **Tài liệu nền tảng cấp cao nhất (Spec Zero - Part 4)**  
> **Trạng thái**: Đóng băng (Frozen Foundation)  
> **Phạm vi áp dụng**: Tiêu chuẩn nghiệm thu tối thượng cho mọi PR và Task của tất cả các Agent Roles.

---

## 1. BỐN TRỤ CỘT NGHIỆM THU TỐI THƯỢNG (CORE DOD CRITERIA)

Một tính năng, một module hoặc một nhánh phát triển chỉ được coi là **HOÀN THÀNH (DONE)** khi thỏa mãn đồng thời cả 4 trụ cột dưới đây:

---

### Trụ cột 1: Truy vết Nguồn gốc & Chuỗi Chân lý Khẳng định (Metric & Claim Provenance)
Mọi số liệu tài chính hiển thị trên giao diện (bảng số liệu, biểu đồ CAMEL, tóm tắt chỉ số) hoặc trích dẫn trong báo cáo phân tích BẮT BUỘC phải tuân thủ chuỗi kiến tạo chân lý:
```text
evidence → structured assertion → AtomicClaim → synthesis → report statement
```

1. **Truy nguyên tầng Dữ liệu (Database Provenance)**:
   - Mỗi giá trị số phải gắn liền với bản ghi trong `financial_observations` hoặc `ratio_observations` trong SQLite (`finance_master_v2.sqlite`).
   - Phải có đầy đủ siêu dữ liệu: `ticker`, `period`, `statement_type`, `field_code`, `unit` và `quality_status = 'valid'`.
2. **Truy nguyên tầng Bằng chứng (Document Evidence Trail)**:
   - Mỗi số liệu trích dẫn phải liên kết đến `document_records` hoặc `source_records`.
   - Phải cung cấp định danh tài liệu (`source_document`), số trang (`page_number`), và vị trí bảng/dòng cụ thể (`source_locator`, ví dụ: `page:42;table:Báo cáo kết quả hoạt động kinh doanh;row:Thu nhập lãi thuần`).
3. **Cấm tuyệt đối số liệu mồ côi (Zero Orphan Metrics / Zero Orphan Claims)**:
   - Nghiêm cấm đưa ra nhận định hoặc con số tài chính mà không có bản ghi xuất xứ trong cơ sở dữ liệu và liên kết đến `AtomicClaim`.

---

### Trụ cột 2: Toàn vẹn Bộ Kiểm thử 100% (Test Suite Integrity & Stage-1 Deterministic Gate)
Mọi thay đổi code không được phép gây ra hồi quy (regression). Trước khi đề xuất merge, tất cả các bộ kiểm tra sau phải PASS hoàn toàn:

| Lớp kiểm thử | Lệnh thực thi | Tiêu chuẩn PASS bắt buộc |
|---|---|---|
| **Architecture Guardrails** | `python scripts/check_architecture_guardrails.py` | `ARCHITECTURE_GUARDRAILS: PASS` |
| **Backend Unit Tests** | `$env:PYTHONPATH="src"; python -m unittest discover -s tests -q` | `Ran 503 tests... OK` (0 failures, 0 errors) |
| **Frontend Unit Tests** | `cd frontend; npm test -- --run` | `46 passed (46)` |
| **Frontend Build Integrity** | `cd frontend; npm run build` | Build thành công (`tsc -b && vite build`), zero lỗi TypeScript |

> **Lưu ý trên Windows PowerShell**: Khi chạy unit test backend, thiết lập biến môi trường `$env:PYTHONPATH="src"` trước khi gọi `python -m unittest` để đảm bảo nhận diện đầy đủ các package `thesis_data` và `thesis_api`.

---

### Trụ cột 3: Kỷ luật Ranh giới Git Worktree & Không Commit Chéo Folder
Để đảm bảo nhiều tác tử/kỹ sư làm việc song song không gây xung đột mã nguồn:

1. **Cô lập trong Git Worktree**:
   - Tất cả các worker bắt buộc phải làm việc trong thư mục worktree riêng biệt nằm trong `.worktrees/`.
   - Khởi tạo qua script: `powershell -File scripts/worker-start.ps1 feat/THES-X-<task>` hoặc `bash scripts/worker-start.sh feat/THES-X-<task>`.
2. **Không commit chéo folder (Strict Boundary Separation)**:
   - **Worker Data**: Chỉ commit trong `data/`, `src/thesis_data/`, `scripts/migrations/`, `tests/test_*data*.py`...
   - **Worker API**: Chỉ commit trong `src/thesis_api/`, `src/thesis_agents/`, `tests/test_api_*.py`...
   - **Worker UI**: Chỉ commit trong `frontend/`.
   - **Lead Architect**: Thẩm định và quản lý `contracts/` và `.agent/`.
   - Bất kỳ diff nào vi phạm ranh giới thư mục đều sẽ bị **Auditor REJECT ngay lập tức**.
3. **Quy chuẩn Commit và Pull Request**:
   - Tiêu đề commit theo Conventional Commits: `feat:`, `fix:`, `test:`, `docs:`, `chore:`.
   - Không commit trực tiếp lên nhánh `main`. Nhánh `main` chỉ được cập nhật thông qua Pull Request trên GitHub sau khi User phê duyệt.

---

### Trụ cột 4: SDLC là Bất biến Dự án & Triển khai Staging (SDLC as a Project Invariant)
1. **Nhịp Delivery Chuẩn tắc**:
   `branch (worktree) → tests → PR → review → merge → staging deploy → smoke test`
2. **Nghiệm thu End-to-End**:
   - Đối với các vertical slice quan trọng, code complete hoặc PR merged chưa đủ để xem là hoàn thành nếu có tác động tới application runtime.
   - Bắt buộc kiểm tra smoke test trên môi trường staging (Vercel Preview / Render) để xác nhận hệ thống vận hành đúng trước khi đóng task.

---

## 2. QUY TRÌNH NGHIỆM THU CỦA AUDITOR (AUDITOR SIGN-OFF CHECKLIST)

Khi worker hoàn tất task và yêu cầu kiểm định, Auditor sẽ rà soát tuần tự:

```text
[ ] 1. WORKTREE CHECK   : Worker có làm việc trong .worktrees/ không?
[ ] 2. BOUNDARY CHECK   : Diff có vi phạm ranh giới thư mục không?
[ ] 3. CONTRACT CHECK   : Có tự ý sửa contracts/ không?
[ ] 4. GUARDRAILS CHECK : check_architecture_guardrails.py -> PASS?
[ ] 5. BACKEND TESTS    : 499/499 tests -> PASS?
[ ] 6. FRONTEND TESTS   : 46/46 tests -> PASS?
[ ] 7. FRONTEND BUILD   : npm run build -> PASS?
[ ] 8. PROVENANCE CHECK : Dữ liệu có nguồn gốc rõ ràng, không số liệu bịa?
```

Chỉ khi tất cả 8 mục trên đều đạt dấu `[x]`, Auditor mới xuất bản báo cáo thẩm định chấp thuận: `VERDICT: APPROVED FOR SQUASH MERGE`.
