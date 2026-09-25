import hashlib
import json
from pathlib import Path
import sqlite3
import tempfile
import unittest

from thesis_data.dataset_contract import CanonicalObservation, DatasetRef, QualityStatus
from thesis_data.dataset_provider import DatasetProviderError, aggregate_peer_median
from thesis_data.gold_dataset_provider import GoldSqliteDatasetProvider
from thesis_data.gold_scope_authority import (
    VerifiedGoldObservationScopeAuthority,
    canonical_lf_utf8_sha256,
)
from thesis_data.storage import create_gold_snapshot_schema


class GoldScopeAuthorityTests(unittest.TestCase):
    def create_snapshot(self, root: Path) -> tuple[Path, DatasetRef]:
        db_path = root / "gold.sqlite"
        create_gold_snapshot_schema(db_path)
        connection = sqlite3.connect(db_path)
        try:
            connection.execute(
                "INSERT INTO snapshot_metadata VALUES (?, ?, ?, ?)",
                ("gold-fixture-v1", "2026-09-25T00:00:00Z", "gold", "{}"),
            )
            connection.executemany(
                "INSERT INTO source_records VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    ("source-a", "filing", "primary", "https://example.test/a", "2026-09-25", "a.pdf", "hash-a", "A", "public", "valid", None),
                    ("source-b", "filing", "primary", "https://example.test/b", "2026-09-25", "b.pdf", "hash-b", "B", "public", "valid", None),
                ),
            )
            connection.executemany(
                "INSERT INTO metric_observations VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    ("obs-a", "entity-a", "bank", "company.roa", 1.0, "percent", "FY-2024-Q4", "2024-12-31", "ttm", "source-a", "page:1;table:roa", "valid", None),
                    ("obs-b", "entity-b", "bank", "company.roa", 3.0, "percent", "FY-2024-Q4", "2024-12-31", "ttm", "source-b", "page:2;table:roa", "valid", None),
                    ("obs-c-missing", "entity-c", "bank", "company.roa", None, None, "FY-2024-Q4", None, None, None, None, "missing", "SOURCE_UNAVAILABLE"),
                ),
            )
            connection.commit()
        finally:
            connection.close()
        return db_path, DatasetRef(
            dataset_id="gold-fixture",
            dataset_snapshot_id="gold-fixture-v1",
        )

    def write_authority(
        self,
        db_path: Path,
        root: Path,
        *,
        mutate=None,
    ) -> VerifiedGoldObservationScopeAuthority:
        connection = sqlite3.connect(f"file:{db_path.as_posix()}?mode=ro", uri=True)
        try:
            connection.row_factory = sqlite3.Row
            rows = connection.execute(
                """
                SELECT observation_id,ticker,period,metric,value,unit,period_basis,
                       source_id,source_locator
                FROM metric_observations WHERE quality_status='valid'
                ORDER BY ticker
                """
            ).fetchall()
        finally:
            connection.close()
        entries = []
        for row, checker in zip(
            rows,
            (("checker-a", "checker-b"), ("checker-c", "checker-d")),
        ):
            entries.append(
                {
                    "observation_id": row["observation_id"],
                    "review_target_id": f"{row['ticker']}:{row['period']}:{row['metric']}",
                    "entity_id": row["ticker"],
                    "period_id": row["period"],
                    "metric_id": row["metric"],
                    "value": row["value"],
                    "unit": row["unit"],
                    "period_basis": row["period_basis"],
                    "source_ref": row["source_id"],
                    "source_locator": row["source_locator"],
                    "reporting_scope": "consolidated",
                    "review_status": "accepted",
                    "checker_ids": list(checker),
                    "checker_scope_confirmations": ["consolidated", "consolidated"],
                    "adjudicator_id": "review-lead",
                }
            )
        payload = {
            "schema_version": "gold-observation-scope-authority-v1",
            "authority_id": "gold-fixture-scope-v1",
            "authority_ref": "scope-authority.json",
            "dataset_id": "gold-fixture",
            "snapshot_id": "gold-fixture-v1",
            "gold_snapshot_sha256": hashlib.sha256(db_path.read_bytes()).hexdigest(),
            "source_review_ledger_ref": "review-ledger.csv",
            "source_review_ledger_raw_file_bytes_sha256": "c" * 64,
            "source_authority_manifest_ref": "authority-manifest.json",
            "source_authority_manifest_canonical_lf_utf8_sha256": "b" * 64,
            "authority_refs": ["docs/DECISIONS.md#D-063", "docs/DECISIONS.md#D-072"],
            "entries": entries,
        }
        if mutate is not None:
            mutate(payload)
        path = root / "scope-authority.json"
        path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8", newline="\n")
        return VerifiedGoldObservationScopeAuthority.load(
            path,
            expected_canonical_sha256=canonical_lf_utf8_sha256(path),
        )

    def test_scope_authority_binds_direct_and_peer_observations_and_preserves_missingness(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            db_path, ref = self.create_snapshot(root)
            authority = self.write_authority(db_path, root)
            provider = GoldSqliteDatasetProvider(
                db_path,
                dataset_id="gold-fixture",
                scope_authority=authority,
            )

            direct = provider.get_metric(ref, "entity-a", "FY-2024-Q4", "company.roa")
            missing = provider.get_metric(ref, "entity-c", "FY-2024-Q4", "company.roa")
            benchmark = provider.get_peer_benchmark(
                ref,
                "sector:bank",
                "FY-2024-Q4",
                ("company.roa",),
            )[0]

        self.assertEqual(direct.reporting_scope, "consolidated")
        self.assertEqual(
            direct.metadata["reporting_scope_authority"]["authority_canonical_lf_utf8_sha256"],
            authority.canonical_sha256,
        )
        self.assertEqual(direct.metadata["reporting_scope_authority"]["review_status"], "accepted")
        self.assertIsNone(missing.reporting_scope)
        self.assertEqual(missing.missing_reason, "SOURCE_UNAVAILABLE")
        self.assertEqual(benchmark.reporting_scope, "consolidated")
        self.assertEqual(benchmark.metadata["requested_denominator"], 3)
        self.assertEqual(benchmark.metadata["eligible_denominator"], 2)
        self.assertEqual(set(benchmark.input_observation_ids), {"obs-a", "obs-b"})
        self.assertEqual(benchmark.metadata["member_observation_ids"], ["obs-a", "obs-b", "obs-c-missing"])
        self.assertEqual(
            benchmark.metadata["missing_members"],
            [
                {
                    "entity_id": "entity-c",
                    "observation_id": "obs-c-missing",
                    "validation_status": "missing",
                    "reason": "SOURCE_UNAVAILABLE",
                }
            ],
        )
        self.assertEqual(
            benchmark.metadata["peer_member_observations"][0]["scope_authority"]["authority_ref"],
            "scope-authority.json",
        )

    def test_peer_median_records_absent_member_and_rejects_incompatible_inputs(self):
        ref = DatasetRef(dataset_id="peer-test", dataset_snapshot_id="snapshot-1")

        def observation(
            entity_id: str,
            *,
            unit: str = "percent",
            period_basis: str = "ttm",
            reporting_scope: str | None = "consolidated",
        ) -> CanonicalObservation:
            return CanonicalObservation(
                observation_id=f"obs-{entity_id}",
                dataset_id=ref.dataset_id,
                dataset_snapshot_id=ref.dataset_snapshot_id,
                entity_id=entity_id,
                period_id="FY-2024-Q4",
                metric_id="company.roa",
                value=1.0,
                unit=unit,
                source_ref=f"source-{entity_id}",
                validation_status=QualityStatus.VALID,
                period_basis=period_basis,
                reporting_scope=reporting_scope,
            )

        benchmark = aggregate_peer_median(
            dataset_ref=ref,
            peer_universe_id="bank-peers",
            period_id="FY-2024-Q4",
            metric_id="company.roa",
            peer_entity_ids=("entity-a", "entity-b"),
            member_observations=(observation("entity-a"),),
        )
        self.assertEqual(benchmark.metadata["requested_denominator"], 2)
        self.assertEqual(benchmark.metadata["eligible_denominator"], 1)
        self.assertEqual(
            benchmark.metadata["missing_members"][0]["reason"],
            "NO_OBSERVATION_FOUND",
        )

        incompatible_inputs = (
            ("units", {"unit": "ratio"}, "incompatible units"),
            ("period bases", {"period_basis": "point_in_time"}, "incompatible period bases"),
            ("reporting scopes", {"reporting_scope": None}, "incompatible reporting scopes"),
        )
        for name, updates, message in incompatible_inputs:
            with self.subTest(name=name):
                members = (
                    observation("entity-a"),
                    observation("entity-b", **updates),
                )
                with self.assertRaisesRegex(DatasetProviderError, message):
                    aggregate_peer_median(
                        dataset_ref=ref,
                        peer_universe_id="bank-peers",
                        period_id="FY-2024-Q4",
                        metric_id="company.roa",
                        peer_entity_ids=("entity-a", "entity-b"),
                        member_observations=members,
                    )

    def test_scope_authority_requires_expected_hash(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            db_path, _ = self.create_snapshot(root)
            authority = self.write_authority(db_path, root)
            with self.assertRaisesRegex(ValueError, "SHA-256"):
                VerifiedGoldObservationScopeAuthority.load(
                    root / "scope-authority.json",
                    expected_canonical_sha256="0" * 64,
                )
            self.assertEqual(authority.authority.dataset_id, "gold-fixture")

    def test_scope_authority_rejects_gold_hash_identity_unknown_id_and_value_mismatches(self):
        mutations = (
            (
                "gold hash",
                lambda payload: payload.update({"gold_snapshot_sha256": "0" * 64}),
                "Gold SQLite SHA-256 mismatch",
            ),
            (
                "dataset identity",
                lambda payload: payload.update({"dataset_id": "different-dataset"}),
                "dataset_id mismatch",
            ),
            (
                "snapshot identity",
                lambda payload: payload.update({"snapshot_id": "different-snapshot"}),
                "snapshot_id mismatch",
            ),
            (
                "unknown observation ID",
                lambda payload: payload["entries"][0].update({"observation_id": "not-in-gold"}),
                "observation IDs do not exactly match",
            ),
            (
                "conflicting value",
                lambda payload: payload["entries"][0].update({"value": 9.9}),
                "conflicts with a Gold observation",
            ),
        )
        for name, mutate, message in mutations:
            with self.subTest(name=name), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                db_path, ref = self.create_snapshot(root)
                authority = self.write_authority(db_path, root, mutate=mutate)
                provider = GoldSqliteDatasetProvider(
                    db_path,
                    dataset_id="gold-fixture",
                    scope_authority=authority,
                )
                with self.assertRaisesRegex(DatasetProviderError, message):
                    provider.get_capabilities(ref)


if __name__ == "__main__":
    unittest.main()
