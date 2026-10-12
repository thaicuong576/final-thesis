# Bản đồ repo: final-thesis

Cập nhật 2026-10-13. Mục quá 30 ngày thì kiểm tra lại trước khi dùng.

## Tổng quan
- Làm gì: khóa luận tốt nghiệp về hệ đa tác tử phân cấp phân tích ngân hàng niêm yết Việt Nam, kèm webapp (báo cáo có truy vết nguồn, xem tiến trình xử lý trực tiếp, bối cảnh thị trường). Mã tính chỉ số tài chính; mô hình ngôn ngữ chỉ truy xuất, giải thích, phê bình.
- Stack: Python 3.11 (FastAPI, LangGraph, SQLite), frontend React + Vite + TypeScript + Tailwind (vitest). Backend chạy Render, frontend chạy Vercel, snapshot SQLite lưu Supabase Storage riêng tư.
- Chủ object: một người dùng duy nhất. Dịch vụ ngoài chỉ đọc: SSI FastConnect Data (giá), OpenAI chính thức (thử nghiệm).

## Chạy và verify
| Việc | Lệnh | Ghi chú |
| :--- | :--- | :--- |
| Cài đặt | `slot.sh init` (xem `.fleet/project.conf`) | mỗi slot có `.venv` và `frontend/node_modules` |
| Chạy API local | `python -m uvicorn thesis_api.main:app --port 8000` | cần `PYTHONPATH=src` và `SQLITE_DB_PATH` tới bản sao snapshot |
| Chạy frontend | `cd frontend && npm run dev` | port mặc định 5173; slot dùng 5201+ |
| Test Python | `PYTHONPATH=src python -m unittest discover -s tests -q` | CI dùng unittest; pytest không có trong requirements-test |
| Ràng buộc | `python scripts/check_architecture_guardrails.py`, `python scripts/check_openapi_contract.py`, `python scripts/eval_regression.py` | cả ba chạy trong CI |
| Frontend | `cd frontend && npm run lint && npm test && npm run build` | CI: `.github/workflows/frontend.yml` |

## Bản đồ tính năng
| Tính năng / vùng | File chính | Luồng | Cập nhật |
| :--- | :--- | :--- | :--- |
| API phân tích + SSE | `src/thesis_api/` (`adaptive_runtime.py`, `analysis_writer.py`, `runtime_events.py`) | kế hoạch đóng băng -> truy xuất -> viết -> Stage-1 -> critic -> sửa | 2026-10-13 |
| Dữ liệu và kiểm định | `src/thesis_data/` | snapshot SQLite -> quan sát có nguồn -> Stage-1 | 2026-10-13 |
| Giá thị trường (chỉ hiển thị) | `src/thesis_api/market_data.py`, `frontend/src/features/market-context/` | SSI -> cache 30 s -> `/api/market/quotes`, `/valuation` | 2026-10-13 |
| Báo cáo | `frontend/src/features/equity-report/` | AdaptiveReport, ReportMarketRow | 2026-10-13 |
| Nguồn gốc số liệu | `frontend/src/features/source-lineage/` | ngăn kéo PDF trang -> dòng dữ liệu -> đường truy vết | 2026-10-13 |
| Snapshot theo quý | `scripts/build_quarterly_snapshot.py`, `data/onboarding/quarterly-top10/` | inputs.csv -> công thức có phiên bản -> SQLite | 2026-10-13 |
| Thực nghiệm | `scripts/er9_run.py`, `er9_score.py`, `redteam_score.py`, `verifier_mutation.py` | chạy mô hình thật bằng khóa OpenAI chính thức | 2026-10-13 |
| Luận văn | `docs/thesis-v2/` (bản gọn `build/Khoa-luan-gon.docx`, 59 trang) | viết tay, dựng Word | 2026-10-13 |

## Bẫy đã biết
- `git pull` trên checkout gốc đang detached không có upstream: dùng `git fetch` rồi checkout/ff `main`. (2026-10-13)
- Windows khóa thư mục worktree ("Device or resource busy"): `git worktree prune`, xóa tay sau khi đóng terminal. (2026-10-13)
- Hai test đã biết fail do `.env` local: `test_readiness_requires_model_configuration_and_writable_distinct_run_store`, `test_get_llm_client_initialization_with_custom_settings`. (2026-10-13)
- `er9_run.py --model` từng bị bỏ qua; dùng biến môi trường `OPENAI_MODEL` (đã sửa ở PR #154). (2026-10-13)
- SSI AccessToken thỉnh thoảng trả 502; client đã có khóa token và retry. `ListedShare` là chuỗi thập phân. (2026-10-13)
- Watcher chạy nền bị hệ điều hành giết khi thiếu RAM: không tự khởi động lại, báo người dùng. (2026-10-13)
- Python: đặt `PYTHONIOENCODING=utf-8` khi in tiếng Việt trên Windows. (2026-10-13)

## Không được đụng
- `data/processed/finance_master_v2.sqlite` và Gold v5: benchmark bất biến; SQLite và WAL/SHM không bao giờ hardlink giữa gốc và worktree.
- `data/raw/`: bằng chứng gốc bất biến.
- `docs/Khoá luận tốt nghiệp - Cường - GVHD_ Lê Văn.md` và PDF/ảnh đi kèm: nguồn chỉ đọc.
- Bí mật: `SSI_PRIVATE_KEY`, thông tin DNSE không bao giờ lên Render; không in giá trị biến môi trường.
- Giá thị trường không vào `facts`, `narrative_audit`, kế hoạch hay critic.
