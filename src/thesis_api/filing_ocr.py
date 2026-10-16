"""PDF text layer extraction and Tesseract OCR adapter.

Phase: INGEST-1 (D-086).
Provides PageTextProvider interface and PyMuPDF + Tesseract implementation
for rendering pages, extracting text layers, running OCR on scanned pages,
and caching page outputs on disk.
"""

from __future__ import annotations

import concurrent.futures
import json
import logging
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
from typing import Callable, Optional, Protocol

from thesis_data.filing_extract import PageInput

logger = logging.getLogger(__name__)


class TesseractNotFoundError(RuntimeError):
    """Raised when Tesseract OCR is required for a scanned page but not installed."""
    pass


class PageTextProvider(Protocol):
    """Protocol for extracting page texts and rendering pages."""

    def get_page_count(self, pdf_path: Path) -> int:
        ...

    def get_page_text(
        self,
        pdf_path: Path,
        page_number: int,
        cache_dir: Optional[Path] = None,
    ) -> PageInput:
        ...

    def extract_all_pages(
        self,
        pdf_path: Path,
        cache_dir: Optional[Path] = None,
        max_workers: int = 4,
        progress_callback: Optional[Callable[[int, int], None]] = None,
        max_pages: Optional[int] = None,
    ) -> list[PageInput]:
        ...

    def render_page_png(
        self,
        pdf_path: Path,
        page_number: int,
        dpi: int = 120,
        cache_path: Optional[Path] = None,
    ) -> bytes:
        ...


def resolve_tesseract_cmd() -> Optional[str]:
    """Find Tesseract executable from environment or standard paths."""
    env_cmd = os.environ.get("TESSERACT_CMD")
    if env_cmd and Path(env_cmd).exists():
        return env_cmd
    which_cmd = shutil.which("tesseract")
    if which_cmd:
        return which_cmd
    standard_win = Path(r"C:\Program Files\Tesseract-OCR\tesseract.exe")
    if standard_win.exists():
        return str(standard_win)
    return None


class PyMuPDFTesseractPageTextProvider:
    """Production provider using PyMuPDF (fitz) and Tesseract OCR."""

    def __init__(
        self,
        tesseract_cmd: Optional[str] = None,
        dpi: int = 200,
        ocr_lang: str = "eng",
    ) -> None:
        self.tesseract_cmd = tesseract_cmd or resolve_tesseract_cmd()
        self.dpi = dpi
        self.ocr_lang = ocr_lang

    def is_tesseract_available(self) -> bool:
        if not self.tesseract_cmd:
            return False
        return Path(self.tesseract_cmd).exists() or shutil.which(self.tesseract_cmd) is not None

    def get_page_count(self, pdf_path: Path) -> int:
        try:
            import fitz
        except ImportError as exc:
            raise ImportError("PyMuPDF (fitz) is required to open PDF files.") from exc

        doc = fitz.open(pdf_path)
        try:
            return len(doc)
        finally:
            doc.close()

    def get_page_text(
        self,
        pdf_path: Path,
        page_number: int,
        cache_dir: Optional[Path] = None,
    ) -> PageInput:
        # Check disk cache
        if cache_dir:
            txt_file = cache_dir / f"p{page_number:03d}.txt"
            meta_file = cache_dir / f"p{page_number:03d}.json"
            if txt_file.exists() and meta_file.exists():
                try:
                    with open(meta_file, encoding="utf-8") as f:
                        meta = json.load(f)
                    text = txt_file.read_text(encoding="utf-8")
                    return PageInput(
                        page_number=page_number,
                        text=text,
                        source=meta.get("source", "ocr"),
                    )
                except Exception:
                    logger.warning("Failed to read cache for page %d; re-extracting", page_number)

        try:
            import fitz
        except ImportError as exc:
            raise ImportError("PyMuPDF (fitz) is required to open PDF files.") from exc

        doc = fitz.open(pdf_path)
        try:
            page = doc[page_number - 1]
            text = page.get_text()

            # If page text layer has >= 200 chars and not corrupted, use text layer
            if len(text.strip()) >= 200 and text.count("\ufffd") <= 20:
                source = "text_layer"
            else:
                # Scanned image page, run Tesseract OCR
                if not self.is_tesseract_available():
                    raise TesseractNotFoundError(
                        "Máy chủ chưa cài đặt Tesseract OCR để đọc báo cáo dạng scan ảnh."
                    )
                source = "ocr"
                pix = page.get_pixmap(dpi=self.dpi)
                with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp:
                    tmp_png = tmp.name
                try:
                    pix.save(tmp_png)
                    res = subprocess.run(
                        [
                            str(self.tesseract_cmd),
                            tmp_png,
                            "stdout",
                            "--psm",
                            "6",
                            "-l",
                            self.ocr_lang,
                        ],
                        capture_output=True,
                        text=True,
                        encoding="utf-8",
                        errors="ignore",
                    )
                    text = res.stdout
                finally:
                    if Path(tmp_png).exists():
                        try:
                            Path(tmp_png).unlink()
                        except OSError:
                            pass
        finally:
            doc.close()

        # Cache result if cache_dir is specified
        if cache_dir:
            cache_dir.mkdir(parents=True, exist_ok=True)
            txt_file = cache_dir / f"p{page_number:03d}.txt"
            meta_file = cache_dir / f"p{page_number:03d}.json"
            txt_file.write_text(text, encoding="utf-8")
            with open(meta_file, "w", encoding="utf-8") as f:
                json.dump({"page": page_number, "source": source}, f)

        return PageInput(page_number=page_number, text=text, source=source)

    def extract_all_pages(
        self,
        pdf_path: Path,
        cache_dir: Optional[Path] = None,
        max_workers: int = 4,
        progress_callback: Optional[Callable[[int, int], None]] = None,
        max_pages: Optional[int] = None,
    ) -> list[PageInput]:
        total_pages = self.get_page_count(pdf_path)
        limit = min(total_pages, max_pages) if max_pages else total_pages
        results: list[Optional[PageInput]] = [None] * limit
        done_count = 0

        def _process_page(idx: int) -> tuple[int, PageInput]:
            p_res = self.get_page_text(pdf_path, idx + 1, cache_dir=cache_dir)
            return idx, p_res

        workers = min(max_workers, limit, 4)
        if workers <= 1:
            for idx in range(limit):
                _, p_res = _process_page(idx)
                results[idx] = p_res
                done_count += 1
                if progress_callback:
                    progress_callback(done_count, limit)
        else:
            with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as executor:
                futures = [executor.submit(_process_page, idx) for idx in range(limit)]
                for future in concurrent.futures.as_completed(futures):
                    idx, p_res = future.result()
                    results[idx] = p_res
                    done_count += 1
                    if progress_callback:
                        progress_callback(done_count, limit)

        return [r for r in results if r is not None]

    def render_page_png(
        self,
        pdf_path: Path,
        page_number: int,
        dpi: int = 120,
        cache_path: Optional[Path] = None,
    ) -> bytes:
        if cache_path and cache_path.exists():
            return cache_path.read_bytes()

        try:
            import fitz
        except ImportError as exc:
            raise ImportError("PyMuPDF (fitz) is required to render PDF pages.") from exc

        doc = fitz.open(pdf_path)
        try:
            if page_number < 1 or page_number > len(doc):
                raise IndexError(f"Page number {page_number} out of range (1..{len(doc)})")
            page = doc[page_number - 1]
            pix = page.get_pixmap(dpi=dpi)
            png_bytes = pix.tobytes("png")
        finally:
            doc.close()

        if cache_path:
            cache_path.parent.mkdir(parents=True, exist_ok=True)
            cache_path.write_bytes(png_bytes)

        return png_bytes


class MockPageTextProvider:
    """Mock provider for deterministic testing without PyMuPDF or Tesseract."""

    def __init__(self, pages: dict[int, tuple[str, str]]) -> None:
        # pages: {page_num: (text, source)}
        self.pages = pages

    def get_page_count(self, pdf_path: Path) -> int:
        return len(self.pages)

    def get_page_text(
        self,
        pdf_path: Path,
        page_number: int,
        cache_dir: Optional[Path] = None,
    ) -> PageInput:
        if page_number in self.pages:
            text, source = self.pages[page_number]
            return PageInput(
                page_number=page_number,
                text=text,
                source=source,  # type: ignore[arg-type]
            )
        return PageInput(page_number=page_number, text="", source="text_layer")

    def extract_all_pages(
        self,
        pdf_path: Path,
        cache_dir: Optional[Path] = None,
        max_workers: int = 4,
        progress_callback: Optional[Callable[[int, int], None]] = None,
        max_pages: Optional[int] = None,
    ) -> list[PageInput]:
        pnos = sorted(self.pages.keys())
        if max_pages:
            pnos = pnos[:max_pages]
        res = [
            self.get_page_text(pdf_path, pno, cache_dir=cache_dir)
            for pno in pnos
        ]
        if progress_callback:
            progress_callback(len(res), len(res))
        return res

    def render_page_png(
        self,
        pdf_path: Path,
        page_number: int,
        dpi: int = 120,
        cache_path: Optional[Path] = None,
    ) -> bytes:
        # Minimal valid 1x1 PNG bytes
        png_1x1 = (
            b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01"
            b"\x08\x06\x00\x00\x00\x1f\x15c4\x00\x00\x00\nIDATx\x9cc\x00\x01"
            b"\x00\x00\x05\x00\x01\r\n-\xb4\x00\x00\x00\x00IEND\xaeB`\x82"
        )
        if page_number < 1 or page_number > len(self.pages):
            raise IndexError(f"Page number {page_number} out of range")
        return png_1x1
