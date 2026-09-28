"""Tests for Report v2 contracts, schemas, DTOs, openapi spec, and fixtures (ER-1)."""

from __future__ import annotations

import json
from pathlib import Path
import unittest

from scripts.check_openapi_contract import check_contract
from thesis_api.schemas import (
    AnalysisResponse,
    AnalysisResponseDTO,
    AnalysisRunRecordDTO,
    AnalysisRunSummaryDTO,
    AnswerBlockDTO,
    BlockDroppedDTO,
    CalloutBlockDTO,
    CapabilitiesDTO,
    CrossLevelFindingDTO,
    DatasetDTO,
    DatasetRowDTO,
    ErrorInfoDTO,
    FactDTO,
    FigureBlockDTO,
    HeadlineBlockDTO,
    KeyPointItemDTO,
    KeyPointsBlockDTO,
    MetricPresentationDTO,
    NarrativeAuditDTO,
    ProducedByDTO,
    QuestionTypeInfoDTO,
    ReferenceLineDTO,
    ReportSpecDTO,
    RunTraceDTO,
    SectionBlockDTO,
    SentenceDTO,
    SentenceDroppedDTO,
    SignalDTO,
    SourceNoteDTO,
    TableBlockDTO,
    TraceStepDTO,
)

ROOT = Path(__file__).resolve().parents[1]
OPENAPI_PATH = ROOT / "contracts" / "openapi.json"
FIXTURES_DIR = ROOT / "frontend" / "src" / "test" / "fixtures"


class ContractErReportTests(unittest.TestCase):
    """Test suite verifying OpenAPI contracts, DTO synchronization, and fixtures."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.openapi_doc = json.loads(OPENAPI_PATH.read_text(encoding="utf-8"))

    def test_01_openapi_has_all_schemas_and_paths_and_passes_check(self) -> None:
        """1. openapi.json has all schemas in §2 and paths in §2.8, and passes check_contract."""
        check_contract(OPENAPI_PATH)

        paths = self.openapi_doc["paths"]
        expected_paths = [
            "/api/capabilities",
            "/api/runs",
            "/api/runs/{run_id}",
            "/api/runs/{run_id}/trace",
            "/api/reports/{report_id}",
            "/api/analyze/stream",
        ]
        for path in expected_paths:
            self.assertIn(path, paths, f"Missing path: {path}")

        stream_desc = paths["/api/analyze/stream"]["post"]["description"]
        self.assertIn("TRACE_STEP", stream_desc)
        self.assertIn("TraceStep", stream_desc)

        schemas_map = self.openapi_doc["components"]["schemas"]
        expected_schemas = [
            "MetricPresentation",
            "QuestionType",
            "QuestionTypeInfo",
            "Capabilities",
            "Fact",
            "ProducedBy",
            "DatasetRow",
            "ReferenceLine",
            "Dataset",
            "Sentence",
            "AnswerBlock",
            "HeadlineBlock",
            "KeyPointItem",
            "KeyPointsBlock",
            "SectionBlock",
            "FigureBlock",
            "CalloutBlock",
            "TableBlock",
            "ReportBlock",
            "ReportSpec",
            "Signal",
            "CrossLevelFinding",
            "SentenceDropped",
            "BlockDropped",
            "NarrativeAudit",
            "SourceNote",
            "ErrorInfo",
            "TraceStep",
            "RunTrace",
            "AnalysisRunSummary",
            "AnalysisRunRecord",
        ]
        for schema_name in expected_schemas:
            self.assertIn(schema_name, schemas_map, f"Missing schema in openapi: {schema_name}")

    def test_02_dto_properties_match_openapi_schemas(self) -> None:
        """2. Each new DTO has property set matching schema with same name (without DTO)."""
        schemas_map = self.openapi_doc["components"]["schemas"]
        dtos = [
            MetricPresentationDTO,
            QuestionTypeInfoDTO,
            CapabilitiesDTO,
            FactDTO,
            ProducedByDTO,
            DatasetRowDTO,
            ReferenceLineDTO,
            DatasetDTO,
            SentenceDTO,
            AnswerBlockDTO,
            HeadlineBlockDTO,
            KeyPointItemDTO,
            KeyPointsBlockDTO,
            SectionBlockDTO,
            FigureBlockDTO,
            CalloutBlockDTO,
            TableBlockDTO,
            ReportSpecDTO,
            SignalDTO,
            CrossLevelFindingDTO,
            SentenceDroppedDTO,
            BlockDroppedDTO,
            NarrativeAuditDTO,
            SourceNoteDTO,
            ErrorInfoDTO,
            TraceStepDTO,
            RunTraceDTO,
            AnalysisRunSummaryDTO,
            AnalysisRunRecordDTO,
        ]

        for dto in dtos:
            dto_name = dto.__name__
            schema_name = dto_name[:-3] if dto_name.endswith("DTO") else dto_name
            self.assertIn(schema_name, schemas_map, f"Schema {schema_name} not found in openapi.json")
            schema = schemas_map[schema_name]
            dto_props = set(dto.model_fields.keys())
            schema_props = set(schema.get("properties", {}).keys())
            self.assertEqual(
                dto_props,
                schema_props,
                f"Properties mismatch for {schema_name}: DTO has {dto_props - schema_props}, openapi has {schema_props - dto_props}",
            )

    def test_03_legacy_analysis_response_validates_without_new_fields(self) -> None:
        """3. Legacy AnalysisResponse without new fields still validates successfully."""
        legacy_payload = {
            "report_id": "rep-legacy-001",
            "status": "completed",
            "company_insights": [
                {
                    "ticker": "ACB",
                    "assessment": "Healthy capital ratios and steady asset quality.",
                }
            ],
            "cross_level_critique": [],
            "limitations": [],
            "synthesis_summary": "Synthesized overview of banking assets.",
        }
        resp = AnalysisResponse.model_validate(legacy_payload)
        self.assertEqual(resp.report_id, "rep-legacy-001")
        self.assertEqual(resp.status, "completed")
        self.assertIsNone(resp.report_version)
        self.assertIsNone(resp.question_type)
        self.assertIsNone(resp.report_spec)
        self.assertEqual(resp.datasets, [])
        self.assertEqual(resp.facts, [])
        self.assertEqual(resp.signals, [])
        self.assertEqual(resp.cross_level_findings, [])
        self.assertIsNone(resp.narrative_audit)
        self.assertEqual(resp.source_notes, [])
        self.assertIsNone(resp.error)

    def test_04_fixtures_validate_with_models(self) -> None:
        """4. All fixture reports validate with AnalysisResponse; fixture trace validates with RunTraceDTO."""
        report_fixtures = [
            "er-lookup-vcb-npl-2024q4.json",
            "er-ranking-coverage-2024q4.json",
            "er-trend-vpb-roe-2024.json",
            "er-h2h-acb-tcb-2024q4.json",
            "er-profile-acb-2024q4.json",
            "er-error-unsupported-period.json",
        ]
        for name in report_fixtures:
            path = FIXTURES_DIR / name
            self.assertTrue(path.exists(), f"Missing fixture file: {path}")
            data = json.loads(path.read_text(encoding="utf-8"))
            resp = AnalysisResponse.model_validate(data)
            self.assertTrue(resp.report_id)
            if name != "er-error-unsupported-period.json":
                self.assertEqual(resp.report_version, "er-report-v1")
            else:
                self.assertEqual(resp.status, "error")
                self.assertIsNotNone(resp.error)
                self.assertEqual(resp.error.code, "unsupported_period")
                self.assertEqual(len(resp.error.suggestions), 3)

        trace_path = FIXTURES_DIR / "er-trace-acb-2024q4.json"
        self.assertTrue(trace_path.exists(), f"Missing trace fixture: {trace_path}")
        trace_data = json.loads(trace_path.read_text(encoding="utf-8"))
        trace = RunTraceDTO.model_validate(trace_data)
        self.assertEqual(trace.run_id, "run-profile-acb-2024q4")
        self.assertGreaterEqual(len(trace.steps), 10)

    def test_05_fixture_dataset_and_fact_ids_reconciled(self) -> None:
        """5. Every dataset_id in report_spec exists in datasets; every fact_id in sentences exists in facts."""
        report_fixtures = [
            "er-lookup-vcb-npl-2024q4.json",
            "er-ranking-coverage-2024q4.json",
            "er-trend-vpb-roe-2024.json",
            "er-h2h-acb-tcb-2024q4.json",
            "er-profile-acb-2024q4.json",
        ]
        for name in report_fixtures:
            path = FIXTURES_DIR / name
            data = json.loads(path.read_text(encoding="utf-8"))
            facts = {f["fact_id"] for f in data.get("facts", [])}
            datasets = {d["dataset_id"] for d in data.get("datasets", [])}
            spec = data.get("report_spec")
            self.assertIsNotNone(spec, f"{name}: missing report_spec")

            for block in spec.get("blocks", []):
                btype = block.get("type")
                if btype in ("figure", "table"):
                    ds_id = block.get("dataset_id")
                    self.assertIn(ds_id, datasets, f"{name}: figure/table dataset_id '{ds_id}' not found in datasets")

                if btype == "answer":
                    val_id = block.get("value_fact_id")
                    self.assertIn(val_id, facts, f"{name}: answer value_fact_id '{val_id}' not found in facts")
                    for s in block.get("sentences", []):
                        for fid in s.get("fact_ids", []):
                            self.assertIn(fid, facts, f"{name}: answer sentence fact_id '{fid}' not found in facts")
                elif btype == "headline":
                    s = block.get("sentence", {})
                    for fid in s.get("fact_ids", []):
                        self.assertIn(fid, facts, f"{name}: headline sentence fact_id '{fid}' not found in facts")
                elif btype == "figure":
                    s = block.get("takeaway", {})
                    for fid in s.get("fact_ids", []):
                        self.assertIn(fid, facts, f"{name}: figure takeaway fact_id '{fid}' not found in facts")
                elif btype == "key_points":
                    for item in block.get("items", []):
                        for s in item.get("sentences", []):
                            for fid in s.get("fact_ids", []):
                                self.assertIn(fid, facts, f"{name}: key_point sentence fact_id '{fid}' not found in facts")
                elif btype in ("section", "callout"):
                    for s in block.get("sentences", []):
                        for fid in s.get("fact_ids", []):
                            self.assertIn(fid, facts, f"{name}: {btype} sentence fact_id '{fid}' not found in facts")

    def test_06_fixture_self_verification(self) -> None:
        """6. Self-verification of fixtures per ER-1 review requirements:
        - recomputes all facts from rows & reference_lines in the fixture, error <= 1e-6
        - input_observation_ids is not empty
        - dataset meets minimum thresholds by shape (ER-4 §4)
        - all sentences obey vocabulary and number matching rules
        """
        import re

        metric_directions = {
            "bank.npl_g35": "lower_is_better",
            "bank.llr_coverage": "higher_is_better",
            "bank.roa": "higher_is_better",
            "bank.roe": "higher_is_better",
        }

        def calc_median(numbers: list[float]) -> float:
            s = sorted(numbers)
            n = len(s)
            if n % 2 == 1:
                return float(s[n // 2])
            return float((s[n // 2 - 1] + s[n // 2]) / 2.0)

        def calc_ranks(entity_vals: list[tuple[str, float]], direction: str) -> dict[str, tuple[int, int]]:
            res = {}
            for entity, val in entity_vals:
                if direction == "lower_is_better":
                    rb = 1 + sum(1 for _, o in entity_vals if o < val)
                    rd = 1 + sum(1 for _, o in entity_vals if o > val)
                else:
                    rb = 1 + sum(1 for _, o in entity_vals if o > val)
                    rd = rb
                res[entity] = (rb, rd)
            return res

        report_fixtures = [
            "er-lookup-vcb-npl-2024q4.json",
            "er-ranking-coverage-2024q4.json",
            "er-trend-vpb-roe-2024.json",
            "er-h2h-acb-tcb-2024q4.json",
            "er-profile-acb-2024q4.json",
        ]

        for name in report_fixtures:
            path = FIXTURES_DIR / name
            data = json.loads(path.read_text(encoding="utf-8"))
            facts = data.get("facts", [])
            facts_by_id = {f["fact_id"]: f for f in facts}
            datasets = data.get("datasets", [])

            # --- 1. Dataset minimum thresholds by shape (ER-4 §4) ---
            for ds in datasets:
                shape = ds.get("shape")
                rows = ds.get("rows", [])
                valid_rows = [r for r in rows if r.get("status") == "valid" and r.get("value") is not None]
                if shape == "kpi":
                    self.assertTrue(1 <= len(rows) <= 6, f"{name}: KPI row count {len(rows)} not in 1..6")
                elif shape == "ranked_list":
                    self.assertGreaterEqual(len(valid_rows), 3, f"{name}: ranked_list valid rows {len(valid_rows)} < 3")
                elif shape == "series":
                    periods = set(r["period"] for r in rows)
                    self.assertGreaterEqual(len(periods), 2, f"{name}: series periods {len(periods)} < 2")
                elif shape == "series_multi":
                    metrics = set(r["metric_id"] for r in rows)
                    periods = set(r["period"] for r in rows)
                    self.assertGreaterEqual(len(metrics), 2, f"{name}: series_multi metrics {len(metrics)} < 2")
                    self.assertGreaterEqual(len(periods), 2, f"{name}: series_multi periods {len(periods)} < 2")
                elif shape == "paired":
                    entities = set(r["entity_id"] for r in valid_rows)
                    self.assertGreaterEqual(len(entities), 3, f"{name}: paired valid entities {len(entities)} < 3")
                elif shape == "peer_table":
                    entities = set(r["entity_id"] for r in rows)
                    metrics = set(r["metric_id"] for r in rows)
                    self.assertGreaterEqual(len(entities), 3, f"{name}: peer_table entities {len(entities)} < 3")
                    self.assertGreaterEqual(len(metrics), 2, f"{name}: peer_table metrics {len(metrics)} < 2")
                elif shape == "comparison_table":
                    entities = set(r["entity_id"] for r in rows)
                    self.assertTrue(2 <= len(entities) <= 5, f"{name}: comparison_table entities {len(entities)} not in 2..5")

            # --- 2. Fact input_observation_ids non-empty ---
            for fact in facts:
                obs_ids = fact.get("input_observation_ids")
                self.assertIsNotNone(obs_ids, f"{name}: fact {fact['fact_id']} missing input_observation_ids")
                self.assertGreater(len(obs_ids), 0, f"{name}: fact {fact['fact_id']} has empty input_observation_ids")

            # --- 3. Recompute every fact from rows & reference_lines ---
            row_vals: dict[tuple[str, str, str], float] = {}
            for ds in datasets:
                for r in ds.get("rows", []):
                    if r.get("value") is not None:
                        row_vals[(r["entity_id"], r["metric_id"], r["period"])] = float(r["value"])

            ref_lines: dict[tuple[str, str, str], float] = {}
            for ds in datasets:
                for ref in ds.get("reference_lines", []):
                    ref_lines[(ref["metric_id"], ref["period"], ref["kind"])] = float(ref["value"])

            for fact in facts:
                ftype = fact["fact_type"]
                val = fact["value"]
                m = fact.get("metric_id")
                p = fact.get("period")
                e = fact.get("entity_id")
                oe = fact.get("other_entity_id")
                fp = fact.get("from_period")

                if ftype == "value":
                    expected = row_vals.get((e, m, p))
                    self.assertIsNotNone(expected, f"{name}: missing row value for ({e}, {m}, {p})")
                    self.assertAlmostEqual(val, expected, delta=1e-6, msg=f"{name}: {fact['fact_id']}")
                elif ftype == "peer_median":
                    if (m, p, "median") in ref_lines:
                        expected = ref_lines[(m, p, "median")]
                    else:
                        m_vals = [v for (ent, met, per), v in row_vals.items() if met == m and per == p]
                        expected = calc_median(m_vals)
                    self.assertAlmostEqual(val, expected, delta=1e-6, msg=f"{name}: {fact['fact_id']}")
                elif ftype == "peer_rank":
                    direction = metric_directions[m]
                    pairs: dict[str, float] = {}
                    for ds in datasets:
                        for r in ds.get("rows", []):
                            if r.get("metric_id") == m and r.get("period") == p and r.get("value") is not None:
                                pairs[r["entity_id"]] = float(r["value"])
                    ranks = calc_ranks(list(pairs.items()), direction)
                    self.assertIn(e, ranks, f"{name}: {e} not in ranked pairs")
                    rb, rd = ranks[e]
                    self.assertEqual(fact["rank_better"], rb, f"{name}: {fact['fact_id']}")
                    self.assertEqual(fact["rank_desc"], rd, f"{name}: {fact['fact_id']}")
                    self.assertEqual(fact["denominator"], len(pairs), f"{name}: {fact['fact_id']}")
                elif ftype == "gap_to_median":
                    e_val = row_vals.get((e, m, p))
                    self.assertIsNotNone(e_val, f"{name}: missing row value for ({e}, {m}, {p})")
                    if (m, p, "median") in ref_lines:
                        med = ref_lines[(m, p, "median")]
                    else:
                        m_vals = [v for (ent, met, per), v in row_vals.items() if met == m and per == p]
                        med = calc_median(m_vals)
                    expected = e_val - med
                    self.assertAlmostEqual(val, expected, delta=1e-6, msg=f"{name}: {fact['fact_id']}")
                elif ftype == "delta":
                    v_to = row_vals.get((e, m, p))
                    v_from = row_vals.get((e, m, fp))
                    self.assertIsNotNone(v_to, f"{name}: missing row value for ({e}, {m}, {p})")
                    self.assertIsNotNone(v_from, f"{name}: missing row value for ({e}, {m}, {fp})")
                    expected = v_to - v_from
                    self.assertAlmostEqual(val, expected, delta=1e-6, msg=f"{name}: {fact['fact_id']}")
                elif ftype == "median_delta":
                    med_to = ref_lines.get((m, p, "median"))
                    if med_to is None:
                        med_to = calc_median([v for (ent, met, per), v in row_vals.items() if met == m and per == p])
                    med_from = ref_lines.get((m, fp, "median"))
                    if med_from is None:
                        med_from = calc_median([v for (ent, met, per), v in row_vals.items() if met == m and per == fp])
                    expected = med_to - med_from
                    self.assertAlmostEqual(val, expected, delta=1e-6, msg=f"{name}: {fact['fact_id']}")
                elif ftype == "pairwise_gap":
                    va = row_vals.get((e, m, p))
                    vb = row_vals.get((oe, m, p))
                    self.assertIsNotNone(va, f"{name}: missing row value for ({e}, {m}, {p})")
                    self.assertIsNotNone(vb, f"{name}: missing row value for ({oe}, {m}, {p})")
                    expected = va - vb
                    self.assertAlmostEqual(val, expected, delta=1e-6, msg=f"{name}: {fact['fact_id']}")
                elif ftype == "spread":
                    m_vals = [v for (ent, met, per), v in row_vals.items() if met == m and per == p]
                    expected = max(m_vals) - min(m_vals)
                    self.assertAlmostEqual(val, expected, delta=1e-6, msg=f"{name}: {fact['fact_id']}")
                elif ftype == "ratio_to_median":
                    e_val = row_vals.get((e, m, p))
                    self.assertIsNotNone(e_val, f"{name}: missing row value for ({e}, {m}, {p})")
                    med = ref_lines.get((m, p, "median"))
                    if med is None:
                        med = calc_median([v for (ent, met, per), v in row_vals.items() if met == m and per == p])
                    expected = e_val / med
                    self.assertAlmostEqual(val, expected, delta=1e-6, msg=f"{name}: {fact['fact_id']}")
                elif ftype == "derived_ratio":
                    if m == "derived.roe_over_roa":
                        v_roe = row_vals.get((e, "bank.roe", p))
                        v_roa = row_vals.get((e, "bank.roa", p))
                        self.assertIsNotNone(v_roe, f"{name}: missing roe for ({e}, {p})")
                        self.assertIsNotNone(v_roa, f"{name}: missing roa for ({e}, {p})")
                        expected = v_roe / v_roa
                        self.assertAlmostEqual(val, expected, delta=1e-6, msg=f"{name}: {fact['fact_id']}")
                elif ftype == "lead_count":
                    metrics = list(dict.fromkeys([met for (ent, met, per) in row_vals.keys() if ent in (e, oe) and per == p]))
                    leads = 0
                    for met in metrics:
                        va = row_vals[(e, met, p)]
                        vb = row_vals[(oe, met, p)]
                        mdir = metric_directions[met]
                        if mdir == "lower_is_better":
                            if va < vb:
                                leads += 1
                        else:
                            if va > vb:
                                leads += 1
                    self.assertEqual(val, float(leads), f"{name}: {fact['fact_id']}")
                    self.assertEqual(fact["denominator"], len(metrics), f"{name}: {fact['fact_id']}")

            # --- 4. Vocabulary rules and number matching in sentences ---
            sentences = []
            spec = data.get("report_spec", {})
            for block in spec.get("blocks", []):
                btype = block.get("type")
                if btype == "headline":
                    sentences.append(block.get("sentence", {}))
                elif btype == "answer":
                    sentences.extend(block.get("sentences", []))
                elif btype == "key_points":
                    for item in block.get("items", []):
                        sentences.extend(item.get("sentences", []))
                elif btype == "figure":
                    sentences.append(block.get("takeaway", {}))
                elif btype in ("section", "callout"):
                    sentences.extend(block.get("sentences", []))

            for sent in sentences:
                text = sent.get("text", "")
                text_lower = text.lower()
                cited_ids = sent.get("fact_ids", [])
                cited_facts = [facts_by_id[fid] for fid in cited_ids if fid in facts_by_id]
                cited_types = {f["fact_type"] for f in cited_facts}

                # 4.1 No causal words
                for causal in ["vì", "nhờ", "dẫn đến", "khiến"]:
                    self.assertIsNone(
                        re.search(rf"\b{re.escape(causal)}\b", text_lower),
                        f"{name}: sentence contains causal word '{causal}': {text}",
                    )

                # 4.2 Rank words: "nhất", "hạng", "nhóm đầu"
                if any(w in text_lower for w in ["nhất", "hạng", "nhóm đầu"]):
                    self.assertIn(
                        "peer_rank",
                        cited_types,
                        f"{name}: sentence with rank word must cite peer_rank fact: {text}",
                    )

                # 4.3 Comparison words: "cao hơn", "thấp hơn", "trung vị", "nhỉnh hơn", "dẫn trước"
                if any(w in text_lower for w in ["cao hơn", "thấp hơn", "trên trung vị", "dưới trung vị", "nhỉnh hơn", "dẫn trước"]):
                    comp_types = {"gap_to_median", "pairwise_gap", "lead_count", "derived_ratio"}
                    self.assertTrue(
                        cited_types.intersection(comp_types),
                        f"{name}: sentence with comparison word must cite comparison fact: {text}",
                    )

                # 4.4 Trend words: "tăng", "giảm", "liên tục", "cải thiện", "thu hẹp"
                if any(w in text_lower for w in ["tăng", "giảm", "liên tục", "cải thiện", "thu hẹp"]):
                    self.assertTrue(
                        "delta" in cited_types or "median_delta" in cited_types,
                        f"{name}: sentence with trend word must cite delta fact: {text}",
                    )

                # 4.5 Ratio words: "lần", "gấp"
                if any(w in text_lower for w in ["lần", "gấp"]):
                    ratio_types = {"ratio_to_median", "derived_ratio"}
                    self.assertTrue(
                        cited_types.intersection(ratio_types),
                        f"{name}: sentence with ratio word must cite ratio fact: {text}",
                    )

                # 4.6 Numbers in sentence match cited facts
                # Match decimals with comma (e.g. 0,96, 21,75, 10,25)
                decimal_matches = re.findall(r"\b\d+,\d+\b", text)
                for dm in decimal_matches:
                    dval = float(dm.replace(",", "."))
                    matched = any(
                        abs(round(abs(f["value"]), 2) - dval) < 1e-4
                        or abs(round(abs(f["value"]), 1) - dval) < 1e-4
                        or abs(abs(f["value"]) - dval) < 1e-4
                        for f in cited_facts
                    )
                    self.assertTrue(matched, f"{name}: number {dm} in sentence does not match any cited fact: {text}")

                # Match fractions (e.g. 3/4, 1/4)
                fraction_matches = re.findall(r"\b\d+/\d+\b", text)
                for fm in fraction_matches:
                    # Exclude quarters like 4/2024 or 3/2024
                    if "/202" in fm:
                        continue
                    matched = any(
                        f.get("fact_type") == "lead_count"
                        and f"{int(f['value'])}/{f['denominator']}" == fm
                        for f in cited_facts
                    )
                    self.assertTrue(matched, f"{name}: fraction {fm} does not match any cited lead_count fact: {text}")

    def test_07_humanize_locator(self) -> None:
        """7. Verify humanize_locator correctly parses real Gold v5 source locators per ER-3 §4."""
        from scripts.er_fixture_helpers import humanize_locator

        s1 = (
            "pdf_pages:29;printed_page:21;section:note_5_customer_loans;row:loan_quality;"
            "denominator:dư_nợ_cho_vay;groups:3|4|5;extraction:visual_transcription"
        )
        self.assertEqual(humanize_locator(s1), "tr. 21 · note 5 customer loans")

        s2 = "pdf_page:17;printed_page:15;section:Phân tích chất lượng nợ cho vay;extraction:visual_check"
        self.assertEqual(humanize_locator(s2), "tr. 15 · Phân tích chất lượng nợ cho vay")


if __name__ == "__main__":
    unittest.main()

