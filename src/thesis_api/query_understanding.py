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
    raw_query: str = ""


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
    "TOP", "AND", "THE", "FOR", "TMCP", "NHTMCP",
})

def _with_bank_prefixes(phrase: str) -> tuple[str, ...]:
    """Generate alias variants requiring an explicit bank prefix ('ngân hàng' or 'nh')."""
    return (
        f"ngân hàng thương mại cổ phần {phrase}",
        f"ngân hàng tmcp {phrase}",
        f"ngân hàng {phrase}",
        f"nh tmcp {phrase}",
        f"nhtmcp {phrase}",
        f"nh {phrase}",
    )


# Canonical Vietnamese bank aliases mapping canonical ticker to known names/phrases.
# Distinctive brand names and tickers are allowed bare; generic/polysemous Vietnamese
# phrases (e.g. 'công thương', 'ngoại thương', 'đầu tư và phát triển', 'quân đội',
# 'á châu', 'sài gòn - hà nội', 'việt nam thịnh vượng') strictly require a bank prefix
# ('ngân hàng', 'nh', etc.) to prevent false matches with non-bank entities.
BANK_NAME_ALIASES: dict[str, tuple[str, ...]] = {
    "VCB": (
        "vietcombank",
        "vietcom bank",
        "vcb",
        *_with_bank_prefixes("ngoại thương việt nam"),
        *_with_bank_prefixes("ngoại thương"),
        *_with_bank_prefixes("vietcombank"),
        *_with_bank_prefixes("vietcom bank"),
        *_with_bank_prefixes("vcb"),
    ),
    "BID": (
        "bidv",
        "bid",
        *_with_bank_prefixes("đầu tư và phát triển việt nam"),
        *_with_bank_prefixes("đầu tư và phát triển"),
        *_with_bank_prefixes("đầu tư & phát triển"),
        *_with_bank_prefixes("bidv"),
        *_with_bank_prefixes("bid"),
    ),
    "CTG": (
        "vietinbank",
        "vietin bank",
        "vietin",
        "ctg",
        *_with_bank_prefixes("công thương việt nam"),
        *_with_bank_prefixes("công thương"),
        *_with_bank_prefixes("vietinbank"),
        *_with_bank_prefixes("vietin bank"),
        *_with_bank_prefixes("ctg"),
    ),
    "TCB": (
        "techcombank",
        "techcom bank",
        "tcb",
        *_with_bank_prefixes("kỹ thương việt nam"),
        *_with_bank_prefixes("kỹ thương"),
        *_with_bank_prefixes("techcombank"),
        *_with_bank_prefixes("techcom bank"),
        *_with_bank_prefixes("tcb"),
    ),
    "MBB": (
        "mbbank",
        "mb bank",
        "mbb",
        "mb",
        *_with_bank_prefixes("quân đội"),
        *_with_bank_prefixes("mbbank"),
        *_with_bank_prefixes("mb bank"),
        *_with_bank_prefixes("mb"),
        *_with_bank_prefixes("mbb"),
    ),
    "VPB": (
        "vpbank",
        "vp bank",
        "vpb",
        *_with_bank_prefixes("việt nam thịnh vượng"),
        *_with_bank_prefixes("vpbank"),
        *_with_bank_prefixes("vp bank"),
        *_with_bank_prefixes("vpb"),
    ),
    "ACB": (
        "acb",
        *_with_bank_prefixes("á châu"),
        *_with_bank_prefixes("acb"),
    ),
    "STB": (
        "sacombank",
        "sacom bank",
        "stb",
        *_with_bank_prefixes("sài gòn thương tín"),
        *_with_bank_prefixes("sacombank"),
        *_with_bank_prefixes("sacom bank"),
        *_with_bank_prefixes("stb"),
    ),
    "SHB": (
        "shb",
        *_with_bank_prefixes("sài gòn - hà nội"),
        *_with_bank_prefixes("sài gòn – hà nội"),
        *_with_bank_prefixes("sài gòn hà nội"),
        *_with_bank_prefixes("shb"),
    ),
    "HDB": (
        "hdbank",
        "hd bank",
        "hdb",
        *_with_bank_prefixes("phát triển thành phố hồ chí minh"),
        *_with_bank_prefixes("hdbank"),
        *_with_bank_prefixes("hd bank"),
        *_with_bank_prefixes("hdb"),
    ),
    "VIB": (
        "vibank",
        "vib",
        *_with_bank_prefixes("quốc tế việt nam"),
        *_with_bank_prefixes("quốc tế"),
        *_with_bank_prefixes("vibank"),
        *_with_bank_prefixes("vib"),
    ),
    # Common unsupported banks: distinctive brand names bare; generic terms require bank prefix
    "OCB": (
        "ocb",
        *_with_bank_prefixes("phương đông"),
        *_with_bank_prefixes("ocb"),
    ),
    "TPB": (
        "tpbank",
        "tp bank",
        "tpb",
        *_with_bank_prefixes("tiên phong"),
        *_with_bank_prefixes("tpbank"),
        *_with_bank_prefixes("tp bank"),
        *_with_bank_prefixes("tpb"),
    ),
    "MSB": (
        "maritime bank",
        "msb",
        *_with_bank_prefixes("hàng hải"),
        *_with_bank_prefixes("msb"),
    ),
    "LPB": (
        "lpbank",
        "lp bank",
        "lpb",
        *_with_bank_prefixes("bưu điện liên việt"),
        *_with_bank_prefixes("lộc phát việt nam"),
        *_with_bank_prefixes("lộc phát"),
        *_with_bank_prefixes("lpbank"),
        *_with_bank_prefixes("lp bank"),
        *_with_bank_prefixes("lpb"),
    ),
    "SSB": (
        "seabank",
        "sea bank",
        "ssb",
        *_with_bank_prefixes("đông nam á"),
        *_with_bank_prefixes("seabank"),
        *_with_bank_prefixes("sea bank"),
        *_with_bank_prefixes("ssb"),
    ),
    "EIB": (
        "eximbank",
        "exim bank",
        "eib",
        *_with_bank_prefixes("xuất nhập khẩu việt nam"),
        *_with_bank_prefixes("xuất nhập khẩu"),
        *_with_bank_prefixes("eximbank"),
        *_with_bank_prefixes("exim bank"),
        *_with_bank_prefixes("eib"),
    ),
}


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
    for e in company_entities:
        ticker_attr = e.attributes.get("ticker") if isinstance(e.attributes, dict) else None
        if ticker_attr and isinstance(ticker_attr, str):
            company_id_map[ticker_attr.upper()] = e.entity_id

    # Build candidates list: (canonical_ticker, pattern_norm_no_accents, length)
    # Longest phrase first ensures e.g. "ngân hàng Á Châu" matches before "Á Châu",
    # "Sài Gòn - Hà Nội" matches before "Sài Gòn", and "MBBank" before "MB".
    candidates: list[tuple[str, str, int]] = []
    seen_aliases: set[tuple[str, str]] = set()

    for ticker, aliases in BANK_NAME_ALIASES.items():
        for alias in aliases:
            a_norm = strip_accents(normalize_text(alias))
            if (ticker, a_norm) not in seen_aliases:
                seen_aliases.add((ticker, a_norm))
                candidates.append((ticker, a_norm, len(a_norm)))

    # Include any company entities from catalog not already covered in alias list
    for entity_id in company_id_map:
        e_norm = strip_accents(normalize_text(entity_id))
        if (entity_id, e_norm) not in seen_aliases:
            seen_aliases.add((entity_id, e_norm))
            candidates.append((entity_id, e_norm, len(e_norm)))

    candidates.sort(key=lambda x: -x[2])

    working_text = norm_no_accents
    found_matches: list[tuple[int, str]] = []  # (start_index, ticker)

    for ticker, a_norm, _length in candidates:
        pattern = rf"(?<![a-z0-9_]){re.escape(a_norm)}(?![a-z0-9_])"
        while True:
            m = re.search(pattern, working_text)
            if not m:
                break
            start, end = m.start(), m.end()
            found_matches.append((start, ticker))
            working_text = working_text[:start] + (" " * (end - start)) + working_text[end:]

    # Separate matches into supported entities and unknown entities
    entity_positions: list[tuple[int, str]] = []
    unknown_positions: list[tuple[int, str]] = []

    for start_index, ticker in found_matches:
        u_tick = ticker.upper()
        if u_tick in company_id_map:
            entity_positions.append((start_index, company_id_map[u_tick]))
        else:
            unknown_positions.append((start_index, u_tick))

    entity_positions.sort(key=lambda x: x[0])
    unknown_positions.sort(key=lambda x: x[0])

    matched_entities_list: list[str] = []
    for _pos, can_id in entity_positions:
        if can_id not in matched_entities_list:
            matched_entities_list.append(can_id)
    matched_entities = tuple(matched_entities_list)

    unknown_entity_tokens: list[str] = []
    for _pos, tok in unknown_positions:
        if tok not in unknown_entity_tokens:
            unknown_entity_tokens.append(tok)

    # Detect unknown entity tokens: uppercase tokens of 3-10 chars not in catalog
    all_raw_tokens = re.findall(r"\b[A-Za-z0-9_]{3,10}\b", query)
    for token in all_raw_tokens:
        u_tok = token.upper()
        t_norm = strip_accents(normalize_text(token))
        tok_pat = rf"(?<![a-z0-9_]){re.escape(t_norm)}(?![a-z0-9_])"
        if not re.search(tok_pat, working_text):
            # Consumed/blanked out by a matched alias
            continue
        if (
            u_tok == token
            and u_tok not in company_id_map
            and u_tok not in _IGNORED_UPPER_TOKENS
            and not re.fullmatch(r"\d+", u_tok)
            and not re.fullmatch(r"20\d{2}", u_tok)
            and not re.fullmatch(r"20\d{2}_Q[1-4]", u_tok)
            and not re.fullmatch(r"Q[1-4]", u_tok)
            and u_tok not in explicit_periods
        ):
            if u_tok not in unknown_entity_tokens:
                unknown_entity_tokens.append(u_tok)

    # 3. Resolve Metrics and Topics
    catalog_metrics = [
        m for m in catalog.metrics if not _is_lineage_only_metric(m.metric_id)
    ]
    catalog_metric_ids = {m.metric_id: m for m in catalog_metrics}

    explicit_metrics_list: list[str] = []

    # --- Longest-phrase-first synonym matching ---
    # Build a flat list of (metric_id, pres, synonym_norm, synonym_no_accents, syn_len)
    # sorted by synonym length descending so longer phrases are matched first.
    # For acronym matches the "phrase" is the acronym itself.
    _candidate_syns: list[tuple[str, object, str, str, int, bool]] = []
    for _metric_id, _pres in METRIC_PRESENTATIONS.items():
        _acronym = _metric_id.rsplit(".", 1)[-1].upper()
        _acronym_norm = normalize_text(_acronym)
        _candidate_syns.append(
            (_metric_id, _pres, _acronym_norm, strip_accents(_acronym_norm), len(_acronym_norm), True)
        )
        for _syn in _pres.synonyms:
            _syn_norm = normalize_text(_syn)
            _syn_no_acc = strip_accents(_syn_norm)
            _candidate_syns.append(
                (_metric_id, _pres, _syn_norm, _syn_no_acc, len(_syn_norm), False)
            )
    # Sort by synonym length descending — longest phrase wins
    _candidate_syns.sort(key=lambda x: -x[4])

    # Work on mutable "remaining" text — replace matched spans with blank spaces
    _remaining_norm = norm
    _remaining_no_accents = norm_no_accents

    _matched_metric_ids: set[str] = set()

    for _metric_id, _pres, _syn_norm, _syn_no_acc, _syn_len, _is_acronym in _candidate_syns:
        if _metric_id in _matched_metric_ids:
            # Already matched this metric; skip additional synonyms for it
            continue

        _matched = False
        if _is_acronym:
            # Acronym: word-boundary match against the *original* query (case-insensitive)
            if re.search(
                rf"(?<![A-Za-z0-9_]){re.escape(_syn_norm)}(?![A-Za-z0-9_])",
                _remaining_no_accents,
                re.I,
            ):
                _matched = True
        else:
            if _syn_norm in _remaining_norm or _syn_no_acc in _remaining_no_accents:
                _matched = True

        if _matched:
            # Resolve catalog id
            _resolved_id = _metric_id
            if _resolved_id not in catalog_metric_ids:
                if _resolved_id == "bank.llr_coverage" and "bank.llr" in catalog_metric_ids:
                    _resolved_id = "bank.llr"
                elif _resolved_id == "bank.npl_g35" and "bank.npl" in catalog_metric_ids:
                    _resolved_id = "bank.npl"
                else:
                    raise AnalysisBlocked(
                        "unsupported_metric",
                        f"The accepted snapshot does not declare requested metric: {_pres.label}.",  # type: ignore[attr-defined]
                    )
            if _resolved_id not in explicit_metrics_list:
                explicit_metrics_list.append(_resolved_id)
            # Mark metric as matched so shorter sub-phrases for the same metric are skipped
            _matched_metric_ids.add(_metric_id)
            # Consume matched span from remaining text so shorter sub-phrases cannot re-match
            _blank = " " * _syn_len
            if _syn_norm in _remaining_norm:
                _remaining_norm = _remaining_norm.replace(_syn_norm, _blank, 1)
            if _syn_no_acc in _remaining_no_accents:
                _remaining_no_accents = _remaining_no_accents.replace(_syn_no_acc, _blank, 1)

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
        raw_query=query,
    )
