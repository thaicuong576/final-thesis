import unittest
from pathlib import Path
from unittest.mock import patch
from fastapi.testclient import TestClient

from thesis_api.main import create_app
from thesis_api.schemas import CapabilitiesDTO, CoverageItemDTO
from thesis_api.service import (
    ProviderBinding,
    _compute_coverage,
    _unavailable_capabilities,
    _COVERAGE_TARGET_METRICS,
)
from thesis_data.dataset_contract import (
    AnalyticalLevel,
    CanonicalObservation,
    DatasetCapabilityCatalog,
    DatasetEntity,
    DatasetEntityType,
    DatasetMetric,
    DatasetPeriod,
    DatasetRef,
    DatasetSource,
    SupportedOperation,
)
from thesis_data.in_memory_provider import InMemoryFinancialDatasetProvider
from thesis_data.schema import QualityStatus


class TestApiCapabilitiesCoverage(unittest.TestCase):
    def setUp(self) -> None:
        self.dataset_ref = DatasetRef(dataset_id="test-cov-dataset", dataset_snapshot_id="test-cov-v1")
        self.entities = (
            DatasetEntity(entity_id="ACB", entity_type=DatasetEntityType.COMPANY, display_name="ACB"),
            DatasetEntity(entity_id="TCB", entity_type=DatasetEntityType.COMPANY, display_name="TCB"),
        )
        self.periods = (
            DatasetPeriod(period_id="2024_Q1", label="2024 Q1"),
            DatasetPeriod(period_id="2024_Q2", label="2024 Q2"),
        )
        self.metrics = tuple(
            DatasetMetric(
                metric_id=m_id,
                display_name=m_id,
                analytical_level=AnalyticalLevel.COMPANY,
                default_unit="percent",
            )
            for m_id in _COVERAGE_TARGET_METRICS
        )
        self.catalog = DatasetCapabilityCatalog(
            dataset_ref=self.dataset_ref,
            entities=self.entities,
            periods=self.periods,
            metrics=self.metrics,
            peer_universes=(),
            source_refs=("src-test",),
            supported_operations=(
                SupportedOperation.GET_METRIC,
                SupportedOperation.GET_ENTITY_METRICS,
                SupportedOperation.RESOLVE_OBSERVATION,
            ),
        )

    def test_compute_coverage_with_missing_cells_and_partial(self) -> None:
        """Provider-backed fixture where missing cells stay missing and partial counts are exact."""
        observations = [
            # ACB 2024_Q1: All 4 metrics valid
            CanonicalObservation(
                observation_id="acb-q1-npl",
                dataset_id=self.dataset_ref.dataset_id,
                dataset_snapshot_id=self.dataset_ref.dataset_snapshot_id,
                entity_id="ACB",
                period_id="2024_Q1",
                metric_id="bank.npl_g35",
                value=1.5,
                unit="percent",
                source_ref="src-test",
                validation_status=QualityStatus.VALID,
            ),
            CanonicalObservation(
                observation_id="acb-q1-llr",
                dataset_id=self.dataset_ref.dataset_id,
                dataset_snapshot_id=self.dataset_ref.dataset_snapshot_id,
                entity_id="ACB",
                period_id="2024_Q1",
                metric_id="bank.llr_coverage",
                value=120.0,
                unit="percent",
                source_ref="src-test",
                validation_status=QualityStatus.VALID,
            ),
            CanonicalObservation(
                observation_id="acb-q1-roa",
                dataset_id=self.dataset_ref.dataset_id,
                dataset_snapshot_id=self.dataset_ref.dataset_snapshot_id,
                entity_id="ACB",
                period_id="2024_Q1",
                metric_id="bank.roa",
                value=2.1,
                unit="percent",
                source_ref="src-test",
                validation_status=QualityStatus.VALID,
            ),
            CanonicalObservation(
                observation_id="acb-q1-roe",
                dataset_id=self.dataset_ref.dataset_id,
                dataset_snapshot_id=self.dataset_ref.dataset_snapshot_id,
                entity_id="ACB",
                period_id="2024_Q1",
                metric_id="bank.roe",
                value=22.0,
                unit="percent",
                source_ref="src-test",
                validation_status=QualityStatus.VALID,
            ),
            # ACB 2024_Q2: Partial (only 2 metrics)
            CanonicalObservation(
                observation_id="acb-q2-npl",
                dataset_id=self.dataset_ref.dataset_id,
                dataset_snapshot_id=self.dataset_ref.dataset_snapshot_id,
                entity_id="ACB",
                period_id="2024_Q2",
                metric_id="bank.npl_g35",
                value=1.6,
                unit="percent",
                source_ref="src-test",
                validation_status=QualityStatus.VALID,
            ),
            CanonicalObservation(
                observation_id="acb-q2-roa",
                dataset_id=self.dataset_ref.dataset_id,
                dataset_snapshot_id=self.dataset_ref.dataset_snapshot_id,
                entity_id="ACB",
                period_id="2024_Q2",
                metric_id="bank.roa",
                value=2.0,
                unit="percent",
                source_ref="src-test",
                validation_status=QualityStatus.VALID,
            ),
            # TCB 2024_Q1: 3 valid, 1 suspect/missing observation
            CanonicalObservation(
                observation_id="tcb-q1-npl",
                dataset_id=self.dataset_ref.dataset_id,
                dataset_snapshot_id=self.dataset_ref.dataset_snapshot_id,
                entity_id="TCB",
                period_id="2024_Q1",
                metric_id="bank.npl_g35",
                value=1.2,
                unit="percent",
                source_ref="src-test",
                validation_status=QualityStatus.VALID,
            ),
            CanonicalObservation(
                observation_id="tcb-q1-llr",
                dataset_id=self.dataset_ref.dataset_id,
                dataset_snapshot_id=self.dataset_ref.dataset_snapshot_id,
                entity_id="TCB",
                period_id="2024_Q1",
                metric_id="bank.llr_coverage",
                value=130.0,
                unit="percent",
                source_ref="src-test",
                validation_status=QualityStatus.VALID,
            ),
            CanonicalObservation(
                observation_id="tcb-q1-roa",
                dataset_id=self.dataset_ref.dataset_id,
                dataset_snapshot_id=self.dataset_ref.dataset_snapshot_id,
                entity_id="TCB",
                period_id="2024_Q1",
                metric_id="bank.roa",
                value=2.5,
                unit="percent",
                source_ref="src-test",
                validation_status=QualityStatus.VALID,
            ),
            CanonicalObservation(
                observation_id="tcb-q1-roe",
                dataset_id=self.dataset_ref.dataset_id,
                dataset_snapshot_id=self.dataset_ref.dataset_snapshot_id,
                entity_id="TCB",
                period_id="2024_Q1",
                metric_id="bank.roe",
                value=None,
                unit="percent",
                validation_status=QualityStatus.MISSING,
                missing_reason="missing_filing",
            ),
            # TCB 2024_Q2: Completely missing cell (0 observations)
        ]

        sources = (
            DatasetSource(
                source_ref="src-test",
                source_type="filing",
                source_tier="primary",
                source_url="https://example.com/source",
                publisher="Test Publisher",
                retrieved_at="2024-01-01T00:00:00Z",
                content_hash="hash123",
                validation_status=QualityStatus.VALID,
            ),
        )
        provider = InMemoryFinancialDatasetProvider(self.catalog, observations=observations, sources=sources)
        binding = ProviderBinding(provider, self.dataset_ref, self.catalog, "in-memory")

        coverage = _compute_coverage(binding)

        self.assertEqual(len(coverage), 4)

        # Check ACB 2024_Q1: 4/4 filled
        acb_q1 = next(item for item in coverage if item["entity_id"] == "ACB" and item["period_id"] == "2024_Q1")
        self.assertEqual(len(acb_q1["metrics"]), 4)
        self.assertEqual(
            set(acb_q1["metrics"]),
            {"bank.npl_g35", "bank.llr_coverage", "bank.roa", "bank.roe"},
        )

        # Check ACB 2024_Q2: partial (2/4)
        acb_q2 = next(item for item in coverage if item["entity_id"] == "ACB" and item["period_id"] == "2024_Q2")
        self.assertEqual(len(acb_q2["metrics"]), 2)
        self.assertEqual(set(acb_q2["metrics"]), {"bank.npl_g35", "bank.roa"})

        # Check TCB 2024_Q1: 3/4 (suspect/missing metric is not accepted)
        tcb_q1 = next(item for item in coverage if item["entity_id"] == "TCB" and item["period_id"] == "2024_Q1")
        self.assertEqual(len(tcb_q1["metrics"]), 3)
        self.assertNotIn("bank.roe", tcb_q1["metrics"])

        # Check TCB 2024_Q2: completely missing cell stays empty
        tcb_q2 = next(item for item in coverage if item["entity_id"] == "TCB" and item["period_id"] == "2024_Q2")
        self.assertEqual(tcb_q2["metrics"], [])

    def test_get_capabilities_endpoint_returns_coverage_and_validates_schema(self) -> None:
        """GET /api/capabilities includes coverage array and passes CapabilitiesDTO validation."""
        observations = [
            CanonicalObservation(
                observation_id="acb-q1-npl",
                dataset_id=self.dataset_ref.dataset_id,
                dataset_snapshot_id=self.dataset_ref.dataset_snapshot_id,
                entity_id="ACB",
                period_id="2024_Q1",
                metric_id="bank.npl_g35",
                value=1.5,
                unit="percent",
                source_ref="src-test",
                validation_status=QualityStatus.VALID,
            ),
        ]
        sources = (
            DatasetSource(
                source_ref="src-test",
                source_type="filing",
                source_tier="primary",
                source_url="https://example.com/source",
                publisher="Test Publisher",
                retrieved_at="2024-01-01T00:00:00Z",
                content_hash="hash123",
                validation_status=QualityStatus.VALID,
            ),
        )
        provider = InMemoryFinancialDatasetProvider(self.catalog, observations=observations, sources=sources)
        binding = ProviderBinding(provider, self.dataset_ref, self.catalog, "in-memory")

        app = create_app()
        client = TestClient(app)

        with patch("thesis_api.service._load_provider", return_value=binding):
            response = client.get("/api/capabilities")

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("coverage", data)
        self.assertIsInstance(data["coverage"], list)

        # Validate with CapabilitiesDTO
        dto = CapabilitiesDTO.model_validate(data)
        self.assertEqual(len(dto.coverage), 4)
        for item in dto.coverage:
            self.assertIsInstance(item, CoverageItemDTO)

        # Check that ACB 2024_Q1 has bank.npl_g35 and TCB 2024_Q2 has []
        acb_q1 = next(c for c in dto.coverage if c.entity_id == "ACB" and c.period_id == "2024_Q1")
        self.assertEqual(acb_q1.metrics, ["bank.npl_g35"])

        tcb_q2 = next(c for c in dto.coverage if c.entity_id == "TCB" and c.period_id == "2024_Q2")
        self.assertEqual(tcb_q2.metrics, [])

    def test_unavailable_capabilities_returns_empty_coverage(self) -> None:
        """When snapshot is unavailable, coverage is an empty list."""
        unavail = _unavailable_capabilities("test reason", "test_code")
        self.assertIn("coverage", unavail)
        self.assertEqual(unavail["coverage"], [])

    def test_real_top10_and_gold_snapshots_coverage(self) -> None:
        """Real top10 operational snapshot has exactly the 8 expected missing quarters and Gold v5 computes correctly."""
        top10_path = Path("data/processed/bank-quarterly-top10-operational-v1.sqlite")
        if top10_path.is_file():
            from thesis_api.service import _load_provider
            binding = _load_provider(top10_path)
            coverage = _compute_coverage(binding)
            self.assertEqual(len(coverage), 150)  # 10 banks * 15 periods

            # 8 missing bank-quarters must have empty metrics
            expected_missing = [
                ("ACB", "2026_Q1"),
                ("BID", "2024_Q3"),
                ("CTG", "2024_Q3"),
                ("CTG", "2025_Q3"),
                ("HDB", "2024_Q3"),
                ("SHB", "2024_Q2"),
                ("VPB", "2026_Q1"),
                ("VPB", "2026_Q2"),
            ]
            for ent_id, per_id in expected_missing:
                cell = next(c for c in coverage if c["entity_id"] == ent_id and c["period_id"] == per_id)
                self.assertEqual(cell["metrics"], [], f"Expected {ent_id} {per_id} to be missing")

            # Filled cells have all 4 metrics
            acb_q1 = next(c for c in coverage if c["entity_id"] == "ACB" and c["period_id"] == "2024_Q1")
            self.assertEqual(len(acb_q1["metrics"]), 4)


if __name__ == "__main__":
    unittest.main()

