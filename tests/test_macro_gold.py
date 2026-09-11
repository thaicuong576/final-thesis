import json
import sqlite3
import tempfile
import unittest
from datetime import date
from pathlib import Path

from thesis_data.acceptance import validate_stage1_claims
from thesis_data.agent_tools import GoldToolRuntime
from thesis_data.experiment_contract import ExperimentArm, ExperimentRunConfig, audit_experiment_inputs
from thesis_data.macro_gold import (
    MACRO_CREDIT_DEFINITION_VERSION,
    MACRO_CREDIT_GROWTH,
    MACRO_POLICY_DEFINITION_VERSION,
    MACRO_POLICY_RATE,
    MACRO_GOLD_PERIOD,
    MACRO_ENTITY,
    macro_cell_availability,
)
from thesis_data.query import get_macro_context, get_macro_evidence
from thesis_data.schema import (
    AcceptancePolicy,
    AgentStatus,
    AssertionType,
    AtomicClaim,
    ClaimDataRef,
    ClaimScope,
    InferenceType,
    MacroObservationV2,
    QualityStatus,
    StructuredAssertion,
    GoldConfig,
)
from thesis_data.storage import create_gold_snapshot_schema


class MacroGoldIntegrationTests(unittest.TestCase):
    def _policy_row(self) -> MacroObservationV2:
        return MacroObservationV2(
            observation_id="macro-policy-q4-v2",
            indicator_id=MACRO_POLICY_RATE,
            value=4.5,
            unit="percent_per_annum",
            period=MACRO_GOLD_PERIOD,
            source_id="macro-source",
            quality_status=QualityStatus.VALID,
            source_series_id="SBV.refinancing_rate",
            indicator_definition_version=MACRO_POLICY_DEFINITION_VERSION,
            frequency="irregular_state",
            observation_date=date(2023, 3, 19),
            effective_from=date(2023, 3, 19),
            as_of_date=date(2024, 12, 31),
            period_basis="quarter_end_state",
            alignment_method="latest_effective_state_at_period_end_v1",
            source_locator="sbv-api#/items/0/refinancing-rate",
            transformation_version="state_carry_forward_v1",
            adjudication_ref="review.json",
            review_check_ids=("checker-a", "checker-b"),
        )

    def _missing_row(self) -> MacroObservationV2:
        return MacroObservationV2(
            observation_id="macro-credit-q4-v2",
            indicator_id=MACRO_CREDIT_GROWTH,
            value=None,
            unit="percent",
            period=MACRO_GOLD_PERIOD,
            source_id=None,
            quality_status=QualityStatus.MISSING,
            reason="DATA_UNAVAILABLE",
            indicator_definition_version=MACRO_CREDIT_DEFINITION_VERSION,
            frequency="quarterly",
            period_basis="ytd_vs_end_2023",
            adjudication_ref="review.json",
        )

    def _insert_macro_row(self, connection: sqlite3.Connection, row: MacroObservationV2) -> None:
        connection.execute(
            """
            INSERT INTO macro_observations_v2
            (observation_id, indicator_id, value, unit, period, source_id,
             quality_status, reason, source_series_id,
             indicator_definition_version, frequency, observation_date,
             effective_from, as_of_date, period_basis, alignment_method,
             source_locator, transformation_version, input_observation_ids_json,
             adjudication_ref, review_check_ids_json)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                row.observation_id,
                row.indicator_id,
                row.value,
                row.unit,
                row.period,
                row.source_id,
                row.quality_status.value,
                row.reason,
                row.source_series_id,
                row.indicator_definition_version,
                row.frequency,
                row.observation_date.isoformat() if row.observation_date else None,
                row.effective_from.isoformat() if row.effective_from else None,
                row.as_of_date.isoformat() if row.as_of_date else None,
                row.period_basis,
                row.alignment_method,
                row.source_locator,
                row.transformation_version,
                json.dumps(list(row.input_observation_ids)),
                row.adjudication_ref,
                json.dumps(list(row.review_check_ids)),
            ),
        )

    def _db(self, root: Path, *, baseline: bool = False) -> Path:
        path = root / "gold.sqlite"
        create_gold_snapshot_schema(path)
        connection = sqlite3.connect(path)
        config = {
            "tickers": ["VCB"],
            "periods": [MACRO_GOLD_PERIOD],
            "required_metrics": ["bank.roa"],
            "min_manual_labels": 2,
            "min_independent_checkers": 2,
            "min_metric_coverage": 1.0,
        }
        connection.execute(
            "INSERT INTO snapshot_metadata VALUES (?, ?, ?, ?)",
            ("gold-macro-test", "2026-09-11T00:00:00Z", "gold", json.dumps(config)),
        )
        connection.execute(
            """
            INSERT INTO source_records VALUES
            ('macro-source', 'api', 'primary', 'https://sbv.test/policy',
             '2026-09-11T00:00:00Z', 'policy.json', 'hash-policy',
             'State Bank of Vietnam', 'test', 'valid', NULL)
            """
        )
        connection.execute(
            """
            INSERT INTO macro_evidence_snippets VALUES
            ('macro-evidence:policy', 'macro-source', 'macro.policy_rate',
             '2024_Q4', 'policy.json', 'items[0].refinancing-rate',
             'Lãi suất tái cấp vốn: 4,500%; ngày áp dụng 19/03/2023.',
             '2024-12-31', '2023-03-19', 'structured_content')
            """
        )
        self._insert_macro_row(connection, self._policy_row())
        self._insert_macro_row(connection, self._missing_row())
        if baseline:
            connection.execute(
                """
                INSERT INTO metric_observations VALUES
                ('obs-vcb-roa', 'VCB', 'bank', 'bank.roa', 1.2, '%',
                 '2024_Q4', '2024-12-31', 'point_in_time', 'macro-source',
                 'page:1', 'valid', NULL)
                """
            )
            connection.executemany(
                """
                INSERT INTO gold_labels VALUES
                (?, 'obs-vcb-roa', 'value_check', 1.2, NULL, ?,
                 '2026-09-11T00:00:00Z', 'page:1', 'matched')
                """,
                [("label-a", "checker-a"), ("label-b", "checker-b")],
            )
        connection.commit()
        connection.close()
        return path

    def _macro_claim(self, *, value: float | None = 4.5, unit: str | None = "percent_per_annum", period: str = MACRO_GOLD_PERIOD, source_refs=("macro-source",)) -> AtomicClaim:
        data_ref = ClaimDataRef(
            ref_id="macro-policy-q4-v2",
            ref_type="macro_observation",
            entity=MACRO_ENTITY,
            period=MACRO_GOLD_PERIOD,
            metric_id=MACRO_POLICY_RATE,
        )
        assertion = StructuredAssertion(
            assertion_id="macro-policy-assertion",
            assertion_type=AssertionType.METRIC_VALUE,
            entity=MACRO_ENTITY,
            period=period,
            metric_id=MACRO_POLICY_RATE,
            asserted_value=value,
            unit=unit,
            data_refs=(data_ref,),
        )
        return AtomicClaim(
            claim_id="macro-policy-claim",
            claim_text="The SBV refinancing rate was 4.5% per annum.",
            claim_type="numeric",
            title="Policy rate",
            interpretation="A directly observed macro state carried forward to quarter end.",
            limitation="The source event predates the analytical period.",
            scope=ClaimScope(
                entities=(MACRO_ENTITY,),
                periods=("2024_Q3", MACRO_GOLD_PERIOD) if period == "2024_Q3" else (MACRO_GOLD_PERIOD,),
                metric_ids=(MACRO_POLICY_RATE,),
            ),
            assertions=(assertion,),
            evidence_refs=("macro-evidence:policy",),
            source_refs=source_refs,
            inference_type=InferenceType.FACT,
            support="evidence_backed",
        )

    def _policy(self) -> AcceptancePolicy:
        return AcceptancePolicy(policy_version="macro-test-v1", provisional_threshold=0.75)

    def test_policy_rate_valid_observation_and_carry_forward_metadata(self):
        with tempfile.TemporaryDirectory() as directory:
            db = self._db(Path(directory))
            payload = get_macro_context(db, MACRO_GOLD_PERIOD, (MACRO_POLICY_RATE,))
            connection = sqlite3.connect(db)
            row = connection.execute(
                "SELECT value, unit, observation_date, effective_from, as_of_date, alignment_method, transformation_version FROM macro_observations_v2 WHERE indicator_id = ?",
                (MACRO_POLICY_RATE,),
            ).fetchone()
            connection.close()
        self.assertEqual(payload.status, AgentStatus.SUCCESS)
        self.assertEqual(payload.metrics[MACRO_POLICY_RATE], 4.5)
        self.assertEqual(payload.observation_ids, ["macro-policy-q4-v2"])
        self.assertEqual(row, (4.5, "percent_per_annum", "2023-03-19", "2023-03-19", "2024-12-31", "latest_effective_state_at_period_end_v1", "state_carry_forward_v1"))

    def test_numeric_macro_claim_passes_stage1(self):
        with tempfile.TemporaryDirectory() as directory:
            db = self._db(Path(directory))
            scope = ClaimScope(entities=(MACRO_ENTITY,), periods=(MACRO_GOLD_PERIOD,), metric_ids=(MACRO_POLICY_RATE,))
            result = validate_stage1_claims(db, (self._macro_claim(),), scope, self._policy())
        self.assertTrue(result.passed)

    def test_wrong_macro_value_unit_period_and_source_fail(self):
        with tempfile.TemporaryDirectory() as directory:
            db = self._db(Path(directory))
            scope = ClaimScope(entities=(MACRO_ENTITY,), periods=("2024_Q3", MACRO_GOLD_PERIOD), metric_ids=(MACRO_POLICY_RATE,))
            wrong_value = validate_stage1_claims(db, (self._macro_claim(value=4.0),), scope, self._policy())
            wrong_unit = validate_stage1_claims(db, (self._macro_claim(unit="percent"),), scope, self._policy())
            wrong_period = validate_stage1_claims(db, (self._macro_claim(period="2024_Q3"),), scope, self._policy())
            wrong_source = validate_stage1_claims(db, (self._macro_claim(source_refs=("fabricated-source",)),), scope, self._policy())
        self.assertFalse(wrong_value.gate_results["numeric_accuracy"].passed)
        self.assertFalse(wrong_unit.gate_results["numeric_accuracy"].passed)
        self.assertFalse(wrong_period.gate_results["numeric_accuracy"].passed)
        self.assertFalse(wrong_source.gate_results["reference_validity"].passed)

    def test_macro_evidence_is_tickerless_and_tool_routed(self):
        with tempfile.TemporaryDirectory() as directory:
            db = self._db(Path(directory))
            snippets = get_macro_evidence(db, ("macro-source",), MACRO_POLICY_RATE, MACRO_GOLD_PERIOD)
            runtime = GoldToolRuntime(
                db,
                ticker="VCB",
                periods=(MACRO_GOLD_PERIOD,),
                metric_ids=(),
                macro_indicator_ids=(MACRO_POLICY_RATE,),
                peer_tickers=("VCB",),
                source_policy_id="primary-only-v1",
            )
            tool_result = runtime.execute(
                "macro",
                "get_evidence",
                {"source_ids": ["macro-source"], "ticker": None, "period": MACRO_GOLD_PERIOD, "indicator_id": MACRO_POLICY_RATE},
            )
        self.assertEqual(snippets[0].ticker, None)
        self.assertEqual(snippets[0].indicator_id, MACRO_POLICY_RATE)
        self.assertEqual(tool_result.output[0]["indicator_id"], MACRO_POLICY_RATE)

    def test_accepted_missing_credit_growth_is_queryable_and_macro_agent_is_partial(self):
        with tempfile.TemporaryDirectory() as directory:
            db = self._db(Path(directory))
            payload = get_macro_context(db, MACRO_GOLD_PERIOD, (MACRO_POLICY_RATE, MACRO_CREDIT_GROWTH))
        self.assertEqual(payload.status, AgentStatus.PARTIAL)
        self.assertEqual(payload.metrics[MACRO_POLICY_RATE], 4.5)
        self.assertIsNone(payload.metrics[MACRO_CREDIT_GROWTH])
        self.assertIn("macro-credit-q4-v2", payload.observation_ids)
        self.assertEqual(payload.missing_reasons[MACRO_CREDIT_GROWTH], "DATA_UNAVAILABLE")
        self.assertIn("accepted_missing:macro.credit_growth:DATA_UNAVAILABLE", payload.quality_flags)
        self.assertIn("missing:macro.credit_growth:DATA_UNAVAILABLE", payload.findings)

    def test_fabricated_numeric_claim_over_accepted_missing_fails(self):
        ref = ClaimDataRef(
            ref_id="macro-credit-q4-v2", ref_type="macro_observation", entity=MACRO_ENTITY,
            period=MACRO_GOLD_PERIOD, metric_id=MACRO_CREDIT_GROWTH,
        )
        claim = AtomicClaim(
            claim_id="fabricated-credit-growth",
            claim_text="Credit growth was 15.08%.",
            claim_type="numeric", title="Credit growth", interpretation="Test.", limitation="Test.",
            scope=ClaimScope(entities=(MACRO_ENTITY,), periods=(MACRO_GOLD_PERIOD,), metric_ids=(MACRO_CREDIT_GROWTH,)),
            assertions=(StructuredAssertion(
                assertion_id="credit-growth-assertion", assertion_type=AssertionType.METRIC_VALUE,
                entity=MACRO_ENTITY, period=MACRO_GOLD_PERIOD, metric_id=MACRO_CREDIT_GROWTH,
                asserted_value=15.08, unit="percent", data_refs=(ref,),
            ),),
            source_refs=(), evidence_refs=(), inference_type=InferenceType.FACT,
        )
        with tempfile.TemporaryDirectory() as directory:
            result = validate_stage1_claims(
                self._db(Path(directory)), (claim,), claim.scope, self._policy()
            )
        self.assertFalse(result.gate_results["numeric_accuracy"].passed)
        self.assertIn("numeric_lhs_missing", " ".join(result.gate_results["numeric_accuracy"].violations))

    def _macro_question(self, root: Path) -> Path:
        path = root / "macro-question.json"
        path.write_text(
            json.dumps({
                "schema_version": 1,
                "status": "test",
                "question_set_id": "macro-questions-v1",
                "scope": {"issuers": ["VCB"], "periods": [MACRO_GOLD_PERIOD], "core_metrics": ["bank.roa"]},
                "questions": [{
                    "id": "macro-q4", "issuer": "VCB", "type": "macro_to_bank",
                    "period": MACRO_GOLD_PERIOD,
                    "macro_indicator_ids": [MACRO_POLICY_RATE, MACRO_CREDIT_GROWTH],
                    "bank_metric_ids": ["bank.roa"],
                    "causal_claim_policy": "association_only",
                    "prompt": "Relate macro context and bank facts.",
                }],
            }),
            encoding="utf-8",
        )
        return path

    def _run_config(self) -> ExperimentRunConfig:
        return ExperimentRunConfig(
            run_id="macro-run", snapshot_id="gold-macro-test",
            question_set_id="macro-questions-v1", question_id="macro-q4",
            rubric_version="rubric-v1", prompt_version="prompt-v1",
            arm=ExperimentArm.SINGLE_AGENT, model_id="test-model",
            source_policy_id="primary-only-v1",
        )

    def test_accepted_missing_does_not_fail_experiment_preflight(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            audit = audit_experiment_inputs(
                self._db(root, baseline=True), self._run_config(), self._macro_question(root),
                GoldConfig(
                    tickers=("VCB",), periods=(MACRO_GOLD_PERIOD,), required_metrics=("bank.roa",),
                    min_manual_labels=2, min_metric_coverage=1.0,
                ),
            )
        self.assertTrue(audit.eligible, audit.blockers)

    def test_pending_or_fallback_credit_growth_blocks_preflight(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            db = self._db(root, baseline=True)
            connection = sqlite3.connect(db)
            connection.execute(
                "UPDATE macro_observations_v2 SET quality_status = 'pending_validation', reason = 'awaiting review' WHERE indicator_id = ?",
                (MACRO_CREDIT_GROWTH,),
            )
            connection.commit()
            connection.close()
            audit = audit_experiment_inputs(
                db, self._run_config(), self._macro_question(root),
                GoldConfig(
                    tickers=("VCB",), periods=(MACRO_GOLD_PERIOD,), required_metrics=("bank.roa",),
                    min_manual_labels=2, min_metric_coverage=1.0,
                ),
            )
            availability = macro_cell_availability(db, MACRO_CREDIT_GROWTH, MACRO_GOLD_PERIOD)
        self.assertFalse(audit.eligible)
        self.assertIn("missing_accepted_macro_observation:2024_Q4:macro.credit_growth", audit.blockers)
        self.assertEqual(availability.status, "blocked")

    def test_pending_v2_row_does_not_fallback_to_legacy_macro_row(self):
        with tempfile.TemporaryDirectory() as directory:
            db = self._db(Path(directory))
            connection = sqlite3.connect(db)
            connection.execute(
                "INSERT INTO macro_observations VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                ("legacy-credit", MACRO_CREDIT_GROWTH, 15.08, "percent", MACRO_GOLD_PERIOD, "macro-source", "valid", None),
            )
            connection.execute(
                "UPDATE macro_observations_v2 SET quality_status = 'pending_validation', reason = 'awaiting review' WHERE indicator_id = ?",
                (MACRO_CREDIT_GROWTH,),
            )
            connection.commit()
            connection.close()
            payload = get_macro_context(db, MACRO_GOLD_PERIOD, (MACRO_CREDIT_GROWTH,))
        self.assertIsNone(payload.metrics[MACRO_CREDIT_GROWTH])
        self.assertNotIn("legacy-credit", payload.observation_ids)
        self.assertIn("missing_or_unaccepted:macro.credit_growth", payload.findings)


if __name__ == "__main__":
    unittest.main()
