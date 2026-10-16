"""Pydantic v2 schemas for the thesis API analysis service.

These models strictly adhere to contracts/openapi.json and contracts/mock-data.json.
"""

from __future__ import annotations

import math
import re
from typing import Annotated, Any, List, Literal, Optional, Union
from pydantic import BaseModel, ConfigDict, Field, PrivateAttr, field_validator, model_serializer, model_validator



_CANONICAL_PERIOD_RE = re.compile(r"^(?P<quarter>20\d{2}_Q[1-4]|FY\d{4})$", re.IGNORECASE)


def _canonical_period(value: str) -> str:
    candidate = value.strip().upper()
    if not _CANONICAL_PERIOD_RE.fullmatch(candidate):
        raise ValueError("periods must use canonical YYYY_Qn or FYyyyy values")
    return candidate


def _period_order(value: str) -> float:
    match = re.fullmatch(r"(20\d{2})_Q([1-4])", value)
    if match:
        return int(match.group(1)) * 4 + int(match.group(2)) - 1
    fiscal_year = re.fullmatch(r"FY(\d{4})", value)
    if fiscal_year:
        return int(fiscal_year.group(1)) * 4 + 3.5
    raise ValueError("unsupported period")


class AnalysisRequest(BaseModel):
    """Natural language analysis query with optional target, peer universe, and period filters."""

    model_config = ConfigDict(extra="ignore")
    _periods_explicit: bool = PrivateAttr(default=False)

    query: str = Field(
        ...,
        description="Natural language analytical question in Vietnamese or English",
        examples=["Phan tich ROE va chat luong tai san (NPL) cua ACB va TCB nam 2024"],
    )
    target_ticker: Optional[str] = Field(
        default=None,
        description="Target bank ticker symbol",
        examples=["ACB"],
    )
    peer_tickers: List[str] = Field(
        default_factory=list,
        description="List of peer comparison bank tickers",
        examples=[["TCB", "MBB"]],
    )
    period: Optional[str] = Field(
        default=None,
        description="Analysis period or fiscal year (e.g., '2024', '2024_Q4')",
        examples=["2024_Q4"],
    )
    periods: Optional[List[str]] = Field(
        default=None,
        min_length=1,
        max_length=4,
        description="Exact ordered period scope for a Company trend; the legacy period is normalized to the final anchor.",
        examples=[["2024_Q1", "2024_Q2", "2024_Q3", "2024_Q4"]],
    )
    upload_id: Optional[str] = Field(
        default=None,
        description="Optional uploaded dataset identifier for user-supplied bank analysis",
        examples=["ctg_upload_123"],
    )

    @field_validator("period")
    @classmethod
    def normalize_legacy_period(cls, value: str | None) -> str | None:
        if value is None:
            return None
        candidate = value.strip()
        if re.fullmatch(r"\d{4}", candidate):
            return candidate
        return _canonical_period(candidate)

    @field_validator("periods")
    @classmethod
    def normalize_period_list(cls, values: list[str] | None) -> list[str] | None:
        return [_canonical_period(value) for value in values] if values is not None else None

    @model_validator(mode="after")
    def normalize_period_scope(self) -> "AnalysisRequest":
        self._periods_explicit = "periods" in self.model_fields_set
        if self.periods is None:
            if self.period is not None:
                self.periods = [self.period]
            return self
        if len(set(self.periods)) != len(self.periods):
            raise ValueError("periods must be unique")
        order = [_period_order(item) for item in self.periods]
        if any(current <= prior for prior, current in zip(order, order[1:])):
            raise ValueError("periods must be strictly increasing chronologically")
        anchor = self.periods[-1]
        if self.period is not None and self.period != anchor:
            raise ValueError("period must equal the final item of periods")
        self.period = anchor
        return self


class AnalysisPlanDTO(BaseModel):
    """Query-adaptive analysis execution plan."""

    model_config = ConfigDict(extra="allow")

    plan_id: str = Field(..., description="Unique plan identifier", examples=["plan-2024-acb-001"])
    query: str = Field(..., description="Original user analytical query")
    target_ticker: Optional[str] = Field(default=None, description="Target bank ticker", examples=["ACB"])
    peer_tickers: List[str] = Field(
        default_factory=list, description="Peer comparison bank tickers", examples=[["TCB", "MBB"]]
    )
    period: Optional[str] = Field(default=None, description="Analysis period declared by the selected snapshot", examples=["2024_Q4"])
    periods: List[str] = Field(default_factory=list, description="Exact frozen ordered period scope; period is the final anchor.")
    required_capabilities: List[str] = Field(
        ...,
        description="Required specialist capabilities (macro, sector, company)",
        examples=[["company", "sector"]],
    )
    applicable_links: List[str] = Field(
        default_factory=list,
        description="Applicable cross-level linkages (peer_comparison, macro_transmission, cross_level_stress)",
        examples=[["peer_comparison"]],
    )
    dataset_snapshot_id: str = Field(
        ..., description="Dataset snapshot identifier bound to the plan", examples=["gold-snapshot-2024-q4"]
    )
    rationale: Optional[str] = Field(default=None, description="Execution plan rationale")
    known_limitations: List[str] = Field(
        default_factory=list, description="Known analytical limitations or scope boundaries"
    )
    question_type: Optional[str] = Field(default=None, description="Analytical question type")
    planner_source: Optional[str] = Field(default=None, description="Planner source: model or rules")
    planner_fallback_reasons: List[str] = Field(
        default_factory=list, description="Fallback reasons if rules planner was used"
    )
    rationale_vi: Optional[str] = Field(default=None, description="Vietnamese explanation of the chosen plan")
    tools: List[dict[str, Any]] = Field(default_factory=list, description="List of planned tool invocations")
    context_periods: List[str] = Field(default_factory=list, description="Context periods within the same year")


class MacroContextDTO(BaseModel):
    """Macroeconomic context indicator observations and policy background."""

    model_config = ConfigDict(extra="allow")

    sbv_policy_rate: Optional[float] = Field(
        default=None,
        description="State Bank of Vietnam refinancing/policy rate in percent",
    )
    system_credit_growth: Optional[float] = Field(
        default=None,
        description="System-wide credit growth percentage",
    )
    interest_rate_trend: Optional[str] = Field(
        default=None,
        description="Qualitative or directional assessment of interest rate conditions",
    )
    source: Optional[str] = Field(
        default=None,
        description="Authoritative source reference for macroeconomic facts",
    )


class PeerBenchmarkRecordDTO(BaseModel):
    """Provider-bound audit metadata for one peer metric benchmark."""

    model_config = ConfigDict(extra="forbid")

    metric_id: str
    benchmark_observation_id: str
    value: float
    unit: str
    period: str
    period_basis: str
    reporting_scope: str
    peer_universe_id: str
    requested_peer_entity_ids: List[str]
    eligible_peer_entity_ids: List[str]
    aggregation_method: str
    requested_denominator: int
    eligible_denominator: int
    input_observation_ids: List[str]
    missing_members: List[dict[str, Any]] = Field(default_factory=list)


class SectorBenchmarkDTO(BaseModel):
    """Sector benchmark medians across banking peers."""

    model_config = ConfigDict(extra="allow")

    sector: str = Field(default="Banking", description="Sector classification")
    peer_median_roe: Optional[float] = Field(
        default=None,
        description="Peer median return on equity (ROE) percentage",
    )
    peer_median_nim: Optional[float] = Field(
        default=None,
        description="Peer median net interest margin (NIM) percentage",
    )
    peer_median_npl: Optional[float] = Field(
        default=None,
        description="Peer median non-performing loan (NPL) ratio percentage",
    )
    peer_median_cir: Optional[float] = Field(
        default=None,
        description="Peer median cost-to-income ratio (CIR) percentage",
    )
    peer_median_casa: Optional[float] = Field(
        default=None,
        description="Peer median current account savings account (CASA) ratio percentage",
    )
    peer_median_car: Optional[float] = Field(
        default=None,
        description="Peer median capital adequacy ratio (CAR) percentage",
    )
    peer_median_ldr: Optional[float] = Field(
        default=None,
        description="Peer median loan-to-deposit ratio (LDR) percentage",
    )
    benchmarks: List[PeerBenchmarkRecordDTO] = Field(
        default_factory=list,
        description="Authoritative per-metric benchmark provenance and denominator records",
    )


class CompanyInsightDTO(BaseModel):
    """Financial CAMEL indicators and synthesized assessment for a specific bank."""

    model_config = ConfigDict(extra="allow")

    ticker: str = Field(..., description="Bank ticker symbol")
    roe: Optional[float] = Field(default=None, description="Return on equity (%)")
    nim: Optional[float] = Field(default=None, description="Net interest margin (%)")
    npl: Optional[float] = Field(default=None, description="Non-performing loans ratio (%)")
    cir: Optional[float] = Field(default=None, description="Cost-to-income ratio (%)")
    casa: Optional[float] = Field(default=None, description="CASA deposit ratio (%)")
    car: Optional[float] = Field(default=None, description="Capital adequacy ratio (%)")
    ldr: Optional[float] = Field(default=None, description="Loan-to-deposit ratio (%)")
    assessment: str = Field(..., description="Synthesized analytical commentary")
    metric_period_records: List["CompanyMetricPeriodRecordDTO"] = Field(
        default_factory=list,
        description="Authoritative facts or explicit missingness ordered by frozen period, then requested metric.",
    )


class CompanyMetricPeriodRecordDTO(BaseModel):
    """One Company fact or accepted missing cell at one exact period."""

    model_config = ConfigDict(extra="forbid")

    metric_id: str = Field(min_length=1)
    period: str = Field(min_length=1)
    validation_status: Literal["valid", "missing"]
    value: Optional[float] = None
    unit: Optional[str] = None
    period_basis: Optional[str] = None
    reporting_scope: Optional[str] = None
    scope_status: Optional[Literal["verified", "unavailable"]] = None
    observation_id: Optional[str] = None
    source_id: Optional[str] = None
    claim_id: Optional[str] = None
    missing_reason: Optional[str] = None

    @model_validator(mode="after")
    def validate_record_state(self) -> "CompanyMetricPeriodRecordDTO":
        if self.validation_status == "valid":
            if (
                self.value is None
                or not math.isfinite(self.value)
                or not self.unit
                or not self.unit.strip()
                or not self.period_basis
                or not self.period_basis.strip()
                or (
                    (
                        self.scope_status == "verified"
                        and (not self.reporting_scope or not self.reporting_scope.strip())
                    )
                    or (self.scope_status == "unavailable" and self.reporting_scope is not None)
                    or self.scope_status not in {"verified", "unavailable"}
                )
                or not self.observation_id
                or not self.observation_id.strip()
                or not self.source_id
                or not self.source_id.strip()
                or not self.claim_id
                or not self.claim_id.strip()
                or self.missing_reason is not None
            ):
                raise ValueError("valid metric-period records require finite facts and exact provenance")
        elif (
            self.value is not None
            or self.unit is not None
            or self.period_basis is not None
            or self.reporting_scope is not None
            or self.scope_status is not None
            or self.observation_id is not None
            or self.source_id is not None
            or self.claim_id is not None
            or not self.missing_reason
        ):
            raise ValueError("missing metric-period records require null facts and a reason")
        return self

    @model_serializer(mode="wrap")
    def serialize_contract_nulls(self, handler):
        payload = handler(self)
        for field_name in (
            "metric_id",
            "period",
            "validation_status",
            "value",
            "unit",
            "period_basis",
            "reporting_scope",
            "scope_status",
            "observation_id",
            "source_id",
            "claim_id",
            "missing_reason",
        ):
            payload.setdefault(field_name, getattr(self, field_name))
        return payload


class CritiqueItemDTO(BaseModel):
    """Cross-level hierarchical critique finding across macro, sector, and company levels."""

    model_config = ConfigDict(extra="allow")

    dimension: str = Field(..., description="Critique analytical dimension")
    finding: str = Field(..., description="Detailed critique finding and discrepancy analysis")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Confidence score [0.0 - 1.0]")
    evidence_ref: Optional[str] = Field(default=None, description="Evidence identifier or citation reference")


class EvidenceTrailDTO(BaseModel):
    """Verifiable source ground truth citation trail for an observation."""

    model_config = ConfigDict(extra="allow")

    evidence_id: Optional[str] = Field(default=None, description="Evidence identifier")
    claim_id: Optional[str] = Field(default=None, description="Claim supported by this source-locator or document-evidence row")
    observation_id: Optional[str] = Field(default=None, description="Accepted observation represented by this provenance row")
    source_id: Optional[str] = Field(default=None, description="Accepted primary source identifier")
    source_url: Optional[str] = Field(default=None, description="URL of the accepted primary source")
    metric: str = Field(..., description="Financial metric or ratio name")
    ticker: str = Field(..., description="Target bank ticker")
    period: str = Field(..., description="Reporting period")
    value: Optional[float] = Field(default=None, description="Reported or observed numeric metric value")
    source_doc: str = Field(..., description="Title or locator of the authoritative filing/disclosure")
    table_locator: Optional[str] = Field(default=None, description="Table, section, or statement locator")
    provenance_hash: Optional[str] = Field(default=None, description="Cryptographic provenance hash")


class AtomicClaimDTO(BaseModel):
    """Atomic verifiable factual or synthesized claim with evidence refs."""

    model_config = ConfigDict(extra="allow")

    claim_id: str = Field(..., description="Unique claim identifier", examples=["claim-acb-roe-001"])
    observation_id: Optional[str] = Field(default=None, description="Accepted observation supporting this numeric claim")
    input_observation_ids: List[str] = Field(default_factory=list, description="Accepted input observations for a derived metric")
    formula_version: Optional[str] = Field(default=None, description="Formula version used to derive this metric, when applicable")
    capability: str = Field(
        ...,
        description="Producing capability (macro, sector, company, synthesis)",
        examples=["company"],
    )
    ticker: Optional[str] = Field(default=None, description="Associated ticker symbol", examples=["ACB"])
    metric: Optional[str] = Field(default=None, description="Target financial metric", examples=["ROE"])
    period: Optional[str] = Field(default=None, description="Reference period", examples=["2024"])
    statement: str = Field(..., description="Claim statement text")
    claim_type: str = Field(
        default="factual_observation",
        description="Claim classification (factual_observation, peer_comparison, policy_transmission, synthesis_evaluation)",
    )
    evidence_refs: List[str] = Field(
        default_factory=list, description="IDs of supporting evidence items"
    )
    confidence: Optional[float] = Field(default=None, ge=0.0, le=1.0, description="Model confidence, when actually assessed")
    stage1_status: str = Field(
        ...,
        description="Stage 1 deterministic validation status (accepted, rejected)",
    )
    stage2_critique_status: Optional[str] = Field(
        default=None,
        description="Stage 2 semantic critique status (sound, revised, limited)",
    )


class BoundedRevisionSummaryDTO(BaseModel):
    """Summary of bounded revision cycles and convergence."""

    model_config = ConfigDict(extra="allow")

    rounds_executed: int = Field(default=0, description="Number of revision rounds executed")
    max_rounds: int = Field(default=2, description="Maximum allowed revision rounds")
    status: str = Field(
        default="passed",
        description="Convergence status (passed, revised_and_passed, accepted_with_limitations, rejected)",
    )
    reason: Optional[str] = Field(default=None, description="Rationale for critique or acceptance")
    revised_capabilities: List[str] = Field(
        default_factory=list, description="Specialist capabilities that underwent revision"
    )
    synthesis_revised: bool = Field(
        default=False,
        description="Whether the report-level synthesis artifact changed during bounded revision",
    )


class ObservableActivityDTO(BaseModel):
    """Observable intermediate specialist activity for UI streaming."""

    model_config = ConfigDict(extra="allow")

    id: str = Field(..., description="Unique activity identifier")
    timestamp: Optional[str] = Field(default=None, description="Activity timestamp")
    description: str = Field(..., description="Human-readable description of the operation")
    type: str = Field(
        ...,
        description="Activity type (DATA_RETRIEVAL, VALIDATION, INSIGHT_GENERATION, REVISION)",
    )


class AnalysisSessionEventDTO(BaseModel):
    """Real-time SSE event frame adhering strictly to OpenAPI specification."""

    model_config = ConfigDict(extra="allow", populate_by_name=True)

    event_id: str = Field(..., alias="eventId", description="Unique event identifier")
    sequence: int = Field(..., description="1-indexed sequence number")
    occurred_at_ms: int = Field(..., alias="occurredAtMs", description="Elapsed milliseconds from request start")
    type: str = Field(..., description="Analysis session event type")
    payload: dict[str, Any] = Field(default_factory=dict, description="Event-specific payload")



QuestionType = Literal[
    "lookup",
    "company_profile",
    "ranking",
    "trend",
    "head_to_head",
    "sector_theme",
    "relationship",
]


class MetricPresentationDTO(BaseModel):
    model_config = ConfigDict(extra="allow")

    id: str
    acronym: str
    label: str
    shortLabel: str
    unit: str
    direction: Literal["higher_is_better", "lower_is_better", "neutral"]
    decimals: int
    group: str
    groupLabel: str


class QuestionTypeInfoDTO(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: QuestionType
    label: str
    example: str


class CoverageItemDTO(BaseModel):
    model_config = ConfigDict(extra="forbid")

    entity_id: str
    period_id: str
    metrics: List[str] = Field(default_factory=list)


class CapabilitiesDTO(BaseModel):
    model_config = ConfigDict(extra="allow")

    snapshotId: Optional[str] = None
    datasetId: Optional[str] = None
    datasetSnapshotId: Optional[str] = None
    dataset_snapshot_id: Optional[str] = None
    analysis_available: Optional[bool] = None
    implemented_capabilities: List[str] = Field(default_factory=list)
    database_status: Optional[str] = None
    entities: List[dict[str, Any]] = Field(default_factory=list)
    periods: List[dict[str, Any]] = Field(default_factory=list)
    metrics: List[MetricPresentationDTO] = Field(default_factory=list)
    coverage: List[CoverageItemDTO] = Field(default_factory=list)
    topics: List[dict[str, Any]] = Field(default_factory=list)
    peerUniverse: Optional[dict[str, Any]] = None
    macro: Optional[dict[str, Any]] = None
    suggestedQuestions: List[str] = Field(default_factory=list)
    questionTypes: List[QuestionTypeInfoDTO] = Field(default_factory=list)
    readiness: Optional[str] = None

    @property
    def question_types(self) -> List[QuestionTypeInfoDTO]:
        return self.questionTypes


FactType = Literal[
    "value",
    "peer_median",
    "peer_rank",
    "gap_to_median",
    "delta",
    "median_delta",
    "pairwise_gap",
    "spread",
    "ratio_to_median",
    "derived_ratio",
    "lead_count",
    "outlier",
]


class FactDTO(BaseModel):
    model_config = ConfigDict(extra="forbid")

    fact_id: str
    fact_type: FactType
    entity_id: Optional[str] = None
    other_entity_id: Optional[str] = None
    universe_id: Optional[str] = None
    metric_id: str
    period: str
    from_period: Optional[str] = None
    value: Optional[float] = None
    unit: str
    rank_better: Optional[int] = None
    rank_desc: Optional[int] = None
    denominator: Optional[int] = None
    formula_version: str
    input_observation_ids: List[str] = Field(default_factory=list)
    input_fact_ids: List[str] = Field(default_factory=list)


class ProducedByDTO(BaseModel):
    model_config = ConfigDict(extra="forbid")

    tool: str
    agent: str


class DatasetRowDTO(BaseModel):
    model_config = ConfigDict(extra="forbid")

    entity_id: str
    metric_id: str
    period: str
    status: Literal["valid", "missing"]
    value: Optional[float] = None
    observation_id: Optional[str] = None
    rank_better: Optional[int] = None
    rank_desc: Optional[int] = None
    missing_reason: Optional[str] = None


class ReferenceLineDTO(BaseModel):
    model_config = ConfigDict(extra="forbid")

    kind: str
    metric_id: str
    period: str
    value: float
    fact_id: Optional[str] = None


DatasetShape = Literal[
    "kpi",
    "ranked_list",
    "series",
    "series_multi",
    "peer_table",
    "comparison_table",
    "paired",
]


class DatasetDTO(BaseModel):
    model_config = ConfigDict(extra="forbid")

    dataset_id: str
    shape: DatasetShape
    title: str
    produced_by: ProducedByDTO
    metric_ids: List[str] = Field(default_factory=list)
    periods: List[str] = Field(default_factory=list)
    highlight_entity_ids: List[str] = Field(default_factory=list)
    rows: List[DatasetRowDTO] = Field(default_factory=list)
    reference_lines: List[ReferenceLineDTO] = Field(default_factory=list)
    allowed_charts: List[str] = Field(default_factory=list)


SentenceAuthor = Literal["orchestrator", "company", "sector", "macro", "critic", "system"]
SentenceSource = Literal["model", "deterministic_fallback"]


class SentenceDTO(BaseModel):
    model_config = ConfigDict(extra="forbid")

    sentence_id: str
    text: str
    fact_ids: List[str] = Field(default_factory=list)
    author: SentenceAuthor
    source: SentenceSource
    revision: int = 0


class AnswerBlockDTO(BaseModel):
    model_config = ConfigDict(extra="forbid")

    type: Literal["answer"] = "answer"
    value_fact_id: str
    sentences: List[SentenceDTO] = Field(default_factory=list)


class HeadlineBlockDTO(BaseModel):
    model_config = ConfigDict(extra="forbid")

    type: Literal["headline"] = "headline"
    sentence: SentenceDTO


class KeyPointItemDTO(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: str
    sentences: List[SentenceDTO] = Field(default_factory=list)


class KeyPointsBlockDTO(BaseModel):
    model_config = ConfigDict(extra="forbid")

    type: Literal["key_points"] = "key_points"
    items: List[KeyPointItemDTO] = Field(default_factory=list)


class SectionBlockDTO(BaseModel):
    model_config = ConfigDict(extra="forbid")

    type: Literal["section"] = "section"
    title: str
    sentences: List[SentenceDTO] = Field(default_factory=list)


ChartType = Literal[
    "kpi_strip",
    "ranked_bar",
    "line_trend",
    "small_multiples",
    "scatter",
    "rank_heatmap",
    "grouped_bar",
    "comparison_table",
]


class FigureBlockDTO(BaseModel):
    model_config = ConfigDict(extra="forbid")

    type: Literal["figure"] = "figure"
    figure_no: int
    chart: ChartType
    dataset_id: str
    title: str
    takeaway: SentenceDTO


class CalloutBlockDTO(BaseModel):
    model_config = ConfigDict(extra="forbid")

    type: Literal["callout"] = "callout"
    tone: Literal["notice", "warning"]
    title: str
    finding_id: Optional[str] = None
    sentences: List[SentenceDTO] = Field(default_factory=list)


class TableBlockDTO(BaseModel):
    model_config = ConfigDict(extra="forbid")

    type: Literal["table"] = "table"
    dataset_id: str
    title: str


ReportBlockDTO = Annotated[
    Union[
        AnswerBlockDTO,
        HeadlineBlockDTO,
        KeyPointsBlockDTO,
        SectionBlockDTO,
        FigureBlockDTO,
        CalloutBlockDTO,
        TableBlockDTO,
    ],
    Field(discriminator="type"),
]


class ReportSpecDTO(BaseModel):
    model_config = ConfigDict(extra="forbid")

    kind: Literal["answer_card", "note"]
    note_label: Optional[str] = None
    composition_source: Optional[Literal["model", "deterministic_fallback"]] = None
    blocks: List[ReportBlockDTO] = Field(default_factory=list)


SignalVerdict = Literal["above_peers", "in_line", "below_peers", "mixed", "insufficient_data"]


class SignalDTO(BaseModel):
    model_config = ConfigDict(extra="forbid")

    group: str
    label: str
    verdict: SignalVerdict
    metric_ids: List[str] = Field(default_factory=list)
    fact_ids: List[str] = Field(default_factory=list)


class CrossLevelFindingDTO(BaseModel):
    model_config = ConfigDict(extra="forbid")

    finding_id: str
    kind: Literal["divergent_signals", "counter_trend", "cross_metric_extreme"]
    severity: Literal["notice", "warning"]
    text: str
    fact_ids: List[str] = Field(default_factory=list)
    status: Literal["confirmed", "dismissed"]


SentenceDropReason = Literal[
    "missing_fact_citation",
    "unknown_fact",
    "number_mismatch",
    "unit_mismatch",
    "rank_mismatch",
    "count_mismatch",
    "period_not_cited",
    "entity_not_in_plan",
    "trend_without_delta",
    "trend_direction_mismatch",
    "comparison_direction_mismatch",
    "causal_language",
    "investment_advice",
    "unresolved_critique",
]


class SentenceDroppedDTO(BaseModel):
    model_config = ConfigDict(extra="forbid")

    sentence_id: str
    author: str
    text: str
    fact_ids: List[str] = Field(default_factory=list)
    reason_code: SentenceDropReason
    reason: str


class BlockDroppedDTO(BaseModel):
    model_config = ConfigDict(extra="forbid")

    type: str
    reason: str


class NarrativeAuditDTO(BaseModel):
    model_config = ConfigDict(extra="forbid")

    sentences_checked: int
    sentences_accepted: int
    sentences_dropped: List[SentenceDroppedDTO] = Field(default_factory=list)
    numbers_checked: int
    numbers_matched: int
    blocks_dropped: List[BlockDroppedDTO] = Field(default_factory=list)
    composition_source: Literal["model", "deterministic_fallback"]
    fallback_reason: Optional[str] = None


class SourceNoteDTO(BaseModel):
    model_config = ConfigDict(extra="forbid")

    note_no: int
    source_id: str
    title: str
    url: Optional[str] = None
    locator: Optional[str] = None
    page: Optional[int] = None
    fact_ids: List[str] = Field(default_factory=list)


class LineageNodeDTO(BaseModel):
    model_config = ConfigDict(extra="forbid")

    observation_id: str
    entity: str
    entity_id: Optional[str] = None
    metric: str
    metric_id: Optional[str] = None
    metric_name: Optional[str] = None
    period: str
    period_id: Optional[str] = None
    value: Optional[float] = None
    unit: Optional[str] = None
    formula_version: Optional[str] = None
    receipt_result: Optional[str] = None
    receipt_tolerance: Optional[str] = None
    calculation_receipt: Optional[dict[str, Any]] = None
    source_title: Optional[str] = None
    source_url: Optional[str] = None
    page: Optional[int] = None
    section: Optional[str] = None
    row_label: Optional[str] = None
    reading: Optional[str] = None
    children: List["LineageNodeDTO"] = Field(default_factory=list)


class ErrorInfoDTO(BaseModel):
    model_config = ConfigDict(extra="forbid")

    code: str
    message: str
    suggestions: List[str] = Field(default_factory=list)


TraceActor = Literal["orchestrator", "company", "sector", "macro", "critic", "verifier", "system"]
TraceKind = Literal[
    "plan",
    "assign",
    "tool_result",
    "draft",
    "verify",
    "compose",
    "critique_issue",
    "cross_level_finding",
    "revision",
    "accept",
    "report_ready",
    "blocked",
]


class TraceStepDTO(BaseModel):
    model_config = ConfigDict(extra="forbid")

    step_id: str
    seq: int
    t_ms: int
    actor: TraceActor
    recipient: Optional[TraceActor] = None
    kind: TraceKind
    summary: str
    detail: dict[str, Any] = Field(default_factory=dict)


RunTraceStepDTO = TraceStepDTO


class RunTraceDTO(BaseModel):
    model_config = ConfigDict(extra="forbid")

    run_id: str
    status: str
    query: str
    created_at: str
    duration_ms: int
    arm: Optional[str] = None
    question_type: Optional[str] = None
    steps: List[TraceStepDTO] = Field(default_factory=list)


class AnalysisRunSummaryDTO(BaseModel):
    model_config = ConfigDict(extra="forbid")

    run_id: str
    created_at: str
    query: str
    target_ticker: Optional[str] = None
    peer_tickers: List[str] = Field(default_factory=list)
    period: Optional[str] = None
    status: str
    latency_ms: Optional[int] = None
    model_used: Optional[str] = None
    error_code: Optional[str] = None
    duration_ms: Optional[int] = None
    arm: Optional[str] = None
    question_type: Optional[str] = None


class AnalysisRunRecordDTO(BaseModel):
    model_config = ConfigDict(extra="forbid")

    run_id: str
    created_at: str
    query: str
    target_ticker: Optional[str] = None
    peer_tickers: List[str] = Field(default_factory=list)
    period: Optional[str] = None
    status: str
    latency_ms: Optional[int] = None
    model_used: Optional[str] = None
    report_json: Optional[dict[str, Any]] = None
    events_json: List[dict[str, Any]] = Field(default_factory=list)
    trace_json: Optional[dict[str, Any]] = None
    error_code: Optional[str] = None
    duration_ms: Optional[int] = None
    model_calls: Optional[int] = None
    input_tokens: Optional[int] = None
    output_tokens: Optional[int] = None
    arm: Optional[str] = None
    question_type: Optional[str] = None


class AnalysisResponse(BaseModel):
    """Hierarchical financial multi-agent analysis report response adhering to OpenAPI spec."""

    model_config = ConfigDict(extra="allow")

    report_id: str = Field(..., description="Unique generated analysis report identifier")
    status: str = Field(
        ...,
        description="Execution status of the analysis (completed, partial, accepted_with_limitations, error)",
    )
    analysis_plan: Optional[AnalysisPlanDTO] = Field(
        default=None,
        description="Query-adaptive analytical execution plan",
    )
    macro_context: Optional[MacroContextDTO | dict[str, Any]] = Field(
        default=None,
        description="Macroeconomic context block (or None if excluded by plan)",
    )
    sector_benchmark: Optional[SectorBenchmarkDTO | dict[str, Any]] = Field(
        default=None,
        description="Sector benchmark peer median block (or None if excluded by plan)",
    )
    company_insights: List[CompanyInsightDTO] = Field(
        default_factory=list,
        description="Per-company financial CAMEL insights and assessments",
    )
    cross_level_critique: List[CritiqueItemDTO] = Field(
        default_factory=list,
        description="Cross-level synthesis and critique findings",
    )
    atomic_claims: List[AtomicClaimDTO] = Field(
        default_factory=list,
        description="Atomic verifiable factual or synthesized claims",
    )
    evidence_trail: List[EvidenceTrailDTO] = Field(
        default_factory=list,
        description="Verifiable source documentation trail",
    )
    revision_summary: Optional[BoundedRevisionSummaryDTO] = Field(
        default=None,
        description="Summary of bounded revision cycles",
    )
    limitations: List[str] = Field(
        default_factory=list,
        description="Analytical limitations and caveats",
    )
    synthesis_summary: Optional[str] = Field(
        default=None,
        description="Constrained orchestrator prose grounded in accepted specialist outputs",
    )
    synthesis_supporting_claim_ids: List[str] = Field(
        default_factory=list,
        description="Ordered claim IDs explicitly used to produce the report-level synthesis",
    )
    report_version: Optional[str] = Field(
        default=None,
        description="Report specification version (e.g. 'er-report-v1')",
    )
    question_type: Optional[QuestionType] = Field(
        default=None,
        description="Resolved or planned question type",
    )
    report_spec: Optional[ReportSpecDTO] = Field(
        default=None,
        description="Structured modular report specification",
    )
    datasets: List[DatasetDTO] = Field(
        default_factory=list,
        description="Datasets backing report figures and tables",
    )
    facts: List[FactDTO] = Field(
        default_factory=list,
        description="Authoritative deterministic facts computed by tools",
    )
    signals: List[SignalDTO] = Field(
        default_factory=list,
        description="Performance signals across financial dimensions",
    )
    cross_level_findings: List[CrossLevelFindingDTO] = Field(
        default_factory=list,
        description="Cross-level synthesis findings",
    )
    narrative_audit: Optional[NarrativeAuditDTO] = Field(
        default=None,
        description="Audit of sentence and block verification",
    )
    source_notes: List[SourceNoteDTO] = Field(
        default_factory=list,
        description="Primary source reference notes",
    )
    error: Optional[ErrorInfoDTO] = Field(
        default=None,
        description="Error details when status is error",
    )

    @model_validator(mode="after")
    def require_scope_limitation(self) -> "AnalysisResponse":
        limitations = tuple(item.casefold() for item in self.limitations)
        for insight in self.company_insights:
            for record in insight.metric_period_records:
                if record.validation_status != "valid" or record.scope_status != "unavailable":
                    continue
                limitation_key = f"scope is unavailable for {record.observation_id}".casefold()
                if not any(limitation_key in item for item in limitations):
                    raise ValueError("unavailable reporting scope requires an explicit response limitation")
        return self


AnalysisResponseDTO = AnalysisResponse


class UploadRowIssueDTO(BaseModel):
    model_config = ConfigDict(extra="ignore")
    row: int = Field(..., description="1-indexed row number in the uploaded CSV (0 for file-level)")
    field: str = Field(..., description="Field name where the issue was detected")
    message_vi: str = Field(..., description="Vietnamese explanation of the issue")


class UploadMetricItemDTO(BaseModel):
    model_config = ConfigDict(extra="ignore")
    metric_id: str = Field(..., description="Canonical metric ID")
    computed_value: float = Field(..., description="Value deterministically recomputed from inputs")
    reported_value: Optional[float] = Field(default=None, description="Reported value from filing if present")
    status: Literal["matched", "computed", "mismatched"] = Field(..., description="Reconciliation status")


class UploadResponseDTO(BaseModel):
    model_config = ConfigDict(extra="ignore")
    upload_id: str = Field(..., description="Unique upload identifier")
    entity_id: str = Field(..., description="Bank ticker / entity ID")
    display_name: str = Field(..., description="Bank display name")
    status: Literal["accepted", "rejected"] = Field(..., description="Overall upload validation status")
    period_id: str = Field(..., description="Target analysis period (e.g. 2024_Q4)")
    metrics: List[UploadMetricItemDTO] = Field(default_factory=list, description="Recomputed ratios")
    row_issues: List[UploadRowIssueDTO] = Field(default_factory=list, description="List of validation errors")
    limitations_vi: str = Field(..., description="Vietnamese limitations and provenance note")
    created_at: Optional[str] = Field(default=None, description="ISO timestamp of upload")


class UploadSummaryDTO(BaseModel):
    model_config = ConfigDict(extra="ignore")
    upload_id: str = Field(..., description="Unique upload identifier")
    entity_id: str = Field(..., description="Bank ticker / entity ID")
    display_name: str = Field(..., description="Bank display name")
    status: Literal["accepted", "rejected"] = Field(..., description="Overall upload validation status")
    period_id: str = Field(..., description="Target analysis period")
    created_at: str = Field(..., description="ISO timestamp of upload")
    row_issues_count: int = Field(..., description="Number of issues found in upload")
    metrics_count: int = Field(..., description="Number of recomputed metrics")


class FilingCreateResponseDTO(BaseModel):
    model_config = ConfigDict(extra="ignore")
    filing_id: str = Field(..., description="Unique filing identifier (fl-12hex)")
    status: Literal["processing"] = Field(..., description="Initial processing status")


class FilingProgressDTO(BaseModel):
    model_config = ConfigDict(extra="ignore")
    pages_done: int = Field(..., description="Number of pages processed")
    page_count: int = Field(..., description="Total pages in filing")


class FilingStatementPagesDTO(BaseModel):
    model_config = ConfigDict(extra="ignore")
    balance_sheet: List[int] = Field(default_factory=list, description="Page numbers of Balance Sheet")
    income_statement: List[int] = Field(default_factory=list, description="Page numbers of Income Statement")
    loan_quality_note: List[int] = Field(default_factory=list, description="Page numbers of Loan Quality Note")


class FilingRowIssueDTO(BaseModel):
    model_config = ConfigDict(extra="ignore")
    code: str = Field(..., description="Issue machine-readable code")
    severity: Literal["error", "warning", "info"] = Field(default="warning", description="Severity level")
    message_vi: str = Field(..., description="Vietnamese explanation of the issue")


class FilingRowAlternativeDTO(BaseModel):
    model_config = ConfigDict(extra="ignore")
    value_billion_vnd: Optional[str] = Field(default=None, description="Alternative value in billion VND")
    raw_text: str = Field(..., description="Raw text of the alternative row")
    row_label: str = Field(..., description="Row label")
    page: int = Field(..., description="1-indexed PDF page")
    score: float = Field(default=0.0, description="Similarity match score")


class FilingCandidateRowDTO(BaseModel):
    model_config = ConfigDict(extra="ignore")
    row_id: str = Field(..., description="Unique candidate row ID")
    metric_id: str = Field(..., description="Canonical metric ID")
    label_vi: str = Field(..., description="Vietnamese metric label")
    period_role: Literal["target", "prior"] = Field(..., description="Period role (target or prior)")
    period_id: str = Field(..., description="Target or prior period ID (e.g. 2025_Q4)")
    value_billion_vnd: Optional[str] = Field(default=None, description="Current or user-edited value in billion VND as decimal string")
    extracted_value_billion_vnd: Optional[str] = Field(default=None, description="Machine-extracted value in billion VND")
    raw_text: Optional[str] = Field(default=None, description="Raw source text line")
    row_label: Optional[str] = Field(default=None, description="Matched row label")
    page: Optional[int] = Field(default=None, description="1-indexed PDF page")
    source: Optional[Literal["text_layer", "ocr", "llamaparse", "user"]] = Field(default=None, description="Extraction source kind")
    status: Literal["candidate", "needs_review", "missing"] = Field(..., description="Candidate status")
    edited: bool = Field(default=False, description="Whether user edited this value")
    confirmed: bool = Field(default=False, description="Whether user explicitly confirmed this row")
    issues: List[FilingRowIssueDTO] = Field(default_factory=list, description="Extraction issues or warnings")
    alternatives: List[FilingRowAlternativeDTO] = Field(default_factory=list, description="Alternative line matches")


class FilingCheckDTO(BaseModel):
    model_config = ConfigDict(extra="ignore")
    code: str = Field(..., description="Validation check code")
    severity: Literal["error", "warning", "info"] = Field(..., description="Check severity")
    message_vi: str = Field(..., description="Vietnamese check message")
    row_ids: List[str] = Field(default_factory=list, description="Related row IDs")
    expected: Optional[str] = Field(default=None, description="Expected value")
    actual: Optional[str] = Field(default=None, description="Actual value")


class FilingValidationDTO(BaseModel):
    model_config = ConfigDict(extra="ignore")
    status: Literal["pass", "warn", "fail"] = Field(..., description="Overall validation status")
    ready_to_confirm: bool = Field(default=False, description="Whether filing is ready to confirm into an operational snapshot")
    blocking_reasons_vi: List[str] = Field(default_factory=list, description="List of blocking reason messages in Vietnamese")
    checks: List[FilingCheckDTO] = Field(default_factory=list, description="List of validation checks")


class FilingDetailDTO(BaseModel):
    model_config = ConfigDict(extra="ignore")
    filing_id: str = Field(..., description="Unique filing identifier")
    entity_id: Optional[str] = Field(default=None, description="Bank ticker / entity ID")
    display_name: Optional[str] = Field(default=None, description="Bank display name")
    fiscal_year: Optional[int] = Field(default=None, description="Reporting fiscal year")
    reporting_scope: Optional[str] = Field(default=None, description="Reporting scope (consolidated or separate)")
    status: Literal["processing", "ready", "failed"] = Field(..., description="Filing processing status")
    error_code: Optional[str] = Field(default=None, description="Error code if failed")
    message_vi: Optional[str] = Field(default=None, description="Vietnamese explanation if failed")
    filename: str = Field(..., description="Original PDF filename")
    sha256: str = Field(..., description="SHA-256 of the uploaded PDF")
    page_count: int = Field(..., description="Total pages in PDF")
    progress: FilingProgressDTO = Field(..., description="Processing progress")
    ocr_provider: Optional[Literal["text_layer", "tesseract", "llamaparse", "mixed", "sample"]] = Field(default="text_layer", description="OCR provider used")
    text_layer_pages: int = Field(default=0, description="Pages read from PDF text layer")
    ocr_pages: int = Field(default=0, description="Pages processed via OCR")
    statement_pages: FilingStatementPagesDTO = Field(default_factory=FilingStatementPagesDTO, description="Identified statement pages")
    unit_detected: Optional[str] = Field(default=None, description="Detected monetary unit")
    rows: List[FilingCandidateRowDTO] = Field(default_factory=list, description="Extracted candidate observation rows")
    validation: Optional[FilingValidationDTO] = Field(default=None, description="Validation summary and checks")
    limitations_vi: Union[List[str], str, None] = Field(default=None, description="Vietnamese provenance and limitation note")
    upload_id: Optional[str] = Field(default=None, description="Operational snapshot upload ID if confirmed")
    created_at: Optional[str] = Field(default=None, description="ISO timestamp of filing creation")


class FilingSummaryDTO(BaseModel):
    model_config = ConfigDict(extra="ignore")
    filing_id: str = Field(..., description="Unique filing identifier")
    entity_id: str = Field(..., description="Bank ticker / entity ID")
    display_name: str = Field(..., description="Bank display name")
    fiscal_year: int = Field(..., description="Reporting fiscal year")
    reporting_scope: str = Field(..., description="Reporting scope")
    status: Literal["processing", "ready", "failed"] = Field(..., description="Filing processing status")
    created_at: str = Field(..., description="ISO timestamp of filing creation")
    filename: str = Field(..., description="Original PDF filename")
    page_count: int = Field(..., description="Total pages in PDF")
    candidate_rows_count: int = Field(default=0, description="Number of candidate rows extracted")
    needs_review_count: int = Field(default=0, description="Number of rows needing review")


class FilingRowUpdateRequest(BaseModel):
    model_config = ConfigDict(extra="ignore")
    value_billion_vnd: Optional[str] = Field(default=None, description="Updated value in billion VND as decimal string")
    confirmed: bool = Field(default=False, description="User confirmation status for this row")


class FilingRowUpdateResponse(BaseModel):
    model_config = ConfigDict(extra="ignore")
    row: FilingCandidateRowDTO = Field(..., description="Updated candidate row")
    validation: FilingValidationDTO = Field(..., description="Recalculated validation results")


class FilingSampleDTO(BaseModel):
    """Catalog item for demonstrator filing samples (INGEST-5)."""

    model_config = ConfigDict(extra="ignore")
    sample_id: str = Field(..., description="Unique sample identifier (e.g. acb-2025)")
    title_vi: str = Field(..., description="Vietnamese title of sample for display")
    entity_id: str = Field(..., description="Bank entity ticker")
    fiscal_year: int = Field(..., description="Reporting fiscal year")
    page_count: int = Field(..., description="Total pages in sample")
    note_vi: str = Field(..., description="Vietnamese descriptive note or highlighted issue")


