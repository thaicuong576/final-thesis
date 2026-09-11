# Mục lục tài liệu — bộ tài liệu trình bày với thầy

Ngày đóng gói: `2026-09-10`

## 1. Bản thảo khóa luận

- [Bản nháp Chương 1–7](THESIS-DRAFT-CHAPTERS-1-4-VI.md)
- [Đề cương và bản đồ viết](THESIS-DRAFT-OUTLINE-VI.md)
- [Từ điển chỉ số](METRIC-DICTIONARY.md)
- [Hợp đồng đầu ra v2](OUTPUT-CONTRACT-V2.md)

## 2. Cơ sở dữ liệu Gold và chất lượng dữ liệu

- [Cơ sở dữ liệu SQLite Gold v5 có bằng chứng](../data/processed/gold-bank-2025-expanded-v5-evidence.sqlite)
- [Báo cáo kiểm toán Gold dạng Markdown](../reports/data-foundation/gold-bank-2025-expanded-v5-evidence.md)
- [Báo cáo kiểm toán Gold dạng JSON](../reports/data-foundation/gold-bank-2025-expanded-v5-evidence.json)
- [Kết luận chất lượng cơ sở dữ liệu](../reports/data-foundation/database-quality-verdict.md)

Tóm tắt: 80 ô mục tiêu, 76 ô hợp lệ, 4 ô thiếu rõ ràng, 76/76 ô hợp lệ có
bằng chứng theo trang đã được rà soát. SQLite là tài liệu dữ liệu; báo cáo
không tự sửa bản chụp.

## 3. Đánh giá và kết quả

- [Báo cáo đánh giá cuối dạng Markdown](../reports/analysis-report-v2-final-evaluation-gold-v5-20260909-v4/final-evaluation.md)
- [Báo cáo đánh giá cuối dạng JSON](../reports/analysis-report-v2-final-evaluation-gold-v5-20260909-v4/final-evaluation.json)
- [Tổng hợp chất lượng/chi phí/độ trễ](../reports/analysis-report-v2-human-review-gold-v5-20260909-aggregate-v2/aggregate.md)
- [Tóm tắt vận hành](../reports/analysis-report-v2-operational-gold-v5-20260909/operational-summary.md)
- [Kế hoạch 75 lượt chạy](../experiments/runs/analysis-report-v2-scaling-5issuer-plan-gold-v5.json)
- [Hàng đợi chấm mù đã kiểm tra](../reports/analysis-report-v2-human-review-gold-v5-20260909/human-review-queue.csv)

Kết quả chính: đa tác tử phân cấp không phản biện có điểm chuyển lợi thế đầu
tiên ở 3 ngân hàng, chất lượng tăng +0,05, nhưng chi phí và độ trễ tăng; 14/75
lượt chạy thất bại được giữ nguyên trong báo cáo.

## 4. Báo cáo và giao diện trình diễn

- [Báo cáo JSON dùng cho giao diện](../legacy/frozen-report-viewer/data/analysis-report.json)
- [Giao diện báo cáo lịch sử](../legacy/frozen-report-viewer/index.html)
- [Bảng chấm mù](../research/evaluation-ui/review.html)
- [Hướng dẫn giao diện lịch sử](../legacy/frozen-report-viewer/README.md)
- [Kịch bản trình diễn 5 phút](ADVISOR-DEMO-SCRIPT-VI.md)
- [Bản trình chiếu PowerPoint 7 trang](../reports/advisor-package-2026-09-10/final/advisor-deck-v3.pptx)

Giao diện xem trước chạy cục bộ bằng:

```powershell
python -m http.server 8765 --directory legacy/frozen-report-viewer
```

Sau đó mở `http://127.0.0.1:8765/`.

## 5. Kiểm thử và tái lập

Lệnh regression:

```powershell
$env:PYTHONPATH='src'
python -m unittest discover -s tests -q
```

Kết quả đóng gói gần nhất: `329 tests ... OK`.

Báo cáo cuối được tạo từ tài liệu có phiên bản, không chứa API key hay thông tin
xác thực. Chi phí là số liệu vận hành/ước tính của lượt chạy mô hình tại thời
điểm thực hiện.

## 6. Hạng mục chưa nên trình bày là đã hoàn thành

- 8 quý hoặc 200 ô ứng viên chưa phải đối sánh Gold.
- Phần mở rộng vĩ mô chưa được gộp vào kết quả tổng hợp chính.
- Chưa có triển khai thực tế, luồng dữ liệu thời gian thực hoặc thực thi đầu tư.
- Không tuyên bố đa tác tử luôn vượt trội trong mọi trường hợp.
