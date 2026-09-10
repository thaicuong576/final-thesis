import tempfile
import unittest
from pathlib import Path

import fitz

from thesis_data.documents import extract_evidence, inspect_document
from thesis_data.query import EvidenceQuery


class DocumentEvidenceTests(unittest.TestCase):
    def create_text_pdf(self, root: Path) -> Path:
        path = root / "VCB_2024_Q1.pdf"
        document = fitz.open()
        page = document.new_page()
        page.insert_text((72, 72), "VCB 2024_Q1\nNPL group 3-5 was 2.5 percent.")
        document.new_page()
        document.save(path)
        document.close()
        return path

    def create_blank_pdf(self, root: Path) -> Path:
        path = root / "scanned.pdf"
        document = fitz.open()
        document.new_page()
        document.save(path)
        document.close()
        return path

    def test_inspect_document_reports_text_layer_and_hash(self):
        with tempfile.TemporaryDirectory() as directory:
            path = self.create_text_pdf(Path(directory))

            quality = inspect_document(path)

        self.assertEqual(quality.page_count, 2)
        self.assertEqual(quality.text_layer_pages, 1)
        self.assertEqual(quality.empty_pages, 1)
        self.assertEqual(quality.parser_status, "mixed_text_layer")
        self.assertEqual(len(quality.content_hash), 64)
        self.assertIsNone(quality.hash_match)

    def test_inspect_document_marks_no_text_layer(self):
        with tempfile.TemporaryDirectory() as directory:
            quality = inspect_document(self.create_blank_pdf(Path(directory)))

        self.assertEqual(quality.parser_status, "no_text_layer")
        self.assertFalse(quality.has_text_layer)
        self.assertEqual(quality.extraction_errors, [])

    def test_extract_evidence_is_page_aware_and_source_bound(self):
        with tempfile.TemporaryDirectory() as directory:
            snippets = extract_evidence(
                self.create_text_pdf(Path(directory)),
                EvidenceQuery(
                    source_id="source-vcb-2024",
                    ticker="VCB",
                    period="2024_Q1",
                    text="NPL",
                ),
            )

        self.assertEqual(len(snippets), 1)
        self.assertEqual(snippets[0].source_id, "source-vcb-2024")
        self.assertEqual(snippets[0].page_number, 1)
        self.assertEqual(snippets[0].parser_status, "text_layer")
        self.assertTrue(snippets[0].is_paginated)

    def test_extract_evidence_rejects_missing_source_identity(self):
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaisesRegex(ValueError, "source_id"):
                extract_evidence(
                    self.create_text_pdf(Path(directory)),
                    EvidenceQuery(ticker="VCB", period="2024_Q1", text="NPL"),
                )


if __name__ == "__main__":
    unittest.main()
