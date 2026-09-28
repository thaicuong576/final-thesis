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


if __name__ == "__main__":
    unittest.main()
