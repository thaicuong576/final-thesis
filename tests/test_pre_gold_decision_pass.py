from __future__ import annotations

from decimal import Decimal, ROUND_HALF_UP
import hashlib
import json
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
PACKAGE = ROOT / "data" / "reconciliation" / "pre-gold-decision-2024-q4-v1"
DECISION = PACKAGE / "decision.json"
CANDIDATES = PACKAGE / "candidate-observations.jsonl"
ACQUISITION_MANIFEST = ROOT / "data" / "manifests" / "pre-phase4-acquisition-v1.jsonl"


def reject_duplicate_keys(pairs: list[tuple[str, object]]) -> dict:
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"duplicate_json_key:{key}")
        result[key] = value
    return result


def read_jsonl(path: Path) -> list[dict]:
    return [
        json.loads(line, object_pairs_hook=reject_duplicate_keys)
        for line in path.read_text(encoding="utf-8").splitlines()
    ]


class PreGoldDecisionPassTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.decision = json.loads(
            DECISION.read_text(encoding="utf-8"),
            object_pairs_hook=reject_duplicate_keys,
        )
        cls.candidates = read_jsonl(CANDIDATES)
        cls.manifest = read_jsonl(ACQUISITION_MANIFEST)

    def test_decision_package_is_strict_json_and_has_expected_source_hash(self) -> None:
        self.assertIsInstance(self.decision, dict)
        source = self.decision["source_registry"]["primary_artifact"]
        manifest_row = next(row for row in self.manifest if row.get("source_id") == source["source_id"])
        self.assertEqual(manifest_row["publisher"], source["publisher"])
        self.assertEqual(manifest_row["source_tier"], source["source_tier"])
        self.assertEqual(manifest_row["content_hash_sha256"], source["sha256"])
        path = ROOT / manifest_row["local_path"]
        self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest(), source["sha256"])

    def test_credit_growth_matches_frozen_semantics(self) -> None:
        row = self.decision["macro_credit_growth"]
        self.assertEqual(row["metric_id"], "macro.credit_growth")
        self.assertEqual(row["entity_scope_match"], True)
        self.assertEqual(row["period_match"], True)
        self.assertEqual(row["definition_match"], True)
        self.assertEqual(row["period"], "2024_Q4")
        self.assertEqual(row["as_of_date"], "2024-12-31")
        self.assertEqual(row["period_basis"], "annual_change_vs_end_2023")
        self.assertEqual(row["value"], 15.1)
        self.assertEqual(row["source_status"], "DIRECT_OFFICIAL")
        self.assertEqual(row["quality_status"], "review_required")
        self.assertEqual(row["promotion_status"], "not_promoted")

    def test_credit_growth_stock_cross_check_rounds_to_source_value(self) -> None:
        row = self.decision["macro_credit_growth"]
        old = Decimal(str(row["stock_inputs_preserved"][0]["value"]))
        new = Decimal(str(row["stock_inputs_preserved"][1]["value"]))
        calculated = ((new / old) - Decimal("1")) * Decimal("100")
        rounded = calculated.quantize(Decimal("0.1"), rounding=ROUND_HALF_UP)
        self.assertEqual(str(calculated), row["derived_cross_check"]["unrounded_percent"])
        self.assertEqual(float(rounded), row["value"])
        self.assertFalse(row["derived_cross_check"]["is_replacement_for_source_native_value"])

    def test_secondary_1508_is_excluded(self) -> None:
        excluded = self.decision["macro_credit_growth"]["excluded_value"]
        self.assertEqual(excluded["value"], 15.08)
        self.assertEqual(excluded["reason"], "secondary_research_statement_without_traceable_primary_year_end_basis")
        self.assertNotEqual(self.decision["macro_credit_growth"]["value"], excluded["value"])

    def test_macro_and_sector_credit_growth_use_one_underlying_fact(self) -> None:
        reconciliation = self.decision["macro_sector_reconciliation"]
        self.assertFalse(reconciliation["new_sector_credit_growth_observation_created"])
        self.assertEqual(
            reconciliation["underlying_observation_id"],
            "nso_statistical_yearbook_2024_table_102_credit_growth_2024_q4",
        )
        self.assertEqual(
            [row["metric_id"] for row in self.candidates],
            ["macro.credit_growth", "sector.system_credit_outstanding"],
        )

    def test_sector_credit_outstanding_is_exact_year_end_candidate(self) -> None:
        row = self.decision["sector_system_credit_outstanding"]
        self.assertEqual(row["metric_id"], "sector.system_credit_outstanding")
        self.assertEqual(row["entity"], "VN_BANKING_SYSTEM")
        self.assertEqual(row["period"], "2024_Q4")
        self.assertEqual(row["as_of_date"], "2024-12-31")
        self.assertEqual(row["period_basis"], "point_in_time_year_end")
        self.assertEqual(row["value"], 15617.1)
        self.assertEqual(row["unit"], "VND_trillion")
        self.assertTrue(row["entity_scope_match"])
        self.assertTrue(row["date_match"])
        self.assertTrue(row["unit_match"])
        self.assertEqual(row["quality_status"], "review_required")

    def test_sector_npl_remains_explicit_missing_without_peer_substitution(self) -> None:
        row = self.decision["sector_system_npl_ratio"]
        self.assertIsNone(row["value"])
        self.assertEqual(row["quality_status"], "missing")
        self.assertEqual(row["missing_reason"], "DATA_UNAVAILABLE")
        self.assertFalse(row["peer_substitution_used"])
        self.assertIsNone(row["source_id"])

    def test_no_gold_promotion_or_locked_artifact_change(self) -> None:
        self.assertFalse(self.decision["gold_promotion"]["performed"])
        self.assertFalse(self.decision["gold_promotion"]["existing_macro_gold_artifacts_modified"])
        self.assertFalse(self.decision["gold_promotion"]["raw_acquisition_artifacts_modified"])


if __name__ == "__main__":
    unittest.main()
