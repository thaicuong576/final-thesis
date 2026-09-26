"""Provider-bound adaptive analysis runtime over accepted data snapshots."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import json
import logging
from pathlib import Path
from queue import Queue
import re
import sqlite3
from threading import Thread
import time
from typing import Any, Iterator, Sequence
import uuid

from thesis_data.acceptance import validate_stage1_claims
from thesis_data.acceptance_resolver import ProviderStage1DatasetResolver
from thesis_data.analysis_plan import (
    ANALYSIS_PLAN_VERSION,
    AnalysisAgent,
    AnalysisPlan,
    AnalysisRequirement,
    AnalysisScope,
    ApplicableLink,
    ApplicableLinkType,
    CausalClaimPolicy,
    FulfillmentPolicy,
    InferenceCeiling,
    LinkLevel,
    MissingDataPolicy,
    RequirementType,
)
from thesis_data.canonical_sqlite_provider import CanonicalSqliteDatasetProvider
from thesis_data.dataset_contract import (
    AnalyticalLevel,
    CanonicalObservation,
    DatasetCapabilityCatalog,
    DatasetRef,
    SupportedOperation,
)
from thesis_data.dataset_provider import DatasetProviderError, FinancialDatasetProvider
from thesis_data.gold_dataset_provider import GoldSqliteDatasetProvider
from thesis_data.openai_semantic_critic import OpenAISemanticCritic
from thesis_data.provider_config import ProviderExecutionConfig
from thesis_data.revision_controller import (
    BoundedRevisionController,
    RevisionRequest,
    RevisionResult,
)
from thesis_data.schema import (
    AcceptancePolicy,
    AcceptanceDecision,
    AssertionOperator,
    AssertionType,
    AtomicClaim,
    ClaimDataRef,
    ClaimScope,
    InferenceType,
    QualityStatus,
    StructuredAssertion,
    UnresolvedReasonCode,
)
from thesis_data.dataset_provider import peer_benchmark_observation_id

from .database import ensure_analysis_runs_table, save_analysis_run
from .llm import LLMConfigurationError
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


_GOLD_SCOPE_AUTHORITY_SHA256 = "fef07af9f3deea7afbaa60ad51c8db740388e88b64bcf843d8ab5ec8f0ad777f"


def _load_provider(
    db_path: Path,
    *,
    scope_authority_path: Path | None = None,
) -> ProviderBinding:
    """Open a supported accepted snapshot through a provider boundary only."""

    adapters: list[tuple[str, Any]] = [
        ("canonical-sqlite", CanonicalSqliteDatasetProvider(db_path)),
    ]
    if scope_authority_path is None:
        adapters.append(("gold-sqlite", GoldSqliteDatasetProvider(db_path, dataset_id="gold-sqlite")))
    else:
        # The sidecar is used only on an explicit, hash-pinned deployment
        # configuration. Never auto-discover it beside a database.
        try:
            from thesis_data.gold_scope_authority import VerifiedGoldObservationScopeAuthority

            authority = VerifiedGoldObservationScopeAuthority.load(
                Path(scope_authority_path),
                expected_canonical_sha256=_GOLD_SCOPE_AUTHORITY_SHA256,
            )
            gold_provider = GoldSqliteDatasetProvider(
                db_path,
                dataset_id="gold-sqlite",
                scope_authority=authority,
            )
        except (ImportError, TypeError, OSError, ValueError) as exc:
            raise AnalysisBlocked(
                "gold_scope_authority_unavailable",
                "The explicitly configured Gold reporting-scope authority could not be hash-verified or applied.",
            ) from exc
        adapters.append(("gold-sqlite-authorized", gold_provider))
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


def _is_lineage_only_metric(metric_id: str) -> bool:
    return metric_id.casefold().startswith("bank.input.")


def _runnable_company_metrics(
    catalog: DatasetCapabilityCatalog,
) -> tuple[Any, ...]:
    return tuple(
        item
        for item in catalog.metrics
        if item.analytical_level is AnalyticalLevel.COMPANY
        and not _is_lineage_only_metric(item.metric_id)
    )


def _metric_id_mentioned(metric_id: str, query: str) -> bool:
    return bool(
        re.search(
            rf"(?<![A-Za-z0-9_.]){re.escape(metric_id)}(?![A-Za-z0-9_.])",
            query,
            re.I,
        )
    )


def _requested_metrics(request: AnalysisRequest, catalog: DatasetCapabilityCatalog) -> tuple[str, ...]:
    company_metrics = _runnable_company_metrics(catalog)
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
    explicitly_named = tuple(
        item for item in catalog.metrics if _metric_id_mentioned(item.metric_id, query)
    )
    if any(_is_lineage_only_metric(item.metric_id) for item in explicitly_named):
        raise AnalysisBlocked(
            "lineage_only_metric",
            "The requested metric is an input used to derive a published company metric and cannot be analyzed directly.",
        )
    exact_metric_ids = {item.metric_id for item in explicitly_named}
    matched = tuple(
        metric.metric_id
        for metric in company_metrics
        if metric.metric_id in exact_metric_ids
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
    include_evidence: bool = True,
) -> tuple[AtomicClaim, Any, tuple[Any, ...], tuple[Any, ...], tuple[Any, ...]]:
    observation = provider.get_metric(dataset_ref, ticker, period, metric_id)
    if observation is None:
        raise AnalysisBlocked(
            "observation_unavailable",
            f"No observation is present for {ticker}/{period}/{metric_id}.",
        )
    if (
        observation.validation_status is not QualityStatus.VALID
        or observation.value is None
        or not observation.unit
    ):
        raise AnalysisBlocked(
            "observation_unaccepted",
            f"The observation for {ticker}/{period}/{metric_id} is not accepted as valid.",
        )
    primary_observations, sources = _resolve_primary_lineage(
        provider=provider,
        dataset_ref=dataset_ref,
        observation=observation,
        ticker=ticker,
        period=period,
        metric_id=metric_id,
    )
    source_refs = tuple(source.source_ref for source in sources)
    evidence = (
        tuple(
            item
            for item in provider.get_evidence(
                dataset_ref,
                source_refs,
                entity_id=ticker,
                period_id=period,
                metric_id=metric_id,
            )
            if item.source_ref in source_refs
            and item.entity_id == ticker
            and item.period_id == period
            and (item.metric_id is None or item.metric_id == metric_id)
            and _evidence_has_explicit_observation_link(
                item,
                observation_id=observation.observation_id,
            )
        )
        if include_evidence
        else ()
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
        limitation="No additional qualitative or causal interpretation is made beyond the structured observation.",
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
        source_refs=source_refs,
        inference_type=InferenceType.FACT,
        support="evidence_backed" if evidence else "source_locator_only",
        origin="deterministic_reference",
    )
    return claim, observation, primary_observations, sources, evidence


def _evidence_has_explicit_observation_link(
    evidence: Any,
    *,
    observation_id: str,
) -> bool:
    """Require the provider to return a reviewed observation-to-snippet join.

    Scope matches such as source, ticker, period, metric, or page overlap do
    not establish that a document snippet supports this numeric observation.
    The provider must populate ``observation_id`` only from a reviewed mapping.
    A claim ID alone is not a sufficient join to the accepted observation.
    Current DatasetEvidence has no observation-link field, so current provider
    snippets remain supplementary and are not attached to numeric claims.
    """

    linked_observation_id = getattr(evidence, "observation_id", None)
    return linked_observation_id == observation_id


def _resolve_primary_lineage(
    *,
    provider: FinancialDatasetProvider,
    dataset_ref: DatasetRef,
    observation: Any,
    ticker: str,
    period: str,
    metric_id: str,
) -> tuple[tuple[Any, ...], tuple[Any, ...]]:
    """Resolve a direct observation or every primary leaf of its derived chain."""

    sources: dict[str, Any] = {}
    primary_observations: dict[str, Any] = {}
    visiting: set[str] = set()
    visited: set[str] = set()

    def visit(current: Any) -> None:
        observation_id = str(getattr(current, "observation_id", "") or "")
        if not observation_id:
            raise AnalysisBlocked(
                "observation_lineage_invalid",
                f"The provenance chain for {ticker}/{period}/{metric_id} contains an observation without an ID.",
            )
        if observation_id in visiting:
            raise AnalysisBlocked(
                "observation_lineage_cycle",
                f"The provenance chain for {ticker}/{period}/{metric_id} contains a cycle.",
            )
        if observation_id in visited:
            return
        if (
            getattr(current, "dataset_id", None) != dataset_ref.dataset_id
            or getattr(current, "dataset_snapshot_id", None) != dataset_ref.dataset_snapshot_id
        ):
            raise AnalysisBlocked(
                "observation_snapshot_mismatch",
                f"The provenance chain for {ticker}/{period}/{metric_id} crosses dataset snapshots.",
            )
        if current.validation_status is not QualityStatus.VALID or current.value is None or not current.unit:
            raise AnalysisBlocked(
                "derived_input_unaccepted",
                f"The provenance chain for {ticker}/{period}/{metric_id} contains an unaccepted input observation.",
            )

        derivation_method = getattr(current, "derivation_method", None)
        input_ids = tuple(getattr(current, "input_observation_ids", ()) or ())
        if derivation_method:
            if getattr(current, "source_ref", None) is not None or not input_ids:
                raise AnalysisBlocked(
                    "derived_provenance_invalid",
                    f"Derived observation {observation_id} must use formula and input-observation provenance without a direct source reference.",
                )
            visiting.add(observation_id)
            for input_id in input_ids:
                input_observation = provider.resolve_observation(dataset_ref, input_id)
                if input_observation is None or input_observation.observation_id != input_id:
                    raise AnalysisBlocked(
                        "derived_input_unavailable",
                        f"Derived observation {observation_id} references an unavailable input observation.",
                    )
                if input_observation.entity_id != ticker:
                    raise AnalysisBlocked(
                        "derived_input_scope_mismatch",
                        f"Derived observation {observation_id} references an input for a different company.",
                    )
                visit(input_observation)
            visiting.remove(observation_id)
        else:
            if input_ids or not getattr(current, "source_ref", None):
                raise AnalysisBlocked(
                    "observation_source_missing",
                    f"Primary observation {observation_id} has no source reference or valid derived lineage.",
                )
            if not _observation_source_locator(current):
                raise AnalysisBlocked(
                    "observation_locator_missing",
                    f"Primary observation {observation_id} has no metric-specific source locator.",
                )
            source_ref = current.source_ref
            source = provider.get_source(dataset_ref, source_ref)
            if (
                source is None
                or source.source_ref != source_ref
                or source.validation_status is not QualityStatus.VALID
            ):
                raise AnalysisBlocked(
                    "source_unaccepted",
                    f"The primary source for observation {observation_id} is missing or unaccepted.",
                )
            sources[source_ref] = source
            primary_observations[observation_id] = current
        visited.add(observation_id)

    visit(observation)
    if not primary_observations or not sources:
        raise AnalysisBlocked(
            "observation_lineage_missing",
            f"No primary observations were resolved for {ticker}/{period}/{metric_id}.",
        )
    return tuple(primary_observations.values()), tuple(sources.values())


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
    company_metrics = _runnable_company_metrics(catalog)
    periods = tuple(item.period_id for item in catalog.periods)
    for ticker in company_entities:
        for period in periods:
            if not re.fullmatch(r"\d{4}_Q[1-4]|FY\d{4}", period, re.I):
                continue
            for metric in company_metrics:
                try:
                    claim, _, _, _, _ = _stage1_claim(
                        provider=binding.provider,
                        dataset_ref=binding.dataset_ref,
                        ticker=ticker,
                        period=period,
                        metric_id=metric.metric_id,
                        display_name=metric.display_name,
                        include_evidence=SupportedOperation.GET_EVIDENCE in operations,
                    )
                except AnalysisBlocked:
                    continue
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
        if not _is_lineage_only_metric(item.metric_id)
    ]
    peer_universes = [
        {
            "id": item.peer_universe_id,
            "label": f"Snapshot peer group ({len(item.entity_ids)} companies)",
            "entityIds": list(item.entity_ids),
            "readonly": True,
            "executable": any(len(item.entity_ids) >= 2 for item in catalog.peer_universes)
            and SupportedOperation.GET_PEER_BENCHMARK in catalog.supported_operations,
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
            "details": "Macro observations are retrieved only when explicitly requested and declared by the accepted provider." if macro_available else "The API analysis route requires declared macro observations before macro claims can execute.",
            "executable": macro_available,
        },
        "ingestionTimestamp": None,
        "validationTimestamp": None,
        "source": binding.provider_name,
        "readiness": "Runnable for company claims." if company_available else "Accepted snapshot is not runnable for company claims.",
        "database_status": "connected",
        "journal_mode": _journal_mode_from_provider(binding),
        "db_tickers_count": sum(1 for item in catalog.entities if item.entity_type.value == "company"),
        "analysis_available": company_available,
        "implemented_capabilities": (
            (["company"] if company_available else [])
            + (["sector"] if any(len(item.entity_ids) >= 2 for item in catalog.peer_universes)
               and SupportedOperation.GET_PEER_BENCHMARK in catalog.supported_operations else [])
            + (["macro"] if macro_available else [])
        ),
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


def get_dataset_capabilities(db_path: Path | None = None, *, settings=None) -> dict[str, Any]:
    """Return only capabilities declared by a validated snapshot provider."""

    resolved_db_path = Path(db_path) if db_path is not None else get_settings().get_sqlite_path()
    try:
        authority_path = getattr(settings, "gold_scope_authority_path", None) if settings is not None else None
        binding = (
            _load_provider(resolved_db_path, scope_authority_path=Path(authority_path))
            if authority_path is not None
            else _load_provider(resolved_db_path)
        )
        return _capabilities_payload(binding)
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
            "Claims without a reviewed metric-specific document snippet use the accepted observation's primary source locator and source hash."
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
        (request.periods[-1] if request.periods else request.period),
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
    """Run the frozen-plan specialist and bounded acceptance runtime."""

    def __init__(
        self,
        db_path: Path,
        settings=None,
        *,
        semantic_critic=None,
        analysis_writer=None,
    ) -> None:
        self.db_path = Path(db_path)
        self.settings = settings or get_settings()
        self._semantic_critic = semantic_critic
        self._analysis_writer = analysis_writer

    def _runs_store_path(self) -> Path:
        return self.settings.get_analysis_runs_path(dataset_path=self.db_path)

    def _model_runtime_configured(self) -> bool:
        return bool(
            self.settings.openai_api_key and self.settings.openai_api_key.strip()
            and self.settings.openai_base_url and self.settings.openai_base_url.strip()
            and self.settings.openai_model and self.settings.openai_model.strip()
        )

    def _binding(self) -> ProviderBinding:
        authority_path = getattr(self.settings, "gold_scope_authority_path", None)
        if authority_path is not None:
            return _load_provider(self.db_path, scope_authority_path=Path(authority_path))
        return _load_provider(self.db_path)

    def _analyze(
        self,
        request: AnalysisRequest,
        *,
        event_sink=None,
    ) -> AnalysisResponse:
        try:
            try:
                self._runs_store_path()
            except (OSError, ValueError):
                return _error_report(
                    "analysis_runs_store_invalid",
                    "The operational analysis history store must resolve to a writable path separate from the accepted dataset.",
                    request,
                )
            if not self._model_runtime_configured() and not (self._semantic_critic is not None and self._analysis_writer is not None):
                return _error_report(
                    "semantic_provider_unconfigured",
                    "A configured OpenAI-compatible specialist writer and semantic reviewer are required before retrieval.",
                    request,
                )
            binding = self._binding()
            semantic_critic = self._semantic_critic
            analysis_writer = self._analysis_writer
            if semantic_critic is None:
                from .adaptive_runtime import build_openai_semantic_critic

                try:
                    semantic_critic = build_openai_semantic_critic(self.settings)
                except (ValueError, LLMConfigurationError) as exc:
                    return _error_report(
                        "semantic_provider_unconfigured",
                        "A configured OpenAI-compatible semantic reviewer is required before specialist execution.",
                        request,
                    )
            if analysis_writer is None:
                from .adaptive_runtime import build_openai_analysis_writer

                try:
                    analysis_writer = build_openai_analysis_writer(self.settings)
                except (ValueError, LLMConfigurationError) as exc:
                    return _error_report(
                        "analysis_writer_unconfigured",
                        "A configured OpenAI-compatible specialist writer is required before specialist execution.",
                        request,
                    )
            from .adaptive_runtime import run_adaptive_analysis

            return run_adaptive_analysis(
                provider=binding.provider,
                dataset_ref=binding.dataset_ref,
                catalog=binding.catalog,
                request=request,
                settings=self.settings,
                semantic_critic=semantic_critic,
                analysis_writer=analysis_writer,
                emit=event_sink,
            )
        except AnalysisBlocked as exc:
            return _error_report(exc.code, exc.detail, request)
        except (DatasetProviderError, sqlite3.Error, OSError, ValueError) as exc:
            logger.warning("Analysis provider failed: %s", type(exc).__name__)
            return _error_report("provider_failure", "The accepted dataset provider could not satisfy this request.", request)

    def analyze(self, request: AnalysisRequest) -> AnalysisResponse:
        report = self._analyze(request)
        if report.status != "error":
            try:
                self.persist_run(request, report, events=[])
            except Exception as exc:
                logger.error("Validated analysis report could not be persisted: %s", type(exc).__name__)
                return _error_report(
                    "analysis_run_persistence_failed",
                    "The operational run store could not persist the accepted report.",
                    request,
                )
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
        save_analysis_run(
            db_path=self._runs_store_path(),
            run_id=report.report_id,
            created_at=datetime.now(timezone.utc).isoformat(),
            query=request.query,
            target_ticker=plan.target_ticker or "",
            peer_tickers=plan.peer_tickers,
            period=plan.period or "",
            status=report.status,
            report_json=report.model_dump(mode="json", exclude_none=True),
            events_json=events,
            model_used=(self.settings.openai_model if self.settings.openai_api_key else "provider-backed-review-unconfigured"),
            latency_ms=None,
        )

    def get_capabilities(self) -> dict[str, Any]:
        capabilities = get_dataset_capabilities(self.db_path, settings=self.settings)
        model_configured = self._model_runtime_configured()
        try:
            runs_path = self._runs_store_path()
            ensure_analysis_runs_table(runs_path)
            connection = sqlite3.connect(runs_path, timeout=2.0)
            try:
                connection.execute("SELECT COUNT(*) FROM analysis_runs").fetchone()
            finally:
                connection.close()
            store_configured = True
        except (OSError, ValueError, sqlite3.Error):
            store_configured = False
        capabilities["semantic_reviewer_configured"] = model_configured
        capabilities["specialist_writer_configured"] = model_configured
        capabilities["analysis_runs_store_configured"] = store_configured
        data_available = bool(capabilities.get("analysis_available"))
        capabilities["analysis_available"] = data_available and model_configured and store_configured
        if not data_available:
            pass
        elif not store_configured:
            capabilities["readiness"] = "ANALYSIS_RUNS_DB_PATH must resolve to a separate operational store, not the accepted dataset file."
            capabilities["limitation_code"] = "analysis_runs_store_invalid"
        elif not model_configured:
            capabilities["readiness"] = "OPENAI_API_KEY, OPENAI_BASE_URL, and OPENAI_MODEL are required for specialist writing and semantic review."
            capabilities["limitation_code"] = "semantic_provider_unconfigured"
        return capabilities

    def is_ready(self) -> tuple[bool, str, str | None]:
        capabilities = self.get_capabilities()
        return (
            bool(capabilities.get("analysis_available")),
            str(capabilities.get("readiness") or "Accepted snapshot unavailable."),
            capabilities.get("datasetSnapshotId"),
        )

    def stream_analysis(self, request: AnalysisRequest, step_delay: float = 0.35) -> Iterator[str]:
        yield from stream_analysis_query(
            request, db_path=self.db_path, step_delay=step_delay,
            settings=self.settings, semantic_critic=self._semantic_critic,
            analysis_writer=self._analysis_writer,
        )


def stream_analysis_query(
    req: AnalysisRequest,
    db_path: Path | None = None,
    step_delay: float = 0.35,
    *,
    settings=None,
    semantic_critic=None,
    analysis_writer=None,
) -> Iterator[str]:
    """Stream actual plan, specialist, review, revision, synthesis, and terminal events."""

    del step_delay  # timing is determined by real work; no scripted delays/events remain
    current_settings = settings or get_settings()
    engine = AnalysisEngine(
        db_path or current_settings.get_sqlite_path(),
        current_settings,
        semantic_critic=semantic_critic,
        analysis_writer=analysis_writer,
    )
    started_at = time.monotonic()
    sequence = 1
    events: list[dict[str, Any]] = []
    pending: Queue[dict[str, Any] | None] = Queue()

    def emit(
        event_type: str,
        payload: dict[str, Any],
        *,
        publish: bool = True,
    ) -> dict[str, Any]:
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
        if publish:
            pending.put(event_dict)
        return event_dict

    emit(
        "USER_REQUEST_CONFIRMED",
        {
            "rawQuestion": req.query,
            "datasetName": "Accepted snapshot",
            "scopeSignature": " | ".join(
                [item for item in (req.target_ticker,) if item]
                + list(req.periods or ([req.period] if req.period else []))
            ),
            "periods": list(req.periods or ([req.period] if req.period else [])),
        },
    )
    emit("PLANNING_STARTED", {"message": "Checking the request against declared snapshot capabilities."})

    def run() -> None:
        nonlocal sequence
        try:
            report = engine._analyze(req, event_sink=emit)
            if report.status == "error":
                if not events or events[-1].get("type") != "RUN_BLOCKED":
                    reason = report.limitations[0] if report.limitations else "analysis_blocked"
                    emit("RUN_BLOCKED", {"reason": reason, "reportId": report.report_id, "status": report.status})
            else:
                ready_event = emit("REPORT_READY", {
                    "reportId": report.report_id,
                    "status": report.status,
                    "message": "The terminal accepted report is ready with its limitations and provenance joins.",
                    "report": report.model_dump(mode="json", exclude_none=True),
                }, publish=False)
                try:
                    engine.persist_run(req, report, events)
                except Exception as exc:
                    logger.error("Accepted SSE report could not be persisted: %s", type(exc).__name__)
                    # The prepared terminal event is persisted only on success
                    # and is never exposed to the client on failure.
                    events.pop()
                    sequence -= 1
                    emit("RUN_BLOCKED", {"reason": "analysis_run_persistence_failed", "status": "error"})
                    return
                pending.put(ready_event)
        except Exception as exc:
            logger.warning("SSE analysis failed: %s", type(exc).__name__)
            emit("RUN_BLOCKED", {"reason": "adaptive_runtime_failure", "status": "error"})
        finally:
            pending.put(None)

    Thread(target=run, name="analysis-sse-runtime", daemon=True).start()
    while True:
        event = pending.get()
        if event is None:
            break
        event_type = str(event["type"])
        data = json.dumps(event, ensure_ascii=False)
        yield f"event: {event_type}\ndata: {data}\n\n"
