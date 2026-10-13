# E5 — How far plain page text gets you (2026-10-11, orchestrator, no model calls)

Inputs: `data/onboarding/quarterly-top10/inputs.csv` (1,123 input rows), local PDFs in
`data/raw/official/bank-quarterly-v1` (100 files; 21 with a text layer, 79 scanned),
page text from the earlier pass (`ocr_all.py` / `scripts/e5_ocr_pages.py`: text layer, else one Tesseract pass at 200 dpi, `-l eng`).
Scripts: `scripts/e5_ocr_measure.py`, `scripts/e5_naive_extract.py`, `scripts/e5_ocr_pages.py`.

> [!NOTE]
> Raw PDF filings (`data/raw/official/bank-quarterly-v1/`) and OCR page text directories (`data/processed/ocrq/`) are ignored evidence in `.gitignore` and are not committed to Git. The structured evaluation results (`experiments/e5/e5_rows.json` and `experiments/e5/e5b_rows.json`) are committed to repository tracking for deterministic verification.

## Reproduction Commands

To reproduce the measurement from scratch:

```bash
# 1. Page text extraction (PDF text layer with Tesseract 200dpi fallback)
python scripts/e5_ocr_pages.py \
  --raw-dir data/raw/official/bank-quarterly-v1 \
  --ocr-dir data/processed/ocrq

# 2. Value presence measurement on plain page text (E5a)
python scripts/e5_ocr_measure.py \
  --raw-dir data/raw/official/bank-quarterly-v1 \
  --ocr-dir data/processed/ocrq \
  --inputs-csv data/onboarding/quarterly-top10/inputs.csv \
  --out-dir experiments/e5

# 3. Naive automatic row-label extractor (E5b)
python scripts/e5_naive_extract.py \
  --raw-dir data/raw/official/bank-quarterly-v1 \
  --ocr-dir data/processed/ocrq \
  --inputs-csv data/onboarding/quarterly-top10/inputs.csv \
  --out-dir experiments/e5
```

When running in an isolated worktree or pointing to local storage directories:
```bash
python scripts/e5_ocr_measure.py \
  --raw-dir <path_to_raw_pdfs> \
  --ocr-dir <path_to_ocr_text> \
  --inputs-csv data/onboarding/quarterly-top10/inputs.csv \
  --out-dir experiments/e5

python scripts/e5_naive_extract.py \
  --raw-dir <path_to_raw_pdfs> \
  --ocr-dir <path_to_ocr_text> \
  --inputs-csv data/onboarding/quarterly-top10/inputs.csv \
  --out-dir experiments/e5
```

## E5a — is the accepted value present anywhere in the text of its page?

Rows with a local PDF, a page and page text: 885 (150 rows have no page/local PDF — FY rows from
D-078 and comparatives; 88 rows' pages were never OCR'd).

| Page type | Rows | Exact value on page | After space fix / digits only | Misread (≤2 digits off) | Not found |
|---|---|---|---|---|---|
| Text layer | 185 | 178 (96%) | 1 | 1 | 5 |
| Scanned (Tesseract) | 700 | 652 (93%) | 12 | 5 | 31 |

## E5b — naive automatic extractor (find the row label, take the column's number)

Rule: best fuzzy match (≥0.6) of the locator's row label against page lines that contain numbers;
first number = current period, second = comparative. No layout knowledge, no oracle beyond the label.

| Outcome | Rows | Share |
|---|---|---|
| Correct value | 463 | 52% |
| Row not found | 236 | 27% |
| Wrong value (wrong column/row) | 185 | 21% |

By metric (correct): NPL group 4 96%, group 5 95%, provisions 92%, total assets 88%,
NPL group 3 66%, NCI 55%, profit after tax 27%, gross loans 16%, parent profit 8%, total equity 0%.
Typical causes: income statements carry quarter and year-to-date columns (accepted value is YTD);
label variants between banks ("Cho vay khách hàng" vs subtotals); equity appears as a section total.

## Reading

Character recognition is not the bottleneck (93–96% of values are legible on the page);
structure is: picking the right row and column fails about half the time. This supports the
design choice that extracted values stay "candidate" until cross-checked with accounting
identities and recomputed with versioned formulas.
