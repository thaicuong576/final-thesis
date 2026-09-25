"""OpenAI-compatible tool specifications and execution dispatcher for financial agents.

All tools query the canonical SQLite database (finance_master_v2.sqlite) to guarantee
Rule 3: 'Code computes financial metrics; language models retrieve, explain, critique, and synthesize.'
"""

from __future__ import annotations

import logging
import sqlite3
from typing import Any

from thesis_api.llm import format_function_tool

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# OpenAI Tool Specifications
# ---------------------------------------------------------------------------

TOOL_GET_COMPANY_METRICS = format_function_tool(
    name="get_company_metrics",
    description=(
        "Retrieve verified CAMEL ratios and financial metrics for a specific listed company "
        "from the canonical financial database. Returns metrics such as ROE, NIM, NPL, CIR, and CASA."
    ),
    parameters={
        "type": "object",
        "properties": {
            "ticker": {
                "type": "string",
                "description": "Stock ticker symbol of the target bank (e.g. ACB, VCB, MBB, TCB, VPB).",
            },
            "period": {
                "type": "string",
                "description": "Reporting period or fiscal year (e.g. '2024' or '2024_Q4').",
            },
            "kpis": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Optional list of specific CAMEL KPIs to retrieve (e.g. ['roe', 'nim', 'npl', 'cir', 'casa']).",
            },
        },
        "required": ["ticker", "period"],
    },
)

TOOL_GET_SECTOR_BENCHMARKS = format_function_tool(
    name="get_sector_benchmarks",
    description=(
        "Calculate or retrieve peer median CAMEL benchmark metrics across banking sector peers "
        "from the canonical financial database."
    ),
    parameters={
        "type": "object",
        "properties": {
            "sector": {
                "type": "string",
                "description": "Industry sector name (defaults to 'Banking').",
            },
            "period": {
                "type": "string",
                "description": "Reporting period or fiscal year (e.g. '2024').",
            },
            "tickers": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Optional list of peer tickers to include in benchmark calculation.",
            },
            "kpis": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Optional list of specific benchmark KPIs to focus on.",
            },
        },
        "required": ["sector", "period"],
    },
)

TOOL_GET_MACRO_CONTEXT = format_function_tool(
    name="get_macro_context",
    description=(
        "Retrieve macroeconomic policy context, SBV policy rates, inflation, and system credit "
        "growth figures for Vietnam from the canonical records."
    ),
    parameters={
        "type": "object",
        "properties": {
            "period": {
                "type": "string",
                "description": "Fiscal year or period (e.g. '2024').",
            },
            "indicators": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Optional list of macro indicators to retrieve (e.g. ['policy_rate', 'credit_growth', 'cpi']).",
            },
        },
        "required": ["period"],
    },
)

# Registry of all available tools
ALL_AGENT_TOOLS = [
    TOOL_GET_COMPANY_METRICS,
    TOOL_GET_SECTOR_BENCHMARKS,
    TOOL_GET_MACRO_CONTEXT,
]

COMPANY_TOOLS = [TOOL_GET_COMPANY_METRICS]
SECTOR_TOOLS = [TOOL_GET_SECTOR_BENCHMARKS]
MACRO_TOOLS = [TOOL_GET_MACRO_CONTEXT]


# ---------------------------------------------------------------------------
# Tool Execution Engine
# ---------------------------------------------------------------------------

def execute_agent_tool(
    tool_name: str,
    args: dict[str, Any],
    conn: sqlite3.Connection,
) -> dict[str, Any]:
    """Execute a structured financial agent tool query against the canonical SQLite database.

    Args:
        tool_name: Name of the function tool to execute.
        args: Dictionary of arguments supplied by the LLM function call.
        conn: Open SQLite connection to finance_master_v2.sqlite.

    Returns:
        Structured dictionary containing query results and provenance metadata.

    Raises:
        ValueError: If tool_name is unrecognized or required arguments are missing.
    """
    from thesis_api.service import (
        calculate_sector_benchmark,
        fetch_company_ratios,
        fetch_macro_context,
    )

    if tool_name == "get_company_metrics":
        ticker = str(args.get("ticker", "")).strip().upper()
        if not ticker:
            raise ValueError("Argument 'ticker' is required for get_company_metrics")
        period = str(args.get("period", "")).strip()
        if not period:
            raise ValueError("Argument 'period' is required for get_company_metrics")
        requested_kpis = args.get("kpis")

        ratios = fetch_company_ratios(conn, ticker, period)

        if requested_kpis and isinstance(requested_kpis, list):
            kpi_set = {k.strip().lower() for k in requested_kpis}
            filtered_ratios = {k: v for k, v in ratios.items() if k.lower() in kpi_set}
        else:
            filtered_ratios = ratios

        return {
            "tool": "get_company_metrics",
            "ticker": ticker,
            "period": period,
            "metrics": filtered_ratios,
            "status": "success",
        }

    elif tool_name == "get_sector_benchmarks":
        sector = str(args.get("sector", "Banking")).strip()
        period = str(args.get("period", "")).strip()
        if not period:
            raise ValueError("Argument 'period' is required for get_sector_benchmarks")
        raw_tickers = args.get("tickers")
        if raw_tickers and isinstance(raw_tickers, list):
            sample_tickers = [t.strip().upper() for t in raw_tickers if t.strip()]
        else:
            sample_tickers = []

        benchmark_dto = calculate_sector_benchmark(conn, period, sample_tickers)
        requested_kpis = args.get("kpis")

        benchmarks_dict = {
            "peer_median_roe": benchmark_dto.peer_median_roe,
            "peer_median_nim": benchmark_dto.peer_median_nim,
            "peer_median_npl": benchmark_dto.peer_median_npl,
            "peer_median_cir": benchmark_dto.peer_median_cir,
            "peer_median_casa": benchmark_dto.peer_median_casa,
        }

        if requested_kpis and isinstance(requested_kpis, list):
            kpi_set = {k.strip().lower() for k in requested_kpis}
            filtered_benchmarks = {
                k: v for k, v in benchmarks_dict.items()
                if any(target in k for target in kpi_set)
            }
        else:
            filtered_benchmarks = benchmarks_dict

        return {
            "tool": "get_sector_benchmarks",
            "sector": sector,
            "period": period,
            "benchmarks": filtered_benchmarks,
            "sample_tickers": sample_tickers,
            "status": "success",
        }

    elif tool_name == "get_macro_context":
        period = str(args.get("period", "")).strip()
        if not period:
            raise ValueError("Argument 'period' is required for get_macro_context")
        macro_dto = fetch_macro_context(conn, period)

        return {
            "tool": "get_macro_context",
            "period": period,
            "sbv_policy_rate": macro_dto.sbv_policy_rate,
            "system_credit_growth": macro_dto.system_credit_growth,
            "interest_rate_trend": macro_dto.interest_rate_trend,
            "source": macro_dto.source,
            "status": "success",
        }

    else:
        raise ValueError(f"Unknown agent tool: {tool_name}")
