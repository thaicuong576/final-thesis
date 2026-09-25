import inspect
from pathlib import Path
import unittest

from langgraph.checkpoint.memory import InMemorySaver

from thesis_data.analysis_plan import (
    ANALYSIS_PLAN_VERSION,
    AnalysisAgent,
    AnalysisPlan,
    AnalysisRequirement,
    AnalysisScope,
    CausalClaimPolicy,
    FulfillmentPolicy,
    InferenceCeiling,
    MissingDataPolicy,
    RequirementType,
    build_tcb_macro_analysis_plan,
)
from thesis_data.dataset_contract import DatasetRef
from thesis_data.langgraph_revision_runtime import (
    LangGraphRevisionWorkflow,
    LangGraphRevisionState,
    build_langgraph_revision_workflow,
)
from thesis_data.revision_controller import (
    BoundedRevisionController,
    RevisionResult,
    RevisionWorkflowKernel,
)
from thesis_data.schema import (
    AcceptanceDecision,
    AcceptancePolicy,
    AssertionType,
    AtomicClaim,
    ClaimDataRef,
    ClaimScope,
    CritiqueAction,
    CritiqueIssue,
    CritiqueIssueStatus,
    CritiqueIssueType,
    CritiqueSeverity,
    HardGateResult,
    InferenceType,
    Stage1ValidationReport,
    StructuredAssertion,
    UnresolvedReasonCode,
)
from thesis_data.semantic_evaluation import (
    ApplicableLinkResult,
    SemanticDimension,
    SemanticDimensionApplicability,
    SemanticDimensionResult,
    StructuredCriticResult,
)


def _plan() -> AnalysisPlan:
    return AnalysisPlan(
        plan_version=ANALYSIS_PLAN_VERSION,
        dataset_id="dataset",
        dataset_snapshot_id="snapshot",
        query_id="langgraph-query",
        normalized_question="Report the company observation.",
        scope=AnalysisScope(
            entities=("TCB",),
            periods=("2024_Q4",),
            company_metric_ids=("bank.roa",),
        ),
        requirements=(
            AnalysisRequirement(
                requirement_id="R1",
                requirement_type=RequirementType.FACTUAL_OBSERVATION,
                description="Report the company observation.",
                required_agents=(AnalysisAgent.COMPANY,),
                entities=("TCB",),
                periods=("2024_Q4",),
                metric_ids=("bank.roa",),
                inference_ceiling=InferenceCeiling.OBSERVATION_ONLY,
                fulfillment_policy=FulfillmentPolicy.VALID_VALUE_REQUIRED,
                missing_data_policy=MissingDataPolicy.REJECT_MISSING,
            ),
        ),
        requested_outputs=("structured_facts",),
        causal_claim_policy=CausalClaimPolicy.ASSOCIATION_ONLY,
    )


def _claim() -> AtomicClaim:
    ref = ClaimDataRef(
        ref_id="company-roa",
        ref_type="observation",
        entity="TCB",
        period="2024_Q4",
        metric_id="bank.roa",
    )
    assertion = StructuredAssertion(
        assertion_id="company-roa-assertion",
        assertion_type=AssertionType.METRIC_VALUE,
        entity="TCB",
        period="2024_Q4",
        metric_id="bank.roa",
        asserted_value=1.2,
        unit="percent",
        data_refs=(ref,),
    )
    return AtomicClaim(
        claim_id="company-claim",
        claim_text="TCB ROA was 1.2% in 2024_Q4.",
        claim_type="factual",
        title="Company ROA",
        interpretation="The requested observation is reported.",
        limitation="The observation is limited to the requested period.",
        scope=ClaimScope(
            entities=("TCB",),
            periods=("2024_Q4",),
            metric_ids=("bank.roa",),
        ),
        assertions=(assertion,),
        inference_type=InferenceType.FACT,
    )


def _stage1(passed: bool = True):
    gate_ids = (
        "numeric_accuracy",
        "reference_validity",
        "critical_evidence_coverage",
        "scope_compliance",
        "fabricated_or_unaccepted_records",
        "blocking_contradictions",
    )
    return Stage1ValidationReport(
        passed=passed,
        gate_results={
            gate_id: HardGateResult(
                gate_id=gate_id,
                passed=passed,
                rate=1.0 if passed else 0.0,
                required_rate=1.0,
                evaluation_unit="fixture",
                evaluated_count=1,
                passed_count=1 if passed else 0,
                violations=() if passed else ("stage1_fixture_failure",),
            )
            for gate_id in gate_ids
        },
        integrity_violations=() if passed else ("stage1_fixture_failure",),
    )


def _issue(
    *,
    issue_id="issue-1",
    status=CritiqueIssueStatus.OPEN,
    issue_type=CritiqueIssueType.MISSING_DATA,
    reason=None,
    affected_requirement_ids=(),
    agent="company",
) -> CritiqueIssue:
    return CritiqueIssue(
        issue_id=issue_id,
        issue_type=issue_type,
        severity=CritiqueSeverity.MAJOR,
        affected_agent=agent,
        affected_requirement_ids=tuple(affected_requirement_ids),
        description="Fixture issue.",
        required_action=CritiqueAction.REVISE_CLAIM,
        resolution_status=status,
        unresolved_reason_code=reason,
    )


def _result(
    plan: AnalysisPlan,
    *,
    fulfilled=(),
    partial=(),
    unfulfilled=None,
    score=0.9,
    issues=(),
    link_results=(),
) -> StructuredCriticResult:
    fulfilled = tuple(fulfilled)
    partial = tuple(partial)
    if unfulfilled is None:
        classified = set(fulfilled) | set(partial)
        unfulfilled = tuple(
            requirement.requirement_id
            for requirement in plan.requirements
            if requirement.requirement_id not in classified
        )
    cross_applicable = bool(plan.applicable_links)
    dimensions = tuple(
        SemanticDimensionResult(
            dimension=dimension,
            applicability=(
                SemanticDimensionApplicability.APPLICABLE
                if cross_applicable or dimension is not SemanticDimension.CROSS_LEVEL_INTEGRATION
                else SemanticDimensionApplicability.NOT_APPLICABLE
            ),
            score=(
                score
                if cross_applicable or dimension is not SemanticDimension.CROSS_LEVEL_INTEGRATION
                else None
            ),
            rationale="deterministic fixture result",
        )
        for dimension in SemanticDimension
    )
    return StructuredCriticResult(
        evaluator_version="langgraph-fixture-v1",
        dimension_scores=dimensions,
        critique_issues=tuple(issues),
        fulfilled_requirement_ids=fulfilled,
        partially_fulfilled_requirement_ids=partial,
        unfulfilled_requirement_ids=tuple(unfulfilled),
        applicable_link_results=tuple(link_results),
    )


class _Stage1Sequence:
    def __init__(self, reports):
        self.reports = list(reports)
        self.calls = []

    def evaluate(self, *, plan, claims, policy):
        del plan, claims, policy
        self.calls.append(True)
        if not self.reports:
            raise AssertionError("unexpected Stage-1 call")
        return self.reports.pop(0).model_copy(deep=True)


class _CriticSequence:
    def __init__(self, results):
        self.results = list(results)
        self.calls = []

    def evaluate(self, *, plan, claims, stage1_report, round_context):
        self.calls.append(round_context.model_copy(deep=True))
        del plan, claims, stage1_report
        if not self.results:
            raise AssertionError("unexpected critic call")
        return self.results.pop(0).model_copy(deep=True)


class _RevisionSequence:
    def __init__(self, results):
        self.results = list(results)
        self.calls = []

    def execute(self, *, request):
        self.calls.append(request.model_copy(deep=True))
        if not self.results:
            raise AssertionError("unexpected revision call")
        result = self.results.pop(0).model_copy(deep=True)
        current_by_id = {claim.claim_id: claim for claim in request.current_claims}
        if result.revised_claims and all(
            claim.claim_id in current_by_id
            and claim.model_dump(mode="json")
            == current_by_id[claim.claim_id].model_dump(mode="json")
            for claim in result.revised_claims
        ):
            result = result.model_copy(
                update={
                    "revised_claims": tuple(
                        current_by_id[claim.claim_id].model_copy(
                            update={
                                "interpretation": (
                                    current_by_id[claim.claim_id].interpretation
                                    + " Further clarified."
                                )
                            }
                        )
                        for claim in result.revised_claims
                    )
                }
            )
        return result


def _revision() -> RevisionResult:
    claim = _claim().model_copy(
        update={"interpretation": _claim().interpretation + " Clarified during revision."}
    )
    return RevisionResult(
        revised_claims=(claim,),
        revised_agents=("company",),
        revised_claim_ids={"company": (claim.claim_id,)},
        payload_version="payload-revised",
    )


def _services(
    plan: AnalysisPlan,
    results,
    *,
    stage1_reports=None,
    revisions=None,
    max_revision_rounds=2,
):
    policy = AcceptancePolicy(
        policy_version="langgraph-test-v1",
        provisional_threshold=0.75,
        max_revision_rounds=max_revision_rounds,
    )
    stage1 = _Stage1Sequence(
        stage1_reports
        if stage1_reports is not None
        else [_stage1() for _ in results]
    )
    critic = _CriticSequence(results)
    executor = _RevisionSequence(revisions or [])
    kernel = RevisionWorkflowKernel(
        policy=policy,
        stage1_evaluator=stage1,
        semantic_critic=critic,
        revision_executor=executor,
    )
    controller = BoundedRevisionController(
        policy=policy,
        stage1_evaluator=stage1,
        semantic_critic=critic,
        revision_executor=executor,
    )
    return policy, stage1, critic, executor, kernel, controller


def _run_pair(results, *, stage1_reports=None, revisions=None, max_revision_rounds=2):
    plan = _plan()
    controller_services = _services(
        plan,
        results,
        stage1_reports=stage1_reports,
        revisions=revisions,
        max_revision_rounds=max_revision_rounds,
    )
    graph_services = _services(
        plan,
        results,
        stage1_reports=stage1_reports,
        revisions=revisions,
        max_revision_rounds=max_revision_rounds,
    )
    controller = controller_services[-1]
    workflow = build_langgraph_revision_workflow(kernel=graph_services[-2])
    controller_result = controller.run(
        run_id="parity-run",
        plan=plan,
        claims=(_claim(),),
        initial_payload_version="payload-initial",
    )
    graph_result = workflow.run(
        run_id="parity-run",
        plan=plan,
        claims=(_claim(),),
        initial_payload_version="payload-initial",
    )
    return controller_result, graph_result


class LangGraphRevisionParityTests(unittest.TestCase):
    def assert_parity(self, controller_result, graph_result):
        self.assertEqual(
            controller_result.model_dump(mode="json"),
            graph_result.model_dump(mode="json"),
        )

    def test_immediate_accept_parity(self):
        result = _result(_plan(), fulfilled=("R1",))
        controller_result, graph_result = _run_pair([result])
        self.assert_parity(controller_result, graph_result)
        self.assertEqual(graph_result.acceptance_state.final_decision, AcceptanceDecision.ACCEPT)

    def test_targeted_revision_accept_parity(self):
        first = _result(_plan(), issues=(_issue(),))
        second = _result(
            _plan(),
            fulfilled=("R1",),
            issues=(_issue(status=CritiqueIssueStatus.RESOLVED),),
        )
        controller_result, graph_result = _run_pair([first, second], revisions=[_revision()])
        self.assert_parity(controller_result, graph_result)
        self.assertEqual(len(graph_result.acceptance_state.rounds), 2)

    def test_initial_stage1_failure_never_invokes_critic(self):
        plan = _plan()
        services = _services(plan, [], stage1_reports=[_stage1(False)])
        workflow = build_langgraph_revision_workflow(kernel=services[-2])
        result = workflow.run(
            run_id="stage1-fail",
            plan=plan,
            claims=(_claim(),),
            initial_payload_version="payload-initial",
        )
        self.assertEqual(result.acceptance_state.final_decision, AcceptanceDecision.FAIL_ACCEPTANCE)
        self.assertEqual(len(services[2].calls), 0)

    def test_revised_stage1_failure_blocks_second_critic(self):
        plan = _plan()
        first = _result(plan, issues=(_issue(),))
        services = _services(
            plan,
            [first],
            stage1_reports=[_stage1(), _stage1(False)],
            revisions=[_revision()],
        )
        workflow = build_langgraph_revision_workflow(kernel=services[-2])
        result = workflow.run(
            run_id="revised-stage1-fail",
            plan=plan,
            claims=(_claim(),),
            initial_payload_version="payload-initial",
        )
        self.assertEqual(result.acceptance_state.final_decision, AcceptanceDecision.FAIL_ACCEPTANCE)
        self.assertEqual(len(services[2].calls), 1)

    def test_limited_acceptance_parity(self):
        issue = _issue(
            status=CritiqueIssueStatus.UNRESOLVED,
            reason=UnresolvedReasonCode.DATA_UNAVAILABLE,
            affected_requirement_ids=("R1",),
        )
        result = _result(_plan(), partial=("R1",), issues=(issue,))
        controller_result, graph_result = _run_pair([result])
        self.assert_parity(controller_result, graph_result)
        self.assertEqual(
            graph_result.acceptance_state.final_decision,
            AcceptanceDecision.ACCEPT_WITH_LIMITATIONS,
        )

    def test_low_quality_actionable_issue_parity(self):
        first = _result(_plan(), issues=(_issue(),), score=0.2)
        second = _result(
            _plan(),
            fulfilled=("R1",),
            issues=(_issue(status=CritiqueIssueStatus.RESOLVED),),
        )
        controller_result, graph_result = _run_pair([first, second], revisions=[_revision()])
        self.assert_parity(controller_result, graph_result)
        self.assertEqual(graph_result.acceptance_state.final_decision, AcceptanceDecision.ACCEPT)

    def test_max_revision_budget_exhaustion_parity(self):
        results = [_result(_plan(), issues=(_issue(issue_id=f"issue-{i}"),)) for i in range(3)]
        revisions = [_revision(), _revision()]
        controller_result, graph_result = _run_pair(
            results,
            revisions=revisions,
            max_revision_rounds=2,
        )
        self.assert_parity(controller_result, graph_result)
        self.assertEqual(
            graph_result.acceptance_state.final_decision,
            AcceptanceDecision.FAIL_ACCEPTANCE,
        )

    def test_terminal_issue_omitted_then_reopened_parity(self):
        results = [
            _result(
                _plan(),
                issues=(
                    _issue(issue_id="A", status=CritiqueIssueStatus.RESOLVED),
                    _issue(issue_id="B"),
                ),
            ),
            _result(
                _plan(),
                issues=(
                    _issue(issue_id="B", status=CritiqueIssueStatus.RESOLVED),
                    _issue(issue_id="C"),
                ),
            ),
            _result(
                _plan(),
                issues=(
                    _issue(issue_id="A"),
                    _issue(issue_id="C", status=CritiqueIssueStatus.RESOLVED),
                ),
            ),
        ]
        controller_result, graph_result = _run_pair(
            results,
            revisions=[_revision(), _revision()],
        )
        self.assert_parity(controller_result, graph_result)
        self.assertIn("issue_terminal_reopened:A", graph_result.terminal_reason)

    def test_macro_company_link_parity(self):
        plan = build_tcb_macro_analysis_plan(
            DatasetRef(dataset_id="dataset", dataset_snapshot_id="snapshot")
        )
        link_result = ApplicableLinkResult(
            link_id="L1",
            score=0.8,
            rationale="linked fixture",
        )
        result = _result(plan, link_results=(link_result,))
        controller_services = _services(plan, [result])
        graph_services = _services(plan, [result])
        controller_result = controller_services[-1].run(
            run_id="macro-link",
            plan=plan,
            claims=(),
            initial_payload_version="payload-initial",
        )
        graph_result = build_langgraph_revision_workflow(kernel=graph_services[-2]).run(
            run_id="macro-link",
            plan=plan,
            claims=(),
            initial_payload_version="payload-initial",
        )
        self.assert_parity(controller_result, graph_result)

    def test_company_only_route_has_no_macro_or_sector_specialist(self):
        first = _result(_plan(), issues=(_issue(),))
        second = _result(
            _plan(),
            fulfilled=("R1",),
            issues=(_issue(status=CritiqueIssueStatus.RESOLVED),),
        )
        services = _services(_plan(), [first, second], revisions=[_revision()])
        workflow = build_langgraph_revision_workflow(kernel=services[-2])
        workflow.run(
            run_id="company-only-routing",
            plan=_plan(),
            claims=(_claim(),),
            initial_payload_version="payload-initial",
        )
        self.assertEqual(services[3].calls[0].target_specialists, ("company",))


class LangGraphRevisionGraphTests(unittest.TestCase):
    def test_graph_contains_real_nodes_and_conditional_transitions(self):
        services = _services(_plan(), [_result(_plan(), fulfilled=("R1",))])
        workflow = build_langgraph_revision_workflow(kernel=services[-2])
        graph = workflow.graph.get_graph()
        nodes = set(graph.nodes)
        self.assertTrue({"evaluate_round", "execute_revision", "finalize"}.issubset(nodes))
        edges = {(edge.source, edge.target) for edge in graph.edges}
        self.assertIn(("__start__", "evaluate_round"), edges)
        self.assertIn(("evaluate_round", "execute_revision"), edges)
        self.assertIn(("evaluate_round", "finalize"), edges)
        self.assertIn(("execute_revision", "evaluate_round"), edges)
        self.assertIn(("finalize", "__end__"), edges)

    def test_checkpointer_records_cycle_and_uses_run_id_thread(self):
        saver = InMemorySaver()
        first = _result(_plan(), issues=(_issue(),))
        second = _result(
            _plan(),
            fulfilled=("R1",),
            issues=(_issue(status=CritiqueIssueStatus.RESOLVED),),
        )
        services = _services(_plan(), [first, second], revisions=[_revision()])
        workflow = build_langgraph_revision_workflow(kernel=services[-2], checkpointer=saver)
        workflow.run(
            run_id="checkpoint-run",
            plan=_plan(),
            claims=(_claim(),),
            initial_payload_version="payload-initial",
        )
        config = {"configurable": {"thread_id": "checkpoint-run"}}
        history = list(workflow.graph.get_state_history(config))
        self.assertGreaterEqual(len(history), 6)
        self.assertEqual(workflow.graph.get_state(config).values["run_id"], "checkpoint-run")

    def test_two_run_ids_do_not_share_checkpoint_state(self):
        saver = InMemorySaver()
        services = _services(
            _plan(),
            [
                _result(_plan(), fulfilled=("R1",)),
                _result(_plan(), fulfilled=("R1",)),
            ],
            stage1_reports=[_stage1(), _stage1()],
        )
        workflow = build_langgraph_revision_workflow(kernel=services[-2], checkpointer=saver)
        for run_id in ("run-a", "run-b"):
            workflow.run(
                run_id=run_id,
                plan=_plan(),
                claims=(_claim(),),
                initial_payload_version="payload-initial",
            )
        for run_id in ("run-a", "run-b"):
            state = workflow.graph.get_state({"configurable": {"thread_id": run_id}})
            self.assertEqual(state.values["run_id"], run_id)

    def test_graph_state_contains_domain_values_not_injected_services(self):
        saver = InMemorySaver()
        services = _services(_plan(), [_result(_plan(), fulfilled=("R1",))])
        workflow = build_langgraph_revision_workflow(kernel=services[-2], checkpointer=saver)
        workflow.run(
            run_id="state-boundary",
            plan=_plan(),
            claims=(_claim(),),
            initial_payload_version="payload-initial",
        )
        values = workflow.graph.get_state(
            {"configurable": {"thread_id": "state-boundary"}}
        ).values
        self.assertNotIn("_stage1_evaluator", values)
        self.assertNotIn("_semantic_critic", values)
        self.assertNotIn("_revision_executor", values)
        self.assertEqual(values["run_id"], "state-boundary")

    def test_core_and_adapter_import_boundaries_are_explicit(self):
        import thesis_data.revision_controller as core
        import thesis_data.langgraph_revision_runtime as adapter

        self.assertTrue(inspect.isclass(core.RevisionWorkflowKernel))
        adapter_source = Path(adapter.__file__).read_text(encoding="utf-8").lower()
        self.assertIn("from langgraph.graph", adapter_source)
        self.assertNotIn("langchain", adapter_source)
        self.assertNotIn("openai", adapter_source)

    def test_state_type_is_explicit_and_adapter_is_not_core_guarded(self):
        self.assertTrue(hasattr(LangGraphRevisionState, "__annotations__"))
        guard_path = Path(__file__).parents[1] / "scripts" / "check_architecture_guardrails.py"
        guard_source = guard_path.read_text(encoding="utf-8")
        self.assertNotIn(
            "langgraph_revision_runtime.py",
            guard_source.split("FORBIDDEN_CORE_TEXT", 1)[0],
        )


if __name__ == "__main__":
    unittest.main()
