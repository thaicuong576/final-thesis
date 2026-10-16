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

from thesis_api.main import create_app
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

        self.settings = Settings(
            app_name="final-thesis-filing-api-test",
            app_env="test",
            sqlite_db_path=":memory:",
            analysis_runs_db_path=str(self.base_dir / "runs.sqlite"),
            user_uploads_dir=str(self.uploads_dir),
            openai_api_key="test-key",
            planner_mode="rules_only",
            ocr_provider="tesseract",
        )

        self.app = create_app(self.settings)
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


if __name__ == "__main__":
    unittest.main()
