# Incident Record Template

> Dùng mẫu này để ghi nhận các sự cố, bug bất ngờ, hoặc edge case phát sinh trong quá trình triển khai task tại các worktree.

---

## [INCIDENT-YYYYMMDD-XXX] <Tóm tắt ngắn gọn sự cố>

- **Date:** YYYY-MM-DD
- **Reporter:** Worker (worker-data | worker-api | worker-ui | Lead)
- **Branch / Worktree:** `feat/...`
- **Component / Target File:** Đường dẫn file bị ảnh hưởng

### 1. Context (Bối cảnh)
Mô tả bối cảnh khi sự cố xảy ra: đang chạy script gì, test case nào, hay thao tác trên module nào.

### 2. Symptom (Triệu chứng)
- Thông báo lỗi, traceback, log chi tiết hoặc hành vi bất thường của hệ thống.
```text
<Paste error log / traceback here>
```

### 3. Root Cause (Nguyên nhân gốc rễ)
Phân tích nguyên nhân kỹ thuật tại sao lỗi xảy ra (do OS Windows, do cơ chế lock SQLite, do kiểu dữ liệu Null, lệch path, v.v.).

### 4. Workaround (Giải pháp xử lý tức thì)
Cách mà worker đã xử lý tại chỗ để vượt qua lỗi và hoàn thành task mà không làm gián đoạn tiến độ.

### 5. Action Item & Promotion Status
- **Proposed Action:** Đề xuất cải tiến dài hạn (thêm rule vào guardrails, sửa script khởi tạo worktree, update schema/contract, bổ sung test case).
- **Status:** `PENDING` <!-- Chuyển thành GRADUATED khi Lead Architect đã đưa vào hard rule hoặc script -->
- **Graduation Target:** `.agent/rules/guardrails.md` | `scripts/...` | `.agent/roles/...`
