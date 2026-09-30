"""Offline integration and contract tests for ER-8 evaluation harness (PR-8 §9).

Ensures:
  1. Dry-run executes 36 runs (12 tasks x 3 arms x 1 rep) generating run JSONs and manifest.json.
  2. Plan hashes are identical across arms for every task under rules_only planner mode.
  3. Single agent arm has no critic calls and no critique trace steps.
  4. Hierarchical no critique arm has zero revision rounds.
  5. Budget guard stops execution when accumulated token budget is exceeded and records aborted_budget.
  6. Scorer detects hallucinated numbers and unresolvable observation IDs.
  7. Question set hashes match canonical LF UTF-8 SHA-256 bindings in task specs and expected coverage.
  8. Rejection control tasks (R1, R2) are properly blocked before model execution.
  9. Strict offline execution enforced by socket_guard.
  10. Unit test for _explicit_missing_claim with descriptive missing_reason.
  11. Scorer numeric correctness: report with all correct numbers gives 100%, 1 wrong number gives < 100%.
  12. When real Gold v5 is available locally, live hash and observation reconciliation are tested.
"""

from __future__ import annotations

import hashlib
import json
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from tests.socket_guard import install_socket_guard


def setUpModule() -> None:
    install_socket_guard()


from scripts.er8_analyze import HAS_MATPLOTLIB, analyze_evaluation, bootstrap_ci
from scripts.er8_run import (
    canonical_lf_utf8_sha256,
    find_gold_path,
    find_gold_path_or_none,
    run_evaluation,
)
from scripts.er8_score import (
    load_gold_observations,
    score_evaluation,
    score_single_run,
)
from thesis_api.adaptive_runtime import _explicit_missing_claim
from thesis_data.dataset_contract import CanonicalObservation, QualityStatus


class TestER8EvaluationHarness(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.root = Path(__file__).resolve().parents[1]
        cls.questions_path = cls.root / "data" / "evaluation" / "er8-questions-v2.jsonl"
        cls.task_specs_path = cls.root / "data" / "evaluation" / "er8-task-specs-v2.json"
        cls.expected_coverage_path = cls.root / "data" / "evaluation" / "er8-expected-coverage-v2.json"

        real_gold = find_gold_path_or_none()
        cls._real_gold_available = (real_gold is not None)

        if real_gold is not None:
            cls.gold_path = real_gold
            cls.fixture_dir = None
            cls.provider_patch = None
        else:
            # Create a small Gold-shaped fixture DB and mock provider so tests run fully in CI
            cls.fixture_dir = tempfile.TemporaryDirectory()
            cls.gold_path = Path(cls.fixture_dir.name) / "fixture_gold.sqlite"
            from thesis_data.storage import create_gold_snapshot_schema
            create_gold_snapshot_schema(cls.gold_path)

            from tests.test_api_er_report import _TableCGoldProvider
            from thesis_api.service import ProviderBinding
            provider = _TableCGoldProvider()
            binding = ProviderBinding(provider, provider.dataset_ref, provider.catalog, "gold-c-fixture")
            cls.provider_patch = patch("thesis_api.service._load_provider", return_value=binding)
            cls.provider_patch.start()

    @classmethod
    def tearDownClass(cls) -> None:
        if getattr(cls, "provider_patch", None) is not None:
            cls.provider_patch.stop()
        if getattr(cls, "fixture_dir", None) is not None:
            cls.fixture_dir.cleanup()

    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.output_dir = Path(self.temp_dir.name) / "er8"
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

    def test_02_dry_run_executes_all_36_runs_and_writes_manifest(self) -> None:
        """--dry-run executes all 12 tasks x 3 arms = 36 runs with zero network calls."""
        manifest = run_evaluation(
            dry_run=True,
            reps=1,
            seed=20260930,
            max_tokens=3000000,
            gold_path=self.gold_path,
            output_dir=self.output_dir,
        )

        self.assertEqual(manifest["total_planned_runs"], 36)
        self.assertEqual(manifest["total_executed_runs"], 36)
        self.assertFalse(manifest["budget_exceeded"])
        self.assertEqual(manifest["plan_hash_mismatches"], 0)

        # Check all 36 JSON run files exist
        runs_dir = self.output_dir / "runs"
        run_files = list(runs_dir.glob("*.json"))
        self.assertEqual(len(run_files), 36)

        # Check manifest.json on disk
        manifest_path = self.output_dir / "manifest.json"
        self.assertTrue(manifest_path.exists())

        # Check that manifest file paths are relative to repo root (no absolute D:/)
        manifest_data = json.loads(manifest_path.read_text(encoding="utf-8"))
        self.assertFalse(manifest_data["questions_file"].startswith("D:"), "questions_file must be relative")
        self.assertFalse(manifest_data["task_specs_file"].startswith("D:"), "task_specs_file must be relative")
        self.assertFalse(manifest_data["expected_coverage_file"].startswith("D:"), "expected_coverage_file must be relative")

    def test_03_plan_hash_identical_across_arms_for_same_task(self) -> None:
        """planner_mode='rules_only' ensures identical plan hashes across arms A, B, C for each task."""
        manifest = run_evaluation(
            dry_run=True,
            reps=1,
            seed=20260930,
            max_tokens=3000000,
            gold_path=self.gold_path,
            output_dir=self.output_dir,
        )

        # Group runs by task_id
        runs_by_task: dict[str, dict[str, str]] = {}
        for r in manifest["runs"]:
            t_id = r["task_id"]
            if t_id not in runs_by_task:
                runs_by_task[t_id] = {}
            runs_by_task[t_id][r["arm"]] = r["plan_hash"]

        for t_id, arm_hashes in runs_by_task.items():
            self.assertEqual(
                len(arm_hashes),
                3,
                f"Task {t_id} did not execute all 3 arms.",
            )
            hashes_set = set(arm_hashes.values())
            self.assertEqual(
                len(hashes_set),
                1,
                f"Task {t_id} has diverging plan hashes across arms: {arm_hashes}",
            )

    def test_04_single_agent_has_no_critic_and_no_specialists(self) -> None:
        """Arm A (single_agent) has zero critic calls, no critic trace steps, and no specialist drafts."""
        manifest = run_evaluation(
            dry_run=True,
            reps=1,
            only_tasks=["T01", "T02"],
            gold_path=self.gold_path,
            output_dir=self.output_dir,
        )

        runs_dir = self.output_dir / "runs"
        for r_meta in manifest["runs"]:
            if r_meta["arm"] == "single_agent":
                run_file = runs_dir / f"{r_meta['run_id']}.json"
                run_data = json.loads(run_file.read_text(encoding="utf-8"))
                trace = run_data.get("trace", [])

                # Verify no steps from or to critic
                critic_steps = [s for s in trace if s.get("actor") == "critic" or s.get("recipient") == "critic"]
                self.assertEqual(
                    len(critic_steps),
                    0,
                    f"Single agent run {r_meta['run_id']} has critic trace steps: {critic_steps}",
                )

                # Verify no specialist draft steps
                specialist_drafts = [s for s in trace if s.get("kind") == "draft"]
                self.assertEqual(
                    len(specialist_drafts),
                    0,
                    f"Single agent run {r_meta['run_id']} has specialist draft steps: {specialist_drafts}",
                )

    def test_05_hierarchical_no_critique_has_no_revisions(self) -> None:
        """Arm B (hierarchical_no_critique) has specialist findings but zero revision rounds."""
        manifest = run_evaluation(
            dry_run=True,
            reps=1,
            only_tasks=["T01", "T02"],
            gold_path=self.gold_path,
            output_dir=self.output_dir,
        )

        runs_dir = self.output_dir / "runs"
        for r_meta in manifest["runs"]:
            if r_meta["arm"] == "hierarchical_no_critique":
                run_file = runs_dir / f"{r_meta['run_id']}.json"
                run_data = json.loads(run_file.read_text(encoding="utf-8"))
                trace = run_data.get("trace", [])

                revise_steps = [s for s in trace if s.get("kind") == "revise"]
                self.assertEqual(len(revise_steps), 0)

    def test_06_budget_guard_stops_and_records_aborted_budget(self) -> None:
        """Budget guard stops execution when accumulated tokens exceed max_tokens, recording aborted_budget."""
        manifest = run_evaluation(
            dry_run=True,
            reps=1,
            seed=20260930,
            max_tokens=500,
            gold_path=self.gold_path,
            output_dir=self.output_dir,
        )

        self.assertTrue(manifest["budget_exceeded"])
        self.assertGreater(manifest["aborted_budget_runs"], 0)
        self.assertEqual(
            manifest["completed_runs"] + manifest["error_runs"] + manifest["aborted_budget_runs"],
            36,
            "Total accounted runs must equal 36 planned runs in the denominator.",
        )

        # Check an aborted file
        runs_dir = self.output_dir / "runs"
        aborted_files = [f for f in runs_dir.glob("*.json") if "aborted_budget" in f.read_text(encoding="utf-8")]
        self.assertGreater(len(aborted_files), 0)
        aborted_data = json.loads(aborted_files[0].read_text(encoding="utf-8"))
        self.assertEqual(aborted_data["status"], "aborted_budget")

    def test_07_scorer_catches_hallucinated_number(self) -> None:
        """Scorer marks numeric_correctness = 0 when sentence contains a number not in cited facts."""
        gold_obs = {
            "expansion:official-MBB-2024-Q4-consolidated:2024_Q4:bank.npl_g35": {
                "observation_id": "expansion:official-MBB-2024-Q4-consolidated:2024_Q4:bank.npl_g35",
                "ticker": "MBB",
                "period": "2024_Q4",
                "metric": "bank.npl_g35",
                "value": 1.6205,
                "unit": "%",
                "quality_status": "accepted",
                "source_locator": "BCTC Q4 p.10",
            }
        }
        cov_payload = json.loads(self.expected_coverage_path.read_text(encoding="utf-8"))
        cov_map = {t["task_id"]: t for t in cov_payload.get("tasks", [])}

        mock_run = {
            "run_id": "test-mock-run-001",
            "task_id": "T01",
            "arm": "hierarchical_with_critique",
            "status": "completed",
            "tokens": {"input_tokens": 100, "output_tokens": 50, "total_tokens": 150},
            "response": {
                "status": "completed",
                "facts": [
                    {
                        "fact_id": "f-1",
                        "fact_type": "value",
                        "entity_id": "MBB",
                        "metric_id": "bank.npl_g35",
                        "period": "2024_Q4",
                        "value": 1.6205,
                        "unit": "%",
                        "input_observation_ids": ["expansion:official-MBB-2024-Q4-consolidated:2024_Q4:bank.npl_g35"],
                    }
                ],
                "report_spec": {
                    "kind": "note",
                    "blocks": [
                        {
                            "type": "headline",
                            "sentence": {
                                "sentence_id": "s-1",
                                "text": "Tỷ lệ nợ xấu của MBB đạt 99,99% tăng đột biến.",  # Hallucinated number 99.99%
                                "fact_ids": ["f-1"],
                            },
                        }
                    ],
                },
                "narrative_audit": {"sentences_checked": 1, "sentences_accepted": 1, "dropped_sentences": []},
            },
            "trace": [],
        }

        score = score_single_run(mock_run, cov_map, gold_obs)
        self.assertEqual(score["numeric_correctness"], 0.0)
        self.assertEqual(score["numbers_checked"], 1)
        self.assertEqual(score["numbers_matched"], 0)

    def test_08_scorer_catches_unresolvable_observation(self) -> None:
        """Scorer flags traceability_score < 1.0 when fact cites non-existent observation ID."""
        gold_obs = {
            "expansion:official-MBB-2024-Q4-consolidated:2024_Q4:bank.npl_g35": {
                "observation_id": "expansion:official-MBB-2024-Q4-consolidated:2024_Q4:bank.npl_g35",
                "ticker": "MBB",
                "period": "2024_Q4",
                "metric": "bank.npl_g35",
                "value": 1.6205,
                "unit": "%",
                "quality_status": "accepted",
                "source_locator": "BCTC Q4 p.10",
            }
        }
        cov_payload = json.loads(self.expected_coverage_path.read_text(encoding="utf-8"))
        cov_map = {t["task_id"]: t for t in cov_payload.get("tasks", [])}

        mock_run = {
            "run_id": "test-mock-run-002",
            "task_id": "T01",
            "arm": "hierarchical_with_critique",
            "status": "completed",
            "tokens": {"input_tokens": 100, "output_tokens": 50, "total_tokens": 150},
            "response": {
                "status": "completed",
                "facts": [
                    {
                        "fact_id": "f-1",
                        "fact_type": "value",
                        "entity_id": "MBB",
                        "metric_id": "bank.npl_g35",
                        "period": "2024_Q4",
                        "value": 1.6205,
                        "unit": "%",
                        "input_observation_ids": ["fabricated:fake-observation-12345"],  # Fake observation ID
                    }
                ],
                "report_spec": {
                    "kind": "note",
                    "blocks": [
                        {
                            "type": "headline",
                            "sentence": {
                                "sentence_id": "s-1",
                                "text": "Tỷ lệ nợ xấu của MBB đạt 1,62%.",
                                "fact_ids": ["f-1"],
                            },
                        }
                    ],
                },
                "narrative_audit": {"sentences_checked": 1, "sentences_accepted": 1, "dropped_sentences": []},
            },
            "trace": [],
        }

        score = score_single_run(mock_run, cov_map, gold_obs)
        self.assertEqual(score["traceability_score"], 0.0)
        self.assertEqual(score["obs_cited_count"], 1)
        self.assertEqual(score["obs_resolved_count"], 0)

    def test_09_rejection_controls_properly_blocked_with_expected_codes(self) -> None:
        """Rejection controls R1 (2025_Q1) and R2 (CTG) are properly blocked with expected codes."""
        manifest = run_evaluation(
            dry_run=True,
            reps=1,
            only_tasks=["R1", "R2"],
            gold_path=self.gold_path,
            output_dir=self.output_dir,
        )

        runs_dir = self.output_dir / "runs"
        scored = score_evaluation(
            runs_dir=runs_dir,
            expected_coverage_path=self.expected_coverage_path,
            gold_path=self.gold_path,
            output_csv=self.output_dir / "scores.csv",
        )

        r1_scores = [s for s in scored if s["task_id"] == "R1"]
        r2_scores = [s for s in scored if s["task_id"] == "R2"]

        self.assertEqual(len(r1_scores), 3)
        self.assertEqual(len(r2_scores), 3)

        for s in r1_scores:
            self.assertEqual(s["correct_rejection"], 1)
            self.assertEqual(s["protocol_success"], 1)

        for s in r2_scores:
            self.assertEqual(s["correct_rejection"], 1)
            self.assertEqual(s["protocol_success"], 1)

    def test_10_analyzer_produces_tables_and_markdown(self) -> None:
        """Analyzer computes bootstrap CIs and produces CSVs and RESULTS.md."""
        manifest = run_evaluation(
            dry_run=True,
            reps=1,
            only_tasks=["T01", "T02"],
            gold_path=self.gold_path,
            output_dir=self.output_dir,
        )

        scores_csv = self.output_dir / "scores" / "deterministic.csv"
        score_evaluation(
            runs_dir=self.output_dir / "runs",
            expected_coverage_path=self.expected_coverage_path,
            gold_path=self.gold_path,
            output_csv=scores_csv,
        )

        analysis_dir = self.output_dir / "analysis"
        results_md = self.output_dir / "RESULTS.md"

        analyze_evaluation(
            scores_csv=scores_csv,
            output_dir=analysis_dir,
            results_md=results_md,
        )

        self.assertTrue((analysis_dir / "arm_summary.csv").exists())
        self.assertTrue((analysis_dir / "pairwise_diffs.csv").exists())
        self.assertTrue(results_md.exists())

        md_text = results_md.read_text(encoding="utf-8")
        self.assertIn("Báo cáo Đánh giá Thực nghiệm A/B/C (ER-8)", md_text)
        self.assertIn("Arm A", md_text)
        self.assertIn("Arm B", md_text)
        self.assertIn("Arm C", md_text)

    @unittest.skipUnless(HAS_MATPLOTLIB, "matplotlib not installed; skipping PNG figures check")
    def test_10b_analyzer_produces_figures(self) -> None:
        """Analyzer produces PNG figures when matplotlib is installed."""
        manifest = run_evaluation(
            dry_run=True,
            reps=1,
            only_tasks=["T01"],
            gold_path=self.gold_path,
            output_dir=self.output_dir,
        )

        scores_csv = self.output_dir / "scores" / "deterministic.csv"
        score_evaluation(
            runs_dir=self.output_dir / "runs",
            expected_coverage_path=self.expected_coverage_path,
            gold_path=self.gold_path,
            output_csv=scores_csv,
        )

        analysis_dir = self.output_dir / "analysis"
        results_md = self.output_dir / "RESULTS.md"

        analyze_evaluation(
            scores_csv=scores_csv,
            output_dir=analysis_dir,
            results_md=results_md,
        )

        self.assertTrue((analysis_dir / "figure_er8_completion_accuracy.png").exists())
        self.assertTrue((analysis_dir / "figure_er8_cost_latency.png").exists())
        self.assertTrue((analysis_dir / "figure_er8_pairwise_diff.png").exists())

    def test_11_explicit_missing_claim_accepts_descriptive_missing_reason(self) -> None:
        """Missing cell with descriptive missing_reason (Gold v5 format) generates valid claim and does not raise."""
        obs = CanonicalObservation(
            dataset_id="gold_bank_v5",
            dataset_snapshot_id="snap1",
            observation_id="missing:ACB:2024_Q1:bank.npl_g35",
            entity_id="ACB",
            period_id="2024_Q1",
            metric_id="bank.npl_g35",
            value=None,
            unit="percent",
            validation_status=QualityStatus.MISSING,
            missing_reason=(
                "The official issuer source reports 1.45% including CIC-linked groups and 1.3% "
                "excluding CIC impact, but does not expose the canonical group 3–5 mapping or "
                "denominator. The cell is missing under D-055 because selecting a variant would guess the definition."
            ),
        )
        claim = _explicit_missing_claim(
            obs,
            display_name="Tỷ lệ nợ xấu (NPL)",
            capability="financial_health",
            macro=False,
        )
        self.assertIsNotNone(claim)
        self.assertEqual(claim.claim_id, "claim-missing:ACB:2024_Q1:bank.npl_g35")
        self.assertIn("unavailable", claim.claim_text.lower())
        self.assertEqual(claim.assertions[0].operator.value, "missing")
        self.assertEqual(claim.assertions[0].data_refs[0].ref_type, "missing_cell")

        # Non-missing observation must raise ValueError
        valid_obs = CanonicalObservation(
            dataset_id="gold_bank_v5",
            dataset_snapshot_id="snap1",
            observation_id="obs:ACB:2024_Q1:bank.npl_g35",
            entity_id="ACB",
            period_id="2024_Q1",
            metric_id="bank.npl_g35",
            value=1.5,
            unit="percent",
            validation_status=QualityStatus.VALID,
            source_ref="src-1",
        )
        with self.assertRaises(ValueError):
            _explicit_missing_claim(
                valid_obs,
                display_name="Tỷ lệ nợ xấu (NPL)",
                capability="financial_health",
            )

    def test_12_scorer_numeric_correctness_with_correct_and_wrong_sentences(self) -> None:
        """Mock report with correct numbers yields 1.0 (100%); 1 wrong number yields < 1.0."""
        cov_payload = json.loads(self.expected_coverage_path.read_text(encoding="utf-8"))
        cov_map = {t["task_id"]: t for t in cov_payload.get("tasks", [])}
        gold_obs = {
            "obs:MBB:2024_Q4:bank.npl_g35": {
                "observation_id": "obs:MBB:2024_Q4:bank.npl_g35",
                "ticker": "MBB",
                "period": "2024_Q4",
                "metric": "bank.npl_g35",
                "value": 1.62,
                "unit": "%",
                "quality_status": "accepted",
                "source_locator": "BCTC Q4",
            },
            "obs:MBB:2024_Q4:bank.llr_coverage": {
                "observation_id": "obs:MBB:2024_Q4:bank.llr_coverage",
                "ticker": "MBB",
                "period": "2024_Q4",
                "metric": "bank.llr_coverage",
                "value": 92.2,
                "unit": "%",
                "quality_status": "accepted",
                "source_locator": "BCTC Q4",
            },
        }

        # 1. Report with 2 correct sentences matching facts
        correct_run = {
            "run_id": "test-mock-correct-run",
            "task_id": "T01",
            "arm": "hierarchical_with_critique",
            "status": "completed",
            "tokens": {"input_tokens": 100, "output_tokens": 50, "total_tokens": 150},
            "response": {
                "status": "completed",
                "facts": [
                    {
                        "fact_id": "f-npl",
                        "fact_type": "value",
                        "entity_id": "MBB",
                        "metric_id": "bank.npl_g35",
                        "period": "2024_Q4",
                        "value": 1.62,
                        "unit": "%",
                        "input_observation_ids": ["obs:MBB:2024_Q4:bank.npl_g35"],
                    },
                    {
                        "fact_id": "f-llr",
                        "fact_type": "value",
                        "entity_id": "MBB",
                        "metric_id": "bank.llr_coverage",
                        "period": "2024_Q4",
                        "value": 92.2,
                        "unit": "%",
                        "input_observation_ids": ["obs:MBB:2024_Q4:bank.llr_coverage"],
                    },
                ],
                "report_spec": {
                    "kind": "note",
                    "blocks": [
                        {
                            "type": "headline",
                            "sentence": {
                                "sentence_id": "s-1",
                                "text": "Tỷ lệ nợ xấu của MBB đạt 1,62%.",
                                "fact_ids": ["f-npl"],
                            },
                        },
                        {
                            "type": "answer",
                            "sentences": [
                                {
                                    "sentence_id": "s-2",
                                    "text": "Tỷ lệ bao phủ nợ xấu của MBB đạt 92,2%.",
                                    "fact_ids": ["f-llr"],
                                }
                            ],
                        },
                    ],
                },
            },
            "trace": [],
        }

        score_correct = score_single_run(correct_run, cov_map, gold_obs)
        self.assertEqual(score_correct["numeric_correctness"], 1.0, "Report with all correct numbers must score 1.0 (100%)")
        self.assertEqual(score_correct["numbers_checked"], 2)
        self.assertEqual(score_correct["numbers_matched"], 2)

        # 2. Report with 1 correct sentence and 1 wrong sentence (50.0% instead of 92.2%)
        partially_wrong_run = {
            "run_id": "test-mock-partially-wrong-run",
            "task_id": "T01",
            "arm": "hierarchical_with_critique",
            "status": "completed",
            "tokens": {"input_tokens": 100, "output_tokens": 50, "total_tokens": 150},
            "response": {
                "status": "completed",
                "facts": [
                    {
                        "fact_id": "f-npl",
                        "fact_type": "value",
                        "entity_id": "MBB",
                        "metric_id": "bank.npl_g35",
                        "period": "2024_Q4",
                        "value": 1.62,
                        "unit": "%",
                        "input_observation_ids": ["obs:MBB:2024_Q4:bank.npl_g35"],
                    },
                    {
                        "fact_id": "f-llr",
                        "fact_type": "value",
                        "entity_id": "MBB",
                        "metric_id": "bank.llr_coverage",
                        "period": "2024_Q4",
                        "value": 92.2,
                        "unit": "%",
                        "input_observation_ids": ["obs:MBB:2024_Q4:bank.llr_coverage"],
                    },
                ],
                "report_spec": {
                    "kind": "note",
                    "blocks": [
                        {
                            "type": "headline",
                            "sentence": {
                                "sentence_id": "s-1",
                                "text": "Tỷ lệ nợ xấu của MBB đạt 1,62%.",
                                "fact_ids": ["f-npl"],
                            },
                        },
                        {
                            "type": "answer",
                            "sentences": [
                                {
                                    "sentence_id": "s-2",
                                    "text": "Tỷ lệ bao phủ nợ xấu của MBB đạt 50,0%.",
                                    "fact_ids": ["f-llr"],
                                }
                            ],
                        },
                    ],
                },
            },
            "trace": [],
        }

        score_wrong = score_single_run(partially_wrong_run, cov_map, gold_obs)
        self.assertLess(score_wrong["numeric_correctness"], 1.0, "Report with wrong number must score < 1.0 (< 100%)")
        self.assertEqual(score_wrong["numeric_correctness"], 0.5)
        self.assertEqual(score_wrong["numbers_checked"], 2)
        self.assertEqual(score_wrong["numbers_matched"], 1)

    @unittest.skipUnless(find_gold_path_or_none() is not None, "Real Gold v5 database not found in local environment")
    def test_13_gold_v5_live_hash_and_reconciliation(self) -> None:
        """When real Gold v5 SQLite is present locally, verify its byte hash and observation loading."""
        real_gold = find_gold_path()
        self.assertIsNotNone(real_gold)
        raw_hash = hashlib.sha256(real_gold.read_bytes()).hexdigest().lower()
        from scripts.er8_run import GOLD_RAW_BYTES_SHA256
        self.assertEqual(raw_hash, GOLD_RAW_BYTES_SHA256)

        obs = load_gold_observations(real_gold)
        self.assertGreater(len(obs), 0)
        self.assertTrue(any(o["ticker"] == "MBB" and o["period"] == "2024_Q4" for o in obs.values()))


if __name__ == "__main__":
    unittest.main()
