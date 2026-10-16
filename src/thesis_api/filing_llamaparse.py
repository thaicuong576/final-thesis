"""LlamaParse table-aware page text provider.

Phase: INGEST-4 (D-086).
Provides LlamaParseProvider implementing PageTextProvider protocol:
- Calls Llama Cloud API v2 (multipart upload + poll with expand=markdown)
- Converts HTML <table> into pipe-separated format: 'nhãn | cột1 | cột2'
- Subsets pages into temporary PDF via PyMuPDF before uploading to preserve credits
- Caches page texts on disk by (sha256, page_number, tier)
- Fallback to Tesseract on missing/invalid key, quota exceeded, or network error
- Strict privacy: never prints, logs, or returns secrets.
"""

from __future__ import annotations

import concurrent.futures
from html.parser import HTMLParser
import io
import json
import logging
from pathlib import Path
import re
import time
from typing import Any, Callable, Optional, Sequence

import httpx

from thesis_api.filing_ocr import (
    PageTextProvider,
    PyMuPDFTesseractPageTextProvider,
    TesseractNotFoundError,
)
from thesis_data.filing_extract import PageInput

logger = logging.getLogger(__name__)

LLAMA_API_BASE_URL = "https://api.cloud.llamaindex.ai/api/v2"


class LlamaParseError(RuntimeError):
    """User-safe exception for LlamaParse failures (never exposes credentials)."""
    pass


# ---------------------------------------------------------------------------
# HTML Table to Pipe-Form Parser
# ---------------------------------------------------------------------------

class _HTMLTableToPipeParser(HTMLParser):
    """HTML parser converting <table> elements into pipe-separated table rows.

    Strips inline styling/markup (<b>, <u>, <span>, <i>, <em>) while preserving
    cell counts and non-table paragraph/header text.
    """

    def __init__(self) -> None:
        super().__init__()
        self.output_lines: list[str] = []
        self.in_table = False
        self.in_row = False
        self.in_cell = False
        self.current_row_cells: list[str] = []
        self.current_cell_parts: list[str] = []
        self.current_text_parts: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, Optional[str]]]) -> None:
        tag_lower = tag.lower()
        if tag_lower == "table":
            self._flush_text()
            self.in_table = True
        elif tag_lower == "tr":
            if self.in_table:
                self.in_row = True
                self.current_row_cells = []
        elif tag_lower in ("th", "td"):
            if self.in_row:
                self.in_cell = True
                self.current_cell_parts = []
        elif tag_lower in ("p", "div", "h1", "h2", "h3", "h4", "h5", "h6", "br"):
            if not self.in_table:
                self._flush_text()

    def handle_endtag(self, tag: str) -> None:
        tag_lower = tag.lower()
        if tag_lower in ("th", "td"):
            if self.in_cell:
                cell_text = "".join(self.current_cell_parts).strip()
                cell_clean = re.sub(r"\s+", " ", cell_text)
                self.current_row_cells.append(cell_clean)
                self.current_cell_parts = []
                self.in_cell = False
        elif tag_lower == "tr":
            if self.in_row:
                if self.current_row_cells:
                    line = " | ".join(self.current_row_cells)
                    self.output_lines.append(line)
                self.current_row_cells = []
                self.in_row = False
        elif tag_lower == "table":
            self.in_table = False
        elif tag_lower in ("p", "div", "h1", "h2", "h3", "h4", "h5", "h6"):
            if not self.in_table:
                self._flush_text()

    def handle_data(self, data: str) -> None:
        if self.in_cell:
            self.current_cell_parts.append(data)
        elif not self.in_table:
            self.current_text_parts.append(data)

    def _flush_text(self) -> None:
        if self.current_text_parts:
            text = "".join(self.current_text_parts).strip()
            self.current_text_parts = []
            if text:
                for line in text.splitlines():
                    clean_line = line.strip()
                    if clean_line:
                        self.output_lines.append(clean_line)

    def get_result(self) -> str:
        self._flush_text()
        return "\n".join(self.output_lines)


def html_table_to_pipe_text(content: str) -> str:
    """Convert HTML or mixed markdown with <table> tags to clean pipe-separated lines.

    Preserves lines outside <table> and transforms <tr><th>/<td> cells into:
        label | col1 | col2
    """
    if not content:
        return ""

    # If the text has no HTML tags at all, check if it's already markdown/pipe text
    if "<table" not in content.lower() and "<tr" not in content.lower():
        # Clean any stray HTML tags if present, or return as-is
        return re.sub(r"<[^>]+>", "", content).strip()

    parser = _HTMLTableToPipeParser()
    try:
        parser.feed(content)
        parser.close()
        res = parser.get_result()
        return res if res.strip() else re.sub(r"<[^>]+>", "", content).strip()
    except Exception:
        # Fallback if html parser fails on malformed HTML
        return re.sub(r"<[^>]+>", "", content).strip()


# ---------------------------------------------------------------------------
# LlamaParse Provider Implementation
# ---------------------------------------------------------------------------

class LlamaParseProvider:
    """LlamaParse Cloud API v2 provider with table-aware markdown extraction."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        *,
        tier: str = "cost_effective",
        version: str = "latest",
        timeout_s: float = 90.0,
        max_retries: int = 2,
        poll_interval_s: float = 2.0,
        enable_fallback: bool = True,
        tesseract_fallback: Optional[PyMuPDFTesseractPageTextProvider] = None,
        transport: Optional[httpx.BaseTransport] = None,
    ) -> None:
        self.api_key = api_key
        self.tier = tier
        self.version = version
        self.timeout_s = timeout_s
        self.max_retries = max_retries
        self.poll_interval_s = poll_interval_s
        self.enable_fallback = enable_fallback
        if not enable_fallback:
            self.tesseract_fallback = None
        else:
            self.tesseract_fallback = tesseract_fallback or PyMuPDFTesseractPageTextProvider()
        self.transport = transport
        self.total_pages_sent: int = 0

    def is_api_key_configured(self) -> bool:
        return bool(self.api_key and self.api_key.strip())

    @staticmethod
    def _calc_sha256(path: Path) -> str:
        import hashlib
        h = hashlib.sha256()
        with open(path, "rb") as f:
            for chunk in iter(lambda: f.read(65536), b""):
                h.update(chunk)
        return h.hexdigest()

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

    def get_page_text(
        self,
        pdf_path: Path,
        page_number: int,
        cache_dir: Optional[Path] = None,
    ) -> PageInput:
        pages = self.extract_pages(pdf_path, [page_number], cache_dir=cache_dir)
        return pages[0] if pages else PageInput(page_number=page_number, text="", source="llamaparse")

    def extract_pages(
        self,
        pdf_path: Path,
        page_numbers: Sequence[int],
        cache_dir: Optional[Path] = None,
        progress_callback: Optional[Callable[[int, int], None]] = None,
        chunk_size: int = 40,
        max_workers: int = 2,
    ) -> list[PageInput]:
        """Extract requested pages using LlamaParse API v2 with chunking, caching, and fallback."""
        if not page_numbers:
            return []

        file_hash = self._calc_sha256(pdf_path)

        # 1. Check disk cache for already extracted pages
        results: dict[int, PageInput] = {}
        missing_pages: list[int] = []

        if cache_dir:
            cache_dir.mkdir(parents=True, exist_ok=True)
            for pno in page_numbers:
                txt_file = cache_dir / f"p{pno:03d}.txt"
                meta_file = cache_dir / f"p{pno:03d}.json"
                if txt_file.exists() and meta_file.exists():
                    try:
                        with open(meta_file, encoding="utf-8") as f:
                            meta = json.load(f)
                        src = meta.get("source")
                        meta_tier = meta.get("tier")
                        meta_sha = meta.get("sha256")
                        if (
                            src == "llamaparse"
                            and (not meta_tier or meta_tier == self.tier)
                            and (not meta_sha or meta_sha == file_hash)
                        ):
                            text = txt_file.read_text(encoding="utf-8")
                            results[pno] = PageInput(page_number=pno, text=text, source="llamaparse")
                        else:
                            missing_pages.append(pno)
                    except Exception:
                        missing_pages.append(pno)
                else:
                    missing_pages.append(pno)
        else:
            missing_pages = list(page_numbers)

        if not missing_pages:
            if progress_callback:
                progress_callback(len(page_numbers), len(page_numbers))
            return [results[pno] for pno in page_numbers]

        # 2. If API key is not configured, fallback or raise
        if not self.is_api_key_configured():
            logger.info("LLAMA_CLOUD_API_KEY is not configured; using Tesseract fallback.")
            return self._fallback_tesseract(pdf_path, page_numbers, cache_dir, progress_callback)

        # 3. Call LlamaParse API v2 in chunks of <= chunk_size (default 40)
        chunks = [
            missing_pages[i : i + chunk_size]
            for i in range(0, len(missing_pages), chunk_size)
        ]

        total_pages_count = len(page_numbers)
        if progress_callback:
            progress_callback(len(results), total_pages_count)

        def _process_chunk(chunk_pnos: list[int]) -> tuple[list[int], dict[int, str]]:
            chunk_res = self._call_llamaparse_v2(pdf_path, chunk_pnos)
            return chunk_pnos, chunk_res

        workers = min(max_workers, len(chunks))
        chunk_errors: list[Exception] = []

        if workers <= 1:
            for chunk_pnos in chunks:
                try:
                    _, chunk_res = _process_chunk(chunk_pnos)
                    chunk_range = f"{min(chunk_pnos)}-{max(chunk_pnos)}"
                    for pno, text in chunk_res.items():
                        results[pno] = PageInput(page_number=pno, text=text, source="llamaparse")
                        if cache_dir:
                            txt_file = cache_dir / f"p{pno:03d}.txt"
                            meta_file = cache_dir / f"p{pno:03d}.json"
                            txt_file.write_text(text, encoding="utf-8")
                            with open(meta_file, "w", encoding="utf-8") as mf:
                                json.dump(
                                    {
                                        "page": pno,
                                        "source": "llamaparse",
                                        "tier": self.tier,
                                        "sha256": file_hash,
                                        "chunk_range": chunk_range,
                                    },
                                    mf,
                                )
                    self.total_pages_sent += len(chunk_pnos)
                    if progress_callback:
                        progress_callback(len(results), total_pages_count)
                except Exception as exc:
                    logger.warning("LlamaParse chunk failed for pages %s: %s", chunk_pnos, exc)
                    chunk_errors.append(exc)
        else:
            with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as executor:
                future_to_chunk = {
                    executor.submit(_process_chunk, ch): ch for ch in chunks
                }
                for future in concurrent.futures.as_completed(future_to_chunk):
                    chunk_pnos = future_to_chunk[future]
                    try:
                        _, chunk_res = future.result()
                        chunk_range = f"{min(chunk_pnos)}-{max(chunk_pnos)}"
                        for pno, text in chunk_res.items():
                            results[pno] = PageInput(page_number=pno, text=text, source="llamaparse")
                            if cache_dir:
                                txt_file = cache_dir / f"p{pno:03d}.txt"
                                meta_file = cache_dir / f"p{pno:03d}.json"
                                txt_file.write_text(text, encoding="utf-8")
                                with open(meta_file, "w", encoding="utf-8") as mf:
                                    json.dump(
                                        {
                                            "page": pno,
                                            "source": "llamaparse",
                                            "tier": self.tier,
                                            "sha256": file_hash,
                                            "chunk_range": chunk_range,
                                        },
                                        mf,
                                    )
                        self.total_pages_sent += len(chunk_pnos)
                        if progress_callback:
                            progress_callback(len(results), total_pages_count)
                    except Exception as exc:
                        logger.warning("LlamaParse chunk failed for pages %s: %s", chunk_pnos, exc)
                        chunk_errors.append(exc)

        unresolved = [p for p in missing_pages if p not in results]
        if unresolved:
            logger.warning("LlamaParse could not resolve %d pages. Attempting fallback.", len(unresolved))
            if self.tesseract_fallback and self.tesseract_fallback.is_tesseract_available():
                logger.info("Falling back to Tesseract OCR for %d pages.", len(unresolved))
                fallback_results = self.tesseract_fallback.extract_all_pages(
                    pdf_path, cache_dir=cache_dir
                )
                fb_map = {p.page_number: p for p in fallback_results}
                for pno in unresolved:
                    if pno in fb_map:
                        results[pno] = fb_map[pno]
            elif chunk_errors:
                first_err = chunk_errors[0]
                if isinstance(first_err, LlamaParseError):
                    raise first_err
                raise LlamaParseError(f"LlamaParse extraction failed: {first_err}") from first_err

        if progress_callback:
            progress_callback(len(page_numbers), len(page_numbers))

        return [results.get(pno, PageInput(page_number=pno, text="", source="llamaparse")) for pno in page_numbers]

    def extract_all_pages(
        self,
        pdf_path: Path,
        cache_dir: Optional[Path] = None,
        max_workers: int = 2,
        progress_callback: Optional[Callable[[int, int], None]] = None,
        max_pages: Optional[int] = None,
    ) -> list[PageInput]:
        """Extract all pages of the document (up to max_pages if specified)."""
        total = self.get_page_count(pdf_path)
        limit = min(total, max_pages) if max_pages else total
        all_pnos = list(range(1, limit + 1))
        return self.extract_pages(
            pdf_path,
            all_pnos,
            cache_dir=cache_dir,
            progress_callback=progress_callback,
            max_workers=max_workers,
        )

    def _fallback_tesseract(
        self,
        pdf_path: Path,
        page_numbers: Sequence[int],
        cache_dir: Optional[Path],
        progress_callback: Optional[Callable[[int, int], None]],
    ) -> list[PageInput]:
        if not self.tesseract_fallback or not self.tesseract_fallback.is_tesseract_available():
            raise LlamaParseError(
                "Không có khóa API Llama Cloud và máy chủ chưa cài đặt Tesseract OCR."
            )
        res = [
            self.tesseract_fallback.get_page_text(pdf_path, pno, cache_dir=cache_dir)
            for pno in page_numbers
        ]
        if progress_callback:
            progress_callback(len(page_numbers), len(page_numbers))
        return res

    def _call_llamaparse_v2(
        self,
        pdf_path: Path,
        page_numbers: list[int],
    ) -> dict[int, str]:
        """Subset PDF to page_numbers, upload to LlamaParse v2, poll job, and return converted text."""
        try:
            import fitz
        except ImportError as exc:
            raise ImportError("PyMuPDF (fitz) is required to slice PDF pages.") from exc

        # Create subset PDF containing only the requested pages
        doc = fitz.open(pdf_path)
        sub_doc = fitz.open()
        try:
            total_doc_pages = len(doc)
            valid_pnos: list[int] = []
            for pno in page_numbers:
                if 1 <= pno <= total_doc_pages:
                    sub_doc.insert_pdf(doc, from_page=pno - 1, to_page=pno - 1)
                    valid_pnos.append(pno)
                else:
                    logger.warning("Requested page %d out of range (1..%d); skipping", pno, total_doc_pages)

            if not valid_pnos:
                return {}

            sub_pdf_bytes = sub_doc.tobytes()
        finally:
            sub_doc.close()
            doc.close()

        headers = {"Authorization": f"Bearer {self.api_key}"}
        config_payload = json.dumps({"tier": self.tier, "version": self.version})

        client_kwargs: dict[str, Any] = {"timeout": self.timeout_s}
        if self.transport:
            client_kwargs["transport"] = self.transport

        with httpx.Client(**client_kwargs) as client:
            upload_url = f"{LLAMA_API_BASE_URL}/parse/upload"
            files = {"file": ("pages.pdf", io.BytesIO(sub_pdf_bytes), "application/pdf")}
            data = {"configuration": config_payload}

            resp: Optional[httpx.Response] = None
            last_err: Optional[Exception] = None

            for attempt in range(self.max_retries + 1):
                try:
                    resp = client.post(upload_url, headers=headers, files=files, data=data)
                    if resp.status_code == 401:
                        raise LlamaParseError("Khóa LLAMA_CLOUD_API_KEY không hợp lệ hoặc đã hết hạn.")
                    if resp.status_code == 429:
                        raise LlamaParseError("Vượt quá hạn mức yêu cầu Llama Cloud.")
                    if resp.status_code >= 500:
                        if attempt < self.max_retries:
                            time.sleep(1.0)
                            continue
                        raise LlamaParseError(f"Máy chủ Llama Cloud phản hồi lỗi {resp.status_code}.")
                    resp.raise_for_status()
                    break
                except (httpx.TimeoutException, httpx.NetworkError) as net_err:
                    last_err = net_err
                    if attempt < self.max_retries:
                        time.sleep(1.5)
                        continue
                    raise LlamaParseError("Không thể kết nối tới dịch vụ Llama Cloud do lỗi mạng hoặc quá thời gian chờ.") from net_err

            if resp is None:
                raise LlamaParseError("Không nhận được phản hồi từ dịch vụ Llama Cloud.")

            upload_data = resp.json()
            job_id = upload_data.get("id") or upload_data.get("job", {}).get("id")
            if not job_id:
                raise LlamaParseError("Dịch vụ Llama Cloud không trả về mã tác vụ (job id).")

            # Poll for completion
            poll_url = f"{LLAMA_API_BASE_URL}/parse/{job_id}?expand=markdown"
            start_poll = time.time()

            while True:
                if time.time() - start_poll > self.timeout_s:
                    raise LlamaParseError(f"Quá thời gian chờ phản hồi từ Llama Cloud ({self.timeout_s:.0f}s).")

                try:
                    poll_resp = client.get(poll_url, headers=headers)
                    if poll_resp.status_code == 401:
                        raise LlamaParseError("Khóa LLAMA_CLOUD_API_KEY không hợp lệ.")
                    poll_resp.raise_for_status()
                    poll_data = poll_resp.json()
                except (httpx.TimeoutException, httpx.NetworkError) as poll_err:
                    time.sleep(self.poll_interval_s)
                    continue

                job_info = poll_data.get("job", poll_data)
                job_status = str(job_info.get("status", "")).upper()

                if job_status == "COMPLETED":
                    markdown_info = poll_data.get("markdown", {})
                    pages_list = markdown_info.get("pages", [])
                    results: dict[int, str] = {}
                    for idx, orig_pno in enumerate(valid_pnos):
                        raw_page_content = ""
                        if idx < len(pages_list):
                            page_item = pages_list[idx]
                            raw_page_content = page_item.get("markdown") or page_item.get("text") or ""
                        converted = html_table_to_pipe_text(raw_page_content)
                        results[orig_pno] = converted
                    return results

                if job_status in ("FAILED", "CANCELLED"):
                    raise LlamaParseError(f"Tác vụ Llama Cloud thất bại (trạng thái: {job_status}).")

                time.sleep(self.poll_interval_s)
