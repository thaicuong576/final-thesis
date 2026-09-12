"""Provider-neutral semantic critic boundary for Phase 3B-A.

This module deliberately stops at semantic evaluation.  It validates the
deterministic Stage-1 precondition, invokes an injected critic, validates the
typed result against the frozen plan, and derives quality dimensions.  It does
not decide acceptance, revise claims, route workers, or call a model/provider.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
import math
from typing import Protocol

from pydantic import BaseModel, ConfigDict, Field, ValidationError, model_validator

from .acceptance_resolver import Stage1DatasetResolver
from .analysis_plan import AnalysisPlan
from .schema import (
    AtomicClaim,
    HardGateResult,
    QualityDimensionScores,
    Stage1ValidationReport,
)
from .semantic_evaluation import (
    SEMANTIC_EVALUATION_VERSION,
    SemanticContractError,
    SemanticDimensionApplicability,
    StructuredCriticResult,
    validate_structured_critic_result,
)


_REQUIRED_STAGE1_GATE_IDS = frozenset(
    {
        "numeric_accuracy",
        "reference_validity",
        "critical_evidence_coverage",
        "scope_compliance",
        "fabricated_or_unaccepted_records",
        "blocking_contradictions",
    }
)


class SemanticRoundContext(BaseModel):
    """Small auditable context passed to one semantic evaluation round."""

    model_config = ConfigDict(extra="forbid")

    case_id: str | None = Field(default=None, min_length=1)
    round_number: int = Field(ge=0)
    prior_issue_ids: tuple[str, ...] = Field(default_factory=tuple)

    @model_validator(mode="after")
    def validate_issue_ids(self) -> "SemanticRoundContext":
        if len(self.prior_issue_ids) != len(set(self.prior_issue_ids)):
            raise ValueError("prior_issue_ids must be unique")
        if any(not issue_id.strip() for issue_id in self.prior_issue_ids):
            raise ValueError("prior_issue_ids must contain non-empty strings")
        return self


class SemanticCritic(Protocol):
    """Injected provider-neutral semantic evaluation interface."""

    def evaluate(
        self,
        *,
        plan: AnalysisPlan,
        claims: Sequence[AtomicClaim],
        stage1_report: Stage1ValidationReport,
        round_context: SemanticRoundContext,
    ) -> StructuredCriticResult:
        """
        Evaluate an already Stage-1-valid candidate without mutating inputs.

        Implementations return only the typed critic contract.  Decisions and
        revisions belong to the later controller phase.
        """


class SemanticEvaluationError(SemanticContractError):
    """A deterministic failure at the Phase 3B-A evaluation boundary."""


class FixtureSemanticCritic:
    """Deterministic contract test double keyed by explicit case IDs.

    The fixture never infers anything from claim prose, queries data, applies
    heuristic rules, or mutates the objects supplied by the caller.
    """

    def __init__(
        self,
        results_by_case: Mapping[str, StructuredCriticResult],
    ) -> None:
        normalized: dict[str, StructuredCriticResult] = {}
        for case_id, result in results_by_case.items():
            if not isinstance(case_id, str) or not case_id.strip():
                raise ValueError("fixture case IDs must be non-empty strings")
            if not isinstance(result, StructuredCriticResult):
                raise TypeError("fixture results must be StructuredCriticResult objects")
            normalized[case_id] = result.model_copy(deep=True)
        self._results_by_case = normalized
        self._calls: list[SemanticRoundContext] = []

    @property
    def invocation_count(self) -> int:
        return len(self._calls)

    @property
    def calls(self) -> tuple[SemanticRoundContext, ...]:
        return tuple(context.model_copy(deep=True) for context in self._calls)

    def evaluate(
        self,
        *,
        plan: AnalysisPlan,
        claims: Sequence[AtomicClaim],
        stage1_report: Stage1ValidationReport,
        round_context: SemanticRoundContext,
    ) -> StructuredCriticResult:
        del plan, claims, stage1_report
        self._calls.append(round_context.model_copy(deep=True))
        case_id = round_context.case_id
        if case_id is None or case_id not in self._results_by_case:
            raise SemanticEvaluationError(
                f"fixture_case_not_found:{case_id or '<missing>'}"
            )
        return self._results_by_case[case_id].model_copy(deep=True)


class SemanticEvaluationArtifact(BaseModel):
    """Validated, decision-free output of one semantic evaluation round."""

    model_config = ConfigDict(extra="forbid")

    evaluation_version: str = SEMANTIC_EVALUATION_VERSION
    round_context: SemanticRoundContext
    critic_result: StructuredCriticResult
    quality_scores: QualityDimensionScores

    @model_validator(mode="after")
    def quality_scores_are_derived(self) -> "SemanticEvaluationArtifact":
        expected = _quality_scores_from_result(self.critic_result)
        if self.quality_scores != expected:
            raise ValueError("quality_scores must be derived from critic_result")
        return self


def _validate_stage1_report(report: Stage1ValidationReport) -> None:
    """Re-check the structural invariant before invoking semantic evaluation."""

    if not isinstance(report, Stage1ValidationReport):
        raise SemanticEvaluationError("stage1_report_type_invalid")
    if set(report.gate_results) != _REQUIRED_STAGE1_GATE_IDS:
        raise SemanticEvaluationError("stage1_report_gate_set_invalid")

    for gate_id, gate in report.gate_results.items():
        if not isinstance(gate, HardGateResult) or gate.gate_id != gate_id:
            raise SemanticEvaluationError(f"stage1_report_gate_identity_invalid:{gate_id}")
        if gate.passed_count > gate.evaluated_count:
            raise SemanticEvaluationError(f"stage1_report_gate_counts_invalid:{gate_id}")
        expected_rate = gate.passed_count / gate.evaluated_count if gate.evaluated_count else 0.0
        if not math.isclose(gate.rate, expected_rate, rel_tol=0.0, abs_tol=1e-12):
            raise SemanticEvaluationError(f"stage1_report_gate_rate_invalid:{gate_id}")
        if gate.passed and (gate.violations or gate.rate + 1e-12 < gate.required_rate):
            raise SemanticEvaluationError(f"stage1_report_gate_status_invalid:{gate_id}")
        if not gate.passed and not gate.violations:
            raise SemanticEvaluationError(f"stage1_report_gate_status_invalid:{gate_id}")

    expected_passed = all(gate.passed for gate in report.gate_results.values()) and not report.integrity_violations
    if report.passed != expected_passed:
        raise SemanticEvaluationError("stage1_report_status_invalid")
    if not report.passed:
        raise SemanticEvaluationError("stage1_failed_semantic_evaluation_blocked")


def _quality_scores_from_result(result: StructuredCriticResult) -> QualityDimensionScores:
    values = {
        item.dimension.value: (
            item.score
            if item.applicability is SemanticDimensionApplicability.APPLICABLE
            else None
        )
        for item in result.dimension_scores
    }
    try:
        return QualityDimensionScores(**values)
    except (TypeError, ValueError, ValidationError) as exc:
        raise SemanticEvaluationError("quality_dimensions_invalid") from exc


def evaluate_semantic_round(
    critic: SemanticCritic,
    *,
    plan: AnalysisPlan,
    claims: Sequence[AtomicClaim],
    stage1_report: Stage1ValidationReport,
    round_context: SemanticRoundContext,
    dataset_resolver: Stage1DatasetResolver | None = None,
) -> SemanticEvaluationArtifact:
    """Evaluate one Stage-1-valid round through an injected typed critic.

    The critic receives defensive copies.  The original plan, claims, report,
    and round context are the values validated and returned to the caller.
    This function never creates an acceptance decision or revision round.
    """

    if not isinstance(plan, AnalysisPlan):
        raise SemanticEvaluationError("analysis_plan_type_invalid")
    normalized_claims = tuple(claims)
    if any(not isinstance(claim, AtomicClaim) for claim in normalized_claims):
        raise SemanticEvaluationError("claims_type_invalid")
    if not isinstance(round_context, SemanticRoundContext):
        raise SemanticEvaluationError("round_context_type_invalid")

    _validate_stage1_report(stage1_report)

    evaluate = getattr(critic, "evaluate", None)
    if not callable(evaluate):
        raise SemanticEvaluationError("semantic_critic_interface_invalid")

    raw_result = evaluate(
        plan=plan.model_copy(deep=True),
        claims=tuple(claim.model_copy(deep=True) for claim in normalized_claims),
        stage1_report=stage1_report.model_copy(deep=True),
        round_context=round_context.model_copy(deep=True),
    )
    if not isinstance(raw_result, StructuredCriticResult):
        raise SemanticEvaluationError("semantic_critic_result_type_invalid")

    try:
        result = StructuredCriticResult.model_validate(
            raw_result.model_dump(mode="python")
        )
        validate_structured_critic_result(
            plan,
            result,
            normalized_claims,
            stage1_report=stage1_report,
            dataset_resolver=dataset_resolver,
        )
    except Exception as exc:
        if isinstance(exc, SemanticEvaluationError):
            raise
        raise SemanticEvaluationError(str(exc)) from exc

    quality_scores = _quality_scores_from_result(result)
    return SemanticEvaluationArtifact(
        round_context=round_context.model_copy(deep=True),
        critic_result=result,
        quality_scores=quality_scores,
    )
