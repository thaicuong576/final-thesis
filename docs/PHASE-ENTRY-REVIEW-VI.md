# Adversarial phase-entry review

Ngày kiểm tra: 2026-09-05

## Kết luận ngắn

Project đủ điều kiện để bắt đầu **guarded build**, viết Chương 1–4 song song và
chuẩn bị baseline trên pilot Gold. Project chưa đủ điều kiện để bắt đầu
provider-backed baseline hoặc tuyên bố multi-agent tốt hơn single-agent.

Đây không phải hai kết luận mâu thuẫn. Build deterministic có thể tiến hành
trên interface, fixture và contract đã kiểm thử; còn mọi kết luận thực nghiệm
phải chờ Gold snapshot được review độc lập và promote.

## Audit theo chuẩn fact–assumption–conclusion

### Facts đã có trong artifact

- Full deterministic suite: `200` tests pass.
- Core question set: `13` câu, core plan: `39` jobs, plan validation không có
  blocker.
- Candidate snapshot v4 remains the source assembly surface; it adds three ACB
  Q2--Q4 consolidated ROE candidates with input/formula/page provenance. The
  completed addendum selected those routes into a new v2 ledger; the promoted
  Gold snapshot is separate from staging.
- Core pilot đại diện `46/48` target routes; hai gap là ACB `2024_Q1`
  `bank.llr_coverage` và `bank.roa`.
- Checker A and the independent Checker B have both reviewed `48/48`. The
  v1 adjudicated ledger is eligible with `41` accepted and `7` reasoned-missing
  final cells; `141` labels were exported non-mutatingly. The later v2 ledger
  adds the independent ROE addendum and is the ledger used for Gold promotion.
- The separate ACB ROE addendum is complete at `3/3` and independently accepts
  the Q2--Q4 consolidated TTM ROE routes. The v2 ledger selects `checker_b`
  for those three cells while preserving the original v1 ledger.
- The promoted pilot Gold snapshot has `44/48` valid numeric cells and `4/48`
  explicit reasoned-missing cells; every core metric has `11/12` coverage.
- Vòng Checker A có tín hiệu thời gian 48 hàng trong `0.4308` giờ, tương đương
  `111.4` hàng/giờ. Đây chỉ là timestamp-based planning signal của một private
  pass, không phải năng suất OCR/manual của người, không phải independent review,
  và không phải bằng chứng Gold; chi tiết nằm trong
  `reports/data-foundation/pilot-review-throughput-signal.md`.
- Staging DB hashes vẫn bất biến; persisted offline fixture v9 là legacy
  schema 2, còn manifest mới có thể ghi prompt fingerprint.

### Assumptions còn cần giữ ở mức giả định

- Advisor sẽ chấp thuận pilot-gated scope thay vì yêu cầu ngay 5 ngân hàng × 8
  quý.
- Các metric có thể được định nghĩa nhất quán giữa nguồn issuer-IR, filing và
  candidate vendor sau khi review.
- Có thể giữ provider/model access và chi phí trong giới hạn triển khai được
  sau khi formal readiness handoff được duyệt; điều này chưa được kiểm chứng.

### Diễn giải được phép nói lúc này

- Kiến trúc source-grounded và ba experiment arms là khả thi về mặt kỹ thuật.
- Hệ thống có đường đi reproducible từ source → observation → evidence →
  Gold → agent manifest.
- Multi-agent là một hypothesis cần đo, không phải contribution đã được chứng
  minh.

### Những điều chưa được phép kết luận

- Database đã đầy đủ hoặc là live/production-quality.
- Single-agent hay multi-agent có factual accuracy, evidence completeness,
  latency hoặc cost tốt hơn.
- Provider prompt đã được calibration.
- Macro extension đã có đủ dữ liệu chính thức để đưa vào aggregate.

## Strongest case against việc bắt đầu build ngay

Một reviewer khó tính có thể nói rằng `200` tests chỉ chứng minh plumbing:
schema, routing, provenance và call shape; chúng không chứng minh answer quality,
source comparability hay khả năng vận hành với provider thật. Phản biện này
đúng nếu “bắt đầu build” được hiểu là chạy agent thật.

Nó không bác bỏ guarded build hiện tại, vì build surface được giới hạn rõ:
không provider call, không live retrieval, không comparative claim và không
thực hiện thêm promotion ngoài Gold snapshot đã được kiểm tra. Do đó wording
đúng là **build deterministic trước baseline**, không phải “đã sẵn sàng chạy
experiment”.

## Điểm yếu nhất và cách xử lý

Điểm yếu nhất là semantic validity của database: sign/denominator/period basis
và consolidated-versus-standalone scope chưa được checker độc lập xác nhận.
Thêm agent hoặc thêm vector database không giải quyết được điểm này.

Cách xử lý:

1. giữ nguyên staging và candidate rows;
2. dùng Gold snapshot v2 đã promote cho bank-core pilot;
3. hoàn tất formal advisor confirmation về scope/cutoff và mở
   `READY_FOR_BASELINE`;
4. cung cấp provider/model config không chứa secret và real transport được
   inject;
5. nếu một metric mở rộng không comparable, tái tạo scope versioned mới,
   không sửa 48-cell artifacts tại chỗ.

## Kill conditions

- Nếu pilot không đạt independent labels, source acceptance hoặc coverage gate,
  không chạy baseline; ghi `NOT_READY` và nêu gap cụ thể.
- Nếu ROA không comparable, loại ROA khỏi core bằng fallback đã version hóa,
  không suy diễn hoặc lấy absolute value để lấp gap.
- Nếu hierarchical arms không cải thiện score, vẫn giữ kết quả đó; không thêm
  agent để ép superiority.
- Nếu review/OCR vượt time-box, giữ pilot nhỏ và báo limitation thay vì mở lên
  80/200 ô.

## Phase-entry decision

| Surface | Decision | Điều kiện tiếp theo |
|---|---|---|
| Deterministic query, schema, runtime, prompt, manifest | `GO` | Có thể build/test và viết Chương 1–4 |
| Offline fixture/non-comparative replay | `GO` | Chỉ dùng làm plumbing evidence |
| Provider-backed execution | `GO — pilot complete` | 39/39 Gold-bound jobs completed with exact `gpt-5.6-luna`; keep artifacts immutable |
| Comparative claims | `HOLD` | Blind-score all 39 manifests with the frozen rubric before interpreting superiority |
| Scope expansion 80/200 | `HOLD` | Pilot Gold + throughput/conflict rate + advisor approval |

## Next action có giá trị cao nhất

Không mở thêm agent role hay data source mới. Hành động có giá trị cao nhất là
blind-score output của 39 jobs theo rubric cố định, sau đó aggregate accuracy,
evidence, missing/conflict, latency và cost. Trong lúc review, giữ nguyên Gold
snapshot và provider artifacts; không biến tool-call count thành proxy cho
chất lượng và không viết superiority claim trước khi có scoring.
deterministic surface đã được ghi trong `docs/PHASE-TRANSITION-CHECKLIST-VI.md`.
