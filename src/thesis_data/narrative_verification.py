"""Deterministic sentence-level narrative verification.

Pure algorithmic module for verifying financial analytical claims:
- No sqlite3, openai, langchain, or langgraph imports.
- No fixed issuer literals.
- Stops at first violation per sentence.
- NFC normalized, casefolded matching.
"""

from __future__ import annotations

from dataclasses import dataclass, field
import math
import re
from typing import Any, Mapping, Sequence
import unicodedata

from .report_facts import Fact


@dataclass(frozen=True)
class NarrativeSentence:
    """A single analytical sentence with cited fact identifiers."""

    sentence_id: str
    author: str
    text: str
    fact_ids: tuple[str, ...]
    source: str
    revision: int = 0


@dataclass(frozen=True)
class SentenceVerdict:
    """Outcome of verifying a single narrative sentence."""

    ok: bool
    reason_code: str | None
    reason: str | None
    numbers_checked: int
    numbers_matched: int


@dataclass(frozen=True)
class DroppedSentence:
    """Record of a sentence rejected by the verifier."""

    sentence_id: str
    author: str
    text: str
    reason_code: str
    reason: str


@dataclass(frozen=True)
class AuditCounts:
    """Aggregated metrics from sentence verification."""

    sentences_checked: int
    sentences_accepted: int
    numbers_checked: int
    numbers_matched: int


@dataclass(frozen=True)
class NarrativeLexicon:
    """Lexical dictionaries for Vietnamese financial narrative auditing."""

    causal_words: tuple[str, ...] = (
        "bởi vì",
        "xuất phát từ",
        "dẫn đến",
        "dẫn tới",
        "kéo theo",
        "gây ra",
        "nhờ vào",
        "nhờ có",
        "do đó",
        "vì vậy",
        "là nguyên nhân",
        "góp phần",
        "giúp cho",
        "giúp",
        "bởi",
        "nhờ",
        "khiến",
        "vì",
        "do",
        "because of",
        "because",
        "due to",
    )
    causal_exclusions: tuple[str, ...] = (
        "lý do",
        "tự do",
        "do dự",
        "trợ giúp",
        "giúp đỡ",
    )
    investment_words: tuple[str, ...] = (
        "định giá hấp dẫn",
        "giá mục tiêu",
        "nên đầu tư",
        "khuyến nghị",
        "nắm giữ",
        "mua",
        "bán",
    )
    investment_exclusions: tuple[str, ...] = ("bán lẻ", "bán buôn", "mua bán nợ")
    trend_words: tuple[str, ...] = (
        "tăng lên",
        "tăng",
        "đi lên",
        "giảm xuống",
        "giảm",
        "đi xuống",
        "đi ngang",
        "ổn định",
        "không đổi",
        "cải thiện",
        "xấu đi",
        "suy giảm",
        "liên tục",
        "thu hẹp",
        "nới rộng",
        "ngược chiều",
        "ngược xu hướng",
        "improved",
        "increased",
        "decreased",
    )
    comparison_words: tuple[str, ...] = (
        "cao hơn",
        "thấp hơn",
        "dày hơn",
        "mỏng hơn",
        "vượt trội",
        "vượt",
        "nhỉnh hơn",
        "dẫn ở",
        "trên trung vị",
        "dưới trung vị",
        "tốt hơn",
        "kém hơn",
        "bằng trung vị",
        "đúng bằng trung vị",
        "ngang trung vị",
        "ngang nhóm",
        "ngang với trung vị",
        "bằng trung vị nhóm",
        "tương đương trung vị",
    )


VI_LEXICON = NarrativeLexicon()


@dataclass(frozen=True)
class VerificationContext:
    """Execution context provided to sentence verifiers."""

    facts: Mapping[str, Fact]
    plan_entities: frozenset[str]
    catalog_entities: frozenset[str]
    metric_terms: Mapping[str, tuple[str, ...]]
    hi_words: Mapping[str, tuple[str, ...]]
    lo_words: Mapping[str, tuple[str, ...]]
    directions: Mapping[str, str]
    flat_pp: Mapping[str, float]
    anchor_year: int
    lexicon: NarrativeLexicon = VI_LEXICON
    enable_label_rules: bool = True


_ORDER_WORD_TO_NUM: dict[str, int] = {
    "nhất": 1,
    "đầu": 1,
    "nhì": 2,
    "hai": 2,
    "ba": 3,
    "tư": 4,
    "bốn": 4,
    "năm": 5,
    "sáu": 6,
    "bảy": 7,
    "tám": 8,
    "chín": 9,
    "mười": 10,
    "cuối": -1,
    "chót": -1,
}


def _normalize(text: str) -> str:
    """Normalize text using Unicode NFC and casefolding."""
    return unicodedata.normalize("NFC", text).casefold()


def _get_metric_flat(flat_pp: Mapping[str, float] | float, metric_id: str, default: float = 0.05) -> float:
    """Resolve metric flat threshold."""
    if isinstance(flat_pp, (int, float)):
        return float(flat_pp)
    if metric_id in flat_pp:
        return float(flat_pp[metric_id])
    short_id = metric_id.rsplit(".", 1)[-1]
    if short_id in flat_pp:
        return float(flat_pp[short_id])
    return default


def _parse_order_token(token: str) -> int | None:
    """Parse numeric or word rank order into integer."""
    token = token.strip()
    if token.isdigit():
        return int(token)
    return _ORDER_WORD_TO_NUM.get(token)


def _classify_fact_unit(f: Fact) -> str:
    """Classify fact unit into 'ratio', 'pp', 'pct', or 'any'."""
    f_unit = (f.unit or "").strip().lower()
    if f_unit in ("x", "lần"):
        return "ratio"
    if f_unit in ("pp", "điểm %"):
        return "pp"
    if f_unit in ("%", "percent", "percent_per_annum"):
        return "pct"
    # Fallback to fact_type only if unit was unspecified
    if not f_unit:
        if f.fact_type in ("ratio_to_median", "derived_ratio"):
            return "ratio"
        if f.fact_type in ("gap_to_median", "delta", "median_delta", "pairwise_gap", "spread"):
            return "pp"
        if f.fact_type in ("value", "peer_median"):
            return "pct"
    return "any"



DEFAULT_METRIC_TERMS: dict[str, tuple[str, ...]] = {
    "bank.npl_g35": (
        "tỷ lệ nợ xấu (nhóm 3–5)",
        "tỷ lệ nợ xấu (nhóm 3-5)",
        "tỷ lệ nợ xấu",
        "nợ xấu (nhóm 3–5)",
        "nợ xấu (nhóm 3-5)",
        "nợ xấu",
        "npl_g35",
        "npl",
        "non-performing loan",
        "non-performing loans",
    ),
    "bank.llr_coverage": (
        "tỷ lệ bao phủ nợ xấu",
        "bao phủ nợ xấu",
        "tỷ lệ bao phủ",
        "đệm dự phòng",
        "llr_coverage",
        "llr",
        "loan loss reserve",
        "loan loss coverage",
        "coverage",
    ),
    "bank.roa": (
        "sinh lời trên tài sản",
        "return on assets",
        "roa",
    ),
    "bank.roe": (
        "sinh lời trên vốn",
        "return on equity",
        "roe",
    ),
    "bank.nim": (
        "biên lãi thuần",
        "biên lãi ròng",
        "nim",
    ),
    "bank.casa": (
        "tỷ lệ tiền gửi không kỳ hạn",
        "tiền gửi không kỳ hạn",
        "tỷ lệ casa",
        "casa",
    ),
    "bank.car": (
        "hệ số an toàn vốn (car)",
        "hệ số an toàn vốn",
        "tỷ lệ an toàn vốn",
        "car",
    ),
    "bank.cir": (
        "tỷ lệ chi phí trên thu nhập (cir)",
        "tỷ lệ chi phí trên thu nhập",
        "chi phí trên thu nhập",
        "tỷ lệ cir",
        "cir",
    ),
    "bank.ldr": (
        "tỷ lệ cho vay trên huy động (ldr)",
        "tỷ lệ cho vay trên huy động",
        "cho vay trên huy động",
        "ldr",
    ),
    "derived.roe_over_roa": (
        "tỷ lệ roe/roa",
        "roe/roa",
        "đòn bẩy vốn",
        "roe trên roa",
    ),
}


def _parse_period_token(p_str: str, anchor_year: int = 2026) -> str:
    """Normalize a Vietnamese period token into canonical period string for equality checks."""
    p = p_str.strip().lower()
    m = re.search(r"(?:quý|q)\s*([1-4])\s*(?:/|\s*năm\s*)(\d{4})", p)
    if m:
        return f"{m.group(2)}_Q{m.group(1)}"
    m = re.search(r"(?:quý|q)\s*([1-4])", p)
    if m:
        return f"{anchor_year}_Q{m.group(1)}"
    m = re.search(r"(?:năm\s+)?(\d{4})", p)
    if m:
        return m.group(1)
    return p


def verify_sentence(s: NarrativeSentence, ctx: VerificationContext) -> SentenceVerdict:
    """Verify an atomic analytical narrative sentence against cited facts.

    Stops at the first encountered violation in canonical check order.
    """
    # 1. Fact citation check
    if not s.fact_ids:
        return SentenceVerdict(
            ok=False,
            reason_code="missing_fact_citation",
            reason="Thiếu trích dẫn fact_id.",
            numbers_checked=0,
            numbers_matched=0,
        )

    for fid in s.fact_ids:
        if fid not in ctx.facts:
            return SentenceVerdict(
                ok=False,
                reason_code="unknown_fact",
                reason=f"fact_id '{fid}' không tồn tại trong danh mục kết quả.",
                numbers_checked=0,
                numbers_matched=0,
            )

    cited_facts = [ctx.facts[fid] for fid in s.fact_ids]
    norm_text = _normalize(s.text)

    # 2. Causal language check
    # Mask permitted causal exclusions first
    causal_test_text = norm_text
    for exc in ctx.lexicon.causal_exclusions:
        exc_norm = _normalize(exc)
        causal_test_text = re.sub(rf"(?<!\w){re.escape(exc_norm)}(?!\w)", " " * len(exc_norm), causal_test_text)

    for word in ctx.lexicon.causal_words:
        w_norm = _normalize(word)
        if re.search(rf"(?<!\w){re.escape(w_norm)}(?!\w)", causal_test_text):
            return SentenceVerdict(
                ok=False,
                reason_code="causal_language",
                reason=f"Chứa từ ngữ nguyên nhân không được phép: '{word}'.",
                numbers_checked=0,
                numbers_matched=0,
            )

    # 3. Investment advice check
    invest_test_text = norm_text
    for exc in ctx.lexicon.investment_exclusions:
        exc_norm = _normalize(exc)
        invest_test_text = re.sub(rf"(?<!\w){re.escape(exc_norm)}(?!\w)", " " * len(exc_norm), invest_test_text)

    for word in ctx.lexicon.investment_words:
        w_norm = _normalize(word)
        if re.search(rf"(?<!\w){re.escape(w_norm)}(?!\w)", invest_test_text):
            return SentenceVerdict(
                ok=False,
                reason_code="investment_advice",
                reason=f"Chứa từ ngữ khuyến nghị đầu tư: '{word}'.",
                numbers_checked=0,
                numbers_matched=0,
            )

    # 4. Entity in plan check
    # Check if any catalog entity outside plan_entities appears in the text
    for cat_ent in ctx.catalog_entities:
        cat_norm = _normalize(cat_ent)
        if re.search(rf"(?<!\w){re.escape(cat_norm)}(?!\w)", norm_text):
            # Check if this entity is in plan_entities (case-insensitive)
            if not any(_normalize(pe) == cat_norm for pe in ctx.plan_entities):
                return SentenceVerdict(
                    ok=False,
                    reason_code="entity_not_in_plan",
                    reason=f"Thực thể '{cat_ent}' không thuộc phạm vi kế hoạch phân tích.",
                    numbers_checked=0,
                    numbers_matched=0,
                )

    # 4b. Self-comparison checks (Rule 2: reject comparing identical entities or identical periods)
    if ctx.enable_label_rules:
        # Check spread extremes: cao nhất - cao nhất, thấp nhất - thấp nhất
        spread_self_match = re.search(
            r"(?<!\w)(?:cao\s+nhất\s*[-–—và]+\s*cao\s+nhất|thấp\s+nhất\s*[-–—và]+\s*thấp\s+nhất)(?!\w)",
            norm_text,
        )
        if spread_self_match:
            return SentenceVerdict(
                ok=False,
                reason_code="self_comparison",
                reason=f"Tự so sánh cùng cực trị: '{spread_self_match.group(0)}'.",
                numbers_checked=0,
                numbers_matched=0,
            )

        # Check period ranges: từ P1 đến P2 (where P1 == P2)
        p_range_pat = re.compile(
            r"(?<!\w)(?:từ\s+)?(quý\s+[1-4](?:\s*(?:/|\s*năm\s*)\d{4})?|q[1-4](?:\s*/\s*\d{4})?|năm\s+\d{4}|\d{4})\s+(?:đến|sang|so\s+với)\s+(quý\s+[1-4](?:\s*(?:/|\s*năm\s*)\d{4})?|q[1-4](?:\s*/\s*\d{4})?|năm\s+\d{4}|\d{4})(?!\w)"
        )
        for pm in p_range_pat.finditer(norm_text):
            p1_raw = pm.group(1)
            p2_raw = pm.group(2)
            p1_tok = _parse_period_token(p1_raw, ctx.anchor_year)
            p2_tok = _parse_period_token(p2_raw, ctx.anchor_year)
            if p1_tok == p2_tok:
                return SentenceVerdict(
                    ok=False,
                    reason_code="self_comparison",
                    reason=f"Tự so sánh cùng một kỳ: '{p1_raw}' và '{p2_raw}'.",
                    numbers_checked=0,
                    numbers_matched=0,
                )

        # Check entity self-comparison across comparison / trend terms
        all_eval_entities = set(ctx.catalog_entities) | set(ctx.plan_entities) | {
            f.entity_id for f in cited_facts if f.entity_id
        } | {
            f.other_entity_id for f in cited_facts if f.other_entity_id
        }
        if not all_eval_entities:
            all_eval_entities = set(re.findall(r"\b[A-Z]{3,4}\b", s.text))
        comp_rel_terms = (
            "vượt trội hơn",
            "vượt trội",
            "dẫn trước",
            "nhỉnh hơn",
            "cao hơn",
            "thấp hơn",
            "tốt hơn",
            "kém hơn",
            "dày hơn",
            "mỏng hơn",
            "tương đương với",
            "tương đương",
            "ngang với",
            "ngang",
            "so với",
        )
        for ct in comp_rel_terms:
            for cm in re.finditer(rf"(?<!\w){re.escape(ct)}(?!\w)", norm_text):
                pre_text = norm_text[: cm.start()]
                post_text = norm_text[cm.end() :]
                ents_before: list[tuple[int, str]] = []
                for e in all_eval_entities:
                    en = _normalize(e)
                    for em in re.finditer(rf"(?<!\w){re.escape(en)}(?!\w)", pre_text):
                        ents_before.append((em.start(), e))
                ents_after: list[tuple[int, str]] = []
                for e in all_eval_entities:
                    en = _normalize(e)
                    for em in re.finditer(rf"(?<!\w){re.escape(en)}(?!\w)", post_text):
                        ents_after.append((em.start(), e))
                if ents_before and ents_after:
                    ents_before.sort(key=lambda x: x[0])
                    ents_after.sort(key=lambda x: x[0])
                    e_before = ents_before[-1][1]
                    e_after = ents_after[0][1]
                    if _normalize(e_before) == _normalize(e_after):
                        return SentenceVerdict(
                            ok=False,
                            reason_code="self_comparison",
                            reason=f"Tự so sánh cùng một ngân hàng: '{e_before}' với chính nó quanh cụm '{ct}'.",
                            numbers_checked=0,
                            numbers_matched=0,
                        )

        # Check explicit 'giữa <Bank> và <Bank>'
        between_match = re.search(r"(?<!\w)giữa\s+([a-zA-Z0-9]+)\s+và\s+([a-zA-Z0-9]+)(?!\w)", norm_text)
        if between_match:
            b1 = between_match.group(1).upper()
            b2 = between_match.group(2).upper()
            if b1 == b2 and any(_normalize(e) == _normalize(b1) for e in all_eval_entities):
                return SentenceVerdict(
                    ok=False,
                    reason_code="self_comparison",
                    reason=f"Tự so sánh cùng một ngân hàng: giữa {b1} và {b2}.",
                    numbers_checked=0,
                    numbers_matched=0,
                )

    # 4c. Metric label check (Rule 1: metric names in sentence must match cited fact metrics)
    if ctx.enable_label_rules:
        all_terms_map: dict[str, set[str]] = {}
        for mid, terms in DEFAULT_METRIC_TERMS.items():
            all_terms_map.setdefault(mid, set()).update(_normalize(t) for t in terms if t)
        if ctx.metric_terms:
            for mid, terms in ctx.metric_terms.items():
                all_terms_map.setdefault(mid, set()).update(_normalize(t) for t in terms if t)

        search_list: list[tuple[str, str]] = []
        GENERIC_EXCLUSIONS = {"bao phủ", "dự phòng"}
        for mid, terms in all_terms_map.items():
            for t in terms:
                if t not in GENERIC_EXCLUSIONS:
                    search_list.append((t, mid))
        search_list.sort(key=lambda x: len(x[0]), reverse=True)

        occupied_metric_spans: list[tuple[int, int]] = []
        found_metrics: set[str] = set()
        for t_norm, mid in search_list:
            for m in re.finditer(rf"(?<!\w){re.escape(t_norm)}(?!\w)", norm_text):
                sp = m.span()
                if not any(sp[0] < occ[1] and sp[1] > occ[0] for occ in occupied_metric_spans):
                    occupied_metric_spans.append(sp)
                    found_metrics.add(mid)

        if found_metrics:
            cited_metric_ids = set()
            for f in cited_facts:
                if f.metric_id:
                    cited_metric_ids.add(f.metric_id)
                    cited_metric_ids.add(f.metric_id.rsplit(".", 1)[-1])

            for fm in found_metrics:
                fm_short = fm.rsplit(".", 1)[-1]
                if fm not in cited_metric_ids and fm_short not in cited_metric_ids:
                    return SentenceVerdict(
                        ok=False,
                        reason_code="metric_label_mismatch",
                        reason=f"Nhãn chỉ tiêu '{fm}' trong câu không khớp với chỉ tiêu của fact được trích dẫn.",
                        numbers_checked=0,
                        numbers_matched=0,
                    )

    # Check for ungrounded number words (e.g. seventeen, half, twice, double, mười bảy)
    num_words_pat = re.compile(r"(?<!\w)(seventeen|mười\s+bảy|half|twice|double)(?!\w)")
    for nwm in num_words_pat.finditer(norm_text):
        nw_tok = nwm.group(1)
        val_eq = 17.0 if "seventeen" in nw_tok or "mười" in nw_tok else (0.5 if "half" in nw_tok else 2.0)
        matched_nw = any(f.value is not None and abs(float(f.value) - val_eq) < 0.1 for f in cited_facts)
        if not matched_nw:
            return SentenceVerdict(
                ok=False,
                reason_code="number_mismatch",
                reason=f"Chứa từ số '{nw_tok}' không khớp fact nào.",
                numbers_checked=1,
                numbers_matched=0,
            )

    # Working copy of text where verified structured tokens will be masked with spaces
    working_chars = list(norm_text)

    def mask_span(start: int, end: int) -> None:
        for idx in range(start, end):
            working_chars[idx] = " "

    # 5. Period checks
    # Gather all accepted periods from cited facts
    valid_periods: set[str] = set()
    valid_years: set[int] = set()
    for f in cited_facts:
        if f.period:
            valid_periods.add(f.period)
            p_parts = f.period.split("_")
            if p_parts[0].isdigit():
                valid_years.add(int(p_parts[0]))
        if f.from_period:
            valid_periods.add(f.from_period)
            p_parts = f.from_period.split("_")
            if p_parts[0].isdigit():
                valid_years.add(int(p_parts[0]))

    # Regex patterns for periods in Vietnamese narrative
    # e.g., "quý 4/2024", "quý 4 năm 2024", "q4/2024", "quý 4", "q4", "năm 2024", "2024"
    period_patterns = [
        # Quarter + Year: quý 4/2024 or quý 4 năm 2024
        re.compile(r"(?<!\w)quý\s+([1-4])\s*(?:/|\s*năm\s*)(\d{4})(?!\w)"),
        # Q4/2024
        re.compile(r"(?<!\w)q([1-4])\s*/\s*(\d{4})(?!\w)"),
        # quý 4 (standalone)
        re.compile(r"(?<!\w)quý\s+([1-4])(?!\w)"),
        # Q4 (standalone)
        re.compile(r"(?<!\w)q([1-4])(?!\w)"),
        # năm 2024
        re.compile(r"(?<!\w)năm\s+(\d{4})(?!\w)"),
        # 2024 (standalone 4-digit year within reasonable boundary)
        re.compile(r"(?<!\w)(20\d{2})(?!\w)"),
    ]

    for p_pat in period_patterns:
        for m in p_pat.finditer("".join(working_chars)):
            p_str = m.group(0)
            groups = m.groups()
            resolved_period: str | None = None
            resolved_year: int | None = None

            if len(groups) == 2:
                # (q, y)
                q_num, y_num = int(groups[0]), int(groups[1])
                resolved_period = f"{y_num}_Q{q_num}"
                resolved_year = y_num
            elif len(groups) == 1:
                val = groups[0]
                if val.isdigit() and len(val) == 1:
                    # Quarter without year: defaults to anchor_year
                    resolved_period = f"{ctx.anchor_year}_Q{val}"
                    resolved_year = ctx.anchor_year
                elif val.isdigit() and len(val) == 4:
                    resolved_year = int(val)

            is_valid_period = False
            if resolved_period and resolved_period in valid_periods:
                is_valid_period = True
            elif resolved_period is None and resolved_year and resolved_year in valid_years:
                is_valid_period = True

            if not is_valid_period:
                return SentenceVerdict(
                    ok=False,
                    reason_code="period_not_cited",
                    reason=f"Kỳ '{p_str}' trong câu không thuộc danh sách kỳ của các fact được trích dẫn.",
                    numbers_checked=0,
                    numbers_matched=0,
                )
            # Mask the period span
            mask_span(m.start(), m.end())

        # Quarters duration count: "qua 4 quý", "trong 4 quý", "4 quý"
        q_count_pat = re.compile(r"(?<!\w)(\d+)\s+quý(?!\w)")
        for q_m in q_count_pat.finditer("".join(working_chars)):
            q_cnt = int(q_m.group(1))
            distinct_periods = {f.period for f in cited_facts if f.period} | {f.from_period for f in cited_facts if f.from_period}
            if q_cnt == len(distinct_periods) or q_cnt == (len([f for f in cited_facts if f.fact_type == "delta"]) + 1):
                mask_span(q_m.start(), q_m.end())

    # 6. Count checks: "N/M chỉ tiêu", "N trên M chỉ tiêu"
    count_pat = re.compile(r"(?<!\w)(\d+)\s*(?:/|trên)\s*(\d+)\s+chỉ tiêu(?!\w)")
    for m in count_pat.finditer("".join(working_chars)):
        n_val = int(m.group(1))
        m_val = int(m.group(2))
        matched = False
        for f in cited_facts:
            if f.fact_type == "lead_count" and f.value is not None:
                lead_n = round(f.value)
                denom = f.denominator
                if denom == m_val and (lead_n == n_val or (denom - lead_n) == n_val):
                    # Accept both the leader's count AND the complement (loser's count)
                    matched = True
                    break
        if not matched:
            return SentenceVerdict(
                ok=False,
                reason_code="count_mismatch",
                reason=f"Số đếm chỉ tiêu {n_val}/{m_val} không khớp fact lead_count được trích dẫn.",
                numbers_checked=1,
                numbers_matched=0,
            )
        mask_span(m.start(), m.end())

    # 7. Rank checks
    # Gather peer_rank facts
    rank_facts = [f for f in cited_facts if f.fact_type == "peer_rank" and f.denominator is not None]

    # Patterns for ranks
    rank_patterns = [
        # hạng N/M or thứ N/M
        re.compile(r"(?<!\w)(?:hạng|thứ)\s+(\d+|nhì|hai|ba|tư|bốn|năm)\s*(?:/|trên)\s*(\d+)(?!\w)"),
        # N/M (where M <= 50 to avoid years)
        re.compile(r"(?<!\w)(\d+)\s*/\s*(\d+)(?!\w)"),
        # cao thứ N, thấp thứ N, tốt thứ N, kém thứ N, dày thứ N, mỏng thứ N
        re.compile(r"(?<!\w)(cao|thấp|tốt|kém|dày|mỏng)\s+thứ\s+(\d+|nhì|hai|ba|tư|bốn|năm)(?!\w)"),
        # hạng N or thứ N
        re.compile(r"(?<!\w)(?:hạng|thứ)\s+(\d+|nhì|hai|ba|tư|bốn|năm)(?!\w)"),
        # superlatives: cao nhất, thấp nhất, tốt nhất, kém nhất, dày nhất, mỏng nhất (optionally followed by nhóm)
        re.compile(r"(?<!\w)(cao|thấp|tốt|kém|dày|mỏng)\s+nhất(?:\s+nhóm)?(?!\w)"),
        # standing: dẫn đầu, đứng đầu, đứng cuối, xếp cuối, đội sổ, nhóm đầu, nhóm cuối
        re.compile(r"(?<!\w)(dẫn đầu|đứng đầu|đứng cuối|xếp cuối|đội sổ|nhóm đầu|nhóm cuối)(?!\w)"),
        # nhất nhóm standalone
        re.compile(r"(?<!\w)nhất\s+nhóm(?!\w)"),
    ]

    # Mask spread range descriptions like "cao nhất – thấp nhất" or "cao nhất và thấp nhất"
    spread_range_pat = re.compile(
        r"(?<!\w)(?:chênh\s+lệch\s+)?(?:(?:giữa\s+)?(?:ngân\s+hàng|đơn\s+vị|thành\s+viên\s+)?cao\s+nhất\s*(?:[-–—]|và)\s*(?:ngân\s+hàng|đơn\s+vị|thành\s+viên\s+)?thấp\s+nhất|(?:giữa\s+)?(?:ngân\s+hàng|đơn\s+vị|thành\s+viên\s+)?thấp\s+nhất\s*(?:[-–—]|và)\s*(?:ngân\s+hàng|đơn\s+vị|thành\s+viên\s+)?cao\s+nhất)(?!\w)"
    )
    for sm in spread_range_pat.finditer("".join(working_chars)):
        mask_span(sm.start(), sm.end())

    has_spread_fact = any(f.fact_type == "spread" for f in cited_facts)

    for r_pat in rank_patterns:
        for m in r_pat.finditer("".join(working_chars)):
            matched_span = m.group(0)
            if not rank_facts:
                if has_spread_fact and any(w in matched_span for w in ("cao", "thấp")):
                    continue
                return SentenceVerdict(
                    ok=False,
                    reason_code="rank_mismatch",
                    reason=f"Nhắc tới thứ hạng '{matched_span}' nhưng không trích dẫn fact peer_rank nào.",
                    numbers_checked=0,
                    numbers_matched=0,
                )

            # Determine associated entity for this span
            target_entity: str | None = None
            preceding_text = norm_text[: m.start()]
            following_text = norm_text[m.end() :]

            entities_before = []
            for ent in ctx.plan_entities | ctx.catalog_entities:
                ent_norm = _normalize(ent)
                for em in re.finditer(rf"(?<!\w){re.escape(ent_norm)}(?!\w)", preceding_text):
                    entities_before.append((em.start(), ent_norm))
            if entities_before:
                entities_before.sort(key=lambda x: x[0])
                target_entity = entities_before[-1][1]
            else:
                entities_after = []
                for ent in ctx.plan_entities | ctx.catalog_entities:
                    ent_norm = _normalize(ent)
                    for em in re.finditer(rf"(?<!\w){re.escape(ent_norm)}(?!\w)", following_text):
                        entities_after.append((em.start(), ent_norm))
                if entities_after:
                    entities_after.sort(key=lambda x: x[0])
                    target_entity = entities_after[0][1]

            if not target_entity:
                distinct_fact_entities = {
                    _normalize(f.entity_id) for f in cited_facts if f.entity_id
                }
                if len(distinct_fact_entities) == 1:
                    target_entity = next(iter(distinct_fact_entities))
                elif len(ctx.plan_entities) == 1:
                    target_entity = _normalize(next(iter(ctx.plan_entities)))

            # Determine associated metric for this span
            clause_start = max(
                norm_text.rfind(",", 0, m.start()),
                norm_text.rfind(";", 0, m.start()),
                norm_text.rfind(".", 0, m.start()),
                norm_text.rfind(" và ", 0, m.start()),
                norm_text.rfind(" nhưng ", 0, m.start()),
            )
            clause_start = 0 if clause_start == -1 else clause_start + 1

            clause_end = len(norm_text)
            for sep in (",", ";", ".", " và ", " nhưng "):
                idx = norm_text.find(sep, m.end())
                if idx != -1 and idx < clause_end:
                    clause_end = idx

            clause_text = norm_text[clause_start:clause_end]

            associated_metric: str | None = None
            metric_terms_sorted: list[tuple[str, str]] = []
            for mid, terms in ctx.metric_terms.items():
                for term in terms:
                    metric_terms_sorted.append((_normalize(term), mid))
            metric_terms_sorted.sort(key=lambda x: len(x[0]), reverse=True)
            for term_norm, mid in metric_terms_sorted:
                if term_norm in clause_text:
                    associated_metric = mid
                    break

            if not associated_metric:
                for term_norm, mid in metric_terms_sorted:
                    if term_norm in norm_text:
                        associated_metric = mid
                        break

            applicable_rf = rank_facts
            if target_entity:
                applicable_rf = [rf for rf in applicable_rf if _normalize(rf.entity_id or "") == target_entity]
            if associated_metric:
                applicable_rf = [rf for rf in applicable_rf if rf.metric_id == associated_metric]

            groups = m.groups()
            rank_matched = False

            if len(groups) == 2 and groups[0].isdigit() and groups[1].isdigit():
                # N/M
                n_val = int(groups[0])
                m_val = int(groups[1])
                for rf in applicable_rf:
                    if rf.denominator == m_val and (rf.rank_better == n_val or rf.rank_desc == n_val or round(rf.value or 0) == n_val):
                        rank_matched = True
                        break
            elif len(groups) == 2 and (groups[0] in ("cao", "thấp", "tốt", "kém", "dày", "mỏng")):
                word_type = groups[0]
                n_ord = _parse_order_token(groups[1]) or 1
                for rf in applicable_rf:
                    den = rf.denominator or 1
                    if word_type in ("cao", "dày"):
                        if rf.rank_desc == n_ord:
                            rank_matched = True
                            break
                    elif word_type in ("thấp", "mỏng"):
                        if rf.rank_desc == (den + 1 - n_ord):
                            rank_matched = True
                            break
                    elif word_type == "tốt":
                        if rf.rank_better == n_ord:
                            rank_matched = True
                            break
                    elif word_type == "kém":
                        if rf.rank_better == (den + 1 - n_ord):
                            rank_matched = True
                            break
            elif len(groups) >= 1 and groups[0] is not None:
                tok = groups[0]
                if tok in ("cao", "thấp", "tốt", "kém", "dày", "mỏng"):
                    # superlative ... nhất
                    for rf in applicable_rf:
                        den = rf.denominator or 1
                        if tok in ("cao", "dày"):
                            if rf.rank_desc == 1:
                                rank_matched = True
                                break
                        elif tok in ("thấp", "mỏng"):
                            if rf.rank_desc == den:
                                rank_matched = True
                                break
                        elif tok == "tốt":
                            if rf.rank_better == 1:
                                rank_matched = True
                                break
                        elif tok == "kém":
                            if rf.rank_better == den:
                                rank_matched = True
                                break
                elif tok in ("dẫn đầu", "đứng đầu"):
                    rank_matched = any(rf.rank_better == 1 for rf in applicable_rf)
                elif tok in ("đứng cuối", "xếp cuối", "đội sổ"):
                    rank_matched = any(rf.rank_better == (rf.denominator or 1) for rf in applicable_rf)
                elif tok == "nhóm đầu":
                    rank_matched = any(
                        rf.rank_better is not None and rf.rank_better <= max(1, round((rf.denominator or 1) / 3))
                        for rf in applicable_rf
                    )
                elif tok == "nhóm cuối":
                    rank_matched = any(
                        rf.rank_better is not None
                        and rf.rank_better >= (rf.denominator or 1) + 1 - max(1, round((rf.denominator or 1) / 3))
                        for rf in applicable_rf
                    )
                else:
                    # hạng N or thứ N
                    n_ord = _parse_order_token(tok)
                    if n_ord:
                        rank_matched = any(
                            rf.rank_better == n_ord or rf.rank_desc == n_ord or round(rf.value or 0) == n_ord
                            for rf in applicable_rf
                        )
            else:
                # Standalone nhất nhóm (len(groups) == 0)
                rank_matched = any(rf.rank_better == 1 for rf in applicable_rf)

            if not rank_matched:
                return SentenceVerdict(
                    ok=False,
                    reason_code="rank_mismatch",
                    reason=f"Thứ hạng '{matched_span}' không khớp giá trị xếp hạng trong fact peer_rank.",
                    numbers_checked=1,
                    numbers_matched=0,
                )
            mask_span(m.start(), m.end())

    # 8. Entity count checks: "(số|một..mười|N) (ngân hàng|thành viên)"
    ent_count_pat = re.compile(
        r"(?<!\w)(?:số|\b(một|hai|ba|bốn|năm|sáu|bảy|tám|chín|mười|\d+))\s+(?:ngân hàng|thành viên)(?!\w)"
    )
    for m in ent_count_pat.finditer("".join(working_chars)):
        tok = m.group(1)
        if tok:
            cnt_val = _parse_order_token(tok)
            if cnt_val:
                matched_denom = any(f.denominator == cnt_val for f in cited_facts if f.denominator is not None)
                distinct_entities = {
                    _normalize(ent)
                    for f in cited_facts
                    for ent in (f.entity_id, f.other_entity_id)
                    if ent
                }
                matched_entities = len(distinct_entities) == cnt_val
                if not (matched_denom or matched_entities):
                    return SentenceVerdict(
                        ok=False,
                        reason_code="number_mismatch",
                        reason=f"Số lượng '{tok} ngân hàng/thành viên' không khớp denominator của fact nào.",
                        numbers_checked=1,
                        numbers_matched=0,
                    )
        mask_span(m.start(), m.end())

    # Mask loan classification groups and regulatory terms containing digits
    # e.g., "nhóm 3-5", "nhóm 3–5", "nhóm 1", "tier 1", "cấp 1", "thông tư 41"
    banking_term_patterns = [
        re.compile(r"(?:\(|\bnợ\s+)nhóm\s*[1-5](?:\s*[-–—]\s*[1-5])?\)?"),
        re.compile(r"(?<!\w)nhóm\s*[1-5]\s*[-–—]\s*[1-5](?!\w)"),
        re.compile(r"(?<!\w)tier\s*[1-3](?!\w)"),
        re.compile(r"(?<!\w)cấp\s*[1-3](?!\w)"),
        re.compile(r"(?<!\w)basel\s*[1-3iIvVxX]+(?!\w)"),
        re.compile(r"(?<!\w)(?:thông tư|nghị định)\s*\d+(?:/\d+)?(?!\w)"),
    ]
    for b_pat in banking_term_patterns:
        for bm in b_pat.finditer("".join(working_chars)):
            mask_span(bm.start(), bm.end())

    for term_list in ctx.metric_terms.values():
        for term in term_list:
            if any(ch.isdigit() for ch in term):
                term_norm = _normalize(term)
                for tm in re.finditer(rf"(?<!\w){re.escape(term_norm)}(?!\w)", "".join(working_chars)):
                    mask_span(tm.start(), tm.end())

    # 9. Remaining numbers checks
    # Regex for number with optional suffix
    # Suffixes: %, điểm %, điểm phần trăm, pp, điểm, lần, x
    num_pat = re.compile(
        r"(?<!\w)([+-]?\d+(?:[.,]\d+)?)(?:\s*(%|điểm\s*%|điểm\s+phần\s+trăm|pp|điểm|lần|x))?(?!\w)"
    )

    numbers_checked = 0
    numbers_matched = 0

    # Build metric name lookup for entity/metric proximity binding
    metric_name_to_id: dict[str, str] = {}
    for mid, terms in ctx.metric_terms.items():
        for term in terms:
            metric_name_to_id[_normalize(term)] = mid

    current_working_str = "".join(working_chars)
    for m in num_pat.finditer(current_working_str):
        num_str = m.group(1)
        sfx_raw = m.group(2)
        numbers_checked += 1

        clean_num_str = num_str.replace(",", ".").lstrip("+")
        val_parsed = abs(float(clean_num_str)) if (sfx_raw or clean_num_str.startswith("-")) else float(clean_num_str)
        # Decimal digits
        if "." in clean_num_str:
            d_digits = len(clean_num_str.split(".")[1])
        else:
            d_digits = 0
        tolerance = 0.5 * (10 ** (-d_digits)) + 1e-9

        # Categorize unit
        unit_cat = "any"
        if sfx_raw:
            sfx_norm = _normalize(sfx_raw)
            if sfx_norm == "%":
                unit_cat = "pct"
            elif sfx_norm in ("điểm %", "điểm phần trăm", "pp", "điểm"):
                unit_cat = "pp"
            elif sfx_norm in ("lần", "x"):
                unit_cat = "ratio"

        # Context detection in 6 words preceding the number
        preceding_text = norm_text[: m.start()]
        preceding_words = preceding_text.split() if preceding_text.split() else []
        last_6_words = preceding_words[-6:] if len(preceding_words) >= 6 else preceding_words
        preceding_snippet = " ".join(last_6_words)
        extended_snippet = " ".join(preceding_words[-10:]) if len(preceding_words) >= 10 else " ".join(preceding_words)

        associated_metric: str | None = None
        sorted_terms = sorted(metric_name_to_id.items(), key=lambda it: len(it[0]), reverse=True)
        for term, mid in sorted_terms:
            if term in preceding_snippet:
                associated_metric = mid
                break
            elif term in extended_snippet and any(w in last_6_words for w in term.split()):
                associated_metric = mid
                break

        # Check entity right before number (or within preceding snippet)
        associated_entity: str | None = None
        for ent in ctx.plan_entities | ctx.catalog_entities:
            ent_norm = _normalize(ent)
            if preceding_words and ent_norm in preceding_words[-3:]:
                associated_entity = ent_norm
                break

        # Also support comparing two facts where the entity is directly before the number
        # or after the number (e.g. "của E1 10,25 lần, cao hơn mức 6,46 lần của E2")
        if not associated_entity:
            following_text = norm_text[m.end() : m.end() + 25]
            following_words = following_text.split()[:3]
            for ent in ctx.plan_entities | ctx.catalog_entities:
                ent_norm = _normalize(ent)
                if ent_norm in following_words:
                    associated_entity = ent_norm
                    break

        # Find matching fact
        has_unit_mismatch = False
        found_fact = False

        for f in cited_facts:
            if f.value is None:
                continue
            f_val = float(f.value)

            f_cat = _classify_fact_unit(f)

            # Target comparison value based on unit category
            if unit_cat == "pp":
                if f_cat != "pp":
                    if abs(abs(f_val) - val_parsed) <= tolerance or abs(f_val - val_parsed) <= tolerance:
                        has_unit_mismatch = True
                    continue
                comp_val = abs(f_val)
            elif unit_cat == "pct":
                if f_cat != "pct":
                    if abs(f_val - val_parsed) <= tolerance or abs(abs(f_val) - val_parsed) <= tolerance:
                        has_unit_mismatch = True
                    continue
                comp_val = f_val
            elif unit_cat == "ratio":
                if f_cat != "ratio":
                    if abs(f_val - val_parsed) <= tolerance or abs(abs(f_val) - val_parsed) <= tolerance:
                        has_unit_mismatch = True
                    continue
                comp_val = f_val
            else:
                # Any unit
                comp_val = abs(f_val) if f_cat == "pp" else f_val

            # Tolerance check: strictly compare against raw value v with 0.5 * 10^-d + 1e-9
            if abs(comp_val - val_parsed) > tolerance:
                continue

            # Metric check if metric was explicitly associated in preceding 6 words
            if associated_metric:
                if f.fact_type == "derived_ratio":
                    # Derived ratio permits constituent metrics in formula
                    formula_parts = f.metric_id.lower()
                    m_short = associated_metric.rsplit(".", 1)[-1].lower()
                    if m_short not in formula_parts and f.metric_id != associated_metric:
                        continue
                elif f.metric_id != associated_metric:
                    continue

            # Entity check if entity was explicitly associated
            if associated_entity and f.fact_type not in ("peer_median", "spread"):
                if f.fact_type in ("pairwise_gap", "lead_count"):
                    f_ents = {_normalize(f.entity_id or ""), _normalize(f.other_entity_id or "")}
                    if associated_entity not in f_ents:
                        continue
                else:
                    f_ent_norm = _normalize(f.entity_id or "")
                    if f_ent_norm and f_ent_norm != associated_entity:
                        continue

            found_fact = True
            break

        # Spec §2 Rule 9: For pp unit, if no direct gap fact is cited, check if two cited facts
        # of the same metric (e.g. value and peer_median, or two values) have matching difference
        if not found_fact and unit_cat == "pp":
            val_and_med = [
                f for f in cited_facts
                if f.fact_type in ("value", "peer_median")
                and f.value is not None
                and _classify_fact_unit(f) == "pct"
            ]
            for i in range(len(val_and_med)):
                for j in range(i + 1, len(val_and_med)):
                    f1 = val_and_med[i]
                    f2 = val_and_med[j]
                    if f1.metric_id == f2.metric_id:
                        v1 = float(f1.value)
                        v2 = float(f2.value)
                        diff_raw = abs(v1 - v2)
                        diff_disp = abs(round(v1, d_digits) - round(v2, d_digits))
                        if abs(diff_raw - val_parsed) <= tolerance or abs(diff_disp - val_parsed) <= tolerance:
                            found_fact = True
                            has_unit_mismatch = False
                            break
                if found_fact:
                    break

        if not found_fact:
            if has_unit_mismatch:
                return SentenceVerdict(
                    ok=False,
                    reason_code="unit_mismatch",
                    reason=f"Đơn vị của số {val_parsed} không khớp loại fact được trích dẫn.",
                    numbers_checked=numbers_checked,
                    numbers_matched=numbers_matched,
                )
            return SentenceVerdict(
                ok=False,
                reason_code="number_mismatch",
                reason=f"Số {val_parsed} không khớp giá trị fact được trích dẫn sau khi làm tròn hiển thị.",
                numbers_checked=numbers_checked,
                numbers_matched=numbers_matched,
            )

        numbers_matched += 1

    # 10. Trend checks
    # Mask "nợ xấu" to avoid false positive matching with "xấu đi"
    trend_eval_text = re.sub(r"(?<!\w)nợ\s+xấu(?!\w)", "nợ ___", norm_text)
    # Mask "sự ổn định" to avoid false positive matching with trend "ổn định"
    trend_eval_text = re.sub(r"(?<!\w)sự\s+ổn\s+định(?!\w)", "sự ___", trend_eval_text)

    trend_terms_found = [
        tw for tw in ctx.lexicon.trend_words
        if re.search(rf"(?<!\w){re.escape(_normalize(tw))}(?!\w)", trend_eval_text)
    ]
    if trend_terms_found:
        delta_facts = [f for f in cited_facts if f.fact_type in ("delta", "median_delta")]
        gap_facts = [f for f in cited_facts if f.fact_type == "gap_to_median"]

        if not delta_facts and len(gap_facts) < 2:
            return SentenceVerdict(
                ok=False,
                reason_code="trend_without_delta",
                reason="Nhận định xu hướng nhưng không trích dẫn fact delta hoặc chuỗi gap.",
                numbers_checked=numbers_checked,
                numbers_matched=numbers_matched,
            )

        # Select delta based on nearest metric
        primary_delta: Fact | None = next((f for f in delta_facts if f.fact_type == "delta"), None)
        if not primary_delta and delta_facts:
            primary_delta = delta_facts[0]

        m_delta = next((f for f in cited_facts if f.fact_type == "median_delta"), None)

        for tw in trend_terms_found:
            tw_norm = _normalize(tw)

            # Determine whether this trend term describes the median or the primary entity
            eval_delta = primary_delta
            if m_delta is not None and tw_norm not in ("thu hẹp", "nới rộng", "ngược chiều", "ngược xu hướng", "liên tục"):
                m_tw = re.search(rf"(?<!\w){re.escape(tw_norm)}(?!\w)", trend_eval_text)
                if m_tw:
                    preceding = trend_eval_text[:m_tw.start()]
                    preceding_clause = preceding.split(",")[-1]
                    if any(term in preceding_clause for term in ("trung vị", "nhóm ngân hàng", "toàn ngành", "cả nhóm")):
                        eval_delta = m_delta

            flat = _get_metric_flat(ctx.flat_pp, eval_delta.metric_id if eval_delta else "", default=0.05)
            d_val = float(eval_delta.value) if (eval_delta and eval_delta.value is not None) else 0.0

            if tw_norm in ("thu hẹp", "nới rộng"):
                if len(gap_facts) < 2:
                    return SentenceVerdict(
                        ok=False,
                        reason_code="trend_without_delta",
                        reason=f"Từ xu hướng '{tw}' cần ít nhất 2 gap fact.",
                        numbers_checked=numbers_checked,
                        numbers_matched=numbers_matched,
                    )
                # Sort gaps chronologically
                sorted_gaps = sorted(gap_facts, key=lambda g: g.period)
                g_first = abs(float(sorted_gaps[0].value or 0))
                g_last = abs(float(sorted_gaps[-1].value or 0))
                if tw_norm == "thu hẹp" and not (g_last < g_first):
                    return SentenceVerdict(
                        ok=False,
                        reason_code="trend_direction_mismatch",
                        reason="Khoảng cách không thu hẹp theo dữ liệu thực tế.",
                        numbers_checked=numbers_checked,
                        numbers_matched=numbers_matched,
                    )
                elif tw_norm == "nới rộng" and not (g_last > g_first):
                    return SentenceVerdict(
                        ok=False,
                        reason_code="trend_direction_mismatch",
                        reason="Khoảng cách không nới rộng theo dữ liệu thực tế.",
                        numbers_checked=numbers_checked,
                        numbers_matched=numbers_matched,
                    )
            elif tw_norm in ("ngược chiều", "ngược xu hướng"):
                if not (primary_delta and m_delta and primary_delta.value is not None and m_delta.value is not None):
                    return SentenceVerdict(
                        ok=False,
                        reason_code="trend_without_delta",
                        reason="Nhận định ngược xu hướng cần cả delta doanh nghiệp và median_delta.",
                        numbers_checked=numbers_checked,
                        numbers_matched=numbers_matched,
                    )
                p_val = float(primary_delta.value)
                med_val = float(m_delta.value)
                if not (p_val * med_val < 0 and abs(p_val) > flat and abs(med_val) > flat):
                    return SentenceVerdict(
                        ok=False,
                        reason_code="trend_direction_mismatch",
                        reason="Biến động không ngược chiều với trung vị nhóm.",
                        numbers_checked=numbers_checked,
                        numbers_matched=numbers_matched,
                    )
            elif tw_norm == "liên tục":
                # e.g. "tăng liên tục" or "giảm liên tục"
                is_tang = any(t in ("tăng", "tăng lên", "đi lên") for t in trend_terms_found)
                is_giam = any(t in ("giảm", "giảm xuống", "đi xuống") for t in trend_terms_found)
                seq_deltas = [f for f in cited_facts if f.fact_type == "delta" and f.from_period]
                if not seq_deltas:
                    return SentenceVerdict(
                        ok=False,
                        reason_code="trend_direction_mismatch",
                        reason="Thiếu chuỗi delta liên tiếp để chứng minh liên tục.",
                        numbers_checked=numbers_checked,
                        numbers_matched=numbers_matched,
                    )
                for sd in seq_deltas:
                    sd_val = float(sd.value or 0)
                    if is_tang and not (sd_val > flat):
                        return SentenceVerdict(
                            ok=False,
                            reason_code="trend_direction_mismatch",
                            reason="Xu hướng không tăng liên tục ở tất cả các kỳ trích dẫn.",
                            numbers_checked=numbers_checked,
                            numbers_matched=numbers_matched,
                        )
                    if is_giam and not (sd_val < -flat):
                        return SentenceVerdict(
                            ok=False,
                            reason_code="trend_direction_mismatch",
                            reason="Xu hướng không giảm liên tục ở tất cả các kỳ trích dẫn.",
                            numbers_checked=numbers_checked,
                            numbers_matched=numbers_matched,
                        )
            elif tw_norm in ("tăng", "tăng lên", "đi lên"):
                if not (d_val > flat):
                    return SentenceVerdict(
                        ok=False,
                        reason_code="trend_direction_mismatch",
                        reason=f"Nhận định '{tw}' nhưng delta không vượt ngưỡng tăng (delta={d_val}).",
                        numbers_checked=numbers_checked,
                        numbers_matched=numbers_matched,
                    )
            elif tw_norm in ("giảm", "giảm xuống", "đi xuống", "suy giảm"):
                if not (d_val < -flat):
                    return SentenceVerdict(
                        ok=False,
                        reason_code="trend_direction_mismatch",
                        reason=f"Nhận định '{tw}' nhưng delta không vượt ngưỡng giảm (delta={d_val}).",
                        numbers_checked=numbers_checked,
                        numbers_matched=numbers_matched,
                    )
            elif tw_norm in ("đi ngang", "ổn định", "không đổi"):
                if not (abs(d_val) <= flat):
                    return SentenceVerdict(
                        ok=False,
                        reason_code="trend_direction_mismatch",
                        reason=f"Nhận định '{tw}' nhưng biến động vượt ngưỡng đi ngang (|delta|={abs(d_val)} > {flat}).",
                        numbers_checked=numbers_checked,
                        numbers_matched=numbers_matched,
                    )
            elif tw_norm in ("cải thiện", "xấu đi"):
                m_dir = ctx.directions.get(eval_delta.metric_id if eval_delta else "", "higher_is_better")
                if m_dir == "lower_is_better":
                    improved = d_val < -flat
                    worsened = d_val > flat
                else:
                    improved = d_val > flat
                    worsened = d_val < -flat

                if tw_norm == "cải thiện" and not improved:
                    return SentenceVerdict(
                        ok=False,
                        reason_code="trend_direction_mismatch",
                        reason=f"Nhận định cải thiện nhưng chiều biến động không tốt hơn ngưỡng quy định (delta={d_val}).",
                        numbers_checked=numbers_checked,
                        numbers_matched=numbers_matched,
                    )
                elif tw_norm == "xấu đi" and not worsened:
                    return SentenceVerdict(
                        ok=False,
                        reason_code="trend_direction_mismatch",
                        reason=f"Nhận định xấu đi nhưng chiều biến động không tệ hơn ngưỡng quy định (delta={d_val}).",
                        numbers_checked=numbers_checked,
                        numbers_matched=numbers_matched,
                    )

    # 11. Comparison checks
    # Mask qualitative implication clause introduced by "hàm ý"
    comp_eval_text = re.sub(r"(?<!\w)hàm\s+ý.*", "", norm_text)

    comp_terms_found = [
        cw for cw in ctx.lexicon.comparison_words
        if re.search(rf"(?<!\w){re.escape(_normalize(cw))}(?!\w)", comp_eval_text)
    ]
    if comp_terms_found:
        gap_facts = [f for f in cited_facts if f.fact_type in ("gap_to_median", "pairwise_gap")]
        val_facts = [f for f in cited_facts if f.fact_type in ("value", "peer_median", "derived_ratio") and f.value is not None]
        lead_facts = [f for f in cited_facts if f.fact_type == "lead_count" and f.value is not None]
        ratio_facts = [f for f in cited_facts if f.fact_type == "ratio_to_median" and f.value is not None]

        # If gap_facts is empty in cited_facts, look up in ctx.facts for matching entity/metric
        if not gap_facts and ctx.facts:
            relevant_entities = {f.entity_id for f in cited_facts if f.entity_id}
            relevant_metrics = {f.metric_id for f in cited_facts if f.metric_id}
            for f in ctx.facts.values():
                if f.fact_type in ("gap_to_median", "pairwise_gap") and f.value is not None:
                    if f.metric_id in relevant_metrics and (not f.entity_id or f.entity_id in relevant_entities):
                        gap_facts.append(f)

        metrics_seen: dict[str, list[Fact]] = {}
        if len(val_facts) >= 2:
            for vf in val_facts:
                metrics_seen.setdefault(vf.metric_id, []).append(vf)
        candidate_metric_ids = [m for m, vfs in metrics_seen.items() if len(vfs) >= 2]
        same_metric_vals = len(candidate_metric_ids) > 0

        has_lead_win = any(float(lf.value or 0) > (float(lf.denominator or 0) / 2.0) for lf in lead_facts)
        has_ratio_win = any(float(rf.value or 0) > 1.0 for rf in ratio_facts)
        has_ratio_loss = any(float(rf.value or 0) < 1.0 for rf in ratio_facts)

        if not gap_facts and not same_metric_vals and not has_lead_win and not ratio_facts:
            return SentenceVerdict(
                ok=False,
                reason_code="comparison_direction_mismatch",
                reason="Nhận định so sánh nhưng không có fact gap hoặc hai giá trị cùng chỉ tiêu.",
                numbers_checked=numbers_checked,
                numbers_matched=numbers_matched,
            )

        # Build comparison candidate tuples: (gap_val, flat, m_dir, metric_id)
        comp_candidates: list[tuple[float, float, str, str]] = []
        for gf in gap_facts:
            g_val = float(gf.value or 0)
            g_flat = _get_metric_flat(ctx.flat_pp, gf.metric_id, default=0.05)
            g_dir = ctx.directions.get(gf.metric_id, "higher_is_better")
            comp_candidates.append((g_val, g_flat, g_dir, gf.metric_id))

        for m in candidate_metric_ids:
            vfs = metrics_seen[m]
            v_ent = next((f for f in vfs if f.fact_type == "value"), None)
            v_med = next((f for f in vfs if f.fact_type == "peer_median"), None)
            if v_ent and v_med:
                g_val = float(v_ent.value or 0) - float(v_med.value or 0)
            else:
                def _ent_pos(f: Fact) -> int:
                    if f.entity_id:
                        p = comp_eval_text.find(_normalize(f.entity_id))
                        return p if p >= 0 else 999999
                    return 999999
                sorted_vfs = sorted(vfs, key=_ent_pos)
                g_val = float(sorted_vfs[0].value or 0) - float(sorted_vfs[1].value or 0)
            g_flat = _get_metric_flat(ctx.flat_pp, m, default=0.05)
            g_dir = ctx.directions.get(m, "higher_is_better")
            comp_candidates.append((g_val, g_flat, g_dir, m))

        # Check if sentence mentions specific metric terms
        mentioned_metrics = set()
        all_candidate_mids = set(c[3] for c in comp_candidates)
        for m in all_candidate_mids:
            terms = ctx.metric_terms.get(m, ())
            if any(re.search(rf"(?<!\w){re.escape(_normalize(t))}(?!\w)", comp_eval_text) for t in terms):
                mentioned_metrics.add(m)

        for cw in comp_terms_found:
            cw_norm = _normalize(cw)
            eval_cands = [c for c in comp_candidates if c[3] in mentioned_metrics] if mentioned_metrics else comp_candidates
            if not eval_cands:
                eval_cands = comp_candidates

            if cw_norm in ("cao hơn", "dày hơn", "vượt", "trên trung vị"):
                matched = any(c[0] > c[1] for c in eval_cands) or has_ratio_win or has_lead_win
                if not matched:
                    last_gap = eval_cands[0][0] if eval_cands else 0.0
                    return SentenceVerdict(
                        ok=False,
                        reason_code="comparison_direction_mismatch",
                        reason=f"Nhận định '{cw}' nhưng chênh lệch không dương vượt ngưỡng (gap={last_gap}).",
                        numbers_checked=numbers_checked,
                        numbers_matched=numbers_matched,
                    )
            elif cw_norm in ("thấp hơn", "mỏng hơn", "dưới trung vị"):
                matched = any(c[0] < -c[1] for c in eval_cands) or has_ratio_loss
                if not matched:
                    last_gap = eval_cands[0][0] if eval_cands else 0.0
                    return SentenceVerdict(
                        ok=False,
                        reason_code="comparison_direction_mismatch",
                        reason=f"Nhận định '{cw}' nhưng chênh lệch không âm vượt ngưỡng (gap={last_gap}).",
                        numbers_checked=numbers_checked,
                        numbers_matched=numbers_matched,
                    )
            elif cw_norm in ("tốt hơn", "nhỉnh hơn", "dẫn ở", "vượt trội"):
                matched = any(
                    (c[0] < -c[1]) if c[2] == "lower_is_better" else (c[0] > c[1])
                    for c in eval_cands
                ) or has_lead_win or has_ratio_win
                if not matched:
                    return SentenceVerdict(
                        ok=False,
                        reason_code="comparison_direction_mismatch",
                        reason=f"Nhận định '{cw}' nhưng kết quả không tốt hơn theo chiều chỉ tiêu.",
                        numbers_checked=numbers_checked,
                        numbers_matched=numbers_matched,
                    )
            elif cw_norm in ("kém hơn",):
                matched = any(
                    (c[0] > c[1]) if c[2] == "lower_is_better" else (c[0] < -c[1])
                    for c in eval_cands
                ) or has_ratio_loss
                if not matched:
                    return SentenceVerdict(
                        ok=False,
                        reason_code="comparison_direction_mismatch",
                        reason=f"Nhận định '{cw}' nhưng kết quả không kém hơn theo chiều chỉ tiêu.",
                        numbers_checked=numbers_checked,
                        numbers_matched=numbers_matched,
                    )
            elif cw_norm in ("bằng trung vị", "ngang trung vị", "ngang nhóm", "đúng bằng trung vị", "tương đương trung vị", "bằng trung vị nhóm", "ngang với trung vị"):
                matched = any(abs(c[0]) <= c[1] for c in eval_cands)
                if not matched:
                    last_gap = eval_cands[0][0] if eval_cands else 0.0
                    flat_thr = eval_cands[0][1] if eval_cands else 0.05
                    return SentenceVerdict(
                        ok=False,
                        reason_code="comparison_direction_mismatch",
                        reason=f"Nhận định '{cw}' nhưng chênh lệch vượt ngưỡng đi ngang (|gap|={abs(last_gap)} > {flat_thr}).",
                        numbers_checked=numbers_checked,
                        numbers_matched=numbers_matched,
                    )

    return SentenceVerdict(
        ok=True,
        reason_code=None,
        reason=None,
        numbers_checked=numbers_checked,
        numbers_matched=numbers_matched,
    )


def verify_all(
    sentences: Sequence[NarrativeSentence],
    ctx: VerificationContext,
) -> tuple[list[NarrativeSentence], list[DroppedSentence], AuditCounts]:
    """Verify all candidate narrative sentences and aggregate audit statistics."""
    accepted: list[NarrativeSentence] = []
    dropped: list[DroppedSentence] = []
    total_nums_checked = 0
    total_nums_matched = 0

    for s in sentences:
        verdict = verify_sentence(s, ctx)
        total_nums_checked += verdict.numbers_checked
        total_nums_matched += verdict.numbers_matched
        if verdict.ok:
            accepted.append(s)
        else:
            dropped.append(
                DroppedSentence(
                    sentence_id=s.sentence_id,
                    author=s.author,
                    text=s.text,
                    reason_code=verdict.reason_code or "rejected",
                    reason=verdict.reason or "Không vượt qua kiểm chứng.",
                )
            )

    counts = AuditCounts(
        sentences_checked=len(sentences),
        sentences_accepted=len(accepted),
        numbers_checked=total_nums_checked,
        numbers_matched=total_nums_matched,
    )
    return accepted, dropped, counts
