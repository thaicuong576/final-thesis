# Domain Invariants & Financial Metric Formulas

> **Tài liệu nền tảng cấp cao nhất (Spec Zero - Part 2)**  
> **Trạng thái**: Đóng băng (Frozen Foundation)  
> **Nguyên tắc tối thượng**: Code Python thuần tính toán số học; LLM chỉ truy xuất, giải thích, phản biện và tổng hợp.

---

## 1. KHUNG CHỈ SỐ CAMEL CHO NGÂN HÀNG THƯƠNG MẠI VIỆT NAM

Hệ thống khóa cứng (freeze) toàn bộ định nghĩa, mã trường (`field_code`), công thức toán học và cơ sở kỳ tính toán cho 5 trụ cột CAMEL:

```
                  ┌─────────────────────────────────────────┐
                  │             KHUNG CHỈ SỐ CAMEL          │
                  └────────────────────┬────────────────────┘
          ┌───────────────┬────────────┼────────────┬───────────────┐
          ▼               ▼            ▼            ▼               ▼
     [C] CAPITAL    [A] ASSET     [M] MANAG.   [E] EARNINGS    [L] LIQUIDITY
       - CAR          - NPL         - CIR        - ROE (TTM)     - LDR
                      - LLC/LLR                  - ROA (TTM)     - CASA
                                                 - NIM
```

---

### C - Capital Adequacy (An toàn vốn)
- **Chỉ số**: Hệ số an toàn vốn CAR (`bank.car` / `car`).
- **Khung pháp lý**: Thông tư 41/2016/TT-NHNN (áp dụng chuẩn Basel II) và Thông tư 22/2019/TT-NHNN.
- **Quy tắc tính toán**:
  - CAR trong hệ thống sử dụng **số liệu do ngân hàng tự công bố chính thức** trên Báo cáo tài chính kiểm toán hoặc Báo cáo thường niên (`bank.car_disclosed`).
  - **Bất biến**: Không tự ý phái sinh hoặc tái tạo CAR từ bảng cân đối kế toán tổng hợp trong MVP, vì việc tính toán tài sản có trọng số rủi ro (RWA - Risk Weighted Assets) đòi hỏi thông tin thuyết minh chi tiết về từng nhóm tài sản rủi ro và các cam kết ngoại bảng.

---

### A - Asset Quality (Chất lượng tài sản)
- **Chỉ số 1: Tỷ lệ Nợ xấu Nhóm 3–5 (`bank.npl_g35` / `npl`)**
  - **Ý nghĩa**: Phản ánh tỷ lệ các khoản nợ xấu có nguy cơ mất vốn trên tổng quy mô danh mục cho vay.
  - **Khung phân loại nợ**: Thông tư 11/2021/TT-NHNN (Nợ nhóm 3: Nợ dưới tiêu chuẩn; Nhóm 4: Nợ nghi ngờ; Nhóm 5: Nợ có khả năng mất vốn).
  - **Công thức**:
    $$\text{NPL Ratio (\%)} = \frac{\text{Nợ nhóm 3} + \text{Nợ nhóm 4} + \text{Nợ nhóm 5}}{\text{Tổng dư nợ cho vay khách hàng}} \times 100$$
    `formula_version: "npl-g35-v1"`
  - **Cơ sở kỳ tính toán**: Thời điểm (`point_in_time`) tại ngày kết thúc kỳ báo cáo.

- **Chỉ số 2: Tỷ lệ Bao phủ Nợ xấu LLC / LLR (`bank.llr_coverage` / `loansLossReservesToNPLs`)**
  - **Ý nghĩa**: Đệm dự phòng tài chính của ngân hàng sẵn sàng bù đắp tổn thất khi các khoản nợ xấu phát sinh rủi ro.
  - **Công thức**:
    $$\text{LLR / LLC (\%)} = \frac{\text{Số dư dự phòng rủi ro cho vay khách hàng}}{\text{Tổng số dư nợ xấu nhóm 3–5}} \times 100$$
    `formula_version: "llr-coverage-v1"`
  - **Cơ sở kỳ tính toán**: Thời điểm (`point_in_time`).
  - **Bất biến**: Mẫu số là tổng dư nợ nhóm 3–5. Dự phòng bao gồm cả dự phòng cụ thể và dự phòng chung trích lập cho vay khách hàng.

---

### M - Management Efficiency (Hiệu quả quản trị)
- **Chỉ số: Tỷ lệ Chi phí trên Thu nhập CIR (`bank.cir` / `costToIncome`)**
  - **Ý nghĩa**: Đo lường hiệu quả quản lý chi phí vận hành để tạo ra một đồng thu nhập hoạt động.
  - **Công thức**:
    $$\text{CIR (\%)} = \frac{\text{Tổng chi phí hoạt động (Operating Expenses)}}{\text{Tổng thu nhập hoạt động (Total Operating Income - TOI)}} \times 100$$
    `formula_version: "cir-v1"`
  - Trong đó:
    $$\text{TOI} = \text{Thu nhập lãi thuần} + \text{Thu nhập ngoài lãi thuần}$$
  - **Bất biến dấu và dữ liệu**:
    - Chi phí hoạt động trên BCTC thường được trình bày dạng số âm (hoặc nằm trong ngoặc đơn). Hàm tính toán **bắt buộc phải lấy trị tuyệt đối hoặc chuyển về giá trị dương** trước khi chia.
    - Nếu TOI $\le 0$, tỷ lệ CIR không còn ý nghĩa kinh tế và phải trả về `None` kèm lý do phù hợp.

---

### E - Earnings Quality (Khả năng sinh lời)
- **Chỉ số 1: Tỷ suất sinh lời trên Vốn chủ sở hữu ROE TTM (`bank.roe` / `roe`)**
  - **Ý nghĩa**: Khả năng tạo ra lợi nhuận cho cổ đông từ nguồn vốn chủ sở hữu.
  - **Công ước chuẩn luận văn (Parent-Attributable Convention)**:
    $$\text{ROE TTM (\%)} = \frac{\text{LNST thuộc về cổ đông ngân hàng mẹ (TTM)}}{\text{Vốn chủ sở hữu bình quân}} \times 100$$
    `formula_version: "roe-ttm-v1"`
  - **Dòng lợi nhuận 4 quý gần nhất (TTM Flow)**:
    $$\text{Profit}_{\text{TTM}} = \text{Profit}_{\text{Prior\_FY}} - \text{Profit}_{\text{Prior\_YTD}} + \text{Profit}_{\text{Current\_YTD}}$$
  - **Vốn chủ sở hữu bình quân**:
    $$\text{Average Equity} = \frac{\text{Vốn CSH đầu kỳ} + \text{Vốn CSH cuối kỳ}}{2}$$
    *(Vốn CSH trừ đi lợi ích cổ đông không kiểm soát NCI nếu có).*

- **Chỉ số 2: Tỷ suất sinh lời trên Tổng tài sản ROA TTM (`bank.roa` / `roa`)**
  - **Ý nghĩa**: Hiệu quả phân bổ và sử dụng tổng tài sản của ngân hàng.
  - **Công thức**:
    $$\text{ROA TTM (\%)} = \frac{\text{Tổng LNST hợp nhất (TTM)}}{\text{Tổng tài sản bình quân}} \times 100$$
    `formula_version: "roa-ttm-v1"`

- **Chỉ số 3: Biên lãi thuần NIM (`bank.nim` / `netInterestMargin`)**
  - **Ý nghĩa**: Chênh lệch giữa thu nhập lãi thu được từ tài sản sinh lời và chi phí lãi phải trả cho nguồn vốn huy động.
  - **Công thức**:
    $$\text{NIM (\%)} = \frac{\text{Thu nhập lãi thuần (NII TTM)}}{\text{Tổng tài sản sinh lời bình quân (Average Earning Assets)}} \times 100$$
  - **Danh mục Tài sản sinh lời (Earning Assets)** bao gồm:
    1. Tiền gửi tại Ngân hàng Nhà nước.
    2. Tiền gửi tại các TCTD khác và cho vay các TCTD khác.
    3. Chứng khoán kinh doanh và chứng khoán đầu tư.
    4. Cho vay khách hàng.

---

### L - Liquidity (Thanh khoản)
- **Chỉ số 1: Tỷ lệ Cho vay trên Huy động LDR (`bank.ldr_simple` / `ldrLoanDepositRatio`)**
  - **Ý nghĩa**: Đánh giá mức độ sử dụng nguồn vốn huy động từ khách hàng để cấp tín dụng.
  - **Công thức phân tích**:
    $$\text{LDR Simple (\%)} = \frac{\text{Cho vay khách hàng (Gross Loans)}}{\text{Tiền gửi của khách hàng (Customer Deposits)}} \times 100$$
  - **Lưu ý**: Đây là LDR phân tích thuần túy trên báo cáo tài chính, khác với LDR theo quy định tại Thông tư 22/2019/TT-NHNN (quy định của NHNN cho phép cộng thêm giấy tờ có giá vào mẫu số).

- **Chỉ số 2: Tỷ lệ Tiền gửi Không kỳ hạn CASA (`bank.casa` / `casaRatio`)**
  - **Ý nghĩa**: Tỷ trọng nguồn vốn giá rẻ giúp ngân hàng tối ưu hóa chi phí vốn (COF).
  - **Công thức**:
    $$\text{CASA Ratio (\%)} = \frac{\text{Tiền gửi không kỳ hạn (Demand Deposits)}}{\text{Tổng tiền gửi của khách hàng}} \times 100$$

---

## 2. CÁC BẤT BIẾN SỐ HỌC (ARITHMETIC INVARIANTS)

Để bảo đảm tính ổn định tuyệt đối của hệ thống, mọi hàm tính toán trong `src/thesis_data/metrics.py` bắt buộc tuân theo 4 bất biến:

### 2.1. Hàm chia an toàn (`safe_div` / `_ratio`)
Không bao giờ để xảy ra ngoại lệ `ZeroDivisionError` hay trả về giá trị vô lý (`inf`, `NaN`).
```python
def _ratio(numerator: Number, denominator: Number, *, formula_version: str, period_basis: str) -> MetricResult:
    # 1. Null handling: Nếu 1 trong 2 toán hạng là None -> trả về MISSING kèm lý do
    if numerator is None or denominator is None:
        return MetricResult(
            value=None,
            unit="%",
            quality_status=QualityStatus.MISSING,
            reason="missing_input",
            formula_version=formula_version,
            period_basis=period_basis,
        )
    
    # 2. Zero denominator handling: Mẫu số <= 0
    if denominator <= 0:
        return MetricResult(
            value=None,
            unit="%",
            quality_status=QualityStatus.MISSING,
            reason="zero_denominator",
            formula_version=formula_version,
            period_basis=period_basis,
        )
        
    # 3. Tính toán chính xác bằng Decimal, nhân 100 cho tỷ lệ phần trăm
    return MetricResult(
        value=(Decimal(str(numerator)) / Decimal(str(denominator))) * Decimal("100"),
        unit="%",
        quality_status=QualityStatus.VALID,
        reason=None,
        formula_version=formula_version,
        period_basis=period_basis,
    )
```

### 2.2. Chuẩn hóa Đơn vị (Unit Normalization)
- **Tỷ lệ / Phần trăm**: Luôn chuẩn hóa về thang đo phần trăm `%` với giá trị hiển thị tự nhiên.
  - Ví dụ: `0.0125` (dạng thập phân vendor) $\rightarrow$ chuẩn hóa thành `1.25%`.
  - Không bao giờ lưu trữ lẫn lộn số thập phân và phần trăm trong cùng cột `value`.
- **Giá trị tiền tệ**:
  - Toàn bộ giá trị tiền tệ trong tầng chuẩn hóa và báo cáo được quy đổi thống nhất về **Tỷ VNĐ (VND Billion)**.
  - Từ Triệu đồng $\rightarrow$ Tỷ đồng: chia `1,000`.
  - Từ Đồng $\rightarrow$ Tỷ đồng: chia `1,000,000,000`.

### 2.3. Tính toán Dòng tiền Quý đơn lẻ (YTD to Quarter Flow)
- Các BCTC quý của Việt Nam công bố số liệu kết quả kinh doanh theo lũy kế từ đầu năm tài chính (YTD).
- Dòng tiền quý đơn lẻ trong năm:
  $$\text{Quarter Flow} = \text{Current YTD} - \text{Prior Quarter YTD}$$
- **Bất biến nghiêm ngặt**:
  - **CẤM** thực hiện phép trừ xuyên năm tài chính (`cross_fiscal_year_subtraction`). Quý 1 năm $T$ chính là lũy kế YTD của Quý 1, không được lấy trừ đi Quý 4 năm $T-1$.

### 2.4. Tính toán Trung vị Ngành (Peer Median Invariant)
- Khi tính trung vị ngành (`sector.peer_median`):
  - Tự động lọc bỏ các giá trị `None` / `MISSING`.
  - Nếu toàn bộ danh sách trong nhóm đối thủ đều là `None` $\rightarrow$ Trả về `value: None`, `quality_status: MISSING`, `reason: "all_values_missing"`.
  - Không thay thế giá trị thiếu bằng số 0 vì số 0 sẽ làm lệch nghiêm trọng phân vị trung vị ngành.

### 2.5. Phạm vi nhóm so sánh và mẫu số thực tế

- `requested_peer_entity_ids` ràng buộc định danh benchmark và phạm vi claim.
- `eligible_peer_entity_ids` và `input_observation_ids` ràng buộc các giá trị
  thực sự tham gia phép tính; mỗi thành viên bị loại phải có lý do cụ thể.
- Chỉ công bố median khi unit, period basis và reporting scope đã xác minh
  cùng tương thích và khác null. Không suy diễn scope từ tên tài liệu.
- Nhóm năm ngân hàng là case study; không mặc định đại diện toàn ngành.
