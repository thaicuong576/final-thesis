# Hiện Trạng Thực Tế Dự Án (Project As-Is Status)

> **Cập nhật ngày:** 24/09/2026  
> **Repository:** 	haicuong576/final-thesis (Branch: main)  
> **Mục tiêu:** Hệ thống Đa tác tử Phân cấp Phân tích Ngành Ngân hàng & Chứng khoán Việt Nam  
> **Trạng thái thực tế:** ~40-45% toàn bộ khối lượng đề tài khóa luận (Hoàn thành Walking Skeleton & Data Ngân hàng; Chưa làm Chứng khoán & Benchmark Đánh giá).

---

## 1. Bản đồ Vòng đời Phát triển (Lifecycle Phase Map)

`	ext
research ➔ specification ➔ plan ➔ data foundation ➔ baseline ➔ hierarchical system ➔ [EVALUATION & PREVIEW DEPLOYMENT] ➔ retest ➔ release
`

| Giai đoạn | Tiến độ | Đánh giá hiện trạng thực tế |
|---|:---:|---|
| **1. Research (Nghiên cứu)** | **80%** | Đã phân tích mô hình CAMEL cho ngân hàng, chính sách tiền tệ NHNN. **Chưa nghiên cứu bộ chỉ số cho ngành chứng khoán**. |
| **2. Specification (Quy chuẩn)** | **90%** | Đã có Spec Zero (.agent/foundation/*), Contracts OpenAPI & SQLite DDL. |
| **3. Plan & SDLC (Quy trình)** | **100%** | Quy trình phân phối Git Worktree, Linear MCP (THES-1 -> THES-14), CI/CD GitHub Actions & Vercel. |
| **4. Data Foundation (Dữ liệu)** | **50%** | **Ngân hàng:** Đã nạp 27 NHTM (2021–2024, 16 quý, CAMEL ratios) vào inance_master_v2.sqlite.<br>**Chứng khoán:** Đã có raw JSON (data/raw/.../vci_finance/) cho SSI, VND, VCI, HCM, MBS, TCBS nhưng **chưa ingest vào SQLite**. |
| **5. Baseline Engine** | **70%** | Code tính toán tài chính deterministic cho ngân hàng đã xong. Chưa có baseline mô hình chứng khoán. |
| **6. Multi-Agent System** | **50%** | **Prototype sơ khai:** Mới là pipeline tuần tự trong service.py, **chưa dùng LangGraph state machine**. Gateway LLM DeepSeek đang lỗi 503 nên hệ thống đang chạy bằng fallback code mẫu. |
| **7. Preview Deployment** | **90%** | Frontend sống tại https://fin-ai.eddiephung.me. Backend sống tại https://final-thesis-zgwt.onrender.com. Đã có bảng nalysis_runs lưu lịch sử vào SQLite. |
| **8. Evaluation (Thực nghiệm)** | **0%** | **Chưa bắt đầu:** Chưa có tập câu hỏi benchmark, chưa đo lường so sánh Multi-Agent vs Single-Agent, chưa tính Hallucination Rate hay Grounding Ratio. |
| **9. Release & Luận văn** | **30%** | Đã có bản thảo thô Chapters 1–4 trong docs/. Chưa có kết quả thực nghiệm để viết Chapter 5 (Kết quả & Đánh giá). |

---

## 2. Những Gì Đang Hoạt Động Thật (Working Features)

1. **Cơ sở Dữ liệu Tài chính Ngân hàng (inance_master_v2.sqlite)**:
   - 27 Ngân hàng thương mại Việt Nam niêm yết.
   - 16 kỳ quý (từ 2021_Q1 đến 2024_Q4).
   - Các chỉ số CAMEL: ROE, NIM, NPL, CAR, CASA, CIR, LDR kèm nguồn gốc dữ liệu (provenance).
   - Bật chế độ WAL (Write-Ahead Logging) cho phép đọc/ghi đồng thời không khóa.
2. **Lưu trữ Lịch sử Phân tích (nalysis_runs)**:
   - Tự động lưu mọi phiên phân tích vào SQLite gồm: câu hỏi, ticker mục tiêu, các ticker so sánh, kết quả sự kiện, full JSON báo cáo, độ trễ xử lý.
   - Các API hoạt động: GET /api/runs, GET /api/runs/{id}, GET /api/reports/{id}.
3. **Frontend Giao diện Phân tích (rontend/)**:
   - **Screen 1 (Composer)**: Chip chọn nhanh ngân hàng (+ ACB, + VCB, + MBB, + TCB, + CTG), hiển thị danh mục 27 ngân hàng từ /api/capabilities, danh sách lịch sử phân tích từ /api/runs.
   - **Screen 2 (Live Session)**: Luồng SSE phát sự kiện tức thì (<100ms), kết nối trực tiếp Render Backend trên domain production, huy hiệu tác tử, cơ chế Retry.
   - **Screen 3 (Report Page)**: Báo cáo tài chính CAMEL đọc trực tiếp từ database qua /api/reports/{id} (loại bỏ hoàn toàn mock fallback), Claim Graph và Evidence Trail minh bạch.

---

## 3. Các Điểm Nghẽn & Vấn Đề Kỹ Thuật Chưa Giải Quyết (Honest Gaps)

1. **LLM Gateway đang lỗi 503**:
   - Provider Codely Pixverse (deepseek-v4-pro-0813) báo lỗi model_not_found / hết quota kênh.
   - Mọi phân tích hiện tại đang tự động chạy vào deterministic fallback (sinh văn bản theo khuôn mẫu định sẵn trong Python, chưa có suy luận AI thật).
2. **Kiến trúc Tác tử chưa phải LangGraph**:
   - Ban đầu quy hoạch dùng LangGraph Supervisor/Worker. Hiện tại đang viết bằng hàm generator Python tuần tự + ThreadPoolExecutor trong service.py.
3. **Mảng Chứng khoán (50% đề tài) chưa được tích hợp**:
   - Dù có raw data nhưng chưa xây dựng schema tỷ lệ tài chính chứng khoán (Doanh thu môi giới, Lãi FVTPL, Dư nợ margin) vào database.
4. **Chưa có Benchmark Đánh giá Luận văn**:
   - Chưa thiết lập kịch bản chạy đối chứng định lượng để chứng minh tính ưu việt của Multi-Agent so với Single-Agent.

---

## 4. Đường Dẫn & Tài Nguyên Tra Cứu

* **Frontend Production**: [https://fin-ai.eddiephung.me](https://fin-ai.eddiephung.me)
* **Backend Staging (Render)**: [https://final-thesis-zgwt.onrender.com](https://final-thesis-zgwt.onrender.com)
* **Lịch sử Phiên phân tích**: [https://final-thesis-zgwt.onrender.com/api/runs](https://final-thesis-zgwt.onrender.com/api/runs)
* **Bảng điều phối Linear**: [https://linear.app/eddiephung](https://linear.app/eddiephung) (Team THES)
* **GitHub Repository**: [https://github.com/thaicuong576/final-thesis](https://github.com/thaicuong576/final-thesis)
