"""Integration and unit tests for UPLOAD-1 new bank CSV upload and analysis."""

from __future__ import annotations

import hashlib
import io
import json
import sqlite3
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT / "src") not in sys.path:
    sys.path.insert(0, str(REPO_ROOT / "src"))
if str(REPO_ROOT / "tests") not in sys.path:
    sys.path.insert(0, str(REPO_ROOT / "tests"))
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from fastapi.testclient import TestClient

try:
    from socket_guard import install_socket_guard
except ImportError:
    from tests.socket_guard import install_socket_guard


def setUpModule() -> None:
    install_socket_guard()


try:
    from test_api_analyze import (
        _ExplicitOfflineAcceptingCritic,
        _ExplicitOfflineAnalysisWriter,
        _LocatorTestProvider,
        _gold_fixture,
    )
except ImportError:
    from tests.test_api_analyze import (
        _ExplicitOfflineAcceptingCritic,
        _ExplicitOfflineAnalysisWriter,
        _LocatorTestProvider,
        _gold_fixture,
    )

from thesis_api.main import create_app
from thesis_api.schemas import AnalysisRequest, AnalysisResponse
from thesis_api.service import ProviderBinding, _load_provider
from thesis_api.settings import Settings
from thesis_data.composite_provider import CompositeDatasetProvider
from thesis_data.user_upload import (
    generate_ctg_error_sample_csv,
    generate_ctg_sample_csv,
    generate_template_csv,
    validate_and_parse_upload_csv,
)


class _ScopeTestProvider(_LocatorTestProvider):
    def _observation(self, observation):
        obs = super()._observation(observation)
        if obs is not None and not getattr(obs, "reporting_scope", None):
            obs.reporting_scope = "consolidated"
        return obs

    def get_peer_benchmark(self, dataset_ref, peer_universe_id, period_id, metric_ids, peer_entity_ids=None):
        benchmarks = []
        peers = tuple(peer_entity_ids) if peer_entity_ids else ("ACB",)
        for metric_id in metric_ids:
            obs = self.get_metric(dataset_ref, peers[0], period_id, metric_id)
            if obs is not None:
                from thesis_data.dataset_contract import CanonicalObservation, QualityStatus
                metadata = {
                    "aggregation_method": "peer_median_v1",
                    "aggregation_version": "peer_median_v1",
                    "peer_universe_id": peer_universe_id,
                    "requested_peer_entity_ids": list(peers),
                    "eligible_peer_entity_ids": list(peers),
                    "requested_denominator": len(peers),
                    "eligible_denominator": len(peers),
                    "missing_members": [],
                    "peer_member_observations": [
                        {
                            "entity_id": peers[0],
                            "observation_id": obs.observation_id,
                            "accepted": True,
                            "reporting_scope": "consolidated",
                            "validation_status": "valid",
                        }
                    ],
                }
                from thesis_data.dataset_provider import peer_benchmark_observation_id
                benchmarks.append(
                    CanonicalObservation(
                        observation_id=peer_benchmark_observation_id(dataset_ref, peer_universe_id, period_id, metric_id, peers),
                        dataset_id=dataset_ref.dataset_id,
                        dataset_snapshot_id=dataset_ref.dataset_snapshot_id,
                        entity_id=peer_universe_id,
                        period_id=period_id,
                        metric_id=metric_id,
                        value=float(obs.value),
                        unit=obs.unit,
                        period_basis="point_in_time",
                        reporting_scope="consolidated",
                        validation_status=QualityStatus.VALID,
                        derivation_method="peer_median_v1",
                        input_observation_ids=(obs.observation_id,),
                        metadata=metadata,
                    )
                )
        return tuple(benchmarks)


def _scope_fixture_provider_binding(path: Path) -> ProviderBinding:
    binding = _load_provider(path)
    provider = _ScopeTestProvider(binding.provider, expose_locator=True)
    return ProviderBinding(provider, binding.dataset_ref, binding.catalog, binding.provider_name)


def _file_hash(path: Path) -> str:
    hasher = hashlib.sha256()
    with open(path, "rb") as f:
        while chunk := f.read(65536):
            hasher.update(chunk)
    return hasher.hexdigest()


class NewBankUploadTests(unittest.TestCase):
    """Verifies CSV parsing, validation, endpoints, composite analysis, and Gold immutability."""

    def setUp(self) -> None:
        self.directory = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
        self.addCleanup(self.directory.cleanup)
        self.dir_path = Path(self.directory.name)

        self.gold_db_path = _gold_fixture(self.dir_path / "accepted-gold.sqlite")
        self.gold_initial_hash = _file_hash(self.gold_db_path)

        self.uploads_dir = self.dir_path / "user_uploads"
        self.uploads_dir.mkdir(parents=True, exist_ok=True)

        self.settings = Settings(
            app_name="final-thesis-api-upload-test",
            app_env="test",
            sqlite_db_path=str(self.gold_db_path),
            analysis_runs_db_path=str(self.dir_path / "analysis-runs.sqlite"),
            user_uploads_dir=str(self.uploads_dir),
            openai_api_key="test-key",
            planner_mode="rules_only",
        )

        self.test_critic = _ExplicitOfflineAcceptingCritic()
        self.critic_factory_patch = patch(
            "thesis_api.adaptive_runtime.build_openai_semantic_critic",
            return_value=self.test_critic,
        )
        self.critic_factory_patch.start()
        self.addCleanup(self.critic_factory_patch.stop)

        self.writer = _ExplicitOfflineAnalysisWriter()
        self.app = create_app(self.settings, analysis_writer=self.writer)
        self.client = TestClient(self.app)
        self.addCleanup(self.client.close)

    def test_ctg_sample_csv_is_accepted_with_recomputed_metrics(self) -> None:
        csv_bytes = generate_ctg_sample_csv()
        result = validate_and_parse_upload_csv(csv_bytes, upload_id="test-ctg", form_entity_id="CTG")

        self.assertEqual(result.status, "accepted")
        self.assertEqual(result.entity_id, "CTG")
        self.assertEqual(result.period_id, "2024_Q4")
        self.assertEqual(len(result.row_issues), 0)

        metric_map = {m.metric_id: m for m in result.metrics}
        self.assertIn("bank.npl_g35", metric_map)
        self.assertIn("bank.llr_coverage", metric_map)
        self.assertIn("bank.roa", metric_map)
        self.assertIn("bank.roe", metric_map)

        for m in metric_map.values():
            self.assertEqual(m.status, "matched")
            self.assertIsNotNone(m.computed_value)
            self.assertIsNotNone(m.reported_value)

        # Recomputed checks matching CTG 2024 Q4
        self.assertAlmostEqual(metric_map["bank.npl_g35"].computed_value, 1.219, places=2)
        self.assertAlmostEqual(metric_map["bank.llr_coverage"].computed_value, 174.68, places=1)
        self.assertAlmostEqual(metric_map["bank.roa"].computed_value, 1.15, places=2)
        self.assertAlmostEqual(metric_map["bank.roe"].computed_value, 18.60, places=1)

    def test_ctg_error_sample_csv_is_rejected_with_exact_three_row_issues(self) -> None:
        csv_bytes = generate_ctg_error_sample_csv()
        result = validate_and_parse_upload_csv(csv_bytes, upload_id="test-err", form_entity_id="CTG")

        self.assertEqual(result.status, "rejected")
        self.assertEqual(len(result.row_issues), 3)

        fields = {issue.field for issue in result.row_issues}
        self.assertIn("source_locator", fields)
        self.assertIn("unit", fields)
        self.assertIn("value", fields)

        # Specific checks on Vietnamese issue messages
        loc_issue = next(i for i in result.row_issues if i.field == "source_locator")
        self.assertEqual(loc_issue.row, 4)
        self.assertIn("trang", loc_issue.message_vi.lower())

        unit_issue = next(i for i in result.row_issues if i.field == "unit")
        self.assertEqual(unit_issue.row, 5)
        self.assertIn("billion_vnd", unit_issue.message_vi)

        val_issue = next(i for i in result.row_issues if i.field == "value")
        self.assertIn("lệch", val_issue.message_vi.lower())

    def test_endpoints_template_and_samples(self) -> None:
        # 1. Template
        resp = self.client.get("/api/onboarding/template.csv")
        self.assertEqual(resp.status_code, 200)
        self.assertIn("text/csv", resp.headers["content-type"])
        self.assertIn("template.csv", resp.headers["content-disposition"])
        self.assertIn("observation_id,entity_id,metric_id", resp.text)

        # 2. Valid CTG sample
        resp = self.client.get("/api/onboarding/samples/ctg-2024q4.csv")
        self.assertEqual(resp.status_code, 200)
        self.assertIn("bank.input.gross_customer_loans", resp.text)
        self.assertIn("1.219", resp.text)

        # 3. Error CTG sample
        resp = self.client.get("/api/onboarding/samples/ctg-2024q4-loi.csv")
        self.assertEqual(resp.status_code, 200)
        self.assertIn("vnd", resp.text)

        # 4. Unknown sample
        resp = self.client.get("/api/onboarding/samples/unknown.csv")
        self.assertEqual(resp.status_code, 404)

    def test_upload_flow_and_details_retrieval(self) -> None:
        valid_csv = generate_ctg_sample_csv()

        resp = self.client.post(
            "/api/onboarding/uploads",
            files={"file": ("ctg-2024q4.csv", io.BytesIO(valid_csv.encode("utf-8")), "text/csv")},
            data={"entity_id": "CTG", "display_name": "VietinBank"},
        )
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data["status"], "accepted")
        self.assertEqual(data["entity_id"], "CTG")
        self.assertEqual(data["period_id"], "2024_Q4")
        upload_id = data["upload_id"]
        self.assertTrue(upload_id)

        # List uploads
        list_resp = self.client.get("/api/onboarding/uploads")
        self.assertEqual(list_resp.status_code, 200)
        items = list_resp.json()
        self.assertTrue(any(item["upload_id"] == upload_id for item in items))

        # Get upload details
        detail_resp = self.client.get(f"/api/onboarding/uploads/{upload_id}")
        self.assertEqual(detail_resp.status_code, 200)
        detail = detail_resp.json()
        self.assertEqual(detail["upload_id"], upload_id)
        self.assertEqual(detail["status"], "accepted")
        self.assertEqual(len(detail["metrics"]), 4)

        # Negative: upload error sample
        error_csv = generate_ctg_error_sample_csv()
        err_resp = self.client.post(
            "/api/onboarding/uploads",
            files={"file": ("ctg-error.csv", io.BytesIO(error_csv.encode("utf-8")), "text/csv")},
            data={"entity_id": "CTG"},
        )
        self.assertEqual(err_resp.status_code, 200)
        err_data = err_resp.json()
        self.assertEqual(err_data["status"], "rejected")
        self.assertEqual(len(err_data["row_issues"]), 3)

    def test_analysis_with_upload_id_accepted_and_gold_immutability(self) -> None:
        # 1. Upload valid CTG sample
        valid_csv = generate_ctg_sample_csv()
        upload_resp = self.client.post(
            "/api/onboarding/uploads",
            files={"file": ("ctg-2024q4.csv", io.BytesIO(valid_csv.encode("utf-8")), "text/csv")},
            data={"entity_id": "CTG", "display_name": "VietinBank"},
        )
        self.assertEqual(upload_resp.status_code, 200)
        upload_id = upload_resp.json()["upload_id"]

        # 2. Analyze CTG with upload_id
        with patch(
            "thesis_api.service._load_provider",
            side_effect=_scope_fixture_provider_binding,
        ):
            analyze_resp = self.client.post(
                "/api/analyze",
                json={
                    "query": "Tỷ lệ nợ xấu của CTG quý 4/2024 là bao nhiêu?",
                    "target_ticker": "CTG",
                    "period": "2024_Q4",
                    "upload_id": upload_id,
                },
            )

        self.assertEqual(analyze_resp.status_code, 200)
        report_data = analyze_resp.json()
        report = AnalysisResponse.model_validate(report_data)

        self.assertEqual(report.status, "completed")
        self.assertEqual(report.analysis_plan.target_ticker, "CTG")

        # Required limitation statement from spec
        expected_limitation = (
            "Số liệu CTG do người dùng cung cấp; hệ thống đã kiểm tra cấu trúc, "
            "nguồn và tính lại chỉ tiêu, chưa được duyệt độc lập như bộ Gold."
        )
        self.assertIn(expected_limitation, report.limitations)

        # Atomic claims verify CTG NPL
        npl_claims = [c for c in report.atomic_claims if c.metric == "bank.npl_g35"]
        self.assertTrue(len(npl_claims) >= 1)
        self.assertEqual(npl_claims[0].ticker, "CTG")
        self.assertEqual(npl_claims[0].stage1_status, "accepted")

        # 3. Immutability verification: Gold DB file hash MUST NOT CHANGE
        gold_current_hash = _file_hash(self.gold_db_path)
        self.assertEqual(
            self.gold_initial_hash,
            gold_current_hash,
            "Gold database was modified during upload/analysis execution!",
        )

    def test_analysis_without_upload_id_fails_closed_for_ctg(self) -> None:
        with patch(
            "thesis_api.service._load_provider",
            side_effect=_scope_fixture_provider_binding,
        ):
            resp = self.client.post(
                "/api/analyze",
                json={
                    "query": "Tỷ lệ nợ xấu của CTG quý 4/2024",
                    "target_ticker": "CTG",
                    "period": "2024_Q4",
                },
            )
        # Without upload_id, CTG is not in the Gold snapshot
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data.get("status"), "error")
        self.assertIn("unsupported_entity", str(data))

    def test_head_to_head_ctg_vs_gold_bank_with_upload_id(self) -> None:
        # Upload valid CTG sample
        valid_csv = generate_ctg_sample_csv()
        upload_resp = self.client.post(
            "/api/onboarding/uploads",
            files={"file": ("ctg-2024q4.csv", io.BytesIO(valid_csv.encode("utf-8")), "text/csv")},
            data={"entity_id": "CTG"},
        )
        upload_id = upload_resp.json()["upload_id"]

        with patch(
            "thesis_api.service._load_provider",
            side_effect=_scope_fixture_provider_binding,
        ):
            resp = self.client.post(
                "/api/analyze",
                json={
                    "query": "So sánh nợ xấu giữa CTG và ACB trong quý 4/2024",
                    "target_ticker": "CTG",
                    "peer_ticker": "ACB",
                    "period": "2024_Q4",
                    "upload_id": upload_id,
                },
            )
        self.assertEqual(resp.status_code, 200)
        report = AnalysisResponse.model_validate(resp.json())
        self.assertEqual(report.status, "completed")
        self.assertTrue(
            any("Số liệu CTG do người dùng cung cấp" in lim for lim in report.limitations)
        )

    def test_peer_median_strictly_excludes_uploaded_bank(self) -> None:
        valid_csv = generate_ctg_sample_csv()
        upload_resp = self.client.post(
            "/api/onboarding/uploads",
            files={"file": ("ctg-2024q4.csv", io.BytesIO(valid_csv.encode("utf-8")), "text/csv")},
            data={"entity_id": "CTG"},
        )
        upload_id = upload_resp.json()["upload_id"]

        from thesis_api.service import _load_provider, resolve_composite_upload_binding

        base_binding = _load_provider(self.gold_db_path)
        composite_binding, _ = resolve_composite_upload_binding(
            base_binding, upload_id, self.uploads_dir
        )

        catalog = composite_binding.catalog
        # CTG is an entity in catalog
        entity_ids = [e.entity_id for e in catalog.entities]
        self.assertIn("CTG", entity_ids)

        # But peer universes ONLY contain the base universe members
        for universe in catalog.peer_universes:
            self.assertNotIn("CTG", universe.entity_ids)

    def test_unsupported_question_type_for_uploaded_bank_fails_closed(self) -> None:
        valid_csv = generate_ctg_sample_csv()
        upload_resp = self.client.post(
            "/api/onboarding/uploads",
            files={"file": ("ctg-2024q4.csv", io.BytesIO(valid_csv.encode("utf-8")), "text/csv")},
            data={"entity_id": "CTG"},
        )
        upload_id = upload_resp.json()["upload_id"]

        with patch(
            "thesis_api.service._load_provider",
            side_effect=_scope_fixture_provider_binding,
        ):
            # Asking for industry landscape / ranking
            resp = self.client.post(
                "/api/analyze",
                json={
                    "query": "Xếp hạng toàn ngành của CTG",
                    "target_ticker": "CTG",
                    "period": "2024_Q4",
                    "upload_id": upload_id,
                },
            )
        self.assertEqual(resp.status_code, 200)
        err = resp.json()
        self.assertEqual(err.get("status"), "error")
        self.assertTrue(
            "upload_question_type_unsupported" in str(err)
            or "chỉ hỗ trợ tra cứu" in str(err).lower()
        )

    def test_unsupported_period_for_uploaded_bank_fails_closed(self) -> None:
        valid_csv = generate_ctg_sample_csv()
        upload_resp = self.client.post(
            "/api/onboarding/uploads",
            files={"file": ("ctg-2024q4.csv", io.BytesIO(valid_csv.encode("utf-8")), "text/csv")},
            data={"entity_id": "CTG"},
        )
        upload_id = upload_resp.json()["upload_id"]

        with patch(
            "thesis_api.service._load_provider",
            side_effect=_scope_fixture_provider_binding,
        ):
            # CTG only has 2024_Q4 data uploaded, request 2024_Q2
            resp = self.client.post(
                "/api/analyze",
                json={
                    "query": "Phân tích nợ xấu của CTG trong quý 2 năm 2024",
                    "target_ticker": "CTG",
                    "period": "2024_Q2",
                    "upload_id": upload_id,
                },
            )
        self.assertEqual(resp.status_code, 200)
        err = resp.json()
        self.assertEqual(err.get("status"), "error")
        self.assertTrue(
            "upload_period_mismatch" in str(err)
            or "2024_q4" in str(err).lower()
            or "không có số liệu" in str(err).lower()
        )
