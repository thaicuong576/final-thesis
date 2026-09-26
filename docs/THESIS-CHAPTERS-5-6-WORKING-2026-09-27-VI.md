# CHƯƠNG 5–6. KẾT QUẢ, THẢO LUẬN VÀ KẾT LUẬN — BẢN WORKING

**Ngày:** 27/09/2026
**Trạng thái:** working draft; chưa phải bản khóa luận cuối cùng.
**Nguyên tắc:** không thay thế kết quả còn thiếu bằng số liệu giả, fixture
offline hoặc historical pilot.

Tài liệu này tiếp nối đề cương sáu chương tại
[`THESIS-DRAFT-OUTLINE-VI.md`](THESIS-DRAFT-OUTLINE-VI.md). Những kết luận
được viết dưới đây chỉ sử dụng các bằng chứng đã có trong repository. Các ô
đánh dấu `PENDING` phải được thay bằng run manifest, snapshot, model/prompt
identity và phiếu chấm tương ứng trước khi nộp bản cuối.

---

## CHƯƠNG 5. KẾT QUẢ VÀ THẢO LUẬN

### 5.1. Quy ước đọc kết quả

Kết quả của đề tài được chia thành ba tầng để tránh nhầm lẫn giữa khả năng
đã kiểm tra và mục tiêu chưa đạt:

| Tầng bằng chứng | Artifact đại diện | Có thể kết luận | Không được suy ra |
|---|---|---|---|
| Dữ liệu và chuyển giao | [`P1 data portability preflight`](P1-DATA-PORTABILITY-PREFLIGHT-2026-09-26.md) | Một gói CTG Q4/2024 đã đi qua đường source reconciliation và operational snapshot với các metric được kiểm tra. | Gold promotion, hỗ trợ mọi ngân hàng/PDF hoặc kết quả benchmark cuối. |
| Runtime offline | [`P2 implementation verification`](P2-IMPLEMENTATION-VERIFICATION-2026-09-26.md), [`P4A runtime evidence`](P4A-IMPLEMENTATION-VERIFICATION-2026-09-26.md) | Một số đường Company/Peer, Stage-1, SSE, run-history và bounded revision hoạt động với provider/writer/critic fixture rõ ràng. | Chất lượng live model, readiness của deployment hoặc ưu thế A/B/C. |
| Live app và thực nghiệm | [`freeze readiness record trên PR #66`](https://github.com/thaicuong576/final-thesis/pull/66), teacher checklist trên PR #64 | Tại thời điểm bản working, các cổng còn được ghi nhận là chưa đạt và việc không chấm điểm là đúng quy trình. | Có URL live tạo report, walkthrough pass hoặc ranking giữa A/B/C. |

Historical pilot 75 jobs/61 hoàn tất chỉ là bằng chứng khả thi trước đó. Vì
pilot không chứng minh targeted revision của phiên bản hiện hành nên không được
gộp vào kết quả của thực nghiệm A/B/C này.

### 5.2. Kết quả đường dữ liệu và ngân hàng ngoài Gold

Case CTG Q4/2024 cho thấy contract onboarding có thể giữ tách biệt dữ liệu
ứng viên, operational snapshot và Gold benchmark. Preflight ghi nhận 22 quan
sát duy nhất, gồm 15 input trực tiếp và 7 giá trị dẫn xuất. Các input được đối
soát với filing primary, locator, kỳ, đơn vị và reporting scope; bảy giá trị
dẫn xuất được tính lại bằng formula version và lưu calculation receipt.

Kết quả này quan trọng ở hai điểm. Thứ nhất, việc một CSV có cấu trúc hợp lệ
không tự làm cho giá trị trở thành bằng chứng chấp nhận được. Thứ hai, đường
promotion không sửa Gold v5 và không đưa CTG vào tập peer benchmark. Snapshot
CTG vì vậy là operational snapshot riêng, đủ để chứng minh transferability cho
case và metric đã kiểm tra, nhưng chưa phải bằng chứng rằng lõi phân tích đã
chấp nhận mọi ngân hàng mới.

Không có `LLAMA_CLOUD_API_KEY` trong môi trường kiểm tra nên không chạy pilot
LlamaParse/OCR. Đây là giới hạn được báo cáo, không phải lỗi cần che giấu.
PDF scan, bảng hoặc biểu đồ được parse trong tương lai vẫn phải là candidate
và đối soát từng observation với trang gốc trước promotion.

### 5.3. Kết quả runtime và cổng kiểm soát

Các artifact P2/P4A ghi nhận những behavior sau trong môi trường offline:

- request được chuyển thành plan có entity, metric, period, expected cells và
  capability trước retrieval;
- Company một kỳ, Company + Peer một kỳ và Company trend 2–4 kỳ sử dụng
  provider-backed observations, claim lineage và Stage-1;
- trend giữ danh sách kỳ có thứ tự, không gộp nhiều kỳ của cùng metric vào một
  map entry; ô thiếu phải được giữ dưới dạng missing có lý do;
- semantic critic tạo issue/action có cấu trúc trong fixture; revision chạy lại
  writer bị ảnh hưởng, re-synthesize và chạy Stage-1 lại, tối đa hai vòng;
- SSE chỉ phát trạng thái terminal thành công sau khi kết quả được persist;
  lỗi persistence đi theo `RUN_BLOCKED`.

Đây là kiểm chứng control-flow và hợp đồng. Các writer/critic trong probe là
offline fixtures được khai báo rõ trong test. Chưa có bằng chứng từ live model,
live accepted snapshot hoặc một request do giảng viên thực hiện trên deployment.
T08 (peer nhiều kỳ) vẫn ngoài scope runtime public hiện tại và không được đưa
vào scoring chỉ vì T04/T05 đã có probe offline.

### 5.4. Trạng thái ứng dụng và walkthrough giảng viên

Preflight GET ngày 26/09 cho thấy frontend public và `/api/health` có thể truy
cập, nhưng `/api/ready` trả `503`. `/api/capabilities` không có snapshot hoặc
dataset accepted, không có entities/periods/metrics, báo
`database_status=disconnected`, `analysis_available=false` và
`accepted_snapshot_unavailable`. Không có analysis request được gửi và không
có live report để dùng trong walkthrough.

Read-only recheck lúc 01:05 ICT ngày 27/09 (được ghi trong [teacher
walkthrough checklist trên PR #64](https://github.com/thaicuong576/final-thesis/pull/64))
cho kết quả cùng chiều: `/api/ready` vẫn trả 503 với
`dataset_snapshot_id=null`, `/api/capabilities` vẫn không có phạm vi chạy được,
trang Data hiển thị kho dữ liệu disconnected, nút bắt đầu ở Analysis disabled,
và Report Library gắn nhãn cả ba mục là dữ liệu giả lập. Đây là bằng chứng
deployment hiện tại đang chặn đúng, không phải bằng chứng walkthrough đã pass.

Vì vậy, checklist walkthrough phải được đọc là checklist nghiệm thu chứ không
phải biên bản pass. Các journey Dataset → Create Analysis → Session → Report,
Company/Peer, revision/SSE/history và responsive UI chỉ được đánh dấu pass khi
chạy được trên một deployment có snapshot/provider hợp lệ. HTTP 200 của
frontend hoặc health endpoint không đủ để thay thế `/api/ready`.

PR #67 là một patch reviewable nhằm pin và kiểm tra SQLite snapshot tại startup,
nhưng đang mở và chưa được merge; nội dung PR không phải bằng chứng deployment
đã được cấu hình. Không có deployment setting hoặc secret nào được thay đổi
trong bản working này.

### 5.5. Trạng thái thiết kế thực nghiệm A/B/C

Bộ candidate hiện dùng question set
`data/evaluation/p4-questions-v1.jsonl` với canonical LF UTF-8 SHA-256
`c4747af992441cc6063fa9dc08b1a09fc1a4a923a5415a2de4391c03e17fbc09`. Snapshot
Gold được protocol nhận diện là `gold-bank-2025-expanded-v5-evidence`, với
raw-byte SHA-256
`1b1b5c090d2f8ede87a4c33ea3ee716f7a54c9de7c51089f4d3893d7a1ffce73`.
Prompt register v1 dùng `prompt-contract-v1` và yêu cầu hash của prompt đã
render cho từng call.

Tuy nhiên, freeze-readiness record ngày 27/09 xác nhận:

| Kiểm soát | Trạng thái hiện tại |
|---|---|
| `protocol_final_freeze_ready` | `false` |
| `scoring_runs_created` | `false` |
| `ab_c_results_created` | `false` |
| T01–T10 `scoring_eligible_now` | đều `false` |
| Question set, snapshot, rubric, repetition, seed, model/prompt hashes | chưa đủ để freeze một run scoring |

Các blocker độc lập gồm query-adaptive peer runtime, multi-period contract,
critique/revision end-to-end thực tế, live readiness, teacher walkthrough,
rubric/repetition/seed và rendered prompt hashes. Do đó chưa được điền các
cột chất lượng, độ trễ, số call, token, cost hoặc tỷ lệ hoàn thành cho A/B/C.

Bảng dưới đây là khuôn kết quả cần điền sau freeze, không phải số liệu:

| Arm | Task | Planned | Completed | Failed/blocked | Numeric accuracy | Evidence/reference | Latency/calls/tokens/cost | Blind score |
|---|---|---:|---:|---:|---:|---:|---|---:|
| A | T01–T08 | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING |
| B | T01–T08 | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING |
| C | T01–T08 | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING |

Khi thực hiện, mọi run thành công, thất bại và incomplete phải ở lại mẫu số;
reviewer phải được làm mù arm, dùng rubric cố định và báo cáo cả completed-only
lẫn completion-adjusted quality. Không được thay rubric sau khi xem kết quả.

### 5.6. Thảo luận theo câu hỏi nghiên cứu

**RQ1 — Thiết kế hệ thống.** Kết quả offline và case CTG cho thấy có thể tách
provider, canonical contract, plan, specialist, Stage-1 và revision boundary
thành các lớp có thể kiểm tra. Việc này trả lời một phần RQ1 ở mức thiết kế và
implementation acceptance. Nó chưa chứng minh toàn bộ reference deployment vận
hành với provider thật.

**RQ2 — A so với B.** Chưa có dữ liệu hợp lệ để kết luận B cải thiện hay làm
giảm chất lượng so với A. Điều kiện so sánh cùng snapshot, question bytes,
model/version, prompt, tools, source policy, rubric và output contract chưa
được freeze thành scored run.

**RQ3 — B so với C.** Control-flow C đã được kiểm thử với fixture trong P4A,
nhưng chưa có kết quả live và chưa có blind scoring. Vì vậy không thể kết luận
semantic critique/bounded revision làm tăng chất lượng, tăng chi phí hay đạt
trade-off tốt hơn B.

### 5.7. Đe dọa đối với giá trị kết quả

Mẫu Gold nhỏ và tập task ứng viên giới hạn khả năng suy rộng. Việc một tác giả
chấm thủ công tạo single-rater limitation. Snapshot và period scope có thể
ảnh hưởng mạnh tới kết luận. Lỗi provider, timeout hoặc missingness nếu không
được giữ trong denominator sẽ tạo survivorship bias; vì vậy protocol yêu cầu
lưu failure. Cuối cùng, một fixture chứng minh thứ tự gọi không đo chất lượng
ngôn ngữ của live model.

---

## CHƯƠNG 6. KẾT LUẬN, HẠN CHẾ VÀ HƯỚNG PHÁT TRIỂN

### 6.1. Kết luận có giới hạn

Nghiên cứu đã xây dựng được một thiết kế hệ thống trong đó dữ liệu, source
evidence, request-derived plan, specialist, Stage-1 và semantic revision có
ranh giới rõ. Case CTG Q4/2024 chứng minh một đường onboarding ngoài Gold có
thể được source-reconcile, tính lại metric dẫn xuất và lưu thành operational
snapshot riêng. Các probe offline chứng minh một phần luồng adaptive analysis,
provenance, missingness và bounded revision.

Các kết luận trên không đồng nghĩa ứng dụng đã đạt nghiệm thu live. Readiness
deployment hiện còn blocked vì accepted snapshot/provider chưa được xác nhận;
teacher walkthrough chưa pass; protocol A/B/C chưa freeze và chưa có điểm
scoring. Đây là kết luận trung thực của trạng thái nghiên cứu tại ngày của bản
working, không phải thiếu kết luận cần được lấp bằng phỏng đoán.

### 6.2. Trả lời ba câu hỏi nghiên cứu

- **RQ1:** Kiến trúc phân cấp thích ứng phù hợp với yêu cầu truy nguyên khi
  planner đóng băng scope trước retrieval, provider chỉ trả accepted facts,
  code giữ arithmetic và Stage-1 chặn claim không đủ provenance. Kết luận này
  được giới hạn ở thiết kế và các đường runtime đã có kiểm chứng offline.
- **RQ2:** Chưa thể trả lời định lượng A và B khác nhau thế nào. Cần cùng
  snapshot, task set, prompt/model, tools, rubric và run manifest sau freeze.
- **RQ3:** Đã có bằng chứng control-flow cho C trong fixture, nhưng chưa thể
  trả lời liệu critique/revision có cải thiện chất lượng hay chi phí so với B.
  Bất kỳ kết luận superiority nào ở giai đoạn này đều vượt quá evidence.

### 6.3. Đóng góp có thể bảo vệ

Đóng góp thực tế của bản triển khai gồm: (1) hợp đồng dữ liệu có provenance và
missingness; (2) boundary giữa Gold, operational onboarding và run history;
(3) request-derived adaptive plan; (4) Stage-1 deterministic gate; (5) issue
và action có cấu trúc cho targeted revision; và (6) bộ kiểm soát pre-freeze
giúp không gọi fixture hoặc historical pilot là kết quả cuối.

Đóng góp thực nghiệm chỉ được bổ sung sau khi có run manifests và phiếu chấm
đủ điều kiện. Khi đó phải báo cáo cả kết quả bất lợi, không chỉ các output
hoàn tất hoặc điểm cao.

### 6.4. Hạn chế, tái lập và đạo đức

Hạn chế chính là chưa có live provider/readiness, cỡ mẫu Gold nhỏ, task peer
nhiều kỳ chưa được hỗ trợ, không có parser/OCR pilot do thiếu key, và chỉ có
một người chấm. Kết quả không được suy rộng thành đại diện toàn ngành hoặc
khẳng định mọi ngân hàng/PDF đều được xử lý.

Để tái lập, cần giữ exact question-set hash, snapshot/hash, formula version,
prompt version và rendered prompt hashes, model/provider version, seed,
repetition, rubric, source policy, timing, calls, tokens, cost và failure
records. Không commit secret hoặc dữ liệu riêng tư; không gửi filing chưa được
phê duyệt cho external model; OCR/parser output luôn phải qua review.

### 6.5. Lộ trình hoàn thiện sau bản working

1. Review và merge các PR đã qua CI chỉ khi người dùng cho phép; không coi CI là
   deployment smoke test.
2. Cấu hình tường minh accepted SQLite snapshot và run-history store tách biệt;
   xác minh hash, integrity, snapshot identity và `/api/ready`.
3. Chạy Company, Peer, missingness, trend và targeted revision trên public
   runtime; lưu run IDs, SSE events và report/evidence lineage.
4. Chạy checklist Dataset → Create Analysis → Session → Report trên link deploy
   bằng desktop và màn hình hẹp; ghi cả failure/blocked state.
5. Freeze task list, rubric, repetition, seed, model/provider, prompt hashes,
   source policy và budget; sau đó chạy A/B/C cùng snapshot và lưu mọi run.
6. Chấm mù, tính deterministic metrics và operational metrics, rồi mới thay
   các ô `PENDING` trong Chương 5 và khóa kết luận Chương 6.

### 6.6. Kết luận cuối của bản working

Hệ thống đã tiến tới một nền tảng có thể kiểm tra về dữ liệu, provenance,
adaptive planning và bounded revision; nhưng trạng thái đúng hiện tại là
**chưa đủ bằng chứng để công bố live application readiness hoặc kết quả A/B/C
cuối cùng**. Việc giữ nguyên giới hạn này bảo vệ tính trung thực của khóa luận
và tạo một điểm xuất phát rõ ràng cho cổng nghiệm thu tiếp theo.
