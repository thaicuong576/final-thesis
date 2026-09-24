"""Integration tests for fail-closed, provider-backed POST /api/analyze."""

from __future__ import annotations

import sqlite3
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from fastapi.testclient import TestClient
from thesis_data.storage import create_gold_snapshot_schema

from thesis_api.main import create_app
from thesis_api.schemas import AnalysisResponse
from thesis_api.service import ProviderBinding, _load_provider as _load_provider_unwrapped
from thesis_api.settings import Settings


def _gold_fixture(path: Path, *, include_evidence: bool = True, source_tier: str = "primary") -> Path:
    create_gold_snapshot_schema(path)
    connection = sqlite3.connect(path)
    connection.execute(
        "INSERT INTO snapshot_metadata VALUES (?, ?, ?, ?)",
        ("gold-snapshot-api-fixture", "2026-09-24T00:00:00Z", "gold", "{}"),
    )
    sources = (
        ("source-roe", "filing", source_tier, "https://example.test/acb/report", "2026-09-24", "private/roe.pdf", "sha256-roe-real", "ACB", "fixture", "valid", None),
        ("source-npl", "filing", source_tier, "https://example.test/acb/report", "2026-09-24", "private/npl.pdf", "sha256-npl-real", "ACB", "fixture", "valid", None),
    )
    connection.executemany(
        "INSERT INTO source_records VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        sources,
    )
    connection.executemany(
        "INSERT INTO metric_observations VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (
            ("obs-roe", "ACB", "bank", "bank.roe", 17.25, "percent", "2024_Q4", "2024-12-31", "point_in_time", "source-roe", "page:42;row:ROE", "valid", None),
            ("obs-npl", "ACB", "bank", "bank.npl_g35", 1.03, "percent", "2024_Q4", "2024-12-31", "point_in_time", "source-npl", "page:61;row:NPL", "valid", None),
        ),
    )
    if include_evidence:
        connection.executemany(
            "INSERT INTO evidence_snippets VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                ("evidence-roe", "source-roe", "ACB annual report", 42, "ROE", "2024_Q4", "ACB", "Reported return on equity.", 1.0, "text_layer", 1),
                ("evidence-npl", "source-npl", "ACB annual report", 61, "NPL", "2024_Q4", "ACB", "Reported non-performing loan ratio.", 1.0, "text_layer", 1),
            ),
        )
    connection.commit()
    connection.close()
    return path


class _LocatorTestProvider:
    """Decorate a Gold provider with the observation-locator contract under test."""

    def __init__(self, provider, *, expose_locator: bool) -> None:
        self._provider = provider
        self._db_path = provider._db_path
        self._expose_locator = expose_locator

    def __getattr__(self, name):
        return getattr(self._provider, name)

    def _observation(self, observation):
        if observation is None:
            return None
        values = observation.model_dump()
        metadata = dict(values.get("metadata") or {})
        locator = getattr(observation, "source_locator", None) or metadata.get("source_locator")
        if self._expose_locator and not locator:
            locator = {
                "bank.roe": "page:42;row:ROE",
                "bank.npl_g35": "page:61;row:NPL",
            }.get(observation.metric_id)
        values.pop("source_locator", None)
        metadata.pop("source_locator", None)
        values["metadata"] = metadata
        if self._expose_locator:
            values["source_locator"] = locator
        return SimpleNamespace(**values)

    def get_metric(self, *args, **kwargs):
        return self._observation(self._provider.get_metric(*args, **kwargs))

    def resolve_observation(self, *args, **kwargs):
        return self._observation(self._provider.resolve_observation(*args, **kwargs))


def _fixture_provider_binding(path: Path, *, expose_locator: bool) -> ProviderBinding:
    binding = _load_provider_unwrapped(path)
    provider = _LocatorTestProvider(binding.provider, expose_locator=expose_locator)
    return ProviderBinding(provider, binding.dataset_ref, binding.catalog, binding.provider_name)


class ApiAnalyzeIntegrationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.db_path = _gold_fixture(Path(self.directory.name) / "accepted-gold.sqlite")
        self.settings = Settings(
            app_name="final-thesis-api-test",
            app_env="test",
            sqlite_db_path=str(self.db_path),
        )
        self.client = TestClient(create_app(self.settings))

    def test_company_claims_are_provider_backed_and_stage1_accepted_only(self) -> None:
        with patch(
            "thesis_api.service._load_provider",
            side_effect=lambda path: _fixture_provider_binding(path, expose_locator=True),
        ):
            response = self.client.post(
                "/api/analyze",
                json={
                    "query": "Phân tích ROE và NPL của ACB quý 4 năm 2024",
                    "target_ticker": "ACB",
                    "period": "2024_Q4",
                },
            )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        report = AnalysisResponse.model_validate(data)

        self.assertEqual(report.status, "partial")
        self.assertEqual(report.analysis_plan.required_capabilities, ["company"])
        self.assertEqual(report.analysis_plan.dataset_snapshot_id, "gold-snapshot-api-fixture")
        self.assertIsNone(report.macro_context)
        self.assertIsNone(report.sector_benchmark)
        self.assertIsNone(report.revision_summary)
        self.assertEqual(report.cross_level_critique, [])
        self.assertEqual({claim.stage1_status for claim in report.atomic_claims}, {"accepted"})
        self.assertTrue(all(claim.stage2_critique_status is None for claim in report.atomic_claims))
        self.assertTrue(all(claim.confidence is None for claim in report.atomic_claims))
        self.assertNotIn("confidence", data["atomic_claims"][0])
        self.assertNotIn("stage2_critique_status", data["atomic_claims"][0])
        self.assertTrue(any("numeric claims rely on each accepted metric observation's own source locator" in item for item in report.limitations))
        self.assertTrue(any("does not infer consolidated or parent-only scope" in item for item in report.limitations))
        self.assertEqual({claim.metric for claim in report.atomic_claims}, {"bank.roe", "bank.npl_g35"})
        self.assertEqual({item.value for item in report.evidence_trail}, {17.25, 1.03})
        self.assertEqual({item.table_locator for item in report.evidence_trail}, {"page:42;row:ROE", "page:61;row:NPL"})
        self.assertEqual({item.provenance_hash for item in report.evidence_trail}, {"sha256-roe-real", "sha256-npl-real"})

    def test_unsupported_entity_returns_no_numeric_claims(self) -> None:
        report = AnalysisResponse.model_validate(
            self.client.post(
                "/api/analyze",
                json={"query": "Analyze ROE of XYZ", "target_ticker": "XYZ", "period": "2024_Q4"},
            ).json()
        )
        self.assertEqual(report.status, "error")
        self.assertEqual(report.atomic_claims, [])
        self.assertEqual(report.evidence_trail, [])
        self.assertIn("unsupported_entity", report.limitations[0])

    def test_unsupported_year_metric_and_capability_requests_fail_closed(self) -> None:
        requests = (
            {"query": "ROE of ACB in 2024", "target_ticker": "ACB", "period": "2024"},
            {"query": "CIR of ACB in 2024 Q4", "target_ticker": "ACB", "period": "2024_Q4"},
            {"query": "Compare ROE of ACB and TCB in 2024 Q4", "target_ticker": "ACB", "period": "2024_Q4"},
            {"query": "SBV policy rate effect on ACB in 2024 Q4", "target_ticker": "ACB", "period": "2024_Q4"},
        )
        for payload in requests:
            with self.subTest(payload=payload):
                report = AnalysisResponse.model_validate(self.client.post("/api/analyze", json=payload).json())
                self.assertEqual(report.status, "error")
                self.assertEqual(report.atomic_claims, [])
                self.assertEqual(report.evidence_trail, [])

    def test_full_metric_names_are_resolved_without_falling_back_to_all_metrics(self) -> None:
        with patch(
            "thesis_api.service._load_provider",
            side_effect=lambda path: _fixture_provider_binding(path, expose_locator=True),
        ):
            report = AnalysisResponse.model_validate(
                self.client.post(
                    "/api/analyze",
                    json={
                        "query": "What is the return on equity for ACB in 2024 Q4?",
                        "target_ticker": "ACB",
                        "period": "2024_Q4",
                    },
                ).json()
            )
        self.assertEqual(report.status, "partial")
        self.assertEqual({claim.metric for claim in report.atomic_claims}, {"bank.roe"})

        unsupported = AnalysisResponse.model_validate(
            self.client.post(
                "/api/analyze",
                json={
                    "query": "What is the loan loss reserve coverage for ACB in 2024 Q4?",
                    "target_ticker": "ACB",
                    "period": "2024_Q4",
                },
            ).json()
        )
        self.assertEqual(unsupported.status, "error")
        self.assertEqual(unsupported.atomic_claims, [])
        self.assertIn("unsupported_metric", unsupported.limitations[0])

    def test_missing_evidence_blocks_numeric_claims(self) -> None:
        db_path = _gold_fixture(Path(self.directory.name) / "no-evidence.sqlite", include_evidence=False)
        client = TestClient(create_app(Settings(app_env="test", sqlite_db_path=str(db_path))))
        with patch(
            "thesis_api.service._load_provider",
            side_effect=lambda path: _fixture_provider_binding(path, expose_locator=True),
        ):
            report = AnalysisResponse.model_validate(
                client.post(
                    "/api/analyze",
                    json={"query": "ROE of ACB in 2024 Q4", "target_ticker": "ACB", "period": "2024_Q4"},
                ).json()
            )
            capabilities = client.get("/api/capabilities").json()
            ready = client.get("/api/ready")
        self.assertEqual(report.status, "error")
        self.assertEqual(report.atomic_claims, [])
        self.assertIn("evidence_unavailable", report.limitations[0])
        self.assertFalse(capabilities["analysis_available"])
        self.assertEqual(ready.status_code, 503)

    def test_capabilities_and_readiness_reflect_snapshot_catalog(self) -> None:
        with patch(
            "thesis_api.service._load_provider",
            side_effect=lambda path: _fixture_provider_binding(path, expose_locator=True),
        ):
            capabilities_response = self.client.get("/api/capabilities")
            ready_response = self.client.get("/api/ready")
        self.assertEqual(capabilities_response.status_code, 200)
        capabilities = capabilities_response.json()
        self.assertTrue(capabilities["analysis_available"])
        self.assertEqual(capabilities["implemented_capabilities"], ["company"])
        self.assertEqual(capabilities["snapshotId"], "gold-snapshot-api-fixture")
        self.assertEqual(capabilities["database_status"], "connected")
        self.assertIn("get_evidence", capabilities["supported_operations"])
        self.assertEqual([item["ticker"] for item in capabilities["entities"]], ["ACB"])
        self.assertEqual([item["id"] for item in capabilities["periods"]], ["2024_Q4"])
        self.assertEqual({item["id"] for item in capabilities["metrics"]}, {"bank.roe", "bank.npl_g35"})
        self.assertTrue(all("sector" not in item["label"].casefold() for item in capabilities["peerUniverses"]))
        self.assertTrue(all(item["executable"] is False for item in capabilities["peerUniverses"]))
        self.assertEqual(ready_response.json()["status"], "ready")

    def test_missing_metric_locator_fails_closed_even_when_source_snippets_exist(self) -> None:
        with patch(
            "thesis_api.service._load_provider",
            side_effect=lambda path: _fixture_provider_binding(path, expose_locator=False),
        ):
            response = self.client.post(
                "/api/analyze",
                json={"query": "ROE of ACB in 2024 Q4", "target_ticker": "ACB", "period": "2024_Q4"},
            )
            capabilities = self.client.get("/api/capabilities").json()
            ready = self.client.get("/api/ready")
        report = AnalysisResponse.model_validate(response.json())
        self.assertEqual(report.status, "error")
        self.assertEqual(report.atomic_claims, [])
        self.assertIn("observation_locator_missing", report.limitations[0])
        self.assertFalse(capabilities["analysis_available"])
        self.assertEqual(ready.status_code, 503)

    def test_missing_database_is_not_created_or_reported_ready(self) -> None:
        missing = Path(self.directory.name) / "does-not-exist.sqlite"
        client = TestClient(create_app(Settings(app_env="test", sqlite_db_path=str(missing))))
        result = client.post(
            "/api/analyze",
            json={"query": "ROE of ACB in 2024 Q4", "target_ticker": "ACB", "period": "2024_Q4"},
        )
        self.assertEqual(result.json()["status"], "error")
        self.assertFalse(missing.exists())
        self.assertEqual(client.get("/api/capabilities").json()["analysis_available"], False)
        self.assertEqual(client.get("/api/ready").status_code, 503)


if __name__ == "__main__":
    unittest.main()
