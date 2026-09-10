import unittest

from thesis_data.composite_schema import CompositeAnalysisPayload, CompositeClaim, CompositeSubreport
from thesis_data.schema import AgentPayload, AgentStatus
from thesis_data.workload_contract import AnalysisTask, WorkloadTier


class CompositeSchemaTests(unittest.TestCase):
    def payload(self, ticker: str = "ACB", period: str = "2024_Q4") -> AgentPayload:
        return AgentPayload(
            agent_id="company",
            status=AgentStatus.SUCCESS,
            ticker=ticker,
            period=period,
            metrics={"bank.roa": 2.1},
            metric_units={"bank.roa": "%"},
            metric_periods={"bank.roa": period},
            observation_ids=[f"obs-{ticker.lower()}"],
            source_ids=[f"source-{ticker.lower()}"],
        )

    def test_subreport_requires_matching_payload_scope(self):
        with self.assertRaisesRegex(ValueError, "payload ticker does not match subreport issuer"):
            CompositeSubreport(
                issuer="ACB",
                period="2024_Q4",
                task=AnalysisTask.SNAPSHOT,
                payload=self.payload("TCB"),
            )

    def test_composite_payload_rejects_duplicate_subreport_keys(self):
        subreport = CompositeSubreport(
            issuer="ACB",
            period="2024_Q4",
            task=AnalysisTask.SNAPSHOT,
            payload=self.payload(),
        )
        with self.assertRaisesRegex(ValueError, "duplicate composite subreport"):
            CompositeAnalysisPayload(
                agent_id="single_agent",
                status=AgentStatus.SUCCESS,
                question_id="ACB_composite_2024",
                tier=WorkloadTier.TIER_2,
                issuers=("ACB",),
                periods=("2024_Q4",),
                metric_ids=("bank.roa",),
                subreports=(subreport, subreport),
                findings=["complete"],
            )

    def test_composite_payload_preserves_missing_conflict_register(self):
        result = CompositeAnalysisPayload(
            agent_id="orchestrator",
            status=AgentStatus.PARTIAL,
            question_id="ACB_composite_2024",
            tier=WorkloadTier.TIER_2,
            issuers=("ACB",),
            periods=("2024_Q1", "2024_Q4"),
            metric_ids=("bank.roa",),
            subreports=(),
            missing_conflict_register=(
                "ACB:2024_Q1:bank.roa:missing_basis",
            ),
            quality_flags=["partial_scope"],
            findings=["Q1 cannot be inferred"],
        )

        self.assertEqual(result.missing_conflict_register[0], "ACB:2024_Q1:bank.roa:missing_basis")
        self.assertEqual(result.status, AgentStatus.PARTIAL)

    def test_composite_payload_accepts_scoped_claim(self):
        claim = CompositeClaim(
            claim_id="q4-roa",
            claim_type="comparison",
            title="ROA leader",
            claim="TCB has the highest ROA in Q4.",
            interpretation="This is a cross-sectional profitability signal.",
            limitation="It does not establish causality.",
            support="source_locator_only",
            data_refs=("TCB|2024_Q4|bank.roa",),
            source_ids=("source-tcb",),
        )
        result = CompositeAnalysisPayload(
            agent_id="orchestrator",
            status=AgentStatus.SUCCESS,
            question_id="TCB_composite_2024",
            tier=WorkloadTier.TIER_2,
            issuers=("TCB",),
            periods=("2024_Q4",),
            metric_ids=("bank.roa",),
            claims=[claim],
        )
        self.assertEqual(result.claims[0].data_refs, ("TCB|2024_Q4|bank.roa",))


if __name__ == "__main__":
    unittest.main()
