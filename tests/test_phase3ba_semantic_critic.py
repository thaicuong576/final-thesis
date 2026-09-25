import unittest

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
from thesis_data.schema import (
    AssertionType,
    AtomicClaim,
    ClaimDataRef,
    ClaimScope,
    HardGateResult,
    InferenceType,
    StructuredAssertion,
    CritiqueAction,
    CritiqueIssue,
    CritiqueIssueType,
    CritiqueSeverity,
    Stage1ValidationReport,
)
from thesis_data.semantic_critic import (
    FixtureSemanticCritic,
    SemanticEvaluationError,
    SemanticRoundContext,
    evaluate_semantic_round,
)
from thesis_data.semantic_evaluation import (
    ApplicableLinkResult,
    SemanticDimension,
    SemanticDimensionApplicability,
    SemanticDimensionResult,
    StructuredCriticResult,
)


def _company_plan() -> AnalysisPlan:
    dataset_ref = DatasetRef(dataset_id="dataset", dataset_snapshot_id="snapshot")
    requirement = AnalysisRequirement(
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
    )
    return AnalysisPlan(
        plan_version=ANALYSIS_PLAN_VERSION,
        dataset_id=dataset_ref.dataset_id,
        dataset_snapshot_id=dataset_ref.dataset_snapshot_id,
        query_id="company-query",
        normalized_question="Report the company observation.",
        scope=AnalysisScope(
            entities=("TCB",),
            periods=("2024_Q4",),
            company_metric_ids=("bank.roa",),
        ),
        requirements=(requirement,),
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
        interpretation="The requested company observation is reported.",
        limitation="The observation is limited to the requested period.",
        scope=ClaimScope(
            entities=("TCB",),
            periods=("2024_Q4",),
            metric_ids=("bank.roa",),
        ),
        assertions=(assertion,),
        inference_type=InferenceType.FACT,
    )


def _stage1(*, passed: bool = True) -> Stage1ValidationReport:
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
            violations=() if gate_passed else ("fixture_stage1_failure",),
        )
    return Stage1ValidationReport(
        passed=passed,
        gate_results=gates,
        integrity_violations=() if passed else ("fixture_stage1_failure",),
    )


def _result(
    plan: AnalysisPlan,
    *,
    fulfilled=(),
    unfulfilled=None,
    cross_applicable=None,
    issues=(),
    link_results=(),
    supporting_claim_ids=(),
    dimension_issue_ids=(),
) -> StructuredCriticResult:
    if unfulfilled is None:
        unfulfilled = tuple(
            requirement.requirement_id
            for requirement in plan.requirements
            if requirement.requirement_id not in fulfilled
        )
    if cross_applicable is None:
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
                0.8
                if cross_applicable or dimension is not SemanticDimension.CROSS_LEVEL_INTEGRATION
                else None
            ),
            rationale="fixture result",
            supporting_claim_ids=(
                tuple(supporting_claim_ids)
                if cross_applicable or dimension is not SemanticDimension.CROSS_LEVEL_INTEGRATION
                else ()
            ),
            issue_ids=(
                tuple(dimension_issue_ids)
                if cross_applicable or dimension is not SemanticDimension.CROSS_LEVEL_INTEGRATION
                else ()
            ),
        )
        for dimension in SemanticDimension
    )
    return StructuredCriticResult(
        evaluator_version="fixture-v1",
        dimension_scores=dimensions,
        critique_issues=tuple(issues),
        fulfilled_requirement_ids=tuple(fulfilled),
        unfulfilled_requirement_ids=tuple(unfulfilled),
        applicable_link_results=tuple(link_results),
    )


def _issue(
    *,
    issue_id="issue-1",
    affected_agent="macro",
    required_action=CritiqueAction.REQUERY_DATA,
    affected_claim_ids=(),
) -> CritiqueIssue:
    return CritiqueIssue(
        issue_id=issue_id,
        issue_type=CritiqueIssueType.MISSING_DATA,
        severity=CritiqueSeverity.MAJOR,
        affected_agent=affected_agent,
        affected_claim_ids=tuple(affected_claim_ids),
        description="Fixture issue.",
        required_action=required_action,
    )


class _MalformedCritic:
    def evaluate(self, **kwargs):
        del kwargs
        return object()


class _MutatingCritic:
    def __init__(self, result):
        self.result = result

    def evaluate(self, *, plan, claims, stage1_report, round_context):
        del stage1_report, round_context
        plan.requirements = ()
        claims[0].claim_text = "mutated by critic"
        return self.result


class Phase3BASemanticCriticTests(unittest.TestCase):
    def test_synthesis_context_fixes_target_and_rejects_numeric_or_period_literals(self):
        with self.assertRaises(ValueError):
            SemanticRoundContext(round_number=0, synthesis_target_id="report-summary")
        with self.assertRaisesRegex(ValueError, "numeric_or_period_literal"):
            SemanticRoundContext(
                round_number=0,
                synthesis_summary="The result improved in 2024.",
            )

    def test_orchestrator_issue_requires_a_report_synthesis_target(self):
        plan = _company_plan()
        issue = _issue(affected_agent="orchestrator")
        critic = FixtureSemanticCritic({"case": _result(plan, issues=(issue,))})
        with self.assertRaisesRegex(
            SemanticEvaluationError,
            "orchestrator_synthesis_target_unavailable",
        ):
            evaluate_semantic_round(
                critic,
                plan=plan,
                claims=(),
                stage1_report=_stage1(),
                round_context=SemanticRoundContext(case_id="case", round_number=0),
            )

    def test_orchestrator_issue_cannot_be_attached_to_a_specialist_claim(self):
        plan = _company_plan()
        claim = _company_claim()
        issue = _issue(
            affected_agent="orchestrator",
            affected_claim_ids=(claim.claim_id,),
        )
        critic = FixtureSemanticCritic({"case": _result(plan, issues=(issue,))})
        with self.assertRaisesRegex(
            SemanticEvaluationError,
            "orchestrator_issue_must_target_synthesis",
        ):
            evaluate_semantic_round(
                critic,
                plan=plan,
                claims=(claim,),
                stage1_report=_stage1(),
                round_context=SemanticRoundContext(
                    case_id="case",
                    round_number=0,
                    synthesis_summary="The report needs a review.",
                    synthesis_supporting_claim_ids=(claim.claim_id,),
                ),
            )

    def test_synthesis_support_ids_must_be_known_and_follow_candidate_order(self):
        plan = _company_plan()
        claim = _company_claim()
        critic = FixtureSemanticCritic({"case": _result(plan)})
        with self.assertRaisesRegex(
            SemanticEvaluationError,
            "must_reference_candidate_claims",
        ):
            evaluate_semantic_round(
                critic,
                plan=plan,
                claims=(claim,),
                stage1_report=_stage1(),
                round_context=SemanticRoundContext(
                    case_id="case",
                    round_number=0,
                    synthesis_summary="The report follows the observation.",
                    synthesis_supporting_claim_ids=("unknown-claim",),
                ),
            )

    def test_fixture_evaluation_returns_derived_quality_scores_for_company_only_plan(self):
        plan = _company_plan()
        claim = _company_claim()
        result = _result(
            plan,
            fulfilled=("R1",),
            supporting_claim_ids=(claim.claim_id,),
        )
        critic = FixtureSemanticCritic({"company-case": result})

        artifact = evaluate_semantic_round(
            critic,
            plan=plan,
            claims=(claim,),
            stage1_report=_stage1(),
            round_context=SemanticRoundContext(case_id="company-case", round_number=0),
        )

        self.assertEqual(artifact.critic_result, result)
        self.assertIsNone(artifact.quality_scores.cross_level_integration)
        self.assertEqual(critic.invocation_count, 1)
        self.assertEqual(critic.calls[0].round_number, 0)

    def test_stage1_failure_blocks_critic_before_invocation(self):
        plan = _company_plan()
        critic = FixtureSemanticCritic({"case": _result(plan)})

        with self.assertRaisesRegex(
            SemanticEvaluationError,
            "stage1_failed_semantic_evaluation_blocked",
        ):
            evaluate_semantic_round(
                critic,
                plan=plan,
                claims=(),
                stage1_report=_stage1(passed=False),
                round_context=SemanticRoundContext(case_id="case", round_number=0),
            )

        self.assertEqual(critic.invocation_count, 0)

    def test_malformed_critic_result_is_rejected(self):
        with self.assertRaisesRegex(SemanticEvaluationError, "result_type_invalid"):
            evaluate_semantic_round(
                _MalformedCritic(),
                plan=_company_plan(),
                claims=(),
                stage1_report=_stage1(),
                round_context=SemanticRoundContext(round_number=0),
            )

    def test_wrong_dimension_applicability_is_rejected_against_plan(self):
        plan = _company_plan()
        critic = FixtureSemanticCritic(
            {"case": _result(plan, cross_applicable=True)}
        )

        with self.assertRaisesRegex(
            SemanticEvaluationError,
            "dimension_applicability_mismatch",
        ):
            evaluate_semantic_round(
                critic,
                plan=plan,
                claims=(),
                stage1_report=_stage1(),
                round_context=SemanticRoundContext(case_id="case", round_number=0),
            )

    def test_inactive_specialist_issue_is_rejected(self):
        plan = _company_plan()
        result = _result(plan, issues=(_issue(affected_agent="macro"),))
        critic = FixtureSemanticCritic({"case": result})

        with self.assertRaisesRegex(SemanticEvaluationError, "issue_agent_not_active"):
            evaluate_semantic_round(
                critic,
                plan=plan,
                claims=(),
                stage1_report=_stage1(),
                round_context=SemanticRoundContext(case_id="case", round_number=0),
            )

    def test_undeclared_cross_level_reconciliation_is_rejected(self):
        plan = _company_plan()
        issue = _issue(
            affected_agent="orchestrator",
            required_action=CritiqueAction.RECONCILE_CROSS_LEVEL,
        )
        critic = FixtureSemanticCritic({"case": _result(plan, issues=(issue,))})

        with self.assertRaisesRegex(
            SemanticEvaluationError,
            "cross_level_reconciliation_requires_applicable_link",
        ):
            evaluate_semantic_round(
                critic,
                plan=plan,
                claims=(),
                stage1_report=_stage1(),
                round_context=SemanticRoundContext(
                    case_id="case",
                    round_number=0,
                    synthesis_summary="The report-level reconciliation needs review.",
                ),
            )

    def test_declared_non_reconcile_link_issue_is_accepted(self):
        plan = build_tcb_macro_analysis_plan(
            DatasetRef(dataset_id="dataset", dataset_snapshot_id="snapshot")
        )
        issue = _issue(issue_id="link-data", affected_agent="macro")
        link_result = ApplicableLinkResult(
            link_id="L1",
            score=0.7,
            rationale="The link is reported with a data limitation.",
            issue_ids=("link-data",),
        )
        result = _result(
            plan,
            issues=(issue,),
            link_results=(link_result,),
        )
        artifact = evaluate_semantic_round(
            FixtureSemanticCritic({"case": result}),
            plan=plan,
            claims=(),
            stage1_report=_stage1(),
            round_context=SemanticRoundContext(
                case_id="case",
                round_number=0,
                synthesis_summary="The declared link needs review.",
            ),
        )

        self.assertEqual(artifact.critic_result.applicable_link_results[0].link_id, "L1")

    def test_unknown_claim_id_is_rejected(self):
        plan = _company_plan()
        result = _result(plan, supporting_claim_ids=("unknown-claim",))

        with self.assertRaisesRegex(SemanticEvaluationError, "unknown_claim_id"):
            evaluate_semantic_round(
                FixtureSemanticCritic({"case": result}),
                plan=plan,
                claims=(),
                stage1_report=_stage1(),
                round_context=SemanticRoundContext(case_id="case", round_number=0),
            )

    def test_unknown_requirement_id_is_rejected(self):
        plan = _company_plan()
        result = _result(plan, fulfilled=("unknown-requirement",))

        with self.assertRaisesRegex(SemanticEvaluationError, "unknown_requirement_id"):
            evaluate_semantic_round(
                FixtureSemanticCritic({"case": result}),
                plan=plan,
                claims=(),
                stage1_report=_stage1(),
                round_context=SemanticRoundContext(case_id="case", round_number=0),
            )

    def test_unknown_issue_id_is_rejected(self):
        plan = _company_plan()
        result = _result(plan, dimension_issue_ids=("unknown-issue",))

        with self.assertRaisesRegex(SemanticEvaluationError, "unknown_issue_id"):
            evaluate_semantic_round(
                FixtureSemanticCritic({"case": result}),
                plan=plan,
                claims=(),
                stage1_report=_stage1(),
                round_context=SemanticRoundContext(case_id="case", round_number=0),
            )

    def test_unknown_link_id_is_rejected(self):
        plan = _company_plan()
        link_result = ApplicableLinkResult(
            link_id="unknown-link",
            score=0.5,
            rationale="Unknown link fixture.",
        )
        result = _result(plan, link_results=(link_result,))

        with self.assertRaisesRegex(SemanticEvaluationError, "unknown_link_id"):
            evaluate_semantic_round(
                FixtureSemanticCritic({"case": result}),
                plan=plan,
                claims=(),
                stage1_report=_stage1(),
                round_context=SemanticRoundContext(case_id="case", round_number=0),
            )

    def test_critic_receives_defensive_copies_and_cannot_mutate_plan_or_claims(self):
        plan = _company_plan()
        claim = _company_claim()
        original_plan = plan.model_dump(mode="python")
        original_claim = claim.model_dump(mode="python")
        result = _result(
            plan,
            fulfilled=("R1",),
            supporting_claim_ids=(claim.claim_id,),
        )

        evaluate_semantic_round(
            _MutatingCritic(result),
            plan=plan,
            claims=(claim,),
            stage1_report=_stage1(),
            round_context=SemanticRoundContext(round_number=0),
        )

        self.assertEqual(plan.model_dump(mode="python"), original_plan)
        self.assertEqual(claim.model_dump(mode="python"), original_claim)

    def test_fixture_requires_explicit_case_and_does_not_infer_from_inputs(self):
        plan = _company_plan()
        critic = FixtureSemanticCritic({"known-case": _result(plan)})

        with self.assertRaisesRegex(SemanticEvaluationError, "fixture_case_not_found"):
            evaluate_semantic_round(
                critic,
                plan=plan,
                claims=(),
                stage1_report=_stage1(),
                round_context=SemanticRoundContext(round_number=0),
            )


if __name__ == "__main__":
    unittest.main()
