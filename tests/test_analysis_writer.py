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


class _ChunkedResponses:
    def __init__(
        self,
        chunks: list[str],
        *,
        fail_stream: bool = False,
        fail_after_deltas: int | None = None,
    ) -> None:
        self.chunks = chunks
        self.fail_stream = fail_stream
        self.fail_after_deltas = fail_after_deltas
        self.calls: list[dict] = []

    def create(self, **kwargs):
        self.calls.append(kwargs)
        if kwargs.get("stream"):
            if self.fail_stream:
                raise RuntimeError("Responses stream error simulation")

            def _event_generator():
                for idx, c in enumerate(self.chunks):
                    if self.fail_after_deltas is not None and idx >= self.fail_after_deltas:
                        raise RuntimeError("Simulated mid-stream failure after deltas")
                    yield SimpleNamespace(type="response.output_text.delta", delta=c)
                full_text = "".join(self.chunks)
                yield SimpleNamespace(
                    type="response.completed",
                    response=SimpleNamespace(output_text=full_text, status="completed"),
                )

            return _event_generator()

        full_text = "".join(self.chunks)
        return SimpleNamespace(output_text=full_text, status="completed")


class _ChunkedChatCompletions:
    def __init__(self, chunks: list[str], *, fail_stream: bool = False) -> None:
        self.chunks = chunks
        self.fail_stream = fail_stream
        self.calls: list[dict] = []

    def create(self, **kwargs):
        self.calls.append(kwargs)
        if kwargs.get("stream"):
            if self.fail_stream:
                raise RuntimeError("Stream error simulation")
            return [
                SimpleNamespace(
                    choices=[SimpleNamespace(delta=SimpleNamespace(content=c))]
                )
                for c in self.chunks
            ]
        # Non-streamed response
        full_text = "".join(self.chunks)
        return SimpleNamespace(
            choices=[SimpleNamespace(message=SimpleNamespace(content=full_text))]
        )


class StreamingWriterTests(unittest.TestCase):
    def test_streaming_json_text_extractor_extracts_only_prose(self) -> None:
        from thesis_api.analysis_writer import StreamingJsonTextExtractor

        emitted: list[str] = []
        extractor = StreamingJsonTextExtractor(emitted.append)

        # Feed JSON in arbitrary chunks
        raw_chunks = [
            '{"sentences": [{"text": "ACB ',
            'đạt ROE 21,75%',
            ' trong năm 2024.", "fact_ids": ["fact-1"]}',
            ', {"text": "Tỷ lệ nợ xấu ở mức thấp.", ',
            '"fact_ids": ["fact-2"]}]}',
        ]
        for c in raw_chunks:
            extractor.feed(c)

        full_prose = "".join(emitted)
        self.assertIn("ACB đạt ROE 21,75% trong năm 2024.", full_prose)
        self.assertIn("Tỷ lệ nợ xấu ở mức thấp.", full_prose)
        self.assertNotIn("{", full_prose)
        self.assertNotIn("}", full_prose)
        self.assertNotIn("fact_ids", full_prose)
        self.assertNotIn("fact-1", full_prose)
        self.assertNotIn("sentences", full_prose)

    def test_writer_stream_produces_byte_identical_result_to_non_streamed(self) -> None:
        findings_resp = {
            "sentences": [
                {
                    "text": "ACB đạt ROE 21,75% trong năm 2024.",
                    "fact_ids": ["fact-1"],
                }
            ]
        }
        json_str = json.dumps(findings_resp)
        # Split into 5-char chunks
        chunks = [json_str[i:i+5] for i in range(0, len(json_str), 5)]

        # 1. Non-streamed
        client_non_stream = SimpleNamespace(
            chat=SimpleNamespace(completions=_ChunkedChatCompletions(chunks))
        )
        writer_non_stream = OpenAIAnalysisWriter(client=client_non_stream, model="test-model")
        facts = [{"fact_id": "fact-1", "mo_ta": "ROE", "hien_thi": "21,75%"}]
        res_non_stream = writer_non_stream.write_findings(
            role="company",
            question="Đánh giá ACB?",
            question_type="lookup",
            facts=facts,
            datasets_summary=[],
        )

        # 2. Streamed with on_delta
        deltas: list[str] = []
        client_stream = SimpleNamespace(
            chat=SimpleNamespace(completions=_ChunkedChatCompletions(chunks))
        )
        writer_stream = OpenAIAnalysisWriter(client=client_stream, model="test-model")
        res_stream = writer_stream.write_findings(
            role="company",
            question="Đánh giá ACB?",
            question_type="lookup",
            facts=facts,
            datasets_summary=[],
            on_delta=deltas.append,
        )

        # Parsed output must be identical
        self.assertEqual(res_stream, res_non_stream)
        # on_delta must have been called
        self.assertGreater(len(deltas), 0)
        streamed_text = "".join(deltas)
        self.assertIn("ACB đạt ROE 21,75% trong năm 2024.", streamed_text)
        self.assertNotIn("{", streamed_text)
        self.assertNotIn("fact_ids", streamed_text)

    def test_writer_streaming_failure_falls_back_silently_to_non_stream(self) -> None:
        findings_resp = {"sentences": [{"text": "Fallback text", "fact_ids": ["f1"]}]}
        json_str = json.dumps(findings_resp)
        chunks = [json_str]

        # Fails when stream=True is requested
        client_failing_stream = SimpleNamespace(
            chat=SimpleNamespace(completions=_ChunkedChatCompletions(chunks, fail_stream=True))
        )
        writer = OpenAIAnalysisWriter(client=client_failing_stream, model="test-model")
        deltas: list[str] = []
        res = writer.write_findings(
            role="company",
            question="q",
            question_type="lookup",
            facts=[{"fact_id": "f1", "mo_ta": "m", "hien_thi": "1"}],
            datasets_summary=[],
            on_delta=deltas.append,
        )
        # Seamlessly falls back and succeeds
        self.assertEqual(res[0]["text"], "Fallback text")

    def test_writer_responses_streaming_produces_identical_result_and_emits_deltas(self) -> None:
        findings_resp = {
            "sentences": [
                {
                    "text": "VCB có tỷ lệ bao phủ nợ xấu đạt 279,3% trong quý 2/2026.",
                    "fact_ids": ["fact-vcb-1"],
                }
            ]
        }
        json_str = json.dumps(findings_resp)
        chunks = [json_str[i:i+6] for i in range(0, len(json_str), 6)]

        # 1. Non-streamed call with a client that HAS .responses
        client_non_stream = SimpleNamespace(
            responses=_ChunkedResponses(chunks)
        )
        writer_non_stream = OpenAIAnalysisWriter(client=client_non_stream, model="test-model")
        facts = [{"fact_id": "fact-vcb-1", "mo_ta": "LLR", "hien_thi": "279,3%"}]
        res_non_stream = writer_non_stream.write_findings(
            role="company",
            question="Xếp hạng nợ xấu?",
            question_type="ranking",
            facts=facts,
            datasets_summary=[],
        )

        # 2. Streamed call with a client that HAS .responses
        deltas: list[str] = []
        client_stream = SimpleNamespace(
            responses=_ChunkedResponses(chunks)
        )
        writer_stream = OpenAIAnalysisWriter(client=client_stream, model="test-model")
        res_stream = writer_stream.write_findings(
            role="company",
            question="Xếp hạng nợ xấu?",
            question_type="ranking",
            facts=facts,
            datasets_summary=[],
            on_delta=deltas.append,
        )

        # Assertions
        self.assertEqual(res_stream, res_non_stream)
        self.assertGreater(len(deltas), 0)
        streamed_text = "".join(deltas)
        self.assertIn("VCB có tỷ lệ bao phủ nợ xấu đạt 279,3% trong quý 2/2026.", streamed_text)
        self.assertNotIn("{", streamed_text)
        self.assertNotIn("fact_ids", streamed_text)

    def test_writer_responses_streaming_failure_discards_draft_and_records_retry(self) -> None:
        findings_resp = {
            "sentences": [
                {
                    "text": "VCB dẫn đầu sau khi thử lại.",
                    "fact_ids": ["fact-1"],
                }
            ]
        }
        json_str = json.dumps(findings_resp)
        chunks = [json_str[i:i+5] for i in range(0, len(json_str), 5)]

        # Fails after emitting text chunks (so deltas WERE emitted)
        client_failing = SimpleNamespace(
            responses=_ChunkedResponses(chunks, fail_after_deltas=7)
        )
        writer = OpenAIAnalysisWriter(client=client_failing, model="test-model")
        deltas: list[str] = []
        discard_called = []

        res = writer.write_findings(
            role="company",
            question="q",
            question_type="ranking",
            facts=[{"fact_id": "fact-1", "mo_ta": "m", "hien_thi": "1"}],
            datasets_summary=[],
            on_delta=deltas.append,
            on_discard=lambda: discard_called.append(True),
        )

        # Deltas were emitted before the failure
        self.assertGreater(len(deltas), 0)
        # Discard callback was invoked
        self.assertEqual(len(discard_called), 1)
        # Retry was recorded
        self.assertEqual(writer.retry_count, 1)
        self.assertEqual(len(writer.retries), 1)
        # Fallback non-streamed succeeded
        self.assertEqual(res[0]["text"], "VCB dẫn đầu sau khi thử lại.")


if __name__ == "__main__":
    unittest.main()


class InlineFactReferenceStrippingTests(unittest.TestCase):
    """Model prose must not show fact identifiers; citations live in fact_ids."""

    def test_strips_parenthesised_bracketed_and_bare_fact_ids_from_text_only(self) -> None:
        from thesis_api.analysis_writer import _strip_inline_fact_refs

        raw = {
            "blocks": [
                {"text": "Tổng mức tăng cả năm đạt +3,3 điểm %. (fact:delta:VPB:2024_Q1_to_2024_Q4:bank.roe)",
                 "fact_ids": ["fact:delta:VPB:2024_Q1_to_2024_Q4:bank.roe"]},
                {"text": "Khoảng cách thu hẹp (fact:a:1, fact:b:2), dù VPB xếp hạng 5/5."},
                {"text": "ROE 21,7% [fact:value:ACB:2024_Q4:bank.roe] cao hơn trung vị."},
            ]
        }
        out = _strip_inline_fact_refs(raw)
        self.assertEqual(out["blocks"][0]["text"], "Tổng mức tăng cả năm đạt +3,3 điểm %.")
        self.assertEqual(out["blocks"][0]["fact_ids"], ["fact:delta:VPB:2024_Q1_to_2024_Q4:bank.roe"])
        self.assertEqual(out["blocks"][1]["text"], "Khoảng cách thu hẹp, dù VPB xếp hạng 5/5.")
        self.assertEqual(out["blocks"][2]["text"], "ROE 21,7% cao hơn trung vị.")
