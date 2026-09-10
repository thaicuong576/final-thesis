import sqlite3
import tempfile
import unittest
from pathlib import Path

from thesis_data.normalize import normalize_vendor_snapshot
from thesis_data.storage import create_gold_snapshot_schema


class VendorNormalizationTests(unittest.TestCase):
    def create_staging_fixture(self, root: Path) -> Path:
        path = root / "staging.sqlite"
        connection = sqlite3.connect(path)
        connection.executescript(
            """
            CREATE TABLE source_records (
                source_id TEXT,
                source_type TEXT,
                publisher TEXT,
                source_url TEXT,
                retrieved_at_utc TEXT,
                local_path TEXT,
                content_hash TEXT,
                bytes INTEGER,
                quality_status TEXT,
                notes TEXT
            );
            INSERT INTO source_records VALUES
                ('vci_ratio-VCB', 'vci_ratio', 'vendor',
                 'https://example.test/ratio', '2026-09-04T00:00:00Z',
                 'data/ratio.json', 'sha256:ratio', 100, 'retrieved_pending_validation', NULL);
            CREATE TABLE ratio_observations (
                id TEXT,
                ticker TEXT,
                sector TEXT,
                period TEXT,
                ratio_type TEXT,
                source_period_year INTEGER,
                source_period_quarter INTEGER,
                field_code TEXT,
                value REAL,
                unit TEXT,
                source_id TEXT,
                source_locator TEXT,
                quality_status TEXT
            );
            INSERT INTO ratio_observations VALUES
                ('ratio-1', 'VCB', 'bank', '2024_Q1', 'RATIO_TTM',
                 2024, 1, 'npl', 0.0125,
                 'vendor_ratio_decimal_or_native', 'vci_ratio-VCB',
                 'data[29].npl', 'retrieved_pending_validation');
            INSERT INTO ratio_observations VALUES
                ('ratio-outside', 'ACB', 'bank', '2024_Q1', 'RATIO_TTM',
                 2024, 1, 'npl', 0.02,
                 'vendor_ratio_decimal_or_native', 'vci_ratio-VCB',
                 'data[29].npl', 'retrieved_pending_validation');
            """
        )
        connection.commit()
        connection.close()
        return path

    def test_normalization_preserves_vendor_uncertainty(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            output = root / "normalized.sqlite"
            count = normalize_vendor_snapshot(
                self.create_staging_fixture(root),
                output,
                tickers=("VCB",),
                periods=("2024_Q1",),
            )

            connection = sqlite3.connect(output)
            source = connection.execute(
                "SELECT source_tier, quality_status FROM source_records"
            ).fetchone()
            metric = connection.execute(
                "SELECT ticker, metric, value, unit, period_basis, quality_status, reason "
                "FROM metric_observations"
            ).fetchone()
            connection.close()

        self.assertEqual(count, 1)
        self.assertEqual(source, ("accelerator", "pending_validation"))
        self.assertEqual(metric[0:3], ("VCB", "bank.npl_g35", 0.0125))
        self.assertEqual(metric[3], "vendor_ratio_decimal_or_native")
        self.assertEqual(metric[4:6], ("ttm", "pending_validation"))
        self.assertIn("pending", metric[6])

    def test_normalization_does_not_overwrite_output(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            staging = self.create_staging_fixture(root)
            output = root / "normalized.sqlite"
            output.write_text("keep", encoding="utf-8")

            with self.assertRaises(FileExistsError):
                normalize_vendor_snapshot(
                    staging,
                    output,
                    tickers=("VCB",),
                    periods=("2024_Q1",),
                )


if __name__ == "__main__":
    unittest.main()
