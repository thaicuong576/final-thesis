# Evaluation Freeze Readiness — 2026-09-30

> **Phiên bản**: ER-8 Evaluation Harness  
> **Ngày**: 2026-09-30  
> **Trạng thái**: FROZEN — Giao thức V2 đã khóa, sẵn sàng chạy lần đầu

---

## 1. Mục tiêu

Tài liệu này xác nhận rằng toàn bộ giao thức đánh giá A/B/C (ER-8) đã được khóa và hệ thống sẵn sàng cho lần chạy chấm điểm đầu tiên.

---

## 2. Bộ câu hỏi đã khóa

| File | Hash (canonical_lf_utf8_sha256) |
|------|---------------------------------|
| `data/evaluation/er8-questions-v2.jsonl` | `62dab818f7e9628c12ee12cd679231a66e1051a253958835d5ae4cac91d7582f` |
| `data/evaluation/er8-task-specs-v2.json` | `34ab2e0630403129150f0ede2bb8f8a4a7fa64b5180db1c9b6c27791ee52144b` |
| `data/evaluation/er8-expected-coverage-v2.json` | `d8e7662ccc15bec5fe5d012eb6aa9f98e5cd8de1621069566b9f39f1d2498ddd` |

> **Lưu ý**: Không được sửa các file trên sau khi freeze. Nếu phát hiện lỗi trong câu hỏi, phải tạo `er8-questions-v3.jsonl` với bộ hash mới và tài liệu lý do thay đổi.

---

## 3. Cấu hình chạy đã khóa

| Tham số | Giá trị |
|---------|---------|
| `planner_mode` | `rules_only` |
| `seed` | `42` (mặc định) |
| `reps` | `1` |
| `max_tokens` | `3 000 000` |
| Arms | `A=single_agent`, `B=hierarchical`, `C=hierarchical_critic` |
| Số run | 36 (12 câu × 3 arm × 1 lần lặp) |

---

## 4. Kiểm tra kỹ thuật đã qua

| Hạng mục | Kết quả |
|----------|---------|
| Toàn bộ test suite (unittest) | **PASS** (≥781 tests) |
| `check_openapi_contract.py` | **PASS** |
| `check_architecture_guardrails.py` | **PASS** |
| `test_er8_harness.py` (10 tests offline) | **PASS** |
| Plan hash nhất quán giữa 3 arm | **VERIFIED** |
| Budget guard dừng đúng | **VERIFIED** |
| Socket guard — không gọi mạng | **VERIFIED** |
| Dry-run 36 run hoàn thành | **VERIFIED** |

---

## 5. Phạm vi và hạn chế đã ghi nhận (D-076)

- **Chưa chạy model thật**: PR này chỉ khóa giao thức và harness; chưa thực hiện run với OpenAI API thật.
- **Không có chấm mù / chấm người**: Phiên bản 1 chỉ chấm tất định. Chấm người dự kiến cho phiên bản sau.
- **Mẫu nhỏ**: 12 câu, 1 lần lặp — kết quả phân tích bootstrap là thăm dò, không có ý nghĩa thống kê cao.
- **1 người phát triển**: Không có phân ly giữa thiết kế câu hỏi và đánh giá kết quả.

---

## 6. Quyết định thiết kế (tham chiếu D-076)

Xem `docs/DECISIONS.md` — D-076: *Đóng băng giao thức đánh giá V2 trước lần chạy đầu tiên*.

---

## 7. Người chịu trách nhiệm

- **Lead Architect**: Orchestrator (root session)
- **Worker**: ER-8 worker (`feat/er-8-eval-harness`)
- **PR**: `feat(eval): [ER-8] A/B/C harness, deterministic scoring and analysis`
