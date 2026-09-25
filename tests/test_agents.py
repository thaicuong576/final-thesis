"""Unit tests for multi-agent cognitive loop and tool calling execution."""

from __future__ import annotations

import json
import sqlite3
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock

import openai

from thesis_api.agents import (
    CompanySpecialistAgent,
    MacroSpecialistAgent,
    OrchestratorAgent,
    SectorSpecialistAgent,
    SemanticCriticAgent,
)
from thesis_api.schemas import AnalysisRequest
from thesis_api.service import stream_analysis_query
from thesis_api.settings import get_settings


class AgentsTests(unittest.TestCase):
    """Test suite covering multi-agent prompt construction, tool calling, and bounded revision."""

    def setUp(self) -> None:
        self.db_path = get_settings().get_sqlite_path()
        self.conn = sqlite3.connect(f"file:{self.db_path}?mode=ro", uri=True)
        self.conn.row_factory = sqlite3.Row

    def tearDown(self) -> None:
        self.conn.close()

    def test_orchestrator_agent_plan_mocked(self) -> None:
        """Test OrchestratorAgent properly parses LLM plan JSON."""
        mock_client = MagicMock(spec=openai.OpenAI)
        mock_response = MagicMock()
        mock_response.choices = [
            MagicMock(
                message=MagicMock(
                    content=json.dumps(
                        {
                            "target_ticker": "TCB",
                            "peer_tickers": ["ACB", "MBB"],
                            "period": "2024",
                            "required_capabilities": ["company", "sector"],
                            "applicable_links": ["peer_comparison"],
                            "rationale": "So sánh hiệu quả NIM và CASA giữa TCB và các đối thủ.",
                            "analytical_hypothesis": "TCB duy trì tỷ lệ CASA cao giúp tối ưu hóa chi phí vốn.",
                        }
                    ),
                    tool_calls=None,
                )
            )
        ]
        mock_client.chat.completions.create.return_value = mock_response

        agent = OrchestratorAgent()
        plan = agent.plan(
            query="So sánh TCB với ACB và MBB năm 2024",
            client=mock_client,
            model="deepseek-v4-pro-0813",
        )

        self.assertEqual(plan["target_ticker"], "TCB")
        self.assertIn("ACB", plan["peer_tickers"])
        self.assertEqual(plan["required_capabilities"], ["company", "sector"])
        self.assertIn("NIM và CASA", plan["rationale"])

    def test_orchestrator_agent_fallback_on_unconfigured(self) -> None:
        """Test OrchestratorAgent fallback when client is None."""
        agent = OrchestratorAgent()
        plan = agent.plan(
            query="Đánh giá toàn diện ACB năm 2024 đặt trong bối cảnh vĩ mô",
            client=None,
        )
        self.assertEqual(plan["target_ticker"], "ACB")
        self.assertIn("company", plan["required_capabilities"])
        self.assertIn("macro", plan["required_capabilities"])

    def test_company_specialist_tool_calling_mocked(self) -> None:
        """Test CompanySpecialistAgent multi-turn tool calling cognitive loop."""
        mock_client = MagicMock(spec=openai.OpenAI)

        # Turn 1: LLM proposes tool call to get_company_metrics
        mock_tool_call = MagicMock()
        mock_tool_call.id = "call_comp_001"
        mock_tool_call.function.name = "get_company_metrics"
        mock_tool_call.function.arguments = json.dumps({"ticker": "ACB", "period": "2024_Q4"})

        choice_turn1 = MagicMock()
        choice_turn1.message.content = None
        choice_turn1.message.tool_calls = [mock_tool_call]
        resp_turn1 = MagicMock(choices=[choice_turn1])

        # Turn 2: LLM receives tool output and synthesizes findings
        choice_turn2 = MagicMock()
        choice_turn2.message.content = (
            "- ROE đạt 21.75% củng cố khả năng sinh lời trên vốn chủ sở hữu vượt trội.\n"
            "- Tỷ lệ nợ xấu NPL được kiểm soát an toàn ở mức 1.49%.\n"
            "- Tỷ lệ chi phí trên thu nhập CIR ở mức 32.53% cho thấy hiệu quả vận hành tối ưu."
        )
        choice_turn2.message.tool_calls = None
        resp_turn2 = MagicMock(choices=[choice_turn2])

        mock_client.chat.completions.create.side_effect = [resp_turn1, resp_turn2]

        agent = CompanySpecialistAgent()
        result = agent.execute(
            self.conn,
            ticker="ACB",
            period="2024_Q4",
            client=mock_client,
            model="deepseek-v4-pro-0813",
        )

        self.assertEqual(result["specialist_id"], "company")
        self.assertEqual(result["ticker"], "ACB")
        self.assertEqual(result["period"], "2024_Q4")
        self.assertEqual(len(result["tool_calls"]), 1)
        self.assertEqual(result["tool_calls"][0]["name"], "get_company_metrics")
        self.assertIn("roe", result["metrics"])
        self.assertEqual(len(result["findings"]), 3)
        self.assertIn("ROE đạt 21.75%", result["findings"][0])

    def test_sector_specialist_tool_calling_mocked(self) -> None:
        """Test SectorSpecialistAgent multi-turn tool calling cognitive loop."""
        mock_client = MagicMock(spec=openai.OpenAI)

        # Turn 1: LLM proposes tool call to get_sector_benchmarks
        mock_tool_call = MagicMock()
        mock_tool_call.id = "call_sec_001"
        mock_tool_call.function.name = "get_sector_benchmarks"
        mock_tool_call.function.arguments = json.dumps(
            {"sector": "Banking", "period": "2024_Q4", "tickers": ["ACB", "TCB", "MBB"]}
        )

        choice_turn1 = MagicMock()
        choice_turn1.message.content = None
        choice_turn1.message.tool_calls = [mock_tool_call]
        resp_turn1 = MagicMock(choices=[choice_turn1])

        # Turn 2: Synthesized findings
        choice_turn2 = MagicMock()
        choice_turn2.message.content = (
            "- Trung vị ROE toàn ngành đạt 18.74%, trong đó ACB vượt trội 3.01 điểm %.\n"
            "- Trung vị nợ xấu duy trì ở mức 1.49% phản ánh sự ổn định chung của nhóm NHTM."
        )
        choice_turn2.message.tool_calls = None
        resp_turn2 = MagicMock(choices=[choice_turn2])

        mock_client.chat.completions.create.side_effect = [resp_turn1, resp_turn2]

        agent = SectorSpecialistAgent()
        result = agent.execute(
            self.conn,
            target_ticker="ACB",
            peer_tickers=["TCB", "MBB"],
            period="2024_Q4",
            target_metrics={"roe": 21.75, "npl": 1.49},
            client=mock_client,
            model="deepseek-v4-pro-0813",
        )

        self.assertEqual(result["specialist_id"], "sector")
        self.assertEqual(len(result["tool_calls"]), 1)
        self.assertIn("peer_median_roe", result["benchmarks"])
        self.assertEqual(len(result["findings"]), 2)

    def test_macro_specialist_tool_calling_mocked(self) -> None:
        """Test MacroSpecialistAgent multi-turn tool calling cognitive loop."""
        mock_client = MagicMock(spec=openai.OpenAI)

        # Turn 1: LLM calls get_macro_context
        mock_tool_call = MagicMock()
        mock_tool_call.id = "call_macro_001"
        mock_tool_call.function.name = "get_macro_context"
        mock_tool_call.function.arguments = json.dumps({"period": "2024"})

        choice_turn1 = MagicMock()
        choice_turn1.message.content = None
        choice_turn1.message.tool_calls = [mock_tool_call]
        resp_turn1 = MagicMock(choices=[choice_turn1])

        # Turn 2: The empty provider result must not be converted into numeric claims.
        choice_turn2 = MagicMock()
        choice_turn2.message.content = (
            "No accepted macro observations are available for this request."
        )
        choice_turn2.message.tool_calls = None
        resp_turn2 = MagicMock(choices=[choice_turn2])

        mock_client.chat.completions.create.side_effect = [resp_turn1, resp_turn2]

        agent = MacroSpecialistAgent()
        result = agent.execute(
            self.conn,
            period="2024",
            client=mock_client,
            model="deepseek-v4-pro-0813",
        )

        self.assertEqual(result["specialist_id"], "macro")
        self.assertEqual(len(result["tool_calls"]), 1)
        self.assertIsNone(result["macro_context"]["sbv_policy_rate"])
        self.assertIsNone(result["macro_context"]["system_credit_growth"])
        self.assertIn("No accepted macro observations", result["findings"][0])

    def test_semantic_critic_round1_revision(self) -> None:
        """Test SemanticCriticAgent triggers revision in round 1 when paradox is detected."""
        mock_client = MagicMock(spec=openai.OpenAI)
        mock_response = MagicMock()
        mock_response.choices = [
            MagicMock(
                message=MagicMock(
                    content=json.dumps(
                        {
                            "decision": "REVISE",
                            "dimension": "NIM vs Sector Margin Pressure",
                            "finding": "NIM mở rộng trong khi chi phí vốn chưa được phân rã rõ ràng.",
                            "critique_summary": "Yêu cầu bổ sung đối soát thuyết minh chi phí vốn.",
                            "reason": "Độ trễ truyền dẫn lãi suất sang NIM quý 4 cần thuyết minh rõ ràng.",
                            "feedback_for_specialist": "Phân rã chi phí vốn huy động tiền gửi.",
                            "confidence": 0.94,
                        }
                    ),
                    tool_calls=None,
                )
            )
        ]
        mock_client.chat.completions.create.return_value = mock_response

        agent = SemanticCriticAgent()
        res = agent.critique(
            company_output={"ticker": "ACB", "metrics": {"roe": 21.75, "nim": 3.61}},
            sector_output={"benchmarks": {"peer_median_nim": 4.19}},
            macro_output={"macro_context": {"sbv_policy_rate": 4.5}},
            period="2024",
            current_round=1,
            max_rounds=2,
            client=mock_client,
        )

        self.assertEqual(res["decision"], "REVISE")
        self.assertTrue(res["requires_revision"])
        self.assertEqual(res["round"], 1)

    def test_semantic_critic_bounded_round2_acceptance(self) -> None:
        """Test SemanticCriticAgent enforces bounded convergence on round 2 (max_rounds)."""
        agent = SemanticCriticAgent()
        # In round 2, critic MUST accept even without LLM call to guarantee bounded convergence
        res = agent.critique(
            company_output={"ticker": "ACB", "metrics": {"roe": 21.75}},
            sector_output=None,
            macro_output=None,
            period="2024",
            current_round=2,
            max_rounds=2,
            client=None,
        )

        self.assertEqual(res["decision"], "ACCEPT")
        self.assertFalse(res["requires_revision"])
        self.assertIn("giới hạn tối đa 2 vòng", res["reason"])

    def test_stream_analysis_query_with_mocked_llm(self) -> None:
        """API streaming does not call the legacy LLM planner or fake specialists."""
        with tempfile.TemporaryDirectory() as directory:
            missing_db = Path(directory) / "missing.sqlite"
            req = AnalysisRequest(query="Analyze ROE of ACB in 2024 Q4", target_ticker="ACB", period="2024_Q4")
            events = list(stream_analysis_query(req, db_path=missing_db, step_delay=0))

        event_types = [json.loads(event.split("data: ")[1])["type"] for event in events]
        self.assertEqual(event_types[:2], ["USER_REQUEST_CONFIRMED", "PLANNING_STARTED"])
        self.assertEqual(event_types[-1], "RUN_BLOCKED")
        self.assertNotIn("SPECIALIST_INVOKED", event_types)
        self.assertNotIn("REVIEW_FEEDBACK_CREATED", event_types)
        self.assertNotIn("REVISION_REQUESTED", event_types)
        self.assertNotIn("REPORT_READY", event_types)

    def test_company_specialist_execute_with_data_single_turn(self) -> None:
        """Test CompanySpecialistAgent execute_with_data runs single-turn prompt without tool calls."""
        agent = CompanySpecialistAgent()
        precomputed = {"roe": 21.75, "nim": 3.82, "npl": 1.21, "cir": 31.8, "casa": 23.2}

        # 1. Without LLM client: deterministic template
        summary, findings = agent.execute_with_data("ACB", 2024, precomputed, client=None)
        self.assertIsInstance(summary, str)
        self.assertIsInstance(findings, list)
        self.assertEqual(len(findings), 3)
        self.assertIn("21.75%", summary)
        self.assertEqual(findings[0]["ticker"], "ACB")

        # 2. With LLM client: single-turn call
        mock_client = MagicMock(spec=openai.OpenAI)
        mock_resp = MagicMock()
        mock_resp.choices = [
            MagicMock(
                message=MagicMock(
                    content="- ROE đạt 21.75% vượt trội.\n- NPL 1.21% kiểm soát tốt.\n- CASA 23.2% tối ưu chi phí vốn.",
                    tool_calls=None,
                )
            )
        ]
        mock_client.chat.completions.create.return_value = mock_resp

        summary_llm, findings_llm = agent.execute_with_data(
            "ACB", 2024, precomputed, client=mock_client, model="deepseek-v4-pro-0813"
        )
        self.assertEqual(mock_client.chat.completions.create.call_count, 1)
        self.assertIn("21.75%", summary_llm)
        self.assertGreaterEqual(len(findings_llm), 2)
        self.assertEqual(findings_llm[0]["ticker"], "ACB")

    def test_sector_specialist_execute_with_data_single_turn(self) -> None:
        """Test SectorSpecialistAgent execute_with_data runs single-turn prompt without tool calls."""
        agent = SectorSpecialistAgent()
        benchmarks = {
            "peer_median_roe": 18.2,
            "peer_median_nim": 3.65,
            "peer_median_npl": 1.62,
        }
        target_metrics = {"roe": 21.75, "npl": 1.21}

        # 1. Without LLM client
        summary, findings = agent.execute_with_data("ACB", 2024, benchmarks, target_metrics=target_metrics, client=None)
        self.assertIsInstance(summary, str)
        self.assertIsInstance(findings, list)
        self.assertIn("18.2%", summary)
        self.assertEqual(findings[0]["ticker"], "ACB")

        # 2. With LLM client
        mock_client = MagicMock(spec=openai.OpenAI)
        mock_resp = MagicMock()
        mock_resp.choices = [
            MagicMock(
                message=MagicMock(
                    content="- Trung vị ROE ngành đạt 18.2%.\n- ACB vượt trội trung vị ngành về chất lượng nợ xấu (1.21% vs 1.62%).",
                    tool_calls=None,
                )
            )
        ]
        mock_client.chat.completions.create.return_value = mock_resp

        summary_llm, findings_llm = agent.execute_with_data(
            "ACB", 2024, benchmarks, target_metrics=target_metrics, client=mock_client
        )
        self.assertEqual(mock_client.chat.completions.create.call_count, 1)
        self.assertIn("18.2%", summary_llm)
        self.assertEqual(len(findings_llm), 2)


if __name__ == "__main__":
    unittest.main()
