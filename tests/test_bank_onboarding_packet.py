from __future__ import annotations

import csv
import json
from pathlib import Path
import sqlite3
import tempfile
import unittest

from pydantic import ValidationError

from thesis_data.analysis_request import AnalysisRequest
from thesis_data.bank_onboarding import (
    build_bank_dataset_candidate,
    parse_bank_onboarding_packet,
    verify_packet_artifacts,
)
from thesis_data.canonical_snapshot import materialize_canonical_snapshot
from thesis_data.canonical_sqlite_provider import CanonicalSqliteDatasetProvider
from thesis_data.dataset_provider import DatasetProviderError
from thesis_data.gold_dataset_provider import GoldSqliteDatasetProvider
from thesis_data.onboarding_contract import demo_metric_registry
from thesis_data.storage import create_gold_snapshot_schema
from thesis_data.transferability import run_metric_probe
from thesis_data.schema import QualityStatus


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
PACKET_PATH = REPOSITORY_ROOT / "data" / "onboarding" / "ctg-2024-audited-2024q4-v1.json"
SOURCE_MANIFEST_PATH = PACKET_PATH.with_name(PACKET_PATH.stem + "-source-manifest.json")
RECONCILIATION_PATH = PACKET_PATH.with_name(PACKET_PATH.stem + "-reconciliation.csv")


class BankOnboardingPacketTests(unittest.TestCase):
    def load_packet(self):
        packet = parse_bank_onboarding_packet(PACKET_PATH.read_bytes())
        paths, details = verify_packet_artifacts(
            packet,
            packet_path=PACKET_PATH,
            source_manifest_path=SOURCE_MANIFEST_PATH,
        )
        candidate, raw_descriptor, report = build_bank_dataset_candidate(
            packet,
            artifact_paths=paths,
            artifact_details=details,
        )
        return packet, candidate, raw_descriptor, report

    @staticmethod
    def request(provider, entity_id: str, metric_id: str, period_id: str = "2024_Q4"):
        ref = provider.current_dataset_ref()
        request = AnalysisRequest(
            request_id=f"transferability-{entity_id}-{metric_id}",
            dataset_id=ref.dataset_id,
            dataset_snapshot_id=ref.dataset_snapshot_id,
            target_entity_ids=(entity_id,),
            period_ids=(period_id,),
            metric_ids=(metric_id,),
            objective="Read one accepted provider-neutral bank metric.",
        )
        return ref, request

    def test_ctg_packet_materializes_and_resolves_all_primary_metrics_with_source_lineage(self):
        packet, candidate, raw_descriptor, report = self.load_packet()
        self.assertEqual(report.status.value, "VALID")
        self.assertEqual(candidate.metadata.status.value, "candidate")
        self.assertEqual(
            {item.metric_id for item in candidate.metrics if item.metric_id in {
                "bank.npl_g35", "bank.llr_coverage", "bank.roa", "bank.roe"
            }},
            {"bank.npl_g35", "bank.llr_coverage", "bank.roa", "bank.roe"},
        )

        with tempfile.TemporaryDirectory() as directory:
            db_path = Path(directory) / "ctg-canonical.sqlite"
            accepted = materialize_canonical_snapshot(
                db_path, candidate, raw_descriptor, report
            )
            provider = CanonicalSqliteDatasetProvider(db_path, dataset_id=packet.dataset_id)
            ref = provider.current_dataset_ref()
            self.assertEqual(ref.dataset_snapshot_id, accepted.dataset_snapshot_id)
            resolved = {}
            for metric_id in ("bank.npl_g35", "bank.llr_coverage", "bank.roa", "bank.roe"):
                scoped_ref, request = self.request(provider, "CTG", metric_id)
                observation = run_metric_probe(
                    provider,
                    scoped_ref,
                    request,
                    entity_id="CTG",
                    period_id="2024_Q4",
                    metric_id=metric_id,
                )
                resolved[metric_id] = observation
                self.assertIsNotNone(observation)
                self.assertEqual(observation.validation_status, QualityStatus.VALID)
                self.assertEqual(observation.period_basis, "point_in_time" if metric_id in {
                    "bank.npl_g35", "bank.llr_coverage"
                } else "ttm")
                self.assertEqual(observation.reporting_scope, "consolidated")
                self.assertTrue(observation.source_locator.startswith("pdf_page="))
                self.assertEqual(observation.review.decision, "reproduced_derived_value")
                source = provider.get_source(ref, observation.source_ref)
                self.assertEqual(source.validation_status, QualityStatus.VALID)
                self.assertEqual(source.source_tier, "primary")
                evidence = provider.get_evidence(
                    ref,
                    (observation.source_ref,),
                    entity_id="CTG",
                    period_id="2024_Q4",
                    metric_id=metric_id,
                )
                self.assertEqual(len(evidence), 1)
                self.assertEqual(evidence[0].locator, observation.source_locator)
                self.assertTrue(evidence[0].quote)
                for input_id in observation.input_observation_ids:
                    source_input = provider.resolve_observation(ref, input_id)
                    self.assertIsNotNone(source_input)
                    self.assertEqual(source_input.validation_status, QualityStatus.VALID)
                    self.assertTrue(source_input.source_locator)
                    self.assertIsNotNone(source_input.review)

        self.assertAlmostEqual(resolved["bank.npl_g35"].value, 1.2190, places=4)
        self.assertAlmostEqual(resolved["bank.llr_coverage"].value, 174.6762, places=4)
        self.assertEqual(resolved["bank.roa"].value, 1.1536)
        self.assertEqual(resolved["bank.roe"].value, 18.6012)

    def test_packet_artifact_manifest_fails_closed_on_byte_or_hash_mismatch(self):
        packet = parse_bank_onboarding_packet(PACKET_PATH.read_bytes())
        manifest = json.loads(SOURCE_MANIFEST_PATH.read_text(encoding="utf-8"))
        source_id = packet.sources[0].source_id
        with tempfile.TemporaryDirectory() as directory:
            changed_manifest = Path(directory) / "manifest.json"
            manifest["artifacts"][source_id]["byte_length"] += 1
            changed_manifest.write_text(json.dumps(manifest), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "byte length"):
                verify_packet_artifacts(
                    packet,
                    packet_path=PACKET_PATH,
                    source_manifest_path=changed_manifest,
                )
            manifest["artifacts"][source_id]["byte_length"] -= 1
            manifest["artifacts"][source_id]["content_sha256"] = "0" * 64
            changed_manifest.write_text(json.dumps(manifest), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "content hash"):
                verify_packet_artifacts(
                    packet,
                    packet_path=PACKET_PATH,
                    source_manifest_path=changed_manifest,
                )

    def test_reconciliation_register_covers_packet_reviews_and_ttm_basis(self):
        packet = json.loads(PACKET_PATH.read_text(encoding="utf-8"))
        manifest = json.loads(SOURCE_MANIFEST_PATH.read_text(encoding="utf-8"))
        source_id = packet["sources"][0]["source_id"]
        artifact = manifest["artifacts"][source_id]
        with RECONCILIATION_PATH.open(encoding="utf-8-sig", newline="") as stream:
            rows = {row["observation_id"]: row for row in csv.DictReader(stream)}

        self.assertEqual(set(rows), {item["observation_id"] for item in packet["observations"]})
        for item in packet["observations"]:
            row = rows[item["observation_id"]]
            self.assertEqual(row["value"], str(item["value"]))
            self.assertEqual(row["unit"], item["unit"])
            self.assertEqual(row["period_id"], item["period_id"])
            self.assertEqual(row["period_basis"], item["period_basis"])
            self.assertEqual(row["reporting_scope"], item["reporting_scope"])
            self.assertEqual(row["formula_version"], item.get("formula", {}).get("formula_version", ""))
            self.assertEqual(row["reviewer_id"], item["review"]["reviewer_id"])
            self.assertEqual(row["reviewed_at"], item["review"]["reviewed_at"])
            self.assertEqual(row["source_sha256"], artifact["content_sha256"])
            self.assertEqual(row["source_url"], artifact["source_url"])
        self.assertEqual(rows["ctg-bank-roa-2024q4"]["period_basis"], "ttm")
        self.assertEqual(rows["ctg-bank-roe-2024q4"]["period_basis"], "ttm")

    def test_packet_rejects_wrong_unit_scope_and_unresolved_formula_inputs(self):
        payload = json.loads(PACKET_PATH.read_text(encoding="utf-8"))
        npl = next(item for item in payload["observations"] if item["metric_id"] == "bank.npl_g35")
        npl["unit"] = "ratio"
        with self.assertRaises(ValidationError):
            parse_bank_onboarding_packet(json.dumps(payload).encode("utf-8"))

        payload = json.loads(PACKET_PATH.read_text(encoding="utf-8"))
        roa = next(item for item in payload["observations"] if item["metric_id"] == "bank.roa")
        roa["reporting_scope"] = "unknown"
        with self.assertRaises(ValidationError):
            parse_bank_onboarding_packet(json.dumps(payload).encode("utf-8"))

        payload = json.loads(PACKET_PATH.read_text(encoding="utf-8"))
        npl = next(item for item in payload["observations"] if item["metric_id"] == "bank.npl_g35")
        npl["period_id"] = "2024-Q4"
        with self.assertRaisesRegex(ValidationError, "period_id"):
            parse_bank_onboarding_packet(json.dumps(payload).encode("utf-8"))

        payload = json.loads(PACKET_PATH.read_text(encoding="utf-8"))
        npl = next(item for item in payload["observations"] if item["metric_id"] == "bank.npl_g35")
        npl["formula"]["input_observation_ids"][0] = "unresolved-input"
        with self.assertRaisesRegex(ValidationError, "does not resolve"):
            parse_bank_onboarding_packet(json.dumps(payload).encode("utf-8"))

    def test_unavailable_metric_remains_explicit_missing_in_provider(self):
        payload = json.loads(PACKET_PATH.read_text(encoding="utf-8"))
        coverage = next(item for item in payload["observations"] if item["metric_id"] == "bank.llr_coverage")
        coverage.update({
            "value": None,
            "unit": None,
            "period_basis": None,
            "reporting_scope": "unknown",
            "quality_status": "missing",
            "reason": "SOURCE_NOT_VERIFIABLE",
        })
        for key in ("candidate_source_id", "candidate_locator", "review", "formula"):
            coverage.pop(key, None)
        packet = parse_bank_onboarding_packet(json.dumps(payload).encode("utf-8"))
        paths, details = verify_packet_artifacts(
            packet,
            packet_path=PACKET_PATH,
            source_manifest_path=SOURCE_MANIFEST_PATH,
        )
        candidate, raw_descriptor, report = build_bank_dataset_candidate(
            packet, artifact_paths=paths, artifact_details=details
        )
        with tempfile.TemporaryDirectory() as directory:
            db_path = Path(directory) / "explicit-missing.sqlite"
            materialize_canonical_snapshot(db_path, candidate, raw_descriptor, report)
            provider = CanonicalSqliteDatasetProvider(db_path)
            ref, request = self.request(provider, "CTG", "bank.llr_coverage")
            observation = run_metric_probe(
                provider,
                ref,
                request,
                entity_id="CTG",
                period_id="2024_Q4",
                metric_id="bank.llr_coverage",
            )
        self.assertIsNone(observation.value)
        self.assertEqual(observation.validation_status, QualityStatus.MISSING)
        self.assertEqual(observation.missing_reason, "SOURCE_NOT_VERIFIABLE")

    def test_gold_acb_2024_q4_metric_locator_survives_provider_and_shared_probe(self):
        with tempfile.TemporaryDirectory() as directory:
            gold_path = Path(directory) / "gold.sqlite"
            create_gold_snapshot_schema(gold_path)
            connection = sqlite3.connect(gold_path)
            connection.execute(
                "INSERT INTO snapshot_metadata VALUES (?, ?, ?, ?)",
                ("gold-v5-fixture", "2026-09-24T00:00:00Z", "gold", "{}"),
            )
            connection.execute(
                "INSERT INTO source_records VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    "source-acb-fy24", "filing", "primary", "https://example.test/acb.pdf",
                    "2026-09-24T00:00:00Z", "ignored/local/path.pdf", "fixture-hash", "ACB",
                    "fixture", "valid", None,
                ),
            )
            connection.execute(
                "INSERT INTO metric_observations VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    "observation-acb-roa-2024q4", "ACB", "banking", "bank.roa", 1.24,
                    "percent", "2024_Q4", "2024-12-31", "ttm", "source-acb-fy24",
                    "pdf_page=18; printed_page=16; audited financial highlights / ROA row",
                    "valid", None,
                ),
            )
            connection.commit()
            connection.close()

            provider = GoldSqliteDatasetProvider(gold_path, dataset_id="gold-v5")
            ref, request = self.request(provider, "ACB", "bank.roa")
            observation = run_metric_probe(
                provider,
                ref,
                request,
                entity_id="ACB",
                period_id="2024_Q4",
                metric_id="bank.roa",
            )
            source = provider.get_source(ref, observation.source_ref)

        self.assertEqual(observation.source_locator, "pdf_page=18; printed_page=16; audited financial highlights / ROA row")
        self.assertEqual(observation.period_basis, "ttm")
        self.assertIsNone(observation.reporting_scope)
        self.assertEqual(source.validation_status, QualityStatus.VALID)

    def test_bank_onboarding_registry_uses_dictionary_metric_ids(self):
        registry = demo_metric_registry()
        self.assertIsNotNone(registry.get("bank.npl_g35"))
        self.assertIsNotNone(registry.get("bank.llr_coverage"))
        self.assertIsNotNone(registry.get("bank.roa"))
        self.assertIsNotNone(registry.get("bank.roe"))
        self.assertIsNone(registry.get("company.roa"))


if __name__ == "__main__":
    unittest.main()
