import json
import sqlite3
import tempfile
import unittest
from pathlib import Path

from scripts.build_mbb_official_candidate_db import build_candidate_db
from scripts.build_mbb_official_candidate_packet_v2 import build as build_packet
from scripts.build_mbb_official_candidates import build as build_profitability
from scripts.build_mbb_official_credit_candidates import build as build_credit


class MbbOfficialCandidatePacketV2Tests(unittest.TestCase):
    def test_combines_four_metrics_and_materializes_pending_v2_snapshot(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            profitability = root / "profitability.jsonl"
            credit = root / "credit.jsonl"
            combined = root / "combined.jsonl"
            build_profitability(profitability)
            build_credit(credit)
            rows = build_packet(profitability, credit, combined)
            manifest = root / "sources.json"
            sources = []
            for period in ("Q1", "Q2", "Q3", "Q4"):
                pdf = root / f"MBB_{period}.pdf"
                pdf.write_bytes(b"pdf-fixture")
                sources.append({
                    "source_id": f"official-MBB-2024-{period}-consolidated",
                    "source_type": "filing",
                    "source_tier": "primary",
                    "url": f"https://example.test/{period}.pdf",
                    "retrieved_at_utc": "2026-09-07T00:00:00Z",
                    "local_path": str(pdf),
                    "content_hash": f"sha256:{period}",
                    "publisher": "MBB",
                    "license_note": "public disclosure",
                })
            manifest.write_text(json.dumps(sources), encoding="utf-8")
            database = root / "candidate-v2.sqlite"

            result = build_candidate_db(
                combined,
                manifest,
                database,
                snapshot_id="MBB-official-candidate-2024-v2",
                min_manual_labels=16,
            )

            connection = sqlite3.connect(database)
            observation_count = connection.execute(
                "SELECT COUNT(*) FROM metric_observations"
            ).fetchone()[0]
            metrics = connection.execute(
                "SELECT DISTINCT metric FROM metric_observations ORDER BY metric"
            ).fetchall()
            metadata = json.loads(connection.execute(
                "SELECT config_json FROM snapshot_metadata"
            ).fetchone()[0])
            connection.close()

        self.assertEqual(len(rows), 20)
        self.assertEqual(result["candidate_rows"], 20)
        self.assertEqual(observation_count, 20)
        self.assertEqual(
            metrics,
            [("bank.llr_coverage",), ("bank.npl_g35",), ("bank.roa",), ("bank.roe",)],
        )
        self.assertEqual(metadata["required_metrics"], [
            "bank.llr_coverage", "bank.npl_g35", "bank.roa", "bank.roe"
        ])
        self.assertEqual(metadata["periods"], ["2024_Q1", "2024_Q2", "2024_Q3", "2024_Q4"])


if __name__ == "__main__":
    unittest.main()
