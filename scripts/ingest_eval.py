"""INGEST-1 accuracy evaluation script.

Runs the filing extraction pipeline against the 10 audited FY2025 annual bank PDFs,
compares extracted candidate rows to ground-truth data/onboarding/top10-2025/<MÃ>-2025q4.csv,
and writes experiments/ingest/RESULTS.md and experiments/ingest/rows.json.

Usage (from worktree root):
    python scripts/ingest_eval.py

The script uses the PyMuPDF + Tesseract provider, caching page texts under
data/processed/ingest_cache/<MÃ>/  so repeated runs are cheap.

Honesty mandate: results are reported as-is. Do NOT modify extraction rules per bank
to inflate accuracy. Generic label synonyms are allowed; bank-specific tuning is NOT.
"""
from __future__ import annotations

import csv
import json
import sys
import time
from decimal import Decimal, InvalidOperation
from pathlib import Path

# ---------------------------------------------------------------------------
# Path setup
# ---------------------------------------------------------------------------
REPO_ROOT = Path(__file__).parent.parent
SRC = REPO_ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

RAW_DIR = REPO_ROOT / "data" / "raw" / "official" / "bank-2025-top10-v1"
GT_DIR = REPO_ROOT / "data" / "onboarding" / "top10-2025"
CACHE_DIR = REPO_ROOT / "data" / "processed" / "ingest_cache"
OUT_DIR = REPO_ROOT / "experiments" / "ingest"

BANKS = ["ACB", "BID", "CTG", "HDB", "MBB", "SHB", "STB", "TCB", "VCB", "VPB"]

FISCAL_YEAR = 2025
TARGET_PERIOD = "2025_Q4"
PRIOR_PERIOD = "2024_Q4"
TOLERANCE_BVN = Decimal("0.01")  # 10 million VND tolerance for match


# ---------------------------------------------------------------------------
# Imports from the extraction pipeline
# ---------------------------------------------------------------------------
from thesis_api.filing_ocr import PyMuPDFTesseractPageTextProvider
from thesis_data.filing_extract import extract_candidates_from_pages


def load_ground_truth(ticker: str) -> dict[tuple[str, str], Decimal]:
    """Load ground-truth values: { (metric_id, period_id) -> value_billion_vnd }."""
    gt_file = GT_DIR / f"{ticker}-2025q4.csv"
    if not gt_file.exists():
        print(f"  [WARN] No ground-truth file for {ticker}: {gt_file}")
        return {}
    result: dict[tuple[str, str], Decimal] = {}
    with open(gt_file, encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            metric_id = row.get("metric_id", "").strip()
            period_id = row.get("period_id", "").strip()
            raw_val = row.get("value", "").strip()
            if not (metric_id and period_id and raw_val):
                continue
            try:
                result[(metric_id, period_id)] = Decimal(raw_val)
            except InvalidOperation:
                pass
    return result


def compare_row(
    extracted_val_str: str | None,
    gt_val: Decimal,
) -> str:
    """Compare extracted value to ground truth.

    Returns one of: 'correct', 'wrong_value', 'missing', 'needs_review'.
    """
    if extracted_val_str is None:
        return "missing"
    try:
        ext_val = Decimal(extracted_val_str)
    except InvalidOperation:
        return "wrong_value"
    if abs(ext_val - gt_val) <= TOLERANCE_BVN:
        return "correct"
    return "wrong_value"


def run_bank(ticker: str, provider: PyMuPDFTesseractPageTextProvider) -> dict:
    """Run extraction for one bank; return per-row comparison results and timing."""
    pdf_path = RAW_DIR / f"{ticker}_2025_audited_consolidated.pdf"
    cache_dir = CACHE_DIR / ticker
    cache_dir.mkdir(parents=True, exist_ok=True)

    if not pdf_path.exists():
        print(f"  [ERROR] PDF not found: {pdf_path}")
        return {"ticker": ticker, "error": "pdf_not_found", "rows": [], "ocr_time_s": 0.0}

    gt = load_ground_truth(ticker)
    if not gt:
        return {"ticker": ticker, "error": "no_ground_truth", "rows": [], "ocr_time_s": 0.0}

    print(f"  Processing {ticker} ({pdf_path.name}, {pdf_path.stat().st_size // 1024} KB)...")
    t0 = time.time()

    pages_done: list[int] = [0]
    page_count: list[int] = [0]

    def _progress(done: int, total: int) -> None:
        pages_done[0] = done
        page_count[0] = total

    pages = provider.extract_all_pages(
        pdf_path,
        cache_dir=cache_dir,
        max_workers=4,
        progress_callback=_progress,
    )
    t_ocr = time.time()

    ext = extract_candidates_from_pages(
        pages,
        entity_id=ticker,
        fiscal_year=FISCAL_YEAR,
        reporting_scope="consolidated",
        display_name=ticker,
        filing_id=f"eval-{ticker.lower()}",
    )
    t_extract = time.time()

    ocr_time = t_ocr - t0
    extract_time = t_extract - t_ocr
    total_pages = len(pages)
    ocr_pages = ext.ocr_pages
    text_layer_pages = ext.text_layer_pages

    # Compare extracted rows against ground truth
    rows_result: list[dict] = []
    for row in ext.rows:
        key = (row.metric_id, row.period_id)
        gt_val = gt.get(key)
        if gt_val is None:
            # ground truth doesn't have this cell (e.g. metric not in prior set)
            status = "not_in_gt"
        elif row.status == "missing":
            status = "missing"
        else:
            status = compare_row(row.value_billion_vnd, gt_val)

        rows_result.append({
            "ticker": ticker,
            "metric_id": row.metric_id,
            "period_id": row.period_id,
            "period_role": row.period_role,
            "status": status,
            "extracted": row.value_billion_vnd,
            "gt": str(gt_val) if gt_val is not None else None,
            "page": row.page,
            "row_label": row.row_label,
            "row_status": row.status,
            "issues": [i.code for i in row.issues],
        })

    return {
        "ticker": ticker,
        "pdf_pages": total_pages,
        "text_layer_pages": text_layer_pages,
        "ocr_pages": ocr_pages,
        "ocr_time_s": round(ocr_time, 2),
        "extract_time_s": round(extract_time, 3),
        "ocr_per_page_s": round(ocr_time / total_pages, 3) if total_pages > 0 else 0.0,
        "unit_detected": ext.unit_detected,
        "statement_pages": ext.statement_pages.to_dict(),
        "rows": rows_result,
    }


def summarize(all_results: list[dict]) -> dict:
    """Aggregate per-bank results into summary counters."""
    totals: dict[str, int] = {
        "correct": 0,
        "wrong_value": 0,
        "missing": 0,
        "not_in_gt": 0,
        "total_in_gt": 0,
    }
    error_groups: dict[str, int] = {}

    for bank in all_results:
        if "error" in bank:
            continue
        for row in bank["rows"]:
            st = row["status"]
            totals[st] = totals.get(st, 0) + 1
            if st in ("correct", "wrong_value", "missing"):
                totals["total_in_gt"] += 1
            if st == "wrong_value":
                for code in row.get("issues", []):
                    error_groups[code] = error_groups.get(code, 0) + 1
            elif st == "missing":
                for code in row.get("issues", []):
                    error_groups[code] = error_groups.get(code, 0) + 1

    return {
        "totals": totals,
        "error_groups": error_groups,
    }


def build_results_md(all_results: list[dict], summary: dict) -> str:
    totals = summary["totals"]
    total_in_gt = totals["total_in_gt"]
    correct = totals["correct"]
    wrong = totals["wrong_value"]
    missing = totals["missing"]
    accuracy = correct / total_in_gt if total_in_gt > 0 else 0.0

    lines: list[str] = [
        "# INGEST-1 Evaluation Results",
        "",
        f"**Run date**: {time.strftime('%Y-%m-%d %H:%M %Z')}  ",
        "**Dataset**: 10 audited FY2025 consolidated annual bank filings  ",
        "**Ground truth**: `data/onboarding/top10-2025/<TICKER>-2025q4.csv`  ",
        "**Pipeline**: PyMuPDF text-layer detection + Tesseract OCR (when no text layer)  ",
        "",
        "## Overall Accuracy",
        "",
        f"| Metric | Count |",
        f"|--------|-------|",
        f"| Cells evaluated (in ground truth) | {total_in_gt} |",
        f"| **Correct** (within ±0.01 tỷ) | **{correct}** |",
        f"| Wrong value | {wrong} |",
        f"| Missing (row not found) | {missing} |",
        f"| **Accuracy** | **{accuracy:.1%}** |",
        "",
        "## Per-Bank Results",
        "",
        "| Bank | Pages | Text-layer | OCR | OCR time | Unit | Correct | Wrong | Missing | Accuracy |",
        "|------|-------|-----------|-----|----------|------|---------|-------|---------|----------|",
    ]

    for bank in all_results:
        if "error" in bank:
            lines.append(f"| {bank['ticker']} | — | — | — | — | — | — | — | — | ERROR: {bank['error']} |")
            continue
        rows_in_gt = [r for r in bank["rows"] if r["status"] in ("correct", "wrong_value", "missing")]
        c = sum(1 for r in rows_in_gt if r["status"] == "correct")
        w = sum(1 for r in rows_in_gt if r["status"] == "wrong_value")
        m = sum(1 for r in rows_in_gt if r["status"] == "missing")
        n = len(rows_in_gt)
        acc = f"{c/n:.0%}" if n > 0 else "—"
        lines.append(
            f"| {bank['ticker']} "
            f"| {bank['pdf_pages']} "
            f"| {bank['text_layer_pages']} "
            f"| {bank['ocr_pages']} "
            f"| {bank['ocr_time_s']:.1f}s "
            f"| {bank.get('unit_detected', '?')} "
            f"| {c} | {w} | {m} | {acc} |"
        )

    lines += [
        "",
        "## Error Analysis (by issue code)",
        "",
        "| Issue Code | Occurrences |",
        "|-----------|------------|",
    ]
    for code, cnt in sorted(summary["error_groups"].items(), key=lambda x: -x[1]):
        lines.append(f"| `{code}` | {cnt} |")

    lines += [
        "",
        "## Notes",
        "",
        "- **Correct**: extracted value matches ground truth within ±0.01 billion VND.",
        "- **Wrong value**: row label was found but extracted number does not match ground truth.",
        "- **Missing**: extraction pipeline did not find a matching row at all.",
        "- Ground truth covers 10 metrics × 2 periods per bank = up to 200 cells; some banks have 0 NCI so fewer cells.",
        "- This is honest experimental evidence for the thesis. No bank-specific rule tuning was applied.",
        "- See `experiments/ingest/rows.json` for full row-level detail.",
    ]

    return "\n".join(lines) + "\n"


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    CACHE_DIR.mkdir(parents=True, exist_ok=True)

    print("=== INGEST-1 Evaluation ===")
    print(f"PDFs:    {RAW_DIR}")
    print(f"GT:      {GT_DIR}")
    print(f"Cache:   {CACHE_DIR}")
    print(f"Output:  {OUT_DIR}")
    print()

    provider = PyMuPDFTesseractPageTextProvider()
    all_results: list[dict] = []

    for ticker in BANKS:
        print(f"[{BANKS.index(ticker) + 1}/{len(BANKS)}] {ticker}")
        bank_result = run_bank(ticker, provider)
        all_results.append(bank_result)

        # Print quick summary per bank
        rows_in_gt = [r for r in bank_result.get("rows", []) if r["status"] in ("correct", "wrong_value", "missing")]
        c = sum(1 for r in rows_in_gt if r["status"] == "correct")
        n = len(rows_in_gt)
        print(f"         {c}/{n} correct  OCR:{bank_result.get('ocr_time_s', '?')}s")

    # Write rows.json
    rows_json_path = OUT_DIR / "rows.json"
    all_rows = [row for bank in all_results for row in bank.get("rows", [])]
    with open(rows_json_path, "w", encoding="utf-8") as f:
        json.dump(all_rows, f, ensure_ascii=False, indent=2)
    print(f"\nWrote {rows_json_path} ({len(all_rows)} rows)")

    summary = summarize(all_results)
    md_content = build_results_md(all_results, summary)
    results_md_path = OUT_DIR / "RESULTS.md"
    with open(results_md_path, "w", encoding="utf-8") as f:
        f.write(md_content)
    print(f"Wrote {results_md_path}")

    totals = summary["totals"]
    total_in_gt = totals["total_in_gt"]
    correct = totals["correct"]
    accuracy = correct / total_in_gt if total_in_gt > 0 else 0.0
    print(f"\n=== FINAL: {correct}/{total_in_gt} correct = {accuracy:.1%} ===")


if __name__ == "__main__":
    main()
