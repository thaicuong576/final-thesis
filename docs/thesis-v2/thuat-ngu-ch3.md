# Thuật ngữ đã lược ở Chương 3

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
