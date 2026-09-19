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


class CompanyInsightDTO(BaseModel):
    """Financial CAMEL indicators and synthesized assessment for a specific bank."""

    model_config = ConfigDict(extra="allow")

    ticker: str = Field(..., description="Bank ticker symbol")
    roe: Optional[float] = Field(default=None, description="Return on equity (%)")
    nim: Optional[float] = Field(default=None, description="Net interest margin (%)")
    npl: Optional[float] = Field(default=None, description="Non-performing loans ratio (%)")
    cir: Optional[float] = Field(default=None, description="Cost-to-income ratio (%)")
    casa: Optional[float] = Field(default=None, description="CASA deposit ratio (%)")
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

    metric: str = Field(..., description="Financial metric or ratio name")
    ticker: str = Field(..., description="Target bank ticker")
    period: str = Field(..., description="Reporting period")
    value: Optional[float] = Field(default=None, description="Reported or observed numeric metric value")
    source_doc: str = Field(..., description="Title or locator of the authoritative filing/disclosure")
    table_locator: Optional[str] = Field(default=None, description="Table, section, or statement locator")


class AnalysisResponse(BaseModel):
    """Hierarchical financial multi-agent analysis report response adhering to OpenAPI spec."""

    model_config = ConfigDict(extra="allow")

    report_id: str = Field(..., description="Unique generated analysis report identifier")
    status: str = Field(
        default="completed",
        description="Execution status of the analysis (completed, partial, error)",
    )
    macro_context: MacroContextDTO | dict[str, Any] = Field(
        ...,
        description="Macroeconomic context block",
    )
    sector_benchmark: SectorBenchmarkDTO | dict[str, Any] = Field(
        ...,
        description="Sector benchmark peer median block",
    )
    company_insights: List[CompanyInsightDTO] = Field(
        ...,
        description="Per-company financial CAMEL insights and assessments",
    )
    cross_level_critique: List[CritiqueItemDTO] = Field(
        ...,
        description="Cross-level synthesis and critique findings",
    )
    evidence_trail: List[EvidenceTrailDTO] = Field(
        default_factory=list,
        description="Verifiable source documentation trail",
    )
