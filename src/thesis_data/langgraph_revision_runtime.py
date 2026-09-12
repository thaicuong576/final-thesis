"""LangGraph reference adapter for the framework-neutral revision kernel.

This module owns only workflow-engine wiring.  Acceptance policy, semantic
validation, issue lifecycle, revision routing, and candidate identity remain
in :mod:`thesis_data.revision_controller`.
"""

from __future__ import annotations

from langgraph.graph import END, START, StateGraph
from langgraph.runtime import Runtime
from typing_extensions import TypedDict

from .acceptance_resolver import Stage1DatasetResolver
from .analysis_plan import AnalysisPlan
from .revision_controller import (
    BoundedRevisionResult,
    RevisionControllerError,
    RevisionWorkflowKernel,
    RevisionWorkflowState,
)
from .schema import (
    AcceptanceDecision,
    AcceptanceRound,
    AtomicClaim,
    CritiqueIssue,
    CritiqueIssueStatus,
)
from .semantic_evaluation import StructuredCriticResult


class LangGraphRevisionState(TypedDict, total=False):
    """Durable graph state; runtime services are intentionally absent."""

    run_id: str
    plan: AnalysisPlan
    plan_payload_hash: str
    current_claims: tuple[AtomicClaim, ...]
    current_candidate_hash: str
    current_payload_version: str
    current_round_number: int
    rounds: tuple[AcceptanceRound, ...]
    issue_status_ledger: dict[str, CritiqueIssueStatus]
    previous_open_issue_ids: tuple[str, ...]
    previous_open_issues: tuple[CritiqueIssue, ...]
    revised_agents_for_round: tuple[str, ...]
    worker_payload_versions_for_round: dict[str, str]
    orchestrator_payload_version_for_round: str | None
    current_disposition: AcceptanceDecision | None
    current_critic_result: StructuredCriticResult | None
    terminal_reason: str | None
    final_result: BoundedRevisionResult | None


class LangGraphRuntimeContext(TypedDict, total=False):
    """Per-invocation services; context is not checkpointed graph state."""

    dataset_resolver: Stage1DatasetResolver | None


class LangGraphRevisionError(RevisionControllerError):
    """Fail-closed adapter boundary error."""


def _domain_state(state: LangGraphRevisionState) -> RevisionWorkflowState:
    try:
        return RevisionWorkflowState.model_validate(state)
    except Exception as exc:
        raise LangGraphRevisionError("graph_state_invalid") from exc


def _graph_state(state: RevisionWorkflowState) -> LangGraphRevisionState:
    return state.model_dump(mode="json")  # type: ignore[return-value]


def _dataset_resolver(
    runtime: Runtime[LangGraphRuntimeContext],
) -> Stage1DatasetResolver | None:
    context = runtime.context
    if context is None:
        return None
    return context.get("dataset_resolver")


def _route_after_evaluate(state: LangGraphRevisionState) -> str:
    disposition = _domain_state(state).current_disposition
    if disposition is AcceptanceDecision.REVISE:
        return "execute_revision"
    if disposition in {
        AcceptanceDecision.ACCEPT,
        AcceptanceDecision.ACCEPT_WITH_LIMITATIONS,
        AcceptanceDecision.FAIL_ACCEPTANCE,
    }:
        return "finalize"
    raise LangGraphRevisionError("graph_evaluation_disposition_missing")


def _route_after_revision(state: LangGraphRevisionState) -> str:
    disposition = _domain_state(state).current_disposition
    if disposition is None:
        return "evaluate_round"
    if disposition is AcceptanceDecision.FAIL_ACCEPTANCE:
        return "finalize"
    raise LangGraphRevisionError("graph_revision_disposition_invalid")


class LangGraphRevisionWorkflow:
    """Reference LangGraph execution of one bounded revision state machine."""

    def __init__(
        self,
        *,
        kernel: RevisionWorkflowKernel,
        checkpointer: object | None = None,
    ) -> None:
        if not isinstance(kernel, RevisionWorkflowKernel):
            raise TypeError("kernel must be a RevisionWorkflowKernel")
        self._kernel = kernel
        self._checkpointer = checkpointer
        self._graph = self._compile_graph(checkpointer)

    @property
    def graph(self):
        """Return the compiled graph for inspection and checkpoint queries."""

        return self._graph

    def _compile_graph(self, checkpointer: object | None):
        graph = StateGraph(
            LangGraphRevisionState,
            context_schema=LangGraphRuntimeContext,
        )

        def evaluate_round(
            state: LangGraphRevisionState,
            runtime: Runtime[LangGraphRuntimeContext],
        ) -> LangGraphRevisionState:
            next_state = self._kernel.evaluate_current_round(
                _domain_state(state),
                dataset_resolver=_dataset_resolver(runtime),
            )
            return _graph_state(next_state)

        def execute_revision(
            state: LangGraphRevisionState,
        ) -> LangGraphRevisionState:
            next_state = self._kernel.execute_revision_step(_domain_state(state))
            return _graph_state(next_state)

        def finalize(
            state: LangGraphRevisionState,
        ) -> LangGraphRevisionState:
            next_state = self._kernel.finalize(_domain_state(state))
            return _graph_state(
                _domain_state(state).model_copy(update={"final_result": next_state})
            )

        graph.add_node("evaluate_round", evaluate_round)
        graph.add_node("execute_revision", execute_revision)
        graph.add_node("finalize", finalize)
        graph.add_edge(START, "evaluate_round")
        graph.add_conditional_edges(
            "evaluate_round",
            _route_after_evaluate,
            {
                "execute_revision": "execute_revision",
                "finalize": "finalize",
            },
        )
        graph.add_conditional_edges(
            "execute_revision",
            _route_after_revision,
            {
                "evaluate_round": "evaluate_round",
                "finalize": "finalize",
            },
        )
        graph.add_edge("finalize", END)
        return graph.compile(checkpointer=checkpointer)

    def run(
        self,
        *,
        run_id: str,
        plan: AnalysisPlan,
        claims: tuple[AtomicClaim, ...] | list[AtomicClaim],
        initial_payload_version: str,
        dataset_resolver: Stage1DatasetResolver | None = None,
    ) -> BoundedRevisionResult:
        initial_state = self._kernel.initial_state(
            run_id=run_id,
            plan=plan,
            claims=claims,
            initial_payload_version=initial_payload_version,
        )
        config = None
        if self._checkpointer is not None:
            config = {"configurable": {"thread_id": run_id}}
        output = self._graph.invoke(
            _graph_state(initial_state),
            config=config,
            context={"dataset_resolver": dataset_resolver},
        )
        final_state = _domain_state(output)
        if final_state.final_result is None:
            raise LangGraphRevisionError("graph_final_result_missing")
        return final_state.final_result.model_copy(deep=True)


def build_langgraph_revision_workflow(
    *,
    kernel: RevisionWorkflowKernel,
    checkpointer: object | None = None,
) -> LangGraphRevisionWorkflow:
    """Build the reference graph without changing the canonical result type."""

    return LangGraphRevisionWorkflow(kernel=kernel, checkpointer=checkpointer)
