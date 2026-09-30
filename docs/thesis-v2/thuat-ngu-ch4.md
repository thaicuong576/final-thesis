# Thuật ngữ đã lược ở Chương 4

| Thuật ngữ gốc | Xuất hiện ở mục | Giải thích dễ hiểu (1–2 câu) | Diễn đạt đã dùng trong bài | Gợi ý (giữ trong phụ lục / bỏ / đưa lại vào bài) |
|---|---|---|---|---|
| `src/thesis_data/` | 4.1.1, 4.2.6, 4.6 | Thư mục chứa tầng lõi nghiệp vụ và các thuật toán tính toán tài chính thuần túy, không phụ thuộc thư viện bên ngoài. | Tầng lõi nghiệp vụ và thuật toán thuần túy | Giữ trong phụ lục |
| `src/thesis_api/` | 4.1.1, 4.5 | Thư mục chứa tầng ứng dụng, khung máy chủ giao tiếp và bộ điều phối luồng phân tích. | Tầng ứng dụng và dịch vụ phân tích | Giữ trong phụ lục |
| `query-adaptive analysis flow` | Mở đầu, 4.2 | Quy trình xử lý tự động điều chỉnh linh hoạt các bước tính toán và báo cáo dựa trên nội dung câu hỏi của người dùng. | Quy trình xử lý một lượt phân tích thích ứng theo câu hỏi | Bỏ |
| `pure Python logic` | 4.1.1 | Thuật toán viết bằng ngôn ngữ lập trình tiêu chuẩn, không kết nối trực tiếp đến cơ sở dữ liệu hay dịch vụ trí tuệ nhân tạo. | Thư viện thuật toán độc lập | Bỏ |
| `Negative Constraints` | 4.1.1 | Các ràng buộc cấm trong kiến trúc nhằm ngăn chặn việc tầng lõi phụ thuộc vào các công nghệ bên ngoài. | Ràng buộc cấm | Giữ trong phụ lục |
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
| `Plan Freezing` | 4.2.2 | Nguyên tắc khóa cố định kế hoạch phân tích sau khi thẩm định để các tác tử không gọi công cụ ngoài phạm vi. | Đóng băng kế hoạch phân tích | Đưa lại vào bài |
| `Fact` | 4.2.3, 4.2.4, 4.2.5, 4.2.6 | Đơn vị dữ kiện tài chính nguyên tử được tính toán chính xác bằng công thức toán học có nguồn gốc đối soát. | Dữ kiện tài chính nguyên tử (hoặc Dữ kiện) | Đưa lại vào bài |
| `Dataset` | 4.2.3, 4.2.7 | Cấu trúc dữ liệu đã được định dạng chuẩn để phục vụ việc hiển thị các loại biểu đồ trực quan. | Tập dữ liệu biểu đồ | Bỏ |
| `formula_version` | 4.2.3 | Mã định danh phiên bản công thức toán học dùng để tính toán dữ kiện tài chính. | Phiên bản công thức tính toán | Giữ trong phụ lục |
| `input_observation_ids` | 4.2.3 | Danh sách mã định danh của các số liệu quan sát gốc cấu thành nên dữ kiện tài chính. | Mã định danh quan sát đầu vào | Giữ trong phụ lục |
| `fact_ids` | 4.2.5, 4.2.6 | Danh sách mã định danh dữ kiện mà câu nhận định bắt buộc phải trích dẫn để chứng minh số liệu. | Mã định danh dữ kiện | Giữ trong phụ lục |
| `hien_thi` | 4.2.5 | Trường dữ liệu chứa chuỗi số đã được định dạng chuẩn kèm đơn vị đo lường để chép vào câu văn. | Chuỗi ký tự hiển thị đã được định dạng sẵn | Bỏ |
| `NarrativeSentence` | 4.2.5 | Cấu trúc dữ liệu biểu diễn một câu nhận định phân tích do chuyên viên hoặc mô hình viết ra. | Câu nhận định phân tích | Bỏ |
| `DroppedSentence` | 4.2.6 | Bản ghi lưu trữ các câu nhận định bị bộ kiểm tra xác định luận loại bỏ kèm theo lý do cụ thể. | Bản ghi câu nhận định bị loại bỏ | Giữ trong phụ lục |
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
| `Snapshot Hydration` | 4.5 | Quy trình tự động tải và kích hoạt tệp cơ sở dữ liệu chuẩn từ đám mây về bộ nhớ máy chủ lúc khởi động. | Cơ chế tự động nạp dữ liệu chuẩn | Đưa lại vào bài |
| `PRAGMA integrity_check` | 4.5 | Lệnh nội tại của cơ sở dữ liệu SQLite dùng để kiểm tra tính toàn vẹn vật lý của các bảng và chỉ mục. | Lệnh kiểm tra tính toàn vẹn cấu trúc vật lý của cơ sở dữ liệu | Bỏ |
| `Liveness / Readiness Probe` | 4.5 | Các điểm kiểm tra tự động định kỳ để xác định máy chủ đang chạy và đã sẵn sàng phục vụ yêu cầu hay chưa. | Cổng thăm dò sự sống / Cổng thăm dò mức độ sẵn sàng | Giữ trong phụ lục |
| `Zero-Failure Handoff` | 4.6 | Nguyên tắc phát triển phần mềm yêu cầu tất cả các bài kiểm thử tự động phải vượt qua tuyệt đối trước khi tích hợp mã nguồn. | Nguyên tắc bàn giao không lỗi | Đưa lại vào bài |
