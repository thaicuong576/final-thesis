import json
from dataclasses import replace
from hashlib import sha256
import sqlite3
import tempfile
import unittest
from pathlib import Path

from thesis_data.agent_runtime import (
    AgentCallRequest,
    AgentCallTelemetry,
    AgentCompletion,
    RuntimeRunResult,
    run_agent_arm,
)
from thesis_data.experiment_contract import ExperimentArm, ExperimentRunConfig
from thesis_data.prompting import render_agent_prompt
from thesis_data.run_manifest import build_run_manifest, write_run_manifest
from thesis_data.schema import AgentPayload, AgentStatus, GoldConfig
from thesis_data.storage import create_gold_snapshot_schema


class FixtureAdapter:
    def complete(self, request):
        return AgentPayload(
            agent_id=request.role,
            status=AgentStatus.SUCCESS,
            ticker=request.ticker,
            period=request.period,
            findings=["offline_fixture_payload"],
        )


class TelemetryAdapter:
    def complete(self, request):
        return AgentCompletion(
            payload=AgentPayload(
                agent_id=request.role,
                status=AgentStatus.SUCCESS,
                ticker=request.ticker,
                period=request.period,
                findings=["telemetry_fixture_payload"],
            ),
            telemetry=AgentCallTelemetry(
                status="provided",
                latency_ms=12.5,
                input_tokens=100,
                output_tokens=20,
                cost_estimate=0.003,
            ),
        )


class RunManifestTests(unittest.TestCase):
    def gold_config(self) -> GoldConfig:
        return GoldConfig(
            tickers=("VCB", "ACB"),
            periods=("2024_Q1",),
            required_metrics=("bank.npl_g35",),
            min_manual_labels=4,
            min_metric_coverage=1.0,
        )

    def run_config(self, arm: ExperimentArm) -> ExperimentRunConfig:
        return ExperimentRunConfig(
            run_id=f"offline-{arm.value}",
            snapshot_id="fixture-gold-v1",
            question_set_id="fixture-questions-v1",
            question_id="q1",
            rubric_version="rubric-v1",
            prompt_version="prompt-contract-v1",
            arm=arm,
            model_id="offline-fixture-model",
            source_policy_id="fixture-primary-only-v1",
            max_critique_attempts=2 if arm is ExperimentArm.HIERARCHICAL_BOUNDED_CRITIQUE else 0,
        )

    def fixture(self, root: Path) -> tuple[Path, Path]:
        db = root / "gold.sqlite"
        create_gold_snapshot_schema(db)
        connection = sqlite3.connect(db)
        config = self.gold_config()
        connection.execute(
            "INSERT INTO snapshot_metadata VALUES (?, ?, ?, ?)",
            ("fixture-gold-v1", "2026-09-05T00:00:00Z", "gold", json.dumps(config.model_dump(mode="json"))),
        )
        connection.execute(
            "INSERT INTO source_records VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            ("fixture-source", "filing", "primary", "https://fixture.test/filing", "2026-09-05T00:00:00Z", "fixture.pdf", "fixture-hash", "fixture", "test", "valid", None),
        )
        connection.execute(
            "INSERT INTO evidence_snippets VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                "fixture-evidence",
                "fixture-source",
                "fixture.pdf",
                10,
                "Credit quality",
                "2024_Q1",
                "VCB",
                "NPL group 3-5 was 2.0 percent.",
                1.0,
                "text_layer",
                1,
            ),
        )
        connection.executemany(
            "INSERT INTO metric_observations VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            [
                ("obs-vcb", "VCB", "bank", "bank.npl_g35", 2.0, "%", "2024_Q1", "2024-03-31", "point_in_time", "fixture-source", "page:10", "valid", None),
                ("obs-acb", "ACB", "bank", "bank.npl_g35", 1.0, "%", "2024_Q1", "2024-03-31", "point_in_time", "fixture-source", "page:11", "valid", None),
            ],
        )
        connection.executemany(
            "INSERT INTO gold_labels VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            [
                ("label-vcb-a", "obs-vcb", "value_check", 2.0, None, "checker-a", "2026-09-05T00:00:00Z", "page:10", "matched"),
                ("label-vcb-b", "obs-vcb", "value_check", 2.0, None, "checker-b", "2026-09-05T00:00:00Z", "page:10", "matched"),
                ("label-acb-a", "obs-acb", "value_check", 1.0, None, "checker-a", "2026-09-05T00:00:00Z", "page:11", "matched"),
                ("label-acb-b", "obs-acb", "value_check", 1.0, None, "checker-b", "2026-09-05T00:00:00Z", "page:11", "matched"),
            ],
        )
        connection.commit()
        connection.close()

        questions = root / "questions.json"
        questions.write_text(
            json.dumps(
                {
                    "schema_version": 1,
                    "status": "test",
                    "question_set_id": "fixture-questions-v1",
                    "scope": {
                        "issuers": ["VCB", "ACB"],
                        "periods": ["2024_Q1"],
                        "core_metrics": ["bank.npl_g35"],
                        "conditional_metrics": ["bank.roa"],
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
        return db, questions

    def test_all_arms_emit_reproducible_offline_manifests_from_same_facts(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            db, questions = self.fixture(root)
            manifests = []
            results = []
            for arm in ExperimentArm:
                result = run_agent_arm(
                    db,
                    self.run_config(arm),
                    questions,
                    self.gold_config(),
                    "VCB",
                    "2024_Q1",
                    ("bank.npl_g35",),
                    FixtureAdapter(),
                    verification_requests=("fixture-check-1", "fixture-check-2"),
                )
                results.append(result)
                manifest = build_run_manifest(
                    result,
                    "q1",
                    ("bank.npl_g35",),
                    question_set_path=questions,
                )
                manifests.append(manifest)

            self.assertEqual([manifest.call_count for manifest in manifests], [1, 4, 6])
            self.assertEqual({manifest.environment for manifest in manifests}, {"offline_fixture"})
            self.assertTrue(all(not manifest.comparative_result for manifest in manifests))
            self.assertEqual({manifest.input_context_sha256 for manifest in manifests}, {manifests[0].input_context_sha256})
            self.assertEqual(set(manifests[0].input_observation_ids), {"obs-vcb", "obs-acb"})
            self.assertEqual(manifests[0].input_source_ids, ["fixture-source"])
            self.assertEqual(manifests[0].input_evidence_ids, ["fixture-evidence"])
            expected_hash = sha256(questions.read_bytes()).hexdigest()
            self.assertEqual(manifests[0].question_set_sha256, expected_hash)
            self.assertEqual(manifests[0].prompt_version, "prompt-contract-v1")
            self.assertEqual(manifests[0].schema_version, 2)
            self.assertEqual(
                manifests[0].calls[0].prompt_sha256,
                sha256(render_agent_prompt(results[0].calls[0]).encode("utf-8")).hexdigest(),
            )
            self.assertTrue(
                all(
                    call.prompt_sha256 is not None and len(call.prompt_sha256) == 64
                    for manifest in manifests
                    for call in manifest.calls
                )
            )
            self.assertTrue(all(len(manifest.calls) == manifest.call_count for manifest in manifests))
            self.assertTrue(all(len(manifest.payloads) == manifest.call_count for manifest in manifests))

    def test_manifest_writer_is_append_safe(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            db, questions = self.fixture(root)
            result = run_agent_arm(
                db,
                self.run_config(ExperimentArm.SINGLE_AGENT),
                questions,
                self.gold_config(),
                "VCB",
                "2024_Q1",
                ("bank.npl_g35",),
                FixtureAdapter(),
            )
            manifest = build_run_manifest(
                result,
                "q1",
                ("bank.npl_g35",),
                question_set_path=questions,
            )
            output = root / "run-manifest.json"
            write_run_manifest(manifest, output)
            self.assertTrue(output.exists())
            with self.assertRaises(FileExistsError):
                write_run_manifest(manifest, output)

    def test_manifest_preserves_multi_period_request_scope(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            _db, questions = self.fixture(root)
            periods = ("2024_Q1", "2024_Q2", "2024_Q3", "2024_Q4")
            request = AgentCallRequest(
                role="single_agent",
                ticker="VCB",
                period="2024_Q4",
                periods=periods,
                question_prompt="fixture trend",
                prompt_version="prompt-contract-v1",
                context={"period_order": list(periods), "periods": {}},
            )
            result = RuntimeRunResult(
                run_config=self.run_config(ExperimentArm.SINGLE_AGENT),
                payloads=(
                    AgentPayload(
                        agent_id="single_agent",
                        status=AgentStatus.SUCCESS,
                        ticker="VCB",
                        period="2024_Q4",
                    ),
                ),
                calls=(request,),
            )
            manifest = build_run_manifest(
                result,
                "q1",
                ("bank.npl_g35",),
                question_set_path=questions,
            )

        self.assertEqual(manifest.periods, list(periods))
        self.assertEqual(manifest.calls[0].periods, list(periods))

    def test_manifest_rejects_call_prompt_version_mismatch(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            db, questions = self.fixture(root)
            result = run_agent_arm(
                db,
                self.run_config(ExperimentArm.SINGLE_AGENT),
                questions,
                self.gold_config(),
                "VCB",
                "2024_Q1",
                ("bank.npl_g35",),
                FixtureAdapter(),
            )
            mismatched = replace(result.calls[0], prompt_version="prompt-contract-v2")
            result_with_mismatch = replace(result, calls=(mismatched,))

            with self.assertRaisesRegex(
                ValueError,
                "call prompt_version does not match run config",
            ):
                build_run_manifest(
                    result_with_mismatch,
                    "q1",
                    ("bank.npl_g35",),
                    question_set_path=questions,
                )

    def test_manifest_question_id_must_match_run_config(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            db, questions = self.fixture(root)
            result = run_agent_arm(
                db,
                self.run_config(ExperimentArm.SINGLE_AGENT),
                questions,
                self.gold_config(),
                "VCB",
                "2024_Q1",
                ("bank.npl_g35",),
                FixtureAdapter(),
            )

            with self.assertRaisesRegex(ValueError, "question_id does not match"):
                build_run_manifest(
                    result,
                    "q-other",
                    ("bank.npl_g35",),
                    question_set_path=questions,
                )

    def test_manifest_records_deterministic_anomaly_triggers(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            db, questions = self.fixture(root)
            result = run_agent_arm(
                db,
                self.run_config(ExperimentArm.HIERARCHICAL_BOUNDED_CRITIQUE),
                questions,
                self.gold_config(),
                "VCB",
                "2024_Q1",
                ("bank.roa",),
                FixtureAdapter(),
            )

            manifest = build_run_manifest(
                result,
                "q1",
                ("bank.roa",),
                question_set_path=questions,
            )

        self.assertEqual(
            [trigger["rule_id"] for trigger in manifest.anomaly_triggers],
            ["company_metric_missing", "sector_benchmark_missing"],
        )

    def test_manifest_records_provider_telemetry_without_inventing_offline_values(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            db, questions = self.fixture(root)
            result = run_agent_arm(
                db,
                self.run_config(ExperimentArm.SINGLE_AGENT),
                questions,
                self.gold_config(),
                "VCB",
                "2024_Q1",
                ("bank.npl_g35",),
                TelemetryAdapter(),
            )

            manifest = build_run_manifest(
                result,
                "q1",
                ("bank.npl_g35",),
                question_set_path=questions,
            )

        self.assertEqual(len(manifest.calls), 1)
        self.assertEqual(manifest.calls[0].telemetry_status, "provided")
        self.assertEqual(manifest.calls[0].latency_ms, 12.5)
        self.assertEqual(manifest.calls[0].input_tokens, 100)
        self.assertEqual(manifest.calls[0].output_tokens, 20)
        self.assertEqual(manifest.calls[0].cost_estimate, 0.003)


if __name__ == "__main__":
    unittest.main()
