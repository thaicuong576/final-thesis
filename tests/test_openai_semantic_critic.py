"""Unit tests for markdown code-fenced JSON parsing in OpenAISemanticCritic."""

from __future__ import annotations

import json
from types import SimpleNamespace
import unittest

from thesis_data.openai_semantic_critic import (
    OpenAISemanticCritic,
    _clean_json_text,
    _normalize_critic_output,
)
from thesis_data.provider_config import ProviderExecutionConfig
from tests.test_phase3bd_openai_semantic_critic import (
    FakeClient,
    FakeResponse,
    _company_plan,
    _config,
    _encoded,
    _result,
    _stage1,
)
from thesis_data.semantic_critic import SemanticRoundContext


class OpenAISemanticCriticFencedJsonTests(unittest.TestCase):
    def test_clean_json_text_helper(self) -> None:
        self.assertEqual(_clean_json_text('{"a": 1}'), '{"a": 1}')
        self.assertEqual(_clean_json_text('```json\n{"a": 1}\n```'), '{"a": 1}')
        self.assertEqual(_clean_json_text('```\n{"a": 1}\n```'), '{"a": 1}')
        self.assertEqual(_clean_json_text('```JSON\n{"a": 1}\n```'), '{"a": 1}')
        self.assertEqual(_clean_json_text('  ```json\n{"a": 1}\n```  '), '{"a": 1}')
        self.assertEqual(_clean_json_text('```json {"a": 1} ```'), '{"a": 1}')
        self.assertEqual(
            _clean_json_text('```json\n{"text": "contains ``` fence"}\n```'),
            '{"text": "contains ``` fence"}',
        )

    def test_critic_accepts_fenced_json(self) -> None:
        plan = _company_plan()
        client = FakeClient()
        critic = OpenAISemanticCritic(client=client, config=_config())
        expected = _result(plan, critic.evaluator_version)
        encoded = _encoded(expected)

        # 1. ```json ... ``` markdown fence
        fenced_json = f"```json\n{encoded}\n```"
        client.responses.responses = [FakeResponse(fenced_json)]
        res_json = critic.evaluate(
            plan=plan,
            claims=(),
            stage1_report=_stage1(),
            round_context=SemanticRoundContext(round_number=0),
        )
        self.assertEqual(res_json.contract_version, expected.contract_version)
        self.assertEqual(res_json.evaluator_version, expected.evaluator_version)

        # 2. ``` ... ``` markdown fence without json tag
        fenced_plain = f"```\n{encoded}\n```"
        client.responses.responses = [FakeResponse(fenced_plain)]
        res_plain = critic.evaluate(
            plan=plan,
            claims=(),
            stage1_report=_stage1(),
            round_context=SemanticRoundContext(round_number=0),
        )
        self.assertEqual(res_plain.contract_version, expected.contract_version)
        self.assertEqual(res_plain.evaluator_version, expected.evaluator_version)


class OpenAISemanticCriticNormalizationTests(unittest.TestCase):
    def test_normalize_critic_output_with_alternative_keys(self) -> None:
        raw_decoded = {
            "issues": [
                {
                    "issue_id": "issue-001",
                    "affected_agent": "company_specialist",
                    "status": "OPEN",
                    "severity": "medium",
                    "rationale": "Missing source locator",
                    "affected_requirement_ids": ["req-1"],
                    "affected_claim_ids": ["claim-1"],
                    "target_id": "claim-1",
                    "required_action": "REVISE_CLAIM",
                },
                {
                    "issue_id": "issue-002",
                    "status": "open",
                    "severity": "high",
                    "rationale": "Executive summary refers to undeclared metric",
                    "target_id": "synthesis",
                    "required_action": "revise_claim",
                },
            ],
            "requirement_results": [
                {"requirement_id": "req-1", "status": "fulfilled"},
                {"requirement_id": "req-2", "status": "partially_fulfilled"},
                {"requirement_id": "req-3", "status": "unfulfilled"},
            ],
            "link_results": [
                {
                    "link_id": "link-1",
                    "score": 1.0,
                    "rationale": "Cross-level link evaluated",
                }
            ],
            "dimension_scores": [
                {
                    "dimension": "factual_accuracy",
                    "score": 0.95,
                    "status": "pass",
                    "rationale": "Factual accuracy confirmed",
                },
                {
                    "dimension": "synthesis_integration",
                    "score": 0.90,
                    "status": "pass",
                    "rationale": "Integrated synthesis",
                },
            ],
        }

        normalized = _normalize_critic_output(raw_decoded, "evaluator-v1")

        # 1. Version enforcement
        self.assertEqual(normalized["contract_version"], "structured-critic-result-v1")
        self.assertEqual(normalized["evaluator_version"], "evaluator-v1")

        # 2. Issues normalization
        self.assertNotIn("issues", normalized)
        self.assertIn("critique_issues", normalized)
        self.assertEqual(len(normalized["critique_issues"]), 2)

        issue_1 = normalized["critique_issues"][0]
        self.assertEqual(issue_1["issue_id"], "issue-001")
        self.assertEqual(issue_1["affected_agent"], "company_specialist")
        self.assertEqual(issue_1["resolution_status"], "OPEN")
        self.assertEqual(issue_1["severity"], "MAJOR")
        self.assertEqual(issue_1["description"], "Missing source locator")
        self.assertEqual(issue_1["required_action"], "REVISE_CLAIM")
        self.assertEqual(issue_1["issue_type"], "unsupported_claim")
        self.assertEqual(issue_1["affected_requirement_ids"], ["req-1"])
        self.assertEqual(issue_1["affected_claim_ids"], ["claim-1"])
        self.assertNotIn("status", issue_1)
        self.assertNotIn("rationale", issue_1)
        self.assertNotIn("target_id", issue_1)

        issue_2 = normalized["critique_issues"][1]
        self.assertEqual(issue_2["issue_id"], "issue-002")
        self.assertEqual(issue_2["affected_agent"], "orchestrator")
        self.assertEqual(issue_2["resolution_status"], "OPEN")
        self.assertEqual(issue_2["severity"], "MAJOR")
        self.assertEqual(issue_2["description"], "Executive summary refers to undeclared metric")

        # 3. Requirement results mapping
        self.assertNotIn("requirement_results", normalized)
        self.assertEqual(normalized["fulfilled_requirement_ids"], ["req-1"])
        self.assertEqual(normalized["partially_fulfilled_requirement_ids"], ["req-2"])
        self.assertEqual(normalized["unfulfilled_requirement_ids"], ["req-3"])

        # 4. Link results mapping
        self.assertNotIn("link_results", normalized)
        self.assertEqual(len(normalized["applicable_link_results"]), 1)
        self.assertEqual(normalized["applicable_link_results"][0]["link_id"], "link-1")
        self.assertEqual(normalized["applicable_link_results"][0]["score"], 1.0)
        self.assertEqual(
            normalized["applicable_link_results"][0]["rationale"],
            "Cross-level link evaluated",
        )

        # 5. Dimension scores: all 6 frozen dimensions present, alias mapped, status removed
        self.assertEqual(len(normalized["dimension_scores"]), 6)
        dims = {d["dimension"]: d for d in normalized["dimension_scores"]}
        self.assertEqual(
            set(dims.keys()),
            {
                "groundedness",
                "cross_level_integration",
                "answer_coverage",
                "logical_soundness",
                "uncertainty_limitations",
                "analytical_usefulness",
            },
        )
        self.assertEqual(dims["groundedness"]["score"], 0.95)
        self.assertEqual(dims["groundedness"]["rationale"], "Factual accuracy confirmed")
        self.assertNotIn("status", dims["groundedness"])
        self.assertEqual(dims["cross_level_integration"]["score"], 0.90)

        # 6. Pydantic validation cleanly succeeds
        from thesis_data.semantic_evaluation import StructuredCriticResult
        validated = StructuredCriticResult.model_validate(normalized)
        self.assertEqual(validated.contract_version, "structured-critic-result-v1")
        self.assertEqual(validated.evaluator_version, "evaluator-v1")
        self.assertEqual(len(validated.dimension_scores), 6)
        self.assertEqual(len(validated.critique_issues), 2)

    def test_critic_evaluate_end_to_end_with_alternative_model_output(self) -> None:
        plan = _company_plan()
        client = FakeClient()
        critic = OpenAISemanticCritic(client=client, config=_config())

        alternative_response = json.dumps({
            "issues": [
                {
                    "issue_id": "issue-deepseek-1",
                    "affected_agent": "company_specialist",
                    "status": "OPEN",
                    "severity": "medium",
                    "rationale": "Citation missing for observed metric",
                    "target_id": "TCB:2024_Q4:bank.roa",
                    "required_action": "REVISE_CLAIM",
                }
            ],
            "requirement_results": [
                {"requirement_id": "R1", "status": "fulfilled"},
            ],
            "link_results": [],
            "dimension_scores": [
                {
                    "dimension": "source_grounding",
                    "score": 0.9,
                    "status": "pass",
                    "rationale": "Grounding acceptable",
                }
            ],
        })

        client.responses.responses = [FakeResponse(alternative_response)]
        res = critic.evaluate(
            plan=plan,
            claims=(),
            stage1_report=_stage1(),
            round_context=SemanticRoundContext(round_number=0),
        )

        self.assertEqual(res.contract_version, "structured-critic-result-v1")
        self.assertEqual(res.evaluator_version, critic.evaluator_version)
        self.assertEqual(len(res.dimension_scores), 6)
        self.assertEqual(len(res.critique_issues), 1)
        self.assertEqual(res.critique_issues[0].issue_id, "issue-deepseek-1")
        self.assertEqual(res.critique_issues[0].severity, "MAJOR")
        self.assertEqual(res.fulfilled_requirement_ids, ("R1",))

    def test_normalize_critic_output_missing_dimensions_and_defaults(self) -> None:
        raw_decoded = {
            "contract_version": "wrong-version",
            "evaluator_version": "",
            "issues": [
                {
                    "affected_agent": "",
                    "target_id": "",
                    "rationale": "Something went wrong",
                }
            ],
            "requirement_results": [],
        }

        normalized = _normalize_critic_output(raw_decoded, "expected-eval-v2")

        self.assertEqual(normalized["contract_version"], "structured-critic-result-v1")
        self.assertEqual(normalized["evaluator_version"], "expected-eval-v2")

        # Missing dimensions: all 6 populated with score 1.0, rationale "Evaluated."
        self.assertEqual(len(normalized["dimension_scores"]), 6)
        for dim in normalized["dimension_scores"]:
            self.assertEqual(dim["score"], 1.0)
            self.assertEqual(dim["rationale"], "Evaluated.")
            self.assertEqual(dim["applicability"], "APPLICABLE")
            self.assertEqual(dim["supporting_claim_ids"], [])
            self.assertEqual(dim["affected_requirement_ids"], [])
            self.assertEqual(dim["issue_ids"], [])
            self.assertNotIn("status", dim)

        # Issue defaults
        self.assertEqual(len(normalized["critique_issues"]), 1)
        issue = normalized["critique_issues"][0]
        self.assertEqual(issue["issue_id"], "issue_1")
        self.assertEqual(issue["affected_agent"], "company_specialist")
        self.assertEqual(issue["issue_type"], "unsupported_claim")
        self.assertEqual(issue["severity"], "MAJOR")
        self.assertEqual(issue["description"], "Something went wrong")
        self.assertEqual(issue["required_action"], "REVISE_CLAIM")
        self.assertEqual(issue["resolution_status"], "OPEN")
        self.assertEqual(issue["affected_claim_ids"], [])
        self.assertEqual(issue["affected_requirement_ids"], [])
        self.assertEqual(issue["evidence_refs"], [])

        # Requirements and links defaults
        self.assertEqual(normalized["fulfilled_requirement_ids"], [])
        self.assertEqual(normalized["partially_fulfilled_requirement_ids"], [])
        self.assertEqual(normalized["unfulfilled_requirement_ids"], [])
        self.assertEqual(normalized["applicable_link_results"], [])

        from thesis_data.semantic_evaluation import StructuredCriticResult
        validated = StructuredCriticResult.model_validate(normalized)
        self.assertEqual(validated.contract_version, "structured-critic-result-v1")
        self.assertEqual(validated.evaluator_version, "expected-eval-v2")

    def test_normalize_critic_output_preserves_valid_output(self) -> None:
        valid_input = {
            "contract_version": "structured-critic-result-v1",
            "evaluator_version": "openai-semantic-critic-v1:gpt-5",
            "dimension_scores": [
                {
                    "dimension": dim,
                    "applicability": "APPLICABLE",
                    "score": 0.85,
                    "rationale": f"Valid score for {dim}",
                    "supporting_claim_ids": ["c1"],
                    "affected_requirement_ids": ["r1"],
                    "issue_ids": [],
                }
                for dim in (
                    "groundedness",
                    "cross_level_integration",
                    "answer_coverage",
                    "logical_soundness",
                    "uncertainty_limitations",
                    "analytical_usefulness",
                )
            ],
            "critique_issues": [
                {
                    "issue_id": "i1",
                    "issue_type": "missing_data",
                    "severity": "MINOR",
                    "affected_agent": "company_specialist",
                    "description": "Minor observation issue",
                    "required_action": "REQUERY_DATA",
                    "resolution_status": "OPEN",
                    "affected_claim_ids": ["c1"],
                    "affected_requirement_ids": ["r1"],
                    "evidence_refs": [],
                }
            ],
            "fulfilled_requirement_ids": ["r1"],
            "partially_fulfilled_requirement_ids": [],
            "unfulfilled_requirement_ids": [],
            "applicable_link_results": [
                {
                    "link_id": "l1",
                    "score": 0.95,
                    "rationale": "Link pass",
                    "supporting_claim_ids": ["c1"],
                    "issue_ids": [],
                }
            ],
        }

        normalized = _normalize_critic_output(valid_input, "openai-semantic-critic-v1:gpt-5")
        from thesis_data.semantic_evaluation import StructuredCriticResult
        validated = StructuredCriticResult.model_validate(normalized)
        self.assertEqual(validated.contract_version, "structured-critic-result-v1")
        self.assertEqual(validated.evaluator_version, "openai-semantic-critic-v1:gpt-5")
        self.assertEqual(len(validated.dimension_scores), 6)
        self.assertEqual(len(validated.critique_issues), 1)
        self.assertEqual(validated.critique_issues[0].issue_type.value, "missing_data")
        self.assertEqual(validated.critique_issues[0].severity.value, "MINOR")
        self.assertEqual(len(validated.applicable_link_results), 1)


if __name__ == "__main__":
    unittest.main()
