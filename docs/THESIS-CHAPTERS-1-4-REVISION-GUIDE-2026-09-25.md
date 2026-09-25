# Hướng dẫn chỉnh Chương 1–4 theo trạng thái hệ thống

**Ngày khóa hướng dẫn:** 25/09/2026  
**Vai trò:** checklist biên tập; không thay thế artifact, manifest hay kết quả chạy.

## 1. Tên và đối tượng nghiên cứu

Tên phù hợp nhất với artifact đang xây là:

> **Thiết kế và đánh giá hệ thống đa tác tử hỗ trợ tổng hợp thông tin và phân tích cơ bản các ngân hàng niêm yết tại Việt Nam**

Tên này mô tả đúng domain đã triển khai và tránh tạo kỳ vọng rằng hệ thống đã hỗ
trợ mọi doanh nghiệp tài chính. Nếu hệ thống quản lý khóa luận không cho đổi
tên, giữ tên hành chính hiện tại nhưng toàn bộ nội dung, dataset, câu hỏi, app và
kết luận phải công bố phạm vi case study là nhóm ngân hàng.

Đối tượng nghiên cứu là **artifact hệ thống và hiệu quả của artifact**. Năm ngân
hàng trong Gold là mẫu kiểm chứng có chủ đích, không phải mẫu đại diện thống kê
cho ngành. CTG ngoài Gold là bài kiểm tra chuyển giao vận hành sau chuẩn hóa và
kiểm định, không tự động trở thành thành viên của benchmark.

## 2. Chương 1

Giữ cấu trúc 1.1–1.4. Sửa ba điểm sau.

### 2.1. Câu hỏi nghiên cứu

- **RQ1:** Hệ thống đa tác tử phân cấp và thích ứng theo truy vấn cần được thiết
  kế như thế nào để tổng hợp thông tin, phân tích cơ bản ngân hàng và duy trì
  khả năng truy nguyên từ nhận định tới dữ liệu và nguồn?
- **RQ2:** Trên cùng bộ câu hỏi, snapshot dữ liệu và điều kiện chạy, cấu hình đa
  tác tử thích ứng không có phản biện (B) khác cấu hình một tác tử (A) như thế
  nào về độ chính xác, truy vết bằng chứng, tính nhất quán và tính hữu ích; khác
  biệt về độ trễ, số lượt gọi, token/chi phí và tỷ lệ hoàn thành ra sao?
- **RQ3:** So với cấu hình B, việc bổ sung phản biện ngữ nghĩa và tối đa hai vòng
  sửa đổi có mục tiêu, kèm kiểm tra Stage-1 lại (C), làm thay đổi chất lượng báo
  cáo và chi phí vận hành như thế nào?

Các câu hỏi không giả định B hoặc C tốt hơn A.

### 2.2. Phạm vi empirical

Dùng phát biểu sau làm ranh giới:

> Trong thực nghiệm, nhóm ngân hàng được chọn là phạm vi đối sánh, không đại
> diện cho toàn bộ ngành. Thống kê peer chỉ được tính từ các quan sát được chấp
> nhận trong nhóm và phải nêu rõ mẫu số. Dữ liệu ngành hoặc vĩ mô chỉ được dùng
> khi có trong snapshot được chấp nhận, phù hợp về nguồn và kỳ, và được
> AnalysisPlan yêu cầu; chúng được trình bày riêng, không gộp vào thống kê peer.

Gold v5 hiện có 80 ô mục tiêu, gồm 76 quan sát hợp lệ và bốn giá trị thiếu được
ghi rõ. Không gọi SQLite legacy 27 ngân hàng là Gold. D-063/D-072 tiếp tục chặn
peer ROE năm issuer cho tới khi VPB definition gate được hòa giải; có thể loại
VPB ROE khỏi task đó thay vì dừng toàn bộ thực nghiệm.

### 2.3. Giới hạn chuyển giao dữ liệu

Hệ thống không hứa rằng tải một PDF bất kỳ là phân tích được ngay. PDF text hoặc
scan đi qua parser/OCR chỉ tạo candidate theo trang. Numeric observation chỉ
được dùng sau khi xác định metric, kỳ, đơn vị, scope, nguồn/locator, đối soát với
tài liệu chính thức và đóng vào snapshot. Derived metric của ngân hàng mới còn
phải được code tính lại từ input đã chấp nhận và lưu calculation receipt.

## 3. Chương 2

Khung 2.1–2.4 phù hợp với thesis hướng ứng dụng. Cần chỉnh:

1. Các mục 2.1–2.3 hiện rút ra sáu nguyên tắc nhưng bảng 2.4 có tám. Đánh số
   1–8 và bổ sung lập luận cho việc tách kiểm tra factual khỏi đánh giá semantic,
   hoặc hợp nhất bảng để số lượng và phần dẫn xuất khớp nhau.
2. Đặt portability như một hệ quả của provider boundary và validated snapshot;
   chi tiết adapter/configuration thuộc Chương 4.
3. MetaGPT, ChatDev, MultiAgentBench và nghiên cứu debate là bằng chứng thiết kế
   AI tổng quát, không phải bằng chứng rằng multi-agent phân tích ngân hàng tốt
   hơn. Giữ cách diễn đạt có điều kiện.
4. Hòa giải `CFA Institute, 2026` với hậu tố `2026a/2026b` theo bibliography;
   kiểm tra venue/năm của MetaGPT, ChatDev và Liang trước khi khóa tài liệu.

## 4. Chương 3: phương pháp, không kể implementation

### 4.1. Cách tiếp cận

Trình bày chuỗi applied/design-oriented:

```text
vấn đề thực tế → yêu cầu thiết kế → artifact → verification → experiment → evaluation
```

Design Science Research chỉ là khung tổ chức. Chương 3 mô tả cách tạo và đánh
giá artifact, không dành một phần dài để khảo cứu DSR.

### 4.2. Dữ liệu và acceptance

Tách bốn trạng thái:

1. nguồn/PDF/CSV thô;
2. candidate đã parse và map;
3. operational snapshot đã đối soát nguồn, locator và phép tính;
4. Gold benchmark đã qua gate độc lập.

Nêu Gold v5 bằng snapshot ID, hash và manifest, cùng 76 valid + 4 missing. CTG
chỉ chứng minh portability sau khi D-071 calculation receipts chạy thật. Phân
biệt structured observations với document evidence; `missing` không bằng 0.

### 4.3. Verification

Mô tả kiểm thử component, contract, fail-closed và end-to-end như bằng chứng hệ
thống làm đúng thiết kế. Test pass không phải bằng chứng B/C tốt hơn A. Không kể
commit, lịch sử phase hoặc số test như nội dung nghiên cứu chính.

### 4.4. Thực nghiệm A/B/C

- A: một tác tử.
- B: hierarchy thích ứng theo truy vấn, chưa có semantic critique/revision.
- C: cùng plan/specialist với B, cộng semantic critique và tối đa hai vòng sửa
  đúng specialist bị ảnh hưởng.

Giữ giống nhau: câu hỏi, accepted facts, snapshot, model/prompt version, tools,
evidence policy và output contract. Giới hạn ngân sách phải so sánh được, nhưng
không ép số call bằng nhau; call, token, cost, latency và revision là outcome.
Đóng băng question set, ghi run order/retry, ẩn nhãn A/B/C khi tự chấm, và giữ
run lỗi trong mẫu số completion. Macro là stratum riêng và chỉ chạy nếu dữ liệu
macro cùng kỳ qua Gold gate.

### 4.5. Evaluation

Numeric accuracy, reference validity và evidence support dùng kiểm tra có quy
tắc. Coverage, logic, uncertainty và usefulness dùng rubric mù. Báo cáo cả
completion/failure, latency, calls, tokens/cost và revisions. Một người chấm là
giới hạn hợp lệ nếu rubric được khóa trước, cấu hình bị ẩn và một phần phiếu được
chấm lại sau khoảng nghỉ.

Pilot 75 job/61 hoàn tất là bằng chứng feasibility lịch sử. Không dùng nó làm
kết quả cuối của C vì vòng targeted revision thật chưa được chứng minh ở pilot.

## 5. Chương 4: chỉ mô tả behavior đã triển khai

- **4.1:** yêu cầu và kiến trúc từ request đến report; query-adaptive, không ép
  tuyến Macro → Sector → Company.
- **4.2:** canonical observation, document evidence, provider/tools, capability
  catalog, snapshot identity và provenance. Numeric claim có tuyến observation
  → source + locator; document snippet chỉ gắn khi có association thật.
- **4.3:** AnalysisRequest → capability check → frozen AnalysisPlan → active
  specialists → synthesis của các relation relevant. Phân biệt peer với sector.
- **4.4:** Stage-1 chạy trước semantic critic. Mỗi CritiqueIssue nêu claim,
  specialist và action; chỉ rerun specialist đang active, re-synthesize rồi chạy
  Stage-1 lại, tối đa hai vòng. `NOT_APPLICABLE` không phải fail hoặc điểm tuyệt
  đối. Hard-gate failure không được đổi thành `ACCEPT_WITH_LIMITATIONS`.
- **4.5:** Dataset → Create Analysis → Session → Report. Không cho chọn agent,
  không lộ chain-of-thought. Chỉ ghi Report Library nếu cuối cùng đã triển khai.

Cho tới khi composite và deploy gate đạt, dùng từ “đã thiết kế/đã kiểm thử ở
core” cho Stage-1/revision kernel và “chưa kiểm chứng end-to-end” cho app. HTTP
200 hoặc unit test của kernel không chứng minh luồng public đã hoạt động.

## 6. Ngân sách 60 trang

| Phần | Trang mục tiêu |
|---|---:|
| Trang đầu | 3 |
| Chương 1 | 8 |
| Chương 2 | 8 |
| Chương 3 | 9 |
| Chương 4 | 11 |
| Chương 5 | 8 |
| Chương 6 | 3 |
| Tài liệu tham khảo | 3 |
| Phụ lục | 7 |
| **Tổng** | **60** |

Đây là ngân sách biên tập. Số trang cuối phải kiểm bằng bản render đúng template.
