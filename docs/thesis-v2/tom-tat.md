# TÓM TẮT

Khóa luận thiết kế, triển khai và đánh giá một hệ thống đa tác tử phân cấp hỗ trợ phân tích cơ bản mười ngân hàng niêm yết lớn nhất Việt Nam, qua mười quý từ quý 1/2024 đến quý 2/2026, với bốn chỉ tiêu chất lượng tài sản và sinh lời. Mọi con số do chương trình tính và kèm nguồn. Các tác tử viết nhận định có trích dẫn, và mỗi câu được kiểm bằng quy tắc cố định.

Khóa luận so sánh ba cấu hình (A: một tác tử; B: đa tác tử phân cấp; C: có phản biện) và một đối chứng không gọi mô hình (D) trên 12 câu hỏi chuẩn hóa, với hai mô hình ngôn ngữ. Cả bốn cấu hình đạt 100,0% khớp số và truy được về số liệu gốc. Chỉ số này đo trên các câu đã qua bộ kiểm chứng nên phản ánh thiết kế, không phản ánh năng lực mô hình. Với DeepSeek V4 Pro, B có độ phủ cao hơn A (0,812 so với 0,756 trên 10 câu phân tích) với chi phí khoảng 2,2 lần. Lợi thế này không còn trên gpt-5.6-luna, nơi A, B và C cùng đạt 0,912. Ở cả hai mô hình, C làm chi phí tăng ba đến bốn lần so với B mà không cải thiện độ phủ.

Bộ kiểm chứng ban đầu bỏ sót 20,8% lỗi đổi tên chỉ tiêu. Sau khi thêm hai quy tắc, tỷ lệ phát hiện đạt 99,2% trên đột biến giả lập, nhưng chưa được chứng minh với loại lỗi khác. Một khảo sát thăm dò 15 người (chọn thuận tiện) cho thấy 11 người cần truy được về trang báo cáo gốc, và 9 trong 12 người từng dùng chatbot AI đã gặp số sai hoặc không rõ số có đúng không. Hạn chế chính là mẫu nhỏ, mỗi cặp chỉ chạy một lần mỗi mô hình, và chấm điểm phần lớn tự động.

**Từ khóa:** hệ thống đa tác tử; mô hình ngôn ngữ lớn; phân tích tài chính; ngân hàng niêm yết; kiểm chứng số liệu.

# ABSTRACT

This thesis designs, implements and evaluates a hierarchical multi-agent system that supports fundamental analysis of the ten largest listed banks in Vietnam over ten quarters (Q1 2024 to Q2 2026), using four asset-quality and profitability indicators. Every figure is computed in code with its provenance. Specialist agents write cited statements, and each statement is checked against a fixed rule set.

The study compares three configurations (A: single agent; B: hierarchical multi-agent; C: with a critic) and a model-free control (D) on 12 standardized questions, using two language models. All four configurations reach 100.0% numeric agreement and traceability. The metric is measured on sentences that already passed the verifier, so it reflects the design, not model ability. With DeepSeek V4 Pro, B has higher coverage than A (0.812 versus 0.756 on the 10 analytical questions) at about 2.2 times the cost. This advantage disappears on gpt-5.6-luna, where A, B and C all reach 0.912. On both models, C raises cost three to four times over B without improving coverage.

The initial verifier missed 20.8% of indicator-name substitutions. After two rules were added, the detection rate rose to 99.2% on simulated mutants, but it has not been shown for other error types. An exploratory survey of 15 respondents (convenience sample) found that 11 need figures traceable to the source page, and 9 of 12 who had used AI chatbots met wrong or unverifiable figures. The main limitations are the small sample, a single run per model, and largely automated scoring.

**Keywords:** multi-agent system; large language model; financial analysis; verification.
