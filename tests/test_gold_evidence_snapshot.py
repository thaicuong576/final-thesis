import json
import sqlite3
import unittest
from pathlib import Path

from scripts.build_gold_evidence_snapshot import _first_pdf_page


ROOT = Path(__file__).resolve().parents[1]


class GoldEvidenceSnapshotTests(unittest.TestCase):
    def test_first_pdf_page_parses_common_locators(self):
        self.assertEqual(_first_pdf_page("pdf_page:17;printed_page:15"), 17)
        self.assertEqual(_first_pdf_page("pdf_pages:3_and_1;formula:ttm"), 3)
        self.assertEqual(_first_pdf_page("pdf:p46:printed:p44"), 46)
        self.assertEqual(_first_pdf_page("PDF p.3-4 consolidated balance sheet"), 3)
        self.assertIsNone(_first_pdf_page("html:article_body:p7"))

    def test_v5_artifact_has_complete_valid_cell_evidence(self):
        db = ROOT / "data/processed/gold-bank-2025-expanded-v5-evidence.sqlite"
        audit_path = ROOT / "reports/data-foundation/gold-bank-2025-expanded-v5-evidence.json"
        self.assertTrue(db.exists())
        audit = json.loads(audit_path.read_text(encoding="utf-8"))
        self.assertEqual(audit["valid_observations"], 76)
        self.assertEqual(audit["valid_with_new_evidence"], 76)
        connection = sqlite3.connect(f"file:{db.resolve()}?mode=ro", uri=True)
        try:
            self.assertEqual(
                connection.execute("SELECT snapshot_id FROM snapshot_metadata").fetchone()[0],
                "gold-bank-2025-expanded-v5-evidence",
            )
            self.assertEqual(
                connection.execute(
                    "SELECT COUNT(*) FROM evidence_snippets WHERE parser_status='human_reviewed_derivation_note'"
                ).fetchone()[0],
                76,
            )
        finally:
            connection.close()


if __name__ == "__main__":
    unittest.main()
