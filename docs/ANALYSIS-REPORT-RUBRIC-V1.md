# Rubric cho report phân tích v1

Report v2 được đánh giá như một sản phẩm phân tích, không chỉ như một bảng
metric có provenance.

## Các chiều đánh giá

| Chiều | Câu hỏi kiểm tra | Đạt khi |
|---|---|---|
| Claim correctness | Claim có đúng với Gold và data refs không? | Không sai ticker, kỳ, metric, ranking hoặc delta |
| Evidence support | Người đọc có lần được claim về đúng nguồn/trang/quote không? | `evidence_backed`, hoặc `source_locator_only` được ghi đúng và không giả làm quote |
| Interpretation | Claim có trả lời “vậy thì sao?” trong đúng scope không? | Có ý nghĩa phân tích, không chỉ lặp lại con số |
| Limitation | Report có nói khi nào không được kết luận không? | Mỗi claim có limitation; missing/conflict được nêu rõ |
| Coverage discipline | Report có xử lý thiếu dữ liệu đúng không? | Không đoán, không zero-fill, không dùng ô pending |
| User usefulness | Người đọc có biết nên chú ý điểm nào không? | Có kết luận nhanh, so sánh, hồ sơ từng ngân hàng và điểm theo dõi |
| Operational efficiency | Chất lượng đạt được với chi phí nào? | Ghi tokens, cost, latency, timeout và failure |

## So sánh single-agent và multi-agent

Mỗi arm phải chạy cùng:

- Gold snapshot;
- question set và scope;
- `analysis-report-v2`;
- rubric và human-review protocol.

Các metric output cần lưu:

```text
claim_correctness_rate
evidence_backed_claim_rate
source_locator_only_rate
interpretation_score
limitation_score
missing_data_discipline_rate
contract_failure_rate
input_tokens
output_tokens
cost_estimate_usd
latency_ms
timeout_rate
```

`claim_origin=deterministic_reference` chỉ là reference report để kiểm tra
pipeline và tạo expected analysis. Nó không được dùng để kết luận model arm
nào tốt hơn. Benchmark chất lượng thật phải dùng `claim_origin=model`, với
claim do arm đó sinh ra và được review mù.

## Không được kết luận quá mức

- Nhiều claim hơn không đồng nghĩa report tốt hơn.
- Có source ID không đồng nghĩa claim đã có evidence.
- Chi phí cao hơn không đồng nghĩa chất lượng cao hơn.
- Một workload 5 ngân hàng không chứng minh quy luật asymptotic.
- Crossover chỉ được gọi khi lợi ích chất lượng vượt chi phí theo ngưỡng đã
  định trước và lặp lại ở các workload/tier phù hợp.

