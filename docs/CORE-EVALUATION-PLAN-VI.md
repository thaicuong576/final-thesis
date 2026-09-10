# Kế hoạch benchmark lõi và macro extension

## Quyết định vận hành

Giữ nguyên `experiments/question-set-v1.json` làm question set đầy đủ, nhưng
tạo thêm `experiments/question-set-core-v1.json` cho benchmark chính. Core set
loại riêng câu hỏi `TCB_macro_to_bank_q4`, không loại Macro Agent khỏi kiến trúc.

Lý do: dữ liệu ngân hàng hiện có thể tiến tới reconciliation độc lập, trong khi
macro Q4 chưa có đủ quan sát chính thức, period-aligned và được kiểm tra. Nếu để
một câu macro khóa toàn bộ baseline, ta đang để thiếu hụt của một data domain
quyết định thay cho câu hỏi nghiên cứu về single-agent và hierarchical-agent.

Đây là cách thu hẹp benchmark, không phải tuyên bố macro không quan trọng.

## Phạm vi thực thi

| Track | Question set | Số câu | Số job (3 arm) | Vai trò |
|---|---|---:|---:|---|
| Core bank benchmark | `question-set-core-v1.json` | 13 | 39 | Kết quả so sánh chính |
| Macro extension | Câu `TCB_macro_to_bank_q4` trong `question-set-v1.json` | 1 | 3 | Chỉ chạy và báo riêng khi macro Gold đạt gate |
| Full draft | `question-set-v1.json` | 14 | 42 | Không dùng để aggregate khi macro chưa đạt |

Ba arm không đổi:

1. single-agent;
2. hierarchical Macro/Sector/Company không critique;
3. hierarchical Macro/Sector/Company có bounded critique.

Trong core benchmark, Macro Agent có thể trả về context rỗng có nhãn
`unavailable`, nhưng không được tự thay bằng DBnomics/IMF hoặc suy diễn macro từ
bank rows. Điều này vẫn kiểm tra được fairness, routing, contract, evidence và
chi phí của kiến trúc; riêng chất lượng giải thích macro được để ở extension.

## Gate dữ liệu

Core benchmark vẫn **chưa được chạy provider-backed**. Cả core và extension đều
cần Gold snapshot cho các bank cells tương ứng. Core không cần macro observation
để mở gate, nhưng vẫn cần:

- tối thiểu 40 value/evidence labels độc lập;
- coverage hoặc missing reason cho từng ô được chọn;
- metric definition, unit, period basis và locator được adjudicate;
- không còn conflict nghiêm trọng trong metric được đưa vào Gold;
- Gold snapshot riêng, không ghi đè staging.

Macro extension chỉ mở thêm khi có cả:

- `macro.policy_rate` với rate type và effective date áp dụng được cho Q4;
- `macro.credit_growth` là quan sát hệ thống đúng period basis, không phải target
  hoặc số giữa kỳ bị trình bày như Q4;
- source ID, publication date, locator và independent check cho từng quan sát.

## Cách chạy và báo cáo

Tạo plan core bằng:

```powershell
$env:PYTHONPATH='src'
python scripts/validate_question_set.py experiments/question-set-core-v1.json
python scripts/plan_baseline_runs.py experiments/question-set-core-v1.json PENDING_GOLD_SNAPSHOT
```

Plan đã materialize sẵn tại
`experiments/runs/baseline-plan-core-v1.json`; preflight bằng:

```powershell
python scripts/validate_baseline_plan.py `
  experiments/runs/baseline-plan-core-v1.json `
  experiments/question-set-core-v1.json
```

Không trộn 39 core jobs với 3 macro jobs trong một aggregate nếu macro extension
chưa đạt gate. Báo cáo chính cần có:

- điểm factual/evidence/citation/anomaly của 39 core jobs;
- latency, call count, token/cost của cùng 39 jobs;
- kết quả macro extension ở bảng riêng, hoặc ghi `not run: macro gold unavailable`;
- limitation rõ ràng rằng core benchmark chưa kiểm định năng lực macro reasoning.

## Điều kiện mở rộng hoặc hủy extension

- Macro Gold đạt: chạy 3 macro jobs như một extension pre-registered.
- Không đạt trong time-box: không dùng fallback để lấp; giữ extension là
  `not scorable` và hoàn thiện luận văn với giới hạn đã nêu.
- Core bank Gold không đạt: chuyển từ 48-cell mặc định sang fallback 36-cell đã
  ghi trong `data/manifests/gold-bank-2025-pilot-v1/fallback-36-selection.json`,
  sau khi có xác nhận scope; không mở rộng lên 80/200 cells.

## Luận điểm phương pháp

Điểm mạnh của cách tách này là giữ nguyên câu hỏi so sánh kiến trúc, đồng thời
không biến một nguồn macro chưa hoàn thiện thành dữ liệu “official”. Điểm yếu
là kết luận chính chỉ bao phủ bank/sector/evidence/anomaly handling; không được
diễn đạt thành kết luận đầy đủ về macro-to-bank reasoning.
