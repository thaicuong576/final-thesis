"""Query-adaptive, provider-backed analysis route orchestration.

The route freezes its plan before retrieving specialist outputs.  Accepted
provider observations are the only source of numeric claims; the semantic
critic is called only after all deterministic Stage-1 gates pass.
"""

from __future__ import annotations

from collections.abc import Callable, Sequence
from dataclasses import dataclass
import hashlib
import logging
from pathlib import Path
import re
import unicodedata
import uuid
from decimal import Decimal, InvalidOperation
from typing import Any

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
from thesis_data.dataset_contract import (
    AnalyticalLevel,
    CanonicalObservation,
    DatasetCapabilityCatalog,
    DatasetMetric,
    DatasetRef,
    SupportedOperation,
)
from thesis_data.dataset_provider import (
    DatasetProviderError,
    FinancialDatasetProvider,
    peer_benchmark_observation_id,
)
from thesis_data.openai_semantic_critic import OpenAISemanticCritic
from thesis_data.provider_config import ProviderExecutionConfig
from thesis_data.revision_controller import (
    BoundedRevisionController,
    RevisionRequest,
    RevisionResult,
)
from thesis_data.schema import (
    AcceptanceDecision,
    AcceptancePolicy,
    AssertionOperator,
    AssertionType,
    AtomicClaim,
    ClaimDataRef,
    ClaimScope,
    CritiqueIssueStatus,
    InferenceType,
    QualityStatus,
    Stage1ValidationReport,
    StructuredAssertion,
)
from thesis_data.semantic_critic import SemanticRoundContext
from thesis_data.semantic_evaluation import (
    ApplicableLinkResult,
    SemanticDimension,
    SemanticDimensionApplicability,
    SemanticDimensionResult,
    StructuredCriticResult,
    expected_dimension_applicability,
)

from .schemas import (
    AnalysisPlanDTO,
    AnalysisRequest,
    AnalysisResponse,
    AtomicClaimDTO,
    BoundedRevisionSummaryDTO,
    CompanyInsightDTO,
    CompanyMetricPeriodRecordDTO,
    CritiqueItemDTO,
    EvidenceTrailDTO,
    MacroContextDTO,
    PeerBenchmarkRecordDTO,
    SectorBenchmarkDTO,
)
from .analysis_writer import AnalysisWriterError
from .settings import Settings

logger = logging.getLogger(__name__)

_COMPARE_TERMS = (
    "so sánh", "so sanh", "đối thủ", "doi thu", "đối chuẩn", "doi chuan",
    "peer", "compare", "comparison", "sector", "benchmark", "trung vị", "trung vi",
)
_MACRO_LINK_TERMS = (
    "impact", "affect", "transmission", "transmit", "relationship", "relate",
    "ảnh hưởng", "anh huong", "tác động", "tac dong", "truyền dẫn", "truyen dan",
)
_QUARTER_RE = re.compile(r"\b(20\d{2})\s*_?\s*[Qq]([1-4])\b")
_FY_PERIOD_RE = re.compile(r"\bFY\s*(20\d{2})\b", re.IGNORECASE)
_FY_RANGE_RE = re.compile(r"\bFY\s*(20\d{2})\s*(?:to|through|[-–—])\s*(?:FY)?\s*(20\d{2})\b", re.IGNORECASE)
_COMPACT_QUARTER_RANGE_RE = re.compile(
    r"\b(20\d{2})\s*_?\s*[Qq]([1-4])\s*[-–—]\s*[Qq]([1-4])\b"
)
_FULL_QUARTER_RANGE_RE = re.compile(
    r"\b(20\d{2})\s*_?\s*[Qq]([1-4])\s*"
    r"(?:to|through|across|until|[-–—])\s*"
    r"(?:(20\d{2})\s*_?\s*)?[Qq]([1-4])\b",
    re.IGNORECASE,
)
_BETWEEN_QUARTER_RANGE_RE = re.compile(
    r"\b(?:between|from|từ|tu)\s+(20\d{2})\s*_?\s*[Qq]([1-4])\s+"
    r"(?:and|to|through|đến|den)\s+(?:(20\d{2})\s*_?\s*)?[Qq]([1-4])\b",
    re.IGNORECASE,
)
_PERIOD_RANGE_RE = re.compile(
    r"\b(?:across|from|between|since|through|over|last|từ|tu|trong giai đoạn)\b.{0,45}"
    r"\b(?:20\d{2}\s*_?\s*[Qq][1-4]|\d+\s+(?:quarters?|years?|năm|quý))\b",
    re.IGNORECASE,
)
_YEAR_QUARTER_RANGE_RE = re.compile(
    r"\b20\d{2}\s*_?\s*[Qq][1-4]\s*(?:to|through|across|until|[-–—])\s*"
    r"(?:(?:20\d{2}\s*_?\s*)?[Qq][1-4])\b",
    re.IGNORECASE,
)
_WRITER_PERIOD_LITERAL_RE = re.compile(r"\b(?:20\d{2}(?:\s*_?\s*Q[1-4])?|Q[1-4])\b", re.IGNORECASE)
_WRITER_PERIOD_WORD_RE = re.compile(
    r"\b(?:(?:last|previous|prior)\s+(?:quarter|year|period)|"
    r"quarter\s+over\s+quarter|year\s+over\s+year|over\s+time|historically|"
    r"quý\s+trước|năm\s+trước|kỳ\s+trước|qua\s+các\s+quý|trong\s+các\s+năm)\b",
    re.IGNORECASE,
)
_WRITER_NUMERAL_WORD_RE = re.compile(
    r"\b(?:zero|one|two|three|four|five|six|seven|eight|nine|ten|eleven|twelve|"
    r"thirteen|fourteen|fifteen|sixteen|seventeen|eighteen|nineteen|twenty|thirty|"
    r"forty|fifty|sixty|seventy|eighty|ninety|hundred|thousand|million|billion|"
    r"trillion|half|halves|quarter|quarters|twice|double|doubled|doubles|doubling|"
    r"triple|tripled|triples|tripling|threefold|fourfold|percent(?:age)?|basis\s+points?|"
    r"không|một|mốt|hai|ba|bốn|tư|năm|"
    r"lăm|sáu|bảy|tám|chín|mười|mươi|trăm|nghìn|ngàn|triệu|tỷ|tỉ|phần\s+trăm|"
    r"điểm\s+cơ\s+bản)\b",
    re.IGNORECASE,
)
_WRITER_TEMPORAL_CHANGE_RE = re.compile(
    r"\b(?:improv(?:e|ed|es|ing)|deteriorat(?:e|ed|es|ing)|increas(?:e|ed|es|ing)|"
    r"decreas(?:e|ed|es|ing)|trend(?:s|ed|ing)?|momentum|rising|fell|falling|"
    r"declin(?:e|ed|es|ing)|growth|grew|shrank|tăng|giảm|cải thiện|xấu đi|"
    r"xu hướng|tăng trưởng|suy giảm)\b",
    re.IGNORECASE,
)
_WRITER_CAUSAL_RE = re.compile(
    r"\b(?:because|due to|driven by|caused by|causes?|leads? to|resulted? from|"
    r"as a result|do|bởi|vì|nhờ|khiến|dẫn đến)\b",
    re.IGNORECASE,
)
_API_POLICY = AcceptancePolicy(
    policy_version="api-adaptive-acceptance-v1",
    provisional_threshold=0.75,
    max_revision_rounds=2,
)


@dataclass
class ClaimArtifact:
    """Provider resources needed to render explicit report provenance joins."""

    claim: AtomicClaim
    observation: CanonicalObservation
    primary_observations: tuple[Any, ...]
    sources: dict[str, Any]
    evidence: tuple[Any, ...]
    capability: str
    display_name: str


class _RuntimeStage1Evaluator:
    def __init__(
        self,
        *,
        resolver: ProviderStage1DatasetResolver,
        workload_scope: ClaimScope,
    ) -> None:
        self.resolver = resolver
        self.workload_scope = workload_scope
        self.last_report: Stage1ValidationReport | None = None

    def evaluate(self, *, plan: AnalysisPlan, claims, policy: AcceptancePolicy) -> Stage1ValidationReport:
        report = validate_stage1_claims(
            self.resolver,
            tuple(claims),
            self.workload_scope,
            policy,
        )
        self.last_report = Stage1ValidationReport(
            passed=all(item.passed for item in report.gate_results.values()) and not report.integrity_violations,
            gate_results=report.gate_results,
            integrity_violations=report.integrity_violations,
        )
        return self.last_report


class _EventingCritic:
    def __init__(self, critic, emit: Callable[[str, dict[str, Any]], None]) -> None:
        self.critic = critic
        self.emit = emit
        self.latest_result: StructuredCriticResult | None = None

    def evaluate(self, *, plan, claims, stage1_report, round_context):
        result = self.critic.evaluate(
            plan=plan,
            claims=claims,
            stage1_report=stage1_report,
            round_context=round_context.model_copy(deep=True),
        )
        self.latest_result = result.model_copy(deep=True)
        self.emit(
            "REVIEW_FEEDBACK_CREATED",
            {
                "round": round_context.round_number,
                "periods": list(plan.scope.periods),
                "issueCount": len(result.critique_issues),
                "openIssueCount": sum(
                    issue.resolution_status is CritiqueIssueStatus.OPEN
                    for issue in result.critique_issues
                ),
                "message": "Structured semantic review completed; detailed private reasoning is not emitted.",
            },
        )
        return result


class _ProviderRevisionExecutor:
    """Refresh only claims assigned to critic-selected active specialists."""

    def __init__(
        self,
        *,
        rerun: Callable[[RevisionRequest], tuple[tuple[AtomicClaim, ...], str, tuple[str, ...], dict[str, tuple[str, ...]]]],
        emit: Callable[[str, dict[str, Any]], None],
    ) -> None:
        self.rerun = rerun
        self.emit = emit

    def execute(self, *, request: RevisionRequest) -> RevisionResult:
        target_specialists = tuple(request.target_specialists)
        self.emit(
            "REVISION_REQUESTED",
            {
                "round": request.next_round_number,
                "periods": list(request.plan.scope.periods),
                "targetSpecialists": list(target_specialists),
                "issueCount": len(request.selected_issues),
            },
        )
        self.emit(
            "REVISION_ACTIVITY",
            {"round": request.next_round_number, "periods": list(request.plan.scope.periods), "message": "Applying selected critique feedback to targeted specialist prose and constrained synthesis."},
        )
        revised_claims, revised_summary, revised_support_ids, revised_claim_ids = self.rerun(request)
        synthesis_changed = (
            revised_summary != request.current_synthesis_summary
            or tuple(revised_support_ids) != tuple(request.current_synthesis_supporting_claim_ids)
        )
        worker_versions = {
            specialist: f"{specialist}-grounded-writer-v1-round-{request.next_round_number}"
            for specialist in target_specialists
        }
        version = f"writer-candidate-v1-round-{request.next_round_number}"
        self.emit(
            "REVISION_COMPLETED",
            {
                "round": request.next_round_number,
                "periods": list(request.plan.scope.periods),
                "revisedSpecialists": list(target_specialists),
                "synthesisRevised": synthesis_changed,
            },
        )
        return RevisionResult(
            revised_claims=revised_claims,
            revised_agents=target_specialists,
            revised_claim_ids=revised_claim_ids,
            payload_version=version,
            worker_payload_versions=worker_versions,
            orchestrator_payload_version=f"orchestrator-writer-v1-round-{request.next_round_number}",
            revised_synthesis_summary=revised_summary if synthesis_changed else None,
            revised_synthesis_supporting_claim_ids=tuple(revised_support_ids) if synthesis_changed else None,
        )


def build_openai_semantic_critic(settings: Settings):
    """Build the real provider critic; an absent credential blocks execution."""

    if not settings.openai_api_key or not settings.openai_api_key.strip():
        raise ValueError("semantic_provider_unconfigured")
    config = ProviderExecutionConfig(
        adapter_id="thesis-api-openai-semantic-critic-v1",
        provider_id="openai",
        model_id=settings.openai_model,
        source_policy_id="accepted-provider-primary-stage1-v1",
        environment="provider_backed",
        retrieval_mode="prefetched",
        network_access="enabled",
        api_key_env_var="OPENAI_API_KEY",
        endpoint_env_var="OPENAI_BASE_URL",
    )
    from .llm import get_llm_client

    client = get_llm_client(settings)
    return OpenAISemanticCritic(client=client, config=config)


def build_openai_analysis_writer(settings: Settings):
    """Build the configured presentation-only specialist and synthesis writer."""
    if not settings.openai_api_key or not settings.openai_api_key.strip():
        raise ValueError("analysis_writer_unconfigured")
    from .analysis_writer import OpenAIAnalysisWriter
    from .llm import get_llm_client

    return OpenAIAnalysisWriter(client=get_llm_client(settings), model=settings.openai_model)


def _is_comparison_requested(request: AnalysisRequest) -> bool:
    text = request.query.casefold()
    return bool(request.peer_tickers) or any(term in text for term in _COMPARE_TERMS)


def _has_macro_request(request: AnalysisRequest) -> bool:
    from .service import _MACRO_TERMS

    text = request.query.casefold()
    return any(term in text for term in _MACRO_TERMS)


def _check_single_period(request: AnalysisRequest) -> None:
    quarters = {f"{year}_Q{quarter}" for year, quarter in _QUARTER_RE.findall(request.query)}
    if (
        len(quarters) > 1
        or _COMPACT_QUARTER_RANGE_RE.search(request.query)
        or _PERIOD_RANGE_RE.search(request.query)
        or _YEAR_QUARTER_RANGE_RE.search(request.query)
    ):
        raise ValueError("multi_period_unsupported: the public request contract supports one exact period per run")


def _quarter_ordinal(year: int, quarter: int) -> int:
    return year * 4 + quarter - 1


def _ordinal_quarter(ordinal: int) -> str:
    year, quarter_index = divmod(ordinal, 4)
    return f"{year}_Q{quarter_index + 1}"


def _expand_quarter_range(start_year: str, start_quarter: str, end_year: str | None, end_quarter: str) -> tuple[str, ...]:
    first = _quarter_ordinal(int(start_year), int(start_quarter))
    last = _quarter_ordinal(int(end_year or start_year), int(end_quarter))
    if last < first:
        raise ValueError("query_period_range_descending: query period range is descending")
    return tuple(_ordinal_quarter(item) for item in range(first, last + 1))


def _query_declared_periods(query: str) -> tuple[tuple[str, ...], bool]:
    """Extract explicit canonical quarter scope and the supported range forms."""

    range_match = _COMPACT_QUARTER_RANGE_RE.search(query)
    if range_match:
        declared = _expand_quarter_range(*range_match.groups()[:2], None, range_match.group(3))
        return declared, True
    range_match = _FULL_QUARTER_RANGE_RE.search(query) or _BETWEEN_QUARTER_RANGE_RE.search(query)
    if range_match:
        declared = _expand_quarter_range(*range_match.groups())
        return declared, True
    fiscal_range = _FY_RANGE_RE.search(query)
    if fiscal_range:
        first, last = (int(item) for item in fiscal_range.groups())
        if last < first:
            raise ValueError("query_period_range_descending: query period range is descending")
        return tuple(f"FY{year}" for year in range(first, last + 1)), True

    declared_matches = [
        (match.start(), f"{year}_Q{quarter}")
        for match in _QUARTER_RE.finditer(query)
        for year, quarter in (match.groups(),)
    ]
    declared_matches.extend(
        (match.start(), f"FY{year}")
        for match in _FY_PERIOD_RE.finditer(query)
        for year in (match.group(1),)
    )
    normalized = tuple(dict.fromkeys(period for _position, period in sorted(declared_matches)))
    if _PERIOD_RANGE_RE.search(query) or _YEAR_QUARTER_RANGE_RE.search(query):
        raise ValueError("query_period_range_unsupported: provide an explicit canonical period list for this range")
    return normalized, False


def _resolve_periods(request: AnalysisRequest, catalog: DatasetCapabilityCatalog) -> tuple[str, ...]:
    period_ids = tuple(item.period_id for item in catalog.periods)
    catalog_periods = {item.casefold(): item for item in period_ids}
    try:
        query_periods, query_has_range = _query_declared_periods(request.query)
    except ValueError as exc:
        code, _, detail = str(exc).partition(": ")
        from .service import AnalysisBlocked

        raise AnalysisBlocked(code, detail or str(exc)) from exc

    if (query_has_range or len(query_periods) > 1) and not request._periods_explicit:
        from .service import AnalysisBlocked

        raise AnalysisBlocked(
            "explicit_periods_required",
            "A multi-period question requires an explicit ordered periods list.",
        )

    supplied = tuple(request.periods or ())
    if not supplied:
        if query_has_range or len(query_periods) > 1:
            from .service import AnalysisBlocked

            raise AnalysisBlocked(
                "explicit_periods_required",
                "A multi-period question requires an explicit ordered periods list.",
            )
        if len(query_periods) == 1:
            supplied = query_periods
        elif request.period:
            supplied = (request.period,)
        else:
            from .service import AnalysisBlocked

            raise AnalysisBlocked(
                "exact_period_required",
                "Provide one exact snapshot period or an explicit ordered periods list.",
            )

    resolved: list[str] = []
    for requested in supplied:
        exact = catalog_periods.get(requested.casefold())
        if exact is None:
            from .service import AnalysisBlocked

            raise AnalysisBlocked(
                "unsupported_period",
                f"Period {requested} is not an exact period in the accepted snapshot.",
            )
        if not re.fullmatch(r"\d{4}_Q[1-4]|FY\d{4}", exact, re.I):
            from .service import AnalysisBlocked

            raise AnalysisBlocked(
                "unsupported_period_contract",
                f"Period {exact} is discoverable but is not supported by the current Stage-1 claim contract.",
            )
        resolved.append(exact)

    periods = tuple(resolved)
    if len(periods) > 4:
        from .service import AnalysisBlocked

        raise AnalysisBlocked("period_budget_exceeded", "Company trend requests support at most four periods.")
    if request.period is not None and request.period.casefold() != periods[-1].casefold():
        from .service import AnalysisBlocked

        raise AnalysisBlocked("period_anchor_mismatch", "The legacy period must equal the final period in the explicit list.")
    if query_periods and tuple(item.casefold() for item in query_periods) != tuple(item.casefold() for item in periods):
        from .service import AnalysisBlocked

        raise AnalysisBlocked(
            "query_period_scope_mismatch",
            "The explicit period list must exactly match every period or expanded range stated in the query.",
        )
    return periods


def _plan_request(
    request: AnalysisRequest,
    dataset_ref: DatasetRef,
    catalog: DatasetCapabilityCatalog,
) -> tuple[AnalysisPlan, str | None, tuple[str, ...], tuple[str, ...], tuple[str, ...], tuple[str, ...]]:
    """Capability-validate and freeze the complete ordered plan."""

    from .service import (
        AnalysisBlocked,
        _catalog_entity_matches,
        _normalized,
        _requested_metrics,
        _resolve_target,
        _provider_macro_available,
    )

    macro_requested = _has_macro_request(request)
    comparison_requested = _is_comparison_requested(request)
    try:
        declared_periods, query_has_range = _query_declared_periods(request.query)
    except ValueError:
        # Let _resolve_periods report the detailed Company range error below;
        # comparison/macro requests still need to stop before specialist work.
        declared_periods = ()
        query_has_range = bool(_PERIOD_RANGE_RE.search(request.query) or _YEAR_QUARTER_RANGE_RE.search(request.query))
    multi_period_requested = (
        len(request.periods or ()) > 1
        or query_has_range
        or len(declared_periods) > 1
    )
    if multi_period_requested and macro_requested:
        raise AnalysisBlocked("unsupported_multi_period_macro_scope", "Multi-period macro analysis is outside the supported Company trend scope.")
    if multi_period_requested and comparison_requested:
        raise AnalysisBlocked("multi_period_unsupported", "Multi-period analysis is supported only for one Company target.")
    periods = _resolve_periods(request, catalog)
    period = periods[-1]
    multi_period = len(periods) > 1
    company_entities = {
        entity.entity_id for entity in catalog.entities if entity.entity_type.value == "company"
    }
    target: str | None
    if request.target_ticker:
        target = _resolve_target(request, catalog)
    elif _catalog_entity_matches(request.query, catalog):
        matches = _catalog_entity_matches(request.query, catalog)
        explicit_peers = {item.strip().upper() for item in request.peer_tickers if item.strip()}
        candidate_targets = [item for item in matches if item.upper() not in explicit_peers]
        if len(candidate_targets) == 1:
            target = candidate_targets[0]
        elif len(matches) == 1:
            target = matches[0]
        else:
            raise AnalysisBlocked("target_entity_ambiguous", "Provide one explicit target ticker for a multi-company request.")
    elif not _has_macro_request(request):
        target = _resolve_target(request, catalog)
    else:
        target = None

    if macro_requested and not _provider_macro_available(catalog):
        raise AnalysisBlocked(
            "unsupported_macro_scope",
            "The accepted snapshot does not declare the requested macro observation capability.",
        )
    if target is None and not macro_requested:
        raise AnalysisBlocked("target_entity_required", "Provide one accepted company or an explicit supported macro request.")
    if multi_period and target is not None:
        extra_entities = [item for item in _catalog_entity_matches(request.query, catalog) if item != target]
        if extra_entities:
            raise AnalysisBlocked("unsupported_multi_period_entity_scope", "A Company trend request must resolve to exactly one target entity.")

    company_metric_ids = _requested_metrics(request, catalog) if target else ()
    macro_metric_rows = tuple(
        metric for metric in catalog.metrics if metric.analytical_level is AnalyticalLevel.MACRO
    ) if macro_requested else ()
    if macro_requested and not macro_metric_rows:
        raise AnalysisBlocked("macro_metrics_unavailable", "No accepted macro indicators are declared by the snapshot.")
    macro_metric_ids = tuple(item.metric_id for item in macro_metric_rows)

    peer_universe_id: str | None = None
    peer_ids: tuple[str, ...] = ()
    if _is_comparison_requested(request):
        if target is None:
            raise AnalysisBlocked("comparison_target_required", "A peer comparison requires one accepted target company.")
        if SupportedOperation.GET_PEER_BENCHMARK not in catalog.supported_operations:
            raise AnalysisBlocked("peer_benchmark_unavailable", "The accepted provider does not expose peer benchmark retrieval.")
        explicit_peer_ids = tuple(item.strip().upper() for item in request.peer_tickers if item.strip())
        explicit_peer_ids = tuple(dict.fromkeys(explicit_peer_ids))
        mentioned = tuple(item for item in _catalog_entity_matches(request.query, catalog) if item != target)
        requested_peer_ids = explicit_peer_ids or mentioned
        if target in requested_peer_ids:
            requested_peer_ids = tuple(item for item in requested_peer_ids if item != target)
        if requested_peer_ids and not set(requested_peer_ids).issubset(company_entities):
            raise AnalysisBlocked("unsupported_peer_entity", "One or more requested peers are not present in the accepted snapshot.")
        if not requested_peer_ids:
            target_universes = [
                universe for universe in catalog.peer_universes if target in universe.entity_ids
            ]
            if len(target_universes) == 1:
                selected_universe = target_universes[0]
            elif len(catalog.peer_universes) == 1:
                selected_universe = catalog.peer_universes[0]
            else:
                raise AnalysisBlocked("peer_universe_ambiguous", "Provide peer tickers or configure one unambiguous catalog peer universe.")
            requested_peer_ids = tuple(item for item in selected_universe.entity_ids if item != target)
            candidates = [selected_universe]
        else:
            candidates = [
                universe for universe in catalog.peer_universes
                if set(requested_peer_ids).issubset(universe.entity_ids)
            ]
        if len(candidates) != 1:
            raise AnalysisBlocked("peer_universe_ambiguous", "Requested peers do not resolve to exactly one accepted peer universe.")
        universe = candidates[0]
        try:
            peer_ids = universe.effective_entity_ids(requested_peer_ids)
        except ValueError as exc:
            raise AnalysisBlocked("unsupported_peer_scope", "Requested peers fall outside the accepted peer universe.") from exc
        if not peer_ids:
            raise AnalysisBlocked("empty_peer_scope", "A peer comparison requires at least one peer entity.")
        peer_universe_id = universe.peer_universe_id

    entities: list[str] = []
    if macro_requested:
        entities.append("VN")
    if target:
        entities.append(target)
    entities.extend(peer_ids)
    if peer_universe_id:
        entities.append(peer_universe_id)
    entities = list(dict.fromkeys(entities))

    requirements: list[AnalysisRequirement] = []
    for metric_id in company_metric_ids:
        for cell_period in periods:
            requirements.append(
                AnalysisRequirement(
                    requirement_id=f"company:{target}:{cell_period}:{metric_id}",
                    requirement_type=RequirementType.FACTUAL_OBSERVATION,
                    description=f"Report the accepted {metric_id} observation for {target} at {cell_period}.",
                    required_agents=(AnalysisAgent.COMPANY,),
                    entities=(target,), periods=(cell_period,), metric_ids=(metric_id,),
                    inference_ceiling=InferenceCeiling.OBSERVATION_ONLY,
                    fulfillment_policy=FulfillmentPolicy.VALUE_OR_ACCEPTED_MISSINGNESS,
                    missing_data_policy=MissingDataPolicy.ACCEPTED_MISSINGNESS,
                )
            )
        if multi_period:
            requirements.append(
                AnalysisRequirement(
                    requirement_id=f"company-trend:{target}:{metric_id}",
                    requirement_type=RequirementType.TREND,
                    description=f"Summarize the grounded direction of {metric_id} across the frozen period scope.",
                    required_agents=(AnalysisAgent.COMPANY,),
                    entities=(target,), periods=periods, metric_ids=(metric_id,),
                    inference_ceiling=InferenceCeiling.TREND_ALLOWED,
                    fulfillment_policy=FulfillmentPolicy.VALID_VALUE_REQUIRED,
                    missing_data_policy=MissingDataPolicy.REJECT_MISSING,
                )
            )
    if peer_universe_id:
        for peer in peer_ids:
            for metric_id in company_metric_ids:
                requirements.append(
                    AnalysisRequirement(
                        requirement_id=f"peer-input:{peer}:{period}:{metric_id}",
                        requirement_type=RequirementType.FACTUAL_OBSERVATION,
                        description=f"Verify the accepted {metric_id} peer input for {peer} at {period}.",
                        required_agents=(AnalysisAgent.SECTOR,),
                        entities=(peer,), periods=periods, metric_ids=(metric_id,),
                        inference_ceiling=InferenceCeiling.OBSERVATION_ONLY,
                        fulfillment_policy=FulfillmentPolicy.VALUE_OR_ACCEPTED_MISSINGNESS,
                        missing_data_policy=MissingDataPolicy.ACCEPTED_MISSINGNESS,
                    )
                )
        for metric_id in company_metric_ids:
            requirements.append(
                AnalysisRequirement(
                    requirement_id=f"peer-median:{peer_universe_id}:{period}:{metric_id}",
                    requirement_type=RequirementType.COMPARISON,
                    description=f"Report the provider-derived peer median for {metric_id} at {period}.",
                    required_agents=(AnalysisAgent.SECTOR,),
                    entities=(peer_universe_id,), periods=periods, metric_ids=(metric_id,),
                    inference_ceiling=InferenceCeiling.COMPARISON_ALLOWED,
                    fulfillment_policy=FulfillmentPolicy.VALID_VALUE_REQUIRED,
                    missing_data_policy=MissingDataPolicy.REJECT_MISSING,
                )
            )
    for metric_id in macro_metric_ids:
        requirements.append(
            AnalysisRequirement(
                requirement_id=f"macro:{period}:{metric_id}",
                requirement_type=RequirementType.FACTUAL_OBSERVATION,
                description=f"Report accepted macro indicator {metric_id} at {period}.",
                required_agents=(AnalysisAgent.MACRO,), entities=("VN",), periods=periods,
                metric_ids=(metric_id,), inference_ceiling=InferenceCeiling.OBSERVATION_ONLY,
                fulfillment_policy=FulfillmentPolicy.VALUE_OR_ACCEPTED_MISSINGNESS,
                missing_data_policy=MissingDataPolicy.ACCEPTED_MISSINGNESS,
            )
        )
    if target is None and not requirements:
        raise AnalysisBlocked("analysis_scope_empty", "The validated request contains no executable observation requirements.")

    company_ids = (target,) if target else ()
    plan_metrics = tuple(company_metric_ids) + tuple(macro_metric_ids)
    links: list[ApplicableLink] = []
    if peer_universe_id and target:
        for index, metric_id in enumerate(company_metric_ids, start=1):
            links.append(
                ApplicableLink(
                    link_id=f"peer-link:{index}:{metric_id}",
                    link_type=ApplicableLinkType.COMPANY_TO_PEER_BENCHMARK,
                    source_level=LinkLevel.COMPANY,
                    target_level=LinkLevel.PEER_BENCHMARK,
                    source_entities=(target,), target_entities=(peer_universe_id,),
                    source_periods=periods, target_periods=periods,
                    source_metric_ids=(metric_id,), target_metric_ids=(metric_id,),
                    description=f"Compare {target} {metric_id} with the accepted {peer_universe_id} median.",
                )
            )
    if macro_metric_ids and target and any(term in _normalized(request.query) for term in _MACRO_LINK_TERMS):
        for index, company_metric in enumerate(company_metric_ids, start=1):
            links.append(
                ApplicableLink(
                    link_id=f"macro-link:{index}:{company_metric}",
                    link_type=ApplicableLinkType.MACRO_TO_COMPANY,
                    source_level=LinkLevel.MACRO,
                    target_level=LinkLevel.COMPANY,
                    source_entities=("VN",), target_entities=(target,),
                    source_periods=periods, target_periods=periods,
                    source_metric_ids=macro_metric_ids, target_metric_ids=(company_metric,),
                    description=f"Assess macro context as association only with {target} {company_metric}.",
                )
            )

    if not plan_metrics:
        raise AnalysisBlocked("analysis_scope_empty", "The validated request contains no accepted metrics.")
    plan = AnalysisPlan(
        plan_version=ANALYSIS_PLAN_VERSION,
        dataset_id=dataset_ref.dataset_id,
        dataset_snapshot_id=dataset_ref.dataset_snapshot_id,
        query_id="query-" + hashlib.sha256(
            f"{dataset_ref.dataset_snapshot_id}\0{_normalized(request.query)}\0{'|'.join(periods)}".encode("utf-8")
        ).hexdigest()[:16],
        normalized_question=_normalized(request.query),
        scope=AnalysisScope(
            entities=tuple(entities), periods=periods,
            company_metric_ids=tuple(company_metric_ids),
            macro_indicator_ids=tuple(macro_metric_ids),
            comparison_universe=(peer_universe_id,) if peer_universe_id else (),
        ),
        requirements=tuple(requirements), applicable_links=tuple(links),
        requested_outputs=("structured_facts", "comparison" if peer_universe_id else "limitations", "evidence_trace"),
        causal_claim_policy=CausalClaimPolicy.ASSOCIATION_ONLY if links else CausalClaimPolicy.NO_CAUSAL_INFERENCE,
    )
    return plan, target, periods, tuple(company_metric_ids), tuple(peer_ids), tuple(macro_metric_ids)


def _explicit_missing_claim(
    observation: CanonicalObservation,
    *,
    display_name: str,
    capability: str,
    macro: bool = False,
) -> AtomicClaim:
    if observation.validation_status is not QualityStatus.MISSING or observation.missing_reason != "DATA_UNAVAILABLE":
        raise ValueError("unsupported_missing_state")
    ref_type = "macro_observation" if macro else "missing_cell"
    ref = ClaimDataRef(
        ref_id=observation.observation_id,
        ref_type=ref_type,
        entity=observation.entity_id,
        period=observation.period_id,
        metric_id=observation.metric_id,
    )
    return AtomicClaim(
        claim_id=f"claim-{observation.observation_id}",
        claim_text=f"The provider records {display_name} for {observation.entity_id} at {observation.period_id} as unavailable.",
        # The accepted missing-cell record itself is the evidence for this
        # disclosure. Requiring a document snippet would invent a second
        # evidence path for an explicitly missing observation.
        critical=False,
        claim_type="missingness", title=f"{observation.entity_id} {display_name} {observation.period_id}",
        interpretation="This is an accepted missing-data state; no value is inferred.",
        limitation="The accepted snapshot does not provide a numeric value for this scope.",
        scope=ClaimScope(entities=(observation.entity_id,), periods=(observation.period_id,), metric_ids=(observation.metric_id,)),
        assertions=(StructuredAssertion(
            assertion_id=f"missing-{observation.observation_id}",
            assertion_type=AssertionType.MISSINGNESS,
            entity=observation.entity_id, period=observation.period_id,
            metric_id=observation.metric_id, operator=AssertionOperator.MISSING,
            data_refs=(ref,),
        ),),
        inference_type=InferenceType.FACT,
        support="partially_supported", origin="deterministic_reference",
    )


def _create_macro_claim(
    provider: FinancialDatasetProvider,
    dataset_ref: DatasetRef,
    *,
    metric: DatasetMetric,
    period: str,
    include_evidence: bool,
) -> ClaimArtifact:
    observation = provider.get_macro_observation(dataset_ref, "VN", period, metric.metric_id)
    if observation is None:
        raise ValueError(f"macro_observation_unavailable:{metric.metric_id}")
    if observation.validation_status is QualityStatus.MISSING:
        claim = _explicit_missing_claim(observation, display_name=metric.display_name, capability="macro", macro=True)
        return ClaimArtifact(claim, observation, (), {}, (), "macro", metric.display_name)
    if observation.validation_status is not QualityStatus.VALID or observation.value is None or not observation.unit:
        raise ValueError(f"macro_observation_unaccepted:{metric.metric_id}")
    from .service import _resolve_primary_lineage, _evidence_has_explicit_observation_link

    primary_observations, claim_sources = _resolve_primary_lineage(
        provider=provider, dataset_ref=dataset_ref, observation=observation,
        ticker="VN", period=period, metric_id=metric.metric_id,
    )
    source_refs = tuple(source.source_ref for source in claim_sources)
    evidence = tuple(
        item for item in provider.get_evidence(dataset_ref, source_refs, entity_id="VN", period_id=period, metric_id=metric.metric_id)
        if include_evidence and item.source_ref in source_refs
        and (item.entity_id in (None, "VN")) and item.period_id == period
        and item.metric_id == metric.metric_id
        and _evidence_has_explicit_observation_link(item, observation_id=observation.observation_id)
    )
    ref = ClaimDataRef(
        ref_id=observation.observation_id,
        ref_type="derived_metric" if observation.derivation_method else "macro_observation",
        entity="VN", period=period, metric_id=metric.metric_id,
    )
    claim = AtomicClaim(
        claim_id=f"claim-{observation.observation_id}",
        claim_text=f"The accepted provider records {metric.display_name}={observation.value} {observation.unit} for Vietnam at {period}.",
        claim_type="numeric", title=f"Vietnam {metric.display_name} {period}",
        interpretation="Provider-backed macro fact; no causal effect is inferred.",
        limitation="A single observation does not establish a time-series relationship.",
        scope=ClaimScope(entities=("VN",), periods=(period,), metric_ids=(metric.metric_id,)),
        assertions=(StructuredAssertion(
            assertion_id=f"assertion-{observation.observation_id}", assertion_type=AssertionType.METRIC_VALUE,
            entity="VN", period=period, metric_id=metric.metric_id,
            asserted_value=observation.value, unit=observation.unit, data_refs=(ref,),
            formula_version=observation.derivation_method,
        ),),
        evidence_refs=tuple(item.evidence_id for item in evidence), source_refs=source_refs,
        inference_type=InferenceType.FACT,
        support="evidence_backed" if evidence else "source_locator_only",
        origin="deterministic_reference",
    )
    return ClaimArtifact(
        claim, observation, primary_observations,
        {source.source_ref: source for source in claim_sources}, evidence, "macro", metric.display_name,
    )


class _AdaptiveRun:
    def __init__(self, *, provider, dataset_ref, catalog, request, settings, critic, writer, emit):
        self.provider = provider
        self.dataset_ref = dataset_ref
        self.catalog = catalog
        self.request = request
        self.settings = settings
        self.critic = critic
        self.writer = writer
        self.emit = emit
        self.metric_by_id = {item.metric_id: item for item in catalog.metrics}
        self.artifacts: dict[str, ClaimArtifact] = {}
        self.benchmark_request_metadata: dict[str, dict[str, Any]] = {}
        self.direct_observations: dict[tuple[str, str, str], CanonicalObservation] = {}
        self._frozen_claims: dict[str, AtomicClaim] = {}
        self._claim_roles: dict[str, str] = {}
        self._revised_claim_ids: set[str] = set()

    @staticmethod
    def _issue_payload(issue) -> dict[str, Any]:
        return issue.model_dump(mode="json")

    @staticmethod
    def _numeric_tokens(value: str) -> set[str]:
        tokens: set[str] = set()
        for token in re.findall(r"(?<![A-Za-z])[+-]?\d+(?:[.,]\d+)?%?", value):
            raw = token.rstrip("%")
            try:
                tokens.add(str(Decimal(raw.replace(",", ".")).normalize()))
            except InvalidOperation:
                tokens.add(raw)
        return tokens

    def _allowed_numbers(self, claims: Sequence[AtomicClaim]) -> set[str]:
        allowed: set[str] = set()
        for claim in claims:
            claim_without_period = _WRITER_PERIOD_LITERAL_RE.sub(" ", claim.claim_text)
            allowed.update(self._numeric_tokens(claim_without_period))
            for assertion in claim.assertions:
                if assertion.asserted_value is not None:
                    allowed.update(self._numeric_tokens(str(assertion.asserted_value)))
        return allowed

    def _validate_writer_prose(self, prose: Any, claim: AtomicClaim) -> str:
        from .service import AnalysisBlocked
        from thesis_data.semantic_critic import numeric_or_period_tokens

        if not isinstance(prose, str):
            raise AnalysisBlocked("analysis_writer_output_invalid", "The presentation writer returned malformed prose.")
        clean = prose.strip()
        if len(clean) < 20 or len(clean) > 2000:
            raise AnalysisBlocked("analysis_writer_output_invalid", "The presentation writer returned prose outside the allowed length.")
        if _WRITER_PERIOD_LITERAL_RE.search(clean) or _WRITER_PERIOD_WORD_RE.search(clean):
            raise AnalysisBlocked("analysis_writer_period_reference_rejected", "The presentation writer may not add or restate period labels.")
        if _WRITER_TEMPORAL_CHANGE_RE.search(clean):
            raise AnalysisBlocked("analysis_writer_unsupported_trend", "A single-period claim cannot carry temporal change language.")
        numeric_or_period = numeric_or_period_tokens(clean)
        if any(not any(character.isdigit() for character in token) for token in numeric_or_period) or _WRITER_NUMERAL_WORD_RE.search(unicodedata.normalize("NFC", clean)):
            raise AnalysisBlocked("analysis_writer_unsupported_number", "The presentation writer may not introduce numeric quantities using number words or unit words.")
        if _WRITER_CAUSAL_RE.search(clean):
            raise AnalysisBlocked("analysis_writer_unsupported_causality", "The presentation writer introduced an unsupported causal claim.")
        if re.search(r"\b(?:claim|obs(?:ervation)?|source|assertion|evidence)[-_](?:[0-9a-f]{8,}|[A-Z0-9]{6,})\b", clean, re.IGNORECASE):
            raise AnalysisBlocked("analysis_writer_provenance_reference_rejected", "The presentation writer may not add provenance identifiers.")
        if re.search(r"https?://|\b(?:page|table|row|source\s+locator)\s*[:#=]", clean, re.IGNORECASE):
            raise AnalysisBlocked("analysis_writer_provenance_reference_rejected", "The presentation writer may not add URLs or source locators.")
        artifact = self.artifacts.get(claim.claim_id)
        allowed_entities = set(claim.scope.entities)
        if artifact is not None:
            allowed_entities.add(artifact.observation.entity_id)
        for entity in self.catalog.entities:
            aliases = {entity.entity_id, entity.display_name}
            if entity.entity_id not in allowed_entities and any(
                alias and re.search(rf"(?<!\w){re.escape(alias)}(?!\w)", clean, re.IGNORECASE)
                for alias in aliases
            ):
                raise AnalysisBlocked("analysis_writer_entity_scope_invalid", "The presentation writer referenced an entity outside this claim's frozen scope.")
        allowed_entity_tokens = {entity_id.upper() for entity_id in allowed_entities}
        allowed_metric_tokens = {
            alias.upper()
            for metric in self.catalog.metrics
            if metric.metric_id in {assertion.metric_id for assertion in claim.assertions}
            for alias in (
                metric.metric_id,
                metric.display_name,
                metric.metric_id.rsplit(".", 1)[-1],
                metric.metric_id.rsplit(".", 1)[-1].split("_", 1)[0],
            )
            if alias
        }
        allowed_metrics = {assertion.metric_id for assertion in claim.assertions}
        for metric in self.catalog.metrics:
            aliases = {
                metric.metric_id,
                metric.display_name,
                metric.metric_id.rsplit(".", 1)[-1],
                metric.metric_id.rsplit(".", 1)[-1].split("_", 1)[0],
            }
            if metric.metric_id not in allowed_metrics and any(
                alias and re.search(rf"(?<!\w){re.escape(alias)}(?!\w)", clean, re.IGNORECASE)
                for alias in aliases
            ):
                raise AnalysisBlocked("analysis_writer_metric_scope_invalid", "The presentation writer referenced a metric outside this claim's support.")
        for token in re.findall(r"\b[A-Z]{3,5}\b", clean):
            if token not in allowed_entity_tokens and token not in allowed_metric_tokens:
                raise AnalysisBlocked("analysis_writer_entity_scope_invalid", "The presentation writer introduced an unplanned ticker or metric token.")
        allowed_numbers = self._allowed_numbers((claim,))
        if not self._numeric_tokens(clean).issubset(allowed_numbers):
            raise AnalysisBlocked("analysis_writer_unsupported_number", "The presentation writer introduced a number absent from accepted claim facts.")
        artifact = self.artifacts.get(claim.claim_id)
        forbidden = {claim.claim_id}
        if artifact is not None:
            forbidden.update((artifact.observation.observation_id, artifact.observation.source_ref))
            forbidden.update(claim.source_refs)
            forbidden.update(claim.evidence_refs)
            forbidden.update(ref.ref_id for assertion in claim.assertions for ref in assertion.data_refs)
            forbidden.update(
                assertion.benchmark_ref.ref_id for assertion in claim.assertions
                if assertion.benchmark_ref is not None
            )
        if any(reference and reference in clean for reference in forbidden):
            raise AnalysisBlocked("analysis_writer_provenance_reference_rejected", "The presentation writer repeated a provenance identifier.")
        return clean

    def _validate_synthesis_prose(self, prose: Any, *, plan: AnalysisPlan) -> str:
        from .service import AnalysisBlocked
        from thesis_data.semantic_critic import numeric_or_period_tokens, validate_synthesis_summary

        if not isinstance(prose, str):
            raise AnalysisBlocked("analysis_synthesis_output_invalid", "The orchestrator writer returned malformed prose.")
        clean = prose.strip()
        if len(clean) < 20 or len(clean) > 2000:
            raise AnalysisBlocked("analysis_synthesis_output_invalid", "The orchestrator writer returned prose outside the allowed length.")
        try:
            validate_synthesis_summary(clean)
        except ValueError as exc:
            raise AnalysisBlocked("analysis_synthesis_fact_reference_rejected", str(exc)) from exc
        if numeric_or_period_tokens(clean) or _WRITER_PERIOD_LITERAL_RE.search(clean) or _WRITER_PERIOD_WORD_RE.search(clean) or _WRITER_NUMERAL_WORD_RE.search(unicodedata.normalize("NFC", clean)):
            raise AnalysisBlocked("analysis_synthesis_fact_reference_rejected", "The synthesis must not introduce numeric or period claims in this runtime slice.")
        multi_period_company = len(plan.scope.periods) > 1 and bool(plan.scope.company_metric_ids)
        if (not multi_period_company and _WRITER_TEMPORAL_CHANGE_RE.search(clean)) or _WRITER_CAUSAL_RE.search(clean):
            raise AnalysisBlocked("analysis_synthesis_fact_reference_rejected", "The synthesis may not introduce temporal or causal claims in this runtime slice.")
        for entity in self.catalog.entities:
            for alias in (entity.entity_id, entity.display_name):
                planned_entity = multi_period_company and entity.entity_id in plan.scope.entities
                if alias and not planned_entity and re.search(rf"(?<!\w){re.escape(alias)}(?!\w)", clean, re.IGNORECASE):
                    raise AnalysisBlocked("analysis_synthesis_fact_reference_rejected", "The report-level synthesis is rendered from accepted specialist prose and cannot introduce entity claims.")
        for metric in self.catalog.metrics:
            for alias in (metric.metric_id, metric.display_name):
                planned_metric = multi_period_company and metric.metric_id in plan.scope.company_metric_ids
                if alias and not planned_metric and re.search(rf"(?<!\w){re.escape(alias)}(?!\w)", clean, re.IGNORECASE):
                    raise AnalysisBlocked("analysis_synthesis_fact_reference_rejected", "The report-level synthesis is rendered from accepted specialist prose and cannot introduce metric claims.")
        if re.search(r"\b(?:claim|obs(?:ervation)?|source|assertion|evidence)[-_](?:[0-9a-f]{8,}|[A-Z0-9]{6,})\b|https?://", clean, re.IGNORECASE):
            raise AnalysisBlocked("analysis_synthesis_fact_reference_rejected", "The synthesis may not introduce source or claim identifiers.")
        return clean

    def _writer_claim_context(self, claim: AtomicClaim) -> dict[str, Any]:
        artifact = self.artifacts.get(claim.claim_id)
        if artifact is None:
            raise ValueError(f"writer_artifact_missing:{claim.claim_id}")
        observation = artifact.observation
        sources = []
        for primary in artifact.primary_observations:
            source = artifact.sources.get(primary.source_ref)
            if source is not None:
                sources.append({
                    "source_ref": source.source_ref,
                    "source_url": source.source_url,
                    "content_hash": source.content_hash,
                    "source_tier": getattr(source, "source_tier", None),
                    "source_locator": getattr(primary, "source_locator", None) or (primary.metadata or {}).get("source_locator"),
                })
        return {
            "claim_id": claim.claim_id,
            "capability": artifact.capability,
            "display_name": artifact.display_name,
            "claim": claim.model_dump(mode="json"),
            "accepted_observation": {
                "observation_id": observation.observation_id,
                "entity_id": observation.entity_id,
                "metric_id": observation.metric_id,
                "period_id": observation.period_id,
                "value": observation.value,
                "unit": observation.unit,
                "period_basis": observation.period_basis,
                "reporting_scope": observation.reporting_scope,
                "validation_status": observation.validation_status.value,
                "missing_reason": observation.missing_reason,
                "input_observation_ids": list(observation.input_observation_ids),
            },
            "primary_sources": sources,
        }

    def _invoke_specialist_writer(self, plan, role: str, claims: Sequence[AtomicClaim], issues=()) -> tuple[AtomicClaim, ...]:
        from .service import AnalysisBlocked

        if not claims:
            raise AnalysisBlocked("analysis_writer_target_empty", f"No grounded claims are available for the {role} writer.")
        payload = self.writer.write_specialist(
            plan=plan.model_dump(mode="json"),
            role=role,
            claims=[self._writer_claim_context(claim) for claim in claims],
            issues=[self._issue_payload(issue) for issue in issues],
        )
        if not isinstance(payload, dict) or set(payload) != {claim.claim_id for claim in claims}:
            raise AnalysisBlocked("analysis_writer_claim_set_invalid", "The specialist writer did not return exactly the targeted claim IDs.")
        output = []
        for claim in claims:
            item = payload[claim.claim_id]
            if (
                not isinstance(item, dict)
                or set(item) != {"prose", "supporting_claim_ids"}
                or item.get("supporting_claim_ids") != [claim.claim_id]
            ):
                raise AnalysisBlocked("analysis_writer_support_invalid", "Each specialist prose point must cite exactly its own frozen claim ID.")
            prose = self._validate_writer_prose(item["prose"], claim)
            output.append(claim.model_copy(update={"claim_text": prose}, deep=True))
        return tuple(output)

    def _specialist_outputs(self, claims: Sequence[AtomicClaim], plan: AnalysisPlan) -> dict[str, list[dict[str, Any]]]:
        outputs: dict[str, list[dict[str, Any]]] = {}
        for claim in claims:
            role = self._claim_roles.get(claim.claim_id)
            if role is None:
                artifact = self.artifacts.get(claim.claim_id)
                role = artifact.capability if artifact else ""
            item: dict[str, Any] = {"claim_id": claim.claim_id, "prose": claim.claim_text}
            artifact = self.artifacts.get(claim.claim_id)
            if artifact is not None and len(plan.scope.periods) > 1 and role == "company":
                observation = artifact.observation
                item["accepted_observation"] = {
                    "entity_id": observation.entity_id,
                    "metric_id": observation.metric_id,
                    "period_id": observation.period_id,
                    "value": observation.value,
                    "unit": observation.unit,
                    "validation_status": observation.validation_status.value,
                    "missing_reason": observation.missing_reason,
                }
            outputs.setdefault(role, []).append(item)
        return outputs

    def _write_synthesis(self, plan, claims: Sequence[AtomicClaim], issues=()) -> tuple[str, list[str]]:
        from .service import AnalysisBlocked

        output = self.writer.synthesize(
            plan=plan.model_dump(mode="json"),
            specialist_outputs=self._specialist_outputs(claims, plan),
            issues=[self._issue_payload(issue) for issue in issues],
        )
        expected_claim_ids = [claim.claim_id for claim in claims]
        if (
            not isinstance(output, dict)
            or set(output) != {"summary", "supporting_claim_ids"}
            or output.get("supporting_claim_ids") != expected_claim_ids
            or len(set(output.get("supporting_claim_ids", ()))) != len(expected_claim_ids)
        ):
            raise AnalysisBlocked("analysis_synthesis_support_invalid", "Synthesis must identify every and only final claim in stable candidate order.")
        return self._validate_synthesis_prose(output["summary"], plan=plan), expected_claim_ids

    def execute(self) -> AnalysisResponse:
        from .service import AnalysisBlocked, _requested_metrics

        plan, target, periods, company_metrics, peers, macro_metrics = _plan_request(
            self.request, self.dataset_ref, self.catalog
        )
        period = periods[-1]
        operations = set(self.catalog.supported_operations)
        required_ops = {SupportedOperation.GET_METRIC, SupportedOperation.RESOLVE_OBSERVATION, SupportedOperation.GET_SOURCE}
        if company_metrics and not required_ops.issubset(operations):
            raise AnalysisBlocked("company_provenance_capability_unavailable", "The accepted provider cannot resolve company observations and primary sources.")
        if peers and SupportedOperation.GET_PEER_BENCHMARK not in operations:
            raise AnalysisBlocked("peer_benchmark_unavailable", "The accepted provider cannot resolve peer benchmarks.")

        # Plan and capability validation are complete before any role retrieves observations.
        self.emit("PLAN_CREATED", {
            "requiredSpecialists": self._active_roles(plan),
            "period": period,
            "periods": list(periods),
            "planSummary": "Frozen provider-bound plan with exact ordered period scope and accepted snapshot identity.",
            "message": f"Bound to accepted snapshot {self.dataset_ref.dataset_snapshot_id}.",
        })
        company_role_claims: list[AtomicClaim] = []
        peer_role_claims: list[AtomicClaim] = []
        macro_role_claims: list[AtomicClaim] = []

        if target and company_metrics:
            self._role_started("company", target, period, periods)
            for company_period in periods:
                company_role_claims.extend(self._fetch_direct("company", (target,), company_metrics, company_period))
        if peers:
            self._role_started("sector", self._peer_universe_id(plan), period, periods)
            peer_role_claims.extend(self._fetch_direct("sector", peers, company_metrics, period))
            peer_role_claims.extend(self._fetch_benchmarks(target, peers, company_metrics, period, plan))
        if macro_metrics:
            self._role_started("macro", "VN", period, periods)
            for metric_id in macro_metrics:
                artifact = _create_macro_claim(
                    self.provider, self.dataset_ref, metric=self.metric_by_id[metric_id],
                    period=period, include_evidence=SupportedOperation.GET_EVIDENCE in operations,
                )
                self.artifacts[artifact.claim.claim_id] = artifact
                macro_role_claims.append(artifact.claim)

        raw_role_claims = {
            "company": company_role_claims,
            "sector": peer_role_claims,
            "macro": macro_role_claims,
        }
        self._frozen_claims = {
            claim.claim_id: claim.model_copy(deep=True)
            for claims in raw_role_claims.values() for claim in claims
        }
        if len(self._frozen_claims) != sum(len(items) for items in raw_role_claims.values()):
            raise AnalysisBlocked("provider_claim_identity_duplicate", "The frozen plan produced duplicate claim IDs.")
        for role, claims in raw_role_claims.items():
            if not claims:
                continue
            self._claim_roles.update({claim.claim_id: role for claim in claims})
            written = self._invoke_specialist_writer(plan, role, claims)
            raw_role_claims[role] = list(written)
            self._role_completed(role, len(written), periods)

        initial_claims = tuple(
            raw_role_claims[role][index]
            for role in ("company", "sector", "macro")
            for index in range(len(raw_role_claims[role]))
        )
        if not initial_claims:
            raise AnalysisBlocked("no_provider_claims", "No accepted provider-backed specialist claims were produced.")
        self.emit("SYNTHESIS_STARTED", {"periods": list(periods), "message": "The orchestrator is synthesizing grounded specialist prose before acceptance review."})
        synthesis_summary, synthesis_supporting_claim_ids = self._write_synthesis(plan, initial_claims)
        workload = ClaimScope(
            entities=plan.scope.entities, periods=periods,
            metric_ids=plan.scope.metric_ids,
            comparison_universe=self._peer_universe_id(plan) if peers else None,
        )
        resolver = ProviderStage1DatasetResolver(self.provider, self.dataset_ref)
        stage1 = _RuntimeStage1Evaluator(resolver=resolver, workload_scope=workload)
        revision = _ProviderRevisionExecutor(
            rerun=self._targeted_rerun, emit=self.emit,
        )
        self.emit("REVIEW_STARTED", {"stage": "stage1", "periods": list(periods), "message": "Running deterministic provenance, scope, numeric, missingness, and frozen-plan gates."})
        eventing_critic = _EventingCritic(self.critic, self.emit)
        controller = BoundedRevisionController(
            policy=_API_POLICY,
            stage1_evaluator=stage1,
            semantic_critic=eventing_critic,
            revision_executor=revision,
            acceptance_model_version="api-bounded-revision-v1",
        )
        result = controller.run(
            run_id=f"run-{uuid.uuid4().hex}", plan=plan,
            claims=initial_claims, initial_payload_version="provider-candidate-v1",
            dataset_resolver=resolver,
            synthesis_summary=synthesis_summary,
            synthesis_supporting_claim_ids=synthesis_supporting_claim_ids,
        )
        state = result.acceptance_state
        if state.final_decision is AcceptanceDecision.FAIL_ACCEPTANCE:
            self.emit("RUN_BLOCKED", {
                "reason": result.terminal_reason or "fail_acceptance",
                "status": "error",
            })
            if state.rounds and not all(gate.passed for gate in state.rounds[-1].hard_gate_results.values()):
                violations = sorted({
                    item
                    for gate in state.rounds[-1].hard_gate_results.values()
                    for item in gate.violations
                })
                detail = "; ".join(violations) or result.terminal_reason or "Stage-1 rejected the candidate."
            else:
                detail = result.terminal_reason or "The candidate did not satisfy the bounded acceptance policy."
            raise AnalysisBlocked("fail_acceptance", detail)

        report = self._render_report(
            plan, target, peers, company_metrics, macro_metrics, result.final_claims,
            state, eventing_critic.latest_result,
            synthesis_summary=result.final_synthesis_summary,
            synthesis_supporting_claim_ids=result.final_synthesis_supporting_claim_ids,
            revised_claim_ids=self._revised_claim_ids,
            synthesis_revised=result.synthesis_was_revised,
        )
        self.emit("SYNTHESIS_COMPLETED", {"periods": list(periods), "message": "The terminal candidate, provenance joins, and limitations are ready."})
        return report

    def _active_roles(self, plan: AnalysisPlan) -> list[str]:
        roles = {agent.value for req in plan.requirements for agent in req.required_agents if agent is not AnalysisAgent.ORCHESTRATOR}
        return [role for role in ("macro", "sector", "company") if role in roles]

    def _peer_universe_id(self, plan: AnalysisPlan) -> str | None:
        return plan.scope.comparison_universe[0] if plan.scope.comparison_universe else None

    def _role_started(self, role: str, entity: str, period: str, periods: Sequence[str]) -> None:
        frozen_periods = list(periods)
        self.emit("SPECIALIST_INVOKED", {"specialist": role, "scope": entity, "period": period, "periods": frozen_periods})
        self.emit("SPECIALIST_STARTED", {"specialist": role, "period": period, "periods": frozen_periods, "message": f"Retrieving accepted {role} observations for {entity} across {', '.join(frozen_periods)}."})
        self.emit("SPECIALIST_ACTIVITY", {"specialist": role, "activityType": "DATA_RETRIEVAL", "periods": frozen_periods})

    def _role_completed(self, role: str, claims: int, periods: Sequence[str]) -> None:
        self.emit("SPECIALIST_OUTPUT_CREATED", {"specialist": role, "claimCount": claims, "periods": list(periods)})
        self.emit("SPECIALIST_COMPLETED", {"specialist": role, "claimCount": claims, "periods": list(periods)})

    def _fetch_direct(self, role: str, entities: Sequence[str], metric_ids: Sequence[str], period: str) -> list[AtomicClaim]:
        from .service import AnalysisBlocked, _stage1_claim

        artifacts: list[AtomicClaim] = []
        for entity in entities:
            for metric_id in metric_ids:
                metric = self.metric_by_id[metric_id]
                observation = self.provider.get_metric(self.dataset_ref, entity, period, metric_id)
                if observation is None:
                    continue
                self.direct_observations[(entity, period, metric_id)] = observation
                if observation.validation_status is QualityStatus.MISSING:
                    claim = _explicit_missing_claim(observation, display_name=metric.display_name, capability=role)
                    artifact = ClaimArtifact(claim, observation, (), {}, (), role, metric.display_name)
                    self.artifacts[claim.claim_id] = artifact
                    artifacts.append(claim)
                    continue
                if observation.validation_status is not QualityStatus.VALID or observation.value is None or not observation.unit:
                    continue
                if role == "company" and len(self.request.periods or ()) > 1 and not observation.period_basis:
                    raise AnalysisBlocked(
                        "company_trend_period_basis_missing",
                        f"The accepted {metric_id} observation for {entity} at {period} has no source-backed period basis.",
                    )
                claim, observation, primary, sources, evidence = _stage1_claim(
                    provider=self.provider, dataset_ref=self.dataset_ref, ticker=entity,
                    period=period, metric_id=metric_id, display_name=metric.display_name,
                    include_evidence=SupportedOperation.GET_EVIDENCE in self.catalog.supported_operations,
                )
                artifact = ClaimArtifact(
                    claim, observation, primary,
                    {source.source_ref: source for source in sources}, evidence, role,
                    metric.display_name,
                )
                self.artifacts[claim.claim_id] = artifact
                artifacts.append(claim)
        return artifacts

    def _fetch_benchmarks(self, target: str, peers: Sequence[str], metric_ids: Sequence[str], period: str, plan: AnalysisPlan) -> list[AtomicClaim]:
        universe_id = self._peer_universe_id(plan)
        if universe_id is None:
            return []
        result: list[AtomicClaim] = []
        target_observations = {
            self.artifacts[claim_id].observation.metric_id: self.artifacts[claim_id].observation
            for claim_id, artifact in self.artifacts.items()
            if artifact.capability == "company" and artifact.observation.entity_id == target
        }
        for metric_id in metric_ids:
            valid_peers = [
                entity for entity in peers
                if any(
                    artifact.capability == "sector"
                    and artifact.observation.entity_id == entity
                    and artifact.observation.metric_id == metric_id
                    and artifact.observation.validation_status is QualityStatus.VALID
                    and artifact.observation.value is not None
                    for artifact in self.artifacts.values()
                )
            ]
            if not valid_peers:
                continue
            peer_observations = {
                entity: next(
                    artifact.observation for artifact in self.artifacts.values()
                    if artifact.capability == "sector"
                    and artifact.observation.entity_id == entity
                    and artifact.observation.metric_id == metric_id
                    and artifact.observation.validation_status is QualityStatus.VALID
                )
                for entity in valid_peers
            }
            target_observation = target_observations.get(metric_id)
            compared_observations = (
                ((target_observation,) if target_observation is not None else ())
                + tuple(peer_observations.values())
            )
            observed_scopes = {getattr(item, "reporting_scope", None) for item in compared_observations}
            observed_units = {getattr(item, "unit", None) for item in compared_observations}
            observed_bases = {getattr(item, "period_basis", None) for item in compared_observations}
            if (
                not target_observation
                or not getattr(target_observation, "reporting_scope", None)
                or any(not isinstance(scope, str) or not scope.strip() for scope in observed_scopes)
                or None in observed_scopes
                or len(observed_scopes) != 1
            ):
                from .service import AnalysisBlocked
                raise AnalysisBlocked(
                    "peer_reporting_scope_unavailable",
                    f"Peer comparison for {metric_id} requires provider-declared, consistent reporting scope; no scope is inferred.",
                )
            if (
                any(not isinstance(unit, str) or not unit.strip() for unit in observed_units)
                or None in observed_units
                or len(observed_units) != 1
            ):
                from .service import AnalysisBlocked
                raise AnalysisBlocked(
                    "peer_unit_incompatible",
                    f"Peer comparison for {metric_id} requires one provider-declared unit across the target and accepted peers.",
                )
            if (
                any(not isinstance(basis, str) or not basis.strip() for basis in observed_bases)
                or None in observed_bases
                or len(observed_bases) != 1
            ):
                from .service import AnalysisBlocked
                raise AnalysisBlocked(
                    "peer_period_basis_unavailable",
                    f"Peer comparison for {metric_id} requires one non-null provider-declared period basis across the target and accepted peers.",
                )
            benchmark_rows = self.provider.get_peer_benchmark(
                # Request the complete frozen peer set so the provider owns
                # the requested denominator and can report excluded members.
                # The derived observation's input IDs still contain only the
                # accepted rows that actually contributed to its median.
                self.dataset_ref, universe_id, period, (metric_id,), peer_entity_ids=tuple(peers)
            )
            if len(benchmark_rows) != 1:
                from .service import AnalysisBlocked
                raise AnalysisBlocked("peer_benchmark_ambiguous", f"The provider did not return one benchmark for {metric_id}.")
            benchmark = benchmark_rows[0]
            input_ids = tuple(item.observation_id for item in peer_observations.values())
            metadata_ids = tuple(benchmark.input_observation_ids)
            if benchmark.validation_status is not QualityStatus.VALID or benchmark.value is None or not benchmark.unit:
                from .service import AnalysisBlocked
                raise AnalysisBlocked("peer_benchmark_unavailable", f"The provider has no accepted peer median for {metric_id} at {period}.")
            if (
                benchmark.unit not in observed_units
                or benchmark.period_basis not in observed_bases
                or benchmark.reporting_scope not in observed_scopes
            ):
                from .service import AnalysisBlocked
                raise AnalysisBlocked(
                    "peer_benchmark_basis_incompatible",
                    f"The provider benchmark for {metric_id} did not preserve the accepted unit, period basis, and reporting scope.",
                )
            if benchmark.derivation_method != "peer_median_v1" or metadata_ids != input_ids:
                from .service import AnalysisBlocked
                raise AnalysisBlocked("peer_benchmark_provenance_invalid", f"The provider benchmark for {metric_id} did not preserve exact accepted peer input IDs.")
            provider_metadata = dict(benchmark.metadata or {})
            if (
                provider_metadata.get("aggregation_method") != "peer_median_v1"
                or provider_metadata.get("aggregation_version") != "peer_median_v1"
            ):
                from .service import AnalysisBlocked
                raise AnalysisBlocked("peer_benchmark_method_invalid", f"The provider benchmark for {metric_id} does not declare the versioned peer median method.")
            requested_peer_ids = provider_metadata.get("requested_peer_entity_ids")
            if not isinstance(requested_peer_ids, (tuple, list)) or tuple(requested_peer_ids) != tuple(peers):
                from .service import AnalysisBlocked
                raise AnalysisBlocked("peer_benchmark_scope_invalid", f"The provider benchmark for {metric_id} does not preserve the frozen ordered peer set.")
            eligible_peer_ids = provider_metadata.get("eligible_peer_entity_ids")
            if not isinstance(eligible_peer_ids, (tuple, list)) or tuple(eligible_peer_ids) != tuple(valid_peers):
                from .service import AnalysisBlocked
                raise AnalysisBlocked("peer_benchmark_eligible_scope_invalid", f"The provider benchmark for {metric_id} does not preserve the ordered accepted input members.")
            if provider_metadata.get("peer_universe_id") != universe_id:
                from .service import AnalysisBlocked
                raise AnalysisBlocked("peer_benchmark_scope_invalid", f"The provider benchmark for {metric_id} names a different peer universe.")
            aggregation_method = provider_metadata["aggregation_method"]
            requested_denominator = provider_metadata.get("requested_denominator")
            eligible_denominator = provider_metadata.get("eligible_denominator")
            if (
                isinstance(requested_denominator, bool)
                or not isinstance(requested_denominator, int)
                or requested_denominator != len(peers)
                or isinstance(eligible_denominator, bool)
                or not isinstance(eligible_denominator, int)
                or eligible_denominator != len(metadata_ids)
            ):
                from .service import AnalysisBlocked
                raise AnalysisBlocked("peer_benchmark_denominator_invalid", f"The provider benchmark for {metric_id} reported inconsistent requested or eligible denominators.")
            missing_details = provider_metadata.get("missing_members")
            expected_missing_entities = tuple(entity for entity in peers if entity not in valid_peers)
            if (
                not isinstance(missing_details, (list, tuple))
                or tuple(item.get("entity_id") for item in missing_details if isinstance(item, dict)) != expected_missing_entities
                or len(missing_details) != len(expected_missing_entities)
                or any(
                    not isinstance(item, dict)
                    or not isinstance(item.get("reason"), str)
                    or not item["reason"].strip()
                    for item in missing_details
                )
            ):
                from .service import AnalysisBlocked
                raise AnalysisBlocked("peer_benchmark_missingness_invalid", f"The provider benchmark for {metric_id} does not preserve ordered missing-member disclosures.")
            for detail in missing_details:
                missing_observation = self.direct_observations.get(
                    (detail["entity_id"], period, metric_id)
                )
                if missing_observation is None:
                    if detail.get("observation_id") is not None or detail.get("validation_status") is not None:
                        from .service import AnalysisBlocked
                        raise AnalysisBlocked("peer_benchmark_missingness_invalid", f"The provider benchmark for {metric_id} reported an observation for a member with no direct provider observation.")
                elif (
                    detail.get("observation_id") != missing_observation.observation_id
                    or detail.get("validation_status") != missing_observation.validation_status.value
                    or detail.get("reason") != (
                        missing_observation.missing_reason
                        or f"STATUS_{missing_observation.validation_status.value.upper()}"
                    )
                ):
                    from .service import AnalysisBlocked
                    raise AnalysisBlocked("peer_benchmark_missingness_invalid", f"The provider benchmark for {metric_id} does not match the direct missing-member observation.")
            if benchmark.observation_id != peer_benchmark_observation_id(
                self.dataset_ref, universe_id, period, metric_id, tuple(peers)
            ):
                from .service import AnalysisBlocked
                raise AnalysisBlocked("peer_benchmark_identity_invalid", f"The provider benchmark ID for {metric_id} does not match its effective peer scope.")
            data_refs = tuple(
                ClaimDataRef(
                    ref_id=peer_observations[entity].observation_id,
                    ref_type="observation", entity=entity, period=period, metric_id=metric_id,
                )
                for entity in valid_peers
            )
            benchmark_ref = ClaimDataRef(
                ref_id=benchmark.observation_id, ref_type="benchmark", entity=universe_id,
                period=period, metric_id=metric_id,
            )
            missing_members = list(expected_missing_entities)
            limitation = (
                f"Peer median uses {len(valid_peers)} of {len(peers)} requested peer entities; missing members: {', '.join(missing_members)}."
                if missing_members else "All requested peer observations were eligible."
            )
            claim = AtomicClaim(
                claim_id=f"claim-{benchmark.observation_id}",
                claim_text=f"The provider-derived median {metric_id} for {universe_id} is {benchmark.value} {benchmark.unit} at {period}, using {len(valid_peers)} accepted peer observations.",
                claim_type="comparison", title=f"{universe_id} peer median {metric_id} {period}",
                interpretation="Provider-derived peer median; no ranking or causal interpretation is implied.",
                limitation=limitation,
                scope=ClaimScope(entities=tuple(peers), periods=(period,), metric_ids=(metric_id,), comparison_universe=universe_id),
                assertions=(StructuredAssertion(
                    assertion_id=f"assertion-{benchmark.observation_id}",
                    assertion_type=AssertionType.AGGREGATE, entity=universe_id,
                    period=period, metric_id=metric_id, asserted_value=benchmark.value,
                    unit=benchmark.unit, operator=AssertionOperator.EQ,
                    benchmark_ref=benchmark_ref, data_refs=data_refs,
                    formula_version=benchmark.derivation_method,
                ),),
                source_refs=tuple(dict.fromkeys(
                    source_ref for artifact in self.artifacts.values()
                    if artifact.capability == "sector" and artifact.observation.entity_id in valid_peers
                    and artifact.observation.metric_id == metric_id
                    for source_ref in artifact.claim.source_refs
                )),
                inference_type=InferenceType.COMPARISON,
                support="source_locator_only", origin="deterministic_reference",
            )
            input_artifacts = tuple(
                artifact for artifact in self.artifacts.values()
                if artifact.capability == "sector" and artifact.observation.observation_id in metadata_ids
            )
            primary_by_id: dict[str, Any] = {}
            for input_artifact in input_artifacts:
                for primary_observation in input_artifact.primary_observations:
                    primary_by_id.setdefault(primary_observation.observation_id, primary_observation)
            primary = tuple(primary_by_id.values())
            sources = {key: value for artifact in input_artifacts for key, value in artifact.sources.items()}
            artifact = ClaimArtifact(claim, benchmark, primary, sources, (), "sector", self.metric_by_id[metric_id].display_name)
            self.artifacts[claim.claim_id] = artifact
            self.benchmark_request_metadata[benchmark.observation_id] = {
                "peer_universe_id": universe_id,
                "requested_denominator": requested_denominator,
                "eligible_denominator": eligible_denominator,
                "requested_peer_entity_ids": list(requested_peer_ids),
                "eligible_peer_entity_ids": list(eligible_peer_ids),
                "missing_members": list(missing_details),
                "aggregation_method": aggregation_method,
            }
            result.append(claim)
        return result

    def _targeted_rerun(self, request: RevisionRequest) -> tuple[tuple[AtomicClaim, ...], str, tuple[str, ...], dict[str, tuple[str, ...]]]:
        from .service import AnalysisBlocked
        roles = tuple(request.target_specialists)
        current_by_id = {claim.claim_id: claim for claim in request.current_claims}
        if len(current_by_id) != len(request.current_claims):
            raise AnalysisBlocked("revision_candidate_identity_invalid", "The revision candidate contains duplicate claim IDs.")
        requirements = {item.requirement_id: item for item in request.plan.requirements}
        affected_by_role: dict[str, set[str]] = {role: set() for role in roles}
        for issue in request.selected_issues:
            role = issue.affected_agent
            if role == AnalysisAgent.ORCHESTRATOR.value:
                continue
            if role not in affected_by_role:
                raise AnalysisBlocked("revision_target_specialist_invalid", "Critique feedback targets a specialist outside the frozen active set.")
            for claim_id in issue.affected_claim_ids:
                if claim_id not in current_by_id or self._claim_roles.get(claim_id) != role:
                    raise AnalysisBlocked("revision_issue_claim_scope_invalid", "Critique feedback references a claim outside its affected specialist.")
                affected_by_role[role].add(claim_id)
            issue_requirements = [requirements[item] for item in issue.affected_requirement_ids if item in requirements]
            for claim in request.current_claims:
                if self._claim_roles.get(claim.claim_id) != role:
                    continue
                if any(
                    assertion.entity in req.entities
                    and assertion.period in req.periods
                    and assertion.metric_id in req.metric_ids
                    for req in issue_requirements
                    for assertion in claim.assertions
                ):
                    affected_by_role[role].add(claim.claim_id)
            if not affected_by_role[role]:
                raise AnalysisBlocked("revision_issue_target_empty", "Critique feedback does not resolve to a claim in its affected specialist scope.")

        periods = request.plan.scope.periods
        period = periods[-1]
        company_entity_ids = {entity.entity_id for entity in self.catalog.entities if entity.entity_type.value == "company"}
        target = next((entity for entity in request.plan.scope.entities if entity != "VN" and entity not in request.plan.scope.comparison_universe and entity in company_entity_ids), None)
        peer_ids = tuple(entity for entity in request.plan.scope.entities if entity in company_entity_ids and entity != target)
        updated = dict(current_by_id)
        changed_ids: set[str] = set()
        changed_by_role: dict[str, list[str]] = {role: [] for role in roles}

        for role in roles:
            targeted_ids = affected_by_role[role]
            targeted_cells = tuple(dict.fromkeys(
                (assertion.period, assertion.metric_id)
                for claim in request.current_claims
                if claim.claim_id in targeted_ids
                for assertion in claim.assertions
            ))
            targeted_periods = tuple(
                item for item in periods if any(cell_period == item for cell_period, _metric in targeted_cells)
            )
            metric_ids_by_period = {
                item: tuple(dict.fromkeys(metric_id for cell_period, metric_id in targeted_cells if cell_period == item))
                for item in targeted_periods
            }
            if role == "company" and target:
                raw = [
                    claim
                    for item_period in targeted_periods
                    for claim in self._fetch_direct(
                        "company", (target,), metric_ids_by_period[item_period], item_period,
                    )
                ]
            elif role == "sector" and target and peer_ids:
                metric_ids = tuple(dict.fromkeys(metric_id for _item_period, metric_id in targeted_cells))
                raw = self._fetch_direct("sector", peer_ids, metric_ids, period)
                raw.extend(self._fetch_benchmarks(target, peer_ids, metric_ids, period, request.plan))
            elif role == "macro":
                raw = []
                for item_period in targeted_periods:
                    for metric_id in metric_ids_by_period[item_period]:
                        metric = self.metric_by_id[metric_id]
                        artifact = _create_macro_claim(
                            self.provider, self.dataset_ref, metric=metric, period=item_period,
                            include_evidence=SupportedOperation.GET_EVIDENCE in self.catalog.supported_operations,
                        )
                        self.artifacts[artifact.claim.claim_id] = artifact
                        raw.append(artifact.claim)
            else:
                raise AnalysisBlocked("revision_target_scope_invalid", "The targeted specialist has no executable frozen scope.")

            raw_by_id = {claim.claim_id: claim for claim in raw}
            if not targeted_ids.issubset(raw_by_id):
                raise AnalysisBlocked("revision_provider_claim_set_changed", "Targeted provider re-query did not reproduce the frozen claim identities.")
            targeted_raw = [
                raw_by_id[claim_id].model_copy(
                    update={"claim_text": current_by_id[claim_id].claim_text},
                    deep=True,
                )
                for claim_id in current_by_id if claim_id in targeted_ids
            ]
            for claim in targeted_raw:
                frozen = self._frozen_claims.get(claim.claim_id)
                if frozen is None or frozen.model_dump(mode="json", exclude={"claim_text"}) != claim.model_dump(mode="json", exclude={"claim_text"}):
                    raise AnalysisBlocked("revision_provider_facts_changed", "Targeted provider re-query changed frozen factual or provenance fields.")
            role_issues = [issue for issue in request.selected_issues if issue.affected_agent == role]
            revised = self._invoke_specialist_writer(request.plan, role, targeted_raw, role_issues)
            for claim in revised:
                previous = current_by_id[claim.claim_id]
                if claim.claim_text != previous.claim_text:
                    changed_ids.add(claim.claim_id)
                    changed_by_role[role].append(claim.claim_id)
                updated[claim.claim_id] = claim

        candidate_claims = tuple(updated[claim.claim_id] for claim in request.current_claims)
        prior_summary = request.current_synthesis_summary
        prior_support_ids = tuple(request.current_synthesis_supporting_claim_ids)
        revised_summary, revised_support_ids = self._write_synthesis(
            request.plan, candidate_claims, request.selected_issues,
        )
        for issue in request.selected_issues:
            if issue.affected_agent == AnalysisAgent.ORCHESTRATOR.value:
                if revised_summary == prior_summary and tuple(revised_support_ids) == prior_support_ids:
                    raise AnalysisBlocked("revision_no_material_change", "The orchestrator writer did not change synthesis in response to selected feedback.")
                continue
            issue_claim_ids = set(issue.affected_claim_ids)
            for requirement_id in issue.affected_requirement_ids:
                req = requirements.get(requirement_id)
                if req is None:
                    continue
                issue_claim_ids.update(
                    claim.claim_id for claim in request.current_claims
                    if self._claim_roles.get(claim.claim_id) == issue.affected_agent
                    and any(
                        assertion.entity in req.entities and assertion.period in req.periods and assertion.metric_id in req.metric_ids
                        for assertion in claim.assertions
                    )
                )
            if not issue_claim_ids.intersection(changed_ids):
                raise AnalysisBlocked("revision_no_material_change", "The specialist writer did not change an affected claim in response to selected feedback.")

        self._revised_claim_ids.update(changed_ids)
        return (
            candidate_claims,
            revised_summary,
            tuple(revised_support_ids),
            {role: tuple(claim_ids) for role, claim_ids in changed_by_role.items()},
        )

    def _render_report(self, plan, target, peers, company_metrics, macro_metrics, final_claims, state, critic_result, *, synthesis_summary=None, synthesis_supporting_claim_ids=(), synthesis_revised=False, revised_claim_ids=()) -> AnalysisResponse:
        role_by_claim = {claim_id: item.capability for claim_id, item in self.artifacts.items()}
        known_limitations: list[str] = []
        claim_dtos: list[AtomicClaimDTO] = []
        evidence_rows: list[EvidenceTrailDTO] = []
        target_values: dict[str, float | None] = {}
        company_records_by_cell: dict[tuple[str, str], CompanyMetricPeriodRecordDTO] = {}
        sector_values: dict[str, Any] = {}
        benchmark_records: list[PeerBenchmarkRecordDTO] = []
        macro_values: dict[str, Any] = {}
        for claim in final_claims:
            artifact = self.artifacts.get(claim.claim_id)
            if artifact is None:
                raise ValueError(f"final_claim_artifact_missing:{claim.claim_id}")
            observation = artifact.observation
            role = role_by_claim.get(claim.claim_id, artifact.capability)
            is_missing = observation.validation_status is QualityStatus.MISSING or observation.value is None
            dto_observation_id = observation.observation_id
            input_ids = list(observation.input_observation_ids)
            claim_type = "missingness" if is_missing else ("peer_comparison" if role == "sector" and observation.derivation_method else "factual_observation")
            if role == "company" and not is_missing and len(plan.scope.periods) == 1:
                target_values[observation.metric_id.rsplit(".", 1)[-1].casefold()] = observation.value
            if role == "company" and len(plan.scope.periods) > 1:
                key = (observation.metric_id, observation.period_id)
                if is_missing:
                    company_records_by_cell[key] = CompanyMetricPeriodRecordDTO(
                        metric_id=observation.metric_id,
                        period=observation.period_id,
                        validation_status="missing",
                        value=None,
                        unit=None,
                        period_basis=None,
                        reporting_scope=None,
                        scope_status=None,
                        observation_id=None,
                        source_id=None,
                        claim_id=None,
                        missing_reason=observation.missing_reason or "accepted_missingness",
                    )
                else:
                    source_id = next(
                        (
                            primary.source_ref
                            for primary in artifact.primary_observations
                            if getattr(primary, "source_ref", None) in artifact.sources
                        ),
                        next(iter(claim.source_refs), None),
                    )
                    reporting_scope = (observation.reporting_scope or "").strip() or None
                    company_records_by_cell[key] = CompanyMetricPeriodRecordDTO(
                        metric_id=observation.metric_id,
                        period=observation.period_id,
                        validation_status="valid",
                        value=observation.value,
                        unit=observation.unit,
                        period_basis=observation.period_basis,
                        reporting_scope=reporting_scope,
                        scope_status="verified" if reporting_scope else "unavailable",
                        observation_id=observation.observation_id,
                        source_id=source_id,
                        claim_id=claim.claim_id,
                        missing_reason=None,
                    )
            if role == "macro":
                macro_values[observation.metric_id.rsplit(".", 1)[-1]] = observation.value
            if role == "sector" and observation.derivation_method == "peer_median_v1":
                key = f"peer_median_{observation.metric_id.rsplit('.', 1)[-1].casefold()}"
                sector_values[key] = observation.value
                request_metadata = self.benchmark_request_metadata[observation.observation_id]
                requested_denominator = request_metadata["requested_denominator"]
                eligible_denominator = request_metadata["eligible_denominator"]
                missing = request_metadata["missing_members"]
                aggregate_assertions = [item for item in claim.assertions if item.assertion_type is AssertionType.AGGREGATE]
                if (
                    len(aggregate_assertions) != 1
                    or aggregate_assertions[0].benchmark_ref is None
                    or aggregate_assertions[0].benchmark_ref.ref_id != observation.observation_id
                    or tuple(item.ref_id for item in aggregate_assertions[0].data_refs)
                    != tuple(observation.input_observation_ids)
                    or len(observation.input_observation_ids) != eligible_denominator
                ):
                    raise ValueError(f"peer_benchmark_claim_binding_invalid:{observation.observation_id}")
                benchmark_records.append(PeerBenchmarkRecordDTO(
                    metric_id=observation.metric_id,
                    benchmark_observation_id=observation.observation_id,
                    value=float(observation.value),
                    unit=observation.unit,
                    period=observation.period_id,
                    period_basis=observation.period_basis,
                    reporting_scope=observation.reporting_scope,
                    peer_universe_id=request_metadata["peer_universe_id"],
                    requested_peer_entity_ids=list(request_metadata["requested_peer_entity_ids"]),
                    eligible_peer_entity_ids=list(request_metadata["eligible_peer_entity_ids"]),
                    aggregation_method=request_metadata["aggregation_method"],
                    requested_denominator=requested_denominator,
                    eligible_denominator=eligible_denominator,
                    input_observation_ids=list(observation.input_observation_ids),
                    missing_members=list(missing),
                ))
                if missing:
                    known_limitations.append(
                        f"Peer median for {observation.metric_id} uses {eligible_denominator}/{requested_denominator} eligible observations; missingness is disclosed by entity."
                    )
            if is_missing:
                known_limitations.append(claim.limitation)
            elif not claim.evidence_refs:
                known_limitations.append(
                    "Claims without a reviewed metric-specific document snippet rely on the accepted observation's primary source locator and source hash."
                )
            if not (getattr(observation, "reporting_scope", None) or "").strip():
                if role == "company":
                    known_limitations.append(
                        f"Reporting scope is unavailable for {observation.observation_id}; the API does not infer consolidated or parent-only scope."
                    )
            stage2_status = (
                "limited" if state.final_decision is AcceptanceDecision.ACCEPT_WITH_LIMITATIONS
                else "revised" if claim.claim_id in revised_claim_ids
                else "sound"
            )
            claim_dtos.append(AtomicClaimDTO(
                claim_id=claim.claim_id,
                observation_id=dto_observation_id,
                input_observation_ids=input_ids,
                formula_version=observation.derivation_method,
                capability=role,
                ticker=(observation.entity_id if role != "sector" or not observation.derivation_method else None),
                metric=artifact.display_name,
                period=observation.period_id,
                statement=claim.claim_text,
                claim_type=claim_type,
                evidence_refs=list(claim.evidence_refs),
                stage1_status="accepted",
                stage2_critique_status=stage2_status,
            ))
            for primary_observation in artifact.primary_observations:
                source = artifact.sources.get(primary_observation.source_ref)
                if source is None:
                    raise ValueError(f"source_artifact_missing:{primary_observation.observation_id}")
                evidence_rows.append(EvidenceTrailDTO(
                    claim_id=claim.claim_id,
                    observation_id=primary_observation.observation_id,
                    source_id=source.source_ref,
                    source_url=source.source_url,
                    metric=(self.metric_by_id.get(primary_observation.metric_id).display_name if self.metric_by_id.get(primary_observation.metric_id) else primary_observation.metric_id),
                    ticker=primary_observation.entity_id,
                    period=primary_observation.period_id,
                    value=primary_observation.value,
                    source_doc=source.source_url,
                    table_locator=(getattr(primary_observation, "source_locator", None) or (primary_observation.metadata or {}).get("source_locator")),
                    provenance_hash=source.content_hash,
                ))
            for item in artifact.evidence:
                source = artifact.sources[item.source_ref]
                evidence_rows.append(EvidenceTrailDTO(
                    evidence_id=item.evidence_id, claim_id=claim.claim_id,
                    observation_id=observation.observation_id, source_id=source.source_ref,
                    source_url=source.source_url, metric=artifact.display_name,
                    ticker=observation.entity_id, period=observation.period_id,
                    value=observation.value, source_doc=source.source_url,
                    table_locator=item.locator, provenance_hash=source.content_hash,
                ))

        capabilities = self._active_roles(plan)
        links = [
            "peer_comparison" if link.link_type is ApplicableLinkType.COMPANY_TO_PEER_BENCHMARK else "macro_transmission"
            for link in plan.applicable_links
        ]
        plan_limitations = list(dict.fromkeys(known_limitations))
        plan_dto = AnalysisPlanDTO(
            plan_id=f"plan-{hashlib.sha256(plan.query_id.encode()).hexdigest()[:12]}",
            query=self.request.query, target_ticker=target, peer_tickers=list(peers),
            period=plan.scope.periods[-1], periods=list(plan.scope.periods), required_capabilities=capabilities,
            applicable_links=links, dataset_snapshot_id=plan.dataset_snapshot_id,
            rationale="Frozen query-adaptive plan created before provider specialist retrieval.",
            known_limitations=plan_limitations,
            plan_version=plan.plan_version,
            requirements=[item.model_dump(mode="json") for item in plan.requirements],
        )
        if macro_values:
            macro_context = MacroContextDTO(**macro_values)
        else:
            macro_context = None
        if benchmark_records:
            sector_values["benchmarks"] = benchmark_records
            first_record = benchmark_records[0]
            if all(record.peer_universe_id == first_record.peer_universe_id for record in benchmark_records):
                sector_values["peer_universe_id"] = first_record.peer_universe_id
            if all(record.aggregation_method == first_record.aggregation_method for record in benchmark_records):
                sector_values["aggregation_method"] = first_record.aggregation_method
            audit_bundle = (
                "requested_peer_entity_ids", "eligible_peer_entity_ids",
                "requested_denominator", "eligible_denominator", "missing_members",
            )
            if all(
                all(getattr(record, field) == getattr(first_record, field) for field in audit_bundle)
                for record in benchmark_records
            ):
                for field in audit_bundle:
                    sector_values[field] = getattr(first_record, field)
        sector_benchmark = SectorBenchmarkDTO(
            sector="Accepted peer universe",
            **sector_values,
        ) if any(key.startswith("peer_median_") for key in sector_values) else None
        company_insights: list[CompanyInsightDTO] = []
        if target:
            metric_period_records = (
                [
                    company_records_by_cell[(metric_id, period_id)]
                    for period_id in plan.scope.periods
                    for metric_id in company_metrics
                ]
                if len(plan.scope.periods) > 1
                else []
            )
            company_insights.append(CompanyInsightDTO(
                ticker=target,
                **{key: value for key, value in target_values.items() if key in {"roe", "roa", "nim", "npl", "cir", "casa", "car", "ldr", "llr"}},
                assessment=synthesis_summary or "Accepted provider facts are listed in the atomic claims.",
                metric_period_records=metric_period_records,
            ))
        final_round = state.rounds[-1]
        status = "completed" if state.final_decision is AcceptanceDecision.ACCEPT else "accepted_with_limitations"
        round_status = (
            "accepted_with_limitations" if status == "accepted_with_limitations"
            else "revised_and_passed" if synthesis_revised or any(item.revised_agents for item in state.rounds)
            else "passed"
        )
        issue_summaries = [
            f"{issue.issue_id} [{issue.issue_type.value}/{issue.severity.value}/{issue.resolution_status.value}/{issue.required_action.value}]: {issue.description}"
            for issue in final_round.critique_issues
        ]
        revision_summary = BoundedRevisionSummaryDTO(
            rounds_executed=len(state.rounds), max_rounds=_API_POLICY.max_revision_rounds,
            status=round_status,
            reason=(
                "; ".join(issue_summaries)
                if issue_summaries
                else "; ".join(final_round.unresolved_reason_codes)
                if final_round.unresolved_reason_codes
                else "Terminal acceptance decision from the bounded semantic controller."
            ),
            revised_capabilities=sorted({agent for item in state.rounds for agent in item.revised_agents}),
            synthesis_revised=synthesis_revised,
        )
        critique_items = [
            CritiqueItemDTO(
                dimension="cross_level_integration",
                finding=link_result.rationale,
                confidence=link_result.score,
                evidence_ref=(link_result.supporting_claim_ids[0] if link_result.supporting_claim_ids else None),
                link_id=link_result.link_id,
            )
            for link_result in (critic_result.applicable_link_results if critic_result is not None else ())
        ]
        return AnalysisResponse(
            report_id=f"report-{uuid.uuid4().hex}", status=status,
            analysis_plan=plan_dto, macro_context=macro_context,
            sector_benchmark=sector_benchmark, company_insights=company_insights,
            cross_level_critique=critique_items,
            atomic_claims=claim_dtos, evidence_trail=evidence_rows,
            revision_summary=revision_summary,
            limitations=list(dict.fromkeys(plan_limitations)),
            synthesis_summary=synthesis_summary,
            synthesis_supporting_claim_ids=list(synthesis_supporting_claim_ids),
        )


def run_adaptive_analysis(
    *,
    provider,
    dataset_ref: DatasetRef,
    catalog: DatasetCapabilityCatalog,
    request: AnalysisRequest,
    settings: Settings,
    semantic_critic,
    analysis_writer,
    emit: Callable[[str, dict[str, Any]], None] | None = None,
) -> AnalysisResponse:
    """Run a frozen-plan provider execution and bounded acceptance workflow."""

    from .service import AnalysisBlocked, _error_report

    emit_event = emit or (lambda _event, _payload: None)
    try:
        return _AdaptiveRun(
            provider=provider, dataset_ref=dataset_ref, catalog=catalog,
            request=request, settings=settings, critic=semantic_critic,
            writer=analysis_writer,
            emit=emit_event,
        ).execute()
    except AnalysisBlocked as exc:
        return _error_report(exc.code, exc.detail, request)
    except Exception as exc:
        logger.warning("Adaptive runtime failed: %s", type(exc).__name__, exc_info=True)
        return _error_report("adaptive_runtime_failure", "The accepted provider or bounded semantic runtime could not satisfy this request.", request)
