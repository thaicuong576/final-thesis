# CHƯƠNG 4. THIẾT KẾ VÀ TRIỂN KHAI HỆ THỐNG

> **Bản working ngày 27/09/2026.** Chương này mô tả kiến trúc và behavior đã
> được ghi nhận trong các tài liệu chuẩn của repository. Những phần được kiểm
> thử bằng provider, writer hoặc critic fixture được gọi rõ là bằng chứng
> implementation/offline; chúng không được diễn giải thành chất lượng mô hình
> thật, readiness của deployment, walkthrough với giảng viên hoặc kết quả
> A/B/C. Ứng dụng công khai vẫn chưa qua cổng `/api/ready` tại lần preflight
> gần nhất. Bản này giữ cấu trúc sáu chương đã được phê duyệt và không thay thế
> các artifact nguồn của khóa luận.

## 4.1. Nguyên tắc kiến trúc và ranh giới hệ thống

Hệ thống được thiết kế như một kiến trúc phân tích tài chính đa tác tử có thể
thay thế hạ tầng. Ứng dụng web là reference client để chứng minh một luồng
end-to-end; nó không phải nguồn chân lý của dữ liệu, công thức hoặc phạm vi
phân tích. Lõi phân tích giữ các hợp đồng claim, lập kế hoạch, điều phối,
kiểm tra xác định luận, phản biện và truy nguyên bằng chứng. Lớp ứng dụng giữ
HTTP, giao diện, cấu hình triển khai, lưu trữ runtime và các adapter cụ thể.
Ranh giới này cho phép thay frontend, SQLite hoặc model provider mà không phải
viết lại logic phân tích cốt lõi ([Architectural Guardrails](ARCHITECTURAL-GUARDRAILS.md)).

Luồng logic của một lượt phân tích được tổ chức như sau:

```text
request intent
  → capability và scope validation
  → frozen AnalysisPlan
  → provider-backed observations/evidence
  → active Company / Sector / Macro capabilities
  → synthesis và AtomicClaim[]
  → Stage-1 deterministic acceptance
  → semantic critique
  → targeted revision (tối đa hai vòng)
  → Stage-1 lần nữa
  → report, quality state và run history
```

Macro, Sector/Peer và Company là các năng lực độc lập. Một request chỉ phân
tích doanh nghiệp không tự động gọi Sector hoặc Macro; một capability không áp
dụng được biểu diễn là `NOT_APPLICABLE`, không phải một worker thất bại. Việc
phân tách này ngăn hệ thống tạo thêm nội dung hoặc chi phí chỉ để làm cho
workflow có vẻ nhiều tác tử hơn.

Ba đối tượng ràng buộc tính tái lập là `AnalysisPlan`, `DatasetSnapshot` và
`AtomicClaim`. Plan quy định entity, kỳ, metric, capability và các liên kết
xuyên tầng được phép. Snapshot quy định các quan sát được coi là sự thật cho
lượt chạy. Claim quy định assertion nào được công bố và nối assertion đó với
observation, source, locator hoặc document evidence. Report vì vậy là lớp
trình bày của claim graph, không phải nguồn sự thật độc lập.

## 4.2. Dữ liệu chuẩn, provider và provenance

### 4.2.1. Các trạng thái dữ liệu

Pipeline dữ liệu phân biệt rõ trạng thái của tài liệu và quan sát:

| Trạng thái | Vai trò trong hệ thống |
|---|---|
| Raw evidence | Tệp PDF, API response, CSV hoặc tài liệu được giữ bất biến và gắn hash/source metadata. Có tệp không đồng nghĩa các con số đã được chấp nhận. |
| Candidate | Giá trị đã parse hoặc map vào contract để chờ kiểm tra. CSV cấu trúc đúng và OCR chỉ tạo candidate. |
| Operational snapshot | Quan sát đã được đối soát với nguồn chính, locator, kỳ, đơn vị và reporting scope; metric dẫn xuất phải được tính lại bằng formula version và có calculation receipt. |
| Gold benchmark | Snapshot được promotion qua coverage, label, authority và independent-review gates. Chỉ snapshot này mới làm dữ liệu benchmark A/B/C. |

Một giá trị thiếu luôn là `null` kèm lý do, không phải số 0. Một quan sát hợp
lệ trực tiếp cần metric, entity, period, unit, period basis, source ID và
metric-specific source locator. Quan sát dẫn xuất giữ formula version và thứ tự
input observation IDs; source trực tiếp của nó có thể là `null` vì source trail
được giải qua các input đã chấp nhận. [Data and Agent Contracts](DATA-CONTRACT.md)
định nghĩa các trường này và cấm dùng snippet cùng tài liệu nhưng không có
association làm bằng chứng riêng cho một numeric claim.

Code xác định luận là nơi tính các tỷ lệ CAMEL, chuyển đổi YTD thành dòng quý,
lọc missingness và tính peer median. Model không phải nguồn sự thật số học.
Peer identity dùng tập thành viên được yêu cầu; numeric denominator chỉ dùng
thành viên có observation hợp lệ và phải giữ lý do loại từng thành viên. Vì vậy
median của năm ngân hàng trong case study không được gọi là median toàn ngành.

### 4.2.2. Provider và snapshot boundary

Lõi chỉ truy cập dữ liệu thông qua provider-neutral interface. Gold SQLite là
một adapter tham chiếu; ứng dụng không được đưa đường dẫn SQLite, tên bảng
hoặc tập năm ngân hàng vào logic phân tích dùng chung. Query boundary chỉ trả
quan sát valid và source record hợp lệ; pending, fallback, conflicting hoặc
unresolved rows không được nâng thành facts.

Đối với bank onboarding ngoài Gold, structural validation tạo candidate trước.
Reviewer phải đối chiếu từng giá trị với filing primary và locator chính xác.
Metric dẫn xuất phải được promotion boundary tính lại từ input đã chấp nhận,
kiểm tra tolerance và ghi receipt. CTG FY2024 Q4 là case transferability đã
được kiểm tra: 22 quan sát trong operational snapshot riêng, gồm 15 input trực
tiếp và 7 giá trị dẫn xuất. Case này chứng minh đường onboarding cho snapshot
và metric đã nêu, không mở rộng Gold benchmark và không chứng minh mọi PDF/CSV
đều được chấp nhận ([P1 data-portability preflight](P1-DATA-PORTABILITY-PREFLIGHT-2026-09-26.md)).

Analytical storage và mutable run history được tách thành hai boundary. SQLite
accepted snapshot phải được mở theo đường dẫn được cấu hình tường minh và không
được thay đổi khi lưu analysis run. `ANALYSIS_RUNS_DB_PATH` là store riêng cho
history; alias vật lý với `SQLITE_DB_PATH` phải bị từ chối. Quy tắc này bảo vệ
hash và tính bất biến của snapshot sau các lượt synchronous hoặc SSE.

## 4.3. Lập kế hoạch thích ứng theo yêu cầu

### 4.3.1. Từ request đến plan đóng băng

API nhận request intent gồm câu hỏi, target entity, kỳ, metric, peer set nếu
có và tùy chọn macro. Planner kiểm tra entity/metric/period/capability với
catalog của provider, sau đó tạo plan chứa snapshot identity, expected cells,
active capabilities và applicable cross-level links. Plan được đóng băng trước
khi retrieval bắt đầu. Dữ liệu hay capability thay đổi sau bước này phải tạo
snapshot hoặc plan mới, không sửa ngầm run đang chạy.

Plan không lấy phạm vi từ những giá trị mặc định của giao diện. Frontend chỉ
truyền request và hiển thị trạng thái; server-side planner quyết định request
có khả năng thực hiện hay không. Một request ngoài coverage hoặc thiếu semantic
configuration bị chặn trước specialist retrieval để không sinh report có vẻ
hoàn chỉnh từ dữ liệu không được chấp nhận.

### 4.3.2. Các đường capability đã được kiểm chứng

| Request | Capability hoạt động | Giới hạn đã ghi nhận |
|---|---|---|
| Company một kỳ | Company | Claim số phải đi qua observation/source/locator; thiếu dữ liệu giữ missingness. |
| Company trend 2–4 kỳ | Company, với context tách theo từng kỳ | Một logical run; metric-period record không được gộp thành map chỉ theo metric. |
| Company + Peer một kỳ | Company và Sector/Peer | Provider cung cấp benchmark; requested members và eligible denominator giữ riêng. |
| Macro + Company | Chỉ khi provider khai báo capability và snapshot có Macro observations hợp lệ | Gold hiện tại không có Macro observations được chấp nhận nên request bị chặn hoặc `NOT_APPLICABLE`. |
| Peer/Macro nhiều kỳ | Không có trong public slice hiện tại | T08 bị chặn trước retrieval theo D-074. |

Company trend là một logical scope với danh sách kỳ có thứ tự, tối đa bốn kỳ.
Kỳ cuối là anchor legacy khi `periods` được cung cấp. Core Stage-1 kiểm tra đủ
ma trận `(entity, metric, period)`: mỗi ô phải là valid hoặc missing có lý do.
Không được rút ngắn danh sách kỳ vì một ô thiếu, cũng không được suy ra delta
hoặc nguyên nhân mới chỉ từ hướng tăng/giảm trong prose.

Trong Peer request, claim scope giữ toàn bộ requested peer set nhưng phép tính
chỉ dùng eligible accepted inputs. Shared unit, period basis và verified
reporting scope là điều kiện để publish median. Metadata denominator nằm trong
từng `PeerBenchmarkRecord`, vì missingness có thể khác giữa các metric.

## 4.4. Stage-1, semantic critique và bounded revision

### 4.4.1. Cổng Stage-1

Candidate synthesis tạo các `AtomicClaim` có scope và provenance. Stage-1 chạy
trước semantic critic và fail closed khi phát hiện số sai, reference không
giải được, source/locator không hợp lệ, claim ngoài plan, missingness bị biến
thành số hoặc output rỗng. Numeric claim có thể dùng structured observation
provenance thay cho snippet nếu observation, source, locator, unit, period và
lineage đều giải được; narrative/policy claim vẫn cần document evidence phù
hợp.

Stage-1 không tự làm arithmetic gate cho candidate onboarding. Arithmetic đã
được thực hiện ở operational promotion bằng formula registry và calculation
receipt; Stage-1 xác nhận report claim khớp observation được chấp nhận và
provenance của observation đó. Semantic critic cũng không được override một
hard-gate failure hoặc đổi một thiếu dữ liệu thành `ACCEPT_WITH_LIMITATIONS`.

### 4.4.2. Critique issue và sửa đổi có mục tiêu

Sau khi Stage-1 pass, semantic critic đánh giá groundedness, coverage,
reasoning, uncertainty và cross-level integration khi plan có applicable link.
Mỗi `CritiqueIssue` hợp lệ phải gắn với active specialist, claim hoặc link
được plan cho phép và một action cụ thể. `RECONCILE_CROSS_LEVEL` chỉ dùng khi
link đó thực sự được khai báo; specialist không active không được rerun.

Một vòng revision có thứ tự cố định:

```text
CritiqueIssue + required action
  → validate against frozen plan
  → rerun affected active specialist/writer
  → retain unaffected artifacts
  → re-synthesize
  → Stage-1 again
  → semantic decision or next bounded round
```

Writer nhận issue/action đã chọn và chỉ được thay đổi grounded prose,
coverage hoặc limitation trong plan. Accepted numeric values, identity,
observation IDs, source IDs, locators và input lineage là bất biến. Orchestrator
synthesis là artifact riêng, có supporting claim IDs có thứ tự; thay đổi
synthesis không được gắn nhãn nhầm là specialist revision. Controller giới hạn
tối đa hai vòng. Re-fetch cùng facts hoặc đổi verdict của critic mà không có
thay đổi đáp ứng issue không phải revision thành công.

### 4.4.3. Bằng chứng implementation và giới hạn

PR #54/P4A và P2 verification đã kiểm tra offline exact-question T04/T05,
Company trend, Company/Peer một kỳ, Stage-1, targeted revision, SSE và
run-history round-trip. Các fixture cho thấy targeted revision thay đổi prose
đúng mục tiêu, giữ facts/provenance không bị ảnh hưởng và chạy lại Stage-1.
Đây là bằng chứng control-flow và contract behavior trên provider/writer/critic
fixture; không phải bằng chứng live model quality, deployed readiness, teacher
walkthrough hoặc final A/B/C score. Multi-period Peer T08 vẫn ngoài runtime
được hỗ trợ ([P4A Runtime Acceptance Evidence](P4A-IMPLEMENTATION-VERIFICATION-2026-09-26.md); [P2 Runtime and Stage-1 Verification](P2-IMPLEMENTATION-VERIFICATION-2026-09-26.md)).

## 4.5. Reference application và khả năng quan sát

### 4.5.1. Luồng sản phẩm

Reference application được tổ chức theo luồng:

```text
Dataset → Create Analysis → Live Agent Workflow → Final Report → Report Library
```

Dataset view chỉ hiển thị snapshot và capability mà backend xác nhận. Create
Analysis gửi request intent, không cho người dùng ép hệ thống gọi agent không
áp dụng. Session hiển thị các hành động business-level như planning,
delegation, tool activity, review và revision. Report hiển thị numeric claims,
quality flags, limitations và source trail. UI không hiển thị chain-of-thought,
hidden scratchpad, system prompt hoặc raw private reasoning.

Synchronous API và SSE dùng cùng adaptive runtime và cùng kết quả cuối. Event
vocabulary có thể gồm `SCOPE_VALIDATED`, `TASK_ASSIGNED`, `AGENT_STARTED`,
`TOOL_COMPLETED`, `AGENT_OUTPUT_CREATED`, `REVIEW_ISSUE_CREATED`,
`REVISION_REQUESTED`, `REVISION_COMPLETED`, `SYNTHESIS_COMPLETED`,
`REPORT_READY`/`REPORT_ACCEPTED` và `RUN_BLOCKED`. `REPORT_READY` chỉ được
phát sau khi final run đã persist; persistence failure phải phát `RUN_BLOCKED`
thay vì report thành công.

### 4.5.2. Trạng thái deployment tại thời điểm bản working

Preflight read-only ngày 26/09 cho thấy frontend public và `/api/health` có
thể truy cập, nhưng `/api/ready` trả 503. `/api/capabilities` không có
`snapshotId`, `datasetId`, entities, periods hoặc metrics; `analysis_available`
là false và limitation code là `accepted_snapshot_unavailable`. Không có
analysis request được gửi và không có report live để giảng viên thử. Các GET
readiness/capabilities vẫn có thể khởi tạo run-history schema nếu schema chưa
tồn tại, nên không được coi là hoàn toàn side-effect-free.

Do đó, HTTP 200 của frontend hoặc health endpoint không đủ để khẳng định
walkthrough đã đạt. Cần provision accepted snapshot, authority scope khi
Gold được dùng, run-history store riêng và writer/critic configuration; sau đó
mới chạy readiness và workflow smoke test theo cùng snapshot. Không được gửi
run có ghi history hoặc thay đổi deployment settings để biến một trạng thái
blocked thành bằng chứng hoàn thành nếu chưa có phê duyệt và bằng chứng tương
ứng.

## 4.6. Khả năng chuyển giao và trạng thái nghiệm thu

Kiến trúc cho phép hai loại provider đưa dữ liệu vào cùng canonical contract:
Gold SQLite adapter cho benchmark và operational onboarding adapter cho case
ngoài Gold. CTG là bằng chứng đã kiểm tra cho một snapshot Q4/2024 và bốn nhóm
metric được hỗ trợ; nó không được trộn vào Gold v5 hay A/B/C. File PDF scan và
OCR chỉ là candidate route nếu chưa có manual source reconciliation. Quy tắc
này giữ được transferability mà không nới lỏng provenance.

Trạng thái các lớp tại bản working:

| Lớp | Trạng thái có bằng chứng | Điều chưa được phép suy ra |
|---|---|---|
| Contract và deterministic acceptance | Có kiểm tra OpenAPI, Stage-1, provenance, missingness và scope | Không suy ra chất lượng mô hình hoặc toàn bộ ứng dụng đã deploy. |
| Bank onboarding | CTG operational snapshot đã được source-reconcile và có calculation receipts | Không suy ra Gold promotion hay tương thích mọi ngân hàng. |
| Adaptive runtime/revision | Offline P2/P4A acceptance đã ghi nhận | Không suy ra live-provider quality hoặc A/B/C score. |
| Reference deployment | Frontend/health reachable; readiness blocked vì thiếu accepted snapshot | Không suy ra teacher walkthrough hoặc report live. |
| A/B/C experiment | Candidate controls và plans tồn tại; protocol vẫn pre-freeze | Không có kết quả final, ranking hay kết luận superiority. |

Thiết kế này bảo đảm chương mô tả đúng ranh giới giữa behavior đã kiểm chứng
và mục tiêu còn phải thực hiện. Khi snapshot, provider và protocol được freeze
thực sự, Chương 5 sẽ mô tả walkthrough/report cụ thể còn Chương 6 sẽ dùng run
manifest, phiếu chấm và failure log để trả lời các câu hỏi nghiên cứu. Cho tới
khi đó, mọi câu văn về chất lượng live, chi phí thực tế hoặc A/B/C phải giữ ở
thì dự kiến hoặc trạng thái pending.

### Tài liệu đối chiếu nội bộ

- [Architecture](ARCHITECTURE.md)
- [Data and Agent Contracts](DATA-CONTRACT.md)
- [Architectural Guardrails](ARCHITECTURAL-GUARDRAILS.md)
- [P1 Data-Portability Preflight](P1-DATA-PORTABILITY-PREFLIGHT-2026-09-26.md)
- [P2 Runtime and Stage-1 Verification](P2-IMPLEMENTATION-VERIFICATION-2026-09-26.md)
- [P4A Runtime Acceptance Evidence](P4A-IMPLEMENTATION-VERIFICATION-2026-09-26.md)
- [Thesis Masterplan](THESIS-MASTERPLAN-2026-09-24.md)

**TODO trước khi hợp nhất vào bản sáu chương:** đồng bộ thuật ngữ với Chương
3 sau khi PR #60 được quyết định; thay các câu mô tả deployment hiện tại bằng
evidence mới nếu readiness thay đổi; chỉ viết Chương 5–6 ở thì quá khứ sau khi
có report live, run manifest và bảng chấm tương ứng.
