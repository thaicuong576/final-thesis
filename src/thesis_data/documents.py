"""Deterministic PDF inspection and page-aware evidence extraction."""

from dataclasses import asdict, dataclass
from hashlib import sha256
from pathlib import Path

import fitz

from .query import EvidenceQuery
from .schema import EvidenceSnippet


@dataclass(frozen=True)
class DocumentQuality:
    path: str
    content_hash: str
    page_count: int
    text_layer_pages: int
    empty_pages: int
    extraction_errors: list[str]
    table_warnings: list[str]
    parser_status: str
    hash_match: bool | None = None

    @property
    def has_text_layer(self) -> bool:
        return self.text_layer_pages > 0

    def to_json(self) -> dict:
        result = asdict(self)
        result["has_text_layer"] = self.has_text_layer
        return result


def _content_hash(path: Path) -> str:
    digest = sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _read_page_text(page: fitz.Page) -> str:
    return (page.get_text("text") or "").strip()


def inspect_document(path: Path, expected_hash: str | None = None) -> DocumentQuality:
    """Inspect a PDF without modifying it or treating scan pages as missing facts."""
    if not path.exists():
        raise FileNotFoundError(path)
    if path.suffix.lower() != ".pdf":
        raise ValueError(f"expected a PDF path: {path}")

    content_hash = _content_hash(path)
    extraction_errors: list[str] = []
    text_layer_pages = 0
    empty_pages = 0
    with fitz.open(path) as document:
        page_count = document.page_count
        for page_number, page in enumerate(document, start=1):
            try:
                if _read_page_text(page):
                    text_layer_pages += 1
                else:
                    empty_pages += 1
            except Exception as exc:  # keep the audit usable for one bad page
                extraction_errors.append(f"page:{page_number}:{type(exc).__name__}")

    if extraction_errors:
        parser_status = "extraction_error"
    elif text_layer_pages == 0:
        parser_status = "no_text_layer"
    elif empty_pages == 0:
        parser_status = "text_layer"
    else:
        parser_status = "mixed_text_layer"

    return DocumentQuality(
        path=str(path),
        content_hash=content_hash,
        page_count=page_count,
        text_layer_pages=text_layer_pages,
        empty_pages=empty_pages,
        extraction_errors=extraction_errors,
        table_warnings=["table_structure_not_evaluated"],
        parser_status=parser_status,
        hash_match=(content_hash.lower() == expected_hash.lower())
        if expected_hash
        else None,
    )


def _bounded_quote(text: str, query_text: str | None, limit: int = 2000) -> str:
    if len(text) <= limit:
        return text
    if not query_text:
        return text[:limit]
    start = text.lower().find(query_text.lower())
    if start < 0:
        return text[:limit]
    half = max(0, (limit - len(query_text)) // 2)
    left = max(0, start - half)
    right = min(len(text), left + limit)
    return text[left:right]


def _evidence_id(source_id: str, path: Path, page_number: int, query_text: str | None) -> str:
    raw = f"{source_id}|{path.name}|{page_number}|{query_text or ''}".encode()
    return sha256(raw).hexdigest()[:24]


def extract_evidence(path: Path, query: EvidenceQuery) -> list[EvidenceSnippet]:
    """Extract only page text that matches the deterministic query.

    A source identity is mandatory because a local file path alone is not a
    durable provenance reference in the gold database.
    """
    if not query.source_id:
        raise ValueError("source_id is required to create evidence")
    if not path.exists():
        raise FileNotFoundError(path)

    snippets: list[EvidenceSnippet] = []
    with fitz.open(path) as document:
        for page_number, page in enumerate(document, start=1):
            try:
                text = _read_page_text(page)
            except Exception:
                continue
            if not text:
                continue
            if query.text and query.text.lower() not in text.lower():
                continue
            first_line = next((line.strip() for line in text.splitlines() if line.strip()), None)
            snippets.append(
                EvidenceSnippet(
                    evidence_id=_evidence_id(query.source_id, path, page_number, query.text),
                    source_id=query.source_id,
                    source_document=path.name,
                    page_number=page_number,
                    section_name=first_line[:200] if first_line else None,
                    period=query.period,
                    ticker=query.ticker,
                    quote=_bounded_quote(text, query.text),
                    retrieval_score=1.0 if query.text else None,
                    parser_status="text_layer",
                    is_paginated=True,
                )
            )
    return snippets
