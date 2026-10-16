"""Integration tests for filing PDF intake, OCR, and candidate extraction API endpoints.

Phase: INGEST-1 (D-086).
Tests POST /api/onboarding/filings, GET /api/onboarding/filings,
GET /api/onboarding/filings/{filing_id}, and GET /api/onboarding/filings/{filing_id}/pages/{n}.png.
"""

from __future__ import annotations

import io
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient

try:
    from tests.test_api_analyze import (
        _ExplicitOfflineAcceptingCritic,
        _ExplicitOfflineAnalysisWriter,
        _gold_fixture,
    )
    from tests.test_new_bank_upload import _scope_fixture_provider_binding
except ImportError:
    from test_api_analyze import (  # type: ignore
        _ExplicitOfflineAcceptingCritic,
        _ExplicitOfflineAnalysisWriter,
        _gold_fixture,
    )
    from test_new_bank_upload import _scope_fixture_provider_binding  # type: ignore

from thesis_api.main import create_app
from thesis_api.schemas import AnalysisRequest, AnalysisResponse
from thesis_api.service import AnalysisEngine
from thesis_api.settings import Settings


def _create_synthetic_filing_pdf() -> bytes:
    """Create a minimal 3-page synthetic PDF with PyMuPDF containing statement text layers."""
    import fitz

    doc = fitz.open()

    # Page 1: Balance Sheet
    p1 = doc.new_page()
    p1.insert_text(
        (50, 72),
        "BAO CAO TINH HINH TAI CHINH HOP NHAT\n"
        "Tai ngay 31.12.2025 va 31.12.2024\n"
        "Don vi tinh: trieu dong\n"
        "1. Cho vay khach hang 600.000.000 500.000.000\n"
        "2. Du phong rui ro cho vay khach hang (7.000.000) (6.000.000)\n"
        "TONG CONG TAI SAN 1.000.000.000 800.000.000\n"
        "TONG VON CHU SO HUU 100.000.000 80.000.000\n"
        "Loi ich cua co dong khong kiem soat 1.000.000 800.000\n"
        "Tong tai san va no phai tra hop nhat day du\n",
    )

    # Page 2: Income Statement
    p2 = doc.new_page()
    p2.insert_text(
        (50, 72),
        "BAO CAO KET QUA HOAT DONG KINH DOANH HOP NHAT\n"
        "Nam 2025 Nam 2024\n"
        "Don vi tinh: trieu dong\n"
        "Thu nhap lai thuan 30.000.000 25.000.000\n"
        "LOI NHUAN SAU THUE 15.000.000 12.000.000\n"
        "Co dong cua Ngan hang 14.000.000 11.200.000\n"
        "Ket qua kinh doanh cua ngan hang me va cong ty con\n",
    )

    # Page 3: Loan Quality Note
    p3 = doc.new_page()
    p3.insert_text(
        (50, 72),
        "THUYET MINH BAO CAO TAI CHINH\n"
        "Theo chat luong no cho vay\n"
        "31.12.2025 31.12.2024\n"
        "Don vi: trieu dong\n"
        "Nhom 1 - No du tieu chuan 580.000.000 480.000.000\n"
        "Nhom 2 - No can chu y 8.000.000 8.000.000\n"
        "Nhom 3 - No duoi tieu chuan 3.000.000 2.500.000\n"
        "Nhom 4 - No nghi ngo 4.000.000 3.500.000\n"
        "Nhom 5 - No co kha nang mat von 5.000.000 6.000.000\n"
        "Tong nhom 1-5 600.000.000 500.000.000\n",
    )

    pdf_bytes = doc.tobytes()
    doc.close()
    return pdf_bytes


class TestFilingApi(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
        self.addCleanup(self.temp_dir.cleanup)
        self.base_dir = Path(self.temp_dir.name)

        self.uploads_dir = self.base_dir / "user_uploads"
        self.uploads_dir.mkdir(parents=True, exist_ok=True)

        self.gold_db_path = _gold_fixture(self.base_dir / "accepted-gold.sqlite")

        self.settings = Settings(
            _env_file=None,
            app_name="final-thesis-filing-api-test",
            app_env="test",
            sqlite_db_path=str(self.gold_db_path),
            analysis_runs_db_path=str(self.base_dir / "runs.sqlite"),
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
        # Enable synchronous execution for fast deterministic test processing
        self.app.state.filing_sync_execution = True

        self.client = TestClient(self.app)
        self.addCleanup(self.client.close)

    def test_upload_valid_pdf_and_query_filing(self) -> None:
        pdf_bytes = _create_synthetic_filing_pdf()

        # 1. POST /api/onboarding/filings
        resp = self.client.post(
            "/api/onboarding/filings",
            files={"file": ("test_filing.pdf", io.BytesIO(pdf_bytes), "application/pdf")},
            data={
                "entity_id": "VIB",
                "display_name": "Ngân hàng TMCP Quốc tế Việt Nam",
                "fiscal_year": 2025,
                "reporting_scope": "consolidated",
            },
        )
        self.assertEqual(resp.status_code, 202)
        body = resp.json()
        self.assertIn("filing_id", body)
        filing_id = body["filing_id"]
        self.assertTrue(filing_id.startswith("fl-"))

        # 2. GET /api/onboarding/filings/{filing_id}
        detail_resp = self.client.get(f"/api/onboarding/filings/{filing_id}")
        self.assertEqual(detail_resp.status_code, 200)
        detail = detail_resp.json()

        self.assertEqual(detail["filing_id"], filing_id)
        self.assertEqual(detail["entity_id"], "VIB")
        self.assertEqual(detail["status"], "ready")
        self.assertEqual(detail["page_count"], 3)
        self.assertEqual(detail["text_layer_pages"], 3)
        self.assertEqual(detail["unit_detected"], "million_vnd")

        # Statement pages
        stmt_pages = detail["statement_pages"]
        self.assertIn(1, stmt_pages["balance_sheet"])
        self.assertIn(2, stmt_pages["income_statement"])
        self.assertIn(3, stmt_pages["loan_quality_note"])

        # Rows check: 20 candidate rows (10 metrics * 2 periods)
        self.assertEqual(len(detail["rows"]), 20)
        row_map = {(r["metric_id"], r["period_role"]): r for r in detail["rows"]}

        ta_target = row_map[("bank.input.total_assets", "target")]
        self.assertEqual(ta_target["value_billion_vnd"], "1000000.000")
        self.assertEqual(ta_target["extracted_value_billion_vnd"], "1000000.000")
        self.assertEqual(ta_target["label_vi"], "Tổng tài sản")
        self.assertFalse(ta_target["edited"])
        self.assertFalse(ta_target["confirmed"])
        self.assertEqual(ta_target["status"], "candidate")
        self.assertEqual(detail["ocr_provider"], "text_layer")
        self.assertIsNotNone(detail.get("validation"))
        self.assertFalse(detail["validation"]["ready_to_confirm"])

        # 3. GET /api/onboarding/filings (list)
        list_resp = self.client.get("/api/onboarding/filings")
        self.assertEqual(list_resp.status_code, 200)
        filings = list_resp.json()
        self.assertGreaterEqual(len(filings), 1)
        self.assertEqual(filings[0]["filing_id"], filing_id)
        self.assertEqual(filings[0]["entity_id"], "VIB")
        self.assertEqual(filings[0]["page_count"], 3)

        # 4. GET /api/onboarding/filings/{filing_id}/pages/1.png
        img_resp = self.client.get(f"/api/onboarding/filings/{filing_id}/pages/1.png")
        self.assertEqual(img_resp.status_code, 200)
        self.assertEqual(img_resp.headers["content-type"], "image/png")
        self.assertGreater(len(img_resp.content), 100)

        # Test page out of bounds
        p0_resp = self.client.get(f"/api/onboarding/filings/{filing_id}/pages/0.png")
        self.assertEqual(p0_resp.status_code, 404)

        p99_resp = self.client.get(f"/api/onboarding/filings/{filing_id}/pages/99.png")
        self.assertEqual(p99_resp.status_code, 404)

    def test_rejections(self) -> None:
        pdf_bytes = _create_synthetic_filing_pdf()

        # Non-PDF file (magic bytes check)
        bad_file = self.client.post(
            "/api/onboarding/filings",
            files={"file": ("fake.pdf", io.BytesIO(b"NOT_A_PDF_DOCUMENT"), "application/pdf")},
            data={"entity_id": "VIB", "fiscal_year": 2025, "reporting_scope": "consolidated"},
        )
        self.assertEqual(bad_file.status_code, 400)
        self.assertIn("không phải là định dạng PDF", bad_file.json()["detail"])

        # Invalid reporting scope
        bad_scope = self.client.post(
            "/api/onboarding/filings",
            files={"file": ("f.pdf", io.BytesIO(pdf_bytes), "application/pdf")},
            data={"entity_id": "VIB", "fiscal_year": 2025, "reporting_scope": "invalid_scope"},
        )
        self.assertEqual(bad_scope.status_code, 400)

        # Invalid fiscal year
        bad_year = self.client.post(
            "/api/onboarding/filings",
            files={"file": ("f.pdf", io.BytesIO(pdf_bytes), "application/pdf")},
            data={"entity_id": "VIB", "fiscal_year": 1980, "reporting_scope": "consolidated"},
        )
        self.assertEqual(bad_year.status_code, 400)

        # Invalid filing_id format
        bad_id = self.client.get("/api/onboarding/filings/fl-invalid-path")
        self.assertEqual(bad_id.status_code, 400)

        bad_format = self.client.get("/api/onboarding/filings/fl-123")
        self.assertEqual(bad_format.status_code, 400)

        # Non-existent filing
        non_existent = self.client.get("/api/onboarding/filings/fl-0123456789ab")
        self.assertEqual(non_existent.status_code, 404)

    def test_gold_entity_rejected(self) -> None:
        pdf_bytes = _create_synthetic_filing_pdf()
        with patch.object(
            AnalysisEngine,
            "get_capabilities",
            return_value={"entities": [{"id": "ACB"}]},
        ):
            resp = self.client.post(
                "/api/onboarding/filings",
                files={"file": ("acb.pdf", io.BytesIO(pdf_bytes), "application/pdf")},
                data={"entity_id": "ACB", "fiscal_year": 2025, "reporting_scope": "consolidated"},
            )
            self.assertEqual(resp.status_code, 400)
            self.assertIn("ACB đã có trong bộ dữ liệu", resp.json()["detail"])

    def test_ocr_unavailable_failure_status(self) -> None:
        from thesis_api.filing_ocr import TesseractNotFoundError

        class FailingProvider:
            def get_page_count(self, p: Path) -> int:
                return 1

            def extract_all_pages(self, p: Path, **kwargs) -> list:
                raise TesseractNotFoundError("Máy chủ chưa cài đặt Tesseract OCR để đọc báo cáo dạng scan ảnh.")

            def render_page_png(self, p: Path, n: int, **kwargs) -> bytes:
                return b"fake-png"

        self.app.state.filing_page_provider = FailingProvider()
        try:
            pdf_bytes = _create_synthetic_filing_pdf()
            resp = self.client.post(
                "/api/onboarding/filings",
                files={"file": ("scan.pdf", io.BytesIO(pdf_bytes), "application/pdf")},
                data={"entity_id": "OCB", "fiscal_year": 2025, "reporting_scope": "consolidated"},
            )
            self.assertEqual(resp.status_code, 202)
            fid = resp.json()["filing_id"]

            detail_resp = self.client.get(f"/api/onboarding/filings/{fid}")
            self.assertEqual(detail_resp.status_code, 200)
            detail = detail_resp.json()
            self.assertEqual(detail["status"], "failed")
            self.assertEqual(detail["error_code"], "ocr_unavailable")
            self.assertIn("Tesseract OCR", detail["message_vi"])
        finally:
            self.app.state.filing_page_provider = None

    def test_filing_edit_row_and_confirm_flow(self) -> None:
        pdf_bytes = _create_synthetic_filing_pdf()

        # 1. POST /api/onboarding/filings -> 202
        resp = self.client.post(
            "/api/onboarding/filings",
            files={"file": ("vib_2025.pdf", io.BytesIO(pdf_bytes), "application/pdf")},
            data={
                "entity_id": "VIB",
                "display_name": "Ngân hàng TMCP Quốc tế Việt Nam",
                "fiscal_year": 2025,
                "reporting_scope": "consolidated",
            },
        )
        self.assertEqual(resp.status_code, 202)
        filing_id = resp.json()["filing_id"]

        # Detail initially ready with candidate rows
        detail = self.client.get(f"/api/onboarding/filings/{filing_id}").json()
        self.assertEqual(detail["status"], "ready")
        self.assertFalse(detail["validation"]["ready_to_confirm"])

        # 2. Confirm before all rows confirmed -> 409 Conflict
        bad_confirm = self.client.post(f"/api/onboarding/filings/{filing_id}/confirm")
        self.assertEqual(bad_confirm.status_code, 409)
        self.assertIn("chưa sẵn sàng", bad_confirm.json()["detail"])

        # 3. PUT row validation edge cases:
        # Invalid row_id format / not found
        bad_row = self.client.put(
            f"/api/onboarding/filings/{filing_id}/rows/unknown_metric:target",
            json={"value_billion_vnd": "100.0", "confirmed": True},
        )
        self.assertEqual(bad_row.status_code, 404)

        # Invalid decimal string
        bad_decimal = self.client.put(
            f"/api/onboarding/filings/{filing_id}/rows/bank.input.total_assets:target",
            json={"value_billion_vnd": "1,000,000", "confirmed": True},
        )
        self.assertEqual(bad_decimal.status_code, 422)

        # Negative value for non-PAT metric
        neg_val = self.client.put(
            f"/api/onboarding/filings/{filing_id}/rows/bank.input.total_assets:target",
            json={"value_billion_vnd": "-500.0", "confirmed": True},
        )
        self.assertEqual(neg_val.status_code, 422)

        # 4. Edit a row: change value, check edited=True, source="user"
        edit_resp = self.client.put(
            f"/api/onboarding/filings/{filing_id}/rows/bank.input.gross_customer_loans:target",
            json={"value_billion_vnd": "600000.000", "confirmed": True},
        )
        self.assertEqual(edit_resp.status_code, 200)
        res_data = edit_resp.json()
        row = res_data["row"]
        self.assertEqual(row["value_billion_vnd"], "600000.000")
        self.assertTrue(row["confirmed"])

        # Edit value
        edit_change = self.client.put(
            f"/api/onboarding/filings/{filing_id}/rows/bank.input.gross_customer_loans:target",
            json={"value_billion_vnd": "600050.000", "confirmed": True},
        )
        self.assertEqual(edit_change.status_code, 200)
        row2 = edit_change.json()["row"]
        self.assertTrue(row2["edited"])
        self.assertEqual(row2["source"], "user")

        # Revert back to 600000.000 for accounting consistency
        self.client.put(
            f"/api/onboarding/filings/{filing_id}/rows/bank.input.gross_customer_loans:target",
            json={"value_billion_vnd": "600000.000", "confirmed": True},
        )

        # 5. Confirm all 20 rows
        for r in detail["rows"]:
            row_id = r["row_id"]
            val = r["value_billion_vnd"]
            put_res = self.client.put(
                f"/api/onboarding/filings/{filing_id}/rows/{row_id}",
                json={"value_billion_vnd": val, "confirmed": True},
            )
            self.assertEqual(put_res.status_code, 200)

        # Now validation should be ready_to_confirm = True
        detail_after = self.client.get(f"/api/onboarding/filings/{filing_id}").json()
        self.assertTrue(detail_after["validation"]["ready_to_confirm"])
        self.assertEqual(detail_after["validation"]["status"], "pass")

        # 6. POST /api/onboarding/filings/{filing_id}/confirm -> 200 UploadResponse
        confirm_resp = self.client.post(f"/api/onboarding/filings/{filing_id}/confirm")
        self.assertEqual(confirm_resp.status_code, 200)
        confirm_body = confirm_resp.json()
        self.assertEqual(confirm_body["status"], "accepted")
        self.assertEqual(confirm_body["entity_id"], "VIB")
        self.assertEqual(confirm_body["period_id"], "2025_Q4")
        upload_id = confirm_body["upload_id"]
        self.assertTrue(upload_id.startswith("up-"))
        self.assertGreaterEqual(len(confirm_body["metrics"]), 4)

        # 7. Idempotent second call -> returns exact same upload_id
        confirm_again = self.client.post(f"/api/onboarding/filings/{filing_id}/confirm")
        self.assertEqual(confirm_again.status_code, 200)
        self.assertEqual(confirm_again.json()["upload_id"], upload_id)

        # 8. Detail reflects upload_id
        detail_final = self.client.get(f"/api/onboarding/filings/{filing_id}").json()
        self.assertEqual(detail_final["upload_id"], upload_id)

        # 9. GET /api/onboarding/uploads/{upload_id}
        upl_detail = self.client.get(f"/api/onboarding/uploads/{upload_id}")
        self.assertEqual(upl_detail.status_code, 200)
        self.assertEqual(upl_detail.json()["upload_id"], upload_id)

        # 10. POST /api/analyze with upload_id
        with patch(
            "thesis_api.service._load_provider",
            side_effect=_scope_fixture_provider_binding,
        ):
            analyze_resp = self.client.post(
                "/api/analyze",
                json={
                    "query": "Tỷ lệ nợ xấu của VIB năm 2025 là bao nhiêu?",
                    "target_ticker": "VIB",
                    "period": "2025_Q4",
                    "upload_id": upload_id,
                },
            )
        self.assertEqual(analyze_resp.status_code, 200)
        report_data = analyze_resp.json()
        report = AnalysisResponse.model_validate(report_data)
        self.assertEqual(report.status, "completed")
        self.assertEqual(report.analysis_plan.target_ticker, "VIB")

        # Provenance sentence must be in limitations
        pdf_sentence = "Số liệu được trích từ tệp PDF do người dùng tải lên và xác nhận."
        self.assertTrue(
            any(pdf_sentence in lim for lim in report.limitations),
            f"Expected '{pdf_sentence}' in limitations: {report.limitations}",
        )
        upload_sentence = "Số liệu VIB do người dùng cung cấp; hệ thống đã kiểm tra cấu trúc, nguồn và tính lại chỉ tiêu, chưa được duyệt độc lập như bộ Gold."
        self.assertTrue(
            any(upload_sentence in lim for lim in report.limitations),
            f"Expected '{upload_sentence}' in limitations: {report.limitations}",
        )

    def test_filing_confirm_rejection_when_accounting_fails(self) -> None:
        pdf_bytes = _create_synthetic_filing_pdf()
        resp = self.client.post(
            "/api/onboarding/filings",
            files={"file": ("vib_err.pdf", io.BytesIO(pdf_bytes), "application/pdf")},
            data={"entity_id": "VIB", "fiscal_year": 2025, "reporting_scope": "consolidated"},
        )
        self.assertEqual(resp.status_code, 202)
        filing_id = resp.json()["filing_id"]

        detail = self.client.get(f"/api/onboarding/filings/{filing_id}").json()

        # Mutate total assets to 5.0 (magnitude_range fail: < 100)
        for r in detail["rows"]:
            row_id = r["row_id"]
            val = r["value_billion_vnd"]
            if row_id == "bank.input.total_assets:target":
                val = "5.000"
            self.client.put(
                f"/api/onboarding/filings/{filing_id}/rows/{row_id}",
                json={"value_billion_vnd": val, "confirmed": True},
            )

        # Confirm should be blocked with 409 Conflict
        blocked_resp = self.client.post(f"/api/onboarding/filings/{filing_id}/confirm")
        self.assertEqual(blocked_resp.status_code, 409)


if __name__ == "__main__":
    unittest.main()
