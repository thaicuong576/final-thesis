"""Application-level metric presentation metadata, synonyms, and derived formulas."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal


@dataclass(frozen=True)
class MetricPresentation:
    metric_id: str
    label: str
    short_label: str
    unit: str
    direction: Literal["higher_is_better", "lower_is_better", "neutral"]
    decimals: int
    delta_decimals: int
    flat_threshold_pp: float
    group: str
    group_label: str
    synonyms: tuple[str, ...]
    superlative_hi: tuple[str, ...]
    superlative_lo: tuple[str, ...]


@dataclass(frozen=True)
class DerivedFormula:
    numerator: str
    denominator: str
    label: str
    unit: str
    decimals: int
    formula_version: str


METRIC_PRESENTATIONS: dict[str, MetricPresentation] = {
    "bank.npl_g35": MetricPresentation(
        metric_id="bank.npl_g35",
        label="Tỷ lệ nợ xấu (nhóm 3–5)",
        short_label="Nợ xấu",
        unit="%",
        direction="lower_is_better",
        decimals=2,
        delta_decimals=2,
        flat_threshold_pp=0.05,
        group="asset_quality",
        group_label="Chất lượng nợ",
        synonyms=("nợ xấu", "tỷ lệ nợ xấu", "npl", "npl_g35", "non-performing loan", "non-performing loans"),
        superlative_hi=("cao",),
        superlative_lo=("thấp",),
    ),
    "bank.llr_coverage": MetricPresentation(
        metric_id="bank.llr_coverage",
        label="Tỷ lệ bao phủ nợ xấu",
        short_label="Bao phủ",
        unit="%",
        direction="higher_is_better",
        decimals=1,
        delta_decimals=1,
        flat_threshold_pp=1.0,
        group="provisioning",
        group_label="Đệm dự phòng",
        synonyms=(
            "bao phủ nợ xấu",
            "tỷ lệ bao phủ",
            "bao phủ",
            "dự phòng",
            "đệm dự phòng",
            "llr",
            "coverage",
            "loan loss reserve",
            "loan loss coverage",
        ),
        superlative_hi=("dày", "cao"),
        superlative_lo=("mỏng", "thấp"),
    ),
    "bank.roa": MetricPresentation(
        metric_id="bank.roa",
        label="ROA",
        short_label="ROA",
        unit="%",
        direction="higher_is_better",
        decimals=2,
        delta_decimals=2,
        flat_threshold_pp=0.05,
        group="profitability",
        group_label="Sinh lời",
        synonyms=("roa", "sinh lời trên tài sản", "return on assets"),
        superlative_hi=("cao",),
        superlative_lo=("thấp",),
    ),
    "bank.roe": MetricPresentation(
        metric_id="bank.roe",
        label="ROE",
        short_label="ROE",
        unit="%",
        direction="higher_is_better",
        decimals=1,
        delta_decimals=1,
        flat_threshold_pp=0.5,
        group="profitability",
        group_label="Sinh lời",
        synonyms=("roe", "sinh lời trên vốn", "return on equity"),
        superlative_hi=("cao",),
        superlative_lo=("thấp",),
    ),
    # Additional banking metrics (available in registry, may not be in catalog yet)
    "bank.nim": MetricPresentation(
        metric_id="bank.nim",
        label="NIM",
        short_label="NIM",
        unit="%",
        direction="higher_is_better",
        decimals=2,
        delta_decimals=2,
        flat_threshold_pp=0.05,
        group="profitability",
        group_label="Sinh lời",
        synonyms=("nim", "biên lãi ròng", "biên lãi thuần"),
        superlative_hi=("cao",),
        superlative_lo=("thấp",),
    ),
    "bank.casa": MetricPresentation(
        metric_id="bank.casa",
        label="Tỷ lệ CASA",
        short_label="CASA",
        unit="%",
        direction="higher_is_better",
        decimals=1,
        delta_decimals=1,
        flat_threshold_pp=0.5,
        group="liquidity",
        group_label="Thanh khoản & Tiền gửi",
        synonyms=("casa", "tiền gửi không kỳ hạn", "tỷ lệ tiền gửi không kỳ hạn"),
        superlative_hi=("cao",),
        superlative_lo=("thấp",),
    ),
    "bank.car": MetricPresentation(
        metric_id="bank.car",
        label="Hệ số an toàn vốn (CAR)",
        short_label="CAR",
        unit="%",
        direction="higher_is_better",
        decimals=1,
        delta_decimals=1,
        flat_threshold_pp=0.5,
        group="capital",
        group_label="An toàn vốn",
        synonyms=("car", "hệ số an toàn vốn", "tỷ lệ an toàn vốn"),
        superlative_hi=("cao",),
        superlative_lo=("thấp",),
    ),
    "bank.cir": MetricPresentation(
        metric_id="bank.cir",
        label="Tỷ lệ chi phí trên thu nhập (CIR)",
        short_label="CIR",
        unit="%",
        direction="lower_is_better",
        decimals=1,
        delta_decimals=1,
        flat_threshold_pp=0.5,
        group="efficiency",
        group_label="Hiệu quả hoạt động",
        synonyms=("cir", "chi phí trên thu nhập", "tỷ lệ cir"),
        superlative_hi=("cao",),
        superlative_lo=("thấp",),
    ),
    "bank.ldr": MetricPresentation(
        metric_id="bank.ldr",
        label="Tỷ lệ cho vay trên huy động (LDR)",
        short_label="LDR",
        unit="%",
        direction="neutral",
        decimals=1,
        delta_decimals=1,
        flat_threshold_pp=0.5,
        group="liquidity",
        group_label="Thanh khoản & Tiền gửi",
        synonyms=("ldr", "cho vay trên huy động", "tỷ lệ cho vay trên huy động"),
        superlative_hi=("cao",),
        superlative_lo=("thấp",),
    ),
    "derived.roe_over_roa": MetricPresentation(
        metric_id="derived.roe_over_roa",
        label="ROE/ROA",
        short_label="ROE/ROA",
        unit="lần",
        direction="neutral",
        decimals=2,
        delta_decimals=2,
        flat_threshold_pp=0.5,
        group="profitability",
        group_label="Sinh lời & Đòn bẩy",
        synonyms=("roe/roa", "đòn bẩy vốn", "roe trên roa"),
        superlative_hi=("cao",),
        superlative_lo=("thấp",),
    ),
}

TOPIC_GROUPS: dict[str, tuple[str, ...]] = {
    # asset_quality + provisioning
    "chất lượng tài sản": ("asset_quality", "provisioning"),
    "chất lượng tín dụng": ("asset_quality", "provisioning"),
    "rủi ro tín dụng": ("asset_quality", "provisioning"),
    "chất lượng nợ": ("asset_quality", "provisioning"),
    # profitability
    "sinh lời": ("profitability",),
    "hiệu quả": ("profitability",),
    "lợi nhuận": ("profitability",),
    # comprehensive
    "sức khỏe tài chính": ("all",),
    "tổng quan": ("all",),
    "toàn diện": ("all",),
}

DERIVED: dict[str, DerivedFormula] = {
    "derived.roe_over_roa": DerivedFormula(
        numerator="bank.roe",
        denominator="bank.roa",
        label="ROE/ROA (đòn bẩy ngầm định)",
        unit="x",
        decimals=1,
        formula_version="roe-over-roa-v1",
    )
}

DEFAULT_SCATTER_PAIRS: list[tuple[str, str]] = [
    ("bank.npl_g35", "bank.llr_coverage"),
    ("bank.roe", "bank.npl_g35"),
]


_ALIASES: dict[str, str] = {
    "bank.llr": "bank.llr_coverage",
    "bank.npl": "bank.npl_g35",
}


def get_metric_presentation(metric_id: str, display_name: str | None = None) -> MetricPresentation:
    """Lookup presentation settings for a metric, falling back to neutral defaults."""
    lookup_id = _ALIASES.get(metric_id, metric_id)
    if lookup_id in METRIC_PRESENTATIONS:
        orig = METRIC_PRESENTATIONS[lookup_id]
        if orig.metric_id != metric_id:
            from dataclasses import replace

            return replace(orig, metric_id=metric_id)
        return orig
    if display_name:
        label = display_name
    elif metric_id.startswith("bank.") or metric_id.startswith("derived."):
        label = metric_id.split(".", 1)[-1].replace("_", " ")
    else:
        label = metric_id
    return MetricPresentation(
        metric_id=metric_id,
        label=label,
        short_label=label,
        unit="",
        direction="neutral",
        decimals=2,
        delta_decimals=2,
        flat_threshold_pp=0.05,
        group="other",
        group_label="Chỉ tiêu khác",
        synonyms=(),
        superlative_hi=("cao",),
        superlative_lo=("thấp",),
    )


def format_metric_display_name(metric_id: str, lowercase: bool = False) -> str:
    """Return natural Vietnamese name for metric, respecting acronyms (ROE, ROA, NIM)."""
    pres = get_metric_presentation(metric_id)
    if metric_id == "bank.llr_coverage":
        return "tỷ lệ bao phủ nợ xấu" if lowercase else "Tỷ lệ bao phủ nợ xấu"
    if metric_id == "bank.npl_g35":
        return "tỷ lệ nợ xấu" if lowercase else "Tỷ lệ nợ xấu"
    if metric_id in ("bank.roe", "bank.roa", "bank.nim", "bank.casa", "bank.car", "bank.cir", "bank.ldr", "derived.roe_over_roa"):
        return pres.short_label
    clean = pres.short_label
    if clean.startswith("bank.") or clean.startswith("derived."):
        clean = clean.split(".", 1)[-1].replace("_", " ")
    return clean.lower() if lowercase else clean
