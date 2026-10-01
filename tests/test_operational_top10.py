"""D-077: operational multi-bank snapshot built from upload-format CSVs."""

from __future__ import annotations

import importlib.util
import shutil
import sqlite3
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
INPUTS = ROOT / "data" / "onboarding" / "top10-2025"

_spec = importlib.util.spec_from_file_location("build_operational_snapshot", ROOT / "scripts" / "build_operational_snapshot.py")
builder = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(builder)


def _subset(tmp: Path, tickers: tuple[str, ...]) -> Path:
    folder = tmp / "inputs"
    folder.mkdir()
    for ticker in tickers:
        shutil.copyfile(INPUTS / f"{ticker}-2025q4.csv", folder / f"{ticker}-2025q4.csv")
    return folder


@unittest.skipUnless(INPUTS.exists(), "top-10 transcription CSVs are not available")
class OperationalTop10BuilderTest(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = Path(tempfile.mkdtemp())

    def tearDown(self) -> None:
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_builds_one_snapshot_with_every_bank_in_the_peer_universe(self) -> None:
        out = self.tmp / "ops.sqlite"
        manifest = builder.build(_subset(self.tmp, ("ACB", "BID", "VCB")), out)
        self.assertEqual(manifest["banks"], ["ACB", "BID", "VCB"])
        self.assertAlmostEqual(manifest["metrics"]["VCB"]["bank.npl_g35"], 0.5778, places=3)
        conn = sqlite3.connect(out)
        try:
            members = [r[0] for r in conn.execute("SELECT entity_id FROM peer_universe_members ORDER BY entity_id")]
            snapshots = {r[0] for r in conn.execute("SELECT DISTINCT dataset_snapshot_id FROM observations")}
            attrs = [r[0] for r in conn.execute("SELECT attributes_json FROM entities")]
        finally:
            conn.close()
        self.assertEqual(members, ["ACB", "BID", "VCB"])
        self.assertEqual(snapshots, {manifest["dataset_snapshot_id"]})
        self.assertTrue(all("user_supplied" not in a for a in attrs))

    def test_rejects_a_bank_with_a_wrong_unit(self) -> None:
        folder = _subset(self.tmp, ("ACB", "BID"))
        path = folder / "BID-2025q4.csv"
        path.write_text(path.read_text(encoding="utf-8").replace("billion_vnd", "million_vnd", 1), encoding="utf-8")
        with self.assertRaises(builder.BuildError):
            builder.build(folder, self.tmp / "ops.sqlite")

    def test_refuses_protected_output_names(self) -> None:
        with self.assertRaises(builder.BuildError):
            builder.build(_subset(self.tmp, ("ACB",)), self.tmp / "gold-bank-2025-expanded-v5-evidence.sqlite")

    def test_api_serves_lookup_ranking_profile_and_comparison(self) -> None:
        from fastapi.testclient import TestClient

        from tests.test_api_er_report import _TestOfflineCritic
        from thesis_api.main import create_app
        from thesis_api.settings import Settings

        class RaisingWriter:
            def write_findings(self, **kw):
                raise RuntimeError("offline")

            def compose_report(self, **kw):
                raise RuntimeError("offline")

            def rewrite_sentence(self, **kw):
                raise RuntimeError("offline")

        out = self.tmp / "ops.sqlite"
        builder.build(_subset(self.tmp, ("ACB", "BID", "HDB", "VCB")), out)
        settings = Settings(
            app_name="ops10-test", app_env="test", sqlite_db_path=str(out),
            analysis_runs_db_path=str(self.tmp / "runs.sqlite"), analysis_arm="hierarchical_with_critique",
            openai_api_key="offline", planner_mode="rules_only", USER_UPLOADS_DIR=str(self.tmp / "up"),
        )
        client = TestClient(create_app(settings, semantic_critic=_TestOfflineCritic(), analysis_writer=RaisingWriter()))
        for query, expected in (
            ("Tỷ lệ nợ xấu của BID năm 2025 là bao nhiêu?", "lookup"),
            ("Ngân hàng nào có tỷ lệ bao phủ nợ xấu cao nhất quý 4/2025?", "ranking"),
            ("Sức khỏe tài chính của HDB so với các ngân hàng cùng nhóm, quý 4/2025", "company_profile"),
            ("So sánh ACB và VCB quý 4/2025", "head_to_head"),
        ):
            body = client.post("/api/analyze", json={"query": query}).json()
            with self.subTest(query=query):
                self.assertIn(body.get("status"), {"completed", "accepted", "accepted_with_limitations"}, body.get("limitations"))
                self.assertEqual(body.get("question_type"), expected)


if __name__ == "__main__":
    unittest.main()
