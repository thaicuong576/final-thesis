"""Lineage endpoint and tree builder for observations and facts.

Provides recursive provenance trees tracing observations back to primary filings,
PDF pages, extracted row labels, formulas, and calculation receipts.
Read-only access strictly preserving immutable data artifacts.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
import re
import sqlite3
from typing import Any, Optional

from fastapi import APIRouter, HTTPException, Request, status
from pydantic import BaseModel, Field

from .settings import get_settings
from thesis_data.evidence_contract import _contains_local_path

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/lineage", tags=["lineage"])

# Metric display names in Vietnamese
METRIC_LABELS_VI = {
    "bank.llr_coverage": "Tỷ lệ bao phủ nợ xấu (LLR)",
    "bank.npl_g35": "Tỷ lệ nợ xấu (nhóm 3–5)",
    "bank.roa": "Tỷ suất sinh lời trên tổng tài sản (ROA)",
    "bank.roe": "Tỷ suất sinh lời trên vốn chủ sở hữu (ROE)",
    "bank.input.loan_loss_provisions": "Dự phòng rủi ro cho vay khách hàng",
    "bank.input.npl_g35_balance": "Tổng nợ xấu (nhóm 3–5)",
    "bank.input.npl_group_3_balance": "Nợ dưới tiêu chuẩn (nhóm 3)",
    "bank.input.npl_group_4_balance": "Nợ nghi ngờ (nhóm 4)",
    "bank.input.npl_group_5_balance": "Nợ có khả năng mất vốn (nhóm 5)",
    "bank.input.gross_customer_loans": "Cho vay khách hàng",
    "bank.input.total_assets": "Tổng tài sản",
    "bank.input.total_equity": "Vốn chủ sở hữu",
    "bank.input.parent_attributable_equity": "Vốn chủ sở hữu của ngân hàng mẹ",
    "bank.input.profit_after_tax": "Lợi nhuận sau thuế",
    "bank.input.parent_attributable_profit": "Lợi nhuận sau thuế của ngân hàng mẹ",
}


def parse_locator(raw_locator: Optional[str]) -> dict[str, Any]:
    """Parse structured fields from a machine source locator string."""
    if not raw_locator:
        return {}
    parts = [p.strip() for p in raw_locator.split(";") if p.strip()]
    kv: dict[str, str] = {}
    for part in parts:
        if ":" in part:
            k, v = part.split(":", 1)
            kv[k.strip()] = v.strip()
        elif "=" in part:
            k, v = part.split("=", 1)
            kv[k.strip()] = v.strip()

    page = None
    for p_key in ("pdf_page", "pdf_pages", "printed_page", "printed_pages", "page", "pages"):
        if p_key in kv:
            m = re.search(r"\d+", kv[p_key])
            if m:
                page = int(m.group(0))
                break

    section = kv.get("section") or kv.get("sections") or kv.get("statement") or kv.get("table")
    row_label = kv.get("row") or kv.get("row_label")
    reading = kv.get("reading")

    return {
        "page": page,
        "section": section,
        "row_label": row_label,
        "reading": reading,
    }


def _resolve_fact_to_observation_id(conn: sqlite3.Connection, fact_id: str) -> Optional[str]:
    """Resolve fact identifier into the primary target observation ID."""
    parts = fact_id.split(":")
    if len(parts) >= 5 and parts[0] == "fact":
        fact_type = parts[1]
        entity = None
        period = None
        metric = None

        if fact_type in ("value", "peer_rank", "gap_to_median"):
            # fact:value:<entity>:<period>:<metric> or fact:peer_rank:<entity>:sector:bank:<period>:<metric>
            entity = parts[2]
            metric = parts[-1]
            period = parts[-2]
        elif fact_type == "peer_median":
            # fact:peer_median:sector:bank:<period>:<metric>
            period = parts[-2]
            metric = parts[-1]
        elif fact_type == "delta":
            # fact:delta:<entity>:<p1>_to_<p2>:<metric>
            entity = parts[2]
            metric = parts[-1]
            p_span = parts[3].split("_to_")
            period = p_span[-1] if len(p_span) == 2 else parts[3]

        cur = conn.cursor()
        if entity and period and metric:
            row = cur.execute(
                "SELECT observation_id FROM observations WHERE entity_id = ? AND period_id = ? AND metric_id = ?",
                (entity, period, metric),
            ).fetchone()
            if row:
                return row["observation_id"]
        elif period and metric:
            row = cur.execute(
                "SELECT observation_id FROM observations WHERE period_id = ? AND metric_id = ? LIMIT 1",
                (period, metric),
            ).fetchone()
            if row:
                return row["observation_id"]

    return None


def get_lineage_tree(db_path: Path, target_id: str) -> Optional[dict[str, Any]]:
    """Build a recursive lineage tree for an observation or fact from SQLite.

    Strictly connects in read-only mode (uri=True, mode=ro) to avoid any file mutation.
    """
    if not db_path.exists():
        logger.error("Lineage database path does not exist: %s", db_path)
        return None

    db_uri = f"file:{db_path.resolve().as_posix()}?mode=ro"
    conn = sqlite3.connect(db_uri, uri=True)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    try:
        observation_id = target_id
        if target_id.startswith("fact:"):
            resolved_id = _resolve_fact_to_observation_id(conn, target_id)
            if not resolved_id:
                return None
            observation_id = resolved_id

        # Cache metrics
        metrics_cache = {
            row["metric_id"]: row["display_name"]
            for row in cur.execute("SELECT metric_id, display_name FROM metrics").fetchall()
        }
        # Cache documents
        documents_cache = {
            row["source_ref"]: row["title"]
            for row in cur.execute("SELECT source_ref, title FROM documents").fetchall()
        }
        # Cache sources
        sources_cache = {
            row["source_ref"]: dict(row)
            for row in cur.execute("SELECT source_ref, source_url, publisher FROM sources").fetchall()
        }

        def build_node(obs_id: str, visited: set[str]) -> Optional[dict[str, Any]]:
            if obs_id in visited:
                return None
            visited.add(obs_id)

            obs_row = cur.execute("SELECT * FROM observations WHERE observation_id = ?", (obs_id,)).fetchone()
            if not obs_row:
                return None

            obs = dict(obs_row)
            metric_id = obs["metric_id"]
            metric_name = METRIC_LABELS_VI.get(metric_id) or metrics_cache.get(metric_id) or metric_id

            # Receipt parsing
            meta = json.loads(obs["metadata_json"]) if obs.get("metadata_json") else {}
            receipt = meta.get("__derived_calculation_receipt_v1") or meta.get("calculation_receipt")
            receipt_result = receipt.get("result") if receipt else None
            receipt_tolerance = receipt.get("tolerance") if receipt else None

            # Parse inputs/children
            child_ids = []
            if obs.get("input_observation_ids_json"):
                try:
                    child_ids = json.loads(obs["input_observation_ids_json"])
                except Exception:
                    child_ids = []

            children = []
            for cid in child_ids:
                cnode = build_node(cid, visited.copy())
                if cnode:
                    children.append(cnode)

            # Source provenance
            source_ref = obs.get("source_ref")
            source_url = None
            source_title = None
            if source_ref and source_ref in sources_cache:
                raw_url = sources_cache[source_ref].get("source_url")
                if raw_url:
                    if raw_url.startswith("http://") or raw_url.startswith("https://"):
                        source_url = raw_url
                    elif not _contains_local_path(raw_url):
                        source_url = raw_url
                raw_title = documents_cache.get(source_ref) or sources_cache[source_ref].get("publisher")
                if raw_title and not _contains_local_path(raw_title):
                    source_title = raw_title

            loc_info = parse_locator(obs.get("source_locator"))

            node = {
                "observation_id": obs["observation_id"],
                "entity": obs["entity_id"],
                "entity_id": obs["entity_id"],
                "metric": metric_id,
                "metric_id": metric_id,
                "metric_name": metric_name,
                "period": obs["period_id"],
                "period_id": obs["period_id"],
                "value": float(obs["value"]) if obs["value"] is not None else None,
                "unit": obs.get("unit"),
                "formula_version": obs.get("derivation_method"),
                "receipt_result": receipt_result,
                "receipt_tolerance": str(receipt_tolerance) if receipt_tolerance is not None else None,
                "calculation_receipt": receipt,
                "source_title": source_title,
                "source_url": source_url,
                "page": loc_info.get("page"),
                "section": loc_info.get("section"),
                "row_label": loc_info.get("row_label"),
                "reading": loc_info.get("reading"),
                "children": children,
            }
            return node

        return build_node(observation_id, set())
    finally:
        conn.close()


def _resolve_db_path(request: Request) -> Path:
    """Resolve SQLite database path from request application state or settings."""
    if hasattr(request.app.state, "sqlite_path") and request.app.state.sqlite_path:
        return Path(request.app.state.sqlite_path)
    return get_settings().get_sqlite_path()


@router.get(
    "/{observation_id}",
    summary="Retrieve recursive lineage tree for an observation or fact",
    response_description="Recursive lineage tree with formula derivation and primary source citations",
)
def get_observation_lineage(
    observation_id: str,
    request: Request,
) -> dict[str, Any]:
    """Retrieve recursive observation lineage tree.

    Rejects unknown observation IDs with 404.
    Returns observation details, calculation receipts, input nodes recursively,
    and filing metadata (PDF url, page, section, row label) on leaf nodes.
    """
    db_path = _resolve_db_path(request)
    tree = get_lineage_tree(db_path, observation_id)
    if tree is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Observation or fact {observation_id} not found in accepted snapshot",
        )
    return tree


@router.get(
    "",
    summary="Query lineage tree by observation_id or fact_id parameter",
    include_in_schema=False,
)
def get_lineage_by_query(
    request: Request,
    observation_id: Optional[str] = None,
    fact_id: Optional[str] = None,
) -> dict[str, Any]:
    """Query parameter alias for lineage resolution."""
    target_id = observation_id or fact_id
    if not target_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Either observation_id or fact_id query parameter is required",
        )
    return get_observation_lineage(target_id, request)
