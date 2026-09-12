import inspect
from pathlib import Path
import unittest

from thesis_data.analysis_plan import (
    AnalysisAgent,
    AnalysisPlan,
    build_tcb_macro_analysis_plan,
)
from thesis_data.dataset_contract import DatasetRef
from thesis_data.revision_controller import (
    BoundedRevisionController,
    RevisionRequest,
    RevisionResult,
    Stage1Evaluator,
    candidate_hash,
)
from thesis_data.schema import (
    AcceptanceDecision,
    AcceptancePolicy,
    AcceptanceRound,
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
    QualityDimensionScores,
    ReportAcceptanceState,
)
from thesis_data.semantic_evaluation import (
    ApplicableLinkResult,
    SemanticDimension,
    SemanticDimensionApplicability,
    SemanticDimensionResult,
    StructuredCriticResult,
)
from thesis_data.semantic_critic import SemanticRoundContext


def _company_plan() -> AnalysisPlan:
    from thesis_data.analysis_plan import (
        ANALYSIS_PLAN_VERSION,
        AnalysisRequirement,
        AnalysisScope,
        CausalClaimPolicy,
        FulfillmentPolicy,
        InferenceCeiling,
        MissingDataPolicy,
        RequirementType,
    )

    return AnalysisPlan(
        plan_version=ANALYSIS_PLAN_VERSION,
        dataset_id="dataset",
        dataset_snapshot_id="snapshot",
        query_id="company-query",
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


def _company_claim() -> AtomicClaim:
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


def _stage1(passed: bool = True) -> Stage1ValidationReport:
    gate_ids = (
        "numeric_accuracy",
        "reference_validity",
        "critical_evidence_coverage",
        "scope_compliance",
        "fabricated_or_unaccepted_records",
        "blocking_contradictions",
    )
    gates = {}
    for gate_id in gate_ids:
        gate_passed = passed or gate_id != "numeric_accuracy"
        gates[gate_id] = HardGateResult(
            gate_id=gate_id,
            passed=gate_passed,
            rate=1.0 if gate_passed else 0.0,
            required_rate=1.0,
            evaluation_unit="fixture",
            evaluated_count=1,
            passed_count=1 if gate_passed else 0,
            violations=() if gate_passed else ("stage1_fixture_failure",),
        )
    return Stage1ValidationReport(
        passed=passed,
        gate_results=gates,
        integrity_violations=() if passed else ("stage1_fixture_failure",),
    )


def _issue(
    *,
    issue_id="issue-1",
    agent="company",
    status=CritiqueIssueStatus.OPEN,
    issue_type=CritiqueIssueType.MISSING_DATA,
    action=CritiqueAction.REVISE_CLAIM,
    severity=CritiqueSeverity.MAJOR,
    reason=None,
) -> CritiqueIssue:
    return CritiqueIssue(
        issue_id=issue_id,
        issue_type=issue_type,
        severity=severity,
        affected_agent=agent,
        description="Fixture issue.",
        required_action=action,
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
            item.requirement_id
            for item in plan.requirements
            if item.requirement_id not in classified
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
        evaluator_version="fixture-sequence-v1",
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
        self._last_report = None
        self.calls = []

    def evaluate(self, *, plan, claims, policy):
        del policy
        from thesis_data.revision_controller import candidate_hash as make_hash

        call = {
            "hash": make_hash(plan, claims),
            "claim_ids": tuple(claim.claim_id for claim in claims),
        }
        self.calls.append(call)
        if self.reports:
            report = self.reports.pop(0)
            self._last_report = report
        elif self._last_report is not None:
            report = self._last_report
        else:
            raise RuntimeError("no fixture Stage-1 report configured")
        return report.model_copy(deep=True)


class _CriticSequence:
    def __init__(self, results):
        self.results = list(results)
        self.calls = []

    def evaluate(self, *, plan, claims, stage1_report, round_context):
        self.calls.append(
            {
                "plan": plan.model_dump(mode="python"),
                "claim_ids": tuple(claim.claim_id for claim in claims),
                "stage1": stage1_report,
                "context": round_context,
            }
        )
        return self.results.pop(0).model_copy(deep=True)


class _RevisionSequence:
    def __init__(self, results):
        self.results = list(results)
        self.calls: list[RevisionRequest] = []

    def execute(self, *, request):
        self.calls.append(request.model_copy(deep=True))
        return self.results.pop(0).model_copy(deep=True)


class _MutatingRevisionExecutor(_RevisionSequence):
    def execute(self, *, request):
        self.calls.append(request.model_copy(deep=True))
        request.plan.requirements = ()
        if request.current_claims:
            request.current_claims[0].claim_text = "mutated"
        request.selected_issues[0].description = "mutated"
        return self.results.pop(0).model_copy(deep=True)


class _MalformedRevisionExecutor:
    def execute(self, *, request):
        del request
        return object()


def _revision(claims, *, agents=("company",), version="payload-revised"):
    return RevisionResult(
        revised_claims=tuple(claims),
        revised_agents=tuple(agents),
        payload_version=version,
    )


def _controller(
    *,
    plan=None,
    stage1_reports=None,
    critic_results=None,
    revision_results=None,
    revision_executor=None,
    threshold=0.75,
    max_revision_rounds=2,
):
    policy = AcceptancePolicy(
        policy_version="controller-test-v1",
        provisional_threshold=threshold,
        max_revision_rounds=max_revision_rounds,
    )
    stage1 = _Stage1Sequence(stage1_reports or [_stage1()])
    critic = _CriticSequence(critic_results or [])
    executor = revision_executor
    if executor is None and revision_results is not None:
        executor = _RevisionSequence(revision_results)
    return (
        BoundedRevisionController(
            policy=policy,
            stage1_evaluator=stage1,
            semantic_critic=critic,
            revision_executor=executor,
        ),
        stage1,
        critic,
        executor,
        plan or _company_plan(),
        policy,
    )


class Phase3BBRevisionControllerTests(unittest.TestCase):
    def test_initial_stage1_pass_invokes_semantic_critic_on_same_candidate(self):
        plan = _company_plan()
        claims = (_company_claim(),)
        controller, stage1, critic, _, _, _ = _controller(
            plan=plan,
            critic_results=[_result(plan, fulfilled=("R1",), score=0.9)],
        )
        result = controller.run(
            run_id="run-1",
            plan=plan,
            claims=claims,
            initial_payload_version="payload-initial",
        )

        self.assertEqual(stage1.calls[0]["hash"], result.acceptance_state.rounds[0].candidate_hash)
        self.assertEqual(stage1.calls[0]["claim_ids"], critic.calls[0]["claim_ids"])
        self.assertEqual(result.acceptance_state.final_decision, AcceptanceDecision.ACCEPT)

    def test_initial_stage1_fail_never_invokes_critic_and_fails_acceptance(self):
        plan = _company_plan()
        controller, _, critic, _, _, _ = _controller(
            plan=plan,
            stage1_reports=[_stage1(False)],
        )
        result = controller.run(
            run_id="run-stage1-fail",
            plan=plan,
            claims=(_company_claim(),),
            initial_payload_version="payload-initial",
        )

        self.assertEqual(len(critic.calls), 0)
        self.assertEqual(result.acceptance_state.final_decision, AcceptanceDecision.FAIL_ACCEPTANCE)

    def test_controller_has_no_external_stage1_report_pairing_parameter(self):
        signature = inspect.signature(BoundedRevisionController.run)
        self.assertNotIn("stage1_report", signature.parameters)

    def test_candidate_hash_is_deterministic_for_identical_content(self):
        plan = _company_plan()
        claims = (_company_claim(),)
        self.assertEqual(candidate_hash(plan, claims), candidate_hash(plan, claims))

    def test_material_claim_change_changes_candidate_hash(self):
        plan = _company_plan()
        original = _company_claim()
        changed = original.model_copy(update={"claim_text": "TCB ROA was 1.3%."})
        self.assertNotEqual(candidate_hash(plan, (original,)), candidate_hash(plan, (changed,)))

    def test_company_only_plan_routes_no_macro_or_sector_revision(self):
        plan = _company_plan()
        claim = _company_claim()
        first = _result(plan, issues=(_issue(),), score=0.4)
        second = _result(
            plan,
            fulfilled=("R1",),
            issues=(_issue(status=CritiqueIssueStatus.RESOLVED),),
        )
        controller, _, _, executor, _, _ = _controller(
            plan=plan,
            critic_results=[first, second],
            revision_results=[_revision((claim,))],
        )
        result = controller.run(
            run_id="company-revision",
            plan=plan,
            claims=(claim,),
            initial_payload_version="payload-initial",
        )

        self.assertEqual(executor.calls[0].target_specialists, ("company",))
        self.assertEqual(result.acceptance_state.final_decision, AcceptanceDecision.ACCEPT)

    def test_active_company_issue_routes_company_only(self):
        plan = _company_plan()
        claim = _company_claim()
        issue = _issue(issue_id="company-only")
        controller, _, _, executor, _, _ = _controller(
            plan=plan,
            critic_results=[
                _result(plan, issues=(issue,)),
                _result(plan, fulfilled=("R1",), issues=(_issue(issue_id="company-only", status=CritiqueIssueStatus.RESOLVED),)),
            ],
            revision_results=[_revision((claim,))],
        )
        controller.run(
            run_id="company-target",
            plan=plan,
            claims=(claim,),
            initial_payload_version="payload-initial",
        )
        self.assertEqual(executor.calls[0].target_specialists, ("company",))

    def test_orchestrator_only_issue_requests_resynthesis_without_specialist(self):
        plan = _company_plan()
        claim = _company_claim()
        issue = _issue(issue_id="synthesis", agent="orchestrator")
        controller, _, _, executor, _, _ = _controller(
            plan=plan,
            critic_results=[
                _result(plan, issues=(issue,)),
                _result(plan, fulfilled=("R1",), issues=(_issue(issue_id="synthesis", agent="orchestrator", status=CritiqueIssueStatus.RESOLVED),)),
            ],
            revision_results=[_revision((claim,), agents=())],
        )
        controller.run(
            run_id="orchestrator-target",
            plan=plan,
            claims=(claim,),
            initial_payload_version="payload-initial",
        )
        self.assertEqual(executor.calls[0].target_specialists, ())
        self.assertEqual(executor.calls[0].selected_issues[0].affected_agent, "orchestrator")

    def test_revision_result_with_inactive_specialist_fails_closed(self):
        plan = _company_plan()
        controller, _, _, _, _, _ = _controller(
            plan=plan,
            critic_results=[_result(plan, issues=(_issue(),))],
            revision_results=[_revision((_company_claim(),), agents=("macro",))],
        )
        result = controller.run(
            run_id="inactive-agent",
            plan=plan,
            claims=(_company_claim(),),
            initial_payload_version="payload-initial",
        )
        self.assertEqual(result.acceptance_state.final_decision, AcceptanceDecision.FAIL_ACCEPTANCE)

    def test_revision_result_with_extra_specialist_fails_closed(self):
        plan = _company_plan()
        controller, _, _, _, _, _ = _controller(
            plan=plan,
            critic_results=[_result(plan, issues=(_issue(),))],
            revision_results=[_revision((_company_claim(),), agents=("company", "sector"))],
        )
        result = controller.run(
            run_id="extra-agent",
            plan=plan,
            claims=(_company_claim(),),
            initial_payload_version="payload-initial",
        )
        self.assertEqual(result.acceptance_state.final_decision, AcceptanceDecision.FAIL_ACCEPTANCE)

    def test_revision_result_omitting_target_specialist_fails_closed(self):
        plan = _company_plan()
        controller, _, _, _, _, _ = _controller(
            plan=plan,
            critic_results=[_result(plan, issues=(_issue(),))],
            revision_results=[_revision((_company_claim(),), agents=())],
        )
        result = controller.run(
            run_id="omitted-agent",
            plan=plan,
            claims=(_company_claim(),),
            initial_payload_version="payload-initial",
        )
        self.assertEqual(result.acceptance_state.final_decision, AcceptanceDecision.FAIL_ACCEPTANCE)

    def test_undeclared_cross_level_reconciliation_remains_rejected(self):
        plan = _company_plan()
        issue = _issue(
            agent="orchestrator",
            action=CritiqueAction.RECONCILE_CROSS_LEVEL,
        )
        controller, _, _, _, _, _ = _controller(
            plan=plan,
            critic_results=[_result(plan, issues=(issue,))],
        )
        result = controller.run(
            run_id="undeclared-link",
            plan=plan,
            claims=(_company_claim(),),
            initial_payload_version="payload-initial",
        )
        self.assertEqual(result.acceptance_state.final_decision, AcceptanceDecision.FAIL_ACCEPTANCE)

    def test_round_zero_can_be_persisted_as_revise(self):
        plan = _company_plan()
        claim = _company_claim()
        issue = _issue()
        controller, _, _, _, _, _ = _controller(
            plan=plan,
            critic_results=[
                _result(plan, issues=(issue,), score=0.4),
                _result(plan, fulfilled=("R1",), issues=(_issue(status=CritiqueIssueStatus.RESOLVED),)),
            ],
            revision_results=[_revision((claim,))],
        )
        result = controller.run(
            run_id="revise-round",
            plan=plan,
            claims=(claim,),
            initial_payload_version="payload-initial",
        )
        self.assertEqual(result.acceptance_state.rounds[0].acceptance_decision, AcceptanceDecision.REVISE)
        self.assertEqual(result.acceptance_state.rounds[1].acceptance_decision, AcceptanceDecision.ACCEPT)

    def test_report_acceptance_state_cannot_finish_with_revise(self):
        plan = _company_plan()
        issue = _issue()
        scores = QualityDimensionScores(
            groundedness=0.9,
            cross_level_integration=None,
            answer_coverage=0.9,
            logical_soundness=0.9,
            uncertainty_limitations=0.9,
            analytical_usefulness=0.9,
        )
        gates = {name: HardGateResult(
            gate_id=name,
            passed=True,
            rate=1.0,
            required_rate=1.0,
            evaluation_unit="fixture",
            evaluated_count=1,
            passed_count=1,
        ) for name in (
            "numeric_accuracy", "reference_validity", "critical_evidence_coverage",
            "scope_compliance", "fabricated_or_unaccepted_records", "blocking_contradictions",
        )}
        round_state = AcceptanceRound(
            round_number=0,
            hard_gate_results=gates,
            quality_scores=scores,
            quality_total=scores.weighted_total(AcceptancePolicy(policy_version="p", provisional_threshold=0.75).quality_weights),
            provisional_threshold=0.75,
            critique_issues=(issue,),
            acceptance_decision=AcceptanceDecision.REVISE,
        )
        with self.assertRaises(ValueError):
            ReportAcceptanceState(
                acceptance_model_version="test",
                run_id="revise-final",
                policy=AcceptancePolicy(policy_version="p", provisional_threshold=0.75),
                rounds=(round_state,),
                final_decision=AcceptanceDecision.REVISE,
            )

    def test_accept_requires_threshold_and_no_open_or_unresolved_issues(self):
        plan = _company_plan()
        controller, _, _, _, _, _ = _controller(
            plan=plan,
            critic_results=[_result(plan, fulfilled=("R1",), score=0.9)],
        )
        result = controller.run(
            run_id="accept",
            plan=plan,
            claims=(_company_claim(),),
            initial_payload_version="payload-initial",
        )
        self.assertEqual(result.acceptance_state.final_decision, AcceptanceDecision.ACCEPT)
        self.assertEqual(result.acceptance_state.final_payload_version, "payload-initial")

    def test_accept_with_limitations_requires_allowed_data_or_evidence_reason(self):
        plan = _company_plan()
        issue = _issue(
            status=CritiqueIssueStatus.UNRESOLVED,
            reason=UnresolvedReasonCode.DATA_UNAVAILABLE,
        )
        controller, _, _, _, _, _ = _controller(
            plan=plan,
            critic_results=[_result(plan, partial=("R1",), issues=(issue,), score=0.9)],
        )
        result = controller.run(
            run_id="limited",
            plan=plan,
            claims=(_company_claim(),),
            initial_payload_version="payload-initial",
        )
        self.assertEqual(result.acceptance_state.final_decision, AcceptanceDecision.ACCEPT_WITH_LIMITATIONS)

    def test_unresolved_reasoning_defect_terminates_fail(self):
        plan = _company_plan()
        issue = _issue(
            issue_type=CritiqueIssueType.UNSUPPORTED_CLAIM,
            status=CritiqueIssueStatus.UNRESOLVED,
            action=CritiqueAction.REMOVE_CLAIM,
            reason=None,
        )
        controller, _, _, _, _, _ = _controller(
            plan=plan,
            critic_results=[_result(plan, issues=(issue,), score=0.9)],
        )
        result = controller.run(
            run_id="reasoning-fail",
            plan=plan,
            claims=(_company_claim(),),
            initial_payload_version="payload-initial",
        )
        self.assertEqual(result.acceptance_state.final_decision, AcceptanceDecision.FAIL_ACCEPTANCE)

    def test_low_quality_with_actionable_issue_and_budget_returns_revise(self):
        plan = _company_plan()
        claim = _company_claim()
        controller, _, _, _, _, _ = _controller(
            plan=plan,
            critic_results=[
                _result(plan, issues=(_issue(),), score=0.2),
                _result(plan, fulfilled=("R1",), issues=(_issue(status=CritiqueIssueStatus.RESOLVED),), score=0.9),
            ],
            revision_results=[_revision((claim,))],
        )
        result = controller.run(
            run_id="low-quality-revise",
            plan=plan,
            claims=(claim,),
            initial_payload_version="payload-initial",
        )
        self.assertEqual(result.acceptance_state.rounds[0].acceptance_decision, AcceptanceDecision.REVISE)

    def test_low_quality_without_revision_path_fails(self):
        plan = _company_plan()
        controller, _, _, _, _, _ = _controller(
            plan=plan,
            critic_results=[_result(plan, score=0.2)],
        )
        result = controller.run(
            run_id="low-quality-fail",
            plan=plan,
            claims=(_company_claim(),),
            initial_payload_version="payload-initial",
        )
        self.assertEqual(result.acceptance_state.final_decision, AcceptanceDecision.FAIL_ACCEPTANCE)

    def test_maximum_two_revision_rounds_never_executes_third(self):
        plan = _company_plan()
        issue = _issue()
        controller, _, _, executor, _, _ = _controller(
            plan=plan,
            critic_results=[
                _result(plan, issues=(issue,)),
                _result(plan, issues=(issue,)),
                _result(plan, issues=(issue,)),
            ],
            revision_results=[_revision((_company_claim(),)), _revision((_company_claim(),))],
            max_revision_rounds=2,
        )
        result = controller.run(
            run_id="max-two",
            plan=plan,
            claims=(_company_claim(),),
            initial_payload_version="payload-initial",
        )
        self.assertEqual(len(executor.calls), 2)
        self.assertEqual(len(result.acceptance_state.rounds), 3)
        self.assertEqual(result.acceptance_state.final_decision, AcceptanceDecision.FAIL_ACCEPTANCE)

    def test_each_revised_candidate_runs_stage1_then_critic(self):
        plan = _company_plan()
        claim = _company_claim()
        issue = _issue()
        controller, stage1, critic, executor, _, _ = _controller(
            plan=plan,
            critic_results=[
                _result(plan, issues=(issue,)),
                _result(plan, fulfilled=("R1",), issues=(_issue(status=CritiqueIssueStatus.RESOLVED),)),
            ],
            revision_results=[_revision((claim,))],
        )
        controller.run(
            run_id="sequence",
            plan=plan,
            claims=(claim,),
            initial_payload_version="payload-initial",
        )
        self.assertEqual(len(executor.calls), 1)
        self.assertEqual(len(stage1.calls), 2)
        self.assertEqual(len(critic.calls), 2)
        self.assertEqual(stage1.calls[1]["claim_ids"], critic.calls[1]["claim_ids"])

    def test_revised_agents_are_persisted_on_the_revised_candidate_round(self):
        plan = _company_plan()
        issue = _issue()
        controller, _, _, _, _, _ = _controller(
            plan=plan,
            critic_results=[
                _result(plan, issues=(issue,)),
                _result(plan, fulfilled=("R1",), issues=(_issue(status=CritiqueIssueStatus.RESOLVED),)),
            ],
            revision_results=[_revision((_company_claim(),))],
        )
        result = controller.run(
            run_id="revised-agent-audit",
            plan=plan,
            claims=(_company_claim(),),
            initial_payload_version="payload-initial",
        )
        self.assertEqual(result.acceptance_state.rounds[1].revised_agents, ("company",))
        self.assertEqual(result.acceptance_state.rounds[1].candidate_payload_version, "payload-revised")

    def test_stage1_failure_after_revision_blocks_second_critic(self):
        plan = _company_plan()
        issue = _issue()
        controller, _, critic, executor, _, _ = _controller(
            plan=plan,
            stage1_reports=[_stage1(), _stage1(False)],
            critic_results=[_result(plan, issues=(issue,))],
            revision_results=[_revision((_company_claim(),))],
        )
        result = controller.run(
            run_id="stage1-after-revision",
            plan=plan,
            claims=(_company_claim(),),
            initial_payload_version="payload-initial",
        )
        self.assertEqual(len(executor.calls), 1)
        self.assertEqual(len(critic.calls), 1)
        self.assertEqual(result.acceptance_state.final_decision, AcceptanceDecision.FAIL_ACCEPTANCE)

    def test_prior_open_issue_cannot_disappear(self):
        plan = _company_plan()
        issue = _issue()
        controller, _, _, _, _, _ = _controller(
            plan=plan,
            critic_results=[_result(plan, issues=(issue,)), _result(plan)],
            revision_results=[_revision((_company_claim(),))],
        )
        result = controller.run(
            run_id="issue-disappears",
            plan=plan,
            claims=(_company_claim(),),
            initial_payload_version="payload-initial",
        )
        self.assertEqual(result.acceptance_state.final_decision, AcceptanceDecision.FAIL_ACCEPTANCE)
        self.assertIn("prior_issue_disappeared", result.terminal_reason)

    def test_open_issue_can_become_resolved(self):
        plan = _company_plan()
        issue = _issue(issue_id="resolve-me")
        controller, _, _, _, _, _ = _controller(
            plan=plan,
            critic_results=[
                _result(plan, issues=(issue,)),
                _result(plan, fulfilled=("R1",), issues=(_issue(issue_id="resolve-me", status=CritiqueIssueStatus.RESOLVED),)),
            ],
            revision_results=[_revision((_company_claim(),))],
        )
        result = controller.run(
            run_id="issue-resolved",
            plan=plan,
            claims=(_company_claim(),),
            initial_payload_version="payload-initial",
        )
        self.assertEqual(result.acceptance_state.final_decision, AcceptanceDecision.ACCEPT)

    def test_open_issue_can_become_explained(self):
        plan = _company_plan()
        issue = _issue(issue_id="explain-me")
        controller, _, _, _, _, _ = _controller(
            plan=plan,
            critic_results=[
                _result(plan, issues=(issue,)),
                _result(plan, fulfilled=("R1",), issues=(_issue(issue_id="explain-me", status=CritiqueIssueStatus.EXPLAINED),)),
            ],
            revision_results=[_revision((_company_claim(),))],
        )
        result = controller.run(
            run_id="issue-explained",
            plan=plan,
            claims=(_company_claim(),),
            initial_payload_version="payload-initial",
        )
        self.assertEqual(result.acceptance_state.final_decision, AcceptanceDecision.ACCEPT)

    def test_open_issue_can_become_unresolved_reasoning_and_fail(self):
        plan = _company_plan()
        issue = _issue(issue_id="reasoning", issue_type=CritiqueIssueType.UNSUPPORTED_CLAIM)
        unresolved = _issue(
            issue_id="reasoning",
            issue_type=CritiqueIssueType.UNSUPPORTED_CLAIM,
            status=CritiqueIssueStatus.UNRESOLVED,
            action=CritiqueAction.REMOVE_CLAIM,
        )
        controller, _, _, _, _, _ = _controller(
            plan=plan,
            critic_results=[_result(plan, issues=(issue,)), _result(plan, issues=(unresolved,))],
            revision_results=[_revision((_company_claim(),))],
        )
        result = controller.run(
            run_id="issue-unresolved",
            plan=plan,
            claims=(_company_claim(),),
            initial_payload_version="payload-initial",
        )
        self.assertEqual(result.acceptance_state.final_decision, AcceptanceDecision.FAIL_ACCEPTANCE)

    def test_terminal_issue_cannot_reopen_as_open(self):
        plan = _company_plan()
        initial = _issue(issue_id="reopen", status=CritiqueIssueStatus.OPEN)
        resolved = _issue(issue_id="reopen", status=CritiqueIssueStatus.RESOLVED)
        reopened = _issue(issue_id="reopen", status=CritiqueIssueStatus.OPEN)
        next_issue = _issue(issue_id="continue", status=CritiqueIssueStatus.OPEN)
        controller, _, _, _, _, _ = _controller(
            plan=plan,
            critic_results=[
                _result(plan, issues=(initial,)),
                _result(plan, issues=(resolved, next_issue)),
                _result(plan, issues=(reopened, next_issue)),
            ],
            revision_results=[_revision((_company_claim(),)), _revision((_company_claim(),))],
        )
        result = controller.run(
            run_id="issue-reopened",
            plan=plan,
            claims=(_company_claim(),),
            initial_payload_version="payload-initial",
        )
        self.assertEqual(result.acceptance_state.final_decision, AcceptanceDecision.FAIL_ACCEPTANCE)
        self.assertIn("issue_terminal_reopened", result.terminal_reason)

    def test_plan_is_unchanged_after_revision_rounds(self):
        plan = _company_plan()
        before = plan.model_dump(mode="python")
        issue = _issue()
        executor = _MutatingRevisionExecutor([_revision((_company_claim(),))])
        controller, _, _, _, _, _ = _controller(
            plan=plan,
            critic_results=[
                _result(plan, issues=(issue,)),
                _result(plan, fulfilled=("R1",), issues=(_issue(status=CritiqueIssueStatus.RESOLVED),)),
            ],
            revision_executor=executor,
        )
        controller.run(
            run_id="immutable-plan",
            plan=plan,
            claims=(_company_claim(),),
            initial_payload_version="payload-initial",
        )
        self.assertEqual(plan.model_dump(mode="python"), before)

    def test_controller_works_with_macro_company_linked_plan(self):
        plan = build_tcb_macro_analysis_plan(
            DatasetRef(dataset_id="dataset", dataset_snapshot_id="snapshot")
        )
        controller, _, _, _, _, _ = _controller(
            plan=plan,
            critic_results=[
                _result(
                    plan,
                    link_results=(
                        ApplicableLinkResult(
                            link_id="L1",
                            score=0.8,
                            rationale="linked fixture",
                        ),
                    ),
                )
            ],
        )
        result = controller.run(
            run_id="linked-plan",
            plan=plan,
            claims=(),
            initial_payload_version="payload-initial",
        )
        self.assertEqual(result.acceptance_state.final_decision, AcceptanceDecision.FAIL_ACCEPTANCE)
        self.assertIsNotNone(result.acceptance_state.rounds[0].candidate_hash)

    def test_no_mandatory_three_agent_execution_assumption(self):
        plan = _company_plan()
        claim = _company_claim()
        controller, _, critic, _, _, _ = _controller(
            plan=plan,
            critic_results=[_result(plan, fulfilled=("R1",))],
        )
        result = controller.run(
            run_id="company-only",
            plan=plan,
            claims=(claim,),
            initial_payload_version="payload-initial",
        )
        self.assertEqual(result.acceptance_state.final_decision, AcceptanceDecision.ACCEPT)
        self.assertEqual(len(critic.calls), 1)
        self.assertIsNone(critic.calls[0]["context"].case_id)

    def test_candidate_identity_fields_are_persisted_per_round(self):
        plan = _company_plan()
        controller, _, _, _, _, _ = _controller(
            plan=plan,
            critic_results=[_result(plan, fulfilled=("R1",))],
        )
        result = controller.run(
            run_id="candidate-fields",
            plan=plan,
            claims=(_company_claim(),),
            initial_payload_version="payload-v1",
        )
        round_state = result.acceptance_state.rounds[0]
        self.assertEqual(round_state.candidate_claim_ids, ("company-claim",))
        self.assertEqual(round_state.candidate_payload_version, "payload-v1")
        self.assertEqual(round_state.candidate_hash, result.final_candidate_hash)

    def test_revision_request_contains_current_candidate_and_target_scope(self):
        plan = _company_plan()
        issue = _issue(issue_id="request-scope")
        controller, _, _, executor, _, _ = _controller(
            plan=plan,
            critic_results=[
                _result(plan, issues=(issue,)),
                _result(plan, fulfilled=("R1",), issues=(_issue(issue_id="request-scope", status=CritiqueIssueStatus.RESOLVED),)),
            ],
            revision_results=[_revision((_company_claim(),))],
        )
        controller.run(
            run_id="request-scope",
            plan=plan,
            claims=(_company_claim(),),
            initial_payload_version="payload-v1",
        )
        request = executor.calls[0]
        self.assertEqual(request.next_round_number, 1)
        self.assertEqual(request.target_specialists, ("company",))
        self.assertEqual(request.selected_issues[0].issue_id, "request-scope")
        self.assertEqual(request.current_candidate_hash, candidate_hash(plan, (_company_claim(),)))

    def test_malformed_revision_result_fails_acceptance(self):
        plan = _company_plan()
        controller, _, _, _, _, _ = _controller(
            plan=plan,
            critic_results=[_result(plan, issues=(_issue(),))],
            revision_executor=_MalformedRevisionExecutor(),
        )
        result = controller.run(
            run_id="malformed-revision",
            plan=plan,
            claims=(_company_claim(),),
            initial_payload_version="payload-v1",
        )
        self.assertEqual(result.acceptance_state.final_decision, AcceptanceDecision.FAIL_ACCEPTANCE)

    def test_revise_round_has_no_final_payload_version(self):
        plan = _company_plan()
        claim = _company_claim()
        controller, _, _, _, _, _ = _controller(
            plan=plan,
            critic_results=[
                _result(plan, issues=(_issue(),)),
                _result(plan, fulfilled=("R1",), issues=(_issue(status=CritiqueIssueStatus.RESOLVED),)),
            ],
            revision_results=[_revision((claim,))],
        )
        result = controller.run(
            run_id="revise-payload",
            plan=plan,
            claims=(claim,),
            initial_payload_version="payload-v1",
        )
        self.assertIsNone(result.acceptance_state.rounds[0].final_payload_version)

    def test_later_round_candidate_hash_changes_when_revision_changes_claim(self):
        plan = _company_plan()
        first_claim = _company_claim()
        second_claim = first_claim.model_copy(update={"claim_text": "TCB ROA was 1.3%."})
        controller, _, _, _, _, _ = _controller(
            plan=plan,
            critic_results=[
                _result(plan, issues=(_issue(),)),
                _result(plan, fulfilled=("R1",), issues=(_issue(status=CritiqueIssueStatus.RESOLVED),)),
            ],
            revision_results=[_revision((second_claim,))],
        )
        result = controller.run(
            run_id="hash-change",
            plan=plan,
            claims=(first_claim,),
            initial_payload_version="payload-v1",
        )
        self.assertNotEqual(
            result.acceptance_state.rounds[0].candidate_hash,
            result.acceptance_state.rounds[1].candidate_hash,
        )

    def test_core_controller_does_not_reference_workflow_frameworks(self):
        source = Path(__file__).parents[1] / "src" / "thesis_data" / "revision_controller.py"
        text = source.read_text(encoding="utf-8").lower()
        self.assertNotIn("langgraph", text)
        self.assertNotIn("langchain", text)


if __name__ == "__main__":
    unittest.main()
