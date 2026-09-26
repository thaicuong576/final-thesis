# Master plan hoàn thiện khóa luận hướng ứng dụng (24–29/09/2026)

**Trạng thái:** kế hoạch thực thi, rà soát sau mỗi cổng nghiệm thu.  
**Base kiểm tra:** `main` tại `3e50b95` ngày 24/09/2026.  
**Phạm vi:** ứng dụng phân tích cơ bản ngân hàng niêm yết Việt Nam; thực nghiệm trên mẫu ngân hàng được kiểm định. Chứng khoán và bao phủ toàn ngành là hướng mở rộng.

## 1. Đích nghiệm thu

Khóa luận hoàn thành khi có **ứng dụng truy cập được bằng link**, thầy có thể tự tạo một phân tích trong phạm vi dữ liệu công bố; kết quả thể hiện số liệu, bằng chứng, giới hạn và trạng thái xử lý dễ hiểu. Hệ thống phải xử lý được **dữ liệu của ít nhất một ngân hàng ngoài bộ Gold hiện tại** sau khi dữ liệu đó được chuẩn hóa và kiểm định, bằng cùng lõi phân tích, không sửa logic theo mã ngân hàng. Nghiên cứu đánh giá hệ thống và ba cấu hình A/B/C; kết quả âm tính hoặc không kết luận được vẫn là kết quả hợp lệ.

| Yêu cầu đã chốt với GVHD | Bằng chứng nghiệm thu cần tạo |
|---|---|
| Nội dung nghiên cứu tập trung nhóm ngân hàng | Tên, phạm vi, dataset, câu hỏi và kết luận nhất quán trong bản 6 chương; không gọi mẫu 5 ngân hàng là toàn ngành. |
| Ngân hàng mới với dữ liệu mới vẫn chạy | Một case ngoài ACB/TCB/VPB/MBB/VCB: nạp theo contract → validation → snapshot mới → capability catalog → yêu cầu phân tích → report có nguồn; không đổi analytical core. Ít nhất một tình huống thiếu/sai dữ liệu bị chặn có lý do. |
| Đánh giá hệ thống hướng ứng dụng | Cùng bộ câu hỏi, snapshot, model, factual access, evidence policy và output contract cho A/B/C; công bố chất lượng **và** độ trễ, số call, token/chi phí, tỷ lệ hoàn thành. |
| Người làm khóa luận có thể tự đánh giá | Chấm theo rubric cố định, ẩn tên cấu hình khi chấm, lưu phiếu và giải thích hạn chế của một người chấm. |
| Thầy phải dùng được app qua link; UI được chấm | Kiểm thử từ trang dữ liệu → tạo phân tích → session → report → mở bằng chứng trên URL triển khai, bằng desktop và màn hình hẹp. Có kịch bản demo và hướng dẫn giới hạn đầu vào. |

### Hợp đồng đầu vào cho ngân hàng mới

MVP chấp nhận một **gói dữ liệu chuẩn hóa** gồm định danh ngân hàng, kỳ, metric, giá trị hoặc trạng thái thiếu, đơn vị, period basis, phạm vi hợp nhất/riêng lẻ, source ID, locator, tài liệu gốc/hash và quy tắc đối soát. Không coi `missing` là 0. File PDF scan có thể đi qua LlamaParse để tạo **candidate text/table/evidence theo trang**; số liệu OCR không tự động được nhận là Gold. Nếu chưa có API key hoặc thử nghiệm không đạt, gói CSV + bằng chứng kiểm tra thủ công vẫn là đường nhập liệu hợp lệ. Không hứa rằng bất kỳ PDF scan nào cũng lập tức tạo báo cáo đúng.

**OCR feasibility check (25/09):** [trang giá chính thức](https://www.llamaindex.ai/pricing) xác nhận Free có 10.000 credits/tháng và tối đa 5 parse jobs đồng thời; [quickstart hiện hành](https://developers.llamaindex.ai/llamaparse/) dùng `llama-cloud`/`LlamaCloud` với API key. Có thể chia PDF thành năm job 20 trang và ghép theo số trang gốc, nhưng giới hạn 5 job **không chứng minh** tốc độ tăng 5 lần; cần đo trên cùng tài liệu và kiểm tra các bảng/biểu đồ đi qua ranh giới phần. Chỉ thử trên vài trang scan CTG có bảng/biểu đồ, so với PDF gốc và ghi lỗi/chi phí. Các con số 20 RPM, 512 MB/file và mức tăng tốc chưa được xác nhận cho tài khoản thực tế nên không dùng làm cam kết sản phẩm.

## 2. Mốc xuất phát đã kiểm chứng và khoảng trống

- Gold v5 có 80 ô mục tiêu, 76 quan sát hợp lệ có evidence và 4 ô thiếu rõ ràng (`reports/analysis-report-v2-final-evaluation-gold-v5-20260909-v4/final-evaluation.md`).
- Artifact SQLite Gold v5 riêng đã được xác nhận ở local `data/processed/gold-bank-2025-expanded-v5-evidence.sqlite` (487.424 byte, SHA-256 `1B1B5C090D2F8EDE87A4C33EA3EE716F7A54C9DE7C51089F4D3893D7A1FFCE73`), chứa 80 observations, 116 evidence snippets và 17 sources. File này bị ignore, **không phải** `finance_master_v2.sqlite` legacy 126 MB mà app hiện mở. API/deploy cần trỏ tường minh tới artifact Gold v5 đã đóng gói hoặc mount; không dựa vào đường dẫn máy phát triển.
- Thực nghiệm cũ: 75 jobs dự kiến, 61 hoàn tất, 14 lỗi; 61 packet được chấm mù với 244 dòng tiêu chí. Đây là **pilot lịch sử** về số ngân hàng mỗi yêu cầu; chi phí và lỗi tăng ở cấu hình phức tạp. Không dùng nó như bằng chứng rằng vòng critique/revision cuối cùng đã hoạt động.
- `docs/ARCHITECTURE.md` xác nhận runtime benchmark hiện còn là scaffold: verification call chưa tạo `CritiqueIssue`, chưa chạy lại specialist bị ảnh hưởng và chưa re-synthesize.
- Bản `docs/THESIS-DRAFT-CHAPTERS-1-4-VI.md` hiện có **7 chương**, khác outline **6 chương** đã được GVHD duyệt. Chương 1–2 người viết gửi trong phiên làm việc là đầu vào biên tập; artifact thesis nguồn trong `docs/Khoá luận tốt nghiệp - Cường - GVHD_ Lê Văn.md` vẫn chỉ đọc.
- Frontend và `/api/health`, `/api/capabilities` trả HTTP 200 ngày 24/09/2026; điều này chưa kiểm chứng hành trình end-to-end hoặc chất lượng báo cáo trên môi trường triển khai.
- Luồng nhập ngân hàng mới và LlamaParse chưa được chứng minh. Không có `LLAMA_CLOUD_API_KEY` trong môi trường làm việc ngày 24/09/2026.
- Audit ngày 24/09 xác nhận core đã có Stage-1, semantic critic và bounded revision kernel (126 unit tests Phase 3B đạt), nhưng `/api/analyze` và SSE chưa chạy qua core này. API hiện có capability 27 ngân hàng/Macro, số sector/macro mặc định, reference/hash và nhãn acceptance được dựng trong service; luồng SSE còn phát sự kiện revision theo kịch bản. Đây là **blocker công bố báo cáo**, không phải bằng chứng hệ thống đã được kiểm định.
- UI public có hai mô tả dữ liệu mâu thuẫn: Data view mẫu 5 ngân hàng/4 metric và Composer từ API 27 ngân hàng/7 metric. Report có CAMEL prose/số mặc định và nhãn kiểm định vô điều kiện; request nhiều kỳ bị gửi thành kỳ đầu. Không dùng các màn này làm bằng chứng app đạt yêu cầu trước khi sửa và retest.
- CSV onboarding hiện kiểm được cấu trúc/mapping nhưng có thể gọi snapshot là `accepted` khi observation vẫn là nguồn `user_supplied`; nó chưa đủ để Stage-1 chấp nhận claim. PR contract riêng khóa ba cổng: structural candidate → đối soát primary theo từng observation → validated operational snapshot. Gold benchmark promotion vẫn là cổng khác.

Các tài liệu trạng thái cũ có thể mô tả những mốc lịch sử khác nhau. Với từng tuyên bố cuối khóa luận, dùng snapshot, manifest, run ID và kết quả kiểm tra tương ứng làm căn cứ.

## 3. Sáu ngày thực thi và cổng chuyển pha

| Ngày | Trọng tâm và việc thực hiện | Deliverable và điều kiện qua cổng |
|---|---|---|
| **24/09 — P0: khóa phạm vi, đối chiếu sự thật** | Chốt outline 6 chương, tên/đối tượng ngân hàng, câu hỏi nghiên cứu trung tính; kiểm kê data, benchmark, ứng dụng và nguồn; đóng băng kịch bản nghiệm thu ngân hàng mới; chọn ngân hàng ngoài mẫu sau kiểm tra nguồn. Ghi tiền kiểm kiến trúc. | Master plan này; ma trận yêu cầu–bằng chứng; danh sách work items có thứ tự. Chỉ sang P1 khi không còn dùng tài liệu trạng thái cũ để khẳng định hệ thống đã hoàn thành. |
| **25/09 — P1: data portability** | Hoàn thiện đúng một đường CSV → canonical candidate → validation → snapshot/provider; cùng contract dùng được qua Gold SQLite và CSV. Kiểm tra một ngân hàng ngoài mẫu ở phạm vi nhỏ, ưu tiên 2024 Q4 và bốn metric chính hoặc missing có lý do. Nếu có key, thử LlamaParse trên vài trang scan/bảng/biểu đồ; so với PDF gốc và lưu page locator. | Test dùng cùng analytical core cho hai adapter, không hard-code 5 bank; case dữ liệu lỗi/missing fail closed. PDF chỉ tạo candidate. Chương 3.2 và 4.2 viết theo hành vi đã có. |
| **26/09 — P2: phân tích thích ứng và kiểm soát cứng** | AnalysisRequest → capability check → frozen AnalysisPlan; chỉ gọi specialist cần thiết; structured claims; Stage-1 kiểm số, scope, reference, evidence và missingness. Khóa một bộ analytical tasks theo độ phức tạp, gồm company-only và peer; macro chỉ khi có dữ liệu Gold cùng kỳ. | Kiểm thử company-only không gọi Sector/Macro; request ngoài coverage bị từ chối hoặc giới hạn rõ; claim sai số/nguồn bị chặn. Chương 4.1–4.3 có sơ đồ khớp runtime. |
| **27/09 — P3: critique/revision và app** | Critic tạo issue có claim/specialist/action; targeted rerun tối đa 2 vòng, re-synthesis và chạy lại Stage-1. Nối luồng thật vào app; kiểm tra Dataset view, Create Analysis, Session, Report và lỗi/giới hạn bằng tiếng Việt. | Một ca được chấp nhận, một ca được sửa đúng mục tiêu, một ca fail acceptance được ghi rõ. UI không lộ chain-of-thought; chỉ hiển thị agent đã gọi. Chương 4.4–4.5 theo app thực tế. |
| **28/09 — P4: triển khai, kiểm thử người dùng và thực nghiệm** | Preview deploy, chạy hành trình thầy sẽ thử, sửa blocker UI/API. Chạy A/B/C trên question set đóng băng, cùng model/snapshot/tools; lưu run/failure/cost. Chấm mù thủ công; phân tích kết quả kể cả kết quả bất lợi. | URL có thể truy cập và tạo report thật; citations bấm mở được; bảng chất lượng và vận hành có mẫu số, lỗi và phiên bản rõ. Không gọi pilot cũ là thực nghiệm của revision loop mới. Viết Chương 5. |
| **29/09 — P5: khóa luận và handoff** | Rà Chương 1–2 với artifact cuối, hoàn thiện Chương 3–6, tài liệu tham khảo, phụ lục, hình/chú thích, giới hạn; kiểm tra lại URL, nguồn, số liệu, build và demo script. Dành ít nhất nửa ngày cho lỗi cuối và trình bày. | Bản khoảng 60 trang tính phụ lục, đúng outline 6 chương; link app, hướng dẫn nhập liệu và demo, repo/commit/snapshot/model/run IDs; không còn claim vượt quá dữ liệu. |

**Nhịp song song:** viết Chương 3–4 sau mỗi cổng kỹ thuật tương ứng, không đợi đến 29/09. Chương 5 chỉ viết kết luận định lượng sau khi run và chấm điểm hoàn tất. Mỗi ngày lưu quyết định, kết quả kiểm tra và giới hạn trong PR/manifest.

**Điều chỉnh sau audit P0:** sửa phát biểu và fallback giả ở API/UI là cổng an toàn chạy song song với P1; nếu chưa nối được provider và Stage-1 thì trả lỗi/giới hạn rõ, không phát hành report `completed`. Bắt đầu P3 bằng adapter production cho core revision hiện có. Không coi việc có 126 test core là bằng chứng API đã chạy critique/revision.

**Bổ sung cổng P1 theo D-071:** với chỉ số dẫn xuất của ngân hàng mới, kiểm tra quan hệ input ID là chưa đủ. Trước khi công nhận operational snapshot, code phải tính lại theo formula version từ các input primary đã được chấp nhận, so giá trị với tolerance đã khai báo và lưu calculation receipt. Stage-1 xác nhận claim khớp observation được chấp nhận và chuỗi nguồn, không thay cho phép kiểm toán học ở cổng dữ liệu.

**Tiền kiểm P4 ngày 25/09:** frontend và `/api/health` public trả 200 nhưng `/api/ready` trả 503 do database disconnected; `/api/capabilities` vẫn công bố snapshot legacy 27 ticker/Gold 2.0 và revision deploy là `3e50b95`, không phải Gold v5. P4 phải tách dataset SQLite chỉ đọc khỏi DB lưu `analysis_runs`, xác minh hash + integrity + snapshot ID lúc khởi động, fail closed nếu artifact sai/thiếu, và đổi health check sang `/api/ready`. Render free có filesystem tạm nên snapshot được rehydrate mỗi lần start; lịch sử preview có thể là DB tạm riêng và reset sau restart. Full Gold artifact chứa excerpt, local-path metadata và checker IDs; chỉ đưa vào secret file/private runtime sau khi ghi quyết định quyền tái sử dụng, không commit hoặc expose file tải xuống.

## 4. Thiết kế đánh giá tối thiểu

1. Đóng băng 8–12 analytical tasks trước khi chạy: company-only, peer, yêu cầu kết hợp nhiều cấp; macro + company chỉ là nhánh riêng nếu Gold macro đạt gate. Mỗi loại có câu dễ/khó, kỳ, metric và expected coverage.
   Với peer ROE, D-063/D-072 nay cho phép dùng đủ năm ngân hàng trong đúng Gold v5 đã khóa hash. Từng task vẫn phải nêu tập thành viên và mẫu số hợp lệ theo kỳ, giữ missingness của ACB 2024_Q1, và không suy rộng năm ngân hàng thành toàn ngành. Case CTG ngoài Gold là bằng chứng chuyển giao vận hành, không tự động là nhãn Gold của thực nghiệm A/B/C.
   Audit 25/09 đã đối chiếu PDF gốc trang 6/8, ledger xét duyệt và Gold v5: Q4 dùng lợi nhuận thuộc cổ đông ngân hàng 15.778.795 triệu VND và vốn chủ sở hữu sau NCI bình quân 138.268.004 triệu VND, cho ROE 11,411747%; dùng tổng vốn chủ sở hữu sẽ cho 10,992965%. Reviewer độc lập đã chấp nhận đúng head được rà soát; attestation canonical `FC1D17BDBBAE9877F482875E730766D049CA5151D32173857D9EDEF2F31E7BAB` được authority manifest `9BC7BDD2EAACA8BFF723B50C547A48B65A7F12B2F81B23303D2B285F1C19C33E` ràng buộc. Definition gate v5 chạy read-only cho kết quả eligible, không có blocker, 80 ô kiểm tra, 76 hợp lệ và 4 missing; D-072 vì vậy mở phạm vi so sánh năm ngân hàng trên snapshot này.
2. A single-agent, B multi-agent thích ứng, C cùng planning/specialist set với B cộng critique/revision. Giữ cùng snapshot, model version, factual tools, evidence policy, đầu ra và giới hạn ngân sách tương ứng. Ghi thứ tự chạy và mọi retry.
3. Mức khả thi ban đầu: ít nhất 8 tasks × 3 cấu hình × 2 lần lặp nếu ngân sách/provider cho phép; số mẫu cuối và mọi thiếu hụt được công bố. Không loại run lỗi khỏi mẫu số completion.
4. Chấm số/reference/evidence bằng quy tắc; chấm coverage, logic, uncertainty và usefulness bằng rubric mù. Người viết khóa luận là người chấm; nêu thiên lệch và kiểm tra lại một phần phiếu sau một khoảng nghỉ.
5. Báo cáo điểm theo cấu hình và loại task, tỷ lệ hoàn thành, độ trễ, model calls, token/cost, vòng revision; phân tích trade-off thay vì giả định C tốt nhất.

## 5. Quy tắc ưu tiên khi thời gian hoặc dịch vụ chậm

**Giữ bằng mọi giá:** ngân hàng mới qua canonical contract; plan thích ứng; Stage-1; revision thật; app tạo report qua link; A/B/C công bằng; bản 6 chương bám kết quả.  
**Giảm hoặc hoãn trước:** chứng khoán, bao phủ toàn ngành, tự động nhận số OCR vào Gold, xử lý mọi PDF scan, vector index nếu metadata retrieval đủ, Report Library chưa làm, tính năng trang trí.  
**Nếu LlamaParse không có key hoặc chất lượng thấp:** ghi thí nghiệm OCR là chưa xác nhận; dùng đường nhập CSV + bằng chứng; app thông báo file scan cần kiểm tra trước khi dùng số liệu.  
**Nếu macro Gold chưa đạt:** đánh giá core company/peer, đánh dấu macro task là không áp dụng/chưa kiểm chứng, không tạo macro số liệu giả.

## 6. Bằng chứng kết thúc

- Demo trên ngân hàng trong Gold và một ngân hàng ngoài mẫu, kèm input package, validation report, snapshot IDs và báo cáo.
- Ba ca runtime: chỉ Company; Company + Peer; có critique dẫn tới sửa có mục tiêu. Có ví dụ dữ liệu thiếu/sai bị chặn.
- Ma trận A/B/C và toàn bộ run manifests, rubric, failure log, bảng kết quả đã đối soát với Chương 5.
- URL ứng dụng, ảnh màn hình và hướng dẫn 5 phút; kiểm tra trên màn desktop và màn hẹp.
- Bản thesis sáu chương và phụ lục tái lập kết quả; mọi con số trong bài nối được tới artifact nguồn.

Mỗi cổng chỉ được đánh dấu đạt bằng bằng chứng chạy được; code, HTTP 200 hoặc tài liệu tự thân không đủ để tuyên bố hoàn thành.

## 7. Tiền kiểm kiến trúc trước P1

| Câu hỏi guardrail | Quyết định |
|---|---|
| Tăng phụ thuộc vào Gold hoặc SQLite vật lý? | Không. Gold SQLite và CSV là hai adapter vào cùng canonical contract; không đưa SQL vào analytical core. |
| Khóa cứng năm ngân hàng hiện tại? | Không. Capability catalog và snapshot quyết định phạm vi; ngân hàng mới là test bắt buộc. |
| Thay frontend hoặc database thì core còn chạy? | Có, đây là điều kiện nghiệm thu của P1–P3. |
| Logic nào thuộc core và logic nào thuộc app? | Planning, specialist contracts, acceptance, revision, provenance thuộc core; upload, parser, storage, HTTP, UI thuộc integration/application. |
| Bằng chứng và snapshot còn truy nguyên được? | Mỗi observation/claim giữ source/locator, dataset snapshot và formula inputs; PDF parse chỉ là candidate. |
| Có giúp workflow analyst không? | Có: dữ liệu hợp lệ rõ phạm vi, phân tích theo yêu cầu, report kiểm tra được và có link cho thầy. |
| Có phần nào ngoài phạm vi thesis? | OCR không kiểm định tự động, chứng khoán, bao phủ toàn ngành và vector index tổng quát được hoãn. |

Trước P2 và P4, Lead ghi lại câu trả lời tiền kiểm nếu phát sinh contract hoặc nguồn dữ liệu mới. Không dùng việc test qua để che giấu phụ thuộc vào bộ Gold hiện tại.

## 8. Rà soát Chương 1–2 (25/09, bản người viết gửi)

- **Sửa trước khi khóa thiết kế thực nghiệm:** RQ2 nêu rõ so sánh A (một tác tử) với B (đa tác tử thích ứng) trên cùng câu hỏi/snapshot/model/tools, gồm chất lượng và độ trễ, calls, token/chi phí, tỷ lệ hoàn thành. RQ3 so B với C (thêm phản biện và tối đa hai vòng sửa có mục tiêu, chạy lại Stage-1). Không dự đoán chiều kết quả.
- **Sửa phạm vi:** thống kê peer chỉ tính từ các quan sát được chấp nhận trong tập issuer/metric/kỳ đã đóng băng, công bố mẫu số. Dữ liệu ngành/vĩ mô bên ngoài chỉ được dùng khi có trong snapshot được chấp nhận và AnalysisPlan yêu cầu, trình bày riêng. Với ROE, giữ cổng định nghĩa thống nhất D-063 nêu trên.
- **Đối chiếu Chương 2:** các tiểu mục 2.1–2.3 rút ra sáu nguyên tắc, trong khi bảng 2.4 liệt kê tám. Đánh số, bổ sung lập luận còn thiếu cho kiểm tra số liệu so với đánh giá ngữ nghĩa, hoặc rút gọn bảng. Nguyên tắc chuyển giao ngân hàng mới cần cơ sở rõ hoặc chuyển thành quyết định kiến trúc ở Chương 4.
- **Khóa trích dẫn:** rà `CFA Institute, 2026` so với `2026a/2026b` theo danh mục tài liệu cuối; kiểm tra thông tin xuất bản MetaGPT, ChatDev và Liang. Chương 2 đang phân biệt đúng bằng chứng nghiên cứu AI tổng quát với hiệu quả tài chính chưa được thử nghiệm.
- **Ngân sách trang để kiểm sau khi dàn trang:** trang đầu 3; Chương 1–6 lần lượt 8, 8, 9, 11, 8, 3; tài liệu tham khảo 3; phụ lục 7 = **60 trang**. Đây là trần biên tập ban đầu, điều chỉnh theo template và bản render thực tế.

## 9. Cập nhật thực thi (26/09/2026)

- PR #54 (`b1aeda4`) đã đưa P4A lên `main`: API hỗ trợ Company-only trend 2–4 kỳ, giữ nguyên đường single-period, kiểm đủ ma trận metric-period bằng core Stage-1, và giữ period scope qua targeted revision, SSE và run history.
- Exact-question T04/T05 offline E2E dùng câu hỏi chuẩn trong P4 JSONL; mỗi case kiểm đủ tám ô, Company-only routing và lineage. T05 kiểm targeted revision đổi prose nhưng giữ facts/provenance, chạy lại Stage-1; issue major chưa sửa phải fail. SSE→run-history so khớp full claims/evidence trail và terminal state. Full suite: 657 passed, 4 skipped; P4/VPB verifiers pass; Gold v5 SHA giữ nguyên.
- Đây là bằng chứng implementation với offline provider/critic fixtures. Nó chưa chứng minh chất lượng live model, app đã triển khai sẵn sàng hoặc A/B/C đã được freeze/chấm. T04/T05 chưa đủ điều kiện đưa vào kết quả cuối; T08 peer trend vẫn bị chặn cho tới decision/runtime riêng về denominator, context và claim links.
- **P1 — data portability đã hoàn tất kiểm chứng; PR #56 sẵn sàng review, chưa merge (26/09).** Báo cáo kiểm toán hợp nhất CTG FY2024 gốc (69 trang, 5.651.992 byte, SHA-256 `36513dd8b060712b188f9eab03b1a7f9479ab21e63866dd95e45759d03ec5369`) được xác minh từ evidence root tường minh. Gói dữ liệu có 22 quan sát duy nhất (15 số liệu báo cáo, 7 số liệu dẫn xuất), tất cả được đối soát và không có giá trị missing; bảy giá trị dẫn xuất được tính lại từ input đã chấp nhận bằng formula versioned và có calculation receipt. Các locator được kiểm tra trên báo cáo gốc; không nhận số liệu đọc từ biểu đồ.
- Luồng promotion tổng quát hiện đòi hỏi receipt từ resolver tự đọc và xác minh raw bytes, gắn hash đã tính với source identity/type/tier; candidate còn phải ràng buộc document/source/hash. Test phủ hash giả, byte mismatch và document/source mismatch. Snapshot operational riêng là `snapshot-b86db41dd976731cf3cf8c457c0874f8bea95798d9c42b3e3ff953efc8a58aaa` (file SHA-256 `81be2e1f7be707f3b1df3f45f780fdf0dbc0ee11ac925f23bf0e332ded2429ea`); Gold v5 giữ nguyên SHA-256 `1b1b5c090d2f8ede87a4c33ea3ee716f7a54c9de7c51089f4d3893d7a1ffce73` và integrity `ok`. Kết quả chứng minh chuyển giao cho đúng snapshot CTG Q4/2024 và các metric đã hỗ trợ, không chứng minh đại diện toàn ngành hoặc chấp nhận được mọi ngân hàng/PDF.
- Kiểm chứng P1 đạt: 53 test onboarding/provider tập trung; toàn bộ unittest discovery 663 passed, 4 skipped; OpenAPI, architecture guardrails, compileall, explicit-root P4 verifier và `git diff --check` đạt. Auditor độc lập và CI đã xác nhận GREEN trên PR head `67622fd`. `LLAMA_CLOUD_API_KEY` không có sẵn nên không chạy LlamaParse/OCR; PDF scan, bảng/biểu đồ qua OCR vẫn là candidate cần đối soát thủ công trước khi promotion.
- **Cổng kế tiếp: P2 sau khi PR #56 được merge vào `main`.** PR đã ready for review, mergeable và chờ quyền merge riêng. P2 cần xác minh frozen AnalysisPlan, routing Company-only không gọi Sector/Macro, peer chỉ khi capability hỗ trợ, và Stage-1 chặn số liệu/scope/reference/evidence sai; không dùng test offline để tuyên bố chất lượng live.
