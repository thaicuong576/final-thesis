"""Tests for deterministic scope gate rejecting out-of-scope queries (SCOPE-1)."""

from __future__ import annotations

import glob
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient
try:
    from socket_guard import install_socket_guard
except ImportError:
    from tests.socket_guard import install_socket_guard


def setUpModule() -> None:
    install_socket_guard()

try:
    from test_api_analyze import (
        _ExplicitOfflineAcceptingCritic,
        _ExplicitOfflineAnalysisWriter,
        _gold_fixture,
    )
except ImportError:
    from tests.test_api_analyze import (
        _ExplicitOfflineAcceptingCritic,
        _ExplicitOfflineAnalysisWriter,
        _gold_fixture,
    )
from thesis_api.analysis_planner import plan_question, rules_plan, validate_scope
from thesis_api.main import create_app
from thesis_api.messages_vi import MESSAGES, get_error_message
from thesis_api.query_understanding import resolve_query
from thesis_api.schemas import AnalysisResponse, AnalysisSessionEventDTO
from thesis_api.service import AnalysisBlocked
from thesis_api.settings import Settings
from thesis_data.dataset_contract import (
    AnalyticalLevel,
    DatasetCapabilityCatalog,
    DatasetEntity,
    DatasetEntityType,
    DatasetMetric,
    DatasetPeriod,
    DatasetRef,
    PeerUniverse,
    SupportedOperation,
)


def _make_test_catalog() -> DatasetCapabilityCatalog:
    ref = DatasetRef(dataset_id="scope-gate-test", dataset_snapshot_id="test-v1")
    tickers = ("VCB", "BID", "CTG", "TCB", "MBB", "VPB", "ACB", "HDB", "SHB", "STB")
    entities = tuple(
        DatasetEntity(
            entity_id=ticker,
            entity_type=DatasetEntityType.COMPANY,
            display_name=ticker,
            attributes={"ticker": ticker},
        )
        for ticker in tickers
    )
    periods = tuple(
        DatasetPeriod(period_id=f"2024_Q{q}", label=f"2024 Q{q}")
        for q in range(1, 5)
    )
    metrics = (
        DatasetMetric(
            metric_id="bank.npl_g35",
            display_name="Tỷ lệ nợ xấu (nhóm 3–5)",
            analytical_level=AnalyticalLevel.COMPANY,
            default_unit="percent",
        ),
        DatasetMetric(
            metric_id="bank.llr_coverage",
            display_name="Tỷ lệ bao phủ nợ xấu",
            analytical_level=AnalyticalLevel.COMPANY,
            default_unit="percent",
        ),
        DatasetMetric(
            metric_id="bank.roa",
            display_name="ROA",
            analytical_level=AnalyticalLevel.COMPANY,
            default_unit="percent",
        ),
        DatasetMetric(
            metric_id="bank.roe",
            display_name="ROE",
            analytical_level=AnalyticalLevel.COMPANY,
            default_unit="percent",
        ),
        DatasetMetric(
            metric_id="bank.nim",
            display_name="NIM",
            analytical_level=AnalyticalLevel.COMPANY,
            default_unit="percent",
        ),
        DatasetMetric(
            metric_id="bank.cir",
            display_name="CIR",
            analytical_level=AnalyticalLevel.COMPANY,
            default_unit="percent",
        ),
        DatasetMetric(
            metric_id="bank.casa",
            display_name="CASA",
            analytical_level=AnalyticalLevel.COMPANY,
            default_unit="percent",
        ),
    )
    peer_universes = (
        PeerUniverse(
            peer_universe_id="universe-top10",
            display_name="Top 10 banks",
            entity_ids=tuple(e.entity_id for e in entities),
        ),
    )
    return DatasetCapabilityCatalog(
        dataset_ref=ref,
        entities=entities,
        periods=periods,
        metrics=metrics,
        peer_universes=peer_universes,
        supported_operations=(
            SupportedOperation.GET_METRIC,
            SupportedOperation.RESOLVE_OBSERVATION,
            SupportedOperation.GET_SOURCE,
            SupportedOperation.GET_PEER_BENCHMARK,
        ),
    )


class ScopeGateUnitTests(unittest.TestCase):
    """Unit tests for validate_scope, rules_plan, and plan_question rejection behavior."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.catalog = _make_test_catalog()

    def test_out_of_scope_queries_rejected_with_out_of_scope_code(self) -> None:
        """Verify at least 6 diverse out-of-scope queries fail closed with out_of_scope."""
        out_of_scope_queries = [
            "Hãy sáng tác một bài thơ về thị trường ngân hàng Việt Nam.",
            "Dự báo giá vàng trong nước và giá vàng thế giới tuần tới.",
            "Dịch đoạn văn sau sang tiếng Anh: Chào buổi sáng và chúc bạn một ngày tốt lành.",
            "Thời tiết hôm nay tại Hà Nội thế nào?",
            "Viết code Python để tính dãy số Fibonacci đệ quy tối ưu.",
            "Giá xăng dầu hôm nay tăng hay giảm bao nhiêu?",
            "",
            "   \t\n   ",
            "asdfghjk lqwerty zxcvbnm",
        ]

        expected_msg = MESSAGES["out_of_scope"]
        self.assertTrue(len(expected_msg) > 10)

        for query in out_of_scope_queries:
            with self.subTest(query=query):
                resolved = resolve_query(query, self.catalog)

                # 1. validate_scope direct call
                with self.assertRaises(AnalysisBlocked) as ctx_gate:
                    validate_scope(resolved, self.catalog)
                self.assertEqual(ctx_gate.exception.code, "out_of_scope")
                self.assertIn("ngoài phạm vi", ctx_gate.exception.detail)

                # 2. rules_plan call
                with self.assertRaises(AnalysisBlocked) as ctx_rules:
                    rules_plan(resolved, self.catalog)
                self.assertEqual(ctx_rules.exception.code, "out_of_scope")

                # 3. plan_question call
                with self.assertRaises(AnalysisBlocked) as ctx_plan:
                    plan_question(query, self.catalog)
                self.assertEqual(ctx_plan.exception.code, "out_of_scope")

    def test_valid_queries_of_different_types_pass_scope_gate(self) -> None:
        """Verify at least 6 diverse valid queries pass through the scope gate without error."""
        valid_queries = [
            # 1. Ranking by metric without entities
            "Xếp hạng ROE các ngân hàng năm 2024",
            # 2. Head to head comparison between two entities
            "So sánh MBB và VCB quý 4 2024",
            # 3. Single entity trend over time
            "Xu hướng tỷ lệ nợ xấu của CTG qua các quý năm 2024",
            # 4. Sector overview with topic metrics
            "Tổng quan ngành ngân hàng về chất lượng tài sản quý 4 2024",
            # 5. Lookup for a specific bank and metric
            "Tỷ lệ nợ xấu của VCB quý 4 2024 là bao nhiêu?",
            # 6. Metric superlative without entity
            "Ngân hàng nào có tỷ lệ bao phủ nợ xấu cao nhất quý 4 2024?",
            # 7. Company profile overview
            "Sức khỏe tài chính của ACB quý 4 2024",
        ]

        for query in valid_queries:
            with self.subTest(query=query):
                resolved = resolve_query(query, self.catalog)
                # validate_scope must not raise
                validate_scope(resolved, self.catalog)

                # plan_question must succeed and return valid PlanSpec
                spec, source, fallbacks, _ = plan_question(query, self.catalog)
                self.assertIsNotNone(spec)
                self.assertTrue(len(spec.tools) > 0)

    def test_domain_keyword_alone_insufficient_to_bypass_scope_gate(self) -> None:
        """Single domain keyword 'ngân hàng' alone must not bypass the scope gate."""
        queries_with_bank_keyword = [
            "Làm một bài thơ về các cô gái làm việc tại ngân hàng.",
            "Truyện cười về giao dịch viên ngân hàng.",
            "Tuyển dụng nhân viên ngân hàng tại Đà Nẵng cần điều kiện gì?",
            "Lịch nghỉ tết của các ngân hàng năm nay ra sao?",
        ]
        for query in queries_with_bank_keyword:
            with self.subTest(query=query):
                resolved = resolve_query(query, self.catalog)
                with self.assertRaises(AnalysisBlocked) as ctx:
                    validate_scope(resolved, self.catalog)
                self.assertEqual(ctx.exception.code, "out_of_scope")


class FrozenEvalSetsScopeGateTests(unittest.TestCase):
    """Verify that no valid queries in frozen evaluation sets are falsely blocked."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.catalog = _make_test_catalog()

    def test_er8_questions_not_blocked_by_scope_gate(self) -> None:
        """Every question in data/evaluation/er8-questions-v2.jsonl must pass the scope gate."""
        path = Path("data/evaluation/er8-questions-v2.jsonl")
        self.assertTrue(path.exists(), f"Missing {path}")

        questions: list[str] = []
        with open(path, encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    item = json.loads(line)
                    q = item.get("question_text") or item.get("prompt") or item.get("question")
                    if q:
                        questions.append(q)

        self.assertGreaterEqual(len(questions), 10)
        for q in questions:
            with self.subTest(query=q):
                try:
                    resolved = resolve_query(q, self.catalog)
                    validate_scope(resolved, self.catalog)
                except AnalysisBlocked as exc:
                    self.assertNotEqual(
                        exc.code,
                        "out_of_scope",
                        f"Frozen ER8 question falsely blocked by scope gate: {q}",
                    )

    def test_experiment_question_sets_not_blocked_by_scope_gate(self) -> None:
        """Questions in experiments/question-set-*.json must not be blocked by out_of_scope."""
        files = glob.glob("experiments/question-set-*.json")
        self.assertGreater(len(files), 0)

        total_tested = 0
        for fpath in files:
            if "design" in fpath:
                continue
            with open(fpath, encoding="utf-8") as f:
                data = json.load(f)
            items = data if isinstance(data, list) else data.get("questions", [])
            for item in items:
                q = item if isinstance(item, str) else (item.get("question_text") or item.get("prompt") or item.get("question"))
                if not q:
                    continue
                total_tested += 1
                with self.subTest(fpath=fpath, query=q):
                    try:
                        resolved = resolve_query(q, self.catalog)
                        validate_scope(resolved, self.catalog)
                    except AnalysisBlocked as exc:
                        self.assertNotEqual(
                            exc.code,
                            "out_of_scope",
                            f"Frozen experiment question in {fpath} falsely blocked: {q}",
                        )
        self.assertGreater(total_tested, 20)

    def test_redteam_specs_refuse_red13_and_red14_and_preserve_others(self) -> None:
        """RED-13 and RED-14 must raise out_of_scope, while all other tasks keep their behavior."""
        specs_path = Path("data/evaluation/redteam-task-specs-v1.json")
        questions_path = Path("data/evaluation/redteam-questions-v1.jsonl")
        self.assertTrue(specs_path.exists())
        self.assertTrue(questions_path.exists())

        with open(specs_path, encoding="utf-8") as f:
            specs_data = json.load(f)
        tasks = {t["task_id"]: t for t in specs_data["tasks"]}

        questions_by_task: dict[str, str] = {}
        with open(questions_path, encoding="utf-8") as f:
            for idx, line in enumerate(f, start=1):
                if line.strip():
                    item = json.loads(line)
                    tid = f"RED-{idx:02d}"
                    questions_by_task[tid] = item.get("question_text") or ""

        # Check RED-13 and RED-14 specifically
        for tid in ("RED-13", "RED-14"):
            q = questions_by_task[tid]
            self.assertTrue(bool(q), f"Empty question for {tid}")
            with self.subTest(task_id=tid, query=q):
                resolved = resolve_query(q, self.catalog)
                with self.assertRaises(AnalysisBlocked) as ctx:
                    validate_scope(resolved, self.catalog)
                self.assertEqual(ctx.exception.code, "out_of_scope")

        # Check that other tasks do NOT raise out_of_scope
        for tid, q in questions_by_task.items():
            if tid in ("RED-13", "RED-14"):
                continue
            with self.subTest(task_id=tid, query=q):
                try:
                    resolved = resolve_query(q, self.catalog)
                    validate_scope(resolved, self.catalog)
                except AnalysisBlocked as exc:
                    self.assertNotEqual(
                        exc.code,
                        "out_of_scope",
                        f"Task {tid} ({q}) was unexpectedly rejected with out_of_scope",
                    )


class ScopeGateApiIntegrationTests(unittest.TestCase):
    """Integration tests for POST /api/analyze and /api/analyze/stream out-of-scope refusal."""

    def setUp(self) -> None:
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.db_path = _gold_fixture(Path(self.directory.name) / "gold.sqlite")

        self.critic_patch = patch(
            "thesis_api.adaptive_runtime.build_openai_semantic_critic",
            return_value=_ExplicitOfflineAcceptingCritic(),
        )
        self.critic_patch.start()
        self.addCleanup(self.critic_patch.stop)

        settings = Settings(
            app_env="test",
            sqlite_db_path=str(self.db_path),
            analysis_runs_db_path=str(Path(self.directory.name) / "analysis-runs.sqlite"),
            openai_api_key="test-key",
            planner_mode="rules_only",
        )
        self.client = TestClient(
            create_app(settings, analysis_writer=_ExplicitOfflineAnalysisWriter())
        )
        self.addCleanup(self.client.close)

    def test_post_analyze_out_of_scope_returns_error_response(self) -> None:
        """POST /api/analyze with out-of-scope question returns error response with out_of_scope."""
        payload = {
            "query": "Hãy sáng tác một bài thơ về thị trường ngân hàng Việt Nam.",
        }
        resp = self.client.post("/api/analyze", json=payload)
        self.assertEqual(resp.status_code, 200)

        data = resp.json()
        report = AnalysisResponse.model_validate(data)
        self.assertEqual(report.status, "error")
        self.assertIsNotNone(report.error)
        self.assertEqual(report.error.code, "out_of_scope")
        self.assertIn("ngoài phạm vi", report.error.message)
        self.assertGreater(len(report.error.suggestions), 0)
        self.assertEqual(report.atomic_claims, [])
        self.assertEqual(report.evidence_trail, [])
        self.assertTrue(any("out_of_scope" in lim for lim in report.limitations))

    def test_post_analyze_stream_out_of_scope_emits_run_blocked_and_never_report_ready(self) -> None:
        """POST /api/analyze/stream with out-of-scope query emits RUN_BLOCKED and never REPORT_READY."""
        payload = {
            "query": "Dự báo giá vàng trong nước và giá vàng thế giới tuần tới.",
        }
        resp = self.client.post("/api/analyze/stream", json=payload)
        self.assertEqual(resp.status_code, 200)

        events: list[tuple[str, dict]] = []
        for block in resp.text.strip().split("\n\n"):
            if not block.strip():
                continue
            event_type = ""
            event_payload = {}
            for line in block.splitlines():
                if line.startswith("event:"):
                    event_type = line.removeprefix("event:").strip()
                elif line.startswith("data:"):
                    event_payload = json.loads(line.removeprefix("data:").strip())
            if event_type:
                events.append((event_type, event_payload))

        event_types = [t for t, _ in events]
        self.assertIn("RUN_BLOCKED", event_types)
        self.assertNotIn("REPORT_READY", event_types)

        # Inspect RUN_BLOCKED payload
        blocked_payloads = [p for t, p in events if t == "RUN_BLOCKED"]
        self.assertEqual(len(blocked_payloads), 1)
        blocked_event = blocked_payloads[0]
        payload = blocked_event.get("payload", blocked_event)
        self.assertIn("out_of_scope", payload.get("reason", ""))
        if "error" in payload:
            self.assertEqual(payload["error"]["code"], "out_of_scope")


if __name__ == "__main__":
    unittest.main()
