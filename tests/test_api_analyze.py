"""Integration tests for POST /api/analyze endpoint."""

from __future__ import annotations

import unittest
from fastapi.testclient import TestClient

from thesis_api.main import create_app
from thesis_api.schemas import AnalysisResponse
from thesis_api.settings import Settings


class ApiAnalyzeIntegrationTests(unittest.TestCase):
    """Test suite verifying /api/analyze endpoint with SQLite data engine."""

    def setUp(self) -> None:
        self.settings = Settings(
            app_name="final-thesis-api-test",
            app_env="test",
            sqlite_db_path="data/processed/finance_master_v2.sqlite",
        )
        self.app = create_app(self.settings)
        self.client = TestClient(self.app)

    def test_analyze_full_payload_success_and_schema_compliance(self) -> None:
        payload = {
            "query": "Phân tích tỷ suất sinh lời ROE và chất lượng tài sản (NPL) của ACB và TCB năm 2024",
            "target_ticker": "ACB",
            "peer_tickers": ["TCB", "MBB"],
            "period": "2024",
        }
        response = self.client.post("/api/analyze", json=payload)
        self.assertEqual(response.status_code, 200)

        data = response.json()

        # Validate 100% adherence to Pydantic v2 AnalysisResponse schema
        validated_response = AnalysisResponse.model_validate(data)
        self.assertIsNotNone(validated_response.report_id)
        self.assertEqual(validated_response.status, "completed")

        # 1. Macro Context validation
        macro = data["macro_context"]
        self.assertEqual(macro["sbv_policy_rate"], 4.5)
        self.assertEqual(macro["system_credit_growth"], 15.08)
        self.assertIn("Accommodative", macro["interest_rate_trend"])
        self.assertIn("SBV", macro["source"])

        # 2. Sector Benchmark validation
        benchmark = data["sector_benchmark"]
        self.assertEqual(benchmark["sector"], "Banking")
        self.assertIsInstance(benchmark["peer_median_roe"], float)
        self.assertIsInstance(benchmark["peer_median_nim"], float)
        self.assertIsInstance(benchmark["peer_median_npl"], float)
        self.assertIsInstance(benchmark["peer_median_cir"], float)
        self.assertIsInstance(benchmark["peer_median_casa"], float)

        # 3. Company Insights validation
        insights = data["company_insights"]
        self.assertGreaterEqual(len(insights), 3)  # ACB, TCB, MBB
        tickers = [item["ticker"] for item in insights]
        self.assertIn("ACB", tickers)
        self.assertIn("TCB", tickers)
        self.assertIn("MBB", tickers)

        acb_insight = next(item for item in insights if item["ticker"] == "ACB")
        self.assertIsNotNone(acb_insight["roe"])
        self.assertIsNotNone(acb_insight["nim"])
        self.assertIsNotNone(acb_insight["npl"])
        self.assertIsNotNone(acb_insight["cir"])
        self.assertIsNotNone(acb_insight["casa"])
        self.assertTrue(len(acb_insight["assessment"]) > 0)

        # 4. Cross-Level Critique validation
        critiques = data["cross_level_critique"]
        self.assertGreaterEqual(len(critiques), 1)
        for crit in critiques:
            self.assertIn("dimension", crit)
            self.assertIn("finding", crit)
            self.assertGreaterEqual(crit["confidence"], 0.0)
            self.assertLessEqual(crit["confidence"], 1.0)

        # 5. Evidence Trail validation
        evidence = data["evidence_trail"]
        self.assertGreaterEqual(len(evidence), 1)
        for ev in evidence:
            self.assertIn("metric", ev)
            self.assertEqual(ev["ticker"], "ACB")
            self.assertIn("source_doc", ev)

    def test_analyze_natural_query_auto_resolves_tickers_and_period(self) -> None:
        payload = {
            "query": "Phân tích ROE và chất lượng tài sản của ACB và TCB năm 2024",
        }
        response = self.client.post("/api/analyze", json=payload)
        self.assertEqual(response.status_code, 200)

        data = response.json()
        validated = AnalysisResponse.model_validate(data)
        self.assertEqual(validated.status, "completed")

        insights = data["company_insights"]
        tickers = [item["ticker"] for item in insights]
        self.assertIn("ACB", tickers)
        self.assertIn("TCB", tickers)

    def test_analyze_nonexistent_bank_returns_valid_partial_status(self) -> None:
        payload = {
            "query": "Phân tích dữ liệu tài chính ngân hàng XYZ năm 2024",
            "target_ticker": "XYZ",
            "period": "2024",
        }
        response = self.client.post("/api/analyze", json=payload)
        self.assertEqual(response.status_code, 200)

        data = response.json()
        # Even for nonexistent bank, API contract must not crash and return valid OpenAPI response
        validated = AnalysisResponse.model_validate(data)
        self.assertEqual(validated.status, "partial")
        self.assertIsInstance(data["macro_context"], dict)
        self.assertIsInstance(data["sector_benchmark"], dict)
        self.assertIsInstance(data["company_insights"], list)
        self.assertIsInstance(data["cross_level_critique"], list)

    def test_analyze_quarterly_period_query(self) -> None:
        payload = {
            "query": "Phân tích ngân hàng VCB quý 4 năm 2024",
            "target_ticker": "VCB",
            "peer_tickers": ["BID", "CTG"],
            "period": "2024_Q4",
        }
        response = self.client.post("/api/analyze", json=payload)
        self.assertEqual(response.status_code, 200)

        data = response.json()
        validated = AnalysisResponse.model_validate(data)
        self.assertEqual(validated.status, "completed")

        vcb_insight = next(item for item in data["company_insights"] if item["ticker"] == "VCB")
        self.assertIsNotNone(vcb_insight["roe"])
        self.assertIsNotNone(vcb_insight["npl"])


if __name__ == "__main__":
    unittest.main()
