# ER-7 · UI: report kiểu equity research, lắp theo khối

Nhánh: `feat/er-7-ui-report` · PR: `feat(ui): [ER-7] block-rendered equity-research report`

Mục tiêu: trang `/reports/:id` render **mọi `ReportSpec` hợp lệ**. Report tra cứu ra thẻ trả lời gọn; report xếp hạng, xu hướng, so sánh, hồ sơ ra ghi chú kiểu equity research với số khối, loại hình và thứ tự khác nhau. Mẫu tham chiếu: `mockups.html` màn **D** (hồ sơ) và **E** (4 dạng khác). Dùng sans-serif.

Bắt đầu được ngay sau ER-1 với 5 fixture report. Nối thật khi ER-4 merge.

Đọc trước: `.agent/rules/design/05-data-visualization.md` (bắt buộc), `01`, `02`, `04`; `frontend/src/pages/reports/ReportPage.tsx`; `frontend/src/features/analysis-report/*`.

## 1. Định tuyến và tương thích
- `ReportPage` tải `/api/reports/{id}`. Có `report_version === "er-report-v1"` thì render `AdaptiveReport`. Ngược lại render `LegacyReport` (bố cục hiện tại đổi tên, không sửa thêm).
- Không fallback sang mock. Lỗi tải thì hiện trạng thái lỗi kèm nút thử lại.

## 2. `AdaptiveReport` (thư mục mới `frontend/src/features/equity-report/`)

```
AdaptiveReport
 ├─ ReportMasthead         (luôn có, code dựng)
 ├─ kind = answer_card → AnswerCardLayout
 │     AnswerBlock (số lớn) + câu bối cảnh → các khối còn lại (≤ 1 figure) → SourceNotes
 └─ kind = note → NoteLayout
       [SignalsAside nếu question_type = company_profile và có signals]
       BlockRenderer cho từng block theo thứ tự trong spec
       ProcessLink → SourceNotes → TechnicalDetails
```

**ReportMasthead:**
- viền trên 2px `--text-primary`;
- trái: `report_spec.note_label`, hoặc nhãn theo question_type nếu thiếu: "Tra cứu nhanh", "Ghi chú doanh nghiệp", "Ghi chú sàng lọc", "Ghi chú xu hướng", "Ghi chú so sánh";
- phải: ngày tạo;
- dòng dưới: badge mã (mono, viền) cho mỗi entity được focus (head_to_head có 2–3 badge; ranking không có badge) cùng kỳ "Quý 4/2024" hoặc "Q1–Q4/2024".

**BlockRenderer:** `switch (block.type)`, gặp type lạ thì bỏ qua và `console.warn`.

| type | Component | Ghi chú |
|---|---|---|
| answer | `AnswerBlock` | số lớn 32px/700 từ `value_fact_id` (định dạng theo registry) + nhãn "{Chỉ tiêu} · {mã} · {kỳ}" + các câu |
| headline | `Headline` | h1 26–28px/700 |
| key_points | `KeyPoints` | mỗi ý: tiêu đề 600 + câu; số chú thích `<sup>` là link tới `#note-n` |
| section | `Section` | h2 18px/700 + đoạn văn |
| figure | `Figure` + `CHARTS[chart]` | caption "Hình n. {title}", thân hình, dòng takeaway (câu, có chú thích), dòng nguồn 11px, nút "Xem bảng số liệu" |
| callout | `Callout` | viền trái 2px (`--warning` cho warning, `--border-strong` cho notice), tiêu đề 600 + câu |
| table | `DataTable` | bảng số từ dataset |

**SignalsAside** (chỉ có ở hồ sơ): grid 1.6fr / 1fr với khối đầu tiên; xếp dọc dưới 768px. Nội dung: "Tín hiệu so với nhóm" (icon + chữ Trên / Ngang / Dưới / Trái chiều / Chưa đủ dữ liệu) và "Phạm vi" (số thành viên, "Số liệu có nguồn {matched}/{checked}").

**ProcessLink, SourceNotes, TechnicalDetails:**
- `ProcessLink`: "Xem quá trình phân tích · {agent} · {vòng} · {thời lượng}", mở `ProcessTrace` của ER-6 trong `Sheet`.
- `SourceNotes`: danh sách `id="note-n"`, title là link mở url (tab mới, `rel="noopener"`), kèm locator. Cuối cùng là các dòng cố định: "Số liệu do code tính từ BCTC gốc, agent chỉ diễn giải.", "Mẫu {n} ngân hàng, không đại diện toàn ngành." (khi có so sánh nhóm), "Không phải khuyến nghị đầu tư.", cùng `limitations`.
- `TechnicalDetails` thu gọn mặc định, chứa `EvidenceTrailTable` và `narrative_audit` (câu bị loại, khối bị bỏ). Đây là **nơi duy nhất** được hiện ID kỹ thuật.

## 3. Thư viện hình (`frontend/src/features/equity-report/charts/`), SVG thuần, không thêm dependency

Props chung: `{ dataset: Dataset; metrics: MetricPresentation[]; highlight: string[] }`. Quy ước chung cho mọi hình:
- thực thể được highlight tô `--accent`, còn lại `--text-secondary` hoặc `--border-strong`;
- ô thiếu không vẽ, và hình có ghi chú "{mã} {kỳ} chưa có số liệu đã kiểm định";
- mỗi điểm hoặc thanh focus được (`tabIndex=0`) với `aria-label` đầy đủ, có tooltip khi hover hoặc focus: "{mã} · {chỉ tiêu}: {giá trị} · {kỳ}";
- số định dạng vi-VN theo `decimals`;
- responsive theo `viewBox`, không bị cắt ở 390px.

| chart | dataset.shape | Mô tả |
|---|---|---|
| `KpiStrip` | kpi | 1–6 ô chỉ số: nhãn, giá trị, dòng phụ (hạng hoặc delta nếu có fact) |
| `RankedBar` | ranked_list | thanh ngang sắp theo giá trị, **bắt đầu từ 0**, đường trung vị nét đứt có chữ "trung vị", nhãn giá trị cuối thanh |
| `LineTrend` | series | trục X là kỳ, đường của entity (2px) và đường trung vị (nét đứt), điểm ở từng kỳ, nhãn cuối đường; kỳ thiếu thì ngắt đường |
| `SmallMultiples` | series_multi | 1 panel mỗi metric (4 cột, 2 cột dưới 768px); entity highlight là accent, các entity khác mảnh xám; 3 mốc trục Y từ `niceTicks` |
| `Scatter` | paired | trục có nhãn và đơn vị, đường trung vị hai trục, nhãn điểm tránh đè (thử phải, trái, trên, dưới) |
| `RankHeatmap` | peer_table | hàng = thực thể (highlight đứng đầu, in đậm), cột = metric, ô ghi "giá trị #hạng", nền theo `rank_better` (1: success 40%, 2: 18%, giữa: trong suốt, áp chót: danger 18%, chót: 36%; `color-mix`); metric neutral không tô; có dòng "Trung vị" và chú thích chiều tốt/xấu |
| `GroupedBar` | comparison_table / peer_table | mỗi metric một cụm, mỗi thực thể một cột (tối đa 3 thực thể), trục từ 0 |
| `ComparisonTable` | comparison_table / peer_table | bảng; ô tốt hơn theo chiều tốt được in đậm, kèm dấu ▲ có `aria-label="tốt hơn"` (không chỉ dùng màu) |

`CHARTS: Record<ChartType, Component>`. Chart không có trong map thì render `DataTable`.

## 4. Định dạng (`frontend/src/shared/lib/formatting.ts`)
- `fmtPct(v,d)` → "21,7%"; `fmtPp(v,d)` → "3,1 điểm %"; `fmtTimes(v,d)` → "2,4 lần"; `fmtRank(r,n)` → "2/5"; `fmtPeriod("2024_Q4")` → "Quý 4/2024"; `fmtPeriodRange` → "Q1–Q4/2024".
- Dùng `Intl.NumberFormat('vi-VN')`. `decimals` lấy từ capabilities.
- Không bao giờ hiện `bank.roe`: dùng `shortLabel`.

## 5. Test
- Mỗi fixture trong 5 fixture ER-1 render không lỗi. Snapshot có đúng loại khối và số hình:

  | fixture | Kết quả mong đợi |
  |---|---|
  | lookup | AnswerCardLayout, không có Headline |
  | ranking | Headline, RankedBar, KeyPoints, Callout |
  | trend | Headline, LineTrend |
  | h2h | Headline, ComparisonTable, Callout |
  | profile | Headline, SignalsAside, Scatter, RankHeatmap, SmallMultiples, Callout |

- Không có chuỗi `bank.` hay `fact:` ngoài `TechnicalDetails`.
- Số chú thích trỏ đúng note.
- Từng chart:
  - `RankedBar` bắt đầu từ 0 và có đường trung vị;
  - `LineTrend` ngắt tại kỳ thiếu (không có đoạn nối qua);
  - `RankHeatmap` có chữ "#hạng";
  - `Scatter` có `aria-label` từng điểm, tooltip khi focus;
  - `ComparisonTable` có ▲ kèm aria-label.
- Khối có `type` lạ thì bị bỏ qua, không crash. Chart lạ thì ra `DataTable`.
- `niceTicks` và các hàm format.
- Report không có `report_version` thì ra `LegacyReport`.

## 6. Kiểm tra thủ công (ảnh chụp trong PR)
- 5 fixture ở 1440px và 390px. In PDF (`@media print`: ẩn sidebar, nút, khối kỹ thuật; hình không bị cắt).
- Đặt cạnh mockup D/E: cùng khối và cùng thứ tự.

## Checklist review
- [ ] Render đúng mọi dạng câu hỏi; không có bố cục cứng theo một dạng.
- [ ] 8 chart đúng quy tắc design 15.x: trục bar từ 0, có tooltip, có bảng thay thế, màu không phải kênh duy nhất.
- [ ] Ô thiếu không vẽ và có ghi chú; không có số 0 giả.
- [ ] Không lộ ID kỹ thuật ngoài "Chi tiết kỹ thuật".
- [ ] Report cũ vẫn mở được. Bản in đẹp. Lint, test, build pass.
