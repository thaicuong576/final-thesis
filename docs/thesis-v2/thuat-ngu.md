# Thuật ngữ kỹ thuật đã lược khỏi bài

Danh sách các thuật ngữ đã được thay bằng cách diễn đạt dễ hiểu trong Chương 3–6. Cột cuối là gợi ý: giữ trong phụ lục, bỏ hẳn, hoặc đưa lại vào bài. Tệp này chỉ để rà soát, không được đưa vào bản Word.

## Thuật ngữ đã lược ở Chương 3

| Thuật ngữ gốc | Xuất hiện ở mục | Giải thích dễ hiểu (1–2 câu) | Diễn đạt đã dùng trong bài | Gợi ý (giữ trong phụ lục / bỏ / đưa lại vào bài) |
|---|---|---|---|---|
| `src/thesis_data/` | 3.1.2 | Thư mục chứa mã nguồn tầng dữ liệu và các thuật toán tính toán tài chính cốt lõi của hệ thống. | tầng nghiệp vụ và thuật toán | giữ trong phụ lục |
| `src/thesis_api/` | 3.1.2 | Thư mục chứa mã nguồn tầng ứng dụng, quản lý lập kế hoạch, điều phối tác tử và giao tiếp API. | tầng ứng dụng | giữ trong phụ lục |
| `src/thesis_api/analysis_tools.py` | 3.2.2, 3.3.1 | Tệp mã nguồn Python chứa các công cụ tính toán số học như tỷ lệ, biến động, trung vị và xếp hạng. | công cụ phần mềm tính toán / công cụ phân tích do chương trình tính | giữ trong phụ lục |
| `src/thesis_data/report_facts.py` | 3.2.2 | Tệp mã nguồn định nghĩa cấu trúc dữ kiện số và tạo lập dữ kiện báo cáo từ các quan sát tài chính. | công cụ phần mềm tính toán | giữ trong phụ lục |
| `narrative_verification.py` | 3.3.1 | Tệp mã nguồn thực hiện thuật toán kiểm tra từng câu văn để loại bỏ câu sai số hoặc khuyến nghị trái quy định. | bộ kiểm tra câu văn qua bộ quy tắc cố định | giữ trong phụ lục |
| `CanonicalObservation` | 3.1.3 | Cấu trúc dữ liệu chuẩn hóa đại diện cho một quan sát tài chính đơn lẻ đã được chuẩn hóa kỳ và phạm vi. | cấu trúc dữ liệu chuẩn hóa | đưa vào phụ lục |
| `Fact` | 3.1.3, 3.2.2, 3.3.1, 3.3.4 | Đối tượng dữ kiện số học nguyên tử được code tính toán sẵn kèm mã định danh và nguồn gốc. | số liệu đã tính sẵn (lưu cùng nguồn và công thức tính với mã định danh riêng) | đưa vào phụ lục |
| `ReportSpec` | 3.1.3, 3.3.1 | Cấu trúc dữ liệu đặc tả toàn bộ bố cục, các khối nội dung và biểu đồ của một báo cáo phân tích. | các khối báo cáo theo mẫu quy định | đưa vào phụ lục |
| `PlanSpec` / `frozen_spec` | 3.3.1, 3.3.2 | Đặc tả kế hoạch phân tích được cố định hóa trước nhằm đảm bảo tính công bằng giữa các lượt chạy thực nghiệm. | kế hoạch phân tích được cố định trước khi chạy theo quy tắc | giữ trong phụ lục |
| `fact_id` | 3.2.2 | Mã định danh duy nhất của từng dữ kiện số để phục vụ truy xuất nguồn gốc. | mã định danh riêng | bỏ |
| `formula_version` | 3.2.1, 3.2.2 | Phiên bản công thức tính toán toán học được dùng để tạo ra chỉ tiêu dẫn xuất. | công thức có phiên bản | giữ trong phụ lục |
| `input_observation_ids` | 3.2.2, 3.2.4, 3.3.4 | Danh sách mã định danh của các quan sát đầu vào được sử dụng để tính ra dữ kiện số. | danh sách mã quan sát đầu vào | giữ trong phụ lục |
| `calculation receipt` | 3.2.1, 3.2.4 | Bản ghi biên nhận điện tử lưu vết chi tiết công thức, đầu vào, sai số và kết quả tính toán số học. | biên nhận tính toán | đưa vào phụ lục |
| `authority sidecar` | 3.2.1, 3.2.2 | Tệp cấu hình độc lập khóa chặt thẩm quyền về phạm vi báo cáo (riêng lẻ hay hợp nhất) của từng ngân hàng. | quy định về phạm vi số liệu (hợp nhất hay riêng lẻ) | giữ trong phụ lục |
| `source locator` (`printed_page`, `table`, `section`) | 3.2.1, 3.2.2, 3.2.4, 3.3.4 | Bộ thông tin định vị chính xác vị trí của con số trong báo cáo gốc gồm số trang in, bảng biểu và mục thuyết minh. | vị trí nguồn cụ thể (số trang in, tên bảng, mục thuyết minh) | đưa vào phụ lục |
| `null` / `MISSING_IN_SOURCE` | 3.2.2 | Trạng thái và mã lỗi biểu thị dữ liệu bị thiếu từ nguồn công bố chính thức, không thể tự ý ngoại suy. | để trống kèm lý do (thiếu từ nguồn công bố) | bỏ |
| `fail-closed` | 3.2.3 | Cơ chế an toàn trong kỹ thuật phần mềm, tự động từ chối xử lý khi thiếu thông tin thay vì phán đoán bừa. | xử lý an toàn trước dữ liệu thiếu | giữ trong phụ lục |
| `single_agent` | 3.1.3, 3.3.1 | Tên mã cấu hình thử nghiệm sử dụng một tác tử duy nhất đảm nhận toàn bộ quá trình phân tích. | Cấu hình A (Tác tử đơn) | giữ trong phụ lục |
| `hierarchical_no_critique` | 3.1.3, 3.3.1 | Tên mã cấu hình hệ thống đa tác tử phân cấp theo vai trò chuyên môn nhưng chưa có tác tử phản biện. | Cấu hình B (Đa tác tử không phản biện) | giữ trong phụ lục |
| `hierarchical_with_critique` | 3.1.3, 3.3.1 | Tên mã cấu hình hệ thống đa tác tử phân cấp hoàn chỉnh có tác tử phản biện ngữ nghĩa và vòng sửa đổi. | Cấu hình C (Đa tác tử có phản biện) | giữ trong phụ lục |
| `Semantic Critic` / `Revision Controller` | 3.1.3, 3.3.1 | Các cấu phần phần mềm thực hiện việc đọc phản biện báo cáo và điều khiển vòng lặp sửa lỗi câu văn. | Tác tử Phản biện ngữ nghĩa / Bộ điều khiển sửa đổi | giữ trong phụ lục |
| `planner_mode="rules_only"` | 3.3.2 | Chế độ thiết lập hệ thống lập kế hoạch hoàn toàn bằng thuật toán theo quy tắc, không gọi mô hình ngôn ngữ. | thuật toán theo quy tắc để cố định kế hoạch | giữ trong phụ lục |
| `temperature=0.0` / `superparameters` | 3.3.2 | Các thiết lập của mô hình ngôn ngữ lớn điều khiển tính ngẫu nhiên của câu chữ sinh ra. | cùng thiết lập mô hình | bỏ |
| `run_id` | 3.3.2 | Chuỗi mã định danh duy nhất cho từng phiên chạy thử nghiệm để ghi nhật ký độc lập. | mã định danh riêng | bỏ |
| `company_profile`, `lookup`, `trend`, `ranking`, `head_to_head`, `refusal` | 3.3.3 | Các mã phân loại dạng câu hỏi phân tích tài chính trong hệ thống phần mềm. | Hồ sơ doanh nghiệp, Tra cứu chỉ tiêu, Xu hướng chuỗi thời gian, Xếp hạng so sánh, So sánh trực diện, Từ chối hợp lệ | giữ trong phụ lục |
| `pairwise_gap` | 3.3.3 | Trường dữ liệu thể hiện khoảng cách chênh lệch số học giữa hai thực thể trong bài toán so sánh đối đầu. | chênh lệch từng chỉ tiêu | bỏ |
| `COMPLETED`, `AnalysisBlocked` | 3.3.4 | Các mã trạng thái phản hồi của hệ thống báo hiệu lượt chạy hoàn thành thành công hoặc bị từ chối hợp lệ. | trạng thái hoàn thành / trạng thái từ chối phân tích | bỏ |
| `expected-coverage` | 3.3.4 | Tệp định nghĩa ma trận các ô dữ liệu chỉ tiêu bắt buộc phải có cho từng câu hỏi kiểm thử. | ma trận kỳ vọng | giữ trong phụ lục |
| `prompt tokens`, `completion tokens` | 3.3.4 | Đơn vị đo lường lượng dữ liệu văn bản đầu vào và kết quả sinh ra ở đầu ra của mô hình ngôn ngữ lớn. | lượng mã thông báo đầu vào và đầu ra | giữ trong phụ lục |
| `LLM-as-a-judge` | 3.3.4 | Phương pháp sử dụng mô hình ngôn ngữ lớn đóng vai trò giám khảo để chấm điểm văn bản do mô hình khác tạo ra. | mô hình ngôn ngữ tự chấm điểm chính mình | đưa vào phụ lục |
| `bank.asset_quality.npl_ratio`, `bank.asset_quality.loan_loss_coverage`, `bank.profitability.roa`, `bank.profitability.roe` | 3.2.3 | Tên mã định danh chuẩn hóa theo cấu trúc chấm của bốn chỉ tiêu tài chính trong cơ sở dữ liệu. | Tỷ lệ nợ xấu nhóm 3 đến 5, Tỷ lệ bao phủ nợ xấu, ROA, ROE | giữ trong phụ lục |
| `2024_Q1`, `2024_Q2`, `2024_Q3`, `2024_Q4` | 3.2.3, 3.3.3 | Định dạng mã hóa chuỗi thời gian kết hợp năm và quý trong hệ thống cơ sở dữ liệu. | Q1/2024, Q2/2024, Q3/2024, Q4/2024 | bỏ |
| `gold-bank-2025-expanded-v5-evidence` | 3.2.3 | Tên định danh của gói dữ liệu chuẩn đối sánh phiên bản 5 được kiểm soát toàn diện. | bộ dữ liệu Gold v5 | giữ trong phụ lục |
| `unit tests` | 3.1.2 | Các bài kiểm thử phần mềm tự động ở cấp độ hàm hoặc module nhỏ nhất. | trường hợp kiểm thử tự động | bỏ |
| `callout` | 3.3.4 | Khối thành phần giao diện người dùng hiển thị hộp thông tin hoặc cảnh báo nổi bật. | phần ghi chú nổi bật | bỏ |
| `tất định` / `xác định luận` | 3.1.2, 3.3.1, 3.3.4 | Khái niệm chỉ các thuật toán máy tính cho cùng một kết quả với cùng một đầu vào. | theo quy tắc cố định / do chương trình tính | đưa vào phụ lục |
| `ảo giác` (hallucination) | 3.1.2, 3.2.2 | Hiện tượng mô hình ngôn ngữ lớn sinh ra các thông tin sai lệch không có trong dữ liệu gốc. | mô hình tự bịa ra thông tin | đưa vào phụ lục |

## Thuật ngữ đã lược ở Chương 4

| Thuật ngữ gốc | Xuất hiện ở mục | Giải thích dễ hiểu (1–2 câu) | Diễn đạt đã dùng trong bài | Gợi ý (giữ trong phụ lục / bỏ / đưa lại vào bài) |
|---|---|---|---|---|
| `src/thesis_data/` | 4.1.1, 4.2.6, 4.6 | Thư mục chứa tầng lõi nghiệp vụ và các thuật toán tính toán tài chính thuần túy, không phụ thuộc thư viện bên ngoài. | Tầng lõi nghiệp vụ và thuật toán thuần túy | Giữ trong phụ lục |
| `src/thesis_api/` | 4.1.1, 4.5 | Thư mục chứa tầng ứng dụng, khung máy chủ giao tiếp và bộ điều phối luồng phân tích. | Tầng ứng dụng và dịch vụ phân tích | Giữ trong phụ lục |
| `query-adaptive analysis flow` | Mở đầu, 4.2 | Quy trình xử lý tự động điều chỉnh linh hoạt các bước tính toán và báo cáo dựa trên nội dung câu hỏi của người dùng. | Quy trình xử lý một lượt phân tích thích ứng theo câu hỏi | Bỏ |
| `pure Python logic` | 4.1.1 | Thuật toán viết bằng ngôn ngữ lập trình tiêu chuẩn, không kết nối trực tiếp đến cơ sở dữ liệu hay dịch vụ trí tuệ nhân tạo. | Thư viện thuật toán độc lập | Bỏ |
| `Negative Constraints` | 4.1.1 | Các ràng buộc trong kiến trúc nhằm ngăn chặn việc tầng lõi phụ thuộc vào các công nghệ bên ngoài. | Ràng buộc kỹ thuật | Giữ trong phụ lục |
| `Transferability Invariant` | 4.1.1 | Nguyên tắc bảo đảm mã nguồn thuật toán không bị gắn cứng vào bất kỳ ngân hàng cụ thể nào để có thể tái sử dụng cho ngân hàng khác. | Tính độc lập với dữ liệu cụ thể | Giữ trong phụ lục |
| `application shell` | 4.1.1 | Lớp vỏ ứng dụng tiếp nhận yêu cầu từ người dùng, quản lý phiên làm việc và kết nối các dịch vụ phụ trợ. | Lớp vỏ điều phối | Bỏ |
| `FastAPI` | 4.1.1, 4.5, 4.6 | Khung phần mềm chuyên dùng để xây dựng các cổng giao tiếp dịch vụ web hiệu năng cao. | Khung máy chủ phân tích | Giữ trong phụ lục |
| `Server-Sent Events (SSE)` | 4.1.1, 4.3.1, 4.4.3, 4.5 | Giao thức truyền dòng dữ liệu một chiều liên tục từ máy chủ về trình duyệt người dùng qua kết nối mạng. | Cơ chế truyền sự kiện từ máy chủ (Server-Sent Events - SSE) | Giữ trong phụ lục |
| `SQLITE_DB_PATH` | 4.1.2, 4.5 | Biến cấu hình chỉ định đường dẫn tệp cơ sở dữ liệu chứa các chỉ tiêu tài chính đã được xác thực. | Cơ sở dữ liệu phân tích chỉ đọc | Giữ trong phụ lục |
| `ANALYSIS_RUNS_DB_PATH` | 4.1.2, 4.3.2 | Biến cấu hình chỉ định đường dẫn tệp cơ sở dữ liệu lưu trữ lịch sử các phiên phân tích và nhật ký vết. | Cơ sở dữ liệu lịch sử phiên chạy | Giữ trong phụ lục |
| `mode=ro` | 4.1.2 | Cấu hình mở tệp cơ sở dữ liệu ở chế độ chỉ đọc nhằm bảo vệ dữ liệu gốc khỏi bị sửa đổi hoặc ghi đè. | Chế độ chỉ đọc | Bỏ |
| `WAL mode` | 4.1.2 | Cơ chế ghi nhật ký trước giúp cơ sở dữ liệu tăng tốc độ truy xuất và hỗ trợ đọc đồng thời an toàn. | Cơ chế nhật ký ghi trước | Giữ trong phụ lục |
| `Alias Rejection` | 4.1.2 | Cơ chế tự động từ chối khởi động nếu phát hiện hai đường dẫn cơ sở dữ liệu trỏ về cùng một tệp vật lý. | Cơ chế chống trùng lặp định danh tệp | Giữ trong phụ lục |
| `hardlink` | 4.1.2 | Liên kết phần cứng trong hệ điều hành khiến hai tên tệp khác nhau cùng trỏ về một vùng dữ liệu vật lý. | Liên kết phần cứng | Bỏ |
| `SnapshotBootstrapError` | 4.1.2 | Thông báo lỗi khi hệ thống không thể tải hoặc xác thực tệp dữ liệu tài chính lúc máy chủ khởi động. | Thông báo lỗi nạp dữ liệu | Bỏ |
| `ResolvedQuery` | 4.2.1, 4.2.2 | Cấu trúc dữ liệu lưu trữ kết quả phân tích cú pháp và ý định câu hỏi của người dùng. | Cấu trúc dữ liệu câu hỏi đã giải mã | Giữ trong phụ lục |
| `Unicode NFC` và `casefolding` | 4.2.1 | Chuẩn mã hóa văn bản thống nhất và phép chuyển chữ thường giúp chuẩn hóa câu hỏi tiếng Việt. | Bảng mã chuẩn Unicode NFC, chuyển toàn bộ về chữ thường | Bỏ |
| `Entity Extraction` | 4.2.1 | Kỹ thuật tự động nhận diện và bóc tách tên thực thể như tên hoặc mã ngân hàng trong văn bản. | Nhận diện ngân hàng | Bỏ |
| `Period Resolution` | 4.2.1 | Kỹ thuật quy đổi các cách biểu đạt thời gian tự do trong tiếng Việt thành mã kỳ kế toán chuẩn. | Xác định kỳ báo cáo | Bỏ |
| `Metric Resolution` | 4.2.1 | Kỹ thuật trích xuất và ánh xạ các cụm từ chỉ tiêu tài chính thành mã chỉ tiêu chuẩn trong hệ thống. | Nhận diện chỉ tiêu tài chính | Bỏ |
| `Semantic Flags` | 4.2.1 | Các cờ logic nhận diện ý định của người dùng dựa trên từ khóa nhận diện được trong câu hỏi. | Phát hiện cờ ý định phân tích | Giữ trong phụ lục |
| `ToolCallSpec` | 4.2.2 | Cấu trúc dữ liệu mô tả lệnh gọi công cụ số học kèm theo các tham số chi tiết. | Lệnh gọi công cụ phân tích | Giữ trong phụ lục |
| `rules_plan` | 4.2.2 | Kế hoạch phân tích được lập hoàn toàn theo các quy tắc luật định sẵn mà không cần gọi mô hình ngôn ngữ. | Kế hoạch phân tích theo luật | Giữ trong phụ lục |
| `model_plan` | 4.2.2 | Kế hoạch phân tích do mô hình ngôn ngữ lớn đề xuất dựa trên câu hỏi của người dùng. | Kế hoạch do mô hình đề xuất | Bỏ |
| `Plan Freezing` | 4.2.2 | Nguyên tắc khóa cố định kế hoạch phân tích sau khi thẩm định để các tác tử không gọi công cụ ngoài phạm vi. | Cố định kế hoạch trước khi chạy | Đưa lại vào bài |
| `Fact` | 4.2.3, 4.2.4, 4.2.5, 4.2.6 | Đơn vị số liệu tài chính được tính toán chính xác bằng công thức toán học có nguồn gốc đối soát. | Số liệu đã tính sẵn (lưu cùng nguồn và công thức) | Đưa lại vào bài |
| `Dataset` | 4.2.3, 4.2.7 | Cấu trúc dữ liệu đã được định dạng chuẩn để phục vụ việc hiển thị các loại biểu đồ trực quan. | Cấu trúc tập dữ liệu biểu đồ | Bỏ |
| `formula_version` | 4.2.3 | Mã định danh phiên bản công thức toán học dùng để tính toán dữ kiện tài chính. | Phiên bản công thức tính toán | Giữ trong phụ lục |
| `input_observation_ids` | 4.2.3 | Danh sách mã định danh của các số liệu quan sát gốc cấu thành nên dữ kiện tài chính. | Mã định danh quan sát đầu vào | Giữ trong phụ lục |
| `fact_ids` | 4.2.5, 4.2.6 | Danh sách mã định danh dữ kiện mà câu nhận định bắt buộc phải trích dẫn để chứng minh số liệu. | Mã định danh dữ kiện | Giữ trong phụ lục |
| `hien_thi` | 4.2.5 | Trường dữ liệu chứa chuỗi số đã được định dạng chuẩn kèm đơn vị đo lường để chép vào câu văn. | Chuỗi văn bản hiển thị đã định dạng sẵn | Bỏ |
| `NarrativeSentence` | 4.2.5 | Cấu trúc dữ liệu biểu diễn một câu nhận định phân tích do chuyên viên hoặc mô hình viết ra. | Câu nhận định phân tích | Bỏ |
| `DroppedSentence` | 4.2.6 | Bản ghi lưu trữ các câu nhận định bị bộ kiểm tra loại bỏ kèm theo lý do cụ thể. | Bản ghi câu nhận định bị loại bỏ | Giữ trong phụ lục |
| `NarrativeAudit` | 4.2.6, 4.3.2 | Hồ sơ lưu vết toàn bộ kết quả thẩm định các câu nhận định trong suốt phiên phân tích. | Hồ sơ kiểm định nhận định | Giữ trong phụ lục |
| `flat_pp` | 4.2.6 | Ngưỡng biến động điểm phần trăm tối thiểu để kết luận một chỉ tiêu tăng hoặc giảm thay vì đi ngang. | Ngưỡng đi ngang mặc định là 0,05 điểm phần trăm | Giữ trong phụ lục |
| `tolerance` | 4.2.6 | Khoảng sai số cho phép khi đối chiếu số thực trong câu văn với dữ kiện gốc dựa trên số chữ số thập phân hiển thị. | Dung sai chấp nhận được | Giữ trong phụ lục |
| `ReportSpec` | 4.2.7, 4.3.2 | Bản đặc tả kỹ thuật quy định cấu trúc và nội dung hoàn chỉnh của báo cáo phân tích theo từng khối. | Bản đặc tả báo cáo | Giữ trong phụ lục |
| `CHART_COMPATIBILITY` | 4.2.7 | Ma trận kiểm tra tính tương thích toán học giữa dạng tập dữ liệu và loại biểu đồ trực quan. | Ma trận tương thích giữa biểu đồ và dữ liệu | Bỏ |
| `CritiqueIssue` | 4.2.8 | Bản ghi mô tả khuyết tật về lập luận hoặc tính trúng trọng tâm do tác tử phản biện ngữ nghĩa phát hiện. | Vấn đề cần khắc phục do phản biện phát hiện | Giữ trong phụ lục |
| `Targeted Revision` | 4.2.8 | Quy trình chỉ gửi yêu cầu viết lại đúng câu nhận định bị gắn cờ lỗi mà không chạy lại toàn bộ hệ thống. | Quy trình sửa đổi có mục tiêu | Đưa lại vào bài |
| `TraceStep` | 4.3.1, 4.3.2 | Đối tượng dữ liệu ghi nhận chi tiết hành động và sự kiện của từng bước trong phiên phân tích. | Bản ghi vết từng bước | Giữ trong phụ lục |
| `AnalysisBlocked` | 4.3.3 | Ngoại lệ thông báo yêu cầu phân tích bị từ chối do vượt quá phạm vi dữ liệu được hỗ trợ. | Thông báo từ chối phân tích có kiểm soát | Bỏ |
| `Single Page Application (SPA)` | 4.4 | Kiến trúc ứng dụng web hiện đại chỉ tải một trang duy nhất và cập nhật dữ liệu động mà không cần tải lại trang. | Ứng dụng trang đơn | Bỏ |
| `Vercel Edge Network` | 4.5 | Nền tảng phân phối ứng dụng phía người dùng tại các máy chủ biên gần vị trí truy cập nhất. | Nền tảng phân phối biên đám mây | Giữ trong phụ lục |
| `Render Web Service` | 4.5 | Nền tảng dịch vụ đám mây vận hành máy chủ phân tích trong môi trường vùng chứa tự động. | Máy chủ dịch vụ đám mây | Giữ trong phụ lục |
| `Supabase Storage` | 4.5 | Dịch vụ lưu trữ đối tượng đám mây an toàn dùng để lưu trữ bản sao dữ liệu chuẩn. | Kho lưu trữ đám mây riêng tư | Giữ trong phụ lục |
| `Snapshot Hydration` | 4.5 | Quy trình tự động tải và kích hoạt tệp cơ sở dữ liệu chuẩn từ đám mây về bộ nhớ máy chủ lúc khởi động. | Cơ chế tự động nạp bộ dữ liệu chuẩn | Đưa lại vào bài |
| `PRAGMA integrity_check` | 4.5 | Lệnh nội tại của cơ sở dữ liệu SQLite dùng để kiểm tra tính toàn vẹn vật lý của các bảng và chỉ mục. | Lệnh kiểm tra tính toàn vẹn cấu trúc vật lý của cơ sở dữ liệu | Bỏ |
| `Liveness / Readiness Probe` | 4.5 | Các điểm kiểm tra tự động định kỳ để xác định máy chủ đang chạy và đã sẵn sàng phục vụ yêu cầu hay chưa. | Cổng thăm dò sự sống / Cổng thăm dò mức độ sẵn sàng | Giữ trong phụ lục |
| `Zero-Failure Handoff` | 4.6 | Nguyên tắc phát triển phần mềm yêu cầu tất cả các bài kiểm thử tự động phải đạt kết quả thành công trước khi tích hợp mã nguồn. | Nguyên tắc bàn giao không lỗi | Đưa lại vào bài |

## Thuật ngữ đã lược ở Chương 5 và Chương 6

| Thuật ngữ gốc | Xuất hiện ở mục | Giải thích dễ hiểu | Diễn đạt đã dùng trong bài | Gợi ý |
|---|---|---|---|---|
| Snapshot Gold v5 (`gold-bank-2025-expanded-v5-evidence`) | 5.2, 6.1 | Bản chụp cố định của bộ dữ liệu đã kiểm chứng, không thay đổi trong suốt thực nghiệm | bộ dữ liệu Gold v5 | Giữ tên "Gold v5"; tên kỹ thuật đầy đủ chỉ cần ở phụ lục |
| SHA-256 `1b1b5c09…ce73` | 5.2 | Mã kiểm tra tính toàn vẹn của tệp dữ liệu; tệp đổi một byte thì mã đổi | được khóa bằng mã kiểm tra | Phụ lục (bảng cấu hình thực nghiệm) |
| `deepseek-v4-pro-0813`, nhà cung cấp tương thích OpenAI | 5.2 | Tên phiên bản mô hình ngôn ngữ và cách gọi mô hình qua giao thức chuẩn | mô hình ngôn ngữ DeepSeek V4 Pro | Phụ lục; có thể nhắc tên đầy đủ một lần trong 3.3 |
| Seed 20260930 | 5.2 | Giá trị cố định để xáo trộn thứ tự chạy mà vẫn lặp lại được | xáo trộn ngẫu nhiên theo một giá trị cố định | Phụ lục |
| Token | 5.2, 5.3, 6.1 | Đơn vị đo khối lượng văn bản mô hình đọc và viết; cũng là cơ sở tính chi phí | "token (đơn vị đo khối lượng văn bản…)" ở lần đầu, sau đó "lượng văn bản mô hình phải xử lý" | Nên giữ "token" trong bảng số liệu vì là đơn vị đo chuẩn |
| `rules_only` | 5.2 | Chế độ lập kế hoạch chỉ theo luật cố định, không để mô hình đề xuất | kế hoạch phân tích được lập theo luật cố định | Bỏ khỏi bài |
| `known_limitations`, mã băm kế hoạch | 5.2 | Trường ghi chú giới hạn do hệ thống thêm sau khi chạy; mã băm dùng để so kế hoạch giữa các cấu hình | hệ thống kiểm tra lại và xác nhận kế hoạch giống hệt nhau | Phụ lục (nếu hội đồng hỏi về tính công bằng) |
| `completed` / `accepted_with_limitations` | 5.2, 5.3 | Hai trạng thái kết thúc của báo cáo: hoàn tất không ghi chú, và hoàn tất kèm ghi chú giới hạn | "hoàn thành trọn vẹn" và "trả lời được (có thể kèm ghi chú giới hạn)" | Bỏ khỏi bài |
| MAJOR / MINOR (mức nghiêm trọng của phản biện) | 5.5 | Hai mức độ vấn đề do bộ phản biện gán | nghiêm trọng / mức nhẹ | Bỏ khỏi bài |
| Staging, Render | 5.1.2 | Môi trường chạy thử trên mạng và dịch vụ máy chủ đang dùng | phiên bản đang vận hành trên mạng | Chương 4 (phần triển khai) đã nêu; không cần lặp lại |
| Kiểm tra hợp đồng OpenAPI, `check_architecture_guardrails.py`, `src/thesis_data/` | 5.1.1 | Hai bước tự động kiểm tra định dạng dữ liệu trao đổi và ranh giới kiến trúc | kiểm tra định dạng dữ liệu trao đổi / phần lõi không bị gắn chặt | Phụ lục kỹ thuật |
| Stage-1 | (1.3, RQ3) | Lớp kiểm tra số liệu theo quy tắc chạy trước mọi bước đánh giá nội dung | "kiểm tra số liệu theo quy tắc" | Chương 1 đã được cập nhật thành diễn đạt thường |
| `experiments/er8/` và tên tệp hình | 5 | Thư mục lưu kết quả thực nghiệm | "các tệp kết quả được lưu lại cùng mã nguồn" | Phụ lục (đường dẫn để tái lập) |

