# INGEST-1 Evaluation Results

**Run date**: 2026-10-16 16:51 SE Asia Standard Time  
**Dataset**: 10 audited FY2025 consolidated annual bank filings  
**Ground truth**: `data/onboarding/top10-2025/<TICKER>-2025q4.csv`  
**Pipeline**: PyMuPDF text-layer detection + Tesseract OCR (when no text layer)  

## Overall Accuracy

| Metric | Count |
|--------|-------|
| Cells evaluated (in ground truth) | 150 |
| **Correct** (within ±0.01 tỷ) | **6** |
| Wrong value | 97 |
| Missing (row not found) | 47 |
| **Accuracy** | **4.0%** |

## Per-Bank Results

| Bank | Pages | Text-layer | OCR | OCR time | Unit | Correct | Wrong | Missing | Accuracy |
|------|-------|-----------|-----|----------|------|---------|-------|---------|----------|
| ACB | 100 | 1 | 99 | 0.6s | vnd | 2 | 12 | 1 | 13% |
| BID | 74 | 2 | 72 | 40.5s | vnd | 0 | 13 | 2 | 0% |
| CTG | 85 | 0 | 85 | 55.7s | vnd | 0 | 13 | 2 | 0% |
| HDB | 71 | 2 | 69 | 36.3s | vnd | 0 | 9 | 6 | 0% |
| MBB | 103 | 2 | 101 | 64.8s | vnd | 0 | 15 | 0 | 0% |
| SHB | 68 | 0 | 68 | 35.0s | vnd | 2 | 0 | 13 | 13% |
| STB | 108 | 0 | 108 | 49.2s | vnd | 2 | 4 | 9 | 13% |
| TCB | 104 | 0 | 104 | 62.8s | vnd | 0 | 9 | 6 | 0% |
| VCB | 84 | 0 | 84 | 50.0s | vnd | 0 | 14 | 1 | 0% |
| VPB | 100 | 1 | 99 | 61.4s | vnd | 0 | 8 | 7 | 0% |

## Error Analysis (by issue code)

| Issue Code | Occurrences |
|-----------|------------|
| `row_not_found` | 47 |
| `period_mismatch` | 40 |
| `prior_column_unconfirmed` | 9 |
| `parent_profit_inferred_from_pat` | 6 |
| `low_confidence_match` | 6 |
| `target_column_unconfirmed` | 2 |
| `nci_not_presented` | 2 |

## Notes

- **Correct**: extracted value matches ground truth within ±0.01 billion VND.
- **Wrong value**: row label was found but extracted number does not match ground truth.
- **Missing**: extraction pipeline did not find a matching row at all.
- Ground truth covers 10 metrics × 2 periods per bank = up to 200 cells; some banks have 0 NCI so fewer cells.
- This is honest experimental evidence for the thesis. No bank-specific rule tuning was applied.
- See `experiments/ingest/rows.json` for full row-level detail.
