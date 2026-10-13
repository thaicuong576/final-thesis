"""E5b: naive automatic extractor (find row label on page text, take column's number) vs accepted values.

Evaluates how well a heuristic rule (fuzzy matching row label and selecting current/comparative column)
performs without layout analysis or accounting domain rules.
"""
from __future__ import annotations

import argparse
import collections
import csv
from difflib import SequenceMatcher
import hashlib
import json
from pathlib import Path
import re
from typing import Any, Dict, List, Optional, Tuple
import unicodedata

NUM = re.compile(r"\(?\d{1,3}(?:[.,]\d{3})+\)?")


def fold(s: str) -> str:
    """Normalize and fold Vietnamese text to lowercase ASCII."""
    s = unicodedata.normalize("NFD", s.replace("đ", "d").replace("Đ", "D"))
    return re.sub(
        r"[^a-z0-9 ]", " ", "".join(ch for ch in s if unicodedata.category(ch) != "Mn").lower()
    )


def find_best_row_match(lines: List[str], row_label: str) -> Tuple[Optional[List[str]], float]:
    """Find the line best matching row_label containing numbers, returning (numbers, similarity_score)."""
    label = fold(row_label).split()
    best: Optional[List[str]] = None
    bestscore = 0.0
    for line in lines:
        nums = NUM.findall(line)
        if not nums:
            continue
        text = fold(NUM.sub(" ", line)).split()
        if not text:
            continue
        sc = SequenceMatcher(None, " ".join(label), " ".join(text[: len(label) + 3])).ratio()
        if sc > bestscore:
            best, bestscore = nums, sc
    return best, bestscore


def classify_extracted_value(
    best_nums: Optional[List[str]],
    bestscore: float,
    target_val: float | str,
    col_label: Optional[str] = None,
) -> str:
    """Classify extraction result as row_not_found, correct, wrong_value, or column_missing."""
    if best_nums is None or bestscore < 0.6:
        return "row_not_found"
    target = round(float(target_val) * 1000)
    idx = 1 if col_label and "so sanh" in fold(col_label) else 0
    vals = [int(re.sub(r"\D", "", n)) for n in best_nums]
    pick = vals[idx] if idx < len(vals) else None
    if pick == abs(target):
        return "correct"
    elif pick is not None:
        return "wrong_value"
    else:
        return "column_missing"


def run_naive_extract(
    raw_dir: Path,
    ocr_dir: Path,
    inputs_csv: Path,
    out_dir: Path,
    e5_rows_path: Optional[Path] = None,
) -> List[Dict[str, Any]]:
    """Run E5b naive extraction evaluation."""
    sha2file = {
        hashlib.sha256(p.read_bytes()).hexdigest().upper(): p
        for p in raw_dir.glob("*.pdf")
    }

    if e5_rows_path is None:
        e5_rows_path = out_dir / "e5_rows.json"

    with open(e5_rows_path, encoding="utf-8") as f:
        layer = json.load(f)

    with open(inputs_csv, encoding="utf-8") as f:
        rows = list(csv.DictReader(f))

    out: List[Dict[str, Any]] = []
    for r, L in zip(rows, layer):
        loc = r["source_locator"]
        m = re.search(r"pdf_page=(\d+)", loc)
        row = re.search(r"row=([^;]+)", loc)
        col = re.search(r"column=([^;]+)", loc)
        pdf = sha2file.get((r["source_sha256"] or "").upper())
        if not (m and row and pdf):
            continue

        t = ocr_dir / pdf.stem / f"p{int(m.group(1)):03d}.txt"
        if not t.exists():
            continue

        lines = t.read_text(encoding="utf-8", errors="ignore").splitlines()
        best, bestscore = find_best_row_match(lines, row.group(1))
        col_text = col.group(1) if col else None
        status = classify_extracted_value(best, bestscore, r["value"], col_text)

        out.append(
            {
                "layer": L.get("layer"),
                "metric": r["metric_id"],
                "reading": L.get("reading"),
                "status": status,
            }
        )

    out_dir.mkdir(parents=True, exist_ok=True)
    out_file = out_dir / "e5b_rows.json"
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=2)

    c = collections.Counter(x["status"] for x in out)
    print("ALL", len(out), c.most_common())
    for lay in ["text_layer", "scanned"]:
        s = [x for x in out if x.get("layer") == lay]
        print(lay, len(s), collections.Counter(x["status"] for x in s).most_common())

    by: Dict[str, collections.Counter[str]] = collections.defaultdict(collections.Counter)
    for x in out:
        by[x["metric"].replace("bank.input.", "")][x["status"]] += 1
    for k, v in sorted(by.items()):
        n = sum(v.values())
        correct_pct = v["correct"] / n if n > 0 else 0.0
        print(f"  {k:28s} n={n:3d} correct={correct_pct:.0%}  {dict(v)}")

    return out


def main() -> None:
    parser = argparse.ArgumentParser(
        description="E5b: naive automatic extractor vs accepted values."
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
    parser.add_argument(
        "--e5-rows",
        type=Path,
        default=None,
        help="Path to e5_rows.json (default: {out-dir}/e5_rows.json)",
    )
    args = parser.parse_args()

    run_naive_extract(
        raw_dir=args.raw_dir,
        ocr_dir=args.ocr_dir,
        inputs_csv=args.inputs_csv,
        out_dir=args.out_dir,
        e5_rows_path=args.e5_rows,
    )


if __name__ == "__main__":
    main()
