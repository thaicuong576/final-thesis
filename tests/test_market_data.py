"""Tests for SSI market data and valuation endpoints (MKT-1).

Verifies:
- Unconfigured behavior (200 with configured: false)
- Fake client quotes fetching and field verification
- In-memory cache TTL and HOSE hours check
- Stale fallback on failed refresh
- Missing inputs resulting in null P/B with reason (never 0)
- 401 token refresh flow
- VND/billion unit conversion giving VCB P/B within 1.5 - 2.5
"""

from __future__ import annotations

import asyncio
from datetime import datetime, timedelta, timezone
from pathlib import Path
import unittest
from unittest.mock import AsyncMock, patch

from fastapi.testclient import TestClient
import httpx

from thesis_api.main import create_app
from thesis_api.market_data import (
    HOSE_BANK_SYMBOLS,
    FakeSSIMarketDataClient,
    RealSSIMarketDataClient,
    clear_market_data_cache,
    get_quotes_cache_ttl,
    is_hose_open,
    set_market_data_client,
)
from thesis_api.settings import Settings


class TestMarketData(unittest.TestCase):
    """Test suite for /api/market/quotes and /api/market/valuation."""

    def setUp(self) -> None:
        clear_market_data_cache()
        set_market_data_client(None)

        # Candidate paths for operational snapshot
        candidate_paths = [
            Path("data/processed/bank-quarterly-top10-operational-v1-r4.sqlite"),
            Path(__file__).resolve().parents[1] / "data" / "processed" / "bank-quarterly-top10-operational-v1-r4.sqlite",
            Path("D:/eddie-projects/personal-projects/final-thesis/data/processed/bank-quarterly-top10-operational-v1-r4.sqlite"),
        ]
        self.db_path = next((p for p in candidate_paths if p.exists()), None)
        self.settings = Settings(
            _env_file=None,
            sqlite_db_path=str(self.db_path) if self.db_path else "data/processed/finance_master_v2.sqlite",
            app_env="test",
        )
        self.app = create_app(self.settings)
        self.client = TestClient(self.app)

    def tearDown(self) -> None:
        clear_market_data_cache()
        set_market_data_client(None)

    def test_unconfigured_endpoints_return_200_with_configured_false(self) -> None:
        """When SSI env vars are missing, endpoints answer 200 with configured: false."""
        with patch.dict("os.environ", {}, clear=True):
            set_market_data_client(None)
            resp_quotes = self.client.get("/api/market/quotes")
            self.assertEqual(resp_quotes.status_code, 200)
            data_quotes = resp_quotes.json()
            self.assertFalse(data_quotes["configured"])
            self.assertEqual(data_quotes["quotes"], [])

            resp_val = self.client.get("/api/market/valuation")
            self.assertEqual(resp_val.status_code, 200)
            data_val = resp_val.json()
            self.assertFalse(data_val["configured"])
            self.assertEqual(data_val["items"], [])

    def test_fake_client_quotes_all_ten_banks_and_caching(self) -> None:
        """Quotes endpoint returns all 10 HOSE banks with expected fields and caches them."""
        fake_client = FakeSSIMarketDataClient()
        set_market_data_client(fake_client)

        resp = self.client.get("/api/market/quotes")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertTrue(data["configured"])
        self.assertFalse(data["stale"])
        self.assertIsNone(data["stale_reason"])
        self.assertEqual(len(data["quotes"]), 10)

        tickers = [q["ticker"] for q in data["quotes"]]
        self.assertEqual(sorted(tickers), sorted(HOSE_BANK_SYMBOLS))

        first_fetched_at = data["fetched_at"]
        self.assertIsNotNone(first_fetched_at)

        # Check VCB quote fields
        vcb_quote = next(q for q in data["quotes"] if q["ticker"] == "VCB")
        self.assertEqual(vcb_quote["close"], 56700.0)
        self.assertEqual(vcb_quote["reference"], 56500.0)
        self.assertEqual(vcb_quote["change"], 200.0)
        self.assertEqual(vcb_quote["trading_date"], "12/10/2026")
        self.assertEqual(vcb_quote["source"], "SSI FastConnect Data")
        self.assertFalse(vcb_quote["stale"])

        # Second call should hit in-memory cache and return identical fetched_at
        resp2 = self.client.get("/api/market/quotes")
        self.assertEqual(resp2.status_code, 200)
        self.assertEqual(resp2.json()["fetched_at"], first_fetched_at)

    def test_stale_fallback_serves_last_good_value_on_refresh_failure(self) -> None:
        """When refreshing fails after successful cache, last good value is served with stale: true."""
        fake_client = FakeSSIMarketDataClient()
        set_market_data_client(fake_client)

        # Initial successful call
        resp1 = self.client.get("/api/market/quotes")
        self.assertEqual(resp1.status_code, 200)
        self.assertFalse(resp1.json()["stale"])

        # Simulate network failure on subsequent refresh
        fake_client.fail_daily = True
        # Force expiration of cache timestamp
        from thesis_api import market_data
        market_data._quotes_timestamp = datetime.now(timezone.utc) - timedelta(hours=1)

        resp2 = self.client.get("/api/market/quotes")
        self.assertEqual(resp2.status_code, 200)
        data2 = resp2.json()
        self.assertTrue(data2["stale"])
        self.assertIsNotNone(data2["stale_reason"])
        self.assertEqual(len(data2["quotes"]), 10)
        self.assertTrue(data2["quotes"][0]["stale"])
        self.assertEqual(data2["quotes"][0]["close"], 20200.0)  # ACB preserved

    def test_hose_market_hours_and_ttl(self) -> None:
        """Cache TTL is 30s during HOSE market hours (09:00-15:00 Mon-Fri) and 15m otherwise."""
        # Vietnam is UTC+7.
        # Monday 10:00 VN time (03:00 UTC) -> Open
        dt_open = datetime(2026, 10, 12, 3, 0, 0, tzinfo=timezone.utc)
        self.assertTrue(is_hose_open(dt_open))
        self.assertEqual(get_quotes_cache_ttl(dt_open), 30.0)

        # Monday 20:00 VN time (13:00 UTC) -> Closed
        dt_closed = datetime(2026, 10, 12, 13, 0, 0, tzinfo=timezone.utc)
        self.assertFalse(is_hose_open(dt_closed))
        self.assertEqual(get_quotes_cache_ttl(dt_closed), 900.0)

        # Sunday 10:00 VN time -> Closed
        dt_sunday = datetime(2026, 10, 11, 3, 0, 0, tzinfo=timezone.utc)
        self.assertFalse(is_hose_open(dt_sunday))
        self.assertEqual(get_quotes_cache_ttl(dt_sunday), 900.0)

    def test_vcb_unit_conversion_pb_within_expected_range(self) -> None:
        """VCB close 56,700 VND and recorded equity yields P/B between 1.5 and 2.5."""
        fake_client = FakeSSIMarketDataClient()
        set_market_data_client(fake_client)

        resp = self.client.get("/api/market/valuation")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertTrue(data["configured"])
        self.assertEqual(len(data["items"]), 10)

        vcb_item = next(item for item in data["items"] if item["ticker"] == "VCB")
        self.assertIsNotNone(vcb_item["pb"], f"VCB missing reason: {vcb_item.get('missing_reason')}")
        self.assertGreaterEqual(vcb_item["pb"], 1.5)
        self.assertLessEqual(vcb_item["pb"], 2.5)

        # Check inputs traceability
        inputs = vcb_item["inputs"]
        self.assertEqual(inputs["close_vnd"], 56700.0)
        self.assertEqual(inputs["listed_shares"], 8356000000)
        self.assertAlmostEqual(inputs["parent_attributable_equity_billion_vnd"], 248490.506, places=1)
        self.assertIsNotNone(inputs["roe_percent"])
        self.assertIn("1e9", inputs["formula"])

    def test_missing_input_returns_null_pb_with_reason_never_zero(self) -> None:
        """When an input like listed shares is missing, pb is null with reason, never 0."""
        # Create a client where STB has missing shares
        shares_without_stb = dict(FakeSSIMarketDataClient().shares)
        shares_without_stb.pop("STB", None)

        fake_client = FakeSSIMarketDataClient(shares=shares_without_stb)
        set_market_data_client(fake_client)

        resp = self.client.get("/api/market/valuation")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()

        stb_item = next(item for item in data["items"] if item["ticker"] == "STB")
        self.assertIsNone(stb_item["pb"])
        self.assertNotEqual(stb_item["pb"], 0)
        self.assertIsNotNone(stb_item["missing_reason"])
        self.assertIn("niêm yết", stb_item["missing_reason"].lower())

    def test_real_client_base_url_strips_api_v2_and_refreshes_on_401(self) -> None:
        """RealSSIMarketDataClient tolerates base URL ending in /api/v2 and refreshes on 401."""
        client = RealSSIMarketDataClient(
            base_url="https://fc-data.ssi.com.vn/api/v2",
            consumer_id="test_id",
            consumer_secret="test_secret",
        )
        self.assertEqual(client.base_url, "https://fc-data.ssi.com.vn")

        # Test token refresh on 401
        mock_http = AsyncMock(spec=httpx.AsyncClient)
        # First call to obtain token
        req_token = httpx.Request("POST", "https://fc-data.ssi.com.vn/api/v2/Market/AccessToken")
        token_resp = httpx.Response(200, json={"status": 200, "data": {"accessToken": "tok-1"}}, request=req_token)
        # Request returns 401
        req_api = httpx.Request("GET", "https://fc-data.ssi.com.vn/api/v2/Market/DailyStockPrice")
        unauth_resp = httpx.Response(401, request=req_api)
        # Second call to obtain token
        token2_resp = httpx.Response(200, json={"status": 200, "data": {"accessToken": "tok-2"}}, request=req_token)
        # Retry request returns 200
        success_resp = httpx.Response(200, json={"status": 200, "data": [{"ClosePrice": "20200"}]}, request=req_api)

        mock_http.post.side_effect = [token_resp, token2_resp]
        mock_http.request.side_effect = [unauth_resp, success_resp]

        client._custom_client = mock_http

        result = asyncio.run(client.get_daily_stock_price("ACB"))
        self.assertEqual(result["status"], 200)
        self.assertEqual(mock_http.post.call_count, 2)
        self.assertEqual(mock_http.request.call_count, 2)
