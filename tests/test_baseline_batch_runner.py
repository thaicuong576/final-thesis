import json
import os
import sqlite3
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from thesis_data.baseline_plan import build_baseline_plan
from thesis_data.baseline_batch_runner import (
    BaselineBatchExecutionError,
    execute_baseline_plan,
    preflight_baseline_plan_inputs,
)
from thesis_data.provider_config import ProviderExecutionConfig
from thesis_data.experiment_contract import ExperimentArm
from thesis_data.agent_runtime import AgentCallRequest
from thesis_data.question_set import load_question_set
from thesis_data.schema import AgentPayload, AgentStatus, GoldConfig
from thesis_data.storage import create_gold_snapshot_schema


class RecordingAdapter:
    def __init__(self):
        self.requests: list[AgentCallRequest] = []

    def complete(self, request: AgentCallRequest) -> AgentPayload:
        self.requests.append(request)
        return AgentPayload(
            agent_id=request.role,
            status=AgentStatus.SUCCESS,
            ticker=request.ticker,
            period=request.period,
        )


class BaselineBatchRunnerTests(unittest.TestCase):
    def fixture(self, root: Path, snapshot_id: str = "fixture-gold-v1") -> tuple[Path, Path, Path, GoldConfig]:
        config = GoldConfig(
            tickers=("VCB", "ACB"),
            periods=("2024_Q1",),
            required_metrics=("bank.npl_g35",),
            min_manual_labels=4,
        )
        db_path = root / "gold.sqlite"
        create_gold_snapshot_schema(db_path)
        connection = sqlite3.connect(db_path)
        connection.execute(
            "INSERT INTO snapshot_metadata VALUES (?, ?, ?, ?)",
            (snapshot_id, "2026-09-06T00:00:00Z", "gold", json.dumps(config.model_dump(mode="json"))),
        )
        connection.execute(
            "INSERT INTO source_records VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            ("source-1", "filing", "primary", "https://fixture.test/filing", "2026-09-06T00:00:00Z", "fixture.pdf", "hash-1", "fixture", "test", "valid", None),
        )
        observations = [
            ("obs-vcb", "VCB", "bank", "bank.npl_g35", 2.0, "%", "2024_Q1", "2024-03-31", "point_in_time", "source-1", "page:10", "valid", None),
            ("obs-acb", "ACB", "bank", "bank.npl_g35", 1.0, "%", "2024_Q1", "2024-03-31", "point_in_time", "source-1", "page:11", "valid", None),
        ]
        connection.executemany(
            "INSERT INTO metric_observations VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            observations,
        )
        labels = []
        for observation_id, value, locator in (("obs-vcb", 2.0, "page:10"), ("obs-acb", 1.0, "page:11")):
            for checker in ("checker-a", "checker-b"):
                labels.append(
                    (f"label-{observation_id}-{checker}", observation_id, "value_check", value, None, checker, "2026-09-06T00:00:00Z", locator, "matched")
                )
        connection.executemany(
            "INSERT INTO gold_labels VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            labels,
        )
        connection.commit()
        connection.close()

        question_path = root / "questions.json"
        question_path.write_text(
            json.dumps(
                {
                    "schema_version": 1,
                    "status": "test",
                    "question_set_id": "fixture-questions-v1",
                    "scope": {
                        "issuers": ["VCB", "ACB"],
                        "periods": ["2024_Q1"],
                        "core_metrics": ["bank.npl_g35"],
                    },
                    "questions": [{
                        "id": "q1",
                        "issuer": "VCB",
                        "type": "company_snapshot",
                        "period": "2024_Q1",
                        "prompt": "fixture",
                    }],
                }
            ),
            encoding="utf-8",
        )
        plan_path = root / "plan.json"
        plan = build_baseline_plan(
            load_question_set(question_path),
            question_path,
            snapshot_id,
        )
        plan_path.write_text(
            json.dumps(plan.model_dump(mode="json"), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        return db_path, question_path, plan_path, config

    def test_batch_runner_executes_all_plan_jobs_and_writes_immutable_manifests(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            db_path, question_path, plan_path, config = self.fixture(root)
            adapter = RecordingAdapter()
            output_dir = root / "runs"

            result = execute_baseline_plan(
                db_path,
                plan_path,
                question_path,
                config,
                adapter,
                output_dir,
                run_id_prefix="batch-v1",
                rubric_version="rubric-v1",
                model_id="fixture-model",
                source_policy_id="primary-only-v1",
                environment="offline_fixture",
                comparative_result=False,
                verification_requests=("batch-check-1", "batch-check-2"),
            )

            self.assertEqual(len(result.manifests), 3)
            self.assertEqual(len(list(output_dir.glob("*.json"))), 3)
            self.assertEqual(
                {manifest.job_id for manifest in result.manifests},
                {f"q1:{arm.value}" for arm in ExperimentArm},
            )
            self.assertEqual(
                [manifest.call_count for manifest in result.manifests],
                [1, 4, 6],
            )
            self.assertTrue(all(not manifest.comparative_result for manifest in result.manifests))
            self.assertEqual(
                {manifest.prompt_version for manifest in result.manifests},
                {"prompt-contract-v1"},
            )
            self.assertEqual(len(adapter.requests), 11)

    def test_provider_backed_execution_requires_explicit_provider_config(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            db_path, question_path, plan_path, config = self.fixture(root)
            adapter = RecordingAdapter()
            output_dir = root / "runs"

            with self.assertRaisesRegex(
                BaselineBatchExecutionError,
                "provider_config_required",
            ):
                execute_baseline_plan(
                    db_path,
                    plan_path,
                    question_path,
                    config,
                    adapter,
                    output_dir,
                    run_id_prefix="batch-v1",
                    rubric_version="rubric-v1",
                    model_id="fixture-model",
                    source_policy_id="primary-only-v1",
                    environment="provider_backed",
                    comparative_result=False,
                )

            self.assertEqual(adapter.requests, [])
            self.assertFalse(output_dir.exists())

    def test_plan_input_preflight_is_read_only_and_checks_every_job(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            db_path, question_path, plan_path, config = self.fixture(root)

            audit = preflight_baseline_plan_inputs(
                db_path,
                plan_path,
                question_path,
                config,
                run_id_prefix="preflight-v1",
                rubric_version="rubric-v1",
                model_id="fixture-model",
                source_policy_id="primary-only-v1",
            )

        self.assertTrue(audit.eligible, audit.blockers)
        self.assertEqual(audit.job_count, 3)
        self.assertEqual(audit.snapshot_id, "fixture-gold-v1")
        self.assertEqual(audit.blockers, ())

    def test_plan_input_preflight_cli_is_read_only(self):
        project_root = Path(__file__).parents[1]
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            db_path, question_path, plan_path, _config = self.fixture(root)
            before = {
                "db": db_path.read_bytes(),
                "question": question_path.read_bytes(),
                "plan": plan_path.read_bytes(),
            }
            environment = dict(os.environ)
            environment["PYTHONPATH"] = str(project_root / "src")
            result = subprocess.run(
                [
                    sys.executable,
                    "scripts/preflight_baseline_plan_inputs.py",
                    str(db_path),
                    str(plan_path),
                    str(question_path),
                    "--ticker", "VCB",
                    "--ticker", "ACB",
                    "--period", "2024_Q1",
                    "--metric", "bank.npl_g35",
                    "--run-id-prefix", "preflight-v1",
                    "--rubric-version", "rubric-v1",
                    "--model-id", "fixture-model",
                    "--source-policy-id", "primary-only-v1",
                    "--min-manual-labels", "4",
                    "--min-metric-coverage", "0.9",
                ],
                cwd=project_root,
                env=environment,
                capture_output=True,
                text=True,
                check=False,
            )

            after = {
                "db": db_path.read_bytes(),
                "question": question_path.read_bytes(),
                "plan": plan_path.read_bytes(),
            }

        self.assertEqual(result.returncode, 0, f"stderr={result.stderr}; stdout={result.stdout}")
        payload = json.loads(result.stdout)
        self.assertTrue(payload["eligible"], payload)
        self.assertEqual(payload["job_count"], 3)
        self.assertEqual(before, after)

    def test_batch_runner_rejects_pending_snapshot_before_dispatch(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            db_path, question_path, _plan_path, config = self.fixture(root)
            pending_plan_path = root / "pending-plan.json"
            pending_plan = build_baseline_plan(
                load_question_set(question_path),
                question_path,
                "PENDING_GOLD_SNAPSHOT",
            )
            pending_plan_path.write_text(
                json.dumps(pending_plan.model_dump(mode="json")),
                encoding="utf-8",
            )
            adapter = RecordingAdapter()
            output_dir = root / "runs"

            with self.assertRaisesRegex(BaselineBatchExecutionError, "snapshot_placeholder"):
                execute_baseline_plan(
                    db_path,
                    pending_plan_path,
                    question_path,
                    config,
                    adapter,
                    output_dir,
                    run_id_prefix="batch-v1",
                    rubric_version="rubric-v1",
                    model_id="fixture-model",
                    source_policy_id="primary-only-v1",
                    environment="offline_fixture",
                    comparative_result=False,
                )

            self.assertEqual(adapter.requests, [])
            self.assertFalse(output_dir.exists())

    def test_batch_runner_preflights_all_job_inputs_before_first_dispatch(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            db_path, _question_path, _plan_path, config = self.fixture(root)
            question_path = root / "macro-questions.json"
            question_path.write_text(
                json.dumps(
                    {
                        "schema_version": 1,
                        "status": "test",
                        "question_set_id": "macro-questions-v1",
                        "scope": {
                            "issuers": ["VCB", "ACB"],
                            "periods": ["2024_Q1"],
                            "core_metrics": ["bank.npl_g35"],
                        },
                        "questions": [{
                            "id": "macro-q1",
                            "issuer": "VCB",
                            "type": "macro_to_bank",
                            "period": "2024_Q1",
                            "macro_indicator_ids": ["macro.policy_rate"],
                            "bank_metric_ids": ["bank.npl_g35"],
                            "causal_claim_policy": "association_only",
                            "prompt": "macro fixture",
                        }],
                    }
                ),
                encoding="utf-8",
            )
            plan_path = root / "macro-plan.json"
            plan = build_baseline_plan(
                load_question_set(question_path),
                question_path,
                "fixture-gold-v1",
            )
            plan_path.write_text(
                json.dumps(plan.model_dump(mode="json")),
                encoding="utf-8",
            )
            adapter = RecordingAdapter()
            output_dir = root / "runs"

            with self.assertRaisesRegex(
                BaselineBatchExecutionError,
                "missing_accepted_macro_observation",
            ):
                execute_baseline_plan(
                    db_path,
                    plan_path,
                    question_path,
                    config,
                    adapter,
                    output_dir,
                    run_id_prefix="batch-v1",
                    rubric_version="rubric-v1",
                    model_id="fixture-model",
                    source_policy_id="primary-only-v1",
                    environment="offline_fixture",
                    comparative_result=False,
                )

            self.assertEqual(adapter.requests, [])
            self.assertFalse(output_dir.exists())


if __name__ == "__main__":
    unittest.main()
