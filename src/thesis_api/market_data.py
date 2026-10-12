"""Market context from SSI market-data API and valuation metrics (MKT-1).

Provides real-time / delayed quotes and P/B vs ROE valuation calculations for 10
HOSE banks beside verified reports.
Read-only market context strictly separated from verified analysis.
"""

from __future__ import annotations

import asyncio
from datetime import datetime, time, timedelta, timezone
import logging
import os
from pathlib import Path
from typing import Any, Protocol, runtime_checkable

from fastapi import APIRouter, Request
import httpx
from pydantic import BaseModel, Field

from .service import _load_provider

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/market", tags=["market"])

HOSE_BANK_SYMBOLS: list[str] = [
    "ACB",
    "BID",
    "CTG",
    "HDB",
    "MBB",
    "SHB",
    "STB",
    "TCB",
    "VCB",
    "VPB",
]

SSI_SOURCE_NAME = "SSI FastConnect Data"

# Recorded fixtures for offline testing & fake transport (2026-10-12)
RECORDED_QUOTES_2026_10_12: dict[str, dict[str, Any]] = {
    "ACB": {"close": 20200.0, "reference": 20150.0, "change": 50.0, "change_percent": 0.25, "volume": 12500000, "trading_date": "12/10/2026"},
    "BID": {"close": 33950.0, "reference": 33900.0, "change": 50.0, "change_percent": 0.15, "volume": 1800000, "trading_date": "12/10/2026"},
    "CTG": {"close": 34200.0, "reference": 34000.0, "change": 200.0, "change_percent": 0.59, "volume": 5400000, "trading_date": "12/10/2026"},
    "HDB": {"close": 26100.0, "reference": 26000.0, "change": 100.0, "change_percent": 0.38, "volume": 4200000, "trading_date": "12/10/2026"},
    "MBB": {"close": 24500.0, "reference": 24300.0, "change": 200.0, "change_percent": 0.82, "volume": 11000000, "trading_date": "12/10/2026"},
    "SHB": {"close": 10400.0, "reference": 10300.0, "change": 100.0, "change_percent": 0.97, "volume": 15200000, "trading_date": "12/10/2026"},
    "STB": {"close": 66900.0, "reference": 66500.0, "change": 400.0, "change_percent": 0.60, "volume": 8400000, "trading_date": "12/10/2026"},
    "TCB": {"close": 23100.0, "reference": 23000.0, "change": 100.0, "change_percent": 0.43, "volume": 9500000, "trading_date": "12/10/2026"},
    "VCB": {"close": 56700.0, "reference": 56500.0, "change": 200.0, "change_percent": 0.35, "volume": 2100000, "trading_date": "12/10/2026"},
    "VPB": {"close": 18900.0, "reference": 18800.0, "change": 100.0, "change_percent": 0.53, "volume": 16000000, "trading_date": "12/10/2026"},
}

RECORDED_SHARES_2026_10_12: dict[str, int] = {
    "ACB": 5137000000,
    "BID": 5700435900,
    "CTG": 5370000000,
    "HDB": 2907000000,
    "MBB": 5214000000,
    "SHB": 3662000000,
    "STB": 1885000000,
    "TCB": 7045000000,
    "VCB": 8356000000,
    "VPB": 7934000000,
}


# ---------------------------------------------------------------------------
# Data Models
# ---------------------------------------------------------------------------

class QuoteItem(BaseModel):
    ticker: str
    close: float
    reference: float
    change: float
    change_percent: float
    volume: int
    trading_date: str
    fetched_at: str
    source: str = SSI_SOURCE_NAME
    stale: bool = False
    stale_reason: str | None = None


class QuotesResponse(BaseModel):
    configured: bool = True
    source: str = SSI_SOURCE_NAME
    fetched_at: str | None = None
    stale: bool = False
    stale_reason: str | None = None
    quotes: list[QuoteItem] = Field(default_factory=list)


class ValuationInputs(BaseModel):
    close_vnd: float | None = None
    close_source: str = SSI_SOURCE_NAME
    close_date: str | None = None
    listed_shares: int | None = None
    shares_source: str = f"{SSI_SOURCE_NAME} (SecuritiesDetails)"
    parent_attributable_equity_billion_vnd: float | None = None
    equity_period: str | None = None
    equity_source: str | None = None
    roe_percent: float | None = None
    roe_period: str | None = None
    formula: str = "P/B = close_vnd / (parent_attributable_equity_billion_vnd * 1e9 / listed_shares)"


class BankValuationItem(BaseModel):
    ticker: str
    close: float | None = None
    listed_shares: int | None = None
    parent_attributable_equity: float | None = None
    bvps: float | None = None
    pb: float | None = None
    roe: float | None = None
    inputs: ValuationInputs = Field(default_factory=ValuationInputs)
    missing_reason: str | None = None


class ValuationResponse(BaseModel):
    configured: bool = True
    source: str = f"{SSI_SOURCE_NAME} & Accepted Financial Snapshot"
    fetched_at: str | None = None
    stale: bool = False
    stale_reason: str | None = None
    items: list[BankValuationItem] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# HOSE Trading Hours & Cache TTL
# ---------------------------------------------------------------------------

def is_hose_open(dt: datetime | None = None) -> bool:
    """Check if HOSE market is currently open (Mon-Fri 09:00-15:00 Asia/Ho_Chi_Minh)."""
    if dt is None:
        dt = datetime.now(timezone.utc)
    tz_vn = timezone(timedelta(hours=7))
    vn_dt = dt.astimezone(tz_vn)
    if vn_dt.weekday() >= 5:  # Saturday=5, Sunday=6
        return False
    cur_time = vn_dt.time()
    return time(9, 0) <= cur_time <= time(15, 0)


def get_quotes_cache_ttl(dt: datetime | None = None) -> float:
    """Return cache TTL: 30 seconds during trading hours, 15 minutes (900s) otherwise."""
    return 30.0 if is_hose_open(dt) else 900.0


def sanitize_market_error_reason(exc: Any) -> str:
    """Map any internal or upstream error to a fixed Vietnamese reason string.

    Strictly never leaks URLs, upstream error tracebacks, or English exception
    text to the public JSON response. Technical details are logged server-side only.
    """
    if exc is None:
        return "Nguồn dữ liệu không phản hồi"

    text = str(exc).lower()

    # Upstream server / gateway / network error (even if URL contains AccessToken)
    if any(k in text for k in ("502", "503", "504", "500", "bad gateway", "service unavailable", "gateway timeout", "connecterror", "timeoutexception")):
        return "Nguồn dữ liệu không phản hồi"

    # Unconfigured / missing credentials
    if any(k in text for k in ("chưa cấu hình", "unconfigured", "missing credentials", "not configured")):
        return "Chưa cấu hình"

    # Token / auth failure: 401/403 Unauthorized or expired token
    if any(k in text for k in ("401", "403", "unauthorized", "forbidden", "hết hạn token", "expired token", "invalid token")):
        return "Hết hạn token"

    # Market closed / outside trading hours
    if any(k in text for k in ("ngoài giờ", "closed", "weekend", "off-hours")):
        return "Dữ liệu ngoài giờ"

    # Default upstream network / gateway failure
    return "Nguồn dữ liệu không phản hồi"


# ---------------------------------------------------------------------------
# SSI Client Interface & Implementations
# ---------------------------------------------------------------------------

@runtime_checkable
class SSIMarketDataClient(Protocol):
    """Protocol for SSI FastConnect Market Data API."""

    async def get_daily_stock_price(self, symbol: str) -> dict[str, Any]:
        """Fetch daily stock price quote."""
        ...

    async def get_securities_details(self, symbol: str) -> dict[str, Any]:
        """Fetch securities details including listed shares."""
        ...


class FakeSSIMarketDataClient:
    """In-memory fake client seeded with verified recorded data for the 10 banks."""

    def __init__(
        self,
        quotes: dict[str, dict[str, Any]] | None = None,
        shares: dict[str, int] | None = None,
        *,
        fail_daily: bool = False,
        simulate_401: bool = False,
    ) -> None:
        self.quotes = quotes if quotes is not None else dict(RECORDED_QUOTES_2026_10_12)
        self.shares = shares if shares is not None else dict(RECORDED_SHARES_2026_10_12)
        self.fail_daily = fail_daily
        self.simulate_401 = simulate_401
        self.token_refreshes = 0

    async def get_daily_stock_price(self, symbol: str) -> dict[str, Any]:
        if self.fail_daily:
            raise RuntimeError("Fake network failure fetching daily stock price")
        if self.simulate_401 and self.token_refreshes == 0:
            self.token_refreshes += 1
            raise httpx.HTTPStatusError(
                "401 Unauthorized",
                request=httpx.Request("GET", "https://fc-data.ssi.com.vn/api/v2/Market/DailyStockPrice"),
                response=httpx.Response(401),
            )
        q = self.quotes.get(symbol.upper())
        if not q:
            return {"status": 200, "message": "Success", "data": []}
        return {
            "status": 200,
            "message": "Success",
            "data": [
                {
                    "TradingDate": q.get("trading_date", "12/10/2026"),
                    "ClosePrice": str(int(q.get("close", 0))),
                    "RefPrice": str(int(q.get("reference", 0))),
                    "PriceChange": str(int(q.get("change", 0))),
                    "PerPriceChange": f"{q.get('change_percent', 0.0):.2f}",
                    "TotalMatchVol": str(q.get("volume", 0)),
                }
            ],
        }

    async def get_securities_details(self, symbol: str) -> dict[str, Any]:
        sh = self.shares.get(symbol.upper())
        if sh is None:
            return {"status": 200, "message": "Success", "data": []}
        return {
            "status": 200,
            "message": "Success",
            "data": [
                {
                    "Symbol": symbol.upper(),
                    "Market": "HOSE",
                    "RepeatedInfo": [{"ListedShare": str(sh)}],
                }
            ],
        }


class RealSSIMarketDataClient:
    """Production client for SSI FastConnect API."""

    def __init__(
        self,
        base_url: str,
        consumer_id: str,
        consumer_secret: str,
        *,
        http_client: httpx.AsyncClient | None = None,
        timeout: float = 10.0,
        retry_delay: float = 1.0,
    ) -> None:
        url = base_url.strip().rstrip("/")
        if url.endswith("/api/v2"):
            url = url[:-len("/api/v2")]
        self.base_url = url
        self.consumer_id = consumer_id
        self.consumer_secret = consumer_secret
        self.timeout = timeout
        self.retry_delay = retry_delay
        self._custom_client = http_client
        self._token: str | None = None
        self._token_lock = asyncio.Lock()

    def _get_http_client(self) -> httpx.AsyncClient:
        if self._custom_client is not None:
            return self._custom_client
        return httpx.AsyncClient(timeout=self.timeout)

    async def _obtain_token(
        self,
        client: httpx.AsyncClient,
        stale_token: str | None = None,
        *,
        force: bool = False,
    ) -> str:
        async with self._token_lock:
            # Return existing token if refreshed by another request while waiting
            if not force and self._token and self._token != stale_token:
                return self._token

            token_url = f"{self.base_url}/api/v2/Market/AccessToken"
            payload = {
                "consumerID": self.consumer_id,
                "consumerSecret": self.consumer_secret,
            }

            resp: httpx.Response | None = None
            last_exc: Exception | None = None
            for attempt in range(2):
                try:
                    resp = await client.post(token_url, json=payload)
                    if resp.status_code >= 500:
                        resp.raise_for_status()
                    break
                except (httpx.HTTPStatusError, httpx.RequestError) as exc:
                    is_5xx = (
                        isinstance(exc, httpx.HTTPStatusError)
                        and exc.response is not None
                        and exc.response.status_code >= 500
                    )
                    is_connect = isinstance(exc, httpx.RequestError)
                    if attempt == 0 and (is_5xx or is_connect):
                        logger.warning(
                            "SSI AccessToken request failed (%s); retrying once after %.1fs...",
                            exc,
                            self.retry_delay,
                        )
                        last_exc = exc
                        await asyncio.sleep(self.retry_delay)
                        continue
                    raise

            if resp is None:
                if last_exc:
                    raise last_exc
                raise RuntimeError("Failed to obtain response from SSI AccessToken endpoint")

            resp.raise_for_status()
            data = resp.json()
            token = data.get("data", {}).get("accessToken")
            if not token:
                raise ValueError("Failed to obtain accessToken from SSI response")
            self._token = token
            return token

    async def _request_with_token(
        self,
        method: str,
        endpoint: str,
        params: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        client = self._get_http_client()
        should_close = self._custom_client is None
        try:
            token = self._token
            if not token:
                token = await self._obtain_token(client, stale_token=token)

            headers = {"Authorization": f"Bearer {token}"}
            url = f"{self.base_url}{endpoint}"
            resp = await client.request(method, url, params=params, headers=headers)

            if resp.status_code == 401:
                # Token expired; refresh once and retry
                token = await self._obtain_token(client, stale_token=token)
                headers["Authorization"] = f"Bearer {token}"
                resp = await client.request(method, url, params=params, headers=headers)

            resp.raise_for_status()
            return resp.json()
        finally:
            if should_close:
                await client.aclose()

    async def get_daily_stock_price(self, symbol: str) -> dict[str, Any]:
        now_vn = datetime.now(timezone(timedelta(hours=7)))
        to_date = now_vn.strftime("%d/%m/%Y")
        from_date = (now_vn - timedelta(days=7)).strftime("%d/%m/%Y")
        params = {
            "symbol": symbol.upper(),
            "fromDate": from_date,
            "toDate": to_date,
            "pageIndex": 1,
            "pageSize": 10,
            "market": "HOSE",
        }
        return await self._request_with_token("GET", "/api/v2/Market/DailyStockPrice", params=params)

    async def get_securities_details(self, symbol: str) -> dict[str, Any]:
        params = {
            "symbol": symbol.upper(),
            "market": "HOSE",
            "pageIndex": 1,
            "pageSize": 10,
        }
        return await self._request_with_token("GET", "/api/v2/Market/SecuritiesDetails", params=params)


# ---------------------------------------------------------------------------
# Global State & Client Injection
# ---------------------------------------------------------------------------

_injected_client: SSIMarketDataClient | None = None

# Quotes in-memory cache
_cached_quotes: list[QuoteItem] = []
_quotes_fetched_at: str | None = None
_quotes_timestamp: datetime | None = None
_quotes_refresh_lock = asyncio.Lock()

# Listed shares cache (symbol -> (shares, fetched_at_timestamp))
_shares_cache: dict[str, tuple[int, datetime]] = {}
_shares_lock = asyncio.Lock()


def set_market_data_client(client: SSIMarketDataClient | None) -> None:
    """Override or inject market data client (used in tests)."""
    global _injected_client
    _injected_client = client


def clear_market_data_cache() -> None:
    """Clear in-memory quotes and valuation caches (used in tests)."""
    global _cached_quotes, _quotes_fetched_at, _quotes_timestamp, _shares_cache
    _cached_quotes = []
    _quotes_fetched_at = None
    _quotes_timestamp = None
    _shares_cache = {}


def get_market_data_client() -> SSIMarketDataClient | None:
    """Get active SSI market data client, or None if unconfigured."""
    if _injected_client is not None:
        return _injected_client

    url = os.environ.get("SSI_FC_URL", "").strip()
    consumer_id = os.environ.get("SSI_CONSUMER_ID", "").strip()
    consumer_secret = os.environ.get("SSI_CONSUMER_SECRET", "").strip()

    if not (url and consumer_id and consumer_secret):
        return None

    return RealSSIMarketDataClient(
        base_url=url,
        consumer_id=consumer_id,
        consumer_secret=consumer_secret,
    )


# ---------------------------------------------------------------------------
# Quote and Valuation Fetchers
# ---------------------------------------------------------------------------

async def fetch_single_quote(
    client: SSIMarketDataClient,
    symbol: str,
    fetched_at_iso: str,
) -> QuoteItem:
    """Fetch daily stock price quote for one bank."""
    raw = await client.get_daily_stock_price(symbol)
    rows = raw.get("data") or []
    if not rows:
        raise ValueError(f"No daily stock price data returned for {symbol}")

    latest = rows[0]
    return QuoteItem(
        ticker=symbol.upper(),
        close=float(latest.get("ClosePrice", 0.0)),
        reference=float(latest.get("RefPrice", 0.0)),
        change=float(latest.get("PriceChange", 0.0)),
        change_percent=float(latest.get("PerPriceChange", 0.0)),
        volume=int(latest.get("TotalMatchVol", 0)),
        trading_date=str(latest.get("TradingDate", "")),
        fetched_at=fetched_at_iso,
        source=SSI_SOURCE_NAME,
        stale=False,
    )


async def get_listed_shares(client: SSIMarketDataClient, symbol: str) -> int | None:
    """Get listed shares for a bank, using a 24-hour in-memory cache."""
    now = datetime.now(timezone.utc)
    sym = symbol.upper()
    async with _shares_lock:
        if sym in _shares_cache:
            shares, fetched_at = _shares_cache[sym]
            if (now - fetched_at).total_seconds() < 86400:
                return shares

    try:
        raw = await client.get_securities_details(sym)
        data = raw.get("data") or []
        if not data:
            return None
        info = data[0].get("RepeatedInfo") or []
        if not info:
            return None
        raw_val = info[0].get("ListedShare")
        if raw_val is None:
            return None
        shares = int(raw_val)
        async with _shares_lock:
            _shares_cache[sym] = (shares, now)
        return shares
    except Exception as exc:
        logger.warning("Error fetching listed shares for %s: %s", sym, exc)
        return None


async def get_or_refresh_quotes(
    client: SSIMarketDataClient,
    force_refresh: bool = False,
) -> tuple[list[QuoteItem], str, bool, str | None]:
    """Retrieve quotes with TTL caching, stampede prevention, and stale fallback."""
    global _cached_quotes, _quotes_fetched_at, _quotes_timestamp
    now = datetime.now(timezone.utc)
    ttl = get_quotes_cache_ttl(now)

    # Check cache first
    if not force_refresh and _cached_quotes and _quotes_timestamp:
        age = (now - _quotes_timestamp).total_seconds()
        if age < ttl:
            return _cached_quotes, _quotes_fetched_at or now.isoformat(), False, None

    # Single in-flight refresh (no stampede)
    async with _quotes_refresh_lock:
        # Re-check cache after acquiring lock
        if not force_refresh and _cached_quotes and _quotes_timestamp:
            age = (now - _quotes_timestamp).total_seconds()
            if age < ttl:
                return _cached_quotes, _quotes_fetched_at or now.isoformat(), False, None

        fetched_at_iso = now.isoformat()
        semaphore = asyncio.Semaphore(3)  # Small bounded concurrency limit

        async def _bounded_fetch(sym: str) -> QuoteItem:
            async with semaphore:
                return await fetch_single_quote(client, sym, fetched_at_iso)

        try:
            if not HOSE_BANK_SYMBOLS:
                return [], fetched_at_iso, False, None

            # Fetch the first quote alone to obtain the token, then run the rest concurrently
            first_sym = HOSE_BANK_SYMBOLS[0]
            first_quote = await fetch_single_quote(client, first_sym, fetched_at_iso)

            remaining_syms = HOSE_BANK_SYMBOLS[1:]
            tasks = [_bounded_fetch(sym) for sym in remaining_syms]
            remaining_quotes = await asyncio.gather(*tasks)

            _cached_quotes = [first_quote, *remaining_quotes]
            _quotes_fetched_at = fetched_at_iso
            _quotes_timestamp = now
            return _cached_quotes, fetched_at_iso, False, None
        except Exception as exc:
            logger.warning("Market quotes refresh failed: %s", exc)
            sanitized_reason = sanitize_market_error_reason(exc)
            if _cached_quotes:
                # Stale fallback: serve last cached value labelled stale
                stale_items = [
                    item.model_copy(update={"stale": True, "stale_reason": sanitized_reason})
                    for item in _cached_quotes
                ]
                return stale_items, _quotes_fetched_at or fetched_at_iso, True, sanitized_reason
            raise


# ---------------------------------------------------------------------------
# API Routes
# ---------------------------------------------------------------------------

@router.get("/quotes", response_model=QuotesResponse, summary="Get quotes for 10 HOSE banks")
async def get_market_quotes() -> QuotesResponse:
    """Fetch or serve cached stock quotes for the ten HOSE banks."""
    client = get_market_data_client()
    if client is None:
        return QuotesResponse(configured=False, quotes=[])

    try:
        quotes, fetched_at, stale, stale_reason = await get_or_refresh_quotes(client)
        return QuotesResponse(
            configured=True,
            source=SSI_SOURCE_NAME,
            fetched_at=fetched_at,
            stale=stale,
            stale_reason=stale_reason,
            quotes=quotes,
        )
    except Exception as exc:
        logger.error("Failed to obtain market quotes: %s", exc)
        return QuotesResponse(
            configured=True,
            source=SSI_SOURCE_NAME,
            fetched_at=datetime.now(timezone.utc).isoformat(),
            stale=True,
            stale_reason=sanitize_market_error_reason(exc),
            quotes=[],
        )


@router.get("/valuation", response_model=ValuationResponse, summary="Get P/B vs ROE valuation metrics")
async def get_market_valuation(request: Request) -> ValuationResponse:
    """Calculate P/B and join with ROE for the ten HOSE banks beside verified reports."""
    client = get_market_data_client()
    if client is None:
        return ValuationResponse(configured=False, items=[])

    # 1. Obtain quotes
    try:
        quotes, fetched_at, quotes_stale, quotes_stale_reason = await get_or_refresh_quotes(client)
    except Exception as exc:
        logger.error("Valuation quotes fetch failed: %s", exc)
        return ValuationResponse(
            configured=True,
            source=f"{SSI_SOURCE_NAME} & Accepted Financial Snapshot",
            fetched_at=datetime.now(timezone.utc).isoformat(),
            stale=True,
            stale_reason=sanitize_market_error_reason(exc),
            items=[],
        )

    quote_by_ticker = {q.ticker.upper(): q for q in quotes}

    # 2. Access accepted dataset snapshot via existing provider boundary
    sqlite_path = getattr(request.app.state, "sqlite_path", None)
    if not sqlite_path or not Path(sqlite_path).exists():
        # Fallback to default operational snapshot if state not found
        candidate_paths = [
            Path("data/processed/bank-quarterly-top10-operational-v1-r4.sqlite"),
            Path("data/processed/finance_master_v2.sqlite"),
        ]
        sqlite_path = next((p for p in candidate_paths if p.exists()), None)

    provider = None
    dataset_ref = None
    latest_period = None
    if sqlite_path:
        try:
            binding = _load_provider(Path(sqlite_path))
            provider = binding.provider
            dataset_ref = binding.dataset_ref
            if binding.catalog.periods:
                latest_period = binding.catalog.periods[-1].period_id
        except Exception as exc:
            logger.warning("Failed to open dataset provider for valuation: %s", exc)

    items: list[BankValuationItem] = []

    for sym in HOSE_BANK_SYMBOLS:
        q = quote_by_ticker.get(sym)
        shares = await get_listed_shares(client, sym)

        equity_val: float | None = None
        equity_source_title: str | None = None
        roe_val: float | None = None

        if provider and dataset_ref and latest_period:
            try:
                obs_eq = provider.get_metric(dataset_ref, sym, latest_period, "bank.input.parent_attributable_equity")
                if obs_eq and obs_eq.value is not None:
                    equity_val = float(obs_eq.value)
                    equity_source_title = f"Báo cáo tài chính hợp nhất {latest_period} - {sym}"
            except Exception:
                pass

            try:
                obs_roe = provider.get_metric(dataset_ref, sym, latest_period, "bank.roe")
                if obs_roe and obs_roe.value is not None:
                    roe_val = float(obs_roe.value)
            except Exception:
                pass

        # Build inputs dict
        inputs = ValuationInputs(
            close_vnd=q.close if q else None,
            close_source=SSI_SOURCE_NAME,
            close_date=q.trading_date if q else None,
            listed_shares=shares,
            shares_source=f"{SSI_SOURCE_NAME} (SecuritiesDetails)",
            parent_attributable_equity_billion_vnd=equity_val,
            equity_period=latest_period,
            equity_source=equity_source_title,
            roe_percent=roe_val,
            roe_period=latest_period,
        )

        # Check completeness: If any input missing, pb is None with reason, NEVER 0!
        missing_reasons: list[str] = []
        if q is None or q.close <= 0:
            missing_reasons.append("Thiếu giá đóng cửa từ SSI")
        if shares is None or shares <= 0:
            missing_reasons.append("Thiếu số cổ phiếu niêm yết từ SSI")
        if equity_val is None or equity_val <= 0:
            missing_reasons.append("Thiếu vốn chủ sở hữu mẹ trong snapshot thẩm định")
        if roe_val is None:
            missing_reasons.append("Thiếu ROE trong snapshot thẩm định")

        if missing_reasons:
            items.append(
                BankValuationItem(
                    ticker=sym,
                    close=q.close if q else None,
                    listed_shares=shares,
                    parent_attributable_equity=equity_val,
                    bvps=None,
                    pb=None,
                    roe=roe_val,
                    inputs=inputs,
                    missing_reason="; ".join(missing_reasons),
                )
            )
        else:
            # Formula: BVPS = (parent_attributable_equity * 1e9) / shares
            # P/B = close / BVPS
            bvps = (equity_val * 1_000_000_000.0) / float(shares)
            pb = round(q.close / bvps, 3)

            items.append(
                BankValuationItem(
                    ticker=sym,
                    close=q.close,
                    listed_shares=shares,
                    parent_attributable_equity=equity_val,
                    bvps=round(bvps, 2),
                    pb=pb,
                    roe=round(roe_val, 2),
                    inputs=inputs,
                    missing_reason=None,
                )
            )

    return ValuationResponse(
        configured=True,
        source=f"{SSI_SOURCE_NAME} & Accepted Financial Snapshot",
        fetched_at=fetched_at,
        stale=quotes_stale,
        stale_reason=quotes_stale_reason,
        items=items,
    )
