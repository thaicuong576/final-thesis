"""Fail-closed validation for the claim-driven analysis-report contract."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any


class AnalysisReportContractError(ValueError):
    """The report does not satisfy the user-facing analysis contract."""


def validate_analysis_report(report: Mapping[str, Any]) -> None:
    """Validate the invariant parts of ``analysis-report-v2``.

    The validator intentionally checks relationships between claims and the
    authoritative matrix.  A report with prose, but without traceable data
    references or limitations, is rejected.
    """

    if report.get("contract_version") != "analysis-report-v2":
        raise AnalysisReportContractError("contract_version_mismatch")
    required_top = {
        "report_type",
        "title",
        "run",
        "scope",
        "executive_summary",
        "comparisons",
        "profiles",
        "claims",
        "matrix",
        "data_quality",
        "limitations",
        "evidence_policy",
    }
    missing_top = sorted(required_top - set(report))
    if missing_top:
        raise AnalysisReportContractError("top_level_fields_missing:" + ",".join(missing_top))

    scope = report["scope"]
    issuers = set(scope.get("issuers") or [])
    periods = set(scope.get("periods") or [])
    metrics = {item["metric_id"] for item in scope.get("metrics") or []}
    if not issuers or not periods or not metrics:
        raise AnalysisReportContractError("scope_incomplete")

    matrix_refs: dict[tuple[str, str, str], Mapping[str, Any]] = {}
    for row in report["matrix"]:
        ticker = row.get("ticker")
        period = row.get("period")
        if ticker not in issuers or period not in periods:
            raise AnalysisReportContractError("matrix_scope_mismatch")
        for metric in row.get("metrics") or []:
            metric_id = metric.get("metric_id")
            if metric_id not in metrics:
                raise AnalysisReportContractError("matrix_metric_scope_mismatch")
            matrix_refs[(ticker, period, metric_id)] = metric

    if not matrix_refs:
        raise AnalysisReportContractError("matrix_empty")

    claims = report["claims"]
    if not isinstance(claims, list) or not claims:
        raise AnalysisReportContractError("claims_empty")
    claim_ids: set[str] = set()
    all_evidence_ids: set[str] = set()
    for claim in claims:
        for key in ("claim_id", "title", "claim", "interpretation", "limitation", "support", "origin", "data_refs", "evidence_ids", "source_ids"):
            if key not in claim:
                raise AnalysisReportContractError(f"claim_field_missing:{key}")
        claim_id = claim["claim_id"]
        if not isinstance(claim_id, str) or not claim_id.strip() or claim_id in claim_ids:
            raise AnalysisReportContractError("claim_id_invalid_or_duplicate")
        claim_ids.add(claim_id)
        if claim["origin"] not in {"model", "deterministic_reference"}:
            raise AnalysisReportContractError(f"claim_origin_invalid:{claim_id}")
        if not all(isinstance(claim.get(key), str) and claim[key].strip() for key in ("title", "claim", "interpretation", "limitation")):
            raise AnalysisReportContractError(f"claim_text_missing:{claim_id}")
        refs = claim["data_refs"]
        if not isinstance(refs, list) or not refs:
            raise AnalysisReportContractError(f"claim_data_refs_missing:{claim_id}")
        ref_evidence: set[str] = set()
        ref_sources: set[str] = set()
        for ref in refs:
            key = (ref.get("ticker"), ref.get("period"), ref.get("metric_id"))
            if key not in matrix_refs:
                raise AnalysisReportContractError(f"claim_ref_outside_matrix:{claim_id}")
            if ref.get("status") == "valid" and ref.get("value") is None:
                raise AnalysisReportContractError(f"claim_ref_valid_without_value:{claim_id}")
            ref_evidence.update(ref.get("evidence_ids") or [])
            if ref.get("source_id"):
                ref_sources.add(ref["source_id"])
        declared_evidence = set(claim.get("evidence_ids") or [])
        declared_sources = set(claim.get("source_ids") or [])
        if not declared_evidence <= ref_evidence:
            raise AnalysisReportContractError(f"claim_evidence_not_in_refs:{claim_id}")
        if not declared_sources <= ref_sources:
            raise AnalysisReportContractError(f"claim_source_not_in_refs:{claim_id}")
        all_evidence_ids.update(declared_evidence)
        if claim["support"] == "evidence_backed" and not all(ref.get("evidence_ids") for ref in refs):
            raise AnalysisReportContractError(f"evidence_backed_without_evidence:{claim_id}")

    executive = report["executive_summary"]
    if not isinstance(executive.get("headline"), str) or not executive["headline"].strip():
        raise AnalysisReportContractError("executive_headline_missing")
    for takeaway in executive.get("takeaways") or []:
        if takeaway.get("claim_id") not in claim_ids:
            raise AnalysisReportContractError("takeaway_claim_unknown")

    limitations = report["limitations"]
    if not isinstance(limitations, list) or not limitations or not all(isinstance(item, str) and item.strip() for item in limitations):
        raise AnalysisReportContractError("limitations_missing")

    quality = report["data_quality"]
    for key in ("total_cells", "valid_cells", "missing_or_unaccepted_cells", "claim_count"):
        if key not in quality:
            raise AnalysisReportContractError(f"data_quality_field_missing:{key}")
    if quality["claim_count"] != len(claims):
        raise AnalysisReportContractError("claim_count_mismatch")
