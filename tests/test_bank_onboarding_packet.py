from __future__ import annotations

import csv
from dataclasses import replace
from decimal import Decimal
import json
from pathlib import Path
import sqlite3
import tempfile
import unittest

from pydantic import ValidationError

from thesis_data.analysis_request import AnalysisRequest
from thesis_data.acceptance import validate_stage1_claims
from thesis_data.acceptance_resolver import ProviderStage1DatasetResolver
from thesis_data.bank_onboarding import (
    build_bank_dataset_candidate,
    parse_bank_onboarding_packet,
    verify_packet_artifacts,
)
from thesis_data.canonical_snapshot import materialize_canonical_snapshot
from thesis_data.canonical_sqlite_provider import CanonicalSqliteDatasetProvider
from thesis_data.dataset_contract import (
    CanonicalObservation,
    DatasetSource,
)
from thesis_data.dataset_provider import DatasetProviderError
from thesis_data.gold_dataset_provider import GoldSqliteDatasetProvider
from thesis_data.onboarding_contract import demo_metric_registry
from thesis_data.storage import create_gold_snapshot_schema
from thesis_data.transferability import run_metric_probe
from thesis_data.schema import (
    AcceptancePolicy,
    AssertionType,
    AtomicClaim,
    ClaimDataRef,
    ClaimScope,
    InferenceType,
    QualityStatus,
    StructuredAssertion,
)


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
                self.assertIsNone(observation.source_ref)
                self.assertIsNotNone(observation.calculation_receipt)
                reviewed_source_refs = tuple(sorted({
                    item.source_ref for item in observation.review.primary_evidence
                }))
                for source_ref in reviewed_source_refs:
                    source = provider.get_source(ref, source_ref)
                    self.assertEqual(source.validation_status, QualityStatus.VALID)
                    self.assertEqual(source.source_tier, "primary")
                evidence = provider.get_evidence(
                    ref,
                    reviewed_source_refs,
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
                    if source_input.derivation_method is not None:
                        self.assertIsNone(source_input.source_ref)
                    else:
                        self.assertIsNotNone(source_input.source_ref)
                        self.assertIn(
                            (source_input.source_ref, source_input.source_locator),
                            {
                                (item.source_ref, item.locator)
                                for item in source_input.review.primary_evidence
                            },
                        )

        self.assertAlmostEqual(resolved["bank.npl_g35"].value, 1.2190, places=4)
        self.assertAlmostEqual(resolved["bank.llr_coverage"].value, 174.6762, places=4)
        self.assertEqual(resolved["bank.roa"].value, 1.1536)
        self.assertEqual(resolved["bank.roe"].value, 18.6012)

    def test_materialized_ctg_derived_observations_have_recomputed_persisted_receipts(self):
        packet, candidate, raw_descriptor, report = self.load_packet()
        expected_outputs = {
            ("bank.input.npl_g35_balance", "2024_Q4"): ("20989.767", "20989.767", "0.0000001"),
            ("bank.input.parent_attributable_equity", "2024_Q4"): ("147533.979", "147533.979", "0.0000001"),
            ("bank.input.parent_attributable_equity", "2023_Q4"): ("125010.60", "125010.60", "0.0000001"),
            ("bank.npl_g35", "2024_Q4"): ("1.219", "1.218950000795433229958915168", "0.00005"),
            ("bank.llr_coverage", "2024_Q4"): ("174.6762", "174.6761886399215389098888044", "0.00005"),
            ("bank.roa", "2024_Q4"): ("1.1536", "1.1536", "0.00005"),
            ("bank.roe", "2024_Q4"): ("18.6012", "18.6012", "0.00005"),
        }
        with tempfile.TemporaryDirectory() as directory:
            db_path = Path(directory) / "ctg-receipts.sqlite"
            accepted = materialize_canonical_snapshot(db_path, candidate, raw_descriptor, report)
            provider = CanonicalSqliteDatasetProvider(db_path, dataset_id=packet.dataset_id)
            ref = provider.current_dataset_ref()
            self.assertEqual(ref.dataset_snapshot_id, accepted.dataset_snapshot_id)

            receipt_count = 0
            for (metric_id, period_id), (candidate_output, calculated_output, tolerance) in expected_outputs.items():
                observation = provider.get_metric(ref, "CTG", period_id, metric_id)
                self.assertIsNotNone(observation, (metric_id, period_id))
                receipt = observation.calculation_receipt
                self.assertIsNotNone(receipt, (metric_id, period_id))
                receipt_count += 1
                self.assertEqual(receipt.formula_version, observation.derivation_method)
                self.assertEqual(receipt.candidate_output, Decimal(candidate_output))
                self.assertEqual(receipt.calculated_output, Decimal(calculated_output))
                self.assertEqual(receipt.tolerance, Decimal(tolerance))
                self.assertEqual(tuple(item.observation_id for item in receipt.ordered_inputs), observation.input_observation_ids)
                self.assertEqual(receipt.result, "passed")
                self.assertLessEqual(receipt.absolute_difference, receipt.tolerance)
                for input_receipt in receipt.ordered_inputs:
                    accepted_input = provider.resolve_observation(ref, input_receipt.observation_id)
                    self.assertIsNotNone(accepted_input)
                    self.assertEqual(accepted_input.validation_status, QualityStatus.VALID)
                    self.assertEqual(Decimal(str(accepted_input.value)), input_receipt.value)
                    self.assertEqual(accepted_input.metric_id, input_receipt.metric_id)
                    self.assertEqual(accepted_input.period_id, input_receipt.period_id)
                    self.assertEqual(accepted_input.unit, input_receipt.unit)
                    self.assertEqual(accepted_input.period_basis, input_receipt.period_basis)
                    self.assertEqual(accepted_input.reporting_scope, input_receipt.reporting_scope)

            self.assertEqual(receipt_count, 7)
            connection = sqlite3.connect(db_path)
            try:
                rows = connection.execute(
                    "SELECT derivation_method, validation_status, metadata_json FROM observations"
                ).fetchall()
            finally:
                connection.close()
            persisted_derived = [
                json.loads(metadata_json)
                for derivation_method, status, metadata_json in rows
                if derivation_method is not None and status == QualityStatus.VALID.value
            ]
            self.assertEqual(len(persisted_derived), receipt_count)
            self.assertTrue(all("__derived_calculation_receipt_v1" in item for item in persisted_derived))

    def test_materialization_rejects_derived_value_formula_unit_scope_and_input_mismatches(self):
        _, candidate, raw_descriptor, report = self.load_packet()
        target_metric = "bank.npl_g35"
        target_period = "2024_Q4"

        def altered_candidate(**updates):
            observations = list(candidate.observations)
            target_index = next(
                index for index, item in enumerate(observations)
                if item.metric_id == target_metric and item.period_id == target_period
            )
            observations[target_index] = observations[target_index].model_copy(update=updates)
            return replace(candidate, observations=tuple(observations))

        target = next(
            item for item in candidate.observations
            if item.metric_id == target_metric and item.period_id == target_period
        )
        altered_inputs = list(target.input_observation_ids)
        altered_inputs[0], altered_inputs[1] = altered_inputs[1], altered_inputs[0]
        invalid_candidates = (
            ("derived candidate value differs", altered_candidate(value=float(target.value) + 0.1)),
            ("formula is unsupported", altered_candidate(derivation_method="unrecognized-formula-v999")),
            ("output unit", altered_candidate(unit="ratio")),
            ("reporting scope", altered_candidate(reporting_scope="separate")),
            ("input metric/order", altered_candidate(input_observation_ids=tuple(altered_inputs))),
        )

        with tempfile.TemporaryDirectory() as directory:
            for index, (message, invalid_candidate) in enumerate(invalid_candidates):
                with self.subTest(message=message):
                    db_path = Path(directory) / f"rejected-{index}.sqlite"
                    with self.assertRaisesRegex(ValueError, message):
                        materialize_canonical_snapshot(
                            db_path, invalid_candidate, raw_descriptor, report
                        )
                    self.assertFalse(db_path.exists(), "failed promotion must not create an accepted snapshot")

    def test_stage1_accepts_ctg_derived_metrics_and_rejects_unreviewed_csv(self):
        packet, candidate, raw_descriptor, report = self.load_packet()
        with tempfile.TemporaryDirectory() as directory:
            db_path = Path(directory) / "ctg-stage1.sqlite"
            materialize_canonical_snapshot(db_path, candidate, raw_descriptor, report)
            provider = CanonicalSqliteDatasetProvider(db_path, dataset_id=packet.dataset_id)
            dataset_ref = provider.current_dataset_ref()
            npl = provider.get_metric(dataset_ref, "CTG", "2024_Q4", "bank.npl_g35")
            coverage = provider.get_metric(dataset_ref, "CTG", "2024_Q4", "bank.llr_coverage")
            self.assertIsNotNone(npl)
            self.assertIsNotNone(coverage)
            self.assertIsNone(npl.source_ref)
            self.assertIsNone(coverage.source_ref)
            self.assertTrue(npl.derivation_method)
            self.assertTrue(coverage.derivation_method)
            self.assertTrue(npl.input_observation_ids)
            self.assertTrue(coverage.input_observation_ids)

            source_refs_set = set()
            for observation in (npl, coverage):
                pending = [observation]
                visited = set()
                while pending:
                    current = pending.pop()
                    if current.observation_id in visited:
                        continue
                    visited.add(current.observation_id)
                    if current.source_ref is not None:
                        source_refs_set.add(current.source_ref)
                        continue
                    self.assertTrue(current.derivation_method)
                    self.assertTrue(current.input_observation_ids)
                    for input_id in current.input_observation_ids:
                        source_input = provider.resolve_observation(dataset_ref, input_id)
                        self.assertIsNotNone(source_input)
                        self.assertEqual(source_input.validation_status, QualityStatus.VALID)
                        self.assertIsNotNone(source_input.value)
                        pending.append(source_input)
            source_refs = tuple(sorted(source_refs_set))
            csv_source = DatasetSource(
                source_ref="upload:unreviewed-ctg-csv",
                source_type="csv",
                source_tier="user_supplied",
                source_url="urn:source:upload:unreviewed-ctg-csv",
                publisher="User upload",
                retrieved_at="2026-09-25T00:00:00Z",
                content_hash="unreviewed-csv-hash",
                validation_status=QualityStatus.PENDING_VALIDATION,
            )
            csv_observation = CanonicalObservation(
                observation_id="observation-unreviewed-ctg-cir",
                dataset_id=dataset_ref.dataset_id,
                dataset_snapshot_id=dataset_ref.dataset_snapshot_id,
                entity_id="CTG",
                period_id="2024_Q4",
                metric_id="bank.cir",
                value=38.4,
                unit="percent",
                source_ref=csv_source.source_ref,
                source_locator="csv_row=2",
                period_basis="quarter_only",
                reporting_scope="consolidated",
                validation_status=QualityStatus.PENDING_VALIDATION,
            )
            derived_claims = tuple(
                self._numeric_claim(
                    observation=observation,
                    # Numeric support comes from the exact observation and
                    # primary-source locator. No reviewed observation-to-snippet
                    # link exists for these source-level document records.
                    evidence_id=None,
                    source_refs=source_refs,
                    ref_type="derived_metric",
                    claim_id=f"ctg-{observation.metric_id}",
                )
                for observation in (npl, coverage)
            )
            policy = AcceptancePolicy(
                policy_version="ctg-derived-stage1-regression-v1",
                provisional_threshold=0.75,
            )
            resolver = ProviderStage1DatasetResolver(provider, dataset_ref)
            accepted_result = validate_stage1_claims(
                resolver,
                derived_claims,
                ClaimScope(
                    entities=("CTG",),
                    periods=("2024_Q4",),
                    metric_ids=("bank.npl_g35", "bank.llr_coverage"),
                ),
                policy,
            )
            self.assertTrue(accepted_result.passed, accepted_result.model_dump_json())

            class CsvOverlayProvider:
                def __getattr__(self, name):
                    return getattr(provider, name)

                def resolve_observation(self, current_ref, observation_id):
                    if observation_id == csv_observation.observation_id:
                        return csv_observation
                    return provider.resolve_observation(current_ref, observation_id)

                def get_source(self, current_ref, source_ref):
                    if source_ref == csv_source.source_ref:
                        return csv_source
                    return provider.get_source(current_ref, source_ref)

            csv_claim = self._numeric_claim(
                observation=csv_observation,
                evidence_id=None,
                source_refs=(csv_source.source_ref,),
                ref_type="observation",
                claim_id="ctg-unreviewed-csv",
                claim_type="candidate",
                critical=False,
            )
            csv_resolver = ProviderStage1DatasetResolver(CsvOverlayProvider(), dataset_ref)
            csv_result = validate_stage1_claims(
                csv_resolver,
                (csv_claim,),
                ClaimScope(
                    entities=("CTG",),
                    periods=("2024_Q4",),
                    metric_ids=("bank.cir",),
                ),
                policy,
            )

        self.assertFalse(csv_result.passed)
        self.assertIn(
            "observation_reference_unaccepted",
            " ".join(csv_result.gate_results["reference_validity"].violations),
        )
        self.assertIn(
            "source_reference_unaccepted",
            " ".join(csv_result.gate_results["reference_validity"].violations),
        )

    @staticmethod
    def _numeric_claim(
        *,
        observation,
        evidence_id: str | None,
        source_refs: tuple[str, ...],
        ref_type: str,
        claim_id: str,
        claim_type: str = "numeric",
        critical: bool = True,
    ) -> AtomicClaim:
        data_ref = ClaimDataRef(
            ref_id=observation.observation_id,
            ref_type=ref_type,
            entity=observation.entity_id,
            period=observation.period_id,
            metric_id=observation.metric_id,
        )
        assertion = StructuredAssertion(
            assertion_id=f"{claim_id}-assertion",
            assertion_type=AssertionType.METRIC_VALUE,
            entity=observation.entity_id,
            period=observation.period_id,
            metric_id=observation.metric_id,
            asserted_value=observation.value,
            unit=observation.unit,
            formula_version=observation.derivation_method,
            data_refs=(data_ref,),
        )
        return AtomicClaim(
            claim_id=claim_id,
            claim_text=f"{observation.entity_id} {observation.metric_id} was {observation.value}.",
            claim_type=claim_type,
            title=observation.metric_id,
            interpretation="A reported or deterministically derived metric.",
            limitation="Stage1 lineage regression fixture.",
            scope=ClaimScope(
                entities=(observation.entity_id,),
                periods=(observation.period_id,),
                metric_ids=(observation.metric_id,),
            ),
            assertions=(assertion,),
            evidence_refs=(evidence_id,) if evidence_id is not None else (),
            source_refs=source_refs,
            inference_type=InferenceType.FACT,
            support="evidence_backed" if evidence_id is not None else "partially_supported",
            critical=critical,
        )

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
