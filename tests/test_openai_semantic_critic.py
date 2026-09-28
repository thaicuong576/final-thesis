"""Unit tests for markdown code-fenced JSON parsing in OpenAISemanticCritic."""

from __future__ import annotations

import unittest
from types import SimpleNamespace

from thesis_data.openai_semantic_critic import (
    OpenAISemanticCritic,
    _clean_json_text,
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


if __name__ == "__main__":
    unittest.main()
