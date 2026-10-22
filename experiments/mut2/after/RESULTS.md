# Verifier Mutation Testing Evaluation Report (mut1)

## 1. Control Verification

- **Total accepted sentences evaluated:** 129
- **Passed unchanged:** 129 (100.0%)
- **Failed controls:** 0

## 2. Overall Mutation Catch Rates

| Operator | n | Caught | Catch Rate | Wilson 95% CI |
| :--- | :---: | :---: | :---: | :---: |
| `number_small` | 96 | 96 | 100.0% (1.0000) | [0.9615, 1.0000] |
| `number_large` | 96 | 96 | 100.0% (1.0000) | [0.9615, 1.0000] |
| `digit_swap` | 96 | 96 | 100.0% (1.0000) | [0.9615, 1.0000] |
| `rank` | 46 | 46 | 100.0% (1.0000) | [0.9229, 1.0000] |
| `denominator` | 52 | 52 | 100.0% (1.0000) | [0.9312, 1.0000] |
| `period` | 118 | 112 | 94.9% (0.9492) | [0.8935, 0.9765] |
| `entity_swap` | 123 | 123 | 100.0% (1.0000) | [0.9697, 1.0000] |
| `direction_flip` | 76 | 73 | 96.0% (0.9605) | [0.8903, 0.9865] |
| `metric_swap` | 120 | 119 | 99.2% (0.9917) | [0.9543, 0.9985] |
| `unsupported_number` | 129 | 129 | 100.0% (1.0000) | [0.9711, 1.0000] |
| `causal_claim` | 129 | 129 | 100.0% (1.0000) | [0.9711, 1.0000] |
| `recommendation` | 129 | 129 | 100.0% (1.0000) | [0.9711, 1.0000] |

## 3. Catch Rates by Evaluation Arm

| Operator | Arm A (`single_agent`) | Arm B (`hierarchical_no_critique`) | Arm C (`hierarchical_with_critique`) |
| :--- | :---: | :---: | :---: |
| `number_small` | 34/34 (100.0%) | 32/32 (100.0%) | 30/30 (100.0%) |
| `number_large` | 34/34 (100.0%) | 32/32 (100.0%) | 30/30 (100.0%) |
| `digit_swap` | 34/34 (100.0%) | 32/32 (100.0%) | 30/30 (100.0%) |
| `rank` | 11/11 (100.0%) | 17/17 (100.0%) | 18/18 (100.0%) |
| `denominator` | 13/13 (100.0%) | 19/19 (100.0%) | 20/20 (100.0%) |
| `period` | 39/41 (95.1%) | 40/43 (93.0%) | 33/34 (97.1%) |
| `entity_swap` | 42/42 (100.0%) | 42/42 (100.0%) | 39/39 (100.0%) |
| `direction_flip` | 26/27 (96.3%) | 24/25 (96.0%) | 23/24 (95.8%) |
| `metric_swap` | 41/41 (100.0%) | 41/42 (97.6%) | 37/37 (100.0%) |
| `unsupported_number` | 44/44 (100.0%) | 44/44 (100.0%) | 41/41 (100.0%) |
| `causal_claim` | 44/44 (100.0%) | 44/44 (100.0%) | 41/41 (100.0%) |
| `recommendation` | 44/44 (100.0%) | 44/44 (100.0%) | 41/41 (100.0%) |

## 4. Escaped Mutants Analysis

Examples of mutants that escaped verification (verifier returned `ok=True`), per operator:

### `number_small`: 0 escapes (100% caught)

### `number_large`: 0 escapes (100% caught)

### `digit_swap`: 0 escapes (100% caught)

### `rank`: 0 escapes (100% caught)

### `denominator`: 0 escapes (100% caught)

### `period`: 6 escapes (Catch rate: 94.9%)

**Example 1:** (`er9-T01-hierarchical_no_critique-r0` / `sent-company-4`)
- **Original:** ROE của BID đi ngang ở mức 17,9% (hạng 4/10), ngang trung vị nhóm trong quý 2/2026.
- **Mutant:** ROE của BID đi ngang ở mức 17,9% (hạng 4/10), ngang trung vị nhóm trong quý 1/2026.

**Example 2:** (`er9-T04-hierarchical_no_critique-r0` / `sent-company-1`)
- **Original:** Tỷ lệ nợ xấu của CTG giảm liên tục từ quý 1/2025 đến quý 3/2025, đạt 1,10% trong quý 4/2025.
- **Mutant:** Tỷ lệ nợ xấu của CTG giảm liên tục từ quý 1/2025 đến quý 4/2025, đạt 1,10% trong quý 4/2025.

**Example 3:** (`er9-T04-hierarchical_no_critique-r0` / `sent-company-4`)
- **Original:** Tỷ lệ bao phủ nợ xấu của CTG cao hơn trung vị nhóm xuyên suốt năm 2025, xếp hạng 2/10 về tỷ lệ bao phủ nợ xấu trong quý 4/2025.
- **Mutant:** Tỷ lệ bao phủ nợ xấu của CTG cao hơn trung vị nhóm xuyên suốt năm 2025, xếp hạng 2/10 về tỷ lệ bao phủ nợ xấu trong quý 2/2025.

### `entity_swap`: 0 escapes (100% caught)

### `direction_flip`: 3 escapes (Catch rate: 96.0%)

**Example 1:** (`er9-T04-hierarchical_with_critique-r0` / `sent-company-2`)
- **Original:** Tỷ lệ bao phủ nợ xấu của CTG giảm trong quý 4/2025, ngược chiều trung vị nhóm tăng.
- **Mutant:** Tỷ lệ bao phủ nợ xấu của CTG giảm trong quý 4/2025, ngược chiều trung vị nhóm giảm.

**Example 2:** (`er9-T08-hierarchical_no_critique-r0` / `sent-orchestrator-15594a`)
- **Original:** Trong năm 2025, VPB duy trì ROA cao hơn trung vị nhóm (+0,63 điểm % ở quý 4/2025) nhưng đánh đổi bằng chất lượng tài sản yếu với tỷ lệ nợ xấu cao hơn trung vị nhóm (+2,07 điểm %) và bao phủ nợ xấu thấp hơn (-42,0 điểm %).
- **Mutant:** Trong năm 2025, VPB duy trì ROA thấp hơn trung vị nhóm (+0,63 điểm % ở quý 4/2025) nhưng đánh đổi bằng chất lượng tài sản yếu với tỷ lệ nợ xấu cao hơn trung vị nhóm (+2,07 điểm %) và bao phủ nợ xấu thấp hơn (-42,0 điểm %).

**Example 3:** (`er9-T08-single_agent-r0` / `sent-orchestrator-cd0429`)
- **Original:** VPB duy trì khả năng sinh lời cao hơn trung vị nhóm (ROA quý 4/2025 đạt 2,23%) nhưng đánh đổi bằng chất lượng tài sản yếu kém (tỷ lệ bao phủ nợ xấu chỉ 54,9%, thấp hơn trung vị nhóm).
- **Mutant:** VPB duy trì khả năng sinh lời thấp hơn trung vị nhóm (ROA quý 4/2025 đạt 2,23%) nhưng đánh đổi bằng chất lượng tài sản yếu kém (tỷ lệ bao phủ nợ xấu chỉ 54,9%, thấp hơn trung vị nhóm).

### `metric_swap`: 1 escapes (Catch rate: 99.2%)

**Example 1:** (`er9-T08-hierarchical_no_critique-r0` / `sent-orchestrator-15594a`)
- **Original:** Trong năm 2025, VPB duy trì ROA cao hơn trung vị nhóm (+0,63 điểm % ở quý 4/2025) nhưng đánh đổi bằng chất lượng tài sản yếu với tỷ lệ nợ xấu cao hơn trung vị nhóm (+2,07 điểm %) và bao phủ nợ xấu thấp hơn (-42,0 điểm %).
- **Mutant:** Trong năm 2025, VPB duy trì ROA cao hơn trung vị nhóm (+0,63 điểm % ở quý 4/2025) nhưng đánh đổi bằng chất lượng tài sản yếu với tỷ lệ bao phủ nợ xấu cao hơn trung vị nhóm (+2,07 điểm %) và bao phủ nợ xấu thấp hơn (-42,0 điểm %).

### `unsupported_number`: 0 escapes (100% caught)

### `causal_claim`: 0 escapes (100% caught)

### `recommendation`: 0 escapes (100% caught)
