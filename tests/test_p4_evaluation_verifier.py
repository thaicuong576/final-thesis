import json
from pathlib import Path
import shutil
import tempfile
import unittest

from scripts.verify_p4_evaluation_inputs import (
    VerificationError,
    peer_probe_record,
    verify_candidate_question_bindings,
    verify_peer_probe_records,
)
from thesis_data.dataset_contract import CanonicalObservation, DatasetRef, QualityStatus
from thesis_data.dataset_provider import aggregate_peer_median


ROOT = Path(__file__).resolve().parents[1]


class P4EvaluationVerifierTests(unittest.TestCase):
    def test_candidate_manifests_have_consistent_hashes_and_premain_eligibility(self):
        report = verify_candidate_question_bindings(ROOT)

        self.assertEqual(report["task_count"], 10)
        self.assertFalse(report["final_protocol_freeze_ready"])
        self.assertFalse(report["scoring_eligible_now"])

    def test_candidate_verifier_rejects_coverage_hash_drift(self):
        with tempfile.TemporaryDirectory() as directory:
            temp_root = Path(directory)
            for relative in (
                "data/evaluation/gold-v5-peer-input-audit-v1.json",
                "data/evaluation/p4-questions-v1.jsonl",
                "data/evaluation/p4-task-specs-v1.json",
                "data/evaluation/p4-expected-coverage-v1.json",
            ):
                target = temp_root / relative
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(ROOT / relative, target)
            coverage_path = temp_root / "data/evaluation/p4-expected-coverage-v1.json"
            coverage = json.loads(coverage_path.read_text(encoding="utf-8"))
            coverage["tasks"][0]["expected_coverage"]["valid_count"] += 1
            coverage_path.write_text(
                json.dumps(coverage, ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
                newline="\n",
            )

            with self.assertRaisesRegex(VerificationError, "expected coverage hash mismatch"):
                verify_candidate_question_bindings(temp_root)

    def test_peer_probe_verifier_detects_any_record_drift(self):
        ref = DatasetRef(dataset_id="peer-verifier", dataset_snapshot_id="snapshot-v1")
        peer_ids = ("bank-a", "bank-b")
        observations = []
        for period_index in range(4):
            for metric_index in range(4):
                period_id = f"2024_Q{period_index + 1}"
                metric_id = f"bank.metric_{metric_index}"
                members = tuple(
                    CanonicalObservation(
                        observation_id=f"obs-{period_id}-{metric_id}-{entity_id}",
                        dataset_id=ref.dataset_id,
                        dataset_snapshot_id=ref.dataset_snapshot_id,
                        entity_id=entity_id,
                        period_id=period_id,
                        metric_id=metric_id,
                        value=float(value),
                        unit="%",
                        source_ref=f"source-{entity_id}",
                        period_basis="ttm",
                        reporting_scope="consolidated",
                        validation_status=QualityStatus.VALID,
                    )
                    for entity_id, value in (("bank-a", 1), ("bank-b", 3))
                )
                observations.append(
                    aggregate_peer_median(
                        dataset_ref=ref,
                        peer_universe_id="sector:bank",
                        period_id=period_id,
                        metric_id=metric_id,
                        peer_entity_ids=peer_ids,
                        member_observations=members,
                    )
                )

        records = [peer_probe_record(item) for item in observations]
        verify_peer_probe_records(records, records)
        changed = [dict(item) for item in records]
        changed[0]["eligible_denominator"] = 1
        with self.assertRaisesRegex(VerificationError, "differ from the bound audit"):
            verify_peer_probe_records(records, changed)
        with self.assertRaisesRegex(VerificationError, "record count must be sixteen"):
            verify_peer_probe_records(records[:-1], records[:-1])


if __name__ == "__main__":
    unittest.main()
