"""Create and run the deterministic offline experiment fixture.

The fixture exercises the real query boundary, guarded arm dispatcher, and run
manifest writer without a provider, network access, or thesis data. Every
manifest is explicitly non-comparative and is intended only to validate the
experiment plumbing before a promoted gold snapshot is available.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import json
from pathlib import Path
import sqlite3
from typing import Any

from .agent_runtime import AgentCallRequest, AgentCallTelemetry
from .baseline_batch_runner import execute_baseline_plan
from .baseline_plan import build_baseline_plan
from .provider_adapter import ProviderResponse, ProviderTransport, StructuredProviderAdapter
from .provider_config import ProviderExecutionConfig
from .question_set import load_question_set
from .run_manifest import ExperimentRunManifest
from .schema import AgentPayload, AgentStatus, GoldConfig
from .storage import create_gold_snapshot_schema


FIXTURE_SNAPSHOT_ID = "offline-fixture-gold-v1"
FIXTURE_QUESTION_SET_ID = "offline-fixture-questions-v1"
FIXTURE_QUESTION_ID = "q1"
FIXTURE_RUBRIC_VERSION = "offline-fixture-rubric-v1"
FIXTURE_PROMPT_VERSION = "offline-fixture-prompt-v1"
FIXTURE_MODEL_ID = "offline-fixture-model"
FIXTURE_SOURCE_POLICY_ID = "offline-fixture-primary-only-v1"
FIXTURE_METRIC_IDS = ("bank.npl_g35",)
FIXTURE_RECORDED_AT = datetime(2026, 9, 5, tzinfo=timezone.utc)


def fixture_gold_config() -> GoldConfig:
    """Return the fixed scope used by the offline fixture."""
    return GoldConfig(
        tickers=("VCB", "ACB"),
        periods=("2024_Q1",),
        required_metrics=FIXTURE_METRIC_IDS,
        min_manual_labels=4,
        min_metric_coverage=1.0,
    )


class OfflineFixtureTransport:
    """Return deterministic provider-shaped responses without external calls."""

    def complete(
        self,
        request: AgentCallRequest,
        rendered_prompt: str,
        config: ProviderExecutionConfig,
    ) -> ProviderResponse:
        # ``StructuredProviderAdapter`` owns prompt rendering and response
        # validation. The fixture transport only supplies a deterministic
        # provider-shaped payload and explicit unavailable telemetry.
        del rendered_prompt, config
        return ProviderResponse(
            payload=AgentPayload(
                agent_id=request.role,
                status=AgentStatus.SUCCESS,
                ticker=request.ticker,
                period=request.period,
                findings=["offline_fixture_payload"],
            ),
            telemetry=AgentCallTelemetry(),
        )


def offline_fixture_provider_config() -> ProviderExecutionConfig:
    """Return the secret-free config used by the local fixture transport."""
    return ProviderExecutionConfig(
        adapter_id="offline-fixture-structured-v1",
        provider_id="offline-fixture",
        model_id=FIXTURE_MODEL_ID,
        source_policy_id=FIXTURE_SOURCE_POLICY_ID,
        environment="offline_fixture",
        network_access="disabled",
        telemetry_required=True,
    )


class OfflineFixtureAdapter(StructuredProviderAdapter):
    """Adapt the deterministic fixture transport through the real boundary."""

    def __init__(self) -> None:
        super().__init__(OfflineFixtureTransport(), offline_fixture_provider_config())


@dataclass(frozen=True)
class OfflineFixtureRun:
    output_dir: Path
    manifests: tuple[ExperimentRunManifest, ...]

    def summary(self) -> dict[str, Any]:
        return {
            "environment": "offline_fixture",
            "snapshot_id": FIXTURE_SNAPSHOT_ID,
            "question_id": FIXTURE_QUESTION_ID,
            "arms": [manifest.arm for manifest in self.manifests],
            "call_counts": [manifest.call_count for manifest in self.manifests],
            "all_noncomparative": all(
                not manifest.comparative_result for manifest in self.manifests
            ),
            "output_dir": str(self.output_dir),
        }


def _write_fixture_database(path: Path, config: GoldConfig) -> None:
    if path.exists():
        raise FileExistsError(f"refusing to overwrite fixture database: {path}")
    create_gold_snapshot_schema(path)
    connection = sqlite3.connect(path)
    try:
        connection.execute(
            "INSERT INTO snapshot_metadata VALUES (?, ?, ?, ?)",
            (
                FIXTURE_SNAPSHOT_ID,
                FIXTURE_RECORDED_AT.isoformat().replace("+00:00", "Z"),
                "gold",
                json.dumps(config.model_dump(mode="json"), sort_keys=True),
            ),
        )
        connection.execute(
            "INSERT INTO source_records VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                "offline-fixture-source",
                "filing",
                "primary",
                "https://offline-fixture.test/filing",
                FIXTURE_RECORDED_AT.isoformat().replace("+00:00", "Z"),
                "fixture.pdf",
                "offline-fixture-hash",
                "offline-fixture",
                "test-only",
                "valid",
                None,
            ),
        )
        connection.execute(
            "INSERT INTO evidence_snippets VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                "offline-fixture-evidence",
                "offline-fixture-source",
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
                (
                    "offline-obs-vcb",
                    "VCB",
                    "bank",
                    "bank.npl_g35",
                    2.0,
                    "%",
                    "2024_Q1",
                    "2024-03-31",
                    "point_in_time",
                    "offline-fixture-source",
                    "page:10",
                    "valid",
                    None,
                ),
                (
                    "offline-obs-acb",
                    "ACB",
                    "bank",
                    "bank.npl_g35",
                    1.0,
                    "%",
                    "2024_Q1",
                    "2024-03-31",
                    "point_in_time",
                    "offline-fixture-source",
                    "page:11",
                    "valid",
                    None,
                ),
            ],
        )
        connection.executemany(
            "INSERT INTO gold_labels VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            [
                (
                    "offline-label-vcb-a",
                    "offline-obs-vcb",
                    "value_check",
                    2.0,
                    None,
                    "checker-a",
                    "2026-09-05T00:00:00Z",
                    "page:10",
                    "offline fixture",
                ),
                (
                    "offline-label-vcb-b",
                    "offline-obs-vcb",
                    "value_check",
                    2.0,
                    None,
                    "checker-b",
                    "2026-09-05T00:00:00Z",
                    "page:10",
                    "offline fixture",
                ),
                (
                    "offline-label-acb-a",
                    "offline-obs-acb",
                    "value_check",
                    1.0,
                    None,
                    "checker-a",
                    "2026-09-05T00:00:00Z",
                    "page:11",
                    "offline fixture",
                ),
                (
                    "offline-label-acb-b",
                    "offline-obs-acb",
                    "value_check",
                    1.0,
                    None,
                    "checker-b",
                    "2026-09-05T00:00:00Z",
                    "page:11",
                    "offline fixture",
                ),
            ],
        )
        connection.commit()
    finally:
        connection.close()


def _write_question_set(path: Path) -> None:
    if path.exists():
        raise FileExistsError(f"refusing to overwrite question set: {path}")
    path.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "status": "offline_fixture",
                "question_set_id": FIXTURE_QUESTION_SET_ID,
                "scope": {
                    "issuers": ["VCB", "ACB"],
                    "periods": ["2024_Q1"],
                    "core_metrics": list(FIXTURE_METRIC_IDS),
                },
                "questions": [{
                    "id": FIXTURE_QUESTION_ID,
                    "issuer": "VCB",
                    "type": "company_snapshot",
                    "period": "2024_Q1",
                    "prompt": "offline fixture",
                }],
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )


def _write_baseline_plan(path: Path, question_set_path: Path) -> None:
    if path.exists():
        raise FileExistsError(f"refusing to overwrite baseline plan: {path}")
    plan = build_baseline_plan(
        load_question_set(question_set_path),
        question_set_path,
        FIXTURE_SNAPSHOT_ID,
    )
    path.write_text(
        json.dumps(plan.model_dump(mode="json"), ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def run_offline_fixture(output_dir: Path) -> OfflineFixtureRun:
    """Write a fresh fixture and execute its three-arm plan offline.

    The manifests are intentionally written below ``manifests/`` so the
    fixture database, question set, and immutable plan can remain alongside
    them without violating the batch runner's empty-output-directory guard.
    """
    output_dir = output_dir.resolve()
    if output_dir.exists():
        if not output_dir.is_dir():
            raise FileExistsError(f"offline fixture output is not a directory: {output_dir}")
        if any(output_dir.iterdir()):
            raise FileExistsError(
                f"refusing to write into non-empty offline fixture output: {output_dir}"
            )
    else:
        output_dir.mkdir(parents=True)

    fixture_db = output_dir / "fixture.sqlite"
    question_set = output_dir / "question-set.json"
    plan_path = output_dir / "plan.json"
    manifest_dir = output_dir / "manifests"
    config = fixture_gold_config()
    _write_fixture_database(fixture_db, config)
    _write_question_set(question_set)
    _write_baseline_plan(plan_path, question_set)

    batch_result = execute_baseline_plan(
        fixture_db,
        plan_path,
        question_set,
        config,
        OfflineFixtureAdapter(),
        manifest_dir,
        run_id_prefix="offline",
        rubric_version=FIXTURE_RUBRIC_VERSION,
        prompt_version=FIXTURE_PROMPT_VERSION,
        model_id=FIXTURE_MODEL_ID,
        source_policy_id=FIXTURE_SOURCE_POLICY_ID,
        max_critique_attempts=2,
        environment="offline_fixture",
        provider_config=offline_fixture_provider_config(),
        comparative_result=False,
        verification_requests=("offline-fixture-check-1", "offline-fixture-check-2"),
        recorded_at_utc=FIXTURE_RECORDED_AT,
    )

    return OfflineFixtureRun(output_dir=output_dir, manifests=batch_result.manifests)
