# CHECKLIST WALKTHROUGH ỨNG DỤNG CHO GIẢNG VIÊN

**Ngày soạn:** 27/09/2026  
**Mục đích:** kịch bản kiểm tra reference application theo đúng phạm vi dữ
liệu, provenance và trạng thái runtime đã được phê duyệt.  
**Trạng thái hiện tại:** `BLOCKED` — preflight ngày 26/09 ghi nhận frontend và
`/api/health` truy cập được nhưng `/api/ready` trả `503`, chưa có accepted
snapshot trong capabilities và chưa có report live. Checklist này là artifact
chuẩn bị nghiệm thu; bản thân nó không phải bằng chứng walkthrough đã chạy.

## 1. Điều kiện được phép bắt đầu walkthrough

Chỉ đánh dấu walkthrough `READY_TO_RUN` khi tất cả điều kiện sau có evidence
đi kèm:

| Điều kiện | Evidence bắt buộc | Trạng thái bản working |
|---|---|---|
| Deployment revision xác định được | URL, revision/commit và thời điểm kiểm tra | Chưa đóng cho workflow phân tích |
| Accepted snapshot được provision tường minh | `snapshot_id`, `dataset_id`, hash SQLite hoặc artifact tương đương, integrity result | **BLOCKED**: capabilities trả `snapshotId=null`, `datasetId=null` |
| Capability catalog có phạm vi hữu hiệu | entities, periods, metrics, validation level và limitation codes | **BLOCKED**: không có entities/periods/metrics |
| Readiness đạt | `/api/ready` response và timestamp | **BLOCKED**: HTTP 503 |
| Run history tách khỏi analytical data | `SQLITE_DB_PATH`, `ANALYSIS_RUNS_DB_PATH`, alias check và schema result | Chưa xác minh trong deployment hiện hành |
| Writer/critic configuration đủ | chỉ ghi nhận presence/status, không ghi secret | Chưa xác minh trong deployment hiện hành |
| Không dùng fixture/mock làm live evidence | snapshot/run metadata và report provenance | Chưa có report live |

Không được gửi `POST /api/analyze` hoặc `/api/analyze/stream` khi readiness
chưa đạt. Lần preflight trước đây chỉ dùng các GET cần thiết, không tạo
analysis run; tuy nhiên `/api/ready` và `/api/capabilities` có thể khởi tạo
schema run-history nếu schema chưa tồn tại, nên các GET này không được coi là
hoàn toàn side-effect-free.

## 2. Evidence header cho mỗi lần kiểm tra

Người kiểm tra tạo một record không chứa secret với các trường:

```text
walkthrough_id
checked_at
deployment_url
frontend_url
frontend_revision_or_deployment_id
backend_revision
snapshot_id
dataset_id
snapshot_hash_or_authority_ref
run_store_identity
browser_and_viewport
question_set_or_demo_case_id
result: PASS | BLOCKED | FAIL
limitation_codes
evidence_paths_or_urls
```

Một ảnh chụp giao diện chỉ là bằng chứng hiển thị. Nó không thay thế
`snapshot_id`, claim/source lineage, response body hoặc run-history record.

## 3. Kịch bản thao tác chính

### 3.1. Dataset và phạm vi được công bố

1. Mở URL reference application bằng trình duyệt sạch và ghi deployment
   revision.
2. Mở Dataset/Data view.
3. Xác nhận ứng dụng hiển thị snapshot accepted, dataset identity, validation
   level, entity list, period list và metric list do backend cung cấp.
4. Xác nhận phạm vi năm ngân hàng case study không được gọi là toàn ngành.
5. Xác nhận ô thiếu, metric chưa hỗ trợ và Macro chưa có dữ liệu được hiển thị
   là limitation/missing, không bị thay thành zero hoặc số mẫu.

**PASS condition:** mọi giá trị phạm vi trên UI khớp capability response và
snapshot authority. Nếu view hiển thị `0` entity/period/metric hoặc
`accepted_snapshot_unavailable`, kết quả là `BLOCKED`, không phải PASS.

### 3.2. Company-only analysis

1. Chọn một task Company-only đã được freeze trong evaluation protocol, một
   target và một kỳ nằm trong capability catalog.
2. Gửi request từ Create Analysis.
3. Trong Session, xác nhận plan được freeze trước retrieval và chỉ Company
   được gọi. UI chỉ hiển thị các trạng thái business-level như planning,
   tool activity, output, review; không hiển thị chain-of-thought.
4. Chờ terminal state.
5. Mở report và kiểm tra mỗi numeric claim có observation ID, source ID,
   metric-specific locator, unit, period, snapshot identity và quality state.
6. Mở evidence/source trail từ claim; không chấp nhận snippet chỉ trùng source,
   ticker, period hoặc page nhưng không có association với đúng observation.

**PASS condition:** report accepted chỉ xuất hiện sau Stage-1 và terminal
persistence; run history nối đúng request, snapshot, claim IDs và evidence
trail. Không được có Sector/Macro artifact nếu plan không khai báo chúng.

### 3.3. Company + Peer analysis một kỳ

1. Chọn task Peer một kỳ có requested member set rõ ràng.
2. Kiểm tra Session cho thấy Company và Sector/Peer là active capabilities.
3. Trong report, kiểm tra `requested_peer_entity_ids` khác biệt rõ với
   `eligible_peer_entity_ids` khi có missing member.
4. Với từng metric, kiểm tra denominator, input observation IDs, aggregation
   version, unit, period basis, reporting scope và missing-member reason.
5. Xác nhận report chỉ nói về bounded peer sample, không suy rộng thành toàn
   ngành.

**PASS condition:** median/benchmark được provider cung cấp và lineage nối tới
đúng eligible inputs; API/UI không tự tính lại từ prose hoặc dùng cùng một
metadata dictionary cho các metric có denominator khác nhau.

### 3.4. Targeted revision và SSE/history

1. Chọn một case đã đăng ký có semantic critic issue cụ thể.
2. Kiểm tra event sequence: synthesis → Stage-1 → review issue → revision
   request → affected specialist/writer → re-synthesis → Stage-1 lần nữa →
   final decision.
3. Xác nhận issue/action đến đúng active writer; writer thay đổi phần prose
   hoặc limitation được yêu cầu, không sửa numeric value/provenance.
4. Xác nhận unaffected claims giữ nguyên identity và lineage.
5. Với SSE, xác nhận `REPORT_READY` chỉ xuất hiện sau khi final run đã persist;
   nếu persistence fail, terminal event là `RUN_BLOCKED` và không có report
   thành công.

**PASS condition:** revision là thay đổi đáp ứng issue có thể quan sát được,
không phải chỉ gọi lại facts hoặc đổi verdict của critic. Controller không vượt
quá hai vòng.

## 4. Kịch bản chặn và giới hạn

Các case dưới đây phải được kiểm tra sau khi happy path đạt, hoặc được giữ trong
test evidence nếu deployment chưa sẵn sàng:

| Case | Hành vi đúng | Không được coi là |
|---|---|---|
| Accepted snapshot thiếu | readiness/capability block trước retrieval, có limitation code | một service “ready” chỉ vì health 200 |
| Metric hoặc kỳ ngoài snapshot | fail closed hoặc missing có lý do | vendor fallback không khai báo |
| Macro khi Gold không có Macro observations | `NOT_APPLICABLE`/blocked trước specialist work | số Macro được bịa hoặc mượn fallback |
| Peer nhiều kỳ/T08 | block trước retrieval theo D-074 | ghép nhiều report một kỳ thành trend |
| Numeric claim thiếu locator/source | Stage-1 reject | snippet cùng tài liệu được gắn đại vào claim |
| `missing` observation | giữ null và reason | thay bằng 0 hoặc median |
| Revision nhắm specialist không active | reject issue routing | gọi thêm agent cho đủ workflow |
| Writer đưa số mới vào prose | reject/review fail | coi numeric-literal guard là semantic proof |
| Report Library sample/mock | gắn nhãn demo rõ ràng | trình bày như kết quả API live |

## 5. Responsive UI và khả năng sử dụng

Thực hiện lại các bước 3.1–3.4 ở ít nhất hai viewport đã ghi trong evidence
header:

- desktop: kiểm tra navigation, bảng số liệu, event timeline, report sections
  và nút mở source;
- màn hình hẹp: kiểm tra không mất target/period/status, bảng có cách đọc
  được, source trail không bị che, lỗi và limitation vẫn nhìn thấy;
- kiểm tra keyboard focus, disabled state và thông báo lỗi; màu sắc không được
  là tín hiệu duy nhất của trạng thái;
- kiểm tra copy tiếng Việt hướng tới chuyên viên phân tích, không lộ internal
  prompt, scratchpad hoặc định danh kỹ thuật ở mức không cần thiết.

UI pass không có nghĩa dữ liệu pass. Mỗi screenshot phải được nối với response,
snapshot và terminal run record tương ứng.

## 6. Tiêu chí kết luận

Walkthrough chỉ được kết luận `PASS` khi:

1. readiness, accepted snapshot và separate run store đều được xác minh;
2. Dataset → Create Analysis → Session → Report chạy được trên một task
   Company-only và một task Company + Peer;
3. ít nhất một targeted revision thay đổi đúng mục tiêu và qua lại Stage-1;
4. report có claim-to-observation/source/locator lineage và source navigation;
5. một case blocked/missing được chặn đúng và hiển thị lý do;
6. SSE/history round-trip và terminal event ordering được xác minh;
7. desktop và màn hình hẹp đều đạt checklist UI;
8. evidence header, response, screenshots, run IDs và known limitations được
   lưu cùng revision/snapshot.

Nếu bất kỳ điều kiện nào chưa có evidence, trạng thái phải là `BLOCKED` hoặc
`INCOMPLETE`, không phải “đã nghiệm thu”. Tại ngày 27/09/2026, checklist này
được giữ `BLOCKED` vì preflight mới nhất chưa có accepted snapshot và readiness
503. Việc chuyển sang `PASS` cần một external-state change được cấp phép và
một lần kiểm tra workflow có ghi evidence; không được suy ra từ các fixture
offline hay từ HTTP 200 của health endpoint.

### Tài liệu đối chiếu

- [Masterplan khóa luận](THESIS-MASTERPLAN-2026-09-24.md)
- [Architecture](ARCHITECTURE.md)
- [Data and Agent Contracts](DATA-CONTRACT.md)
- [P2 Runtime and Stage-1 Verification](P2-IMPLEMENTATION-VERIFICATION-2026-09-26.md)
- [P4A Runtime Acceptance Evidence](P4A-IMPLEMENTATION-VERIFICATION-2026-09-26.md)
- [Deployment staging guide](DEPLOYMENT-STAGING.md)
