"""Claim-driven user-facing analysis reports.

The existing ``ReportView`` is a useful transport view, but it is not a
decision-ready report.  This module turns the authoritative matrix into a
small set of explicit claims.  Every claim carries the data cells it uses,
the available evidence IDs, an interpretation, and a limitation.

The deterministic claim builder is intentionally conservative.  It does not
invent causes or investment recommendations.  A future model-generated claim
can use the same shape and be evaluated against this report contract.
"""

from __future__ import annotations

from collections import defaultdict
from typing import Any, Iterable

from .report_view import format_value, metric_label


REPORT_CONTRACT_VERSION = "analysis-report-v2"
METRIC_ORDER = (
    "bank.npl_g35",
    "bank.llr_coverage",
    "bank.roa",
    "bank.roe",
)


def _period_key(period: str) -> tuple[int, int, str]:
    try:
        year, quarter = period.split("_Q")
        return int(year), int(quarter), period
    except ValueError:
        return 9999, 9, period


def _rows(view: dict[str, Any]) -> dict[tuple[str, str, str], dict[str, Any]]:
    return {
        (row["ticker"], row["period"], metric["metric_id"]): metric
        for row in view["matrix"]
        for metric in row["metrics"]
    }


def _metric_ref(
    index: dict[tuple[str, str, str], dict[str, Any]],
    ticker: str,
    period: str,
    metric_id: str,
) -> dict[str, Any]:
    item = index.get((ticker, period, metric_id))
    if item is None:
        return {
            "ticker": ticker,
            "period": period,
            "metric_id": metric_id,
            "value": None,
            "display_value": "—",
            "status": "missing",
            "observation_id": None,
            "source_id": None,
            "source_locator": None,
            "evidence_ids": [],
        }
    return {
        "ticker": ticker,
        "period": period,
        "metric_id": metric_id,
        "value": item.get("value"),
        "display_value": item.get("display_value") or format_value(item.get("value"), item.get("unit")),
        "status": item.get("status"),
        "observation_id": item.get("observation_id"),
        "source_id": item.get("source_id"),
        "source_locator": item.get("source_locator"),
        "evidence_ids": list(item.get("evidence_ids") or []),
    }


def _support(refs: Iterable[dict[str, Any]]) -> tuple[str, list[str], list[str]]:
    refs = list(refs)
    evidence_ids = list(dict.fromkeys(evidence_id for ref in refs for evidence_id in ref["evidence_ids"]))
    source_ids = list(dict.fromkeys(ref["source_id"] for ref in refs if ref.get("source_id")))
    valid = all(ref.get("status") == "valid" and ref.get("value") is not None for ref in refs)
    if not valid:
        return "partially_supported", evidence_ids, source_ids
    if all(ref["evidence_ids"] for ref in refs):
        return "evidence_backed", evidence_ids, source_ids
    if all(ref.get("source_id") and ref.get("source_locator") for ref in refs):
        return "source_locator_only", evidence_ids, source_ids
    return "partially_supported", evidence_ids, source_ids


def _claim(
    claim_id: str,
    title: str,
    claim_text: str,
    interpretation: str,
    limitation: str,
    refs: list[dict[str, Any]],
    claim_type: str,
    priority: str = "normal",
    origin: str = "deterministic_reference",
) -> dict[str, Any]:
    support, evidence_ids, source_ids = _support(refs)
    return {
        "claim_id": claim_id,
        "claim_type": claim_type,
        "priority": priority,
        "origin": origin,
        "title": title,
        "claim": claim_text,
        "interpretation": interpretation,
        "limitation": limitation,
        "support": support,
        "data_refs": refs,
        "evidence_ids": evidence_ids,
        "source_ids": source_ids,
    }


def _normalize_model_claims(
    raw_claims: list[dict[str, Any]],
    index: dict[tuple[str, str, str], dict[str, Any]],
) -> list[dict[str, Any]]:
    """Normalize typed provider claims against the Gold-backed matrix."""

    normalized: list[dict[str, Any]] = []
    seen: set[str] = set()
    for raw in raw_claims:
        if not isinstance(raw, dict):
            raise ValueError("model_claim_not_object")
        required = ("claim_id", "claim_type", "title", "claim", "interpretation", "limitation", "data_refs")
        if any(not isinstance(raw.get(key), str) or not raw[key].strip() for key in required[:-1]):
            raise ValueError("model_claim_text_missing")
        claim_id = raw["claim_id"]
        if claim_id in seen:
            raise ValueError("model_claim_id_duplicate")
        seen.add(claim_id)
        raw_refs = raw.get("data_refs")
        if not isinstance(raw_refs, list) or not raw_refs:
            raise ValueError("model_claim_data_refs_missing")
        refs: list[dict[str, Any]] = []
        for data_ref in raw_refs:
            if not isinstance(data_ref, str):
                raise ValueError("model_claim_data_ref_invalid")
            parts = data_ref.split("|", 2)
            if len(parts) != 3 or (parts[0], parts[1], parts[2]) not in index:
                raise ValueError("model_claim_data_ref_outside_scope")
            refs.append(_metric_ref(index, parts[0], parts[1], parts[2]))
        normalized.append(
            _claim(
                claim_id=claim_id,
                title=raw["title"],
                claim_text=raw["claim"],
                interpretation=raw["interpretation"],
                limitation=raw["limitation"],
                refs=refs,
                claim_type=raw["claim_type"],
                priority=str(raw.get("priority") or "normal"),
                origin="model",
            )
        )
    return normalized


def _value(index: dict[tuple[str, str, str], dict[str, Any]], ticker: str, period: str, metric_id: str) -> float | None:
    item = index.get((ticker, period, metric_id))
    if item is None or item.get("status") != "valid":
        return None
    value = item.get("value")
    return float(value) if isinstance(value, (int, float)) else None


def _fmt(value: float | None) -> str:
    return "—" if value is None else f"{value:.4f}%"


def _fmt_delta(value: float | None) -> str:
    return "—" if value is None else f"{value:+.4f} điểm %"


def _delta(index: dict[tuple[str, str, str], dict[str, Any]], ticker: str, first: str, last: str, metric_id: str) -> float | None:
    start = _value(index, ticker, first, metric_id)
    end = _value(index, ticker, last, metric_id)
    return None if start is None or end is None else end - start


def _direction(delta: float | None) -> str:
    if delta is None:
        return "not_available"
    if abs(delta) < 0.00005:
        return "stable"
    return "up" if delta > 0 else "down"


def _rankings(
    index: dict[tuple[str, str, str], dict[str, Any]],
    issuers: list[str],
    period: str,
    metric_id: str,
    ascending: bool,
) -> list[dict[str, Any]]:
    values = [
        (ticker, _value(index, ticker, period, metric_id))
        for ticker in issuers
    ]
    values = [(ticker, value) for ticker, value in values if value is not None]
    values.sort(key=lambda pair: pair[1], reverse=not ascending)
    return [
        {"rank": rank, "ticker": ticker, "value": value, "display_value": _fmt(value)}
        for rank, (ticker, value) in enumerate(values, start=1)
    ]


def _first_last_valid_periods(view: dict[str, Any]) -> tuple[str, str]:
    periods = sorted(view["scope"]["periods"], key=_period_key)
    return periods[0], periods[-1]


def build_analysis_report(view: dict[str, Any]) -> dict[str, Any]:
    """Build a claim-driven report from a previously built ``ReportView``."""

    issuers = list(view["scope"]["issuers"])
    periods = sorted(view["scope"]["periods"], key=_period_key)
    metrics = [item["metric_id"] for item in view["scope"]["metrics"]]
    index = _rows(view)
    first_period, last_period = _first_last_valid_periods(view)

    claims: list[dict[str, Any]] = []
    q4_npl = _rankings(index, issuers, last_period, "bank.npl_g35", ascending=True)
    q4_coverage = _rankings(index, issuers, last_period, "bank.llr_coverage", ascending=False)
    q4_roa = _rankings(index, issuers, last_period, "bank.roa", ascending=False)
    q4_roe = _rankings(index, issuers, last_period, "bank.roe", ascending=False)
    risk_ticker = q4_npl[-1]["ticker"] if q4_npl else None
    protection_ticker = q4_npl[0]["ticker"] if q4_npl else None

    if q4_npl and q4_coverage:
        risk_ticker = q4_npl[-1]["ticker"]
        lowest_coverage = q4_coverage[-1]["ticker"]
        if risk_ticker == lowest_coverage:
            refs = [
                _metric_ref(index, risk_ticker, last_period, "bank.npl_g35"),
                _metric_ref(index, risk_ticker, last_period, "bank.llr_coverage"),
            ]
            claims.append(
                _claim(
                    "q4-credit-risk-outlier",
                    "Outlier rủi ro tín dụng",
                    f"Ở {last_period}, {risk_ticker} có NPL cao nhất ({_fmt(_value(index, risk_ticker, last_period, 'bank.npl_g35'))}) và Coverage thấp nhất ({_fmt(_value(index, risk_ticker, last_period, 'bank.llr_coverage'))}) trong nhóm.",
                    "Đây là ngân hàng cần được ưu tiên theo dõi về chất lượng tài sản và mức đệm dự phòng trong snapshot Q4.",
                    "Đây là so sánh ngang tại một kỳ, không chứng minh nguyên nhân hay dự báo vỡ nợ.",
                    refs,
                    "cross_sectional_risk",
                    "high",
                )
            )

    if q4_roa and q4_roe:
        roa_ticker = q4_roa[0]["ticker"]
        roe_ticker = q4_roe[0]["ticker"]
        refs = [
            _metric_ref(index, roa_ticker, last_period, "bank.roa"),
            _metric_ref(index, roe_ticker, last_period, "bank.roe"),
        ]
        if roa_ticker == roe_ticker:
            claim_text = f"Ở {last_period}, {roa_ticker} có ROA cao nhất ({_fmt(_value(index, roa_ticker, last_period, 'bank.roa'))}) và ROE cao nhất ({_fmt(_value(index, roe_ticker, last_period, 'bank.roe'))}) trong nhóm."
            interpretation = f"{roa_ticker} là điểm nổi bật về hiệu quả sinh lời trong snapshot Q4, nhưng vị trí này cần đọc cùng với rủi ro tín dụng và Coverage."
        else:
            claim_text = f"Ở {last_period}, {roa_ticker} dẫn đầu ROA ({_fmt(_value(index, roa_ticker, last_period, 'bank.roa'))}), còn {roe_ticker} dẫn đầu ROE ({_fmt(_value(index, roe_ticker, last_period, 'bank.roe'))}); không có một ngân hàng dẫn đầu cả hai chỉ số."
            interpretation = "Hiệu quả sinh lời có hai góc nhìn khác nhau: ROA phản ánh hiệu quả trên tài sản, còn ROE phản ánh hiệu quả trên vốn chủ sở hữu; không nên gộp thành một thứ hạng duy nhất."
        claims.append(
            _claim(
                "q4-profitability-profile",
                "Hồ sơ sinh lời",
                claim_text,
                interpretation,
                "ROA/ROE không đủ để kết luận ngân hàng tốt nhất toàn diện hoặc giải thích động lực tạo lợi nhuận.",
                refs,
                "cross_sectional_profitability",
                "high",
            )
        )

    if q4_npl and q4_coverage and q4_npl[0]["ticker"] == q4_coverage[0]["ticker"]:
        protection_ticker = q4_npl[0]["ticker"]
        refs = [
            _metric_ref(index, protection_ticker, last_period, "bank.npl_g35"),
            _metric_ref(index, protection_ticker, last_period, "bank.llr_coverage"),
        ]
        claims.append(
            _claim(
                "q4-credit-protection-leader",
                "Đệm tín dụng tốt nhất",
                f"Ở {last_period}, {protection_ticker} có NPL thấp nhất ({_fmt(_value(index, protection_ticker, last_period, 'bank.npl_g35'))}) và Coverage cao nhất ({_fmt(_value(index, protection_ticker, last_period, 'bank.llr_coverage'))}) trong nhóm.",
                f"{protection_ticker} đang có hồ sơ chất lượng tín dụng và mức bao phủ dự phòng nổi bật nhất trong so sánh Q4.",
                "Đây là tín hiệu về snapshot chất lượng tín dụng, không phải kết luận về toàn bộ sức khỏe ngân hàng.",
                refs,
                "cross_sectional_credit_protection",
                "high",
            )
        )

    # Trend claims are emitted only when all four metrics are available for both endpoints.
    trend_specs = (
        ("bank.npl_g35", "NPL"),
        ("bank.llr_coverage", "Coverage"),
        ("bank.roa", "ROA"),
        ("bank.roe", "ROE"),
    )
    for ticker in issuers:
        start_values = [_value(index, ticker, first_period, metric_id) for metric_id, _ in trend_specs]
        end_values = [_value(index, ticker, last_period, metric_id) for metric_id, _ in trend_specs]
        if not all(value is not None for value in (*start_values, *end_values)):
            continue
        deltas = [end - start for start, end in zip(start_values, end_values)]
        refs = [
            _metric_ref(index, ticker, first_period, metric_id)
            for metric_id, _ in trend_specs
        ] + [
            _metric_ref(index, ticker, last_period, metric_id)
            for metric_id, _ in trend_specs
        ]
        claims.append(
            _claim(
                f"{ticker.lower()}-trend-{first_period}-{last_period}",
                f"Xu hướng {ticker}",
                f"Từ {first_period} đến {last_period}, {ticker} thay đổi NPL {_fmt_delta(deltas[0])}, Coverage {_fmt_delta(deltas[1])}, ROA {_fmt_delta(deltas[2])} và ROE {_fmt_delta(deltas[3])}.",
                f"Mức thay đổi cho thấy hướng đi của {ticker} trong giai đoạn, nhưng không tách được nguyên nhân từ bốn chỉ số này riêng lẻ.",
                "Xu hướng không được tính nếu một đầu kỳ hoặc cuối kỳ thiếu dữ liệu hợp lệ; không suy diễn các quý ở giữa.",
                refs,
                "issuer_trend",
                "high" if ticker == risk_ticker else "normal",
            )
        )

    deterministic_claims = claims
    model_claims = view["analysis"].get("model_claims") or []
    if model_claims:
        claims = _normalize_model_claims(model_claims, index)
        claim_origin = "model"
    else:
        claims = deterministic_claims
        claim_origin = "deterministic_reference"

    profiles: list[dict[str, Any]] = []
    for ticker in issuers:
        q4 = {
            metric_id: _metric_ref(index, ticker, last_period, metric_id)
            for metric_id in metrics
        }
        trend = {
            metric_id: {
                "from": _value(index, ticker, first_period, metric_id),
                "to": _value(index, ticker, last_period, metric_id),
                "delta": _delta(index, ticker, first_period, last_period, metric_id),
                "direction": _direction(_delta(index, ticker, first_period, last_period, metric_id)),
            }
            for metric_id in metrics
        }
        profile_claims = [
            claim for claim in claims
            if any(ref.get("ticker") == ticker for ref in claim["data_refs"])
        ]
        watch_points: list[str] = []
        if q4["bank.npl_g35"]["status"] == "valid" and q4["bank.llr_coverage"]["status"] == "valid":
            if q4_npl and q4_npl[-1]["ticker"] == ticker and q4_coverage and q4_coverage[-1]["ticker"] == ticker:
                watch_points.append("NPL cao nhất và Coverage thấp nhất trong nhóm ở kỳ cuối")
            if q4_npl and q4_npl[0]["ticker"] == ticker and q4_coverage and q4_coverage[0]["ticker"] == ticker:
                watch_points.append("NPL thấp nhất và Coverage cao nhất trong nhóm ở kỳ cuối")
        if any(item["status"] != "valid" for item in q4.values()):
            watch_points.append("Kỳ cuối chưa đủ dữ liệu hợp lệ cho toàn bộ chỉ số.")
        if any(item["direction"] == "not_available" for item in trend.values()):
            watch_points.append("Thiếu kỳ đầu hoặc kỳ cuối nên chưa thể kết luận xu hướng đầy đủ")
        if any(item["status"] != "valid" for item in q4.values()):
            watch_points.append("Không nên xếp hạng hoặc kết luận xu hướng từ ô thiếu/unaccepted")
        assessment_parts: list[str] = []
        if ticker == risk_ticker:
            assessment_parts.append("Q4 là outlier rủi ro tín dụng trong nhóm")
        if ticker == protection_ticker:
            assessment_parts.append("Q4 có hồ sơ NPL/Coverage nổi bật nhất về chất lượng tín dụng")
        if q4_roa and q4_roa[0]["ticker"] == ticker:
            assessment_parts.append("dẫn đầu ROA")
        if q4_roe and q4_roe[0]["ticker"] == ticker:
            assessment_parts.append("dẫn đầu ROE")
        npl_delta = trend.get("bank.npl_g35", {}).get("delta")
        coverage_delta = trend.get("bank.llr_coverage", {}).get("delta")
        roa_delta = trend.get("bank.roa", {}).get("delta")
        roe_delta = trend.get("bank.roe", {}).get("delta")
        if npl_delta is not None and coverage_delta is not None:
            if npl_delta < 0 and coverage_delta > 0:
                assessment_parts.append("NPL giảm và Coverage tăng từ kỳ đầu đến kỳ cuối")
            elif npl_delta > 0 and coverage_delta < 0:
                assessment_parts.append("NPL tăng và Coverage giảm từ kỳ đầu đến kỳ cuối")
        if roa_delta is not None and roe_delta is not None and roa_delta < 0 and roe_delta < 0:
            assessment_parts.append("ROA và ROE cùng giảm ở hai đầu kỳ")
        assessment = "; ".join(assessment_parts) + "." if assessment_parts else "Chưa có kết luận nổi bật trong scope này."
        profiles.append(
            {
                "ticker": ticker,
                "period": last_period,
                "metrics": q4,
                "trend": trend,
                "assessment": assessment,
                "claim_ids": [claim["claim_id"] for claim in profile_claims],
                "watch_points": watch_points,
            }
        )

    ranking_specs = (
        ("bank.npl_g35", True),
        ("bank.llr_coverage", False),
        ("bank.roa", False),
        ("bank.roe", False),
    )
    comparisons = [
        {
            "period": last_period,
            "metric_id": metric_id,
            "label": metric_label(metric_id),
            "direction": "lower_is_better" if ascending else "higher_is_better",
            "ranking": _rankings(index, issuers, last_period, metric_id, ascending),
        }
        for metric_id, ascending in ranking_specs
    ]

    missing_limitations = [
        f"{item['ticker']} / {item['period']} / {item['metric']}: {item['reason']}"
        for item in view.get("missing_cells", [])
    ]
    support_counts: dict[str, int] = defaultdict(int)
    for claim in claims:
        support_counts[claim["support"]] += 1

    headline_parts: list[str] = []
    if q4_roa and q4_roe:
        if q4_roa[0]["ticker"] == q4_roe[0]["ticker"]:
            headline_parts.append(f"{q4_roa[0]['ticker']} dẫn đầu sinh lời")
        else:
            headline_parts.append(f"{q4_roa[0]['ticker']} dẫn ROA và {q4_roe[0]['ticker']} dẫn ROE")
    if q4_npl and q4_coverage and q4_npl[-1]["ticker"] == q4_coverage[-1]["ticker"]:
        headline_parts.append(f"{q4_npl[-1]['ticker']} là outlier rủi ro tín dụng")
    if q4_npl and q4_coverage and q4_npl[0]["ticker"] == q4_coverage[0]["ticker"]:
        headline_parts.append(f"{q4_npl[0]['ticker']} có đệm tín dụng tốt nhất")
    headline = "; ".join(headline_parts) + "." if headline_parts else "Chưa đủ dữ liệu để tạo kết luận so sánh."

    limitations = [
        "Các con số được lấy từ Gold snapshot; model không phải nguồn tính toán.",
        "Không đưa ra kết luận nhân quả hoặc khuyến nghị đầu tư.",
        "Missing/unaccepted cells không được điền hoặc suy đoán.",
    ]
    if missing_limitations:
        limitations.insert(2, "Ô thiếu hoặc chưa được chấp nhận: " + "; ".join(missing_limitations))

    return {
        "contract_version": REPORT_CONTRACT_VERSION,
        "report_type": "bank_comparative_analysis",
        "title": f"Phân tích {', '.join(issuers)} ({first_period}–{last_period})",
        "run": view["run"],
        "scope": view["scope"],
        "executive_summary": {
            "headline": headline,
            "takeaways": [
                {
                    "claim_id": claim["claim_id"],
                    "title": claim["title"],
                    "text": claim["claim"],
                    "interpretation": claim["interpretation"],
                    "support": claim["support"],
                }
                for claim in claims
                if claim["priority"] == "high"
            ],
        },
        "comparisons": comparisons,
        "profiles": profiles,
        "claims": claims,
        "matrix": view["matrix"],
        "data_quality": {
            **view["summary"],
            "claim_count": len(claims),
            "claim_origin": claim_origin,
            "claim_support_counts": dict(sorted(support_counts.items())),
            "model_findings": view["analysis"].get("findings", []),
        },
        "limitations": limitations,
        "evidence_policy": {
            "numeric_authority": "gold_snapshot",
            "claim_evidence_rule": "Mỗi claim phải chỉ rõ data_refs và evidence_ids; source_locator_only không được gọi là quote-backed.",
            "causal_inference": "not_supported",
        },
    }
