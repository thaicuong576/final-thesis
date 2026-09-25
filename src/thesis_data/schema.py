"""Versioned Pydantic boundary models for the thesis data foundation."""

from datetime import date, datetime
from enum import StrEnum
import math
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class SourceType(StrEnum):
    API = "api"
    FILING = "filing"
    ISSUER_IR = "issuer_ir"
    POLICY = "policy"
    MARKET_DATA = "market_data"
    RESEARCH_REPORT = "research_report"


class SourceTier(StrEnum):
    PRIMARY = "primary"
    ACCELERATOR = "accelerator"
    CROSS_CHECK = "cross_check"
    CONTEXT = "context"
    FALLBACK = "fallback"


class QualityStatus(StrEnum):
    VALID = "valid"
    MISSING = "missing"
    ESTIMATED = "estimated"
    CONFLICTING = "conflicting"
    INVALID = "invalid"
    PENDING_VALIDATION = "pending_validation"


class PeriodBasis(StrEnum):
    POINT_IN_TIME = "point_in_time"
    QUARTER_ONLY = "quarter_only"
    YTD = "ytd"
    ANNUAL = "annual"
    TTM = "ttm"


class AgentStatus(StrEnum):
    SUCCESS = "success"
    PARTIAL = "partial"
    FAILED = "failed"


class AssertionType(StrEnum):
    """The factual shape of a structured claim assertion."""

    METRIC_VALUE = "metric_value"
    COMPARISON = "comparison"
    TREND = "trend"
    AGGREGATE = "aggregate"
    MISSINGNESS = "missingness"
    REFERENCE_ONLY = "reference_only"


class AssertionOperator(StrEnum):
    """Operators used by deterministic assertion validation."""

    EQ = "eq"
    GT = "gt"
    GTE = "gte"
    LT = "lt"
    LTE = "lte"
    INCREASE = "increase"
    DECREASE = "decrease"
    MISSING = "missing"
    EXISTS = "exists"


class InferenceType(StrEnum):
    """How a claim moves beyond a directly observed value."""

    FACT = "fact"
    COMPARISON = "comparison"
    TREND = "trend"
    ASSOCIATION = "association"
    CAUSAL = "causal"
    INTERPRETATION = "interpretation"


class CritiqueIssueType(StrEnum):
    """Stable issue categories for the future structured critic."""

    UNSUPPORTED_CLAIM = "unsupported_claim"
    MISSING_DATA = "missing_data"
    MISSING_EVIDENCE = "missing_evidence"
    NUMERIC_INCONSISTENCY = "numeric_inconsistency"
    SCOPE_VIOLATION = "scope_violation"
    CROSS_LEVEL_CONTRADICTION = "cross_level_contradiction"
    MEANINGFUL_DIVERGENCE = "meaningful_divergence"
    INCOMPLETE_SYNTHESIS = "incomplete_synthesis"
    MALFORMED_OUTPUT = "malformed_output"


class CritiqueSeverity(StrEnum):
    BLOCKER = "BLOCKER"
    MAJOR = "MAJOR"
    MINOR = "MINOR"


class CritiqueAction(StrEnum):
    REQUERY_DATA = "REQUERY_DATA"
    RETRIEVE_EVIDENCE = "RETRIEVE_EVIDENCE"
    REVISE_CLAIM = "REVISE_CLAIM"
    REMOVE_CLAIM = "REMOVE_CLAIM"
    ADD_LIMITATION = "ADD_LIMITATION"
    RECONCILE_CROSS_LEVEL = "RECONCILE_CROSS_LEVEL"


class CritiqueIssueStatus(StrEnum):
    OPEN = "OPEN"
    RESOLVED = "RESOLVED"
    EXPLAINED = "EXPLAINED"
    UNRESOLVED = "UNRESOLVED"


class AcceptanceDecision(StrEnum):
    ACCEPT = "ACCEPT"
    ACCEPT_WITH_LIMITATIONS = "ACCEPT_WITH_LIMITATIONS"
    REVISE = "REVISE"
    FAIL_ACCEPTANCE = "FAIL_ACCEPTANCE"


class UnresolvedReasonCode(StrEnum):
    """Only data/evidence availability reasons may support limited acceptance."""

    DATA_UNAVAILABLE = "DATA_UNAVAILABLE"
    DATA_INSUFFICIENT_FOR_SCOPE = "DATA_INSUFFICIENT_FOR_SCOPE"
    EVIDENCE_UNAVAILABLE = "EVIDENCE_UNAVAILABLE"
    EVIDENCE_INSUFFICIENT_FOR_SCOPE = "EVIDENCE_INSUFFICIENT_FOR_SCOPE"
    PERIOD_NOT_COVERED = "PERIOD_NOT_COVERED"


_LIMITED_ACCEPTANCE_REASON_CODES = {
    CritiqueIssueType.MISSING_DATA: frozenset(
        {
            UnresolvedReasonCode.DATA_UNAVAILABLE,
            UnresolvedReasonCode.DATA_INSUFFICIENT_FOR_SCOPE,
            UnresolvedReasonCode.PERIOD_NOT_COVERED,
        }
    ),
    CritiqueIssueType.MISSING_EVIDENCE: frozenset(
        {
            UnresolvedReasonCode.EVIDENCE_UNAVAILABLE,
            UnresolvedReasonCode.EVIDENCE_INSUFFICIENT_FOR_SCOPE,
        }
    ),
}


class CritiqueResolution(StrEnum):
    RESOLVED = "resolved"
    EXPLAINED = "explained"
    UNRESOLVED = "unresolved"


class SourceRecord(BaseModel):
    model_config = ConfigDict(extra="forbid")

    source_id: str = Field(min_length=1)
    source_type: SourceType
    source_tier: SourceTier
    source_url: str = Field(min_length=1)
    retrieved_at: datetime
    local_path: str = Field(min_length=1)
    content_hash: str = Field(min_length=1)
    publisher: str = Field(min_length=1)
    license_note: str = Field(min_length=1)
    quality_status: QualityStatus = QualityStatus.PENDING_VALIDATION
    notes: str | None = None


class MetricObservation(BaseModel):
    model_config = ConfigDict(extra="forbid")

    observation_id: str = Field(min_length=1)
    ticker: str = Field(min_length=1)
    sector: str = Field(pattern=r"^(bank|securities)$")
    metric: str = Field(min_length=1)
    value: float | None
    unit: str | None = Field(default=None, min_length=1)
    period: str = Field(pattern=r"^\d{4}_Q[1-4]$|^FY\d{4}$")
    as_of_date: date | None = None
    period_basis: PeriodBasis | None = None
    source_id: str | None = Field(default=None, min_length=1)
    source_locator: str | None = None
    quality_status: QualityStatus
    reason: str | None = None

    @model_validator(mode="after")
    def require_reason_for_non_value(self) -> "MetricObservation":
        if self.value is not None and not math.isfinite(self.value):
            raise ValueError("value must be finite")
        non_value_statuses = {
            QualityStatus.MISSING,
            QualityStatus.CONFLICTING,
            QualityStatus.INVALID,
            QualityStatus.PENDING_VALIDATION,
        }
        if self.value is None and self.quality_status in non_value_statuses and not self.reason:
            raise ValueError("reason is required when metric value is null")
        if self.quality_status is QualityStatus.VALID:
            if self.unit is None:
                raise ValueError("unit is required for a valid observation")
            if self.period_basis is None:
                raise ValueError("period_basis is required for a valid observation")
            if self.source_id is None:
                raise ValueError("source_id is required for a valid observation")
            if self.source_locator is None:
                raise ValueError("source_locator is required for a valid observation")
        return self


class MacroObservationV2(BaseModel):
    """Versioned, source-aligned macro observation contract.

    The legacy ``macro_observations`` table is intentionally not reinterpreted
    as this contract.  New acceptance-aware macro references must resolve to
    the versioned physical table created by the storage layer.
    """

    model_config = ConfigDict(extra="forbid")

    observation_id: str = Field(min_length=1)
    indicator_id: str = Field(min_length=1)
    value: float | None = None
    unit: str | None = Field(default=None, min_length=1)
    period: str = Field(pattern=r"^\d{4}_Q[1-4]$|^FY\d{4}$")
    source_id: str | None = Field(default=None, min_length=1)
    quality_status: QualityStatus
    reason: str | None = None
    source_series_id: str | None = Field(default=None, min_length=1)
    indicator_definition_version: str = Field(min_length=1)
    # Frequency describes the original source series.  An accepted missing
    # row has no source observation, so its source-native frequency is
    # intentionally nullable; valid rows must still provide it below.
    frequency: str | None = Field(default=None, min_length=1)
    observation_date: date | None = None
    effective_from: date | None = None
    as_of_date: date | None = None
    period_basis: str = Field(min_length=1)
    alignment_method: str | None = Field(default=None, min_length=1)
    source_locator: str | None = Field(default=None, min_length=1)
    transformation_version: str | None = Field(default=None, min_length=1)
    input_observation_ids: tuple[str, ...] = Field(default_factory=tuple)
    adjudication_ref: str | None = Field(default=None, min_length=1)
    review_check_ids: tuple[str, ...] = Field(default_factory=tuple)

    @model_validator(mode="after")
    def validate_status_contract(self) -> "MacroObservationV2":
        if self.value is not None and not math.isfinite(self.value):
            raise ValueError("value must be finite")
        if len(set(self.input_observation_ids)) != len(self.input_observation_ids):
            raise ValueError("input_observation_ids must be unique")
        if len(set(self.review_check_ids)) != len(self.review_check_ids):
            raise ValueError("review_check_ids must be unique")
        if self.quality_status is QualityStatus.VALID:
            required = {
                "unit": self.unit,
                "source_id": self.source_id,
                "source_series_id": self.source_series_id,
                "frequency": self.frequency,
                "observation_date": self.observation_date,
                "as_of_date": self.as_of_date,
                "alignment_method": self.alignment_method,
                "source_locator": self.source_locator,
                "transformation_version": self.transformation_version,
                "adjudication_ref": self.adjudication_ref,
            }
            missing = sorted(name for name, value in required.items() if value in (None, ""))
            if self.value is None:
                missing.append("value")
            if missing:
                raise ValueError(
                    "valid macro observation missing required fields: " + ",".join(missing)
                )
            if len(self.review_check_ids) < 2:
                raise ValueError("valid macro observation requires two independent review checks")
        elif self.quality_status is QualityStatus.MISSING:
            if self.value is not None:
                raise ValueError("missing macro observation cannot contain a value")
            if not self.reason:
                raise ValueError("missing macro observation requires reason")
            if not self.adjudication_ref:
                raise ValueError("missing macro observation requires adjudication_ref")
            if self.frequency is not None:
                raise ValueError(
                    "accepted missing macro observation must not invent source frequency"
                )
            if len(self.review_check_ids) < 2:
                raise ValueError(
                    "accepted missing macro observation requires two independent review checks"
                )
        elif self.value is None and not self.reason:
            raise ValueError("non-valid null macro observation requires reason")
        return self


class DerivedMetric(BaseModel):
    model_config = ConfigDict(extra="forbid")

    derived_id: str = Field(min_length=1)
    ticker: str | None = None
    sector: str | None = None
    metric: str = Field(min_length=1)
    value: float | None
    unit: str = Field(min_length=1)
    period: str = Field(pattern=r"^\d{4}_Q[1-4]$|^FY\d{4}$")
    period_basis: PeriodBasis
    input_observation_ids: list[str] = Field(min_length=1)
    formula_version: str = Field(min_length=1)
    quality_status: QualityStatus
    reason: str | None = None

    @model_validator(mode="after")
    def require_reason_for_null(self) -> "DerivedMetric":
        if self.value is not None and not math.isfinite(self.value):
            raise ValueError("value must be finite")
        if self.value is None and not self.reason:
            raise ValueError("reason is required when derived value is null")
        return self


class EvidenceSnippet(BaseModel):
    model_config = ConfigDict(extra="forbid")

    evidence_id: str = Field(min_length=1)
    source_id: str = Field(min_length=1)
    source_document: str = Field(min_length=1)
    page_number: int | None = Field(default=None, ge=1)
    section_name: str | None = None
    period: str | None = None
    ticker: str | None = None
    indicator_id: str | None = Field(default=None, min_length=1)
    source_locator: str | None = Field(default=None, min_length=1)
    as_of_date: date | None = None
    effective_from: date | None = None
    quote: str = Field(min_length=1)
    retrieval_score: float | None = None
    parser_status: str = Field(min_length=1)
    is_paginated: bool = False

    @model_validator(mode="after")
    def require_page_for_paginated_source(self) -> "EvidenceSnippet":
        if self.retrieval_score is not None and not math.isfinite(self.retrieval_score):
            raise ValueError("retrieval_score must be finite")
        if self.is_paginated and self.page_number is None:
            raise ValueError("page_number is required for paginated evidence")
        return self


class GoldLabel(BaseModel):
    model_config = ConfigDict(extra="forbid")

    label_id: str = Field(min_length=1)
    target_id: str = Field(min_length=1)
    label_type: str = Field(min_length=1)
    expected_value: float | None = None
    expected_judgment: str | None = None
    checker_id: str = Field(min_length=1)
    checked_at: datetime
    source_locator: str | None = None
    resolution_note: str = Field(min_length=1)

    @model_validator(mode="after")
    def expected_value_must_be_finite(self) -> "GoldLabel":
        if self.expected_value is not None and not math.isfinite(self.expected_value):
            raise ValueError("expected_value must be finite")
        return self


class CoverageSummary(BaseModel):
    model_config = ConfigDict(extra="forbid")

    summary_id: str = Field(min_length=1)
    snapshot_id: str = Field(min_length=1)
    ticker: str = Field(min_length=1)
    metric: str = Field(min_length=1)
    expected_count: int = Field(ge=0)
    candidate_count: int = Field(ge=0)
    valid_count: int = Field(ge=0)
    missing_count: int = Field(ge=0)
    coverage_ratio: float = Field(ge=0.0, le=1.0)

    @model_validator(mode="after")
    def counts_are_consistent(self) -> "CoverageSummary":
        if not math.isfinite(self.coverage_ratio):
            raise ValueError("coverage_ratio must be finite")
        if self.candidate_count > self.expected_count:
            raise ValueError("candidate_count cannot exceed expected_count")
        if self.valid_count + self.missing_count > self.candidate_count:
            raise ValueError("valid_count plus missing_count cannot exceed candidate_count")
        return self


class ClaimDataRef(BaseModel):
    """Typed reference to a Gold observation or deterministic aggregate input.

    The ``legacy`` kind exists only for compatibility adapters.  Stage-1
    validation deliberately rejects it as an authoritative reference until a
    legacy claim has been enriched with a typed Gold reference.
    """

    model_config = ConfigDict(extra="forbid")

    ref_id: str = Field(min_length=1)
    ref_type: Literal[
        "observation",
        "macro_observation",
        "derived_metric",
        "benchmark",
        "missing_cell",
        "legacy",
    ]
    entity: str = Field(min_length=1)
    period: str = Field(pattern=r"^\d{4}_Q[1-4]$|^FY\d{4}$")
    metric_id: str = Field(min_length=1)


class ClaimScope(BaseModel):
    """Generalized analytical scope shared by every role and claim type."""

    model_config = ConfigDict(extra="forbid")

    entities: tuple[str, ...] = Field(min_length=1)
    periods: tuple[str, ...] = Field(min_length=1)
    metric_ids: tuple[str, ...] = Field(min_length=1)
    comparison_universe: str | None = None

    @model_validator(mode="after")
    def validate_unique_scope_values(self) -> "ClaimScope":
        if len(set(self.entities)) != len(self.entities) or any(not item.strip() for item in self.entities):
            raise ValueError("scope entities must be unique and non-empty")
        if len(set(self.periods)) != len(self.periods):
            raise ValueError("scope periods must be unique")
        if len(set(self.metric_ids)) != len(self.metric_ids) or any(not item.strip() for item in self.metric_ids):
            raise ValueError("scope metric_ids must be unique and non-empty")
        if self.comparison_universe is not None and not self.comparison_universe.strip():
            raise ValueError("comparison_universe must be non-empty when provided")
        return self


class StructuredAssertion(BaseModel):
    """A deterministic factual unit behind a publishable analytical claim."""

    model_config = ConfigDict(extra="forbid")

    assertion_id: str = Field(min_length=1)
    assertion_type: AssertionType
    entity: str = Field(min_length=1)
    period: str = Field(pattern=r"^\d{4}_Q[1-4]$|^FY\d{4}$")
    metric_id: str = Field(min_length=1)
    asserted_value: float | None = None
    unit: str | None = Field(default=None, min_length=1)
    operator: AssertionOperator | None = None
    reference_ref: ClaimDataRef | None = None
    benchmark_ref: ClaimDataRef | None = None
    data_refs: tuple[ClaimDataRef, ...] = Field(min_length=1)
    formula_version: str | None = None

    @model_validator(mode="after")
    def validate_assertion_shape(self) -> "StructuredAssertion":
        if self.asserted_value is not None and not math.isfinite(self.asserted_value):
            raise ValueError("asserted_value must be finite")
        ref_keys = [(item.ref_type, item.ref_id) for item in self.data_refs]
        if len(ref_keys) != len(set(ref_keys)):
            raise ValueError("data_refs must be unique within an assertion")
        if self.reference_ref is not None and self.reference_ref.ref_type not in {
            "observation",
            "macro_observation",
            "derived_metric",
        }:
            raise ValueError("reference_ref must resolve to an observation or derived metric")
        if self.benchmark_ref is not None and self.benchmark_ref.ref_type != "benchmark":
            raise ValueError("benchmark_ref must be a benchmark reference")

        if self.assertion_type is AssertionType.METRIC_VALUE:
            if self.asserted_value is None or self.unit is None:
                raise ValueError("metric_value requires asserted_value and unit")
            if len(self.data_refs) != 1:
                raise ValueError("metric_value requires exactly one data_ref")
        elif self.assertion_type is AssertionType.REFERENCE_ONLY:
            if self.asserted_value is not None:
                raise ValueError("reference_only cannot contain asserted_value")
        elif self.assertion_type is AssertionType.MISSINGNESS:
            if self.asserted_value is not None or self.operator not in {
                AssertionOperator.MISSING,
                AssertionOperator.EXISTS,
            }:
                raise ValueError("missingness requires missing or exists operator and no value")
        else:
            if self.operator is None:
                raise ValueError("comparison, trend and aggregate require an operator")
            if self.asserted_value is None and self.reference_ref is None and self.benchmark_ref is None:
                raise ValueError(
                    "comparison, trend and aggregate require asserted_value or a reference"
                )
            if self.asserted_value is not None and self.unit is None:
                raise ValueError("asserted_value requires unit")
        return self


class AtomicClaim(BaseModel):
    """Canonical claim contract for workers, orchestrators and final reports."""

    model_config = ConfigDict(extra="forbid")

    claim_id: str = Field(min_length=1)
    claim_text: str = Field(min_length=1)
    claim_type: str = Field(min_length=1)
    title: str = Field(min_length=1)
    interpretation: str = Field(min_length=1)
    limitation: str = Field(min_length=1)
    scope: ClaimScope
    assertions: tuple[StructuredAssertion, ...] = Field(min_length=1)
    evidence_refs: tuple[str, ...] = Field(default_factory=tuple)
    source_refs: tuple[str, ...] = Field(default_factory=tuple)
    inference_type: InferenceType
    support: Literal["evidence_backed", "source_locator_only", "partially_supported"] = (
        "partially_supported"
    )
    priority: Literal["high", "normal", "low"] = "normal"
    origin: Literal["model", "deterministic_reference"] = "model"
    critical: bool = True

    @model_validator(mode="after")
    def validate_assertions_are_in_scope(self) -> "AtomicClaim":
        assertion_ids = [item.assertion_id for item in self.assertions]
        if len(assertion_ids) != len(set(assertion_ids)):
            raise ValueError("assertion IDs must be unique within a claim")
        allowed_entities = set(self.scope.entities)
        if self.scope.comparison_universe:
            allowed_entities.add(self.scope.comparison_universe)
        for assertion in self.assertions:
            if assertion.entity not in allowed_entities:
                raise ValueError("assertion entity outside claim scope")
            if assertion.period not in self.scope.periods:
                raise ValueError("assertion period outside claim scope")
            if assertion.metric_id not in self.scope.metric_ids:
                raise ValueError("assertion metric outside claim scope")
            for ref in assertion.data_refs:
                if ref.entity not in allowed_entities:
                    raise ValueError("data reference entity outside claim scope")
                if ref.period not in self.scope.periods:
                    raise ValueError("data reference period outside claim scope")
                if ref.metric_id not in self.scope.metric_ids:
                    raise ValueError("data reference metric outside claim scope")
            for ref in (assertion.reference_ref, assertion.benchmark_ref):
                if ref is None:
                    continue
                if ref.entity not in allowed_entities:
                    raise ValueError("assertion reference entity outside claim scope")
                if ref.period not in self.scope.periods:
                    raise ValueError("assertion reference period outside claim scope")
                if ref.metric_id not in self.scope.metric_ids:
                    raise ValueError("assertion reference metric outside claim scope")
        if len(set(self.evidence_refs)) != len(self.evidence_refs):
            raise ValueError("evidence_refs must be unique")
        if len(set(self.source_refs)) != len(self.source_refs):
            raise ValueError("source_refs must be unique")
        return self


class AgentPayload(BaseModel):
    model_config = ConfigDict(extra="forbid")

    agent_id: str = Field(min_length=1)
    status: AgentStatus
    ticker: str | None = None
    period: str
    metrics: dict[str, float | None] = Field(default_factory=dict)
    metric_units: dict[str, str] = Field(default_factory=dict)
    metric_periods: dict[str, str] = Field(default_factory=dict)
    sector_benchmarks: dict[str, float | None] = Field(default_factory=dict)
    findings: list[str] = Field(default_factory=list)
    evidence: list[EvidenceSnippet] = Field(default_factory=list)
    quality_flags: list[str] = Field(default_factory=list)
    missing_reasons: dict[str, str] = Field(default_factory=dict)
    observation_ids: list[str] = Field(default_factory=list)
    source_ids: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def numeric_values_must_be_finite(self) -> "AgentPayload":
        for field_name, values in (
            ("metrics", self.metrics),
            ("sector_benchmarks", self.sector_benchmarks),
        ):
            for metric, value in values.items():
                if value is not None and not math.isfinite(value):
                    raise ValueError(f"{field_name}.{metric} must be finite")
        return self


class CritiqueRecord(BaseModel):
    model_config = ConfigDict(extra="forbid")

    critique_id: str = Field(min_length=1)
    rule_id: str = Field(min_length=1)
    conflict_detected: bool
    conflict_description: str = Field(min_length=1)
    affected_agents: list[str] = Field(default_factory=list)
    verification_request: str | None = None
    new_evidence_ids: list[str] = Field(default_factory=list)
    resolution: CritiqueResolution


class CritiqueIssue(BaseModel):
    """Structured issue returned by the future supervisor critic."""

    model_config = ConfigDict(extra="forbid")

    issue_id: str = Field(min_length=1)
    issue_type: CritiqueIssueType
    severity: CritiqueSeverity
    affected_agent: str = Field(min_length=1)
    affected_claim_ids: tuple[str, ...] = Field(default_factory=tuple)
    affected_requirement_ids: tuple[str, ...] = Field(default_factory=tuple)
    description: str = Field(min_length=1)
    evidence_refs: tuple[str, ...] = Field(default_factory=tuple)
    required_action: CritiqueAction
    resolution_status: CritiqueIssueStatus = CritiqueIssueStatus.OPEN
    unresolved_reason_code: UnresolvedReasonCode | None = None

    @model_validator(mode="after")
    def validate_unresolved_reason(self) -> "CritiqueIssue":
        if self.resolution_status is CritiqueIssueStatus.UNRESOLVED:
            allowed_reasons = _LIMITED_ACCEPTANCE_REASON_CODES.get(self.issue_type)
            if allowed_reasons is None:
                if self.unresolved_reason_code is not None:
                    raise ValueError(
                        "reasoning issues cannot claim data/evidence availability"
                    )
            elif self.unresolved_reason_code not in allowed_reasons:
                raise ValueError(
                    "unresolved reason does not match the issue availability family"
                )
        elif self.unresolved_reason_code is not None:
            raise ValueError("unresolved_reason_code is only valid for unresolved issues")
        if any(
            not isinstance(requirement_id, str) or not requirement_id.strip()
            for requirement_id in self.affected_requirement_ids
        ):
            raise ValueError("affected_requirement_ids must contain non-empty strings")
        if len(self.affected_requirement_ids) != len(set(self.affected_requirement_ids)):
            raise ValueError("affected_requirement_ids must be unique")
        return self


class QualityWeights(BaseModel):
    """Configurable Stage-2 quality weights; values are research parameters."""

    model_config = ConfigDict(extra="forbid")

    groundedness: float = Field(default=0.30, ge=0.0, le=1.0)
    cross_level_integration: float = Field(default=0.20, ge=0.0, le=1.0)
    answer_coverage: float = Field(default=0.20, ge=0.0, le=1.0)
    logical_soundness: float = Field(default=0.15, ge=0.0, le=1.0)
    uncertainty_limitations: float = Field(default=0.10, ge=0.0, le=1.0)
    analytical_usefulness: float = Field(default=0.05, ge=0.0, le=1.0)

    @model_validator(mode="after")
    def weights_must_sum_to_one(self) -> "QualityWeights":
        total = sum(
            (
                self.groundedness,
                self.cross_level_integration,
                self.answer_coverage,
                self.logical_soundness,
                self.uncertainty_limitations,
                self.analytical_usefulness,
            )
        )
        if not math.isclose(total, 1.0, rel_tol=0.0, abs_tol=1e-9):
            raise ValueError("quality weights must sum to 1.0")
        return self


class AcceptancePolicy(BaseModel):
    """Versioned policy for Stage-1 gates and provisional Stage-2 scoring."""

    model_config = ConfigDict(extra="forbid")

    policy_version: str = Field(min_length=1)
    provisional_threshold: float = Field(ge=0.0, le=1.0)
    quality_weights: QualityWeights = Field(default_factory=QualityWeights)
    numeric_tolerance: float = Field(default=1e-9, ge=0.0)
    max_revision_rounds: int = Field(default=2, ge=0, le=2)
    accepted_source_tiers: tuple[SourceTier, ...] = (SourceTier.PRIMARY,)
    critical_claim_types: tuple[str, ...] = (
        "factual",
        "numeric",
        "comparison",
        "trend",
        "association",
        "causal",
    )

    @model_validator(mode="after")
    def validate_policy_lists(self) -> "AcceptancePolicy":
        if not self.accepted_source_tiers:
            raise ValueError("accepted_source_tiers must not be empty")
        if len(set(self.accepted_source_tiers)) != len(self.accepted_source_tiers):
            raise ValueError("accepted_source_tiers must be unique")
        if len(set(self.critical_claim_types)) != len(self.critical_claim_types):
            raise ValueError("critical_claim_types must be unique")
        return self


class HardGateResult(BaseModel):
    """One non-compensatory Stage-1 result."""

    model_config = ConfigDict(extra="forbid")

    gate_id: str = Field(min_length=1)
    passed: bool
    rate: float = Field(ge=0.0, le=1.0)
    required_rate: float = Field(default=1.0, ge=0.0, le=1.0)
    evaluation_unit: str = Field(min_length=1)
    evaluated_count: int = Field(ge=0)
    passed_count: int = Field(ge=0)
    violations: tuple[str, ...] = Field(default_factory=tuple)
    deferred_to_critic: bool = False

    @model_validator(mode="after")
    def rate_matches_evaluation_counts(self) -> "HardGateResult":
        if self.passed_count > self.evaluated_count:
            raise ValueError("passed_count cannot exceed evaluated_count")
        expected_rate = (
            self.passed_count / self.evaluated_count
            if self.evaluated_count
            else 0.0
        )
        if not math.isclose(self.rate, expected_rate, rel_tol=0.0, abs_tol=1e-12):
            raise ValueError("rate must equal passed_count / evaluated_count")
        if self.passed and self.rate + 1e-12 < self.required_rate:
            raise ValueError("passed gate cannot have a rate below required_rate")
        if self.passed and self.violations:
            raise ValueError("passed gate cannot contain violations")
        if not self.passed and not self.violations:
            raise ValueError("failed gate requires at least one violation")
        return self


class Stage1ValidationReport(BaseModel):
    """Deterministic Stage-1 result before any semantic critic is invoked."""

    model_config = ConfigDict(extra="forbid")

    passed: bool
    gate_results: dict[str, HardGateResult]
    integrity_violations: tuple[str, ...] = Field(default_factory=tuple)

    @model_validator(mode="after")
    def status_matches_gates(self) -> "Stage1ValidationReport":
        expected = all(item.passed for item in self.gate_results.values()) and not self.integrity_violations
        if self.passed != expected:
            raise ValueError("Stage-1 status must match all hard-gate results")
        return self


class QualityDimensionScores(BaseModel):
    """Separate Stage-2 dimensions, each normalized to [0, 1]."""

    model_config = ConfigDict(extra="forbid")

    groundedness: float | None = Field(ge=0.0, le=1.0)
    cross_level_integration: float | None = Field(ge=0.0, le=1.0)
    answer_coverage: float | None = Field(ge=0.0, le=1.0)
    logical_soundness: float | None = Field(ge=0.0, le=1.0)
    uncertainty_limitations: float | None = Field(ge=0.0, le=1.0)
    analytical_usefulness: float | None = Field(ge=0.0, le=1.0)

    @model_validator(mode="after")
    def validate_applicable_scores(self) -> "QualityDimensionScores":
        values = (
            self.groundedness,
            self.cross_level_integration,
            self.answer_coverage,
            self.logical_soundness,
            self.uncertainty_limitations,
            self.analytical_usefulness,
        )
        if not any(value is not None for value in values):
            raise ValueError("quality scores must contain at least one applicable dimension")
        if any(value is not None and not math.isfinite(value) for value in values):
            raise ValueError("quality scores must be finite values")
        return self

    def weighted_total(self, weights: QualityWeights) -> float:
        """Recompute the persisted quality total from canonical dimensions."""

        values_and_weights = (
            (self.groundedness, weights.groundedness),
            (self.cross_level_integration, weights.cross_level_integration),
            (self.answer_coverage, weights.answer_coverage),
            (self.logical_soundness, weights.logical_soundness),
            (self.uncertainty_limitations, weights.uncertainty_limitations),
            (self.analytical_usefulness, weights.analytical_usefulness),
        )
        applicable = tuple(
            (value, weight)
            for value, weight in values_and_weights
            if value is not None
        )
        applicable_weight_total = sum(weight for _, weight in applicable)
        if not applicable or applicable_weight_total <= 0.0:
            raise ValueError("quality total requires at least one applicable positive-weight dimension")
        return round(
            sum(value * weight for value, weight in applicable)
            / applicable_weight_total,
            12,
        )


class AcceptanceRound(BaseModel):
    """Durable record of one evaluation or revision round."""

    model_config = ConfigDict(extra="forbid")

    round_number: int = Field(ge=0)
    candidate_hash: str | None = Field(default=None, min_length=1)
    candidate_claim_ids: tuple[str, ...] = Field(default_factory=tuple)
    candidate_synthesis_summary: str | None = Field(default=None, min_length=1)
    candidate_synthesis_supporting_claim_ids: tuple[str, ...] = Field(default_factory=tuple)
    candidate_payload_version: str | None = Field(default=None, min_length=1)
    worker_payload_versions: dict[str, str] = Field(default_factory=dict)
    orchestrator_payload_version: str | None = None
    critique_issues: tuple[CritiqueIssue, ...] = Field(default_factory=tuple)
    resolved_issue_ids: tuple[str, ...] = Field(default_factory=tuple)
    unresolved_issue_ids: tuple[str, ...] = Field(default_factory=tuple)
    hard_gate_results: dict[str, HardGateResult] = Field(default_factory=dict)
    quality_scores: QualityDimensionScores | None = None
    quality_total: float | None = Field(default=None, ge=0.0, le=1.0)
    provisional_threshold: float = Field(ge=0.0, le=1.0)
    token_usage: dict[str, int] = Field(default_factory=dict)
    latency_ms: float | None = Field(default=None, ge=0.0)
    affected_agents: tuple[str, ...] = Field(default_factory=tuple)
    revised_agents: tuple[str, ...] = Field(default_factory=tuple)
    revised_claim_ids: dict[str, tuple[str, ...]] = Field(default_factory=dict)
    final_payload_version: str | None = None
    acceptance_decision: AcceptanceDecision
    unresolved_reason_codes: tuple[UnresolvedReasonCode, ...] = Field(default_factory=tuple)

    @model_validator(mode="after")
    def validate_round_state(self) -> "AcceptanceRound":
        required_gates = {
            "numeric_accuracy",
            "reference_validity",
            "critical_evidence_coverage",
            "scope_compliance",
            "fabricated_or_unaccepted_records",
            "blocking_contradictions",
        }
        if set(self.hard_gate_results) != required_gates:
            raise ValueError("acceptance round must persist all Stage-1 hard gates")
        if self.quality_total is not None and self.quality_scores is None:
            raise ValueError("quality_total requires quality_scores")
        if len(self.candidate_claim_ids) != len(set(self.candidate_claim_ids)):
            raise ValueError("candidate_claim_ids must be unique")
        if self.revised_claim_ids and set(self.revised_claim_ids) != set(
            self.revised_agents
        ):
            raise ValueError("revised_claim_ids keys must match revised_agents")
        assigned_revision_claim_ids: list[str] = []
        for agent, claim_ids in self.revised_claim_ids.items():
            if not agent.strip():
                raise ValueError("revised_claim_ids keys must be non-empty")
            if not claim_ids:
                raise ValueError(f"revised_claim_ids for {agent} must be non-empty")
            if any(not claim_id.strip() for claim_id in claim_ids):
                raise ValueError("revised_claim_ids must contain non-empty claim IDs")
            if len(claim_ids) != len(set(claim_ids)):
                raise ValueError(f"revised_claim_ids for {agent} must be unique")
            assigned_revision_claim_ids.extend(claim_ids)
        if len(assigned_revision_claim_ids) != len(set(assigned_revision_claim_ids)):
            raise ValueError("a claim ID cannot be assigned to multiple specialists")
        if any(
            claim_id not in self.candidate_claim_ids
            for claim_id in assigned_revision_claim_ids
        ):
            raise ValueError("revised_claim_ids must reference candidate_claim_ids")
        if self.candidate_synthesis_summary is not None and any(
            character.isdigit() for character in self.candidate_synthesis_summary
        ):
            raise ValueError("candidate_synthesis_summary_numeric_or_period_literal_forbidden")
        if (
            self.candidate_synthesis_summary is None
            and self.candidate_synthesis_supporting_claim_ids
        ):
            raise ValueError("candidate_synthesis_supporting_claim_ids_require_summary")
        if (
            self.candidate_synthesis_summary is not None
            and not self.candidate_synthesis_supporting_claim_ids
        ):
            raise ValueError("candidate_synthesis_summary_requires_supporting_claim_ids")
        if any(
            not claim_id.strip()
            for claim_id in self.candidate_synthesis_supporting_claim_ids
        ):
            raise ValueError(
                "candidate_synthesis_supporting_claim_ids_must_be_non_empty_strings"
            )
        if len(self.candidate_synthesis_supporting_claim_ids) != len(
            set(self.candidate_synthesis_supporting_claim_ids)
        ):
            raise ValueError("candidate_synthesis_supporting_claim_ids_must_be_unique")
        claim_positions = {
            claim_id: index for index, claim_id in enumerate(self.candidate_claim_ids)
        }
        if any(
            claim_id not in claim_positions
            for claim_id in self.candidate_synthesis_supporting_claim_ids
        ):
            raise ValueError(
                "candidate_synthesis_supporting_claim_ids_must_reference_candidate_claims"
            )
        if tuple(
            sorted(
                self.candidate_synthesis_supporting_claim_ids,
                key=claim_positions.__getitem__,
            )
        ) != self.candidate_synthesis_supporting_claim_ids:
            raise ValueError(
                "candidate_synthesis_supporting_claim_ids_must_follow_candidate_order"
            )
        issue_ids = {issue.issue_id for issue in self.critique_issues}
        if not set(self.resolved_issue_ids).issubset(issue_ids):
            raise ValueError("resolved_issue_ids must reference round critique issues")
        if not set(self.unresolved_issue_ids).issubset(issue_ids):
            raise ValueError("unresolved_issue_ids must reference round critique issues")
        if set(self.resolved_issue_ids) & set(self.unresolved_issue_ids):
            raise ValueError("an issue cannot be both resolved and unresolved")
        unresolved_issues = {
            issue.issue_id
            for issue in self.critique_issues
            if issue.resolution_status is CritiqueIssueStatus.UNRESOLVED
        }
        if unresolved_issues != set(self.unresolved_issue_ids):
            raise ValueError("unresolved_issue_ids do not match issue resolution status")
        if not set(self.unresolved_reason_codes).issubset(
            {
                issue.unresolved_reason_code
                for issue in self.critique_issues
                if issue.unresolved_reason_code is not None
            }
        ):
            raise ValueError("unresolved_reason_codes must be backed by critique issues")
        if self.acceptance_decision in {
            AcceptanceDecision.ACCEPT,
            AcceptanceDecision.ACCEPT_WITH_LIMITATIONS,
        } and any(
            issue.resolution_status is CritiqueIssueStatus.OPEN
            for issue in self.critique_issues
        ):
            raise ValueError("accepted rounds cannot contain OPEN critique issues")
        if self.acceptance_decision is AcceptanceDecision.ACCEPT:
            if self.unresolved_issue_ids or self.unresolved_reason_codes:
                raise ValueError("ACCEPT cannot contain unresolved issues or reasons")
        elif self.acceptance_decision is AcceptanceDecision.ACCEPT_WITH_LIMITATIONS:
            if not self.unresolved_issue_ids or not self.unresolved_reason_codes:
                raise ValueError("limited acceptance requires explicit unresolved data/evidence reasons")
            unresolved = [
                issue
                for issue in self.critique_issues
                if issue.issue_id in self.unresolved_issue_ids
            ]
            if any(issue.severity is CritiqueSeverity.BLOCKER for issue in unresolved):
                raise ValueError("limited acceptance cannot contain an unresolved BLOCKER")
            if any(
                issue.issue_type not in _LIMITED_ACCEPTANCE_REASON_CODES
                or issue.unresolved_reason_code
                not in _LIMITED_ACCEPTANCE_REASON_CODES[issue.issue_type]
                for issue in unresolved
            ):
                raise ValueError("limited acceptance only permits data/evidence availability deficiencies")
        if self.acceptance_decision in {
            AcceptanceDecision.ACCEPT,
            AcceptanceDecision.ACCEPT_WITH_LIMITATIONS,
        }:
            if self.quality_total is None or self.provisional_threshold is None:
                raise ValueError("accepted rounds require a quality score and provisional threshold")
            if self.quality_total + 1e-12 < self.provisional_threshold:
                raise ValueError("accepted rounds cannot bypass the provisional quality threshold")
            if any(not gate.passed for gate in self.hard_gate_results.values()):
                raise ValueError("accepted rounds cannot bypass a failed Stage-1 hard gate")
            if not self.final_payload_version:
                raise ValueError("accepted rounds require final_payload_version")
        if self.acceptance_decision is AcceptanceDecision.REVISE:
            if self.final_payload_version is not None:
                raise ValueError("REVISE rounds cannot have final_payload_version")
            if self.quality_scores is None or self.quality_total is None:
                raise ValueError("REVISE rounds require semantic quality results")
            if any(not gate.passed for gate in self.hard_gate_results.values()):
                raise ValueError("REVISE rounds cannot bypass a failed Stage-1 hard gate")
            if not any(
                issue.resolution_status is CritiqueIssueStatus.OPEN
                for issue in self.critique_issues
            ):
                raise ValueError("REVISE rounds require an actionable OPEN critique issue")
        return self


class ReportStatementLink(BaseModel):
    """Mapping from one rendered report statement to canonical claim IDs."""

    model_config = ConfigDict(extra="forbid")

    statement_id: str = Field(min_length=1)
    claim_ids: tuple[str, ...] = Field(min_length=1)


class ReportAcceptanceState(BaseModel):
    """Versioned acceptance history for a generated analytical report."""

    model_config = ConfigDict(extra="forbid")

    acceptance_model_version: str = Field(min_length=1)
    run_id: str = Field(min_length=1)
    policy: AcceptancePolicy
    rounds: tuple[AcceptanceRound, ...] = Field(min_length=1)
    final_payload_version: str | None = None
    final_statement_links: tuple[ReportStatementLink, ...] = Field(default_factory=tuple)
    final_decision: AcceptanceDecision

    @model_validator(mode="after")
    def validate_round_sequence(self) -> "ReportAcceptanceState":
        numbers = [item.round_number for item in self.rounds]
        if numbers != list(range(len(numbers))):
            raise ValueError("acceptance rounds must start at zero and be contiguous")
        if len(self.rounds) - 1 > self.policy.max_revision_rounds:
            raise ValueError("acceptance rounds exceed policy max_revision_rounds")
        for round_state in self.rounds:
            if not math.isclose(
                round_state.provisional_threshold,
                self.policy.provisional_threshold,
                rel_tol=0.0,
                abs_tol=1e-12,
            ):
                raise ValueError("each round provisional_threshold must match policy")
            if round_state.quality_total is not None:
                if round_state.quality_scores is None:
                    raise ValueError("quality_total requires quality_scores")
                expected_quality_total = round_state.quality_scores.weighted_total(
                    self.policy.quality_weights
                )
                if not math.isclose(
                    round_state.quality_total,
                    expected_quality_total,
                    rel_tol=0.0,
                    abs_tol=1e-12,
                ):
                    raise ValueError("quality_total does not match quality_scores and policy weights")
        statement_ids = [link.statement_id for link in self.final_statement_links]
        if len(statement_ids) != len(set(statement_ids)):
            raise ValueError("final statement IDs must be unique")
        if self.final_decision is not self.rounds[-1].acceptance_decision:
            raise ValueError("final_decision must match the last acceptance round")
        if self.final_decision is AcceptanceDecision.REVISE:
            raise ValueError("ReportAcceptanceState.final_decision cannot be REVISE")
        if self.rounds[-1].acceptance_decision is AcceptanceDecision.REVISE:
            raise ValueError("final round cannot have REVISE disposition")
        if self.final_decision in {
            AcceptanceDecision.ACCEPT,
            AcceptanceDecision.ACCEPT_WITH_LIMITATIONS,
        }:
            if not self.final_payload_version:
                raise ValueError("accepted state requires final_payload_version")
            if self.final_payload_version != self.rounds[-1].final_payload_version:
                raise ValueError("state final_payload_version must match final accepted round")
        return self


class FinalAnalysisState(BaseModel):
    model_config = ConfigDict(extra="forbid")

    run_id: str = Field(min_length=1)
    snapshot_id: str = Field(min_length=1)
    target_ticker: str = Field(min_length=1)
    target_period: str = Field(min_length=1)
    macro_payload: AgentPayload
    sector_payload: AgentPayload
    company_payload: AgentPayload
    critique_history: list[CritiqueRecord] = Field(default_factory=list)
    final_report_markdown: str = Field(min_length=1)
    all_claims_have_evidence: bool


class GoldConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    tickers: tuple[str, ...] = Field(min_length=1)
    periods: tuple[str, ...] = Field(min_length=1)
    required_metrics: tuple[str, ...] = Field(min_length=1)
    min_manual_labels: int = Field(default=40, ge=1)
    min_independent_checkers: int = Field(default=2, ge=2)
    min_metric_coverage: float = Field(default=0.9, ge=0.0, le=1.0)


class GoldPromotionResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    eligible: bool
    blockers: list[str] = Field(default_factory=list)
    output_path: str | None = None
    snapshot_id: str | None = None
