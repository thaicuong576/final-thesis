# Đề cương khóa luận sáu chương — bản làm việc có kiểm soát

**Trạng thái:** working outline; các chương có kết quả định lượng chỉ được
khóa sau khi artifact tương ứng đã qua cổng nghiệm thu.

Đề cương này là artifact biên tập được README tham chiếu. Bản nháp cũ
`docs/THESIS-DRAFT-CHAPTERS-1-4-VI.md` có cấu trúc bảy chương và được giữ lại
như tài liệu lịch sử, không phải outline nghiệm thu hiện hành. Tài liệu nguồn
`docs/Khoá luận tốt nghiệp - Cường - GVHD_ Lê Văn.md` và PDF đi kèm chỉ là
nguồn tham khảo, không được sửa trong track triển khai này.

## Chương 1. Giới thiệu

Trình bày bối cảnh phân tích cơ bản ngân hàng niêm yết tại Việt Nam, vấn đề
nghiên cứu, mục tiêu, ba câu hỏi nghiên cứu, phạm vi ngân hàng niêm yết và
đóng góp dự kiến. Chương phải nêu rõ nghiên cứu không mặc định hệ đa tác tử
hoặc vòng phản biện luôn tốt hơn baseline.

## Chương 2. Cơ sở lý luận và nghiên cứu liên quan

Trình bày phân tích tài chính ngân hàng, các chỉ tiêu CAMEL được chọn, dữ liệu
có provenance, mô hình ngôn ngữ, hệ đa tác tử phân cấp, adaptive planning,
Stage-1 và đánh giá chất lượng đầu ra. Phân biệt nền tảng lý thuyết với các
quyết định triển khai của case study.

## Chương 3. Phương pháp nghiên cứu

Mô tả nghiên cứu hướng ứng dụng, pipeline raw → candidate → accepted snapshot,
quy tắc missingness và source reconciliation, thiết kế request-derived plan,
ba arm A/B/C, rubric, run manifest và các cổng freeze. Không dùng fixture
offline làm bằng chứng live.

## Chương 4. Thiết kế và triển khai hệ thống

Mô tả ranh giới core/application, provider và snapshot, planner, specialist,
orchestrator, Stage-1, semantic critic, bounded revision, SSE/run history và
reference UI. Chỉ mô tả behavior đã có bằng evidence; giới hạn deployment phải
được giữ trong chương.

## Chương 5. Kết quả và thảo luận

Tách ba lớp bằng chứng: (i) data portability/operational onboarding, (ii)
implementation acceptance bằng provider/critic fixture, và (iii) live
deployment, teacher walkthrough, A/B/C scoring. Chỉ lớp (i) và (ii) có thể
được báo cáo khi chưa mở các cổng live; lớp (iii) phải dùng bảng kết quả có
run ID, snapshot, model, prompt, rubric và mẫu số.

## Chương 6. Kết luận, hạn chế và hướng phát triển

Trả lời RQ1–RQ3 theo đúng mức evidence, nêu giới hạn dữ liệu và evaluator,
không suy rộng từ mẫu năm ngân hàng thành toàn ngành, trình bày khả năng tái
lập và đạo đức dữ liệu, sau đó đề xuất các bước mở cổng live, freeze và đánh
giá công bằng.

## Quy tắc biên tập chung

- Mọi số liệu trong chương kết quả phải nối được tới artifact/manifest có hash,
  snapshot và locator; không lấy số từ prose không có lineage.
- `missing` không phải zero; kết quả bị chặn phải được báo cáo như kết quả
  kiểm soát, không xóa khỏi mẫu số một cách tùy tiện.
- Bản demo, mock, offline fixture, historical pilot và CI xanh không được gọi
  là live validation hoặc final A/B/C score.
- Khi PR #60 và các PR working draft chưa merge, bản report phải liên kết tới
  chúng như nguồn làm việc và ghi rõ trạng thái review, không giả định nội
  dung đã là main.

## Ma trận lắp ghép artifact hiện tại

Bảng này ngăn việc ghép nhầm bản nháp bảy chương với các phần đã được viết
theo outline sáu chương. Các PR dưới đây đều là review-only tại ngày ghi nhận;
việc chúng có CI xanh không làm nội dung trở thành `main` hoặc kết quả nghiệm
thu.

| Phần | Artifact/nguồn làm việc | Trạng thái lắp ghép |
|---|---|---|
| Chương 1–2 | `docs/THESIS-CHAPTERS-1-2-WORKING-2026-09-26-VI.md` | Có bản working; rà lại trích dẫn và thuật ngữ khi khóa report. |
| Chương 3 | [PR #60 — phương pháp nghiên cứu](https://github.com/thaicuong576/final-thesis/pull/60) | Open/green/review-only; không giả định đã merge. |
| Chương 4 | [PR #63 — thiết kế hệ thống](https://github.com/thaicuong576/final-thesis/pull/63) | Open/green/review-only; giữ giới hạn deployment trong chương. |
| Chương 5–6 | `docs/THESIS-CHAPTERS-5-6-WORKING-2026-09-27-VI.md` trên [PR #70](https://github.com/thaicuong576/final-thesis/pull/70) | Working draft; các kết quả live và A/B/C vẫn `PENDING`. |
| Cổng nghiệm thu | [PR #64 walkthrough](https://github.com/thaicuong576/final-thesis/pull/64), [PR #66 freeze readiness](https://github.com/thaicuong576/final-thesis/pull/66) | Evidence/control artifacts, không phải kết quả pass. |

Trước khi khóa bản sáu chương, người biên tập phải tạo một bản assembly mới
trên `main` mới nhất, kiểm tra RQ1–RQ3 xuất hiện nhất quán ở Chương 1, 3, 5 và
6, đối chiếu mọi số liệu với snapshot/run manifest, rồi thay thế `PENDING` chỉ
khi cổng tương ứng có evidence. Không được lấy bản nháp cũ bảy chương làm
nguồn lắp ghép mặc định.
