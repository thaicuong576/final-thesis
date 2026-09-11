import hashlib
import json
import sqlite3
import tempfile
import unittest
from datetime import date
from pathlib import Path

from thesis_data.gold_acceptance_compat import validate_gold_stage1_claims as validate_stage1_claims
from thesis_data.agent_tools import GoldToolRuntime
from thesis_data.experiment_contract import ExperimentArm, ExperimentRunConfig, audit_experiment_inputs
from thesis_data.macro_gold import (
    MACRO_CREDIT_DEFINITION_VERSION,
    MACRO_CREDIT_GROWTH,
    MACRO_GOLD_CONTRACT_VERSION,
    MACRO_POLICY_DEFINITION_VERSION,
    MACRO_POLICY_RATE,
    MACRO_GOLD_PERIOD,
    MACRO_ENTITY,
    EXPECTED_PARENT_SCOPE,
    EXPECTED_PARENT_SNAPSHOT_ID,
    materialize_macro_gold_snapshot,
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
            observation_date=date(2023, 6, 19),
            effective_from=date(2023, 6, 19),
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
            frequency=None,
            period_basis="ytd_vs_end_2023",
            adjudication_ref="review.json",
            review_check_ids=("credit-checker-a", "credit-checker-b"),
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

    def _db(
        self,
        root: Path,
        *,
        baseline: bool = False,
        parent_ready: bool = False,
        include_macro: bool = True,
    ) -> Path:
        path = root / "gold.sqlite"
        create_gold_snapshot_schema(path)
        connection = sqlite3.connect(path)
        if parent_ready:
            config = {
                **EXPECTED_PARENT_SCOPE,
                "min_manual_labels": 2,
                "min_independent_checkers": 2,
                "min_metric_coverage": 1.0,
            }
            snapshot_id = EXPECTED_PARENT_SNAPSHOT_ID
        else:
            config = {
                "tickers": ["VCB"],
                "periods": [MACRO_GOLD_PERIOD],
                "required_metrics": ["bank.roa"],
                "min_manual_labels": 2,
                "min_independent_checkers": 2,
                "min_metric_coverage": 1.0,
            }
            snapshot_id = "gold-macro-test"
        connection.execute(
            "INSERT INTO snapshot_metadata VALUES (?, ?, ?, ?)",
            (snapshot_id, "2026-09-11T00:00:00Z", "gold", json.dumps(config)),
        )
        connection.execute(
            """
            INSERT INTO source_records VALUES
            ('macro-source', 'api', 'primary', 'https://sbv.test/policy',
             '2026-09-11T00:00:00Z', 'policy.json', 'hash-policy',
             'State Bank of Vietnam', 'test', 'valid', NULL)
            """
        )
        if include_macro:
            connection.execute(
                """
                INSERT INTO macro_evidence_snippets VALUES
                ('macro-evidence:policy', 'macro-source', 'macro.policy_rate',
                 '2024_Q4', 'policy.json', 'items[0].refinancing-rate',
                 'Lãi suất tái cấp vốn: 4,500%; Decision 1123/QĐ-NHNN ngày 16/06/2023; record 19-06-2023.',
                 '2024-12-31', '2023-06-19', 'structured_content')
                """
            )
            self._insert_macro_row(connection, self._policy_row())
            self._insert_macro_row(connection, self._missing_row())
        if baseline:
            if parent_ready:
                target_rows = []
                labels = []
                for ticker in EXPECTED_PARENT_SCOPE["tickers"]:
                    for period in EXPECTED_PARENT_SCOPE["periods"]:
                        for metric in EXPECTED_PARENT_SCOPE["required_metrics"]:
                            observation_id = f"obs-{ticker}-{period}-{metric}"
                            target_rows.append(
                                (
                                    observation_id, ticker, "bank", metric, 1.2, "%",
                                    period, "2024-12-31", "point_in_time", "macro-source",
                                    "page:1", "valid", None,
                                )
                            )
                            labels.extend(
                                [
                                    (f"{observation_id}-a", observation_id, "checker-a"),
                                    (f"{observation_id}-b", observation_id, "checker-b"),
                                ]
                            )
                connection.executemany(
                    "INSERT INTO metric_observations VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                    target_rows,
                )
                connection.executemany(
                    """
                    INSERT INTO gold_labels
                    (label_id, target_id, label_type, expected_value, expected_judgment,
                     checker_id, checked_at, source_locator, resolution_note)
                    VALUES (?, ?, 'value_check', 1.2, NULL, ?,
                            '2026-09-11T00:00:00Z', 'page:1', 'matched')
                    """,
                    labels,
                )
                connection.executemany(
                    """
                    INSERT INTO coverage_summary
                    (summary_id, snapshot_id, ticker, metric, expected_count,
                     candidate_count, valid_count, missing_count, coverage_ratio)
                    VALUES (?, ?, ?, ?, 4, 4, 4, 0, 1.0)
                    """,
                    [
                        (
                            f"{EXPECTED_PARENT_SNAPSHOT_ID}:{ticker}:{metric}",
                            EXPECTED_PARENT_SNAPSHOT_ID,
                            ticker,
                            metric,
                        )
                        for ticker in EXPECTED_PARENT_SCOPE["tickers"]
                        for metric in EXPECTED_PARENT_SCOPE["required_metrics"]
                    ],
                )
            else:
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

    def _materializer_artifacts(self, root: Path) -> dict[str, Path]:
        raw = root / "raw"
        raw.mkdir(parents=True)
        source_specs = {
            "sbv_policy_rates_history_api": (
                "history.json",
                "State Bank of Vietnam (SBV)",
                "official_headless_delivery_api",
                "SBV content structure 3450482; returned totalCount=1; record 3451452",
                "accepted_primary_reviewed",
            ),
            "sbv_policy_rates_overview_page": (
                "overview.html",
                "State Bank of Vietnam (SBV)",
                "official_web_page",
                "SBV Lãi suất page",
                "accepted_primary_reviewed",
            ),
            "sbv_policy_rates_regulated_page": (
                "regulated.html",
                "State Bank of Vietnam (SBV)",
                "official_web_page",
                "SBV Lãi suất NHNN quy định page",
                "reviewed_supporting_primary",
            ),
        }
        manifest_records = []
        paths: dict[str, Path] = {}
        for artifact_id, (filename, publisher, source_type, source_identity, status) in source_specs.items():
            path = raw / filename
            path.write_text(f"fixture acquisition artifact: {artifact_id}\n", encoding="utf-8")
            digest = hashlib.sha256(path.read_bytes()).hexdigest().upper()
            paths[artifact_id] = path
            manifest_records.append({
                "artifact_id": artifact_id,
                "indicator_id": MACRO_POLICY_RATE,
                "publisher": publisher,
                "source_type": source_type,
                "source_url": f"https://sbv.test/{artifact_id}",
                "retrieved_at_utc": "2026-09-11T00:00:00Z",
                "local_path": str(path),
                "sha256": digest,
                "source_identity": source_identity,
                "locator": "fixture locator",
                "candidate_status": status,
                "source_tier": "primary",
                "quality_status": "valid",
                "review_status": "reviewed",
                "notes": "fixture",
            })
        manifest_path = root / "macro-manifest.jsonl"
        manifest_path.write_text(
            "\n".join(json.dumps(item, ensure_ascii=False) for item in manifest_records) + "\n",
            encoding="utf-8",
        )

        candidate_path = root / "candidate-observations.json"
        candidate_path.write_text(
            json.dumps(
                {
                    "acquisition_id": "macro-fixture-v1",
                    "scope": {"period": MACRO_GOLD_PERIOD, "indicators": [MACRO_POLICY_RATE, MACRO_CREDIT_GROWTH]},
                    "gold_promotion": "not_performed",
                    "candidate_cells": [
                        {
                            "indicator_id": MACRO_POLICY_RATE,
                            "period": MACRO_GOLD_PERIOD,
                            "status": "DERIVABLE_FROM_OFFICIAL_INPUTS",
                            "quality_status": "candidate_reviewed_not_promoted",
                            "candidate_value": 4.5,
                            "unit": "percent_per_annum",
                            "definition": "SBV refinancing rate",
                            "observation_date": "2023-06-19",
                            "observation_date_semantics": "official effective-date event",
                            "as_of_date": "2024-12-31",
                            "as_of_date_semantics": "analytical alignment boundary",
                            "effective_from": "2023-06-19",
                            "period_basis": "quarter_end_state",
                            "alignment_method": "latest_effective_state_at_period_end_v1",
                            "transformation_version": "state_carry_forward_v1",
                            "source_series_id": "SBV.refinancing_rate",
                            "source_id": "sbv_policy_rates_history_api",
                            "input_observation_ids": [],
                            "source_locator": ["fixture title=19-06-2023", "fixture decision=1123/QĐ-NHNN"],
                            "source_evidence": {
                                "publisher": "State Bank of Vietnam",
                                "source_effective_date": "19/06/2023",
                                "source_effective_date_iso": "2023-06-19",
                                "decision_identity": "1123/QĐ-NHNN ngày 16/06/2023",
                            },
                            "source_adjudication_status": "READY_FOR_MACRO_GOLD",
                            "promotion_status": "not_promoted",
                        },
                        {
                            "indicator_id": MACRO_CREDIT_GROWTH,
                            "period": MACRO_GOLD_PERIOD,
                            "status": "UNAVAILABLE",
                            "candidate_value": None,
                            "unit": "percent",
                            "definition": "Total credit growth relative to end-2023",
                            "period_basis": "ytd_vs_end_2023",
                            "source_id": None,
                            "source_locator": [],
                            "source_adjudication_status": "PRIMARY_SOURCE_NOT_ESTABLISHED",
                            "quality_status": "missing",
                            "missing_reason": "DATA_UNAVAILABLE",
                        },
                    ],
                },
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )

        def source_check(artifact_id: str) -> dict[str, object]:
            digest = hashlib.sha256(paths[artifact_id].read_bytes()).hexdigest().upper()
            return {
                "artifact_id": artifact_id,
                "local_path": str(paths[artifact_id]),
                "expected_sha256": digest,
                "actual_sha256": digest,
                "hash_match": True,
            }

        policy_checks = {
            "specifically_refinancing_rate": "PASS",
            "value_exactly_4_5": "PASS",
            "effective_date_interpretation": "PASS: Decision 1123/QĐ-NHNN dated 16/06/2023; effective 19/06/2023",
            "locator_exact": "PASS",
            "no_later_change_on_or_before_cutoff": "PASS",
            "carry_forward_not_fabricated_observation": "PASS",
        }
        credit_checks = {
            "frozen_definition": True,
            "no_exact_q4_primary_observation": True,
            "no_official_year_end_stock_pair": True,
            "secondary_15_08_rejected": True,
            "accepted_missing_decision": True,
        }
        adjudication_path = root / "final-source-adjudication.json"
        adjudication_path.write_text(
            json.dumps(
                {
                    "scope": {"period": MACRO_GOLD_PERIOD, "indicators": [MACRO_POLICY_RATE, MACRO_CREDIT_GROWTH]},
                    "promotion_performed": False,
                    "policy_rate": {
                        "candidate": {
                            "reported_effective_from": "2023-06-19",
                            "source_observation_date": "2023-06-19",
                        },
                        "checker_a": {"checker_id": "policy-a", "result": "PASS", "source_checks": [source_check("sbv_policy_rates_history_api"), source_check("sbv_policy_rates_overview_page")], "checks": policy_checks},
                        "checker_b": {"checker_id": "policy-b", "result": "PASS", "source_checks": [source_check("sbv_policy_rates_history_api"), source_check("sbv_policy_rates_regulated_page")], "checks": policy_checks},
                        "final_candidate_status": "READY_FOR_MACRO_GOLD",
                    },
                    "credit_growth": {
                        "final_status": "PRIMARY_SOURCE_NOT_ESTABLISHED",
                        "missing_reason": "DATA_UNAVAILABLE",
                        "checker_a": {"checker_id": "credit-a", "result": "PASS", "checks": credit_checks},
                        "checker_b": {"checker_id": "credit-b", "result": "PASS", "checks": credit_checks},
                    },
                },
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )
        evidence_path = root / "evidence-package.json"
        evidence_path.write_text(
            json.dumps(
                {
                    "status": "candidate_only_not_gold",
                    "evidence": [
                        {"indicator_id": MACRO_POLICY_RATE, "resolved_effective_from": "2023-06-19"},
                        {"indicator_id": MACRO_POLICY_RATE, "resolved_effective_from": "2023-06-19"},
                    ],
                }
            ),
            encoding="utf-8",
        )
        return {
            "candidate": candidate_path,
            "adjudication": adjudication_path,
            "manifest": manifest_path,
            "evidence": evidence_path,
        }

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
        self.assertEqual(row, (4.5, "percent_per_annum", "2023-06-19", "2023-06-19", "2024-12-31", "latest_effective_state_at_period_end_v1", "state_carry_forward_v1"))

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

    def _macro_question(
        self,
        root: Path,
        *,
        issuers: tuple[str, ...] = ("VCB",),
        question_issuer: str = "VCB",
        periods: tuple[str, ...] = (MACRO_GOLD_PERIOD,),
        core_metrics: tuple[str, ...] = ("bank.roa",),
    ) -> Path:
        path = root / "macro-question.json"
        path.write_text(
            json.dumps({
                "schema_version": 1,
                "status": "test",
                "question_set_id": "macro-questions-v1",
                "scope": {"issuers": list(issuers), "periods": list(periods), "core_metrics": list(core_metrics)},
                "questions": [{
                    "id": "macro-q4", "issuer": question_issuer, "type": "macro_to_bank",
                    "period": MACRO_GOLD_PERIOD,
                    "macro_indicator_ids": [MACRO_POLICY_RATE, MACRO_CREDIT_GROWTH],
                    "bank_metric_ids": list(core_metrics),
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

    def test_materialization_correct_parent_records_lineage_coverage_and_preflight(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            base = self._db(root, baseline=True, parent_ready=True, include_macro=False)
            artifacts = self._materializer_artifacts(root / "artifacts")
            output = root / "macro-gold.sqlite"
            result = materialize_macro_gold_snapshot(
                base,
                output,
                artifacts["candidate"],
                artifacts["adjudication"],
                artifacts["manifest"],
                artifacts["evidence"],
            )
            connection = sqlite3.connect(output)
            metadata = connection.execute(
                "SELECT snapshot_id, status, config_json FROM snapshot_metadata"
            ).fetchone()
            coverage = connection.execute(
                "SELECT COUNT(*), COUNT(CASE WHEN snapshot_id = ? THEN 1 END), COUNT(CASE WHEN summary_id LIKE ? THEN 1 END) FROM coverage_summary",
                (result.snapshot_id, f"{result.snapshot_id}:%"),
            ).fetchone()
            policy = connection.execute(
                "SELECT value, observation_date, effective_from FROM macro_observations_v2 WHERE indicator_id = ?",
                (MACRO_POLICY_RATE,),
            ).fetchone()
            missing = connection.execute(
                "SELECT value, frequency, quality_status, reason, review_check_ids_json FROM macro_observations_v2 WHERE indicator_id = ?",
                (MACRO_CREDIT_GROWTH,),
            ).fetchone()
            connection.close()

            config = json.loads(metadata[2])
            lineage = config["macro_gold_lineage"]
            self.assertTrue(result.eligible)
            self.assertEqual(metadata[:2], (result.snapshot_id, "gold"))
            self.assertEqual(lineage["parent_snapshot_id"], EXPECTED_PARENT_SNAPSHOT_ID)
            self.assertEqual(lineage["macro_contract_version"], MACRO_GOLD_CONTRACT_VERSION)
            self.assertEqual(lineage["macro_period"], MACRO_GOLD_PERIOD)
            self.assertEqual(set(lineage["macro_indicator_ids"]), {MACRO_POLICY_RATE, MACRO_CREDIT_GROWTH})
            self.assertEqual(coverage, (12, 12, 12))
            self.assertEqual(policy, (4.5, "2023-06-19", "2023-06-19"))
            self.assertEqual(missing[0:4], (None, None, "missing", "DATA_UNAVAILABLE"))
            self.assertEqual(set(json.loads(missing[4])), {"credit-a", "credit-b"})

            run_config = ExperimentRunConfig(
                run_id="materialized-macro-run",
                snapshot_id=result.snapshot_id,
                question_set_id="macro-questions-v1",
                question_id="macro-q4",
                rubric_version="rubric-v1",
                prompt_version="prompt-v1",
                arm=ExperimentArm.SINGLE_AGENT,
                model_id="test-model",
                source_policy_id="primary-only-v1",
            )
            audit = audit_experiment_inputs(
                output,
                run_config,
                self._macro_question(
                    root,
                    issuers=tuple(EXPECTED_PARENT_SCOPE["tickers"]),
                    question_issuer="ACB",
                    periods=tuple(EXPECTED_PARENT_SCOPE["periods"]),
                    core_metrics=tuple(EXPECTED_PARENT_SCOPE["required_metrics"]),
                ),
                GoldConfig(
                    tickers=tuple(EXPECTED_PARENT_SCOPE["tickers"]),
                    periods=tuple(EXPECTED_PARENT_SCOPE["periods"]),
                    required_metrics=tuple(EXPECTED_PARENT_SCOPE["required_metrics"]),
                    min_manual_labels=2,
                    min_metric_coverage=1.0,
                ),
            )
        self.assertTrue(audit.eligible, audit.blockers)

    def test_materialization_wrong_parent_snapshot_fails_closed(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            base = self._db(root, baseline=True, parent_ready=True, include_macro=False)
            connection = sqlite3.connect(base)
            connection.execute("UPDATE snapshot_metadata SET snapshot_id = 'wrong-parent'")
            connection.commit()
            connection.close()
            artifacts = self._materializer_artifacts(root / "artifacts")
            with self.assertRaisesRegex(ValueError, "macro parent snapshot mismatch"):
                materialize_macro_gold_snapshot(
                    base,
                    root / "macro-gold.sqlite",
                    artifacts["candidate"],
                    artifacts["adjudication"],
                    artifacts["manifest"],
                    artifacts["evidence"],
                )

    def test_materialization_rejects_unreviewed_or_non_sbv_source_metadata(self):
        for field, invalid_value in (
            ("publisher", "Untrusted Publisher"),
            ("source_tier", "secondary"),
            ("candidate_status", "retrieved_pending_validation"),
        ):
            with self.subTest(field=field):
                with tempfile.TemporaryDirectory() as directory:
                    root = Path(directory)
                    base = self._db(root, parent_ready=True, include_macro=False)
                    artifacts = self._materializer_artifacts(root / "artifacts")
                    records = [
                        json.loads(line)
                        for line in artifacts["manifest"].read_text(encoding="utf-8").splitlines()
                    ]
                    records[0][field] = invalid_value
                    artifacts["manifest"].write_text(
                        "\n".join(json.dumps(record, ensure_ascii=False) for record in records) + "\n",
                        encoding="utf-8",
                    )
                    with self.assertRaisesRegex(ValueError, "macro source"):
                        materialize_macro_gold_snapshot(
                            base,
                            root / "macro-gold.sqlite",
                            artifacts["candidate"],
                            artifacts["adjudication"],
                            artifacts["manifest"],
                            artifacts["evidence"],
                        )

    def test_missing_macro_schema_rejects_fabricated_frequency_and_requires_reviews(self):
        with self.assertRaisesRegex(ValueError, "must not invent source frequency"):
            MacroObservationV2(
                **self._missing_row().model_dump(exclude={"frequency", "review_check_ids"}),
                frequency="quarterly",
                review_check_ids=("credit-checker-a", "credit-checker-b"),
            )
        with self.assertRaisesRegex(ValueError, "requires two independent review checks"):
            MacroObservationV2(
                **self._missing_row().model_dump(exclude={"review_check_ids"}),
                review_check_ids=(),
            )


if __name__ == "__main__":
    unittest.main()
