"""Pure logic for financial filing text extraction and candidate row extraction.

Phase: INGEST-1 (D-086).
Processes page texts (plain text layer or OCR) from annual bank financial filings,
classifies financial statement pages (Balance Sheet, Income Statement, Loan Quality Note),
identifies reporting units, column headers, and extracts candidate observation rows
for the 10 UPLOAD-1 input metrics across target and prior fiscal periods.

This module is strictly pure logic: NO I/O, NO subprocesses, NO database dependencies.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal, InvalidOperation
from difflib import SequenceMatcher
import re
from typing import Any, Dict, List, Literal, Optional, Tuple
import unicodedata

# 10 standard UPLOAD-1 input metrics
INPUT_METRICS = (
    "bank.input.npl_group_3_balance",
    "bank.input.npl_group_4_balance",
    "bank.input.npl_group_5_balance",
    "bank.input.gross_customer_loans",
    "bank.input.loan_loss_provisions",
    "bank.input.profit_after_tax",
    "bank.input.total_assets",
    "bank.input.parent_attributable_profit",
    "bank.input.total_equity",
    "bank.input.non_controlling_interests",
)

METRIC_LABELS_VI: dict[str, str] = {
    "bank.input.npl_group_3_balance": "Nợ dưới tiêu chuẩn (Nhóm 3)",
    "bank.input.npl_group_4_balance": "Nợ nghi ngờ (Nhóm 4)",
    "bank.input.npl_group_5_balance": "Nợ có khả năng mất vốn (Nhóm 5)",
    "bank.input.gross_customer_loans": "Cho vay khách hàng (dư nợ gộp)",
    "bank.input.loan_loss_provisions": "Dự phòng rủi ro cho vay khách hàng",
    "bank.input.profit_after_tax": "Lợi nhuận sau thuế",
    "bank.input.total_assets": "Tổng tài sản",
    "bank.input.parent_attributable_profit": "Lợi nhuận sau thuế của cổ đông công ty mẹ",
    "bank.input.total_equity": "Tổng vốn chủ sở hữu",
    "bank.input.non_controlling_interests": "Lợi ích của cổ đông không kiểm soát",
}

# Regex matching numbers with 3-digit thousands separators (dot or comma) and optional parentheses for negative
_NUMBER_RE = re.compile(r"\(?\s*\d{1,3}(?:[.,]\d{3})+(?:[.,]\d+)?\s*\)?|\(?\s*\d+\s*\)?")
_THOUSANDS_NUM_RE = re.compile(r"\(?\s*\d{1,3}(?:[.,]\d{3})+\s*\)?")


def fold(s: str) -> str:
    """Normalize and fold Vietnamese text to lowercase ASCII.
    
    Handles 'đ'/'Đ', decomposes unicode, strips diacritical marks, and normalizes
    spaces and punctuation for robust heuristic matching.
    """
    if not s:
        return ""
    normalized = unicodedata.normalize("NFD", s.replace("đ", "d").replace("Đ", "D"))
    stripped = "".join(ch for ch in normalized if unicodedata.category(ch) != "Mn").lower()
    return re.sub(r"[^a-z0-9 ]", " ", stripped)


def _clean_spaces(s: str) -> str:
    return re.sub(r"\s+", " ", s).strip()


@dataclass(frozen=True)
class PageInput:
    """Input representation of a single filing page."""
    page_number: int  # 1-indexed
    text: str
    source: Literal["text_layer", "ocr", "llamaparse"] = "text_layer"


@dataclass(frozen=True)
class StatementPages:
    """Classified page numbers for core statement sections."""
    balance_sheet: list[int] = field(default_factory=list)
    income_statement: list[int] = field(default_factory=list)
    loan_quality_note: list[int] = field(default_factory=list)

    def to_dict(self) -> dict[str, list[int]]:
        return {
            "balance_sheet": self.balance_sheet,
            "income_statement": self.income_statement,
            "loan_quality_note": self.loan_quality_note,
        }

    def get_selected_pages_with_overflow(self, total_pages: int, max_pages: int = 30) -> list[int]:
        """Collect all classified statement pages plus adjacent (±1) overflow pages, capped at max_pages."""
        core_pages = set(self.balance_sheet + self.income_statement + self.loan_quality_note)
        expanded: set[int] = set()
        for p in core_pages:
            if 1 <= p <= total_pages:
                expanded.add(p)
            if p - 1 >= 1:
                expanded.add(p - 1)
            if p + 1 <= total_pages:
                expanded.add(p + 1)
        sorted_pages = sorted(expanded)
        return sorted_pages[:max_pages]


@dataclass(frozen=True)
class RowIssue:
    """An issue or warning encountered while extracting a candidate row."""
    code: str
    severity: Literal["error", "warning", "info"] = "warning"
    message_vi: str = ""

    def to_dict(self) -> dict[str, str]:
        return {"code": self.code, "severity": self.severity, "message_vi": self.message_vi}


@dataclass(frozen=True)
class RowAlternative:
    """Alternative line match candidate for auditing and user selection."""
    value_billion_vnd: Optional[str]
    raw_text: str
    row_label: str
    page: int
    score: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "value_billion_vnd": self.value_billion_vnd,
            "raw_text": self.raw_text,
            "row_label": self.row_label,
            "page": self.page,
            "score": round(self.score, 3),
        }


@dataclass(frozen=True)
class CandidateRow:
    """An extracted candidate metric observation row."""
    row_id: str
    metric_id: str
    label_vi: str
    period_role: Literal["target", "prior"]
    period_id: str
    value_billion_vnd: Optional[str]
    extracted_value_billion_vnd: Optional[str]
    raw_text: Optional[str]
    row_label: Optional[str]
    page: Optional[int]
    source: Optional[Literal["text_layer", "ocr", "llamaparse", "user"]]
    status: Literal["candidate", "needs_review", "missing"]
    edited: bool = False
    confirmed: bool = False
    issues: list[RowIssue] = field(default_factory=list)
    alternatives: list[RowAlternative] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "row_id": self.row_id,
            "metric_id": self.metric_id,
            "label_vi": self.label_vi,
            "period_role": self.period_role,
            "period_id": self.period_id,
            "value_billion_vnd": self.value_billion_vnd,
            "extracted_value_billion_vnd": self.extracted_value_billion_vnd,
            "raw_text": self.raw_text,
            "row_label": self.row_label,
            "page": self.page,
            "source": self.source,
            "status": self.status,
            "edited": self.edited,
            "confirmed": self.confirmed,
            "issues": [i.to_dict() for i in self.issues],
            "alternatives": [a.to_dict() for a in self.alternatives],
        }


@dataclass(frozen=True)
class ExtractionResult:
    """Complete candidate extraction result for a financial filing."""
    filing_id: str
    entity_id: str
    display_name: str
    fiscal_year: int
    reporting_scope: str
    page_count: int
    text_layer_pages: int
    ocr_pages: int
    statement_pages: StatementPages
    unit_detected: Optional[str]
    rows: list[CandidateRow]
    limitations_vi: list[str] = field(default_factory=list)
    ocr_provider: Literal["text_layer", "tesseract", "llamaparse", "mixed", "sample"] = "text_layer"
    validation: Optional[dict[str, Any]] = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "filing_id": self.filing_id,
            "entity_id": self.entity_id,
            "display_name": self.display_name,
            "fiscal_year": self.fiscal_year,
            "reporting_scope": self.reporting_scope,
            "page_count": self.page_count,
            "ocr_provider": self.ocr_provider,
            "text_layer_pages": self.text_layer_pages,
            "ocr_pages": self.ocr_pages,
            "statement_pages": self.statement_pages.to_dict(),
            "unit_detected": self.unit_detected,
            "rows": [r.to_dict() for r in self.rows],
            "validation": self.validation,
            "limitations_vi": self.limitations_vi,
        }


# =============================================================================
# Page Classification
# =============================================================================

def is_table_of_contents(folded_text: str) -> bool:
    """Detect whether a page is likely a Table of Contents rather than a statement."""
    if "muc luc" in folded_text or "danh muc" in folded_text:
        return True
    # If the page has lots of dot sequences "...." and page keywords
    dot_count = folded_text.count("....") or folded_text.count(". . .")
    if dot_count >= 5 and "trang" in folded_text:
        return True
    return False


def score_page_classification(folded_text: str) -> dict[str, float]:
    """Score a page's likelihood of being Balance Sheet, Income Statement, or Loan Quality Note."""
    scores = {"balance_sheet": 0.0, "income_statement": 0.0, "loan_quality_note": 0.0}

    # 1. Balance Sheet Cues
    if any(k in folded_text for k in ["bao cao tinh hinh tai chinh", "can doi ke toan", "bang can doi"]):
        scores["balance_sheet"] += 15.0
    if "tong tai san" in folded_text or "tong cong tai san" in folded_text or "tong tai san co" in folded_text:
        scores["balance_sheet"] += 8.0
    if "von chu so huu" in folded_text:
        scores["balance_sheet"] += 5.0
    if "no phai tra" in folded_text:
        scores["balance_sheet"] += 4.0

    # 2. Income Statement Cues
    if any(k in folded_text for k in ["ket qua hoat dong kinh doanh", "bao cao ket qua hoat dong", "ket qua kinh doanh"]):
        scores["income_statement"] += 15.0
    if "loi nhuan sau thue" in folded_text:
        scores["income_statement"] += 8.0
    if "thu nhap lai thuan" in folded_text or "thu nhap lai" in folded_text:
        scores["income_statement"] += 5.0
    if "co dong cua ngan hang" in folded_text or "co dong cong ty me" in folded_text or "co dong ngan hang" in folded_text:
        scores["income_statement"] += 5.0

    # 3. Loan Quality Note & Provisions Cues (Full Page Scan)
    if any(k in folded_text for k in ["chat luong no", "phan tich chat luong no", "theo chat luong no", "phan loai no"]):
        scores["loan_quality_note"] += 15.0
    if "no duoi tieu chuan" in folded_text or "no dui tieu chuan" in folded_text:
        scores["loan_quality_note"] += 15.0
    if "no nghi ngo" in folded_text:
        scores["loan_quality_note"] += 10.0
    if "no co kha nang mat von" in folded_text or "mat von" in folded_text:
        scores["loan_quality_note"] += 10.0
    if any(k in folded_text for k in ["du phong rui ro cho vay", "du phong cho vay khach hang", "du phong chung", "du phong cu the"]):
        scores["loan_quality_note"] += 12.0
    # Group indicators
    groups_found = sum(1 for g in ["nhom 1", "nhom 2", "nhom 3", "nhom 4", "nhom 5"] if g in folded_text)
    if groups_found >= 3:
        scores["loan_quality_note"] += 15.0

    return scores


def classify_pages(pages: list[PageInput]) -> StatementPages:
    """Classify the collection of pages into statement sections."""
    bs_candidates: list[tuple[int, float]] = []
    is_candidates: list[tuple[int, float]] = []
    lq_candidates: list[tuple[int, float]] = []

    for p in pages:
        folded = fold(p.text)
        if is_table_of_contents(folded):
            continue

        scores = score_page_classification(folded)
        if scores["balance_sheet"] >= 10.0:
            bs_candidates.append((p.page_number, scores["balance_sheet"]))
        if scores["income_statement"] >= 10.0:
            is_candidates.append((p.page_number, scores["income_statement"]))
        if scores["loan_quality_note"] >= 10.0:
            lq_candidates.append((p.page_number, scores["loan_quality_note"]))

    def _pick_cluster(candidates: list[tuple[int, float]], max_count: int = 3) -> list[int]:
        if not candidates:
            return []
        candidates.sort(key=lambda x: x[1], reverse=True)
        top_page = candidates[0][0]
        selected = [top_page]
        for pno, _ in candidates[1:]:
            if abs(pno - top_page) <= 2 and len(selected) < max_count and pno not in selected:
                selected.append(pno)
        return sorted(selected)

    # For loan quality note, scan across the whole document:
    # Pick the top candidate page and any distinct high-scoring note pages (e.g. provisions note)
    selected_lq: list[int] = []
    if lq_candidates:
        lq_candidates.sort(key=lambda x: x[1], reverse=True)
        for pno, score in lq_candidates:
            if pno not in selected_lq:
                # Add if it's the top page, near an existing selected note page, or very high confidence
                if not selected_lq or any(abs(pno - existing) <= 2 for existing in selected_lq) or score >= 20.0:
                    selected_lq.append(pno)
                    if len(selected_lq) >= 4:
                        break
        selected_lq.sort()

    return StatementPages(
        balance_sheet=_pick_cluster(bs_candidates, max_count=3),
        income_statement=_pick_cluster(is_candidates, max_count=2),
        loan_quality_note=selected_lq,
    )


# =============================================================================
# Unit Normalization
# =============================================================================

# Regex patterns for unit detection in Vietnamese banking filings and OCR artifacts
_MILLION_RE = re.compile(
    r"\btri[a-z]{0,3}u\s*(?:vnd|d[a-z]{0,3}ng|d\b)"
    r"|\btr[.,]?\s*vnd\b"
    r"|\bmillion\b"
    r"|\b(?:don\s*vi(?:\s*tinh)?|dvt|dvi|bon\s*vi)\s*[:=]?\s*(?:tri[a-z]{0,3}u|million)\b",
    re.IGNORECASE,
)
_THOUSAND_RE = re.compile(
    r"\b(?:nghin|ngan)\s*(?:vnd|d[a-z]{0,3}ng|d\b)\b"
    r"|\bthousand\b"
    r"|\b(?:don\s*vi(?:\s*tinh)?|dvt)\s*[:=]?\s*(?:nghin|ngan)\b",
    re.IGNORECASE,
)
_BILLION_RE = re.compile(
    r"\b(?:ty|ti)\s*(?:vnd|d[a-z]{0,3}ng|d\b)\b"
    r"|\bbillion\b"
    r"|\b(?:don\s*vi(?:\s*tinh)?|dvt)\s*[:=]?\s*(?:ty|ti)\b",
    re.IGNORECASE,
)
_VND_EXPLICIT_RE = re.compile(
    r"\b(?:don\s*vi(?:\s*tinh)?|dvt|dvi|bon\s*vi)\s*[:=]?\s*(?:vnd|dong)\b",
    re.IGNORECASE,
)


def detect_unit(text: str) -> Optional[str]:
    """Detect monetary reporting unit from page header, table header, or text lines.

    Checks the first 35 lines of the page text (including table header cells in pipe format),
    and the first 2000 chars for explicit unit indicators. Never lets a bare 'vnd' or 'dong'
    mention imply unit = vnd without an explicit unit indicator (e.g. 'Đơn vị tính: VND').
    """
    lines = text.splitlines()[:35]
    for line in lines:
        f = fold(line)
        if _MILLION_RE.search(f):
            return "million_vnd"
        if _THOUSAND_RE.search(f):
            return "thousand_vnd"
        if _BILLION_RE.search(f):
            return "billion_vnd"
        if _VND_EXPLICIT_RE.search(f):
            return "vnd"
        # Also check individual cells if line is pipe-separated
        if "|" in line:
            for cell in line.split("|"):
                f_cell = fold(cell)
                if _MILLION_RE.search(f_cell):
                    return "million_vnd"
                if _THOUSAND_RE.search(f_cell):
                    return "thousand_vnd"
                if _BILLION_RE.search(f_cell):
                    return "billion_vnd"

    # Also check the first 2000 characters
    f_head = fold(text[:2000])
    if _MILLION_RE.search(f_head):
        return "million_vnd"
    if _THOUSAND_RE.search(f_head):
        return "thousand_vnd"
    if _BILLION_RE.search(f_head):
        return "billion_vnd"
    if _VND_EXPLICIT_RE.search(f_head):
        return "vnd"

    return None


def unit_to_multiplier(unit: Optional[str]) -> Decimal:
    """Return multiplier to convert unit to billion VND.

    Requires an explicit valid unit. Does not silently default.
    """
    if unit == "million_vnd":
        return Decimal("0.001")
    if unit == "thousand_vnd":
        return Decimal("0.000001")
    if unit == "vnd":
        return Decimal("0.000000001")
    if unit == "billion_vnd":
        return Decimal("1.0")
    raise ValueError(f"Explicit unit required; unknown or None unit: {unit!r}")


# =============================================================================
# Column Header Detection
# =============================================================================

@dataclass(frozen=True)
class ColumnHeaderInfo:
    target_year: int
    prior_year: int
    target_col_idx: int = 0
    prior_col_idx: int = 1
    has_target_header: bool = False
    has_prior_header: bool = False
    period_mismatch: bool = False
    details_vi: str = ""


def detect_column_headers(lines: list[str], target_year: int) -> ColumnHeaderInfo:
    """Detect column headers for target and prior fiscal periods in table top lines."""
    prior_year = target_year - 1
    target_str = str(target_year)
    prior_str = str(prior_year)

    has_target = False
    has_prior = False
    period_mismatch = False

    header_text = fold(" ".join(lines[:20]))

    # Check for target year indicators
    if target_str in header_text or f"31 12 {target_str}" in header_text or "nam nay" in header_text or "ky nay" in header_text or "so cuoi nam" in header_text:
        has_target = True

    # Check for prior year indicators
    if prior_str in header_text or f"31 12 {prior_str}" in header_text or f"01 01 {target_str}" in header_text or "nam truoc" in header_text or "ky truoc" in header_text or "so dau nam" in header_text:
        has_prior = True

    # Check if a different year is prominently displayed as target
    other_years = re.findall(r"\b(20[12]\d)\b", header_text)
    if other_years:
        for y in other_years:
            iy = int(y)
            if iy not in (target_year, prior_year, target_year + 1):
                # An unexpected year appeared
                period_mismatch = True

    return ColumnHeaderInfo(
        target_year=target_year,
        prior_year=prior_year,
        target_col_idx=0,
        prior_col_idx=1,
        has_target_header=has_target,
        has_prior_header=has_prior,
        period_mismatch=period_mismatch,
    )


# =============================================================================
# Number Parsing
# =============================================================================

def parse_number_token(tok: str) -> Optional[Decimal]:
    """Parse a single raw number token into a Decimal, handling parens, dots, commas."""
    tok = tok.strip()
    if not tok or tok in ("-", "—", "–"):
        return Decimal("0")

    is_negative = False
    if tok.startswith("(") and tok.endswith(")"):
        is_negative = True
        tok = tok[1:-1].strip()

    # Determine thousand separator:
    # Vietnamese financial filings typically use dot '.' as thousands separator and comma ',' as decimal.
    # OCR sometimes uses comma ',' as thousand separator.
    # If the token has both: e.g. 1.234,56 or 1,234.56
    if "." in tok and "," in tok:
        if tok.rfind(",") > tok.rfind("."):
            # 1.234,56: dot is thousand, comma is decimal
            tok = tok.replace(".", "").replace(",", ".")
        else:
            # 1,234.56: comma is thousand, dot is decimal
            tok = tok.replace(",", "")
    elif "." in tok:
        # Check if dot is thousand separator or decimal point
        parts = tok.split(".")
        if all(len(p) == 3 for p in parts[1:]) and len(parts) > 1:
            tok = "".join(parts)
        elif len(parts) == 2 and len(parts[1]) != 3:
            # decimal
            pass
        else:
            tok = "".join(parts)
    elif "," in tok:
        parts = tok.split(",")
        if all(len(p) == 3 for p in parts[1:]) and len(parts) > 1:
            tok = "".join(parts)
        elif len(parts) == 2 and len(parts[1]) != 3:
            tok = parts[0] + "." + parts[1]
        else:
            tok = "".join(parts)

    try:
        val = Decimal(tok)
        return -val if is_negative else val
    except InvalidOperation:
        return None


def extract_numbers_from_line(line: str) -> list[Decimal]:
    """Extract numeric values from a table row line."""
    tokens = _NUMBER_RE.findall(line)
    if not tokens:
        return []

    # If the line has percentages (e.g. 97,19 or 96.92 or followed by %),
    # filter them out or distinguish them from amounts
    results: list[Decimal] = []
    for tok in tokens:
        # Check if token is percentage-like: followed by '%' in line or has 2 decimals and < 100
        clean = tok.strip("() ")
        # Skip small single digits that are likely row numbers at the start of line
        val = parse_number_token(tok)
        if val is not None:
            results.append(val)

    return results


_AMOUNT_GROUPED_RE = re.compile(r"\(?\s*\d{1,3}(?:[.,]\d{3})+(?:[.,]\d+)?\s*\)?")


def extract_amount_columns_from_line(line: str) -> list[Decimal]:
    """Extract specifically the monetary amount columns from a financial table row.

    Accepts both Tesseract/text-layer plain lines and pipe-separated table-flattened
    lines produced by LlamaParse (e.g. "label | 686.777.352 | 580.686.248").

    Prioritizes numbers formatted with thousands separators (dots or commas) which
    represent currency amounts in Vietnamese financial filings, naturally ignoring
    row numbering ('Nhóm 3'), note references ('22', '33.2'), and percentages ('0,19').
    """
    # 1. Pipe-form (LlamaParse table-flattened markdown)
    if is_pipe_form(line):
        return extract_amounts_from_pipe_line(line)

    # 2. Primary for plain lines: search for numbers with 3-digit thousands separators
    grouped_tokens = _AMOUNT_GROUPED_RE.findall(line)
    if grouped_tokens:
        amounts: list[Decimal] = []
        for tok in grouped_tokens:
            dec = parse_number_token(tok)
            if dec is not None:
                amounts.append(dec)
        if amounts:
            return amounts

    # 2. Fallback: check trailing tokens at the end of the line (e.g. for 0, -, nil)
    tokens = _NUMBER_RE.findall(line)
    if not tokens:
        return []

    parsed: list[Decimal] = []
    for tok in tokens:
        dec = parse_number_token(tok)
        if dec is not None:
            parsed.append(dec)

    # Return the last 2 amount tokens if present
    if len(parsed) >= 2:
        return parsed[-2:]
    return parsed


# ---------------------------------------------------------------------------
# Pipe-form line support (LlamaParse / table-flattened markdown)
# Lines look like: "Nhóm 3 - Nợ dưới tiêu chuẩn | 686.777.352 | 580.686.248"
# Header lines look like: "| 31.12.2025 Triệu VND | 31.12.2024 Triệu VND"
# ---------------------------------------------------------------------------

_PIPE_ROW_RE = re.compile(r"\|")


def is_pipe_form(line: str) -> bool:
    """Return True if the line appears to be a pipe-separated table row.

    A line qualifies when it contains at least two '|' separators,
    which is characteristic of LlamaParse HTML <table>-flattened output.
    """
    return line.count("|") >= 2


def extract_amounts_from_pipe_line(line: str) -> list[Decimal]:
    """Extract monetary amounts from a pipe-separated table row.

    Splits on '|', skips the first cell (label), then extracts one amount
    per remaining cell in order.  Non-numeric cells (e.g. empty, dates, unit
    labels) are skipped.  Returns at most the first two valid amounts found
    (target column first, prior column second).

    Example input::

        Nhóm 3 - Nợ dưới tiêu chuẩn | 686.777.352 | 580.686.248

    Returns: [Decimal('686777352'), Decimal('580686248')]
    """
    parts = _PIPE_ROW_RE.split(line)
    # parts[0] is the row label; numeric amounts start at index 1
    amounts: list[Decimal] = []
    for cell in parts[1:]:
        cell = cell.strip()
        if not cell:
            continue
        # Only extract if the cell contains a grouped number (thousands-separated)
        grouped = _AMOUNT_GROUPED_RE.findall(cell)
        if grouped:
            for tok in grouped:
                dec = parse_number_token(tok)
                if dec is not None:
                    amounts.append(dec)
            if len(amounts) >= 2:
                break
    return amounts[:2]


# =============================================================================
# Label Matching Specifications
# =============================================================================

@dataclass(frozen=True)
class MetricMatchSpec:
    metric_id: str
    target_section: Literal["balance_sheet", "income_statement", "loan_quality_note"]
    primary_labels: tuple[str, ...]
    exclude_terms: tuple[str, ...] = ()
    prefer_total: bool = False
    allow_zero_default: bool = False


METRIC_SPECS: tuple[MetricMatchSpec, ...] = (
    # NPL Groups 3, 4, 5
    MetricMatchSpec(
        metric_id="bank.input.npl_group_3_balance",
        target_section="loan_quality_note",
        primary_labels=(
            "nhom 3 no duoi tieu chuan",
            "nhom 3",
            "no duoi tieu chuan",
            "no dui tieu chuan",
            "nhom 3 no dui tieu chuan",
            "3 no duoi tieu chuan",
        ),
        exclude_terms=("nhom 1", "nhom 2", "nhom 4", "nhom 5", "tong cong"),
    ),
    MetricMatchSpec(
        metric_id="bank.input.npl_group_4_balance",
        target_section="loan_quality_note",
        primary_labels=(
            "nhom 4 no nghi ngo",
            "nhom 4",
            "no nghi ngo",
            "nhom 4 no nghi ngo",
            "4 no nghi ngo",
        ),
        exclude_terms=("nhom 1", "nhom 2", "nhom 3", "nhom 5", "tong cong"),
    ),
    MetricMatchSpec(
        metric_id="bank.input.npl_group_5_balance",
        target_section="loan_quality_note",
        primary_labels=(
            "nhom 5 no co kha nang mat von",
            "nhom 5",
            "no co kha nang mat von",
            "kha nang mat von",
            "mat von",
            "5 no co kha nang mat von",
        ),
        exclude_terms=("nhom 1", "nhom 2", "nhom 3", "nhom 4", "tong cong"),
    ),
    # Gross customer loans: in loan quality note total row OR balance sheet "Cho vay khách hàng"
    MetricMatchSpec(
        metric_id="bank.input.gross_customer_loans",
        target_section="loan_quality_note",
        primary_labels=(
            "tong cong",
            "tong nhom 1 5",
            "tong",
            "cho vay khach hang",
            "tong cong du no",
            "tong du no",
            "1 cho vay khach hang",
        ),
        prefer_total=True,
    ),
    # Loan loss provisions: in balance sheet OR loan quality note
    MetricMatchSpec(
        metric_id="bank.input.loan_loss_provisions",
        target_section="balance_sheet",
        primary_labels=(
            "du phong rui ro cho vay khach hang",
            "du phong rui ro cho vay",
            "2 du phong rui ro cho vay khach hang",
            "du phong cho vay khach hang",
            "tong du phong rui ro cho vay",
            "du phong rui ro",
        ),
        exclude_terms=("chung khoan", "dau tu", "tai san co khac"),
    ),
    # Profit after tax: in income statement
    MetricMatchSpec(
        metric_id="bank.input.profit_after_tax",
        target_section="income_statement",
        primary_labels=(
            "loi nhuan sau thue",
            "loi nhuan sau thue thu nhap doanh nghiep",
            "loi nhuan sau thue tndn",
            "tong loi nhuan sau thue",
            "xiii loi nhuan sau thue",
            "xii loi nhuan sau thue",
        ),
        exclude_terms=("truoc thue",),
    ),
    # Parent attributable profit: in income statement
    MetricMatchSpec(
        metric_id="bank.input.parent_attributable_profit",
        target_section="income_statement",
        primary_labels=(
            "loi nhuan thuan cua ngan hang me",
            "loi nhuan thuan cua chu so huu",
            "loi nhuan sau thue thuoc ve ngan hang me",
            "loi nhuan thuan cua co dong cua ngan hang",
            "loi nhuan thuan cua co dong ngan hang",
            "co dong cua ngan hang",
            "co dong cong ty me",
            "co dong ngan hang",
            "loi nhuan sau thue cua co dong cong ty me",
        ),
        exclude_terms=("thieu so", "khong kiem soat"),
    ),
    # Total assets: in balance sheet
    MetricMatchSpec(
        metric_id="bank.input.total_assets",
        target_section="balance_sheet",
        primary_labels=(
            "tong tai san",
            "tong cong tai san",
            "tong tai san co",
            "tong cong tai san co",
        ),
        exclude_terms=("tai san ngan han", "tai san dai han", "tai san co dinh"),
    ),
    # Total equity: in balance sheet
    MetricMatchSpec(
        metric_id="bank.input.total_equity",
        target_section="balance_sheet",
        primary_labels=(
            "tong von chu so huu",
            "von chu so huu",
            "tong von",
            "von va cac quy",
            "tong cong von chu so huu",
        ),
        exclude_terms=("no phai tra va von chu so huu", "tong no phai tra va"),
    ),
    # Non-controlling interests: in balance sheet
    MetricMatchSpec(
        metric_id="bank.input.non_controlling_interests",
        target_section="balance_sheet",
        primary_labels=(
            "loi ich cua co dong khong kiem soat",
            "loi ich co dong khong kiem soat",
            "loi ich cua co dong thieu so",
            "loi ich co dong thieu so",
            "co dong khong kiem soat",
            "co dong thieu so",
        ),
        allow_zero_default=True,
    ),
)


# =============================================================================
# Match Scoring and Line Finding
# =============================================================================

def match_score_for_spec(line_text: str, spec: MetricMatchSpec) -> float:
    """Calculate similarity score of a line against a metric's label specification."""
    folded_line = fold(line_text)
    if not folded_line:
        return 0.0

    # Reject if line contains an exclude term
    for exc in spec.exclude_terms:
        if exc in folded_line:
            return 0.0

    # Specific heuristic boosts for NPL groups to avoid OCR noise confusion
    if spec.metric_id == "bank.input.npl_group_3_balance":
        if "3" in folded_line and any(k in folded_line for k in ["nhom", "nhem", "nhdem", "tieu chuan", "dui", "duoi"]):
            return 0.95
    elif spec.metric_id == "bank.input.npl_group_4_balance":
        if "4" in folded_line and any(k in folded_line for k in ["nhom", "nhem", "nhdem", "nghi ngo", "nghi"]):
            return 0.95
    elif spec.metric_id == "bank.input.npl_group_5_balance":
        if "5" in folded_line and any(k in folded_line for k in ["nhom", "nhem", "nhdem", "mat von", "mat v"]):
            return 0.95

    # Check for exact substring match
    best_score = 0.0
    for target in spec.primary_labels:
        if target in folded_line:
            score = len(target) / max(len(folded_line.split()), 1)
            # Perfect substring match is high score
            score = max(score, 0.85)
            if score > best_score:
                best_score = score
        else:
            # Fuzzy match on the prefix tokens
            words = folded_line.split()
            target_words = target.split()
            prefix = " ".join(words[: len(target_words) + 3])
            ratio = SequenceMatcher(None, target, prefix).ratio()
            if ratio > 0.65 and ratio > best_score:
                best_score = ratio

    return best_score


# =============================================================================
# Extraction Pipeline Core
# =============================================================================

def extract_candidates_from_pages(
    pages: list[PageInput],
    *,
    entity_id: str,
    fiscal_year: int,
    reporting_scope: str = "consolidated",
    display_name: Optional[str] = None,
    filing_id: Optional[str] = None,
) -> ExtractionResult:
    """Execute pure candidate extraction over page texts according to INGEST-1 spec."""
    fid = filing_id or "fl-synthetic"
    ename = display_name or entity_id.upper()
    target_period = f"{fiscal_year}_Q4"
    prior_period = f"{fiscal_year - 1}_Q4"

    # Count pages by source
    text_layer_count = sum(1 for p in pages if p.source == "text_layer")
    ocr_count = sum(1 for p in pages if p.source == "ocr")
    llamaparse_count = sum(1 for p in pages if p.source == "llamaparse")

    # 1. Classify pages
    statement_pages = classify_pages(pages)

    # 2. Detect global unit
    # Prefer statement pages first (balance sheet, income statement, loan note), checking their
    # header lines (first 25 lines) and table column headers. If not found, inspect all pages.
    detected_unit: Optional[str] = None
    statement_page_nums = set(
        statement_pages.balance_sheet
        + statement_pages.income_statement
        + statement_pages.loan_quality_note
    )
    for p in pages:
        if p.page_number in statement_page_nums:
            u = detect_unit(p.text)
            if u:
                detected_unit = u
                break

    if not detected_unit:
        for p in pages:
            u = detect_unit(p.text)
            if u:
                detected_unit = u
                break

    unit_multiplier: Optional[Decimal] = (
        unit_to_multiplier(detected_unit) if detected_unit is not None else None
    )

    # Build page lookup
    pages_by_num = {p.page_number: p for p in pages}

    # Helper to get candidate pages for a section
    def _pages_for_section(section_name: str) -> list[PageInput]:
        pnums = getattr(statement_pages, section_name, [])
        return [pages_by_num[n] for n in pnums if n in pages_by_num]

    candidate_rows: list[CandidateRow] = []

    # Cache profit after tax values in case parent attributable profit needs fallback
    cached_pat: dict[str, Optional[Decimal]] = {"target": None, "prior": None}
    cached_pat_raw: dict[str, str] = {"target": "", "prior": ""}
    cached_pat_page: dict[str, int] = {"target": 1, "prior": 1}
    cached_pat_source: dict[str, str] = {"target": "ocr", "prior": "ocr"}

    # Process each metric
    for spec in METRIC_SPECS:
        # Determine candidate pages to search
        candidate_p = _pages_for_section(spec.target_section)
        # Fallbacks: for gross customer loans / provisions, can check both loan note and balance sheet
        if spec.metric_id == "bank.input.gross_customer_loans" and not candidate_p:
            candidate_p = _pages_for_section("balance_sheet")
        elif spec.metric_id == "bank.input.loan_loss_provisions" and not candidate_p:
            candidate_p = _pages_for_section("loan_quality_note")

        matched_lines: list[tuple[float, PageInput, str, list[Decimal]]] = []

        for p in candidate_p:
            for line in p.text.splitlines():
                line_str = _clean_spaces(line)
                if not line_str:
                    continue
                score = match_score_for_spec(line_str, spec)
                if score >= 0.5:
                    amounts = extract_amount_columns_from_line(line_str)
                    if amounts or spec.allow_zero_default:
                        matched_lines.append((score, p, line_str, amounts))

        # Sort matches by score descending
        matched_lines.sort(key=lambda x: x[0], reverse=True)

        # Fallback handling for parent_attributable_profit: if no line found, equals profit_after_tax
        if not matched_lines and spec.metric_id == "bank.input.parent_attributable_profit" and cached_pat["target"] is not None:
            # Use profit after tax as fallback
            for role, pid, pval in [("target", target_period, cached_pat["target"]), ("prior", prior_period, cached_pat["prior"])]:
                r_id = f"{spec.metric_id}:{role}"
                c_val = str(pval) if pval is not None else None
                candidate_rows.append(
                    CandidateRow(
                        row_id=r_id,
                        metric_id=spec.metric_id,
                        label_vi=METRIC_LABELS_VI[spec.metric_id],
                        period_role=role,  # type: ignore[arg-type]
                        period_id=pid,
                        value_billion_vnd=c_val,
                        extracted_value_billion_vnd=c_val,
                        raw_text=cached_pat_raw.get(role),
                        row_label="Lợi nhuận sau thuế (tương đương cổ đông mẹ do không tách riêng CĐTSKT)",
                        page=cached_pat_page.get(role),
                        source=cached_pat_source.get(role, "ocr"),  # type: ignore[arg-type]
                        status="candidate" if c_val is not None else "missing",
                        edited=False,
                        confirmed=False,
                        issues=[
                            RowIssue(
                                code="parent_profit_inferred_from_pat",
                                severity="info",
                                message_vi="Báo cáo không trình bày riêng lợi nhuận cổ đông mẹ; lấy tương đương lợi nhuận sau thuế.",
                            )
                        ] if c_val is not None else [],
                        alternatives=[],
                    )
                )
            continue

        # Handling for non_controlling_interests: if not presented, default 0
        if not matched_lines and spec.allow_zero_default:
            bs_p = _pages_for_section("balance_sheet")
            ref_page = bs_p[0].page_number if bs_p else 1
            ref_source = bs_p[0].source if bs_p else "ocr"
            for role, pid in [("target", target_period), ("prior", prior_period)]:
                r_id = f"{spec.metric_id}:{role}"
                candidate_rows.append(
                    CandidateRow(
                        row_id=r_id,
                        metric_id=spec.metric_id,
                        label_vi=METRIC_LABELS_VI[spec.metric_id],
                        period_role=role,  # type: ignore[arg-type]
                        period_id=pid,
                        value_billion_vnd="0.000",
                        extracted_value_billion_vnd="0.000",
                        raw_text=None,
                        row_label="Lợi ích cổ đông không kiểm soát (không phát sinh)",
                        page=ref_page,
                        source=ref_source,  # type: ignore[arg-type]
                        status="candidate",
                        edited=False,
                        confirmed=False,
                        issues=[
                            RowIssue(
                                code="nci_not_presented",
                                severity="info",
                                message_vi="Không tìm thấy dòng lợi ích cổ đông thiểu số; ghi nhận 0.000.",
                            )
                        ],
                        alternatives=[],
                    )
                )
            continue

        if not matched_lines:
            # Row missing
            for role, pid in [("target", target_period), ("prior", prior_period)]:
                r_id = f"{spec.metric_id}:{role}"
                candidate_rows.append(
                    CandidateRow(
                        row_id=r_id,
                        metric_id=spec.metric_id,
                        label_vi=METRIC_LABELS_VI[spec.metric_id],
                        period_role=role,  # type: ignore[arg-type]
                        period_id=pid,
                        value_billion_vnd=None,
                        extracted_value_billion_vnd=None,
                        raw_text=None,
                        row_label=None,
                        page=None,
                        source=None,
                        status="missing",
                        edited=False,
                        confirmed=False,
                        issues=[
                            RowIssue(
                                code="row_not_found",
                                severity="error",
                                message_vi=f"Không tìm thấy dòng tương ứng với chỉ tiêu {spec.metric_id}.",
                            )
                        ],
                        alternatives=[],
                    )
                )
            continue

        # Best match line
        best_score, best_page, best_line, best_amounts = matched_lines[0]
        col_info = detect_column_headers(best_page.text.splitlines(), fiscal_year)

        # Build alternatives (up to 3 other matches)
        alternatives: list[RowAlternative] = []
        for alt_score, alt_page, alt_line, alt_amounts in matched_lines[1:4]:
            alt_val = None
            if alt_amounts and unit_multiplier is not None:
                alt_val = str((alt_amounts[0] * unit_multiplier).quantize(Decimal("0.001")))
            alternatives.append(
                RowAlternative(
                    value_billion_vnd=alt_val,
                    raw_text=alt_line,
                    row_label=alt_line,
                    page=alt_page.page_number,
                    score=alt_score,
                )
            )

        # Extract target and prior amounts from best_amounts
        val_target: Optional[Decimal] = None
        val_prior: Optional[Decimal] = None

        if len(best_amounts) >= 2:
            val_target = best_amounts[0]
            val_prior = best_amounts[1]
        elif len(best_amounts) == 1:
            val_target = best_amounts[0]

        # Convert to billion VND
        # Note: loan_loss_provisions in balance sheet is displayed negative (in parens),
        # but in accounting metric calculations it represents positive reserve balance.
        if spec.metric_id == "bank.input.loan_loss_provisions":
            if val_target is not None and val_target < 0:
                val_target = abs(val_target)
            if val_prior is not None and val_prior < 0:
                val_prior = abs(val_prior)

        if unit_multiplier is not None:
            target_billion = (
                (val_target * unit_multiplier).quantize(Decimal("0.001"))
                if val_target is not None
                else None
            )
            prior_billion = (
                (val_prior * unit_multiplier).quantize(Decimal("0.001"))
                if val_prior is not None
                else None
            )
        else:
            target_billion = None
            prior_billion = None

        if spec.metric_id == "bank.input.profit_after_tax":
            cached_pat["target"] = target_billion
            cached_pat["prior"] = prior_billion
            cached_pat_raw["target"] = best_line
            cached_pat_raw["prior"] = best_line
            cached_pat_page["target"] = best_page.page_number
            cached_pat_page["prior"] = best_page.page_number
            cached_pat_source["target"] = best_page.source
            cached_pat_source["prior"] = best_page.source

        # Build CandidateRows for target and prior periods
        for role, pid, b_val in [
            ("target", target_period, target_billion),
            ("prior", prior_period, prior_billion),
        ]:
            issues: list[RowIssue] = []
            row_status: Literal["candidate", "needs_review", "missing"] = "candidate"

            if detected_unit is None:
                row_status = "needs_review"
                issues.append(
                    RowIssue(
                        code="unit_unknown",
                        severity="warning",
                        message_vi="Không phát hiện được đơn vị tiền tệ trên trang báo cáo; cần người dùng xác nhận.",
                    )
                )

            if b_val is None:
                if detected_unit is not None:
                    row_status = "missing"
                    issues.append(
                        RowIssue(
                            code="column_missing",
                            severity="error",
                            message_vi=f"Không tìm thấy cột số liệu cho kỳ {pid} trên dòng này.",
                        )
                    )
            else:
                if not col_info.has_target_header and role == "target":
                    row_status = "needs_review"
                    issues.append(
                        RowIssue(
                            code="target_column_unconfirmed",
                            severity="warning",
                            message_vi="Tiêu đề cột kỳ mục tiêu không rõ ràng; cần người dùng kiểm tra lại.",
                        )
                    )
                if not col_info.has_prior_header and role == "prior":
                    row_status = "needs_review"
                    issues.append(
                        RowIssue(
                            code="prior_column_unconfirmed",
                            severity="warning",
                            message_vi="Tiêu đề cột kỳ so sánh không rõ ràng; cần người dùng kiểm tra lại.",
                        )
                    )
                if col_info.period_mismatch:
                    issues.append(
                        RowIssue(
                            code="period_mismatch",
                            severity="warning",
                            message_vi="Phát hiện năm khác trong tiêu đề bảng; cần đối chiếu ngày báo cáo.",
                        )
                    )
                if best_score < 0.7:
                    row_status = "needs_review"
                    issues.append(
                        RowIssue(
                            code="low_confidence_match",
                            severity="warning",
                            message_vi=f"Độ khớp nhãn dòng thấp ({best_score:.2f}); cần người dùng xác nhận.",
                        )
                    )

            r_id = f"{spec.metric_id}:{role}"
            val_str = str(b_val) if b_val is not None else None
            candidate_rows.append(
                CandidateRow(
                    row_id=r_id,
                    metric_id=spec.metric_id,
                    label_vi=METRIC_LABELS_VI[spec.metric_id],
                    period_role=role,  # type: ignore[arg-type]
                    period_id=pid,
                    value_billion_vnd=val_str,
                    extracted_value_billion_vnd=val_str,
                    raw_text=best_line,
                    row_label=best_line,
                    page=best_page.page_number,
                    source=best_page.source,
                    status=row_status,
                    edited=False,
                    confirmed=False,
                    issues=issues,
                    alternatives=alternatives,
                )
            )

    if llamaparse_count > 0:
        source_kind = f"nhận diện cấu trúc bảng LlamaParse ({llamaparse_count} trang)"
    elif ocr_count > 0:
        source_kind = "scan OCR (Tesseract)"
    else:
        source_kind = "lớp chữ PDF"

    limitations_vi = [
        f"Số liệu {entity_id.upper()} được trích xuất tự động từ tệp PDF dạng {source_kind}.",
        "Mọi số liệu ở trạng thái ứng viên (candidate) và phải được kiểm tra, xác nhận trước khi đưa vào phân tích.",
    ]

    provider: Literal["text_layer", "tesseract", "llamaparse", "mixed", "sample"] = "text_layer"
    if llamaparse_count > 0:
        provider = "llamaparse"
    elif ocr_count > 0 and text_layer_count == 0:
        provider = "tesseract"
    elif ocr_count > 0 and text_layer_count > 0:
        provider = "mixed"

    has_blocking = any(r.status == "missing" or any(iss.severity == "error" for iss in r.issues) for r in candidate_rows)
    initial_validation = {
        "status": "fail" if has_blocking else "warn",
        "ready_to_confirm": False,
        "blocking_reasons_vi": ["Một số chỉ tiêu chưa được trích xuất; cần hoàn thiện."] if has_blocking else ["Cần kiểm tra và xác nhận các chỉ tiêu trước khi confirm."],
        "checks": [],
    }

    return ExtractionResult(
        filing_id=fid,
        entity_id=entity_id.upper(),
        display_name=ename,
        fiscal_year=fiscal_year,
        reporting_scope=reporting_scope,
        page_count=len(pages),
        ocr_provider=provider,
        text_layer_pages=text_layer_count,
        ocr_pages=ocr_count,
        statement_pages=statement_pages,
        unit_detected=detected_unit,
        rows=candidate_rows,
        validation=initial_validation,
        limitations_vi=limitations_vi,
    )
