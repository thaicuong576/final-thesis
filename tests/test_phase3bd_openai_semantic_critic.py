import json
from pathlib import Path
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
from thesis_data.openai_semantic_critic import (
    OpenAISemanticCritic,
    OpenAISemanticCriticError,
    structured_critic_response_schema,
)
from thesis_data.provider_config import ProviderExecutionConfig
from thesis_data.revision_controller import (
    RevisionResult,
    RevisionWorkflowKernel,
    RevisionWorkflowState,
    BoundedRevisionController,
)
from thesis_data.schema import (
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
from thesis_data.semantic_critic import (
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


class FakeResponse:
    def __init__(self, output_text=None, *, status="completed", output=()):
        self.output_text = output_text
        self.status = status
        self.output = output


class FakeResponses:
    def __init__(self, responses=(), exception=None):
        self.responses = list(responses)
        self.exception = exception
        self.calls = []

    def create(self, **kwargs):
        self.calls.append(kwargs)
        if self.exception is not None:
            raise self.exception
        if not self.responses:
            raise AssertionError("unexpected Responses API call")
        return self.responses.pop(0)


class FakeClient:
    def __init__(self, responses=(), exception=None):
        self.responses = FakeResponses(responses, exception=exception)


def _config() -> ProviderExecutionConfig:
    return ProviderExecutionConfig(
        adapter_id="openai-semantic-critic-v1",
        provider_id="openai",
        model_id="gpt-5.6-luna",
        source_policy_id="primary-only-v1",
        environment="provider_backed",
        retrieval_mode="prefetched",
        network_access="enabled",
        api_key_env_var="OPENAI_API_KEY",
        reasoning_effort="medium",
        max_output_tokens=4096,
    )


def _company_plan(query_id="company-query") -> AnalysisPlan:
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
        query_id=query_id,
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


def _company_two_requirement_plan() -> AnalysisPlan:
    base = _company_plan("company-two-requirements")
    second_requirement = AnalysisRequirement(
        requirement_id="R2",
        requirement_type=RequirementType.FACTUAL_OBSERVATION,
        description="Report the second company observation.",
        required_agents=(AnalysisAgent.COMPANY,),
        entities=("TCB",),
        periods=("2024_Q4",),
        metric_ids=("bank.roe",),
        inference_ceiling=InferenceCeiling.OBSERVATION_ONLY,
        fulfillment_policy=FulfillmentPolicy.VALID_VALUE_REQUIRED,
        missing_data_policy=MissingDataPolicy.REJECT_MISSING,
    )
    return base.model_copy(
        update={
            "scope": base.scope.model_copy(
                update={"company_metric_ids": ("bank.roa", "bank.roe")}
            ),
            "requirements": base.requirements + (second_requirement,),
        }
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


def _stage1(passed=True) -> Stage1ValidationReport:
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
        gate_passed = passed
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
    issue_id="issue-1",
    *,
    status=CritiqueIssueStatus.OPEN,
    issue_type=CritiqueIssueType.MISSING_DATA,
    action=CritiqueAction.REQUERY_DATA,
    agent="company",
    affected_requirement_ids=(),
    unresolved_reason_code=None,
) -> CritiqueIssue:
    return CritiqueIssue(
        issue_id=issue_id,
        issue_type=issue_type,
        severity=CritiqueSeverity.MAJOR,
        affected_agent=agent,
        affected_requirement_ids=tuple(affected_requirement_ids),
        description="The candidate needs a bounded data follow-up.",
        required_action=action,
        resolution_status=status,
        unresolved_reason_code=unresolved_reason_code,
    )


def _result(
    plan: AnalysisPlan,
    evaluator_version: str,
    *,
    fulfilled=(),
    partial=(),
    issues=(),
    link_results=(),
    supporting_claim_ids=(),
    cross_applicable=None,
):
    if cross_applicable is None:
        cross_applicable = bool(plan.applicable_links)
    fulfilled = tuple(fulfilled)
    partial = tuple(partial)
    unfulfilled = tuple(
        requirement.requirement_id
        for requirement in plan.requirements
        if requirement.requirement_id not in fulfilled
        and requirement.requirement_id not in partial
    )
    dimensions = tuple(
        SemanticDimensionResult(
            dimension=dimension,
            applicability=(
                SemanticDimensionApplicability.APPLICABLE
                if cross_applicable or dimension is not SemanticDimension.CROSS_LEVEL_INTEGRATION
                else SemanticDimensionApplicability.NOT_APPLICABLE
            ),
            score=(
                0.85
                if cross_applicable or dimension is not SemanticDimension.CROSS_LEVEL_INTEGRATION
                else None
            ),
            rationale="The fixture supplies a concise observable rationale.",
            supporting_claim_ids=(
                tuple(supporting_claim_ids)
                if cross_applicable or dimension is not SemanticDimension.CROSS_LEVEL_INTEGRATION
                else ()
            ),
        )
        for dimension in SemanticDimension
    )
    return StructuredCriticResult(
        evaluator_version=evaluator_version,
        dimension_scores=dimensions,
        critique_issues=tuple(issues),
        fulfilled_requirement_ids=fulfilled,
        unfulfilled_requirement_ids=unfulfilled,
        partially_fulfilled_requirement_ids=partial,
        applicable_link_results=tuple(link_results),
    )


def _encoded(result: StructuredCriticResult) -> str:
    return result.model_dump_json()


class _Stage1Sequence:
    def __init__(self, reports):
        self.reports = list(reports)

    def evaluate(self, *, plan, claims, policy):
        del plan, claims, policy
        if not self.reports:
            raise AssertionError("unexpected Stage-1 call")
        return self.reports.pop(0).model_copy(deep=True)


class _RevisionExecutor:
    def __init__(self, claim):
        self.claim = claim

    def execute(self, *, request):
        source_claim = next(
            (
                claim
                for claim in request.current_claims
                if claim.claim_id == self.claim.claim_id
            ),
            self.claim,
        )
        revised_claim = source_claim.model_copy(
            update={
                "interpretation": (
                    source_claim.interpretation + " Clarified during revision."
                )
            }
        )
        return RevisionResult(
            revised_claims=(revised_claim,),
            revised_agents=request.target_specialists,
            revised_claim_ids={
                agent: (revised_claim.claim_id,)
                for agent in request.target_specialists
            },
            payload_version="payload-revised",
        )


class OpenAISemanticCriticAdapterTests(unittest.TestCase):
    def _critic_with(self, result, *, responses=None):
        if responses is None:
            responses = [FakeResponse(_encoded(result))]
        client = FakeClient(responses)
        critic = OpenAISemanticCritic(client=client, config=_config())
        return critic, client

    def _run_controller_with_results(self, *, plan, run_id, results_builder):
        claim = _company_claim()
        client = FakeClient()
        critic = OpenAISemanticCritic(client=client, config=_config())
        results = results_builder(critic.evaluator_version)
        client.responses.responses.extend(
            FakeResponse(_encoded(result)) for result in results
        )
        controller = BoundedRevisionController(
            policy=AcceptancePolicy(
                policy_version=f"{run_id}-policy",
                provisional_threshold=0.75,
            ),
            stage1_evaluator=_Stage1Sequence([_stage1() for _ in results]),
            semantic_critic=critic,
            revision_executor=_RevisionExecutor(claim),
        )
        return controller.run(
            run_id=run_id,
            plan=plan,
            claims=(claim,),
            initial_payload_version="payload-initial",
        ), client

    def test_valid_company_result_passes_evaluate_semantic_round(self):
        plan = _company_plan()
        claim = _company_claim()
        client = FakeClient()
        critic = OpenAISemanticCritic(client=client, config=_config())
        result = _result(
            plan,
            critic.evaluator_version,
            fulfilled=("R1",),
            supporting_claim_ids=(claim.claim_id,),
        )
        client.responses.responses.append(FakeResponse(_encoded(result)))

        artifact = evaluate_semantic_round(
            critic,
            plan=plan,
            claims=(claim,),
            stage1_report=_stage1(),
            round_context=SemanticRoundContext(round_number=0),
        )

        self.assertEqual(artifact.critic_result, result)
        self.assertIsNone(artifact.quality_scores.cross_level_integration)

    def test_company_only_payload_derives_cross_level_not_applicable(self):
        plan = _company_plan()
        critic, client = self._critic_with(
            _result(plan, "wrong-until-replaced")
        )
        result = _result(plan, critic.evaluator_version)
        client.responses.responses[0] = FakeResponse(_encoded(result))

        critic.evaluate(
            plan=plan,
            claims=(),
            stage1_report=_stage1(),
            round_context=SemanticRoundContext(round_number=0),
        )

        payload = json.loads(client.responses.calls[0]["input"])
        self.assertEqual(
            payload["expected_semantic_dimension_applicability"]["cross_level_integration"],
            "NOT_APPLICABLE",
        )

    def test_report_level_synthesis_and_support_ids_are_rendered_separately(self):
        plan = _company_plan()
        claim = _company_claim()
        critic, client = self._critic_with(_result(plan, "placeholder"))
        client.responses.responses[0] = FakeResponse(
            _encoded(_result(plan, critic.evaluator_version))
        )
        context = SemanticRoundContext(
            round_number=0,
            synthesis_summary="The reviewed observation frames the company report.",
            synthesis_supporting_claim_ids=(claim.claim_id,),
        )

        critic.evaluate(
            plan=plan,
            claims=(claim,),
            stage1_report=_stage1(),
            round_context=context,
        )

        payload = json.loads(client.responses.calls[0]["input"])
        self.assertEqual(
            payload["report_level_synthesis"],
            {
                "target_id": "synthesis",
                "summary": "The reviewed observation frames the company report.",
                "supporting_claim_ids": [claim.claim_id],
            },
        )
        self.assertEqual(payload["claims"][0]["claim_id"], claim.claim_id)
        self.assertNotIn("report_level_synthesis", payload["claims"][0])

    def test_invalid_constructed_synthesis_context_fails_before_provider_call(self):
        plan = _company_plan()
        critic, client = self._critic_with(_result(plan, "placeholder"))
        malformed_context = SemanticRoundContext.model_construct(
            round_number=0,
            synthesis_target_id="not-synthesis",
            synthesis_summary="The report is qualitative.",
            synthesis_supporting_claim_ids=(),
        )
        with self.assertRaisesRegex(
            OpenAISemanticCriticError,
            "openai_semantic_critic_context_invalid",
        ):
            critic.evaluate(
                plan=plan,
                claims=(),
                stage1_report=_stage1(),
                round_context=malformed_context,
            )
        self.assertEqual(client.responses.calls, [])

    def test_synthesis_support_ids_are_checked_before_provider_call(self):
        plan = _company_plan()
        critic, client = self._critic_with(_result(plan, "placeholder"))
        context = SemanticRoundContext(
            round_number=0,
            synthesis_summary="The report is qualitative.",
            synthesis_supporting_claim_ids=("unknown-claim",),
        )
        with self.assertRaisesRegex(
            OpenAISemanticCriticError,
            "openai_semantic_critic_synthesis_support_invalid",
        ):
            critic.evaluate(
                plan=plan,
                claims=(),
                stage1_report=_stage1(),
                round_context=context,
            )
        self.assertEqual(client.responses.calls, [])

    def test_linked_payload_marks_applicable_and_lists_only_declared_links(self):
        plan = build_tcb_macro_analysis_plan(
            DatasetRef(dataset_id="dataset", dataset_snapshot_id="snapshot")
        )
        critic, client = self._critic_with(_result(plan, "placeholder"))
        link_result = ApplicableLinkResult(
            link_id="L1",
            score=0.8,
            rationale="The declared macro-to-company link is assessed.",
        )
        result = _result(
            plan,
            critic.evaluator_version,
            link_results=(link_result,),
        )
        client.responses.responses[0] = FakeResponse(_encoded(result))

        critic.evaluate(
            plan=plan,
            claims=(),
            stage1_report=_stage1(),
            round_context=SemanticRoundContext(round_number=0),
        )

        payload = json.loads(client.responses.calls[0]["input"])
        self.assertEqual(
            payload["expected_semantic_dimension_applicability"]["cross_level_integration"],
            "APPLICABLE",
        )
        self.assertEqual(payload["allowed_applicable_link_ids"], ["L1"])
        self.assertEqual([link["link_id"] for link in payload["applicable_links"]], ["L1"])

    def test_payload_preserves_dataset_snapshot_query_claim_and_requirement_ids(self):
        plan = _company_plan()
        claim = _company_claim()
        critic, client = self._critic_with(_result(plan, "placeholder"))
        result = _result(
            plan,
            critic.evaluator_version,
            fulfilled=("R1",),
            supporting_claim_ids=(claim.claim_id,),
        )
        client.responses.responses[0] = FakeResponse(_encoded(result))

        critic.evaluate(
            plan=plan,
            claims=(claim,),
            stage1_report=_stage1(),
            round_context=SemanticRoundContext(round_number=0),
        )
        payload = json.loads(client.responses.calls[0]["input"])
        self.assertEqual(payload["dataset_id"], "dataset")
        self.assertEqual(payload["dataset_snapshot_id"], "snapshot")
        self.assertEqual(payload["query_id"], "company-query")
        self.assertEqual(payload["allowed_claim_ids"], ["company-claim"])
        self.assertEqual(payload["allowed_requirement_ids"], ["R1"])
        self.assertEqual(payload["claims"][0]["claim_id"], "company-claim")
        self.assertEqual(client.responses.calls[0]["model"], "gpt-5.6-luna")
        self.assertNotIn("tools", client.responses.calls[0])

    def test_payload_preserves_frozen_scope_and_causal_policy(self):
        base_plan = _company_plan()
        plan = base_plan.model_copy(
            update={
                "scope": base_plan.scope.model_copy(
                    update={"comparison_universe": ("TCB",)}
                )
            }
        )
        critic, client = self._critic_with(_result(plan, "placeholder"))
        client.responses.responses[0] = FakeResponse(
            _encoded(_result(plan, critic.evaluator_version))
        )

        critic.evaluate(
            plan=plan,
            claims=(),
            stage1_report=_stage1(),
            round_context=SemanticRoundContext(round_number=0),
        )

        payload = json.loads(client.responses.calls[0]["input"])
        self.assertEqual(payload["analysis_scope"]["comparison_universe"], ["TCB"])
        self.assertEqual(
            payload["causal_claim_policy"],
            CausalClaimPolicy.ASSOCIATION_ONLY.value,
        )

    def test_responses_request_uses_strict_complete_json_schema(self):
        version = "openai-semantic-critic-v1:gpt-5.6-luna"
        schema = structured_critic_response_schema(version)

        def assert_strict_objects(node):
            if isinstance(node, dict):
                if node.get("type") == "object" and "properties" in node:
                    self.assertFalse(node.get("additionalProperties", True))
                    self.assertEqual(set(node["properties"]), set(node["required"]))
                for value in node.values():
                    assert_strict_objects(value)
            elif isinstance(node, list):
                for value in node:
                    assert_strict_objects(value)

        assert_strict_objects(schema)
        self.assertEqual(
            schema["properties"]["contract_version"]["enum"],
            ["structured-critic-result-v1"],
        )
        self.assertEqual(schema["properties"]["evaluator_version"]["enum"], [version])

    def test_provider_cannot_select_arbitrary_evaluator_version(self):
        plan = _company_plan()
        critic, client = self._critic_with(_result(plan, "placeholder"))
        wrong_version = _result(plan, "provider-chosen-version")
        client.responses.responses[0] = FakeResponse(_encoded(wrong_version))
        # The provider's echoed version is ignored: the result always carries the
        # configured adapter:model identity, so the provider still cannot select it.
        result = critic.evaluate(
            plan=plan,
            claims=(),
            stage1_report=_stage1(),
            round_context=SemanticRoundContext(round_number=0),
        )
        self.assertEqual(result.evaluator_version, critic.evaluator_version)
        self.assertNotEqual(result.evaluator_version, "provider-chosen-version")

    def test_prior_open_issue_details_are_rendered_and_can_be_resolved(self):
        plan = _company_plan()
        prior = _issue("prior-issue")
        context = SemanticRoundContext(
            round_number=1,
            prior_issue_ids=(prior.issue_id,),
            prior_issues=(prior,),
        )
        critic, client = self._critic_with(_result(plan, "placeholder"))
        resolved = _issue("prior-issue", status=CritiqueIssueStatus.RESOLVED)
        result = _result(
            plan,
            critic.evaluator_version,
            fulfilled=("R1",),
            issues=(resolved,),
        )
        client.responses.responses[0] = FakeResponse(_encoded(result))

        output = critic.evaluate(
            plan=plan,
            claims=(),
            stage1_report=_stage1(),
            round_context=context,
        )

        payload = json.loads(client.responses.calls[0]["input"])
        self.assertEqual(payload["prior_issue_ids"], ["prior-issue"])
        self.assertEqual(payload["prior_open_issues"][0]["description"], prior.description)
        self.assertEqual(output.critique_issues[0].resolution_status, CritiqueIssueStatus.RESOLVED)

    def test_prior_issue_ids_without_details_fail_before_provider_invocation(self):
        plan = _company_plan()
        for context in (
            SemanticRoundContext(
                round_number=1,
                prior_issue_ids=("prior-issue",),
            ),
            SemanticRoundContext.model_construct(
                round_number=1,
                prior_issue_ids=("prior-issue", "another-issue"),
                prior_issues=(_issue("prior-issue"),),
            ),
        ):
            with self.subTest(context=context):
                client = FakeClient()
                critic = OpenAISemanticCritic(client=client, config=_config())
                with self.assertRaisesRegex(
                    OpenAISemanticCriticError,
                    "openai_semantic_critic_prior_issue_details_missing",
                ):
                    critic.evaluate(
                        plan=plan,
                        claims=(),
                        stage1_report=_stage1(),
                        round_context=context,
                    )
                self.assertEqual(len(client.responses.calls), 0)

    def test_non_prefetched_retrieval_mode_is_rejected(self):
        config = _config().model_copy(update={"retrieval_mode": "tool_calling"})
        with self.assertRaisesRegex(
            OpenAISemanticCriticError,
            "openai_semantic_critic_retrieval_mode_invalid",
        ):
            OpenAISemanticCritic(client=FakeClient(), config=config)

    def test_prior_issue_rename_or_disappearance_fails_closed(self):
        plan = _company_plan()
        prior = _issue("prior-issue")
        context = SemanticRoundContext(
            round_number=1,
            prior_issue_ids=(prior.issue_id,),
            prior_issues=(prior,),
        )
        critic, client = self._critic_with(_result(plan, "placeholder"))
        renamed = _result(
            plan,
            critic.evaluator_version,
            fulfilled=("R1",),
            issues=(_issue("renamed-issue"),),
        )
        client.responses.responses[0] = FakeResponse(_encoded(renamed))

        with self.assertRaisesRegex(OpenAISemanticCriticError, "prior_issue_accounting_invalid"):
            critic.evaluate(
                plan=plan,
                claims=(),
                stage1_report=_stage1(),
                round_context=context,
            )

    def test_inactive_agent_and_undeclared_link_are_normalized(self):
        plan = _company_plan()
        issue = _issue("inactive", agent="macro")
        critic, client = self._critic_with(_result(plan, "placeholder"))
        client.responses.responses[0] = FakeResponse(
            _encoded(_result(plan, critic.evaluator_version, issues=(issue,)))
        )
        artifact = evaluate_semantic_round(
            critic,
            plan=plan,
            claims=(),
            stage1_report=_stage1(),
            round_context=SemanticRoundContext(round_number=0),
        )
        self.assertEqual(artifact.critic_result.critique_issues[0].affected_agent, "company")

        reconcile = _issue(
            "reconcile",
            action=CritiqueAction.RECONCILE_CROSS_LEVEL,
        )
        client.responses.responses.append(
            FakeResponse(
                _encoded(_result(plan, critic.evaluator_version, issues=(reconcile,)))
            )
        )
        artifact2 = evaluate_semantic_round(
            critic,
            plan=plan,
            claims=(),
            stage1_report=_stage1(),
            round_context=SemanticRoundContext(round_number=0),
        )
        self.assertEqual(
            artifact2.critic_result.critique_issues[0].required_action,
            CritiqueAction.REVISE_CLAIM,
        )

    def test_unknown_claim_requirement_and_link_ids_fail_closed(self):
        plan = _company_plan()
        critic, client = self._critic_with(_result(plan, "placeholder"))
        unknown_claim = _result(
            plan,
            critic.evaluator_version,
            supporting_claim_ids=("unknown-claim",),
        )
        client.responses.responses[0] = FakeResponse(_encoded(unknown_claim))
        with self.assertRaisesRegex(SemanticEvaluationError, "unknown_claim_id"):
            evaluate_semantic_round(
                critic,
                plan=plan,
                claims=(),
                stage1_report=_stage1(),
                round_context=SemanticRoundContext(round_number=0),
            )

        unknown_requirement = _result(
            plan,
            critic.evaluator_version,
            fulfilled=("unknown-requirement",),
        )
        client.responses.responses.append(FakeResponse(_encoded(unknown_requirement)))
        with self.assertRaisesRegex(SemanticEvaluationError, "unknown_requirement_id"):
            evaluate_semantic_round(
                critic,
                plan=plan,
                claims=(),
                stage1_report=_stage1(),
                round_context=SemanticRoundContext(round_number=0),
            )

        linked_plan = build_tcb_macro_analysis_plan(
            DatasetRef(dataset_id="dataset", dataset_snapshot_id="snapshot")
        )
        unknown_link = _result(
            linked_plan,
            critic.evaluator_version,
            link_results=(
                ApplicableLinkResult(
                    link_id="unknown-link",
                    score=0.5,
                    rationale="Unknown link.",
                ),
            ),
        )
        client.responses.responses.append(FakeResponse(_encoded(unknown_link)))
        artifact = evaluate_semantic_round(
            critic,
            plan=linked_plan,
            claims=(),
            stage1_report=_stage1(),
            round_context=SemanticRoundContext(round_number=0),
        )
        self.assertNotIn("unknown-link", [l.link_id for l in artifact.critic_result.applicable_link_results])

    def test_wrong_applicability_is_normalized(self):
        plan = _company_plan()
        critic, client = self._critic_with(_result(plan, "placeholder"))
        result = _result(plan, critic.evaluator_version, cross_applicable=True)
        client.responses.responses[0] = FakeResponse(_encoded(result))
        artifact = evaluate_semantic_round(
            critic,
            plan=plan,
            claims=(),
            stage1_report=_stage1(),
            round_context=SemanticRoundContext(round_number=0),
        )
        cross_dim = next(
            d for d in artifact.critic_result.dimension_scores
            if d.dimension == SemanticDimension.CROSS_LEVEL_INTEGRATION
        )
        self.assertEqual(cross_dim.applicability, SemanticDimensionApplicability.NOT_APPLICABLE)
        self.assertIsNone(cross_dim.score)

    def test_refusal_incomplete_missing_invalid_json_and_invalid_result_fail_closed(self):
        plan = _company_plan()
        cases = (
            (FakeResponse(output=[{"type": "refusal", "refusal": "no"}]), "refused"),
            (FakeResponse("{}", status="incomplete"), "response_incomplete"),
            (FakeResponse(None), "output_missing"),
            (FakeResponse("not-json"), "json_invalid"),
            (FakeResponse("{}"), "result_invalid"),
        )
        for response, expected in cases:
            with self.subTest(expected=expected):
                client = FakeClient([response])
                critic = OpenAISemanticCritic(client=client, config=_config())
                with self.assertRaisesRegex(OpenAISemanticCriticError, expected):
                    critic.evaluate(
                        plan=plan,
                        claims=(),
                        stage1_report=_stage1(),
                        round_context=SemanticRoundContext(round_number=0),
                    )

    def test_critic_accepts_fenced_json_responses(self):
        plan = _company_plan()
        client = FakeClient()
        critic = OpenAISemanticCritic(client=client, config=_config())
        result = _result(plan, critic.evaluator_version)
        encoded = _encoded(result)

        cases = (
            f"```json\n{encoded}\n```",
            f"```\n{encoded}\n```",
            f"```JSON\n{encoded}\n```",
            f"  ```json\n{encoded}\n```  ",
        )
        for output_text in cases:
            with self.subTest(fence=output_text.splitlines()[0]):
                client.responses.responses = [FakeResponse(output_text)]
                eval_result = critic.evaluate(
                    plan=plan,
                    claims=(),
                    stage1_report=_stage1(),
                    round_context=SemanticRoundContext(round_number=0),
                )
                self.assertEqual(eval_result.contract_version, result.contract_version)
                self.assertEqual(eval_result.evaluator_version, result.evaluator_version)

    def test_provider_exception_fails_closed_without_leaking_exception_details(self):
        client = FakeClient(exception=RuntimeError("secret db path /private/file"))
        critic = OpenAISemanticCritic(client=client, config=_config())
        with self.assertRaisesRegex(OpenAISemanticCriticError, "request_failed") as raised:
            critic.evaluate(
                plan=_company_plan(),
                claims=(),
                stage1_report=_stage1(),
                round_context=SemanticRoundContext(round_number=0),
            )
        self.assertNotIn("private", str(raised.exception))
        self.assertNotIn("secret", str(raised.exception))

    def test_adapter_has_no_json_repair_tools_or_gold_storage_dependency(self):
        source = Path(
            "src/thesis_data/openai_semantic_critic.py"
        ).read_text(encoding="utf-8")
        self.assertNotIn("find(\"{\")", source)
        self.assertNotIn("json_repair", source)
        self.assertNotIn("sqlite", source.lower())
        self.assertNotIn("gold", source.lower())
        self.assertNotIn("db_path", source)

    def test_same_instance_does_not_retain_run_specific_issue_state(self):
        plan_a = _company_plan("query-a")
        plan_b = _company_plan("query-b")
        client = FakeClient()
        critic = OpenAISemanticCritic(client=client, config=_config())
        result_a = _result(plan_a, critic.evaluator_version)
        result_b = _result(plan_b, critic.evaluator_version)
        client.responses.responses.extend(
            [FakeResponse(_encoded(result_a)), FakeResponse(_encoded(result_b))]
        )
        critic.evaluate(
            plan=plan_a,
            claims=(),
            stage1_report=_stage1(),
            round_context=SemanticRoundContext(round_number=0),
        )
        critic.evaluate(
            plan=plan_b,
            claims=(),
            stage1_report=_stage1(),
            round_context=SemanticRoundContext(round_number=0),
        )
        self.assertEqual(
            [json.loads(call["input"])["query_id"] for call in client.responses.calls],
            ["query-a", "query-b"],
        )

    def test_revision_state_round_trip_preserves_prior_open_issue_details(self):
        plan = _company_plan()
        policy = AcceptancePolicy(policy_version="test-policy", provisional_threshold=0.75)
        kernel = RevisionWorkflowKernel(
            policy=policy,
            stage1_evaluator=object(),
            semantic_critic=object(),
            revision_executor=None,
        )
        state = kernel.initial_state(
            run_id="round-trip",
            plan=plan,
            claims=(_company_claim(),),
            initial_payload_version="payload-initial",
        )
        issue = _issue("persisted-open")
        state = state.model_copy(
            update={
                "previous_open_issue_ids": (issue.issue_id,),
                "previous_open_issues": (issue,),
            }
        )
        restored = RevisionWorkflowState.model_validate(state.model_dump(mode="json"))
        self.assertEqual(restored.previous_open_issue_ids, ("persisted-open",))
        self.assertEqual(restored.previous_open_issues[0].description, issue.description)

    def test_controller_can_complete_one_open_then_resolved_fake_openai_path(self):
        plan = _company_plan()
        claim = _company_claim()
        client = FakeClient()
        critic = OpenAISemanticCritic(client=client, config=_config())
        first_issue = _issue("resolve-me", affected_requirement_ids=("R1",))
        first = _result(plan, critic.evaluator_version, issues=(first_issue,))
        second = _result(
            plan,
            critic.evaluator_version,
            fulfilled=("R1",),
            issues=(
                _issue(
                    "resolve-me",
                    status=CritiqueIssueStatus.RESOLVED,
                    affected_requirement_ids=("R1",),
                ),
            ),
        )
        client.responses.responses.extend(
            [FakeResponse(_encoded(first)), FakeResponse(_encoded(second))]
        )
        controller = BoundedRevisionController(
            policy=AcceptancePolicy(
                policy_version="controller-test",
                provisional_threshold=0.75,
            ),
            stage1_evaluator=_Stage1Sequence([_stage1(), _stage1()]),
            semantic_critic=critic,
            revision_executor=_RevisionExecutor(claim),
        )

        result = controller.run(
            run_id="openai-fake-controller",
            plan=plan,
            claims=(claim,),
            initial_payload_version="payload-initial",
        )
        self.assertEqual(result.acceptance_state.final_decision.value, "ACCEPT")
        self.assertEqual(len(client.responses.calls), 2)

    def test_controller_rejects_issue_identity_laundering_into_limited_acceptance(self):
        plan = _company_plan("identity-laundering")
        claim = _company_claim()
        client = FakeClient()
        critic = OpenAISemanticCritic(client=client, config=_config())
        first_issue = _issue(
            "I1",
            issue_type=CritiqueIssueType.UNSUPPORTED_CLAIM,
            action=CritiqueAction.REVISE_CLAIM,
            affected_requirement_ids=("R1",),
        )
        second_issue = _issue(
            "I1",
            issue_type=CritiqueIssueType.MISSING_DATA,
            status=CritiqueIssueStatus.UNRESOLVED,
            affected_requirement_ids=("R1",),
            unresolved_reason_code=UnresolvedReasonCode.DATA_UNAVAILABLE,
        )
        client.responses.responses.extend(
            [
                FakeResponse(
                    _encoded(_result(plan, critic.evaluator_version, issues=(first_issue,)))
                ),
                FakeResponse(
                    _encoded(
                        _result(
                            plan,
                            critic.evaluator_version,
                            partial=("R1",),
                            issues=(second_issue,),
                        )
                    )
                ),
            ]
        )
        controller = BoundedRevisionController(
            policy=AcceptancePolicy(policy_version="identity-test", provisional_threshold=0.75),
            stage1_evaluator=_Stage1Sequence([_stage1(), _stage1()]),
            semantic_critic=critic,
            revision_executor=_RevisionExecutor(claim),
        )

        result = controller.run(
            run_id="identity-laundering",
            plan=plan,
            claims=(claim,),
            initial_payload_version="payload-initial",
        )

        self.assertEqual(result.acceptance_state.final_decision.value, "FAIL_ACCEPTANCE")
        self.assertEqual(
            result.terminal_reason,
            "prior_issue_identity_changed:I1:issue_type",
        )
        self.assertNotEqual(
            result.acceptance_state.final_decision.value,
            "ACCEPT_WITH_LIMITATIONS",
        )

    def test_controller_rejects_changed_prior_issue_agent(self):
        plan = _company_plan("identity-agent")
        claim = _company_claim()
        client = FakeClient()
        critic = OpenAISemanticCritic(client=client, config=_config())
        first_issue = _issue(
            "I1",
            affected_requirement_ids=("R1",),
            agent="company",
        )
        second_issue = _issue(
            "I1",
            affected_requirement_ids=("R1",),
            agent="orchestrator",
            status=CritiqueIssueStatus.RESOLVED,
        )
        client.responses.responses.extend(
            [
                FakeResponse(
                    _encoded(_result(plan, critic.evaluator_version, issues=(first_issue,)))
                ),
                FakeResponse(
                    _encoded(
                        _result(
                            plan,
                            critic.evaluator_version,
                            fulfilled=("R1",),
                            issues=(second_issue,),
                        )
                    )
                ),
            ]
        )
        controller = BoundedRevisionController(
            policy=AcceptancePolicy(policy_version="identity-agent-test", provisional_threshold=0.75),
            stage1_evaluator=_Stage1Sequence([_stage1(), _stage1()]),
            semantic_critic=critic,
            revision_executor=_RevisionExecutor(claim),
        )

        result = controller.run(
            run_id="identity-agent",
            plan=plan,
            claims=(claim,),
            initial_payload_version="payload-initial",
            synthesis_summary="The reviewed observation frames the report.",
            synthesis_supporting_claim_ids=(claim.claim_id,),
        )

        self.assertEqual(
            result.terminal_reason,
            "prior_issue_identity_changed:I1:affected_agent",
        )

    def test_controller_rejects_changed_prior_issue_requirements(self):
        plan = _company_two_requirement_plan()
        claim = _company_claim()
        client = FakeClient()
        critic = OpenAISemanticCritic(client=client, config=_config())
        first_issue = _issue(
            "I1",
            affected_requirement_ids=("R2",),
        )
        second_issue = _issue(
            "I1",
            status=CritiqueIssueStatus.UNRESOLVED,
            affected_requirement_ids=("R1",),
            unresolved_reason_code=UnresolvedReasonCode.DATA_UNAVAILABLE,
        )
        client.responses.responses.extend(
            [
                FakeResponse(
                    _encoded(_result(plan, critic.evaluator_version, issues=(first_issue,)))
                ),
                FakeResponse(
                    _encoded(
                        _result(
                            plan,
                            critic.evaluator_version,
                            partial=("R1",),
                            issues=(second_issue,),
                        )
                    )
                ),
            ]
        )
        controller = BoundedRevisionController(
            policy=AcceptancePolicy(policy_version="identity-requirements-test", provisional_threshold=0.75),
            stage1_evaluator=_Stage1Sequence([_stage1(), _stage1()]),
            semantic_critic=critic,
            revision_executor=_RevisionExecutor(claim),
        )

        result = controller.run(
            run_id="identity-requirements",
            plan=plan,
            claims=(claim,),
            initial_payload_version="payload-initial",
        )

        self.assertEqual(
            result.terminal_reason,
            "prior_issue_identity_changed:I1:affected_requirement_ids",
        )

    def test_historical_issue_reuse_after_omission_fails_closed(self):
        plan = _company_plan("historical-identity")

        def results(version):
            return (
                _result(
                    plan,
                    version,
                    fulfilled=("R1",),
                    issues=(
                        _issue(
                            "A",
                            issue_type=CritiqueIssueType.UNSUPPORTED_CLAIM,
                            action=CritiqueAction.REVISE_CLAIM,
                            status=CritiqueIssueStatus.RESOLVED,
                            affected_requirement_ids=("R1",),
                        ),
                        _issue("B", affected_requirement_ids=("R1",)),
                    ),
                ),
                _result(
                    plan,
                    version,
                    fulfilled=("R1",),
                    issues=(
                        _issue(
                            "B",
                            status=CritiqueIssueStatus.RESOLVED,
                            affected_requirement_ids=("R1",),
                        ),
                        _issue("C", affected_requirement_ids=("R1",)),
                    ),
                ),
                _result(
                    plan,
                    version,
                    partial=("R1",),
                    issues=(
                        _issue(
                            "A",
                            affected_requirement_ids=("R1",),
                            status=CritiqueIssueStatus.UNRESOLVED,
                            unresolved_reason_code=UnresolvedReasonCode.DATA_UNAVAILABLE,
                        ),
                        _issue(
                            "C",
                            status=CritiqueIssueStatus.RESOLVED,
                            affected_requirement_ids=("R1",),
                        ),
                    ),
                ),
            )

        result, client = self._run_controller_with_results(
            plan=plan,
            run_id="historical-identity",
            results_builder=results,
        )

        self.assertEqual(
            result.acceptance_state.final_decision.value,
            "FAIL_ACCEPTANCE",
        )
        self.assertEqual(
            result.terminal_reason,
            "historical_issue_identity_changed:A:issue_type",
        )
        self.assertNotEqual(
            result.acceptance_state.final_decision.value,
            "ACCEPT_WITH_LIMITATIONS",
        )
        self.assertEqual(len(client.responses.calls), 3)

    def test_historical_terminal_status_change_after_omission_fails_closed(self):
        plan = _company_plan("historical-terminal-status")

        def results(version):
            return (
                _result(
                    plan,
                    version,
                    fulfilled=("R1",),
                    issues=(
                        _issue(
                            "A",
                            status=CritiqueIssueStatus.RESOLVED,
                            affected_requirement_ids=("R1",),
                        ),
                        _issue("B", affected_requirement_ids=("R1",)),
                    ),
                ),
                _result(
                    plan,
                    version,
                    fulfilled=("R1",),
                    issues=(
                        _issue(
                            "B",
                            status=CritiqueIssueStatus.RESOLVED,
                            affected_requirement_ids=("R1",),
                        ),
                        _issue(
                            "A",
                            status=CritiqueIssueStatus.UNRESOLVED,
                            affected_requirement_ids=("R1",),
                            unresolved_reason_code=UnresolvedReasonCode.DATA_UNAVAILABLE,
                        ),
                    ),
                ),
            )

        result, _ = self._run_controller_with_results(
            plan=plan,
            run_id="historical-terminal-status",
            results_builder=results,
        )

        self.assertEqual(
            result.acceptance_state.final_decision.value,
            "FAIL_ACCEPTANCE",
        )
        self.assertEqual(
            result.terminal_reason,
            "historical_issue_terminal_status_changed:A",
        )

    def test_historical_resolved_issue_can_reappear_with_same_identity_and_status(self):
        plan = _company_plan("historical-terminal-repeat")

        def results(version):
            resolved_a = _issue(
                "A",
                status=CritiqueIssueStatus.RESOLVED,
                affected_requirement_ids=("R1",),
            )
            return (
                _result(
                    plan,
                    version,
                    fulfilled=("R1",),
                    issues=(resolved_a, _issue("B", affected_requirement_ids=("R1",))),
                ),
                _result(
                    plan,
                    version,
                    fulfilled=("R1",),
                    issues=(
                        _issue(
                            "B",
                            status=CritiqueIssueStatus.RESOLVED,
                            affected_requirement_ids=("R1",),
                        ),
                        resolved_a,
                    ),
                ),
            )

        result, _ = self._run_controller_with_results(
            plan=plan,
            run_id="historical-terminal-repeat",
            results_builder=results,
        )

        self.assertEqual(result.acceptance_state.final_decision.value, "ACCEPT")


if __name__ == "__main__":
    unittest.main()
