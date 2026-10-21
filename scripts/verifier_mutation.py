#!/usr/bin/env python3
"""Verifier mutation testing for narrative verification recall evaluation.

Generates systematic mutants on accepted analytical sentences from ER-9 runs
across 12 error-injection operators, runs the deterministic sentence verifier
on every mutant, measures catch rates with Wilson 95% confidence intervals,
and outputs detailed mutation records and markdown summaries.
"""

from __future__ import annotations

import argparse
import csv
import json
import logging
import math
import random
import re
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Mapping, Sequence

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT))

from scripts.er8_score import build_verification_context_for_run, extract_sentences_from_report_spec
from thesis_data.narrative_verification import (
    NarrativeSentence,
    SentenceVerdict,
    VerificationContext,
    verify_sentence,
)
from thesis_data.report_facts import Fact

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("verifier_mutation")

ALL_OPERATORS = [
    "number_small",
    "number_large",
    "digit_swap",
    "rank",
    "denominator",
    "period",
    "entity_swap",
    "direction_flip",
    "metric_swap",
    "unsupported_number",
    "causal_claim",
    "recommendation",
]

BANK_TICKERS = (
    "VCB", "CTG", "BID", "TCB", "MBB", "VPB", "HDB", "ACB",
    "STB", "TPB", "VIB", "LPB", "SHB", "MSB", "SSB", "OCB", "EIB",
)


def wilson_ci(k: int, n: int, confidence: float = 0.95) -> tuple[float, float]:
    """Calculate Wilson score interval for binomial proportion."""
    if n <= 0:
        return (0.0, 0.0)
    z = 1.959963984540054 if confidence == 0.95 else 1.96
    p = k / n
    denom = 1.0 + (z * z) / n
    center = (p + (z * z) / (2.0 * n)) / denom
    spread = (z / denom) * math.sqrt((p * (1.0 - p)) / n + (z * z) / (4.0 * (n * n)))
    lower = max(0.0, center - spread)
    upper = min(1.0, center + spread)
    return (round(lower, 4), round(upper, 4))


# ---------------------------------------------------------------------------
# Text analysis & extraction helpers
# ---------------------------------------------------------------------------

def find_metric_numbers(text: str) -> list[tuple[str, str, int, int]]:
    """Identify metric numbers and their spans in Vietnamese text.

    Masks period years/quarters, ranks, and banking terms first so only
    financial metric numbers are returned.
    Returns: list of (raw_str, suffix, start_char, end_char)
    """
    chars = list(text)

    def mask(m: re.Match[str]) -> None:
        for idx in range(m.start(), m.end()):
            chars[idx] = " "

    # Mask periods (e.g. quý 4/2024, năm 2024, 2024, 4 quý)
    re.sub(r"(?<!\w)(?:quý\s+[1-4]|q[1-4])(?:\s*(?:/|\s*năm\s*)\d{4})?(?!\w)", mask, text, flags=re.IGNORECASE)
    re.sub(r"(?<!\w)năm\s+\d{4}(?!\w)", mask, text, flags=re.IGNORECASE)
    re.sub(r"(?<!\w)20\d{2}(?!\w)", mask, text)
    re.sub(r"(?<!\w)\d+\s+quý(?!\w)", mask, text, flags=re.IGNORECASE)

    # Mask rank expressions (hạng 7/10, thứ 4/10, xếp hạng 7/10, 7/10 where denom <= 50)
    re.sub(r"(?<!\w)(?:hạng|thứ|xếp hạng)\s+\d+(?:\s*(?:/|trên)\s*\d+)?(?!\w)", mask, text, flags=re.IGNORECASE)
    re.sub(r"(?<!\w)\d+\s*/\s*(?:[1-9]|[1-4]\d|50)(?!\w)", mask, text)

    # Mask banking classification terms (e.g. nhóm 3-5, tier 1, cấp 1)
    re.sub(r"(?<!\w)nhóm\s*[1-5](?:\s*[-–—]\s*[1-5])?(?!\w)", mask, text, flags=re.IGNORECASE)
    re.sub(r"(?<!\w)(?:tier|cấp)\s*[1-3](?!\w)", mask, text, flags=re.IGNORECASE)
    re.sub(r"(?<!\w)(?:thông tư|nghị định)\s*\d+(?:/\d+)?(?!\w)", mask, text, flags=re.IGNORECASE)

    masked_str = "".join(chars)
    num_pat = re.compile(r"(?<!\w)([+-]?\d+(?:[.,]\d+)?)(?:\s*(%|điểm\s*%|điểm\s+phần\s+trăm|pp|điểm|lần|x))?(?!\w)")
    results: list[tuple[str, str, int, int]] = []
    for m in num_pat.finditer(masked_str):
        raw = m.group(1)
        suffix = m.group(2) or ""
        span = m.span(1)
        results.append((raw, suffix, span[0], span[1]))
    return results


def _format_vietnamese_number(val: float, decimal_digits: int, signed: bool = False, sign_char: str = "") -> str:
    """Format floating point number the Vietnamese way using comma as decimal separator."""
    formatted = f"{val:.{decimal_digits}f}"
    parts = formatted.split(".")
    int_part = parts[0]
    frac_part = f",{parts[1]}" if len(parts) > 1 and decimal_digits > 0 else ""
    res = f"{int_part}{frac_part}"
    if signed and sign_char == "+" and not res.startswith(("-", "+")):
        res = f"+{res}"
    return res


# ---------------------------------------------------------------------------
# Mutation Operators
# ---------------------------------------------------------------------------

def mutate_number_small(text: str, rng: random.Random) -> str | None:
    """Change a cited number by 1-5% and re-format the Vietnamese way."""
    nums = find_metric_numbers(text)
    if not nums:
        return None
    raw, suffix, start, end = rng.choice(nums)
    sign_char = "+" if raw.startswith("+") else ("-" if raw.startswith("-") else "")
    clean = raw.replace(",", ".").lstrip("+")
    try:
        val = float(clean)
    except ValueError:
        return None

    d_digits = len(clean.split(".")[1]) if "." in clean else 1
    tol = 0.5 * (10 ** (-d_digits))

    # Pick factor between 1% and 5%
    factor_sign = rng.choice([-1.0, 1.0])
    factor_pct = rng.uniform(0.015, 0.045)
    new_val = val * (1.0 + factor_sign * factor_pct)

    # Ensure difference exceeds verifier tolerance
    if abs(new_val - val) <= tol:
        new_val = val + (factor_sign * (tol + 10 ** (-d_digits)))

    new_str = _format_vietnamese_number(new_val, d_digits, signed=bool(sign_char), sign_char=sign_char)
    if new_str == raw:
        # Fallback if precision truncated difference
        step = 10 ** (-d_digits)
        new_val = val + (step * (2 if factor_sign > 0 else -2))
        new_str = _format_vietnamese_number(new_val, d_digits, signed=bool(sign_char), sign_char=sign_char)

    return text[:start] + new_str + text[end:]


def mutate_number_large(text: str, rng: random.Random) -> str | None:
    """Multiply or divide a cited number by 2."""
    nums = find_metric_numbers(text)
    if not nums:
        return None
    raw, suffix, start, end = rng.choice(nums)
    sign_char = "+" if raw.startswith("+") else ("-" if raw.startswith("-") else "")
    clean = raw.replace(",", ".").lstrip("+")
    try:
        val = float(clean)
    except ValueError:
        return None

    d_digits = len(clean.split(".")[1]) if "." in clean else 1
    multiplier = 2.0 if (abs(val) < 2.0 or rng.random() < 0.5) else 0.5
    new_val = val * multiplier
    new_str = _format_vietnamese_number(new_val, d_digits, signed=bool(sign_char), sign_char=sign_char)
    if new_str == raw:
        new_str = _format_vietnamese_number(val * 2.0 + 1.0, d_digits, signed=bool(sign_char), sign_char=sign_char)

    return text[:start] + new_str + text[end:]


def mutate_digit_swap(text: str, rng: random.Random) -> str | None:
    """Swap two distinct digits in a cited number."""
    nums = find_metric_numbers(text)
    if not nums:
        return None

    # Filter to numbers that contain at least two distinct digits
    candidates = []
    for raw, sfx, s, e in nums:
        digits_only = [c for c in raw if c.isdigit()]
        if len(set(digits_only)) >= 2:
            candidates.append((raw, sfx, s, e))

    if not candidates:
        return None

    raw, suffix, start, end = rng.choice(candidates)
    # Find two distinct digit positions to swap
    digit_indices = [i for i, c in enumerate(raw) if c.isdigit()]
    pairs = [
        (i, j) for i in digit_indices for j in digit_indices
        if i < j and raw[i] != raw[j]
    ]
    if not pairs:
        return None
    i, j = rng.choice(pairs)
    chars = list(raw)
    chars[i], chars[j] = chars[j], chars[i]
    new_raw = "".join(chars)
    return text[:start] + new_raw + text[end:]


def mutate_rank(text: str, rng: random.Random) -> str | None:
    """Change a rank expression to another valid rank."""
    # Pattern: (hạng|thứ|xếp hạng) N/M or N/M (where M <= 50)
    pat = re.compile(
        r"(?<!\w)((?:hạng|thứ|xếp hạng)\s+(\d+)\s*(?:/|trên)\s*(\d+)|(\d+)\s*/\s*([1-9]|[1-4]\d|50))(?!\w)",
        flags=re.IGNORECASE,
    )
    matches = list(pat.finditer(text))
    if matches:
        m = rng.choice(matches)
        # Check groups
        if m.group(2) and m.group(3):
            prefix = m.group(1).split()[0]  # hạng or thứ or xếp
            curr_r = int(m.group(2))
            denom = int(m.group(3))
            sep = "/" if "/" in m.group(1) else " trên "
            # Pick another valid rank in [1, denom]
            choices = [r for r in range(1, denom + 1) if r != curr_r]
            new_r = rng.choice(choices) if choices else ((curr_r % denom) + 1)
            repl = f"{prefix} {new_r}{sep}{denom}"
            return text[:m.start()] + repl + text[m.end():]
        elif m.group(4) and m.group(5):
            curr_r = int(m.group(4))
            denom = int(m.group(5))
            choices = [r for r in range(1, denom + 1) if r != curr_r]
            new_r = rng.choice(choices) if choices else ((curr_r % denom) + 1)
            repl = f"{new_r}/{denom}"
            return text[:m.start()] + repl + text[m.end():]

    # Superlative / standing rank
    standing_pat = re.compile(r"(?<!\w)(dẫn đầu|đứng đầu|đứng cuối|xếp cuối|đội sổ)(?!\w)", flags=re.IGNORECASE)
    sm = standing_pat.search(text)
    if sm:
        curr_tok = sm.group(1).lower()
        repl = "đứng cuối" if curr_tok in ("dẫn đầu", "đứng đầu") else "dẫn đầu"
        return text[:sm.start()] + repl + text[sm.end():]

    return None


def mutate_denominator(text: str, rng: random.Random) -> str | None:
    """Change denominator from 10 to 9 or D to D-1."""
    # Pattern 1: rank ratio x/10 or x/D
    pat1 = re.compile(r"(?<!\w)(\d+)\s*(/|trên)\s*([1-9]|[1-4]\d|50)(?!\w)")
    m1 = pat1.search(text)
    if m1:
        nom = m1.group(1)
        sep = m1.group(2)
        denom = int(m1.group(3))
        new_denom = 9 if denom == 10 else (denom - 1 if denom > 1 else 9)
        repl = f"{nom}{sep}{new_denom}"
        return text[:m1.start()] + repl + text[m1.end():]

    # Pattern 2: N ngân hàng / thành viên
    pat2 = re.compile(r"(?<!\w)(10|[1-9])\s+(ngân hàng|thành viên)(?!\w)", flags=re.IGNORECASE)
    m2 = pat2.search(text)
    if m2:
        denom = int(m2.group(1))
        noun = m2.group(2)
        new_denom = 9 if denom == 10 else (denom - 1 if denom > 1 else 9)
        repl = f"{new_denom} {noun}"
        return text[:m2.start()] + repl + text[m2.end():]

    return None


def mutate_period(text: str, available_quarters: Sequence[str], rng: random.Random) -> str | None:
    """Change cited quarter to another quarter present in data."""
    # Match quý N/YYYY, quý N năm YYYY, qN/YYYY
    pat = re.compile(r"(?<!\w)(quý\s+([1-4])\s*(?:/|\s*năm\s*)(\d{4})|q([1-4])\s*/\s*(\d{4}))(?!\w)", flags=re.IGNORECASE)
    matches = list(pat.finditer(text))
    if not matches:
        return None

    m = rng.choice(matches)
    curr_text = m.group(1)

    # Format available quarters as Vietnamese strings: e.g. "2025_Q4" -> "quý 4/2025"
    vi_quarters = []
    for q in available_quarters:
        if "_" in q:
            parts = q.split("_")
            y_str = parts[0]
            q_num = parts[1].replace("Q", "").replace("q", "")
            vi_quarters.append(f"quý {q_num}/{y_str}")

    # Fallback quarters if none available or none different
    fallback_quarters = ["quý 1/2025", "quý 2/2025", "quý 3/2025", "quý 4/2025", "quý 1/2026", "quý 2/2026"]
    candidates = [q for q in vi_quarters if q.casefold() not in curr_text.casefold()]
    if not candidates:
        candidates = [q for q in fallback_quarters if q.casefold() not in curr_text.casefold()]

    new_q = rng.choice(candidates)
    return text[:m.start()] + new_q + text[m.end():]


def mutate_entity_swap(text: str, run_banks: Sequence[str], rng: random.Random) -> str | None:
    """Swap bank ticker with another bank present in run or catalog."""
    found_banks = [b for b in BANK_TICKERS if re.search(rf"(?<!\w){b}(?!\w)", text)]
    if not found_banks:
        return None

    target = rng.choice(found_banks)
    candidates = [b for b in run_banks if b != target and b in BANK_TICKERS]
    if not candidates:
        candidates = [b for b in BANK_TICKERS if b != target]

    replacement = rng.choice(candidates)
    # Replace only word-bounded occurrences of target bank
    repl_text = re.sub(rf"(?<!\w){target}(?!\w)", replacement, text, count=1)
    return repl_text if repl_text != text else None


def mutate_direction_flip(text: str, rng: random.Random) -> str | None:
    """Flip direction term to its opposite."""
    # Ordered pairs (longest phrases first)
    pairs = [
        ("cao hơn", "thấp hơn"),
        ("thấp hơn", "cao hơn"),
        ("dày hơn", "mỏng hơn"),
        ("mỏng hơn", "dày hơn"),
        ("tốt hơn", "kém hơn"),
        ("kém hơn", "tốt hơn"),
        ("trên trung vị", "dưới trung vị"),
        ("dưới trung vị", "trên trung vị"),
        ("tăng lên", "giảm xuống"),
        ("giảm xuống", "tăng lên"),
        ("đi lên", "đi xuống"),
        ("đi xuống", "đi lên"),
        ("tăng", "giảm"),
        ("giảm", "tăng"),
        ("cao nhất", "thấp nhất"),
        ("thấp nhất", "cao nhất"),
        ("tốt nhất", "kém nhất"),
        ("kém nhất", "tốt nhất"),
        ("dẫn đầu", "đứng cuối"),
        ("đứng đầu", "đứng cuối"),
        ("xếp cuối", "dẫn đầu"),
        ("cải thiện", "xấu đi"),
        ("xấu đi", "cải thiện"),
        ("thu hẹp", "nới rộng"),
        ("nới rộng", "thu hẹp"),
        ("nhóm đầu", "nhóm cuối"),
        ("nhóm cuối", "nhóm đầu"),
        ("cao", "thấp"),
        ("thấp", "cao"),
    ]

    for src, dst in pairs:
        pat = re.compile(rf"(?<!\w){re.escape(src)}(?!\w)", flags=re.IGNORECASE)
        m = pat.search(text)
        if m:
            orig_match = text[m.start():m.end()]
            # Preserve case of first character
            if orig_match[0].isupper():
                dst = dst[0].upper() + dst[1:]
            return text[:m.start()] + dst + text[m.end():]

    return None


def mutate_metric_swap(text: str, rng: random.Random) -> str | None:
    """Swap financial metric terms while keeping numbers unchanged."""
    pairs = [
        ("tỷ lệ bao phủ nợ xấu", "tỷ lệ nợ xấu"),
        ("tỷ lệ nợ xấu", "tỷ lệ bao phủ nợ xấu"),
        ("bao phủ nợ xấu", "nợ xấu"),
        ("ROA", "ROE"),
        ("ROE", "ROA"),
        ("NPL", "LLR"),
        ("LLR", "NPL"),
        ("NIM", "CASA"),
        ("CASA", "NIM"),
        ("CIR", "CAR"),
        ("CAR", "CIR"),
    ]

    for src, dst in pairs:
        pat = re.compile(rf"(?<!\w){re.escape(src)}(?!\w)", flags=re.IGNORECASE)
        m = pat.search(text)
        if m:
            orig_match = text[m.start():m.end()]
            if orig_match.isupper():
                dst = dst.upper()
            elif orig_match[0].isupper():
                dst = dst[0].upper() + dst[1:]
            return text[:m.start()] + dst + text[m.end():]

    return None


def mutate_unsupported_number(text: str, run_fact_values: Sequence[float], rng: random.Random) -> str | None:
    """Append a clause with an ungrounded number not matching any fact."""
    # Find a number not in run facts
    candidate_numbers = [14.87, 89.45, 33.72, 91.15, 6.78, 48.92]
    chosen = None
    for c in candidate_numbers:
        if not any(abs(c - fv) < 0.5 for fv in run_fact_values):
            chosen = c
            break
    if chosen is None:
        chosen = 93.77

    chosen_str = _format_vietnamese_number(chosen, 2)
    clause = f", trong khi biên lãi thuần đạt {chosen_str}%."
    t = text.rstrip(". ")
    return f"{t}{clause}"


def mutate_causal_claim(text: str, rng: random.Random) -> str | None:
    """Insert causal words (do/vì) into sentence."""
    variants = [
        ("do áp lực trích lập dự phòng rủi ro", ", do áp lực trích lập dự phòng rủi ro"),
        ("vì tăng trưởng tín dụng chậm lại", ", vì tăng trưởng tín dụng chậm lại"),
        ("do chi phí vốn gia tăng", ", do chi phí vốn gia tăng"),
    ]
    _, insertion = rng.choice(variants)

    # Insert after first comma if present, else prepend or insert before period
    if "," in text:
        parts = text.split(",", 1)
        return f"{parts[0]}{insertion},{parts[1]}"
    else:
        t = text.rstrip(". ")
        return f"{t}{insertion}."


def mutate_recommendation(text: str, rng: random.Random) -> str | None:
    """Append investment recommendation (nên mua/bán)."""
    options = [
        ", khuyến nghị nhà đầu tư nên mua tích lũy.",
        ", nên mua cổ phiếu ở vùng giá này.",
        ", khuyến nghị nhà đầu tư nên bán giảm tỷ trọng.",
    ]
    rec = rng.choice(options)
    t = text.rstrip(". ")
    return f"{t}{rec}"


def apply_mutation_operator(
    operator: str,
    text: str,
    run_quarters: Sequence[str],
    run_banks: Sequence[str],
    run_fact_values: Sequence[float],
    rng: random.Random,
) -> str | None:
    """Apply a specific mutation operator to a sentence.

    Returns the mutated sentence text, or None if the operator does not apply.
    """
    if operator == "number_small":
        return mutate_number_small(text, rng)
    elif operator == "number_large":
        return mutate_number_large(text, rng)
    elif operator == "digit_swap":
        return mutate_digit_swap(text, rng)
    elif operator == "rank":
        return mutate_rank(text, rng)
    elif operator == "denominator":
        return mutate_denominator(text, rng)
    elif operator == "period":
        return mutate_period(text, run_quarters, rng)
    elif operator == "entity_swap":
        return mutate_entity_swap(text, run_banks, rng)
    elif operator == "direction_flip":
        return mutate_direction_flip(text, rng)
    elif operator == "metric_swap":
        return mutate_metric_swap(text, rng)
    elif operator == "unsupported_number":
        return mutate_unsupported_number(text, run_fact_values, rng)
    elif operator == "causal_claim":
        return mutate_causal_claim(text, rng)
    elif operator == "recommendation":
        return mutate_recommendation(text, rng)
    else:
        raise ValueError(f"Unknown mutation operator: {operator}")


# ---------------------------------------------------------------------------
# Runner & evaluation pipeline
# ---------------------------------------------------------------------------

@dataclass
class MutantRecord:
    run_id: str
    task_id: str
    arm: str
    sentence_id: str
    operator: str
    original: str
    mutant: str
    caught: bool
    verdict: str  # "caught" or "escaped"
    reason_code: str | None
    reason: str | None


@dataclass
class OperatorStats:
    operator: str
    n: int
    caught: int
    rate: float
    ci_lower: float
    ci_upper: float
    wilson_95_ci: str


def run_mutation_evaluation(
    runs_dir: Path,
    seed: int = 42,
    output_dir: Path | None = None,
    disable_label_rules: bool = False,
) -> dict[str, Any]:
    """Execute the full mutation evaluation pipeline on ER-9 runs."""
    rng = random.Random(seed)
    run_files = sorted(runs_dir.glob("*.json"))
    if not run_files:
        raise FileNotFoundError(f"No ER-9 run json files found in {runs_dir}")

    logger.info("Found %d run files in %s", len(run_files), runs_dir)

    # 1. Controls check
    control_total = 0
    control_passed = 0
    control_failures: list[dict[str, Any]] = []

    # Collected data
    all_mutants: list[MutantRecord] = []
    sentence_verdicts: list[dict[str, Any]] = []
    arm_mutants: dict[str, list[MutantRecord]] = {
        "hierarchical_no_critique": [],
        "hierarchical_with_critique": [],
        "single_agent": [],
    }

    # Iterate through runs
    for rf in run_files:
        with open(rf, encoding="utf-8") as f:
            run_data = json.load(f)

        run_id = run_data.get("run_id", rf.stem)
        task_id = run_data.get("task_id", "")
        arm = run_data.get("arm", "unknown")
        resp = run_data.get("response") or {}
        facts_data = resp.get("facts") or []
        plan_data = resp.get("analysis_plan") or run_data.get("plan") or {}

        # Collect facts and build verification context
        ctx = build_verification_context_for_run(facts_data, plan_data)
        if disable_label_rules:
            from dataclasses import replace
            ctx = replace(ctx, enable_label_rules=False)
        accepted_sentences = extract_sentences_from_report_spec(resp.get("report_spec"))

        # Gather run-level contextual domains for operators
        run_fact_values = [float(f["value"]) for f in facts_data if f.get("value") is not None]
        run_quarters = sorted({
            f.get("period") for f in facts_data if f.get("period")
        } | {
            f.get("from_period") for f in facts_data if f.get("from_period")
        })
        run_banks = sorted(ctx.plan_entities | {
            f.get("entity_id") for f in facts_data if f.get("entity_id")
        })

        for s_dict in accepted_sentences:
            control_total += 1
            s_id = s_dict.get("sentence_id", "")
            orig_text = s_dict.get("text", "")
            f_ids = tuple(s_dict.get("fact_ids", ()))

            ns_orig = NarrativeSentence(
                sentence_id=s_id,
                author=s_dict.get("author", "orchestrator"),
                text=orig_text,
                fact_ids=f_ids,
                source=s_dict.get("source", "model"),
                revision=s_dict.get("revision", 0),
            )

            # Control verification
            ctrl_verdict = verify_sentence(ns_orig, ctx)
            if ctrl_verdict.ok:
                control_passed += 1
            else:
                control_failures.append({
                    "run_id": run_id,
                    "sentence_id": s_id,
                    "text": orig_text,
                    "reason_code": ctrl_verdict.reason_code,
                    "reason": ctrl_verdict.reason,
                })

            # Generate mutants for each operator
            for op in ALL_OPERATORS:
                mut_text = apply_mutation_operator(
                    operator=op,
                    text=orig_text,
                    run_quarters=run_quarters,
                    run_banks=run_banks,
                    run_fact_values=run_fact_values,
                    rng=rng,
                )
                if mut_text is None or mut_text == orig_text:
                    continue  # Operator does not apply to this sentence

                # Test mutant against verifier keeping original fact_ids
                ns_mut = NarrativeSentence(
                    sentence_id=f"{s_id}-mut-{op}",
                    author=ns_orig.author,
                    text=mut_text,
                    fact_ids=f_ids,
                    source="mutant",
                    revision=ns_orig.revision,
                )
                mut_verdict = verify_sentence(ns_mut, ctx)
                is_caught = not mut_verdict.ok
                rec = MutantRecord(
                    run_id=run_id,
                    task_id=task_id,
                    arm=arm,
                    sentence_id=s_id,
                    operator=op,
                    original=orig_text,
                    mutant=mut_text,
                    caught=is_caught,
                    verdict="caught" if is_caught else "escaped",
                    reason_code=mut_verdict.reason_code,
                    reason=mut_verdict.reason,
                )
                all_mutants.append(rec)
                if arm in arm_mutants:
                    arm_mutants[arm].append(rec)

        # Record sentence verdicts for baseline
        for s_dict in accepted_sentences:
            s_id = s_dict.get("sentence_id", "")
            orig_text = s_dict.get("text", "")
            sentence_verdicts.append({
                "run_id": run_id,
                "sentence_id": s_id,
                "text": orig_text,
                "is_dropped": False,
                "recorded_audit_reason": None,
                "verdict_ok": True,
                "reason_code": None,
            })

        # Also verify and record dropped sentences
        audit = resp.get("narrative_audit") or {}
        for d_sent in audit.get("sentences_dropped", []):
            d_id = d_sent.get("sentence_id", "")
            d_text = d_sent.get("text", "")
            d_fids = tuple(d_sent.get("fact_ids", ()))
            ns_drop = NarrativeSentence(
                sentence_id=d_id,
                author=d_sent.get("author", "orchestrator"),
                text=d_text,
                fact_ids=d_fids,
                source="dropped",
                revision=0,
            )
            v_drop = verify_sentence(ns_drop, ctx)
            sentence_verdicts.append({
                "run_id": run_id,
                "sentence_id": d_id,
                "text": d_text,
                "is_dropped": True,
                "recorded_audit_reason": d_sent.get("reason_code"),
                "verdict_ok": v_drop.ok,
                "reason_code": v_drop.reason_code,
            })

    logger.info("Controls: %d / %d passed (%.2f%%)", control_passed, control_total, (control_passed / control_total * 100) if control_total else 0)
    logger.info("Recorded %d total sentence verdicts (accepted + dropped)", len(sentence_verdicts))
    logger.info("Generated %d mutants across %d operators", len(all_mutants), len(ALL_OPERATORS))

    # Calculate overall stats per operator
    stats_by_op: dict[str, OperatorStats] = {}
    for op in ALL_OPERATORS:
        op_recs = [m for m in all_mutants if m.operator == op]
        n = len(op_recs)
        caught = sum(1 for m in op_recs if m.caught)
        rate = round(caught / n, 4) if n > 0 else 0.0
        ci_low, ci_high = wilson_ci(caught, n)
        stats_by_op[op] = OperatorStats(
            operator=op,
            n=n,
            caught=caught,
            rate=rate,
            ci_lower=ci_low,
            ci_upper=ci_high,
            wilson_95_ci=f"[{ci_low:.4f}, {ci_high:.4f}]",
        )

    # Calculate stats per arm
    arm_stats: dict[str, dict[str, OperatorStats]] = {}
    for arm_name, recs in arm_mutants.items():
        arm_stats[arm_name] = {}
        for op in ALL_OPERATORS:
            op_recs = [m for m in recs if m.operator == op]
            n = len(op_recs)
            caught = sum(1 for m in op_recs if m.caught)
            rate = round(caught / n, 4) if n > 0 else 0.0
            ci_low, ci_high = wilson_ci(caught, n)
            arm_stats[arm_name][op] = OperatorStats(
                operator=op,
                n=n,
                caught=caught,
                rate=rate,
                ci_lower=ci_low,
                ci_upper=ci_high,
                wilson_95_ci=f"[{ci_low:.4f}, {ci_high:.4f}]",
            )

    results_payload = {
        "controls": {
            "total": control_total,
            "passed": control_passed,
            "rate": round(control_passed / control_total, 4) if control_total else 0.0,
            "failures": control_failures,
        },
        "operators": {op: asdict(st) for op, st in stats_by_op.items()},
        "arms": {
            arm: {op: asdict(st) for op, st in arm_stats[arm].items()}
            for arm in arm_stats
        },
        "total_mutants": len(all_mutants),
        "total_caught": sum(1 for m in all_mutants if m.caught),
        "sentence_verdicts": sentence_verdicts,
    }

    if output_dir:
        output_dir.mkdir(parents=True, exist_ok=True)
        write_evaluation_artifacts(output_dir, all_mutants, results_payload)

    return results_payload


def write_evaluation_artifacts(
    out_dir: Path,
    all_mutants: Sequence[MutantRecord],
    results: dict[str, Any],
) -> None:
    """Save mutants.jsonl, results.csv, RESULTS.md, and baseline.json."""
    # 1. mutants.jsonl
    jsonl_path = out_dir / "mutants.jsonl"
    with open(jsonl_path, "w", encoding="utf-8") as f:
        for m in all_mutants:
            f.write(json.dumps(asdict(m), ensure_ascii=False) + "\n")
    logger.info("Saved %s", jsonl_path)

    # 2. results.csv
    csv_path = out_dir / "results.csv"
    with open(csv_path, "w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["operator", "n", "caught", "rate", "ci_lower", "ci_upper", "wilson_95_ci"])
        for op in ALL_OPERATORS:
            st = results["operators"][op]
            writer.writerow([
                st["operator"],
                st["n"],
                st["caught"],
                st["rate"],
                st["ci_lower"],
                st["ci_upper"],
                st["wilson_95_ci"],
            ])
    logger.info("Saved %s", csv_path)

    # 3. baseline.json for regression gating
    baseline_path = out_dir / "baseline.json"
    baseline_data = {
        "seed": 42,
        "controls": {
            "total": results["controls"]["total"],
            "passed": results["controls"]["passed"],
        },
        "operator_catch_rates": {
            op: results["operators"][op]["rate"] for op in ALL_OPERATORS
        },
        "operator_counts": {
            op: {
                "n": results["operators"][op]["n"],
                "caught": results["operators"][op]["caught"],
                "rate": results["operators"][op]["rate"],
            }
            for op in ALL_OPERATORS
        },
        "sentence_verdicts": results.get("sentence_verdicts", []),
    }
    with open(baseline_path, "w", encoding="utf-8") as f:
        json.dump(baseline_data, f, indent=2, ensure_ascii=False)
    logger.info("Saved %s", baseline_path)

    # 4. RESULTS.md
    md_path = out_dir / "RESULTS.md"
    content = _generate_markdown_report(all_mutants, results)
    with open(md_path, "w", encoding="utf-8") as f:
        f.write(content)
    logger.info("Saved %s", md_path)


def _generate_markdown_report(
    all_mutants: Sequence[MutantRecord],
    results: dict[str, Any],
) -> str:
    """Generate detailed markdown report with escaped examples and arm breakdowns."""
    ctrl = results["controls"]
    ops = results["operators"]
    arms = results["arms"]

    lines = [
        "# Verifier Mutation Testing Evaluation Report (mut1)",
        "",
        "## 1. Control Verification",
        "",
        f"- **Total accepted sentences evaluated:** {ctrl['total']}",
        f"- **Passed unchanged:** {ctrl['passed']} ({ctrl['rate'] * 100:.1f}%)",
        f"- **Failed controls:** {len(ctrl['failures'])}",
        "",
    ]

    if ctrl["failures"]:
        lines.append("### Control Failures")
        for f in ctrl["failures"]:
            lines.append(f"- `[{f['run_id']}]` {f['sentence_id']}: {f['text']} (Reason: `{f['reason_code']}` - {f['reason']})")
        lines.append("")

    lines.extend([
        "## 2. Overall Mutation Catch Rates",
        "",
        "| Operator | n | Caught | Catch Rate | Wilson 95% CI |",
        "| :--- | :---: | :---: | :---: | :---: |",
    ])

    for op in ALL_OPERATORS:
        st = ops[op]
        pct = st["rate"] * 100.0
        lines.append(f"| `{op}` | {st['n']} | {st['caught']} | {pct:.1f}% ({st['rate']:.4f}) | {st['wilson_95_ci']} |")

    lines.extend([
        "",
        "## 3. Catch Rates by Evaluation Arm",
        "",
        "| Operator | Arm A (`single_agent`) | Arm B (`hierarchical_no_critique`) | Arm C (`hierarchical_with_critique`) |",
        "| :--- | :---: | :---: | :---: |",
    ])

    for op in ALL_OPERATORS:
        a_st = arms.get("single_agent", {}).get(op, {"caught": 0, "n": 0, "rate": 0.0})
        b_st = arms.get("hierarchical_no_critique", {}).get(op, {"caught": 0, "n": 0, "rate": 0.0})
        c_st = arms.get("hierarchical_with_critique", {}).get(op, {"caught": 0, "n": 0, "rate": 0.0})
        lines.append(
            f"| `{op}` | {a_st['caught']}/{a_st['n']} ({a_st['rate']*100:.1f}%) | "
            f"{b_st['caught']}/{b_st['n']} ({b_st['rate']*100:.1f}%) | "
            f"{c_st['caught']}/{c_st['n']} ({c_st['rate']*100:.1f}%) |"
        )

    lines.extend([
        "",
        "## 4. Escaped Mutants Analysis",
        "",
        "Examples of mutants that escaped verification (verifier returned `ok=True`), per operator:",
        "",
    ])

    for op in ALL_OPERATORS:
        escaped = [m for m in all_mutants if m.operator == op and not m.caught]
        if not escaped:
            lines.append(f"### `{op}`: 0 escapes (100% caught)")
            lines.append("")
            continue

        lines.append(f"### `{op}`: {len(escaped)} escapes (Catch rate: {ops[op]['rate']*100:.1f}%)")
        lines.append("")
        sample = escaped[:3]
        for idx, m in enumerate(sample, 1):
            lines.append(f"**Example {idx}:** (`{m.run_id}` / `{m.sentence_id}`)")
            lines.append(f"- **Original:** {m.original}")
            lines.append(f"- **Mutant:** {m.mutant}")
            lines.append("")

    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description="Run verifier mutation suite.")
    parser.add_argument(
        "--runs-dir",
        type=Path,
        default=ROOT / "experiments" / "er9" / "runs",
        help="Path to ER-9 runs directory",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=ROOT / "experiments" / "mut1",
        help="Path to output directory",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=42,
        help="Random seed for deterministic mutant generation",
    )
    parser.add_argument(
        "--disable-label-rules",
        action="store_true",
        default=False,
        help="Disable the two new verifier label rules (legacy before-mode)",
    )
    args = parser.parse_args()

    results = run_mutation_evaluation(
        runs_dir=args.runs_dir,
        seed=args.seed,
        output_dir=args.output_dir,
        disable_label_rules=args.disable_label_rules,
    )
    print("\n=== VERIFIER MUTATION EVALUATION SUMMARY ===")
    print(f"Controls: {results['controls']['passed']} / {results['controls']['total']} passed")
    print(f"Total Mutants: {results['total_mutants']}, Caught: {results['total_caught']}")
    for op, st in results["operators"].items():
        print(f"  {op:20s}: {st['caught']:3d} / {st['n']:3d} caught ({st['rate']*100:5.1f}%) Wilson 95% CI: {st['wilson_95_ci']}")


if __name__ == "__main__":
    main()
