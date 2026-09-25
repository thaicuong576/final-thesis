from __future__ import annotations

import csv
import json
from pathlib import Path
import unittest


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
PACKET_PATH = REPOSITORY_ROOT / "data" / "onboarding" / "ctg-2024-audited-2024q4-v1.json"
RECONCILIATION_PATH = PACKET_PATH.with_name(PACKET_PATH.stem + "-reconciliation.csv")

NOTE_10 = "pdf_page=38; printed_page=36; section=Note 10: customer loan quality analysis"
NOTE_11 = "pdf_page=39; printed_page=37; section=Note 11: loan loss provisions"

EXPECTED_LOCATORS = {
    "ctg-input-group-3-2024q4": f"{NOTE_10}; row=customer loans, group 3; column=closing balance",
    "ctg-input-group-4-2024q4": f"{NOTE_10}; row=customer loans, group 4; column=closing balance",
    "ctg-input-group-5-2024q4": f"{NOTE_10}; row=customer loans, group 5; column=closing balance",
    "ctg-input-gross-loans-2024q4": f"{NOTE_10}; row=total gross customer loans; column=closing balance",
    "ctg-input-provisions-2024q4": f"{NOTE_11}; row=total closing allowance; column=closing balance",
    "ctg-input-npl-balance-2024q4": f"{NOTE_10}; row=customer loans, group 3; column=closing balance",
    "ctg-bank-npl-g35-2024q4": f"{NOTE_10}; row=customer loans, group 3; column=closing balance",
    "ctg-bank-llr-coverage-2024q4": f"{NOTE_11}; row=total closing allowance; column=closing balance",
}


class CTGSourceLocatorTests(unittest.TestCase):
    def test_corrected_locators_match_packet_evidence_and_reconciliation_register(self):
        packet = json.loads(PACKET_PATH.read_text(encoding="utf-8"))
        observations = {item["observation_id"]: item for item in packet["observations"]}
        with RECONCILIATION_PATH.open(encoding="utf-8-sig", newline="") as stream:
            register = {row["observation_id"]: row for row in csv.DictReader(stream)}

        self.assertTrue(set(EXPECTED_LOCATORS).issubset(observations))
        self.assertTrue(set(EXPECTED_LOCATORS).issubset(register))
        for observation_id, expected_locator in EXPECTED_LOCATORS.items():
            with self.subTest(observation_id=observation_id):
                observation = observations[observation_id]
                self.assertEqual(observation["candidate_locator"], expected_locator)
                evidence_locators = [
                    evidence["source_locator"]
                    for evidence in observation["review"]["primary_evidence"]
                ]
                self.assertEqual(evidence_locators, [expected_locator])
                self.assertEqual(register[observation_id]["source_locator"], expected_locator)
                self.assertEqual(observation["review"]["reviewer_id"], "codex-worker-data")


if __name__ == "__main__":
    unittest.main()
