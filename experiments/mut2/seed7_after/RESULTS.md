# Verifier Mutation Testing Evaluation Report (mut1)

## 1. Control Verification

- **Total accepted sentences evaluated:** 129
- **Passed unchanged:** 129 (100.0%)
- **Failed controls:** 0

## 2. Overall Mutation Catch Rates

| Operator | n | Caught | Catch Rate | Wilson 95% CI |
| :--- | :---: | :---: | :---: | :---: |
| `number_small` | 96 | 95 | 99.0% (0.9896) | [0.9433, 0.9982] |
| `number_large` | 96 | 96 | 100.0% (1.0000) | [0.9615, 1.0000] |
| `digit_swap` | 96 | 96 | 100.0% (1.0000) | [0.9615, 1.0000] |
| `rank` | 46 | 41 | 89.1% (0.8913) | [0.7696, 0.9527] |
| `denominator` | 52 | 52 | 100.0% (1.0000) | [0.9312, 1.0000] |
| `period` | 118 | 114 | 96.6% (0.9661) | [0.9161, 0.9867] |
| `entity_swap` | 123 | 123 | 100.0% (1.0000) | [0.9697, 1.0000] |
| `direction_flip` | 76 | 73 | 96.0% (0.9605) | [0.8903, 0.9865] |
| `metric_swap` | 120 | 119 | 99.2% (0.9917) | [0.9543, 0.9985] |
| `unsupported_number` | 129 | 129 | 100.0% (1.0000) | [0.9711, 1.0000] |
| `causal_claim` | 129 | 129 | 100.0% (1.0000) | [0.9711, 1.0000] |
| `recommendation` | 129 | 129 | 100.0% (1.0000) | [0.9711, 1.0000] |

## 3. Catch Rates by Evaluation Arm

| Operator | Arm A (`single_agent`) | Arm B (`hierarchical_no_critique`) | Arm C (`hierarchical_with_critique`) |
| :--- | :---: | :---: | :---: |
| `number_small` | 34/34 (100.0%) | 32/32 (100.0%) | 29/30 (96.7%) |
| `number_large` | 34/34 (100.0%) | 32/32 (100.0%) | 30/30 (100.0%) |
| `digit_swap` | 34/34 (100.0%) | 32/32 (100.0%) | 30/30 (100.0%) |
| `rank` | 11/11 (100.0%) | 15/17 (88.2%) | 15/18 (83.3%) |
| `denominator` | 13/13 (100.0%) | 19/19 (100.0%) | 20/20 (100.0%) |
| `period` | 41/41 (100.0%) | 40/43 (93.0%) | 33/34 (97.1%) |
| `entity_swap` | 42/42 (100.0%) | 42/42 (100.0%) | 39/39 (100.0%) |
| `direction_flip` | 26/27 (96.3%) | 24/25 (96.0%) | 23/24 (95.8%) |
| `metric_swap` | 41/41 (100.0%) | 41/42 (97.6%) | 37/37 (100.0%) |
| `unsupported_number` | 44/44 (100.0%) | 44/44 (100.0%) | 41/41 (100.0%) |
| `causal_claim` | 44/44 (100.0%) | 44/44 (100.0%) | 41/41 (100.0%) |
| `recommendation` | 44/44 (100.0%) | 44/44 (100.0%) | 41/41 (100.0%) |

## 4. Escaped Mutants Analysis

Examples of mutants that escaped verification (verifier returned `ok=True`), per operator:

### `number_small`: 1 escapes (Catch rate: 99.0%)

**Example 1:** (`er9-T09-hierarchical_with_critique-r0` / `sent-company-1`)
- **Original:** MBB có ROE 21,1% cao hơn TCB ở mức 15,5%, chênh lệch +5,5 điểm %.
- **Mutant:** MBB có ROE 21,1% cao hơn TCB ở mức 15,5%, chênh lệch +5,6 điểm %.

### `number_large`: 0 escapes (100% caught)

### `digit_swap`: 0 escapes (100% caught)

### `rank`: 5 escapes (Catch rate: 89.1%)

**Example 1:** (`er9-T02-hierarchical_no_critique-r0` / `sent-company-1`)
- **Original:** STB đạt tỷ lệ nợ xấu 6,41% (hạng 10/10), cao hơn trung vị nhóm trong quý 4/2025.
- **Mutant:** STB đạt tỷ lệ nợ xấu 6,41% (hạng 1/10), cao hơn trung vị nhóm trong quý 4/2025.

**Example 2:** (`er9-T06-hierarchical_with_critique-r0` / `sent-sector-1`)
- **Original:** VCB có tỷ lệ nợ xấu thấp nhất nhóm với 0,61% (hạng 1/10) trong quý 2/2026.
- **Mutant:** VCB có tỷ lệ nợ xấu thấp nhất nhóm với 0,61% (hạng 10/10) trong quý 2/2026.

**Example 3:** (`er9-T08-hierarchical_with_critique-r0` / `sent-company-2`)
- **Original:** Tỷ lệ nợ xấu của VPB cao hơn trung vị nhóm, ở mức 3,46% (hạng 9/10) trong quý 4/2025.
- **Mutant:** Tỷ lệ nợ xấu của VPB cao hơn trung vị nhóm, ở mức 3,46% (hạng 2/10) trong quý 4/2025.

### `denominator`: 0 escapes (100% caught)

### `period`: 4 escapes (Catch rate: 96.6%)

**Example 1:** (`er9-T01-hierarchical_no_critique-r0` / `sent-company-4`)
- **Original:** ROE của BID đi ngang ở mức 17,9% (hạng 4/10), ngang trung vị nhóm trong quý 2/2026.
- **Mutant:** ROE của BID đi ngang ở mức 17,9% (hạng 4/10), ngang trung vị nhóm trong quý 1/2026.

**Example 2:** (`er9-T04-hierarchical_no_critique-r0` / `sent-company-1`)
- **Original:** Tỷ lệ nợ xấu của CTG giảm liên tục từ quý 1/2025 đến quý 3/2025, đạt 1,10% trong quý 4/2025.
- **Mutant:** Tỷ lệ nợ xấu của CTG giảm liên tục từ quý 1/2025 đến quý 3/2025, đạt 1,10% trong quý 3/2025.

**Example 3:** (`er9-T04-hierarchical_no_critique-r0` / `sent-company-4`)
- **Original:** Tỷ lệ bao phủ nợ xấu của CTG cao hơn trung vị nhóm xuyên suốt năm 2025, xếp hạng 2/10 về tỷ lệ bao phủ nợ xấu trong quý 4/2025.
- **Mutant:** Tỷ lệ bao phủ nợ xấu của CTG cao hơn trung vị nhóm xuyên suốt năm 2025, xếp hạng 2/10 về tỷ lệ bao phủ nợ xấu trong quý 3/2025.

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
