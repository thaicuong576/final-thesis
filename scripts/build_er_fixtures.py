#!/usr/bin/env python3
"""Build equity research report fixtures directly from Gold v5 SQLite.

Reads Gold v5 in read-only mode, computes facts and dataset rows with exact
mathematical precision (no rounding on numbers), and writes the 7 fixture JSON files.
"""

from __future__ import annotations

import json
import sqlite3
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


def get_gold_db_path() -> Path:
    candidates = [
        Path("data/processed/gold-bank-2025-expanded-v5-evidence.sqlite"),
        Path(__file__).resolve().parent.parent / "data/processed/gold-bank-2025-expanded-v5-evidence.sqlite",
        Path(__file__).resolve().parent.parent.parent.parent / "data/processed/gold-bank-2025-expanded-v5-evidence.sqlite",
    ]
    for p in candidates:
        if p.exists():
            return p.resolve()
    raise FileNotFoundError("Could not find gold-bank-2025-expanded-v5-evidence.sqlite")


def get_fixtures_dir() -> Path:
    root = Path(__file__).resolve().parent.parent
    fdir = root / "frontend" / "src" / "test" / "fixtures"
    fdir.mkdir(parents=True, exist_ok=True)
    return fdir


class GoldDatabase:
    def __init__(self, db_path: Path):
        self.db_path = db_path
        uri = f"file:{db_path.as_posix()}?mode=ro"
        self.conn = sqlite3.connect(uri, uri=True)
        self.conn.row_factory = sqlite3.Row
        self._load_data()

    def _load_data(self) -> None:
        c = self.conn.cursor()
        self.obs: Dict[Tuple[str, str, str], Dict[str, Any]] = {}
        for r in c.execute("SELECT * FROM metric_observations"):
            d = dict(r)
            self.obs[(d["ticker"], d["metric"], d["period"])] = d

        self.sources: Dict[str, Dict[str, Any]] = {}
        for r in c.execute("SELECT * FROM source_records"):
            d = dict(r)
            self.sources[d["source_id"]] = d

    def get_obs(self, ticker: str, metric: str, period: str) -> Optional[Dict[str, Any]]:
        return self.obs.get((ticker, metric, period))

    def get_source(self, source_id: str) -> Optional[Dict[str, Any]]:
        return self.sources.get(source_id)


def calc_median(numbers: List[float]) -> float:
    if not numbers:
        raise ValueError("Cannot calculate median of empty list")
    s = sorted(numbers)
    n = len(s)
    if n % 2 == 1:
        return float(s[n // 2])
    return float((s[n // 2 - 1] + s[n // 2]) / 2.0)


def calc_ranks(entity_vals: List[Tuple[str, float]], direction: str) -> Dict[str, Tuple[int, int]]:
    """Competition ranking (1-2-2-4): returns {entity: (rank_better, rank_desc)}."""
    res = {}
    for entity, val in entity_vals:
        if direction == "lower_is_better":
            rank_better = 1 + sum(1 for _, other in entity_vals if other < val)
            rank_desc = 1 + sum(1 for _, other in entity_vals if other > val)
        else:
            rank_better = 1 + sum(1 for _, other in entity_vals if other > val)
            rank_desc = rank_better
        res[entity] = (rank_better, rank_desc)
    return res


METRIC_DIRECTIONS = {
    "bank.npl_g35": "lower_is_better",
    "bank.llr_coverage": "higher_is_better",
    "bank.roa": "higher_is_better",
    "bank.roe": "higher_is_better",
}

ALL_BANKS = ["VCB", "TCB", "ACB", "MBB", "VPB"]
ALL_METRICS = ["bank.npl_g35", "bank.llr_coverage", "bank.roa", "bank.roe"]
ALL_PERIODS = ["2024_Q1", "2024_Q2", "2024_Q3", "2024_Q4"]


try:
    from scripts.er_fixture_helpers import humanize_locator
except ImportError:
    from er_fixture_helpers import humanize_locator


def format_source_note(
    db: GoldDatabase,
    note_no: int,
    ticker: str,
    metric: str,
    period: str,
    fact_ids: List[str],
) -> Dict[str, Any]:
    obs = db.get_obs(ticker, metric, period)
    if not obs:
        raise ValueError(f"Observation not found in Gold v5 for {ticker}, {metric}, {period}")
    src_id = obs.get("source_id")
    if not src_id:
        raise ValueError(f"Observation {obs.get('observation_id')} is missing source_id in Gold v5")

    src = db.get_source(src_id)
    if not src or not src.get("source_url"):
        raise ValueError(f"Source {src_id} missing in source_records or has empty source_url")

    url = src["source_url"]
    src_type = src.get("source_type", "filing")

    year, q_part = period.split("_")
    quarter = q_part.replace("Q", "")
    if src_type == "issuer_ir":
        title = f"{ticker} · Tài liệu công bố cho nhà đầu tư {year}"
    else:
        title = f"{ticker} · Báo cáo tài chính quý {quarter}/{year}"

    raw_locator = obs.get("source_locator") or ""
    locator = humanize_locator(raw_locator)

    return {
        "note_no": note_no,
        "source_id": src_id,
        "title": title,
        "url": url,
        "locator": locator,
        "fact_ids": fact_ids,
    }


def build_er_lookup_fixture(db: GoldDatabase) -> Dict[str, Any]:
    """1. Lookup VCB NPL Q4/2024."""
    obs_q4 = db.get_obs("VCB", "bank.npl_g35", "2024_Q4")
    obs_q3 = db.get_obs("VCB", "bank.npl_g35", "2024_Q3")
    assert obs_q4 and obs_q3

    vcb_q4_val = float(obs_q4["value"])
    vcb_q3_val = float(obs_q3["value"])
    delta_q3_q4 = vcb_q4_val - vcb_q3_val

    # 5 banks Q4 for npl_g35
    q4_pairs = []
    q4_obs_ids = []
    for b in ALL_BANKS:
        o = db.get_obs(b, "bank.npl_g35", "2024_Q4")
        assert o
        q4_pairs.append((b, float(o["value"])))
        q4_obs_ids.append(o["observation_id"])

    median_q4 = calc_median([v for _, v in q4_pairs])
    ranks = calc_ranks(q4_pairs, METRIC_DIRECTIONS["bank.npl_g35"])
    vcb_ranks = ranks["VCB"]

    fact_val_q4 = {
        "fact_id": "fact:value:VCB:2024_Q4:bank.npl_g35",
        "fact_type": "value",
        "entity_id": "VCB",
        "other_entity_id": None,
        "universe_id": None,
        "metric_id": "bank.npl_g35",
        "period": "2024_Q4",
        "from_period": None,
        "value": vcb_q4_val,
        "unit": "%",
        "rank_better": None,
        "rank_desc": None,
        "denominator": None,
        "formula_version": "primary-observation-v1",
        "input_observation_ids": [obs_q4["observation_id"]],
        "input_fact_ids": [],
    }

    fact_val_q3 = {
        "fact_id": "fact:value:VCB:2024_Q3:bank.npl_g35",
        "fact_type": "value",
        "entity_id": "VCB",
        "other_entity_id": None,
        "universe_id": None,
        "metric_id": "bank.npl_g35",
        "period": "2024_Q3",
        "from_period": None,
        "value": vcb_q3_val,
        "unit": "%",
        "rank_better": None,
        "rank_desc": None,
        "denominator": None,
        "formula_version": "primary-observation-v1",
        "input_observation_ids": [obs_q3["observation_id"]],
        "input_fact_ids": [],
    }

    fact_rank = {
        "fact_id": "fact:peer_rank:VCB:sector:bank:2024_Q4:bank.npl_g35",
        "fact_type": "peer_rank",
        "entity_id": "VCB",
        "other_entity_id": None,
        "universe_id": "sector:bank",
        "metric_id": "bank.npl_g35",
        "period": "2024_Q4",
        "from_period": None,
        "value": float(vcb_ranks[0]),
        "unit": "rank",
        "rank_better": vcb_ranks[0],
        "rank_desc": vcb_ranks[1],
        "denominator": len(ALL_BANKS),
        "formula_version": "peer-rank-v1",
        "input_observation_ids": q4_obs_ids,
        "input_fact_ids": [fact_val_q4["fact_id"]],
    }

    fact_delta = {
        "fact_id": "fact:delta:VCB:2024_Q3_to_2024_Q4:bank.npl_g35",
        "fact_type": "delta",
        "entity_id": "VCB",
        "other_entity_id": None,
        "universe_id": None,
        "metric_id": "bank.npl_g35",
        "period": "2024_Q4",
        "from_period": "2024_Q3",
        "value": delta_q3_q4,
        "unit": "pp",
        "rank_better": None,
        "rank_desc": None,
        "denominator": None,
        "formula_version": "period-delta-v1",
        "input_observation_ids": [obs_q3["observation_id"], obs_q4["observation_id"]],
        "input_fact_ids": [fact_val_q3["fact_id"], fact_val_q4["fact_id"]],
    }

    fact_median = {
        "fact_id": "fact:peer_median:sector:bank:2024_Q4:bank.npl_g35",
        "fact_type": "peer_median",
        "entity_id": None,
        "other_entity_id": None,
        "universe_id": "sector:bank",
        "metric_id": "bank.npl_g35",
        "period": "2024_Q4",
        "from_period": None,
        "value": median_q4,
        "unit": "%",
        "rank_better": None,
        "rank_desc": None,
        "denominator": len(ALL_BANKS),
        "formula_version": "peer-median-v1",
        "input_observation_ids": q4_obs_ids,
        "input_fact_ids": [],
    }

    facts = [fact_val_q4, fact_val_q3, fact_rank, fact_delta, fact_median]

    # Dataset 1: KPI
    ds_kpi = {
        "dataset_id": "ds-vcb-npl-lookup",
        "shape": "kpi",
        "title": "tỷ lệ nợ xấu VCB, Q4/2024",
        "produced_by": {"tool": "lookup", "agent": "company"},
        "metric_ids": ["bank.npl_g35"],
        "periods": ["2024_Q4", "2024_Q3"],
        "highlight_entity_ids": ["VCB"],
        "rows": [
            {
                "entity_id": "VCB",
                "metric_id": "bank.npl_g35",
                "period": "2024_Q4",
                "status": "valid",
                "value": vcb_q4_val,
                "observation_id": obs_q4["observation_id"],
                "rank_better": vcb_ranks[0],
                "rank_desc": vcb_ranks[1],
                "missing_reason": None,
            },
            {
                "entity_id": "VCB",
                "metric_id": "bank.npl_g35",
                "period": "2024_Q3",
                "status": "valid",
                "value": vcb_q3_val,
                "observation_id": obs_q3["observation_id"],
                "rank_better": None,
                "rank_desc": None,
                "missing_reason": None,
            },
        ],
        "reference_lines": [
            {
                "kind": "median",
                "metric_id": "bank.npl_g35",
                "period": "2024_Q4",
                "value": median_q4,
                "fact_id": fact_median["fact_id"],
            }
        ],
        "allowed_charts": ["kpi_strip"],
    }

    # Dataset 2: Ranked list for peer context
    peer_rows = []
    for b in ALL_BANKS:
        o = db.get_obs(b, "bank.npl_g35", "2024_Q4")
        assert o
        b_ranks = ranks[b]
        peer_rows.append(
            {
                "entity_id": b,
                "metric_id": "bank.npl_g35",
                "period": "2024_Q4",
                "status": "valid",
                "value": float(o["value"]),
                "observation_id": o["observation_id"],
                "rank_better": b_ranks[0],
                "rank_desc": b_ranks[1],
                "missing_reason": None,
            }
        )
    # Sort peer rows by rank_better
    peer_rows.sort(key=lambda r: r["rank_better"])

    ds_peer = {
        "dataset_id": "ds-vcb-npl-peers-q4",
        "shape": "ranked_list",
        "title": "tỷ lệ nợ xấu các ngân hàng, Q4/2024",
        "produced_by": {"tool": "ranking", "agent": "sector"},
        "metric_ids": ["bank.npl_g35"],
        "periods": ["2024_Q4"],
        "highlight_entity_ids": ["VCB"],
        "rows": peer_rows,
        "reference_lines": [
            {
                "kind": "median",
                "metric_id": "bank.npl_g35",
                "period": "2024_Q4",
                "value": median_q4,
                "fact_id": fact_median["fact_id"],
            }
        ],
        "allowed_charts": ["ranked_bar", "comparison_table"],
    }

    report_spec = {
        "kind": "answer_card",
        "note_label": "Tra cứu nhanh",
        "blocks": [
            {
                "type": "answer",
                "value_fact_id": fact_val_q4["fact_id"],
                "sentences": [
                    {
                        "sentence_id": "s-ans-1",
                        "text": "Tỷ lệ nợ xấu của VCB quý 4/2024 đạt 0,96%.",
                        "fact_ids": [fact_val_q4["fact_id"]],
                        "author": "company",
                        "source": "model",
                        "revision": 0,
                    },
                    {
                        "sentence_id": "s-ans-2",
                        "text": "Mức nợ xấu này thấp nhất trong nhóm 5 ngân hàng và giảm 0,26 điểm phần trăm so với quý 3/2024.",
                        "fact_ids": [fact_rank["fact_id"], fact_delta["fact_id"]],
                        "author": "company",
                        "source": "model",
                        "revision": 0,
                    },
                ],
            }
        ],
    }

    source_notes = [
        format_source_note(
            db, 1, "VCB", "bank.npl_g35", "2024_Q4",
            [fact_val_q4["fact_id"], fact_rank["fact_id"], fact_delta["fact_id"]],
        ),
        format_source_note(
            db, 2, "VCB", "bank.npl_g35", "2024_Q3",
            [fact_val_q3["fact_id"], fact_delta["fact_id"]],
        ),
    ]

    return {
        "report_id": "rep-lookup-vcb-npl-2024q4",
        "status": "completed",
        "report_version": "er-report-v1",
        "question_type": "lookup",
        "analysis_plan": None,
        "macro_context": None,
        "sector_benchmark": None,
        "company_insights": [],
        "cross_level_critique": [],
        "atomic_claims": [],
        "evidence_trail": [],
        "revision_summary": None,
        "limitations": [],
        "synthesis_summary": "Tỷ lệ nợ xấu của VCB quý 4/2024 đạt 0,96%, giữ vị trí thấp nhất nhóm ngân hàng tham chiếu.",
        "synthesis_supporting_claim_ids": [],
        "facts": facts,
        "datasets": [ds_kpi, ds_peer],
        "report_spec": report_spec,
        "signals": [],
        "cross_level_findings": [],
        "narrative_audit": {
            "sentences_checked": 2,
            "sentences_accepted": 2,
            "sentences_dropped": [],
            "numbers_checked": 3,
            "numbers_matched": 3,
            "blocks_dropped": [],
            "composition_source": "model",
        },
        "source_notes": source_notes,
        "error": None,
    }


def build_er_ranking_fixture(db: GoldDatabase) -> Dict[str, Any]:
    """2. Ranking LLR Coverage Q4/2024."""
    # 5 banks Q4 coverage
    cov_pairs = []
    cov_obs_ids = []
    for b in ALL_BANKS:
        o = db.get_obs(b, "bank.llr_coverage", "2024_Q4")
        assert o
        cov_pairs.append((b, float(o["value"])))
        cov_obs_ids.append(o["observation_id"])

    cov_median = calc_median([v for _, v in cov_pairs])
    cov_ranks = calc_ranks(cov_pairs, METRIC_DIRECTIONS["bank.llr_coverage"])
    cov_spread = max(v for _, v in cov_pairs) - min(v for _, v in cov_pairs)

    facts = []

    # Facts: peer_rank for all 5 banks in coverage
    for b in ALL_BANKS:
        o = db.get_obs(b, "bank.llr_coverage", "2024_Q4")
        assert o
        r_better, r_desc = cov_ranks[b]
        facts.append(
            {
                "fact_id": f"fact:peer_rank:{b}:sector:bank:2024_Q4:bank.llr_coverage",
                "fact_type": "peer_rank",
                "entity_id": b,
                "other_entity_id": None,
                "universe_id": "sector:bank",
                "metric_id": "bank.llr_coverage",
                "period": "2024_Q4",
                "from_period": None,
                "value": float(r_better),
                "unit": "rank",
                "rank_better": r_better,
                "rank_desc": r_desc,
                "denominator": 5,
                "formula_version": "peer-rank-v1",
                "input_observation_ids": cov_obs_ids,
                "input_fact_ids": [],
            }
        )

    # Context metrics: NPL and ROA ranks for #1 (VCB) and #5 (VPB)
    for metric in ["bank.npl_g35", "bank.roa"]:
        m_pairs = []
        m_obs_ids = []
        for b in ALL_BANKS:
            o = db.get_obs(b, metric, "2024_Q4")
            assert o
            m_pairs.append((b, float(o["value"])))
            m_obs_ids.append(o["observation_id"])
        m_ranks = calc_ranks(m_pairs, METRIC_DIRECTIONS[metric])
        for b in ["VCB", "VPB"]:
            rb, rd = m_ranks[b]
            facts.append(
                {
                    "fact_id": f"fact:peer_rank:{b}:sector:bank:2024_Q4:{metric}",
                    "fact_type": "peer_rank",
                    "entity_id": b,
                    "other_entity_id": None,
                    "universe_id": "sector:bank",
                    "metric_id": metric,
                    "period": "2024_Q4",
                    "from_period": None,
                    "value": float(rb),
                    "unit": "rank",
                    "rank_better": rb,
                    "rank_desc": rd,
                    "denominator": 5,
                    "formula_version": "peer-rank-v1",
                    "input_observation_ids": m_obs_ids,
                    "input_fact_ids": [],
                }
            )

    # Ratio to median for VCB and VPB in coverage
    vcb_cov_obs = db.get_obs("VCB", "bank.llr_coverage", "2024_Q4")
    vpb_cov_obs = db.get_obs("VPB", "bank.llr_coverage", "2024_Q4")
    assert vcb_cov_obs and vpb_cov_obs
    vcb_cov_val = float(vcb_cov_obs["value"])
    vpb_cov_val = float(vpb_cov_obs["value"])

    ratio_vcb = vcb_cov_val / cov_median
    ratio_vpb = vpb_cov_val / cov_median

    facts.append(
        {
            "fact_id": "fact:ratio_to_median:VCB:sector:bank:2024_Q4:bank.llr_coverage",
            "fact_type": "ratio_to_median",
            "entity_id": "VCB",
            "other_entity_id": None,
            "universe_id": "sector:bank",
            "metric_id": "bank.llr_coverage",
            "period": "2024_Q4",
            "from_period": None,
            "value": ratio_vcb,
            "unit": "x",
            "rank_better": None,
            "rank_desc": None,
            "denominator": None,
            "formula_version": "ratio-to-median-v1",
            "input_observation_ids": cov_obs_ids,
            "input_fact_ids": [],
        }
    )

    facts.append(
        {
            "fact_id": "fact:ratio_to_median:VPB:sector:bank:2024_Q4:bank.llr_coverage",
            "fact_type": "ratio_to_median",
            "entity_id": "VPB",
            "other_entity_id": None,
            "universe_id": "sector:bank",
            "metric_id": "bank.llr_coverage",
            "period": "2024_Q4",
            "from_period": None,
            "value": ratio_vpb,
            "unit": "x",
            "rank_better": None,
            "rank_desc": None,
            "denominator": None,
            "formula_version": "ratio-to-median-v1",
            "input_observation_ids": cov_obs_ids,
            "input_fact_ids": [],
        }
    )

    # Spread
    facts.append(
        {
            "fact_id": "fact:spread:sector:bank:2024_Q4:bank.llr_coverage",
            "fact_type": "spread",
            "entity_id": None,
            "other_entity_id": None,
            "universe_id": "sector:bank",
            "metric_id": "bank.llr_coverage",
            "period": "2024_Q4",
            "from_period": None,
            "value": cov_spread,
            "unit": "pp",
            "rank_better": None,
            "rank_desc": None,
            "denominator": 5,
            "formula_version": "spread-v1",
            "input_observation_ids": cov_obs_ids,
            "input_fact_ids": [],
        }
    )

    # Values for VCB and VPB
    facts.append(
        {
            "fact_id": "fact:value:VCB:2024_Q4:bank.llr_coverage",
            "fact_type": "value",
            "entity_id": "VCB",
            "other_entity_id": None,
            "universe_id": None,
            "metric_id": "bank.llr_coverage",
            "period": "2024_Q4",
            "from_period": None,
            "value": vcb_cov_val,
            "unit": "%",
            "rank_better": None,
            "rank_desc": None,
            "denominator": None,
            "formula_version": "primary-observation-v1",
            "input_observation_ids": [vcb_cov_obs["observation_id"]],
            "input_fact_ids": [],
        }
    )
    facts.append(
        {
            "fact_id": "fact:value:VPB:2024_Q4:bank.llr_coverage",
            "fact_type": "value",
            "entity_id": "VPB",
            "other_entity_id": None,
            "universe_id": None,
            "metric_id": "bank.llr_coverage",
            "period": "2024_Q4",
            "from_period": None,
            "value": vpb_cov_val,
            "unit": "%",
            "rank_better": None,
            "rank_desc": None,
            "denominator": None,
            "formula_version": "primary-observation-v1",
            "input_observation_ids": [vpb_cov_obs["observation_id"]],
            "input_fact_ids": [],
        }
    )

    # Peer median fact
    fact_med = {
        "fact_id": "fact:peer_median:sector:bank:2024_Q4:bank.llr_coverage",
        "fact_type": "peer_median",
        "entity_id": None,
        "other_entity_id": None,
        "universe_id": "sector:bank",
        "metric_id": "bank.llr_coverage",
        "period": "2024_Q4",
        "from_period": None,
        "value": cov_median,
        "unit": "%",
        "rank_better": None,
        "rank_desc": None,
        "denominator": 5,
        "formula_version": "peer-median-v1",
        "input_observation_ids": cov_obs_ids,
        "input_fact_ids": [],
    }
    facts.append(fact_med)

    # Dataset 1: ranked_list coverage
    ranked_rows = []
    for b in ALL_BANKS:
        o = db.get_obs(b, "bank.llr_coverage", "2024_Q4")
        assert o
        rb, rd = cov_ranks[b]
        ranked_rows.append(
            {
                "entity_id": b,
                "metric_id": "bank.llr_coverage",
                "period": "2024_Q4",
                "status": "valid",
                "value": float(o["value"]),
                "observation_id": o["observation_id"],
                "rank_better": rb,
                "rank_desc": rd,
                "missing_reason": None,
            }
        )
    ranked_rows.sort(key=lambda r: r["rank_better"])

    ds_ranked = {
        "dataset_id": "ds-ranked-coverage-2024q4",
        "shape": "ranked_list",
        "title": "tỷ lệ bao phủ nợ xấu, Q4/2024",
        "produced_by": {"tool": "ranking", "agent": "sector"},
        "metric_ids": ["bank.llr_coverage"],
        "periods": ["2024_Q4"],
        "highlight_entity_ids": ["VCB"],
        "rows": ranked_rows,
        "reference_lines": [
            {
                "kind": "median",
                "metric_id": "bank.llr_coverage",
                "period": "2024_Q4",
                "value": cov_median,
                "fact_id": fact_med["fact_id"],
            }
        ],
        "allowed_charts": ["ranked_bar", "comparison_table"],
    }

    # Dataset 2: context metrics peer_table (npl_g35 and roa)
    ctx_rows = []
    for m in ["bank.npl_g35", "bank.roa"]:
        m_pairs = [(b, float(db.get_obs(b, m, "2024_Q4")["value"])) for b in ALL_BANKS]
        m_ranks = calc_ranks(m_pairs, METRIC_DIRECTIONS[m])
        for b in ALL_BANKS:
            o = db.get_obs(b, m, "2024_Q4")
            assert o
            rb, rd = m_ranks[b]
            ctx_rows.append(
                {
                    "entity_id": b,
                    "metric_id": m,
                    "period": "2024_Q4",
                    "status": "valid",
                    "value": float(o["value"]),
                    "observation_id": o["observation_id"],
                    "rank_better": rb,
                    "rank_desc": rd,
                    "missing_reason": None,
                }
            )

    ds_ctx = {
        "dataset_id": "ds-ranking-context-metrics",
        "shape": "peer_table",
        "title": "chỉ tiêu chất lượng nợ và sinh lời bổ trợ, Q4/2024",
        "produced_by": {"tool": "ranking", "agent": "sector"},
        "metric_ids": ["bank.npl_g35", "bank.roa"],
        "periods": ["2024_Q4"],
        "highlight_entity_ids": ["VCB", "VPB"],
        "rows": ctx_rows,
        "reference_lines": [],
        "allowed_charts": ["rank_heatmap", "comparison_table"],
    }

    report_spec = {
        "kind": "note",
        "note_label": "Ghi chú sàng lọc · Ngân hàng",
        "blocks": [
            {
                "type": "headline",
                "sentence": {
                    "sentence_id": "s-rank-head",
                    "text": "VCB có đệm bao phủ nợ xấu cao nhất, gấp 2,42 lần trung vị nhóm.",
                    "fact_ids": [
                        "fact:peer_rank:VCB:sector:bank:2024_Q4:bank.llr_coverage",
                        "fact:ratio_to_median:VCB:sector:bank:2024_Q4:bank.llr_coverage",
                    ],
                    "author": "sector",
                    "source": "model",
                    "revision": 0,
                },
            },
            {
                "type": "figure",
                "figure_no": 1,
                "chart": "ranked_bar",
                "dataset_id": "ds-ranked-coverage-2024q4",
                "title": "tỷ lệ bao phủ nợ xấu, Q4/2024",
                "takeaway": {
                    "sentence_id": "s-rank-fig",
                    "text": "VCB dẫn đầu nhóm với tỷ lệ bao phủ 223,31%, trong khi VPB xếp vị trí thấp nhất ở mức 56,17%.",
                    "fact_ids": [
                        "fact:value:VCB:2024_Q4:bank.llr_coverage",
                        "fact:peer_rank:VCB:sector:bank:2024_Q4:bank.llr_coverage",
                        "fact:value:VPB:2024_Q4:bank.llr_coverage",
                        "fact:peer_rank:VPB:sector:bank:2024_Q4:bank.llr_coverage",
                    ],
                    "author": "sector",
                    "source": "model",
                    "revision": 0,
                },
            },
            {
                "type": "key_points",
                "items": [
                    {
                        "title": "Chênh lệch lớn",
                        "sentences": [
                            {
                                "sentence_id": "s-rank-kp1",
                                "text": "Khoảng cách giữa ngân hàng dẫn đầu và thấp nhất đạt 167,14 điểm phần trăm.",
                                "fact_ids": [
                                    "fact:spread:sector:bank:2024_Q4:bank.llr_coverage",
                                    "fact:peer_rank:VCB:sector:bank:2024_Q4:bank.llr_coverage",
                                    "fact:peer_rank:VPB:sector:bank:2024_Q4:bank.llr_coverage",
                                ],
                                "author": "sector",
                                "source": "model",
                                "revision": 0,
                            }
                        ],
                    }
                ],
            },
            {
                "type": "callout",
                "tone": "notice",
                "title": "Lưu ý chéo",
                "finding_id": "f-cross-extreme-vcb-vpb",
                "sentences": [
                    {
                        "sentence_id": "s-rank-call",
                        "text": "VCB xếp thứ nhất về bao phủ nợ xấu nhưng xếp thứ 5 về ROA; VPB xếp thứ 5 ở cả bao phủ và nợ xấu.",
                        "fact_ids": [
                            "fact:peer_rank:VCB:sector:bank:2024_Q4:bank.llr_coverage",
                            "fact:peer_rank:VCB:sector:bank:2024_Q4:bank.roa",
                            "fact:peer_rank:VPB:sector:bank:2024_Q4:bank.llr_coverage",
                            "fact:peer_rank:VPB:sector:bank:2024_Q4:bank.npl_g35",
                        ],
                        "author": "critic",
                        "source": "model",
                        "revision": 0,
                    }
                ],
            },
        ],
    }

    source_notes = [
        format_source_note(
            db, 1, "VCB", "bank.llr_coverage", "2024_Q4",
            [
                "fact:value:VCB:2024_Q4:bank.llr_coverage",
                "fact:peer_rank:VCB:sector:bank:2024_Q4:bank.llr_coverage",
                "fact:ratio_to_median:VCB:sector:bank:2024_Q4:bank.llr_coverage",
                "fact:spread:sector:bank:2024_Q4:bank.llr_coverage",
            ],
        ),
        format_source_note(
            db, 2, "VPB", "bank.llr_coverage", "2024_Q4",
            [
                "fact:value:VPB:2024_Q4:bank.llr_coverage",
                "fact:peer_rank:VPB:sector:bank:2024_Q4:bank.llr_coverage",
                "fact:ratio_to_median:VPB:sector:bank:2024_Q4:bank.llr_coverage",
                "fact:spread:sector:bank:2024_Q4:bank.llr_coverage",
            ],
        ),
        format_source_note(
            db, 3, "TCB", "bank.llr_coverage", "2024_Q4",
            ["fact:peer_rank:TCB:sector:bank:2024_Q4:bank.llr_coverage"],
        ),
        format_source_note(
            db, 4, "MBB", "bank.llr_coverage", "2024_Q4",
            ["fact:peer_rank:MBB:sector:bank:2024_Q4:bank.llr_coverage"],
        ),
        format_source_note(
            db, 5, "ACB", "bank.llr_coverage", "2024_Q4",
            ["fact:peer_rank:ACB:sector:bank:2024_Q4:bank.llr_coverage"],
        ),
        format_source_note(
            db, 6, "VCB", "bank.roa", "2024_Q4",
            ["fact:peer_rank:VCB:sector:bank:2024_Q4:bank.roa"],
        ),
        format_source_note(
            db, 7, "VPB", "bank.npl_g35", "2024_Q4",
            ["fact:peer_rank:VPB:sector:bank:2024_Q4:bank.npl_g35"],
        ),
    ]

    return {
        "report_id": "rep-ranking-coverage-2024q4",
        "status": "completed",
        "report_version": "er-report-v1",
        "question_type": "ranking",
        "analysis_plan": None,
        "macro_context": None,
        "sector_benchmark": None,
        "company_insights": [],
        "cross_level_critique": [],
        "atomic_claims": [],
        "evidence_trail": [],
        "revision_summary": None,
        "limitations": [],
        "synthesis_summary": "VCB dẫn đầu ngành về tỷ lệ bao phủ nợ xấu trong khi VPB có mức đệm dự phòng mỏng nhất.",
        "synthesis_supporting_claim_ids": [],
        "facts": facts,
        "datasets": [ds_ranked, ds_ctx],
        "report_spec": report_spec,
        "signals": [],
        "cross_level_findings": [
            {
                "finding_id": "f-cross-extreme-vcb-vpb",
                "kind": "cross_metric_extreme",
                "severity": "notice",
                "text": "VCB dẫn đầu bao phủ nhưng xếp cuối ROA; VPB đứng cuối ở cả hai chỉ tiêu rủi ro tín dụng.",
                "fact_ids": [
                    "fact:peer_rank:VCB:sector:bank:2024_Q4:bank.llr_coverage",
                    "fact:peer_rank:VCB:sector:bank:2024_Q4:bank.roa",
                    "fact:peer_rank:VPB:sector:bank:2024_Q4:bank.llr_coverage",
                    "fact:peer_rank:VPB:sector:bank:2024_Q4:bank.npl_g35",
                ],
                "status": "confirmed",
            }
        ],
        "narrative_audit": {
            "sentences_checked": 4,
            "sentences_accepted": 4,
            "sentences_dropped": [],
            "numbers_checked": 7,
            "numbers_matched": 7,
            "blocks_dropped": [],
            "composition_source": "model",
        },
        "source_notes": source_notes,
        "error": None,
    }


def build_er_trend_fixture(db: GoldDatabase) -> Dict[str, Any]:
    """3. Trend VPB ROE 2024."""
    vpb_obs = {p: db.get_obs("VPB", "bank.roe", p) for p in ALL_PERIODS}
    vpb_vals = {p: float(vpb_obs[p]["value"]) for p in ALL_PERIODS}

    # Quarterly medians for ROE
    medians: Dict[str, float] = {}
    for p in ALL_PERIODS:
        p_vals = []
        for b in ALL_BANKS:
            o = db.get_obs(b, "bank.roe", p)
            if o and o["value"] is not None:
                p_vals.append(float(o["value"]))
        medians[p] = calc_median(p_vals)

    delta_q1_q2 = vpb_vals["2024_Q2"] - vpb_vals["2024_Q1"]
    delta_q2_q3 = vpb_vals["2024_Q3"] - vpb_vals["2024_Q2"]
    delta_q3_q4 = vpb_vals["2024_Q4"] - vpb_vals["2024_Q3"]
    delta_q1_q4 = vpb_vals["2024_Q4"] - vpb_vals["2024_Q1"]
    med_delta_q3_q4 = medians["2024_Q4"] - medians["2024_Q3"]

    gap_q1 = vpb_vals["2024_Q1"] - medians["2024_Q1"]
    gap_q4 = vpb_vals["2024_Q4"] - medians["2024_Q4"]

    # Q4 peer rank for VPB ROE
    q4_pairs = [(b, float(db.get_obs(b, "bank.roe", "2024_Q4")["value"])) for b in ALL_BANKS]
    q4_ranks = calc_ranks(q4_pairs, METRIC_DIRECTIONS["bank.roe"])
    vpb_q4_rank = q4_ranks["VPB"]

    facts = []

    # Values for VPB ROE
    for p in ALL_PERIODS:
        facts.append(
            {
                "fact_id": f"fact:value:VPB:{p}:bank.roe",
                "fact_type": "value",
                "entity_id": "VPB",
                "other_entity_id": None,
                "universe_id": None,
                "metric_id": "bank.roe",
                "period": p,
                "from_period": None,
                "value": vpb_vals[p],
                "unit": "%",
                "rank_better": None,
                "rank_desc": None,
                "denominator": None,
                "formula_version": "primary-observation-v1",
                "input_observation_ids": [vpb_obs[p]["observation_id"]],
                "input_fact_ids": [],
            }
        )

    # Deltas
    deltas_info = [
        ("2024_Q1", "2024_Q2", delta_q1_q2),
        ("2024_Q2", "2024_Q3", delta_q2_q3),
        ("2024_Q3", "2024_Q4", delta_q3_q4),
        ("2024_Q1", "2024_Q4", delta_q1_q4),
    ]
    for p_from, p_to, d_val in deltas_info:
        facts.append(
            {
                "fact_id": f"fact:delta:VPB:{p_from}_to_{p_to}:bank.roe",
                "fact_type": "delta",
                "entity_id": "VPB",
                "other_entity_id": None,
                "universe_id": None,
                "metric_id": "bank.roe",
                "period": p_to,
                "from_period": p_from,
                "value": d_val,
                "unit": "pp",
                "rank_better": None,
                "rank_desc": None,
                "denominator": None,
                "formula_version": "period-delta-v1",
                "input_observation_ids": [vpb_obs[p_from]["observation_id"], vpb_obs[p_to]["observation_id"]],
                "input_fact_ids": [f"fact:value:VPB:{p_from}:bank.roe", f"fact:value:VPB:{p_to}:bank.roe"],
            }
        )

    # Medians
    for p in ALL_PERIODS:
        obs_ids = [db.get_obs(b, "bank.roe", p)["observation_id"] for b in ALL_BANKS if db.get_obs(b, "bank.roe", p) and db.get_obs(b, "bank.roe", p)["value"] is not None]
        facts.append(
            {
                "fact_id": f"fact:peer_median:sector:bank:{p}:bank.roe",
                "fact_type": "peer_median",
                "entity_id": None,
                "other_entity_id": None,
                "universe_id": "sector:bank",
                "metric_id": "bank.roe",
                "period": p,
                "from_period": None,
                "value": medians[p],
                "unit": "%",
                "rank_better": None,
                "rank_desc": None,
                "denominator": len(obs_ids),
                "formula_version": "peer-median-v1",
                "input_observation_ids": obs_ids,
                "input_fact_ids": [],
            }
        )

    # Median delta Q3->Q4
    q3_obs_ids = [db.get_obs(b, "bank.roe", "2024_Q3")["observation_id"] for b in ALL_BANKS]
    q4_obs_ids = [db.get_obs(b, "bank.roe", "2024_Q4")["observation_id"] for b in ALL_BANKS]
    facts.append(
        {
            "fact_id": "fact:median_delta:sector:bank:2024_Q3_to_2024_Q4:bank.roe",
            "fact_type": "median_delta",
            "entity_id": None,
            "other_entity_id": None,
            "universe_id": "sector:bank",
            "metric_id": "bank.roe",
            "period": "2024_Q4",
            "from_period": "2024_Q3",
            "value": med_delta_q3_q4,
            "unit": "pp",
            "rank_better": None,
            "rank_desc": None,
            "denominator": 5,
            "formula_version": "median-delta-v1",
            "input_observation_ids": q3_obs_ids + q4_obs_ids,
            "input_fact_ids": [],
        }
    )

    # Gaps Q1 and Q4
    facts.append(
        {
            "fact_id": "fact:gap_to_median:VPB:sector:bank:2024_Q1:bank.roe",
            "fact_type": "gap_to_median",
            "entity_id": "VPB",
            "other_entity_id": None,
            "universe_id": "sector:bank",
            "metric_id": "bank.roe",
            "period": "2024_Q1",
            "from_period": None,
            "value": gap_q1,
            "unit": "pp",
            "rank_better": None,
            "rank_desc": None,
            "denominator": None,
            "formula_version": "gap-to-median-v1",
            "input_observation_ids": [vpb_obs["2024_Q1"]["observation_id"]],
            "input_fact_ids": [],
        }
    )
    facts.append(
        {
            "fact_id": "fact:gap_to_median:VPB:sector:bank:2024_Q4:bank.roe",
            "fact_type": "gap_to_median",
            "entity_id": "VPB",
            "other_entity_id": None,
            "universe_id": "sector:bank",
            "metric_id": "bank.roe",
            "period": "2024_Q4",
            "from_period": None,
            "value": gap_q4,
            "unit": "pp",
            "rank_better": None,
            "rank_desc": None,
            "denominator": None,
            "formula_version": "gap-to-median-v1",
            "input_observation_ids": [vpb_obs["2024_Q4"]["observation_id"]],
            "input_fact_ids": [],
        }
    )

    # Q4 rank_better=5, rank_desc=5
    facts.append(
        {
            "fact_id": "fact:peer_rank:VPB:sector:bank:2024_Q4:bank.roe",
            "fact_type": "peer_rank",
            "entity_id": "VPB",
            "other_entity_id": None,
            "universe_id": "sector:bank",
            "metric_id": "bank.roe",
            "period": "2024_Q4",
            "from_period": None,
            "value": float(vpb_q4_rank[0]),
            "unit": "rank",
            "rank_better": vpb_q4_rank[0],
            "rank_desc": vpb_q4_rank[1],
            "denominator": 5,
            "formula_version": "peer-rank-v1",
            "input_observation_ids": q4_obs_ids,
            "input_fact_ids": [],
        }
    )

    # Dataset 1: series
    series_rows = []
    for p in ALL_PERIODS:
        series_rows.append(
            {
                "entity_id": "VPB",
                "metric_id": "bank.roe",
                "period": p,
                "status": "valid",
                "value": vpb_vals[p],
                "observation_id": vpb_obs[p]["observation_id"],
                "rank_better": None,
                "rank_desc": None,
                "missing_reason": None,
            }
        )

    ref_lines = [
        {
            "kind": "median",
            "metric_id": "bank.roe",
            "period": p,
            "value": medians[p],
            "fact_id": f"fact:peer_median:sector:bank:{p}:bank.roe",
        }
        for p in ALL_PERIODS
    ]

    ds_series = {
        "dataset_id": "ds-vpb-roe-trend",
        "shape": "series",
        "title": "diễn biến ROE của VPB qua các quý năm 2024",
        "produced_by": {"tool": "trend", "agent": "company"},
        "metric_ids": ["bank.roe"],
        "periods": ALL_PERIODS,
        "highlight_entity_ids": ["VPB"],
        "rows": series_rows,
        "reference_lines": ref_lines,
        "allowed_charts": ["line_trend"],
    }

    # Dataset 2: ranked_list for Q4 peer ranking
    peer_rows_q4 = []
    for b in ALL_BANKS:
        o = db.get_obs(b, "bank.roe", "2024_Q4")
        assert o
        rb, rd = q4_ranks[b]
        peer_rows_q4.append(
            {
                "entity_id": b,
                "metric_id": "bank.roe",
                "period": "2024_Q4",
                "status": "valid",
                "value": float(o["value"]),
                "observation_id": o["observation_id"],
                "rank_better": rb,
                "rank_desc": rd,
                "missing_reason": None,
            }
        )
    peer_rows_q4.sort(key=lambda r: r["rank_better"])

    ds_peer_q4 = {
        "dataset_id": "ds-vpb-roe-peers-q4",
        "shape": "ranked_list",
        "title": "xếp hạng ROE các ngân hàng, Q4/2024",
        "produced_by": {"tool": "ranking", "agent": "sector"},
        "metric_ids": ["bank.roe"],
        "periods": ["2024_Q4"],
        "highlight_entity_ids": ["VPB"],
        "rows": peer_rows_q4,
        "reference_lines": [
            {
                "kind": "median",
                "metric_id": "bank.roe",
                "period": "2024_Q4",
                "value": medians["2024_Q4"],
                "fact_id": "fact:peer_median:sector:bank:2024_Q4:bank.roe",
            }
        ],
        "allowed_charts": ["ranked_bar", "comparison_table"],
    }

    report_spec = {
        "kind": "note",
        "note_label": "Ghi chú xu hướng · Ngân hàng",
        "blocks": [
            {
                "type": "headline",
                "sentence": {
                    "sentence_id": "s-trend-head",
                    "text": "ROE của VPB tăng 3,34 điểm phần trăm trong năm 2024 dù xếp vị trí thứ 5 trong nhóm.",
                    "fact_ids": [
                        "fact:delta:VPB:2024_Q1_to_2024_Q4:bank.roe",
                        "fact:peer_rank:VPB:sector:bank:2024_Q4:bank.roe",
                    ],
                    "author": "company",
                    "source": "model",
                    "revision": 0,
                },
            },
            {
                "type": "figure",
                "figure_no": 1,
                "chart": "line_trend",
                "dataset_id": "ds-vpb-roe-trend",
                "title": "diễn biến ROE của VPB qua các quý năm 2024",
                "takeaway": {
                    "sentence_id": "s-trend-fig",
                    "text": "Chỉ số ROE tăng liên tục từ 8,07% lên 11,41% qua các quý.",
                    "fact_ids": [
                        "fact:value:VPB:2024_Q1:bank.roe",
                        "fact:value:VPB:2024_Q4:bank.roe",
                        "fact:delta:VPB:2024_Q1_to_2024_Q2:bank.roe",
                        "fact:delta:VPB:2024_Q2_to_2024_Q3:bank.roe",
                        "fact:delta:VPB:2024_Q3_to_2024_Q4:bank.roe",
                    ],
                    "author": "company",
                    "source": "model",
                    "revision": 0,
                },
            },
            {
                "type": "key_points",
                "items": [
                    {
                        "title": "Thu hẹp khoảng cách",
                        "sentences": [
                            {
                                "sentence_id": "s-trend-kp1",
                                "text": "Chênh lệch so với trung vị nhóm thu hẹp từ 9,39 điểm phần trăm ở quý 1 xuống 7,18 điểm phần trăm ở quý 4.",
                                "fact_ids": [
                                    "fact:gap_to_median:VPB:sector:bank:2024_Q1:bank.roe",
                                    "fact:gap_to_median:VPB:sector:bank:2024_Q4:bank.roe",
                                    "fact:delta:VPB:2024_Q1_to_2024_Q4:bank.roe",
                                ],
                                "author": "company",
                                "source": "model",
                                "revision": 0,
                            }
                        ],
                    }
                ],
            },
            {
                "type": "callout",
                "tone": "notice",
                "title": "Nghịch xu hướng",
                "finding_id": "f-trend-vpb-counter",
                "sentences": [
                    {
                        "sentence_id": "s-trend-call",
                        "text": "Trong quý 4/2024, ROE của VPB tăng 1,77 điểm phần trăm, ngược chiều với mức giảm 0,94 điểm phần trăm của trung vị nhóm.",
                        "fact_ids": [
                            "fact:delta:VPB:2024_Q3_to_2024_Q4:bank.roe",
                            "fact:median_delta:sector:bank:2024_Q3_to_2024_Q4:bank.roe",
                        ],
                        "author": "critic",
                        "source": "model",
                        "revision": 0,
                    }
                ],
            },
        ],
    }

    source_notes = [
        format_source_note(
            db, 1, "VPB", "bank.roe", "2024_Q1",
            [
                "fact:value:VPB:2024_Q1:bank.roe",
                "fact:gap_to_median:VPB:sector:bank:2024_Q1:bank.roe",
                "fact:delta:VPB:2024_Q1_to_2024_Q2:bank.roe",
                "fact:delta:VPB:2024_Q1_to_2024_Q4:bank.roe",
            ],
        ),
        format_source_note(
            db, 2, "VPB", "bank.roe", "2024_Q2",
            [
                "fact:value:VPB:2024_Q2:bank.roe",
                "fact:delta:VPB:2024_Q1_to_2024_Q2:bank.roe",
                "fact:delta:VPB:2024_Q2_to_2024_Q3:bank.roe",
            ],
        ),
        format_source_note(
            db, 3, "VPB", "bank.roe", "2024_Q3",
            [
                "fact:value:VPB:2024_Q3:bank.roe",
                "fact:delta:VPB:2024_Q2_to_2024_Q3:bank.roe",
                "fact:delta:VPB:2024_Q3_to_2024_Q4:bank.roe",
            ],
        ),
        format_source_note(
            db, 4, "VPB", "bank.roe", "2024_Q4",
            [
                "fact:value:VPB:2024_Q4:bank.roe",
                "fact:gap_to_median:VPB:sector:bank:2024_Q4:bank.roe",
                "fact:peer_rank:VPB:sector:bank:2024_Q4:bank.roe",
                "fact:delta:VPB:2024_Q1_to_2024_Q4:bank.roe",
                "fact:delta:VPB:2024_Q3_to_2024_Q4:bank.roe",
            ],
        ),
    ]

    return {
        "report_id": "rep-trend-vpb-roe-2024",
        "status": "completed",
        "report_version": "er-report-v1",
        "question_type": "trend",
        "analysis_plan": None,
        "macro_context": None,
        "sector_benchmark": None,
        "company_insights": [],
        "cross_level_critique": [],
        "atomic_claims": [],
        "evidence_trail": [],
        "revision_summary": None,
        "limitations": [],
        "synthesis_summary": "ROE của VPB cải thiện liên tục qua 4 quý nhưng vẫn giữ vị trí thấp nhất nhóm 5 ngân hàng.",
        "synthesis_supporting_claim_ids": [],
        "facts": facts,
        "datasets": [ds_series, ds_peer_q4],
        "report_spec": report_spec,
        "signals": [],
        "cross_level_findings": [
            {
                "finding_id": "f-trend-vpb-counter",
                "kind": "counter_trend",
                "severity": "notice",
                "text": "VPB tăng trưởng ROE trong quý 4 ngược lại với xu hướng giảm của trung vị toàn ngành.",
                "fact_ids": [
                    "fact:delta:VPB:2024_Q3_to_2024_Q4:bank.roe",
                    "fact:median_delta:sector:bank:2024_Q3_to_2024_Q4:bank.roe",
                ],
                "status": "confirmed",
            }
        ],
        "narrative_audit": {
            "sentences_checked": 4,
            "sentences_accepted": 4,
            "sentences_dropped": [],
            "numbers_checked": 8,
            "numbers_matched": 8,
            "blocks_dropped": [],
            "composition_source": "model",
        },
        "source_notes": source_notes,
        "error": None,
    }


def build_er_h2h_fixture(db: GoldDatabase) -> Dict[str, Any]:
    """4. Head-to-Head ACB vs TCB Q4/2024."""
    metrics = ALL_METRICS
    acb_obs = {m: db.get_obs("ACB", m, "2024_Q4") for m in metrics}
    tcb_obs = {m: db.get_obs("TCB", m, "2024_Q4") for m in metrics}

    acb_vals = {m: float(acb_obs[m]["value"]) for m in metrics}
    tcb_vals = {m: float(tcb_obs[m]["value"]) for m in metrics}

    facts = []

    # Values
    for m in metrics:
        facts.append(
            {
                "fact_id": f"fact:value:ACB:2024_Q4:{m}",
                "fact_type": "value",
                "entity_id": "ACB",
                "other_entity_id": None,
                "universe_id": None,
                "metric_id": m,
                "period": "2024_Q4",
                "from_period": None,
                "value": acb_vals[m],
                "unit": "%",
                "rank_better": None,
                "rank_desc": None,
                "denominator": None,
                "formula_version": "primary-observation-v1",
                "input_observation_ids": [acb_obs[m]["observation_id"]],
                "input_fact_ids": [],
            }
        )
        facts.append(
            {
                "fact_id": f"fact:value:TCB:2024_Q4:{m}",
                "fact_type": "value",
                "entity_id": "TCB",
                "other_entity_id": None,
                "universe_id": None,
                "metric_id": m,
                "period": "2024_Q4",
                "from_period": None,
                "value": tcb_vals[m],
                "unit": "%",
                "rank_better": None,
                "rank_desc": None,
                "denominator": None,
                "formula_version": "primary-observation-v1",
                "input_observation_ids": [tcb_obs[m]["observation_id"]],
                "input_fact_ids": [],
            }
        )

    # Pairwise gaps (ACB - TCB)
    pairwise_gaps = {}
    for m in metrics:
        gap = acb_vals[m] - tcb_vals[m]
        pairwise_gaps[m] = gap
        facts.append(
            {
                "fact_id": f"fact:pairwise_gap:ACB:vs:TCB:2024_Q4:{m}",
                "fact_type": "pairwise_gap",
                "entity_id": "ACB",
                "other_entity_id": "TCB",
                "universe_id": None,
                "metric_id": m,
                "period": "2024_Q4",
                "from_period": None,
                "value": gap,
                "unit": "pp",
                "rank_better": None,
                "rank_desc": None,
                "denominator": None,
                "formula_version": "pairwise-gap-v1",
                "input_observation_ids": [acb_obs[m]["observation_id"], tcb_obs[m]["observation_id"]],
                "input_fact_ids": [f"fact:value:ACB:2024_Q4:{m}", f"fact:value:TCB:2024_Q4:{m}"],
            }
        )

    # Lead counts
    tcb_leads = 0
    acb_leads = 0
    for m in metrics:
        if METRIC_DIRECTIONS[m] == "lower_is_better":
            if tcb_vals[m] < acb_vals[m]:
                tcb_leads += 1
            elif acb_vals[m] < tcb_vals[m]:
                acb_leads += 1
        else:
            if tcb_vals[m] > acb_vals[m]:
                tcb_leads += 1
            elif acb_vals[m] > tcb_vals[m]:
                acb_leads += 1

    facts.append(
        {
            "fact_id": "fact:lead_count:TCB:vs:ACB:2024_Q4",
            "fact_type": "lead_count",
            "entity_id": "TCB",
            "other_entity_id": "ACB",
            "universe_id": None,
            "metric_id": "comparison.overall",
            "period": "2024_Q4",
            "from_period": None,
            "value": float(tcb_leads),
            "unit": "count",
            "rank_better": None,
            "rank_desc": None,
            "denominator": len(metrics),
            "formula_version": "lead-count-v1",
            "input_observation_ids": [o["observation_id"] for o in list(acb_obs.values()) + list(tcb_obs.values())],
            "input_fact_ids": [],
        }
    )

    facts.append(
        {
            "fact_id": "fact:lead_count:ACB:vs:TCB:2024_Q4",
            "fact_type": "lead_count",
            "entity_id": "ACB",
            "other_entity_id": "TCB",
            "universe_id": None,
            "metric_id": "comparison.overall",
            "period": "2024_Q4",
            "from_period": None,
            "value": float(acb_leads),
            "unit": "count",
            "rank_better": None,
            "rank_desc": None,
            "denominator": len(metrics),
            "formula_version": "lead-count-v1",
            "input_observation_ids": [o["observation_id"] for o in list(acb_obs.values()) + list(tcb_obs.values())],
            "input_fact_ids": [],
        }
    )

    # Derived ratio ROE/ROA
    ratio_acb = acb_vals["bank.roe"] / acb_vals["bank.roa"]
    ratio_tcb = tcb_vals["bank.roe"] / tcb_vals["bank.roa"]

    facts.append(
        {
            "fact_id": "fact:derived_ratio:ACB:2024_Q4:derived.roe_over_roa",
            "fact_type": "derived_ratio",
            "entity_id": "ACB",
            "other_entity_id": None,
            "universe_id": None,
            "metric_id": "derived.roe_over_roa",
            "period": "2024_Q4",
            "from_period": None,
            "value": ratio_acb,
            "unit": "x",
            "rank_better": None,
            "rank_desc": None,
            "denominator": None,
            "formula_version": "derived-ratio-v1",
            "input_observation_ids": [acb_obs["bank.roe"]["observation_id"], acb_obs["bank.roa"]["observation_id"]],
            "input_fact_ids": ["fact:value:ACB:2024_Q4:bank.roe", "fact:value:ACB:2024_Q4:bank.roa"],
        }
    )

    facts.append(
        {
            "fact_id": "fact:derived_ratio:TCB:2024_Q4:derived.roe_over_roa",
            "fact_type": "derived_ratio",
            "entity_id": "TCB",
            "other_entity_id": None,
            "universe_id": None,
            "metric_id": "derived.roe_over_roa",
            "period": "2024_Q4",
            "from_period": None,
            "value": ratio_tcb,
            "unit": "x",
            "rank_better": None,
            "rank_desc": None,
            "denominator": None,
            "formula_version": "derived-ratio-v1",
            "input_observation_ids": [tcb_obs["bank.roe"]["observation_id"], tcb_obs["bank.roa"]["observation_id"]],
            "input_fact_ids": ["fact:value:TCB:2024_Q4:bank.roe", "fact:value:TCB:2024_Q4:bank.roa"],
        }
    )

    # Dataset: comparison_table
    table_rows = []
    for m in metrics:
        table_rows.append(
            {
                "entity_id": "ACB",
                "metric_id": m,
                "period": "2024_Q4",
                "status": "valid",
                "value": acb_vals[m],
                "observation_id": acb_obs[m]["observation_id"],
                "rank_better": None,
                "rank_desc": None,
                "missing_reason": None,
            }
        )
        table_rows.append(
            {
                "entity_id": "TCB",
                "metric_id": m,
                "period": "2024_Q4",
                "status": "valid",
                "value": tcb_vals[m],
                "observation_id": tcb_obs[m]["observation_id"],
                "rank_better": None,
                "rank_desc": None,
                "missing_reason": None,
            }
        )

    ds_comp = {
        "dataset_id": "ds-h2h-acb-tcb-2024q4",
        "shape": "comparison_table",
        "title": "so sánh 4 chỉ tiêu tài chính giữa ACB và TCB, Q4/2024",
        "produced_by": {"tool": "head_to_head", "agent": "company"},
        "metric_ids": metrics,
        "periods": ["2024_Q4"],
        "highlight_entity_ids": ["ACB", "TCB"],
        "rows": table_rows,
        "reference_lines": [],
        "allowed_charts": ["comparison_table", "grouped_bar"],
    }

    report_spec = {
        "kind": "note",
        "note_label": "Ghi chú so sánh · Ngân hàng",
        "blocks": [
            {
                "type": "headline",
                "sentence": {
                    "sentence_id": "s-h2h-head",
                    "text": "TCB nhỉnh hơn ACB ở 3/4 chỉ tiêu tài chính, trong khi ACB duy trì tỷ suất ROE cao hơn.",
                    "fact_ids": [
                        "fact:lead_count:TCB:vs:ACB:2024_Q4",
                        "fact:lead_count:ACB:vs:TCB:2024_Q4",
                        "fact:pairwise_gap:ACB:vs:TCB:2024_Q4:bank.roe",
                    ],
                    "author": "company",
                    "source": "model",
                    "revision": 0,
                },
            },
            {
                "type": "figure",
                "figure_no": 1,
                "chart": "comparison_table",
                "dataset_id": "ds-h2h-acb-tcb-2024q4",
                "title": "so sánh 4 chỉ tiêu tài chính giữa ACB và TCB, Q4/2024",
                "takeaway": {
                    "sentence_id": "s-h2h-fig",
                    "text": "ACB dẫn trước ở tỷ suất ROE cao hơn 6,25 điểm phần trăm nhưng đệm bao phủ nợ xấu thấp hơn 37,24 điểm phần trăm so với TCB.",
                    "fact_ids": [
                        "fact:pairwise_gap:ACB:vs:TCB:2024_Q4:bank.roe",
                        "fact:pairwise_gap:ACB:vs:TCB:2024_Q4:bank.llr_coverage",
                    ],
                    "author": "company",
                    "source": "model",
                    "revision": 0,
                },
            },
            {
                "type": "callout",
                "tone": "notice",
                "title": "Phân rã ROE và ROA",
                "finding_id": "f-h2h-decomposition",
                "sentences": [
                    {
                        "sentence_id": "s-h2h-call",
                        "text": "Tỷ số ROE trên ROA của ACB đạt 10,25 lần, cao hơn mức 6,46 lần của TCB.",
                        "fact_ids": [
                            "fact:derived_ratio:ACB:2024_Q4:derived.roe_over_roa",
                            "fact:derived_ratio:TCB:2024_Q4:derived.roe_over_roa",
                        ],
                        "author": "company",
                        "source": "model",
                        "revision": 0,
                    }
                ],
            },
        ],
    }

    source_notes = [
        format_source_note(
            db, 1, "ACB", "bank.roe", "2024_Q4",
            [
                "fact:value:ACB:2024_Q4:bank.roe",
                "fact:pairwise_gap:ACB:vs:TCB:2024_Q4:bank.roe",
                "fact:derived_ratio:ACB:2024_Q4:derived.roe_over_roa",
                "fact:lead_count:ACB:vs:TCB:2024_Q4",
            ],
        ),
        format_source_note(
            db, 2, "ACB", "bank.llr_coverage", "2024_Q4",
            [
                "fact:value:ACB:2024_Q4:bank.llr_coverage",
                "fact:pairwise_gap:ACB:vs:TCB:2024_Q4:bank.llr_coverage",
            ],
        ),
        format_source_note(
            db, 3, "ACB", "bank.roa", "2024_Q4",
            [
                "fact:value:ACB:2024_Q4:bank.roa",
                "fact:derived_ratio:ACB:2024_Q4:derived.roe_over_roa",
            ],
        ),
        format_source_note(
            db, 4, "ACB", "bank.npl_g35", "2024_Q4",
            [
                "fact:value:ACB:2024_Q4:bank.npl_g35",
            ],
        ),
        format_source_note(
            db, 5, "TCB", "bank.roe", "2024_Q4",
            [
                "fact:value:TCB:2024_Q4:bank.roe",
                "fact:value:TCB:2024_Q4:bank.roa",
                "fact:value:TCB:2024_Q4:bank.llr_coverage",
                "fact:value:TCB:2024_Q4:bank.npl_g35",
                "fact:pairwise_gap:ACB:vs:TCB:2024_Q4:bank.roe",
                "fact:pairwise_gap:ACB:vs:TCB:2024_Q4:bank.llr_coverage",
                "fact:derived_ratio:TCB:2024_Q4:derived.roe_over_roa",
                "fact:lead_count:TCB:vs:ACB:2024_Q4",
            ],
        ),
    ]

    return {
        "report_id": "rep-h2h-acb-tcb-2024q4",
        "status": "completed",
        "report_version": "er-report-v1",
        "question_type": "head_to_head",
        "analysis_plan": None,
        "macro_context": None,
        "sector_benchmark": None,
        "company_insights": [],
        "cross_level_critique": [],
        "atomic_claims": [],
        "evidence_trail": [],
        "revision_summary": None,
        "limitations": [],
        "synthesis_summary": "TCB vượt trội về an toàn vốn và chất lượng tài sản trong khi ACB duy trì hiệu quả sinh lời trên vốn cao hơn.",
        "synthesis_supporting_claim_ids": [],
        "facts": facts,
        "datasets": [ds_comp],
        "report_spec": report_spec,
        "signals": [],
        "cross_level_findings": [],
        "narrative_audit": {
            "sentences_checked": 3,
            "sentences_accepted": 3,
            "sentences_dropped": [],
            "numbers_checked": 6,
            "numbers_matched": 6,
            "blocks_dropped": [],
            "composition_source": "model",
        },
        "source_notes": source_notes,
        "error": None,
    }


def build_er_profile_fixture(db: GoldDatabase) -> Dict[str, Any]:
    """5. Company Profile ACB Q4/2024."""
    # 4 metrics Q4
    q4_pairs_by_m = {}
    q4_obs_by_m = {}
    medians_q4 = {}
    ranks_q4 = {}

    for m in ALL_METRICS:
        pairs = []
        obs_ids = []
        for b in ALL_BANKS:
            o = db.get_obs(b, m, "2024_Q4")
            assert o
            pairs.append((b, float(o["value"])))
            obs_ids.append(o["observation_id"])
        q4_pairs_by_m[m] = pairs
        q4_obs_by_m[m] = obs_ids
        medians_q4[m] = calc_median([v for _, v in pairs])
        ranks_q4[m] = calc_ranks(pairs, METRIC_DIRECTIONS[m])

    # Q3 medians and ACB Q3 values for deltas
    medians_q3 = {}
    for m in ALL_METRICS:
        pairs = []
        for b in ALL_BANKS:
            o = db.get_obs(b, m, "2024_Q3")
            assert o
            pairs.append((b, float(o["value"])))
        medians_q3[m] = calc_median([v for _, v in pairs])

    acb_q4_obs = {m: db.get_obs("ACB", m, "2024_Q4") for m in ALL_METRICS}
    acb_q3_obs = {m: db.get_obs("ACB", m, "2024_Q3") for m in ALL_METRICS}
    acb_q4_vals = {m: float(acb_q4_obs[m]["value"]) for m in ALL_METRICS}
    acb_q3_vals = {m: float(acb_q3_obs[m]["value"]) for m in ALL_METRICS}

    facts = []

    # 4 metrics: value, peer_median, peer_rank, gap_to_median
    for m in ALL_METRICS:
        # value
        facts.append(
            {
                "fact_id": f"fact:value:ACB:2024_Q4:{m}",
                "fact_type": "value",
                "entity_id": "ACB",
                "other_entity_id": None,
                "universe_id": None,
                "metric_id": m,
                "period": "2024_Q4",
                "from_period": None,
                "value": acb_q4_vals[m],
                "unit": "%",
                "rank_better": None,
                "rank_desc": None,
                "denominator": None,
                "formula_version": "primary-observation-v1",
                "input_observation_ids": [acb_q4_obs[m]["observation_id"]],
                "input_fact_ids": [],
            }
        )
        # peer_median
        facts.append(
            {
                "fact_id": f"fact:peer_median:sector:bank:2024_Q4:{m}",
                "fact_type": "peer_median",
                "entity_id": None,
                "other_entity_id": None,
                "universe_id": "sector:bank",
                "metric_id": m,
                "period": "2024_Q4",
                "from_period": None,
                "value": medians_q4[m],
                "unit": "%",
                "rank_better": None,
                "rank_desc": None,
                "denominator": 5,
                "formula_version": "peer-median-v1",
                "input_observation_ids": q4_obs_by_m[m],
                "input_fact_ids": [],
            }
        )
        # peer_rank
        rb, rd = ranks_q4[m]["ACB"]
        facts.append(
            {
                "fact_id": f"fact:peer_rank:ACB:sector:bank:2024_Q4:{m}",
                "fact_type": "peer_rank",
                "entity_id": "ACB",
                "other_entity_id": None,
                "universe_id": "sector:bank",
                "metric_id": m,
                "period": "2024_Q4",
                "from_period": None,
                "value": float(rb),
                "unit": "rank",
                "rank_better": rb,
                "rank_desc": rd,
                "denominator": 5,
                "formula_version": "peer-rank-v1",
                "input_observation_ids": q4_obs_by_m[m],
                "input_fact_ids": [],
            }
        )
        # gap_to_median
        gap = acb_q4_vals[m] - medians_q4[m]
        facts.append(
            {
                "fact_id": f"fact:gap_to_median:ACB:sector:bank:2024_Q4:{m}",
                "fact_type": "gap_to_median",
                "entity_id": "ACB",
                "other_entity_id": None,
                "universe_id": "sector:bank",
                "metric_id": m,
                "period": "2024_Q4",
                "from_period": None,
                "value": gap,
                "unit": "pp",
                "rank_better": None,
                "rank_desc": None,
                "denominator": None,
                "formula_version": "gap-to-median-v1",
                "input_observation_ids": [acb_q4_obs[m]["observation_id"]],
                "input_fact_ids": [],
            }
        )

    # 4 metrics: delta and median_delta Q3->Q4
    for m in ALL_METRICS:
        d = acb_q4_vals[m] - acb_q3_vals[m]
        facts.append(
            {
                "fact_id": f"fact:delta:ACB:2024_Q3_to_2024_Q4:{m}",
                "fact_type": "delta",
                "entity_id": "ACB",
                "other_entity_id": None,
                "universe_id": None,
                "metric_id": m,
                "period": "2024_Q4",
                "from_period": "2024_Q3",
                "value": d,
                "unit": "pp",
                "rank_better": None,
                "rank_desc": None,
                "denominator": None,
                "formula_version": "period-delta-v1",
                "input_observation_ids": [acb_q3_obs[m]["observation_id"], acb_q4_obs[m]["observation_id"]],
                "input_fact_ids": [],
            }
        )

        md = medians_q4[m] - medians_q3[m]
        q3_obs_ids = [db.get_obs(b, m, "2024_Q3")["observation_id"] for b in ALL_BANKS]
        facts.append(
            {
                "fact_id": f"fact:median_delta:sector:bank:2024_Q3_to_2024_Q4:{m}",
                "fact_type": "median_delta",
                "entity_id": None,
                "other_entity_id": None,
                "universe_id": "sector:bank",
                "metric_id": m,
                "period": "2024_Q4",
                "from_period": "2024_Q3",
                "value": md,
                "unit": "pp",
                "rank_better": None,
                "rank_desc": None,
                "denominator": 5,
                "formula_version": "median-delta-v1",
                "input_observation_ids": q3_obs_ids + q4_obs_by_m[m],
                "input_fact_ids": [],
            }
        )

    # derived_ratio ROE/ROA
    ratio_roe_roa = acb_q4_vals["bank.roe"] / acb_q4_vals["bank.roa"]
    facts.append(
        {
            "fact_id": "fact:derived_ratio:ACB:2024_Q4:derived.roe_over_roa",
            "fact_type": "derived_ratio",
            "entity_id": "ACB",
            "other_entity_id": None,
            "universe_id": None,
            "metric_id": "derived.roe_over_roa",
            "period": "2024_Q4",
            "from_period": None,
            "value": ratio_roe_roa,
            "unit": "x",
            "rank_better": None,
            "rank_desc": None,
            "denominator": None,
            "formula_version": "derived-ratio-v1",
            "input_observation_ids": [acb_q4_obs["bank.roe"]["observation_id"], acb_q4_obs["bank.roa"]["observation_id"]],
            "input_fact_ids": ["fact:value:ACB:2024_Q4:bank.roe", "fact:value:ACB:2024_Q4:bank.roa"],
        }
    )

    # Dataset 1: paired (scatter) - NPL x Coverage for all 5 banks
    scatter_rows = []
    for b in ALL_BANKS:
        o_npl = db.get_obs(b, "bank.npl_g35", "2024_Q4")
        o_llr = db.get_obs(b, "bank.llr_coverage", "2024_Q4")
        assert o_npl and o_llr
        scatter_rows.append(
            {
                "entity_id": b,
                "metric_id": "bank.npl_g35",
                "period": "2024_Q4",
                "status": "valid",
                "value": float(o_npl["value"]),
                "observation_id": o_npl["observation_id"],
                "rank_better": ranks_q4["bank.npl_g35"][b][0],
                "rank_desc": ranks_q4["bank.npl_g35"][b][1],
                "missing_reason": None,
            }
        )
        scatter_rows.append(
            {
                "entity_id": b,
                "metric_id": "bank.llr_coverage",
                "period": "2024_Q4",
                "status": "valid",
                "value": float(o_llr["value"]),
                "observation_id": o_llr["observation_id"],
                "rank_better": ranks_q4["bank.llr_coverage"][b][0],
                "rank_desc": ranks_q4["bank.llr_coverage"][b][1],
                "missing_reason": None,
            }
        )

    ds_scatter = {
        "dataset_id": "ds-profile-acb-scatter",
        "shape": "paired",
        "title": "ma trận định vị nợ xấu và đệm bao phủ, Q4/2024",
        "produced_by": {"tool": "peer_position", "agent": "company"},
        "metric_ids": ["bank.npl_g35", "bank.llr_coverage"],
        "periods": ["2024_Q4"],
        "highlight_entity_ids": ["ACB"],
        "rows": scatter_rows,
        "reference_lines": [
            {
                "kind": "median",
                "metric_id": "bank.npl_g35",
                "period": "2024_Q4",
                "value": medians_q4["bank.npl_g35"],
                "fact_id": "fact:peer_median:sector:bank:2024_Q4:bank.npl_g35",
            },
            {
                "kind": "median",
                "metric_id": "bank.llr_coverage",
                "period": "2024_Q4",
                "value": medians_q4["bank.llr_coverage"],
                "fact_id": "fact:peer_median:sector:bank:2024_Q4:bank.llr_coverage",
            },
        ],
        "allowed_charts": ["scatter"],
    }

    # Dataset 2: peer_table (rank_heatmap) - 5 banks x 4 metrics
    heatmap_rows = []
    for m in ALL_METRICS:
        for b in ALL_BANKS:
            o = db.get_obs(b, m, "2024_Q4")
            assert o
            rb, rd = ranks_q4[m][b]
            heatmap_rows.append(
                {
                    "entity_id": b,
                    "metric_id": m,
                    "period": "2024_Q4",
                    "status": "valid",
                    "value": float(o["value"]),
                    "observation_id": o["observation_id"],
                    "rank_better": rb,
                    "rank_desc": rd,
                    "missing_reason": None,
                }
            )

    ds_heatmap = {
        "dataset_id": "ds-profile-acb-heatmap",
        "shape": "peer_table",
        "title": "thứ hạng các chỉ tiêu tài chính của ACB so với nhóm, Q4/2024",
        "produced_by": {"tool": "peer_position", "agent": "company"},
        "metric_ids": ALL_METRICS,
        "periods": ["2024_Q4"],
        "highlight_entity_ids": ["ACB"],
        "rows": heatmap_rows,
        "reference_lines": [],
        "allowed_charts": ["rank_heatmap", "comparison_table"],
    }

    # Dataset 3: series_multi - 5 banks x 4 metrics x 4 quarters = 80 rows!
    multi_rows = []
    for b in ALL_BANKS:
        for m in ALL_METRICS:
            for p in ALL_PERIODS:
                o = db.get_obs(b, m, p)
                if b == "ACB" and p == "2024_Q1":
                    multi_rows.append(
                        {
                            "entity_id": "ACB",
                            "metric_id": m,
                            "period": "2024_Q1",
                            "status": "missing",
                            "value": None,
                            "observation_id": o["observation_id"] if o else f"missing:ACB:2024_Q1:{m}",
                            "rank_better": None,
                            "rank_desc": None,
                            "missing_reason": "ACB quý 1/2024 chưa có số liệu đã kiểm định; để trống thay vì ước tính.",
                        }
                    )
                else:
                    assert o and o["value"] is not None
                    multi_rows.append(
                        {
                            "entity_id": b,
                            "metric_id": m,
                            "period": p,
                            "status": "valid",
                            "value": float(o["value"]),
                            "observation_id": o["observation_id"],
                            "rank_better": None,
                            "rank_desc": None,
                            "missing_reason": None,
                        }
                    )

    assert len(multi_rows) == 80, f"Expected 80 rows, got {len(multi_rows)}"

    ds_multi = {
        "dataset_id": "ds-profile-acb-small-multiples",
        "shape": "series_multi",
        "title": "diễn biến 4 chỉ tiêu tài chính của các ngân hàng qua các quý năm 2024",
        "produced_by": {"tool": "trend", "agent": "company"},
        "metric_ids": ALL_METRICS,
        "periods": ALL_PERIODS,
        "highlight_entity_ids": ["ACB"],
        "rows": multi_rows,
        "reference_lines": [],
        "allowed_charts": ["small_multiples"],
    }

    report_spec = {
        "kind": "note",
        "note_label": "Ghi chú doanh nghiệp · Ngân hàng",
        "blocks": [
            {
                "type": "headline",
                "sentence": {
                    "sentence_id": "s-prof-head",
                    "text": "ACB duy trì khả năng sinh lời với ROE xếp thứ 2 trong 5 ngân hàng, nhưng đệm dự phòng bao phủ nợ xấu thấp hơn trung vị nhóm 15,69 điểm phần trăm.",
                    "fact_ids": [
                        "fact:peer_rank:ACB:sector:bank:2024_Q4:bank.roe",
                        "fact:gap_to_median:ACB:sector:bank:2024_Q4:bank.llr_coverage",
                    ],
                    "author": "company",
                    "source": "model",
                    "revision": 0,
                },
            },
            {
                "type": "key_points",
                "items": [
                    {
                        "title": "Sinh lời vượt trội",
                        "sentences": [
                            {
                                "sentence_id": "s-prof-kp1",
                                "text": "Chỉ số ROE đạt 21,75%, cao hơn trung vị nhóm 3,15 điểm phần trăm.",
                                "fact_ids": [
                                    "fact:value:ACB:2024_Q4:bank.roe",
                                    "fact:gap_to_median:ACB:sector:bank:2024_Q4:bank.roe",
                                ],
                                "author": "company",
                                "source": "model",
                                "revision": 0,
                            }
                        ],
                    },
                    {
                        "title": "Đòn bẩy vốn",
                        "sentences": [
                            {
                                "sentence_id": "s-prof-kp2",
                                "text": "Tỷ số ROE trên ROA của ACB đạt 10,25 lần tại quý 4/2024.",
                                "fact_ids": ["fact:derived_ratio:ACB:2024_Q4:derived.roe_over_roa"],
                                "author": "company",
                                "source": "model",
                                "revision": 0,
                            }
                        ],
                    },
                ],
            },
            {
                "type": "figure",
                "figure_no": 1,
                "chart": "scatter",
                "dataset_id": "ds-profile-acb-scatter",
                "title": "ma trận định vị nợ xấu và đệm bao phủ, Q4/2024",
                "takeaway": {
                    "sentence_id": "s-prof-fig1",
                    "text": "ACB ghi nhận tỷ lệ nợ xấu 1,51% và đệm bao phủ 76,56%, thấp hơn trung vị nhóm 15,69 điểm phần trăm.",
                    "fact_ids": [
                        "fact:value:ACB:2024_Q4:bank.npl_g35",
                        "fact:value:ACB:2024_Q4:bank.llr_coverage",
                        "fact:gap_to_median:ACB:sector:bank:2024_Q4:bank.llr_coverage",
                    ],
                    "author": "company",
                    "source": "model",
                    "revision": 0,
                },
            },
            {
                "type": "figure",
                "figure_no": 2,
                "chart": "rank_heatmap",
                "dataset_id": "ds-profile-acb-heatmap",
                "title": "thứ hạng các chỉ tiêu tài chính của ACB so với nhóm, Q4/2024",
                "takeaway": {
                    "sentence_id": "s-prof-fig2",
                    "text": "ACB đạt thứ hạng cao ở sinh lời với ROE xếp thứ 2 trong 5 ngân hàng, trong khi đệm dự phòng bao phủ nợ xấu xếp thứ 4.",
                    "fact_ids": [
                        "fact:peer_rank:ACB:sector:bank:2024_Q4:bank.roe",
                        "fact:peer_rank:ACB:sector:bank:2024_Q4:bank.llr_coverage",
                    ],
                    "author": "sector",
                    "source": "model",
                    "revision": 0,
                },
            },
            {
                "type": "figure",
                "figure_no": 3,
                "chart": "small_multiples",
                "dataset_id": "ds-profile-acb-small-multiples",
                "title": "diễn biến 4 chỉ tiêu tài chính của các ngân hàng qua các quý năm 2024",
                "takeaway": {
                    "sentence_id": "s-prof-fig3",
                    "text": "Trong quý 4, đệm bao phủ nợ xấu của ACB giảm 2,51 điểm phần trăm so với quý 3.",
                    "fact_ids": ["fact:delta:ACB:2024_Q3_to_2024_Q4:bank.llr_coverage"],
                    "author": "company",
                    "source": "model",
                    "revision": 0,
                },
            },
            {
                "type": "callout",
                "tone": "warning",
                "title": "Cảnh báo phân kỳ tín hiệu và nghịch xu hướng",
                "finding_id": "f-profile-counter-trend",
                "sentences": [
                    {
                        "sentence_id": "s-prof-call",
                        "text": "Đệm bao phủ nợ xấu của ACB giảm 2,51 điểm phần trăm trong quý 4, ngược chiều với đà tăng 13,18 điểm phần trăm của trung vị nhóm.",
                        "fact_ids": [
                            "fact:delta:ACB:2024_Q3_to_2024_Q4:bank.llr_coverage",
                            "fact:median_delta:sector:bank:2024_Q3_to_2024_Q4:bank.llr_coverage",
                        ],
                        "author": "critic",
                        "source": "model",
                        "revision": 0,
                    }
                ],
            },
        ],
    }

    signals = [
        {
            "group": "profitability",
            "label": "Sinh lời",
            "verdict": "above_peers",
            "metric_ids": ["bank.roe", "bank.roa"],
            "fact_ids": [
                "fact:gap_to_median:ACB:sector:bank:2024_Q4:bank.roe",
                "fact:peer_rank:ACB:sector:bank:2024_Q4:bank.roe",
            ],
        },
        {
            "group": "asset_quality",
            "label": "Chất lượng nợ",
            "verdict": "in_line",
            "metric_ids": ["bank.npl_g35"],
            "fact_ids": [
                "fact:gap_to_median:ACB:sector:bank:2024_Q4:bank.npl_g35",
                "fact:peer_rank:ACB:sector:bank:2024_Q4:bank.npl_g35",
            ],
        },
        {
            "group": "reserve_cushion",
            "label": "Đệm dự phòng",
            "verdict": "below_peers",
            "metric_ids": ["bank.llr_coverage"],
            "fact_ids": [
                "fact:gap_to_median:ACB:sector:bank:2024_Q4:bank.llr_coverage",
                "fact:peer_rank:ACB:sector:bank:2024_Q4:bank.llr_coverage",
            ],
        },
    ]

    cross_level_findings = [
        {
            "finding_id": "f-profile-divergent",
            "kind": "divergent_signals",
            "severity": "notice",
            "text": "Tín hiệu sinh lời vượt trội phân kỳ với mức đệm bao phủ nợ xấu mỏng hơn trung vị ngành.",
            "fact_ids": [
                "fact:gap_to_median:ACB:sector:bank:2024_Q4:bank.roe",
                "fact:gap_to_median:ACB:sector:bank:2024_Q4:bank.llr_coverage",
            ],
            "status": "confirmed",
        },
        {
            "finding_id": "f-profile-counter-trend",
            "kind": "counter_trend",
            "severity": "warning",
            "text": "Đệm bao phủ nợ xấu của ACB giảm trong khi xu hướng chung toàn ngành tiếp tục được củng cố.",
            "fact_ids": [
                "fact:delta:ACB:2024_Q3_to_2024_Q4:bank.llr_coverage",
                "fact:median_delta:sector:bank:2024_Q3_to_2024_Q4:bank.llr_coverage",
            ],
            "status": "confirmed",
        },
    ]

    source_notes = [
        format_source_note(
            db, 1, "ACB", "bank.roe", "2024_Q4",
            [
                "fact:value:ACB:2024_Q4:bank.roe",
                "fact:gap_to_median:ACB:sector:bank:2024_Q4:bank.roe",
                "fact:peer_rank:ACB:sector:bank:2024_Q4:bank.roe",
                "fact:derived_ratio:ACB:2024_Q4:derived.roe_over_roa",
            ],
        ),
        format_source_note(
            db, 2, "ACB", "bank.roa", "2024_Q4",
            [
                "fact:value:ACB:2024_Q4:bank.roa",
                "fact:gap_to_median:ACB:sector:bank:2024_Q4:bank.roa",
                "fact:peer_rank:ACB:sector:bank:2024_Q4:bank.roa",
                "fact:derived_ratio:ACB:2024_Q4:derived.roe_over_roa",
            ],
        ),
        format_source_note(
            db, 3, "ACB", "bank.npl_g35", "2024_Q4",
            [
                "fact:value:ACB:2024_Q4:bank.npl_g35",
                "fact:gap_to_median:ACB:sector:bank:2024_Q4:bank.npl_g35",
                "fact:peer_rank:ACB:sector:bank:2024_Q4:bank.npl_g35",
            ],
        ),
        format_source_note(
            db, 4, "ACB", "bank.llr_coverage", "2024_Q4",
            [
                "fact:value:ACB:2024_Q4:bank.llr_coverage",
                "fact:gap_to_median:ACB:sector:bank:2024_Q4:bank.llr_coverage",
                "fact:peer_rank:ACB:sector:bank:2024_Q4:bank.llr_coverage",
                "fact:delta:ACB:2024_Q3_to_2024_Q4:bank.llr_coverage",
            ],
        ),
        format_source_note(
            db, 5, "ACB", "bank.llr_coverage", "2024_Q3",
            [
                "fact:delta:ACB:2024_Q3_to_2024_Q4:bank.llr_coverage",
            ],
        ),
    ]

    return {
        "report_id": "rep-profile-acb-2024q4",
        "status": "accepted_with_limitations",
        "report_version": "er-report-v1",
        "question_type": "company_profile",
        "analysis_plan": None,
        "macro_context": None,
        "sector_benchmark": None,
        "company_insights": [],
        "cross_level_critique": [],
        "atomic_claims": [],
        "evidence_trail": [],
        "revision_summary": None,
        "limitations": [
            "ACB quý 1/2024 chưa có số liệu đã kiểm định; để trống thay vì ước tính."
        ],
        "synthesis_summary": "ACB duy trì khả năng sinh lời vượt trội với ROE 21,75% nhưng đệm dự phòng bao nợ xấu ở mức 76,56% thấp hơn trung vị ngành.",
        "synthesis_supporting_claim_ids": [],
        "facts": facts,
        "datasets": [ds_scatter, ds_heatmap, ds_multi],
        "report_spec": report_spec,
        "signals": signals,
        "cross_level_findings": cross_level_findings,
        "narrative_audit": {
            "sentences_checked": 8,
            "sentences_accepted": 7,
            "sentences_dropped": [
                {
                    "sentence_id": "s-prof-drop-1",
                    "author": "company",
                    "text": "Lợi nhuận ACB tăng mạnh nhờ tối ưu hóa chi phí hoạt động và mở rộng cho vay bán lẻ.",
                    "reason_code": "causal_language",
                    "reason": "Sử dụng từ chỉ nguyên nhân (nhờ).",
                }
            ],
            "numbers_checked": 14,
            "numbers_matched": 14,
            "blocks_dropped": [],
            "composition_source": "model",
        },
        "source_notes": source_notes,
        "error": None,
    }


def build_er_trace_fixture() -> Dict[str, Any]:
    """6. Run Trace fixture for ACB profile run."""
    steps = [
        {
            "step_id": "t-1",
            "seq": 1,
            "t_ms": 120,
            "actor": "orchestrator",
            "recipient": "system",
            "kind": "plan",
            "summary": "Lập kế hoạch phân tích hồ sơ doanh nghiệp ACB",
            "detail": {
                "question_type": "company_profile",
                "planner_source": "rules",
                "rationale": "Yêu cầu đánh giá sức khỏe tài chính toàn diện của ACB so với các ngân hàng cùng nhóm",
                "entities": ["ACB"],
                "metric_ids": ["bank.npl_g35", "bank.llr_coverage", "bank.roa", "bank.roe"],
                "anchor_period": "2024_Q4",
                "periods": ["2024_Q1", "2024_Q2", "2024_Q3", "2024_Q4"],
                "tools": [
                    {"tool": "peer_position", "agent": "company", "label": "Vị thế nhóm"},
                    {"tool": "trend", "agent": "company", "label": "Diễn biến chuỗi thời gian"},
                    {"tool": "decomposition", "agent": "company", "label": "Phân rã ROE/ROA"},
                ],
                "agents": [
                    {"agent": "company", "decision": "run", "reason": "Phân tích nội tại doanh nghiệp"},
                    {"agent": "sector", "decision": "run", "reason": "Tính toán vị thế nhóm ngân hàng"},
                    {"agent": "macro", "decision": "skip", "reason": "Chưa có dữ liệu vĩ mô kiểm định"},
                ],
                "defaults_applied": [],
            },
        },
        {
            "step_id": "t-2",
            "seq": 2,
            "t_ms": 350,
            "actor": "orchestrator",
            "recipient": "company",
            "kind": "assign",
            "summary": "Giao nhiệm vụ trích xuất fact và vẽ biểu đồ cho agent công ty",
            "detail": {
                "task": "peer_position, trend, decomposition",
                "tools": ["Vị thế nhóm", "Diễn biến chuỗi thời gian", "Phân rã ROE/ROA"],
            },
        },
        {
            "step_id": "t-3",
            "seq": 3,
            "t_ms": 1500,
            "actor": "company",
            "recipient": "orchestrator",
            "kind": "tool_result",
            "summary": "Hoàn thành tính toán các fact và 3 tập dữ liệu",
            "detail": {
                "tool": "peer_position",
                "label": "Vị thế nhóm và chuỗi thời gian",
                "facts": [
                    {"fact_id": "fact:value:ACB:2024_Q4:bank.roe", "label": "ROE Q4", "display_value": "21,75%", "source_note_no": 1},
                    {"fact_id": "fact:gap_to_median:ACB:sector:bank:2024_Q4:bank.roe", "label": "ROE gap", "display_value": "+3,15 pp", "source_note_no": 1},
                ],
                "datasets": [
                    {"dataset_id": "ds-profile-acb-scatter", "title": "ma trận định vị nợ xấu và đệm bao phủ, Q4/2024"},
                    {"dataset_id": "ds-profile-acb-heatmap", "title": "thứ hạng các chỉ tiêu tài chính của ACB so với nhóm, Q4/2024"},
                    {"dataset_id": "ds-profile-acb-small-multiples", "title": "diễn biến 4 chỉ tiêu tài chính của các ngân hàng qua các quý năm 2024"},
                ],
                "missing": [
                    {
                        "entity_id": "ACB",
                        "metric_id": "bank.llr_coverage",
                        "period": "2024_Q1",
                        "reason": "ACB quý 1/2024 chưa có số liệu đã kiểm định; để trống thay vì ước tính.",
                    }
                ],
            },
        },
        {
            "step_id": "t-4",
            "seq": 4,
            "t_ms": 4200,
            "actor": "company",
            "recipient": "verifier",
            "kind": "draft",
            "summary": "Soạn thảo bản nháp nhận định ban đầu",
            "detail": {
                "sentences": [
                    {
                        "sentence_id": "s-prof-head",
                        "text": "ACB duy trì khả năng sinh lời với ROE xếp thứ 2 trong 5 ngân hàng, nhưng đệm dự phòng bao phủ nợ xấu thấp hơn trung vị nhóm 15,69 điểm phần trăm.",
                        "fact_ids": [
                            "fact:peer_rank:ACB:sector:bank:2024_Q4:bank.roe",
                            "fact:gap_to_median:ACB:sector:bank:2024_Q4:bank.llr_coverage",
                        ],
                    },
                    {
                        "sentence_id": "s-prof-drop-1",
                        "text": "Lợi nhuận ACB tăng mạnh nhờ tối ưu hóa chi phí hoạt động và mở rộng cho vay bán lẻ.",
                        "fact_ids": [],
                    },
                ]
            },
        },
        {
            "step_id": "t-5",
            "seq": 5,
            "t_ms": 4800,
            "actor": "verifier",
            "recipient": "orchestrator",
            "kind": "verify",
            "summary": "Kiểm tra tính chuẩn xác của các câu văn: loại 1 câu vi phạm luật nhân quả",
            "detail": {
                "sentences_checked": 8,
                "numbers_checked": 14,
                "numbers_matched": 14,
                "dropped": [
                    {
                        "sentence_id": "s-prof-drop-1",
                        "text": "Lợi nhuận ACB tăng mạnh nhờ tối ưu hóa chi phí hoạt động và mở rộng cho vay bán lẻ.",
                        "reason_code": "causal_language",
                        "reason": "Sử dụng từ chỉ nguyên nhân (nhờ).",
                    }
                ],
            },
        },
        {
            "step_id": "t-6",
            "seq": 6,
            "t_ms": 6100,
            "actor": "orchestrator",
            "recipient": "critic",
            "kind": "compose",
            "summary": "Lắp ráp bố cục báo cáo hoàn chỉnh",
            "detail": {
                "kind": "note",
                "blocks": [
                    {"type": "headline", "title": "Tiêu đề chính"},
                    {"type": "key_points", "title": "Luận điểm chủ chốt"},
                    {"type": "figure", "title": "Hình 1. Ma trận định vị"},
                    {"type": "figure", "title": "Hình 2. Thứ hạng các chỉ tiêu"},
                    {"type": "figure", "title": "Hình 3. Diễn biến 4 chỉ tiêu"},
                    {"type": "callout", "title": "Cảnh báo phân kỳ"},
                ],
                "composition_source": "model",
            },
        },
        {
            "step_id": "t-7",
            "seq": 7,
            "t_ms": 7800,
            "actor": "critic",
            "recipient": "orchestrator",
            "kind": "cross_level_finding",
            "summary": "Phát hiện mâu thuẫn chéo giữa sinh lời cao và đệm bao phủ thấp",
            "detail": {
                "finding_id": "f-profile-divergent",
                "kind": "divergent_signals",
                "text": "Tín hiệu sinh lời vượt trội phân kỳ với mức đệm bao phủ nợ xấu mỏng hơn trung vị ngành.",
                "fact_ids": [
                    "fact:gap_to_median:ACB:sector:bank:2024_Q4:bank.roe",
                    "fact:gap_to_median:ACB:sector:bank:2024_Q4:bank.llr_coverage",
                ],
            },
        },
        {
            "step_id": "t-8",
            "seq": 8,
            "t_ms": 8200,
            "actor": "critic",
            "recipient": "company",
            "kind": "critique_issue",
            "summary": "Yêu cầu làm rõ chiều biến động quý 4 của đệm dự phòng",
            "detail": {
                "issue_id": "iss-1",
                "round": 1,
                "issue_type": "evidence_sufficiency",
                "severity": "notice",
                "target_sentence_id": "s-prof-fig3",
                "target_text": "Đệm bao phủ nợ xấu của ACB giảm.",
                "evidence": "delta = -2.51 pp",
                "evidence_fact_ids": ["fact:delta:ACB:2024_Q3_to_2024_Q4:bank.llr_coverage"],
                "required_action": "Bổ sung số liệu delta cụ thể đã được kiểm định.",
            },
        },
        {
            "step_id": "t-9",
            "seq": 9,
            "t_ms": 9400,
            "actor": "company",
            "recipient": "verifier",
            "kind": "revision",
            "summary": "Cập nhật câu văn với số liệu chính xác",
            "detail": {
                "round": 1,
                "sentence_id": "s-prof-fig3",
                "before": "Đệm bao phủ nợ xấu của ACB giảm.",
                "after": "Trong quý 4, đệm bao phủ nợ xấu của ACB giảm 2,51 điểm phần trăm so với quý 3.",
                "verified": True,
            },
        },
        {
            "step_id": "t-10",
            "seq": 10,
            "t_ms": 9900,
            "actor": "critic",
            "recipient": "orchestrator",
            "kind": "accept",
            "summary": "Phê duyệt toàn bộ báo cáo sau vòng 1",
            "detail": {
                "round": 1,
                "open_issues": 0,
            },
        },
        {
            "step_id": "t-11",
            "seq": 11,
            "t_ms": 10500,
            "actor": "orchestrator",
            "recipient": "system",
            "kind": "report_ready",
            "summary": "Báo cáo sẵn sàng cung cấp cho người dùng",
            "detail": {
                "report_id": "rep-profile-acb-2024q4",
                "duration_ms": 10500,
                "model_calls": 3,
            },
        },
    ]

    return {
        "run_id": "run-profile-acb-2024q4",
        "status": "completed",
        "query": "Sức khỏe tài chính của ACB so với các ngân hàng cùng nhóm, quý 4/2024",
        "created_at": "2024-12-31T17:00:00Z",
        "duration_ms": 10500,
        "arm": "arm_c_adaptive_revision",
        "steps": steps,
    }


def build_er_error_fixture() -> Dict[str, Any]:
    """7. Error fixture for unsupported period."""
    return {
        "report_id": "rep-error-unsupported-period",
        "status": "error",
        "report_version": "er-report-v1",
        "question_type": "lookup",
        "analysis_plan": None,
        "macro_context": None,
        "sector_benchmark": None,
        "company_insights": [],
        "cross_level_critique": [],
        "atomic_claims": [],
        "evidence_trail": [],
        "revision_summary": None,
        "limitations": [],
        "synthesis_summary": None,
        "synthesis_supporting_claim_ids": [],
        "facts": [],
        "datasets": [],
        "report_spec": None,
        "signals": [],
        "cross_level_findings": [],
        "narrative_audit": None,
        "source_notes": [],
        "error": {
            "code": "unsupported_period",
            "message": "Hệ thống hiện tại chỉ hỗ trợ dữ liệu các kỳ quý 1 đến quý 4 năm 2024 (Q1–Q4/2024). Kỳ quý 4/2023 chưa có trong cơ sở dữ liệu đã kiểm định.",
            "suggestions": [
                "Tỷ lệ nợ xấu của ACB quý 4/2024 là bao nhiêu?",
                "Diễn biến nợ xấu của ACB trong năm 2024",
                "So sánh nợ xấu của ACB với các ngân hàng cùng nhóm quý 4/2024",
            ],
        },
    }


def build_all_fixtures() -> None:
    db_path = get_gold_db_path()
    print(f"[INIT] Reading Gold v5 from {db_path} (mode=ro)...")
    db = GoldDatabase(db_path)

    fdir = get_fixtures_dir()
    print(f"[INIT] Output directory: {fdir}")

    fixtures = {
        "er-lookup-vcb-npl-2024q4.json": build_er_lookup_fixture(db),
        "er-ranking-coverage-2024q4.json": build_er_ranking_fixture(db),
        "er-trend-vpb-roe-2024.json": build_er_trend_fixture(db),
        "er-h2h-acb-tcb-2024q4.json": build_er_h2h_fixture(db),
        "er-profile-acb-2024q4.json": build_er_profile_fixture(db),
        "er-trace-acb-2024q4.json": build_er_trace_fixture(),
        "er-error-unsupported-period.json": build_er_error_fixture(),
    }

    for name, data in fixtures.items():
        out_path = fdir / name
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        print(f"[OK] Generated {name} ({len(json.dumps(data))} bytes)")


if __name__ == "__main__":
    build_all_fixtures()
