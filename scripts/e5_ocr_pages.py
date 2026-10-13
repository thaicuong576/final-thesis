"""Text extraction for every page of quarterly filings (PDF text layer, else Tesseract at 200 dpi).

Replaces hard-coded paths from ocr_all.py with repo-relative CLI options.
Dependencies like PyMuPDF (fitz) are imported lazily so CI tests pass without them.
"""
from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
from pathlib import Path


def default_tesseract_cmd() -> str:
    which_cmd = shutil.which("tesseract")
    if which_cmd:
        return which_cmd
    win_path = Path(r"C:\Program Files\Tesseract-OCR\tesseract.exe")
    if win_path.exists():
        return str(win_path)
    return "tesseract"


def extract_pages_for_pdf(
    pdf_path: Path,
    out_dir: Path,
    tesseract_cmd: str = "tesseract",
    dpi: int = 200,
    lang: str = "eng",
) -> int:
    try:
        import fitz
    except ImportError as exc:
        raise ImportError(
            "PyMuPDF (fitz) is required to run PDF page extraction. Install with `pip install PyMuPDF`."
        ) from exc

    d = out_dir / pdf_path.stem
    d.mkdir(parents=True, exist_ok=True)
    doc = fitz.open(pdf_path)
    for i, page in enumerate(doc, start=1):
        txt = d / f"p{i:03d}.txt"
        if txt.exists():
            continue
        text = page.get_text()
        if len(text.strip()) < 200 or text.count("\ufffd") > 20:
            png = d / f"p{i:03d}.png"
            page.get_pixmap(dpi=dpi).save(png)
            try:
                r = subprocess.run(
                    [tesseract_cmd, str(png), "stdout", "--psm", "6", "-l", lang],
                    capture_output=True,
                    text=True,
                    encoding="utf-8",
                    errors="ignore",
                )
                text = r.stdout
            finally:
                if png.exists():
                    png.unlink()
        txt.write_text(text, encoding="utf-8")
    return len(doc)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Extract page text from quarterly filing PDFs (text layer or Tesseract fallback)."
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
        help="Output directory for extracted page text files (default: data/processed/ocrq)",
    )
    parser.add_argument(
        "--tesseract-cmd",
        type=str,
        default=default_tesseract_cmd(),
        help="Path or name of tesseract executable",
    )
    parser.add_argument(
        "--worker-index",
        type=int,
        default=0,
        help="0-based worker index for parallel slicing",
    )
    parser.add_argument(
        "--worker-count",
        type=int,
        default=1,
        help="Total worker count for parallel slicing",
    )
    parser.add_argument(
        "--dpi",
        type=int,
        default=200,
        help="Rasterization DPI for scanned pages (default: 200)",
    )
    parser.add_argument(
        "--lang",
        type=str,
        default="eng",
        help="Tesseract OCR language model (default: eng)",
    )
    # Optional positional arguments for backward compatibility with ocr_all.py <idx> <cnt>
    parser.add_argument("positional_args", nargs="*", type=int, help="Optional [worker_index, worker_count]")

    args = parser.parse_args()

    worker_idx = args.worker_index
    worker_cnt = args.worker_count
    if len(args.positional_args) >= 2:
        worker_idx = args.positional_args[0]
        worker_cnt = args.positional_args[1]
    elif len(args.positional_args) == 1:
        worker_idx = args.positional_args[0]

    files = sorted(args.raw_dir.glob("*.pdf"))[worker_idx::worker_cnt]
    for pdf in files:
        page_count = extract_pages_for_pdf(
            pdf_path=pdf,
            out_dir=args.ocr_dir,
            tesseract_cmd=args.tesseract_cmd,
            dpi=args.dpi,
            lang=args.lang,
        )
        print(pdf.stem, page_count, flush=True)

    print("WORKER DONE", worker_idx, flush=True)


if __name__ == "__main__":
    main()
