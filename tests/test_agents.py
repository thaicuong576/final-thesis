"""Unit tests for multi-agent cognitive loop and tool calling execution."""

from __future__ import annotations

import json
import sqlite3
import unittest
from unittest.mock import MagicMock, patch

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
        mock_tool_call.function.arguments = json.dumps({"ticker": "ACB", "period": "2024"})

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
            period="2024",
            client=mock_client,
            model="deepseek-v4-pro-0813",
        )

        self.assertEqual(result["specialist_id"], "company")
        self.assertEqual(result["ticker"], "ACB")
        self.assertEqual(result["period"], "2024")
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
            {"sector": "Banking", "period": "2024", "tickers": ["ACB", "TCB", "MBB"]}
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
            period="2024",
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

        # Turn 2: Synthesized macro findings
        choice_turn2 = MagicMock()
        choice_turn2.message.content = (
            "- NHNN duy trì lãi suất tái cấp vốn 4.5% hỗ trợ thanh khoản hệ thống.\n"
            "- Mục tiêu tăng trưởng tín dụng 15.08% tạo đà cho mở rộng danh mục cho vay."
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
        self.assertEqual(result["macro_context"]["sbv_policy_rate"], 4.5)
        self.assertEqual(len(result["findings"]), 2)

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
        """Test stream_analysis_query end-to-end event sequence with mocked LLM client."""
        mock_client = MagicMock(spec=openai.OpenAI)

        # Plan response
        plan_resp = MagicMock()
        plan_resp.choices = [
            MagicMock(
                message=MagicMock(
                    content=json.dumps(
                        {
                            "target_ticker": "ACB",
                            "peer_tickers": ["TCB"],
                            "period": "2024",
                            "required_capabilities": ["company"],
                            "rationale": "Phân tích CAMEL nội tại ACB.",
                        }
                    ),
                    tool_calls=None,
                )
            )
        ]

        # Specialist responses
        comp_tool_call = MagicMock()
        comp_tool_call.id = "call_comp_999"
        comp_tool_call.function.name = "get_company_metrics"
        comp_tool_call.function.arguments = json.dumps({"ticker": "ACB", "period": "2024"})

        comp_turn1 = MagicMock(choices=[MagicMock(message=MagicMock(content=None, tool_calls=[comp_tool_call]))])
        comp_turn2 = MagicMock(choices=[MagicMock(message=MagicMock(content="- ROE đạt 21.75%.\n- NPL đạt 1.49%.", tool_calls=None))])

        # Critic response
        critic_resp = MagicMock()
        critic_resp.choices = [
            MagicMock(
                message=MagicMock(
                    content=json.dumps(
                        {
                            "decision": "ACCEPT",
                            "dimension": "Soundness",
                            "finding": "Chỉ số tài chính nhất quán.",
                            "confidence": 0.96,
                        }
                    ),
                    tool_calls=None,
                )
            )
        ]

        mock_client.chat.completions.create.side_effect = [
            plan_resp,
            comp_turn1,
            comp_turn2,
            critic_resp,
        ]

        with patch("thesis_api.service.get_llm_config", return_value={"is_configured": True, "model": "deepseek-v4-pro-0813"}), \
             patch("thesis_api.service.get_llm_client", return_value=mock_client):

            req = AnalysisRequest(query="Phân tích ACB 2024")
            events = list(stream_analysis_query(req, step_delay=0))

            event_types = [
                json.loads(e.split("data: ")[1])["type"]
                for e in events if "data: " in e
            ]

            self.assertIn("USER_REQUEST_CONFIRMED", event_types)
            self.assertIn("PLAN_CREATED", event_types)
            self.assertIn("SPECIALIST_INVOKED", event_types)
            self.assertIn("SPECIALIST_ACTIVITY", event_types)
            self.assertIn("SPECIALIST_OUTPUT_CREATED", event_types)
            self.assertIn("SPECIALIST_COMPLETED", event_types)
            self.assertIn("REVIEW_STARTED", event_types)
            self.assertIn("SYNTHESIS_STARTED", event_types)
            self.assertIn("REPORT_READY", event_types)


if __name__ == "__main__":
    unittest.main()
