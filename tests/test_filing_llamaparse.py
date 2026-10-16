"""Offline unit tests for LlamaParse table-aware page provider.

Phase: INGEST-4 (D-086).
Tests:
- HTML table to pipe-text conversion (with real ACB Note 9.3 snippet, tags stripped)
- Mock transport simulating LlamaParse v2 upload + poll flow
- Error handling: 401 unauthorized, 429 rate limit, 500 retry, timeout
- Secret protection (API key never leaked into exceptions/logs)
- Disk caching by (sha256, page, tier)
- Fallback to Tesseract when LlamaParse fails
- Full API onboarding integration with mock transport
"""

from __future__ import annotations

import io
import json
from pathlib import Path
import tempfile
import unittest

import fitz
from fastapi.testclient import TestClient
import httpx

from thesis_api.filing_llamaparse import (
    LLAMA_API_BASE_URL,
    LlamaParseError,
    LlamaParseProvider,
    html_table_to_pipe_text,
)
from thesis_api.main import create_app
from thesis_api.settings import Settings
from thesis_data.filing_extract import PageInput


def _create_minimal_pdf(pages_text: list[str]) -> bytes:
    doc = fitz.open()
    for txt in pages_text:
        page = doc.new_page()
        page.insert_text((50, 72), txt)
    data = doc.tobytes()
    doc.close()
    return data


class TestFilingLlamaParse(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
        self.addCleanup(self.temp_dir.cleanup)
        self.base_dir = Path(self.temp_dir.name)

    def test_html_table_to_pipe_text_acb_fixture(self) -> None:
        """Test HTML table conversion using ACB Note 9.3 fixture with styling tags."""
        html_fixture = """
        <p>9.3 Phân loại chất lượng nợ cho vay theo Thông tư 11</p>
        <p>Đơn vị tính: Triệu VND</p>
        <table>
            <thead>
                <tr>
                    <th>Phân loại nợ</th>
                    <th>31.12.2025</th>
                    <th>31.12.2024</th>
                </tr>
            </thead>
            <tbody>
                <tr>
                    <td>Nợ đủ tiêu chuẩn</td>
                    <td>580.000.000</td>
                    <td>480.000.000</td>
                </tr>
                <tr>
                    <td><b>Nợ cần chú ý</b></td>
                    <td>8.000.000</td>
                    <td>8.000.000</td>
                </tr>
                <tr>
                    <td><u>Nợ dưới tiêu chuẩn</u></td>
                    <td>3.000.000</td>
                    <td>2.500.000</td>
                </tr>
                <tr>
                    <td><i>Nợ nghi ngờ</i></td>
                    <td>4.000.000</td>
                    <td>3.500.000</td>
                </tr>
                <tr>
                    <td><span>Nợ có khả năng mất vốn</span></td>
                    <td>5.000.000</td>
                    <td>6.000.000</td>
                </tr>
            </tbody>
        </table>
        <p>Ghi chú bổ sung cuối trang</p>
        """
        converted = html_table_to_pipe_text(html_fixture)
        lines = [line.strip() for line in converted.splitlines() if line.strip()]

        self.assertIn("9.3 Phân loại chất lượng nợ cho vay theo Thông tư 11", lines)
        self.assertIn("Đơn vị tính: Triệu VND", lines)
        self.assertIn("Phân loại nợ | 31.12.2025 | 31.12.2024", lines)
        self.assertIn("Nợ đủ tiêu chuẩn | 580.000.000 | 480.000.000", lines)
        # Verify formatting tags <b>, <u>, <i>, <span> are stripped
        self.assertIn("Nợ cần chú ý | 8.000.000 | 8.000.000", lines)
        self.assertIn("Nợ dưới tiêu chuẩn | 3.000.000 | 2.500.000", lines)
        self.assertIn("Nợ nghi ngờ | 4.000.000 | 3.500.000", lines)
        self.assertIn("Nợ có khả năng mất vốn | 5.000.000 | 6.000.000", lines)
        self.assertIn("Ghi chú bổ sung cuối trang", lines)

    def test_mock_transport_success_and_cache(self) -> None:
        """Test success flow via MockTransport and verify disk cache hit."""
        pdf_bytes = _create_minimal_pdf(["Trang 1 noi dung scan", "Trang 2 noi dung scan"])
        pdf_path = self.base_dir / "sample.pdf"
        pdf_path.write_bytes(pdf_bytes)

        request_log: list[str] = []

        def handler(request: httpx.Request) -> httpx.Response:
            request_log.append(f"{request.method} {request.url.path}")
            # Ensure Authorization header contains secret without leaking
            self.assertEqual(request.headers.get("Authorization"), "Bearer mock-secret-key-12345")
            if request.url.path == "/api/v2/parse/upload":
                return httpx.Response(
                    200,
                    json={"id": "job-test-789", "status": "PENDING"},
                )
            if request.url.path == "/api/v2/parse/job-test-789":
                return httpx.Response(
                    200,
                    json={
                        "job": {"id": "job-test-789", "status": "COMPLETED"},
                        "markdown": {
                            "pages": [
                                {
                                    "page": 1,
                                    "markdown": "<table><tr><th>Chỉ tiêu</th><th>2025 Triệu VND</th></tr><tr><td>Tổng tài sản</td><td>100.000.000</td></tr></table>",
                                }
                            ]
                        },
                    },
                )
            return httpx.Response(404)

        transport = httpx.MockTransport(handler)
        cache_dir = self.base_dir / "cache_pages"

        provider = LlamaParseProvider(
            api_key="mock-secret-key-12345",
            poll_interval_s=0.01,
            transport=transport,
        )

        # 1. First extraction: hits mock transport
        pages = provider.extract_pages(pdf_path, [1], cache_dir=cache_dir)
        self.assertEqual(len(pages), 1)
        self.assertEqual(pages[0].page_number, 1)
        self.assertEqual(pages[0].source, "llamaparse")
        self.assertIn("Tổng tài sản | 100.000.000", pages[0].text)
        self.assertEqual(provider.total_pages_sent, 1)

        # Verify disk cache files created
        txt_path = cache_dir / "p001.txt"
        meta_path = cache_dir / "p001.json"
        self.assertTrue(txt_path.exists())
        self.assertTrue(meta_path.exists())
        meta = json.loads(meta_path.read_text(encoding="utf-8"))
        self.assertEqual(meta["page"], 1)
        self.assertEqual(meta["source"], "llamaparse")
        self.assertIn("sha256", meta)

        # 2. Second extraction: must hit disk cache without network requests
        initial_req_count = len(request_log)
        cached_pages = provider.extract_pages(pdf_path, [1], cache_dir=cache_dir)
        self.assertEqual(len(cached_pages), 1)
        self.assertEqual(cached_pages[0].text, pages[0].text)
        self.assertEqual(len(request_log), initial_req_count, "Cache hit must not make HTTP calls")

    def test_mock_transport_401_unauthorized(self) -> None:
        """Test 401 response raises user-safe LlamaParseError without exposing secrets."""
        pdf_bytes = _create_minimal_pdf(["Trang test"])
        pdf_path = self.base_dir / "test401.pdf"
        pdf_path.write_bytes(pdf_bytes)

        secret_key = "super-confidential-api-token-999"

        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(401, json={"detail": "Unauthorized token"})

        provider = LlamaParseProvider(
            api_key=secret_key,
            transport=httpx.MockTransport(handler),
            enable_fallback=False,
        )

        with self.assertRaises(LlamaParseError) as ctx:
            provider.extract_pages(pdf_path, [1])

        err_msg = str(ctx.exception)
        self.assertNotIn(secret_key, err_msg, "Secret API key must NEVER be leaked in errors")
        self.assertIn("không hợp lệ", err_msg)

    def test_mock_transport_429_rate_limit(self) -> None:
        """Test 429 response raises user-safe LlamaParseError."""
        pdf_bytes = _create_minimal_pdf(["Trang test"])
        pdf_path = self.base_dir / "test429.pdf"
        pdf_path.write_bytes(pdf_bytes)

        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(429, json={"detail": "Quota exceeded"})

        provider = LlamaParseProvider(
            api_key="mock-key",
            transport=httpx.MockTransport(handler),
            enable_fallback=False,
        )

        with self.assertRaises(LlamaParseError) as ctx:
            provider.extract_pages(pdf_path, [1])

        self.assertIn("hạn mức", str(ctx.exception))

    def test_mock_transport_500_retry_success(self) -> None:
        """Test 500 error triggers retry and succeeds on next attempt."""
        pdf_bytes = _create_minimal_pdf(["Trang test retry"])
        pdf_path = self.base_dir / "test500.pdf"
        pdf_path.write_bytes(pdf_bytes)

        call_count = 0

        def handler(request: httpx.Request) -> httpx.Response:
            nonlocal call_count
            call_count += 1
            if request.url.path == "/api/v2/parse/upload":
                if call_count == 1:
                    return httpx.Response(500, json={"error": "Internal server error"})
                return httpx.Response(200, json={"id": "job-retry-1"})
            if request.url.path == "/api/v2/parse/job-retry-1":
                return httpx.Response(
                    200,
                    json={
                        "job": {"status": "COMPLETED"},
                        "markdown": {"pages": [{"markdown": "Dong 1 | Dong 2"}]},
                    },
                )
            return httpx.Response(404)

        provider = LlamaParseProvider(
            api_key="mock-key",
            poll_interval_s=0.01,
            max_retries=2,
            transport=httpx.MockTransport(handler),
        )

        pages = provider.extract_pages(pdf_path, [1])
        self.assertEqual(len(pages), 1)
        self.assertIn("Dong 1 | Dong 2", pages[0].text)
        self.assertGreaterEqual(call_count, 2)

    def test_mock_transport_timeout(self) -> None:
        """Test poll timeout raises LlamaParseError."""
        pdf_bytes = _create_minimal_pdf(["Trang test timeout"])
        pdf_path = self.base_dir / "test_timeout.pdf"
        pdf_path.write_bytes(pdf_bytes)

        def handler(request: httpx.Request) -> httpx.Response:
            if request.url.path == "/api/v2/parse/upload":
                return httpx.Response(200, json={"id": "job-timeout-1"})
            return httpx.Response(200, json={"job": {"status": "RUNNING"}})

        provider = LlamaParseProvider(
            api_key="mock-key",
            timeout_s=0.05,
            poll_interval_s=0.02,
            transport=httpx.MockTransport(handler),
            enable_fallback=False,
        )

        with self.assertRaises(LlamaParseError) as ctx:
            provider.extract_pages(pdf_path, [1])

        self.assertIn("thời gian chờ", str(ctx.exception))

    def test_fallback_to_tesseract_when_configured(self) -> None:
        """Test fallback provider is invoked when LlamaParse encounters an error."""
        pdf_bytes = _create_minimal_pdf(["Trang test fallback"])
        pdf_path = self.base_dir / "test_fb.pdf"
        pdf_path.write_bytes(pdf_bytes)

        class StubTesseractProvider:
            def is_tesseract_available(self) -> bool:
                return True

            def extract_all_pages(self, pdf_path: Path, cache_dir: Path | None = None) -> list[PageInput]:
                return [PageInput(page_number=1, text="Text tu Tesseract fallback", source="ocr")]

        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(500, json={"error": "Down"})

        provider = LlamaParseProvider(
            api_key="mock-key",
            max_retries=0,
            transport=httpx.MockTransport(handler),
            tesseract_fallback=StubTesseractProvider(),  # type: ignore[arg-type]
        )

        pages = provider.extract_pages(pdf_path, [1])
        self.assertEqual(len(pages), 1)
        self.assertEqual(pages[0].source, "ocr")
        self.assertEqual(pages[0].text, "Text tu Tesseract fallback")

    def test_api_onboarding_llamaparse_flow(self) -> None:
        """Test full onboarding API endpoint with mocked LlamaParse provider on app state."""
        uploads_dir = self.base_dir / "user_uploads"
        uploads_dir.mkdir(parents=True, exist_ok=True)

        settings = Settings(
            _env_file=None,
            app_name="final-thesis-llamaparse-test",
            app_env="test",
            sqlite_db_path=":memory:",
            analysis_runs_db_path=str(self.base_dir / "runs.sqlite"),
            user_uploads_dir=str(uploads_dir),
            openai_api_key="test-key",
            planner_mode="rules_only",
            ocr_provider="llamaparse",
        )

        app = create_app(settings)
        app.state.filing_sync_execution = True

        class MockLlamaProvider:
            def __init__(self) -> None:
                self.total_pages_sent = 3

            def get_page_count(self, pdf_path: Path) -> int:
                return 3

            def render_page_png(self, pdf_path: Path, page_number: int, dpi: int = 120, cache_path: Path | None = None) -> bytes:
                return b"fake-png"

            def extract_all_pages(self, pdf_path: Path, cache_dir: Path | None = None, max_workers: int = 4, progress_callback: Any = None) -> list[PageInput]:
                return [
                    PageInput(
                        page_number=1,
                        text="BAO CAO TINH HINH TAI CHINH HOP NHAT\nDon vi tinh: trieu dong\nTong tai san | 100.000.000 | 80.000.000\nTong von chu so huu | 10.000.000 | 8.000.000\nCho vay khach hang | 60.000.000 | 50.000.000\nDu phong rui ro cho vay | (1.000.000) | (800.000)",
                        source="llamaparse",
                    ),
                    PageInput(
                        page_number=2,
                        text="BAO CAO KET QUA HOAT DONG KINH DOANH HOP NHAT\nDon vi: trieu dong\nThu nhap lai thuan | 5.000.000 | 4.000.000\nLoi nhuan sau thue | 2.000.000 | 1.600.000\nCo dong cua Ngan hang | 1.900.000 | 1.500.000",
                        source="llamaparse",
                    ),
                    PageInput(
                        page_number=3,
                        text="THUYET MINH PHAN LOAI NO THEO CHAT LUONG NO\nDon vi: trieu dong\nNo du tieu chuan | 58.000.000 | 48.000.000\nNo can chu y | 1.000.000 | 1.000.000\nNo duoi tieu chuan | 300.000 | 250.000\nNo nghi ngo | 300.000 | 350.000\nNo co kha nang mat von | 400.000 | 400.000",
                        source="llamaparse",
                    ),
                ]

        app.state.filing_page_provider = MockLlamaProvider()

        client = TestClient(app)
        pdf_bytes = _create_minimal_pdf(["P1", "P2", "P3"])

        resp = client.post(
            "/api/onboarding/filings",
            files={"file": ("test_llama.pdf", io.BytesIO(pdf_bytes), "application/pdf")},
            data={
                "entity_id": "ACB",
                "display_name": "Ngân hàng TMCP Á Châu",
                "fiscal_year": 2025,
                "reporting_scope": "consolidated",
            },
        )
        self.assertEqual(resp.status_code, 202)
        body = resp.json()
        filing_id = body["filing_id"]

        detail_resp = client.get(f"/api/onboarding/filings/{filing_id}")
        self.assertEqual(detail_resp.status_code, 200)
        detail = detail_resp.json()

        self.assertEqual(detail["status"], "ready")
        self.assertEqual(detail["ocr_provider"], "llamaparse")
        self.assertEqual(len(detail["rows"]), 20)
        # Verify limitations note mentions pages sent to OCR
        limitations = detail.get("limitations_vi")
        self.assertTrue(
            any("Đã gửi 3 trang tới dịch vụ OCR" in str(item) for item in (limitations if isinstance(limitations, list) else [limitations]))
        )


if __name__ == "__main__":
    unittest.main()
