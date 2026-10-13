"""E5: how often does plain page text (text layer or one Tesseract pass) contain accepted values?

Evaluates whether verified numeric inputs from quarterly bank filings appear in the raw
page text extracted from the corresponding filing page.
"""
from __future__ import annotations

import argparse
import collections
import csv
import hashlib
import json
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple


def candidates(v: str | float) -> Tuple[int, Set[str]]:
    """Generate candidate number representations for a value in million VND."""
    m = round(float(v) * 1000)  # billion -> million VND
    s = f"{abs(m):,}"
    out = {s, s.replace(",", "."), s.replace(",", " ")}
    return m, out


def classify_text_match(txt: str, val: str | float) -> str:
    """Classify the match status of a numeric value inside page text."""
    mil, cands = candidates(val)
    flat = re.sub(r"[ \t]", "", txt)
    digits = re.sub(r"\D", "", txt)
    if any(c in txt for c in cands):
        return "exact_on_page"
    elif any(c.replace(" ", "") in flat for c in cands):
        return "exact_after_space_fix"
    elif str(abs(mil)) in digits:
        return "digits_only"
    else:
        # wrong digits: same length number on page differing in <=2 digits
        nums = re.findall(r"\d{1,3}(?:[.,]\d{3})+", txt)
        target = str(abs(mil))
        near = False
        for n in nums:
            d = re.sub(r"\D", "", n)
            if len(d) == len(target) and sum(a != b for a, b in zip(d, target)) <= 2:
                near = True
                break
        return "near_miss_misread" if near else "not_found"


def has_layer(pdf: Path, layer_cache: Optional[Dict[Path, bool]] = None) -> bool:
    """Check if PDF has an embedded text layer (first 6 pages > 500 chars)."""
    if layer_cache is None:
        layer_cache = {}
    if pdf not in layer_cache:
        try:
            import fitz
        except ImportError as exc:
            raise ImportError(
                "PyMuPDF (fitz) is required to inspect PDF text layers. Install with `pip install PyMuPDF`."
            ) from exc
        d = fitz.open(pdf)
        n = min(len(d), 6)
        layer_cache[pdf] = sum(len(d[i].get_text()) for i in range(n)) > 500
    return layer_cache[pdf]


def page_text(ocr_dir: Path, pdf: Path, page: int) -> Optional[str]:
    """Load pre-extracted page text from OCR directory."""
    t = ocr_dir / pdf.stem / f"p{page:03d}.txt"
    return t.read_text(encoding="utf-8", errors="ignore") if t.exists() else None


def run_e5_measure(
    raw_dir: Path,
    ocr_dir: Path,
    inputs_csv: Path,
    out_dir: Path,
) -> List[Dict[str, Any]]:
    """Run E5 measurement and write results to out_dir/e5_rows.json."""
    sha2file: Dict[str, Path] = {}
    for p in raw_dir.glob("*.pdf"):
        sha2file[hashlib.sha256(p.read_bytes()).hexdigest().upper()] = p

    with open(inputs_csv, encoding="utf-8") as f:
        rows = list(csv.DictReader(f))

    layer_cache: Dict[Path, bool] = {}
    res: List[Dict[str, Any]] = []

    for r in rows:
        m = re.search(r"pdf_page=(\d+)", r["source_locator"])
        rd = re.search(r"reading=([^;]+)", r["source_locator"])
        pdf = sha2file.get((r["source_sha256"] or "").upper())
        rec: Dict[str, Any] = {
            "entity": r["entity_id"],
            "metric": r["metric_id"],
            "period": r["period_id"],
            "reading": rd.group(1).strip() if rd else "none",
            "pdf": pdf.name if pdf else None,
        }
        if not (m and pdf):
            rec["status"] = "no_local_pdf_or_page"
            res.append(rec)
            continue

        page = int(m.group(1))
        txt = page_text(ocr_dir, pdf, page)
        rec["layer"] = "text_layer" if has_layer(pdf, layer_cache) else "scanned"
        if txt is None:
            rec["status"] = "no_ocr_text"
            res.append(rec)
            continue

        rec["status"] = classify_text_match(txt, r["value"])
        res.append(rec)

    out_dir.mkdir(parents=True, exist_ok=True)
    out_file = out_dir / "e5_rows.json"
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(res, f, ensure_ascii=False, indent=2)

    c = collections.Counter(x["status"] for x in res)
    print("ALL", len(res), c.most_common())
    for lay in ["text_layer", "scanned"]:
        sub = [x for x in res if x.get("layer") == lay]
        cc = collections.Counter(x["status"] for x in sub)
        print(lay, len(sub), cc.most_common())

    by: Dict[str, collections.Counter[str]] = collections.defaultdict(collections.Counter)
    for x in res:
        if x.get("layer") == "scanned":
            by[x["metric"]][x["status"]] += 1
    for k, v in sorted(by.items()):
        print(" scanned", k, dict(v))

    return res


def main() -> None:
    parser = argparse.ArgumentParser(
        description="E5: how often does plain page text contain accepted values?"
    )
    parser.add_argument(
        "--raw-dir",
        type=Path,
        default=Path("data/raw/official/bank-quarterly-v1"),
        help="Path to directory containing filing PDFs (default: data/raw/official/bank-quarterly-v1)",
    )
    parser.add_argument(
        "--ocr-dir",
        type=Path,
        default=Path("data/processed/ocrq"),
        help="Directory containing extracted page texts (default: data/processed/ocrq)",
    )
    parser.add_argument(
        "--inputs-csv",
        type=Path,
        default=Path("data/onboarding/quarterly-top10/inputs.csv"),
        help="Path to inputs.csv (default: data/onboarding/quarterly-top10/inputs.csv)",
    )
    parser.add_argument(
        "--out-dir",
        type=Path,
        default=Path("experiments/e5"),
        help="Output directory for results JSON (default: experiments/e5)",
    )
    args = parser.parse_args()

    run_e5_measure(
        raw_dir=args.raw_dir,
        ocr_dir=args.ocr_dir,
        inputs_csv=args.inputs_csv,
        out_dir=args.out_dir,
    )


if __name__ == "__main__":
    main()
