"""Unit tests for pure core report_facts calculation module."""

from __future__ import annotations

import unittest
from tests.socket_guard import install_socket_guard
from thesis_data.dataset_contract import CanonicalObservation, DatasetRef, QualityStatus
from thesis_data.dataset_provider import aggregate_peer_median
from thesis_data.report_facts import (
    FORMULA,
    Fact,
    SignalResult,
    classify_signals,
    delta_fact,
    derived_ratio_fact,
    detect_cross_level_candidates,
    gap_fact,
    lead_count_fact,
    median_delta_fact,
    median_fact,
    pairwise_gap_fact,
    rank_facts,
    ratio_to_median_fact,
    spread_fact,
    value_fact,
)

setUpModule = install_socket_guard


def _make_obs(
    entity_id: str,
    metric_id: str,
    period_id: str,
    value: float | None,
    unit: str = "%",
    status: QualityStatus = QualityStatus.VALID,
) -> CanonicalObservation:
    return CanonicalObservation(
        observation_id=f"obs:{entity_id}:{period_id}:{metric_id}",
        dataset_id="test-ds",
        dataset_snapshot_id="test-snap",
        entity_id=entity_id,
        period_id=period_id,
        metric_id=metric_id,
        value=value,
        unit=unit,
        period_basis="quarterly",
        reporting_scope="consolidated",
        validation_status=status,
        source_ref=f"src:{entity_id}:{period_id}" if status == QualityStatus.VALID else None,
        missing_reason="DATA_UNAVAILABLE" if status != QualityStatus.VALID else None,
    )


class TestReportFactsCore(unittest.TestCase):
    def test_value_fact(self) -> None:
        obs = _make_obs("E1", "m.roe", "2024_Q4", 20.5)
        fact = value_fact(obs)
        self.assertIsNotNone(fact)
        assert fact is not None
        self.assertEqual(fact.fact_id, "fact:value:E1:2024_Q4:m.roe")
        self.assertEqual(fact.fact_type, "value")
        self.assertEqual(fact.value, 20.5)
        self.assertEqual(fact.formula_version, FORMULA["value"])
        self.assertEqual(fact.input_observation_ids, ["obs:E1:2024_Q4:m.roe"])

        # Invalid obs returns None
        bad_obs = _make_obs("E1", "m.roe", "2024_Q4", None, status=QualityStatus.MISSING)
        self.assertIsNone(value_fact(bad_obs))

    def test_median_fact_matches_aggregate_peer_median(self) -> None:
        dataset_ref = DatasetRef(dataset_id="test-ds", dataset_snapshot_id="test-snap")
        # Odd count (3 entities)
        obs_odd = [
            _make_obs("E1", "m.roe", "2024_Q4", 10.0),
            _make_obs("E2", "m.roe", "2024_Q4", 20.0),
            _make_obs("E3", "m.roe", "2024_Q4", 30.0),
        ]
        agg_odd = aggregate_peer_median(
            dataset_ref=dataset_ref,
            peer_universe_id="sector:test",
            period_id="2024_Q4",
            metric_id="m.roe",
            peer_entity_ids=("E1", "E2", "E3"),
            member_observations=obs_odd,
        )
        fact_odd = median_fact(agg_odd, "sector:test", obs_odd)
        self.assertIsNotNone(fact_odd)
        assert fact_odd is not None
        self.assertEqual(fact_odd.value, 20.0)
        self.assertEqual(fact_odd.denominator, 3)

        # Even count (4 entities)
        obs_even = [
            _make_obs("E1", "m.roe", "2024_Q4", 10.0),
            _make_obs("E2", "m.roe", "2024_Q4", 20.0),
            _make_obs("E3", "m.roe", "2024_Q4", 30.0),
            _make_obs("E4", "m.roe", "2024_Q4", 40.0),
        ]
        agg_even = aggregate_peer_median(
            dataset_ref=dataset_ref,
            peer_universe_id="sector:test",
            period_id="2024_Q4",
            metric_id="m.roe",
            peer_entity_ids=("E1", "E2", "E3", "E4"),
            member_observations=obs_even,
        )
        fact_even = median_fact(agg_even, "sector:test", obs_even)
        self.assertIsNotNone(fact_even)
        assert fact_even is not None
        self.assertEqual(fact_even.value, 25.0)
        self.assertEqual(fact_even.denominator, 4)

    def test_rank_facts_ties_and_directions(self) -> None:
        # Values: E1=20, E2=20, E3=10, E4=30
        obs_list = [
            _make_obs("E1", "m.metric", "2024_Q4", 20.0),
            _make_obs("E2", "m.metric", "2024_Q4", 20.0),
            _make_obs("E3", "m.metric", "2024_Q4", 10.0),
            _make_obs("E4", "m.metric", "2024_Q4", 30.0),
        ]
        # Higher is better: 1-2-2-4 competition ranking
        # E4 (30) -> rank 1
        # E1, E2 (20) -> rank 2
        # E3 (10) -> rank 4
        ranks_hib = {f.entity_id: f for f in rank_facts(obs_list, "univ", "higher_is_better")}
        self.assertEqual(ranks_hib["E4"].rank_better, 1)
        self.assertEqual(ranks_hib["E1"].rank_better, 2)
        self.assertEqual(ranks_hib["E2"].rank_better, 2)
        self.assertEqual(ranks_hib["E3"].rank_better, 4)
        self.assertEqual(ranks_hib["E4"].denominator, 4)

        # Lower is better (e.g. NPL):
        # E3 (10) -> rank 1
        # E1, E2 (20) -> rank 2
        # E4 (30) -> rank 4
        ranks_lib = {f.entity_id: f for f in rank_facts(obs_list, "univ", "lower_is_better")}
        self.assertEqual(ranks_lib["E3"].rank_better, 1)
        self.assertEqual(ranks_lib["E1"].rank_better, 2)
        self.assertEqual(ranks_lib["E2"].rank_better, 2)
        self.assertEqual(ranks_lib["E4"].rank_better, 4)
        self.assertEqual(ranks_lib["E4"].rank_desc, 1)

        # Neutral: rank_better is None, value is float(rank_desc)
        ranks_neutral = {f.entity_id: f for f in rank_facts(obs_list, "univ", "neutral")}
        self.assertIsNone(ranks_neutral["E4"].rank_better)
        self.assertEqual(ranks_neutral["E4"].rank_desc, 1)
        self.assertEqual(ranks_neutral["E4"].value, 1.0)

    def test_delta_and_gap_and_spread_and_ratios(self) -> None:
        o1 = _make_obs("E1", "m.roe", "2024_Q3", 15.0)
        o2 = _make_obs("E1", "m.roe", "2024_Q4", 22.0)
        d = delta_fact(o1, o2)
        self.assertIsNotNone(d)
        assert d is not None
        self.assertEqual(d.value, 7.0)
        self.assertEqual(d.from_period, "2024_Q3")
        self.assertEqual(d.period, "2024_Q4")

        # Gap to median
        val_fact = value_fact(o2)
        med_obs = _make_obs("univ", "m.roe", "2024_Q4", 18.0)
        med_f = median_fact(med_obs, "univ", [o2, med_obs])
        gap_f = gap_fact(val_fact, med_f)
        self.assertIsNotNone(gap_f)
        assert gap_f is not None
        self.assertEqual(gap_f.value, 4.0)

        # Ratio to median
        ratio_f = ratio_to_median_fact(val_fact, med_f)
        self.assertIsNotNone(ratio_f)
        assert ratio_f is not None
        self.assertAlmostEqual(ratio_f.value or 0.0, 22.0 / 18.0)

        # Division by zero in ratio_to_median
        zero_med = Fact(fact_id="zero", fact_type="peer_median", universe_id="u", metric_id="m", period="p", value=0.0)
        self.assertIsNone(ratio_to_median_fact(val_fact, zero_med))

        # Spread
        obs_set = [
            _make_obs("E1", "m.roe", "2024_Q4", 10.0),
            _make_obs("E2", "m.roe", "2024_Q4", 25.0),
            _make_obs("E3", "m.roe", "2024_Q4", 18.0),
        ]
        sp = spread_fact(obs_set, "univ")
        self.assertIsNotNone(sp)
        assert sp is not None
        self.assertEqual(sp.value, 15.0)
        self.assertEqual(sp.denominator, 3)

        # Derived ratio (e.g. ROE / ROA)
        roe_obs = _make_obs("E1", "m.roe", "2024_Q4", 20.0)
        roa_obs = _make_obs("E1", "m.roa", "2024_Q4", 2.0)
        dr = derived_ratio_fact(roe_obs, roa_obs, "derived.roe_over_roa", "roe-over-roa-v1")
        self.assertIsNotNone(dr)
        assert dr is not None
        self.assertEqual(dr.value, 10.0)

        # Zero denominator in derived ratio
        roa_zero = _make_obs("E1", "m.roa", "2024_Q4", 0.0)
        self.assertIsNone(derived_ratio_fact(roe_obs, roa_zero, "derived.roe_over_roa", "v1"))

    def test_pairwise_gap_and_lead_count(self) -> None:
        a_obs = _make_obs("E1", "m.roe", "2024_Q4", 20.0)
        b_obs = _make_obs("E2", "m.roe", "2024_Q4", 15.0)
        pg = pairwise_gap_fact(a_obs, b_obs)
        self.assertIsNotNone(pg)
        assert pg is not None
        self.assertEqual(pg.value, 5.0)
        self.assertEqual(pg.fact_id, "fact:pairwise_gap:E1:vs:E2:2024_Q4:m.roe")

        # Lead count with missing metric
        gap_roe = pg
        # NPL: lower is better. E1=1.5, E2=1.0 -> gap=0.5 -> E2 leads
        a_npl = _make_obs("E1", "m.npl", "2024_Q4", 1.5)
        b_npl = _make_obs("E2", "m.npl", "2024_Q4", 1.0)
        gap_npl = pairwise_gap_fact(a_npl, b_npl)

        metric_pairs = [
            ("m.roe", gap_roe),
            ("m.npl", gap_npl),
            ("m.missing", None),  # missing metric
        ]
        directions = {"m.roe": "higher_is_better", "m.npl": "lower_is_better"}
        lc_a = lead_count_fact("E1", "E2", metric_pairs, directions, flat_pp=0.0, period="2024_Q4")
        self.assertEqual(lc_a.value, 1.0)
        self.assertEqual(lc_a.denominator, 2)  # only 2 eligible metrics

        lc_b = lead_count_fact("E2", "E1", [
            ("m.roe", pairwise_gap_fact(b_obs, a_obs)),
            ("m.npl", pairwise_gap_fact(b_npl, a_npl)),
        ], directions, flat_pp=0.0, period="2024_Q4")
        self.assertEqual(lc_b.value, 1.0)
        self.assertEqual(lc_b.denominator, 2)

    def test_classify_signals_all_five_verdicts(self) -> None:
        directions = {"m1": "higher_is_better", "m2": "higher_is_better"}

        # 1. above_peers: at least 1 better, 0 worse
        facts_above = [
            Fact(fact_id="g1", fact_type="gap_to_median", entity_id="E1", metric_id="m1", value=2.0),
            Fact(fact_id="g2", fact_type="gap_to_median", entity_id="E1", metric_id="m2", value=0.01),
        ]
        res = classify_signals("E1", facts_above, {"dim": ("m1", "m2")}, directions, flat_pp=0.05)
        self.assertEqual(res[0].verdict, "above_peers")

        # 2. below_peers: at least 1 worse, 0 better
        facts_below = [
            Fact(fact_id="g1", fact_type="gap_to_median", entity_id="E1", metric_id="m1", value=-1.0),
            Fact(fact_id="g2", fact_type="gap_to_median", entity_id="E1", metric_id="m2", value=0.0),
        ]
        res = classify_signals("E1", facts_below, {"dim": ("m1", "m2")}, directions, flat_pp=0.05)
        self.assertEqual(res[0].verdict, "below_peers")

        # 3. mixed: both better and worse
        facts_mixed = [
            Fact(fact_id="g1", fact_type="gap_to_median", entity_id="E1", metric_id="m1", value=2.0),
            Fact(fact_id="g2", fact_type="gap_to_median", entity_id="E1", metric_id="m2", value=-2.0),
        ]
        res = classify_signals("E1", facts_mixed, {"dim": ("m1", "m2")}, directions, flat_pp=0.05)
        self.assertEqual(res[0].verdict, "mixed")

        # 4. in_line: all within flat_pp
        facts_inline = [
            Fact(fact_id="g1", fact_type="gap_to_median", entity_id="E1", metric_id="m1", value=0.02),
            Fact(fact_id="g2", fact_type="gap_to_median", entity_id="E1", metric_id="m2", value=-0.01),
        ]
        res = classify_signals("E1", facts_inline, {"dim": ("m1", "m2")}, directions, flat_pp=0.05)
        self.assertEqual(res[0].verdict, "in_line")

        # 5. insufficient_data: no gap facts
        res = classify_signals("E1", [], {"dim": ("m1", "m2")}, directions, flat_pp=0.05)
        self.assertEqual(res[0].verdict, "insufficient_data")

    def test_detect_cross_level_candidates(self) -> None:
        # 1. Divergent signals (positive & negative cases)
        signals_div = [
            SignalResult(group="g1", label="G1", verdict="above_peers", metric_ids=["m1"], fact_ids=["f1"]),
            SignalResult(group="g2", label="G2", verdict="below_peers", metric_ids=["m2"], fact_ids=["f2"]),
        ]
        cand_div = detect_cross_level_candidates([], signals_div)
        self.assertTrue(any(c.kind == "divergent_signals" for c in cand_div))

        signals_no_div = [
            SignalResult(group="g1", label="G1", verdict="above_peers", metric_ids=["m1"], fact_ids=["f1"]),
            SignalResult(group="g2", label="G2", verdict="above_peers", metric_ids=["m2"], fact_ids=["f2"]),
        ]
        cand_no_div = detect_cross_level_candidates([], signals_no_div)
        self.assertFalse(any(c.kind == "divergent_signals" for c in cand_no_div))

        # 2. Counter-trend (positive & negative cases)
        facts_counter = [
            Fact(fact_id="d1", fact_type="delta", entity_id="E1", from_period="Q3", period="Q4", metric_id="m1", value=1.5),
            Fact(fact_id="md1", fact_type="median_delta", universe_id="u", from_period="Q3", period="Q4", metric_id="m1", value=-0.8),
        ]
        cand_ct = detect_cross_level_candidates(facts_counter, [], flat_pp=0.05)
        self.assertTrue(any(c.kind == "counter_trend" for c in cand_ct))

        facts_same_trend = [
            Fact(fact_id="d1", fact_type="delta", entity_id="E1", from_period="Q3", period="Q4", metric_id="m1", value=1.5),
            Fact(fact_id="md1", fact_type="median_delta", universe_id="u", from_period="Q3", period="Q4", metric_id="m1", value=0.8),
        ]
        cand_no_ct = detect_cross_level_candidates(facts_same_trend, [], flat_pp=0.05)
        self.assertFalse(any(c.kind == "counter_trend" for c in cand_no_ct))

        # 3. Cross-metric extreme (tradeoff & consistent cases)
        # Consistent: rank 1 in both m1 and m2 (different groups)
        facts_extreme_cons = [
            Fact(fact_id="r1", fact_type="peer_rank", entity_id="E1", metric_id="m1", rank_better=1, denominator=5),
            Fact(fact_id="r2", fact_type="peer_rank", entity_id="E1", metric_id="m2", rank_better=1, denominator=5),
        ]
        cand_cons = detect_cross_level_candidates(facts_extreme_cons, [], metric_to_group={"m1": "g1", "m2": "g2"})
        self.assertTrue(any(c.kind == "cross_metric_extreme" and c.pattern == "consistent" for c in cand_cons))

        # Tradeoff: rank 1 in m1 and rank 5 (denominator) in m2
        facts_extreme_trade = [
            Fact(fact_id="r1", fact_type="peer_rank", entity_id="E1", metric_id="m1", rank_better=1, denominator=5),
            Fact(fact_id="r2", fact_type="peer_rank", entity_id="E1", metric_id="m2", rank_better=5, denominator=5),
        ]
        cand_trade = detect_cross_level_candidates(facts_extreme_trade, [], metric_to_group={"m1": "g1", "m2": "g2"})
        self.assertTrue(any(c.kind == "cross_metric_extreme" and c.pattern == "tradeoff" for c in cand_trade))

        # Not extreme if same group or not extreme rank
        facts_no_ext = [
            Fact(fact_id="r1", fact_type="peer_rank", entity_id="E1", metric_id="m1", rank_better=2, denominator=5),
            Fact(fact_id="r2", fact_type="peer_rank", entity_id="E1", metric_id="m2", rank_better=3, denominator=5),
        ]
        cand_no_ext = detect_cross_level_candidates(facts_no_ext, [], metric_to_group={"m1": "g1", "m2": "g2"})
        self.assertFalse(any(c.kind == "cross_metric_extreme" for c in cand_no_ext))


if __name__ == "__main__":
    unittest.main()
