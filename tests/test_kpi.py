import tempfile
import unittest
from pathlib import Path

import fitz

from thesis_data.kpi import extract_tcb_fy24_evidence, extract_tcb_fy24_kpis


class KpiExtractionTests(unittest.TestCase):
    def create_fixture(self, root: Path) -> Path:
        path = root / "tcb.pdf"
        document = fitz.open()
        page = document.new_page()
        page.insert_text(
            (30, 30),
            """4Q24 Financial Highlights (1/3)
Balance Sheet
NPL
%
1.00%
1.10%
1.20%
1.30%
1.40%
Coverage ratio
%
90.0%
91.0%
92.0%
93.0%
94.0%
CIR
%
30.0%
31.0%
32.0%
33.0%
34.0%
ROA (LTM)
%
2.0%
2.1%
2.2%
2.3%
2.4%
ROE (LTM)
%
14.0%
14.1%
14.2%
14.3%
14.4%
""",
        )
        document.save(path)
        document.close()
        return path

    def test_extracts_four_periods_and_preserves_pending_status(self):
        with tempfile.TemporaryDirectory() as directory:
            observations = extract_tcb_fy24_kpis(
                self.create_fixture(Path(directory)),
                "source-tcb",
            )

        self.assertEqual(len(observations), 20)
        npl_q1 = next(item for item in observations if item.metric == "bank.npl_g35" and item.period == "2024_Q1")
        roe_q4 = next(item for item in observations if item.metric == "bank.roe" and item.period == "2024_Q4")
        self.assertEqual(npl_q1.value, 1.1)
        self.assertEqual(roe_q4.value, 14.4)
        self.assertEqual(npl_q1.quality_status.value, "pending_validation")
        self.assertIn("group 3-5", npl_q1.reason)
        self.assertIn("page:", npl_q1.source_locator)

    def test_evidence_is_page_aware_and_contains_the_source_row(self):
        with tempfile.TemporaryDirectory() as directory:
            snippets = extract_tcb_fy24_evidence(
                self.create_fixture(Path(directory)),
                "source-tcb",
            )

        self.assertEqual(len(snippets), 5)
        coverage = next(item for item in snippets if "Coverage ratio" in item.quote)
        self.assertEqual(coverage.page_number, 1)
        self.assertTrue(coverage.is_paginated)
        self.assertIn("1Q24", coverage.quote)
        self.assertEqual(coverage.parser_status, "text_layer_table_row")


if __name__ == "__main__":
    unittest.main()
