"""Versioned semantic-evaluation contracts and deterministic preflight checks.

Phase 3A stops at contracts and checks that do not require a model.  The
semantic dimensions below are intentionally represented as structured results;
semantic entailment, reasoning quality, and score generation remain Phase 3B
responsibilities.
"""

from __future__ import annotations

from enum import StrEnum
import math
from typing import Iterable, Sequence

from pydantic import BaseModel, ConfigDict, Field, model_validator

from .analysis_plan import AnalysisPlan, AnalysisRequirement, FulfillmentPolicy
from .schema import (
    AssertionType,
    AtomicClaim,
    CritiqueIssue,
    Stage1ValidationReport,
)


SEMANTIC_EVALUATION_VERSION = "semantic-evaluation-v1"
STRUCTURED_CRITIC_RESULT_VERSION = "structured-critic-result-v1"


class SemanticDimension(StrEnum):
    GROUNDEDNESS = "groundedness"
    CROSS_LEVEL_INTEGRATION = "cross_level_integration"
    ANSWER_COVERAGE = "answer_coverage"
    LOGICAL_SOUNDNESS = "logical_soundness"
    UNCERTAINTY_LIMITATIONS = "uncertainty_limitations"
    ANALYTICAL_USEFULNESS = "analytical_usefulness"


FROZEN_SEMANTIC_DIMENSIONS = frozenset(SemanticDimension)


class SemanticDimensionResult(BaseModel):
    """One future evaluator result for one frozen semantic dimension."""

    model_config = ConfigDict(extra="forbid")

    dimension: SemanticDimension
    score: float = Field(ge=0.0, le=1.0)
    rationale: str = Field(min_length=1)
    supporting_claim_ids: tuple[str, ...] = Field(default_factory=tuple)
    affected_requirement_ids: tuple[str, ...] = Field(default_factory=tuple)
    issue_ids: tuple[str, ...] = Field(default_factory=tuple)

    @model_validator(mode="after")
    def validate_result(self) -> "SemanticDimensionResult":
        if not math.isfinite(self.score):
            raise ValueError("semantic score must be finite")
        _unique(self.supporting_claim_ids, "supporting_claim_ids")
        _unique(self.affected_requirement_ids, "affected_requirement_ids")
        _unique(self.issue_ids, "issue_ids")
        return self


class ApplicableLinkResult(BaseModel):
    """Future semantic result for one link declared by the AnalysisPlan."""

    model_config = ConfigDict(extra="forbid")

    link_id: str = Field(min_length=1)
    score: float = Field(ge=0.0, le=1.0)
    rationale: str = Field(min_length=1)
    supporting_claim_ids: tuple[str, ...] = Field(default_factory=tuple)
    issue_ids: tuple[str, ...] = Field(default_factory=tuple)

    @model_validator(mode="after")
    def validate_result(self) -> "ApplicableLinkResult":
        if not math.isfinite(self.score):
            raise ValueError("applicable-link score must be finite")
        _unique(self.supporting_claim_ids, "link supporting_claim_ids")
        _unique(self.issue_ids, "link issue_ids")
        return self


class StructuredCriticResult(BaseModel):
    """Versioned future critic output, without provider/model execution."""

    model_config = ConfigDict(extra="forbid")

    contract_version: str = STRUCTURED_CRITIC_RESULT_VERSION
    evaluator_version: str = Field(min_length=1)
    dimension_scores: tuple[SemanticDimensionResult, ...] = Field(min_length=1)
    critique_issues: tuple[CritiqueIssue, ...] = Field(default_factory=tuple)
    fulfilled_requirement_ids: tuple[str, ...] = Field(default_factory=tuple)
    partially_fulfilled_requirement_ids: tuple[str, ...] = Field(default_factory=tuple)
    unfulfilled_requirement_ids: tuple[str, ...] = Field(default_factory=tuple)
    applicable_link_results: tuple[ApplicableLinkResult, ...] = Field(default_factory=tuple)

    @model_validator(mode="after")
    def validate_result_shape(self) -> "StructuredCriticResult":
        if self.contract_version != STRUCTURED_CRITIC_RESULT_VERSION:
            raise ValueError("unsupported structured critic result version")
        dimensions = [item.dimension for item in self.dimension_scores]
        if len(dimensions) != len(set(dimensions)):
            raise ValueError("dimension scores must be unique")
        if set(dimensions) != FROZEN_SEMANTIC_DIMENSIONS:
            raise ValueError("dimension scores must contain all six frozen dimensions")
        for field_name in (
            "fulfilled_requirement_ids",
            "partially_fulfilled_requirement_ids",
            "unfulfilled_requirement_ids",
        ):
            _unique(getattr(self, field_name), field_name)
        requirement_groups = (
            set(self.fulfilled_requirement_ids),
            set(self.partially_fulfilled_requirement_ids),
            set(self.unfulfilled_requirement_ids),
        )
        if len(requirement_groups[0] & requirement_groups[1]) or len(
            requirement_groups[0] & requirement_groups[2]
        ) or len(requirement_groups[1] & requirement_groups[2]):
            raise ValueError("a requirement cannot have multiple fulfillment states")
        issue_ids = [issue.issue_id for issue in self.critique_issues]
        if len(issue_ids) != len(set(issue_ids)):
            raise ValueError("critique issue IDs must be unique")
        link_ids = [item.link_id for item in self.applicable_link_results]
        if len(link_ids) != len(set(link_ids)):
            raise ValueError("applicable link result IDs must be unique")
        return self


class SemanticContractError(ValueError):
    """A deterministic Phase 3A contract/reference preflight failure."""


def _unique(values: Iterable[str], field_name: str) -> None:
    values = tuple(values)
    if any(not isinstance(value, str) or not value.strip() for value in values):
        raise ValueError(f"{field_name} must contain non-empty strings")
    if len(values) != len(set(values)):
        raise ValueError(f"{field_name} must be unique")


def _claim_matches_requirement(
    claim: AtomicClaim,
    requirement: AnalysisRequirement,
) -> bool:
    allowed_entities = set(requirement.entities)
    allowed_periods = set(requirement.periods)
    allowed_metrics = set(requirement.metric_ids)
    return any(
        assertion.entity in allowed_entities
        and assertion.period in allowed_periods
        and assertion.metric_id in allowed_metrics
        for assertion in claim.assertions
    )


def _has_numeric_assertion(claim: AtomicClaim) -> bool:
    return any(
        assertion.assertion_type
        in {
            AssertionType.METRIC_VALUE,
            AssertionType.COMPARISON,
            AssertionType.TREND,
            AssertionType.AGGREGATE,
        }
        and assertion.asserted_value is not None
        for assertion in claim.assertions
    )


def _has_explicit_missingness(claim: AtomicClaim) -> bool:
    return any(
        assertion.assertion_type is AssertionType.MISSINGNESS
        and any(
            ref.ref_type in {"missing_cell", "macro_observation"}
            for ref in assertion.data_refs
        )
        for assertion in claim.assertions
    )


def deterministic_coverage_violations(
    plan: AnalysisPlan,
    result: StructuredCriticResult,
    claims: Sequence[AtomicClaim],
    *,
    stage1_report: Stage1ValidationReport | None = None,
) -> tuple[str, ...]:
    """Return only checks that are deterministic before semantic judging.

    The check verifies identities and the mechanical missingness boundary.  It
    does not decide whether prose entails a fact or whether an interpretation
    is analytically good.
    """

    violations: list[str] = []
    plan_requirement_ids = {item.requirement_id for item in plan.requirements}
    plan_link_ids = {item.link_id for item in plan.applicable_links}
    claim_ids = [claim.claim_id for claim in claims]
    if len(claim_ids) != len(set(claim_ids)):
        violations.append("duplicate_claim_ids")
    known_claim_ids = set(claim_ids)
    issue_ids = {issue.issue_id for issue in result.critique_issues}

    classified = (
        result.fulfilled_requirement_ids
        + result.partially_fulfilled_requirement_ids
        + result.unfulfilled_requirement_ids
    )
    if len(classified) != len(set(classified)):
        violations.append("duplicate_requirement_ids")
    unknown_requirements = sorted(set(classified) - plan_requirement_ids)
    violations.extend(f"unknown_requirement_id:{item}" for item in unknown_requirements)
    missing_requirements = sorted(plan_requirement_ids - set(classified))
    violations.extend(f"unclassified_requirement_id:{item}" for item in missing_requirements)

    result_claim_ids: list[str] = []
    result_requirement_ids: list[str] = []
    result_issue_ids: list[str] = []
    for dimension in result.dimension_scores:
        result_claim_ids.extend(dimension.supporting_claim_ids)
        result_requirement_ids.extend(dimension.affected_requirement_ids)
        result_issue_ids.extend(dimension.issue_ids)
    for link_result in result.applicable_link_results:
        result_claim_ids.extend(link_result.supporting_claim_ids)
        result_issue_ids.extend(link_result.issue_ids)
        if link_result.link_id not in plan_link_ids:
            violations.append(f"unknown_link_id:{link_result.link_id}")
    for issue in result.critique_issues:
        result_claim_ids.extend(issue.affected_claim_ids)
        if issue.issue_id not in issue_ids:
            violations.append(f"unknown_issue_id:{issue.issue_id}")

    violations.extend(
        f"unknown_claim_id:{item}"
        for item in sorted(set(result_claim_ids) - known_claim_ids)
    )
    violations.extend(
        f"unknown_requirement_id:{item}"
        for item in sorted(set(result_requirement_ids) - plan_requirement_ids)
    )
    violations.extend(
        f"unknown_issue_id:{item}"
        for item in sorted(set(result_issue_ids) - issue_ids)
    )
    for issue in result.critique_issues:
        if issue.issue_id not in issue_ids:
            violations.append(f"unknown_issue_id:{issue.issue_id}")

    numeric_gate_passed = None
    if stage1_report is not None:
        numeric_gate = stage1_report.gate_results.get("numeric_accuracy")
        if numeric_gate is None:
            violations.append("stage1_numeric_gate_missing")
        else:
            numeric_gate_passed = numeric_gate.passed

    satisfied_ids = set(result.fulfilled_requirement_ids) | set(
        result.partially_fulfilled_requirement_ids
    )
    for requirement in plan.requirements:
        if requirement.requirement_id not in satisfied_ids:
            continue
        matching_claims = [
            claim for claim in claims if _claim_matches_requirement(claim, requirement)
        ]
        if not matching_claims:
            violations.append(
                f"requirement_has_no_matching_claim:{requirement.requirement_id}"
            )
            continue
        has_numeric = any(_has_numeric_assertion(claim) for claim in matching_claims)
        has_missingness = any(
            _has_explicit_missingness(claim) for claim in matching_claims
        )
        if numeric_gate_passed is False and has_numeric:
            violations.append(
                f"numeric_claim_rejected_by_stage1:{requirement.requirement_id}"
            )
        if requirement.fulfillment_policy is FulfillmentPolicy.VALID_VALUE_REQUIRED:
            if has_missingness and not has_numeric:
                violations.append(
                    f"missingness_not_allowed:{requirement.requirement_id}"
                )
        elif not has_numeric and not has_missingness:
            violations.append(
                f"missing_aware_requirement_has_no_value_or_missingness:{requirement.requirement_id}"
            )
        elif has_missingness and stage1_report is not None and not stage1_report.passed:
            violations.append(
                f"accepted_missingness_requires_stage1_pass:{requirement.requirement_id}"
            )

    return tuple(dict.fromkeys(violations))


def validate_deterministic_coverage(
    plan: AnalysisPlan,
    result: StructuredCriticResult,
    claims: Sequence[AtomicClaim],
    *,
    stage1_report: Stage1ValidationReport | None = None,
) -> None:
    """Fail closed on deterministic plan/result/claim identity violations."""

    violations = deterministic_coverage_violations(
        plan,
        result,
        claims,
        stage1_report=stage1_report,
    )
    if violations:
        raise SemanticContractError(";".join(violations))


def validate_structured_critic_result(
    plan: AnalysisPlan,
    result: StructuredCriticResult,
    claims: Sequence[AtomicClaim],
    *,
    stage1_report: Stage1ValidationReport | None = None,
) -> None:
    """Validate a future critic result without evaluating semantic entailment."""

    validate_deterministic_coverage(
        plan,
        result,
        claims,
        stage1_report=stage1_report,
    )
