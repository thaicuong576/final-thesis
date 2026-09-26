# CHƯƠNG 3. PHƯƠNG PHÁP NGHIÊN CỨU

> **Bản working ngày 26/09/2026.** Chương này mô tả thiết kế nghiên cứu và quy trình dự kiến để tạo, kiểm chứng và đánh giá artifact. Bộ câu hỏi và rubric A/B/C hiện vẫn ở trạng thái dự thảo trước khi đóng băng; chưa có kết quả chấm A/B/C trong các hồ sơ được tham chiếu ở đây. Những nội dung cần quyết định bằng bằng chứng hoặc cấu hình chạy được đánh dấu **[TODO]**. Liên kết đến tài liệu nội bộ dùng để truy nguyên trong bản làm việc, không thay thế danh mục tài liệu tham khảo của bản nộp.

Nghiên cứu xem xét một hệ thống hỗ trợ phân tích cơ bản các ngân hàng niêm yết Việt Nam, trong đó kết quả cần nối được từ yêu cầu phân tích đến quan sát dữ liệu, nguồn và báo cáo. Phương pháp được tổ chức theo hướng nghiên cứu ứng dụng và thiết kế artifact: xác định vấn đề thực tiễn, chuyển vấn đề thành yêu cầu thiết kế, xây dựng artifact, kiểm chứng artifact, thiết kế thực nghiệm so sánh và đánh giá kết quả. Phần này tập trung vào cách tiến hành và điều kiện để diễn giải kết quả; mô tả cấu trúc triển khai cụ thể thuộc Chương 4.

## 3.1. Cách tiếp cận nghiên cứu

Khóa luận kết hợp định hướng Design Science Research (DSR) với nghiên cứu tình huống trong lĩnh vực ngân hàng. DSR được dùng như khung tổ chức công việc hướng đến một artifact có thể sử dụng và kiểm chứng; trọng tâm của chương không phải là khảo cứu riêng về DSR mà là nêu rõ artifact được hình thành và đánh giá như thế nào. Nghiên cứu tình huống giới hạn bối cảnh thực nghiệm ở một nhóm ngân hàng và các kỳ dữ liệu xác định, vì vậy kết luận chỉ áp dụng trong phạm vi các điều kiện đã khảo sát.

Quy trình phương pháp gồm sáu bước có liên hệ với nhau:

1. **Xác định vấn đề thực tiễn:** việc tổng hợp báo cáo tài chính và thông tin liên quan cần kiểm soát độ đúng của số liệu, phạm vi phân tích, tính hợp lệ của nguồn và cách thể hiện dữ liệu thiếu; kiến trúc nhiều thành phần cũng có thể làm phát sinh chi phí điều phối.
2. **Chuyển vấn đề thành yêu cầu thiết kế:** yêu cầu về dữ liệu chuẩn hóa, truy nguyên từ nhận định đến nguồn, lựa chọn năng lực theo câu hỏi, kiểm tra xác định luận và phản biện có giới hạn được ghi thành các hợp đồng đầu vào, đầu ra và điều kiện chấp nhận.
3. **Xây dựng artifact:** artifact nghiên cứu gồm quy trình dữ liệu, định nghĩa các cấu hình thực nghiệm A/B/C và ứng dụng tham chiếu. A/B/C là các nhánh cần được kiểm chứng trong thực nghiệm; việc định nghĩa chúng không có nghĩa cả ba đã được triển khai và xác nhận trong runtime hiện tại. Chương 4 mô tả hành vi đã có bằng chứng; tại thời điểm bản thảo này, ứng dụng công khai vẫn chưa qua cổng readiness (`/api/ready` trả 503 và chưa có accepted snapshot theo preflight ngày 26/09/2026).
4. **Verification — kiểm chứng:** dùng kiểm tra thành phần, hợp đồng, trường hợp biên, chặn lỗi và luồng tích hợp để xác định artifact có thực hiện đúng các điều kiện thiết kế hay không.
5. **Experiment — thực nghiệm:** chạy các cấu hình trên cùng các câu hỏi đủ điều kiện, cùng snapshot và cùng chính sách đầu vào đã đóng băng.
6. **Evaluation — đánh giá:** đối chiếu tính đúng, bằng chứng và độ bao phủ bằng quy tắc; đánh giá các thuộc tính nội dung bằng rubric mù; đồng thời báo cáo tỷ lệ hoàn thành và chi phí vận hành.

Verification và evaluation trả lời hai câu hỏi khác nhau. Verification xem xét hệ thống có tuân thủ hợp đồng, phạm vi và các cổng chấp nhận hay không. Evaluation xem xét chất lượng báo cáo và chi phí khi các cấu hình xử lý cùng một nhiệm vụ. Một kiểm tra kỹ thuật thành công không phải bằng chứng rằng cấu hình đa tác tử tốt hơn cấu hình một tác tử.

Thiết kế này gắn với ba câu hỏi nghiên cứu đã nêu ở Chương 1. RQ1 được trả lời qua việc mô tả cách yêu cầu, dữ liệu, nguồn, năng lực phân tích và đầu ra được liên kết trong artifact. RQ2 so sánh cấu hình B với A về chất lượng báo cáo và chi phí trong điều kiện đầu vào tương ứng. RQ3 so sánh C với B để xem việc bổ sung phản biện ngữ nghĩa và sửa đổi có mục tiêu làm thay đổi các kết quả đó ra sao. Các câu hỏi không giả định trước cấu hình nào sẽ vượt trội.

## 3.2. Dữ liệu nghiên cứu và quy trình chấp nhận

### 3.2.1. Phạm vi dữ liệu

Trường hợp nghiên cứu là phân tích cơ bản nhóm ngân hàng niêm yết tại Việt Nam. Phạm vi dữ liệu chuẩn dùng cho đánh giá gồm ACB, TCB, VPB, MBB và VCB trong các quý năm 2024, với bốn chỉ tiêu chính: tỷ lệ nợ xấu, tỷ lệ bao phủ nợ xấu, tỷ suất sinh lời trên tổng tài sản (ROA) và tỷ suất sinh lời trên vốn chủ sở hữu (ROE). Đây là mẫu trường hợp giới hạn, không phải mẫu đại diện thống kê cho toàn ngành. Dữ liệu vĩ mô chỉ có thể được sử dụng nếu snapshot được chấp nhận công bố rõ năng lực và chứa quan sát phù hợp với kỳ của câu hỏi; Gold v5 hiện không có dữ liệu vĩ mô được chấp nhận.

Đơn vị dữ liệu phân tích là tổ hợp ngân hàng, chỉ tiêu và kỳ báo cáo. Mỗi giá trị cần giữ đơn vị, cơ sở kỳ, phạm vi báo cáo, trạng thái chấp nhận và liên kết nguồn phù hợp. Khi câu hỏi yêu cầu so sánh nhóm, tập thành viên được yêu cầu phải được nêu rõ; mẫu số thống kê chỉ gồm các quan sát hợp lệ đã được chấp nhận. Thành viên bị loại khỏi một phép tính phải có lý do cụ thể. Bốn ô thiếu trong ACB quý I năm 2024 tiếp tục được biểu diễn là thiếu, không đổi thành số không hoặc giá trị ước tính.

### 3.2.2. Các trạng thái dữ liệu

Nghiên cứu phân biệt bốn trạng thái để không nhầm dữ liệu đã thu thập với dữ liệu đủ điều kiện cho báo cáo hoặc benchmark:

| Trạng thái | Ý nghĩa và điều kiện sử dụng |
|---|---|
| Nguồn thô | Báo cáo gốc, PDF, CSV hoặc tệp bằng chứng được lưu bất biến; giữ định danh nguồn và dấu kiểm tra byte khi áp dụng. Việc có tệp không có nghĩa các số liệu trong tệp đã được xác nhận. |
| Candidate đã parse và map | Nội dung được trích xuất hoặc ánh xạ vào cấu trúc dữ liệu chuẩn. Candidate hỗ trợ rà soát, nhưng chưa được dùng như quan sát đã chấp nhận. OCR cũng chỉ tạo candidate. |
| Snapshot vận hành đã đối soát | Các quan sát được rà soát với nguồn chính, đúng chỉ tiêu, kỳ, đơn vị, cơ sở kỳ và phạm vi báo cáo; mỗi quan sát có locator cụ thể. Với metric dẫn xuất, hệ thống tính lại từ input đã được chấp nhận bằng công thức phiên bản hóa, kiểm tra tolerance và lưu calculation receipt. Snapshot này phục vụ đường vận hành đã kiểm định, nhưng tự nó chưa trở thành Gold benchmark. |
| Gold benchmark | Tập quan sát và nhãn đã qua quy trình rà soát, promotion và thẩm quyền phạm vi riêng. Chỉ dữ liệu thuộc snapshot Gold đã xác định mới được tính vào mẫu đánh giá benchmark. |

Quy trình acceptance vì vậy đi từ tài liệu hoặc tệp thô đến candidate, tiếp theo là đối soát từng quan sát cho snapshot vận hành, rồi mới xét cổng Gold riêng nếu mục tiêu là benchmark. Cấu trúc CSV hợp lệ chỉ chứng minh tệp có thể đọc và ánh xạ; nó không xác nhận con số đúng. Với số liệu dẫn xuất, việc khai báo input IDs không thay thế việc tính lại bằng công thức được công nhận. Các trạng thái `parsed`, `candidate`, `accepted` và `Gold` không được dùng thay thế lẫn nhau.

### 3.2.3. Snapshot Gold v5 và ca onboarding CTG

Benchmark ngân hàng được khóa theo snapshot `gold-bank-2025-expanded-v5-evidence`, tại tệp local `data/processed/gold-bank-2025-expanded-v5-evidence.sqlite`, có SHA-256 byte thô `1b1b5c090d2f8ede87a4c33ea3ee716f7a54c9de7c51089f4d3893d7a1ffce73`. Snapshot có 80 ô mục tiêu: 76 quan sát hợp lệ và 4 ô thiếu, đều thuộc ACB trong quý I năm 2024. Tệp SQLite và báo cáo đối soát cũ được master plan dẫn tại `reports/analysis-report-v2-final-evaluation-gold-v5-20260909-v4/final-evaluation.md` là artifact local bị Git bỏ qua; việc xác minh lại cần evidence root tường minh. Các hồ sơ có thể truy cập trong checkout gồm authority sidecar [`gold-v5-reporting-scope-authority-v1.json`](../data/evaluation/gold-v5-reporting-scope-authority-v1.json) và [authority manifest cho rà soát VPB ROE](../reports/data-foundation/vpb-roe-parent-equity-authority-manifest-20260925.json). Không suy ra phạm vi hợp nhất hay riêng lẻ nếu metadata của quan sát không nêu rõ. Thông tin task và coverage được lưu trong [`p4-task-specs-v1.json`](../data/evaluation/p4-task-specs-v1.json), [`p4-expected-coverage-v1.json`](../data/evaluation/p4-expected-coverage-v1.json) và các hồ sơ Gold được dẫn tại [Research Register](RESEARCH.md).

CTG FY2024 Q4 là ca kiểm tra khả năng chuyển giao ngoài Gold, được lưu trong snapshot vận hành riêng `snapshot-b86db41dd976731cf3cf8c457c0874f8bea95798d9c42b3e3ff953efc8a58aaa`. Gói này có 22 quan sát đã đối soát, gồm 15 quan sát trực tiếp và 7 quan sát dẫn xuất; các giá trị dẫn xuất được tính lại bằng công thức phiên bản hóa và có biên nhận tính toán. Ca CTG cho phép kiểm tra đường onboarding với snapshot và các metric được hỗ trợ trong gói đó. CTG không phải thành viên Gold v5, không được gộp vào mẫu A/B/C và không tự chứng minh hệ thống có thể tiếp nhận mọi ngân hàng hoặc mọi dạng tài liệu. Chi tiết gói được lưu tại [`ctg-2024-audited-2024q4-v1.json`](../data/onboarding/ctg-2024-audited-2024q4-v1.json).

Báo cáo CTG gốc là PDF không có lớp văn bản chọn được. Kết quả OCR, nếu có, chỉ là gợi ý để tạo candidate và phải được so khớp thủ công với tài liệu gốc, số trang và vị trí nguồn trước khi xem xét chấp nhận. Hồ sơ hiện có không công nhận số đọc từ OCR là bằng chứng đã chấp nhận; các số được dùng trong gói CTG dựa trên quá trình đối soát. **[TODO: nếu luận văn mô tả một thử nghiệm OCR cụ thể, bổ sung bộ trang, công cụ/phiên bản, tiêu chí đối chiếu và nhật ký lỗi/chi phí; nếu không có phép thử được lưu, chỉ giữ giới hạn này.]**

## 3.3. Verification của artifact

Verification được tổ chức thành các lớp bằng chứng có thể kiểm tra lại. Kiểm tra thành phần xác nhận các phép biến đổi hoặc quy tắc đơn lẻ; kiểm tra hợp đồng xác nhận cấu trúc, định danh và miền giá trị ở ranh giới dữ liệu; kiểm tra trường hợp biên xác nhận hệ thống chặn dữ liệu thiếu, ngoài phạm vi hoặc sai provenance; kiểm tra tích hợp xác nhận luồng từ yêu cầu đến đầu ra tuân thủ cùng kế hoạch và snapshot. Với claim số, điều kiện chấp nhận bao gồm observation đã được chấp nhận, nguồn được chấp nhận, locator dành riêng cho metric và bằng chứng có thể phân giải. Claim dẫn xuất cần truy được các input đã chấp nhận và kết quả tính toán tương ứng.

Stage-1 là cổng xác định luận, dùng quy tắc để kiểm tra những thuộc tính có thể xác định trực tiếp: claim có thuộc entity, metric và kỳ đã yêu cầu không; số có khớp observation; nguồn và locator có hợp lệ không; claim có vượt quá reporting scope hoặc dùng sai trạng thái thiếu không; các ô kỳ vọng có được chấp nhận hoặc nêu rõ là thiếu hay không. Stage-1 không thay thế quá trình rà soát nguồn ban đầu, cũng không đánh giá toàn bộ chất lượng lập luận bằng một điểm số duy nhất.

Sau cổng xác định luận, bước phản biện ngữ nghĩa có thể đánh giá vấn đề về hỗ trợ của bằng chứng, độ bao phủ, tính mạch lạc, bất định hoặc mức độ phù hợp với câu hỏi. Nếu có lỗi có thể sửa, issue phải chỉ rõ claim bị ảnh hưởng, specialist liên quan và hành động cần thực hiện. Cấu hình có phản biện chỉ chạy lại specialist đang hoạt động và bị ảnh hưởng, tổng hợp lại kết quả, rồi thực hiện Stage-1 lần nữa; giới hạn tối đa là hai vòng sửa đổi có mục tiêu. Ghi nhận việc đánh giá lại hoặc thay verdict mà không có thay đổi đáp ứng issue không được tính là một lần sửa thành công.

Các phép kiểm thử với provider, critic hoặc writer giả lập/offline chỉ cho biết đường mã thực thi theo fixture đã thiết kế; chúng không chứng minh chất lượng mô hình trực tiếp, mức sẵn sàng của provider, khả năng sử dụng của bản triển khai hay hiệu quả A/B/C. Hồ sơ P4A hiện phân loại các phép thử T04/T05 là kiểm chứng triển khai offline và giữ chúng ngoài kết quả chấm cuối cho đến khi qua cổng sẵn sàng và đóng băng thực nghiệm. T08, yêu cầu so sánh Peer qua nhiều kỳ, vẫn ngoài phạm vi runtime được hỗ trợ. Các phân biệt này phải được giữ nguyên khi chuyển bằng chứng sang Chương 4 và Chương 5.

Mỗi kết quả verification dùng trong báo cáo cần có liên kết tới phiên bản artifact, cấu hình, đầu vào, log hoặc manifest và giới hạn của phép kiểm. Chỉ ghi trạng thái pass/fail mà không nêu đối tượng được kiểm chứng sẽ không đủ để suy rộng từ một kiểm tra hẹp sang độ tin cậy tổng thể. **[TODO: trước khi nộp, lập bảng liên kết yêu cầu thiết kế – phép kiểm – artifact kết quả – giới hạn; không thay bảng này bằng tổng số test.]**

## 3.4. Thiết kế thực nghiệm A/B/C

### 3.4.1. Các cấu hình đối chiếu

Thực nghiệm được thiết kế để tách ảnh hưởng của việc phân công tác vụ khỏi ảnh hưởng của phản biện và sửa đổi:

| Cấu hình | Quy trình xử lý trong thực nghiệm |
|---|---|
| A — một tác tử | Một tác tử tạo báo cáo từ cùng dữ kiện đã chấp nhận, quyền truy cập dữ kiện, công cụ xác định, chính sách bằng chứng và hợp đồng đầu ra áp dụng cho câu hỏi. |
| B — đa tác tử phân cấp thích ứng | Bộ điều phối lập kế hoạch từ yêu cầu và chỉ gọi các năng lực cần cho câu hỏi. Các specialist xử lý phần việc tương ứng; đầu ra được tổng hợp và qua Stage-1. Cấu hình này không có vòng semantic critique/revision. |
| C — đa tác tử có phản biện và sửa đổi | Dùng cùng kế hoạch và tập specialist như B trước điểm phản biện. Sau tổng hợp và Stage-1, critic tạo issue có mục tiêu; specialist bị ảnh hưởng được yêu cầu sửa, hệ thống tổng hợp lại và chạy Stage-1 cho candidate mới. Tối đa hai vòng sửa đổi. |

A/B/C là các cấu hình cần so sánh, không phải giả định về thứ hạng chất lượng. Với mỗi tác vụ, cần giữ nhất quán câu hỏi, snapshot, tập quan sát đã chấp nhận, phiên bản nền của model, quyền truy cập dữ kiện/công cụ, chính sách bằng chứng và hợp đồng đầu ra. Bộ prompt riêng của từng cấu hình có thể khác nhau theo vai trò; chúng phải được đóng băng và ghi lại trước khi chạy, không tinh chỉnh dựa trên điểm số đã quan sát. Vì vậy, kết quả so sánh phản ánh toàn bộ cấu hình A/B/C đã đăng ký, gồm cả prompt theo vai trò. Hạn mức tài nguyên tối đa cần đủ tương đương để phép so sánh có ý nghĩa, nhưng không ép số lần gọi thực tế bằng nhau vì số call, token, thời gian, chi phí và số vòng sửa là các biến kết quả cần đo.

### 3.4.2. Tác vụ và khả năng áp dụng

Bộ [`p4-questions-v1.jsonl`](../data/evaluation/p4-questions-v1.jsonl) và [`p4-task-specs-v1.json`](../data/evaluation/p4-task-specs-v1.json) là bộ câu hỏi ứng viên, có hash chuẩn hóa LF UTF-8 `c4747af992441cc6063fa9dc08b1a09fc1a4a923a5415a2de4391c03e17fbc09`. Các câu hỏi phân thành: phân tích Company tại một kỳ; trường hợp Company có dữ liệu thiếu; xu hướng Company qua các kỳ; so sánh Peer tại một kỳ; yêu cầu Peer qua nhiều kỳ; và hai kiểm soát từ chối cho kỳ ngoài snapshot hoặc thành viên ngoài tập Gold. Bộ ứng viên gồm mười mã T01–T10, trong đó T09–T10 là kiểm soát phạm vi chứ không phải câu hỏi phân tích chính.

| Mã | Tác vụ ứng viên | Trạng thái theo hồ sơ hiện tại |
|---|---|---|
| T01–T02 | Phân tích MBB hoặc VCB tại 2024 Q4 theo bốn metric chính. | Chờ kiểm chứng end-to-end trên cùng snapshot; chưa đủ điều kiện chấm. |
| T03 | Mô tả điều có thể và không thể kết luận cho bốn ô thiếu của ACB tại 2024 Q1. | Chờ kiểm chứng fail-closed cho trường hợp thiếu; chưa đủ điều kiện chấm. |
| T04–T05 | Phân tích xu hướng TCB (NPL, coverage) hoặc MBB (ROA, ROE) qua 2024 Q1–Q4. | Có kiểm chứng Company trend offline theo đúng câu hỏi; vẫn chưa đủ điều kiện chấm live. |
| T06–T07 | So sánh năm ngân hàng trong Gold tại 2024 Q4 lần lượt theo NPL/coverage hoặc ROA/ROE. | Chờ kiểm chứng Peer end-to-end; chưa đủ điều kiện chấm. |
| T08 | So sánh Peer năm ngân hàng qua bốn quý theo chất lượng tài sản và khả năng sinh lời. | Không đủ điều kiện vì runtime Peer nhiều kỳ chưa hỗ trợ. |
| T09 | Yêu cầu dữ liệu ACB tại 2025 Q1, ngoài kỳ của snapshot. | Kiểm soát từ chối; phép kiểm này chưa được ghi nhận là đã chạy. |
| T10 | Thêm CTG vào tập Peer Gold tại 2024 Q4. | Kiểm soát từ chối; phép kiểm này chưa được ghi nhận là đã chạy. |

Bộ câu hỏi này chưa phải protocol đã đóng băng: hồ sơ task-spec đặt tất cả task ở trạng thái chưa đủ điều kiện chấm và ghi nhận chưa tạo run A/B/C. Riêng T04/T05 hiện đã có phép kiểm exact-question offline theo hợp đồng xu hướng Company, nhưng hồ sơ triển khai không nâng chúng thành kết quả live hay kết quả chấm; chúng vẫn cần qua cổng sẵn sàng provider và đóng băng. T08 là Peer đa kỳ, chưa được hỗ trợ. Các yêu cầu Company/Sector/Peer khác cũng chỉ được đưa vào tập chấm sau khi hoàn tất cổng end-to-end trên đúng snapshot và cấu hình. **[TODO: đồng bộ trạng thái T04/T05 trong task-spec với quyết định D-074 và hồ sơ P4A; chốt danh sách task thực sự đủ điều kiện trước khi lập kế hoạch run.]**

Peer là phép so sánh có phạm vi thành viên được khai báo; mẫu số mỗi metric/kỳ gồm các quan sát Gold hợp lệ trong đúng tập yêu cầu. Nếu một thành viên bị loại do thiếu dữ liệu hoặc không đủ điều kiện, báo cáo nêu thành viên, lý do và mẫu số thực tế. Kết quả trên năm ngân hàng không được diễn giải thành ước lượng cho toàn ngành. Macro, nếu được xem xét, là tầng đánh giá riêng và chỉ chạy khi snapshot có quan sát Macro được chấp nhận, phù hợp cùng kỳ và khai báo năng lực cần thiết. CTG bị loại khỏi benchmark A/B/C vì là ca onboarding ngoài Gold.

### 3.4.3. Tổ chức lượt chạy và lưu vết

Trước lượt chấm đầu tiên, cần đóng băng danh sách câu hỏi, bytes/hash của câu hỏi, snapshot và authority scope, phiên bản model/provider, prompt/configuration, rubric, đầu ra, ngân sách tối đa và chính sách lỗi/thử lại. Thứ tự chạy được ngẫu nhiên hóa theo seed đã ghi. Mọi lần thử lại phải tuân theo một chính sách đã định trước; không chỉ chạy lại các kết quả có điểm thấp. Run lỗi, từ chối do điều kiện phạm vi và run không hoàn thành được giữ trong mẫu số completion theo phân loại đã định trước.

Hồ sơ mỗi run cần đủ để nối câu hỏi, arm, lần lặp, thứ tự chạy, snapshot/hash, prompt/configuration và model version, tool/evidence policy, ngân sách, thời điểm bắt đầu/kết thúc, latency, số call, token/chi phí, số vòng sửa, lỗi và trạng thái kết thúc. Candidate run chỉ được so sánh khi mỗi arm dùng đúng prompt/configuration đã đóng băng cho arm đó, không bị trộn giữa phiên bản hoặc bản ghi; snapshot, question-set, rubric, model version, quyền dữ kiện và chính sách bằng chứng cũng phải giữ nguyên theo protocol.

Giao thức dự thảo hiện đưa ra phương án 8 tác vụ phân tích × 3 cấu hình × 2 lần lặp (48 run); phương án ba lần lặp phụ thuộc ngân sách provider. Đây là mục tiêu dự kiến, không phải số run đã thực hiện hoặc cỡ mẫu cuối đã chốt. **[TODO: khóa số tác vụ đủ điều kiện, số lần lặp, seed, timeout, retry, max budget, model/provider cụ thể và cách tính chi phí trước khi khởi tạo run đầu tiên.]**

## 3.5. Phương pháp đánh giá

### 3.5.1. Đánh giá bằng quy tắc

Các thuộc tính có đáp án hoặc hợp đồng xác định được đánh giá bằng quy tắc thay vì chỉ dựa vào nhận xét văn bản. Từng claim số được đối chiếu với observation Gold theo đúng ngân hàng, metric, kỳ, đơn vị và tolerance của metric. Tham chiếu được kiểm tra theo ID và locator; bằng chứng phải hỗ trợ claim theo tuyến phù hợp. Độ bao phủ được tính trên các mục mà AnalysisPlan xác định là áp dụng được: một mục cần được trả lời hoặc được nêu rõ là thiếu/không khả dụng với lý do hợp lệ. `NOT_APPLICABLE` không phải lỗi và bị loại khỏi mẫu số của tiêu chí tương ứng. Trạng thái thiếu đúng được nêu rõ là hành vi mong đợi, không phải giá trị 0.

Các tỷ lệ định lượng phải trình bày cả tử số và mẫu số, ngoài tỷ lệ phần trăm. Ít nhất, báo cáo cần phân biệt độ đúng số liệu, tính hợp lệ của tham chiếu, mức hỗ trợ của bằng chứng, độ bao phủ, vi phạm hợp đồng và trạng thái hoàn thành. Claim không thể chấm phải được phân loại là lỗi hợp đồng hoặc trường hợp cần rà soát, không được âm thầm bỏ khỏi dữ liệu.

### 3.5.2. Đánh giá mù và chi phí vận hành

Các thuộc tính nội dung không rút gọn được thành kiểm tra số học — như tính mạch lạc, mức độ nêu rõ bất định và giới hạn, tính hữu ích cho chuyên viên phân tích, và mức tích hợp giữa các cấp khi AnalysisPlan yêu cầu — được chấm theo rubric có ví dụ neo. Người nghiên cứu (tác giả khóa luận) chấm các phiếu đã được xáo trộn thứ tự và ẩn nhãn A/B/C; một phần phiếu được chấm lại sau khoảng nghỉ để xem xét tính ổn định trong nội bộ người chấm. Đây là thiết kế một người chấm, có giới hạn về độ tin cậy liên chủ thể. Không yêu cầu một nghiên cứu người dùng hoặc đánh giá chuyên gia độc lập như một phần của phép so sánh A/B/C.

**[TODO: hai artifact rubric hiện chưa thống nhất.]** [`scoring-rubric-v1.md`](../experiments/scoring-rubric-v1.md) là bản dự thảo yêu cầu hai checker độc lập và adjudication, đồng thời dùng một số tiêu chí nhị phân; [`EVALUATION-PROTOCOL-V1-DRAFT.md`](EVALUATION-PROTOCOL-V1-DRAFT.md) đề xuất tác giả chấm mù các tiêu chí nội dung thang 0–4 và chấm lại một phần sau độ trễ. Việc người nghiên cứu là người chấm đã được chốt cho phạm vi khóa luận; trước khi chấm, cần cập nhật rubric/protocol cho thống nhất với lựa chọn này, rồi khóa tiêu chí, thang điểm, ví dụ neo, quy tắc bất đồng (nếu có phát sinh rà soát) và cách tổng hợp. Không yêu cầu bổ sung người chấm độc lập.

Chi phí vận hành được báo cáo song song với chất lượng: thời gian xử lý, số lượt gọi mô hình, token đầu vào/đầu ra, ước tính chi phí theo bảng giá/configuration đã ghi, số vòng revision, issue được giải quyết hoặc còn tồn đọng, lỗi và tỷ lệ hoàn thành. Kết quả nên trình bày theo arm và loại tác vụ, giữ các run lỗi trong thống kê completion, đồng thời cho thấy kết quả theo từng câu hỏi/run và chênh lệch ghép cặp giữa cấu hình trên cùng đầu vào. Với cỡ mẫu nhỏ, trọng tâm là thống kê mô tả, chênh lệch ghép cặp và độ lớn hiệu ứng; kiểm định suy luận nếu có chỉ mang tính thăm dò. Nếu báo cáo thêm điểm chất lượng điều chỉnh theo completion, công thức và mẫu số phải được đăng ký trước khi quan sát kết quả. **[TODO: giao thức hiện chưa khóa công thức tổng hợp và cách tính chi phí.]**

### 3.5.3. Ranh giới diễn giải và giới hạn hiện tại

Pilot lịch sử gồm 75 job dự kiến và 61 job hoàn tất chỉ là bằng chứng khả thi cho một phạm vi thử nghiệm trước đây. Pilot đó không chứng minh cấu hình C đã thực hiện vòng targeted revision theo thiết kế hiện tại và không được gộp vào kết quả A/B/C cuối cùng. Những phép thử offline cũng không được trình bày như kết quả chất lượng của model trực tiếp.

Phạm vi suy luận bị giới hạn bởi snapshot năm ngân hàng trong năm 2024, bốn ô thiếu ACB Q1, các task được qua cổng đánh giá, và khả năng cung cấp dữ liệu của snapshot. Hiện chưa có Macro Gold để kiểm tra tác vụ vĩ mô; Peer nhiều kỳ như T08 chưa hỗ trợ; dữ liệu CTG thuộc snapshot onboarding riêng; OCR không được xem là nguồn số liệu đã chấp nhận. Khả năng chạy Company trend trong fixture offline không thay thế kiểm tra provider thật. Các giới hạn này cần được nêu cạnh bảng kết quả nếu các tác vụ liên quan được loại hoặc chưa chạy.

Chấm báo cáo A/B/C không thay thế kiểm tra khả năng chạy của ứng dụng. Readiness và walkthrough ứng dụng là cổng nghiệm thu sản phẩm riêng, không phải điểm chất lượng báo cáo và không đòi hỏi tổ chức nghiên cứu người dùng hoặc chuyên gia độc lập. **[TODO: nếu walkthrough của tác giả được thực hiện, ghi URL/commit, readiness, kịch bản và kết quả; nếu chưa thực hiện, giữ trạng thái pending và không mô tả ứng dụng như đã được kiểm chứng end-to-end.]**

### Hồ sơ nội bộ dùng để biên tập chương này

- [Chương 1–2 working copy, 26/09/2026](THESIS-CHAPTERS-1-2-WORKING-2026-09-26-VI.md): phạm vi, RQ1–RQ3 và định nghĩa A/B/C.
- [Hướng dẫn chỉnh Chương 1–4, 25/09/2026](THESIS-CHAPTERS-1-4-REVISION-GUIDE-2026-09-25.md): cấu trúc Chương 3 và các ranh giới phương pháp được duyệt.
- [Master plan hoàn thiện khóa luận, 24–29/09/2026](THESIS-MASTERPLAN-2026-09-24.md): hiện trạng dữ liệu, onboarding, cổng đánh giá và trạng thái triển khai.
- [Evaluation Protocol v1 — pre-freeze draft](EVALUATION-PROTOCOL-V1-DRAFT.md), [rubric v1](../experiments/scoring-rubric-v1.md) và các task-spec/question/coverage artifact trong `data/evaluation/`: cấu hình ứng viên, tiêu chí và trạng thái chưa đóng băng.
- [Research Register](RESEARCH.md), [Data and Agent Contracts](DATA-CONTRACT.md), [Decisions](DECISIONS.md) và [Architecture](ARCHITECTURE.md): nguồn trạng thái và các ranh giới dữ liệu/runtime.

**[TODO trước khi nộp bản chính thức: bổ sung nguồn học thuật cho khung DSR và nghiên cứu tình huống; thay các ghi chú biên tập bằng tham chiếu/bảng biểu cuối cùng; xác nhận từng con số và cấu hình với snapshot, manifest, run ID và phiếu chấm gốc; chỉ chuyển câu ở thì tương lai/dự kiến sang quá khứ khi có artifact chứng minh thực sự đã thực hiện.]**
