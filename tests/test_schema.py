from datetime import datetime
import unittest

from pydantic import ValidationError

from thesis_data.schema import (
    AgentPayload,
    AgentStatus,
    CoverageSummary,
    DerivedMetric,
    EvidenceSnippet,
    GoldConfig,
    MetricObservation,
    QualityStatus,
    SourceRecord,
)


class SchemaTests(unittest.TestCase):
    def test_numeric_contracts_reject_non_finite_values(self):
        with self.assertRaisesRegex(ValidationError, "finite"):
            AgentPayload(
                agent_id="company",
                status=AgentStatus.SUCCESS,
                ticker="VCB",
                period="2024_Q1",
                metrics={"bank.npl_g35": float("nan")},
            )

        with self.assertRaisesRegex(ValidationError, "finite"):
            MetricObservation(
                observation_id="obs-1",
                ticker="VCB",
                sector="bank",
                metric="bank.npl_g35",
                value=float("inf"),
                unit="%",
                period="2024_Q1",
                period_basis="point_in_time",
                source_id="source-1",
                source_locator="page:1",
                quality_status=QualityStatus.VALID,
            )

    def test_gold_config_defaults_to_two_independent_checkers(self):
        config = GoldConfig(
            tickers=("VCB",),
            periods=("2024_Q1",),
            required_metrics=("bank.npl_g35",),
        )

        self.assertEqual(config.min_independent_checkers, 2)

    def test_coverage_summary_requires_bounded_ratio(self):
        summary = CoverageSummary(
            summary_id="coverage-1",
            snapshot_id="gold-1",
            ticker="VCB",
            metric="bank.npl_g35",
            expected_count=8,
            candidate_count=8,
            valid_count=8,
            missing_count=0,
            coverage_ratio=1.0,
        )

        self.assertEqual(summary.coverage_ratio, 1.0)

        with self.assertRaises(ValueError):
            CoverageSummary(
                summary_id="coverage-2",
                snapshot_id="gold-1",
                ticker="VCB",
                metric="bank.npl_g35",
                expected_count=8,
                candidate_count=8,
                valid_count=9,
                missing_count=0,
                coverage_ratio=1.125,
            )
    def test_source_record_requires_identity_and_hash(self):
        with self.assertRaises(ValidationError):
            SourceRecord(
                source_id="",
                source_type="filing",
                source_tier="primary",
                source_url="https://example.test/source",
                retrieved_at="2026-09-04T00:00:00Z",
                local_path="data/source.pdf",
                content_hash="",
                publisher="Issuer",
                license_note="public",
            )

    def test_issuer_ir_is_a_first_class_source_type(self):
        source = SourceRecord(
            source_id="ir-1",
            source_type="issuer_ir",
            source_tier="primary",
            source_url="https://issuer.test/investors",
            retrieved_at=datetime(2026, 9, 4),
            local_path="data/ir.html",
            content_hash="sha256:ir",
            publisher="issuer",
            license_note="public issuer page",
        )
        self.assertEqual(source.source_type.value, "issuer_ir")

    def test_missing_metric_requires_reason(self):
        with self.assertRaises(ValidationError):
            MetricObservation(
                observation_id="obs-1",
                ticker="VCB",
                sector="bank",
                metric="bank.npl_g35",
                value=None,
                unit="%",
                period="2024_Q1",
                period_basis="point_in_time",
                source_id="source-1",
                quality_status=QualityStatus.MISSING,
            )

    def test_missing_metric_may_omit_source_unit_and_period_basis(self):
        observation = MetricObservation(
            observation_id="missing-obs-1",
            ticker="ACB",
            sector="bank",
            metric="bank.roa",
            value=None,
            unit=None,
            period="2024_Q1",
            period_basis=None,
            source_id=None,
            quality_status=QualityStatus.MISSING,
            reason="no official candidate route in the bounded pilot",
        )

        self.assertIsNone(observation.source_id)
        self.assertIsNone(observation.unit)
        self.assertIsNone(observation.period_basis)

    def test_derived_metric_retains_inputs_and_formula_version(self):
        result = DerivedMetric(
            derived_id="derived-1",
            ticker="VCB",
            metric="bank.cir",
            value=32.5,
            unit="%",
            period="2024_Q1",
            period_basis="quarter_only",
            input_observation_ids=["obs-expense", "obs-income"],
            formula_version="cir-v1",
            quality_status=QualityStatus.VALID,
        )
        self.assertEqual(result.input_observation_ids, ["obs-expense", "obs-income"])
        self.assertEqual(result.formula_version, "cir-v1")

    def test_paginated_evidence_requires_page_number(self):
        with self.assertRaises(ValidationError):
            EvidenceSnippet(
                evidence_id="evidence-1",
                source_id="source-1",
                source_document="annual-report.pdf",
                page_number=None,
                section_name="Risk",
                period="2024_Q1",
                ticker="VCB",
                quote="Quoted text",
                parser_status="text_layer",
                is_paginated=True,
            )
