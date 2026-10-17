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


class TestMetricPhraseResolution(unittest.TestCase):
    """Tests for Fix A: longest-phrase-first metric synonym matching.

    Ensures "bao phủ nợ xấu" is not polluted by the shorter "nợ xấu" synonym.
    """

    def setUp(self) -> None:
        self.catalog = _make_mock_catalog()

    def test_ranking_llr_coverage_not_npl(self) -> None:
        """'Ngân hàng nào có tỷ lệ bao phủ nợ xấu cao nhất quý 4/2024?' → llr_coverage only."""
        resolved = resolve_query(
            "Ngân hàng nào có tỷ lệ bao phủ nợ xấu cao nhất quý 4/2024?", self.catalog
        )
        self.assertIn("bank.llr_coverage", resolved.explicit_metrics)
        self.assertNotIn("bank.npl_g35", resolved.explicit_metrics)
        self.assertIn("superlative", resolved.flags)

    def test_llr_coverage_acb_lookup_only_llr(self) -> None:
        """'Tỷ lệ bao phủ nợ xấu của ACB quý 4/2024' → only llr_coverage (lookup intent)."""
        resolved = resolve_query(
            "Tỷ lệ bao phủ nợ xấu của BANK_A quý 4/2024", self.catalog
        )
        self.assertIn("bank.llr_coverage", resolved.explicit_metrics)
        self.assertNotIn("bank.npl_g35", resolved.explicit_metrics)

    def test_npl_only_lookup(self) -> None:
        """'Tỷ lệ nợ xấu của VCB quý 4/2024 là bao nhiêu?' → only npl_g35."""
        resolved = resolve_query(
            "Tỷ lệ nợ xấu của BANK_A quý 4/2024 là bao nhiêu?", self.catalog
        )
        self.assertIn("bank.npl_g35", resolved.explicit_metrics)
        self.assertNotIn("bank.llr_coverage", resolved.explicit_metrics)
        self.assertIn("lookup", resolved.flags)

    def test_both_npl_and_llr(self) -> None:
        """'Nợ xấu và bao phủ nợ xấu của TCB năm 2024' → both metrics."""
        resolved = resolve_query(
            "Nợ xấu và bao phủ nợ xấu của BANK_A năm 2024", self.catalog
        )
        self.assertIn("bank.npl_g35", resolved.explicit_metrics)
        self.assertIn("bank.llr_coverage", resolved.explicit_metrics)

    def test_dem_du_phong_maps_to_llr(self) -> None:
        """'đệm dự phòng' → llr_coverage."""
        resolved = resolve_query("đệm dự phòng của BANK_A quý 4/2024", self.catalog)
        self.assertEqual(resolved.explicit_metrics, ("bank.llr_coverage",))

    def test_no_double_match_bao_phu_no_xau(self) -> None:
        """'bao phủ nợ xấu' must NOT produce both llr_coverage and npl_g35."""
        resolved = resolve_query("bao phủ nợ xấu của BANK_A quý 4/2024", self.catalog)
        self.assertIn("bank.llr_coverage", resolved.explicit_metrics)
        self.assertNotIn(
            "bank.npl_g35",
            resolved.explicit_metrics,
            msg="nợ xấu sub-phrase inside bao phủ nợ xấu must not yield npl_g35",
        )


def _make_gold_catalog() -> DatasetCapabilityCatalog:
    ref = DatasetRef(dataset_id="gold-fixture", dataset_snapshot_id="gold-fixture-v1")
    entities = tuple(
        DatasetEntity(
            entity_id=ticker,
            entity_type=DatasetEntityType.COMPANY,
            display_name=ticker,
            attributes={"ticker": ticker},
        )
        for ticker in ("ACB", "BID", "CTG", "HDB", "MBB", "SHB", "STB", "TCB", "VCB", "VPB")
    )
    periods = tuple(
        DatasetPeriod(period_id=f"{year}_Q{q}", label=f"{year} Q{q}")
        for year in (2024, 2025, 2026)
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
            peer_universe_id="universe-gold",
            display_name="Gold Universe",
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


class TestBankNameAliases(unittest.TestCase):
    """Tests for Task ALIAS-1: recognise common Vietnamese bank names in questions."""

    def setUp(self) -> None:
        self.catalog = _make_gold_catalog()
        self.mock_catalog = _make_mock_catalog()

    def test_regression_generic_vietnamese_phrases_not_banks(self) -> None:
        """Regression tests: non-bank phrases containing common words must NOT resolve to banks.

        - 'Bộ Công Thương và VCB quý 4/2025' -> only VCB (Bộ Công Thương is not CTG)
        - 'Sinh viên Ngoại thương hỏi ROE của ACB quý 4/2025' -> only ACB (Ngoại thương here is university, not VCB)
        - 'Đầu tư và phát triển số của TCB quý 4/2025' -> only TCB (Đầu tư và phát triển số is not BID)
        """
        res1 = resolve_query("Bộ Công Thương và VCB quý 4/2025", self.catalog)
        self.assertEqual(res1.entities, ("VCB",))
        self.assertEqual(res1.unknown_entity_tokens, ())

        res2 = resolve_query("Sinh viên Ngoại thương hỏi ROE của ACB quý 4/2025", self.catalog)
        self.assertEqual(res2.entities, ("ACB",))
        self.assertEqual(res2.unknown_entity_tokens, ())

        res3 = resolve_query("Đầu tư và phát triển số của TCB quý 4/2025", self.catalog)
        self.assertEqual(res3.entities, ("TCB",))
        self.assertEqual(res3.unknown_entity_tokens, ())

    def test_vietcombank_and_techcombank_order(self) -> None:
        """'So sánh Vietcombank và Techcombank quý 4/2025' → VCB, TCB in that order."""
        resolved = resolve_query(
            "So sánh Vietcombank và Techcombank quý 4/2025", self.catalog
        )
        self.assertEqual(resolved.entities, ("VCB", "TCB"))
        self.assertEqual(resolved.unknown_entity_tokens, ())
        self.assertEqual(resolved.anchor_period, "2025_Q4")

        # Reverse order preserved
        resolved_rev = resolve_query(
            "So sánh Techcombank và Vietcombank quý 4/2025", self.catalog
        )
        self.assertEqual(resolved_rev.entities, ("TCB", "VCB"))

    def test_acb_accents_and_accentless(self) -> None:
        """'Nợ xấu của ngân hàng Á Châu quý 2/2026' and the accentless 'a chau' → ACB."""
        # Accented with 'ngân hàng'
        res1 = resolve_query("Nợ xấu của ngân hàng Á Châu quý 2/2026", self.catalog)
        self.assertEqual(res1.entities, ("ACB",))
        self.assertEqual(res1.anchor_period, "2026_Q2")

        # Accentless with 'ngan hang'
        res2 = resolve_query("Nợ xấu của ngan hang a chau quý 2/2026", self.catalog)
        self.assertEqual(res2.entities, ("ACB",))

        # With 'NH' prefix
        res3 = resolve_query("Nợ xấu của NH Á Châu quý 2/2026", self.catalog)
        self.assertEqual(res3.entities, ("ACB",))

        # Accentless with 'nh' prefix
        res4 = resolve_query("Nợ xấu của nh a chau quý 2/2026", self.catalog)
        self.assertEqual(res4.entities, ("ACB",))

        # Ticker ACB alone
        res5 = resolve_query("Nợ xấu của ACB quý 2/2026", self.catalog)
        self.assertEqual(res5.entities, ("ACB",))

    def test_mbb_variants_and_mbs_boundary(self) -> None:
        """'MB Bank' / 'MBBank' / 'ngân hàng Quân đội' → MBB; 'MB' does not match inside 'MBS' or other words."""
        # 'MB Bank'
        res_mb_bank = resolve_query("Nợ xấu của MB Bank quý 4/2025", self.catalog)
        self.assertEqual(res_mb_bank.entities, ("MBB",))

        # 'MBBank'
        res_mbbank = resolve_query("Nợ xấu của MBBank quý 4/2025", self.catalog)
        self.assertEqual(res_mbbank.entities, ("MBB",))

        # 'ngân hàng Quân đội'
        res_qd = resolve_query("Nợ xấu của ngân hàng Quân đội quý 4/2025", self.catalog)
        self.assertEqual(res_qd.entities, ("MBB",))

        # 'NH Quân đội'
        res_nh_qd = resolve_query("Nợ xấu của NH Quân đội quý 4/2025", self.catalog)
        self.assertEqual(res_nh_qd.entities, ("MBB",))

        # 'MB' alone
        res_mb = resolve_query("Nợ xấu của MB quý 4/2025", self.catalog)
        self.assertEqual(res_mb.entities, ("MBB",))

        # 'MB' does not match inside 'MBS'
        res_mbs = resolve_query("Phân tích MBS quý 4/2025", self.catalog)
        self.assertNotIn("MBB", res_mbs.entities)
        self.assertEqual(res_mbs.entities, ())
        self.assertIn("MBS", res_mbs.unknown_entity_tokens)

        # Bare 'quân đội' in non-bank context must not match MBB
        res_nonbank = resolve_query("Doanh nghiệp quân đội vay vốn tại TCB", self.catalog)
        self.assertNotIn("MBB", res_nonbank.entities)
        self.assertEqual(res_nonbank.entities, ("TCB",))

    def test_unsupported_bank_names(self) -> None:
        """A name of a bank not in the catalog (e.g. 'OCB', 'Phương Đông') → unsupported, as today."""
        # 'OCB' ticker
        res_ocb = resolve_query("Phân tích OCB quý 4/2025", self.catalog)
        self.assertEqual(res_ocb.entities, ())
        self.assertIn("OCB", res_ocb.unknown_entity_tokens)

        # 'ngân hàng Phương Đông'
        res_pd = resolve_query("Phân tích ngân hàng Phương Đông quý 4/2025", self.catalog)
        self.assertEqual(res_pd.entities, ())
        self.assertIn("OCB", res_pd.unknown_entity_tokens)

        # 'NH Phương Đông'
        res_nh_pd = resolve_query("Phân tích NH Phương Đông quý 4/2025", self.catalog)
        self.assertEqual(res_nh_pd.entities, ())
        self.assertIn("OCB", res_nh_pd.unknown_entity_tokens)

        # Accentless 'ngan hang phuong dong'
        res_pd_noacc = resolve_query("Phân tích ngan hang phuong dong quý 4/2025", self.catalog)
        self.assertEqual(res_pd_noacc.entities, ())
        self.assertIn("OCB", res_pd_noacc.unknown_entity_tokens)

        # Bare 'phương đông' in non-bank phrase does not match OCB
        res_hotel = resolve_query("Khách sạn Phương Đông và VCB quý 4/2025", self.catalog)
        self.assertEqual(res_hotel.entities, ("VCB",))
        self.assertNotIn("OCB", res_hotel.unknown_entity_tokens)

        # When a bank name is in alias map but NOT in the catalog for this request:
        # e.g. Vietcombank queried against mock catalog (which only has BANK_A..BANK_E)
        res_mock = resolve_query("Phân tích Vietcombank quý 4/2024", self.mock_catalog)
        self.assertEqual(res_mock.entities, ())
        self.assertIn("VCB", res_mock.unknown_entity_tokens)

    def test_all_served_bank_aliases(self) -> None:
        """Verify Vietnamese names for all served banks map to correct tickers."""
        cases = [
            ("BIDV", "BID"),
            ("ngân hàng Đầu tư và Phát triển", "BID"),
            ("NH Đầu tư và Phát triển", "BID"),
            ("VietinBank", "CTG"),
            ("ngân hàng Công Thương", "CTG"),
            ("NH Công Thương", "CTG"),
            ("Techcombank", "TCB"),
            ("ngân hàng Kỹ Thương", "TCB"),
            ("NH Kỹ Thương", "TCB"),
            ("Sacombank", "STB"),
            ("ngân hàng Sài Gòn Thương Tín", "STB"),
            ("NH Sài Gòn Thương Tín", "STB"),
            ("ngân hàng Sài Gòn – Hà Nội", "SHB"),
            ("ngân hàng Sài Gòn - Hà Nội", "SHB"),
            ("NH Sài Gòn - Hà Nội", "SHB"),
            ("HDBank", "HDB"),
            ("VPBank", "VPB"),
            ("ngân hàng Việt Nam Thịnh Vượng", "VPB"),
            ("NH Việt Nam Thịnh Vượng", "VPB"),
            ("ngân hàng Ngoại thương", "VCB"),
            ("NH Ngoại thương", "VCB"),
            ("Vietcombank", "VCB"),
        ]
        for name, expected_ticker in cases:
            with self.subTest(name=name):
                resolved = resolve_query(f"Tỷ lệ nợ xấu của {name} quý 4/2025", self.catalog)
                self.assertEqual(resolved.entities, (expected_ticker,))

    def test_vib_uploaded_and_quoc_te_boundary(self) -> None:
        """'Quốc tế' matches VIB only in 'ngân hàng Quốc tế', not in generic phrases."""
        # In gold catalog (without VIB), 'ngân hàng Quốc tế' maps to unsupported VIB
        res_vib_unsupported = resolve_query("Tỷ lệ nợ xấu của ngân hàng Quốc tế quý 4/2025", self.catalog)
        self.assertEqual(res_vib_unsupported.entities, ())
        self.assertIn("VIB", res_vib_unsupported.unknown_entity_tokens)

        # 'chuẩn quốc tế' must NOT match VIB
        res_generic = resolve_query("Chất lượng tín dụng chuẩn quốc tế quý 4/2025", self.catalog)
        self.assertEqual(res_generic.entities, ())
        self.assertNotIn("VIB", res_generic.unknown_entity_tokens)

        # In composite catalog containing VIB (e.g. from user upload)
        vib_entity = DatasetEntity(
            entity_id="VIB",
            entity_type=DatasetEntityType.COMPANY,
            display_name="VIB",
            attributes={"ticker": "VIB"},
        )
        catalog_with_vib = DatasetCapabilityCatalog(
            dataset_ref=self.catalog.dataset_ref,
            entities=self.catalog.entities + (vib_entity,),
            periods=self.catalog.periods,
            metrics=self.catalog.metrics,
            peer_universes=self.catalog.peer_universes,
            supported_operations=self.catalog.supported_operations,
        )
        res_vib_ok = resolve_query("Tỷ lệ nợ xấu của ngân hàng Quốc tế quý 4/2025", catalog_with_vib)
        self.assertEqual(res_vib_ok.entities, ("VIB",))
        res_vib_ticker = resolve_query("Tỷ lệ nợ xấu của VIB quý 4/2025", catalog_with_vib)
        self.assertEqual(res_vib_ticker.entities, ("VIB",))

    def test_ticker_questions_pass_unchanged(self) -> None:
        """Existing ticker-based questions continue to pass unchanged."""
        res_mock = resolve_query("So sánh BANK_C, BANK_A và BANK_B quý 4/2024", self.mock_catalog)
        self.assertEqual(res_mock.entities, ("BANK_C", "BANK_A", "BANK_B"))

        res_gold = resolve_query("Tỷ lệ nợ xấu của VCB quý 4/2025", self.catalog)
        self.assertEqual(res_gold.entities, ("VCB",))

        res_pair = resolve_query("So sánh VCB và TCB quý 4/2025", self.catalog)
        self.assertEqual(res_pair.entities, ("VCB", "TCB"))

    def test_uploaded_bank_omitted_period_defaults_to_upload_latest_period(self) -> None:
        """When an uploaded bank is present and query omits period, default to uploaded bank's period."""
        vib_entity = DatasetEntity(
            entity_id="VIB",
            entity_type=DatasetEntityType.COMPANY,
            display_name="VIB",
            attributes={
                "ticker": "VIB",
                "user_supplied": True,
                "upload_periods": ("2025_Q4",),
                "latest_upload_period": "2025_Q4",
            },
        )
        catalog_with_vib = DatasetCapabilityCatalog(
            dataset_ref=self.catalog.dataset_ref,
            entities=self.catalog.entities + (vib_entity,),
            periods=self.catalog.periods,
            metrics=self.catalog.metrics,
            peer_universes=self.catalog.peer_universes,
            supported_operations=self.catalog.supported_operations,
        )

        # 1. Query without period defaults to upload's period
        res_no_period = resolve_query("Tỷ lệ nợ xấu của VIB là bao nhiêu?", catalog_with_vib)
        self.assertEqual(res_no_period.anchor_period, "2025_Q4")
        self.assertEqual(res_no_period.context_periods, ("2025_Q4",))
        self.assertIn("period_defaulted_to_upload", res_no_period.defaults_applied)
        self.assertNotIn("period_defaulted_to_latest", res_no_period.defaults_applied)

        # 2. Query with explicit period preserves requested period
        res_explicit = resolve_query("Tỷ lệ nợ xấu của VIB quý 3/2025 là bao nhiêu?", catalog_with_vib)
        self.assertEqual(res_explicit.anchor_period, "2025_Q3")
        self.assertNotIn("period_defaulted_to_upload", res_explicit.defaults_applied)
        self.assertNotIn("period_defaulted_to_latest", res_explicit.defaults_applied)

        # 3. Gold catalog query without period continues to default to latest catalog period
        res_gold = resolve_query("Tỷ lệ nợ xấu của ACB là bao nhiêu?", self.catalog)
        self.assertEqual(res_gold.anchor_period, self.catalog.periods[-1].period_id)
        self.assertIn("period_defaulted_to_latest", res_gold.defaults_applied)
        self.assertNotIn("period_defaulted_to_upload", res_gold.defaults_applied)


if __name__ == "__main__":
    unittest.main()
