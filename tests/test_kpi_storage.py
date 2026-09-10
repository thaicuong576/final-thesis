import json
import sqlite3
import tempfile
import unittest
from pathlib import Path

from thesis_data.kpi_storage import import_kpi_candidates


class KpiStorageTests(unittest.TestCase):
    def test_import_preserves_pending_status_and_source_metadata(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            candidates = root / "candidates.jsonl"
            manifest = root / "manifest.json"
            evidence = root / "evidence.jsonl"
            output = root / "candidate.sqlite"
            candidates.write_text(
                json.dumps(
                    {
                        "observation_id": "obs-1",
                        "ticker": "TCB",
                        "sector": "bank",
                        "metric": "bank.roa",
                        "value": 2.5,
                        "unit": "%",
                        "period": "2024_Q1",
                        "as_of_date": "2024-03-31",
                        "period_basis": "ttm",
                        "source_id": "source-1",
                        "source_locator": "page:30;row:ROA (LTM)",
                        "quality_status": "pending_validation",
                        "reason": "pending independent check",
                    }
                ),
                encoding="utf-8",
            )
            manifest.write_text(
                json.dumps(
                    [
                        {
                            "source_id": "source-1",
                            "source_type": "issuer_ir",
                            "source_tier": "primary",
                            "url": "https://example.test/tcb.pdf",
                            "retrieved_at_utc": "2026-09-04T00:00:00Z",
                            "local_path": "data/tcb.pdf",
                            "content_hash": "sha256:test",
                            "publisher": "TCB",
                            "license_note": "public",
                            "quality_status": "retrieved_pending_validation",
                        }
                    ]
                ),
                encoding="utf-8",
            )
            evidence.write_text(
                json.dumps(
                    {
                        "evidence_id": "evidence-1",
                        "source_id": "source-1",
                        "source_document": "tcb.pdf",
                        "page_number": 30,
                        "section_name": "Highlights",
                        "ticker": "TCB",
                        "quote": "ROA (LTM) | 1Q24 2.5%",
                        "retrieval_score": 1.0,
                        "parser_status": "text_layer_table_row",
                        "is_paginated": True,
                    }
                ),
                encoding="utf-8",
            )

            count = import_kpi_candidates(candidates, manifest, output, evidence)
            connection = sqlite3.connect(output)
            source = connection.execute(
                "SELECT source_type, source_tier, quality_status FROM source_records"
            ).fetchone()
            observation = connection.execute(
                "SELECT ticker, metric, value, quality_status FROM metric_observations"
            ).fetchone()
            evidence_count = connection.execute(
                "SELECT COUNT(*) FROM evidence_snippets"
            ).fetchone()[0]
            connection.close()

        self.assertEqual(count, 1)
        self.assertEqual(source, ("issuer_ir", "primary", "pending_validation"))
        self.assertEqual(observation, ("TCB", "bank.roa", 2.5, "pending_validation"))
        self.assertEqual(evidence_count, 1)


if __name__ == "__main__":
    unittest.main()
