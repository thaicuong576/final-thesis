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
| `period` | 118 | 101 | 85.6% (0.8559) | [0.7814, 0.9081] |
| `entity_swap` | 123 | 105 | 85.4% (0.8537) | [0.7805, 0.9054] |
| `direction_flip` | 76 | 67 | 88.2% (0.8816) | [0.7900, 0.9364] |
| `metric_swap` | 120 | 95 | 79.2% (0.7917) | [0.7105, 0.8547] |
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
| `period` | 36/41 (87.8%) | 37/43 (86.1%) | 28/34 (82.3%) |
| `entity_swap` | 35/42 (83.3%) | 35/42 (83.3%) | 35/39 (89.7%) |
| `direction_flip` | 24/27 (88.9%) | 22/25 (88.0%) | 21/24 (87.5%) |
| `metric_swap` | 34/41 (82.9%) | 32/42 (76.2%) | 29/37 (78.4%) |
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

### `period`: 17 escapes (Catch rate: 85.6%)

**Example 1:** (`er9-T01-hierarchical_no_critique-r0` / `sent-company-4`)
- **Original:** ROE của BID đi ngang ở mức 17,9% (hạng 4/10), ngang trung vị nhóm trong quý 2/2026.
- **Mutant:** ROE của BID đi ngang ở mức 17,9% (hạng 4/10), ngang trung vị nhóm trong quý 1/2026.

**Example 2:** (`er9-T01-hierarchical_no_critique-r0` / `sent-fb-7`)
- **Original:** Tỷ lệ bao phủ nợ xấu của BID giảm 11,0 điểm % từ quý 1/2026 đến quý 2/2026.
- **Mutant:** Tỷ lệ bao phủ nợ xấu của BID giảm 11,0 điểm % từ quý 1/2026 đến quý 1/2026.

**Example 3:** (`er9-T01-hierarchical_with_critique-r0` / `sent-fb-7`)
- **Original:** Tỷ lệ bao phủ nợ xấu của BID giảm 11,0 điểm % từ quý 1/2026 đến quý 2/2026.
- **Mutant:** Tỷ lệ bao phủ nợ xấu của BID giảm 11,0 điểm % từ quý 2/2026 đến quý 2/2026.

### `entity_swap`: 18 escapes (Catch rate: 85.4%)

**Example 1:** (`er9-T09-hierarchical_no_critique-r0` / `sent-company-1`)
- **Original:** TCB vượt trội MBB ở ROA và tỷ lệ bao phủ nợ xấu trong quý 2/2026.
- **Mutant:** TCB vượt trội TCB ở ROA và tỷ lệ bao phủ nợ xấu trong quý 2/2026.

**Example 2:** (`er9-T09-hierarchical_no_critique-r0` / `sent-orchestrator-e8f6d1`)
- **Original:** TCB dẫn trước MBB ở 3/4 chỉ tiêu chính trong quý 2/2026.
- **Mutant:** MBB dẫn trước MBB ở 3/4 chỉ tiêu chính trong quý 2/2026.

**Example 3:** (`er9-T09-hierarchical_no_critique-r0` / `sent-fb-2`)
- **Original:** MBB có tỷ lệ bao phủ nợ xấu thấp hơn TCB 32,0 điểm % trong quý 2/2026.
- **Mutant:** TCB có tỷ lệ bao phủ nợ xấu thấp hơn TCB 32,0 điểm % trong quý 2/2026.

### `direction_flip`: 9 escapes (Catch rate: 88.2%)

**Example 1:** (`er9-T04-hierarchical_with_critique-r0` / `sent-company-2`)
- **Original:** Tỷ lệ bao phủ nợ xấu của CTG giảm trong quý 4/2025, ngược chiều trung vị nhóm tăng.
- **Mutant:** Tỷ lệ bao phủ nợ xấu của CTG giảm trong quý 4/2025, ngược chiều trung vị nhóm giảm.

**Example 2:** (`er9-T06-hierarchical_no_critique-r0` / `sent-fb-2`)
- **Original:** Chênh lệch cao nhất – thấp nhất về tỷ lệ nợ xấu của nhóm 10 ngân hàng là 6,93 điểm % trong quý 2/2026.
- **Mutant:** Chênh lệch thấp nhất – thấp nhất về tỷ lệ nợ xấu của nhóm 10 ngân hàng là 6,93 điểm % trong quý 2/2026.

**Example 3:** (`er9-T06-hierarchical_with_critique-r0` / `sent-fb-2`)
- **Original:** Chênh lệch cao nhất – thấp nhất về tỷ lệ nợ xấu của nhóm 10 ngân hàng là 6,93 điểm % trong quý 2/2026.
- **Mutant:** Chênh lệch thấp nhất – thấp nhất về tỷ lệ nợ xấu của nhóm 10 ngân hàng là 6,93 điểm % trong quý 2/2026.

### `metric_swap`: 25 escapes (Catch rate: 79.2%)

**Example 1:** (`er9-T02-hierarchical_no_critique-r0` / `sent-fb-7`)
- **Original:** Tỷ lệ bao phủ nợ xấu của STB đi ngang từ quý 1/2025 đến quý 2/2025.
- **Mutant:** Tỷ lệ nợ xấu của STB đi ngang từ quý 1/2025 đến quý 2/2025.

**Example 2:** (`er9-T02-hierarchical_with_critique-r0` / `sent-fb-7`)
- **Original:** Tỷ lệ bao phủ nợ xấu của STB đi ngang từ quý 1/2025 đến quý 2/2025.
- **Mutant:** Tỷ lệ nợ xấu của STB đi ngang từ quý 1/2025 đến quý 2/2025.

**Example 3:** (`er9-T02-single_agent-r0` / `sent-fb-7`)
- **Original:** Tỷ lệ bao phủ nợ xấu của STB đi ngang từ quý 1/2025 đến quý 2/2025.
- **Mutant:** Tỷ lệ nợ xấu của STB đi ngang từ quý 1/2025 đến quý 2/2025.

### `unsupported_number`: 0 escapes (100% caught)

### `causal_claim`: 0 escapes (100% caught)

### `recommendation`: 0 escapes (100% caught)
