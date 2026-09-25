# System Architecture & Source-of-Truth Foundation

> **Tài liệu nền tảng cấp cao nhất (Spec Zero - Part 3)**  
> **Trạng thái**: Đóng băng (Frozen Foundation)  
> **Phạm vi áp dụng**: Bắt buộc cho toàn bộ các Agent Roles (`Lead`, `Worker-Data`, `Worker-API`, `Worker-UI`, `Auditor`).

---

## 1. TỔNG QUAN ĐỊNH DANH DỰ ÁN & NORTH STAR

Dự án này là một **kiến trúc phân tích tài chính đa-agent có khả năng tái sử dụng (Reusable Financial Analysis Architecture)**, trong đó hệ thống không chạy một pipeline cố định mà lập kế hoạch theo từng yêu cầu phân tích (**Query-Adaptive Planning**) và chỉ kích hoạt những năng lực phân tích thực sự cần thiết.

- **Năng lực phân tích độc lập (Analytical Capabilities)**: `Macro`, `Sector/Peer` và `Company` là các capabilities độc lập, không phải ba stage bắt buộc phải chạy tuần tự.
- **Mục tiêu cốt lõi**: Tạo ra các phân tích có thể truy xuất ngược đến dữ liệu và bằng chứng, có kiểm soát chất lượng xác định được bằng luật, có semantic critique và bounded revision, đồng thời giữ ranh giới đủ sạch để frontend, database, orchestration framework hoặc data provider có thể được thay thế mà không phải viết lại analytical core.
- **Web Application**: Chỉ là **Reference Implementation** để chứng minh kiến trúc end-to-end, không phải bản thân kiến trúc.

> **Tuyên ngôn North Star (Formal Charter Mandate)**:  
> *"A reusable, query-adaptive hierarchical multi-agent financial-analysis architecture in which an Orchestrator plans and composes only the analytical capabilities required by each request, with evidence-grounded outputs, bounded critique/revision, deterministic quality controls, and replaceable enterprise data interfaces, demonstrated through an end-to-end web application for financial analysts."*

---

## 2. MÔ HÌNH CHÂN LÝ PHÂN TẦNG (SOURCE-OF-TRUTH HIERARCHY)

Dự án không có một “source of truth” duy nhất cho mọi loại thông tin, mà được tổ chức theo tầng và theo trách nhiệm:
1. **Product Intent & Mục tiêu Nghiên cứu**: Được xác định bởi các canonical product/spec documents (`.agent/foundation/*`, `docs/SPEC.md`).
2. **Ràng buộc Kiến trúc (Architecture Constraints)**: Được xác định bởi `docs/ARCHITECTURE.md`, `docs/CONSTRAINTS.md` và `docs/ARCHITECTURAL-GUARDRAILS.md`.
3. **Ngữ nghĩa Dữ liệu (Data Semantics)**: Được xác định bởi `docs/DATA-CONTRACT.md` và executable schemas (`contracts/*`).
4. **Dữ liệu phân tích trong một Run**: Được xác định bởi một `DatasetSnapshot` cụ thể.
5. **Phạm vi và Năng lực kích hoạt**: Được xác định bởi `AnalysisPlan` đã freeze.
6. **Nhận định Thực tế (Factual Statements)**: Phải truy ngược được về `AtomicClaim`, bằng chứng và xuất xứ (`provenance`).

> **Thứ bậc Thẩm quyền (Authority Order)**:  
> `Project Constitution & Canonical Specs` $\rightarrow$ `Executable Contracts` $\rightarrow$ `Runtime Implementation`.  
> *Historical documents, experiment runs và phase records có giá trị tái hiện lịch sử nhưng không được override current canonical architecture.* Khi có mâu thuẫn giữa code và spec, code không tự động là truth mà được coi là **contract drift** cần xử lý có chủ đích.

---

## 3. BA ĐỐI TƯỢNG CHÂN LÝ RUNTIME CỐT LÕI (THREE CORE RUNTIME TRUTH OBJECTS)

Toàn bộ tính tái hiện (reproducibility) và giải trình (explainability) của hệ thống tựa trên 3 hợp đồng trung tâm:

### 3.1. `AnalysisPlan` (Ràng buộc Thực thi)
- Là source of truth cho phạm vi thực thi của từng request.
- Khi nhận objective từ người dùng, Planner xác định entities, periods, metrics, required capabilities, applicability, applicable cross-level links, dataset snapshot identity và known limitations, sau đó **freeze plan trước execution**.
- Một plan đã freeze **không được mutate** giữa chừng vì dữ liệu thay đổi. Nếu dataset hoặc capability catalog thay đổi sau khi plan được tạo, hệ thống phải tạo snapshot/catalog mới và re-plan thay vì sửa ngầm run đang chạy.

### 3.2. `DatasetSnapshot` (Ràng buộc Tri thức/Dữ liệu)
- Dữ liệu trong hệ thống phân biệt rõ ràng giữa:
  - `Raw Evidence`: Thu thập có hash, timestamp và nguồn gốc.
  - `Candidate Observations`: Dữ liệu đã parse/normalize nhưng chưa kiểm định.
  - `Canonical Analytical Data`: Dữ liệu đã đi qua validation, reconciliation và acceptance.
- `downloaded`, `parsed` và `candidate` **không đồng nghĩa** với `accepted`.
- Một analysis run chỉ được sử dụng dữ liệu đã resolve qua provider boundary và được ràng buộc bởi `DatasetSnapshot` mà `AnalysisPlan` đã freeze.

### 3.3. `AtomicClaim` (Ràng buộc Kết quả Đầu ra)
- Báo cáo phân tích (Report) không phải factual source of truth, mà chỉ là presentation layer của một claim graph có nguồn gốc rõ ràng.
- Chuỗi kiến tạo chân lý bất biến:
  ```text
  evidence → structured assertion → AtomicClaim → synthesis → report statement
  ```
- Mỗi statement quan trọng trong báo cáo phải truy ngược được về `claim_id`, `evidence_reference`, `source_metadata` và `provenance`.
- LLM có thể hỗ trợ reasoning và synthesis, nhưng **nghiêm cấm đưa factual assertions mới** vào report nếu assertions đó không tồn tại trong claim/evidence structure.

---

## 4. MÔ HÌNH NĂNG LỰC PHÂN TÍCH (CAPABILITY MODEL)

- Unit thiết kế quan trọng là **Analytical Capability** (không phải những nhân vật agent cố định trong pipeline).
- Mỗi capability có input contract, applicability rule, evidence resolution boundary, analytical logic và structured output contract riêng:
  - `Macro Policy Context Capability`: Phân tích chính sách tiền tệ, lãi suất điều hành, trần tín dụng.
  - `Sector / Peer Comparison Capability`: Tính toán phân vị và trung vị đối thủ trong ngành.
  - `Company Financial Performance Capability (CAMEL)`: Bóc tách sức khỏe tài chính ngân hàng theo 5 trụ cột CAMEL.
- **Nguyên tắc Query-Adaptive**: Một capability không applicable thì **không chạy**, và trạng thái đó không phải là failure.
- **Liên kết Xuyên tầng (Cross-Level Links)**: Tổng hợp xuyên tầng chỉ được thực hiện khi `AnalysisPlan` khai báo `ApplicableLink` tương ứng. Không được tự động kéo bối cảnh vĩ mô hoặc ngành vào một yêu cầu chỉ phân tích doanh nghiệp (`company-only`) chỉ vì capability đó tồn tại.

---

## 5. HAI LỚP KIỂM SOÁT CHẤT LƯỢNG VÀ NGHIỆM THU (QUALITY & ACCEPTANCE BOUNDARY)

Hệ thống phân định rạch ròi giữa 2 lớp kiểm soát chất lượng:

```text
Specialist Outputs → Synthesis → AtomicClaim[] → Stage-1 → Semantic Critic
                                                   │            │
                                             FAIL CLOSED   Decision
                                                                │
                                    Targeted revision (<= 2 rounds)
                                      → Re-synthesis → Stage-1 again
```

### 5.1. Stage 1: Deterministic Acceptance (Kiểm tra Toàn vẹn Xác định luận)
- Chịu trách nhiệm cho **Hard Integrity**: Độ chính xác số học, đối soát bằng chứng (evidence resolution), tính hợp lệ của tham chiếu, tuân thủ phạm vi plan, chặn mâu thuẫn logic cứng.
- Kiểm tra 100% bằng code và quy tắc xác định, không dùng LLM.
- **Nguyên tắc cứng**: Một sai lệch số học hoặc trích dẫn thiếu bằng chứng BẮT BUỘC bị REJECT tại Stage 1, tuyệt đối không chuyển sang Semantic Critic để "đánh giá tương đối".

### 5.2. Stage 2: Semantic Critique & Bounded Revision (Phản biện Ngữ nghĩa Có giới hạn)
- Chỉ chạy sau khi Stage 1 đã đạt yêu cầu.
- Đánh giá: Độ bám sát bằng chứng (groundedness), độ bao phủ câu hỏi (answer coverage), tính hợp lý logic (soundness), xử lý bất định và tính nhất quán xuyên tầng đối với các `ApplicableLink`.
- **Bounded Revision**: Giới hạn tối đa **2 vòng hiệu đính** (max 2 revision rounds) và chỉ chạy lại đúng capability bị ảnh hưởng. Không lặp vô hạn.
- `ACCEPT_WITH_LIMITATIONS` chỉ hợp lệ khi dữ liệu thực tế thiếu sau khi Stage 1 đã pass; không dùng để che giấu sai số số học, bằng chứng bịa đặt hoặc lỗi provider.

---

## 6. RANH GIỚI TRỪU TƯỢNG HÓA HẠ TẦNG (FRAMEWORK & INFRASTRUCTURE BOUNDARY)

- **Lõi phân tích (Analytical Core) độc lập tuyệt đối**:
  - `LangGraph`: Chỉ là reference control-plane adapter cho orchestration.
  - `FastAPI`: Chỉ là HTTP application gateway boundary.
  - `SQLite / Gold`: Là storage adapter cho demo, testing và research benchmarks.
  - `Supabase / PostgreSQL`: Là application persistence provider.
  - `Vercel / Render`: Là deployment hosting providers.
- **Mô hình Trừu tượng hóa Đa tầng**:
  ```text
  Analyst Interface ──► Application Boundary ──► Analysis Runtime ──► Capabilities ──► Provider Interfaces ──► Data Sources
  ```
- **Nguyên tắc Thay thế (Replaceability Principle)**:
  Nếu thay thế SQLite bằng PostgreSQL/Snowflake, hoặc thay LangGraph bằng framework orchestration khác, hoặc thay Vercel/Render bằng hạ tầng nội bộ doanh nghiệp, **Analytical Core không bao giờ phải viết lại**.

---

## 7. QUYỀN HẠN FRONTEND & LƯU TRỮ (FRONTEND & PERSISTENCE BOUNDARIES)

### 7.1. Quyền hạn của Frontend (Frontend Authority)
- Frontend là **Analyst Workspace** và **Reference Client**, không phải source of truth cho ngữ nghĩa phân tích.
- Việc người dùng tick chọn filter trên UI không quyết định capability nào bắt buộc phải chạy nếu server-side Planner và dataset capability catalog không xác nhận tính hợp lệ.
- Frontend chỉ truyền request intent và hiển thị run state, evidence, claims và reports. Toàn bộ logic về applicability, planning, claim generation, acceptance và revision nằm ở backend/core.

### 7.2. Ranh giới Lưu trữ (Persistence Boundary)
- Tách biệt hoàn toàn giữa **Application Persistence** (lưu phân tích, sự kiện, report metadata, trạng thái phiên làm việc trong Supabase/PostgreSQL) và **Canonical Analytical Data** (dữ liệu tài chính chuẩn tắc).
- Core không gọi SDK Supabase trực tiếp khắp nơi mà đi qua Repository / Provider Interfaces rõ ràng.

---

## 8. HỢP ĐỒNG ĐÓNG BĂNG & RÀO CHẮN BẮT BUỘC (CONTRACTS & GUARDRAILS)

Ba tệp mỏ neo trong `contracts/` là Single Source of Truth giữa các tầng và các roles:
1. `contracts/schema.sql`: DDL chuẩn tắc của cơ sở dữ liệu phân tích SQLite `finance_master_v2.sqlite`.
2. `contracts/openapi.json`: Chuẩn giao tiếp REST API giữa Gateway và Client (`POST /api/analyze`).
3. `contracts/mock-data.json`: Bộ dữ liệu mẫu chuẩn hóa 100% phục vụ decoupled development cho Frontend.

### Rào chắn Kiến trúc Bắt buộc (Architectural Guardrails):
1. **SQLite WAL Mode**: `data/processed/finance_master_v2.sqlite` bắt buộc chạy `PRAGMA journal_mode = WAL;` và `PRAGMA busy_timeout = 30000;`.
2. **Worktree Database Isolation**: Không hardlink SQLite database hoặc file
   `-wal`/`-shm` giữa root và worktree. `worker-start` dùng SQLite backup API để
   tạo snapshot độc lập, kiểm tra integrity và bật WAL cho bản copy. Test và API
   local chỉ được ghi vào bản worktree/temp; artifact nguồn ở root là read-only.
3. **NTFS Hardlinks**: Chỉ đồng bộ `.env` giữa root và các `.worktrees/` qua hardlink (`mklink /H`).
4. **Kiểm tra Guardrail Tự động**: Lệnh `python scripts/check_architecture_guardrails.py` bắt buộc phải trả về PASS trước mọi đợt merge.

## 9. Trạng thái triển khai tham chiếu ngày 2026-09-25

API đã kết nối Company và Sector/Peer một kỳ vào plan đóng băng trước truy vấn,
synthesis, Stage-1, semantic critique và tối đa hai vòng targeted revision.
Scope của Gold chỉ được bổ sung qua authority sidecar khai báo rõ và kiểm hash
theo D-073; core vẫn chỉ nhận dữ liệu qua provider. Metadata nhóm yêu cầu và
nhóm có dữ liệu hợp lệ được giữ riêng để giải thích mẫu số.

Các test offline xác minh luồng điều phối; chưa chứng minh chất lượng phân tích
của model thật hoặc khả năng dùng ứng dụng đã triển khai. Multi-period và macro
chưa được hỗ trợ trên API này. Bộ câu hỏi cuối vẫn pre-freeze. Quy trình CI
Python kiểm contract và suite trong checkout; bằng chứng ignored có gate riêng.

Application run history uses contracts/run-store-schema.sql on its separate ANALYSIS_RUNS_DB_PATH. contracts/schema.sql remains the analytical schema contract; accepted snapshots are never initialized or migrated for run history.
