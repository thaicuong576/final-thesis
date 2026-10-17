"""Unit tests for filing LLM row selector with fake client.

Phase: INGEST-6 (D-086).
Tests:
- Successful selection of candidate printed line by LLM
- Deterministic numeric parsing from line text (model never produces numbers)
- Proper tagging with source='llm_assisted_selection' and issue='llm_selected'
- Graceful handling of unknown line_id (ignored, row unchanged)
- Graceful handling of malformed JSON / empty response (ignored, row unchanged)
- No chain-of-thought stored
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
import json
from typing import Any, Optional
import unittest

from thesis_api.filing_llm_selector import refine_candidates_with_llm
from thesis_data.filing_extract import (
    CandidateRow,
    ExtractionResult,
    PageInput,
    RowIssue,
    StatementPages,
)


@dataclass
class FakeMessage:
    content: str


@dataclass
class FakeChoice:
    message: FakeMessage


@dataclass
class FakeUsage:
    total_tokens: int = 150


@dataclass
class FakeCompletion:
    choices: list[FakeChoice]
    usage: FakeUsage


class FakeChatCompletions:
    def __init__(self, responses: list[str]) -> None:
        self.responses = list(responses)
        self.call_count = 0
        self.prompts: list[dict[str, Any]] = []

    def create(self, **kwargs: Any) -> FakeCompletion:
        self.call_count += 1
        self.prompts.append(kwargs)
        if self.responses:
            resp_str = self.responses.pop(0)
        else:
            resp_str = json.dumps({"line_id": None, "reason": "none"})
        return FakeCompletion(
            choices=[FakeChoice(message=FakeMessage(content=resp_str))],
            usage=FakeUsage(total_tokens=120),
        )


class FakeOpenAIClient:
    def __init__(self, responses: list[str]) -> None:
        self.chat = type("Chat", (), {"completions": FakeChatCompletions(responses)})()


class TestFilingLLMSelector(unittest.TestCase):
    def setUp(self) -> None:
        # Sample statement pages: page 1 is loan note with NPL breakdown
        self.note_page_text = (
            "THUYẾT MINH BÁO CÁO TÀI CHÍNH (tiếp theo)\n"
            "Đơn vị tính: Triệu VND\n"
            "9.3 Phân loại nợ cho vay theo Thông tư 11\n"
            "1. Nợ đủ tiêu chuẩn | 500.000.000 | 450.000.000\n"
            "2. Nợ cần chú ý | 5.000.000 | 4.000.000\n"
            "3. Nợ dưới tiêu chuẩn | 1.234.567 | 987.654\n"
            "4. Nợ nghi ngờ | 2.345.678 | 1.876.543\n"
            "5. Nợ có khả năng mất vốn | 3.456.789 | 2.765.432\n"
            "Tổng cộng dư nợ cho vay | 512.037.034 | 459.629.629\n"
        )
        self.pages = [
            PageInput(page_number=1, text=self.note_page_text, source="llamaparse"),
        ]
        self.stmt_pages = StatementPages(
            balance_sheet=[],
            income_statement=[],
            loan_quality_note=[1],
        )

    def test_successful_llm_selection(self) -> None:
        """When LLM returns a valid line_id, code deterministically parses the line."""
        # Initial extraction result with missing NPL group 3
        initial_row = CandidateRow(
            row_id="bank.input.npl_group_3_balance:target",
            metric_id="bank.input.npl_group_3_balance",
            label_vi="Nợ dưới tiêu chuẩn (Nhóm 3)",
            period_role="target",
            period_id="2025_Q4",
            value_billion_vnd=None,
            extracted_value_billion_vnd=None,
            raw_text=None,
            row_label=None,
            page=None,
            source=None,
            status="missing",
            issues=[RowIssue(code="row_not_found", severity="error", message_vi="Missing")],
            alternatives=[],
        )
        initial_prior = CandidateRow(
            row_id="bank.input.npl_group_3_balance:prior",
            metric_id="bank.input.npl_group_3_balance",
            label_vi="Nợ dưới tiêu chuẩn (Nhóm 3)",
            period_role="prior",
            period_id="2024_Q4",
            value_billion_vnd=None,
            extracted_value_billion_vnd=None,
            raw_text=None,
            row_label=None,
            page=None,
            source=None,
            status="missing",
            issues=[RowIssue(code="row_not_found", severity="error", message_vi="Missing")],
            alternatives=[],
        )
        ext = ExtractionResult(
            filing_id="fl-test",
            entity_id="VCB",
            display_name="Vietcombank",
            fiscal_year=2025,
            reporting_scope="consolidated",
            page_count=1,
            statement_pages=self.stmt_pages,
            unit_detected="million_vnd",
            rows=[initial_row, initial_prior],
            text_layer_pages=0,
            ocr_pages=1,
            limitations_vi=[],
        )

        fake_response = json.dumps({
            "line_id": "L3",  # Line 3 is "3. Nợ dưới tiêu chuẩn"
            "column_target": 0,
            "column_prior": 1,
            "reason": "Dòng 3. Nợ dưới tiêu chuẩn thể hiện số dư nợ nhóm 3",
        })
        client = FakeOpenAIClient([fake_response])

        refined_ext, tokens = refine_candidates_with_llm(
            ext,
            self.pages,
            client=client,
            model="test-model",
        )

        self.assertGreater(tokens, 0)
        target_r = next(r for r in refined_ext.rows if r.period_role == "target")
        prior_r = next(r for r in refined_ext.rows if r.period_role == "prior")

        # Verify that chat completions create did not receive a temperature argument
        self.assertGreater(len(client.chat.completions.prompts), 0)
        for prompt_kwargs in client.chat.completions.prompts:
            self.assertNotIn("temperature", prompt_kwargs)

        # Code took numbers from line (1.234.567 million VND -> 1234.567 billion VND)
        self.assertEqual(target_r.value_billion_vnd, "1234.567")
        self.assertEqual(prior_r.value_billion_vnd, "987.654")
        self.assertEqual(target_r.source, "llm_assisted_selection")
        self.assertEqual(target_r.status, "candidate")
        self.assertTrue(any(iss.code == "llm_selected" for iss in target_r.issues))

    def test_unknown_line_id_ignored(self) -> None:
        """When LLM returns an unknown line_id, code ignores it safely."""
        initial_row = CandidateRow(
            row_id="bank.input.npl_group_3_balance:target",
            metric_id="bank.input.npl_group_3_balance",
            label_vi="Nợ dưới tiêu chuẩn (Nhóm 3)",
            period_role="target",
            period_id="2025_Q4",
            value_billion_vnd=None,
            extracted_value_billion_vnd=None,
            raw_text=None,
            row_label=None,
            page=None,
            source=None,
            status="missing",
            issues=[],
            alternatives=[],
        )
        ext = ExtractionResult(
            filing_id="fl-test",
            entity_id="VCB",
            display_name="Vietcombank",
            fiscal_year=2025,
            reporting_scope="consolidated",
            page_count=1,
            statement_pages=self.stmt_pages,
            unit_detected="million_vnd",
            rows=[initial_row],
            text_layer_pages=0,
            ocr_pages=1,
            limitations_vi=[],
        )

        # Invalid line_id
        client = FakeOpenAIClient([json.dumps({"line_id": "L9999", "reason": "hallucinated"})])
        refined_ext, _ = refine_candidates_with_llm(
            ext,
            self.pages,
            client=client,
            model="test-model",
        )

        target_r = refined_ext.rows[0]
        self.assertIsNone(target_r.value_billion_vnd)
        self.assertEqual(target_r.status, "missing")

    def test_malformed_json_ignored(self) -> None:
        """When LLM returns invalid JSON or text, code ignores it safely."""
        initial_row = CandidateRow(
            row_id="bank.input.npl_group_3_balance:target",
            metric_id="bank.input.npl_group_3_balance",
            label_vi="Nợ dưới tiêu chuẩn (Nhóm 3)",
            period_role="target",
            period_id="2025_Q4",
            value_billion_vnd=None,
            extracted_value_billion_vnd=None,
            raw_text=None,
            row_label=None,
            page=None,
            source=None,
            status="missing",
            issues=[],
            alternatives=[],
        )
        ext = ExtractionResult(
            filing_id="fl-test",
            entity_id="VCB",
            display_name="Vietcombank",
            fiscal_year=2025,
            reporting_scope="consolidated",
            page_count=1,
            statement_pages=self.stmt_pages,
            unit_detected="million_vnd",
            rows=[initial_row],
            text_layer_pages=0,
            ocr_pages=1,
            limitations_vi=[],
        )

        client = FakeOpenAIClient(["Sorry, I cannot help with this."])
        refined_ext, _ = refine_candidates_with_llm(
            ext,
            self.pages,
            client=client,
            model="test-model",
        )

        target_r = refined_ext.rows[0]
        self.assertIsNone(target_r.value_billion_vnd)
        self.assertEqual(target_r.status, "missing")

    def test_create_does_not_receive_temperature(self) -> None:
        """Verify chat completions create is called without 'temperature' keyword."""
        initial_row = CandidateRow(
            row_id="bank.input.npl_group_3_balance:target",
            metric_id="bank.input.npl_group_3_balance",
            label_vi="Nợ dưới tiêu chuẩn (Nhóm 3)",
            period_role="target",
            period_id="2025_Q4",
            value_billion_vnd=None,
            extracted_value_billion_vnd=None,
            raw_text=None,
            row_label=None,
            page=None,
            source=None,
            status="missing",
            issues=[RowIssue(code="row_not_found", severity="error", message_vi="Missing")],
            alternatives=[],
        )
        ext = ExtractionResult(
            filing_id="fl-test",
            entity_id="VCB",
            display_name="Vietcombank",
            fiscal_year=2025,
            reporting_scope="consolidated",
            page_count=1,
            statement_pages=self.stmt_pages,
            unit_detected="million_vnd",
            rows=[initial_row],
            text_layer_pages=0,
            ocr_pages=1,
            limitations_vi=[],
        )
        fake_response = json.dumps({
            "line_id": "L3",
            "column_target": 0,
            "column_prior": 1,
            "reason": "Dòng 3",
        })
        client = FakeOpenAIClient([fake_response])
        refine_candidates_with_llm(ext, self.pages, client=client, model="test-model")
        self.assertEqual(client.chat.completions.call_count, 1)
        for call_kwargs in client.chat.completions.prompts:
            self.assertNotIn("temperature", call_kwargs)


if __name__ == "__main__":
    unittest.main()
