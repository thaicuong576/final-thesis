"""Provider-neutral semantic critic boundary for Phase 3B-A.

This module deliberately stops at semantic evaluation.  It validates the
deterministic Stage-1 precondition, invokes an injected critic, validates the
typed result against the frozen plan, and derives quality dimensions.  It does
not decide acceptance, revise claims, route workers, or call a model/provider.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
import math
import re
import unicodedata
from typing import Any, Literal, Protocol

from pydantic import BaseModel, ConfigDict, Field, ValidationError, model_validator

from .acceptance_resolver import Stage1DatasetResolver
from .analysis_plan import AnalysisPlan
from .schema import (
    AtomicClaim,
    CritiqueIssue,
    CritiqueIssueStatus,
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

# Synthesis summaries are qualitative in the current contract. Detect number
# words as whole Unicode tokens so phrases such as "seventeen percent" and
# "mười bảy phần trăm" are rejected without matching substrings like "one" in
# "someone". Keep this provider-neutral for API adapters to reuse.
_NUMERIC_WORDS = frozenset(
    {
        "zero", "one", "two", "three", "four", "five", "six", "seven",
        "eight", "nine", "ten", "eleven", "twelve", "thirteen",
        "fourteen", "fifteen", "sixteen", "seventeen", "eighteen",
        "nineteen", "twenty", "thirty", "forty", "fifty", "sixty",
        "seventy", "eighty", "ninety", "hundred", "thousand", "million",
        "billion", "trillion", "quadrillion", "quintillion", "first",
        "second", "third", "fourth", "fifth", "sixth", "seventh",
        "eighth", "ninth", "tenth", "eleventh", "twelfth", "thirteenth",
        "fourteenth", "fifteenth", "sixteenth", "seventeenth", "eighteenth",
        "nineteenth", "twentieth", "thirtieth", "fortieth", "fiftieth",
        "sixtieth", "seventieth", "eightieth", "ninetieth", "half",
        "halves", "quarter", "quarters", "dozen", "score",
        # Vietnamese cardinal, scale, and common fractional number words.
        "không", "một", "mốt", "hai", "ba", "tư", "bốn", "năm", "lăm",
        "sáu", "bảy", "tám", "chín", "mười", "mươi", "chục", "trăm",
        "nghìn", "ngàn", "triệu", "tỷ", "tỉ", "linh", "lẻ", "nửa",
        "rưỡi",
    }
)
_NUMERIC_TOKEN_PATTERN = re.compile(r"[+-]?\d+(?:[.,]\d+)*(?:%|bps|x)?|[^\W\d_]+", re.IGNORECASE)


def numeric_or_period_tokens(value: object) -> tuple[str, ...]:
    """Return ordered numeric and period-bearing tokens from prose.

    Digit literals and English/Vietnamese number words are matched as complete
    tokens. The same helper is used for synthesis rejection and to ensure a
    claim revision does not alter the numeric content of presentation prose.
    """

    normalized = unicodedata.normalize("NFC", str(value))
    tokens: list[str] = []
    for token in _NUMERIC_TOKEN_PATTERN.findall(normalized):
        folded = token.casefold()
        if any(character.isdigit() for character in folded) or folded in _NUMERIC_WORDS:
            tokens.append(folded)
    return tuple(tokens)


def validate_synthesis_summary(summary: str | None) -> str | None:
    """Validate the report-level prose that is reviewed as a separate artifact.

    Synthesis prose has no direct numeric evidence contract in this layer, so
    numeric literals (including year/period digits) are rejected. API adapters
    remain responsible for grounding qualitative statements in their explicit
    support set.
    """

    if summary is None:
        return None
    if not isinstance(summary, str) or not summary.strip():
        raise ValueError("synthesis_summary_must_be_non_empty_text")
    if numeric_or_period_tokens(summary):
        raise ValueError("synthesis_summary_numeric_or_period_literal_forbidden")
    return summary


def validate_synthesis_supporting_claim_ids(
    summary: str | None,
    supporting_claim_ids: Sequence[str],
    claims: Sequence[AtomicClaim],
) -> tuple[str, ...]:
    """Validate that report synthesis cites only ordered candidate claims."""

    normalized_ids = tuple(supporting_claim_ids)
    if summary is None and normalized_ids:
        raise ValueError("synthesis_supporting_claim_ids_require_summary")
    if summary is not None and not normalized_ids:
        raise ValueError("synthesis_summary_requires_supporting_claim_ids")
    if any(not isinstance(claim_id, str) or not claim_id.strip() for claim_id in normalized_ids):
        raise ValueError("synthesis_supporting_claim_ids_must_be_non_empty_strings")
    if len(normalized_ids) != len(set(normalized_ids)):
        raise ValueError("synthesis_supporting_claim_ids_must_be_unique")

    ordered_claim_ids = tuple(claim.claim_id for claim in claims)
    if len(ordered_claim_ids) != len(set(ordered_claim_ids)):
        raise ValueError("candidate_claim_ids_must_be_unique")
    positions = {claim_id: index for index, claim_id in enumerate(ordered_claim_ids)}
    unknown_ids = tuple(claim_id for claim_id in normalized_ids if claim_id not in positions)
    if unknown_ids:
        raise ValueError("synthesis_supporting_claim_ids_must_reference_candidate_claims")
    if tuple(sorted(normalized_ids, key=positions.__getitem__)) != normalized_ids:
        raise ValueError("synthesis_supporting_claim_ids_must_follow_candidate_order")
    return normalized_ids


class SemanticRoundContext(BaseModel):
    """Small auditable context passed to one semantic evaluation round."""

    model_config = ConfigDict(extra="forbid")

    case_id: str | None = Field(default=None, min_length=1)
    round_number: int = Field(ge=0)
    prior_issue_ids: tuple[str, ...] = Field(default_factory=tuple)
    prior_issues: tuple[CritiqueIssue, ...] = Field(default_factory=tuple)
    synthesis_target_id: Literal["synthesis"] = "synthesis"
    synthesis_summary: str | None = Field(default=None, min_length=1)
    synthesis_supporting_claim_ids: tuple[str, ...] = Field(default_factory=tuple)
    narrative: tuple[Any, ...] = Field(default_factory=tuple)
    report_spec: dict[str, Any] | None = None
    cross_level_candidates: tuple[Any, ...] = Field(default_factory=tuple)

    @model_validator(mode="after")
    def validate_issue_context(self) -> "SemanticRoundContext":
        validate_synthesis_summary(self.synthesis_summary)
        if any(
            not isinstance(claim_id, str) or not claim_id.strip()
            for claim_id in self.synthesis_supporting_claim_ids
        ):
            raise ValueError(
                "synthesis_supporting_claim_ids_must_be_non_empty_strings"
            )
        if len(self.synthesis_supporting_claim_ids) != len(
            set(self.synthesis_supporting_claim_ids)
        ):
            raise ValueError("synthesis_supporting_claim_ids_must_be_unique")
        if self.synthesis_summary is None and self.synthesis_supporting_claim_ids:
            raise ValueError("synthesis_supporting_claim_ids_require_summary")
        if self.synthesis_summary is not None and not self.synthesis_supporting_claim_ids:
            raise ValueError("synthesis_summary_requires_supporting_claim_ids")
        if len(self.prior_issue_ids) != len(set(self.prior_issue_ids)):
            raise ValueError("prior_issue_ids must be unique")
        if any(not issue_id.strip() for issue_id in self.prior_issue_ids):
            raise ValueError("prior_issue_ids must contain non-empty strings")
        issue_ids = tuple(issue.issue_id for issue in self.prior_issues)
        if len(issue_ids) != len(set(issue_ids)):
            raise ValueError("prior_issues IDs must be unique")
        if any(
            issue.resolution_status is not CritiqueIssueStatus.OPEN
            for issue in self.prior_issues
        ):
            raise ValueError("prior_issues must contain only OPEN issues")
        if self.prior_issues and self.prior_issue_ids != issue_ids:
            raise ValueError("prior_issue_ids must match prior_issues IDs")
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

    try:
        checked_round_context = SemanticRoundContext.model_validate(
            round_context.model_dump(mode="python")
        )
    except (TypeError, ValueError, ValidationError) as exc:
        raise SemanticEvaluationError("round_context_invalid") from exc

    _validate_stage1_report(stage1_report)

    evaluate = getattr(critic, "evaluate", None)
    if not callable(evaluate):
        raise SemanticEvaluationError("semantic_critic_interface_invalid")

    raw_result = evaluate(
        plan=plan.model_copy(deep=True),
        claims=tuple(claim.model_copy(deep=True) for claim in normalized_claims),
        stage1_report=stage1_report.model_copy(deep=True),
        round_context=checked_round_context.model_copy(deep=True),
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
        validate_synthesis_supporting_claim_ids(
            checked_round_context.synthesis_summary,
            checked_round_context.synthesis_supporting_claim_ids,
            normalized_claims,
        )
        if checked_round_context.synthesis_summary is None and any(
            issue.affected_agent == "orchestrator"
            for issue in result.critique_issues
        ):
            raise SemanticEvaluationError("orchestrator_synthesis_target_unavailable")
    except Exception as exc:
        if isinstance(exc, SemanticEvaluationError):
            raise
        raise SemanticEvaluationError(str(exc)) from exc

    quality_scores = _quality_scores_from_result(result)
    return SemanticEvaluationArtifact(
        round_context=checked_round_context.model_copy(deep=True),
        critic_result=result,
        quality_scores=quality_scores,
    )
