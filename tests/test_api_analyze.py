"""Integration tests for fail-closed, provider-backed POST /api/analyze."""

from __future__ import annotations

import sqlite3
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from fastapi.testclient import TestClient
from thesis_data.dataset_contract import (
    AnalyticalLevel,
    CanonicalObservation,
    DatasetCapabilityCatalog,
    DatasetEntity,
    DatasetEntityType,
    DatasetEvidence,
    DatasetMetric,
    DatasetPeriod,
    DatasetRef,
    DatasetSource,
    SupportedOperation,
)
from thesis_data.schema import QualityStatus, SourceTier
from thesis_data.storage import create_gold_snapshot_schema

from thesis_api.main import create_app
from thesis_api.schemas import AnalysisRequest, AnalysisResponse
from thesis_api.service import (
    AnalysisBlocked,
    AnalysisEngine,
    ProviderBinding,
    _capabilities_payload,
    _load_provider as _load_provider_unwrapped,
    _requested_metrics,
    _stage1_claim,
)
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
        ("source-input", "filing", source_tier, "https://example.test/acb/report", "2026-09-24", "private/input.pdf", "sha256-input-real", "ACB", "fixture", "valid", None),
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
            ("obs-input-npl-balance", "ACB", "bank", "bank.input.npl_g35_balance", 123.0, "billion_vnd", "2024_Q4", "2024-12-31", "point_in_time", "source-input", "page:62;row:NPL balance", "valid", None),
        ),
    )
    if include_evidence:
        connection.executemany(
            "INSERT INTO evidence_snippets VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                ("evidence-roe", "source-roe", "ACB annual report", 42, "ROE", "2024_Q4", "ACB", "Reported return on equity.", 1.0, "text_layer", 1),
                ("evidence-npl", "source-npl", "ACB annual report", 61, "NPL", "2024_Q4", "ACB", "Reported non-performing loan ratio.", 1.0, "text_layer", 1),
                ("evidence-input", "source-input", "ACB annual report", 62, "NPL balance", "2024_Q4", "ACB", "Reported non-performing loan balance.", 1.0, "text_layer", 1),
            ),
        )
    connection.commit()
    connection.close()
    return path


def _gold_fanout_fixture(path: Path) -> Path:
    """Gold snippets share a source/period scope but carry no metric mapping."""

    create_gold_snapshot_schema(path)
    connection = sqlite3.connect(path)
    connection.execute(
        "INSERT INTO snapshot_metadata VALUES (?, ?, ?, ?)",
        ("gold-snapshot-api-fanout", "2026-09-24T00:00:00Z", "gold", "{}"),
    )
    connection.execute(
        "INSERT INTO source_records VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        ("source-acb-annual", "filing", "primary", "https://example.test/acb/report", "2026-09-24", "private/acb.pdf", "sha256-acb-annual", "ACB", "fixture", "valid", None),
    )
    connection.executemany(
        "INSERT INTO metric_observations VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (
            ("obs-roa", "ACB", "bank", "bank.roa", 1.2, "percent", "2024_Q4", "2024-12-31", "point_in_time", "source-acb-annual", "page:41;row:ROA", "valid", None),
            ("obs-roe", "ACB", "bank", "bank.roe", 17.25, "percent", "2024_Q4", "2024-12-31", "point_in_time", "source-acb-annual", "page:42;row:ROE", "valid", None),
            ("obs-npl", "ACB", "bank", "bank.npl_g35", 1.03, "percent", "2024_Q4", "2024-12-31", "point_in_time", "source-acb-annual", "page:61;row:NPL", "valid", None),
            ("obs-llr", "ACB", "bank", "bank.llr", 148.0, "percent", "2024_Q4", "2024-12-31", "point_in_time", "source-acb-annual", "page:62;row:LLR", "valid", None),
        ),
    )
    connection.executemany(
        "INSERT INTO evidence_snippets VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (
            ("evidence-roa", "source-acb-annual", "ACB annual report", 41, "ROA", "2024_Q4", "ACB", "Reported return on assets.", 1.0, "text_layer", 1),
            ("evidence-roe", "source-acb-annual", "ACB annual report", 42, "ROE", "2024_Q4", "ACB", "Reported return on equity.", 1.0, "text_layer", 1),
            ("evidence-npl", "source-acb-annual", "ACB annual report", 61, "NPL", "2024_Q4", "ACB", "Reported non-performing loan ratio.", 1.0, "text_layer", 1),
            ("evidence-llr", "source-acb-annual", "ACB annual report", 62, "LLR", "2024_Q4", "ACB", "Reported loan loss reserve coverage.", 1.0, "text_layer", 1),
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
                "bank.input.npl_g35_balance": "page:62;row:NPL balance",
                "bank.roa": "page:41;row:ROA",
                "bank.llr": "page:62;row:LLR",
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
        self.assertTrue(all(claim.evidence_refs == [] for claim in report.atomic_claims))
        self.assertTrue(all(claim.stage2_critique_status is None for claim in report.atomic_claims))
        self.assertTrue(all(claim.confidence is None for claim in report.atomic_claims))
        self.assertNotIn("confidence", data["atomic_claims"][0])
        self.assertNotIn("stage2_critique_status", data["atomic_claims"][0])
        self.assertTrue(any("primary source locator and source hash" in item for item in report.limitations))
        self.assertTrue(any("does not infer consolidated or parent-only scope" in item for item in report.limitations))
        self.assertEqual({claim.metric for claim in report.atomic_claims}, {"bank.roe", "bank.npl_g35"})
        self.assertEqual(
            {claim.metric: claim.observation_id for claim in report.atomic_claims},
            {"bank.roe": "obs-roe", "bank.npl_g35": "obs-npl"},
        )
        self.assertTrue(all(claim.input_observation_ids == [] for claim in report.atomic_claims))
        self.assertTrue(all(claim.formula_version is None for claim in report.atomic_claims))
        self.assertEqual({item.value for item in report.evidence_trail}, {17.25, 1.03})
        self.assertTrue(all(item.evidence_id is None for item in report.evidence_trail))
        self.assertEqual({item.table_locator for item in report.evidence_trail}, {"page:42;row:ROE", "page:61;row:NPL"})
        self.assertEqual({item.provenance_hash for item in report.evidence_trail}, {"sha256-roe-real", "sha256-npl-real"})
        claims_by_id = {claim.claim_id: claim for claim in report.atomic_claims}
        self.assertTrue(all(item.claim_id in claims_by_id for item in report.evidence_trail))
        self.assertTrue(
            all(
                item.observation_id == claims_by_id[item.claim_id].observation_id
                for item in report.evidence_trail
            )
        )
        self.assertEqual({item.source_id for item in report.evidence_trail}, {"source-roe", "source-npl"})
        self.assertTrue(all(item.source_url == "https://example.test/acb/report" for item in report.evidence_trail))

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

    def test_missing_document_evidence_uses_accepted_observation_locator(self) -> None:
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
        self.assertEqual(report.status, "partial")
        self.assertEqual(len(report.atomic_claims), 1)
        self.assertEqual(report.atomic_claims[0].evidence_refs, [])
        self.assertEqual(len(report.evidence_trail), 1)
        self.assertIsNone(report.evidence_trail[0].evidence_id)
        self.assertEqual(report.evidence_trail[0].table_locator, "page:42;row:ROE")
        self.assertTrue(any("primary source locator and source hash" in item for item in report.limitations))
        self.assertTrue(capabilities["analysis_available"])
        self.assertEqual(ready.status_code, 200)

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

    def test_exact_metric_selection_keeps_lineage_inputs_non_runnable(self) -> None:
        binding = _fixture_provider_binding(self.db_path, expose_locator=True)
        selected = _requested_metrics(
            AnalysisRequest(
                query="Analyze bank.npl_g35 for ACB in 2024 Q4",
                target_ticker="ACB",
                period="2024_Q4",
            ),
            binding.catalog,
        )
        self.assertEqual(selected, ("bank.npl_g35",))

        with self.assertRaises(AnalysisBlocked) as blocked:
            _requested_metrics(
                AnalysisRequest(
                    query="Analyze bank.input.npl_g35_balance for ACB in 2024 Q4",
                    target_ticker="ACB",
                    period="2024_Q4",
                ),
                binding.catalog,
            )
        self.assertEqual(blocked.exception.code, "lineage_only_metric")
        capability_metric_ids = {item["id"] for item in _capabilities_payload(binding)["metrics"]}
        self.assertNotIn("bank.input.npl_g35_balance", capability_metric_ids)

    def test_direct_claim_omits_same_source_metric_snippet_without_reviewed_link(self) -> None:
        binding = _fixture_provider_binding(self.db_path, expose_locator=True)
        unrelated = DatasetEvidence(
            evidence_id="same-source-metric-scope-unlinked",
            source_ref="source-roe",
            entity_id="ACB",
            period_id="2024_Q4",
            metric_id="bank.roe",
            locator="page:42;row:neighboring-note",
            quote="A same-source snippet with no reviewed observation link.",
        )
        claim_only_link = SimpleNamespace(
            evidence_id="claim-only-link-is-insufficient",
            source_ref="source-roe",
            entity_id="ACB",
            period_id="2024_Q4",
            metric_id="bank.roe",
            claim_id="claim-obs-roe",
            locator="page:42;row:ROE",
            quote="A claim identifier without an observation join.",
        )
        explicitly_linked = SimpleNamespace(
            evidence_id="reviewed-observation-link",
            source_ref="source-roe",
            entity_id="ACB",
            period_id="2024_Q4",
            metric_id="bank.roe",
            observation_id="obs-roe",
            locator="page:42;row:ROE",
            quote="Provider-declared reviewed link to the exact observation.",
        )

        class Provider:
            def __getattr__(self, name):
                return getattr(binding.provider, name)

            def get_evidence(self, *_args, **_kwargs):
                return unrelated, claim_only_link, explicitly_linked

        claim, observation, _, _, evidence = _stage1_claim(
            provider=Provider(),
            dataset_ref=binding.dataset_ref,
            ticker="ACB",
            period="2024_Q4",
            metric_id="bank.roe",
            display_name="ROE",
        )

        self.assertEqual(observation.observation_id, "obs-roe")
        self.assertEqual(claim.source_refs, ("source-roe",))
        self.assertEqual([item.evidence_id for item in evidence], ["reviewed-observation-link"])
        self.assertEqual(claim.evidence_refs, ("reviewed-observation-link",))
        self.assertEqual(claim.support, "evidence_backed")

    def test_acb_generic_gold_snippets_are_not_fanned_out_across_metrics(self) -> None:
        db_path = _gold_fanout_fixture(Path(self.directory.name) / "gold-fanout.sqlite")
        client = TestClient(create_app(Settings(app_env="test", sqlite_db_path=str(db_path))))
        with patch(
            "thesis_api.service._load_provider",
            side_effect=lambda path: _fixture_provider_binding(path, expose_locator=True),
        ):
            report = AnalysisResponse.model_validate(
                client.post(
                    "/api/analyze",
                    json={
                        "query": "Analyze ROA, ROE, NPL, and loan loss reserve coverage for ACB in 2024 Q4",
                        "target_ticker": "ACB",
                        "period": "2024_Q4",
                    },
                ).json()
            )
        self.assertEqual(report.status, "partial")
        self.assertEqual(
            {claim.metric for claim in report.atomic_claims},
            {"bank.roa", "bank.roe", "bank.npl_g35", "bank.llr"},
        )
        self.assertTrue(all(claim.evidence_refs == [] for claim in report.atomic_claims))
        self.assertEqual(len(report.evidence_trail), 4)
        self.assertTrue(all(item.evidence_id is None for item in report.evidence_trail))
        claims_by_id = {claim.claim_id: claim for claim in report.atomic_claims}
        self.assertEqual(len(claims_by_id), 4)
        self.assertTrue(all(item.claim_id in claims_by_id for item in report.evidence_trail))
        self.assertTrue(
            all(
                item.observation_id == claims_by_id[item.claim_id].observation_id
                for item in report.evidence_trail
            )
        )
        self.assertEqual(
            {item.table_locator for item in report.evidence_trail},
            {
                "page:41;row:ROA",
                "page:42;row:ROE",
                "page:61;row:NPL",
                "page:62;row:LLR",
            },
        )
        self.assertEqual({item.provenance_hash for item in report.evidence_trail}, {"sha256-acb-annual"})

    def test_derived_claim_resolves_primary_input_lineage_without_direct_source_ref(self) -> None:
        dataset_ref = DatasetRef(dataset_id="fixture", dataset_snapshot_id="snapshot-1")
        input_observations = {
            "input-npl": CanonicalObservation(
                observation_id="input-npl",
                dataset_id=dataset_ref.dataset_id,
                dataset_snapshot_id=dataset_ref.dataset_snapshot_id,
                entity_id="CTG",
                period_id="2024_Q4",
                metric_id="bank.input.npl_g35_balance",
                value=120.0,
                unit="billion_vnd",
                source_ref="source-npl",
                validation_status=QualityStatus.VALID,
                metadata={"source_locator": "page:57;row:bad-debts"},
            ),
            "input-loans": CanonicalObservation(
                observation_id="input-loans",
                dataset_id=dataset_ref.dataset_id,
                dataset_snapshot_id=dataset_ref.dataset_snapshot_id,
                entity_id="CTG",
                period_id="2024_Q4",
                metric_id="bank.input.total_loans",
                value=10000.0,
                unit="billion_vnd",
                source_ref="source-loans",
                validation_status=QualityStatus.VALID,
                metadata={"source_locator": "page:54;row:loans"},
            ),
        }
        derived = CanonicalObservation(
            observation_id="derived-npl",
            dataset_id=dataset_ref.dataset_id,
            dataset_snapshot_id=dataset_ref.dataset_snapshot_id,
            entity_id="CTG",
            period_id="2024_Q4",
            metric_id="bank.npl_g35",
            value=1.2,
            unit="percent",
            source_ref=None,
            validation_status=QualityStatus.VALID,
            derivation_method="npl_g35_ratio_v1",
            input_observation_ids=("input-npl", "input-loans"),
        )
        sources = {
            ref: DatasetSource(
                source_ref=ref,
                source_type="filing",
                source_tier=SourceTier.PRIMARY,
                source_url=f"https://example.test/ctg/{ref}.pdf",
                publisher="CTG",
                retrieved_at="2026-09-24T00:00:00Z",
                content_hash=f"sha256-{ref}",
                validation_status=QualityStatus.VALID,
            )
            for ref in ("source-npl", "source-loans")
        }
        generic_evidence = DatasetEvidence(
            evidence_id="gold-source-period-snippet",
            source_ref="source-npl",
            entity_id="CTG",
            period_id="2024_Q4",
            metric_id="bank.npl_g35",
            locator="page:57;row:unrelated-note",
            quote="Same-source metric-scope snippet without a reviewed observation link.",
        )

        class Provider:
            def get_metric(self, *_args, **_kwargs):
                return derived

            def resolve_observation(self, _dataset_ref, observation_id):
                if observation_id == derived.observation_id:
                    return derived
                return input_observations.get(observation_id)

            def get_source(self, _dataset_ref, source_ref):
                return sources.get(source_ref)

            def get_evidence(self, *_args, **_kwargs):
                return (generic_evidence,)

            def resolve_evidence(self, *_args, **_kwargs):
                return None

        claim, observation, primary_observations, claim_sources, evidence = _stage1_claim(
            provider=Provider(),
            dataset_ref=dataset_ref,
            ticker="CTG",
            period="2024_Q4",
            metric_id="bank.npl_g35",
            display_name="NPL",
        )
        self.assertEqual(observation.observation_id, "derived-npl")
        self.assertIsNone(observation.source_ref)
        self.assertEqual(observation.input_observation_ids, ("input-npl", "input-loans"))
        self.assertEqual(claim.assertions[0].formula_version, "npl_g35_ratio_v1")
        self.assertEqual(claim.assertions[0].data_refs[0].ref_id, "derived-npl")
        self.assertEqual(claim.assertions[0].data_refs[0].ref_type, "derived_metric")
        self.assertEqual(claim.source_refs, ("source-npl", "source-loans"))
        self.assertEqual({item.observation_id for item in primary_observations}, {"input-npl", "input-loans"})
        self.assertEqual(
            {
                item.observation_id: item.metadata["source_locator"]
                for item in primary_observations
            },
            {
                "input-npl": "page:57;row:bad-debts",
                "input-loans": "page:54;row:loans",
            },
        )
        self.assertEqual({item.source_ref for item in claim_sources}, {"source-npl", "source-loans"})
        self.assertEqual({item.content_hash for item in claim_sources}, {"sha256-source-npl", "sha256-source-loans"})
        self.assertEqual(evidence, ())
        self.assertEqual(claim.evidence_refs, ())
        self.assertEqual(claim.support, "source_locator_only")

        same_metric_unlinked_evidence = DatasetEvidence(
            evidence_id="same-source-metric-scope-unlinked",
            source_ref="source-npl",
            entity_id="CTG",
            period_id="2024_Q4",
            metric_id="bank.npl_g35",
            locator="page:57;row:unrelated-note",
            quote="A same-source snippet without a reviewed observation link.",
        )

        class SameScopeProvider(Provider):
            def get_evidence(self, *_args, **_kwargs):
                return generic_evidence, same_metric_unlinked_evidence

            def resolve_evidence(self, _dataset_ref, evidence_id):
                return (
                    same_metric_unlinked_evidence
                    if evidence_id == same_metric_unlinked_evidence.evidence_id
                    else None
                )

        catalog = DatasetCapabilityCatalog(
            dataset_ref=dataset_ref,
            entities=(
                DatasetEntity(
                    entity_id="CTG",
                    entity_type=DatasetEntityType.COMPANY,
                    display_name="CTG",
                ),
            ),
            periods=(DatasetPeriod(period_id="2024_Q4", label="2024 Q4"),),
            metrics=(
                DatasetMetric(
                    metric_id="bank.npl_g35",
                    display_name="NPL",
                    analytical_level=AnalyticalLevel.COMPANY,
                    default_unit="percent",
                ),
            ),
            source_refs=("source-npl", "source-loans"),
            supported_operations=(
                SupportedOperation.GET_METRIC,
                SupportedOperation.RESOLVE_OBSERVATION,
                SupportedOperation.GET_SOURCE,
                SupportedOperation.GET_EVIDENCE,
            ),
        )
        with patch(
            "thesis_api.service._load_provider",
            return_value=ProviderBinding(SameScopeProvider(), dataset_ref, catalog, "fixture"),
        ):
            report = AnalysisEngine(self.db_path)._analyze(
                AnalysisRequest(
                    query="Analyze NPL of CTG in 2024 Q4",
                    target_ticker="CTG",
                    period="2024_Q4",
                )
            )
        self.assertEqual(report.status, "partial")
        output_claim = report.atomic_claims[0]
        self.assertEqual(output_claim.observation_id, "derived-npl")
        self.assertEqual(output_claim.input_observation_ids, ["input-npl", "input-loans"])
        self.assertEqual(output_claim.formula_version, "npl_g35_ratio_v1")
        self.assertEqual(output_claim.evidence_refs, [])
        self.assertTrue(
            all(item.claim_id == output_claim.claim_id for item in report.evidence_trail)
        )
        input_trails = {
            item.observation_id: item
            for item in report.evidence_trail
            if item.evidence_id is None
        }
        self.assertEqual(set(input_trails), {"input-npl", "input-loans"})
        self.assertEqual(input_trails["input-npl"].source_id, "source-npl")
        self.assertEqual(input_trails["input-npl"].source_url, sources["source-npl"].source_url)
        self.assertEqual(input_trails["input-npl"].table_locator, "page:57;row:bad-debts")
        self.assertEqual(input_trails["input-npl"].provenance_hash, "sha256-source-npl")
        self.assertEqual(input_trails["input-loans"].source_id, "source-loans")
        self.assertEqual(input_trails["input-loans"].table_locator, "page:54;row:loans")
        self.assertEqual(input_trails["input-loans"].provenance_hash, "sha256-source-loans")
        self.assertTrue(all(item.evidence_id is None for item in report.evidence_trail))

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
