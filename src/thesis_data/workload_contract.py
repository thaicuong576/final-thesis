"""Typed contracts for multi-workload complexity experiments."""

from __future__ import annotations

from enum import StrEnum
import re

from pydantic import BaseModel, ConfigDict, Field, model_validator


PERIOD_PATTERN = r"^\d{4}_Q[1-4]$"


class WorkloadTier(StrEnum):
    TIER_1 = "tier_1"
    TIER_2 = "tier_2"
    TIER_3 = "tier_3"


class AnalysisTask(StrEnum):
    SNAPSHOT = "snapshot"
    TREND = "trend"
    PEER_COMPARISON = "peer_comparison"
    MISSING_CONFLICT = "missing_conflict"
    ANOMALY_REVIEW = "anomaly_review"
    EVIDENCE_SUMMARY = "evidence_summary"


class ComplexityVector(BaseModel):
    model_config = ConfigDict(extra="forbid")

    issuer_count: int = Field(ge=1)
    period_count: int = Field(ge=1)
    metric_count: int = Field(ge=1)
    analysis_task_count: int = Field(ge=1)
    cross_issuer_comparisons: int = Field(ge=0)
    missing_conflict_checks: int = Field(ge=0)
    evidence_groups: int = Field(ge=0)


class CompositeWorkloadSpec(BaseModel):
    """Immutable scope and pre-registered complexity for one composite request."""

    model_config = ConfigDict(extra="forbid")

    question_id: str = Field(min_length=1)
    tier: WorkloadTier
    issuers: tuple[str, ...] = Field(min_length=1)
    periods: tuple[str, ...] = Field(min_length=1)
    metric_ids: tuple[str, ...] = Field(min_length=1)
    analysis_tasks: tuple[AnalysisTask, ...] = Field(min_length=1)
    peer_tickers: tuple[str, ...] = Field(default_factory=tuple)
    macro_indicator_ids: tuple[str, ...] = Field(default_factory=tuple)
    complexity_vector: ComplexityVector

    @model_validator(mode="after")
    def validate_scope_and_complexity(self) -> "CompositeWorkloadSpec":
        if self.tier is WorkloadTier.TIER_1:
            raise ValueError("composite workload spec must use tier_2 or tier_3")
        if self.tier is WorkloadTier.TIER_2 and len(self.issuers) != 1:
            raise ValueError("tier_2 requires exactly one issuer")
        if self.tier is WorkloadTier.TIER_3 and len(self.issuers) < 2:
            raise ValueError("tier_3 requires at least two issuers")
        if len(set(self.issuers)) != len(self.issuers):
            raise ValueError("issuers must be unique")
        if len(set(self.periods)) != len(self.periods):
            raise ValueError("periods must be unique")
        if any(not re.fullmatch(PERIOD_PATTERN, period) for period in self.periods):
            raise ValueError("periods must use YYYY_QN format")
        if len(set(self.metric_ids)) != len(self.metric_ids):
            raise ValueError("metric_ids must be unique")
        if len(set(self.analysis_tasks)) != len(self.analysis_tasks):
            raise ValueError("analysis_tasks must be unique")
        if AnalysisTask.PEER_COMPARISON in self.analysis_tasks:
            if len(self.peer_tickers) < 2 or not set(self.issuers).issubset(self.peer_tickers):
                raise ValueError("peer_comparison requires all issuers in peer_tickers")

        expected = {
            "issuer_count": len(self.issuers),
            "period_count": len(self.periods),
            "metric_count": len(self.metric_ids),
            "analysis_task_count": len(self.analysis_tasks),
            "cross_issuer_comparisons": int(
                AnalysisTask.PEER_COMPARISON in self.analysis_tasks
                and len(self.peer_tickers) > 1
            ),
            "missing_conflict_checks": (
                len(self.issuers) * len(self.periods) * len(self.metric_ids)
                if AnalysisTask.MISSING_CONFLICT in self.analysis_tasks
                else 0
            ),
            "evidence_groups": (
                len(self.issuers) * len(self.periods)
                if AnalysisTask.EVIDENCE_SUMMARY in self.analysis_tasks
                else 0
            ),
        }
        for field, value in expected.items():
            if getattr(self.complexity_vector, field) != value:
                raise ValueError(f"complexity_vector {field} mismatch")
        return self
