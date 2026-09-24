"""Truthful API boundary over accepted, provider-backed dataset snapshots.

The reference API currently executes company facts and Stage-1 deterministic
acceptance only. Macro, sector, semantic critique, and revision are not
implemented by this path and are never implied by its output.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import json
import logging
from pathlib import Path
import re
import sqlite3
import time
from typing import Any, Iterator, Sequence
import uuid

from thesis_data.acceptance import validate_stage1_claims
from thesis_data.acceptance_resolver import ProviderStage1DatasetResolver
from thesis_data.canonical_sqlite_provider import CanonicalSqliteDatasetProvider
from thesis_data.dataset_contract import (
    AnalyticalLevel,
    DatasetCapabilityCatalog,
    DatasetRef,
    SupportedOperation,
)
from thesis_data.dataset_provider import DatasetProviderError, FinancialDatasetProvider
from thesis_data.gold_dataset_provider import GoldSqliteDatasetProvider
from thesis_data.schema import (
    AcceptancePolicy,
    AssertionType,
    AtomicClaim,
    ClaimDataRef,
    ClaimScope,
    InferenceType,
    QualityStatus,
    StructuredAssertion,
)

from .database import save_analysis_run
from .settings import get_settings
from .schemas import (
    AnalysisPlanDTO,
    AnalysisRequest,
    AnalysisResponse,
    AnalysisSessionEventDTO,
    AtomicClaimDTO,
    CompanyInsightDTO,
    EvidenceTrailDTO,
    MacroContextDTO,
    SectorBenchmarkDTO,
)

logger = logging.getLogger(__name__)

_COMPANY_REQUIRED_OPERATIONS = frozenset(
    {
        SupportedOperation.GET_METRIC,
        SupportedOperation.RESOLVE_OBSERVATION,
        SupportedOperation.GET_SOURCE,
        SupportedOperation.GET_EVIDENCE,
    }
)
_COMPARISON_TERMS = (
    "so sánh", "so sanh", "đối thủ", "doi thu", "đối chuẩn", "doi chuan",
    "peer", "compare", "comparison", "ngành", "nganh", "sector", "trung vị", "trung vi", "benchmark",
)
_MACRO_TERMS = (
    "vĩ mô", "vi mo", "macro", "chính sách", "chinh sach", "tiền tệ", "tien te",
    "nhnn", "sbv", "lãi suất", "lai suat", "tín dụng", "tin dung", "lạm phát",
    "lam phat", "cpi", "truyền dẫn", "truyen dan",
)
_METRIC_CODES = ("ROE", "ROA", "NIM", "NPL", "CIR", "CASA", "CAR", "LDR", "LLR")
_METRIC_PHRASES = {
    "ROE": (
        "return on equity", "return-on-equity", "tỷ suất sinh lời trên vốn chủ sở hữu",
        "ty suat sinh loi tren von chu so huu", "lợi nhuận trên vốn chủ sở hữu",
        "loi nhuan tren von chu so huu",
    ),
    "ROA": (
        "return on assets", "return-on-assets", "tỷ suất sinh lời trên tổng tài sản",
        "ty suat sinh loi tren tong tai san", "lợi nhuận trên tổng tài sản",
        "loi nhuan tren tong tai san",
    ),
    "NIM": ("net interest margin", "biên lãi ròng", "bien lai rong", "biên lãi thuần", "bien lai thuan"),
    "NPL": (
        "non-performing loans", "non performing loans", "nonperforming loans",
        "nợ xấu", "no xau",
    ),
    "CIR": (
        "cost-to-income ratio", "cost to income ratio", "cost income ratio",
        "chi phí trên thu nhập", "chi phi tren thu nhap",
    ),
    "CASA": (
        "current account savings account", "current account and savings account",
        "tiền gửi không kỳ hạn", "tien gui khong ky han",
    ),
    "CAR": (
        "capital adequacy ratio", "hệ số an toàn vốn", "he so an toan von",
    ),
    "LDR": (
        "loan-to-deposit ratio", "loan to deposit ratio", "tỷ lệ cho vay trên huy động",
        "ty le cho vay tren huy dong",
    ),
    "LLR": (
        "loan loss reserve coverage", "loan-loss reserve coverage",
        "coverage of loan loss reserves", "dự phòng tổn thất cho vay",
        "du phong ton that cho vay",
    ),
}


class AnalysisBlocked(ValueError):
    """A request cannot be executed from the currently accepted data scope."""

    def __init__(self, code: str, detail: str) -> None:
        super().__init__(detail)
        self.code = code
        self.detail = detail


class ProviderBinding:
    """One validated provider, snapshot reference, and discovered catalog."""

    def __init__(
        self,
        provider: FinancialDatasetProvider,
        dataset_ref: DatasetRef,
        catalog: DatasetCapabilityCatalog,
        provider_name: str,
    ) -> None:
        self.provider = provider
        self.dataset_ref = dataset_ref
        self.catalog = catalog
        self.provider_name = provider_name


def _load_provider(db_path: Path) -> ProviderBinding:
    """Open a supported accepted snapshot through a provider boundary only."""

    adapters: tuple[tuple[str, Any], ...] = (
        ("canonical-sqlite", CanonicalSqliteDatasetProvider(db_path)),
        ("gold-sqlite", GoldSqliteDatasetProvider(db_path, dataset_id="gold-sqlite")),
    )
    for provider_name, provider in adapters:
        try:
            dataset_ref = provider.current_dataset_ref()
            catalog = provider.get_capabilities(dataset_ref)
            return ProviderBinding(provider, dataset_ref, catalog, provider_name)
        except (DatasetProviderError, sqlite3.Error, OSError, ValueError):
            continue
    if not db_path.exists():
        raise AnalysisBlocked(
            "accepted_snapshot_unavailable",
            "No readable accepted canonical or Gold snapshot is configured.",
        )
    raise AnalysisBlocked(
        "accepted_snapshot_unavailable",
        "The configured SQLite file does not expose a supported accepted canonical or Gold snapshot.",
    )


def _normalized(value: str) -> str:
    return re.sub(r"\s+", " ", value.casefold()).strip()


def _catalog_entity_matches(text: str, catalog: DatasetCapabilityCatalog) -> list[str]:
    tokens = {item.upper() for item in re.findall(r"\b[A-Za-z0-9._-]+\b", text)}
    company_ids = {
        entity.entity_id
        for entity in catalog.entities
        if entity.entity_type.value == "company"
    }
    return sorted(item for item in company_ids if item.upper() in tokens)


def _resolve_target(request: AnalysisRequest, catalog: DatasetCapabilityCatalog) -> str:
    company_ids = {
        entity.entity_id
        for entity in catalog.entities
        if entity.entity_type.value == "company"
    }
    requested = request.target_ticker.strip().upper() if request.target_ticker else None
    if requested:
        target = next((item for item in company_ids if item.upper() == requested), None)
        if target is None:
            raise AnalysisBlocked(
                "unsupported_entity",
                f"Entity {requested} is not present in the accepted snapshot.",
            )
        return target

    matches = _catalog_entity_matches(request.query, catalog)
    if len(matches) == 1:
        return matches[0]
    if len(matches) > 1:
        raise AnalysisBlocked(
            "unsupported_comparison_scope",
            "The request names multiple companies; peer comparison is not executed by this API path.",
        )
    raise AnalysisBlocked(
        "target_entity_required",
        "Provide one company present in the accepted snapshot.",
    )


def _resolve_period(request: AnalysisRequest, catalog: DatasetCapabilityCatalog) -> str:
    period_ids = tuple(item.period_id for item in catalog.periods)
    requested = request.period.strip() if request.period else None
    if requested:
        exact = next((item for item in period_ids if item.casefold() == requested.casefold()), None)
        if exact is None:
            raise AnalysisBlocked(
                "unsupported_period",
                f"Period {requested} is not an exact period in the accepted snapshot.",
            )
        period = exact
    else:
        query = request.query
        period = next(
            (item for item in period_ids if re.search(rf"(?<![\w]){re.escape(item)}(?![\w])", query, re.I)),
            None,
        )
        quarter_year = re.search(r"\b(20\d{2})\s*_?\s*[Qq]([1-4])\b", query)
        if period is None and quarter_year:
            canonical = f"{quarter_year.group(1)}_Q{quarter_year.group(2)}"
            period = next((item for item in period_ids if item.casefold() == canonical.casefold()), None)
        if period is None:
            year = re.search(r"\b20\d{2}\b", query)
            if year:
                exact_year = next((item for item in period_ids if item.casefold() == year.group(0).casefold()), None)
                period = exact_year
        if period is None:
            raise AnalysisBlocked(
                "exact_period_required",
                "Provide an exact period supported by the accepted snapshot; a year is not mapped to a quarter automatically.",
            )

    if not re.fullmatch(r"\d{4}_Q[1-4]|FY\d{4}", period, re.I):
        raise AnalysisBlocked(
            "unsupported_period_contract",
            f"Period {period} is discoverable but is not supported by the current Stage-1 claim contract.",
        )
    return period


def _metric_aliases(metric_id: str, display_name: str) -> set[str]:
    pieces = set(re.findall(r"[A-Za-z]+", metric_id.upper()))
    words = set(re.findall(r"\b[A-Za-z]{2,}\b", display_name.upper()))
    return pieces | words


def _requested_metrics(request: AnalysisRequest, catalog: DatasetCapabilityCatalog) -> tuple[str, ...]:
    company_metrics = tuple(
        item for item in catalog.metrics if item.analytical_level is AnalyticalLevel.COMPANY
    )
    if not company_metrics:
        raise AnalysisBlocked(
            "company_metrics_unavailable",
            "The accepted snapshot declares no company-level metrics.",
        )

    query = request.query
    explicit_codes = {
        code
        for code in _METRIC_CODES
        if re.search(rf"(?<![A-Z]){re.escape(code)}(?![A-Z])", query, re.I)
    }
    normalized_query = _normalized(query)
    requested_codes = set(explicit_codes)
    for code, phrases in _METRIC_PHRASES.items():
        if any(_normalized(phrase) in normalized_query for phrase in phrases):
            requested_codes.add(code)
    matched = tuple(
        metric.metric_id
        for metric in company_metrics
        if metric.metric_id.casefold() in query.casefold()
        or _normalized(metric.display_name) in normalized_query
        or bool(_metric_aliases(metric.metric_id, metric.display_name) & requested_codes)
    )
    present_codes = set().union(
        *(_metric_aliases(item.metric_id, item.display_name) for item in company_metrics)
    )
    unsupported_codes = requested_codes - present_codes
    if unsupported_codes:
        labels = ", ".join(sorted(unsupported_codes))
        raise AnalysisBlocked(
            "unsupported_metric",
            f"The accepted snapshot does not declare requested metric(s): {labels}.",
        )
    return matched or tuple(item.metric_id for item in company_metrics)


def _validate_company_only_scope(
    request: AnalysisRequest,
    target: str,
    catalog: DatasetCapabilityCatalog,
) -> tuple[str, tuple[str, ...]]:
    query = _normalized(request.query)
    if request.peer_tickers or any(term in query for term in _COMPARISON_TERMS):
        raise AnalysisBlocked(
            "unsupported_comparison_scope",
            "Peer and sector analysis is not executed by this API path.",
        )
    if any(term in query for term in _MACRO_TERMS):
        raise AnalysisBlocked(
            "unsupported_macro_scope",
            "Macro analysis is not executed by this API path.",
        )
    additional = [item for item in _catalog_entity_matches(request.query, catalog) if item != target]
    if additional:
        raise AnalysisBlocked(
            "unsupported_comparison_scope",
            "The request names multiple companies; peer comparison is not executed by this API path.",
        )
    return _resolve_period(request, catalog), _requested_metrics(request, catalog)


def _stage1_claim(
    *,
    provider: FinancialDatasetProvider,
    dataset_ref: DatasetRef,
    ticker: str,
    period: str,
    metric_id: str,
    display_name: str,
) -> tuple[AtomicClaim, Any, Any, Any]:
    observation = provider.get_metric(dataset_ref, ticker, period, metric_id)
    if observation is None:
        raise AnalysisBlocked(
            "observation_unavailable",
            f"No observation is present for {ticker}/{period}/{metric_id}.",
        )
    if observation.validation_status is not QualityStatus.VALID or observation.value is None:
        raise AnalysisBlocked(
            "observation_unaccepted",
            f"The observation for {ticker}/{period}/{metric_id} is not accepted as valid.",
        )
    if not _observation_source_locator(observation):
        raise AnalysisBlocked(
            "observation_locator_missing",
            f"The accepted observation for {ticker}/{period}/{metric_id} has no metric-specific source locator.",
        )
    if not observation.source_ref:
        raise AnalysisBlocked(
            "observation_source_missing",
            f"The observation for {ticker}/{period}/{metric_id} has no source reference.",
        )
    source = provider.get_source(dataset_ref, observation.source_ref)
    if source is None or source.validation_status is not QualityStatus.VALID:
        raise AnalysisBlocked(
            "source_unaccepted",
            f"The source for {ticker}/{period}/{metric_id} is missing or unaccepted.",
        )
    evidence = tuple(
        item
        for item in provider.get_evidence(
            dataset_ref,
            (observation.source_ref,),
            entity_id=ticker,
            period_id=period,
            metric_id=metric_id,
        )
        if item.source_ref == observation.source_ref
    )
    if not evidence:
        raise AnalysisBlocked(
            "evidence_unavailable",
            f"No resolvable document evidence is available for {ticker}/{period}/{metric_id}.",
        )

    reference_type = "derived_metric" if observation.derivation_method else "observation"
    data_ref = ClaimDataRef(
        ref_id=observation.observation_id,
        ref_type=reference_type,
        entity=ticker,
        period=period,
        metric_id=metric_id,
    )
    scope = ClaimScope(entities=(ticker,), periods=(period,), metric_ids=(metric_id,))
    claim = AtomicClaim(
        claim_id=f"claim-{observation.observation_id}",
        claim_text=(
            f"{ticker} has provider-backed {display_name}={observation.value} {observation.unit} "
            f"for {period}."
        ),
        claim_type="numeric",
        title=f"{ticker} {display_name} {period}",
        interpretation="Provider-backed factual observation; no financial interpretation was generated.",
        limitation="Semantic critique and bounded revision were not run by this API path.",
        scope=scope,
        assertions=(
            StructuredAssertion(
                assertion_id=f"assertion-{observation.observation_id}",
                assertion_type=AssertionType.METRIC_VALUE,
                entity=ticker,
                period=period,
                metric_id=metric_id,
                asserted_value=observation.value,
                unit=observation.unit,
                data_refs=(data_ref,),
                formula_version=observation.derivation_method,
            ),
        ),
        evidence_refs=tuple(item.evidence_id for item in evidence),
        source_refs=(observation.source_ref,),
        inference_type=InferenceType.FACT,
        support="evidence_backed",
        origin="deterministic_reference",
    )
    return claim, observation, source, evidence


def _observation_source_locator(observation: Any) -> str | None:
    locator = getattr(observation, "source_locator", None)
    if not locator:
        locator = observation.metadata.get("source_locator")
    return locator.strip() if isinstance(locator, str) and locator.strip() else None


def _error_report(code: str, detail: str, request: AnalysisRequest) -> AnalysisResponse:
    report_id = f"report-{uuid.uuid4().hex}"
    return AnalysisResponse(
        report_id=report_id,
        status="error",
        limitations=[f"{code}: {detail}"],
    )


def _provider_macro_available(catalog: DatasetCapabilityCatalog) -> bool:
    operations = set(catalog.supported_operations)
    return (
        SupportedOperation.GET_MACRO_OBSERVATION in operations
        and any(metric.analytical_level is AnalyticalLevel.MACRO for metric in catalog.metrics)
    )


def _has_runnable_company_claim(binding: ProviderBinding) -> bool:
    """Check that the declared company scope contains at least one Stage-1 claim."""

    catalog = binding.catalog
    operations = set(catalog.supported_operations)
    if not _COMPANY_REQUIRED_OPERATIONS.issubset(operations):
        return False
    company_entities = tuple(
        item.entity_id for item in catalog.entities if item.entity_type.value == "company"
    )
    company_metrics = tuple(
        item for item in catalog.metrics if item.analytical_level is AnalyticalLevel.COMPANY
    )
    periods = tuple(item.period_id for item in catalog.periods)
    for ticker in company_entities:
        for period in periods:
            if not re.fullmatch(r"\d{4}_Q[1-4]|FY\d{4}", period, re.I):
                continue
            for metric in company_metrics:
                try:
                    claim, _, _, _ = _stage1_claim(
                        provider=binding.provider,
                        dataset_ref=binding.dataset_ref,
                        ticker=ticker,
                        period=period,
                        metric_id=metric.metric_id,
                        display_name=metric.display_name,
                    )
                except AnalysisBlocked as exc:
                    if exc.code in {
                        "observation_unavailable",
                        "observation_unaccepted",
                        "observation_locator_missing",
                        "observation_source_missing",
                        "source_unaccepted",
                        "evidence_unavailable",
                    }:
                        continue
                    raise
                scope = ClaimScope(
                    entities=(ticker,),
                    periods=(period,),
                    metric_ids=(metric.metric_id,),
                )
                stage1_report = validate_stage1_claims(
                    ProviderStage1DatasetResolver(binding.provider, binding.dataset_ref),
                    (claim,),
                    scope,
                    AcceptancePolicy(policy_version="api-stage1-v1", provisional_threshold=0.75),
                )
                if stage1_report.passed:
                    return True
    return False


def _capabilities_payload(binding: ProviderBinding) -> dict[str, Any]:
    catalog = binding.catalog
    company_available = _has_runnable_company_claim(binding)
    entities = [
        {
            "id": item.entity_id,
            "ticker": str(item.attributes.get("ticker") or item.entity_id),
            "name": item.display_name,
            "type": item.entity_type.value,
        }
        for item in catalog.entities
    ]
    periods = []
    for item in catalog.periods:
        match = re.fullmatch(r"(20\d{2})_Q([1-4])", item.period_id, re.I)
        period_row: dict[str, Any] = {"id": item.period_id, "label": item.label}
        if match:
            period_row.update({"year": int(match.group(1)), "quarter": int(match.group(2))})
        periods.append(period_row)
    metrics = [
        {
            "id": item.metric_id,
            "acronym": item.metric_id.rsplit(".", 1)[-1].upper(),
            "label": item.display_name,
            "topicId": item.analytical_level.value,
            "unit": item.default_unit,
        }
        for item in catalog.metrics
    ]
    peer_universes = [
        {
            "id": item.peer_universe_id,
            "label": f"Snapshot peer group ({len(item.entity_ids)} companies)",
            "entityIds": list(item.entity_ids),
            "readonly": True,
            "executable": False,
        }
        for item in catalog.peer_universes
    ]
    macro_available = _provider_macro_available(catalog)
    return {
        "snapshotId": catalog.dataset_ref.dataset_snapshot_id,
        "datasetId": catalog.dataset_ref.dataset_id,
        "datasetSnapshotId": catalog.dataset_ref.dataset_snapshot_id,
        "goldVersion": "v5" if binding.provider_name == "gold-sqlite" else None,
        "entities": entities,
        "periods": periods,
        "metrics": metrics,
        "topics": [],
        "peerUniverses": peer_universes,
        "peerUniverse": peer_universes[0] if len(peer_universes) == 1 else None,
        "macro": {
            "status": "AVAILABLE" if macro_available else "UNAVAILABLE",
            "minimumContractSatisfied": macro_available,
            "summary": "Macro observations are declared by the accepted provider." if macro_available else "No accepted macro observation capability is declared.",
            "details": "The API analysis route does not execute macro analysis.",
            "executable": False,
        },
        "ingestionTimestamp": None,
        "validationTimestamp": None,
        "source": binding.provider_name,
        "readiness": "Runnable for company claims." if company_available else "Accepted snapshot is not runnable for company claims.",
        "database_status": "connected",
        "journal_mode": _journal_mode_from_provider(binding),
        "db_tickers_count": sum(1 for item in catalog.entities if item.entity_type.value == "company"),
        "analysis_available": company_available,
        "implemented_capabilities": ["company"] if company_available else [],
        "supported_operations": sorted(item.value for item in catalog.supported_operations),
    }


def _journal_mode_from_provider(binding: ProviderBinding) -> str:
    db_path = getattr(binding.provider, "_db_path", None)
    if db_path is None:
        return "unknown"
    try:
        connection = sqlite3.connect(f"file:{Path(db_path).resolve()}?mode=ro", uri=True)
        try:
            row = connection.execute("PRAGMA journal_mode").fetchone()
            return str(row[0]).lower() if row else "unknown"
        finally:
            connection.close()
    except sqlite3.Error:
        return "unknown"


def _unavailable_capabilities(detail: str, code: str) -> dict[str, Any]:
    return {
            "snapshotId": None,
            "datasetId": None,
            "datasetSnapshotId": None,
            "goldVersion": None,
            "entities": [],
            "periods": [],
            "metrics": [],
            "topics": [],
            "peerUniverses": [],
            "peerUniverse": None,
            "macro": {
                "status": "UNAVAILABLE",
                "minimumContractSatisfied": False,
                "summary": "No accepted snapshot is available.",
                "details": "Macro capability is unknown until an accepted snapshot is configured.",
                "executable": False,
            },
            "ingestionTimestamp": None,
            "validationTimestamp": None,
            "source": None,
            "readiness": detail,
            "database_status": "disconnected",
            "journal_mode": "unknown",
            "db_tickers_count": 0,
            "analysis_available": False,
            "implemented_capabilities": [],
            "supported_operations": [],
            "limitation_code": code,
    }


def get_dataset_capabilities(db_path: Path | None = None) -> dict[str, Any]:
    """Return only capabilities declared by a validated snapshot provider."""

    resolved_db_path = Path(db_path) if db_path is not None else get_settings().get_sqlite_path()
    try:
        return _capabilities_payload(_load_provider(resolved_db_path))
    except AnalysisBlocked as exc:
        return _unavailable_capabilities(exc.detail, exc.code)
    except (DatasetProviderError, sqlite3.Error, OSError, ValueError):
        return _unavailable_capabilities(
            "The accepted dataset provider could not verify runnable company observations.",
            "provider_failure",
        )


def _plan(
    request: AnalysisRequest,
    target: str,
    period: str,
    dataset_snapshot_id: str,
    metric_ids: Sequence[str],
    metric_specific_evidence: bool,
    reporting_scope_known: bool,
) -> AnalysisPlanDTO:
    return AnalysisPlanDTO(
        plan_id=f"plan-{uuid.uuid4().hex[:12]}",
        query=request.query,
        target_ticker=target,
        peer_tickers=[],
        period=period,
        required_capabilities=["company"],
        applicable_links=[],
        dataset_snapshot_id=dataset_snapshot_id,
        rationale="The request is limited to the target company and the listed provider metrics.",
        known_limitations=[
            "Macro and sector analysis are not executed by this API path.",
            "Semantic critique and bounded revision were not run.",
        ] + ([] if metric_specific_evidence else [
            "Gold snippets are source/period-level; numeric claims rely on each accepted metric observation's own source locator, not on snippets from another metric."
        ]) + ([] if reporting_scope_known else [
            "The accepted observation does not declare reporting scope; the API does not infer consolidated or parent-only scope."
        ]),
    )


def parse_query_entities(
    query: str,
    target_ticker: str | None = None,
    peer_tickers: Sequence[str] | None = None,
    period: str | None = None,
    auto_default_peers: bool = False,
) -> tuple[str | None, list[str], str | None]:
    """Parse explicit request scope without inventing a target, peer, or period."""

    del auto_default_peers  # retained for source compatibility; defaults are intentionally disabled
    target = target_ticker.strip().upper() if target_ticker and target_ticker.strip() else None
    peers = [item.strip().upper() for item in (peer_tickers or ()) if item.strip()]
    tokens = re.findall(r"\b[A-Za-z]{3}\b", query.upper())
    if target is None and tokens:
        target = tokens[0]
    if not peers and target is not None:
        peers = list(dict.fromkeys(item for item in tokens if item != target))
    clean_period = period.strip() if period and period.strip() else None
    if clean_period is None:
        quarter = re.search(r"\b(20\d{2})\s*_?\s*[Qq]([1-4])\b", query)
        year = re.search(r"\b20\d{2}\b", query)
        if quarter:
            clean_period = f"{quarter.group(1)}_Q{quarter.group(2)}"
        elif year:
            clean_period = year.group(0)
    return target, peers, clean_period


@dataclass(frozen=True)
class _UnboundAnalysisPlan:
    """Internal planner draft; it is never serialized as a public API plan."""

    plan_id: str
    query: str
    target_ticker: str | None
    peer_tickers: list[str]
    period: str | None
    required_capabilities: list[str]
    applicable_links: list[str]
    dataset_snapshot_id: None
    rationale: str
    known_limitations: list[str]


def build_analysis_plan(
    request: AnalysisRequest,
    plan_id: str | None = None,
    dataset_snapshot_id: str | None = None,
) -> _UnboundAnalysisPlan:
    """Build an unbound scope draft for legacy planner callers; never fake snapshot identity."""

    del dataset_snapshot_id  # Planner-only drafts cannot assert provider binding.

    target, peers, period = parse_query_entities(
        request.query,
        request.target_ticker,
        request.peer_tickers,
        request.period,
    )
    query = _normalized(request.query)
    needs_macro = any(item in query for item in _MACRO_TERMS)
    needs_sector = bool(peers) or any(item in query for item in _COMPARISON_TERMS)
    capabilities = ["company"]
    if needs_sector:
        capabilities.append("sector")
    if needs_macro:
        capabilities.append("macro")
    links = ["peer_comparison"] if needs_sector else []
    if needs_macro:
        links.append("macro_transmission")
    return _UnboundAnalysisPlan(
        plan_id=plan_id or f"plan-{uuid.uuid4().hex[:12]}",
        query=request.query,
        target_ticker=target,
        peer_tickers=peers,
        period=period,
        required_capabilities=capabilities,
        applicable_links=links,
        dataset_snapshot_id=None,
        rationale="Unbound plan draft; execution must validate the accepted provider scope.",
        known_limitations=["This plan is not executable until bound to an accepted snapshot."],
    )


# The following helpers remain for legacy agent-tool imports. API routes below do
# not use them; the route path uses only the accepted providers and Stage-1.
def _resolve_db_period(conn: sqlite3.Connection, ticker: str, period: str) -> str:
    return period.upper()


def fetch_company_ratios(
    conn: sqlite3.Connection,
    ticker: str,
    period: str,
) -> dict[str, float | None]:
    raw: dict[str, float | None] = {}
    try:
        rows = conn.execute(
            "SELECT field_code, value FROM ratio_observations WHERE ticker = ? AND period = ?",
            (ticker, _resolve_db_period(conn, ticker, period)),
        ).fetchall()
    except sqlite3.Error:
        rows = ()
    aliases = {
        "roe": ("roe",), "nim": ("nim", "netinterestmargin"), "npl": ("npl",),
        "cir": ("cir", "costtoincome"), "casa": ("casa", "casaratio"),
    }
    for code, value in rows:
        raw[str(code).casefold()] = float(value) if value is not None else None
    result: dict[str, float | None] = {}
    for key, codes in aliases.items():
        value = next((raw[code] for code in codes if code in raw), None)
        if value is not None:
            if key == "cir":
                value = abs(value)
            if abs(value) <= 1.0:
                value *= 100.0
            value = round(value, 2)
        result[key] = value
    return result


def calculate_sector_benchmark(
    conn: sqlite3.Connection,
    period: str,
    sample_tickers: Sequence[str],
) -> SectorBenchmarkDTO:
    from statistics import median

    values: dict[str, list[float]] = {key: [] for key in ("roe", "nim", "npl", "cir", "casa")}
    for ticker in dict.fromkeys(item.strip().upper() for item in sample_tickers if item.strip()):
        for key, value in fetch_company_ratios(conn, ticker, period).items():
            if value is not None:
                values[key].append(value)
    return SectorBenchmarkDTO(
        sector="Banking",
        peer_median_roe=median(values["roe"]) if values["roe"] else None,
        peer_median_nim=median(values["nim"]) if values["nim"] else None,
        peer_median_npl=median(values["npl"]) if values["npl"] else None,
        peer_median_cir=median(values["cir"]) if values["cir"] else None,
        peer_median_casa=median(values["casa"]) if values["casa"] else None,
    )


def fetch_macro_context(conn: sqlite3.Connection, period: str) -> MacroContextDTO:
    """Legacy helper returns no macro values unless a future provider path supplies them."""

    del conn, period
    return MacroContextDTO()


def generate_company_assessment(
    ticker: str,
    metrics: dict[str, float | None],
    benchmark: SectorBenchmarkDTO | None = None,
) -> str:
    del ticker, metrics, benchmark
    return "No qualitative assessment was performed by this API path."


class AnalysisEngine:
    """Run company observations against a validated snapshot and Stage-1 gates."""

    def __init__(self, db_path: Path) -> None:
        self.db_path = Path(db_path)

    def _analyze(self, request: AnalysisRequest) -> AnalysisResponse:
        try:
            binding = _load_provider(self.db_path)
            target = _resolve_target(request, binding.catalog)
            period, metric_ids = _validate_company_only_scope(request, target, binding.catalog)
            operations = set(binding.catalog.supported_operations)
            if not _COMPANY_REQUIRED_OPERATIONS.issubset(operations):
                raise AnalysisBlocked(
                    "company_evidence_capability_unavailable",
                    "The accepted provider cannot resolve observations, sources, and document evidence required for company claims.",
                )

            metric_by_id = {item.metric_id: item for item in binding.catalog.metrics}
            claims: list[AtomicClaim] = []
            observations: list[Any] = []
            sources: dict[str, Any] = {}
            evidence_by_id: dict[str, Any] = {}
            for metric_id in metric_ids:
                claim, observation, source, evidence = _stage1_claim(
                    provider=binding.provider,
                    dataset_ref=binding.dataset_ref,
                    ticker=target,
                    period=period,
                    metric_id=metric_id,
                    display_name=metric_by_id[metric_id].display_name,
                )
                claims.append(claim)
                observations.append(observation)
                sources[source.source_ref] = source
                evidence_by_id.update({item.evidence_id: item for item in evidence})

            workload_scope = ClaimScope(
                entities=(target,), periods=(period,), metric_ids=metric_ids
            )
            resolver = ProviderStage1DatasetResolver(binding.provider, binding.dataset_ref)
            stage1_report = validate_stage1_claims(
                resolver,
                tuple(claims),
                workload_scope,
                AcceptancePolicy(policy_version="api-stage1-v1", provisional_threshold=0.75),
            )
            if not stage1_report.passed:
                violations = sorted(
                    {
                        violation
                        for gate in stage1_report.gate_results.values()
                        for violation in gate.violations
                    }
                    | set(stage1_report.integrity_violations)
                )
                detail = "; ".join(violations) if violations else "Stage-1 rejected the candidate claims."
                raise AnalysisBlocked("stage1_rejected", detail)

            metric_specific_evidence = all(
                evidence_by_id[evidence_id].metric_id == observation.metric_id
                for claim, observation in zip(claims, observations)
                for evidence_id in claim.evidence_refs
            )
            reporting_scope_known = all(
                bool(
                    getattr(observation, "reporting_scope", None)
                    or observation.metadata.get("reporting_scope")
                )
                for observation in observations
            )
            plan = _plan(
                request,
                target,
                period,
                binding.dataset_ref.dataset_snapshot_id,
                metric_ids,
                metric_specific_evidence,
                reporting_scope_known,
            )
            evidence_trail: list[EvidenceTrailDTO] = []
            claim_dtos: list[AtomicClaimDTO] = []
            for claim, observation in zip(claims, observations):
                source = sources[observation.source_ref]
                claim_evidence = [evidence_by_id[item] for item in claim.evidence_refs]
                claim_dtos.append(
                    AtomicClaimDTO(
                        claim_id=claim.claim_id,
                        capability="company",
                        ticker=target,
                        metric=metric_by_id[observation.metric_id].display_name,
                        period=period,
                        statement=claim.claim_text,
                        claim_type="factual_observation",
                        evidence_refs=list(claim.evidence_refs),
                        confidence=None,
                        stage1_status="accepted",
                        stage2_critique_status=None,
                    )
                )
                for item in claim_evidence:
                    evidence_trail.append(
                        EvidenceTrailDTO(
                            evidence_id=item.evidence_id,
                            metric=metric_by_id[observation.metric_id].display_name,
                            ticker=target,
                            period=period,
                            value=observation.value,
                            source_doc=source.source_url,
                            table_locator=_observation_source_locator(observation),
                            provenance_hash=source.content_hash,
                        )
                    )

            return AnalysisResponse(
                report_id=f"report-{uuid.uuid4().hex}",
                status="partial",
                analysis_plan=plan,
                macro_context=None,
                sector_benchmark=None,
                company_insights=[
                    CompanyInsightDTO(
                        ticker=target,
                        assessment="No qualitative assessment was performed by this API path.",
                    )
                ],
                cross_level_critique=[],
                atomic_claims=claim_dtos,
                evidence_trail=evidence_trail,
                revision_summary=None,
                limitations=plan.known_limitations,
            )
        except AnalysisBlocked as exc:
            return _error_report(exc.code, exc.detail, request)
        except (DatasetProviderError, sqlite3.Error, OSError, ValueError) as exc:
            logger.warning("Analysis provider failed: %s", type(exc).__name__)
            return _error_report(
                "provider_failure",
                "The accepted dataset provider could not satisfy this request.",
                request,
            )

    def analyze(self, request: AnalysisRequest) -> AnalysisResponse:
        report = self._analyze(request)
        if report.status != "error":
            self.persist_run(request, report, events=[])
        return report

    def persist_run(
        self,
        request: AnalysisRequest,
        report: AnalysisResponse,
        events: list[dict[str, Any]],
    ) -> None:
        plan = report.analysis_plan
        if plan is None or report.status == "error":
            return
        try:
            save_analysis_run(
                db_path=self.db_path,
                run_id=report.report_id,
                created_at=datetime.now(timezone.utc).isoformat(),
                query=request.query,
                target_ticker=plan.target_ticker or "",
                peer_tickers=[],
                period=plan.period or "",
                status=report.status,
                report_json=report.model_dump(mode="json", exclude_none=True),
                events_json=events,
                model_used="provider-stage1",
                latency_ms=None,
            )
        except Exception as exc:
            logger.warning("Failed to persist validated analysis run: %s", type(exc).__name__)

    def get_capabilities(self) -> dict[str, Any]:
        return get_dataset_capabilities(self.db_path)

    def is_ready(self) -> tuple[bool, str, str | None]:
        capabilities = self.get_capabilities()
        return (
            bool(capabilities.get("analysis_available")),
            str(capabilities.get("readiness") or "Accepted snapshot unavailable."),
            capabilities.get("datasetSnapshotId"),
        )

    def stream_analysis(self, request: AnalysisRequest, step_delay: float = 0.35) -> Iterator[str]:
        yield from stream_analysis_query(request, db_path=self.db_path, step_delay=step_delay)


def stream_analysis_query(
    req: AnalysisRequest,
    db_path: Path | None = None,
    step_delay: float = 0.35,
) -> Iterator[str]:
    """Stream only plan, Stage-1, synthesis, blocked, and report events that occurred."""

    del step_delay
    engine = AnalysisEngine(db_path or get_settings().get_sqlite_path())
    started_at = time.monotonic()
    sequence = 1
    events: list[dict[str, Any]] = []

    def emit(event_type: str, payload: dict[str, Any]) -> str:
        nonlocal sequence
        event = AnalysisSessionEventDTO(
            eventId=f"evt-{uuid.uuid4().hex}",
            sequence=sequence,
            occurredAtMs=max(0, int((time.monotonic() - started_at) * 1000)),
            type=event_type,
            payload=payload,
        )
        sequence += 1
        event_dict = event.model_dump(by_alias=True)
        events.append(event_dict)
        data = json.dumps(event_dict, ensure_ascii=False)
        return f"event: {event_type}\ndata: {data}\n\n"

    yield emit(
        "USER_REQUEST_CONFIRMED",
        {
            "rawQuestion": req.query,
            "datasetName": "Accepted snapshot",
            "scopeSignature": " | ".join(
                item for item in (req.target_ticker, req.period) if item
            ),
        },
    )
    yield emit(
        "PLANNING_STARTED",
        {"message": "Checking the request against the configured accepted snapshot."},
    )

    report = engine._analyze(req)
    if report.status == "error":
        reason = report.limitations[0] if report.limitations else "analysis_blocked"
        yield emit(
            "RUN_BLOCKED",
            {"reason": reason, "reportId": report.report_id, "status": report.status},
        )
        return

    plan = report.analysis_plan
    assert plan is not None
    yield emit(
        "PLAN_CREATED",
        {
            "requiredSpecialists": plan.required_capabilities,
            "planSummary": "Company-only provider retrieval with deterministic Stage-1 acceptance.",
            "message": f"Bound to accepted snapshot {plan.dataset_snapshot_id} for {plan.target_ticker} at {plan.period}.",
        },
    )
    yield emit(
        "REVIEW_STARTED",
        {"message": "Running deterministic Stage-1 acceptance. Semantic critique and revision are unavailable."},
    )
    yield emit("SYNTHESIS_STARTED", {"message": "Assembling the accepted factual claims and evidence trail."})
    yield emit("SYNTHESIS_COMPLETED", {"message": "The provider-backed Stage-1 report has been assembled."})
    yield emit(
        "REPORT_READY",
        {
            "reportId": report.report_id,
            "status": report.status,
            "message": "The Stage-1 factual report is ready with the listed limitations.",
            "report": report.model_dump(mode="json", exclude_none=True),
        },
    )
    engine.persist_run(req, report, events)
