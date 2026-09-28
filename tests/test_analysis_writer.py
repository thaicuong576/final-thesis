"""Offline contract tests for the production Responses writer adapter."""

from __future__ import annotations

import json
import unittest
from types import SimpleNamespace

from thesis_api.analysis_writer import (
    AnalysisWriterError,
    OpenAIAnalysisWriter,
    _clean_json_text,
)


class _FakeResponses:
    def __init__(self, outputs: list[str], *, statuses: list[str | None] | None = None) -> None:
        self.outputs = list(outputs)
        self.statuses = list(statuses or ["completed"] * len(outputs))
        self.calls: list[dict] = []

    def create(self, **kwargs):
        self.calls.append(kwargs)
        output = self.outputs.pop(0)
        status = self.statuses.pop(0)
        return SimpleNamespace(output_text=output, status=status)


def _claim(claim_id: str) -> dict:
    return {
        "claim_id": claim_id,
        "capability": "company",
        "display_name": "ROE",
        "claim": {"claim_id": claim_id, "claim_text": "Accepted provider statement."},
        "accepted_observation": {"observation_id": f"obs-{claim_id}", "value": 17.25},
        "primary_sources": [],
    }


class OpenAIAnalysisWriterTests(unittest.TestCase):
    def test_role_writer_forwards_exact_revision_issue_and_synthesis_support(self) -> None:
        claim_id = "claim-a"
        initial = {
            "claim_texts": [{
                "claim_id": claim_id,
                "prose": "A grounded statement stays within this accepted claim and its scope.",
                "supporting_claim_ids": [claim_id],
            }],
        }
        revised = {
            "claim_texts": [{
                "claim_id": claim_id,
                "prose": "The specialist responds to the selected review action with grounded wording.",
                "supporting_claim_ids": [claim_id],
            }],
        }
        synthesized = {
            "summary": "The reviewed specialist outputs remain within the frozen scope and accepted evidence.",
            "supporting_claim_ids": [claim_id],
        }
        fake = _FakeResponses([json.dumps(initial), json.dumps(revised), json.dumps(synthesized)])
        writer = OpenAIAnalysisWriter(client=SimpleNamespace(responses=fake), model="test-model")
        plan = {"plan_version": "plan-v1", "scope": {"periods": ["2024_Q4"]}}
        claim = _claim(claim_id)

        first = writer.write_specialist(plan=plan, role="company", claims=[claim], issues=[])
        issue = {
            "issue_id": "review-7",
            "issue_type": "unsupported_claim",
            "severity": "MAJOR",
            "affected_agent": "company",
            "affected_claim_ids": [claim_id],
            "affected_requirement_ids": ["company:ACB:2024_Q4:bank.roe"],
            "description": "Clarify the accepted scope for this claim.",
            "required_action": "REVISE_CLAIM",
        }
        second = writer.write_specialist(plan=plan, role="company", claims=[claim], issues=[issue])
        summary = writer.synthesize(
            plan=plan,
            specialist_outputs={"company": [{"claim_id": claim_id, "prose": second[claim_id]["prose"]}]},
            issues=[issue],
        )

        self.assertEqual(first[claim_id]["supporting_claim_ids"], [claim_id])
        self.assertNotEqual(first[claim_id]["prose"], second[claim_id]["prose"])
        revision_payload = json.loads(fake.calls[1]["input"])
        self.assertEqual(revision_payload["role"], "company")
        self.assertEqual(revision_payload["claims"][0]["claim_id"], claim_id)
        self.assertEqual(revision_payload["selected_issues"], [issue])
        self.assertEqual(summary["supporting_claim_ids"], [claim_id])
        self.assertEqual(json.loads(fake.calls[2]["input"])["selected_issues"], [issue])
        self.assertEqual(fake.calls[0]["text"]["format"]["type"], "json_schema")
        self.assertTrue(fake.calls[0]["text"]["format"]["strict"])
        self.assertFalse(fake.calls[0]["store"])
        self.assertIn("CRITICAL CONSTRAINTS FOR PROSE:", fake.calls[0]["instructions"])
        self.assertIn("NEVER mention any year", fake.calls[0]["instructions"])
        self.assertIn("NUMERIC CONSTRAINTS FOR PROSE:", fake.calls[0]["instructions"])
        self.assertIn("write the EXACT asserted value verbatim", fake.calls[0]["instructions"])
        self.assertIn("CRITICAL CONSTRAINTS FOR SUMMARY:", fake.calls[2]["instructions"])
        self.assertIn("NEVER include any ticker symbols", fake.calls[2]["instructions"])
        self.assertIn("NEVER include digits, numbers, or spelled-out number words", fake.calls[2]["instructions"])
        self.assertIn("NEVER write any years, quarters, dates, or period labels", fake.calls[2]["instructions"])

    def test_writer_rejects_malformed_responses_and_out_of_scope_support(self) -> None:
        claim = _claim("claim-a")
        plan = {"plan_version": "plan-v1"}

        malformed = _FakeResponses(["not-json"])
        writer = OpenAIAnalysisWriter(client=SimpleNamespace(responses=malformed), model="test-model")
        with self.assertRaisesRegex(AnalysisWriterError, "analysis_writer_json_invalid"):
            writer.write_specialist(plan=plan, role="company", claims=[claim], issues=[])

        out_of_scope = _FakeResponses([json.dumps({
            "claim_texts": [{
                "claim_id": "claim-a",
                "prose": "This wording attempts to cite an unrelated claim in its support.",
                "supporting_claim_ids": ["claim-b"],
            }],
        })])
        writer = OpenAIAnalysisWriter(client=SimpleNamespace(responses=out_of_scope), model="test-model")
        with self.assertRaisesRegex(AnalysisWriterError, "analysis_writer_specialist_support_scope_invalid"):
            writer.write_specialist(plan=plan, role="company", claims=[claim], issues=[])

        bad_synthesis = _FakeResponses([json.dumps({
            "summary": "The summary attempts to cite a claim outside its accepted inputs.",
            "supporting_claim_ids": ["claim-b"],
        })])
        writer = OpenAIAnalysisWriter(client=SimpleNamespace(responses=bad_synthesis), model="test-model")
        with self.assertRaisesRegex(AnalysisWriterError, "analysis_writer_synthesis_support_scope_invalid"):
            writer.synthesize(
                plan=plan,
                specialist_outputs={"company": [{"claim_id": "claim-a", "prose": "Grounded claim prose."}]},
                issues=[],
            )

        incomplete = _FakeResponses(["{}"], statuses=["incomplete"])
        writer = OpenAIAnalysisWriter(client=SimpleNamespace(responses=incomplete), model="test-model")
        with self.assertRaisesRegex(AnalysisWriterError, "analysis_writer_response_incomplete"):
            writer.write_specialist(plan=plan, role="company", claims=[claim], issues=[])

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

    def test_writer_accepts_fenced_json_responses(self) -> None:
        claim_id = "claim-a"
        claim = _claim(claim_id)
        plan = {"plan_version": "plan-v1", "scope": {"periods": ["2024_Q4"]}}
        specialist_payload = {
            "claim_texts": [{
                "claim_id": claim_id,
                "prose": "Clean grounded prose.",
                "supporting_claim_ids": [claim_id],
            }],
        }
        synthesis_payload = {
            "summary": "Clean synthesis summary.",
            "supporting_claim_ids": [claim_id],
        }

        # Case 1: ```json ... ``` code fence
        fenced_json_specialist = f"```json\n{json.dumps(specialist_payload)}\n```"
        fenced_json_synthesis = f"```json\n{json.dumps(synthesis_payload)}\n```"
        fake_json = _FakeResponses([fenced_json_specialist, fenced_json_synthesis])
        writer_json = OpenAIAnalysisWriter(client=SimpleNamespace(responses=fake_json), model="test-model")

        res_spec = writer_json.write_specialist(plan=plan, role="company", claims=[claim], issues=[])
        self.assertEqual(res_spec[claim_id]["prose"], "Clean grounded prose.")

        res_synth = writer_json.synthesize(
            plan=plan,
            specialist_outputs={"company": [{"claim_id": claim_id, "prose": "Clean grounded prose."}]},
            issues=[],
        )
        self.assertEqual(res_synth["summary"], "Clean synthesis summary.")

        # Case 2: ``` ... ``` code fence without json tag
        fenced_plain_specialist = f"```\n{json.dumps(specialist_payload)}\n```"
        fenced_plain_synthesis = f"```\n{json.dumps(synthesis_payload)}\n```"
        fake_plain = _FakeResponses([fenced_plain_specialist, fenced_plain_synthesis])
        writer_plain = OpenAIAnalysisWriter(client=SimpleNamespace(responses=fake_plain), model="test-model")

        res_spec_plain = writer_plain.write_specialist(plan=plan, role="company", claims=[claim], issues=[])
        self.assertEqual(res_spec_plain[claim_id]["prose"], "Clean grounded prose.")

        res_synth_plain = writer_plain.synthesize(
            plan=plan,
            specialist_outputs={"company": [{"claim_id": claim_id, "prose": "Clean grounded prose."}]},
            issues=[],
        )
        self.assertEqual(res_synth_plain["summary"], "Clean synthesis summary.")


if __name__ == "__main__":
    unittest.main()
