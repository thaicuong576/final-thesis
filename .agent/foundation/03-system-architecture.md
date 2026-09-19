# System Architecture & Contract Freeze Principles

> **Tài liệu nền tảng cấp cao nhất (Spec Zero - Part 3)**  
> **Trạng thái**: Đóng băng (Frozen Foundation)  
> **Phạm vi áp dụng**: Bắt buộc cho toàn bộ các Agent Roles (`Lead`, `Worker-Data`, `Worker-API`, `Worker-UI`, `Auditor`).

---

## 1. TỔNG QUAN KIẾN TRÚC VÀ DÒNG CHẢY DỮ LIỆU (END-TO-END DATA FLOW)

Hệ thống được thiết kế theo mô hình phân lớp rõ ràng, đảm bảo tính đơn nhiệm và khả năng kiểm thử độc lập:

```
┌─────────────────────────────────────────────────────────────────────────┐
│                          TẦNG 1: DỮ LIỆU NGUỒN                          │
│   - BCTC kiểm toán PDF (thanhnp-uel / SBV / Issuer IR)                 │
│   - Bảng chuỗi thời gian thô từ FiinGroup / VNStock                    │
└────────────────────────────────────┬────────────────────────────────────┘
                                     │ (Ingestion & Hash Check)
                                     ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                     TẦNG 2: SQLITE STORAGE ENGINE                       │
│   - data/processed/finance_master_v2.sqlite (Chế độ WAL Mode)           │
│   - Đóng băng cấu trúc theo: contracts/schema.sql                       │
│   - Bảng: financial_observations, ratio_observations, document_records  │
└────────────────────────────────────┬────────────────────────────────────┘
                                     │ (Deterministic SQL / Provenance)
                                     ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                     TẦNG 3: PYTHON DATA FOUNDATION                      │
│   - src/thesis_data/ (Tính toán CAMEL, Safe Div, Unit Normalization)    │
│   - Không LLM: 100% code xác định, zero hallucination                  │
└────────────────────────────────────┬────────────────────────────────────┘
                                     │ (Data Provider & Tool Injection)
                                     ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                     TẦNG 4: HIERARCHICAL AGENT SYSTEM                   │
│   - src/thesis_agents/ (LangGraph / StateGraph Orchestration)           │
│   - Macro Specialist ──► Sector Specialist ──► Company Specialist       │
│                                                     │                   │
│                    Cross-Level Critic ◄─────────────┘                   │
│              (Phản biện & Hiệu đính Bounded Revision)                   │
└────────────────────────────────────┬────────────────────────────────────┘
                                     │ (Pydantic v2 DTOs)
                                     ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                     TẦNG 5: FASTAPI BACKEND GATEWAY                     │
│   - src/thesis_api/ (REST API Gateway)                                  │
│   - Endpoints: GET /api/health, GET /api/ready, POST /api/analyze       │
│   - Tuân thủ 100%: contracts/openapi.json                               │
└────────────────────────────────────┬────────────────────────────────────┘
                                     │ (JSON over HTTP / Mock Fallback)
                                     ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                     TẦNG 6: FRONTEND WORKBENCH UI                       │
│   - frontend/ (React 19, Vite, Tailwind CSS, Retro Workbench)           │
│   - Tuân thủ mock data: contracts/mock-data.json                        │
│   - 3 Screens: Query Composer ──► Live Session ──► Financial Report     │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## 2. NGUYÊN TẮC ĐÓNG BĂNG HỢP ĐỒNG (CONTRACT FREEZE PRINCIPLES)

Ba tệp mỏ neo trong `contracts/` là **Single Source of Truth** tuyệt đối giữa các tầng và giữa các role kỹ sư:

### 2.1. Hợp đồng Cơ sở dữ liệu: `contracts/schema.sql`
- **Mục đích**: Định nghĩa cấu trúc chuẩn của SQLite `finance_master_v2.sqlite`.
- **Nguyên tắc**:
  - Mọi thay đổi DDL (thêm bảng, sửa cột, tạo index) BẮT BUỘC phải được Lead Architect phản ánh trong `contracts/schema.sql` TRƯỚC khi Worker Data viết script migration trong `scripts/migrations/`.
  - Nghiêm cấm chạy lệnh DDL trực tiếp trên SQLite mà không có hợp đồng trong `schema.sql`.

### 2.2. Hợp đồng API: `contracts/openapi.json`
- **Mục đích**: Quy định chuẩn giao tiếp mạng giữa Backend (`src/thesis_api/`) và Frontend (`frontend/`).
- **Endpoint trọng tâm `POST /api/analyze`**:
  - **Request**:
    ```json
    {
      "query": "string (Câu hỏi tự nhiên)",
      "target_ticker": "string (ACB, TCB, MBB...)",
      "peer_tickers": ["array of strings"],
      "period": "string (2024, 2024_Q4...)"
    }
    ```
  - **Response**: Bắt buộc chứa 6 khối dữ liệu:
    1. `report_id`: Chuỗi định danh báo cáo.
    2. `status`: Trạng thái xử lý (`completed`, `error`).
    3. `macro_context`: Bối cảnh vĩ mô và lãi suất điều hành NHNN.
    4. `sector_benchmark`: Số liệu trung vị ngành (peer median ROE, NIM, NPL, CIR, CASA).
    5. `company_insights`: Mảng phân tích chi tiết sức khỏe tài chính từng ngân hàng.
    6. `cross_level_critique`: Mảng phát hiện mâu thuẫn giữa hiệu quả doanh nghiệp và toàn ngành.
    7. `evidence_trail`: Mảng bằng chứng số liệu trích dẫn trực tiếp từ BCTC kiểm toán.

### 2.3. Hợp đồng Dữ liệu Giả lập: `contracts/mock-data.json`
- **Mục đích**: Cung cấp payload chuẩn xác 100% theo `openapi.json` để Worker UI phát triển và kiểm thử giao diện độc lập (decoupled development), không phụ thuộc vào trạng thái deploy backend hay kết nối LLM.
- **Nguyên tắc**:
  - **CẤM BỊA KIỂU DỮ LIỆU Ở FRONTEND**: Worker UI không được tự định nghĩa thêm trường dữ liệu nào trong TypeScript interface của component mà không có trong `contracts/mock-data.json` hoặc `contracts/openapi.json`.
  - Mọi mock scenarios trong `frontend/src/features/analysis-session/mock/` phải là phép chiếu trực tiếp từ hợp đồng này.

---

## 3. CÁC RÀO CHẮN KIẾN TRÚC BẮT BUỘC (ARCHITECTURAL GUARDRAILS)

Theo quy định tại `docs/ARCHITECTURAL-GUARDRAILS.md` và `AGENTS.md`:

1. **Ranh giới Ứng dụng & Dữ liệu (Application-First Boundary)**:
   - Các module trong `src/` không được phụ thuộc ngược vào các công cụ đánh giá thử nghiệm hay thư mục `research/`.
   - Cơ sở dữ liệu SQLite chạy độc lập, có thể sao lưu và di chuyển (`transferability`).
2. **Cơ chế SQLite WAL Mode**:
   - `data/processed/finance_master_v2.sqlite` bắt buộc chạy ở chế độ **WAL (Write-Ahead Logging)**:
     ```sql
     PRAGMA journal_mode = WAL;
     PRAGMA busy_timeout = 30000;
     ```
   - Cho phép nhiều tiến trình đọc đồng thời trong khi một tiến trình ghi cập nhật, chống hoàn toàn lỗi `database is locked`.
3. **Đồng bộ Môi trường qua NTFS Hardlink**:
   - Khi khởi tạo Git Worktrees, file cấu hình `.env` được liên kết cứng (`mklink /H .env ..\.env`) để chia sẻ cấu hình API keys mà không sao chép rò rỉ bí mật.
4. **Kiểm tra Guardrails Tự động**:
   - Trước khi bất kỳ PR nào được hợp nhất, lệnh sau bắt buộc phải trả về PASS:
     ```bash
     python scripts/check_architecture_guardrails.py
     ```
