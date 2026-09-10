import json
import sqlite3
import tempfile
import unittest
from pathlib import Path

from thesis_data.agent_runtime import AgentCallRequest
from thesis_data.baseline_plan import BaselineJob
from thesis_data.baseline_runner import (
    BaselineExecutionError,
    execute_baseline_job,
)
from thesis_data.experiment_contract import ExperimentArm, ExperimentRunConfig
from thesis_data.question_set import question_set_sha256
from thesis_data.run_manifest import build_run_manifest
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


class BaselineRunnerTests(unittest.TestCase):
    periods = ("2024_Q1", "2024_Q2")

    def gold_config(self) -> GoldConfig:
        return GoldConfig(
            tickers=("VCB", "ACB"),
            periods=self.periods,
            required_metrics=("bank.npl_g35",),
            min_manual_labels=4,
            min_metric_coverage=1.0,
        )

    def question_set(self, root: Path) -> Path:
        path = root / "questions.json"
        path.write_text(
            json.dumps(
                {
                    "schema_version": 1,
                    "status": "test",
                    "question_set_id": "trend-questions-v1",
                    "scope": {
                        "issuers": ["VCB", "ACB"],
                        "periods": list(self.periods),
                        "core_metrics": ["bank.npl_g35"],
                    },
                    "questions": [{
                        "id": "trend-q1",
                        "issuer": "VCB",
                        "type": "company_trend",
                        "periods": list(self.periods),
                        "prompt": "trend fixture",
                    }],
                }
            ),
            encoding="utf-8",
        )
        return path

    def database(self, root: Path) -> Path:
        path = root / "gold.sqlite"
        config = self.gold_config()
        create_gold_snapshot_schema(path)
        connection = sqlite3.connect(path)
        connection.execute(
            "INSERT INTO snapshot_metadata VALUES (?, ?, ?, ?)",
            ("gold-v1", "2026-09-06T00:00:00Z", "gold", json.dumps(config.model_dump(mode="json"))),
        )
        connection.execute(
            "INSERT INTO source_records VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            ("source-1", "filing", "primary", "https://fixture.test/filing", "2026-09-06T00:00:00Z", "fixture.pdf", "hash-1", "fixture", "test", "valid", None),
        )
        observations = []
        labels = []
        value = 1.0
        for ticker in ("VCB", "ACB"):
            for period in self.periods:
                observation_id = f"obs-{ticker.lower()}-{period}"
                observations.append(
                    (observation_id, ticker, "bank", "bank.npl_g35", value, "%", period, "2024-03-31", "point_in_time", "source-1", "page:10", "valid", None)
                )
                for checker in ("checker-a", "checker-b"):
                    labels.append(
                        (f"label-{observation_id}-{checker}", observation_id, "value_check", value, None, checker, "2026-09-06T00:00:00Z", "page:10", "matched")
                    )
                value += 1.0
        connection.executemany(
            "INSERT INTO metric_observations VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            observations,
        )
        connection.executemany(
            "INSERT INTO gold_labels VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            labels,
        )
        connection.commit()
        connection.close()
        return path

    def run_config(self) -> ExperimentRunConfig:
        return ExperimentRunConfig(
            run_id="run-trend-v1",
            snapshot_id="gold-v1",
            question_set_id="trend-questions-v1",
            question_id="trend-q1",
            rubric_version="rubric-v1",
            prompt_version="prompt-contract-v1",
            arm=ExperimentArm.SINGLE_AGENT,
            model_id="fixture-model",
            source_policy_id="primary-only-v1",
        )

    def job(self, question_path: Path) -> BaselineJob:
        return BaselineJob(
            job_id="trend-q1:single_agent",
            snapshot_id="gold-v1",
            question_set_id="trend-questions-v1",
            question_set_sha256=question_set_sha256(question_path),
            question_id="trend-q1",
            arm=ExperimentArm.SINGLE_AGENT,
            issuer="VCB",
            periods=self.periods,
            metric_ids=("bank.npl_g35",),
        )

    def test_runner_passes_complete_trend_job_scope_to_runtime(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            question_path = self.question_set(root)
            adapter = RecordingAdapter()
            result = execute_baseline_job(
                self.database(root),
                self.job(question_path),
                self.run_config(),
                question_path,
                self.gold_config(),
                adapter,
            )
            manifest = build_run_manifest(
                result,
                "trend-q1",
                ("bank.npl_g35",),
                question_set_path=question_path,
            )

        self.assertEqual(len(adapter.requests), 1)
        self.assertEqual(result.job_id, "trend-q1:single_agent")
        self.assertEqual(manifest.job_id, "trend-q1:single_agent")
        self.assertEqual(adapter.requests[0].period, "2024_Q2")
        self.assertEqual(adapter.requests[0].periods, self.periods)
        self.assertEqual(
            adapter.requests[0].context["period_order"],
            list(self.periods),
        )

    def test_runner_rejects_job_question_hash_mismatch_before_dispatch(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            question_path = self.question_set(root)
            job = self.job(question_path).model_copy(
                update={"question_set_sha256": "0" * 64}
            )
            adapter = RecordingAdapter()

            with self.assertRaisesRegex(ValueError, "question_set_hash_mismatch"):
                execute_baseline_job(
                    self.database(root),
                    job,
                    self.run_config(),
                    question_path,
                    self.gold_config(),
                    adapter,
                )

        self.assertEqual(adapter.requests, [])

    def test_runner_exposes_runtime_input_blockers_without_calling_adapter(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            question_path = self.question_set(root)
            config = self.run_config().model_copy(update={"snapshot_id": "wrong"})
            adapter = RecordingAdapter()

            with self.assertRaises(BaselineExecutionError):
                execute_baseline_job(
                    self.database(root),
                    self.job(question_path),
                    config,
                    question_path,
                    self.gold_config(),
                    adapter,
                )

        self.assertEqual(adapter.requests, [])


if __name__ == "__main__":
    unittest.main()
