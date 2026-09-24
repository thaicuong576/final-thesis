"""Pydantic v2 schemas for the thesis API analysis service.

These models strictly adhere to contracts/openapi.json and contracts/mock-data.json.
"""

from __future__ import annotations

from typing import Any, List, Optional
from pydantic import BaseModel, ConfigDict, Field


class AnalysisRequest(BaseModel):
    """Natural language analysis query with optional target, peer universe, and period filters."""

    model_config = ConfigDict(extra="ignore")

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
        examples=["2024"],
    )


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
