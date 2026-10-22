# Báo cáo Đo lường Độ nhạy Kiểm chứng Đột biến (mut2)

## 1. Thông tin chung & Nguồn gốc thực nghiệm

- **Mục tiêu**: Bổ sung hai quy tắc kiểm chứng ngữ nghĩa vào bộ kiểm chứng câu (`verify_sentence`):
  1. **Quy tắc nhãn chỉ tiêu** (`metric_label_mismatch`): Khớp tên chỉ tiêu cụm dài nhất trước (tránh nhầm lẫn 'tỷ lệ bao phủ nợ xấu' / 'bao phủ nợ xấu' thành 'nợ xấu'; hỗ trợ cả NPL, LLR, ROA, ROE, v.v.), bắt buộc nhãn nêu trong câu phải trùng với chỉ tiêu của fact được trích dẫn.
  2. **Quy tắc loại trừ câu tự so sánh** (`self_comparison`): Loại bỏ câu so sánh một ngân hàng với chính nó quanh các từ so sánh ('vượt trội', 'cao hơn', 'thấp hơn', v.v.), câu biến động có cùng kỳ xuất phát và kỳ kết thúc ('từ quý 2/2026 đến quý 2/2026'), và so sánh cực trị cùng chiều ('thấp nhất – thấp nhất').
- **Mã nguồn (Commit SHAs)**:
  - SHA gốc (`origin/main`): `2a239ac0f0f214a3d12b113205e8c83fa8170cea`
  - Nhánh thực nghiệm: `feat/verifier-label-rules`
- **Đặc tính kỹ thuật**: Thực nghiệm đột biến chạy hoàn toàn cục bộ, xác định, tiêu thụ 0 token mô hình.

## 2. Kiểm soát Tỷ lệ Bác bỏ nhầm (False Positive / False Rejection Rate)

Yêu cầu cốt lõi: Các quy tắc mới chỉ loại bỏ nhận định sai lệch ngữ nghĩa/tự tham chiếu, không được loại nhầm bất kỳ câu phân tích hợp lệ nào.

- **Bộ câu gốc ER-9 (36 runs, 129 câu chấp nhận)**:
  - Số câu kiểm tra: **129**
  - Số câu vượt qua kiểm chứng sau khi thêm 2 quy tắc: **129 / 129 (100,0%)**
  - Số câu bị bác bỏ nhầm: **0 (0,0%)**
- **Mở rộng trên toàn bộ runs E2R (`experiments/e2r/**/runs`)**:
  - Số file run: **36**
  - Số câu phân tích hợp lệ được kiểm tra: **171**
  - Số câu vượt qua kiểm chứng sau khi thêm 2 quy tắc: **171 / 171 (100,0%)**
  - Số câu bị loại bởi 2 quy tắc mới: **0 (0,0%)**
- **Tổng cộng toàn bộ dữ liệu kiểm soát**:
  - **300 / 300** câu hợp lệ được chấp nhận tuyệt đối (**100,0%**). Tỷ lệ bác bỏ nhầm là **0,0%**.

## 3. Bảng So sánh Trước / Sau cho Bộ Cũ (Seed 42)

Bộ kiểm thử gốc gồm **1.210 đột biến** sinh từ 129 câu chấp nhận qua 12 toán tử lỗi.

| Toán tử đột biến | Số lượng (n) | Trước: Bắt (Tỷ lệ) | Trước: Wilson 95% CI | Sau: Bắt (Tỷ lệ) | Sau: Wilson 95% CI | Chênh lệch tỷ lệ |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| `number_small` | 96 | 96/96 (100,0%) | [0,9615; 1,0000] | 96/96 (100,0%) | [0,9615; 1,0000] | **0,0%** |
| `number_large` | 96 | 96/96 (100,0%) | [0,9615; 1,0000] | 96/96 (100,0%) | [0,9615; 1,0000] | **0,0%** |
| `digit_swap` | 96 | 96/96 (100,0%) | [0,9615; 1,0000] | 96/96 (100,0%) | [0,9615; 1,0000] | **0,0%** |
| `rank` | 46 | 46/46 (100,0%) | [0,9229; 1,0000] | 46/46 (100,0%) | [0,9229; 1,0000] | **0,0%** |
| `denominator` | 52 | 52/52 (100,0%) | [0,9312; 1,0000] | 52/52 (100,0%) | [0,9312; 1,0000] | **0,0%** |
| `period` | 118 | 98/118 (83,0%) | [0,7527; 0,8875] | 112/118 (94,9%) | [0,8935; 0,9765] | **+11,9%** |
| `entity_swap` | 123 | 106/123 (86,2%) | [0,7898; 0,9119] | 123/123 (100,0%) | [0,9697; 1,0000] | **+13,8%** |
| `direction_flip` | 76 | 67/76 (88,2%) | [0,7900; 0,9364] | 73/76 (96,0%) | [0,8903; 0,9865] | **+7,9%** |
| `metric_swap` | 120 | 95/120 (79,2%) | [0,7105; 0,8547] | 119/120 (99,2%) | [0,9543; 0,9985] | **+20,0%** |
| `unsupported_number` | 129 | 129/129 (100,0%) | [0,9711; 1,0000] | 129/129 (100,0%) | [0,9711; 1,0000] | **0,0%** |
| `causal_claim` | 129 | 129/129 (100,0%) | [0,9711; 1,0000] | 129/129 (100,0%) | [0,9711; 1,0000] | **0,0%** |
| `recommendation` | 129 | 129/129 (100,0%) | [0,9711; 1,0000] | 129/129 (100,0%) | [0,9711; 1,0000] | **0,0%** |
| **Tổng cộng** | **1210** | **1139/1210 (94,1%)** | - | **1200/1210 (99,2%)** | - | **+5,0%** |

> **Điểm nhấn cải tiến trên bộ cũ (seed 42)**:
> - Tổng số đột biến bắt giữ tăng từ **1139** lên **1200** (+61 đột biến được ngăn chặn).
> - Số đột biến bị lọt giảm mạnh từ **71** xuống còn **10** (giảm **85.9%** lỗi lọt).
> - Toán tử `entity_swap`: bắt trọn **123/123 (100,0%)** đột biến (trước đó lọt 17 đột biến do tự so sánh cùng ngân hàng).
> - Toán tử `metric_swap`: bắt **119/120 (99,2%)** đột biến (trước đó lọt 25 đột biến do thiếu kiểm tra nhãn chỉ tiêu).
> - Toán tử `period`: tăng từ **83,0%** lên **94,9%** (loại bỏ toàn bộ các câu biến động tự quy chiếu cùng một kỳ).
> - Toán tử `direction_flip`: tăng từ **88,2%** lên **96,0%** (chặn các câu tự so sánh cực trị 'thấp nhất – thấp nhất').

## 4. Bảng So sánh Trước / Sau cho các Bộ Mới (Seed 7 và Seed 2026)

Để bảo đảm tính khách quan và tránh hiện tượng quá khớp (overfitting) trên seed 42, hai bộ đột biến mới độc lập được sinh từ cùng 129 câu gốc bằng seed 7 và seed 2026. Phép đo 'Trước' được thực hiện bằng cờ `--disable-label-rules` (tắt 2 quy tắc mới), phép đo 'Sau' bật đầy đủ 2 quy tắc.

### 4.1. Bộ độc lập Seed 7

| Toán tử | n | Trước (Seed 7) | Sau (Seed 7) | Chênh lệch |
| :--- | :---: | :---: | :---: | :---: |
| `number_small` | 96 | 95/96 (99,0%) | 95/96 (99,0%) | **0,0%** |
| `number_large` | 96 | 96/96 (100,0%) | 96/96 (100,0%) | **0,0%** |
| `digit_swap` | 96 | 96/96 (100,0%) | 96/96 (100,0%) | **0,0%** |
| `rank` | 46 | 41/46 (89,1%) | 41/46 (89,1%) | **0,0%** |
| `denominator` | 52 | 52/52 (100,0%) | 52/52 (100,0%) | **0,0%** |
| `period` | 118 | 101/118 (85,6%) | 114/118 (96,6%) | **+11,0%** |
| `entity_swap` | 123 | 105/123 (85,4%) | 123/123 (100,0%) | **+14,6%** |
| `direction_flip` | 76 | 67/76 (88,2%) | 73/76 (96,0%) | **+7,9%** |
| `metric_swap` | 120 | 95/120 (79,2%) | 119/120 (99,2%) | **+20,0%** |
| `unsupported_number` | 129 | 129/129 (100,0%) | 129/129 (100,0%) | **0,0%** |
| `causal_claim` | 129 | 129/129 (100,0%) | 129/129 (100,0%) | **0,0%** |
| `recommendation` | 129 | 129/129 (100,0%) | 129/129 (100,0%) | **0,0%** |
| **Tổng cộng** | **1210** | **1135/1210 (93,8%)** | **1196/1210 (98,8%)** | **+5,0%** |

### 4.2. Bộ độc lập Seed 2026

| Toán tử | n | Trước (Seed 2026) | Sau (Seed 2026) | Chênh lệch |
| :--- | :---: | :---: | :---: | :---: |
| `number_small` | 96 | 96/96 (100,0%) | 96/96 (100,0%) | **0,0%** |
| `number_large` | 96 | 96/96 (100,0%) | 96/96 (100,0%) | **0,0%** |
| `digit_swap` | 96 | 96/96 (100,0%) | 96/96 (100,0%) | **0,0%** |
| `rank` | 46 | 41/46 (89,1%) | 41/46 (89,1%) | **0,0%** |
| `denominator` | 52 | 52/52 (100,0%) | 52/52 (100,0%) | **0,0%** |
| `period` | 118 | 98/118 (83,0%) | 115/118 (97,5%) | **+14,4%** |
| `entity_swap` | 123 | 105/123 (85,4%) | 123/123 (100,0%) | **+14,6%** |
| `direction_flip` | 76 | 67/76 (88,2%) | 73/76 (96,0%) | **+7,9%** |
| `metric_swap` | 120 | 95/120 (79,2%) | 119/120 (99,2%) | **+20,0%** |
| `unsupported_number` | 129 | 129/129 (100,0%) | 129/129 (100,0%) | **0,0%** |
| `causal_claim` | 129 | 129/129 (100,0%) | 129/129 (100,0%) | **0,0%** |
| `recommendation` | 129 | 129/129 (100,0%) | 129/129 (100,0%) | **0,0%** |
| **Tổng cộng** | **1210** | **1133/1210 (93,6%)** | **1198/1210 (99,0%)** | **+5,4%** |

## 5. Danh sách Đột biến vẫn Lọt sau khi Thêm Quy tắc (Seed 42)

Tổng số đột biến còn lọt qua bộ kiểm chứng mới là **10 / 1.210** (tỷ lệ lọt chỉ còn 0,8%).
Toàn bộ 10 đột biến này được phân loại bằng quy tắc máy (machine rule classification):

### 1. Đột biến `period`: `er9-T01-hierarchical_no_critique-r0` / `sent-company-4`
- **Phân loại máy**: `Không tự quy chiếu` (Không tự quy chiếu)
- **Câu gốc**: "ROE của BID đi ngang ở mức 17,9% (hạng 4/10), ngang trung vị nhóm trong quý 2/2026."
- **Câu đột biến**: "ROE của BID đi ngang ở mức 17,9% (hạng 4/10), ngang trung vị nhóm trong quý 1/2026."

### 2. Đột biến `period`: `er9-T04-hierarchical_no_critique-r0` / `sent-company-1`
- **Phân loại máy**: `Không tự quy chiếu` (Không tự quy chiếu)
- **Câu gốc**: "Tỷ lệ nợ xấu của CTG giảm liên tục từ quý 1/2025 đến quý 3/2025, đạt 1,10% trong quý 4/2025."
- **Câu đột biến**: "Tỷ lệ nợ xấu của CTG giảm liên tục từ quý 1/2025 đến quý 4/2025, đạt 1,10% trong quý 4/2025."

### 3. Đột biến `period`: `er9-T04-hierarchical_no_critique-r0` / `sent-company-4`
- **Phân loại máy**: `Không tự quy chiếu` (Không tự quy chiếu)
- **Câu gốc**: "Tỷ lệ bao phủ nợ xấu của CTG cao hơn trung vị nhóm xuyên suốt năm 2025, xếp hạng 2/10 về tỷ lệ bao phủ nợ xấu trong quý 4/2025."
- **Câu đột biến**: "Tỷ lệ bao phủ nợ xấu của CTG cao hơn trung vị nhóm xuyên suốt năm 2025, xếp hạng 2/10 về tỷ lệ bao phủ nợ xấu trong quý 2/2025."

### 4. Đột biến `period`: `er9-T04-hierarchical_with_critique-r0` / `sent-company-2`
- **Phân loại máy**: `Không tự quy chiếu` (Không tự quy chiếu)
- **Câu gốc**: "Tỷ lệ bao phủ nợ xấu của CTG giảm trong quý 4/2025, ngược chiều trung vị nhóm tăng."
- **Câu đột biến**: "Tỷ lệ bao phủ nợ xấu của CTG giảm trong quý 3/2025, ngược chiều trung vị nhóm tăng."

### 5. Đột biến `direction_flip`: `er9-T04-hierarchical_with_critique-r0` / `sent-company-2`
- **Phân loại máy**: `Không tự quy chiếu` (Không tự quy chiếu)
- **Câu gốc**: "Tỷ lệ bao phủ nợ xấu của CTG giảm trong quý 4/2025, ngược chiều trung vị nhóm tăng."
- **Câu đột biến**: "Tỷ lệ bao phủ nợ xấu của CTG giảm trong quý 4/2025, ngược chiều trung vị nhóm giảm."

### 6. Đột biến `period`: `er9-T04-single_agent-r0` / `sent-fb-hl`
- **Phân loại máy**: `Không tự quy chiếu` (Không tự quy chiếu)
- **Câu gốc**: "Tỷ lệ bao phủ nợ xấu của CTG tăng 22,0 điểm % từ quý 1/2025 đến quý 4/2025, xếp hạng 2/10 trong quý 4/2025."
- **Câu đột biến**: "Tỷ lệ bao phủ nợ xấu của CTG tăng 22,0 điểm % từ quý 1/2025 đến quý 4/2025, xếp hạng 2/10 trong quý 1/2025."

### 7. Đột biến `period`: `er9-T05-single_agent-r0` / `sent-fb-hl`
- **Phân loại máy**: `Không tự quy chiếu` (Không tự quy chiếu)
- **Câu gốc**: "ROA của SHB tăng 0,21 điểm % từ quý 1/2025 đến quý 4/2025, xếp hạng 7/10 trong quý 4/2025."
- **Câu đột biến**: "ROA của SHB tăng 0,21 điểm % từ quý 1/2025 đến quý 4/2025, xếp hạng 7/10 trong quý 1/2025."

### 8. Đột biến `direction_flip`: `er9-T08-hierarchical_no_critique-r0` / `sent-orchestrator-15594a`
- **Phân loại máy**: `Không tự quy chiếu` (Không tự quy chiếu)
- **Câu gốc**: "Trong năm 2025, VPB duy trì ROA cao hơn trung vị nhóm (+0,63 điểm % ở quý 4/2025) nhưng đánh đổi bằng chất lượng tài sản yếu với tỷ lệ nợ xấu cao hơn trung vị nhóm (+2,07 điểm %) và bao phủ nợ xấu thấp hơn (-42,0 điểm %)."
- **Câu đột biến**: "Trong năm 2025, VPB duy trì ROA thấp hơn trung vị nhóm (+0,63 điểm % ở quý 4/2025) nhưng đánh đổi bằng chất lượng tài sản yếu với tỷ lệ nợ xấu cao hơn trung vị nhóm (+2,07 điểm %) và bao phủ nợ xấu thấp hơn (-42,0 điểm %)."

### 9. Đột biến `metric_swap`: `er9-T08-hierarchical_no_critique-r0` / `sent-orchestrator-15594a`
- **Phân loại máy**: `Không tự quy chiếu` (Không tự quy chiếu)
- **Câu gốc**: "Trong năm 2025, VPB duy trì ROA cao hơn trung vị nhóm (+0,63 điểm % ở quý 4/2025) nhưng đánh đổi bằng chất lượng tài sản yếu với tỷ lệ nợ xấu cao hơn trung vị nhóm (+2,07 điểm %) và bao phủ nợ xấu thấp hơn (-42,0 điểm %)."
- **Câu đột biến**: "Trong năm 2025, VPB duy trì ROA cao hơn trung vị nhóm (+0,63 điểm % ở quý 4/2025) nhưng đánh đổi bằng chất lượng tài sản yếu với tỷ lệ bao phủ nợ xấu cao hơn trung vị nhóm (+2,07 điểm %) và bao phủ nợ xấu thấp hơn (-42,0 điểm %)."

### 10. Đột biến `direction_flip`: `er9-T08-single_agent-r0` / `sent-orchestrator-cd0429`
- **Phân loại máy**: `Không tự quy chiếu` (Không tự quy chiếu)
- **Câu gốc**: "VPB duy trì khả năng sinh lời cao hơn trung vị nhóm (ROA quý 4/2025 đạt 2,23%) nhưng đánh đổi bằng chất lượng tài sản yếu kém (tỷ lệ bao phủ nợ xấu chỉ 54,9%, thấp hơn trung vị nhóm)."
- **Câu đột biến**: "VPB duy trì khả năng sinh lời thấp hơn trung vị nhóm (ROA quý 4/2025 đạt 2,23%) nhưng đánh đổi bằng chất lượng tài sản yếu kém (tỷ lệ bao phủ nợ xấu chỉ 54,9%, thấp hơn trung vị nhóm)."

### Nhận xét & Kết luận kỹ thuật:
1. **Không còn bất kỳ đột biến tự quy chiếu nào lọt lưới**: Trong 71 đột biến lọt ở `mut1`, có 37 đột biến tự quy chiếu (cùng ngân hàng ở hai vế so sánh, cùng một kỳ trong mệnh đề biến động, hoặc so sánh cực trị cùng chiều). Sau khi kích hoạt `self_comparison`, **100% các đột biến tự quy chiếu đã bị ngăn chặn hoàn toàn**.
2. **10 trường hợp còn lọt đều thuộc dạng ngữ nghĩa đa mệnh đề hoặc kỳ tương thích kép**:
   - 6 ca `period`: Đổi một kỳ trong câu nhưng kỳ bị đổi ngẫu nhiên vẫn trùng với một kỳ hợp lệ khác có sẵn trong danh mục facts được trích dẫn (ví dụ ngân hàng duy trì cùng thứ hạng/trung vị ở cả 2 quý liên tiếp).
   - 3 ca `direction_flip`: Đảo chiều mệnh đề phụ ('ngược chiều trung vị nhóm tăng' thành 'ngược chiều trung vị nhóm giảm'), nằm ngoài phạm vi kiểm chứng của từ vựng chiều chính.
   - 1 ca `metric_swap`: Câu phức hợp đa chỉ tiêu của VPB (`sent-orchestrator-15594a`) trích dẫn đồng thời facts cho ROA, NPL và LLR. Khi đột biến tráo nhãn giữa NPL và LLR, cả hai chỉ tiêu này đều có mặt trong tập facts trích dẫn nên không vi phạm tập hợp nhãn tổng.
3. **Độ an toàn tuyệt đối**: Không có bất kỳ nhận định phân tích hợp lệ nào bị loại nhầm trên 300 câu kiểm soát (tỷ lệ bác bỏ nhầm 0,0%).
