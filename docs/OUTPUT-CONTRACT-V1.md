# Transport output contract v1 (superseded for user-facing reports)

Contract user-facing hiện tại là [OUTPUT-CONTRACT-V2.md](OUTPUT-CONTRACT-V2.md).
File này vẫn được giữ để tương thích với `ReportView` matrix và các fixture v1;
không dùng nó làm chuẩn cuối để đánh giá giá trị của report.

Đây là contract giữa runtime và report/UI. Nó không thay thế `docs/DATA-CONTRACT.md`; nó chuyển payload kỹ thuật thành nội dung người dùng đọc được.

## Input

- Một run manifest đã hoàn tất hoặc có trạng thái `partial`.
- Một snapshot Gold đã được freeze.
- Scope trong manifest: issuer, period và metric.

## Output

`ReportView` là JSON versioned với các phần:

- `contract_version`: `report-view-v1`.
- `run`: snapshot, question, arm, model, status và telemetry.
- `scope`: issuers, periods và metrics.
- `summary`: số ô hợp lệ/thiếu, số ô có stored evidence snippet và cảnh báo.
- `matrix`: đúng một dòng cho mỗi issuer-period; mỗi metric giữ value, unit, period basis, observation, source locator và evidence.
- `analysis`: findings, anomaly classifications, missing/conflict register và quality flags từ agent.

## Invariants

1. Giá trị số trong `matrix` lấy từ Gold snapshot, không lấy lại từ prose của model.
2. Số liệu hợp lệ phải có observation, source và locator.
3. Evidence snippet phải giữ `evidence_id`, source, tài liệu, trang và quote. Số ô có snippet không được gọi là claim-level evidence completeness.
4. Missing giữ `null` và lý do; không zero-fill hoặc suy đoán.
5. Report phải nói rõ khi run là `partial`.
6. UI chỉ đọc `ReportView`, không truy cập SQLite và không tự tính metric.
