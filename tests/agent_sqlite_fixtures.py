"""Isolated SQLite fixtures for legacy agent-tool tests."""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path

from thesis_data.storage import create_gold_snapshot_schema


_MOCK_RATIOS = {
    "ACB": {"bank.roe": 21.75, "bank.nim": 3.82, "bank.npl_g35": 1.21, "bank.cir": 31.8, "bank.casa": 23.2},
    "TCB": {"bank.roe": 18.74, "bank.nim": 4.19, "bank.npl_g35": 1.49, "bank.cir": 35.0, "bank.casa": 28.0},
    "MBB": {"bank.roe": 19.2, "bank.nim": 4.1, "bank.npl_g35": 1.33, "bank.cir": 32.0, "bank.casa": 22.0},
}
_POINT_IN_TIME_METRICS = {"bank.npl_g35", "bank.casa"}
_FIELD_CODES = {
    "bank.roe": "ROE",
    "bank.nim": "NIM",
    "bank.npl_g35": "NPL",
    "bank.cir": "CIR",
    "bank.casa": "CASA",
}


def create_synthetic_agent_database(db_path: Path) -> Path:
    """Create a labeled, source-linked mock Gold snapshot for agent tests."""

    db_path = Path(db_path)
    db_path.parent.mkdir(parents=True, exist_ok=True)
    create_gold_snapshot_schema(db_path)

    with sqlite3.connect(db_path) as connection:
        connection.execute(
            "INSERT INTO snapshot_metadata VALUES (?, ?, ?, ?)",
            (
                "synthetic-agent-tools-test-v1",
                "2026-09-25T00:00:00Z",
                "mock-test-fixture",
                json.dumps({"fixture_label": "synthetic_mock_data", "tickers": sorted(_MOCK_RATIOS)}),
            ),
        )
        source_rows = [
            (
                f"mock-source-{ticker}",
                "filing",
                "primary",
                f"https://mock.example.test/{ticker}/2024-q4",
                "2026-09-25T00:00:00Z",
                f"{ticker}-synthetic-fixture.pdf",
                f"mock-sha256-{ticker.lower()}",
                ticker,
                "synthetic_mock_data",
                "valid",
                None,
            )
            for ticker in sorted(_MOCK_RATIOS)
        ]
        connection.executemany(
            "INSERT INTO source_records VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            source_rows,
        )
        observation_rows = []
        ratio_rows = []
        for ticker, metrics in sorted(_MOCK_RATIOS.items()):
            for metric_id, value in sorted(metrics.items()):
                basis = "point_in_time" if metric_id in _POINT_IN_TIME_METRICS else "ttm"
                observation_rows.append(
                    (
                        f"mock-{ticker}-{metric_id}-2024-q4",
                        ticker,
                        "bank",
                        metric_id,
                        value,
                        "%",
                        "2024_Q4",
                        "2024-12-31",
                        basis,
                        f"mock-source-{ticker}",
                        f"mock-fixture:{ticker}:{metric_id}:2024_Q4",
                        "valid",
                        None,
                    )
                )
                ratio_rows.append(
                    (
                        ticker,
                        _FIELD_CODES[metric_id],
                        "2024_Q4",
                        value,
                        "%",
                        f"mock-source-{ticker}",
                        "valid",
                        "valid",
                        f"mock-fixture:{ticker}:{metric_id}:2024_Q4",
                    )
                )
        connection.executemany(
            "INSERT INTO metric_observations VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            observation_rows,
        )
        connection.execute(
            """CREATE TABLE ratio_observations (
                ticker TEXT NOT NULL,
                field_code TEXT NOT NULL,
                period TEXT NOT NULL,
                value REAL NOT NULL,
                unit TEXT NOT NULL,
                source_id TEXT NOT NULL,
                quality_status TEXT NOT NULL,
                status TEXT NOT NULL,
                source_locator TEXT NOT NULL,
                PRIMARY KEY (ticker, field_code, period)
            )"""
        )
        connection.executemany(
            "INSERT INTO ratio_observations VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            ratio_rows,
        )
    connection.close()
    return db_path
