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

from .acceptance_resolver import Stage1DatasetResolver
from .analysis_plan import (
    AnalysisAgent,
    AnalysisPlan,
    AnalysisRequirement,
    FulfillmentPolicy,
)
from .dataset_contract import CanonicalObservation
from .schema import (
    AssertionType,
    AtomicClaim,
    ClaimDataRef,
    CritiqueAction,
    CritiqueIssue,
    Stage1ValidationReport,
    StructuredAssertion,
)


SEMANTIC_EVALUATION_VERSION = "semantic-evaluation-v1"
STRUCTURED_CRITIC_RESULT_VERSION = "structured-critic-result-v1"
_OBSERVATION_REF_TYPES = frozenset(
    {"observation", "macro_observation", "derived_metric", "missing_cell"}
)


class SemanticDimension(StrEnum):
    GROUNDEDNESS = "groundedness"
    CROSS_LEVEL_INTEGRATION = "cross_level_integration"
    ANSWER_COVERAGE = "answer_coverage"
    LOGICAL_SOUNDNESS = "logical_soundness"
    UNCERTAINTY_LIMITATIONS = "uncertainty_limitations"
    ANALYTICAL_USEFULNESS = "analytical_usefulness"


class SemanticDimensionApplicability(StrEnum):
    APPLICABLE = "APPLICABLE"
    NOT_APPLICABLE = "NOT_APPLICABLE"


FROZEN_SEMANTIC_DIMENSIONS = frozenset(SemanticDimension)


def expected_dimension_applicability(
    plan: AnalysisPlan,
) -> dict[SemanticDimension, SemanticDimensionApplicability]:
    """Derive semantic applicability from the frozen plan, not the evaluator."""

    return {
        dimension: (
            SemanticDimensionApplicability.APPLICABLE
            if dimension is not SemanticDimension.CROSS_LEVEL_INTEGRATION
            or bool(plan.applicable_links)
            else SemanticDimensionApplicability.NOT_APPLICABLE
        )
        for dimension in SemanticDimension
    }


class SemanticDimensionResult(BaseModel):
    """One future evaluator result for one frozen semantic dimension."""

    model_config = ConfigDict(extra="forbid")

    dimension: SemanticDimension
    applicability: SemanticDimensionApplicability = SemanticDimensionApplicability.APPLICABLE
    score: float | None = Field(default=None, ge=0.0, le=1.0)
    rationale: str = Field(min_length=1)
    supporting_claim_ids: tuple[str, ...] = Field(default_factory=tuple)
    affected_requirement_ids: tuple[str, ...] = Field(default_factory=tuple)
    issue_ids: tuple[str, ...] = Field(default_factory=tuple)

    @model_validator(mode="after")
    def validate_result(self) -> "SemanticDimensionResult":
        if self.applicability is SemanticDimensionApplicability.APPLICABLE:
            if self.score is None:
                raise ValueError("applicable semantic dimension requires a score")
            if not math.isfinite(self.score):
                raise ValueError("semantic score must be finite")
        else:
            if self.score is not None:
                raise ValueError("not-applicable semantic dimension must not have a score")
            if self.supporting_claim_ids or self.affected_requirement_ids or self.issue_ids:
                raise ValueError(
                    "not-applicable semantic dimension cannot carry claims, requirements, or issues"
                )
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
    return any(
        assertion_matches_requirement(assertion, requirement)
        for assertion in claim.assertions
    )


def assertion_matches_requirement(
    assertion: StructuredAssertion,
    requirement: AnalysisRequirement,
) -> bool:
    """Check whether one assertion is in a requirement's exact scope."""

    return (
        assertion.entity in requirement.entities
        and assertion.period in requirement.periods
        and assertion.metric_id in requirement.metric_ids
    )


def ref_matches_assertion(
    ref: ClaimDataRef,
    assertion: StructuredAssertion,
) -> bool:
    """Check that a data ref addresses the assertion's exact cell."""

    return (
        ref.entity == assertion.entity
        and ref.period == assertion.period
        and ref.metric_id == assertion.metric_id
    )


def _has_numeric_assertion(assertions: Sequence[StructuredAssertion]) -> bool:
    return any(
        assertion.assertion_type
        in {
            AssertionType.METRIC_VALUE,
            AssertionType.COMPARISON,
            AssertionType.TREND,
            AssertionType.AGGREGATE,
        }
        and assertion.asserted_value is not None
        for assertion in assertions
    )


def _has_missingness_shape(assertions: Sequence[StructuredAssertion]) -> bool:
    return any(
        assertion.assertion_type is AssertionType.MISSINGNESS
        and any(
            ref.ref_type in _OBSERVATION_REF_TYPES
            for ref in assertion.data_refs
        )
        for assertion in assertions
    )


def _status_value(value: object) -> str:
    return str(getattr(value, "value", value))


def _accepted_missingness_observation(
    ref,
    resolver: Stage1DatasetResolver,
) -> tuple[CanonicalObservation | None, str | None]:
    """Resolve and prove one accepted missing canonical observation."""

    try:
        observation = resolver.resolve_observation_ref(ref)
    except (TypeError, ValueError):
        return None, f"accepted_missingness_observation_unresolved:{ref.ref_id}"
    if observation is None:
        return None, f"accepted_missingness_observation_unresolved:{ref.ref_id}"
    if (
        observation.entity_id != ref.entity
        or observation.period_id != ref.period
        or observation.metric_id != ref.metric_id
    ):
        return None, f"accepted_missingness_scope_mismatch:{ref.ref_id}"
    if (
        observation.dataset_id != resolver.dataset_ref.dataset_id
        or observation.dataset_snapshot_id != resolver.dataset_ref.dataset_snapshot_id
    ):
        return None, f"accepted_missingness_dataset_identity_mismatch:{ref.ref_id}"
    if (
        _status_value(observation.validation_status) != "missing"
        or observation.value is not None
        or observation.missing_reason != "DATA_UNAVAILABLE"
    ):
        return None, f"accepted_missingness_state_not_proven:{ref.ref_id}"
    return observation, None


def _accepted_missingness_proof(
    assertions: Sequence[StructuredAssertion],
    resolver: Stage1DatasetResolver | None,
) -> tuple[bool, tuple[str, ...]]:
    candidate_assertions = tuple(
        assertion
        for assertion in assertions
        if assertion.assertion_type is AssertionType.MISSINGNESS
        and any(ref.ref_type in _OBSERVATION_REF_TYPES for ref in assertion.data_refs)
    )
    if not candidate_assertions:
        return False, ()
    if resolver is None:
        return False, ("accepted_missingness_resolver_required",)
    diagnostics: list[str] = []
    accepted = False
    for assertion in candidate_assertions:
        refs = tuple(
            ref
            for ref in assertion.data_refs
            if ref.ref_type in _OBSERVATION_REF_TYPES
            and ref_matches_assertion(ref, assertion)
        )
        if not refs:
            diagnostics.append(
                f"accepted_missingness_matching_ref_missing:{assertion.assertion_id}"
            )
            continue
        assertion_passed = True
        for ref in refs:
            observation, diagnostic = _accepted_missingness_observation(ref, resolver)
            if observation is None:
                assertion_passed = False
                if diagnostic is not None:
                    diagnostics.append(diagnostic)
        if assertion_passed:
            accepted = True
    return accepted, tuple(dict.fromkeys(diagnostics))


def deterministic_coverage_violations(
    plan: AnalysisPlan,
    result: StructuredCriticResult,
    claims: Sequence[AtomicClaim],
    *,
    stage1_report: Stage1ValidationReport | None = None,
    dataset_resolver: Stage1DatasetResolver | None = None,
) -> tuple[str, ...]:
    """Return only checks that are deterministic before semantic judging.

    The check verifies identities and the mechanical missingness boundary.  It
    does not decide whether prose entails a fact or whether an interpretation
    is analytically good.
    """

    violations: list[str] = []
    plan_requirement_ids = {item.requirement_id for item in plan.requirements}
    plan_link_ids = {item.link_id for item in plan.applicable_links}
    expected_applicability = expected_dimension_applicability(plan)
    active_agents = {
        agent.value
        for requirement in plan.requirements
        for agent in requirement.required_agents
        if agent != AnalysisAgent.ORCHESTRATOR
    }
    allowed_issue_agents = active_agents | {AnalysisAgent.ORCHESTRATOR.value}
    if dataset_resolver is not None:
        if plan.dataset_ref != dataset_resolver.dataset_ref:
            violations.append("analysis_plan_dataset_identity_mismatch")
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
        expected = expected_applicability[dimension.dimension]
        if dimension.applicability is not expected:
            violations.append(
                "dimension_applicability_mismatch:"
                f"{dimension.dimension.value}:expected={expected.value}:"
                f"actual={dimension.applicability.value}"
            )
        result_claim_ids.extend(dimension.supporting_claim_ids)
        result_requirement_ids.extend(dimension.affected_requirement_ids)
        result_issue_ids.extend(dimension.issue_ids)
    for link_result in result.applicable_link_results:
        result_claim_ids.extend(link_result.supporting_claim_ids)
        result_issue_ids.extend(link_result.issue_ids)
        if link_result.link_id not in plan_link_ids:
            violations.append(f"unknown_link_id:{link_result.link_id}")
    result_link_ids = [item.link_id for item in result.applicable_link_results]
    missing_link_ids = sorted(plan_link_ids - set(result_link_ids))
    violations.extend(f"omitted_link_result:{item}" for item in missing_link_ids)
    issues_by_id = {issue.issue_id: issue for issue in result.critique_issues}
    for issue in result.critique_issues:
        result_claim_ids.extend(issue.affected_claim_ids)
        if issue.issue_id not in issue_ids:
            violations.append(f"unknown_issue_id:{issue.issue_id}")
        if issue.affected_agent not in allowed_issue_agents:
            violations.append(
                f"issue_agent_not_active:{issue.issue_id}:{issue.affected_agent}"
            )
        if issue.required_action is CritiqueAction.RECONCILE_CROSS_LEVEL:
            if not plan_link_ids:
                violations.append(
                    f"cross_level_reconciliation_requires_applicable_link:{issue.issue_id}"
                )
            linked_results = tuple(
                link_result
                for link_result in result.applicable_link_results
                if issue.issue_id in link_result.issue_ids
            )
            if not linked_results:
                violations.append(
                    f"cross_level_issue_link_result_missing:{issue.issue_id}"
                )
            elif len(linked_results) > 1:
                violations.append(
                    f"cross_level_issue_link_result_ambiguous:{issue.issue_id}"
                )

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
    for link_result in result.applicable_link_results:
        for issue_id in link_result.issue_ids:
            issue = issues_by_id.get(issue_id)
            if issue is not None and issue.required_action is not CritiqueAction.RECONCILE_CROSS_LEVEL:
                violations.append(
                    f"undeclared_link_issue_relation:{link_result.link_id}:{issue_id}"
                )

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
        matching_assertions = tuple(
            assertion
            for claim in matching_claims
            for assertion in claim.assertions
            if assertion_matches_requirement(assertion, requirement)
        )
        has_numeric = _has_numeric_assertion(matching_assertions)
        has_missingness_shape = _has_missingness_shape(matching_assertions)
        accepted_missingness, missingness_proof_violations = _accepted_missingness_proof(
            matching_assertions, dataset_resolver
        )
        violations.extend(
            f"{item}:{requirement.requirement_id}"
            for item in missingness_proof_violations
        )
        if numeric_gate_passed is False and has_numeric:
            violations.append(
                f"numeric_claim_rejected_by_stage1:{requirement.requirement_id}"
            )
        if requirement.fulfillment_policy is FulfillmentPolicy.DISCLOSURE_REQUIRED:
            if not any(claim.limitation.strip() for claim in matching_claims):
                violations.append(
                    f"disclosure_requirement_not_fulfilled:{requirement.requirement_id}"
                )
        elif requirement.fulfillment_policy is FulfillmentPolicy.VALID_VALUE_REQUIRED:
            if not has_numeric:
                violation = (
                    f"missingness_not_allowed:{requirement.requirement_id}"
                    if has_missingness_shape
                    else f"valid_value_required_not_fulfilled:{requirement.requirement_id}"
                )
                violations.append(
                    violation
                )
        elif not has_numeric and not accepted_missingness:
            violations.append(
                f"missing_aware_requirement_has_no_value_or_missingness:{requirement.requirement_id}"
            )
        elif accepted_missingness and stage1_report is not None and not stage1_report.passed:
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
    dataset_resolver: Stage1DatasetResolver | None = None,
) -> None:
    """Fail closed on deterministic plan/result/claim identity violations."""

    violations = deterministic_coverage_violations(
        plan,
        result,
        claims,
        stage1_report=stage1_report,
        dataset_resolver=dataset_resolver,
    )
    if violations:
        raise SemanticContractError(";".join(violations))


def validate_structured_critic_result(
    plan: AnalysisPlan,
    result: StructuredCriticResult,
    claims: Sequence[AtomicClaim],
    *,
    stage1_report: Stage1ValidationReport | None = None,
    dataset_resolver: Stage1DatasetResolver | None = None,
) -> None:
    """Validate a future critic result without evaluating semantic entailment."""

    validate_deterministic_coverage(
        plan,
        result,
        claims,
        stage1_report=stage1_report,
        dataset_resolver=dataset_resolver,
    )
