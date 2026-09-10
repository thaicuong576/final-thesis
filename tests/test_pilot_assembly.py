import json
import sqlite3
import tempfile
import unittest
from pathlib import Path

from thesis_data.pilot_assembly import assemble_official_pilot_candidates


def _candidate(
    observation_id: str,
    *,
    value: float = 2.5,
    variant: str | None = None,
) -> dict:
    row = {
        "observation_id": observation_id,
        "ticker": "TCB",
        "sector": "bank",
        "metric": "bank.roa",
        "value": value,
        "unit": "%",
        "period": "2024_Q1",
        "as_of_date": "2024-03-31",
        "period_basis": "ttm",
        "source_id": "official-source",
        "source_locator": "page:30;row:ROA",
        "quality_status": "pending_validation",
        "reason": "pending independent review",
        "formula_version": "roa.v1",
        "input_facts": {"pat": 100, "assets": 4000},
    }
    if variant is not None:
        row["variant"] = variant
    return row


def _write_json(path: Path, payload) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")


class PilotAssemblyTests(unittest.TestCase):
    def files(self, root: Path, *, duplicate_id: bool = False) -> tuple[Path, Path, Path]:
        candidate = root / "candidates.jsonl"
        rows = [_candidate("obs-1", variant="reported"), _candidate("obs-2", value=2.6, variant="alternate")]
        if duplicate_id:
            rows[1]["observation_id"] = "obs-1"
        candidate.write_text(
            "\n".join(json.dumps(row, ensure_ascii=False) for row in rows) + "\n",
            encoding="utf-8",
        )
        manifest = root / "sources.json"
        _write_json(
            manifest,
            [
                {
                    "source_id": "official-source",
                    "source_type": "issuer_ir",
                    "source_tier": "primary",
                    "publisher": "TCB",
                    "url": "https://issuer.test/results.pdf",
                    "retrieved_at_utc": "2026-09-05T00:00:00Z",
                    "local_path": "data/results.pdf",
                    "content_hash": "sha256:results",
                    "license_note": "public",
                    "quality_status": "retrieved_pending_validation",
                }
            ],
        )
        evidence = root / "evidence.jsonl"
        evidence.write_text(
            json.dumps(
                {
                    "evidence_id": "evidence-1",
                    "source_id": "official-source",
                    "source_document": "results.pdf",
                    "page_number": 30,
                    "section_name": "Highlights",
                    "period": "2024_Q1",
                    "ticker": "TCB",
                    "quote": "ROA (LTM) 2.5%",
                    "retrieval_score": 1.0,
                    "parser_status": "text_layer_table_row",
                    "is_paginated": True,
                }
            ),
            encoding="utf-8",
        )
        return candidate, manifest, evidence

    def test_assembles_pending_candidates_sources_evidence_and_metadata(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            candidate, manifest, evidence = self.files(root)
            output = root / "pilot-candidate.sqlite"

            result = assemble_official_pilot_candidates(
                (candidate,),
                (manifest,),
                (evidence,),
                output,
                tickers=("TCB",),
                periods=("2024_Q1",),
                required_metrics=("bank.roa",),
            )

            connection = sqlite3.connect(output)
            metadata = json.loads(
                connection.execute("SELECT config_json FROM snapshot_metadata").fetchone()[0]
            )
            observations = connection.execute(
                "SELECT COUNT(*), COUNT(DISTINCT source_id), "
                "COUNT(DISTINCT quality_status) FROM metric_observations"
            ).fetchone()
            source = connection.execute(
                "SELECT quality_status FROM source_records"
            ).fetchone()[0]
            evidence_count = connection.execute(
                "SELECT COUNT(*) FROM evidence_snippets"
            ).fetchone()[0]
            labels = connection.execute("SELECT COUNT(*) FROM gold_labels").fetchone()[0]
            variants = connection.execute(
                "SELECT variant FROM candidate_metadata ORDER BY observation_id"
            ).fetchall()
            coverage = connection.execute(
                "SELECT expected_count, candidate_count, valid_count, missing_count "
                "FROM coverage_summary"
            ).fetchone()
            connection.close()

        self.assertEqual(result.candidate_count, 2)
        self.assertEqual(result.unique_candidate_cells, 1)
        self.assertEqual(result.source_count, 1)
        self.assertEqual(result.evidence_count, 1)
        self.assertEqual(observations, (2, 1, 1))
        self.assertEqual(source, "pending_validation")
        self.assertEqual(evidence_count, 1)
        self.assertEqual(labels, 0)
        self.assertEqual(variants, [("reported",), ("alternate",)])
        self.assertEqual(coverage, (1, 1, 0, 0))
        self.assertEqual(metadata["source_strategy"], "official_candidate_union")
        self.assertEqual(metadata["candidate_metrics"], ["bank.roa"])
        self.assertEqual(len(metadata["input_file_hashes"]), 3)

    def test_refuses_unknown_source_and_duplicate_observation_id(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            candidate, manifest, evidence = self.files(root, duplicate_id=True)
            unknown_candidate = root / "unknown.jsonl"
            row = _candidate("obs-unknown")
            row["source_id"] = "missing-source"
            unknown_candidate.write_text(json.dumps(row), encoding="utf-8")

            with self.assertRaisesRegex(ValueError, "duplicate_observation_id"):
                assemble_official_pilot_candidates(
                    (candidate,), (manifest,), (evidence,), root / "duplicate.sqlite",
                    tickers=("TCB",), periods=("2024_Q1",), required_metrics=("bank.roa",),
                )
            with self.assertRaisesRegex(ValueError, "candidate_source_missing_from_manifests"):
                assemble_official_pilot_candidates(
                    (unknown_candidate,), (manifest,), (), root / "unknown.sqlite",
                    tickers=("TCB",), periods=("2024_Q1",), required_metrics=("bank.roa",),
                )

    def test_does_not_overwrite_output(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            candidate, manifest, evidence = self.files(root)
            output = root / "pilot-candidate.sqlite"
            output.write_text("keep", encoding="utf-8")
            with self.assertRaises(FileExistsError):
                assemble_official_pilot_candidates(
                    (candidate,), (manifest,), (evidence,), output,
                    tickers=("TCB",), periods=("2024_Q1",), required_metrics=("bank.roa",),
                )

    def test_adds_explicit_missing_placeholder_for_uncovered_core_cell(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            candidate, manifest, evidence = self.files(root)
            output = root / "pilot-candidate.sqlite"

            result = assemble_official_pilot_candidates(
                (candidate,),
                (manifest,),
                (evidence,),
                output,
                tickers=("TCB",),
                periods=("2024_Q1", "2024_Q2"),
                required_metrics=("bank.roa",),
            )

            connection = sqlite3.connect(output)
            missing = connection.execute(
                "SELECT observation_id, value, unit, period_basis, source_id, "
                "quality_status, reason FROM metric_observations "
                "WHERE period = '2024_Q2'"
            ).fetchone()
            metadata = connection.execute(
                "SELECT extraction_status FROM candidate_metadata "
                "WHERE observation_id = ?",
                (missing[0],),
            ).fetchone()[0]
            connection.close()

        self.assertEqual(result.candidate_count, 2)
        self.assertEqual(result.placeholder_count, 1)
        self.assertEqual(missing[1:6], (None, None, None, None, "missing"))
        self.assertIn("no official candidate route", missing[6])
        self.assertEqual(metadata, "no_official_candidate_route")


if __name__ == "__main__":
    unittest.main()
