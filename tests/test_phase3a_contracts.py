import unittest

from pydantic import ValidationError

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
from thesis_data.schema import (
    AssertionOperator,
    AssertionType,
    AtomicClaim,
    ClaimDataRef,
    ClaimScope,
    HardGateResult,
    InferenceType,
    Stage1ValidationReport,
    StructuredAssertion,
)
from thesis_data.semantic_evaluation import (
    ApplicableLinkResult,
    SemanticContractError,
    SemanticDimension,
    SemanticDimensionResult,
    StructuredCriticResult,
    validate_structured_critic_result,
)


def _minimal_plan(
    *,
    requirement: AnalysisRequirement | None = None,
) -> AnalysisPlan:
    requirement = requirement or AnalysisRequirement(
        requirement_id="R1",
        requirement_type=RequirementType.FACTUAL_OBSERVATION,
        description="Report the observation.",
        required_agents=(AnalysisAgent.MACRO,),
        entities=("VN",),
        periods=("2024_Q4",),
        metric_ids=("macro.credit_growth",),
        inference_ceiling=InferenceCeiling.OBSERVATION_ONLY,
        fulfillment_policy=FulfillmentPolicy.VALUE_OR_ACCEPTED_MISSINGNESS,
        missing_data_policy=MissingDataPolicy.ACCEPTED_GOLD_MISSINGNESS,
    )
    return AnalysisPlan(
        plan_version=ANALYSIS_PLAN_VERSION,
        query_id="test-query",
        normalized_question="Report the observation.",
        scope=AnalysisScope(
            entities=("VN",),
            periods=("2024_Q4",),
            macro_indicator_ids=("macro.credit_growth",),
        ),
        requirements=(requirement,),
        requested_outputs=("structured_facts",),
        causal_claim_policy=CausalClaimPolicy.ASSOCIATION_ONLY,
    )


def _missing_claim() -> AtomicClaim:
    reference = ClaimDataRef(
        ref_id="macro-credit-growth-missing",
        ref_type="macro_observation",
        entity="VN",
        period="2024_Q4",
        metric_id="macro.credit_growth",
    )
    assertion = StructuredAssertion(
        assertion_id="a1",
        assertion_type=AssertionType.MISSINGNESS,
        entity="VN",
        period="2024_Q4",
        metric_id="macro.credit_growth",
        operator=AssertionOperator.MISSING,
        data_refs=(reference,),
    )
    return AtomicClaim(
        claim_id="claim-macro-credit-missing",
        claim_text="System credit growth is unavailable for 2024_Q4.",
        claim_type="factual",
        title="Credit-growth missingness",
        interpretation="The unavailable observation is disclosed.",
        limitation="No value is fabricated.",
        scope=ClaimScope(
            entities=("VN",),
            periods=("2024_Q4",),
            metric_ids=("macro.credit_growth",),
        ),
        assertions=(assertion,),
        inference_type=InferenceType.FACT,
    )


def _passing_stage1() -> Stage1ValidationReport:
    gates = {
        gate_id: HardGateResult(
            gate_id=gate_id,
            passed=True,
            rate=0.0,
            required_rate=0.0,
            evaluation_unit="test",
            evaluated_count=0,
            passed_count=0,
        )
        for gate_id in (
            "numeric_accuracy",
            "reference_validity",
            "critical_evidence_coverage",
            "scope_compliance",
            "fabricated_or_unaccepted_records",
            "blocking_contradictions",
        )
    }
    return Stage1ValidationReport(passed=True, gate_results=gates)


def _result(
    *,
    requirement_ids=("R1",),
    claims=("claim-macro-credit-missing",),
    link_results=(),
) -> StructuredCriticResult:
    dimensions = tuple(
        SemanticDimensionResult(
            dimension=dimension,
            score=1.0,
            rationale="deterministic test rationale",
            supporting_claim_ids=claims,
            affected_requirement_ids=requirement_ids,
        )
        for dimension in SemanticDimension
    )
    return StructuredCriticResult(
        evaluator_version="future-critic-v1",
        dimension_scores=dimensions,
        fulfilled_requirement_ids=requirement_ids,
        applicable_link_results=link_results,
    )


class Phase3AContractTests(unittest.TestCase):
    def test_valid_analysis_plan_construction(self):
        plan = _minimal_plan()

        self.assertEqual(plan.plan_version, ANALYSIS_PLAN_VERSION)
        self.assertEqual(plan.scope.macro_indicator_ids, ("macro.credit_growth",))

    def test_duplicate_requirement_ids_fail(self):
        plan = _minimal_plan()
        payload = plan.model_dump(mode="python")
        requirement = plan.requirements[0].model_dump(mode="python")
        payload["requirements"] = (requirement, requirement)

        with self.assertRaisesRegex(ValueError, "duplicate requirement IDs"):
            AnalysisPlan(**payload)

    def test_frozen_tcb_macro_question_has_expected_requirements(self):
        plan = build_tcb_macro_analysis_plan()

        self.assertEqual(plan.query_id, "TCB_macro_to_bank_q4")
        self.assertEqual(
            {item.requirement_id for item in plan.requirements},
            {"R1", "R2", "R3", "R4", "R5", "R6", "R7"},
        )
        self.assertEqual(plan.causal_claim_policy, CausalClaimPolicy.ASSOCIATION_ONLY)
        self.assertEqual(plan.scope.macro_indicator_ids, (
            "macro.policy_rate",
            "macro.credit_growth",
        ))
        self.assertEqual(plan.scope.company_metric_ids, ("bank.roa", "bank.roe"))
        self.assertEqual(plan.applicable_links[0].link_id, "L1")

    def test_credit_growth_accepted_missingness_is_permitted(self):
        plan = _minimal_plan()
        result = _result()

        validate_structured_critic_result(
            plan,
            result,
            (_missing_claim(),),
            stage1_report=_passing_stage1(),
        )

    def test_unavailable_credit_growth_needs_no_fabricated_numeric_value(self):
        claim = _missing_claim()

        self.assertIsNone(claim.assertions[0].asserted_value)
        validate_structured_critic_result(
            _minimal_plan(),
            _result(),
            (claim,),
            stage1_report=_passing_stage1(),
        )

    def test_association_only_plan_rejects_causal_inference_ceiling(self):
        plan = build_tcb_macro_analysis_plan()
        payload = plan.model_dump(mode="python")
        requirements = [item.model_dump(mode="python") for item in plan.requirements]
        requirements[4]["inference_ceiling"] = InferenceCeiling.CAUSAL
        payload["requirements"] = tuple(requirements)

        with self.assertRaisesRegex(ValueError, "causal inference ceiling"):
            AnalysisPlan(**payload)

    def test_semantic_score_outside_range_fails(self):
        with self.assertRaises(ValidationError):
            SemanticDimensionResult(
                dimension=SemanticDimension.GROUNDEDNESS,
                score=1.01,
                rationale="invalid",
            )

    def test_critic_unknown_requirement_fails_closed(self):
        result = _result(requirement_ids=("R999",))

        with self.assertRaisesRegex(SemanticContractError, "unknown_requirement_id:R999"):
            validate_structured_critic_result(_minimal_plan(), result, (_missing_claim(),))

    def test_critic_unknown_claim_fails_closed(self):
        result = _result(claims=("claim-unknown",))

        with self.assertRaisesRegex(SemanticContractError, "unknown_claim_id:claim-unknown"):
            validate_structured_critic_result(_minimal_plan(), result, (_missing_claim(),))

    def test_critic_unknown_link_fails_closed(self):
        link_result = ApplicableLinkResult(
            link_id="L999",
            score=1.0,
            rationale="invalid link",
        )
        result = _result(link_results=(link_result,))

        with self.assertRaisesRegex(SemanticContractError, "unknown_link_id:L999"):
            validate_structured_critic_result(_minimal_plan(), result, (_missing_claim(),))


if __name__ == "__main__":
    unittest.main()
