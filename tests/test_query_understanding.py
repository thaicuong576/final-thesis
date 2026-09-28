"""Tests for query understanding and deterministic parameter resolution."""

from __future__ import annotations

import unittest
try:
    from socket_guard import install_socket_guard
except ImportError:
    from tests.socket_guard import install_socket_guard


def setUpModule() -> None:
    install_socket_guard()

from thesis_api.messages_vi import get_error_message
from thesis_api.query_understanding import resolve_query
from thesis_api.service import AnalysisBlocked
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


def _make_mock_catalog() -> DatasetCapabilityCatalog:
    ref = DatasetRef(dataset_id="test-fixture", dataset_snapshot_id="test-fixture-v1")
    entities = tuple(
        DatasetEntity(
            entity_id=f"BANK_{c}",
            entity_type=DatasetEntityType.COMPANY,
            display_name=f"Bank {c}",
            attributes={"ticker": f"BANK_{c}"},
        )
        for c in ("A", "B", "C", "D", "E")
    )
    periods = tuple(
        DatasetPeriod(period_id=f"2024_Q{q}", label=f"2024 Q{q}")
        for q in range(1, 5)
    )
    metrics = (
        DatasetMetric(
            metric_id="bank.npl_g35",
            display_name="Tỷ lệ nợ xấu",
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
    )
    peer_universes = (
        PeerUniverse(
            peer_universe_id="universe-test",
            display_name="Test Universe",
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


class TestQueryUnderstanding(unittest.TestCase):
    def setUp(self) -> None:
        self.catalog = _make_mock_catalog()

    def test_single_quarter_patterns_with_and_without_accents(self) -> None:
        patterns = [
            ("quý 4/2024", "2024_Q4"),
            ("quy 4/2024", "2024_Q4"),
            ("quý 4 năm 2024", "2024_Q4"),
            ("quy 4 nam 2024", "2024_Q4"),
            ("quý 4 2024", "2024_Q4"),
            ("Q4/2024", "2024_Q4"),
            ("Q4 2024", "2024_Q4"),
            ("Q4-2024", "2024_Q4"),
            ("4Q24", "2024_Q4"),
            ("4Q2024", "2024_Q4"),
            ("2024Q4", "2024_Q4"),
            ("2024_Q4", "2024_Q4"),
            ("cuối năm 2024", "2024_Q4"),
            ("cuoi nam 2024", "2024_Q4"),
        ]
        for query_frag, expected_period in patterns:
            with self.subTest(query=query_frag):
                resolved = resolve_query(f"Tỷ lệ nợ xấu của BANK_A {query_frag}", self.catalog)
                self.assertEqual(resolved.anchor_period, expected_period)
                self.assertEqual(resolved.explicit_periods, (expected_period,))
                self.assertIsNone(resolved.year_only)

    def test_period_ranges(self) -> None:
        ranges = [
            "từ quý 1 đến quý 4/2024",
            "tu quy 1 den quy 4/2024",
            "Q1-Q4/2024",
            "Q1–Q4/2024",
            "quý 1-4/2024",
            "quý 1–4/2024",
            "2024_Q1 đến 2024_Q4",
            "2024_Q1 to 2024_Q4",
            "từ 2024_Q1 đến 2024_Q4",
        ]
        expected = ("2024_Q1", "2024_Q2", "2024_Q3", "2024_Q4")
        for query_frag in ranges:
            with self.subTest(query=query_frag):
                resolved = resolve_query(f"Diễn biến ROE của BANK_A {query_frag}", self.catalog)
                self.assertEqual(resolved.explicit_periods, expected)
                self.assertEqual(resolved.anchor_period, "2024_Q4")
                self.assertIn("trend", resolved.flags)

    def test_year_only(self) -> None:
        queries = ["năm 2024", "nam 2024", "trong 2024", "trong năm 2024"]
        for q in queries:
            with self.subTest(query=q):
                resolved = resolve_query(f"ROE của BANK_A thay đổi thế nào {q}?", self.catalog)
                self.assertEqual(resolved.year_only, 2024)
                self.assertEqual(resolved.anchor_period, "2024_Q4")
                self.assertEqual(resolved.explicit_periods, ())
                self.assertEqual(
                    resolved.context_periods,
                    ("2024_Q1", "2024_Q2", "2024_Q3", "2024_Q4"),
                )
                self.assertIn("trend", resolved.flags)

    def test_no_period_defaults_to_latest(self) -> None:
        resolved = resolve_query("Sức khỏe tài chính của BANK_B", self.catalog)
        self.assertEqual(resolved.anchor_period, "2024_Q4")
        self.assertEqual(resolved.explicit_periods, ())
        self.assertIn("period_defaulted_to_latest", resolved.defaults_applied)
        self.assertEqual(
            resolved.context_periods,
            ("2024_Q1", "2024_Q2", "2024_Q3", "2024_Q4"),
        )

    def test_unsupported_period_raises_and_message_contains_available_range(self) -> None:
        with self.assertRaises(AnalysisBlocked) as cm:
            resolve_query("Tỷ lệ nợ xấu của BANK_A quý 4/2023", self.catalog)
        self.assertEqual(cm.exception.code, "unsupported_period")
        msg = get_error_message(cm.exception.code, catalog=self.catalog)
        self.assertIn("Q1–Q4/2024", msg)

    def test_synonyms_and_topic_recognition(self) -> None:
        # Synonyms
        res_npl = resolve_query("nợ xấu của BANK_A quý 4/2024", self.catalog)
        self.assertEqual(res_npl.explicit_metrics, ("bank.npl_g35",))

        res_llr = resolve_query("đệm dự phòng của BANK_A quý 4/2024", self.catalog)
        self.assertEqual(res_llr.explicit_metrics, ("bank.llr_coverage",))

        # Topic: "chất lượng tín dụng" should NOT trigger macro
        res_credit = resolve_query("Chất lượng tín dụng của BANK_A quý 4/2024 thế nào?", self.catalog)
        self.assertEqual(res_credit.topic_metrics, ("bank.npl_g35", "bank.llr_coverage"))
        self.assertNotIn("macro", res_credit.flags)

        # Topic: "sinh lời"
        res_prof = resolve_query("Hiệu quả sinh lời của BANK_A quý 4/2024", self.catalog)
        self.assertEqual(res_prof.topic_metrics, ("bank.roa", "bank.roe"))

        # Topic: "sức khỏe tài chính"
        res_all = resolve_query("Sức khỏe tài chính của BANK_A quý 4/2024", self.catalog)
        self.assertEqual(len(res_all.topic_metrics), 4)

    def test_unsupported_metric_in_registry_not_in_catalog(self) -> None:
        with self.assertRaises(AnalysisBlocked) as cm:
            resolve_query("NIM của BANK_A quý 4/2024", self.catalog)
        self.assertEqual(cm.exception.code, "unsupported_metric")

    def test_unknown_entity_token_detected(self) -> None:
        resolved = resolve_query("Phân tích HDB quý 4/2024", self.catalog)
        self.assertIn("HDB", resolved.unknown_entity_tokens)
        self.assertEqual(resolved.entities, ())

        resolved2 = resolve_query("Tỷ lệ nợ xấu của BANK_Z quý 4/2024", self.catalog)
        self.assertIn("BANK_Z", resolved2.unknown_entity_tokens)

    def test_entity_order_preserved(self) -> None:
        resolved = resolve_query("So sánh BANK_C, BANK_A và BANK_B quý 4/2024", self.catalog)
        self.assertEqual(resolved.entities, ("BANK_C", "BANK_A", "BANK_B"))


if __name__ == "__main__":
    unittest.main()
