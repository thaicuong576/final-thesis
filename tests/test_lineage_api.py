"""Tests for observation and fact lineage API (LIN-1).

Verifies recursive lineage tree, formula recomputation, primary source URL and page
extraction, 404 handling, immutability of snapshot, and public-data guard.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
import shutil
import tempfile
import unittest

from fastapi.testclient import TestClient

from thesis_api.lineage import get_lineage_tree
from thesis_api.main import create_app
from thesis_api.settings import Settings
from thesis_data.evidence_contract import _contains_local_path


def _file_sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return h.hexdigest()


def _create_synthetic_test_db(path: Path) -> None:
    """Create a minimal synthetic SQLite database mimicking the quarterly snapshot for CI."""
    import sqlite3
    conn = sqlite3.connect(path)
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE metrics (
            metric_id TEXT PRIMARY KEY,
            display_name TEXT
        )
    """)
    cur.execute("""
        CREATE TABLE sources (
            source_ref TEXT PRIMARY KEY,
            source_url TEXT,
            publisher TEXT
        )
    """)
    cur.execute("""
        CREATE TABLE documents (
            source_ref TEXT PRIMARY KEY,
            title TEXT
        )
    """)
    cur.execute("""
        CREATE TABLE observations (
            observation_id TEXT PRIMARY KEY,
            entity_id TEXT,
            period_id TEXT,
            metric_id TEXT,
            value REAL,
            unit TEXT,
            derivation_method TEXT,
            input_observation_ids_json TEXT,
            metadata_json TEXT,
            source_ref TEXT,
            source_locator TEXT
        )
    """)
    cur.execute("""
        CREATE TABLE peer_universes (
            peer_universe_id TEXT PRIMARY KEY,
            description TEXT
        )
    """)
    cur.execute("""
        CREATE TABLE peer_universe_members (
            peer_universe_id TEXT,
            entity_id TEXT,
            PRIMARY KEY (peer_universe_id, entity_id)
        )
    """)
    cur.execute("INSERT INTO peer_universes VALUES ('sector:bank', 'Top 10 listed banks')")
    cur.executemany("INSERT INTO peer_universe_members VALUES (?, ?)", [
        ("sector:bank", "VCB"),
        ("sector:bank", "BID"),
        ("sector:bank", "CTG"),
    ])

    # Insert metrics
    cur.executemany("INSERT INTO metrics VALUES (?, ?)", [
        ("bank.llr_coverage", "Tỷ lệ bao phủ nợ xấu (LLR)"),
        ("bank.roe", "Tỷ suất sinh lời trên vốn chủ sở hữu (ROE)"),
        ("bank.input.loan_loss_provisions", "Dự phòng rủi ro cho vay khách hàng"),
        ("bank.input.npl_g35_balance", "Tổng nợ xấu (nhóm 3–5)"),
        ("bank.input.npl_group_3_balance", "Nợ dưới tiêu chuẩn (nhóm 3)"),
        ("bank.input.npl_group_4_balance", "Nợ nghi ngờ (nhóm 4)"),
        ("bank.input.npl_group_5_balance", "Nợ có khả năng mất vốn (nhóm 5)"),
    ])
    # Insert sources and documents
    cur.execute("INSERT INTO sources VALUES (?, ?, ?)", (
        "src_vcb_bctc_2026_q2", "https://static2.vietstock.vn/vcb_2026_q2.pdf", "Vietcombank"
    ))
    cur.execute("INSERT INTO documents VALUES (?, ?)", (
        "src_vcb_bctc_2026_q2", "Báo cáo tài chính hợp nhất Quý 2/2026 - VCB"
    ))
    # Insert observations
    vcb_llr_meta = json.dumps({"__derived_calculation_receipt_v1": {"result": "passed", "tolerance": "0.00005"}})
    cur.executemany("INSERT INTO observations VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", [
        (
            "observation-3a26e363c78be87d85d2c7b3a34d4121cc5b718647425d8b3017678fb966e936",
            "VCB", "2026_Q2", "bank.llr_coverage", 279.2775704532222, "%", "llr-coverage-v1",
            json.dumps(["obs_vcb_prov_2026_q2", "obs_vcb_npl_g35_2026_q2"]), vcb_llr_meta, None, None
        ),
        (
            "obs_bid_llr_2026_q2",
            "BID", "2026_Q2", "bank.llr_coverage", 75.88728294221634, "%", "llr-coverage-v1",
            None, vcb_llr_meta, "src_vcb_bctc_2026_q2", "pdf_page=15; row=Du phong; reading=single"
        ),
        (
            "obs_bid_llr_2026_q1",
            "BID", "2026_Q1", "bank.llr_coverage", 86.88572396947453, "%", "llr-coverage-v1",
            None, vcb_llr_meta, "src_vcb_bctc_2026_q2", "pdf_page=15; row=Du phong; reading=single"
        ),
        (
            "obs_ctg_llr_2026_q2",
            "CTG", "2026_Q2", "bank.llr_coverage", 150.0, "%", "llr-coverage-v1",
            None, vcb_llr_meta, "src_vcb_bctc_2026_q2", "pdf_page=12; row=Du phong; reading=single"
        ),
        (
            "obs_vcb_roe_2025_q4",
            "VCB", "2025_Q4", "bank.roe", 16.7274, "%", None,
            None, None, "src_vcb_bctc_2026_q2", "pdf_page=5; row=Loi nhuan; reading=single"
        ),
        (
            "obs_bid_roe_2025_q4",
            "BID", "2025_Q4", "bank.roe", 19.4349, "%", None,
            None, None, "src_vcb_bctc_2026_q2", "pdf_page=5; row=Loi nhuan; reading=single"
        ),
        (
            "obs_ctg_roe_2025_q4",
            "CTG", "2025_Q4", "bank.roe", 21.2309, "%", None,
            None, None, "src_vcb_bctc_2026_q2", "pdf_page=5; row=Loi nhuan; reading=single"
        ),
        (
            "obs_vcb_prov_2026_q2",
            "VCB", "2026_Q2", "bank.input.loan_loss_provisions", 29984.695, "VND", None,
            None, None, "src_vcb_bctc_2026_q2", "pdf_page=7; section=Thuyet minh; row=Du phong rui ro cho vay khach hang; reading=single"
        ),
        (
            "obs_vcb_npl_g35_2026_q2",
            "VCB", "2026_Q2", "bank.input.npl_g35_balance", 10736.521, "VND", "npl-g35-balance-v1",
            json.dumps(["obs_vcb_npl_g3_2026_q2", "obs_vcb_npl_g4_2026_q2", "obs_vcb_npl_g5_2026_q2"]), None, None, None
        ),
        (
            "obs_vcb_npl_g3_2026_q2",
            "VCB", "2026_Q2", "bank.input.npl_group_3_balance", 2000.0, "VND", None,
            None, None, "src_vcb_bctc_2026_q2", "pdf_page=30; section=Thuyet minh; row=No duoi tieu chuan; reading=single"
        ),
        (
            "obs_vcb_npl_g4_2026_q2",
            "VCB", "2026_Q2", "bank.input.npl_group_4_balance", 3000.0, "VND", None,
            None, None, "src_vcb_bctc_2026_q2", "pdf_page=30; section=Thuyet minh; row=No nghi ngo; reading=single"
        ),
        (
            "obs_vcb_npl_g5_2026_q2",
            "VCB", "2026_Q2", "bank.input.npl_group_5_balance", 5736.521, "VND", None,
            None, None, "src_vcb_bctc_2026_q2", "pdf_page=30; section=Thuyet minh; row=No co kha nang mat von; reading=single"
        ),
    ])
    conn.commit()
    conn.close()


class TestLineageApi(unittest.TestCase):
    """Test suite for observation lineage endpoint and tree building."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.temp_dir = tempfile.mkdtemp()
        cls.temp_db_path = Path(cls.temp_dir) / "test_snapshot.sqlite"

        candidates = [
            Path("data/processed/bank-quarterly-top10-operational-v1-r4.sqlite"),
            Path(__file__).resolve().parents[1] / "data" / "processed" / "bank-quarterly-top10-operational-v1-r4.sqlite",
            Path("data/processed/bank-quarterly-top10-operational-v1.sqlite"),
            Path(__file__).resolve().parents[1] / "data" / "processed" / "bank-quarterly-top10-operational-v1.sqlite",
            Path(__file__).resolve().parents[2] / "data" / "processed" / "bank-quarterly-top10-operational-v1.sqlite",
            Path("D:/eddie-projects/personal-projects/final-thesis/data/processed/bank-quarterly-top10-operational-v1.sqlite"),
        ]
        src_db = next((p for p in candidates if p.exists()), None)
        if src_db:
            shutil.copyfile(src_db, cls.temp_db_path)
        else:
            _create_synthetic_test_db(cls.temp_db_path)

        cls.initial_hash = _file_sha256(cls.temp_db_path)

        cls.settings = Settings(
            _env_file=None,
            SQLITE_DB_PATH=str(cls.temp_db_path),
            app_env="test",
        )
        cls.app = create_app(settings=cls.settings)
        cls.client = TestClient(cls.app)

        # Dynamically retrieve VCB bank.llr_coverage 2026_Q2 observation id
        import sqlite3
        conn = sqlite3.connect(cls.temp_db_path)
        cur = conn.cursor()
        row = cur.execute(
            "SELECT observation_id FROM observations WHERE entity_id = 'VCB' AND period_id = '2026_Q2' AND metric_id = 'bank.llr_coverage'"
        ).fetchone()
        cls.vcb_llr_obs_id = row[0] if row else "observation-3a26e363c78be87d85d2c7b3a34d4121cc5b718647425d8b3017678fb966e936"
        conn.close()

    @classmethod
    def tearDownClass(cls) -> None:
        shutil.rmtree(cls.temp_dir, ignore_errors=True)

    def test_vcb_llr_coverage_lineage_tree_structure(self) -> None:
        """Lineage of VCB llr_coverage 2026_Q2 returns 2 inputs, NPL input has 3 children with pages, all leaves have URL."""
        resp = self.client.get(f"/api/lineage/{self.vcb_llr_obs_id}")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()

        # Root node
        self.assertEqual(data["observation_id"], self.vcb_llr_obs_id)
        self.assertEqual(data["entity"], "VCB")
        self.assertEqual(data["metric"], "bank.llr_coverage")
        self.assertEqual(data["period"], "2026_Q2")
        self.assertAlmostEqual(data["value"], 279.2775704532222, places=4)
        self.assertEqual(data["formula_version"], "llr-coverage-v1")
        self.assertEqual(data["receipt_result"], "passed")
        self.assertEqual(data["receipt_tolerance"], "0.00005")

        # Must have 2 inputs (provisions and npl_g35_balance)
        children = data["children"]
        self.assertEqual(len(children), 2, "Root node must return exactly 2 input children")

        prov_node = next(c for c in children if c["metric"] == "bank.input.loan_loss_provisions")
        npl_node = next(c for c in children if c["metric"] == "bank.input.npl_g35_balance")

        # Provisions input is a leaf
        self.assertIsNotNone(prov_node["source_url"])
        self.assertTrue(prov_node["source_url"].startswith("http"))
        self.assertEqual(prov_node["page"], 7)
        self.assertTrue(
            prov_node["row_label"] in (
                "Dự phòng rủi ro cho vay khách hàng",
                "Du phong rui ro cho vay khach hang",
            ) or "phong rui ro" in prov_node["row_label"].lower() or "phòng rủi ro" in prov_node["row_label"].lower()
        )
        self.assertAlmostEqual(prov_node["value"], 29984.695, places=2)

        # NPL balance has 3 children (groups 3, 4, 5) with pages
        self.assertEqual(len(npl_node["children"]), 3, "NPL balance input must have 3 children")
        for g_child in npl_node["children"]:
            self.assertIsNotNone(g_child["source_url"], f"Child {g_child['metric']} must have a URL")
            self.assertTrue(g_child["source_url"].startswith("http"))
            self.assertEqual(g_child["page"], 30, f"Child {g_child['metric']} page must be 30")
            self.assertIsNotNone(g_child["row_label"])
            self.assertIsNotNone(g_child["reading"])

        # Recompute NPL sum
        sum_npl = sum(c["value"] for c in npl_node["children"])
        self.assertAlmostEqual(sum_npl, npl_node["value"], places=3)
        self.assertAlmostEqual(npl_node["value"], 10736.521, places=3)

        # Recompute formula from returned inputs: Provisions / NPL * 100 == 279.2775...
        recomputed = (prov_node["value"] / npl_node["value"]) * 100.0
        self.assertAlmostEqual(recomputed, data["value"], places=4)
        self.assertAlmostEqual(recomputed, 279.2775704532222, places=4)

    def test_lineage_unknown_id_returns_404(self) -> None:
        """Unknown observation id returns 404."""
        resp = self.client.get("/api/lineage/observation-nonexistent-12345")
        self.assertEqual(resp.status_code, 404)

    def test_public_data_guard_no_local_paths(self) -> None:
        """Response tree passes the public-data guard (no local filesystem paths)."""
        import re

        resp = self.client.get(f"/api/lineage/{self.vcb_llr_obs_id}")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()

        def _assert_no_local_path(val: Any) -> None:
            if isinstance(val, dict):
                for k, v in val.items():
                    self.assertNotIn(k.lower(), {"local_path", "file_path", "filepath"})
                    _assert_no_local_path(v)
            elif isinstance(val, list):
                for item in val:
                    _assert_no_local_path(item)
            elif isinstance(val, str):
                if val.startswith("http://") or val.startswith("https://"):
                    return
                self.assertFalse(
                    bool(re.search(r"^[A-Za-z]:[\\/]|/(Users|home|tmp|mnt)|file://", val)),
                    f"Found local file path in response: {val}",
                )

        _assert_no_local_path(data)

    def test_fact_id_resolution(self) -> None:
        """Resolving via single value fact ID returns the observation lineage tree."""
        fact_id = "fact:value:VCB:2026_Q2:bank.llr_coverage"
        resp = self.client.get(f"/api/lineage/{fact_id}")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data["observation_id"], self.vcb_llr_obs_id)
        self.assertEqual(len(data["children"]), 2)

    def test_aggregate_fact_spread_does_not_404(self) -> None:
        """Requirement 2: Spread fact does not 404 and returns constituent banks."""
        fact_id = "fact:spread:sector:bank:2025_Q4:bank.roe"
        resp = self.client.get(f"/api/lineage/{fact_id}")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data["observation_id"], fact_id)
        self.assertEqual(data["formula_version"], "spread-pp-v1")
        self.assertGreaterEqual(len(data["children"]), 2)
        # Child nodes are sorted descending by value
        vals = [c["value"] for c in data["children"] if c.get("value") is not None]
        self.assertEqual(vals, sorted(vals, reverse=True))

    def test_aggregate_fact_peer_rank_focal_bank_first(self) -> None:
        """Requirement 2: Peer rank fact returns all bank values behind it, focal bank first."""
        fact_id = "fact:peer_rank:BID:sector:bank:2026_Q2:bank.llr_coverage"
        resp = self.client.get(f"/api/lineage/{fact_id}")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data["formula_version"], "peer-rank-competition-v1")
        self.assertGreaterEqual(len(data["children"]), 2)
        # Focal bank BID is placed strictly first
        self.assertEqual(data["children"][0]["entity"], "BID")

    def test_aggregate_fact_gap_to_median_focal_bank_first(self) -> None:
        """Requirement 2: Gap to median fact returns focal bank first."""
        fact_id = "fact:gap_to_median:BID:sector:bank:2026_Q2:bank.llr_coverage"
        resp = self.client.get(f"/api/lineage/{fact_id}")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data["formula_version"], "gap-to-median-pp-v1")
        self.assertEqual(data["children"][0]["entity"], "BID")

    def test_aggregate_fact_delta_latest_period_first(self) -> None:
        """Requirement 2: Delta fact returns latest period observation first."""
        fact_id = "fact:delta:BID:2026_Q1_to_2026_Q2:bank.llr_coverage"
        resp = self.client.get(f"/api/lineage/{fact_id}")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data["formula_version"], "delta-pp-v1")
        self.assertEqual(len(data["children"]), 2)
        self.assertEqual(data["children"][0]["period"], "2026_Q2")
        self.assertEqual(data["children"][1]["period"], "2026_Q1")

    def test_snapshot_hash_unchanged_after_calls(self) -> None:
        """Snapshot file hash remains completely unchanged after lineage calls (pure read-only)."""
        final_hash = _file_sha256(self.temp_db_path)
        self.assertEqual(self.initial_hash, final_hash, "SQLite file was mutated by lineage queries")


if __name__ == "__main__":
    unittest.main()
