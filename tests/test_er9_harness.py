"""Offline integration and contract tests for ER-9 evaluation harness.

Ensures:
  1. Question set, task specs, and expected coverage hash bindings are canonical LF UTF-8.
  2. Hash and snapshot ID mismatch refusal before running.
  3. ER-8 defaults remain 100% unchanged in scripts/er8_run.py.
  4. Concurrency (N > 1) produces identical run files and plan hashes as concurrency 1.
  5. Token budget guard aborts subsequent runs under concurrency.
  6. --resume flag skips already completed/blocked runs.
  7. Deterministic scoring reports missingness as N/A when missing_count is 0.
  8. CLI wrapper entrypoints (scripts/er9_*.py) function correctly.
"""

from __future__ import annotations

import csv
import json
import sqlite3
import tempfile
import unittest
from pathlib import Path

from tests.socket_guard import install_socket_guard


def setUpModule() -> None:
    install_socket_guard()


from scripts.er8_analyze import analyze_evaluation
from scripts.er8_run import (
    canonical_lf_utf8_sha256,
    find_dataset_path,
    find_gold_path_or_none,
    run_evaluation,
    verify_dataset_snapshot,
    ER9_DATASET_RAW_BYTES_SHA256,
    ER9_DATASET_SNAPSHOT_ID,
    ER9_RELATIVE_CANDIDATES,
    GOLD_RAW_BYTES_SHA256,
    GOLD_SNAPSHOT_ID,
)
from scripts.er8_score import load_dataset_observations, score_evaluation, score_single_run


class TestER9EvaluationHarness(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.root = Path(__file__).resolve().parents[1]
        cls.questions_path = cls.root / "data" / "evaluation" / "er9-questions-v1.jsonl"
        cls.task_specs_path = cls.root / "data" / "evaluation" / "er9-task-specs-v1.json"
        cls.expected_coverage_path = cls.root / "data" / "evaluation" / "er9-expected-coverage-v1.json"

        # Locate verified operational snapshot
        cls.dataset_path = None
        for cand in ER9_RELATIVE_CANDIDATES:
            if cand.exists():
                try:
                    verify_dataset_snapshot(cand, ER9_DATASET_RAW_BYTES_SHA256, ER9_DATASET_SNAPSHOT_ID)
                    cls.dataset_path = cand
                    break
                except (ValueError, FileNotFoundError):
                    continue

    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.output_dir = Path(self.temp_dir.name) / "er9"
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.addCleanup(self.temp_dir.cleanup)

    def test_01_question_and_spec_hash_bindings(self) -> None:
        """Question set canonical LF UTF-8 SHA-256 matches task specs and expected coverage."""
        q_bytes = self.questions_path.read_bytes()
        specs_bytes = self.task_specs_path.read_bytes()
        cov_bytes = self.expected_coverage_path.read_bytes()

        q_hash = canonical_lf_utf8_sha256(q_bytes)
        specs_hash = canonical_lf_utf8_sha256(specs_bytes)
        cov_hash = canonical_lf_utf8_sha256(cov_bytes)

        specs_data = json.loads(specs_bytes.decode("utf-8"))
        cov_data = json.loads(cov_bytes.decode("utf-8"))

        self.assertEqual(
            specs_data["question_set"]["canonical_lf_utf8_sha256"],
            q_hash,
            "Task specs question set hash does not match canonical questions hash.",
        )
        self.assertEqual(
            cov_data["question_set_canonical_lf_utf8_sha256"],
            q_hash,
            "Expected coverage question set hash does not match canonical questions hash.",
        )
        self.assertEqual(
            cov_data["task_specs_canonical_lf_utf8_sha256"],
            specs_hash,
            "Expected coverage task specs hash does not match canonical task specs hash.",
        )
        self.assertEqual(
            cov_data["peer_scope_label"],
            "ten listed banks, operational snapshot, not the whole sector",
        )
        # All tasks in ER-9 have 0 missing cells
        for task in cov_data["tasks"]:
            cov = task["expected_coverage"]
            if not cov.get("is_rejection"):
                self.assertEqual(cov.get("missing_count"), 0)
                self.assertEqual(cov.get("missing_observation_ids"), [])

    def test_02_hash_and_snapshot_mismatch_refusal(self) -> None:
        """Harness strictly refuses execution if dataset hash or snapshot ID does not match."""
        # Create a dummy sqlite
        dummy_db = Path(self.temp_dir.name) / "dummy.sqlite"
        conn = sqlite3.connect(dummy_db)
        conn.execute("CREATE TABLE dataset_metadata (dataset_snapshot_id TEXT)")
        conn.execute("INSERT INTO dataset_metadata VALUES ('fake-id')")
        conn.commit()
        conn.close()

        # 1. Hash mismatch
        with self.assertRaises(ValueError) as ctx:
            verify_dataset_snapshot(dummy_db, expected_hash="0000000000000000000000000000000000000000000000000000000000000000")
        self.assertIn("SHA-256 mismatch", str(ctx.exception))

        # 2. Snapshot ID mismatch
        with self.assertRaises(ValueError) as ctx:
            verify_dataset_snapshot(dummy_db, expected_snapshot_id="different-snapshot-id")
        self.assertIn("snapshot_id mismatch", str(ctx.exception))

        # 3. File not found
        non_existent = Path(self.temp_dir.name) / "does_not_exist.sqlite"
        with self.assertRaises(FileNotFoundError):
            verify_dataset_snapshot(non_existent)

        # 4. run_evaluation refuses mismatch
        if self.dataset_path:
            with self.assertRaises(ValueError):
                run_evaluation(
                    dry_run=True,
                    dataset_path=self.dataset_path,
                    expected_raw_sha256="ffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffff",
                    output_dir=self.output_dir,
                )

    def test_03_er8_defaults_unchanged(self) -> None:
        """scripts/er8_run.py without --er9 maintains all ER-8 defaults and Gold constants."""
        real_gold = find_gold_path_or_none()
        if real_gold is None:
            self.skipTest("Gold v5 snapshot not available locally to test unchanged defaults.")

        manifest = run_evaluation(
            dry_run=True,
            reps=1,
            only_tasks=["T01"],
            output_dir=self.output_dir,
        )

        self.assertEqual(manifest["manifest_id"], "er8-evaluation-manifest-v2")
        self.assertEqual(manifest["concurrency"], 1)
        self.assertEqual(manifest["gold_snapshot_bytes_sha256"], GOLD_RAW_BYTES_SHA256)
        self.assertIn("er8-questions-v2.jsonl", manifest["questions_file"])
        self.assertIn("er8-task-specs-v2.json", manifest["task_specs_file"])
        self.assertIn("er8-expected-coverage-v2.json", manifest["expected_coverage_file"])

    def test_04_concurrency_deterministic_reproducibility(self) -> None:
        """Concurrency N > 1 produces identical results and plan hashes as concurrency 1."""
        if self.dataset_path is None:
            self.skipTest("Operational snapshot not available.")

        test_tasks = ["T01", "T03", "R1", "R2"]  # 4 tasks x 3 arms = 12 runs
        dir_seq = Path(self.temp_dir.name) / "seq"
        dir_conc = Path(self.temp_dir.name) / "conc"

        manifest_seq = run_evaluation(
            dry_run=True,
            reps=1,
            seed=20260930,
            only_tasks=test_tasks,
            dataset_path=self.dataset_path,
            output_dir=dir_seq,
            run_id_prefix="er9",
            concurrency=1,
        )

        manifest_conc = run_evaluation(
            dry_run=True,
            reps=1,
            seed=20260930,
            only_tasks=test_tasks,
            dataset_path=self.dataset_path,
            output_dir=dir_conc,
            run_id_prefix="er9",
            concurrency=4,
        )

        self.assertEqual(manifest_seq["total_executed_runs"], 12)
        self.assertEqual(manifest_conc["total_executed_runs"], 12)
        self.assertEqual(manifest_seq["plan_hash_mismatches"], 0)
        self.assertEqual(manifest_conc["plan_hash_mismatches"], 0)
        self.assertEqual(manifest_conc["concurrency"], 4)

        # Verify all 12 run files match order, status, and plan hash
        runs_seq = {r["run_id"]: r for r in manifest_seq["runs"]}
        runs_conc = {r["run_id"]: r for r in manifest_conc["runs"]}
        self.assertEqual(set(runs_seq.keys()), set(runs_conc.keys()))

        for run_id in runs_seq:
            r1 = runs_seq[run_id]
            r2 = runs_conc[run_id]
            self.assertEqual(r1["order"], r2["order"], f"Shuffled order mismatch for {run_id}")
            self.assertEqual(r1["status"], r2["status"], f"Status mismatch for {run_id}")
            self.assertEqual(r1["plan_hash"], r2["plan_hash"], f"Plan hash mismatch for {run_id}")

        # Check consolidated runs.sqlite exists in concurrent run
        self.assertTrue((dir_conc / "runs.sqlite").exists())

    def test_05_concurrency_budget_abort(self) -> None:
        """Token budget guard aborts subsequent runs under concurrency."""
        if self.dataset_path is None:
            self.skipTest("Operational snapshot not available.")

        # Total tokens per run in dry run is ~540. With budget=600, only the first wave completes.
        manifest = run_evaluation(
            dry_run=True,
            reps=1,
            seed=20260930,
            only_tasks=["T01", "T02", "T03"],
            max_tokens=600,
            dataset_path=self.dataset_path,
            output_dir=self.output_dir,
            run_id_prefix="er9",
            concurrency=3,
        )

        self.assertTrue(manifest["budget_exceeded"])
        self.assertGreater(manifest["aborted_budget_runs"], 0)

        # Check that aborted runs have status aborted_budget in runs/
        runs_dir = self.output_dir / "runs"
        aborted_files = []
        for rf in runs_dir.glob("*.json"):
            data = json.loads(rf.read_text(encoding="utf-8"))
            if data["status"] == "aborted_budget":
                aborted_files.append(data)
                self.assertIsNone(data["plan"])
                self.assertEqual(data["tokens"]["total_tokens"], 0)
        self.assertGreater(len(aborted_files), 0)

    def test_06_resume_skips_completed_runs(self) -> None:
        """--resume flag skips already completed/blocked runs."""
        if self.dataset_path is None:
            self.skipTest("Operational snapshot not available.")

        # Phase 1: Run 1 task (3 runs)
        run_evaluation(
            dry_run=True,
            reps=1,
            only_tasks=["T01"],
            dataset_path=self.dataset_path,
            output_dir=self.output_dir,
            run_id_prefix="er9",
            concurrency=2,
        )

        t01_file = self.output_dir / "runs" / "er9-T01-single_agent-r0.json"
        self.assertTrue(t01_file.exists())
        mtime_before = t01_file.stat().st_mtime

        # Phase 2: Run with resume=True including T01 and T02
        manifest_resumed = run_evaluation(
            dry_run=True,
            reps=1,
            only_tasks=["T01", "T02"],
            dataset_path=self.dataset_path,
            output_dir=self.output_dir,
            run_id_prefix="er9",
            concurrency=2,
            resume=True,
        )

        self.assertEqual(manifest_resumed["total_executed_runs"], 6)
        mtime_after = t01_file.stat().st_mtime
        self.assertEqual(mtime_before, mtime_after, "Resumed run file should not have been overwritten")

    def test_07_deterministic_scoring_missingness_handling(self) -> None:
        """ER-9 has 0 missing cells: missingness_handled is None (reported as N/A in analysis)."""
        if self.dataset_path is None:
            self.skipTest("Operational snapshot not available.")

        run_evaluation(
            dry_run=True,
            reps=1,
            only_tasks=["T03", "T08"],
            dataset_path=self.dataset_path,
            output_dir=self.output_dir,
            run_id_prefix="er9",
        )

        scores_csv = self.output_dir / "scores" / "deterministic.csv"
        score_evaluation(
            runs_dir=self.output_dir / "runs",
            expected_coverage_path=self.expected_coverage_path,
            dataset_path=self.dataset_path,
            output_csv=scores_csv,
        )

        self.assertTrue(scores_csv.exists())
        with open(scores_csv, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            rows = list(reader)

        self.assertEqual(len(rows), 6)  # 2 tasks x 3 arms
        for r in rows:
            # missingness_handled should be empty string (None) for ER-9
            self.assertEqual(r["missingness_handled"], "", "ER-9 missingness_handled must be empty (N/A), not 1 or 0")

        # Run analyzer
        analysis_dir = self.output_dir / "analysis"
        results_md = self.output_dir / "RESULTS.md"
        analyze_evaluation(
            scores_csv=scores_csv,
            output_dir=analysis_dir,
            results_md=results_md,
            is_er9=True,
        )

        arm_summary_csv = analysis_dir / "arm_summary.csv"
        self.assertTrue(arm_summary_csv.exists())
        with open(arm_summary_csv, "r", encoding="utf-8") as f:
            summary_rows = list(csv.DictReader(f))
        for sr in summary_rows:
            self.assertEqual(sr["mean_missingness_handled"], "N/A")

    def test_08_cli_wrappers(self) -> None:
        """CLI wrapper scripts (er9_run, er9_score, er9_analyze) exist and are importable."""
        import scripts.er9_analyze as w_analyze
        import scripts.er9_run as w_run
        import scripts.er9_score as w_score

        self.assertTrue(callable(getattr(w_run, "main", None)))
        self.assertTrue(callable(getattr(w_score, "main", None)))
        self.assertTrue(callable(getattr(w_analyze, "main", None)))

    def test_09_scorer_dropped_sentences_and_fallback_flag(self) -> None:
        """Scorer counts dropped sentences from sentences_dropped list, supports old key, and tracks fallbacks."""
        cov_payload = json.loads(self.expected_coverage_path.read_text(encoding="utf-8"))
        cov_map = {t["task_id"]: t for t in cov_payload.get("tasks", [])}

        def make_run(
            audit: dict | None,
            task_id: str = "T01",
            status: str = "completed",
        ) -> dict:
            resp: dict = {"status": status}
            if audit is not None:
                resp["narrative_audit"] = audit
            return {
                "run_id": f"test-run-{task_id}",
                "task_id": task_id,
                "arm": "hierarchical_with_critique",
                "rep": 0,
                "order": 1,
                "status": status,
                "plan_hash": "a" * 64,
                "tokens": {"input_tokens": 10, "output_tokens": 10, "total_tokens": 20},
                "response": resp,
            }

        # 1. Primary key: sentences_dropped as list of 3, sentences_checked 10 -> discard rate 0.3
        run_primary = make_run({
            "sentences_checked": 10,
            "sentences_accepted": 7,
            "sentences_dropped": [{"sentence_id": "d1"}, {"sentence_id": "d2"}, {"sentence_id": "d3"}],
            "composition_source": "deterministic_fallback",
        })
        score_primary = score_single_run(run_primary, cov_map, {})
        self.assertEqual(score_primary["sentences_proposed"], 10)
        self.assertEqual(score_primary["sentences_accepted"], 7)
        self.assertEqual(score_primary["sentences_discarded"], 3)
        self.assertAlmostEqual(score_primary["discard_rate"], 0.3, places=4)
        self.assertEqual(score_primary["composition_fallback"], 1)

        # 2. Old key: dropped_sentences as list of 3, sentences_checked 10 -> discard rate 0.3
        run_old_list = make_run({
            "sentences_checked": 10,
            "sentences_accepted": 7,
            "dropped_sentences": [{"sentence_id": "d1"}, {"sentence_id": "d2"}, {"sentence_id": "d3"}],
            "composition_source": "model",
        })
        score_old_list = score_single_run(run_old_list, cov_map, {})
        self.assertEqual(score_old_list["sentences_discarded"], 3)
        self.assertAlmostEqual(score_old_list["discard_rate"], 0.3, places=4)
        self.assertEqual(score_old_list["composition_fallback"], 0)

        # 3. Old key with integer: dropped_sentences = 2
        run_old_int = make_run({
            "sentences_checked": 10,
            "sentences_accepted": 8,
            "dropped_sentences": 2,
            "composition_source": "model",
        })
        score_old_int = score_single_run(run_old_int, cov_map, {})
        self.assertEqual(score_old_int["sentences_discarded"], 2)
        self.assertAlmostEqual(score_old_int["discard_rate"], 0.2, places=4)

        # 4. Refused / no-audit run: composition_fallback is blank ("")
        run_refused = make_run(None, task_id="R1", status="error")
        score_refused = score_single_run(run_refused, cov_map, {})
        self.assertEqual(score_refused["composition_fallback"], "")
        self.assertEqual(score_refused["sentences_discarded"], 0)
        self.assertEqual(score_refused["discard_rate"], 0.0)

        # 5. Analyzer computes mean_composition_fallback and formats in RESULTS.md
        scores_csv = self.output_dir / "scores_fallback_test.csv"
        rows = [score_primary, score_old_list, score_refused]
        scores_csv.parent.mkdir(parents=True, exist_ok=True)
        with open(scores_csv, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=list(score_primary.keys()))
            writer.writeheader()
            writer.writerows(rows)

        analysis_dir = self.output_dir / "analysis_fallback"
        results_md = self.output_dir / "RESULTS_fallback.md"
        analyze_evaluation(
            scores_csv=scores_csv,
            output_dir=analysis_dir,
            results_md=results_md,
            is_er9=True,
        )

        with open(analysis_dir / "arm_summary.csv", "r", encoding="utf-8") as f:
            summary = list(csv.DictReader(f))
        arm_c = next(s for s in summary if s["arm"] == "hierarchical_with_critique")
        # 1 fallback out of 2 answered runs = 0.5 (refused run with blank is skipped)
        self.assertEqual(float(arm_c["mean_composition_fallback"]), 0.5)

        md_text = results_md.read_text(encoding="utf-8")
        self.assertIn("Composition Fallback", md_text)


if __name__ == "__main__":
    unittest.main()
