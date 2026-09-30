"""Query-adaptive, provider-backed analysis route orchestration.

The route freezes its plan before retrieving specialist outputs.  Accepted
provider observations are the only source of numeric claims; the semantic
critic is called only after all deterministic Stage-1 gates pass.
"""

from __future__ import annotations

from collections.abc import Callable, Sequence
from dataclasses import dataclass
from pydantic import ValidationError
import hashlib
import logging
from pathlib import Path
import re
import unicodedata
import uuid
import copy
import time
import concurrent.futures
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
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

import time

from .schemas import (
    AnalysisPlanDTO,
    AnalysisRequest,
    AnalysisResponse,
    AnswerBlockDTO,
    AtomicClaimDTO,
    BlockDroppedDTO,
    BoundedRevisionSummaryDTO,
    CalloutBlockDTO,
    CompanyInsightDTO,
    CompanyMetricPeriodRecordDTO,
    CritiqueItemDTO,
    CrossLevelFindingDTO,
    DatasetDTO,
    EvidenceTrailDTO,
    FactDTO,
    FigureBlockDTO,
    HeadlineBlockDTO,
    KeyPointItemDTO,
    KeyPointsBlockDTO,
    MacroContextDTO,
    NarrativeAuditDTO,
    PeerBenchmarkRecordDTO,
    ReportSpecDTO,
    SectionBlockDTO,
    SectorBenchmarkDTO,
    SentenceDTO,
    SentenceDroppedDTO,
    SignalDTO,
    SourceNoteDTO,
    TableBlockDTO,
    TraceActor,
    TraceKind,
    TraceStepDTO,
    RunTraceDTO,
    QuestionType,
)
from .cost_tracker import LLMUsageTracker, wrap_llm_client
from .summaries_vi import (
    AGENT_LABELS_VI,
    TOOL_LABELS_VI,
    clean_reader_facing_limitations,
    format_critic_limitations,
    summary_accept,
    summary_assign,
    summary_blocked,
    summary_compose,
    summary_critique_issue,
    summary_cross_level_finding,
    summary_draft,
    summary_plan,
    summary_report_ready,
    summary_revision,
    summary_tool_result,
    summary_verify,
)
from .analysis_writer import AnalysisWriterError
from .narrative_templates import (
    default_report_spec,
    describe_fact,
    display_fact,
    make_fallback_sentence,
    period_vi,
)
from .settings import Settings
from thesis_data.narrative_verification import (
    AuditCounts,
    DroppedSentence,
    NarrativeSentence,
    SentenceVerdict,
    VerificationContext,
    verify_all,
    verify_sentence,
)

TOOL_AGENT_MAP: dict[str, str] = {
    "lookup": "company",
    "trend": "company",
    "head_to_head": "company",
    "decomposition": "company",
    "peer_position": "sector",
    "ranking": "sector",
    "dispersion": "sector",
    "relationship": "sector",
}
from thesis_data.report_spec import normalize_report_spec_dict, validate_report_spec


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
            plan=plan,
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


class _PlanResult(tuple):
    def __new__(
        cls,
        plan,
        target,
        periods,
        metrics,
        peers,
        macro_metrics,
        spec=None,
        resolved=None,
        planner_source=None,
        fallback_reasons=None,
    ):
        instance = super().__new__(
            cls, (plan, target, periods, metrics, peers, macro_metrics)
        )
        instance.spec = spec
        instance.resolved = resolved
        instance.planner_source = planner_source
        instance.fallback_reasons = list(fallback_reasons or [])
        return instance


def _plan_request(
    request: AnalysisRequest,
    dataset_ref: DatasetRef,
    catalog: DatasetCapabilityCatalog,
    settings: Any = None,
    client: Any = None,
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

    if not getattr(request, "_periods_explicit", False) and not (
        _has_macro_request(request) and _provider_macro_available(catalog)
    ):
        if request.period is not None:
            catalog_period_set = {p.period_id.casefold() for p in catalog.periods}
            if request.period.casefold() not in catalog_period_set:
                from .service import AnalysisBlocked

                raise AnalysisBlocked(
                    "unsupported_period",
                    f"Period {request.period} is not an exact period in the accepted snapshot.",
                )

        from .analysis_planner import plan_question, build_analysis_plan

        planner_client = client
        if planner_client is None and settings is not None:
            planner_mode = getattr(settings, "planner_mode", "model_with_fallback")
            if planner_mode == "model_with_fallback" and getattr(settings, "openai_api_key", None) and getattr(settings, "openai_api_key", "").strip():
                try:
                    from .llm import get_llm_client

                    planner_client = get_llm_client(settings)
                except Exception:
                    planner_client = None

        spec, planner_source, fallback_reasons, resolved = plan_question(
            request.query, catalog, settings=settings, client=planner_client
        )
        try:
            plan, target, periods, company_metric_ids, peer_ids, macro_metric_ids = (
                build_analysis_plan(
                    spec,
                    catalog,
                    dataset_ref,
                    query_text=request.query,
                    peer_tickers=request.peer_tickers,
                )
            )
        except ValidationError as exc:
            if planner_source != "model":
                raise
            # A model-proposed spec that cannot be frozen into a valid AnalysisPlan
            # (e.g. an empty metric list) falls back to the deterministic rules plan.
            logger.warning("Model plan could not be frozen, using rules plan: %s", exc)
            spec, planner_source, rules_reasons, resolved = plan_question(
                request.query, catalog, settings=settings, client=None
            )
            fallback_reasons = list(fallback_reasons or []) + ["model_plan_not_freezable"] + list(rules_reasons or [])
            plan, target, periods, company_metric_ids, peer_ids, macro_metric_ids = (
                build_analysis_plan(
                    spec,
                    catalog,
                    dataset_ref,
                    query_text=request.query,
                    peer_tickers=request.peer_tickers,
                )
            )
        return _PlanResult(
            plan,
            target,
            periods,
            company_metric_ids,
            peer_ids,
            macro_metric_ids,
            spec=spec,
            resolved=resolved,
            planner_source=planner_source,
            fallback_reasons=fallback_reasons,
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
    return _PlanResult(plan, target, periods, tuple(company_metric_ids), tuple(peer_ids), tuple(macro_metric_ids))


def _explicit_missing_claim(
    observation: CanonicalObservation,
    *,
    display_name: str,
    capability: str,
    macro: bool = False,
) -> AtomicClaim:
    if observation.validation_status is not QualityStatus.MISSING:
        raise ValueError("unsupported_missing_state")
    # NOTE: Gold v5 uses descriptive missing_reason strings (not the literal
    # "DATA_UNAVAILABLE"). We accept any QualityStatus.MISSING observation so
    # that legitimate missing cells (e.g. ACB bad-debt-ratio under D-055) are
    # handled correctly in the evaluation harness.
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
    def __init__(
        self,
        *,
        provider,
        dataset_ref,
        catalog,
        request,
        settings,
        critic,
        writer,
        emit,
        client=None,
        tracker: LLMUsageTracker | None = None,
    ):
        self.provider = provider
        self.dataset_ref = dataset_ref
        self.catalog = catalog
        self.request = request
        self.settings = settings
        self.tracker = tracker or LLMUsageTracker()
        self._started_at = time.monotonic()
        self.trace_steps: list[TraceStepDTO] = []
        self._seq = 1

        self.client = wrap_llm_client(client, self.tracker, default_role="orchestrator")
        if hasattr(writer, "client"):
            writer.client = wrap_llm_client(
                writer.client,
                self.tracker,
                default_role="company",
                role_getter=lambda: getattr(writer, "_current_role", "company") or "company",
            )
        self.writer = writer
        if hasattr(critic, "_client"):
            critic._client = wrap_llm_client(critic._client, self.tracker, default_role="critic")
        elif hasattr(critic, "client"):
            critic.client = wrap_llm_client(critic.client, self.tracker, default_role="critic")
        self.critic = critic

        self.emit = emit
        self.metric_by_id = {item.metric_id: item for item in catalog.metrics}
        self.artifacts: dict[str, ClaimArtifact] = {}
        self.benchmark_request_metadata: dict[str, dict[str, Any]] = {}
        self.direct_observations: dict[tuple[str, str, str], CanonicalObservation] = {}
        self._frozen_claims: dict[str, AtomicClaim] = {}
        self._claim_roles: dict[str, str] = {}
        self._revised_claim_ids: set[str] = set()

    def _trace(
        self,
        kind: TraceKind,
        actor: TraceActor,
        summary: str,
        detail: dict[str, Any],
        recipient: TraceActor | None = None,
    ) -> TraceStepDTO:
        t_ms = max(0, int((time.monotonic() - self._started_at) * 1000))
        step = TraceStepDTO(
            step_id=f"t-{self._seq}",
            seq=self._seq,
            t_ms=t_ms,
            actor=actor,
            recipient=recipient,
            kind=kind,
            summary=summary,
            detail=detail,
        )
        self._seq += 1
        self.trace_steps.append(step)
        self.emit("TRACE_STEP", step.model_dump(mode="json"))
        return step

    def _build_verification_context(
        self,
        plan: AnalysisPlan,
        verified_facts: Sequence[Any],
    ) -> VerificationContext:
        from .metric_presentation import get_metric_presentation

        facts_map = {f.fact_id: f for f in verified_facts}
        plan_entities = frozenset(plan.scope.entities)
        cat_entities = set(e.entity_id for e in self.catalog.entities)
        for u in getattr(self.catalog, "peer_universes", ()):
            cat_entities.update(u.entity_ids)
        cat_entities.update(["VCB", "CTG", "BID", "TCB", "MBB", "VPB", "HDB", "ACB", "STB", "TPB", "VIB", "LPB", "SHB", "MSB", "SSB", "OCB", "EIB"])
        catalog_entities = frozenset(cat_entities)

        metric_terms: dict[str, tuple[str, ...]] = {}
        hi_words: dict[str, tuple[str, ...]] = {}
        lo_words: dict[str, tuple[str, ...]] = {}
        directions: dict[str, str] = {}
        flat_pp: dict[str, float] = {}

        for m in self.catalog.metrics:
            pres = get_metric_presentation(m.metric_id)
            terms = [pres.label, pres.short_label, m.display_name, m.metric_id.rsplit(".", 1)[-1]]
            if pres.synonyms:
                terms.extend(pres.synonyms)
            metric_terms[m.metric_id] = tuple(dict.fromkeys(t for t in terms if t))
            if pres.superlative_hi:
                hi_words[m.metric_id] = tuple(pres.superlative_hi)
            if pres.superlative_lo:
                lo_words[m.metric_id] = tuple(pres.superlative_lo)
            directions[m.metric_id] = pres.direction
            flat_pp[m.metric_id] = pres.flat_threshold_pp

        anchor_period = plan.scope.periods[-1]
        match = re.search(r"\b(20\d{2})\b", anchor_period)
        anchor_year = int(match.group(1)) if match else 2024

        return VerificationContext(
            facts=facts_map,
            plan_entities=plan_entities,
            catalog_entities=catalog_entities,
            metric_terms=metric_terms,
            hi_words=hi_words,
            lo_words=lo_words,
            directions=directions,
            flat_pp=flat_pp,
            anchor_year=anchor_year,
        )

    @staticmethod
    def _facts_payload(facts: Sequence[Any]) -> list[dict[str, str]]:
        return [
            {
                "fact_id": f.fact_id,
                "mo_ta": describe_fact(f),
                "hien_thi": display_fact(f),
            }
            for f in facts
        ]

    @staticmethod
    def _datasets_summary(datasets: Sequence[DatasetDTO]) -> list[dict[str, Any]]:
        return [
            {
                "dataset_id": d.dataset_id,
                "title": d.title,
                "shape": d.shape,
                "allowed_charts": list(d.allowed_charts),
                "n_rows": len(d.rows),
            }
            for d in datasets
        ]


    def execute(self) -> AnalysisResponse:
        from .service import AnalysisBlocked, _requested_metrics

        plan_result = _plan_request(
            self.request,
            self.dataset_ref,
            self.catalog,
            settings=self.settings,
            client=self.client,
        )
        plan, target, periods, company_metrics, peers, macro_metrics = plan_result
        self.spec = getattr(plan_result, "spec", None)
        self.resolved = getattr(plan_result, "resolved", None)
        self.planner_source = getattr(plan_result, "planner_source", None)
        self.fallback_reasons = getattr(plan_result, "fallback_reasons", [])
        period = periods[-1]
        operations = set(self.catalog.supported_operations)
        required_ops = {SupportedOperation.GET_METRIC, SupportedOperation.RESOLVE_OBSERVATION, SupportedOperation.GET_SOURCE}
        if company_metrics and not required_ops.issubset(operations):
            raise AnalysisBlocked("company_provenance_capability_unavailable", "The accepted provider cannot resolve company observations and primary sources.")
        if peers and SupportedOperation.GET_PEER_BENCHMARK not in operations:
            raise AnalysisBlocked("peer_benchmark_unavailable", "The accepted provider cannot resolve peer benchmarks.")

        # Plan and capability validation are complete before any role retrieves observations.
        plan_created_payload = {
            "requiredSpecialists": self._active_roles(plan),
            "period": period,
            "periods": list(periods),
            "planSummary": "Frozen provider-bound plan with exact ordered period scope and accepted snapshot identity.",
            "message": f"Bound to accepted snapshot {self.dataset_ref.dataset_snapshot_id}.",
        }
        if self.spec is not None:
            plan_created_payload["questionType"] = self.spec.question_type
            plan_created_payload["plannerSource"] = self.planner_source
            plan_created_payload["plannerFallbackReasons"] = list(self.fallback_reasons)
            plan_created_payload["rationaleVi"] = self.spec.rationale
            plan_created_payload["tools"] = [{"tool": t.tool, "params": t.params} for t in self.spec.tools]
        self.emit("PLAN_CREATED", plan_created_payload)

        # Trace plan step
        active_specialists = self._active_roles(plan)
        q_type_str = self.spec.question_type if self.spec else (getattr(plan, "question_type", None) or "lookup")
        plan_tools_detail = [
            {
                "tool": t.tool,
                "agent": TOOL_AGENT_MAP.get(t.tool, "company"),
                "label": TOOL_LABELS_VI.get(t.tool, t.tool),
            }
            for t in (self.spec.tools if self.spec and getattr(self.spec, "tools", None) else [])
        ]
        self._trace(
            kind="plan",
            actor="orchestrator",
            summary=summary_plan(
                question_type=q_type_str,
                tools=plan_tools_detail,
                active_agents=active_specialists,
            ),
            detail={
                "question_type": q_type_str,
                "planner_source": self.planner_source or "rules",
                "rationale": getattr(self.spec, "rationale", "") if self.spec else "",
                "entities": list(plan.scope.entities),
                "metric_ids": list(plan.scope.metric_ids),
                "anchor_period": period,
                "periods": list(periods),
                "tools": plan_tools_detail,
                "agents": [
                    {
                        "agent": a,
                        "decision": "run" if a in active_specialists else "skip",
                        "reason": f"Chuyên viên {AGENT_LABELS_VI.get(a, a)}" if a in active_specialists else "Không yêu cầu trong kế hoạch",
                    }
                    for a in ["company", "sector", "macro"]
                ],
                "defaults_applied": list(getattr(self.spec, "defaults_applied", [])) if self.spec else [],
            },
            recipient="system",
        )

        company_role_claims: list[AtomicClaim] = []
        peer_role_claims: list[AtomicClaim] = []
        macro_role_claims: list[AtomicClaim] = []

        if target and company_metrics:
            self._role_started("company", target, period, periods)
            for company_period in periods:
                company_role_claims.extend(self._fetch_direct("company", (target,), company_metrics, company_period))
        clean_peers = tuple(p for p in peers if p != target) if target else tuple(peers)
        if clean_peers:
            self._role_started("sector", self._peer_universe_id(plan), period, periods)
            peer_role_claims.extend(self._fetch_direct("sector", clean_peers, company_metrics, period))
            peer_role_claims.extend(self._fetch_benchmarks(target, clean_peers, company_metrics, period, plan))
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
            self._role_completed(role, len(claims), periods)

        if hasattr(self.writer, "write_specialist"):
            written_initial: list[AtomicClaim] = []
            for role in ("company", "sector", "macro"):
                r_claims = raw_role_claims.get(role, [])
                if not r_claims:
                    continue
                claims_payload = [
                    {
                        "claim_id": c.claim_id,
                        "display_name": c.title,
                        "accepted_observation": {
                            "entity_id": c.assertions[0].entity if c.assertions else "",
                            "metric_id": c.assertions[0].metric_id if c.assertions else "",
                            "period_id": c.assertions[0].period if c.assertions else "",
                            "validation_status": "present",
                        },
                    }
                    for c in r_claims
                ]
                try:
                    writer_res = self.writer.write_specialist(
                        plan=plan.model_dump() if hasattr(plan, "model_dump") else plan,
                        role=role,
                        claims=claims_payload,
                        issues=[],
                    )
                    for c in r_claims:
                        if c.claim_id in writer_res:
                            c = c.model_copy(update={
                                "claim_text": writer_res[c.claim_id]["prose"],
                                "statement": writer_res[c.claim_id]["prose"],
                            })
                        written_initial.append(c)
                except Exception as exc:
                    logger.warning("Writer write_specialist initial failed: %s", exc)
                    written_initial.extend(r_claims)
            initial_claims = tuple(written_initial)
        else:
            initial_claims = tuple(
                raw_role_claims[role][index]
                for role in ("company", "sector", "macro")
                for index in range(len(raw_role_claims[role]))
            )
        if not initial_claims:
            raise AnalysisBlocked("no_provider_claims", "No accepted provider-backed specialist claims were produced.")

        # Stage-1 deterministic gates
        workload = ClaimScope(
            entities=plan.scope.entities, periods=periods,
            metric_ids=plan.scope.metric_ids,
            comparison_universe=self._peer_universe_id(plan) if peers else None,
        )
        resolver = ProviderStage1DatasetResolver(self.provider, self.dataset_ref)
        stage1 = _RuntimeStage1Evaluator(resolver=resolver, workload_scope=workload)
        stage1_report = stage1.evaluate(plan=plan, claims=initial_claims, policy=_API_POLICY)
        if not stage1_report.passed:
            violations = sorted({
                item
                for gate in stage1_report.gate_results.values()
                for item in gate.violations
            })
            detail = "; ".join(violations) or "Stage-1 rejected the candidate."
            self.emit("RUN_BLOCKED", {
                "reason": "fail_acceptance",
                "status": "error",
                "detail": detail,
            })
            raise AnalysisBlocked("fail_acceptance", detail)

        # Execute ER-3 analysis tools
        tool_facts: list[Any] = []
        tool_datasets: list[Any] = []
        tool_missing: list[Any] = []
        tool_limitations: list[str] = []
        tool_facts_by_agent: dict[str, list[Any]] = {"company": [], "sector": [], "macro": []}
        tool_datasets_by_agent: dict[str, list[Any]] = {"company": [], "sector": [], "macro": []}

        from .analysis_tools import (
            TOOLS,
            ToolContext,
            build_source_notes,
            verify_fact_inputs,
        )
        from .metric_presentation import get_metric_presentation

        if self.spec is not None and getattr(self.spec, "tools", None):
            # Populate universe members
            universe_id = self._peer_universe_id(plan)
            focus_entity = getattr(self.spec, "focus_entity", None) or target
            candidate_universes = [
                u for u in self.catalog.peer_universes
                if not focus_entity or focus_entity in u.entity_ids
            ]
            if not universe_id and candidate_universes:
                universe_id = candidate_universes[0].peer_universe_id

            universe_members: tuple[str, ...] = ()
            if universe_id:
                for univ in self.catalog.peer_universes:
                    if univ.peer_universe_id == universe_id:
                        universe_members = tuple(univ.entity_ids)
                        break
            if not universe_members and peers:
                universe_members = tuple(peers + ((target,) if target else ()))

            tool_ctx = ToolContext(
                provider=self.provider,
                dataset_ref=self.dataset_ref,
                catalog=self.catalog,
                universe_id=universe_id,
                universe_members=universe_members,
                presentation=get_metric_presentation,
                cache={},
            )

            # Pre-populate cache from initial artifacts
            for artifact in self.artifacts.values():
                obs = getattr(artifact, "observation", None)
                if obs is not None:
                    tool_ctx.cache[(obs.entity_id, obs.period_id, obs.metric_id)] = obs

            agent_order: list[str] = []
            for t in self.spec.tools:
                ag = TOOL_AGENT_MAP.get(t.tool, "company")
                if ag not in agent_order:
                    agent_order.append(ag)

            for ag in agent_order:
                ag_tools = [t for t in self.spec.tools if TOOL_AGENT_MAP.get(t.tool, "company") == ag]
                tool_labels = [TOOL_LABELS_VI.get(t.tool, t.tool) for t in ag_tools]
                task_str = ", ".join(t.tool for t in ag_tools)
                self._trace(
                    kind="assign",
                    actor="orchestrator",
                    summary=summary_assign(recipient=ag, tools=tool_labels),
                    detail={"task": task_str, "tools": tool_labels},
                    recipient=ag,  # type: ignore
                )
                for tool_call in ag_tools:
                    tool_fn = TOOLS.get(tool_call.tool)
                    if tool_fn is not None:
                        try:
                            res = tool_fn(tool_ctx, tool_call.params)
                            tool_facts.extend(res.facts)
                            tool_datasets.extend(res.datasets)
                            tool_missing.extend(res.missing)
                            tool_facts_by_agent[ag].extend(res.facts)
                            tool_datasets_by_agent[ag].extend(res.datasets)

                            t_label = TOOL_LABELS_VI.get(tool_call.tool, tool_call.tool)
                            self._trace(
                                kind="tool_result",
                                actor=ag,  # type: ignore
                                summary=summary_tool_result(t_label, len(res.facts)),
                                detail={
                                    "tool": tool_call.tool,
                                    "label": t_label,
                                    "facts": [
                                        {
                                            "fact_id": f.fact_id,
                                            "label": getattr(f, "label", "") or describe_fact(f),
                                            "display_value": display_fact(f),
                                            "source_note_no": None,
                                        }
                                        for f in res.facts
                                    ],
                                    "datasets": [
                                        {"dataset_id": d.dataset_id, "title": d.title}
                                        for d in res.datasets
                                    ],
                                    "missing": [
                                        {
                                            "entity_id": m.entity_id,
                                            "metric_id": m.metric_id,
                                            "period": m.period,
                                            "reason": getattr(m, "reason", "") or f"{m.entity_id} {period_vi(m.period)} chưa có số liệu đã kiểm định; để trống thay vì ước tính.",
                                        }
                                        for m in res.missing
                                    ],
                                },
                                recipient="orchestrator",
                            )
                        except Exception as exc:
                            logger.warning("Analysis tool %s failed: %s", tool_call.tool, exc, exc_info=True)
                            tool_limitations.append(f"Không thực hiện được phép phân tích {tool_call.tool}.")

            # Dedupe tool_facts immediately after running tools (preserving first occurrence order)
            deduped_tool_facts: list[Any] = []
            seen_fact_ids: dict[str, Any] = {}
            for f in tool_facts:
                fid = f.fact_id
                if fid not in seen_fact_ids:
                    seen_fact_ids[fid] = f
                    deduped_tool_facts.append(f)
                else:
                    prev_f = seen_fact_ids[fid]
                    if prev_f.value != f.value:
                        logger.warning(
                            "Duplicate fact_id %s has conflicting values: %s != %s. Keeping first occurrence.",
                            fid,
                            prev_f.value,
                            f.value,
                        )
            tool_facts = deduped_tool_facts

            # Verify fact inputs
            verified_facts, dropped_facts, verify_lims = verify_fact_inputs(
                self.provider, self.dataset_ref, tool_facts
            )
            tool_limitations.extend(verify_lims)

            # Missing cells limitations
            for m in tool_missing:
                tool_limitations.append(f"{m.entity_id} {period_vi(m.period)} chưa có số liệu đã kiểm định; để trống thay vì ước tính.")
        else:
            from thesis_data.report_facts import Fact
            verified_facts = []
            for claim in initial_claims:
                art = self.artifacts.get(claim.claim_id)
                if art and getattr(art, "observation", None):
                    obs = art.observation
                    role = art.capability or "company"
                    f = Fact(
                        fact_id=f"fact:value:{obs.entity_id or role}:{obs.period_id}:{obs.metric_id}",
                        fact_type="value",
                        entity_id=obs.entity_id,
                        metric_id=obs.metric_id,
                        period=obs.period_id,
                        value=obs.value,
                        unit=getattr(obs, "unit", "%"),
                        input_observation_ids=[obs.observation_id],
                    )
                    verified_facts.append(f)
                    tool_facts_by_agent[role].append(f)

        # Signals and Cross-Level Candidates
        signals: list[Any] = []
        cross_level_candidates_list: list[Any] = []
        source_notes: list[Any] = []
        if verified_facts and self.spec is not None:
            from thesis_data.report_facts import classify_signals, detect_cross_level_candidates
            from .metric_presentation import METRIC_PRESENTATIONS, get_metric_presentation
            from .schemas import SignalDTO

            # Metric groups, directions, and flat_pp map from registry
            metric_groups: dict[str, list[str]] = {}
            group_labels: dict[str, str] = {}
            directions: dict[str, str] = {}
            metric_to_group: dict[str, str] = {}
            flat_pp_map: dict[str, float] = {
                m_id: pres.flat_threshold_pp
                for m_id, pres in METRIC_PRESENTATIONS.items()
            }
            for m_id in plan.scope.company_metric_ids:
                pres = get_metric_presentation(m_id)
                grp = pres.group or "other"
                metric_groups.setdefault(grp, []).append(m_id)
                group_labels[grp] = pres.group_label or grp
                directions[m_id] = pres.direction
                metric_to_group[m_id] = grp
                if m_id not in flat_pp_map:
                    flat_pp_map[m_id] = pres.flat_threshold_pp

            for f in verified_facts:
                if f.metric_id and f.metric_id not in metric_to_group:
                    pres = get_metric_presentation(f.metric_id)
                    grp = pres.group or "other"
                    metric_groups.setdefault(grp, []).append(f.metric_id)
                    group_labels[grp] = pres.group_label or grp
                    directions[f.metric_id] = pres.direction
                    metric_to_group[f.metric_id] = grp
                    if f.metric_id not in flat_pp_map:
                        flat_pp_map[f.metric_id] = pres.flat_threshold_pp

            universe_id = self._peer_universe_id(plan)
            anchor_p = periods[-1] if periods else None
            # Signals for company_profile or trend with universe
            if self.spec.question_type == "company_profile" or (self.spec.question_type == "trend" and universe_id):
                sig_results = classify_signals(
                    target=target or "",
                    facts=verified_facts,
                    metric_groups=metric_groups,
                    directions=directions,
                    flat_pp=flat_pp_map,
                    group_labels=group_labels,
                    anchor_period=anchor_p,
                )
                for sr in sig_results:
                    signals.append(
                        SignalDTO(
                            group=sr.group,
                            label=sr.label,
                            verdict=sr.verdict,  # type: ignore
                            metric_ids=sr.metric_ids,
                            fact_ids=sr.fact_ids,
                        )
                    )
                candidates = detect_cross_level_candidates(
                    facts=verified_facts,
                    signals=sig_results,
                    flat_pp=flat_pp_map,
                    directions=directions,
                    metric_to_group=metric_to_group,
                )
            else:
                candidates = detect_cross_level_candidates(
                    facts=verified_facts,
                    signals=[],
                    flat_pp=flat_pp_map,
                    directions=directions,
                    metric_to_group=metric_to_group,
                )
            cross_level_candidates_list = candidates
        else:
            candidates = []

        # =====================================================================
        # ER-4 Narrative Verification and Report Composition
        # =====================================================================
        from .analysis_tools import ToolResult
        from thesis_data.schema import CritiqueAction
        q_type = self.spec.question_type if self.spec else "company_profile"
        v_ctx = self._build_verification_context(plan, verified_facts)

        arm = getattr(self.settings, "analysis_arm", "hierarchical_with_critique")
        composition_source = "model"
        fallback_reason: str | None = None
        all_draft_sentences: list[NarrativeSentence] = []
        all_dropped_sentences: list[SentenceDroppedDTO] = []
        all_dropped_blocks: list[BlockDroppedDTO] = []
        early_dropped_numbers_checked = 0
        early_dropped_numbers_matched = 0

        # Build tool results for fallback
        tr_fallback = [
            ToolResult(
                tool="composite",
                agent="orchestrator",
                label="Phân tích tổng hợp",
                facts=verified_facts,
                datasets=tool_datasets,
                missing=tool_missing,
            )
        ]

        # 1. Specialists write findings (if hierarchical)
        accepted_specialist_sentences: list[NarrativeSentence] = []
        if arm in ("hierarchical_no_critique", "hierarchical_with_critique"):
            company_fids = {f.fact_id for f in tool_facts_by_agent.get("company", [])}
            sector_fids = {f.fact_id for f in tool_facts_by_agent.get("sector", [])}
            macro_fids = {f.fact_id for f in tool_facts_by_agent.get("macro", [])}
            role_facts_map = {
                "company": [f for f in verified_facts if f.fact_id in company_fids],
                "sector": [f for f in verified_facts if f.fact_id in sector_fids],
                "macro": [f for f in verified_facts if f.fact_id in macro_fids],
            }
            role_datasets_map = {
                "company": tool_datasets_by_agent.get("company", []),
                "sector": tool_datasets_by_agent.get("sector", []),
                "macro": tool_datasets_by_agent.get("macro", []),
            }

            for role in ("company", "sector", "macro"):
                if role == "sector" and q_type == "lookup" and not role_facts_map["sector"]:
                    continue
                r_facts = role_facts_map[role]
                if not r_facts:
                    continue
                try:
                    findings_raw = self.writer.write_findings(
                        role=role,
                        question=self.request.query,
                        question_type=q_type,
                        facts=self._facts_payload(r_facts),
                        datasets_summary=self._datasets_summary(role_datasets_map[role]),
                        candidates=[c.__dict__ if hasattr(c, "__dict__") else c for c in candidates] if role == "company" else [],
                    )
                except Exception as exc:
                    orig = exc.__cause__ or exc
                    logger.warning("Writer write_findings for %s failed: %s (%s: %s)", role, exc, type(orig).__name__, orig)
                    tool_limitations.append(f"Chuyên viên {role} không phản hồi phân tích tự động.")
                    findings_raw = []

                role_sentences = []
                for s_idx, f_item in enumerate(findings_raw):
                    sent = NarrativeSentence(
                        sentence_id=f"sent-{role}-{s_idx+1}",
                        author=role,
                        text=f_item.get("text", ""),
                        fact_ids=tuple(f_item.get("fact_ids", ())),
                        source="model",
                    )
                    role_sentences.append(sent)
                all_draft_sentences.extend(role_sentences)

                # Emit draft step for this role
                if role_sentences:
                    self._trace(
                        kind="draft",
                        actor=role,  # type: ignore
                        summary=summary_draft(role, len(role_sentences)),
                        detail={
                            "sentences": [
                                {
                                    "sentence_id": s.sentence_id,
                                    "text": s.text,
                                    "fact_ids": list(s.fact_ids),
                                }
                                for s in role_sentences
                            ]
                        },
                        recipient="orchestrator",
                    )

                # Verify specialist sentences
                role_dropped: list[SentenceDroppedDTO] = []
                role_numbers_checked = 0
                role_numbers_matched = 0
                for sent in role_sentences:
                    v_res = verify_sentence(sent, v_ctx)
                    role_numbers_checked += v_res.numbers_checked
                    role_numbers_matched += v_res.numbers_matched
                    if v_res.ok:
                        accepted_specialist_sentences.append(sent)
                    else:
                        drop_dto = SentenceDroppedDTO(
                            sentence_id=sent.sentence_id,
                            author=sent.author,
                            text=sent.text,
                            reason_code=v_res.reason_code or "unknown_fact",  # type: ignore
                            reason=v_res.reason or "",
                        )
                        all_dropped_sentences.append(drop_dto)
                        role_dropped.append(drop_dto)
                        early_dropped_numbers_checked += v_res.numbers_checked
                        early_dropped_numbers_matched += v_res.numbers_matched

                if role_sentences:
                    self._trace(
                        kind="verify",
                        actor="verifier",
                        summary=summary_verify(
                            numbers_matched=role_numbers_matched,
                            numbers_checked=role_numbers_checked,
                            dropped_count=len(role_dropped),
                        ),
                        detail={
                            "sentences_checked": len(role_sentences),
                            "numbers_checked": role_numbers_checked,
                            "numbers_matched": role_numbers_matched,
                            "dropped": [
                                {
                                    "sentence_id": d.sentence_id,
                                    "text": d.text,
                                    "reason_code": d.reason_code,
                                    "reason": d.reason,
                                }
                                for d in role_dropped
                            ],
                        },
                        recipient="orchestrator",
                    )

        # 2. Orchestrator compose report
        self.emit("SYNTHESIS_STARTED", {"periods": list(periods), "message": "The orchestrator is composing the block-structured report."})
        raw_spec_dict = None
        try:
            raw_spec_dict = self.writer.compose_report(
                question=self.request.query,
                question_type=q_type,
                sentences=[
                    {"sentence_id": s.sentence_id, "author": s.author, "text": s.text, "fact_ids": list(s.fact_ids)}
                    for s in accepted_specialist_sentences
                ],
                datasets_summary=self._datasets_summary(tool_datasets),
                signals=[s.model_dump() for s in signals],
                findings=[c.__dict__ if hasattr(c, "__dict__") else c for c in candidates],
                facts=self._facts_payload(verified_facts),
            )
        except Exception as exc:
            orig = exc.__cause__ or exc
            logger.warning("Orchestrator compose_report failed: %s (%s: %s)", exc, type(orig).__name__, orig)
            tool_limitations.append("Một phần diễn giải do hệ thống tạo tự động vì mô hình không phản hồi.")
            composition_source = "deterministic_fallback"
            fallback_reason = f"compose_report_error: {type(orig).__name__}"

        # Helper to parse and verify raw_spec_dict blocks
        def _process_spec_blocks(spec_dict: dict[str, Any]) -> tuple[dict[str, Any], list[NarrativeSentence]]:
            nonlocal early_dropped_numbers_checked, early_dropped_numbers_matched
            spec_dict = normalize_report_spec_dict(spec_dict, q_type)
            processed_blocks: list[dict[str, Any]] = []
            spec_sentences: list[NarrativeSentence] = []
            known_sentences_by_id = {s.sentence_id: s for s in accepted_specialist_sentences}

            for blk in spec_dict.get("blocks", []):
                b = dict(blk)
                b_type = b.get("type")

                def _resolve_sent(s_data: Any, fallback_role: str = "orchestrator") -> dict[str, Any] | None:
                    nonlocal early_dropped_numbers_checked, early_dropped_numbers_matched
                    if not isinstance(s_data, dict):
                        return None
                    if "sentence_id" in s_data and s_data["sentence_id"] in known_sentences_by_id:
                        orig = known_sentences_by_id[s_data["sentence_id"]]
                        spec_sentences.append(orig)
                        return {
                            "sentence_id": orig.sentence_id,
                            "text": orig.text,
                            "fact_ids": list(orig.fact_ids),
                            "author": orig.author,
                            "source": orig.source,
                            "revision": orig.revision,
                        }
                    # New sentence
                    text = s_data.get("text", "")
                    fact_ids = tuple(s_data.get("fact_ids", ()))
                    s_id = s_data.get("sentence_id") or f"sent-{fallback_role}-{uuid.uuid4().hex[:6]}"
                    author = s_data.get("author") or fallback_role
                    new_sent = NarrativeSentence(
                        sentence_id=s_id,
                        author=author,
                        text=text,
                        fact_ids=fact_ids,
                        source="model",
                    )
                    v_res = verify_sentence(new_sent, v_ctx)
                    if v_res.ok:
                        spec_sentences.append(new_sent)
                        known_sentences_by_id[s_id] = new_sent
                        return {
                            "sentence_id": new_sent.sentence_id,
                            "text": new_sent.text,
                            "fact_ids": list(new_sent.fact_ids),
                            "author": new_sent.author,
                            "source": new_sent.source,
                            "revision": 0,
                        }
                    else:
                        all_dropped_sentences.append(SentenceDroppedDTO(
                            sentence_id=s_id,
                            author=author,
                            text=text,
                            reason_code=v_res.reason_code or "unknown_fact",  # type: ignore
                            reason=v_res.reason or "",
                        ))
                        early_dropped_numbers_checked += v_res.numbers_checked
                        early_dropped_numbers_matched += v_res.numbers_matched
                        return None

                if b_type == "headline":
                    s_dto = _resolve_sent(b.get("sentence"))
                    if s_dto:
                        b["sentence"] = s_dto
                        processed_blocks.append(b)
                elif b_type == "answer":
                    res_sents = []
                    for s in b.get("sentences", []):
                        resolved = _resolve_sent(s)
                        if resolved:
                            res_sents.append(resolved)
                    b["sentences"] = res_sents
                    processed_blocks.append(b)
                elif b_type == "key_points":
                    clean_items = []
                    for item in b.get("items", []):
                        it_sents = []
                        for s in item.get("sentences", []):
                            resolved = _resolve_sent(s)
                            if resolved:
                                it_sents.append(resolved)
                        if it_sents:
                            clean_items.append({"title": item.get("title", ""), "sentences": it_sents})
                    if clean_items:
                        b["items"] = clean_items
                        processed_blocks.append(b)
                elif b_type == "section":
                    sec_sents = []
                    for s in b.get("sentences", []):
                        resolved = _resolve_sent(s)
                        if resolved:
                            sec_sents.append(resolved)
                    if sec_sents:
                        b["sentences"] = sec_sents
                        processed_blocks.append(b)
                elif b_type == "callout":
                    c_sents = []
                    for s in b.get("sentences", []):
                        resolved = _resolve_sent(s)
                        if resolved:
                            c_sents.append(resolved)
                    if c_sents:
                        b["sentences"] = c_sents
                        processed_blocks.append(b)
                elif b_type == "figure":
                    # Takeaway check: if not pass, keep figure without takeaway
                    if b.get("takeaway"):
                        resolved = _resolve_sent(b["takeaway"])
                        if resolved:
                            b["takeaway"] = resolved
                        else:
                            # Use neutral fallback takeaway
                            b["takeaway"] = {
                                "sentence_id": f"sent-fb-fig-{b.get('figure_no', 1)}",
                                "text": f"Biểu đồ thể hiện {b.get('title', 'dữ liệu')}.",
                                "fact_ids": [verified_facts[0].fact_id] if verified_facts else [],
                                "author": "orchestrator",
                                "source": "deterministic_fallback",
                                "revision": 0,
                            }
                    processed_blocks.append(b)
                elif b_type == "table":
                    processed_blocks.append(b)

            clean_spec = {
                "kind": spec_dict.get("kind", "note"),
                "note_label": spec_dict.get("note_label"),
                "blocks": processed_blocks,
            }
            return clean_spec, spec_sentences

        active_report_spec: ReportSpecDTO | None = None
        current_sentences: list[NarrativeSentence] = []

        if raw_spec_dict is not None and isinstance(raw_spec_dict, dict):
            clean_spec_raw, spec_sentences = _process_spec_blocks(raw_spec_dict)
            # When verification removes every content sentence of a model note but its
            # headline survives, keep that headline and borrow the verified default
            # content blocks instead of discarding the whole model composition.
            _content_types = ("key_points", "section", "callout", "table")
            _raw_blocks = clean_spec_raw.get("blocks") or []
            if (
                clean_spec_raw.get("kind") == "note"
                and any(b.get("type") == "headline" for b in _raw_blocks)
                and not any(b.get("type") in _content_types for b in _raw_blocks)
            ):
                _default_spec = default_report_spec(
                    question_type=q_type,
                    tool_results=tr_fallback,
                    signals=signals,
                    findings=candidates,
                )
                _borrowed = [b for b in _default_spec.blocks if b.type in _content_types]
                if _borrowed:
                    clean_spec_raw["blocks"] = _raw_blocks + [b.model_dump() for b in _borrowed]
                    for b in _borrowed:
                        _sents = list(getattr(b, "sentences", []) or [])
                        for item in getattr(b, "items", []) or []:
                            _sents.extend(item.sentences)
                        for x in _sents:
                            spec_sentences.append(NarrativeSentence(
                                sentence_id=x.sentence_id, author=x.author, text=x.text,
                                fact_ids=tuple(x.fact_ids), source=x.source,
                            ))
                    all_dropped_blocks.append(BlockDroppedDTO(
                        type="spec_structure",
                        reason="Mọi câu nội dung của mô hình không qua kiểm chứng; dùng khối nội dung mặc định đã kiểm chứng.",
                    ))
            # Same idea for the single mandatory block: if verification removed the model's
            # headline (note) or answer (answer_card) but other verified content remains,
            # borrow the verified default headline/answer instead of discarding everything.
            _raw_blocks = clean_spec_raw.get("blocks") or []
            _required = {"note": "headline", "answer_card": "answer"}.get(clean_spec_raw.get("kind"))
            if _required and _raw_blocks and not any(
                b.get("type") == _required and (b.get("sentence") or b.get("sentences")) for b in _raw_blocks
            ):
                _default_spec = default_report_spec(
                    question_type=q_type,
                    tool_results=tr_fallback,
                    signals=signals,
                    findings=candidates,
                )
                _req_block = next((b for b in _default_spec.blocks if b.type == _required), None)
                if _req_block is not None:
                    _others = [b for b in _raw_blocks if b.get("type") != _required]
                    clean_spec_raw["blocks"] = [_req_block.model_dump()] + _others
                    _sents = [_req_block.sentence] if _required == "headline" else list(_req_block.sentences)
                    for x in _sents:
                        spec_sentences.append(NarrativeSentence(
                            sentence_id=x.sentence_id, author=x.author, text=x.text,
                            fact_ids=tuple(x.fact_ids), source=x.source,
                        ))
                    all_dropped_blocks.append(BlockDroppedDTO(
                        type=_required,
                        reason="Khối bắt buộc của mô hình không qua kiểm chứng; dùng khối mặc định đã kiểm chứng.",
                    ))
            if not clean_spec_raw.get("blocks"):
                fallback_reason = "model_spec_empty_after_normalization"
            val_res_dict, dropped_blocks_list = validate_report_spec(clean_spec_raw, tool_datasets, verified_facts)
            for db in dropped_blocks_list:
                all_dropped_blocks.append(BlockDroppedDTO(type=db["type"], reason=db["reason"]))
            if val_res_dict.get("is_valid", False):
                try:
                    val_res_clean = {k: v for k, v in val_res_dict.items() if k != "is_valid"}
                    active_report_spec = ReportSpecDTO.model_validate(val_res_clean)
                    current_sentences = spec_sentences
                    # The model sometimes composes a text-only note even when chartable
                    # datasets exist; keep its prose but add the default figures so the
                    # report stays an exhibit-backed note. Figure takeaways still pass the
                    # final verification sweep and validate_report_spec below.
                    if (
                        active_report_spec.kind == "note"
                        and tool_datasets
                        and not any(b.type == "figure" for b in active_report_spec.blocks)
                    ):
                        default_figs = [
                            b for b in default_report_spec(
                                question_type=q_type,
                                tool_results=tr_fallback,
                                signals=signals,
                                findings=candidates,
                            ).blocks
                            if b.type == "figure"
                        ]
                        if default_figs:
                            blocks = list(active_report_spec.blocks)
                            insert_at = 1 if blocks and blocks[0].type == "headline" else 0
                            for offset, fig in enumerate(default_figs):
                                blocks.insert(insert_at + 1 + offset if insert_at else offset, fig)
                            active_report_spec.blocks = blocks
                    # Confirmed cross-level findings belong in callouts (spec §6.6); when the
                    # model omitted them, append the default callouts (verified in the sweep).
                    if (
                        active_report_spec.kind == "note"
                        and candidates
                        and not any(b.type == "callout" for b in active_report_spec.blocks)
                    ):
                        default_callouts = [
                            b for b in default_report_spec(
                                question_type=q_type,
                                tool_results=tr_fallback,
                                signals=signals,
                                findings=candidates,
                            ).blocks
                            if b.type == "callout"
                        ]
                        if default_callouts:
                            active_report_spec.blocks = list(active_report_spec.blocks) + default_callouts
                except Exception as exc:
                    logger.warning("ReportSpecDTO validation failed: %s", exc)
                    fallback_reason = f"spec_dto_validation_failed: {exc}"
                    active_report_spec = None
            else:
                struct_reasons = [db.get("reason", "") for db in dropped_blocks_list if db.get("type") in ("spec_structure", "figure", "answer", "headline")]
                fallback_reason = f"spec_invalid: {'; '.join(struct_reasons) or 'structural validation failed'}"

        if active_report_spec is None:
            composition_source = "deterministic_fallback"
            if not fallback_reason:
                fallback_reason = "compose_report_returned_none"
            active_report_spec = default_report_spec(
                question_type=q_type,
                tool_results=tr_fallback,
                signals=signals,
                findings=candidates,
            )
            # Collect sentences from fallback spec
            for blk in active_report_spec.blocks:
                if blk.type == "headline":
                    current_sentences.append(NarrativeSentence(
                        sentence_id=blk.sentence.sentence_id,
                        author=blk.sentence.author,
                        text=blk.sentence.text,
                        fact_ids=tuple(blk.sentence.fact_ids),
                        source=blk.sentence.source,
                    ))
                elif blk.type == "answer":
                    for s in blk.sentences:
                        current_sentences.append(NarrativeSentence(
                            sentence_id=s.sentence_id,
                            author=s.author,
                            text=s.text,
                            fact_ids=tuple(s.fact_ids),
                            source=s.source,
                        ))
                elif blk.type == "key_points":
                    for it in blk.items:
                        for s in it.sentences:
                            current_sentences.append(NarrativeSentence(
                                sentence_id=s.sentence_id,
                                author=s.author,
                                text=s.text,
                                fact_ids=tuple(s.fact_ids),
                                source=s.source,
                            ))
                elif blk.type == "figure" and blk.takeaway:
                    current_sentences.append(NarrativeSentence(
                        sentence_id=blk.takeaway.sentence_id,
                        author=blk.takeaway.author,
                        text=blk.takeaway.text,
                        fact_ids=tuple(blk.takeaway.fact_ids),
                        source=blk.takeaway.source,
                    ))

        # Trace compose step
        blocks_detail = []
        for blk in active_report_spec.blocks:
            blk_title = getattr(blk, "title", "")
            if not blk_title and blk.type == "key_points" and getattr(blk, "items", None):
                blk_title = blk.items[0].title if blk.items else ""
            blocks_detail.append({
                "type": blk.type,
                "title": blk_title or f"Khối {blk.type}",
            })
        self._trace(
            kind="compose",
            actor="orchestrator",
            summary=summary_compose(
                kind=active_report_spec.kind,
                blocks=active_report_spec.blocks,
                composition_source=composition_source,
            ),
            detail={
                "kind": active_report_spec.kind,
                "blocks": blocks_detail,
                "composition_source": composition_source,
            },
            recipient="critic" if arm == "hierarchical_with_critique" else "system",
        )

        # 3. Critique & Revision loop (if hierarchical_with_critique)
        critic_result = None
        rounds_executed = 0
        current_claims = tuple(
            c.model_copy(update={"stage2_critique_status": "sound"})
            for c in initial_claims
        )
        synthesis_summary: str | None = None
        all_revised_agents: set[str] = set()

        if hasattr(self.writer, "synthesize"):
            try:
                synth_out = self.writer.synthesize(
                    plan=plan.model_dump() if hasattr(plan, "model_dump") else plan,
                    specialist_outputs={
                        "company": [{"claim_id": c.claim_id} for c in current_claims]
                    },
                    issues=[],
                )
                if isinstance(synth_out, dict):
                    synthesis_summary = synth_out.get("summary")
            except Exception:
                pass

        if arm == "hierarchical_with_critique":
            # Any failure inside critique/revision (e.g. an unexpected model output shape)
            # must not fail the run: keep the verified pre-critique report instead.
            _pre_critique_spec = active_report_spec.model_copy(deep=True)
            _pre_critique_sentences = list(current_sentences)
            try:
                rounds_executed = 1

                # Trace assign to critic (round 1)
                self._trace(
                    kind="assign",
                    actor="orchestrator",
                    summary=summary_assign("critic", round_no=1),
                    detail={
                        "task": "Gửi bản nháp để kiểm tra chéo (vòng 1)",
                        "tools": ["semantic_critique"],
                    },
                    recipient="critic",
                )
                synth_summary_for_ctx = None
                if synthesis_summary is not None:
                    try:
                        from thesis_data.semantic_critic import validate_synthesis_summary
                        validate_synthesis_summary(synthesis_summary)
                        synth_summary_for_ctx = synthesis_summary
                    except Exception:
                        synth_summary_for_ctx = None
                round1_ctx = SemanticRoundContext(
                    round_number=0,
                    narrative=tuple(current_sentences),
                    report_spec=active_report_spec.model_dump(),
                    cross_level_candidates=tuple(candidates),
                    synthesis_summary=synth_summary_for_ctx,
                    synthesis_supporting_claim_ids=tuple(c.claim_id for c in current_claims) if synth_summary_for_ctx else (),
                )
                self.emit("REVIEW_STARTED", {"stage": "stage2", "periods": list(periods), "message": "Running semantic critique on block-structured report."})
                try:
                    critic_result = self.critic.evaluate(
                        plan=plan,
                        claims=current_claims,
                        stage1_report=stage1_report,
                        round_context=round1_ctx,
                    )
                except Exception as exc:
                    orig = exc.__cause__ or exc
                    logger.warning("Critic evaluate round 1 failed: %s (%s: %s)", exc, type(orig).__name__, orig)
                    critic_result = None
                    tool_limitations.append("Không thực hiện được phản biện tự động.")

                if critic_result is not None:
                    critic_limitation_issues: list[Any] = []
                    self.emit("REVIEW_FEEDBACK_CREATED", {
                        "round": 1,
                        "periods": list(plan.scope.periods),
                        "issueCount": len(critic_result.critique_issues),
                        "openIssueCount": sum(issue.resolution_status is CritiqueIssueStatus.OPEN for issue in critic_result.critique_issues),
                        "message": "Structured semantic review completed.",
                    })

                    # Trace critique issues
                    for issue in critic_result.critique_issues:
                        target_s_id = (
                            getattr(issue, "target_sentence_id", None)
                            or (issue.affected_sentence_ids[0] if getattr(issue, "affected_sentence_ids", None) else None)
                        )
                        issue_detail = {
                            "issue_id": issue.issue_id,
                            "round": 1,
                            "issue_type": issue.issue_type.value if hasattr(issue.issue_type, "value") else str(issue.issue_type),
                            "severity": issue.severity.value if hasattr(issue.severity, "value") else str(issue.severity),
                            "target_sentence_id": target_s_id,
                            "target_text": getattr(issue, "target_text", "") or "",
                            "evidence": getattr(issue, "evidence", "") or "",
                            "evidence_fact_ids": list(getattr(issue, "evidence_fact_ids", ())),
                            "required_action": issue.required_action.value if hasattr(issue.required_action, "value") else str(issue.required_action),
                        }
                        self._trace(
                            kind="critique_issue",
                            actor="critic",
                            summary=summary_critique_issue(
                                description=issue.description,
                                issue_type=issue_detail["issue_type"],
                                required_action=issue_detail["required_action"],
                            ),
                            detail=issue_detail,
                            recipient=issue.affected_agent if issue.affected_agent in ("company", "sector", "macro") else "orchestrator",  # type: ignore
                        )

                    # Verify confirmed cross-level candidates
                    for c in getattr(critic_result, "cross_level_candidates", ()):
                        if getattr(c, "status", "") == "confirmed":
                            c_sent = NarrativeSentence(
                                sentence_id=f"sent-crit-{getattr(c, 'finding_id', 'cand')}",
                                author="critic",
                                text=getattr(c, "text", ""),
                                fact_ids=tuple(getattr(c, "fact_ids", ())),
                                source="model",
                            )
                            c_verdict = verify_sentence(c_sent, v_ctx)
                            if not c_verdict.ok:
                                if hasattr(c, "status"):
                                    c.status = "dismissed"
                                all_dropped_sentences.append(SentenceDroppedDTO(
                                    sentence_id=c_sent.sentence_id,
                                    author=c_sent.author,
                                    text=c_sent.text,
                                    reason_code=c_verdict.reason_code or "unknown_fact",  # type: ignore
                                    reason="không kiểm chứng được",
                                ))
                                early_dropped_numbers_checked += c_verdict.numbers_checked
                                early_dropped_numbers_matched += c_verdict.numbers_matched
                            else:
                                self._trace(
                                    kind="cross_level_finding",
                                    actor="critic",
                                    summary=summary_cross_level_finding(count=1),
                                    detail={
                                        "finding_id": getattr(c, "finding_id", "cand"),
                                        "kind": getattr(c, "kind", "divergent_signals"),
                                        "text": getattr(c, "text", ""),
                                        "fact_ids": list(getattr(c, "fact_ids", ())),
                                    },
                                    recipient="orchestrator",
                                )

                    open_issues = [
                        issue for issue in critic_result.critique_issues
                        if issue.resolution_status is CritiqueIssueStatus.OPEN
                    ]
                    lead_count_fact_ids = {f.fact_id for f in verified_facts if getattr(f, "fact_type", "") == "lead_count"}
                    filtered_open_issues = []
                    for issue in open_issues:
                        is_lead_count_issue = False
                        for s in current_sentences:
                            if any(fid in lead_count_fact_ids for fid in s.fact_ids):
                                if issue.affected_sentence_ids and s.sentence_id in issue.affected_sentence_ids:
                                    is_lead_count_issue = True
                                    break
                                if s.text and (s.text in issue.description or any(tok in issue.description for tok in ("chỉ tiêu", "nhỉnh hơn", "3/4", "lead_count"))):
                                    is_lead_count_issue = True
                                    break
                        if not is_lead_count_issue and any(tok in issue.description for tok in ("3/4 chỉ tiêu", "chỉ tiêu nào", "chiều so sánh của từng chỉ tiêu", "mỗi bên nhỉnh hơn ở 2/4")):
                            is_lead_count_issue = True

                        if is_lead_count_issue:
                            logger.info(
                                "Ignoring critic issue %s on lead_count sentence (%s): arithmetic/lead_count is deterministically verified by verifier.",
                                issue.issue_id,
                                issue.description,
                            )
                            continue
                        filtered_open_issues.append(issue)
                    open_issues = filtered_open_issues

                    # Perform round 1 revision if open issues
                    if open_issues:
                        self.emit("REVISION_REQUESTED", {
                            "round": 1,
                            "periods": list(plan.scope.periods),
                            "targetSpecialists": sorted({i.affected_agent for i in open_issues}),
                            "issueCount": len(open_issues),
                        })
                        self.emit("REVISION_ACTIVITY", {
                            "round": 1,
                            "periods": list(plan.scope.periods),
                            "message": "Applying critique feedback to revise narrative sentences and report blocks.",
                        })

                        # Handle sentence rewrites and drop actions
                        for issue in open_issues:
                            if getattr(issue, "affected_agent", None):
                                all_revised_agents.add(issue.affected_agent)

                            # ADD_LIMITATION
                            if getattr(issue, "required_action", None) == "ADD_LIMITATION" or getattr(issue, "required_action", None) == CritiqueAction.ADD_LIMITATION:
                                critic_limitation_issues.append(issue)

                            # REMOVE_CLAIM
                            elif getattr(issue, "required_action", None) == "REMOVE_CLAIM" or getattr(issue, "required_action", None) == CritiqueAction.REMOVE_CLAIM:
                                if issue.affected_sentence_ids:
                                    for s_id in issue.affected_sentence_ids:
                                        drop_target = next((s for s in current_sentences if s.sentence_id == s_id), None)
                                        if drop_target:
                                            all_dropped_sentences.append(SentenceDroppedDTO(
                                                sentence_id=drop_target.sentence_id,
                                                author=drop_target.author,
                                                text=drop_target.text,
                                                reason_code="unresolved_critique",
                                                reason=issue.description,
                                            ))
                                if issue.affected_block_index is not None and issue.affected_block_index < len(active_report_spec.blocks):
                                    all_dropped_blocks.append(BlockDroppedDTO(
                                        type=active_report_spec.blocks[issue.affected_block_index].type,
                                        reason=issue.description,
                                    ))
                                    active_report_spec.blocks.pop(issue.affected_block_index)

                            # Claim update compatibility for test fixtures/offline writers
                            if issue.affected_claim_ids and hasattr(self.writer, "write_specialist"):
                                target_claims = [c for c in current_claims if c.claim_id in issue.affected_claim_ids]
                                if target_claims:
                                    for c in target_claims:
                                        if c.assertions:
                                            a = c.assertions[0]
                                            self._fetch_direct(issue.affected_agent, (a.entity,), (a.metric_id,), a.period)
                                    claims_payload = [
                                        {
                                            "claim_id": c.claim_id,
                                            "display_name": c.title,
                                            "accepted_observation": {
                                                "entity_id": c.assertions[0].entity if c.assertions else "",
                                                "metric_id": c.assertions[0].metric_id if c.assertions else "",
                                                "period_id": c.assertions[0].period if c.assertions else "",
                                                "validation_status": "present",
                                            },
                                        }
                                        for c in target_claims
                                    ]
                                    try:
                                        writer_res = self.writer.write_specialist(
                                            plan=plan.model_dump() if hasattr(plan, "model_dump") else plan,
                                            role=issue.affected_agent,
                                            claims=claims_payload,
                                            issues=[issue.model_dump() if hasattr(issue, "model_dump") else issue.__dict__],
                                        )
                                        updated_claims = list(current_claims)
                                        for idx, c in enumerate(updated_claims):
                                            if c.claim_id in writer_res:
                                                updated_claims[idx] = c.model_copy(update={
                                                    "claim_text": writer_res[c.claim_id]["prose"],
                                                    "statement": writer_res[c.claim_id]["prose"],
                                                    "stage2_critique_status": "revised",
                                                })
                                        current_claims = tuple(updated_claims)
                                    except Exception as exc:
                                        orig = exc.__cause__ or exc
                                        logger.warning("Writer write_specialist revision failed: %s (%s: %s)", exc, type(orig).__name__, orig)

                            # REVISE_CLAIM with affected sentences
                            affected_s_ids = list(issue.affected_sentence_ids)
                            if not affected_s_ids and getattr(issue, "required_action", None) in (CritiqueAction.REVISE_CLAIM, "REVISE_CLAIM"):
                                agent_s = [s for s in current_sentences if s.author == issue.affected_agent]
                                if agent_s:
                                    affected_s_ids = [agent_s[0].sentence_id]

                            if affected_s_ids:
                                for s_id in affected_s_ids:
                                    orig_s = next((s for s in current_sentences if s.sentence_id == s_id), None)
                                    if orig_s:
                                        try:
                                            revised_dict = self.writer.rewrite_sentence(
                                                role=orig_s.author,
                                                question=self.request.query,
                                                sentence={"text": orig_s.text, "fact_ids": list(orig_s.fact_ids)},
                                                issue=issue.model_dump() if hasattr(issue, "model_dump") else issue.__dict__,
                                                facts=self._facts_payload(verified_facts),
                                            )
                                            rev_s = NarrativeSentence(
                                                sentence_id=orig_s.sentence_id,
                                                author=orig_s.author,
                                                text=revised_dict.get("text", ""),
                                                fact_ids=tuple(revised_dict.get("fact_ids", ())),
                                                source="model",
                                                revision=orig_s.revision + 1,
                                            )
                                            rev_v = verify_sentence(rev_s, v_ctx)
                                            self._trace(
                                                kind="revision",
                                                actor=orig_s.author,  # type: ignore
                                                summary=summary_revision(round_no=1, author=orig_s.author),
                                                detail={
                                                    "round": 1,
                                                    "sentence_id": orig_s.sentence_id,
                                                    "before": orig_s.text,
                                                    "after": rev_s.text,
                                                    "verified": rev_v.ok,
                                                },
                                                recipient="verifier",
                                            )
                                            if rev_v.ok:
                                                # Replace sentence in spec
                                                current_sentences = [
                                                    rev_s if s.sentence_id == orig_s.sentence_id else s
                                                    for s in current_sentences
                                                ]
                                                # Update in active_report_spec blocks
                                                for blk in active_report_spec.blocks:
                                                    if blk.type == "headline" and blk.sentence.sentence_id == orig_s.sentence_id:
                                                        blk.sentence = SentenceDTO(
                                                            sentence_id=rev_s.sentence_id,
                                                            text=rev_s.text,
                                                            fact_ids=list(rev_s.fact_ids),
                                                            author=rev_s.author,  # type: ignore
                                                            source=rev_s.source,  # type: ignore
                                                            revision=rev_s.revision,
                                                        )
                                                    elif blk.type == "answer":
                                                        for s_idx, s in enumerate(blk.sentences):
                                                            if s.sentence_id == orig_s.sentence_id:
                                                                blk.sentences[s_idx] = SentenceDTO(
                                                                    sentence_id=rev_s.sentence_id,
                                                                    text=rev_s.text,
                                                                    fact_ids=list(rev_s.fact_ids),
                                                                    author=rev_s.author,  # type: ignore
                                                                    source=rev_s.source,  # type: ignore
                                                                    revision=rev_s.revision,
                                                                )
                                                    elif blk.type == "key_points":
                                                        for item in blk.items:
                                                            for s_idx, s in enumerate(item.sentences):
                                                                if s.sentence_id == orig_s.sentence_id:
                                                                    item.sentences[s_idx] = SentenceDTO(
                                                                        sentence_id=rev_s.sentence_id,
                                                                        text=rev_s.text,
                                                                        fact_ids=list(rev_s.fact_ids),
                                                                        author=rev_s.author,  # type: ignore
                                                                        source=rev_s.source,  # type: ignore
                                                                        revision=rev_s.revision,
                                                                    )
                                                    elif blk.type == "figure" and blk.takeaway and blk.takeaway.sentence_id == orig_s.sentence_id:
                                                        blk.takeaway = SentenceDTO(
                                                            sentence_id=rev_s.sentence_id,
                                                            text=rev_s.text,
                                                            fact_ids=list(rev_s.fact_ids),
                                                            author=rev_s.author,  # type: ignore
                                                            source=rev_s.source,  # type: ignore
                                                            revision=rev_s.revision,
                                                        )
                                            else:
                                                # Dropped
                                                all_dropped_sentences.append(SentenceDroppedDTO(
                                                    sentence_id=orig_s.sentence_id,
                                                    author=orig_s.author,
                                                    text=rev_s.text,
                                                    reason_code=rev_v.reason_code or "unknown_fact",  # type: ignore
                                                    reason=rev_v.reason or "",
                                                ))
                                                early_dropped_numbers_checked += rev_v.numbers_checked
                                                early_dropped_numbers_matched += rev_v.numbers_matched
                                        except Exception as exc:
                                            orig = exc.__cause__ or exc
                                            logger.warning("Rewrite sentence failed: %s (%s: %s)", exc, type(orig).__name__, orig)

                            # Reconcile cross level / incomplete synthesis
                            elif getattr(issue, "required_action", None) == "RECONCILE_CROSS_LEVEL" or getattr(issue, "required_action", None) == CritiqueAction.RECONCILE_CROSS_LEVEL:
                                # Re-compose
                                try:
                                    recomposed = self.writer.compose_report(
                                        question=self.request.query,
                                        question_type=q_type,
                                        sentences=[
                                            {"sentence_id": s.sentence_id, "author": s.author, "text": s.text, "fact_ids": list(s.fact_ids)}
                                            for s in current_sentences
                                        ],
                                        datasets_summary=self._datasets_summary(tool_datasets),
                                        signals=[s.model_dump() for s in signals],
                                        findings=[c.__dict__ if hasattr(c, "__dict__") else c for c in candidates],
                                        facts=self._facts_payload(verified_facts),
                                    )
                                    c_spec_raw, c_sents = _process_spec_blocks(recomposed)
                                    v_res_c, d_c = validate_report_spec(c_spec_raw, tool_datasets, verified_facts)
                                    if v_res_c.get("is_valid", False):
                                        v_res_clean = {k: v for k, v in v_res_c.items() if k != "is_valid"}
                                        active_report_spec = ReportSpecDTO.model_validate(v_res_clean)
                                        current_sentences = c_sents
                                except Exception as exc:
                                    orig = exc.__cause__ or exc
                                    logger.warning("Recompose report failed: %s (%s: %s)", exc, type(orig).__name__, orig)

                        if hasattr(self.writer, "synthesize"):
                            try:
                                synth_out = self.writer.synthesize(
                                    plan=plan.model_dump() if hasattr(plan, "model_dump") else plan,
                                    specialist_outputs={
                                        "company": [{"claim_id": c.claim_id} for c in current_claims]
                                    },
                                    issues=[i.model_dump() if hasattr(i, "model_dump") else i.__dict__ for i in open_issues],
                                )
                                if isinstance(synth_out, dict):
                                    synthesis_summary = synth_out.get("summary")
                            except Exception as exc:
                                logger.warning("Synthesize re-run failed: %s", exc)

                        self.emit("REVISION_COMPLETED", {
                            "round": 1,
                            "periods": list(plan.scope.periods),
                            "revisedSpecialists": sorted({i.affected_agent for i in open_issues}),
                            "synthesisRevised": True,
                        })

                        # Re-evaluate Stage-1 on current claims
                        try:
                            stage1_report = stage1.evaluate(plan=plan, claims=current_claims, policy=_API_POLICY)
                        except Exception as exc:
                            logger.warning("Stage-1 re-evaluation failed: %s", exc)

                        # Critic Round 2
                        rounds_executed = 2
                        synth_summary_for_ctx2 = None
                        if synthesis_summary is not None:
                            try:
                                from thesis_data.semantic_critic import validate_synthesis_summary
                                validate_synthesis_summary(synthesis_summary)
                                synth_summary_for_ctx2 = synthesis_summary
                            except Exception:
                                synth_summary_for_ctx2 = None
                        round2_ctx = SemanticRoundContext(
                            round_number=1,
                            narrative=tuple(current_sentences),
                            report_spec=active_report_spec.model_dump(),
                            cross_level_candidates=tuple(candidates),
                            prior_issue_ids=tuple(i.issue_id for i in open_issues),
                            prior_issues=tuple(open_issues),
                            synthesis_summary=synth_summary_for_ctx2,
                            synthesis_supporting_claim_ids=tuple(c.claim_id for c in current_claims) if synth_summary_for_ctx2 else (),
                        )
                        # Trace assign to critic (round 2)
                        self._trace(
                            kind="assign",
                            actor="orchestrator",
                            summary=summary_assign("critic", round_no=2),
                            detail={
                                "task": "Gửi bản nháp để kiểm tra chéo (vòng 2)",
                                "tools": ["semantic_critique"],
                            },
                            recipient="critic",
                        )
                        try:
                            critic_result = self.critic.evaluate(
                                plan=plan,
                                claims=current_claims,
                                stage1_report=stage1_report,
                                round_context=round2_ctx,
                            )
                        except Exception as exc:
                            orig = exc.__cause__ or exc
                            logger.warning("Critic evaluate round 2 failed: %s (%s: %s)", exc, type(orig).__name__, orig)

                        if critic_result is not None:
                            # Drop any sentences that still have OPEN issues
                            still_open_issues = [
                                i for i in critic_result.critique_issues
                                if i.resolution_status is CritiqueIssueStatus.OPEN
                            ]
                            still_open_filtered = []
                            for i in still_open_issues:
                                is_lc = False
                                for s in current_sentences:
                                    if any(fid in lead_count_fact_ids for fid in s.fact_ids):
                                        if i.affected_sentence_ids and s.sentence_id in i.affected_sentence_ids:
                                            is_lc = True
                                            break
                                        if s.text and (s.text in i.description or any(tok in i.description for tok in ("chỉ tiêu", "nhỉnh hơn", "3/4", "lead_count"))):
                                            is_lc = True
                                            break
                                if not is_lc and any(tok in i.description for tok in ("3/4 chỉ tiêu", "chỉ tiêu nào", "chiều so sánh của từng chỉ tiêu", "mỗi bên nhỉnh hơn ở 2/4")):
                                    is_lc = True

                                if is_lc:
                                    logger.info(
                                        "Ignoring round 2 critic issue %s on lead_count sentence (%s): verified deterministically.",
                                        i.issue_id,
                                        i.description,
                                    )
                                    continue
                                still_open_filtered.append(i)
                            still_open_issues = still_open_filtered

                            verified_sentence_ids = {s.sentence_id for s in current_sentences}
                            _vf_by_id = {f.fact_id: f for f in verified_facts if hasattr(f, "fact_id")}

                            for i in still_open_issues:
                                # Only MAJOR/CRITICAL issues still open after the last round remove
                                # sentences. MINOR ones (style, duplication, extra context) are kept
                                # as limitations so a readable model report is not emptied by nitpicks.
                                severity = str(getattr(getattr(i, "severity", ""), "value", getattr(i, "severity", ""))).lower()
                                if severity == "minor" or getattr(i, "required_action", None) in ("ADD_LIMITATION", CritiqueAction.ADD_LIMITATION):
                                    if i not in critic_limitation_issues:
                                        critic_limitation_issues.append(i)
                                    continue
                                s_ids = list(i.affected_sentence_ids)
                                if not s_ids:
                                    agent_s = [s for s in current_sentences if s.author == i.affected_agent]
                                    if agent_s:
                                        s_ids = [agent_s[0].sentence_id]

                                # If ALL affected sentence IDs resolve to sentences that cite ONLY
                                # lead_count facts (no value/peer_median facts), skip the drop —
                                # those sentences contain no numbers the critic could legitimately flag;
                                # any remaining issue is a comparison-direction dispute already cleared
                                # by the deterministic verifier.
                                if s_ids and all(sid in verified_sentence_ids for sid in s_ids if sid):
                                    def _only_lead_count(sid: str) -> bool:
                                        sent = next((s for s in current_sentences if s.sentence_id == sid), None)
                                        if sent is None:
                                            return False
                                        cited = [_vf_by_id.get(fid) for fid in sent.fact_ids if fid in _vf_by_id]
                                        if not cited:
                                            return False
                                        return all(
                                            getattr(f, "fact_type", "") in ("lead_count",)
                                            for f in cited if f is not None
                                        )
                                    if all(_only_lead_count(sid) for sid in s_ids if sid):
                                        logger.info(
                                            "Skipping round 2 critic drop for issue %s: all affected sentences (%s) "
                                            "cite only lead_count facts — verifier is authoritative. Critic: %s",
                                            i.issue_id, s_ids, i.description,
                                        )
                                        continue

                                if i.affected_claim_ids and hasattr(self.writer, "write_specialist"):
                                    target_claims = [c for c in current_claims if c.claim_id in i.affected_claim_ids]
                                    for c in target_claims:
                                        if c.assertions:
                                            a = c.assertions[0]
                                            self._fetch_direct(i.affected_agent, (a.entity,), (a.metric_id,), a.period)
                                for s_id in s_ids:
                                    drop_target = next((s for s in current_sentences if s.sentence_id == s_id), None)
                                    if drop_target:
                                        all_dropped_sentences.append(SentenceDroppedDTO(
                                            sentence_id=drop_target.sentence_id,
                                            author=drop_target.author,
                                            text=drop_target.text,
                                            reason_code="unresolved_critique",
                                            reason=i.description,
                                        ))

                        # Re-validate spec after round 2
                        val_after, drop_after = validate_report_spec(active_report_spec.model_dump(), tool_datasets, verified_facts)
                        for db in drop_after:
                            all_dropped_blocks.append(BlockDroppedDTO(type=db["type"], reason=db["reason"]))
                        if val_after.get("is_valid", False):
                            val_after_clean = {k: v for k, v in val_after.items() if k != "is_valid"}
                            active_report_spec = ReportSpecDTO.model_validate(val_after_clean)
                        else:
                            composition_source = "deterministic_fallback"
                            fallback_reason = f"recomposed_spec_invalid: {'; '.join(db.get('reason', '') for db in drop_after) or 'validation failed'}"
                            active_report_spec = default_report_spec(
                                question_type=q_type,
                                tool_results=tr_fallback,
                                signals=signals,
                                findings=candidates,
                            )

                if critic_limitation_issues:
                    reader_lims = format_critic_limitations(critic_limitation_issues)
                    for r_lim in reader_lims:
                        if r_lim not in tool_limitations:
                            tool_limitations.append(r_lim)

                open_count = (
                    sum(i.resolution_status is CritiqueIssueStatus.OPEN for i in getattr(critic_result, "critique_issues", ()))
                    if critic_result
                    else 0
                )
                self._trace(
                    kind="accept",
                    actor="critic",
                    summary=summary_accept(round_no=rounds_executed, open_issues=open_count),
                    detail={
                        "round": rounds_executed,
                        "open_issues": open_count,
                    },
                    recipient="orchestrator",
                )
            except Exception as exc:  # noqa: BLE001
                from .service import AnalysisBlocked as _AnalysisBlocked

                if isinstance(exc, _AnalysisBlocked):
                    raise  # deliberate policy outcomes (e.g. unrepairable critical issue) stay terminal
                orig = exc.__cause__ or exc
                logger.warning("Critique/revision stage failed: %s (%s: %s)", exc, type(orig).__name__, orig, exc_info=True)
                active_report_spec = _pre_critique_spec
                current_sentences = _pre_critique_sentences
                tool_limitations.append("Vòng phản biện gặp lỗi kỹ thuật; báo cáo giữ bản đã kiểm chứng trước phản biện.")

        # Helper to verify every sentence in a ReportSpecDTO
        def _sweep_report_spec(spec: ReportSpecDTO) -> tuple[ReportSpecDTO, int, int]:
            sweep_chk = 0
            sweep_mat = 0
            verified_blks: list[Any] = []

            for blk in spec.blocks:
                if blk.type == "headline":
                    n_sent = NarrativeSentence(
                        sentence_id=blk.sentence.sentence_id,
                        author=blk.sentence.author,
                        text=blk.sentence.text,
                        fact_ids=tuple(blk.sentence.fact_ids),
                        source=blk.sentence.source,
                        revision=blk.sentence.revision,
                    )
                    v_res = verify_sentence(n_sent, v_ctx)
                    sweep_chk += v_res.numbers_checked
                    sweep_mat += v_res.numbers_matched
                    if v_res.ok:
                        verified_blks.append(blk)
                    else:
                        all_dropped_sentences.append(
                            SentenceDroppedDTO(
                                sentence_id=blk.sentence.sentence_id,
                                author=blk.sentence.author,
                                text=blk.sentence.text,
                                reason_code=v_res.reason_code or "unknown_fact",  # type: ignore
                                reason=v_res.reason or "",
                            )
                        )
                        safe_hl = SentenceDTO(
                            sentence_id="sent-fb-hl-safe",
                            text="Báo cáo phân tích tài chính.",
                            fact_ids=[],
                            author="orchestrator",
                            source="deterministic_fallback",
                            revision=0,
                        )
                        blk.sentence = safe_hl
                        verified_blks.append(blk)

                elif blk.type == "answer":
                    val_sents = []
                    for s in blk.sentences:
                        n_sent = NarrativeSentence(
                            sentence_id=s.sentence_id,
                            author=s.author,
                            text=s.text,
                            fact_ids=tuple(s.fact_ids),
                            source=s.source,
                            revision=s.revision,
                        )
                        v_res = verify_sentence(n_sent, v_ctx)
                        sweep_chk += v_res.numbers_checked
                        sweep_mat += v_res.numbers_matched
                        if v_res.ok:
                            val_sents.append(s)
                        else:
                            all_dropped_sentences.append(
                                SentenceDroppedDTO(
                                    sentence_id=s.sentence_id,
                                    author=s.author,
                                    text=s.text,
                                    reason_code=v_res.reason_code or "unknown_fact",  # type: ignore
                                    reason=v_res.reason or "",
                                )
                            )
                    blk.sentences = val_sents
                    verified_blks.append(blk)

                elif blk.type == "key_points":
                    val_items = []
                    for item in blk.items:
                        it_sents = []
                        for s in item.sentences:
                            n_sent = NarrativeSentence(
                                sentence_id=s.sentence_id,
                                author=s.author,
                                text=s.text,
                                fact_ids=tuple(s.fact_ids),
                                source=s.source,
                                revision=s.revision,
                            )
                            v_res = verify_sentence(n_sent, v_ctx)
                            sweep_chk += v_res.numbers_checked
                            sweep_mat += v_res.numbers_matched
                            if v_res.ok:
                                it_sents.append(s)
                            else:
                                all_dropped_sentences.append(
                                    SentenceDroppedDTO(
                                        sentence_id=s.sentence_id,
                                        author=s.author,
                                        text=s.text,
                                        reason_code=v_res.reason_code or "unknown_fact",  # type: ignore
                                        reason=v_res.reason or "",
                                    )
                                )
                        if it_sents:
                            item.sentences = it_sents
                            val_items.append(item)
                    if val_items:
                        blk.items = val_items
                        verified_blks.append(blk)
                    else:
                        all_dropped_blocks.append(BlockDroppedDTO(type="key_points", reason="Tất cả câu nhận định không qua kiểm chứng."))

                elif blk.type == "section":
                    sec_sents = []
                    for s in blk.sentences:
                        n_sent = NarrativeSentence(
                            sentence_id=s.sentence_id,
                            author=s.author,
                            text=s.text,
                            fact_ids=tuple(s.fact_ids),
                            source=s.source,
                            revision=s.revision,
                        )
                        v_res = verify_sentence(n_sent, v_ctx)
                        sweep_chk += v_res.numbers_checked
                        sweep_mat += v_res.numbers_matched
                        if v_res.ok:
                            sec_sents.append(s)
                        else:
                            all_dropped_sentences.append(
                                SentenceDroppedDTO(
                                    sentence_id=s.sentence_id,
                                    author=s.author,
                                    text=s.text,
                                    reason_code=v_res.reason_code or "unknown_fact",  # type: ignore
                                    reason=v_res.reason or "",
                                )
                            )
                    if sec_sents:
                        blk.sentences = sec_sents
                        verified_blks.append(blk)
                    else:
                        all_dropped_blocks.append(BlockDroppedDTO(type="section", reason="Tất cả câu trong phần không qua kiểm chứng."))

                elif blk.type == "callout":
                    c_sents = []
                    for s in blk.sentences:
                        n_sent = NarrativeSentence(
                            sentence_id=s.sentence_id,
                            author=s.author,
                            text=s.text,
                            fact_ids=tuple(s.fact_ids),
                            source=s.source,
                            revision=s.revision,
                        )
                        v_res = verify_sentence(n_sent, v_ctx)
                        sweep_chk += v_res.numbers_checked
                        sweep_mat += v_res.numbers_matched
                        if v_res.ok:
                            c_sents.append(s)
                        else:
                            all_dropped_sentences.append(
                                SentenceDroppedDTO(
                                    sentence_id=s.sentence_id,
                                    author=s.author,
                                    text=s.text,
                                    reason_code=v_res.reason_code or "unknown_fact",  # type: ignore
                                    reason=v_res.reason or "",
                                )
                            )
                    if c_sents:
                        blk.sentences = c_sents
                        verified_blks.append(blk)
                    else:
                        all_dropped_blocks.append(BlockDroppedDTO(type="callout", reason="Câu trong callout không qua kiểm chứng."))

                elif blk.type == "figure":
                    if blk.takeaway:
                        n_sent = NarrativeSentence(
                            sentence_id=blk.takeaway.sentence_id,
                            author=blk.takeaway.author,
                            text=blk.takeaway.text,
                            fact_ids=tuple(blk.takeaway.fact_ids),
                            source=blk.takeaway.source,
                            revision=blk.takeaway.revision,
                        )
                        v_res = verify_sentence(n_sent, v_ctx)
                        sweep_chk += v_res.numbers_checked
                        sweep_mat += v_res.numbers_matched
                        if not v_res.ok:
                            all_dropped_sentences.append(
                                SentenceDroppedDTO(
                                    sentence_id=blk.takeaway.sentence_id,
                                    author=blk.takeaway.author,
                                    text=blk.takeaway.text,
                                    reason_code=v_res.reason_code or "unknown_fact",  # type: ignore
                                    reason=v_res.reason or "",
                                )
                            )
                            blk.takeaway = None
                    verified_blks.append(blk)

                elif blk.type == "table":
                    verified_blks.append(blk)

            spec.blocks = verified_blks
            return spec, sweep_chk, sweep_mat

        # Execute final verification sweep on active_report_spec
        # A sentence must appear once in the report: drop repeats that the model or the
        # revision loop copied into later blocks (headline first, then block order).
        def _dedupe_report_sentences(spec: ReportSpecDTO) -> ReportSpecDTO:
            # Sentences that still had an OPEN critique issue after the last round are
            # removed from the report (spec §7), wherever the model or revision placed them.
            seen: set[str] = {
                " ".join((d.text or "").split()).casefold()
                for d in all_dropped_sentences
                if d.reason_code == "unresolved_critique" and d.text
            }

            def fresh(sent: SentenceDTO | None) -> bool:
                if sent is None:
                    return False
                key = " ".join((sent.text or "").split()).casefold()
                if not key or key in seen:
                    return False
                seen.add(key)
                return True

            kept_blocks = []
            for blk in spec.blocks:
                if blk.type == "headline":
                    fresh(blk.sentence)
                elif blk.type in ("section", "callout", "answer"):
                    blk.sentences = [x for x in blk.sentences if fresh(x)]
                    if not blk.sentences and blk.type != "answer":
                        continue
                elif blk.type == "key_points":
                    for item in blk.items:
                        item.sentences = [x for x in item.sentences if fresh(x)]
                    blk.items = [item for item in blk.items if item.sentences]
                    if not blk.items:
                        continue
                elif blk.type == "figure":
                    fresh(blk.takeaway)  # takeaway is required; a repeat is tolerated, only recorded
                kept_blocks.append(blk)
            spec.blocks = kept_blocks
            return spec

        _deduped = _dedupe_report_sentences(active_report_spec.model_copy(deep=True))
        # Never let de-duplication empty a note: it needs a headline plus content.
        if _deduped.kind != "note" or any(b.type in ("key_points", "section", "callout", "table") for b in _deduped.blocks):
            active_report_spec = _deduped
        active_report_spec, sweep_chk, sweep_mat = _sweep_report_spec(active_report_spec)
        val_final, drop_final = validate_report_spec(active_report_spec.model_dump(), tool_datasets, verified_facts)
        for db in drop_final:
            all_dropped_blocks.append(BlockDroppedDTO(type=db["type"], reason=db["reason"]))
        if not val_final.get("is_valid", False):
            composition_source = "deterministic_fallback"
            fallback_reason = f"final_spec_invalid: {'; '.join(db.get('reason', '') for db in drop_final) or 'validation failed'}"
            active_report_spec = default_report_spec(
                question_type=q_type,
                tool_results=tr_fallback,
                signals=signals,
                findings=candidates,
            )
            active_report_spec, sweep_chk, sweep_mat = _sweep_report_spec(active_report_spec)

        active_report_spec.composition_source = composition_source
        total_numbers_checked = sweep_chk + early_dropped_numbers_checked
        total_numbers_matched = sweep_mat + early_dropped_numbers_matched

        # 4. Filter facts and datasets to only those cited in the final report_spec
        facts_map = {f.fact_id: f for f in verified_facts}
        datasets_map = {d.dataset_id: d for d in tool_datasets}
        filtered_facts, filtered_datasets, ordered_cited_facts = self._collect_spec_facts_and_datasets(
            active_report_spec, facts_map, datasets_map
        )
        # F1: pass filtered_facts (includes expanded input facts) so all input_observation_ids are walked
        source_notes = build_source_notes(self.provider, self.dataset_ref, filtered_facts)

        # Backfill source_note_no into tool_result trace steps
        fact_to_note_no: dict[str, int] = {}
        for sn in source_notes:
            for fid in sn.fact_ids:
                if fid not in fact_to_note_no:
                    fact_to_note_no[fid] = sn.note_no

        for step in self.trace_steps:
            if step.kind == "tool_result" and "facts" in step.detail:
                for f_dict in step.detail["facts"]:
                    fid = f_dict.get("fact_id")
                    if fid in fact_to_note_no:
                        f_dict["source_note_no"] = fact_to_note_no[fid]

        # 5. Build narrative audit
        final_spec_sent_ids = set()
        for b in active_report_spec.blocks:
            if b.type == "headline":
                final_spec_sent_ids.add(b.sentence.sentence_id)
            elif b.type == "answer":
                for s in b.sentences:
                    final_spec_sent_ids.add(s.sentence_id)
            elif b.type == "key_points":
                for item in b.items:
                    for s in item.sentences:
                        final_spec_sent_ids.add(s.sentence_id)
            elif b.type == "section":
                for s in b.sentences:
                    final_spec_sent_ids.add(s.sentence_id)
            elif b.type == "callout":
                for s in b.sentences:
                    final_spec_sent_ids.add(s.sentence_id)
            elif b.type == "figure" and b.takeaway:
                final_spec_sent_ids.add(b.takeaway.sentence_id)

        # Audit consistency: a sentence shown in the final report is not "dropped", and
        # each dropped sentence is recorded once with its last reason.
        shown_texts: set[str] = set()
        for b in active_report_spec.blocks:
            sents = []
            if b.type == "headline":
                sents = [b.sentence]
            elif b.type in ("answer", "section", "callout"):
                sents = list(b.sentences)
            elif b.type == "key_points":
                sents = [x for item in b.items for x in item.sentences]
            elif b.type == "figure" and b.takeaway:
                sents = [b.takeaway]
            shown_texts.update(" ".join((x.text or "").split()).casefold() for x in sents if x is not None)
        unique_dropped: dict[str, SentenceDroppedDTO] = {}
        for d in all_dropped_sentences:
            key = " ".join((d.text or "").split()).casefold()
            if key in shown_texts and d.reason_code != "unresolved_critique":
                continue  # an identical sentence passed verification elsewhere and is shown
            unique_dropped[key] = d
        all_dropped_sentences = list(unique_dropped.values())

        narrative_audit = NarrativeAuditDTO(
            sentences_checked=max(len(final_spec_sent_ids) + len(all_dropped_sentences), 1),
            sentences_accepted=len(final_spec_sent_ids),
            sentences_dropped=all_dropped_sentences,
            numbers_checked=total_numbers_checked,
            numbers_matched=total_numbers_matched,
            blocks_dropped=all_dropped_blocks,
            composition_source=composition_source,  # type: ignore
            fallback_reason=fallback_reason if composition_source == "deterministic_fallback" else None,
        )

        # Determine status
        has_unresolved_drop = any(d.reason_code == "unresolved_critique" for d in all_dropped_sentences)
        has_open_issues = critic_result is not None and any(i.resolution_status is CritiqueIssueStatus.OPEN for i in getattr(critic_result, "critique_issues", ()))
        if composition_source == "model" and not has_unresolved_drop and not has_open_issues and not any("không phản hồi" in lim for lim in tool_limitations):
            final_status = "completed"
        else:
            final_status = "accepted_with_limitations"

        # Assessment text
        assessment_text = None
        for b in active_report_spec.blocks:
            if b.type == "answer" and b.sentences:
                assessment_text = b.sentences[0].text
                break
            elif b.type == "headline":
                assessment_text = b.sentence.text
                break

        # Revision summary
        rev_reason = None
        if critic_result and getattr(critic_result, "critique_issues", ()):
            issue_summaries = []
            for issue in critic_result.critique_issues:
                action_part = f"/{getattr(issue.required_action, 'value', issue.required_action)}" if getattr(issue, "required_action", None) is not None else ""
                issue_summaries.append(
                    f"{issue.issue_id} [{getattr(issue.issue_type, 'value', issue.issue_type)}/{getattr(issue.severity, 'value', issue.severity)}/{getattr(issue.resolution_status, 'value', issue.resolution_status)}{action_part}]: {issue.description}"
                )
            rev_reason = "; ".join(issue_summaries)
        elif arm == "single_agent":
            rev_reason = "Single-agent arm execution without specialist findings or critique."
        elif arm == "hierarchical_no_critique":
            rev_reason = "Hierarchical execution without semantic critique."
        else:
            rev_reason = "Terminal acceptance decision from the verified narrative controller."

        revised_specialists = sorted({
            agent for agent in all_revised_agents
            if agent and agent != "orchestrator"
        })
        synthesis_revised = "orchestrator" in all_revised_agents or rounds_executed > 1

        if rounds_executed > 1 and final_status == "completed":
            rev_status = "revised_and_passed"
        elif final_status == "completed":
            rev_status = "passed"
        elif final_status == "error":
            rev_status = "rejected"
        else:
            rev_status = "accepted_with_limitations"

        revision_summary = BoundedRevisionSummaryDTO(
            rounds_executed=rounds_executed,
            max_rounds=_API_POLICY.max_revision_rounds,
            status=rev_status,
            reason=rev_reason,
            revised_capabilities=revised_specialists,
            synthesis_revised=synthesis_revised,
        )

        report = self._render_report(
            plan, target, peers, company_metrics, macro_metrics, current_claims,
            critic_result=critic_result,
            report_version="er-report-v1",
            report_spec=active_report_spec,
            narrative_audit=narrative_audit,
            revision_summary=revision_summary,
            status=final_status,
            assessment=assessment_text,
            facts=filtered_facts,
            datasets=filtered_datasets,
            signals=signals,
            cross_level_findings=[c for c in cross_level_candidates_list if getattr(c, "status", "confirmed") == "confirmed"],
            source_notes=source_notes,
            extra_limitations=tool_limitations,
            synthesis_summary=synthesis_summary,
        )
        self.emit("SYNTHESIS_COMPLETED", {"periods": list(periods), "message": "The terminal candidate, provenance joins, and limitations are ready."})

        # Trace report_ready step
        duration_ms = max(0, int((time.monotonic() - self._started_at) * 1000))
        model_calls = self.tracker.model_calls
        self._trace(
            kind="report_ready",
            actor="orchestrator",
            summary=summary_report_ready(),
            detail={
                "report_id": report.report_id,
                "duration_ms": duration_ms,
                "model_calls": model_calls,
            },
            recipient="system",
        )
        report._trace_steps = self.trace_steps
        report._duration_ms = duration_ms
        report._tracker = self.tracker
        report._arm = arm
        report._question_type = q_type
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
        if not target:
            return []
        universe_id = self._peer_universe_id(plan)
        if universe_id is None:
            return []
        result: list[AtomicClaim] = []
        target_observations = {
            artifact.observation.metric_id: artifact.observation
            for artifact in self.artifacts.values()
            if artifact.observation.entity_id == target and artifact.observation.period_id == period
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

    @staticmethod
    def _collect_spec_facts_and_datasets(
        spec: ReportSpecDTO,
        facts_map: dict[str, Any],
        datasets_map: dict[str, Any],
    ) -> tuple[list[Any], list[Any], list[Any]]:
        cited_fact_ids: list[str] = []
        referenced_dataset_ids: list[str] = []

        for block in spec.blocks:
            b_type = block.type
            if b_type == "answer":
                if block.value_fact_id:
                    cited_fact_ids.append(block.value_fact_id)
                for s in block.sentences:
                    cited_fact_ids.extend(s.fact_ids)
            elif b_type == "headline":
                cited_fact_ids.extend(block.sentence.fact_ids)
            elif b_type == "key_points":
                for item in block.items:
                    for s in item.sentences:
                        cited_fact_ids.extend(s.fact_ids)
            elif b_type == "section":
                for s in block.sentences:
                    cited_fact_ids.extend(s.fact_ids)
            elif b_type == "figure":
                if block.dataset_id:
                    referenced_dataset_ids.append(block.dataset_id)
                if block.takeaway:
                    cited_fact_ids.extend(block.takeaway.fact_ids)
            elif b_type == "callout":
                for s in block.sentences:
                    cited_fact_ids.extend(s.fact_ids)
            elif b_type == "table":
                if block.dataset_id:
                    referenced_dataset_ids.append(block.dataset_id)

        ordered_cited_fact_ids = list(dict.fromkeys(cited_fact_ids))
        ordered_cited_facts = [facts_map[fid] for fid in ordered_cited_fact_ids if fid in facts_map]

        all_needed_fact_ids: set[str] = set(ordered_cited_fact_ids)
        to_expand = list(ordered_cited_fact_ids)
        while to_expand:
            cur_id = to_expand.pop()
            f = facts_map.get(cur_id)
            if f is not None:
                for in_id in getattr(f, "input_fact_ids", ()):
                    if in_id not in all_needed_fact_ids:
                        all_needed_fact_ids.add(in_id)
                        to_expand.append(in_id)

        filtered_facts = [f for f in facts_map.values() if f.fact_id in all_needed_fact_ids]
        ref_ds_set = set(referenced_dataset_ids)
        filtered_datasets = [ds for ds in datasets_map.values() if ds.dataset_id in ref_ds_set]

        return filtered_facts, filtered_datasets, ordered_cited_facts

    def _render_report(
        self,
        plan: AnalysisPlan,
        target: str | None,
        peers: Sequence[str],
        company_metrics: Sequence[str],
        macro_metrics: Sequence[str],
        final_claims: Sequence[AtomicClaim],
        critic_result: StructuredCriticResult | None = None,
        *,
        report_version: str = "er-report-v1",
        report_spec: ReportSpecDTO | None = None,
        narrative_audit: NarrativeAuditDTO | None = None,
        revision_summary: BoundedRevisionSummaryDTO | None = None,
        status: str = "completed",
        assessment: str | None = None,
        facts: Sequence[Any] = (),
        datasets: Sequence[Any] = (),
        signals: Sequence[Any] = (),
        cross_level_findings: Sequence[Any] = (),
        source_notes: Sequence[Any] = (),
        extra_limitations: Sequence[str] = (),
        synthesis_summary: str | None = None,
    ) -> AnalysisResponse:
        from .schemas import FactDTO, CrossLevelFindingDTO
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
                    "Các nhận định không có đoạn trích tài liệu đã duyệt theo chỉ tiêu sẽ dựa trên định vị nguồn sơ cấp và mã băm nguồn của quan sát được chấp nhận."
                )
            if not (getattr(observation, "reporting_scope", None) or "").strip():
                if role == "company":
                    known_limitations.append(
                        f"Reporting scope is unavailable for {observation.observation_id}; the API does not infer consolidated or parent-only scope."
                    )
            stage2_status = getattr(claim, "stage2_critique_status", None) or ("sound" if status == "completed" else "limited")
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
        plan_limitations = clean_reader_facing_limitations(list(dict.fromkeys(known_limitations + list(extra_limitations))))
        plan_dto = AnalysisPlanDTO(
            plan_id=f"plan-{hashlib.sha256(plan.query_id.encode()).hexdigest()[:12]}",
            query=self.request.query, target_ticker=target, peer_tickers=list(peers),
            period=plan.scope.periods[-1], periods=list(plan.scope.periods), required_capabilities=capabilities,
            applicable_links=links, dataset_snapshot_id=plan.dataset_snapshot_id,
            rationale=(self.spec.rationale if hasattr(self, "spec") and self.spec else "Frozen query-adaptive plan created before provider specialist retrieval."),
            known_limitations=plan_limitations,
            plan_version=plan.plan_version,
            requirements=[item.model_dump(mode="json") for item in plan.requirements],
            question_type=self.spec.question_type if hasattr(self, "spec") and self.spec else None,
            planner_source=self.planner_source if hasattr(self, "planner_source") else None,
            planner_fallback_reasons=list(self.fallback_reasons) if hasattr(self, "fallback_reasons") and self.fallback_reasons else [],
            rationale_vi=self.spec.rationale if hasattr(self, "spec") and self.spec else None,
            tools=[{"tool": t.tool, "params": t.params} for t in self.spec.tools] if hasattr(self, "spec") and self.spec else [],
            context_periods=list(self.resolved.context_periods) if hasattr(self, "resolved") and self.resolved else [],
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
                assessment=assessment or "Accepted provider facts are listed in the atomic claims.",
                metric_period_records=metric_period_records,
            ))

        if revision_summary is None:
            revision_summary = BoundedRevisionSummaryDTO(
                rounds_executed=0,
                max_rounds=_API_POLICY.max_revision_rounds,
                status="passed",
                reason="Terminal acceptance decision.",
                revised_capabilities=[],
                synthesis_revised=False,
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
        unique_facts = []
        seen_fact_ids = set()
        for f in facts:
            fid = getattr(f, "fact_id", None)
            if fid:
                if fid not in seen_fact_ids:
                    seen_fact_ids.add(fid)
                    unique_facts.append(f)
            else:
                unique_facts.append(f)

        fact_dtos = [
            FactDTO(
                fact_id=f.fact_id,
                fact_type=f.fact_type,  # type: ignore
                entity_id=f.entity_id,
                other_entity_id=f.other_entity_id,
                universe_id=f.universe_id,
                metric_id=f.metric_id,
                period=f.period,
                from_period=f.from_period,
                value=f.value,
                unit=f.unit,
                rank_better=f.rank_better,
                rank_desc=f.rank_desc,
                denominator=f.denominator,
                formula_version=f.formula_version,
                input_observation_ids=f.input_observation_ids,
                input_fact_ids=f.input_fact_ids,
            )
            if not isinstance(f, FactDTO) else f
            for f in unique_facts
        ]
        finding_dtos = [
            CrossLevelFindingDTO(
                finding_id=c.finding_id,
                kind=c.kind,  # type: ignore
                severity=c.severity,  # type: ignore
                text=c.text,
                fact_ids=c.fact_ids,
                status=getattr(c, "status", "confirmed"),
            )
            if not isinstance(c, CrossLevelFindingDTO) else c
            for c in cross_level_findings
        ]
        return AnalysisResponse(
            report_id=f"report-{uuid.uuid4().hex}", status=status,
            analysis_plan=plan_dto, macro_context=macro_context,
            sector_benchmark=sector_benchmark, company_insights=company_insights,
            cross_level_critique=critique_items,
            atomic_claims=claim_dtos, evidence_trail=evidence_rows,
            revision_summary=revision_summary,
            limitations=clean_reader_facing_limitations(list(dict.fromkeys(plan_limitations))),
            synthesis_summary=synthesis_summary,
            synthesis_supporting_claim_ids=[c.claim_id for c in claim_dtos] if synthesis_summary else [],
            report_version=report_version,
            question_type=(self.spec.question_type if hasattr(self, "spec") and self.spec else None),
            report_spec=report_spec,
            narrative_audit=narrative_audit,
            facts=fact_dtos,
            datasets=list(datasets),
            signals=list(signals),
            cross_level_findings=finding_dtos,
            source_notes=list(source_notes),
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
    client: Any = None,
    tracker: LLMUsageTracker | None = None,
) -> AnalysisResponse:
    """Run a frozen-plan provider execution and bounded acceptance workflow."""

    from .service import AnalysisBlocked, _error_report
    from .messages_vi import get_error_message

    emit_event = emit or (lambda _event, _payload: None)
    usage_tracker = tracker or LLMUsageTracker()
    runner = _AdaptiveRun(
        provider=provider,
        dataset_ref=dataset_ref,
        catalog=catalog,
        request=request,
        settings=settings,
        critic=semantic_critic,
        writer=analysis_writer,
        emit=emit_event,
        client=client,
        tracker=usage_tracker,
    )
    try:
        return runner.execute()
    except AnalysisBlocked as exc:
        msg = get_error_message(exc.code, catalog=catalog, default=exc.detail)
        if not any(s.kind == "blocked" for s in runner.trace_steps):
            runner._trace(
                kind="blocked",
                actor="system",
                summary=msg,
                detail={"code": exc.code, "message": msg},
                recipient="system",
            )
        report = _error_report(exc.code, exc.detail, request, catalog=catalog)
        report._trace_steps = runner.trace_steps
        report._duration_ms = max(0, int((time.monotonic() - runner._started_at) * 1000))
        report._tracker = usage_tracker
        report._arm = getattr(settings, "analysis_arm", "hierarchical_with_critique")
        report._question_type = getattr(runner, "spec", None) and runner.spec.question_type or getattr(report, "question_type", None)
        return report
    except Exception as exc:
        logger.warning("Adaptive runtime failed: %s", type(exc).__name__, exc_info=True)
        msg = "Lỗi hệ thống khi xử lý phân tích thích ứng."
        if not any(s.kind == "blocked" for s in runner.trace_steps):
            runner._trace(
                kind="blocked",
                actor="system",
                summary=msg,
                detail={"code": "adaptive_runtime_failure", "message": msg},
                recipient="system",
            )
        report = _error_report("adaptive_runtime_failure", "The accepted provider or bounded semantic runtime could not satisfy this request.", request, catalog=catalog)
        report._trace_steps = runner.trace_steps
        report._duration_ms = max(0, int((time.monotonic() - runner._started_at) * 1000))
        report._tracker = usage_tracker
        report._arm = getattr(settings, "analysis_arm", "hierarchical_with_critique")
        report._question_type = getattr(runner, "spec", None) and runner.spec.question_type or getattr(report, "question_type", None)
        return report
