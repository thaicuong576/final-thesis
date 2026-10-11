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


class TestLineageApi(unittest.TestCase):
    """Test suite for observation lineage endpoint and tree building."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.temp_dir = tempfile.mkdtemp()
        candidates = [
            Path("data/processed/bank-quarterly-top10-operational-v1.sqlite"),
            Path(__file__).resolve().parents[1] / "data" / "processed" / "bank-quarterly-top10-operational-v1.sqlite",
            Path(__file__).resolve().parents[2] / "data" / "processed" / "bank-quarterly-top10-operational-v1.sqlite",
            Path("D:/eddie-projects/personal-projects/final-thesis/data/processed/bank-quarterly-top10-operational-v1.sqlite"),
        ]
        src_db = next((p for p in candidates if p.exists()), None)
        if not src_db:
            raise FileNotFoundError("Source quarterly snapshot not found in candidates")

        cls.temp_db_path = Path(cls.temp_dir) / "test_snapshot.sqlite"
        shutil.copyfile(src_db, cls.temp_db_path)
        cls.initial_hash = _file_sha256(cls.temp_db_path)

        cls.settings = Settings(
            sqlite_db_path=str(cls.temp_db_path),
            app_env="test",
        )
        cls.app = create_app(settings=cls.settings)
        cls.client = TestClient(cls.app)

        # VCB bank.llr_coverage 2026_Q2 observation id in quarterly snapshot
        cls.vcb_llr_obs_id = "observation-3a26e363c78be87d85d2c7b3a34d4121cc5b718647425d8b3017678fb966e936"

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
        self.assertEqual(prov_node["row_label"], "Du phong rui ro cho vay khach hang")
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
        """Resolving via fact ID returns the observation lineage tree."""
        fact_id = "fact:value:VCB:2026_Q2:bank.llr_coverage"
        resp = self.client.get(f"/api/lineage/{fact_id}")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data["observation_id"], self.vcb_llr_obs_id)
        self.assertEqual(len(data["children"]), 2)

    def test_snapshot_hash_unchanged_after_calls(self) -> None:
        """Snapshot file hash remains completely unchanged after lineage calls (pure read-only)."""
        final_hash = _file_sha256(self.temp_db_path)
        self.assertEqual(self.initial_hash, final_hash, "SQLite file was mutated by lineage queries")


if __name__ == "__main__":
    unittest.main()
