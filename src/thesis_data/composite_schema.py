"""Strict output contracts for composite multi-workload answers."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from .schema import AgentPayload, AgentStatus
from .workload_contract import AnalysisTask, WorkloadTier


class CompositeClaim(BaseModel):
    """A model-produced claim that can be normalized into report v2."""

    model_config = ConfigDict(extra="forbid")

    claim_id: str = Field(min_length=1)
    claim_type: str = Field(min_length=1)
    priority: Literal["high", "normal", "low"] = "normal"
    title: str = Field(min_length=1)
    claim: str = Field(min_length=1)
    interpretation: str = Field(min_length=1)
    limitation: str = Field(min_length=1)
    support: Literal["evidence_backed", "source_locator_only", "partially_supported"]
    data_refs: tuple[str, ...]
    evidence_ids: tuple[str, ...] = Field(default_factory=tuple)
    source_ids: tuple[str, ...] = Field(default_factory=tuple)

    @model_validator(mode="after")
    def require_data_reference(self) -> "CompositeClaim":
        if not self.data_refs:
            raise ValueError("claim data reference is required")
        return self


class CompositeSubreport(BaseModel):
    model_config = ConfigDict(extra="forbid")

    issuer: str = Field(min_length=1)
    period: str = Field(pattern=r"^\d{4}_Q[1-4]$")
    task: AnalysisTask
    payload: AgentPayload | None = None
    payload_ref: str | None = Field(default=None, min_length=1)
    status: AgentStatus = AgentStatus.SUCCESS
    missing_reasons: tuple[str, ...] = Field(default_factory=tuple)
    observation_ids: tuple[str, ...] = Field(default_factory=tuple)
    source_ids: tuple[str, ...] = Field(default_factory=tuple)
    evidence_ids: tuple[str, ...] = Field(default_factory=tuple)

    @model_validator(mode="after")
    def validate_payload_scope(self) -> "CompositeSubreport":
        if self.payload is not None:
            if self.payload.ticker != self.issuer:
                raise ValueError("payload ticker does not match subreport issuer")
            if self.payload.period != self.period:
                raise ValueError("payload period does not match subreport period")
        if self.payload_ref is not None and self.payload_ref != f"{self.issuer}|{self.period}":
            raise ValueError("payload reference does not match subreport issuer-period")
        if self.status is AgentStatus.SUCCESS and self.payload is None and self.payload_ref is None and not self.missing_reasons:
            raise ValueError("successful subreport requires payload or missing reason")
        return self


class CompositeAnalysisPayload(BaseModel):
    model_config = ConfigDict(extra="forbid")

    agent_id: str = Field(min_length=1)
    status: AgentStatus
    question_id: str = Field(min_length=1)
    tier: WorkloadTier
    issuers: tuple[str, ...] = Field(min_length=1)
    periods: tuple[str, ...] = Field(min_length=1)
    metric_ids: tuple[str, ...] = Field(min_length=1)
    data_slices: tuple[AgentPayload, ...] = Field(default_factory=tuple)
    subreports: tuple[CompositeSubreport, ...] = Field(default_factory=tuple)
    missing_conflict_register: tuple[str, ...] = Field(default_factory=tuple)
    anomaly_classifications: tuple[str, ...] = Field(default_factory=tuple)
    findings: list[str] = Field(default_factory=list)
    claims: list[CompositeClaim] = Field(default_factory=list)
    quality_flags: list[str] = Field(default_factory=list)
    observation_ids: tuple[str, ...] = Field(default_factory=tuple)
    source_ids: tuple[str, ...] = Field(default_factory=tuple)
    evidence_ids: tuple[str, ...] = Field(default_factory=tuple)

    @model_validator(mode="after")
    def validate_subreports(self) -> "CompositeAnalysisPayload":
        keys = [(item.issuer, item.period, item.task) for item in self.subreports]
        if len(keys) != len(set(keys)):
            raise ValueError("duplicate composite subreport")
        allowed_issuers = set(self.issuers)
        allowed_periods = set(self.periods)
        for item in self.subreports:
            if item.issuer not in allowed_issuers:
                raise ValueError("subreport issuer outside composite scope")
            if item.period not in allowed_periods:
                raise ValueError("subreport period outside composite scope")
        claim_ids = [claim.claim_id for claim in self.claims]
        if len(claim_ids) != len(set(claim_ids)):
            raise ValueError("duplicate composite claim")
        allowed_metrics = set(self.metric_ids)
        allowed_issuers = set(self.issuers)
        allowed_periods = set(self.periods)
        for claim in self.claims:
            for data_ref in claim.data_refs:
                parts = data_ref.split("|", 2)
                if len(parts) != 3:
                    raise ValueError("claim data reference must be ticker|period|metric")
                ticker, period, metric = parts
                if ticker not in allowed_issuers or period not in allowed_periods or metric not in allowed_metrics:
                    raise ValueError("claim data reference outside composite scope")
        return self
