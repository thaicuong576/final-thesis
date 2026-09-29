"""End-to-end offline integration tests for ER-4 narrative critique and modular reports (PR-4 §11).

Tests the full execution pipeline against simulated Table C Gold data:
1. 5 questions B1-B5 of acceptance-questions: correct kind, block types, chart types; all sentences pass verifier.
2. Writer returns bad sentence ("Nợ xấu cải thiện...") -> dropped, audited, run completes.
3. compose_report returns invalid chart for dataset -> swapped to allowed chart or dropped.
4. compose_report returns garbage -> default_report_spec, accepted_with_limitations.
5. Critic round 1 flags sentence -> rewrite passes verifier -> round 2 accepted (before/after tracked).
6. Critic flags duplicate figure -> block removed in final spec.
7. Writer raises exception -> graceful fallback to default_report_spec, no crash.
8. Configurable analysis arms (single_agent, hierarchical_no_critique, hierarchical_with_critique).
"""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from typing import Any, Mapping, Sequence
from unittest.mock import patch

from tests.socket_guard import install_socket_guard


def setUpModule() -> None:
    install_socket_guard()


from thesis_data.dataset_contract import (
    AnalyticalLevel,
    CanonicalObservation,
    DatasetCapabilityCatalog,
    DatasetEntity,
    DatasetEntityType,
    DatasetEvidence,
    DatasetMetric,
    DatasetPeriod,
    DatasetRef,
    DatasetSource,
    PeerUniverse,
    QualityStatus,
    SourceTier,
    SupportedOperation,
)
from thesis_data.dataset_provider import aggregate_peer_median
from thesis_data.narrative_verification import (
    NarrativeSentence,
    VerificationContext,
    verify_sentence,
)
from thesis_data.report_facts import Fact
from thesis_data.report_spec import validate_report_spec
from thesis_data.schema import (
    CritiqueAction,
    CritiqueIssue,
    CritiqueIssueStatus,
    CritiqueIssueType,
    CritiqueSeverity,
)
from thesis_data.semantic_evaluation import (
    ApplicableLinkResult,
    SemanticDimension,
    SemanticDimensionApplicability,
    SemanticDimensionResult,
    StructuredCriticResult,
    expected_dimension_applicability,
)
from thesis_data.storage import create_gold_snapshot_schema

from thesis_api.adaptive_runtime import _AdaptiveRun
from thesis_api.narrative_templates import (
    default_report_spec,
    describe_fact,
    display_fact,
    make_fallback_sentence,
)
from thesis_api.schemas import (
    AnalysisRequest,
    AnalysisResponse,
    ReportSpecDTO,
)
from thesis_api.service import AnalysisEngine, ProviderBinding
from thesis_api.settings import Settings


class _TableCGoldProvider:
    """Offline test double implementing the exact Table C Gold figures."""

    def __init__(self) -> None:
        self.dataset_ref = DatasetRef(dataset_id="gold-c-fixture", dataset_snapshot_id="gold-c-v1")
        self.entities = ("ACB", "MBB", "TCB", "VCB", "VPB")
        self.periods = ("2024_Q1", "2024_Q2", "2024_Q3", "2024_Q4")
        self.metrics = ("bank.npl_g35", "bank.llr_coverage", "bank.roa", "bank.roe")

        # Table C Q4 values:
        # ACB: NPL 1.5122, LLR 76.5591, ROA 2.1215, ROE 21.7459
        # MBB: NPL 1.6205, LLR 92.2484, ROA 2.2135, ROE 22.0939
        # TCB: NPL 1.17, LLR 113.8, ROA 2.4, ROE 15.5
        # VCB: NPL 0.9636, LLR 223.311, ROA 1.7249, ROE 18.5965
        # VPB: NPL 4.1956, LLR 56.1749, ROA 1.8361, ROE 11.4117
        q4_vals = {
            "ACB": {"bank.npl_g35": 1.5122, "bank.llr_coverage": 76.5591, "bank.roa": 2.1215, "bank.roe": 21.7459},
            "MBB": {"bank.npl_g35": 1.6205, "bank.llr_coverage": 92.2484, "bank.roa": 2.2135, "bank.roe": 22.0939},
            "TCB": {"bank.npl_g35": 1.17, "bank.llr_coverage": 113.8, "bank.roa": 2.4, "bank.roe": 15.5},
            "VCB": {"bank.npl_g35": 0.9636, "bank.llr_coverage": 223.311, "bank.roa": 1.7249, "bank.roe": 18.5965},
            "VPB": {"bank.npl_g35": 4.1956, "bank.llr_coverage": 56.1749, "bank.roa": 1.8361, "bank.roe": 11.4117},
        }

        # Multi-period values for trends and Q3->Q4 changes:
        # VPB ROE: Q1: 8.0671, Q2: 8.5867, Q3: 9.6445, Q4: 11.4117
        # ACB LLR: Q3: 79.0691 -> delta = -2.51
        # VCB NPL: Q3: 1.2228 -> delta = -0.2592
        q3_vals = {
            "ACB": {"bank.npl_g35": 1.50, "bank.llr_coverage": 79.0691, "bank.roa": 2.10, "bank.roe": 21.0},
            "MBB": {"bank.npl_g35": 1.60, "bank.llr_coverage": 90.0, "bank.roa": 2.20, "bank.roe": 22.0},
            "TCB": {"bank.npl_g35": 1.15, "bank.llr_coverage": 110.0, "bank.roa": 2.35, "bank.roe": 15.0},
            "VCB": {"bank.npl_g35": 1.2228, "bank.llr_coverage": 220.0, "bank.roa": 1.70, "bank.roe": 18.0},
            "VPB": {"bank.npl_g35": 4.15, "bank.llr_coverage": 55.0, "bank.roa": 1.80, "bank.roe": 9.6445},
        }
        q2_vals = {
            "ACB": {"bank.npl_g35": 1.48, "bank.llr_coverage": 80.0, "bank.roa": 2.05, "bank.roe": 20.5},
            "MBB": {"bank.npl_g35": 1.58, "bank.llr_coverage": 88.0, "bank.roa": 2.15, "bank.roe": 21.5},
            "TCB": {"bank.npl_g35": 1.12, "bank.llr_coverage": 108.0, "bank.roa": 2.30, "bank.roe": 14.8},
            "VCB": {"bank.npl_g35": 1.25, "bank.llr_coverage": 215.0, "bank.roa": 1.68, "bank.roe": 17.8},
            "VPB": {"bank.npl_g35": 4.10, "bank.llr_coverage": 54.0, "bank.roa": 1.78, "bank.roe": 8.5867},
        }
        q1_vals = {
            # ACB in Q1: 4 missing cells
            "MBB": {"bank.npl_g35": 1.55, "bank.llr_coverage": 85.0, "bank.roa": 2.10, "bank.roe": 21.0},
            "TCB": {"bank.npl_g35": 1.10, "bank.llr_coverage": 105.0, "bank.roa": 2.25, "bank.roe": 14.5},
            "VCB": {"bank.npl_g35": 1.28, "bank.llr_coverage": 210.0, "bank.roa": 1.65, "bank.roe": 17.5},
            "VPB": {"bank.npl_g35": 4.05, "bank.llr_coverage": 53.0, "bank.roa": 1.75, "bank.roe": 8.0671},
        }

        period_tables = {
            "2024_Q1": q1_vals,
            "2024_Q2": q2_vals,
            "2024_Q3": q3_vals,
            "2024_Q4": q4_vals,
        }

        self.observations: dict[tuple[str, str, str], CanonicalObservation] = {}
        self.obs_by_id: dict[str, CanonicalObservation] = {}
        self.sources: dict[str, DatasetSource] = {}
        self.evidences: dict[str, list[DatasetEvidence]] = {}

        for ent in self.entities:
            src_id = f"source-{ent}"
            self.sources[src_id] = DatasetSource(
                source_ref=src_id,
                source_type="filing",
                source_tier=SourceTier.PRIMARY,
                source_url=f"https://example.test/{ent}/filing",
                publisher=f"Ngân hàng {ent}",
                retrieved_at="2026-09-25T00:00:00Z",
                content_hash=f"hash-{ent}",
                validation_status=QualityStatus.VALID,
            )
            self.evidences[src_id] = []

            for p in self.periods:
                p_table = period_tables[p]
                for m in self.metrics:
                    obs_id = f"obs-{ent}-{p}-{m}"
                    if ent == "ACB" and p == "2024_Q1":
                        obs = CanonicalObservation(
                            observation_id=obs_id,
                            dataset_id=self.dataset_ref.dataset_id,
                            dataset_snapshot_id=self.dataset_ref.dataset_snapshot_id,
                            entity_id=ent,
                            period_id=p,
                            metric_id=m,
                            value=None,
                            unit="%",
                            period_basis="point_in_time",
                            reporting_scope=None,
                            validation_status=QualityStatus.MISSING,
                            missing_reason="DATA_UNAVAILABLE",
                        )
                    else:
                        v = p_table[ent][m]
                        loc = f"table:{m};row:{ent};period:{p}"
                        obs = CanonicalObservation(
                            observation_id=obs_id,
                            dataset_id=self.dataset_ref.dataset_id,
                            dataset_snapshot_id=self.dataset_ref.dataset_snapshot_id,
                            entity_id=ent,
                            period_id=p,
                            metric_id=m,
                            value=v,
                            unit="%",
                            period_basis="point_in_time",
                            reporting_scope="consolidated",
                            validation_status=QualityStatus.VALID,
                            source_ref=src_id,
                            source_locator=loc,
                        )
                        evi = DatasetEvidence(
                            evidence_id=f"evi-{ent}-{p}-{m}",
                            source_ref=src_id,
                            entity_id=ent,
                            period_id=p,
                            metric_id=m,
                            locator=loc,
                            quote=f"Báo cáo tài chính {ent} {p} ghi nhận chỉ tiêu {m} đạt {v}%.",
                        )
                        self.evidences[src_id].append(evi)

                    self.observations[(ent, p, m)] = obs
                    self.obs_by_id[obs_id] = obs

        self.catalog = DatasetCapabilityCatalog(
            dataset_ref=self.dataset_ref,
            entities=tuple(
                DatasetEntity(
                    entity_id=e,
                    entity_type=DatasetEntityType.COMPANY,
                    display_name=e,
                    attributes={"sector": "bank"},
                )
                for e in self.entities
            ),
            periods=tuple(DatasetPeriod(period_id=p, label=p) for p in self.periods),
            metrics=tuple(
                DatasetMetric(
                    metric_id=m,
                    display_name=m,
                    analytical_level=AnalyticalLevel.COMPANY,
                    default_unit="%",
                )
                for m in self.metrics
            ),
            peer_universes=(
                PeerUniverse(
                    peer_universe_id="sector:bank",
                    display_name="Vietnamese Listed Banks",
                    entity_ids=tuple(self.entities),
                ),
            ),
            source_refs=tuple(self.sources.keys()),
            supported_operations=(
                SupportedOperation.GET_METRIC,
                SupportedOperation.GET_ENTITY_METRICS,
                SupportedOperation.GET_PEER_BENCHMARK,
                SupportedOperation.RESOLVE_OBSERVATION,
                SupportedOperation.GET_SOURCE,
                SupportedOperation.GET_EVIDENCE,
            ),
        )

    def get_capabilities(self, _dataset_ref: DatasetRef) -> DatasetCapabilityCatalog:
        return self.catalog

    def get_metric(
        self, _dataset_ref: DatasetRef, entity_id: str, period_id: str, metric_id: str
    ) -> CanonicalObservation | None:
        return self.observations.get((entity_id, period_id, metric_id))

    def get_entity_metrics(
        self,
        _dataset_ref: DatasetRef,
        entity_id: str,
        period_ids: Sequence[str],
        metric_ids: Sequence[str],
    ) -> tuple[CanonicalObservation, ...]:
        res = []
        for p in period_ids:
            for m in metric_ids:
                obs = self.get_metric(_dataset_ref, entity_id, p, m)
                if obs is not None:
                    res.append(obs)
        return tuple(res)

    def get_peer_benchmark(
        self,
        dataset_ref: DatasetRef,
        peer_universe_id: str,
        period_id: str,
        metric_ids: Sequence[str],
        peer_entity_ids: Sequence[str] | None = None,
    ) -> tuple[CanonicalObservation, ...]:
        res = []
        members = peer_entity_ids or self.entities
        for m in metric_ids:
            valid_obs = [
                self.observations[(e, period_id, m)]
                for e in members
                if (e, period_id, m) in self.observations
                and self.observations[(e, period_id, m)].validation_status is QualityStatus.VALID
            ]
            res.append(
                aggregate_peer_median(
                    dataset_ref=dataset_ref,
                    peer_universe_id=peer_universe_id,
                    period_id=period_id,
                    metric_id=m,
                    peer_entity_ids=members,
                    member_observations=valid_obs,
                )
            )
        return tuple(res)

    def resolve_observation(self, _dataset_ref: DatasetRef, observation_id: str) -> CanonicalObservation | None:
        return self.obs_by_id.get(observation_id)

    def get_source(self, _dataset_ref: DatasetRef, source_ref: str) -> DatasetSource | None:
        return self.sources.get(source_ref)

    def get_evidence(
        self,
        _dataset_ref: DatasetRef,
        source_refs: Sequence[str],
        entity_id: str | None = None,
        period_id: str | None = None,
        metric_id: str | None = None,
    ) -> tuple[DatasetEvidence, ...]:
        res = []
        for sref in source_refs:
            for evi in self.evidences.get(sref, []):
                if entity_id and evi.entity_id != entity_id:
                    continue
                if period_id and evi.period_id != period_id:
                    continue
                if metric_id and evi.metric_id != metric_id:
                    continue
                res.append(evi)
        return tuple(res)


class _TestOfflineWriter:
    """Offline writer double for ER-4 end-to-end tests."""

    def __init__(
        self,
        *,
        injected_bad_sentence: str | None = None,
        injected_bad_chart: str | None = None,
        injected_garbage_spec: bool = False,
        should_raise: bool = False,
    ) -> None:
        self.injected_bad_sentence = injected_bad_sentence
        self.injected_bad_chart = injected_bad_chart
        self.injected_garbage_spec = injected_garbage_spec
        self.should_raise = should_raise
        self.write_findings_calls: list[dict] = []
        self.compose_report_calls: list[dict] = []
        self.rewrite_sentence_calls: list[dict] = []

    def write_findings(
        self,
        *,
        role: str,
        question: str,
        question_type: str,
        facts: Sequence[Mapping[str, Any]],
        datasets_summary: Sequence[Mapping[str, Any]],
        candidates: Sequence[Mapping[str, Any]] = (),
        max_sentences: int = 4,
    ) -> list[dict[str, Any]]:
        if self.should_raise:
            raise RuntimeError("Model service unavailable")
        self.write_findings_calls.append(dict(role=role, question=question, question_type=question_type))

        if self.injected_bad_sentence is not None:
            fid = facts[0]["fact_id"] if facts else "f-1"
            return [{"text": self.injected_bad_sentence, "fact_ids": [fid]}]

        results = []
        for f in facts[:max_sentences]:
            fid = f.get("fact_id", "")
            mota = f.get("mo_ta") or "Chỉ tiêu"
            hienthi = f.get("hien_thi") or str(f.get("value", ""))
            results.append({
                "text": f"{mota} đạt {hienthi}.",
                "fact_ids": [fid],
            })
        return results

    def compose_report(
        self,
        *,
        question: str,
        question_type: str,
        sentences: Sequence[Mapping[str, Any]],
        datasets_summary: Sequence[Mapping[str, Any]],
        signals: Sequence[Mapping[str, Any]] | None = None,
        findings: Sequence[Mapping[str, Any]] | None = None,
        facts: Sequence[Mapping[str, Any]] | None = None,
    ) -> dict[str, Any]:
        if self.should_raise:
            raise RuntimeError("Model service unavailable")
        self.compose_report_calls.append(dict(question=question, question_type=question_type))

        if self.injected_garbage_spec:
            return {"garbage_field": "corrupted json without blocks"}

        # Assemble layout based on question type
        if question_type == "lookup":
            val_fid = facts[0]["fact_id"] if facts else "f-1"
            return {
                "kind": "answer_card",
                "blocks": [
                    {
                        "type": "answer",
                        "value_fact_id": val_fid,
                        "sentences": [
                            {"sentence_id": s["sentence_id"]}
                            for s in sentences[:1]
                        ] if sentences else [],
                    }
                ],
            }

        blocks: list[dict[str, Any]] = []
        # Headline
        if sentences:
            blocks.append({
                "type": "headline",
                "sentence": {"sentence_id": sentences[0]["sentence_id"]},
            })
        elif facts:
            f0 = facts[0]
            blocks.append({
                "type": "headline",
                "sentence": {
                    "text": f"{f0.get('mo_ta', 'Chỉ tiêu')} đạt {f0.get('hien_thi', '')}.",
                    "fact_ids": [f0["fact_id"]],
                },
            })

        # Figures
        if self.injected_bad_chart and datasets_summary:
            ds0 = datasets_summary[0]
            fid = facts[0]["fact_id"] if facts else "f-1"
            blocks.append({
                "type": "figure",
                "figure_no": 1,
                "chart": self.injected_bad_chart,
                "dataset_id": ds0["dataset_id"],
                "title": ds0["title"],
                "takeaway": {
                    "text": f"{ds0['title']} được ghi nhận theo dữ liệu công bố.",
                    "fact_ids": [fid],
                },
            })
        else:
            for idx, ds in enumerate(datasets_summary[:2], start=1):
                chart = ds.get("allowed_charts", ["rank_heatmap"])[0] if ds.get("allowed_charts") else "rank_heatmap"
                fid = facts[0]["fact_id"] if facts else "f-1"
                blocks.append({
                    "type": "figure",
                    "figure_no": idx,
                    "chart": chart,
                    "dataset_id": ds["dataset_id"],
                    "title": ds["title"],
                    "takeaway": {
                        "text": f"{ds['title']} thể hiện dữ liệu phân tích.",
                        "fact_ids": [fid],
                    },
                })

        # Key points
        if len(sentences) > 1:
            blocks.append({
                "type": "key_points",
                "items": [
                    {
                        "title": "Nhận định chính",
                        "sentences": [
                            {"sentence_id": s["sentence_id"]}
                            for s in sentences[1:4]
                        ],
                    }
                ],
            })

        # Callout for findings
        if findings:
            fnd = findings[0]
            fid = fnd.get("fact_ids", [facts[0]["fact_id"] if facts else "f-1"])[0]
            blocks.append({
                "type": "callout",
                "tone": "notice",
                "title": fnd.get("text", "Phát hiện liên tầng"),
                "sentences": [
                    {
                        "text": f"{fnd.get('text', 'Phát hiện')} được ghi nhận từ dữ liệu.",
                        "fact_ids": [fid],
                    }
                ],
            })

        return {
            "kind": "note",
            "blocks": blocks,
        }

    def rewrite_sentence(
        self,
        *,
        role: str,
        question: str,
        sentence: Mapping[str, Any],
        issue: Mapping[str, Any],
        facts: Sequence[Mapping[str, Any]],
    ) -> dict[str, Any]:
        self.rewrite_sentence_calls.append(dict(role=role, question=question, sentence=sentence, issue=issue))
        if facts:
            f = facts[0]
            mota = f.get("mo_ta") or "Chỉ tiêu"
            hienthi = f.get("hien_thi") or str(f.get("value", ""))
            return {
                "text": f"{mota} ghi nhận {hienthi}.",
                "fact_ids": [f["fact_id"]],
            }
        return {
            "text": "Dữ liệu được cập nhật phù hợp.",
            "fact_ids": [],
        }


class _TestOfflineCritic:
    """Offline critic double with customizable scenarios."""

    def __init__(
        self,
        *,
        round1_issue_sentence: bool = False,
        round1_issue_duplicate_figure: bool = False,
    ) -> None:
        self.round1_issue_sentence = round1_issue_sentence
        self.round1_issue_duplicate_figure = round1_issue_duplicate_figure
        self.calls = 0

    def evaluate(self, *, plan, claims, stage1_report, round_context):
        del stage1_report
        self.calls += 1
        claim_ids = tuple(claim.claim_id for claim in claims)
        issues: list[CritiqueIssue] = []

        if self.round1_issue_sentence:
            if round_context.round_number == 0:
                s_id = round_context.narrative[0].sentence_id if round_context.narrative else "s-1"
                issues.append(
                    CritiqueIssue(
                        issue_id="issue-sentence-unsupported",
                        issue_type=CritiqueIssueType.UNSUPPORTED_CLAIM,
                        severity=CritiqueSeverity.MAJOR,
                        affected_agent="company",
                        affected_sentence_ids=(s_id,),
                        affected_requirement_ids=tuple(item.requirement_id for item in plan.requirements),
                        description="Nhận định cần được diễn đạt chính xác theo số liệu.",
                        required_action=CritiqueAction.REVISE_CLAIM,
                        resolution_status=CritiqueIssueStatus.OPEN,
                    )
                )
            else:
                # Resolved in round 2
                s_id = round_context.narrative[0].sentence_id if round_context.narrative else "s-1"
                issues.append(
                    CritiqueIssue(
                        issue_id="issue-sentence-unsupported",
                        issue_type=CritiqueIssueType.UNSUPPORTED_CLAIM,
                        severity=CritiqueSeverity.MAJOR,
                        affected_agent="company",
                        affected_sentence_ids=(s_id,),
                        affected_requirement_ids=tuple(item.requirement_id for item in plan.requirements),
                        description="Nhận định đã được cập nhật chính xác.",
                        required_action=CritiqueAction.REVISE_CLAIM,
                        resolution_status=CritiqueIssueStatus.RESOLVED,
                    )
                )

        if self.round1_issue_duplicate_figure:
            # Drop block 1
            issues.append(
                CritiqueIssue(
                    issue_id="issue-dup-figure",
                    issue_type=CritiqueIssueType.INCOMPLETE_SYNTHESIS,
                    severity=CritiqueSeverity.MINOR,
                    affected_agent="orchestrator",
                    affected_block_index=1,
                    affected_requirement_ids=tuple(item.requirement_id for item in plan.requirements),
                    description="Hình trùng lặp ý, đề nghị lược bỏ.",
                    required_action=CritiqueAction.REMOVE_CLAIM,
                    resolution_status=CritiqueIssueStatus.OPEN,
                )
            )

        dimensions = []
        for dimension, applicability in expected_dimension_applicability(plan).items():
            dimensions.append(
                SemanticDimensionResult(
                    dimension=dimension,
                    applicability=applicability,
                    score=0.9 if applicability is SemanticDimensionApplicability.APPLICABLE else None,
                    rationale="Offline critic test fixture acceptance.",
                    supporting_claim_ids=claim_ids if applicability is SemanticDimensionApplicability.APPLICABLE else (),
                )
            )

        return StructuredCriticResult(
            evaluator_version="test-only-offline-er-critic-v1",
            dimension_scores=tuple(dimensions),
            critique_issues=tuple(issues),
            fulfilled_requirement_ids=tuple(item.requirement_id for item in plan.requirements),
        )


class ApiERReportTests(unittest.TestCase):
    def setUp(self) -> None:
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.db_path = Path(self.directory.name) / "test-er.sqlite"
        create_gold_snapshot_schema(self.db_path)

        self.settings = Settings(
            app_name="final-thesis-api-test",
            app_env="test",
            sqlite_db_path=str(self.db_path),
            analysis_runs_db_path=str(Path(self.directory.name) / "runs.sqlite"),
            planner_mode="rules_only",
            openai_api_key="test-key",
            analysis_arm="hierarchical_with_critique",
        )

        self.provider = _TableCGoldProvider()
        self.binding = ProviderBinding(self.provider, self.provider.dataset_ref, self.provider.catalog, "gold-c-fixture")
        self.load_patch = patch("thesis_api.service._load_provider", return_value=self.binding)
        self.load_patch.start()
        self.addCleanup(self.load_patch.stop)

    def _run_query(
        self,
        query: str,
        *,
        writer: Any = None,
        critic: Any = None,
        arm: str = "hierarchical_with_critique",
    ) -> AnalysisResponse:
        settings = self.settings.model_copy(update={"analysis_arm": arm})
        w = writer or _TestOfflineWriter()
        c = critic or _TestOfflineCritic()
        with patch("thesis_api.adaptive_runtime.build_openai_semantic_critic", return_value=c):
            engine = AnalysisEngine(
                self.db_path,
                settings,
                semantic_critic=c,
                analysis_writer=w,
            )
            return engine._analyze(AnalysisRequest(query=query))

    def test_11_1_b1_to_b5_acceptance_questions_and_report_shapes(self) -> None:
        """Scenario 1: 5 questions B1-B5 match expected kind and block layout, and all sentences pass verifier."""
        questions = [
            ("B1", "Sức khỏe tài chính của ACB so với các ngân hàng cùng nhóm, quý 4/2024", "company_profile", "note"),
            ("B2", "Ngân hàng nào có đệm dự phòng dày nhất quý 4/2024?", "ranking", "note"),
            ("B3", "ROE của VPB thay đổi thế nào trong năm 2024?", "trend", "note"),
            ("B4", "So sánh ACB và TCB quý 4/2024", "head_to_head", "note"),
            ("B5", "Tỷ lệ nợ xấu của VCB quý 4/2024 là bao nhiêu?", "lookup", "answer_card"),
        ]

        for q_id, query, expected_qtype, expected_kind in questions:
            with self.subTest(question_id=q_id, query=query):
                report = self._run_query(query)
                self.assertIn(report.status, ("completed", "accepted_with_limitations"))
                self.assertEqual(report.question_type, expected_qtype)
                self.assertIsNotNone(report.report_spec)
                self.assertEqual(report.report_spec.kind, expected_kind)

                # Check block types
                block_types = [b.type for b in report.report_spec.blocks]
                if expected_kind == "answer_card":
                    self.assertIn("answer", block_types)
                    fig_count = sum(1 for bt in block_types if bt == "figure")
                    self.assertLessEqual(fig_count, 1)
                else:
                    self.assertIn("headline", block_types)

                if q_id == "B1":
                    # B1 company profile: headline, key_points, figures, callouts
                    self.assertIn("key_points", block_types)
                elif q_id == "B2":
                    # B2 ranking: headline, figure (ranked_bar), key_points
                    figures = [b for b in report.report_spec.blocks if b.type == "figure"]
                    self.assertTrue(any(f.chart == "ranked_bar" for f in figures))
                elif q_id == "B3":
                    # B3 trend: headline, figure (line_trend), key_points
                    figures = [b for b in report.report_spec.blocks if b.type == "figure"]
                    self.assertTrue(any(f.chart == "line_trend" for f in figures))
                elif q_id == "B4":
                    # B4 head to head: headline, figure (comparison_table or grouped_bar)
                    figures = [b for b in report.report_spec.blocks if b.type == "figure"]
                    self.assertTrue(any(f.chart in ("comparison_table", "grouped_bar") for f in figures))

                # Verification audit: no numbers mismatched
                self.assertIsNotNone(report.narrative_audit)
                self.assertEqual(report.narrative_audit.numbers_matched, report.narrative_audit.numbers_checked)

    def test_11_2_writer_bad_sentence_rejected_by_verifier(self) -> None:
        """Scenario 2: Writer returns invalid sentence -> rejected by verifier, recorded in audit, run completed."""
        bad_text = "Nợ xấu của ACB cải thiện so với quý 3 và đạt 99,5%."
        writer = _TestOfflineWriter(injected_bad_sentence=bad_text)
        report = self._run_query("Sức khỏe tài chính của ACB so với các ngân hàng cùng nhóm, quý 4/2024", writer=writer)

        self.assertIn(report.status, ("completed", "accepted_with_limitations"))
        self.assertIsNotNone(report.narrative_audit)
        self.assertTrue(
            any(
                s.reason_code in ("number_mismatch", "trend_without_delta", "period_not_cited")
                for s in report.narrative_audit.sentences_dropped
            ),
            f"Expected bad sentence to be dropped, got: {report.narrative_audit.sentences_dropped}",
        )

    def test_11_3_compose_report_invalid_chart_dataset_corrected_or_dropped(self) -> None:
        """Scenario 3: compose_report returns incompatible chart -> swapped to allowed chart or dropped."""
        # Inject line_trend for a peer_table dataset
        writer = _TestOfflineWriter(injected_bad_chart="line_trend")
        report = self._run_query("Ngân hàng nào có đệm dự phòng dày nhất quý 4/2024?", writer=writer)

        self.assertIn(report.status, ("completed", "accepted_with_limitations"))
        self.assertIsNotNone(report.narrative_audit)
        # Blocks dropped or swapped
        figures = [b for b in report.report_spec.blocks if b.type == "figure"]
        for fig in figures:
            # Figure must not have line_trend on single-period ranked list
            ds = next((d for d in report.datasets if d.dataset_id == fig.dataset_id), None)
            if ds and len(ds.periods) < 2:
                self.assertNotEqual(fig.chart, "line_trend")

    def test_11_4_compose_report_garbage_fallback(self) -> None:
        """Scenario 4: compose_report returns garbage -> default_report_spec fallback, accepted_with_limitations."""
        writer = _TestOfflineWriter(injected_garbage_spec=True)
        report = self._run_query("Sức khỏe tài chính của ACB so với các ngân hàng cùng nhóm, quý 4/2024", writer=writer)

        self.assertEqual(report.status, "accepted_with_limitations")
        self.assertIsNotNone(report.report_spec)
        self.assertEqual(report.report_spec.kind, "note")
        self.assertTrue(len(report.report_spec.blocks) >= 2)

    def test_11_5_critic_round1_revision_accepted_round2(self) -> None:
        """Scenario 5: Critic round 1 flags sentence -> rewrite passes verifier -> round 2 accepted."""
        critic = _TestOfflineCritic(round1_issue_sentence=True)
        writer = _TestOfflineWriter()
        report = self._run_query(
            "Sức khỏe tài chính của ACB so với các ngân hàng cùng nhóm, quý 4/2024",
            writer=writer,
            critic=critic,
        )

        self.assertEqual(report.status, "completed")
        self.assertGreaterEqual(critic.calls, 2)
        self.assertTrue(len(writer.rewrite_sentence_calls) >= 1)
        self.assertIsNotNone(report.revision_summary)
        self.assertGreaterEqual(report.revision_summary.rounds_executed, 1)

    def test_11_6_critic_duplicate_image_dropped(self) -> None:
        """Scenario 6: Critic flags duplicate figure -> block removed in final report spec."""
        critic = _TestOfflineCritic(round1_issue_duplicate_figure=True)
        report = self._run_query(
            "Sức khỏe tài chính của ACB so với các ngân hàng cùng nhóm, quý 4/2024",
            critic=critic,
        )

        self.assertIn(report.status, ("completed", "accepted_with_limitations"))
        self.assertIsNotNone(report.narrative_audit)
        self.assertTrue(
            any("lược bỏ" in b.reason or "trùng" in b.reason for b in report.narrative_audit.blocks_dropped),
            f"Expected dropped figure block in audit: {report.narrative_audit.blocks_dropped}",
        )

    def test_11_7_writer_exception_fallback_without_error(self) -> None:
        """Scenario 7: Writer raises exception -> graceful fallback, run completes with limitation."""
        writer = _TestOfflineWriter(should_raise=True)
        report = self._run_query("Sức khỏe tài chính của ACB so với các ngân hàng cùng nhóm, quý 4/2024", writer=writer)

        self.assertEqual(report.status, "accepted_with_limitations")
        self.assertIsNotNone(report.report_spec)
        self.assertTrue(
            any("tự động vì mô hình không phản hồi" in lim for lim in report.limitations),
            f"Expected fallback limitation, got: {report.limitations}",
        )

    def test_11_8_three_analysis_arms(self) -> None:
        """Scenario 8: All 3 analysis arms execute properly and record their arm identifier."""
        query = "Sức khỏe tài chính của ACB so với các ngân hàng cùng nhóm, quý 4/2024"

        # 1. Single agent
        w_single = _TestOfflineWriter()
        c_single = _TestOfflineCritic()
        rep_single = self._run_query(query, writer=w_single, critic=c_single, arm="single_agent")
        self.assertEqual(len(w_single.write_findings_calls), 0)  # No specialist findings
        self.assertEqual(len(w_single.compose_report_calls), 1)
        self.assertEqual(c_single.calls, 0)  # No critic

        # 2. Hierarchical no critique
        w_hier = _TestOfflineWriter()
        c_hier = _TestOfflineCritic()
        rep_hier = self._run_query(query, writer=w_hier, critic=c_hier, arm="hierarchical_no_critique")
        self.assertGreater(len(w_hier.write_findings_calls), 0)  # Specialists called
        self.assertEqual(len(w_hier.compose_report_calls), 1)
        self.assertEqual(c_hier.calls, 0)  # No critic

        # 3. Hierarchical with critique
        w_crit = _TestOfflineWriter()
        c_crit = _TestOfflineCritic()
        rep_crit = self._run_query(query, writer=w_crit, critic=c_crit, arm="hierarchical_with_critique")
        self.assertGreater(len(w_crit.write_findings_calls), 0)
        self.assertEqual(len(w_crit.compose_report_calls), 1)
        self.assertGreater(c_crit.calls, 0)  # Critic called


if __name__ == "__main__":
    unittest.main()
