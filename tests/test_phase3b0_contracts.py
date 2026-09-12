import unittest

from pydantic import ValidationError

from thesis_data.analysis_plan import (
    ANALYSIS_PLAN_VERSION,
    AnalysisAgent,
    AnalysisPlan,
    AnalysisRequirement,
    AnalysisScope,
    ApplicableLink,
    ApplicableLinkType,
    CausalClaimPolicy,
    FulfillmentPolicy,
    InferenceCeiling,
    LinkLevel,
    MissingDataPolicy,
    RequirementType,
)
from thesis_data.dataset_contract import DatasetRef
from thesis_data.schema import (
    AcceptanceDecision,
    AcceptancePolicy,
    AcceptanceRound,
    CritiqueAction,
    CritiqueIssue,
    CritiqueIssueStatus,
    CritiqueIssueType,
    CritiqueSeverity,
    HardGateResult,
    QualityDimensionScores,
    ReportAcceptanceState,
    UnresolvedReasonCode,
)
from thesis_data.semantic_evaluation import (
    ApplicableLinkResult,
    SemanticContractError,
    SemanticDimension,
    SemanticDimensionApplicability,
    SemanticDimensionResult,
    StructuredCriticResult,
    deterministic_coverage_violations,
    validate_structured_critic_result,
)


def _plan(*, with_link: bool = False) -> AnalysisPlan:
    dataset_ref = DatasetRef(dataset_id="dataset", dataset_snapshot_id="snapshot")
    requirement = AnalysisRequirement(
        requirement_id="R1",
        requirement_type=RequirementType.FACTUAL_OBSERVATION,
        description="Report the requested observation.",
        required_agents=(AnalysisAgent.MACRO,),
        entities=("VN",),
        periods=("2024_Q4",),
        metric_ids=("macro.credit_growth",),
        inference_ceiling=InferenceCeiling.OBSERVATION_ONLY,
        fulfillment_policy=FulfillmentPolicy.VALUE_OR_ACCEPTED_MISSINGNESS,
        missing_data_policy=MissingDataPolicy.ACCEPTED_MISSINGNESS,
    )
    links = ()
    if with_link:
        links = (
            ApplicableLink(
                link_id="L1",
                link_type=ApplicableLinkType.MACRO_TO_COMPANY,
                source_level=LinkLevel.MACRO,
                target_level=LinkLevel.COMPANY,
                source_entities=("VN",),
                target_entities=("TCB",),
                source_periods=("2024_Q4",),
                target_periods=("2024_Q4",),
                source_metric_ids=("macro.credit_growth",),
                target_metric_ids=("bank.roa",),
                description="Macro context to company performance.",
            ),
        )
    return AnalysisPlan(
        plan_version=ANALYSIS_PLAN_VERSION,
        dataset_id=dataset_ref.dataset_id,
        dataset_snapshot_id=dataset_ref.dataset_snapshot_id,
        query_id="query",
        normalized_question="Report the requested observation.",
        scope=AnalysisScope(
            entities=("VN", "TCB") if with_link else ("VN",),
            periods=("2024_Q4",),
            company_metric_ids=("bank.roa",) if with_link else (),
            macro_indicator_ids=("macro.credit_growth",),
        ),
        requirements=(requirement,),
        applicable_links=links,
        requested_outputs=("structured_facts",),
        causal_claim_policy=CausalClaimPolicy.ASSOCIATION_ONLY,
    )


def _result(
    plan: AnalysisPlan,
    *,
    issues=(),
    link_results=(),
    fulfilled=(),
    unfulfilled=("R1",),
) -> StructuredCriticResult:
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
                1.0
                if cross_applicable or dimension is not SemanticDimension.CROSS_LEVEL_INTEGRATION
                else None
            ),
            rationale="contract fixture",
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


def _gates() -> dict[str, HardGateResult]:
    gate_ids = (
        "numeric_accuracy",
        "reference_validity",
        "critical_evidence_coverage",
        "scope_compliance",
        "fabricated_or_unaccepted_records",
        "blocking_contradictions",
    )
    return {
        gate_id: HardGateResult(
            gate_id=gate_id,
            passed=True,
            rate=1.0,
            required_rate=1.0,
            evaluation_unit="fixture",
            evaluated_count=1,
            passed_count=1,
        )
        for gate_id in gate_ids
    }


def _issue(
    *,
    issue_id: str = "issue-1",
    issue_type: CritiqueIssueType = CritiqueIssueType.MISSING_DATA,
    action: CritiqueAction = CritiqueAction.REQUERY_DATA,
    agent: str = "macro",
    reason: UnresolvedReasonCode | None = None,
    status: CritiqueIssueStatus = CritiqueIssueStatus.OPEN,
) -> CritiqueIssue:
    return CritiqueIssue(
        issue_id=issue_id,
        issue_type=issue_type,
        severity=CritiqueSeverity.MAJOR,
        affected_agent=agent,
        description="Fixture issue.",
        required_action=action,
        resolution_status=status,
        unresolved_reason_code=reason,
    )


class Phase3B0ContractTests(unittest.TestCase):
    def test_applicable_dimension_requires_finite_score(self):
        with self.assertRaisesRegex(ValidationError, "requires a score"):
            SemanticDimensionResult(
                dimension=SemanticDimension.GROUNDEDNESS,
                applicability=SemanticDimensionApplicability.APPLICABLE,
                rationale="missing score",
            )

    def test_not_applicable_dimension_has_no_score_or_support(self):
        for fake_score in (0.0, 1.0):
            with self.subTest(fake_score=fake_score):
                with self.assertRaises(ValidationError):
                    SemanticDimensionResult(
                        dimension=SemanticDimension.CROSS_LEVEL_INTEGRATION,
                        applicability=SemanticDimensionApplicability.NOT_APPLICABLE,
                        score=fake_score,
                        rationale="not applicable",
                    )
        with self.assertRaises(ValidationError):
            SemanticDimensionResult(
                dimension=SemanticDimension.CROSS_LEVEL_INTEGRATION,
                applicability=SemanticDimensionApplicability.NOT_APPLICABLE,
                rationale="not applicable",
                supporting_claim_ids=("claim-1",),
            )

    def test_no_link_plan_derives_cross_level_not_applicable(self):
        plan = _plan()
        result = _result(plan)
        validate_structured_critic_result(plan, result, ())
        cross_level = next(
            item
            for item in result.dimension_scores
            if item.dimension is SemanticDimension.CROSS_LEVEL_INTEGRATION
        )
        self.assertIs(cross_level.applicability, SemanticDimensionApplicability.NOT_APPLICABLE)
        self.assertIsNone(cross_level.score)

    def test_wrong_plan_derived_applicability_fails_closed(self):
        plan = _plan()
        dimensions = list(_result(plan).dimension_scores)
        index = next(
            index
            for index, item in enumerate(dimensions)
            if item.dimension is SemanticDimension.CROSS_LEVEL_INTEGRATION
        )
        dimensions[index] = SemanticDimensionResult(
            dimension=SemanticDimension.CROSS_LEVEL_INTEGRATION,
            applicability=SemanticDimensionApplicability.APPLICABLE,
            score=1.0,
            rationale="incorrectly applicable",
        )
        result = StructuredCriticResult(
            evaluator_version="fixture-v1",
            dimension_scores=tuple(dimensions),
            unfulfilled_requirement_ids=("R1",),
        )
        with self.assertRaisesRegex(SemanticContractError, "dimension_applicability_mismatch"):
            validate_structured_critic_result(plan, result, ())

    def test_linked_plan_requires_applicable_cross_level_score(self):
        plan = _plan(with_link=True)
        result = _result(
            plan,
            link_results=(
                ApplicableLinkResult(link_id="L1", score=1.0, rationale="covered"),
            ),
        )
        cross_level = next(
            item
            for item in result.dimension_scores
            if item.dimension is SemanticDimension.CROSS_LEVEL_INTEGRATION
        )
        self.assertIs(cross_level.applicability, SemanticDimensionApplicability.APPLICABLE)
        self.assertIsNotNone(cross_level.score)
        validate_structured_critic_result(plan, result, ())

    def test_quality_total_renormalizes_over_applicable_dimensions(self):
        scores = QualityDimensionScores(
            groundedness=0.5,
            cross_level_integration=None,
            answer_coverage=0.75,
            logical_soundness=0.25,
            uncertainty_limitations=0.5,
            analytical_usefulness=1.0,
        )
        self.assertEqual(scores.weighted_total(AcceptancePolicy(
            policy_version="policy-v1",
            provisional_threshold=0.5,
        ).quality_weights), 0.546875)

    def test_all_six_applicable_scoring_remains_unchanged(self):
        scores = QualityDimensionScores(
            groundedness=1.0,
            cross_level_integration=0.5,
            answer_coverage=0.5,
            logical_soundness=1.0,
            uncertainty_limitations=0.0,
            analytical_usefulness=1.0,
        )
        policy = AcceptancePolicy(policy_version="policy-v1", provisional_threshold=0.5)
        self.assertEqual(scores.weighted_total(policy.quality_weights), 0.7)

    def test_all_not_applicable_quality_scores_fail_closed(self):
        with self.assertRaisesRegex(ValueError, "at least one applicable"):
            QualityDimensionScores(
                groundedness=None,
                cross_level_integration=None,
                answer_coverage=None,
                logical_soundness=None,
                uncertainty_limitations=None,
                analytical_usefulness=None,
            )

    def test_zero_weight_only_applicable_dimension_fails_quality_total(self):
        scores = QualityDimensionScores(
            groundedness=1.0,
            cross_level_integration=None,
            answer_coverage=None,
            logical_soundness=None,
            uncertainty_limitations=None,
            analytical_usefulness=None,
        )
        policy = AcceptancePolicy(
            policy_version="policy-v1",
            provisional_threshold=0.5,
            quality_weights={
                "groundedness": 0.0,
                "cross_level_integration": 1.0,
                "answer_coverage": 0.0,
                "logical_soundness": 0.0,
                "uncertainty_limitations": 0.0,
                "analytical_usefulness": 0.0,
            },
        )
        with self.assertRaisesRegex(ValueError, "positive-weight"):
            scores.weighted_total(policy.quality_weights)

    def test_missing_data_with_data_reason_supports_limited_acceptance(self):
        policy = AcceptancePolicy(policy_version="policy-v1", provisional_threshold=0.75)
        issue = _issue(
            status=CritiqueIssueStatus.UNRESOLVED,
            reason=UnresolvedReasonCode.DATA_UNAVAILABLE,
        )
        round_state = AcceptanceRound(
            round_number=0,
            hard_gate_results=_gates(),
            critique_issues=(issue,),
            unresolved_issue_ids=(issue.issue_id,),
            unresolved_reason_codes=(UnresolvedReasonCode.DATA_UNAVAILABLE,),
            quality_scores=QualityDimensionScores(
                groundedness=1.0,
                cross_level_integration=None,
                answer_coverage=1.0,
                logical_soundness=1.0,
                uncertainty_limitations=1.0,
                analytical_usefulness=1.0,
            ),
            quality_total=1.0,
            provisional_threshold=policy.provisional_threshold,
            final_payload_version="payload-v1",
            acceptance_decision=AcceptanceDecision.ACCEPT_WITH_LIMITATIONS,
        )
        self.assertEqual(round_state.acceptance_decision, AcceptanceDecision.ACCEPT_WITH_LIMITATIONS)

    def test_missing_data_with_evidence_reason_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "availability family"):
            _issue(
                status=CritiqueIssueStatus.UNRESOLVED,
                reason=UnresolvedReasonCode.EVIDENCE_UNAVAILABLE,
            )

    def test_missing_evidence_with_evidence_reason_supports_limited_acceptance(self):
        policy = AcceptancePolicy(policy_version="policy-v1", provisional_threshold=0.75)
        issue = _issue(
            issue_type=CritiqueIssueType.MISSING_EVIDENCE,
            action=CritiqueAction.RETRIEVE_EVIDENCE,
            status=CritiqueIssueStatus.UNRESOLVED,
            reason=UnresolvedReasonCode.EVIDENCE_UNAVAILABLE,
        )
        round_state = AcceptanceRound(
            round_number=0,
            hard_gate_results=_gates(),
            critique_issues=(issue,),
            unresolved_issue_ids=(issue.issue_id,),
            unresolved_reason_codes=(UnresolvedReasonCode.EVIDENCE_UNAVAILABLE,),
            quality_scores=QualityDimensionScores(
                groundedness=1.0,
                cross_level_integration=1.0,
                answer_coverage=1.0,
                logical_soundness=1.0,
                uncertainty_limitations=1.0,
                analytical_usefulness=1.0,
            ),
            quality_total=1.0,
            provisional_threshold=policy.provisional_threshold,
            final_payload_version="payload-v1",
            acceptance_decision=AcceptanceDecision.ACCEPT_WITH_LIMITATIONS,
        )
        self.assertEqual(round_state.acceptance_decision, AcceptanceDecision.ACCEPT_WITH_LIMITATIONS)

    def test_missing_evidence_with_data_reason_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "availability family"):
            _issue(
                issue_type=CritiqueIssueType.MISSING_EVIDENCE,
                action=CritiqueAction.RETRIEVE_EVIDENCE,
                status=CritiqueIssueStatus.UNRESOLVED,
                reason=UnresolvedReasonCode.DATA_UNAVAILABLE,
            )

    def test_inactive_issue_agent_fails_closed(self):
        plan = _plan()
        result = _result(plan, issues=(_issue(agent="company"),))
        with self.assertRaisesRegex(SemanticContractError, "issue_agent_not_active"):
            validate_structured_critic_result(plan, result, ())

    def test_orchestrator_issue_agent_is_allowed(self):
        plan = _plan()
        result = _result(plan, issues=(_issue(agent="orchestrator"),))
        validate_structured_critic_result(plan, result, ())

    def test_reconcile_action_requires_declared_link(self):
        plan = _plan()
        result = _result(
            plan,
            issues=(
                _issue(
                    issue_type=CritiqueIssueType.CROSS_LEVEL_CONTRADICTION,
                    action=CritiqueAction.RECONCILE_CROSS_LEVEL,
                    agent="orchestrator",
                ),
            ),
        )
        with self.assertRaisesRegex(
            SemanticContractError,
            "cross_level_reconciliation_requires_applicable_link",
        ):
            validate_structured_critic_result(plan, result, ())

    def test_reconcile_action_requires_exactly_one_link_result(self):
        plan = _plan(with_link=True)
        issue = _issue(
            issue_type=CritiqueIssueType.CROSS_LEVEL_CONTRADICTION,
            action=CritiqueAction.RECONCILE_CROSS_LEVEL,
            agent="orchestrator",
        )
        missing = _result(plan, issues=(issue,))
        with self.assertRaisesRegex(SemanticContractError, "link_result_missing"):
            validate_structured_critic_result(plan, missing, ())

        linked = _result(
            plan,
            issues=(issue,),
            link_results=(
                ApplicableLinkResult(
                    link_id="L1",
                    score=1.0,
                    rationale="linked",
                    issue_ids=(issue.issue_id,),
                ),
            ),
        )
        validate_structured_critic_result(plan, linked, ())

    def test_reconcile_action_rejects_unknown_or_multiple_link_results(self):
        plan = _plan(with_link=True)
        issue = _issue(
            issue_type=CritiqueIssueType.CROSS_LEVEL_CONTRADICTION,
            action=CritiqueAction.RECONCILE_CROSS_LEVEL,
            agent="orchestrator",
        )
        unknown = _result(
            plan,
            issues=(issue,),
            link_results=(
                ApplicableLinkResult(
                    link_id="L999",
                    score=1.0,
                    rationale="unknown link",
                    issue_ids=(issue.issue_id,),
                ),
            ),
        )
        with self.assertRaisesRegex(SemanticContractError, "unknown_link_id:L999"):
            validate_structured_critic_result(plan, unknown, ())

        second_link = plan.applicable_links[0].model_copy(update={"link_id": "L2"})
        two_link_plan = plan.model_copy(
            update={"applicable_links": (plan.applicable_links[0], second_link)}
        )
        multiple = _result(
            two_link_plan,
            issues=(issue,),
            link_results=(
                ApplicableLinkResult(
                    link_id="L1",
                    score=1.0,
                    rationale="first link",
                    issue_ids=(issue.issue_id,),
                ),
                ApplicableLinkResult(
                    link_id="L2",
                    score=1.0,
                    rationale="second link",
                    issue_ids=(issue.issue_id,),
                ),
            ),
        )
        with self.assertRaisesRegex(SemanticContractError, "link_result_ambiguous"):
            validate_structured_critic_result(two_link_plan, multiple, ())

    def test_non_reconcile_issues_may_attach_to_declared_link(self):
        plan = _plan(with_link=True)
        divergence = _issue(
            issue_id="divergence-1",
            issue_type=CritiqueIssueType.MEANINGFUL_DIVERGENCE,
            action=CritiqueAction.ADD_LIMITATION,
            agent="orchestrator",
        )
        missing_evidence = _issue(
            issue_id="evidence-1",
            issue_type=CritiqueIssueType.MISSING_EVIDENCE,
            action=CritiqueAction.RETRIEVE_EVIDENCE,
            agent="orchestrator",
        )
        result = _result(
            plan,
            issues=(divergence, missing_evidence),
            link_results=(
                ApplicableLinkResult(
                    link_id="L1",
                    score=1.0,
                    rationale="declared link with non-reconcile issues",
                    issue_ids=(divergence.issue_id, missing_evidence.issue_id),
                ),
            ),
        )
        validate_structured_critic_result(plan, result, ())

    def test_unsupported_reasoning_issue_cannot_produce_limited_acceptance(self):
        issue = _issue(
            issue_type=CritiqueIssueType.UNSUPPORTED_CLAIM,
            action=CritiqueAction.REVISE_CLAIM,
            status=CritiqueIssueStatus.UNRESOLVED,
        )
        with self.assertRaisesRegex(ValueError, "limited acceptance requires explicit"):
            AcceptanceRound(
                round_number=0,
                hard_gate_results=_gates(),
                critique_issues=(issue,),
                unresolved_issue_ids=(issue.issue_id,),
                quality_scores=QualityDimensionScores(
                    groundedness=1.0,
                    cross_level_integration=1.0,
                    answer_coverage=1.0,
                    logical_soundness=1.0,
                    uncertainty_limitations=1.0,
                    analytical_usefulness=1.0,
                ),
                quality_total=1.0,
                provisional_threshold=0.75,
                final_payload_version="payload-v1",
                acceptance_decision=AcceptanceDecision.ACCEPT_WITH_LIMITATIONS,
            )

    def test_unresolved_unsupported_claim_without_reason_is_valid(self):
        issue = _issue(
            issue_type=CritiqueIssueType.UNSUPPORTED_CLAIM,
            action=CritiqueAction.REVISE_CLAIM,
            status=CritiqueIssueStatus.UNRESOLVED,
        )
        self.assertIsNone(issue.unresolved_reason_code)

    def test_fail_acceptance_persists_unresolved_reasoning_issue(self):
        issue = _issue(
            issue_type=CritiqueIssueType.UNSUPPORTED_CLAIM,
            action=CritiqueAction.REVISE_CLAIM,
            status=CritiqueIssueStatus.UNRESOLVED,
        )
        round_state = AcceptanceRound(
            round_number=0,
            hard_gate_results=_gates(),
            critique_issues=(issue,),
            unresolved_issue_ids=(issue.issue_id,),
            quality_scores=QualityDimensionScores(
                groundedness=0.0,
                cross_level_integration=1.0,
                answer_coverage=0.0,
                logical_soundness=0.0,
                uncertainty_limitations=0.0,
                analytical_usefulness=0.0,
            ),
            quality_total=0.0,
            provisional_threshold=0.75,
            final_payload_version=None,
            acceptance_decision=AcceptanceDecision.FAIL_ACCEPTANCE,
        )
        self.assertEqual(round_state.unresolved_issue_ids, (issue.issue_id,))

    def test_accept_rejects_open_issue(self):
        issue = _issue(status=CritiqueIssueStatus.OPEN)
        with self.assertRaisesRegex(ValueError, "OPEN critique issues"):
            AcceptanceRound(
                round_number=0,
                hard_gate_results=_gates(),
                critique_issues=(issue,),
                quality_scores=QualityDimensionScores(
                    groundedness=1.0,
                    cross_level_integration=1.0,
                    answer_coverage=1.0,
                    logical_soundness=1.0,
                    uncertainty_limitations=1.0,
                    analytical_usefulness=1.0,
                ),
                quality_total=1.0,
                provisional_threshold=0.75,
                final_payload_version="payload-v1",
                acceptance_decision=AcceptanceDecision.ACCEPT,
            )

    def test_limited_acceptance_rejects_open_issue(self):
        open_issue = _issue(issue_id="open-1", status=CritiqueIssueStatus.OPEN)
        missing_issue = _issue(
            issue_id="missing-1",
            status=CritiqueIssueStatus.UNRESOLVED,
            reason=UnresolvedReasonCode.DATA_UNAVAILABLE,
        )
        with self.assertRaisesRegex(ValueError, "OPEN critique issues"):
            AcceptanceRound(
                round_number=0,
                hard_gate_results=_gates(),
                critique_issues=(open_issue, missing_issue),
                unresolved_issue_ids=(missing_issue.issue_id,),
                unresolved_reason_codes=(UnresolvedReasonCode.DATA_UNAVAILABLE,),
                quality_scores=QualityDimensionScores(
                    groundedness=1.0,
                    cross_level_integration=1.0,
                    answer_coverage=1.0,
                    logical_soundness=1.0,
                    uncertainty_limitations=1.0,
                    analytical_usefulness=1.0,
                ),
                quality_total=1.0,
                provisional_threshold=0.75,
                final_payload_version="payload-v1",
                acceptance_decision=AcceptanceDecision.ACCEPT_WITH_LIMITATIONS,
            )

    def test_applicable_link_results_cover_every_declared_link(self):
        plan = _plan(with_link=True)
        violations = deterministic_coverage_violations(plan, _result(plan), ())
        self.assertIn("omitted_link_result:L1", violations)

    def test_plan_valid_active_specialist_issue_passes(self):
        plan = _plan()
        validate_structured_critic_result(plan, _result(plan, issues=(_issue(),)), ())

    def test_report_acceptance_uses_renormalized_quality_total(self):
        policy = AcceptancePolicy(policy_version="policy-v1", provisional_threshold=0.75)
        scores = QualityDimensionScores(
            groundedness=1.0,
            cross_level_integration=None,
            answer_coverage=1.0,
            logical_soundness=1.0,
            uncertainty_limitations=1.0,
            analytical_usefulness=1.0,
        )
        round_state = AcceptanceRound(
            round_number=0,
            hard_gate_results=_gates(),
            quality_scores=scores,
            quality_total=1.0,
            provisional_threshold=policy.provisional_threshold,
            final_payload_version="payload-v1",
            acceptance_decision=AcceptanceDecision.ACCEPT,
        )
        state = ReportAcceptanceState(
            acceptance_model_version="acceptance-v1",
            run_id="run-1",
            policy=policy,
            rounds=(round_state,),
            final_payload_version="payload-v1",
            final_decision=AcceptanceDecision.ACCEPT,
        )
        self.assertEqual(state.rounds[0].quality_scores.cross_level_integration, None)


if __name__ == "__main__":
    unittest.main()
