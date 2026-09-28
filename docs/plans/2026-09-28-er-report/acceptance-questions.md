# Bộ câu hỏi nghiệm thu

Dùng cho: test planner ER-2 (phần A), kiểm với số thật ở ER-3 (phần C), kiểm với model thật ở ER-4 (phần B), và review của Claude.
Trong test tự động được thay ticker bằng thực thể của provider test. Khi kiểm với Gold v5 thì dùng nguyên văn.

## A. Lập kế hoạch (offline, `planner_mode="rules_only"`)

"Nhóm" = peer universe của catalog. Context = các quý cùng năm, không vượt anchor.

| # | Câu hỏi | question_type | focus / entities | anchor · kỳ | metrics | tools (luật) |
|---|---|---|---|---|---|---|
| A1 | Sức khỏe tài chính của ACB so với các ngân hàng cùng nhóm, quý 4/2024 | company_profile | ACB | Q4 · Q1–Q4 | cả 4 | peer_position, trend, decomposition |
| A2 | Chất lượng tín dụng của ACB quý 4/2024 thế nào? | company_profile | ACB | Q4 · Q1–Q4 | nợ xấu, bao phủ | peer_position, trend (không có macro) |
| A3 | Ngân hàng nào có đệm dự phòng dày nhất quý 4/2024? | ranking | — | Q4 | bao phủ | ranking(context_metrics = nợ xấu, ROA) |
| A4 | ACB đứng thứ mấy về ROE trong nhóm quý 4/2024? | ranking | highlight ACB | Q4 | ROE | ranking(highlight ACB) |
| A5 | ROE của VPB thay đổi thế nào trong năm 2024? | trend | VPB | Q4 · Q1–Q4 | ROE | trend, peer_position |
| A6 | Diễn biến ROA của VPB từ 2024_Q1 đến 2024_Q4 | trend | VPB | Q4 · Q1–Q4 | ROA | trend, peer_position |
| A7 | So sánh ACB và TCB quý 4/2024 | head_to_head | ACB, TCB | Q4 | cả 4 | head_to_head, decomposition |
| A8 | So sánh ACB, TCB và MBB về ROE quý 3/2024 | head_to_head | ACB, TCB, MBB | Q3 | ROE | head_to_head |
| A9 | Tỷ lệ nợ xấu của VCB quý 4/2024 là bao nhiêu? | lookup | VCB | Q4 | nợ xấu | lookup |
| A10 | Sức khỏe tài chính của MBB | company_profile | MBB | Q4 (mặc định) · Q1–Q4 | cả 4 | peer_position, trend, decomposition; có `period_defaulted_to_latest` |
| A11 | phan tich no xau cua VPB quy 4 2024 | company_profile | VPB | Q4 · Q1–Q4 | nợ xấu | peer_position, trend |
| A12 | Lãi suất điều hành ảnh hưởng thế nào đến nợ xấu của MBB quý 4/2024? | company_profile | MBB | Q4 · Q1–Q4 | nợ xấu | peer_position, trend; macro = skip, có limitation |
| A13 | Vì sao ROE của ACB cao? | company_profile | ACB | Q4 · Q1–Q4 | ROE | peer_position, trend, decomposition (cần ROA làm input); limitation về nguyên nhân |
| A14 | API: `{"query":"Diễn biến ROE của ACB","periods":["2024_Q1","2024_Q2","2024_Q3","2024_Q4"]}` | (đường D-074 cũ) | ACB | Q1–Q4 | ROE | không qua planner |

Câu bị chặn (phải có `error.message` tiếng Việt và 3 gợi ý):

| # | Câu hỏi | code | message phải nhắc |
|---|---|---|---|
| X1 | Tỷ lệ nợ xấu của ACB quý 4/2023 | unsupported_period | "Q1–Q4/2024" |
| X2 | Tăng trưởng tín dụng toàn ngành 2024 thế nào? | unsupported_macro_scope | chưa có dữ liệu vĩ mô |
| X3 | NIM của ACB quý 4/2024 | unsupported_metric | danh sách chỉ tiêu đang có |
| X4 | Phân tích HDB quý 4/2024 | unsupported_entity | danh sách ngân hàng đang có |
| X5 | ACB quý 4/2024 là bao nhiêu? | metric_required | cần nêu một chỉ tiêu |

## B. Chạy với model thật (Gold v5 + model của staging, `planner_mode="model_with_fallback"`)

| # | Câu hỏi | Hình dạng report mong đợi |
|---|---|---|
| B1 | Sức khỏe tài chính của ACB so với các ngân hàng cùng nhóm, quý 4/2024 | note · headline · luận điểm · ≥ 2 hình (trong số scatter, rank_heatmap, small_multiples) · callout · cột tín hiệu |
| B2 | Ngân hàng nào có đệm dự phòng dày nhất quý 4/2024? | note · headline · ranked_bar · luận điểm · callout |
| B3 | ROE của VPB thay đổi thế nào trong năm 2024? | note · headline · line_trend · luận điểm (± callout) |
| B4 | So sánh ACB và TCB quý 4/2024 | note · headline · comparison_table hoặc grouped_bar · callout |
| B5 | Tỷ lệ nợ xấu của VCB quý 4/2024 là bao nhiêu? | answer_card · answer · ≤ 1 hình |

Mỗi câu phải đạt:
- `status` ∈ {completed, accepted_with_limitations}; thời gian < 90 giây;
- mọi câu có `fact_ids` và qua verifier; `numbers_matched == numbers_checked`;
- không có `bank.`, `claim`, `provider`, hay câu tiếng Anh;
- **5 report có hình dạng khác nhau như bảng.**

Dán JSON rút gọn vào PR ER-4. Sau khi deploy thì chạy lại trên staging để Claude review.

## C. Số Gold v5 dùng để đối chiếu (ER-3 bắt buộc khớp)

Q4/2024, trung vị gồm cả 5 ngân hàng:

| | Nợ xấu % | Bao phủ % | ROA % | ROE % |
|---|---|---|---|---|
| ACB | 1,5122 (#3) | 76,5591 (#4) | 2,1215 (#3) | 21,7459 (#2) |
| MBB | 1,6205 (#4) | 92,2484 (#3) | 2,2135 (#2) | 22,0939 (#1) |
| TCB | 1,17 (#2) | 113,8 (#2) | 2,4 (#1) | 15,5 (#4) |
| VCB | 0,9636 (#1) | 223,311 (#1) | 1,7249 (#5) | 18,5965 (#3) |
| VPB | 4,1956 (#5) | 56,1749 (#5) | 1,8361 (#4) | 11,4117 (#5) |
| Trung vị | 1,5122 | 92,2484 | 2,1215 | 18,5965 |

(#n = `rank_better`)

Kỳ vọng từng câu:
- **B1 ACB:**
  - gap: bao phủ −15,69 pp; ROE +3,15 pp; nợ xấu và ROA đều 0.
  - signals: Sinh lời = above_peers; Chất lượng nợ = in_line; Đệm dự phòng = below_peers.
  - delta Q3→Q4: bao phủ −2,51 pp; median bao phủ +13,18 pp → `counter_trend`. Có `divergent_signals` (Sinh lời ↔ Đệm dự phòng).
  - ROE/ROA = 10,25 lần; trung vị ROE/ROA của nhóm là 9,98.
  - ACB Q1/2024: 4 ô missing.
- **B2 bao phủ:**
  - thứ tự VCB 223,3 > TCB 113,8 > MBB 92,2 > ACB 76,6 > VPB 56,2;
  - ratio_to_median: VCB 2,42 lần, VPB 0,61 lần; spread 167,14 pp;
  - `cross_metric_extreme`: VPB chót ở cả bao phủ và nợ xấu (consistent); VCB đầu ở cả bao phủ và nợ xấu (consistent); VCB đầu ở bao phủ nhưng chót ở ROA (tradeoff).
- **B3 VPB ROE:**
  - 8,0671 → 8,5867 → 9,6445 → 11,4117 (tăng liên tục: +0,52, +1,06, +1,77); đầu → cuối +3,34 pp;
  - trung vị: Q1 17,4587 (4 ngân hàng hợp lệ, ACB thiếu), Q2 19,2688, Q3 19,5335, Q4 18,5965;
  - gap Q1 −9,39, Q4 −7,18 (thu hẹp); hạng Q4 5/5;
  - Q3→Q4: VPB +1,77 trong khi trung vị −0,94 → `counter_trend`.
- **B4 ACB–TCB:**
  - pairwise ACB − TCB: nợ xấu +0,34, bao phủ −37,24, ROA −0,28, ROE +6,25;
  - lead_count: TCB hơn ACB 3/4, ACB hơn TCB 1/4;
  - ROE/ROA: ACB 10,25, TCB 6,46.
- **B5 VCB nợ xấu:** 0,9636%, hạng 1/5 (thấp nhất); Q3 1,2228 → delta −0,26 pp; trung vị 1,5122.
