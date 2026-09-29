# ER-8 · Đánh giá A/B/C trên kiến trúc report mới

Nhánh: `feat/er-8-evaluation-harness` · PR: `feat(eval): [ER-8] protocol v2, A/B/C run harness, deterministic scoring and blinded packet`

Phụ thuộc: ER-4 (công tắc `ANALYSIS_ARM`, verifier, critic, revision) và ER-5 (trace, đếm token) đã merge.

Mục tiêu: có một thí nghiệm A/B/C **công bằng, tái lập được** cho chương 5 của luận văn. PR này chỉ xây công cụ và đóng băng protocol. Chạy thật với model (tốn tiền) là bước riêng ER-8-run, cần người dùng duyệt ngân sách.

Đọc trước: `docs/EVALUATION-PROTOCOL-V1-DRAFT.md`, `docs/EVALUATION-FREEZE-READINESS-2026-09-27.md`, D-075 §8 trong `docs/DECISIONS.md`, `data/evaluation/p4-*.json*`, `scripts/verify_p4_evaluation_inputs.py`, ER-4 §9 (arm), ER-5 (trace, token).

## 1. Vì sao cần protocol v2

Protocol v1 viết cho pipeline cũ (claim + Stage-1 + writer/critic cũ). D-075 đã thay pipeline: plan đóng băng theo loại câu hỏi, fact tất định, câu có trích fact, report theo khối. Chỉ số đo phải bám vào các đối tượng mới (fact, câu đã kiểm, NarrativeAudit, ReportSpec, trace). **Không sửa file v1**; tạo v2 và ghi decision mới.

## 2. Bộ câu hỏi v2 (file mới, không sửa file p4 v1)

`data/evaluation/er8-questions-v2.jsonl`, `er8-task-specs-v2.json`, `er8-expected-coverage-v2.json`. Hash theo `canonical_lf_utf8_sha256`.

Câu hỏi viết bằng tiếng Việt tự nhiên như người dùng thật (không nhồi hướng dẫn định dạng như v1). Phủ đủ 5 loại câu hỏi đang bật:

| ID | Loại | Ý câu hỏi | Nguồn |
|---|---|---|---|
| T01 | company_profile | Sức khỏe tài chính MBB quý 4/2024 so với nhóm | v1 T01 |
| T02 | company_profile | Chất lượng tài sản và sinh lời VCB quý 4/2024 | v1 T02 |
| T03 | lookup (thiếu dữ liệu) | Nợ xấu ACB quý 1/2024 | v1 T03 — phải nói rõ thiếu, không ước tính |
| T04 | trend | Xu hướng nợ xấu và bao phủ nợ xấu của TCB năm 2024 | v1 T04 |
| T05 | trend | ROA, ROE của MBB thay đổi thế nào qua các quý 2024 | v1 T05 |
| T06 | ranking | Ngân hàng nào có nợ xấu thấp nhất quý 4/2024 | v1 T06 |
| T07 | ranking | Xếp hạng ROE các ngân hàng quý 4/2024 | v1 T07 |
| T08 | company_profile nhiều kỳ | ACB đánh đổi chất lượng tài sản và sinh lời thế nào trong 2024 so với nhóm | v1 T08 (nay chạy được qua trend + median_delta) |
| T09 | head_to_head | So sánh ACB và TCB quý 4/2024 | mới |
| T10 | head_to_head | VCB hay VPB tốt hơn về chất lượng tài sản quý 4/2024 | mới |
| R1 | từ chối | Nợ xấu VCB quý 1/2025 (kỳ không có) | v1 T09 |
| R2 | từ chối | Phân tích CTG quý 4/2024 (ngoài nhóm Gold) | v1 T10 |

`expected-coverage` ghi cho mỗi task: loại câu hỏi mong đợi, entity, metric, kỳ, các ô phải có fact hoặc phải được khai báo thiếu, và mẫu số nhóm so sánh. Số liệu đối chiếu lấy từ Gold v5 bằng script, không gõ tay.

## 3. Công bằng giữa các arm

- **Plan đóng băng một lần cho mỗi task**: chạy planner (`model_with_fallback`) một lần, lưu `spec` + `plan` + hash vào `experiments/er8/plans/<task>.json`. Cả 3 arm và mọi lần lặp dùng đúng plan đó. Cần một điểm nạp plan cho runtime, chỉ dùng trong đánh giá: tham số `frozen_spec` ở tầng application (`_AdaptiveRun`), không lộ ra API công khai. Test: cùng `frozen_spec` thì 3 arm có tập fact giống hệt nhau.
- Cùng snapshot (kiểm SHA-256 raw bytes `1b1b5c09…ce73` trước khi chạy), cùng model/phiên bản, cùng temperature, cùng catalog, cùng verifier, cùng danh mục khối.
- Ghi `prompt_sha256` cho mọi lần gọi model (render xong mới hash) vào trace.

## 4. Harness chạy `scripts/er8_run.py`

```
python scripts/er8_run.py --plan-only             # bước 1: đóng băng plan
python scripts/er8_run.py --dry-run               # offline stub, kiểm pipeline
python scripts/er8_run.py --reps 2 --seed 20260929 --budget-usd <N>
```

- Thứ tự chạy ngẫu nhiên theo seed ghi lại; retry chỉ cho lỗi mạng/rate limit, tối đa 2 lần, theo một chính sách ghi trong manifest. Không bao giờ chạy lại vì điểm thấp.
- Dừng cứng khi chi phí cộng dồn vượt `--budget-usd`; run đang dở được ghi là `aborted_budget`, vẫn nằm trong mẫu số.
- Mỗi run ghi `experiments/er8/runs/<run_id>.json`: task, arm, lần lặp, thứ tự, hash snapshot/câu hỏi/plan, model, `prompt_sha256[]`, thời gian, số lần gọi, token vào/ra, chi phí, số vòng revision, trạng thái cuối, response đầy đủ (ReportSpec, facts, NarrativeAudit, findings) và trace.
- `experiments/er8/manifest.json` gom các thông tin trên + seed + phiên bản rubric.
- Run thất bại hoặc bị chặn vẫn được lưu và tính vào mẫu số.

## 5. Chấm tất định `scripts/er8_score.py`

Tính từ file run, không gọi model:

| Chỉ số | Cách đo |
|---|---|
| Hoàn thành | trạng thái cuối trên tổng số run dự kiến |
| Đúng số | mọi số trong câu được giữ lại khớp fact được trích (sau làm tròn hiển thị), và mọi fact tái tính khớp Gold v5 |
| Truy vết | mọi `input_observation_ids` resolve được tới observation, nguồn, locator |
| Độ phủ | ô bắt buộc trong `expected-coverage` có fact hoặc được khai báo thiếu đúng |
| Xử lý thiếu dữ liệu | T03 và ACB Q1 trong T08: không có số bịa, có câu giới hạn |
| Từ chối đúng | R1, R2 bị chặn trước khi gọi model phân tích |
| Chất lượng câu | tỷ lệ câu bị verifier loại, số câu còn lại, số câu có trích fact |
| Liên kết tầng | số cross-level finding được nêu trong report so với số ứng viên từ ER-3 |
| Chi phí | độ trễ, số lần gọi, token, chi phí, số vòng revision |

Xuất `experiments/er8/scores/deterministic.csv`.

## 6. Gói chấm mù `scripts/er8_blind_packet.py`

- Render mỗi report thành HTML tĩnh (dùng lại renderer frontend qua build tĩnh, hoặc HTML server-side đơn giản có cùng nội dung khối), bỏ mọi dấu hiệu arm (arm, số vòng revision, trace).
- Đặt mã ngẫu nhiên, trộn thứ tự theo seed riêng; file khóa `blind-key.json` để ngoài gói.
- Form chấm `blind-scores.csv`: 4 tiêu chí 0–4 (mạch lạc, nêu giới hạn/bất định, hữu ích cho chuyên viên phân tích, liên kết giữa các tầng khi plan có khai báo). Rubric có ví dụ neo cho từng mức, viết trong `docs/EVALUATION-PROTOCOL-V2.md` **trước** khi chạy.
- Chọn trước 20% report để chấm lại sau ít nhất 24 giờ (đo độ nhất quán của cùng người chấm).

## 7. Phân tích `scripts/er8_analyze.py`

- Bảng theo arm × loại câu hỏi: dự kiến/hoàn thành/thất bại, các chỉ số tất định, điểm mù, chi phí.
- Chất lượng chỉ tính run hoàn thành, và chất lượng có điều chỉnh theo tỷ lệ hoàn thành.
- Khác biệt theo cặp (cùng task, cùng lần lặp) C−B, B−A, C−A; bootstrap khoảng tin cậy, ghi rõ là khám phá vì mẫu nhỏ.
- Xuất CSV + hình (PNG/SVG) + `experiments/er8/RESULTS.md` để đưa vào chương 5.

## 8. Tài liệu và decision

- `docs/EVALUATION-PROTOCOL-V2.md`: arm, bộ câu hỏi, số lần lặp (mặc định 2: 12 task × 3 arm × 2 = 72 run), seed, rubric có neo, chính sách retry, ngân sách, cách xử lý thiếu dữ liệu. Ghi rõ v1 và pilot 75 job là bằng chứng lịch sử, không gộp.
- Decision D-076: đóng băng protocol v2 (hash câu hỏi, task spec, expected coverage, rubric, seed) trước run chấm điểm đầu tiên.
- Cập nhật `docs/EVALUATION-FREEZE-READINESS-*` bằng file ngày mới, không sửa file cũ.

## 9. Test (offline, không gọi mạng — dùng `tests/socket_guard.py`)

- `--dry-run` với writer/critic stub chạy hết 12 task × 3 arm, sinh đủ file run, manifest, điểm tất định.
- Cùng `frozen_spec` ⇒ tập fact giống nhau giữa 3 arm; arm `single_agent` không có critic; `hierarchical_no_critique` không có revision.
- Budget guard dừng đúng và ghi `aborted_budget`.
- Scorer bắt được số bịa (câu có số không có trong fact) và observation không resolve.
- Gói mù không chứa chuỗi arm/revision/trace.
- Hash câu hỏi v2 khớp giá trị trong task spec.

## 10. Ngoài phạm vi PR này

- Chạy thật 72 run với model (ER-8-run, orchestrator chạy sau khi người dùng duyệt ngân sách và model).
- Chấm mù (người dùng tự chấm).
- Viết chương 5.

## Checklist review

- [ ] Không sửa file p4 v1, protocol v1, freeze readiness cũ.
- [ ] `frozen_spec` không lộ ra API công khai.
- [ ] Không có số Gold gõ tay trong expected coverage.
- [ ] Run thất bại nằm trong mẫu số.
- [ ] Gói mù không lộ arm.
- [ ] Không test nào gọi mạng.
