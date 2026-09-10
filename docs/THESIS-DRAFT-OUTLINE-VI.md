# Outline khóa luận cập nhật - bản làm việc

Trạng thái: có thể bắt đầu viết các phần không phụ thuộc kết quả; các phần
đánh giá vẫn bị khóa cho đến khi có gold snapshot và run manifest.

Bản prose draft hiện tại: `docs/THESIS-DRAFT-CHAPTERS-1-4-VI.md`.

## Tên đề tài làm việc

**Thiết kế và đánh giá prototype phân tích tài chính dựa trên nguồn dữ liệu có
truy nguyên bằng kiến trúc single-agent và hierarchical multi-agent**

Tên này cố ý dùng “prototype” và “đánh giá”, không hứa hẹn một hệ thống tư vấn
đầu tư production hoặc ưu thế phổ quát của multi-agent.

## Câu hỏi nghiên cứu

Trên cùng một snapshot dữ liệu đã kiểm chứng, cùng bộ câu hỏi, tools, source
policy và model configuration, hierarchical Macro/Sector/Company có cải thiện
độ đúng, độ đầy đủ bằng chứng và xử lý bất nhất so với single-agent đủ nhiều để
bù thêm latency, số lần gọi và cost hay không?

## Đóng góp dự kiến

1. Một pipeline source-grounded cho dữ liệu tài chính ngân hàng Việt Nam, tách
   dữ liệu thô, staging, normalized và gold.
2. Một data/agent contract bảo đảm metric, period, unit, source và locator được
   truyền qua các boundary.
3. Một so sánh công bằng giữa single-agent, hierarchical không critique và
   hierarchical có critique giới hạn.
4. Một đánh giá có cả mặt lợi ích, chi phí, lỗi và trường hợp multi-agent không
   cải thiện.

## Chương 1 - Giới thiệu

### Có thể viết ngay

- vấn đề phân tích nhiều tầng: macro, sector, company;
- rủi ro số liệu tài chính thiếu nguồn, lệch kỳ và khác định nghĩa;
- mục tiêu prototype và phạm vi ngân hàng niêm yết;
- câu hỏi nghiên cứu, đóng góp và non-goals;
- lý do cần baseline công bằng.

### Không được khẳng định trước kết quả

- “multi-agent tốt hơn single-agent”;
- “database đầy đủ/live”;
- khả năng tư vấn đầu tư hoặc triển khai production.

Artifact nền: `docs/SPEC.md`, `docs/NEXT-PHASE-PRIORITIES.md` và one-pager xin
duyệt phạm vi.

## Chương 2 - Cơ sở lý thuyết và bối cảnh

- các metric ngân hàng: NPL nhóm 3–5, coverage, ROA, ROE;
- khác biệt point-in-time, quarter-only, YTD, annual và TTM;
- source-grounded QA và provenance;
- single-agent, task decomposition, critique và trade-off latency/cost;
- giới hạn của việc suy luận nguyên nhân từ số liệu quan sát.

Artifact nền: `docs/METRIC-DICTIONARY.md`, tài liệu nghiên cứu và bảng source
hierarchy. Chương này phải ghi rõ metric nào là định nghĩa của luận văn, metric
nào là source-disclosed variant.

## Chương 3 - Phương pháp nghiên cứu

- quy tắc chọn issuer/period và pilot-first decision tree;
- source ladder và quality status;
- immutable raw/staging, reconciliation register và gold promotion;
- ba experiment arms và fairness controls;
- câu hỏi cố định, blind scoring, atomic claims và reason codes;
- primary/secondary outcomes và threats to validity.

Artifact nền: `docs/DATA-READINESS-CHECKLIST.md`,
`docs/EVALUATION-PROTOCOL.md`, `experiments/question-set-core-v1.json`,
`experiments/question-set-v1.json` và `experiments/scoring-rubric-v1.md`.

## Chương 4 - Thiết kế hệ thống

- logical flow từ raw source đến gold snapshot và report;
- deterministic quantitative plane;
- evidence plane và page-aware locator;
- single-agent baseline;
- Macro/Sector/Company workers;
- Master Orchestrator, anomaly triggers và tối đa hai verification attempts;
- contract validator và fail-closed boundary.

Artifact nền: `docs/ARCHITECTURE.md`, `docs/DATA-CONTRACT.md`,
`src/thesis_data/` và `tests/`.

## Chương 5 - Triển khai

Chỉ chốt sau khi có run reproducible:

- cấu trúc project và data manifest;
- normalization và formula implementation;
- PDF inspection/OCR/manual review;
- query layer và experiment input guard;
- prompt/tool configuration;
- run logging, token/cost/latency capture.

Không dùng số candidate hoặc số lần download làm bằng chứng cho chất lượng
thực tế.

## Chương 6 - Đánh giá

Chỉ viết sau khi gold labels, question set, rubric và run manifests được freeze:

- kết quả theo từng primary measure;
- paired comparison giữa ba arms;
- anomaly/error taxonomy;
- latency, model calls và cost;
- missingness và evidence completeness;
- null hoặc negative findings;
- threats to validity và giới hạn generalization.

Không gộp “văn phong hay” vào factual correctness.

## Chương 7 - Kết luận

- trả lời đúng câu hỏi nghiên cứu ở mức prototype;
- nêu trade-off và điều kiện áp dụng;
- phân biệt kết quả đã đo với hướng mở rộng;
- đề xuất mở rộng 80/200 cells, securities sector hoặc realtime chỉ như future
  work nếu có nguồn và validation tương ứng.

## Bảng/figure nên chuẩn bị

1. sơ đồ data plane và agent plane;
2. bảng metric dictionary và period basis;
3. source ladder và trạng thái quality;
4. scope decision tree 48/80/200;
5. bảng fairness controls giữa ba arms;
6. bảng error taxonomy;
7. bảng kết quả quality-cost-latency.

## Quy tắc viết trong giai đoạn hiện tại

- dùng “proposed”, “pending validation”, “candidate” cho phần chưa gold;
- dùng “validated” chỉ khi có source, locator, checker và promotion gate;
- mọi số liệu trong chương kết quả phải truy ngược được về run manifest;
- nếu pilot thất bại, coi đó là phát hiện về giới hạn nguồn và thu hẹp metric;
- không sửa tài liệu thesis nguồn gốc; outline này là artifact làm việc mới.
