"""Deterministic Vietnamese query understanding and parameter resolution."""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass
from typing import Any, Sequence

from .metric_presentation import (
    METRIC_PRESENTATIONS,
    TOPIC_GROUPS,
    get_metric_presentation,
)
from .service import AnalysisBlocked, _is_lineage_only_metric


@dataclass(frozen=True)
class ResolvedQuery:
    entities: tuple[str, ...]
    unknown_entity_tokens: tuple[str, ...]
    explicit_periods: tuple[str, ...]
    year_only: int | None
    anchor_period: str
    context_periods: tuple[str, ...]
    explicit_metrics: tuple[str, ...]
    topic_metrics: tuple[str, ...]
    flags: frozenset[str]
    defaults_applied: tuple[str, ...]


_MACRO_KEYWORDS = (
    "vĩ mô", "vi mo", "lãi suất điều hành", "lai suat dieu hanh",
    "chính sách tiền tệ", "chinh sach tien te", "nhnn",
    "ngân hàng nhà nước", "ngan hang nha nuoc", "sbv",
    "lạm phát", "lam phat", "cpi",
    "tăng trưởng tín dụng toàn ngành", "tang truong tin dung toan nganh",
    "truyền dẫn", "truyen dan",
)

_LOOKUP_KEYWORDS = (
    "bao nhiêu", "bao nhieu", "là mấy", "la may", "giá trị", "gia tri",
    "con số", "con so", "what is", "how much",
)

_SUPERLATIVE_KEYWORDS = (
    "nào", "nao", "nhất", "nhat", "top", "xếp hạng", "xep hang",
    "đứng thứ", "dung thu", "dẫn đầu", "dan dau",
)

_COMPARISON_KEYWORDS = (
    "so sánh", "so sanh", "so với", "so voi", "cùng nhóm", "cung nhom",
    "ngành", "nganh", "trung vị", "trung vi", "peer",
)

_TREND_KEYWORDS = (
    "diễn biến", "dien bien", "xu hướng", "xu huong", "thay đổi", "thay doi",
    "qua các quý", "qua cac quy",
)

_WHY_KEYWORDS = (
    "vì sao", "vi sao", "tại sao", "tai sao", "nguyên nhân", "nguyen nhan",
)

_RELATIONSHIP_KEYWORDS = (
    "có đi cùng", "co di cung", "tương quan", "tuong quan",
    "quan hệ giữa", "quan he giua", "liên quan giữa", "lien quan giua",
)

_IGNORED_UPPER_TOKENS = frozenset({
    "ROE", "ROA", "NIM", "NPL", "CIR", "CASA", "CAR", "LDR", "LLR",
    "Q1", "Q2", "Q3", "Q4", "FY20", "FY21", "FY22", "FY23", "FY24",
    "SBV", "NHNN", "CPI", "GDP", "VND", "USD", "API", "DTO",
    "TOP", "AND", "THE", "FOR",
})


def strip_accents(text: str) -> str:
    """Strip Vietnamese diacritics for insensitive matching."""
    text = text.replace("đ", "d").replace("Đ", "D")
    decomposed = unicodedata.normalize("NFD", text)
    return "".join(c for c in decomposed if unicodedata.category(c) != "Mn")


def normalize_text(text: str) -> str:
    """Normalize text: NFC, lowercase, collapse whitespace, unified dashes."""
    text = unicodedata.normalize("NFC", text).casefold()
    text = text.replace("–", "-").replace("—", "-")
    return re.sub(r"\s+", " ", text).strip()


def _parse_period_key(period_id: str) -> tuple[int, int]:
    match = re.fullmatch(r"(\d{4})_Q([1-4])", period_id, re.I)
    if match:
        return int(match.group(1)), int(match.group(2))
    fy_match = re.fullmatch(r"FY(\d{4})", period_id, re.I)
    if fy_match:
        return int(fy_match.group(1)), 4
    return 0, 0


def _quarter_ordinal(year: int, quarter: int) -> int:
    return year * 4 + quarter - 1


def _ordinal_quarter(ordinal: int) -> str:
    year, quarter_index = divmod(ordinal, 4)
    return f"{year}_Q{quarter_index + 1}"


def resolve_query(query: str, catalog: Any) -> ResolvedQuery:
    """Deterministically resolve entity, period, metric, and analytical intent from a query."""
    norm = normalize_text(query)
    norm_no_accents = strip_accents(norm)

    catalog_periods = [p.period_id for p in catalog.periods]
    catalog_periods.sort(key=_parse_period_key)
    if not catalog_periods:
        raise AnalysisBlocked("accepted_snapshot_unavailable", "Catalog contains no accepted periods.")

    catalog_period_set = {p.casefold(): p for p in catalog_periods}

    # 1. Resolve Periods
    explicit_periods: tuple[str, ...] = ()
    year_only: int | None = None
    anchor_period: str
    defaults_applied: list[str] = []

    # 1a. Range check
    # Check "2024_Q1 đến 2024_Q4", "2024_Q1 to 2024_Q4", "2024_Q1-2024_Q4"
    canonical_range = re.search(
        r"(?:từ|tu|from)?\s*(20\d{2})_?Q([1-4])\s*(?:đến|den|to|-)\s*(20\d{2})_?Q([1-4])",
        norm_no_accents,
        re.I,
    )
    # Check "quý 1 đến quý 4/2024", "Q1-Q4/2024", "quý 1-4/2024", "quý 1 đến 4/2024"
    text_range_1 = re.search(
        r"(?:từ|tu|from)?\s*(?:quy|q)\s*([1-4])\s*(?:đến|den|to|-)\s*(?:quy|q)?\s*([1-4])\s*(?:/|nam|\s+)\s*(20\d{2})",
        norm_no_accents,
        re.I,
    )
    text_range_2 = re.search(
        r"(?:từ|tu|from)?\s*(?:quy|q)\s*([1-4])\s*(?:/|nam|\s+)\s*(20\d{2})\s*(?:đến|den|to|-)\s*(?:quy|q)\s*([1-4])\s*(?:/|nam|\s+)\s*(20\d{2})",
        norm_no_accents,
        re.I,
    )

    if canonical_range:
        y1, q1, y2, q2 = canonical_range.groups()
        first_ord = _quarter_ordinal(int(y1), int(q1))
        last_ord = _quarter_ordinal(int(y2), int(q2))
        if last_ord < first_ord:
            raise AnalysisBlocked("query_period_range_descending", "Query period range is descending.")
        expanded = [_ordinal_quarter(o) for o in range(first_ord, last_ord + 1)]
        for p in expanded:
            if p.casefold() not in catalog_period_set:
                raise AnalysisBlocked(
                    "unsupported_period",
                    f"Period {p} is not an exact period in the accepted snapshot.",
                )
        explicit_periods = tuple(expanded)
        anchor_period = explicit_periods[-1]
    elif text_range_2:
        q1, y1, q2, y2 = text_range_2.groups()
        first_ord = _quarter_ordinal(int(y1), int(q1))
        last_ord = _quarter_ordinal(int(y2), int(q2))
        if last_ord < first_ord:
            raise AnalysisBlocked("query_period_range_descending", "Query period range is descending.")
        expanded = [_ordinal_quarter(o) for o in range(first_ord, last_ord + 1)]
        for p in expanded:
            if p.casefold() not in catalog_period_set:
                raise AnalysisBlocked(
                    "unsupported_period",
                    f"Period {p} is not an exact period in the accepted snapshot.",
                )
        explicit_periods = tuple(expanded)
        anchor_period = explicit_periods[-1]
    elif text_range_1:
        q1, q2, y = text_range_1.groups()
        first_ord = _quarter_ordinal(int(y), int(q1))
        last_ord = _quarter_ordinal(int(y), int(q2))
        if last_ord < first_ord:
            raise AnalysisBlocked("query_period_range_descending", "Query period range is descending.")
        expanded = [_ordinal_quarter(o) for o in range(first_ord, last_ord + 1)]
        for p in expanded:
            if p.casefold() not in catalog_period_set:
                raise AnalysisBlocked(
                    "unsupported_period",
                    f"Period {p} is not an exact period in the accepted snapshot.",
                )
        explicit_periods = tuple(expanded)
        anchor_period = explicit_periods[-1]
    else:
        # 1b. Single quarter check
        single_quarter: str | None = None
        # Check "cuối năm 2024", "cuoi nam 2024"
        cuoi_nam = re.search(r"cuoi\s+nam\s+(20\d{2})", norm_no_accents)
        if cuoi_nam:
            single_quarter = f"{cuoi_nam.group(1)}_Q4"
        else:
            # Check "quý 4/2024", "q4/2024", "quy 4 2024", "quý 4 năm 2024"
            m_q1 = re.search(r"(?:quy|q)\s*([1-4])\s*(?:/|nam|-|\s+)\s*(20\d{2})", norm_no_accents)
            if m_q1:
                single_quarter = f"{m_q1.group(2)}_Q{m_q1.group(1)}"
            else:
                # Check "4Q24", "4Q2024"
                m_q2 = re.search(r"\b([1-4])q(20\d{2}|\d{2})\b", norm_no_accents)
                if m_q2:
                    y_str = m_q2.group(2)
                    full_y = f"20{y_str}" if len(y_str) == 2 else y_str
                    single_quarter = f"{full_y}_Q{m_q2.group(1)}"
                else:
                    # Check "2024Q4", "2024_Q4", "2024-Q4", "2024 Q4"
                    m_q3 = re.search(r"\b(20\d{2})[-_\s]*[Qq]([1-4])\b", norm_no_accents)
                    if m_q3:
                        single_quarter = f"{m_q3.group(1)}_Q{m_q3.group(2)}"

        if single_quarter:
            exact = catalog_period_set.get(single_quarter.casefold())
            if exact is None:
                raise AnalysisBlocked(
                    "unsupported_period",
                    f"Period {single_quarter} is not an exact period in the accepted snapshot.",
                )
            explicit_periods = (exact,)
            anchor_period = exact
        else:
            # 1c. Year only check
            m_year = re.search(r"\b(?:nam|trong|in)?\s*(20\d{2})\b", norm_no_accents)
            if m_year:
                y_val = int(m_year.group(1))
                year_quarters = [p for p in catalog_periods if p.startswith(f"{y_val}_Q")]
                if not year_quarters:
                    raise AnalysisBlocked(
                        "unsupported_period",
                        f"Year {y_val} has no periods in the accepted snapshot.",
                    )
                year_only = y_val
                anchor_period = year_quarters[-1]
            else:
                # 1d. No period specified
                anchor_period = catalog_periods[-1]
                defaults_applied.append("period_defaulted_to_latest")

    # 1e. Context periods: same year, <= anchor_period, sorted ascending, max 4
    anchor_y, anchor_q = _parse_period_key(anchor_period)
    context_periods = tuple(
        p
        for p in catalog_periods
        if _parse_period_key(p)[0] == anchor_y and _parse_period_key(p)[1] <= anchor_q
    )[-4:]

    # 2. Resolve Entities
    company_entities = [e for e in catalog.entities if e.entity_type.value == "company"]
    company_id_map = {e.entity_id.upper(): e.entity_id for e in company_entities}

    # Find position of each company match in query
    entity_positions: list[tuple[int, str]] = []
    for entity_id, canonical_id in company_id_map.items():
        pattern = rf"(?<![A-Za-z0-9_]){re.escape(entity_id)}(?![A-Za-z0-9_])"
        match = re.search(pattern, query, re.I)
        if match:
            entity_positions.append((match.start(), canonical_id))
    entity_positions.sort(key=lambda item: item[0])
    matched_entities = tuple(item[1] for item in entity_positions)

    # Detect unknown entity tokens: uppercase tokens of 3-10 chars not in catalog
    all_raw_tokens = re.findall(r"\b[A-Za-z0-9_]{3,10}\b", query)
    unknown_entity_tokens: list[str] = []
    for token in all_raw_tokens:
        u_tok = token.upper()
        if (
            u_tok == token
            and u_tok not in company_id_map
            and u_tok not in _IGNORED_UPPER_TOKENS
            and not re.fullmatch(r"\d+", u_tok)
            and not re.fullmatch(r"20\d{2}", u_tok)
        ):
            if u_tok not in unknown_entity_tokens:
                unknown_entity_tokens.append(u_tok)

    # 3. Resolve Metrics and Topics
    catalog_metrics = [
        m for m in catalog.metrics if not _is_lineage_only_metric(m.metric_id)
    ]
    catalog_metric_ids = {m.metric_id: m for m in catalog_metrics}

    explicit_metrics_list: list[str] = []
    # Check all presentations in METRIC_PRESENTATIONS
    for metric_id, pres in METRIC_PRESENTATIONS.items():
        matched = False
        # Match acronym
        acronym = metric_id.rsplit(".", 1)[-1].upper()
        if re.search(rf"(?<![A-Za-z0-9_]){re.escape(acronym)}(?![A-Za-z0-9_])", query, re.I):
            matched = True
        # Match synonyms
        if not matched:
            for syn in pres.synonyms:
                syn_norm = normalize_text(syn)
                syn_no_accents = strip_accents(syn_norm)
                if syn_norm in norm or syn_no_accents in norm_no_accents:
                    matched = True
                    break
        if matched:
            resolved_id = metric_id
            if resolved_id not in catalog_metric_ids:
                if resolved_id == "bank.llr_coverage" and "bank.llr" in catalog_metric_ids:
                    resolved_id = "bank.llr"
                elif resolved_id == "bank.npl_g35" and "bank.npl" in catalog_metric_ids:
                    resolved_id = "bank.npl"
                else:
                    raise AnalysisBlocked(
                        "unsupported_metric",
                        f"The accepted snapshot does not declare requested metric: {pres.label}.",
                    )
            if resolved_id not in explicit_metrics_list:
                explicit_metrics_list.append(resolved_id)

    topic_metrics_list: list[str] = []
    for topic_phrase, groups in TOPIC_GROUPS.items():
        phrase_norm = normalize_text(topic_phrase)
        phrase_no_accents = strip_accents(phrase_norm)
        if phrase_norm in norm or phrase_no_accents in norm_no_accents:
            if groups == ("all",):
                for m in catalog_metrics:
                    if m.metric_id not in topic_metrics_list:
                        topic_metrics_list.append(m.metric_id)
            else:
                for m in catalog_metrics:
                    pres = get_metric_presentation(m.metric_id, m.display_name)
                    if pres.group in groups and m.metric_id not in topic_metrics_list:
                        topic_metrics_list.append(m.metric_id)

    # 4. Resolve Flags
    flags: set[str] = set()

    if any(k in norm or k in norm_no_accents for k in _LOOKUP_KEYWORDS):
        flags.add("lookup")

    norm_no_how = re.sub(r"\b(?:như\s+)?thế\s+nào\b", " ", norm)
    norm_no_accents_no_how = re.sub(r"\b(?:nhu\s+)?the\s+nao\b", " ", norm_no_accents)
    _superlative_matched = False
    for k in _SUPERLATIVE_KEYWORDS:
        if k in ("nào", "nao"):
            if re.search(rf"\b{re.escape(k)}\b", norm_no_how) or re.search(rf"\b{re.escape(k)}\b", norm_no_accents_no_how):
                _superlative_matched = True
                break
        else:
            if k in norm_no_how or k in norm_no_accents_no_how:
                _superlative_matched = True
                break
    if _superlative_matched:
        flags.add("superlative")
    if any(k in norm or k in norm_no_accents for k in _COMPARISON_KEYWORDS):
        flags.add("comparison")
    if (
        any(k in norm or k in norm_no_accents for k in _TREND_KEYWORDS)
        or len(explicit_periods) > 1
        or year_only is not None
    ):
        flags.add("trend")
    if any(k in norm or k in norm_no_accents for k in _MACRO_KEYWORDS):
        flags.add("macro")
    if any(k in norm or k in norm_no_accents for k in _WHY_KEYWORDS):
        flags.add("why")
    if any(k in norm or k in norm_no_accents for k in _RELATIONSHIP_KEYWORDS):
        flags.add("relationship")

    return ResolvedQuery(
        entities=matched_entities,
        unknown_entity_tokens=tuple(unknown_entity_tokens),
        explicit_periods=explicit_periods,
        year_only=year_only,
        anchor_period=anchor_period,
        context_periods=context_periods,
        explicit_metrics=tuple(explicit_metrics_list),
        topic_metrics=tuple(topic_metrics_list),
        flags=frozenset(flags),
        defaults_applied=tuple(defaults_applied),
    )
