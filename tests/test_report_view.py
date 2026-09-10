import json
import sqlite3
import tempfile
import unittest
from pathlib import Path

from scripts.render_analysis_report import render_markdown
from thesis_data.report_view import load_report_view


class ReportViewTests(unittest.TestCase):
    def _fixture(self, root: Path) -> tuple[Path, Path]:
        db = root / "gold.sqlite"
        con = sqlite3.connect(db)
        con.executescript(
            """
            CREATE TABLE metric_observations (
                observation_id TEXT, ticker TEXT, sector TEXT, metric TEXT,
                value REAL, unit TEXT, period TEXT, as_of_date TEXT,
                period_basis TEXT, source_id TEXT, source_locator TEXT,
                quality_status TEXT, reason TEXT
            );
            CREATE TABLE source_records (
                source_id TEXT, source_type TEXT, source_tier TEXT,
                source_url TEXT, retrieved_at TEXT, local_path TEXT,
                content_hash TEXT, publisher TEXT, license_note TEXT,
                quality_status TEXT, notes TEXT
            );
            CREATE TABLE evidence_snippets (
                evidence_id TEXT, source_id TEXT, source_document TEXT,
                page_number INTEGER, section_name TEXT, period TEXT,
                ticker TEXT, quote TEXT, retrieval_score REAL,
                parser_status TEXT, is_paginated INTEGER
            );
            """
        )
        con.execute(
            "INSERT INTO source_records VALUES (?,?,?,?,?,?,?,?,?,?,?)",
            ("src-acb", "filing", "primary", "https://example.test/acb.pdf", "2026-01-01", "x.pdf", "hash", "ACB", "public", "valid", None),
        )
        con.execute(
            "INSERT INTO metric_observations VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)",
            ("obs-acb-roe", "ACB", "bank", "bank.roe", 22.529, "%", "2024_Q2", "2024-06-30", "ttm", "src-acb", "pdf_pages:10;section:roe", "valid", None),
        )
        con.execute(
            "INSERT INTO evidence_snippets VALUES (?,?,?,?,?,?,?,?,?,?,?)",
            ("ev-acb", "src-acb", "acb.pdf", 10, "ROE", "2024_Q2", "ACB", "ROE 22.529%", 1.0, "text_layer", 1),
        )
        con.execute(
            "INSERT INTO evidence_snippets VALUES (?,?,?,?,?,?,?,?,?,?,?)",
            ("ev-acb-unrelated-page", "src-acb", "acb.pdf", 11, "Other", "2024_Q2", "ACB", "Other page", 1.0, "text_layer", 1),
        )
        con.commit()
        con.close()
        manifest = root / "manifest.json"
        manifest.write_text(
            json.dumps(
                {
                    "run_id": "run-1", "job_id": "job-1", "snapshot_id": "gold-1",
                    "question_id": "q-1", "question_set_id": "qs-1", "arm": "single_agent",
                    "model_id": "test-model", "status": "partial", "issuers": ["ACB"],
                    "periods": ["2024_Q2"], "metric_ids": ["bank.roe", "bank.roa"],
                    "call_count": 1, "total_tool_calls": 2, "total_input_tokens": 10,
                    "total_output_tokens": 5, "total_cost_estimate": 0.01,
                    "wall_clock_latency_ms": 1000,
                    "final_payload": {
                        "status": "partial", "findings": ["one finding"],
                        "quality_flags": ["partial_data"], "anomaly_classifications": [],
                        "missing_conflict_register": [],
                    },
                },
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )
        return manifest, db

    def test_builds_authoritative_matrix_and_evidence(self):
        with tempfile.TemporaryDirectory() as temp:
            view = load_report_view(*self._fixture(Path(temp)))
        self.assertEqual(view["contract_version"], "report-view-v1")
        self.assertEqual(view["summary"]["valid_cells"], 1)
        self.assertEqual(view["summary"]["missing_or_unaccepted_cells"], 1)
        self.assertEqual(view["summary"]["cells_with_stored_evidence"], 1)
        roe = view["matrix"][0]["metrics"][0]
        self.assertEqual(roe["display_value"], "22.5290%")
        self.assertEqual(roe["evidence_ids"], ["ev-acb"])
        self.assertEqual(view["missing_cells"][0]["metric"], "bank.roa")

    def test_periodless_multi_period_evidence_is_reused_only_by_locator(self):
        with tempfile.TemporaryDirectory() as temp:
            manifest, db = self._fixture(Path(temp))
            con = sqlite3.connect(db)
            con.execute("UPDATE evidence_snippets SET period=NULL WHERE evidence_id='ev-acb'")
            con.commit()
            con.close()
            view = load_report_view(manifest, db)
        roe = view["matrix"][0]["metrics"][0]
        self.assertEqual(roe["evidence_ids"], ["ev-acb"])

    def test_markdown_is_readable_and_explicit_about_gold_authority(self):
        with tempfile.TemporaryDirectory() as temp:
            view = load_report_view(*self._fixture(Path(temp)))
        markdown = render_markdown(view)
        self.assertIn("# Bank analysis report", markdown)
        self.assertIn("ACB", markdown)
        self.assertIn("22.5290%", markdown)
        self.assertIn("Gold snapshot", markdown)
        self.assertIn("Missing cells", markdown)


if __name__ == "__main__":
    unittest.main()
