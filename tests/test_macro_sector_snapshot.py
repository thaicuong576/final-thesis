"""Tests for macro and sector observations ingestion into the operational snapshot (MACRO-INGEST)."""

from __future__ import annotations

import csv
import importlib.util
import shutil
import sqlite3
import tempfile
import unittest
from pathlib import Path

from thesis_api.adaptive_runtime import _AdaptiveRun, _plan_request
from thesis_api.agents import MacroSpecialistAgent
from thesis_api.schemas import AnalysisRequest
from thesis_api.service import AnalysisBlocked, fetch_macro_context
from thesis_data.analysis_plan import AnalysisAgent
from thesis_data.canonical_sqlite_provider import CanonicalSqliteDatasetProvider
from thesis_data.dataset_contract import (
    AnalyticalLevel,
    DatasetEntityType,
    DatasetRef,
    SupportedOperation,
)
from thesis_data.schema import QualityStatus

ROOT = Path(__file__).resolve().parents[1]
_spec = importlib.util.spec_from_file_location("build_quarterly_snapshot", ROOT / "scripts" / "build_quarterly_snapshot.py")
builder = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(builder)

URL = "https://example.org/{b}-{p}.pdf"


def _bank_rows(bank: str, scale: int) -> list[list[str]]:
    """Two years of synthetic inputs (billion VND) for one bank."""
    rows = []
    for period, assets, equity, pat in (
        ("2023_Q2", None, None, 40), ("2023_Q4", 1000, 100, 90),
        ("2024_Q2", 1100, 110, 50), ("2024_Q4", 1200, 120, 110),
    ):
        p = {
            "bank.input.profit_after_tax": pat * scale,
            "bank.input.parent_attributable_profit": pat * scale - 1,
        }
        if assets:
            p.update({
                "bank.input.total_assets": assets * scale,
                "bank.input.total_equity": equity * scale,
                "bank.input.non_controlling_interests": 2,
            })
        if period.startswith("2024"):
            p.update({
                "bank.input.npl_group_3_balance": 3, "bank.input.npl_group_4_balance": 4,
                "bank.input.npl_group_5_balance": 5, "bank.input.gross_customer_loans": 600 * scale,
                "bank.input.loan_loss_provisions": 15,
            })
        for metric, value in p.items():
            basis = "ytd" if metric in builder.YTD else "point_in_time"
            rows.append([bank, metric, period, str(value), "billion_vnd", basis,
                         "pdf_page=3; printed_page=1; section=statement", URL.format(b=bank, p=period), ""])
    return rows


class MacroSectorSnapshotTest(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = Path(tempfile.mkdtemp())
        self.inputs = self.tmp / "inputs.csv"
        with self.inputs.open("w", encoding="utf-8", newline="") as f:
            w = csv.writer(f)
            w.writerow(["entity_id", "metric_id", "period_id", "value", "unit", "period_basis",
                        "source_locator", "source_url", "source_sha256"])
            for bank, scale in (("AAA", 1), ("BBB", 2), ("CCC", 3)):
                w.writerows(_bank_rows(bank, scale))

        self.macro_inputs = self.tmp / "macro_inputs.csv"
        # 2 macro indicators x 3 periods + 1 sector = 7 rows
        # 1 secondary row: macro.credit_growth at 2024_Q3
        # 1 missing cell: macro.policy_rate at 2024_Q3
        macro_rows = [
            ["entity_id", "metric_id", "period_id", "value", "unit", "period_basis",
             "source_locator", "source_url", "source_sha256", "source_tier", "scope"],
            ["VN", "macro.policy_rate", "2024_Q2", "4.5", "%", "point_in_time",
             "Quyết định 1123/QĐ-NHNN, tr. 1", "https://sbv.gov.vn/rate-2024q2.pdf", "", "primary", "system"],
            ["VN", "macro.policy_rate", "2024_Q3", "", "%", "point_in_time",
             "Quyết định 1500/QĐ-NHNN, tr. 1", "https://sbv.gov.vn/rate-2024q3.pdf", "", "primary", "system"],
            ["VN", "macro.policy_rate", "2024_Q4", "4.5", "%", "point_in_time",
             "Quyết định 2415/QĐ-NHNN, tr. 1", "https://sbv.gov.vn/rate-2024q4.pdf", "", "primary", "system"],
            ["VN", "macro.credit_growth", "2024_Q2", "6.0", "%", "point_in_time",
             "Báo cáo NHNN 6T2024, tr. 5", "https://sbv.gov.vn/credit-2024q2.pdf", "", "primary", "system"],
            ["VN", "macro.credit_growth", "2024_Q3", "9.0", "%", "point_in_time",
             "Báo cáo CTCK Bản Việt, tr. 12", "https://vcsc.com.vn/macro-2024q3.pdf", "", "secondary", "system"],
            ["VN", "macro.credit_growth", "2024_Q4", "15.08", "%", "point_in_time",
             "Họp báo ngành ngân hàng 2024, tr. 2", "https://sbv.gov.vn/credit-2024q4.pdf", "", "primary", "system"],
            ["VN", "sector.system_npl_ratio", "2024_Q4", "1.93", "%", "point_in_time",
             "Báo cáo NHNN cuối năm 2024, tr. 8", "https://sbv.gov.vn/sector-npl-2024q4.pdf", "", "primary", "system"],
        ]
        with self.macro_inputs.open("w", encoding="utf-8", newline="") as f:
            csv.writer(f).writerows(macro_rows)

    def tearDown(self) -> None:
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_build_with_macro_inputs(self) -> None:
        out = self.tmp / "ops_macro.sqlite"
        manifest = builder.build(
            self.inputs,
            out,
            macro_inputs_csv=self.macro_inputs,
            ratio_periods={"2024_Q2", "2024_Q4"},
        )

        dataset_ref = DatasetRef(
            dataset_id=manifest["dataset_id"],
            dataset_snapshot_id=manifest["dataset_snapshot_id"],
        )
        provider = CanonicalSqliteDatasetProvider(out)
        catalog = provider.get_capabilities(dataset_ref)

        # 1. VN entity and macro/sector metrics are in catalog
        entity_ids = {e.entity_id for e in catalog.entities}
        self.assertIn("VN", entity_ids)
        vn_entity = next(e for e in catalog.entities if e.entity_id == "VN")
        self.assertEqual(vn_entity.entity_type, DatasetEntityType.MACRO)
        self.assertEqual(vn_entity.display_name, "Việt Nam – vĩ mô và ngành")

        metric_ids = {m.metric_id for m in catalog.metrics}
        self.assertIn("macro.policy_rate", metric_ids)
        self.assertIn("macro.credit_growth", metric_ids)
        self.assertIn("sector.system_npl_ratio", metric_ids)

        policy_rate_m = next(m for m in catalog.metrics if m.metric_id == "macro.policy_rate")
        self.assertEqual(policy_rate_m.analytical_level, AnalyticalLevel.MACRO)
        credit_growth_m = next(m for m in catalog.metrics if m.metric_id == "macro.credit_growth")
        self.assertEqual(credit_growth_m.analytical_level, AnalyticalLevel.MACRO)
        sector_npl_m = next(m for m in catalog.metrics if m.metric_id == "sector.system_npl_ratio")
        self.assertEqual(sector_npl_m.analytical_level, AnalyticalLevel.SECTOR)

        self.assertIn(SupportedOperation.GET_MACRO_OBSERVATION, catalog.supported_operations)

        # 2. get_macro_observation returns correct value/source for primary rows
        obs_rate_q2 = provider.get_macro_observation(dataset_ref, "VN", "2024_Q2", "macro.policy_rate")
        self.assertIsNotNone(obs_rate_q2)
        self.assertEqual(obs_rate_q2.value, 4.5)
        self.assertEqual(obs_rate_q2.validation_status, QualityStatus.VALID)
        self.assertEqual(obs_rate_q2.source_locator, "Quyết định 1123/QĐ-NHNN, tr. 1")

        obs_credit_q4 = provider.get_macro_observation(dataset_ref, "VN", "2024_Q4", "macro.credit_growth")
        self.assertIsNotNone(obs_credit_q4)
        self.assertEqual(obs_credit_q4.value, 15.08)
        self.assertEqual(obs_credit_q4.validation_status, QualityStatus.VALID)
        self.assertEqual(obs_credit_q4.source_locator, "Họp báo ngành ngân hàng 2024, tr. 2")

        # 3. Secondary row is NOT accepted
        obs_credit_q3 = provider.get_macro_observation(dataset_ref, "VN", "2024_Q3", "macro.credit_growth")
        self.assertIsNotNone(obs_credit_q3)
        self.assertNotEqual(obs_credit_q3.validation_status, QualityStatus.VALID)
        self.assertEqual(obs_credit_q3.validation_status, QualityStatus.PENDING_VALIDATION)

        # 4. Missing cell has NO observation (None)
        obs_rate_q3 = provider.get_macro_observation(dataset_ref, "VN", "2024_Q3", "macro.policy_rate")
        self.assertIsNone(obs_rate_q3)

        # 5. Sector metric is queryable via get_metric
        obs_sector = provider.get_metric(dataset_ref, "VN", "2024_Q4", "sector.system_npl_ratio")
        self.assertIsNotNone(obs_sector)
        self.assertEqual(obs_sector.value, 1.93)
        self.assertEqual(obs_sector.validation_status, QualityStatus.VALID)

    def test_build_without_macro_inputs_is_identical(self) -> None:
        """Without --macro-inputs, snapshot observations table is byte-for-byte identical."""
        out1 = self.tmp / "build1.sqlite"
        out2 = self.tmp / "build2.sqlite"

        builder.build(self.inputs, out1, ratio_periods={"2024_Q2", "2024_Q4"})
        builder.build(self.inputs, out2, macro_inputs_csv=None, ratio_periods={"2024_Q2", "2024_Q4"})

        conn1 = sqlite3.connect(out1)
        conn2 = sqlite3.connect(out2)
        try:
            cols = [
                d[0]
                for d in conn1.execute("SELECT * FROM observations LIMIT 1").description
                if d[0] != "review_json"
            ]
            col_list = ", ".join(cols)
            rows1 = conn1.execute(f"SELECT {col_list} FROM observations ORDER BY observation_id").fetchall()
            rows2 = conn2.execute(f"SELECT {col_list} FROM observations ORDER BY observation_id").fetchall()
            self.assertEqual(len(rows1), len(rows2))
            self.assertEqual(rows1, rows2)

            entities1 = conn1.execute("SELECT * FROM entities ORDER BY entity_id").fetchall()
            entities2 = conn2.execute("SELECT * FROM entities ORDER BY entity_id").fetchall()
            self.assertEqual(entities1, entities2)
            self.assertNotIn("VN", [r[0] for r in entities1])
        finally:
            conn1.close()
            conn2.close()

    def test_fetch_macro_context(self) -> None:
        """fetch_macro_context retrieves accepted VN macro indicators from snapshot."""
        out = self.tmp / "ops_macro_fetch.sqlite"
        builder.build(
            self.inputs,
            out,
            macro_inputs_csv=self.macro_inputs,
            ratio_periods={"2024_Q2", "2024_Q4"},
        )
        conn = sqlite3.connect(out)
        try:
            # 2024_Q2 has both rate (4.5) and credit_growth (6.0)
            dto_q2 = fetch_macro_context(conn, "2024_Q2")
            self.assertEqual(dto_q2.sbv_policy_rate, 4.5)
            self.assertEqual(dto_q2.system_credit_growth, 6.0)
            self.assertIn("Quyết định 1123/QĐ-NHNN, tr. 1", dto_q2.source)
            self.assertIn("Báo cáo NHNN 6T2024, tr. 5", dto_q2.source)

            # 2024_Q3: rate is missing cell, credit_growth is secondary (not valid)
            dto_q3 = fetch_macro_context(conn, "2024_Q3")
            self.assertIsNone(dto_q3.sbv_policy_rate)
            self.assertIsNone(dto_q3.system_credit_growth)

            # 2024_Q4: rate is 4.5, credit_growth is 15.08
            dto_q4 = fetch_macro_context(conn, "2024_Q4")
            self.assertEqual(dto_q4.sbv_policy_rate, 4.5)
            self.assertEqual(dto_q4.system_credit_growth, 15.08)
        finally:
            conn.close()

        # Database built without macro inputs returns empty MacroContextDTO
        out_no_macro = self.tmp / "ops_no_macro.sqlite"
        builder.build(self.inputs, out_no_macro, ratio_periods={"2024_Q2", "2024_Q4"})
        conn_no = sqlite3.connect(out_no_macro)
        try:
            dto_none = fetch_macro_context(conn_no, "2024_Q2")
            self.assertIsNone(dto_none.sbv_policy_rate)
            self.assertIsNone(dto_none.system_credit_growth)
        finally:
            conn_no.close()

    def test_macro_specialist_agent_grounded_execution(self) -> None:
        """MacroSpecialistAgent executes grounded offline analysis with real numbers."""
        out = self.tmp / "ops_macro_agent.sqlite"
        builder.build(
            self.inputs,
            out,
            macro_inputs_csv=self.macro_inputs,
            ratio_periods={"2024_Q2", "2024_Q4"},
        )
        conn = sqlite3.connect(out)
        try:
            agent = MacroSpecialistAgent()
            res = agent.execute(conn, "2024_Q2")
            self.assertEqual(res["specialist_id"], "macro")
            self.assertEqual(res["macro_context"]["sbv_policy_rate"], 4.5)
            self.assertEqual(res["macro_context"]["system_credit_growth"], 6.0)
            self.assertTrue(any("4.5%" in f for f in res["findings"]))
            self.assertTrue(any("6.0%" in f for f in res["findings"]))

            # On empty/missing period
            res_q3 = agent.execute(conn, "2024_Q3")
            self.assertTrue(any("Chưa có dữ liệu vĩ mô" in f for f in res_q3["findings"]))
        finally:
            conn.close()

    def test_macro_query_routing_and_claim_creation(self) -> None:
        """Macro queries on snapshot with macro inputs succeed and create provider-backed claims."""
        out = self.tmp / "ops_macro_plan.sqlite"
        manifest = builder.build(
            self.inputs,
            out,
            macro_inputs_csv=self.macro_inputs,
            ratio_periods={"2024_Q2", "2024_Q4"},
        )
        dataset_ref = DatasetRef(
            dataset_id=manifest["dataset_id"],
            dataset_snapshot_id=manifest["dataset_snapshot_id"],
        )
        provider = CanonicalSqliteDatasetProvider(out)
        catalog = provider.get_capabilities(dataset_ref)

        # 1. Macro query with Vietnamese quarter
        req = AnalysisRequest(query="Lãi suất điều hành quý 2/2024 là bao nhiêu?")
        plan_res = _plan_request(req, dataset_ref, catalog)
        plan, target, periods, company_metric_ids, peer_ids, macro_metric_ids = plan_res
        self.assertIsNone(target)
        self.assertEqual(periods, ("2024_Q2",))
        self.assertIn("macro.policy_rate", macro_metric_ids)
        self.assertIn(AnalysisAgent.MACRO, plan.requirements[0].required_agents)

        # 2. Execute via _AdaptiveRun
        runner = _AdaptiveRun(
            provider=provider,
            dataset_ref=dataset_ref,
            catalog=catalog,
            request=req,
            settings=None,
            critic=None,
            writer=None,
            emit=lambda *a, **k: None,
            client=None,
        )
        report = runner.execute()
        self.assertIn(report.status, {"completed", "accepted_with_limitations"})
        self.assertGreater(len(report.atomic_claims), 0)
        macro_claim = report.atomic_claims[0]
        self.assertEqual(macro_claim.capability, "macro")
        self.assertEqual(macro_claim.stage1_status, "accepted")
        self.assertIn("4.5", macro_claim.statement)

        self.assertGreater(len(report.evidence_trail), 0)
        trail_item = report.evidence_trail[0]
        self.assertEqual(trail_item.ticker, "VN")
        self.assertEqual(trail_item.period, "2024_Q2")
        self.assertEqual(trail_item.value, 4.5)
        self.assertEqual(trail_item.table_locator, "Quyết định 1123/QĐ-NHNN, tr. 1")
        self.assertEqual(trail_item.source_doc, "https://sbv.gov.vn/rate-2024q2.pdf")

    def test_macro_query_on_snapshot_without_macro_is_blocked(self) -> None:
        """Macro queries on snapshot without macro inputs are rejected with unsupported_macro_scope."""
        out = self.tmp / "ops_no_macro_plan.sqlite"
        manifest = builder.build(self.inputs, out, ratio_periods={"2024_Q2", "2024_Q4"})
        dataset_ref = DatasetRef(
            dataset_id=manifest["dataset_id"],
            dataset_snapshot_id=manifest["dataset_snapshot_id"],
        )
        provider = CanonicalSqliteDatasetProvider(out)
        catalog = provider.get_capabilities(dataset_ref)

        req = AnalysisRequest(query="Lãi suất điều hành quý 2/2024 là bao nhiêu?")
        with self.assertRaises(AnalysisBlocked) as ctx:
            _plan_request(req, dataset_ref, catalog)
        self.assertEqual(ctx.exception.code, "unsupported_macro_scope")

    def _build_rich_macro_snapshot(self, out_name: str = "ops_rich_macro.sqlite") -> tuple[CanonicalSqliteDatasetProvider, DatasetRef, Any]:
        rich_macro_csv = self.tmp / f"rich_macro_{out_name}.csv"
        rows = [
            ["entity_id", "metric_id", "period_id", "value", "unit", "period_basis",
             "source_locator", "source_url", "source_sha256", "source_tier", "scope"],
            ["VN", "macro.policy_rate", "2024_Q2", "4.5", "%", "point_in_time",
             "Quyết định 1123/QĐ-NHNN, tr. 1", "https://sbv.gov.vn/rate-2024q2.pdf", "", "primary", "system"],
            ["VN", "macro.credit_growth_yoy", "2024_Q2", "15.0", "%", "point_in_time",
             "Báo cáo NHNN 6T2024, tr. 5", "https://sbv.gov.vn/credit-2024q2.pdf", "", "primary", "system"],
            ["VN", "macro.credit_growth_ytd", "2024_Q2", "6.0", "%", "ytd",
             "Báo cáo NHNN 6T2024, tr. 6", "https://sbv.gov.vn/credit-ytd-2024q2.pdf", "", "primary", "system"],
            ["VN", "macro.gdp_growth_yoy", "2024_Q2", "6.42", "%", "point_in_time",
             "TCTK Báo cáo KT-XH Q2/2024, tr. 1", "https://gso.gov.vn/gdp-2024q2.pdf", "", "primary", "system"],
            ["VN", "sector.system_npl_ratio", "2024_Q2", "1.85", "%", "point_in_time",
             "Báo cáo NHNN 6T2024, tr. 8", "https://sbv.gov.vn/sector-npl-2024q2.pdf", "", "primary", "system"],
            ["VN", "sector.system_npl_ratio_excl_special_control", "2024_Q2", "1.50", "%", "point_in_time",
             "Báo cáo NHNN 6T2024, tr. 9", "https://sbv.gov.vn/sector-npl-excl-2024q2.pdf", "", "primary", "system"],
        ]
        with rich_macro_csv.open("w", encoding="utf-8", newline="") as f:
            csv.writer(f).writerows(rows)
        out = self.tmp / out_name
        manifest = builder.build(
            self.inputs,
            out,
            macro_inputs_csv=rich_macro_csv,
            ratio_periods={"2024_Q2", "2024_Q4"},
        )
        dataset_ref = DatasetRef(
            dataset_id=manifest["dataset_id"],
            dataset_snapshot_id=manifest["dataset_snapshot_id"],
        )
        provider = CanonicalSqliteDatasetProvider(out)
        catalog = provider.get_capabilities(dataset_ref)
        return provider, dataset_ref, catalog

    def test_a_system_npl_ratio_claim_created(self) -> None:
        """(a) snapshot có sector.system_npl_ratio + macro: hỏi 'tỷ lệ nợ xấu toàn hệ thống quý 2/2024' -> báo cáo có khẳng định lấy từ sector.system_npl_ratio."""
        provider, dataset_ref, catalog = self._build_rich_macro_snapshot("snap_a.sqlite")
        req = AnalysisRequest(query="Tỷ lệ nợ xấu toàn hệ thống quý 2/2024 là bao nhiêu?")
        plan_res = _plan_request(req, dataset_ref, catalog)
        plan, target, periods, company_metric_ids, peer_ids, macro_metric_ids = plan_res
        self.assertIsNone(target)
        self.assertIn("sector.system_npl_ratio", macro_metric_ids)

        runner = _AdaptiveRun(
            provider=provider,
            dataset_ref=dataset_ref,
            catalog=catalog,
            request=req,
            settings=None,
            critic=None,
            writer=None,
            emit=lambda *a, **k: None,
            client=None,
        )
        report = runner.execute()
        self.assertIn(report.status, {"completed", "accepted_with_limitations"})
        npl_claims = [
            c for c in report.atomic_claims
            if "1.85" in c.statement
        ]
        self.assertEqual(len(npl_claims), 1)
        self.assertEqual(npl_claims[0].capability, "macro")
        self.assertEqual(npl_claims[0].stage1_status, "accepted")
        self.assertIn("1.85", npl_claims[0].statement)

    def test_b_credit_growth_query_selects_credit_not_gdp(self) -> None:
        """(b) hỏi về tín dụng chọn đúng các mã credit_growth*, không kéo GDP."""
        provider, dataset_ref, catalog = self._build_rich_macro_snapshot("snap_b.sqlite")
        req = AnalysisRequest(query="Tăng trưởng tín dụng quý 2/2024 là bao nhiêu?")
        plan_res = _plan_request(req, dataset_ref, catalog)
        plan, target, periods, company_metric_ids, peer_ids, macro_metric_ids = plan_res
        self.assertIsNone(target)
        self.assertTrue(any(m.startswith("macro.credit_growth") for m in macro_metric_ids))
        self.assertNotIn("macro.gdp_growth_yoy", macro_metric_ids)
        self.assertFalse(any("gdp" in m for m in macro_metric_ids))

    def test_c_general_macro_context_query_takes_all_macro_metrics(self) -> None:
        """(c) câu hỏi chung 'bối cảnh vĩ mô' vẫn lấy mọi chỉ tiêu macro."""
        provider, dataset_ref, catalog = self._build_rich_macro_snapshot("snap_c.sqlite")
        req = AnalysisRequest(query="Bối cảnh vĩ mô quý 2/2024 như thế nào?")
        plan_res = _plan_request(req, dataset_ref, catalog)
        plan, target, periods, company_metric_ids, peer_ids, macro_metric_ids = plan_res
        self.assertIsNone(target)
        expected_macro_ids = tuple(
            m.metric_id for m in catalog.metrics if m.analytical_level is AnalyticalLevel.MACRO
        )
        self.assertEqual(macro_metric_ids, expected_macro_ids)
        self.assertIn("macro.policy_rate", macro_metric_ids)
        self.assertIn("macro.gdp_growth_yoy", macro_metric_ids)

    def test_d_snapshot_without_macro_blocks_unsupported_macro_scope(self) -> None:
        """(d) snapshot không có macro vẫn chặn unsupported_macro_scope."""
        out = self.tmp / "ops_no_macro_plan2.sqlite"
        manifest = builder.build(self.inputs, out, ratio_periods={"2024_Q2", "2024_Q4"})
        dataset_ref = DatasetRef(
            dataset_id=manifest["dataset_id"],
            dataset_snapshot_id=manifest["dataset_snapshot_id"],
        )
        provider = CanonicalSqliteDatasetProvider(out)
        catalog = provider.get_capabilities(dataset_ref)

        for query in (
            "Tỷ lệ nợ xấu toàn hệ thống quý 2/2024 là bao nhiêu?",
            "Tăng trưởng tín dụng quý 2/2024?",
            "Bối cảnh vĩ mô quý 2/2024?",
        ):
            req = AnalysisRequest(query=query)
            with self.assertRaises(AnalysisBlocked) as ctx:
                _plan_request(req, dataset_ref, catalog)
            self.assertEqual(ctx.exception.code, "unsupported_macro_scope")

    def test_e_system_npl_ratio_and_excl_special_control_distinct_claims(self) -> None:
        """(e) chỉ tiêu sector.system_npl_ratio_excl_special_control KHÔNG bị gộp chung với sector.system_npl_ratio (hai khẳng định riêng, mỗi cái ghi đúng mã)."""
        provider, dataset_ref, catalog = self._build_rich_macro_snapshot("snap_e.sqlite")
        req = AnalysisRequest(query="Tỷ lệ nợ xấu toàn hệ thống quý 2/2024 là bao nhiêu?")
        runner = _AdaptiveRun(
            provider=provider,
            dataset_ref=dataset_ref,
            catalog=catalog,
            request=req,
            settings=None,
            critic=None,
            writer=None,
            emit=lambda *a, **k: None,
            client=None,
        )
        report = runner.execute()
        self.assertIn(report.status, {"completed", "accepted_with_limitations"})
        claim_npl = next(
            (c for c in report.atomic_claims if "1.85" in c.statement),
            None,
        )
        claim_excl = next(
            (c for c in report.atomic_claims if "1.5" in c.statement),
            None,
        )
        self.assertIsNotNone(claim_npl)
        self.assertIsNotNone(claim_excl)
        self.assertNotEqual(claim_npl.claim_id, claim_excl.claim_id)
        self.assertNotEqual(claim_npl.statement, claim_excl.statement)

        # Check evidence trail rows
        npl_trail = next(
            (t for t in report.evidence_trail if t.value == 1.85),
            None,
        )
        excl_trail = next(
            (t for t in report.evidence_trail if t.value == 1.50),
            None,
        )
        self.assertIsNotNone(npl_trail)
        self.assertIsNotNone(excl_trail)
        self.assertNotEqual(npl_trail.claim_id, excl_trail.claim_id)

    def test_fetch_macro_context_credit_growth_priority_and_basis(self) -> None:
        """fetch_macro_context prioritizes credit_growth_yoy > credit_growth_ytd > credit_growth and records basis."""
        test_db = self.tmp / "test_credit_priority.sqlite"
        conn = sqlite3.connect(test_db)
        try:
            conn.execute("""
                CREATE TABLE observations (
                    observation_id TEXT PRIMARY KEY,
                    entity_id TEXT,
                    period_id TEXT,
                    metric_id TEXT,
                    value REAL,
                    source_locator TEXT,
                    period_basis TEXT,
                    validation_status TEXT
                )
            """)
            conn.execute("""
                INSERT INTO observations VALUES
                ('obs-1', 'VN', '2024_Q2', 'macro.policy_rate', 4.5, 'NHNN tr. 1', 'point_in_time', 'valid'),
                ('obs-2', 'VN', '2024_Q2', 'macro.credit_growth_yoy', 15.08, 'NHNN tr. 2', 'point_in_time', 'valid'),
                ('obs-3', 'VN', '2024_Q2', 'macro.credit_growth_ytd', 6.0, 'NHNN tr. 3', 'ytd', 'valid'),
                ('obs-4', 'VN', '2024_Q2', 'macro.credit_growth', 5.5, 'NHNN tr. 4', 'point_in_time', 'valid')
            """)
            conn.commit()
            dto = fetch_macro_context(conn, "2024_Q2")
            self.assertEqual(dto.system_credit_growth, 15.08)
            self.assertIn("(YoY)", dto.source)

            conn.execute("DELETE FROM observations WHERE metric_id = 'macro.credit_growth_yoy'")
            conn.commit()
            dto_ytd = fetch_macro_context(conn, "2024_Q2")
            self.assertEqual(dto_ytd.system_credit_growth, 6.0)
            self.assertIn("(YTD)", dto_ytd.source)

            conn.execute("DELETE FROM observations WHERE metric_id = 'macro.credit_growth_ytd'")
            conn.commit()
            dto_old = fetch_macro_context(conn, "2024_Q2")
            self.assertEqual(dto_old.system_credit_growth, 5.5)
            self.assertIn("NHNN tr. 4", dto_old.source)
        finally:
            conn.close()


if __name__ == "__main__":
    unittest.main()
