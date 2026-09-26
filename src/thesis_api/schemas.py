"""Pydantic v2 schemas for the thesis API analysis service.

These models strictly adhere to contracts/openapi.json and contracts/mock-data.json.
"""

from __future__ import annotations

import math
import re
from typing import Any, List, Literal, Optional
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
