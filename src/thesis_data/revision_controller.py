"""Framework-neutral bounded semantic revision state machine.

Phase 3B-B owns workflow policy and audit state, not agent execution.  Stage-1,
semantic critique, revision, and synthesis are injected behind small
provider-neutral protocols so a later workflow framework can become an adapter
without becoming the thesis architecture.
"""

from __future__ import annotations

from collections.abc import Sequence
import hashlib
import json
from typing import Protocol

from pydantic import BaseModel, ConfigDict, Field, ValidationError, model_validator

from .acceptance import allowed_limited_acceptance_reason
from .acceptance_resolver import Stage1DatasetResolver
from .analysis_plan import AnalysisAgent, AnalysisPlan
from .schema import (
    AcceptanceDecision,
    AcceptancePolicy,
    AcceptanceRound,
    AtomicClaim,
    CritiqueIssue,
    CritiqueIssueStatus,
    CritiqueIssueType,
    CritiqueSeverity,
    ReportAcceptanceState,
    Stage1ValidationReport,
    UnresolvedReasonCode,
)
from .semantic_critic import (
    SemanticEvaluationArtifact,
    SemanticEvaluationError,
    SemanticRoundContext,
    SemanticCritic,
    evaluate_semantic_round,
    numeric_or_period_tokens,
    validate_synthesis_summary,
    validate_synthesis_supporting_claim_ids,
)
from .semantic_evaluation import StructuredCriticResult


REVISION_CONTROLLER_VERSION = "bounded-revision-controller-v1"


class Stage1Evaluator(Protocol):
    """Provider-neutral deterministic Stage-1 evaluator."""

    def evaluate(
        self,
        *,
        plan: AnalysisPlan,
        claims: Sequence[AtomicClaim],
        policy: AcceptancePolicy,
    ) -> Stage1ValidationReport:
        ...


class RevisionRequest(BaseModel):
    """Auditable input for one targeted revision execution."""

    model_config = ConfigDict(extra="forbid")

    plan: AnalysisPlan
    current_candidate_hash: str = Field(min_length=1)
    current_claims: tuple[AtomicClaim, ...]
    current_synthesis_summary: str | None = Field(default=None, min_length=1)
    current_synthesis_supporting_claim_ids: tuple[str, ...] = Field(default_factory=tuple)
    selected_issues: tuple[CritiqueIssue, ...] = Field(min_length=1)
    target_specialists: tuple[str, ...] = Field(default_factory=tuple)
    next_round_number: int = Field(ge=1)

    @model_validator(mode="after")
    def validate_revision_scope(self) -> "RevisionRequest":
        validate_synthesis_summary(self.current_synthesis_summary)
        validate_synthesis_supporting_claim_ids(
            self.current_synthesis_summary,
            self.current_synthesis_supporting_claim_ids,
            self.current_claims,
        )
        if self.current_candidate_hash != candidate_hash(
            self.plan,
            self.current_claims,
            self.current_synthesis_summary,
            self.current_synthesis_supporting_claim_ids,
        ):
            raise ValueError(
                "current_candidate_hash does not match current_claims and synthesis_summary"
            )
        issue_ids = [issue.issue_id for issue in self.selected_issues]
        if len(issue_ids) != len(set(issue_ids)):
            raise ValueError("selected revision issue IDs must be unique")
        if any(issue.resolution_status is not CritiqueIssueStatus.OPEN for issue in self.selected_issues):
            raise ValueError("revision requests may contain only OPEN issues")
        if len(self.target_specialists) != len(set(self.target_specialists)):
            raise ValueError("target_specialists must be unique")
        if any(not specialist.strip() for specialist in self.target_specialists):
            raise ValueError("target_specialists must contain non-empty strings")
        return self


class RevisionResult(BaseModel):
    """Canonical candidate returned by an injected revision executor."""

    model_config = ConfigDict(extra="forbid")

    revised_claims: tuple[AtomicClaim, ...]
    revised_synthesis_summary: str | None = Field(default=None, min_length=1)
    revised_synthesis_supporting_claim_ids: tuple[str, ...] | None = None
    revised_agents: tuple[str, ...] = Field(default_factory=tuple)
    revised_claim_ids: dict[str, tuple[str, ...]] = Field(default_factory=dict)
    payload_version: str = Field(min_length=1)
    worker_payload_versions: dict[str, str] = Field(default_factory=dict)
    orchestrator_payload_version: str | None = Field(default=None, min_length=1)

    @model_validator(mode="after")
    def validate_agents(self) -> "RevisionResult":
        validate_synthesis_summary(self.revised_synthesis_summary)
        if self.revised_synthesis_summary is None and (
            self.revised_synthesis_supporting_claim_ids is not None
        ):
            raise ValueError(
                "revised_synthesis_supporting_claim_ids_require_revised_summary"
            )
        if self.revised_synthesis_summary is not None and (
            self.revised_synthesis_supporting_claim_ids is None
        ):
            raise ValueError(
                "revised_synthesis_summary_requires_supporting_claim_ids"
            )
        if self.revised_synthesis_supporting_claim_ids is not None:
            validate_synthesis_supporting_claim_ids(
                self.revised_synthesis_summary,
                self.revised_synthesis_supporting_claim_ids,
                self.revised_claims,
            )
        if len(self.revised_agents) != len(set(self.revised_agents)):
            raise ValueError("revised_agents must be unique")
        if any(not agent.strip() for agent in self.revised_agents):
            raise ValueError("revised_agents must contain non-empty strings")
        if any(not agent.strip() for agent in self.revised_claim_ids):
            raise ValueError("revised_claim_ids keys must contain non-empty specialist IDs")
        assigned_claim_ids: list[str] = []
        for agent, claim_ids in self.revised_claim_ids.items():
            if any(not claim_id.strip() for claim_id in claim_ids):
                raise ValueError("revised_claim_ids must contain non-empty claim IDs")
            if len(claim_ids) != len(set(claim_ids)):
                raise ValueError(f"revised_claim_ids for {agent} must be unique")
            assigned_claim_ids.extend(claim_ids)
        if len(assigned_claim_ids) != len(set(assigned_claim_ids)):
            raise ValueError("a claim ID cannot be assigned to multiple specialists")
        return self


class RevisionExecutor(Protocol):
    """Framework-neutral targeted revision + merge + re-synthesis boundary."""

    def execute(self, *, request: RevisionRequest) -> RevisionResult:
        ...


class RevisionControllerError(ValueError):
    """Fail-closed controller or injected-adapter contract error."""


_REVISION_PRESENTATION_FIELDS = frozenset(
    {"claim_text", "title", "interpretation", "limitation"}
)


def _validate_revision_claim_delta(
    *,
    current_claims: Sequence[AtomicClaim],
    revised_claims: Sequence[AtomicClaim],
    target_specialists: Sequence[str],
    revised_claim_ids: dict[str, tuple[str, ...]],
) -> tuple[str, ...]:
    """Require every declared specialist target to change exact claim artifacts.

    Claim identities stay stable. Only presentation and interpretation prose may
    change, and all numeric/period tokens in those fields must remain identical.
    """

    current_by_id = {claim.claim_id: claim for claim in current_claims}
    revised_by_id = {claim.claim_id: claim for claim in revised_claims}
    if len(current_by_id) != len(current_claims) or len(revised_by_id) != len(
        revised_claims
    ):
        raise RevisionControllerError("revision_claim_ids_must_be_unique")
    if set(current_by_id) != set(revised_by_id):
        raise RevisionControllerError("revision_claim_identity_set_changed")

    changed_claim_ids: list[str] = []
    for claim_id in current_by_id:
        before = current_by_id[claim_id].model_dump(mode="json")
        after = revised_by_id[claim_id].model_dump(mode="json")
        if before == after:
            continue
        changed_fields = {
            field_name
            for field_name in before
            if before[field_name] != after[field_name]
        }
        protected_changes = changed_fields - _REVISION_PRESENTATION_FIELDS
        if protected_changes:
            raise RevisionControllerError(
                f"revision_changed_protected_claim_fields:{claim_id}:"
                f"{','.join(sorted(protected_changes))}"
            )
        for field_name in _REVISION_PRESENTATION_FIELDS & changed_fields:
            if numeric_or_period_tokens(before[field_name]) != numeric_or_period_tokens(
                after[field_name]
            ):
                raise RevisionControllerError(
                    f"revision_changed_numeric_or_period_claim_text:{claim_id}"
                )
        changed_claim_ids.append(claim_id)

    targets = tuple(target_specialists)
    if set(revised_claim_ids) != set(targets):
        raise RevisionControllerError("revision_result_claim_targets_mismatch")
    for target in targets:
        if not revised_claim_ids[target]:
            raise RevisionControllerError(
                f"revision_target_claim_not_revised:{target}"
            )
    flattened_ids = [
        claim_id
        for target in targets
        for claim_id in revised_claim_ids[target]
    ]
    if len(flattened_ids) != len(set(flattened_ids)):
        raise RevisionControllerError("revision_result_claim_ids_overlap")
    if any(claim_id not in current_by_id for claim_id in flattened_ids):
        raise RevisionControllerError("revision_result_claim_id_unknown")
    if set(flattened_ids) != set(changed_claim_ids):
        raise RevisionControllerError("revision_result_changed_claim_ids_mismatch")
    return tuple(changed_claim_ids)


class BoundedRevisionResult(BaseModel):
    """Final terminal state and candidate produced by the controller."""

    model_config = ConfigDict(extra="forbid")

    acceptance_state: ReportAcceptanceState
    final_claims: tuple[AtomicClaim, ...]
    final_synthesis_summary: str | None = Field(default=None, min_length=1)
    final_synthesis_supporting_claim_ids: tuple[str, ...] = Field(default_factory=tuple)
    final_candidate_hash: str = Field(min_length=1)
    was_revised: bool = False
    synthesis_was_revised: bool = False
    terminal_reason: str | None = Field(default=None, min_length=1)

    @model_validator(mode="after")
    def validate_final_synthesis(self) -> "BoundedRevisionResult":
        validate_synthesis_summary(self.final_synthesis_summary)
        validate_synthesis_supporting_claim_ids(
            self.final_synthesis_summary,
            self.final_synthesis_supporting_claim_ids,
            self.final_claims,
        )
        return self


def candidate_hash(
    plan: AnalysisPlan,
    claims: Sequence[AtomicClaim],
    synthesis_summary: str | None = None,
    synthesis_supporting_claim_ids: Sequence[str] = (),
) -> str:
    """Return a stable SHA-256 fingerprint for one canonical candidate."""

    if not isinstance(plan, AnalysisPlan):
        raise TypeError("candidate hash requires an AnalysisPlan")
    normalized_claims = tuple(claims)
    if any(not isinstance(claim, AtomicClaim) for claim in normalized_claims):
        raise TypeError("candidate hash requires AtomicClaim objects")
    validate_synthesis_summary(synthesis_summary)
    normalized_supporting_ids = validate_synthesis_supporting_claim_ids(
        synthesis_summary, synthesis_supporting_claim_ids, normalized_claims
    )
    claim_ids = [claim.claim_id for claim in normalized_claims]
    if len(claim_ids) != len(set(claim_ids)):
        raise ValueError("candidate claim IDs must be unique")
    payload = {
        "plan_version": plan.plan_version,
        "dataset_id": plan.dataset_id,
        "dataset_snapshot_id": plan.dataset_snapshot_id,
        "query_id": plan.query_id,
        "periods": list(plan.scope.periods),
        "claims": [
            claim.model_dump(mode="json")
            for claim in sorted(normalized_claims, key=lambda item: item.claim_id)
        ],
    }
    if synthesis_summary is not None:
        payload["synthesis_summary"] = synthesis_summary
        payload["synthesis_supporting_claim_ids"] = list(normalized_supporting_ids)
    serialized = json.dumps(
        payload,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")
    return hashlib.sha256(serialized).hexdigest()


compute_candidate_hash = candidate_hash
candidate_fingerprint = candidate_hash


def _active_specialists(plan: AnalysisPlan) -> frozenset[str]:
    return frozenset(
        agent.value
        for requirement in plan.requirements
        for agent in requirement.required_agents
        if agent is not AnalysisAgent.ORCHESTRATOR
    )


def _open_issues(result: StructuredCriticResult) -> tuple[CritiqueIssue, ...]:
    return tuple(
        issue
        for issue in result.critique_issues
        if issue.resolution_status is CritiqueIssueStatus.OPEN
    )


def _unresolved_issues(result: StructuredCriticResult) -> tuple[CritiqueIssue, ...]:
    return tuple(
        issue
        for issue in result.critique_issues
        if issue.resolution_status is CritiqueIssueStatus.UNRESOLVED
    )


def _limited_issue_allowed(issue: CritiqueIssue) -> bool:
    return (
        issue.issue_type in {
            CritiqueIssueType.MISSING_DATA,
            CritiqueIssueType.MISSING_EVIDENCE,
        }
        and issue.severity is not CritiqueSeverity.BLOCKER
        and issue.unresolved_reason_code is not None
        and allowed_limited_acceptance_reason(issue.unresolved_reason_code)
    )


def _issue_ids_by_status(
    issues: Sequence[CritiqueIssue],
) -> tuple[tuple[str, ...], tuple[str, ...], tuple[UnresolvedReasonCode, ...]]:
    resolved: list[str] = []
    unresolved: list[str] = []
    reasons: list[UnresolvedReasonCode] = []
    for issue in issues:
        if issue.resolution_status in {
            CritiqueIssueStatus.RESOLVED,
            CritiqueIssueStatus.EXPLAINED,
        }:
            resolved.append(issue.issue_id)
        elif issue.resolution_status is CritiqueIssueStatus.UNRESOLVED:
            unresolved.append(issue.issue_id)
            if issue.unresolved_reason_code is not None and issue.unresolved_reason_code not in reasons:
                reasons.append(issue.unresolved_reason_code)
    return tuple(resolved), tuple(unresolved), tuple(reasons)


def _validate_issue_lifecycle(
    issue_status_ledger: dict[str, CritiqueIssueStatus],
    previous_open_ids: frozenset[str],
    result: StructuredCriticResult,
    previous_open_issues: Sequence[CritiqueIssue] = (),
    previous_rounds: Sequence[AcceptanceRound] = (),
) -> None:
    current = {issue.issue_id: issue for issue in result.critique_issues}
    for issue_id in sorted(previous_open_ids):
        if issue_id not in current:
            raise RevisionControllerError(f"prior_issue_disappeared:{issue_id}")

    terminal_statuses = {
        CritiqueIssueStatus.RESOLVED,
        CritiqueIssueStatus.EXPLAINED,
        CritiqueIssueStatus.UNRESOLVED,
    }
    previous_by_id = {issue.issue_id: issue for issue in previous_open_issues}
    for issue_id in sorted(previous_by_id):
        current_issue = current.get(issue_id)
        if current_issue is None:
            continue
        previous_issue = previous_by_id[issue_id]
        if current_issue.issue_type != previous_issue.issue_type:
            raise RevisionControllerError(
                f"prior_issue_identity_changed:{issue_id}:issue_type"
            )
        if current_issue.affected_agent != previous_issue.affected_agent:
            raise RevisionControllerError(
                f"prior_issue_identity_changed:{issue_id}:affected_agent"
            )
        previous_requirement_ids = tuple(
            sorted(set(previous_issue.affected_requirement_ids))
        )
        current_requirement_ids = tuple(
            sorted(set(current_issue.affected_requirement_ids))
        )
        if current_requirement_ids != previous_requirement_ids:
            raise RevisionControllerError(
                f"prior_issue_identity_changed:{issue_id}:affected_requirement_ids"
            )

    historical_identity: dict[str, tuple[CritiqueIssueType, str, tuple[str, ...]]] = {}
    historical_terminal_status: dict[str, CritiqueIssueStatus] = {}

    def observe(issue: CritiqueIssue) -> None:
        issue_id = issue.issue_id
        identity = (
            issue.issue_type,
            issue.affected_agent,
            tuple(sorted(set(issue.affected_requirement_ids))),
        )
        previous_identity = historical_identity.get(issue_id)
        if previous_identity is not None:
            if identity[0] != previous_identity[0]:
                raise RevisionControllerError(
                    f"historical_issue_identity_changed:{issue_id}:issue_type"
                )
            if identity[1] != previous_identity[1]:
                raise RevisionControllerError(
                    f"historical_issue_identity_changed:{issue_id}:affected_agent"
                )
            if identity[2] != previous_identity[2]:
                raise RevisionControllerError(
                    f"historical_issue_identity_changed:{issue_id}:affected_requirement_ids"
                )
        else:
            historical_identity[issue_id] = identity

        previous_terminal_status = historical_terminal_status.get(issue_id)
        if previous_terminal_status is not None:
            if issue.resolution_status is CritiqueIssueStatus.OPEN:
                # Preserve the established public diagnostic for terminal
                # issue reopening while applying it across the full history.
                raise RevisionControllerError(f"issue_terminal_reopened:{issue_id}")
            if issue.resolution_status is not previous_terminal_status:
                raise RevisionControllerError(
                    f"historical_issue_terminal_status_changed:{issue_id}"
                )
        elif issue.resolution_status in terminal_statuses:
            historical_terminal_status[issue_id] = issue.resolution_status

    for round_state in previous_rounds:
        for issue in round_state.critique_issues:
            observe(issue)
    for issue_id in sorted(previous_by_id):
        observe(previous_by_id[issue_id])
    for issue_id in sorted(current):
        observe(current[issue_id])

    # Keep compatibility with older/in-memory callers that provide only the
    # terminal status ledger rather than persisted round history.
    for issue_id in sorted(current):
        prior_status = issue_status_ledger.get(issue_id)
        if prior_status not in terminal_statuses:
            continue
        current_status = current[issue_id].resolution_status
        if current_status is CritiqueIssueStatus.OPEN:
            raise RevisionControllerError(f"issue_terminal_reopened:{issue_id}")
        if current_status is not prior_status:
            raise RevisionControllerError(
                f"historical_issue_terminal_status_changed:{issue_id}"
            )


def _stable_payload_hash(payload: object) -> str:
    serialized = json.dumps(
        payload,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")
    return hashlib.sha256(serialized).hexdigest()


def _plan_payload_hash(plan: AnalysisPlan) -> str:
    return _stable_payload_hash(plan.model_dump(mode="json"))


class RevisionWorkflowState(BaseModel):
    """Serializable domain state shared by controller and workflow adapters."""

    model_config = ConfigDict(extra="forbid")

    run_id: str = Field(min_length=1)
    plan: AnalysisPlan
    plan_payload_hash: str = Field(min_length=1)
    current_claims: tuple[AtomicClaim, ...]
    current_synthesis_summary: str | None = Field(default=None, min_length=1)
    current_synthesis_supporting_claim_ids: tuple[str, ...] = Field(default_factory=tuple)
    current_candidate_hash: str = Field(min_length=1)
    current_payload_version: str = Field(min_length=1)
    current_round_number: int = Field(ge=0)
    rounds: tuple[AcceptanceRound, ...] = Field(default_factory=tuple)
    issue_status_ledger: dict[str, CritiqueIssueStatus] = Field(default_factory=dict)
    previous_open_issue_ids: tuple[str, ...] = Field(default_factory=tuple)
    previous_open_issues: tuple[CritiqueIssue, ...] = Field(default_factory=tuple)
    revised_agents_for_round: tuple[str, ...] = Field(default_factory=tuple)
    revised_claim_ids_for_round: dict[str, tuple[str, ...]] = Field(default_factory=dict)
    was_revised: bool = False
    synthesis_was_revised: bool = False
    worker_payload_versions_for_round: dict[str, str] = Field(default_factory=dict)
    orchestrator_payload_version_for_round: str | None = None
    current_disposition: AcceptanceDecision | None = None
    current_critic_result: StructuredCriticResult | None = None
    terminal_reason: str | None = None
    final_result: BoundedRevisionResult | None = None

    @model_validator(mode="after")
    def validate_previous_open_issue_context(self) -> "RevisionWorkflowState":
        validate_synthesis_summary(self.current_synthesis_summary)
        validate_synthesis_supporting_claim_ids(
            self.current_synthesis_summary,
            self.current_synthesis_supporting_claim_ids,
            self.current_claims,
        )
        if self.current_candidate_hash != candidate_hash(
            self.plan,
            self.current_claims,
            self.current_synthesis_summary,
            self.current_synthesis_supporting_claim_ids,
        ):
            raise ValueError(
                "current_candidate_hash does not match current candidate artifact"
            )
        if len(self.previous_open_issue_ids) != len(set(self.previous_open_issue_ids)):
            raise ValueError("previous_open_issue_ids must be unique")
        if any(not issue_id.strip() for issue_id in self.previous_open_issue_ids):
            raise ValueError("previous_open_issue_ids must contain non-empty strings")
        issue_ids = tuple(issue.issue_id for issue in self.previous_open_issues)
        if len(issue_ids) != len(set(issue_ids)):
            raise ValueError("previous_open_issues IDs must be unique")
        if any(
            issue.resolution_status is not CritiqueIssueStatus.OPEN
            for issue in self.previous_open_issues
        ):
            raise ValueError("previous_open_issues must contain only OPEN issues")
        if self.previous_open_issues and self.previous_open_issue_ids != issue_ids:
            raise ValueError("previous_open_issue_ids must match previous_open_issues IDs")
        return self


class RevisionWorkflowKernel:
    """One framework-neutral step kernel for the bounded revision workflow."""

    def __init__(
        self,
        *,
        policy: AcceptancePolicy,
        stage1_evaluator: Stage1Evaluator,
        semantic_critic: SemanticCritic,
        revision_executor: RevisionExecutor | None,
        acceptance_model_version: str = REVISION_CONTROLLER_VERSION,
    ) -> None:
        self._policy = policy.model_copy(deep=True)
        self._stage1_evaluator = stage1_evaluator
        self._semantic_critic = semantic_critic
        self._revision_executor = revision_executor
        self._acceptance_model_version = acceptance_model_version

    def initial_state(
        self,
        *,
        run_id: str,
        plan: AnalysisPlan,
        claims: Sequence[AtomicClaim],
        initial_payload_version: str,
        synthesis_summary: str | None = None,
        synthesis_supporting_claim_ids: Sequence[str] = (),
    ) -> RevisionWorkflowState:
        if not run_id.strip():
            raise ValueError("run_id must be non-empty")
        if not initial_payload_version.strip():
            raise ValueError("initial_payload_version must be non-empty")
        if not isinstance(plan, AnalysisPlan):
            raise RevisionControllerError("analysis_plan_type_invalid")
        current_claims = tuple(claims)
        if any(not isinstance(claim, AtomicClaim) for claim in current_claims):
            raise RevisionControllerError("claims_type_invalid")
        try:
            validate_synthesis_summary(synthesis_summary)
            normalized_supporting_ids = validate_synthesis_supporting_claim_ids(
                synthesis_summary, synthesis_supporting_claim_ids, current_claims
            )
        except (TypeError, ValueError) as exc:
            raise RevisionControllerError("synthesis_summary_invalid") from exc
        current_hash = candidate_hash(
            plan,
            current_claims,
            synthesis_summary,
            normalized_supporting_ids,
        )
        return RevisionWorkflowState(
            run_id=run_id,
            plan=plan.model_copy(deep=True),
            plan_payload_hash=_plan_payload_hash(plan),
            current_claims=tuple(
                claim.model_copy(deep=True) for claim in current_claims
            ),
            current_synthesis_summary=synthesis_summary,
            current_synthesis_supporting_claim_ids=normalized_supporting_ids,
            current_candidate_hash=current_hash,
            current_payload_version=initial_payload_version,
            current_round_number=0,
        )

    def evaluate_current_round(
        self,
        state: RevisionWorkflowState,
        *,
        dataset_resolver: Stage1DatasetResolver | None = None,
    ) -> RevisionWorkflowState:
        state = self._copy_state(state)
        if state.current_disposition is not None:
            raise RevisionControllerError("round_already_evaluated")

        current_hash = candidate_hash(
            state.plan,
            state.current_claims,
            state.current_synthesis_summary,
            state.current_synthesis_supporting_claim_ids,
        )
        stage1_report = self._evaluate_stage1(state.plan, state.current_claims)
        if not stage1_report.passed:
            round_state = self._build_round(
                state=state,
                candidate_hash_value=current_hash,
                stage1_report=stage1_report,
                result=None,
                decision=AcceptanceDecision.FAIL_ACCEPTANCE,
            )
            return state.model_copy(
                update={
                    "current_candidate_hash": current_hash,
                    "rounds": state.rounds + (round_state,),
                    "current_disposition": AcceptanceDecision.FAIL_ACCEPTANCE,
                    "current_critic_result": None,
                    "terminal_reason": "stage1_failed",
                }
            )

        context = SemanticRoundContext(
            round_number=state.current_round_number,
            prior_issue_ids=(
                tuple(issue.issue_id for issue in state.previous_open_issues)
                if state.previous_open_issues
                else tuple(sorted(state.previous_open_issue_ids))
            ),
            prior_issues=tuple(
                issue.model_copy(deep=True)
                for issue in state.previous_open_issues
            ),
            synthesis_summary=state.current_synthesis_summary,
            synthesis_supporting_claim_ids=state.current_synthesis_supporting_claim_ids,
        )
        try:
            artifact = evaluate_semantic_round(
                self._semantic_critic,
                plan=state.plan,
                claims=state.current_claims,
                stage1_report=stage1_report,
                round_context=context,
                dataset_resolver=dataset_resolver,
            )
            _validate_issue_lifecycle(
                dict(state.issue_status_ledger),
                frozenset(state.previous_open_issue_ids),
                artifact.critic_result,
                tuple(
                    issue.model_copy(deep=True)
                    for issue in state.previous_open_issues
                ),
                tuple(state.rounds),
            )
        except (SemanticEvaluationError, RevisionControllerError) as exc:
            round_state = self._build_round(
                state=state,
                candidate_hash_value=current_hash,
                stage1_report=stage1_report,
                result=None,
                decision=AcceptanceDecision.FAIL_ACCEPTANCE,
            )
            return state.model_copy(
                update={
                    "current_candidate_hash": current_hash,
                    "rounds": state.rounds + (round_state,),
                    "current_disposition": AcceptanceDecision.FAIL_ACCEPTANCE,
                    "current_critic_result": None,
                    "terminal_reason": str(exc),
                }
            )

        decision, quality_total = self._decide(artifact, state.current_round_number)
        round_state = self._build_round(
            state=state,
            candidate_hash_value=current_hash,
            stage1_report=stage1_report,
            result=artifact.critic_result,
            quality_scores=artifact.quality_scores,
            quality_total=quality_total,
            decision=decision,
        )
        issue_status_ledger = dict(state.issue_status_ledger)
        for issue in artifact.critic_result.critique_issues:
            if issue.resolution_status in {
                CritiqueIssueStatus.RESOLVED,
                CritiqueIssueStatus.EXPLAINED,
                CritiqueIssueStatus.UNRESOLVED,
            }:
                issue_status_ledger[issue.issue_id] = issue.resolution_status
        terminal_reason = (
            self._failure_reason(artifact, state.current_round_number)
            if decision is AcceptanceDecision.FAIL_ACCEPTANCE
            else None
        )
        return state.model_copy(
            update={
                "current_candidate_hash": current_hash,
                "rounds": state.rounds + (round_state,),
                "issue_status_ledger": issue_status_ledger,
                "current_disposition": decision,
                "current_critic_result": artifact.critic_result.model_copy(deep=True),
                "terminal_reason": terminal_reason,
            }
        )

    def execute_revision_step(self, state: RevisionWorkflowState) -> RevisionWorkflowState:
        state = self._copy_state(state)
        if state.current_disposition is not AcceptanceDecision.REVISE:
            raise RevisionControllerError("revision_step_requires_revise_disposition")
        if state.current_critic_result is None:
            raise RevisionControllerError("revision_critic_result_missing")
        try:
            revision = self._execute_revision(
                plan=state.plan,
                claims=state.current_claims,
                synthesis_summary=state.current_synthesis_summary,
                synthesis_supporting_claim_ids=(
                    state.current_synthesis_supporting_claim_ids
                ),
                candidate_hash_value=state.current_candidate_hash,
                result=state.current_critic_result,
                next_round_number=state.current_round_number + 1,
            )
        except (RevisionControllerError, TypeError, ValueError) as exc:
            failed_round = self._replace_decision(
                state.rounds[-1],
                AcceptanceDecision.FAIL_ACCEPTANCE,
            )
            return state.model_copy(
                update={
                    "rounds": state.rounds[:-1] + (failed_round,),
                    "current_disposition": AcceptanceDecision.FAIL_ACCEPTANCE,
                    "current_critic_result": None,
                    "terminal_reason": str(exc),
                }
            )

        revised_claims = tuple(
            claim.model_copy(deep=True) for claim in revision.revised_claims
        )
        revised_synthesis_summary = (
            revision.revised_synthesis_summary
            if revision.revised_synthesis_summary is not None
            else state.current_synthesis_summary
        )
        revised_synthesis_supporting_claim_ids = (
            revision.revised_synthesis_supporting_claim_ids
            if revision.revised_synthesis_summary is not None
            else state.current_synthesis_supporting_claim_ids
        )
        assert revised_synthesis_supporting_claim_ids is not None
        next_hash = candidate_hash(
            state.plan,
            revised_claims,
            revised_synthesis_summary,
            revised_synthesis_supporting_claim_ids,
        )
        synthesis_changed = (
            revised_synthesis_summary != state.current_synthesis_summary
            or revised_synthesis_supporting_claim_ids
            != state.current_synthesis_supporting_claim_ids
        )
        candidate_changed = next_hash != state.current_candidate_hash
        previous_open_issues = tuple(
            sorted(
                _open_issues(state.current_critic_result),
                key=lambda issue: issue.issue_id,
            )
        )
        previous_open_issue_ids = tuple(issue.issue_id for issue in previous_open_issues)
        return state.model_copy(
            update={
                "current_claims": revised_claims,
                "current_synthesis_summary": revised_synthesis_summary,
                "current_synthesis_supporting_claim_ids": (
                    revised_synthesis_supporting_claim_ids
                ),
                "current_candidate_hash": next_hash,
                "current_payload_version": revision.payload_version,
                "current_round_number": state.current_round_number + 1,
                "previous_open_issue_ids": previous_open_issue_ids,
                "previous_open_issues": tuple(
                    issue.model_copy(deep=True) for issue in previous_open_issues
                ),
                "revised_agents_for_round": tuple(revision.revised_agents),
                "revised_claim_ids_for_round": dict(revision.revised_claim_ids),
                "was_revised": state.was_revised or candidate_changed,
                "synthesis_was_revised": (
                    state.synthesis_was_revised or synthesis_changed
                ),
                "worker_payload_versions_for_round": dict(
                    revision.worker_payload_versions
                ),
                "orchestrator_payload_version_for_round": revision.orchestrator_payload_version,
                "current_disposition": None,
                "current_critic_result": None,
                "terminal_reason": None,
            }
        )

    def finalize(self, state: RevisionWorkflowState) -> BoundedRevisionResult:
        state = self._copy_state(state)
        if _plan_payload_hash(state.plan) != state.plan_payload_hash:
            raise RevisionControllerError("analysis_plan_mutated")
        if state.current_disposition in {None, AcceptanceDecision.REVISE}:
            raise RevisionControllerError("workflow_not_terminal")
        if not state.rounds:
            raise RevisionControllerError("workflow_has_no_rounds")

        final_round = state.rounds[-1]
        acceptance_state = ReportAcceptanceState(
            acceptance_model_version=self._acceptance_model_version,
            run_id=state.run_id,
            policy=self._policy.model_copy(deep=True),
            rounds=tuple(state.rounds),
            final_payload_version=(
                final_round.final_payload_version
                if final_round.acceptance_decision
                in {
                    AcceptanceDecision.ACCEPT,
                    AcceptanceDecision.ACCEPT_WITH_LIMITATIONS,
                }
                else None
            ),
            final_statement_links=(),
            final_decision=final_round.acceptance_decision,
        )
        return BoundedRevisionResult(
            acceptance_state=acceptance_state,
            final_claims=tuple(
                claim.model_copy(deep=True) for claim in state.current_claims
            ),
            final_synthesis_summary=state.current_synthesis_summary,
            final_synthesis_supporting_claim_ids=(
                state.current_synthesis_supporting_claim_ids
            ),
            final_candidate_hash=candidate_hash(
                state.plan,
                state.current_claims,
                state.current_synthesis_summary,
                state.current_synthesis_supporting_claim_ids,
            ),
            was_revised=state.was_revised,
            synthesis_was_revised=state.synthesis_was_revised,
            terminal_reason=state.terminal_reason,
        )

    @staticmethod
    def _copy_state(state: RevisionWorkflowState) -> RevisionWorkflowState:
        if not isinstance(state, RevisionWorkflowState):
            raise RevisionControllerError("workflow_state_type_invalid")
        return state.model_copy(deep=True)

    def _evaluate_stage1(
        self,
        plan: AnalysisPlan,
        claims: Sequence[AtomicClaim],
    ) -> Stage1ValidationReport:
        try:
            report = self._stage1_evaluator.evaluate(
                plan=plan.model_copy(deep=True),
                claims=tuple(claim.model_copy(deep=True) for claim in claims),
                policy=self._policy.model_copy(deep=True),
            )
        except Exception as exc:
            raise RevisionControllerError("stage1_evaluator_failed") from exc
        if not isinstance(report, Stage1ValidationReport):
            raise RevisionControllerError("stage1_report_type_invalid")
        return report

    def _execute_revision(
        self,
        *,
        plan: AnalysisPlan,
        claims: Sequence[AtomicClaim],
        synthesis_summary: str | None,
        synthesis_supporting_claim_ids: Sequence[str],
        candidate_hash_value: str,
        result: StructuredCriticResult,
        next_round_number: int,
    ) -> RevisionResult:
        open_issues = _open_issues(result)
        active_specialists = _active_specialists(plan)
        targets = tuple(
            sorted(
                {
                    issue.affected_agent
                    for issue in open_issues
                    if issue.affected_agent != AnalysisAgent.ORCHESTRATOR.value
                }
            )
        )
        if any(target not in active_specialists for target in targets):
            raise RevisionControllerError("revision_target_specialist_not_active")
        if self._revision_executor is None:
            raise RevisionControllerError("revision_executor_required")

        request = RevisionRequest(
            plan=plan.model_copy(deep=True),
            current_candidate_hash=candidate_hash_value,
            current_claims=tuple(claim.model_copy(deep=True) for claim in claims),
            current_synthesis_summary=synthesis_summary,
            current_synthesis_supporting_claim_ids=tuple(
                synthesis_supporting_claim_ids
            ),
            selected_issues=tuple(issue.model_copy(deep=True) for issue in open_issues),
            target_specialists=targets,
            next_round_number=next_round_number,
        )
        try:
            raw_revision = self._revision_executor.execute(request=request)
        except Exception as exc:
            raise RevisionControllerError("revision_executor_failed") from exc
        if not isinstance(raw_revision, RevisionResult):
            raise RevisionControllerError("revision_result_type_invalid")
        try:
            revision = RevisionResult.model_validate(raw_revision.model_dump(mode="python"))
        except (TypeError, ValueError, ValidationError) as exc:
            raise RevisionControllerError("revision_result_malformed") from exc

        revised_agents = set(revision.revised_agents)
        if revised_agents != set(targets):
            raise RevisionControllerError("revision_result_agents_mismatch")
        _validate_revision_claim_delta(
            current_claims=claims,
            revised_claims=revision.revised_claims,
            target_specialists=targets,
            revised_claim_ids=revision.revised_claim_ids,
        )
        if any(
            issue.affected_agent == AnalysisAgent.ORCHESTRATOR.value
            for issue in open_issues
        ):
            resulting_summary = (
                revision.revised_synthesis_summary
                if revision.revised_synthesis_summary is not None
                else synthesis_summary
            )
            resulting_support_ids = (
                revision.revised_synthesis_supporting_claim_ids
                if revision.revised_synthesis_summary is not None
                else tuple(synthesis_supporting_claim_ids)
            )
            if resulting_summary == synthesis_summary and resulting_support_ids == tuple(
                synthesis_supporting_claim_ids
            ):
                raise RevisionControllerError("orchestrator_synthesis_not_revised")
        candidate_hash(
            plan,
            revision.revised_claims,
            (
                revision.revised_synthesis_summary
                if revision.revised_synthesis_summary is not None
                else synthesis_summary
            ),
            (
                revision.revised_synthesis_supporting_claim_ids
                if revision.revised_synthesis_summary is not None
                else synthesis_supporting_claim_ids
            ),
        )
        return revision

    def _decide(
        self,
        artifact: SemanticEvaluationArtifact,
        round_number: int,
    ) -> tuple[AcceptanceDecision, float]:
        quality_total = artifact.quality_scores.weighted_total(self._policy.quality_weights)
        result = artifact.critic_result
        open_issues = _open_issues(result)
        unresolved_issues = _unresolved_issues(result)
        if open_issues:
            if round_number < self._policy.max_revision_rounds:
                return AcceptanceDecision.REVISE, quality_total
            return AcceptanceDecision.FAIL_ACCEPTANCE, quality_total
        if quality_total + 1e-12 < self._policy.provisional_threshold:
            return AcceptanceDecision.FAIL_ACCEPTANCE, quality_total
        if result.unfulfilled_requirement_ids:
            return AcceptanceDecision.FAIL_ACCEPTANCE, quality_total
        if result.partially_fulfilled_requirement_ids:
            if not unresolved_issues or not all(
                _limited_issue_allowed(issue) for issue in unresolved_issues
            ):
                return AcceptanceDecision.FAIL_ACCEPTANCE, quality_total
            limitation_requirement_ids = {
                requirement_id
                for issue in unresolved_issues
                if _limited_issue_allowed(issue)
                for requirement_id in issue.affected_requirement_ids
            }
            if not set(result.partially_fulfilled_requirement_ids).issubset(
                limitation_requirement_ids
            ):
                return AcceptanceDecision.FAIL_ACCEPTANCE, quality_total
        if unresolved_issues:
            if all(_limited_issue_allowed(issue) for issue in unresolved_issues):
                return AcceptanceDecision.ACCEPT_WITH_LIMITATIONS, quality_total
            return AcceptanceDecision.FAIL_ACCEPTANCE, quality_total
        if result.partially_fulfilled_requirement_ids:
            return AcceptanceDecision.FAIL_ACCEPTANCE, quality_total
        return AcceptanceDecision.ACCEPT, quality_total

    def _build_round(
        self,
        *,
        state: RevisionWorkflowState,
        candidate_hash_value: str,
        stage1_report: Stage1ValidationReport,
        result: StructuredCriticResult | None,
        decision: AcceptanceDecision,
        quality_scores=None,
        quality_total: float | None = None,
    ) -> AcceptanceRound:
        issues = result.critique_issues if result is not None else ()
        resolved_ids, unresolved_ids, unresolved_reasons = _issue_ids_by_status(issues)
        return AcceptanceRound(
            round_number=state.current_round_number,
            candidate_hash=candidate_hash_value,
            candidate_claim_ids=tuple(claim.claim_id for claim in state.current_claims),
            candidate_synthesis_summary=state.current_synthesis_summary,
            candidate_synthesis_supporting_claim_ids=(
                state.current_synthesis_supporting_claim_ids
            ),
            candidate_payload_version=state.current_payload_version,
            worker_payload_versions=dict(state.worker_payload_versions_for_round),
            orchestrator_payload_version=(
                state.orchestrator_payload_version_for_round
                or state.current_payload_version
            ),
            critique_issues=tuple(issues),
            resolved_issue_ids=resolved_ids,
            unresolved_issue_ids=unresolved_ids,
            hard_gate_results=dict(stage1_report.gate_results),
            quality_scores=quality_scores,
            quality_total=quality_total,
            provisional_threshold=self._policy.provisional_threshold,
            affected_agents=tuple(sorted({issue.affected_agent for issue in issues})),
            revised_agents=tuple(state.revised_agents_for_round),
            revised_claim_ids=dict(state.revised_claim_ids_for_round),
            final_payload_version=(
                state.current_payload_version
                if decision
                in {
                    AcceptanceDecision.ACCEPT,
                    AcceptanceDecision.ACCEPT_WITH_LIMITATIONS,
                }
                else None
            ),
            acceptance_decision=decision,
            unresolved_reason_codes=unresolved_reasons,
        )

    @staticmethod
    def _replace_decision(
        round_state: AcceptanceRound,
        decision: AcceptanceDecision,
    ) -> AcceptanceRound:
        payload = round_state.model_dump(mode="python")
        payload["acceptance_decision"] = decision
        return AcceptanceRound(**payload)

    @staticmethod
    def _failure_reason(
        artifact: SemanticEvaluationArtifact,
        round_number: int,
    ) -> str:
        result = artifact.critic_result
        if _open_issues(result) and round_number >= 0:
            return "revision_not_available_or_budget_exhausted"
        if result.unfulfilled_requirement_ids:
            return "required_requirement_unfulfilled"
        if result.partially_fulfilled_requirement_ids:
            return "partial_requirement_not_limited_acceptance_eligible"
        return "semantic_quality_or_acceptance_policy_failed"


class BoundedRevisionController:
    """Execute the bounded, framework-neutral semantic revision workflow."""

    def __init__(
        self,
        *,
        policy: AcceptancePolicy,
        stage1_evaluator: Stage1Evaluator,
        semantic_critic: SemanticCritic,
        revision_executor: RevisionExecutor | None,
        acceptance_model_version: str = REVISION_CONTROLLER_VERSION,
    ) -> None:
        self._kernel = RevisionWorkflowKernel(
            policy=policy,
            stage1_evaluator=stage1_evaluator,
            semantic_critic=semantic_critic,
            revision_executor=revision_executor,
            acceptance_model_version=acceptance_model_version,
        )

    def run(
        self,
        *,
        run_id: str,
        plan: AnalysisPlan,
        claims: Sequence[AtomicClaim],
        initial_payload_version: str,
        dataset_resolver: Stage1DatasetResolver | None = None,
        synthesis_summary: str | None = None,
        synthesis_supporting_claim_ids: Sequence[str] = (),
    ) -> BoundedRevisionResult:
        state = self._kernel.initial_state(
            run_id=run_id,
            plan=plan,
            claims=claims,
            initial_payload_version=initial_payload_version,
            synthesis_summary=synthesis_summary,
            synthesis_supporting_claim_ids=synthesis_supporting_claim_ids,
        )
        while True:
            state = self._kernel.evaluate_current_round(
                state,
                dataset_resolver=dataset_resolver,
            )
            if state.current_disposition is not AcceptanceDecision.REVISE:
                break
            state = self._kernel.execute_revision_step(state)
            if state.current_disposition is AcceptanceDecision.FAIL_ACCEPTANCE:
                break
        return self._kernel.finalize(state)
