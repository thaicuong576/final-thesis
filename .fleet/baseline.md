# Baseline (2026-10-13, slot-1, main b719c2a)

Chạy trong `.worktrees/slot-1` sau `slot.sh init`. Không có `.env` ở slot.

| Lệnh | Kết quả |
| :--- | :--- |
| `PYTHONPATH=src python -m unittest discover -s tests -q` | OK: 980 test, 7 skipped, 264 s (không có test nào fail) |
| `python scripts/check_architecture_guardrails.py` | PASS |
| `python scripts/check_openapi_contract.py` | PASS |
| `python scripts/eval_regression.py` | PASS (khoảng 1-2 s) |
| `python -m compileall -q src scripts tests` | OK |
| `cd frontend && npm run lint` | sạch |
| `cd frontend && npm test` | 235 passed |
| `cd frontend && npm run build` | exit 0 |

## Ghi chú
- CI dùng `unittest`; pytest không nằm trong `requirements-test.txt`. Các TASK.md cũ ghi `pytest` là sai so với CI.
- Hai test từng fail vì `.env` local (`test_readiness_requires_model_configuration_and_writable_distinct_run_store`, `test_get_llm_client_initialization_with_custom_settings`) đã không fail ở slot vì slot không có `.env`; ở checkout gốc có `.env` thì chúng vẫn có thể fail.
- Bộ Python chậm (264 s): nhiều test dựng cả luồng phân tích bằng mô hình giả (cứ 2-3 s một lần chạy). Chưa đo file nào nặng nhất; việc tối ưu là việc riêng.
