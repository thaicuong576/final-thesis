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


class OpenAIAnalysisWriterTests(unittest.TestCase):
    def test_writer_methods_contract(self) -> None:
        findings_resp = {
            "sentences": [
                {
                    "text": "ACB đạt ROE 21,75% trong năm 2024.",
                    "fact_ids": ["fact-1"],
                }
            ]
        }
        compose_resp = {
            "kind": "note",
            "blocks": [
                {
                    "type": "headline",
                    "headline": "ACB: Hiệu quả sinh lời dẫn đầu",
                },
                {
                    "type": "takeaway",
                    "text": "ACB đạt ROE 21,75% trong năm 2024.",
                    "fact_ids": ["fact-1"],
                },
            ],
        }
        rewrite_resp = {
            "text": "ACB ghi nhận ROE ở mức 21,75%, cao hơn trung vị ngành.",
            "fact_ids": ["fact-1", "fact-2"],
        }

        fake = _FakeResponses([
            json.dumps(findings_resp),
            json.dumps(compose_resp),
            json.dumps(rewrite_resp),
        ])
        writer = OpenAIAnalysisWriter(client=SimpleNamespace(responses=fake), model="test-model")

        facts = [
            {"fact_id": "fact-1", "mo_ta": "ROE 2024", "hien_thi": "21,75%"},
            {"fact_id": "fact-2", "mo_ta": "Trung vị ROE", "hien_thi": "18,50%"},
        ]
        datasets = [{"dataset_id": "ds-1", "title": "ROE Dataset", "allowed_charts": ["bar"]}]

        # 1. write_findings
        findings = writer.write_findings(
            role="company",
            question="Đánh giá hiệu quả kinh doanh của ACB năm 2024?",
            question_type="company_profile",
            facts=facts,
            datasets_summary=datasets,
        )
        self.assertEqual(len(findings), 1)
        self.assertEqual(findings[0]["text"], "ACB đạt ROE 21,75% trong năm 2024.")
        self.assertEqual(findings[0]["fact_ids"], ["fact-1"])
        self.assertIn("doanh nghiệp", fake.calls[0]["instructions"])

        # 2. compose_report
        spec = writer.compose_report(
            question="Đánh giá hiệu quả kinh doanh của ACB năm 2024?",
            question_type="company_profile",
            sentences=[{"sentence_id": "s1", "text": findings[0]["text"], "fact_ids": ["fact-1"]}],
            datasets_summary=datasets,
            facts=facts,
        )
        self.assertEqual(spec["kind"], "note")
        self.assertEqual(len(spec["blocks"]), 2)
        self.assertIn("điều phối viên", fake.calls[1]["instructions"])

        # 3. rewrite_sentence
        rewritten = writer.rewrite_sentence(
            role="company",
            question="Đánh giá hiệu quả kinh doanh của ACB năm 2024?",
            sentence={"text": findings[0]["text"], "fact_ids": ["fact-1"]},
            issue={
                "description": "Cần so sánh thêm với trung vị ngành.",
                "required_action": "REVISE_CLAIM",
            },
            facts=facts,
        )
        self.assertEqual(rewritten["text"], "ACB ghi nhận ROE ở mức 21,75%, cao hơn trung vị ngành.")
        self.assertEqual(rewritten["fact_ids"], ["fact-1", "fact-2"])

    def test_writer_rejects_malformed_responses(self) -> None:
        malformed = _FakeResponses(["not-json"])
        writer = OpenAIAnalysisWriter(client=SimpleNamespace(responses=malformed), model="test-model")
        with self.assertRaisesRegex(AnalysisWriterError, "analysis_writer_json_invalid"):
            writer.write_findings(
                role="company",
                question="q",
                question_type="lookup",
                facts=[],
                datasets_summary=[],
            )

        incomplete = _FakeResponses(["{}"], statuses=["incomplete"])
        writer2 = OpenAIAnalysisWriter(client=SimpleNamespace(responses=incomplete), model="test-model")
        with self.assertRaisesRegex(AnalysisWriterError, "analysis_writer_response_incomplete"):
            writer2.write_findings(
                role="company",
                question="q",
                question_type="lookup",
                facts=[],
                datasets_summary=[],
            )

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
        findings_resp = {"sentences": [{"text": "Fenced text", "fact_ids": ["f1"]}]}
        fenced_json = f"```json\n{json.dumps(findings_resp)}\n```"
        fake_json = _FakeResponses([fenced_json])
        writer_json = OpenAIAnalysisWriter(client=SimpleNamespace(responses=fake_json), model="test-model")

        res = writer_json.write_findings(
            role="company",
            question="q",
            question_type="lookup",
            facts=[{"fact_id": "f1", "mo_ta": "m", "hien_thi": "1"}],
            datasets_summary=[],
        )
        self.assertEqual(res[0]["text"], "Fenced text")


if __name__ == "__main__":
    unittest.main()
