"""Integration tests for fail-closed, provider-backed POST /api/analyze."""

from __future__ import annotations

import sqlite3
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from fastapi.testclient import TestClient
from thesis_data.dataset_contract import (
    AnalyticalLevel,
    CanonicalObservation,
    DatasetCapabilityCatalog,
    DatasetEntity,
    DatasetEntityType,
    DatasetEvidence,
    DatasetMetric,
    DatasetPeriod,
    PeerUniverse,
    DatasetRef,
    DatasetSource,
    SupportedOperation,
)
from thesis_data.schema import (
    AssertionType,
    AtomicClaim,
    ClaimDataRef,
    ClaimScope,
    CritiqueAction,
    CritiqueIssue,
    CritiqueIssueStatus,
    CritiqueIssueType,
    CritiqueSeverity,
    InferenceType,
    QualityStatus,
    SourceTier,
    StructuredAssertion,
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

from thesis_api.main import create_app
from thesis_api.adaptive_runtime import _API_POLICY, _RuntimeStage1Evaluator, _plan_request
from thesis_api.schemas import AnalysisRequest, AnalysisResponse
from thesis_data.acceptance_resolver import ProviderStage1DatasetResolver
from thesis_api.service import (
    AnalysisBlocked,
    AnalysisEngine,
    ProviderBinding,
    _capabilities_payload,
    _load_provider as _load_provider_unwrapped,
    _requested_metrics,
    _stage1_claim,
)
from thesis_api.settings import Settings


class _ExplicitOfflineAcceptingCritic:
    """Contract-valid offline test double; never used by the production factory."""

    def __init__(self) -> None:
        self.calls = 0

    def evaluate(self, *, plan, claims, stage1_report, round_context):
        self.calls += 1
        del stage1_report, round_context
        claim_ids = tuple(claim.claim_id for claim in claims)
        dimensions = []
        for dimension, applicability in expected_dimension_applicability(plan).items():
            dimensions.append(SemanticDimensionResult(
                dimension=dimension,
                applicability=applicability,
                score=0.9 if applicability is SemanticDimensionApplicability.APPLICABLE else None,
                rationale="Explicit offline test fixture accepted the supplied claim structure.",
                supporting_claim_ids=claim_ids if applicability is SemanticDimensionApplicability.APPLICABLE else (),
            ))
        link_results = tuple(
            ApplicableLinkResult(
                link_id=link.link_id,
                score=0.9,
                rationale="Explicit offline test fixture confirmed the declared link was reviewed.",
                supporting_claim_ids=claim_ids[:1],
            )
            for link in plan.applicable_links
        )
        return StructuredCriticResult(
            evaluator_version="test-only-offline-accepting-critic-v1",
            dimension_scores=tuple(dimensions),
            fulfilled_requirement_ids=tuple(item.requirement_id for item in plan.requirements),
            applicable_link_results=link_results,
        )


class _ExplicitOfflineAnalysisWriter:
    """Test adapter for grounded prose; it never queries data or sources."""

    def __init__(self, *, respond_to_feedback: bool = True, injected_text: str | None = None, initial_text: str | None = None, missing_text: str | None = None, injected_summary: str | None = None) -> None:
        self.respond_to_feedback = respond_to_feedback
        self.injected_text = injected_text
        self.initial_text = initial_text
        self.missing_text = missing_text
        self.injected_summary = injected_summary
        self.specialist_calls: list[dict] = []
        self.synthesis_calls: list[dict] = []

    def write_specialist(self, *, plan, role, claims, issues):
        self.specialist_calls.append({
            "plan": plan,
            "role": role,
            "claim_ids": [item["claim_id"] for item in claims],
            "issues": issues,
        })
        result = {}
        for item in claims:
            claim_id = item["claim_id"]
            display_name = item["display_name"]
            prose = f"The {display_name} statement stays anchored to its accepted provider observation and declared scope."
            if issues and self.respond_to_feedback:
                issue = issues[0]
                prose += f" The specialist addressed the review request: {issue['description']} Action: {issue['required_action']}."
            elif not issues and self.initial_text is not None:
                prose += f" {self.initial_text}"
            if self.injected_text is not None:
                prose += f" {self.injected_text}"
            if self.missing_text is not None and item["accepted_observation"]["validation_status"] == "missing":
                prose += f" {self.missing_text}"
            result[claim_id] = {
                "prose": prose,
                "supporting_claim_ids": [claim_id],
            }
        return result

    def synthesize(self, *, plan, specialist_outputs, issues):
        self.synthesis_calls.append({"plan": plan, "specialist_outputs": specialist_outputs, "issues": issues})
        summary = "Specialist outputs stay within the frozen request scope and accepted provider evidence."
        if issues and self.respond_to_feedback:
            summary += " The synthesis addresses the selected review request: " + " ".join(item["description"] for item in issues)
        if self.injected_summary is not None:
            summary += f" {self.injected_summary}"
        return {
            "summary": summary,
            "supporting_claim_ids": [
                item["claim_id"]
                for role_outputs in specialist_outputs.values()
                for item in role_outputs
            ],
        }


class _RevisionScenarioCritic:
    """Explicit test critic for a repaired or unrepairable company issue."""

    def __init__(self, *, resolve_after_revision: bool) -> None:
        self.resolve_after_revision = resolve_after_revision
        self.calls = 0

    def evaluate(self, *, plan, claims, stage1_report, round_context):
        del stage1_report
        self.calls += 1
        claim_ids = tuple(claim.claim_id for claim in claims)
        req_id = plan.requirements[0].requirement_id
        resolved = (
            self.resolve_after_revision
            and round_context.round_number > 0
            and "Action: REVISE_CLAIM." in claims[0].claim_text
        )
        issue = CritiqueIssue(
            issue_id="test-injected-claim-review",
            issue_type=CritiqueIssueType.UNSUPPORTED_CLAIM,
            severity=CritiqueSeverity.MAJOR,
            affected_agent="company",
            affected_claim_ids=(claim_ids[0],),
            affected_requirement_ids=(req_id,),
            description="Test fixture requires the company specialist to recheck its claim.",
            required_action=CritiqueAction.REVISE_CLAIM,
            resolution_status=(CritiqueIssueStatus.RESOLVED if resolved else CritiqueIssueStatus.OPEN),
        )
        dimensions = []
        for dimension, applicability in expected_dimension_applicability(plan).items():
            dimensions.append(SemanticDimensionResult(
                dimension=dimension,
                applicability=applicability,
                score=0.9 if applicability is SemanticDimensionApplicability.APPLICABLE else None,
                rationale="Explicit revision test fixture result.",
                supporting_claim_ids=claim_ids if applicability is SemanticDimensionApplicability.APPLICABLE else (),
                issue_ids=(issue.issue_id,) if dimension is SemanticDimension.ANSWER_COVERAGE else (),
            ))
        return StructuredCriticResult(
            evaluator_version="test-only-revision-scenario-v1",
            dimension_scores=tuple(dimensions),
            critique_issues=(issue,),
            fulfilled_requirement_ids=tuple(item.requirement_id for item in plan.requirements),
        )


class _SynthesisOnlyCritic:
    """Targets the typed report summary without attaching it to a claim."""

    def __init__(self) -> None:
        self.contexts: list[dict] = []

    def evaluate(self, *, plan, claims, stage1_report, round_context):
        del stage1_report
        claim_ids = tuple(claim.claim_id for claim in claims)
        self.contexts.append({
            "summary": round_context.synthesis_summary,
            "supporting_claim_ids": tuple(round_context.synthesis_supporting_claim_ids),
            "first_claim_text": claims[0].claim_text,
        })
        issue_id = "synthesis-review"
        description = "Clarify how the specialist outputs fit together."
        resolved = round_context.round_number > 0 and description in (round_context.synthesis_summary or "")
        issue = CritiqueIssue(
            issue_id=issue_id,
            issue_type=CritiqueIssueType.INCOMPLETE_SYNTHESIS,
            severity=CritiqueSeverity.MAJOR,
            affected_agent="orchestrator",
            affected_claim_ids=(),
            affected_requirement_ids=tuple(item.requirement_id for item in plan.requirements),
            description=description,
            required_action=CritiqueAction.REVISE_CLAIM,
            resolution_status=CritiqueIssueStatus.RESOLVED if resolved else CritiqueIssueStatus.OPEN,
        )
        dimensions = []
        for dimension, applicability in expected_dimension_applicability(plan).items():
            dimensions.append(SemanticDimensionResult(
                dimension=dimension,
                applicability=applicability,
                score=0.9 if applicability is SemanticDimensionApplicability.APPLICABLE else None,
                rationale="Explicit synthesis test critic reviewed the typed summary separately from claim text.",
                supporting_claim_ids=claim_ids if applicability is SemanticDimensionApplicability.APPLICABLE else (),
                issue_ids=(issue_id,) if dimension is SemanticDimension.ANSWER_COVERAGE else (),
            ))
        return StructuredCriticResult(
            evaluator_version="test-only-synthesis-critic-v1",
            dimension_scores=tuple(dimensions),
            critique_issues=(issue,),
            fulfilled_requirement_ids=tuple(item.requirement_id for item in plan.requirements),
        )


def _gold_fixture(
    path: Path,
    *,
    include_evidence: bool = True,
    include_metric_locators: bool = True,
    source_tier: str = "primary",
) -> Path:
    create_gold_snapshot_schema(path)
    connection = sqlite3.connect(path)
    connection.execute(
        "INSERT INTO snapshot_metadata VALUES (?, ?, ?, ?)",
        ("gold-snapshot-api-fixture", "2026-09-24T00:00:00Z", "gold", "{}"),
    )
    sources = (
        ("source-roe", "filing", source_tier, "https://example.test/acb/report", "2026-09-24", "private/roe.pdf", "sha256-roe-real", "ACB", "fixture", "valid", None),
        ("source-npl", "filing", source_tier, "https://example.test/acb/report", "2026-09-24", "private/npl.pdf", "sha256-npl-real", "ACB", "fixture", "valid", None),
        ("source-input", "filing", source_tier, "https://example.test/acb/report", "2026-09-24", "private/input.pdf", "sha256-input-real", "ACB", "fixture", "valid", None),
    )
    connection.executemany(
        "INSERT INTO source_records VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        sources,
    )
    connection.executemany(
        "INSERT INTO metric_observations VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (
            ("obs-roe", "ACB", "bank", "bank.roe", 17.25, "percent", "2024_Q4", "2024-12-31", "point_in_time", "source-roe", "page:42;row:ROE" if include_metric_locators else None, "valid", None),
            ("obs-npl", "ACB", "bank", "bank.npl_g35", 1.03, "percent", "2024_Q4", "2024-12-31", "point_in_time", "source-npl", "page:61;row:NPL" if include_metric_locators else None, "valid", None),
            ("obs-input-npl-balance", "ACB", "bank", "bank.input.npl_g35_balance", 123.0, "billion_vnd", "2024_Q4", "2024-12-31", "point_in_time", "source-input", "page:62;row:NPL balance" if include_metric_locators else None, "valid", None),
        ),
    )
    if include_evidence:
        connection.executemany(
            "INSERT INTO evidence_snippets VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                ("evidence-roe", "source-roe", "ACB annual report", 42, "ROE", "2024_Q4", "ACB", "Reported return on equity.", 1.0, "text_layer", 1),
                ("evidence-npl", "source-npl", "ACB annual report", 61, "NPL", "2024_Q4", "ACB", "Reported non-performing loan ratio.", 1.0, "text_layer", 1),
                ("evidence-input", "source-input", "ACB annual report", 62, "NPL balance", "2024_Q4", "ACB", "Reported non-performing loan balance.", 1.0, "text_layer", 1),
            ),
        )
    connection.commit()
    connection.close()
    return path


def _gold_fanout_fixture(path: Path) -> Path:
    """Gold snippets share a source/period scope but carry no metric mapping."""

    create_gold_snapshot_schema(path)
    connection = sqlite3.connect(path)
    connection.execute(
        "INSERT INTO snapshot_metadata VALUES (?, ?, ?, ?)",
        ("gold-snapshot-api-fanout", "2026-09-24T00:00:00Z", "gold", "{}"),
    )
    connection.execute(
        "INSERT INTO source_records VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        ("source-acb-annual", "filing", "primary", "https://example.test/acb/report", "2026-09-24", "private/acb.pdf", "sha256-acb-annual", "ACB", "fixture", "valid", None),
    )
    connection.executemany(
        "INSERT INTO metric_observations VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (
            ("obs-roa", "ACB", "bank", "bank.roa", 1.2, "percent", "2024_Q4", "2024-12-31", "point_in_time", "source-acb-annual", "page:41;row:ROA", "valid", None),
            ("obs-roe", "ACB", "bank", "bank.roe", 17.25, "percent", "2024_Q4", "2024-12-31", "point_in_time", "source-acb-annual", "page:42;row:ROE", "valid", None),
            ("obs-npl", "ACB", "bank", "bank.npl_g35", 1.03, "percent", "2024_Q4", "2024-12-31", "point_in_time", "source-acb-annual", "page:61;row:NPL", "valid", None),
            ("obs-llr", "ACB", "bank", "bank.llr", 148.0, "percent", "2024_Q4", "2024-12-31", "point_in_time", "source-acb-annual", "page:62;row:LLR", "valid", None),
        ),
    )
    connection.executemany(
        "INSERT INTO evidence_snippets VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (
            ("evidence-roa", "source-acb-annual", "ACB annual report", 41, "ROA", "2024_Q4", "ACB", "Reported return on assets.", 1.0, "text_layer", 1),
            ("evidence-roe", "source-acb-annual", "ACB annual report", 42, "ROE", "2024_Q4", "ACB", "Reported return on equity.", 1.0, "text_layer", 1),
            ("evidence-npl", "source-acb-annual", "ACB annual report", 61, "NPL", "2024_Q4", "ACB", "Reported non-performing loan ratio.", 1.0, "text_layer", 1),
            ("evidence-llr", "source-acb-annual", "ACB annual report", 62, "LLR", "2024_Q4", "ACB", "Reported loan loss reserve coverage.", 1.0, "text_layer", 1),
        ),
    )
    connection.commit()
    connection.close()
    return path


class _LocatorTestProvider:
    """Decorate a Gold provider with the observation-locator contract under test."""

    def __init__(self, provider, *, expose_locator: bool) -> None:
        self._provider = provider
        self._db_path = provider._db_path
        self._expose_locator = expose_locator

    def __getattr__(self, name):
        return getattr(self._provider, name)

    def _observation(self, observation):
        if observation is None:
            return None
        values = observation.model_dump()
        metadata = dict(values.get("metadata") or {})
        locator = getattr(observation, "source_locator", None) or metadata.get("source_locator")
        if self._expose_locator and not locator:
            locator = {
                "bank.roe": "page:42;row:ROE",
                "bank.npl_g35": "page:61;row:NPL",
                "bank.input.npl_g35_balance": "page:62;row:NPL balance",
                "bank.roa": "page:41;row:ROA",
                "bank.llr": "page:62;row:LLR",
            }.get(observation.metric_id)
        values.pop("source_locator", None)
        metadata.pop("source_locator", None)
        values["metadata"] = metadata
        if self._expose_locator:
            values["source_locator"] = locator
        return SimpleNamespace(**values)

    def get_metric(self, *args, **kwargs):
        return self._observation(self._provider.get_metric(*args, **kwargs))

    def resolve_observation(self, *args, **kwargs):
        return self._observation(self._provider.resolve_observation(*args, **kwargs))


def _fixture_provider_binding(path: Path, *, expose_locator: bool) -> ProviderBinding:
    binding = _load_provider_unwrapped(path)
    provider = _LocatorTestProvider(binding.provider, expose_locator=expose_locator)
    return ProviderBinding(provider, binding.dataset_ref, binding.catalog, binding.provider_name)


class _FiveMemberPeerProvider:
    """Small provider double with one accepted missing peer cell and scoped values."""

    def __init__(self) -> None:
        self.dataset_ref = DatasetRef(dataset_id="peer-fixture", dataset_snapshot_id="peer-fixture-v1")
        peer_ids = ("ACB", "BID", "CTG", "MBB", "VCB")
        entity_ids = ("TCB", *peer_ids)
        self.catalog = DatasetCapabilityCatalog(
            dataset_ref=self.dataset_ref,
            entities=tuple(DatasetEntity(entity_id=item, entity_type=DatasetEntityType.COMPANY, display_name=item) for item in entity_ids),
            periods=(DatasetPeriod(period_id="2024_Q1", label="2024 Q1"),),
            metrics=(DatasetMetric(metric_id="bank.roe", display_name="bank.roe", analytical_level=AnalyticalLevel.COMPANY, default_unit="percent"),),
            peer_universes=(PeerUniverse(peer_universe_id="vn-banks-v1", display_name="Accepted five-member universe", entity_ids=peer_ids),),
            source_refs=tuple(f"source-{ticker}" for ticker in entity_ids if ticker != "ACB"),
            supported_operations=(
                SupportedOperation.GET_METRIC,
                SupportedOperation.GET_PEER_BENCHMARK,
                SupportedOperation.RESOLVE_OBSERVATION,
                SupportedOperation.GET_SOURCE,
                SupportedOperation.GET_EVIDENCE,
            ),
        )
        self.observations = {}
        values = {"TCB": 16.0, "BID": 10.0, "CTG": 12.0, "MBB": 14.0, "VCB": 18.0}
        for ticker in entity_ids:
            observation_id = f"obs-{ticker}-roe-q1"
            if ticker == "ACB":
                item = CanonicalObservation(
                    observation_id=observation_id,
                    dataset_id=self.dataset_ref.dataset_id,
                    dataset_snapshot_id=self.dataset_ref.dataset_snapshot_id,
                    entity_id=ticker,
                    period_id="2024_Q1",
                    metric_id="bank.roe",
                    validation_status=QualityStatus.MISSING,
                    missing_reason="DATA_UNAVAILABLE",
                    period_basis="point_in_time",
                    reporting_scope=None,
                )
            else:
                item = CanonicalObservation(
                    observation_id=observation_id,
                    dataset_id=self.dataset_ref.dataset_id,
                    dataset_snapshot_id=self.dataset_ref.dataset_snapshot_id,
                    entity_id=ticker,
                    period_id="2024_Q1",
                    metric_id="bank.roe",
                    value=values[ticker],
                    unit="percent",
                    period_basis="point_in_time",
                    source_ref=f"source-{ticker}",
                    source_locator=f"table:roe;row:{ticker}",
                    reporting_scope="consolidated",
                    validation_status=QualityStatus.VALID,
                )
            self.observations[(ticker, "2024_Q1", "bank.roe")] = item
        self.sources = {
            f"source-{ticker}": DatasetSource(
                source_ref=f"source-{ticker}",
                source_type="filing",
                source_tier=SourceTier.PRIMARY,
                source_url=f"https://example.test/{ticker}/filing",
                publisher="Accepted test source",
                retrieved_at="2026-09-25T00:00:00Z",
                content_hash=f"sha256-{ticker}",
                validation_status=QualityStatus.VALID,
            )
            for ticker in entity_ids if ticker != "ACB"
        }

    def get_capabilities(self, dataset_ref):
        return self.catalog

    def get_metric(self, dataset_ref, entity_id, period_id, metric_id):
        return self.observations.get((entity_id, period_id, metric_id))

    def get_entity_metrics(self, dataset_ref, entity_id, period_ids, metric_ids):
        return tuple(
            item for period_id in period_ids for metric_id in metric_ids
            if (item := self.get_metric(dataset_ref, entity_id, period_id, metric_id)) is not None
        )

    def get_peer_benchmark(self, dataset_ref, peer_universe_id, period_id, metric_ids, peer_entity_ids=None):
        from statistics import median
        from thesis_data.dataset_provider import peer_benchmark_observation_id

        universe = self.catalog.peer_universe(peer_universe_id)
        effective = universe.effective_entity_ids(peer_entity_ids)
        result = []
        for metric_id in metric_ids:
            members = [self.get_metric(dataset_ref, entity, period_id, metric_id) for entity in effective]
            valid = [item for item in members if item is not None and item.validation_status is QualityStatus.VALID]
            missing = [item for item in members if item is not None and item.validation_status is QualityStatus.MISSING]
            benchmark_id = peer_benchmark_observation_id(dataset_ref, peer_universe_id, period_id, metric_id, effective)
            eligible_ids = [item.entity_id for item in valid]
            member_records = [
                {
                    "entity_id": entity,
                    "observation_id": item.observation_id if item is not None else None,
                    "validation_status": item.validation_status.value if item is not None else None,
                    "accepted": item is not None and item.validation_status is QualityStatus.VALID and item.value is not None,
                    "reason": None if item is not None and item.validation_status is QualityStatus.VALID and item.value is not None else (
                        item.missing_reason if item is not None else "NO_OBSERVATION_FOUND"
                    ),
                    "reporting_scope": item.reporting_scope if item is not None else None,
                    "scope_authority": None,
                }
                for entity, item in zip(effective, members, strict=True)
            ]
            missing_members = [
                {"entity_id": item.entity_id, "observation_id": item.observation_id,
                 "validation_status": item.validation_status.value, "reason": item.missing_reason}
                for item in missing
            ]
            metadata = {
                "aggregation_method": "peer_median_v1",
                "aggregation_version": "peer_median_v1",
                "peer_universe_id": peer_universe_id,
                "requested_peer_entity_ids": list(effective),
                "eligible_peer_entity_ids": eligible_ids,
                "requested_denominator": len(effective),
                "eligible_denominator": len(valid),
                "missing_members": missing_members,
                "peer_member_observations": member_records,
            }
            if not valid:
                result.append(CanonicalObservation(
                    observation_id=benchmark_id, dataset_id=dataset_ref.dataset_id,
                    dataset_snapshot_id=dataset_ref.dataset_snapshot_id,
                    entity_id=peer_universe_id, period_id=period_id, metric_id=metric_id,
                    period_basis="point_in_time", reporting_scope="consolidated",
                    validation_status=QualityStatus.MISSING, missing_reason="DATA_UNAVAILABLE",
                    metadata=metadata,
                ))
            else:
                result.append(CanonicalObservation(
                    observation_id=benchmark_id, dataset_id=dataset_ref.dataset_id,
                    dataset_snapshot_id=dataset_ref.dataset_snapshot_id,
                    entity_id=peer_universe_id, period_id=period_id, metric_id=metric_id,
                    value=float(median(item.value for item in valid)), unit=valid[0].unit,
                    period_basis="point_in_time", reporting_scope="consolidated",
                    validation_status=QualityStatus.VALID,
                    derivation_method="peer_median_v1",
                    input_observation_ids=tuple(item.observation_id for item in valid),
                    metadata=metadata,
                ))
        return tuple(result)

    def get_source(self, dataset_ref, source_ref):
        return self.sources.get(source_ref)

    def get_evidence(self, dataset_ref, source_refs, entity_id=None, period_id=None, metric_id=None):
        return ()

    def resolve_evidence(self, dataset_ref, evidence_id):
        return None

    def resolve_observation(self, dataset_ref, observation_id):
        return next((item for item in self.observations.values() if item.observation_id == observation_id), None)


class _DifferentMetricEligibilityPeerProvider(_FiveMemberPeerProvider):
    """Two metrics with different accepted peer sets and denominators."""

    def __init__(self) -> None:
        super().__init__()
        npl_metric = DatasetMetric(
            metric_id="bank.npl_g35",
            display_name="NPL",
            analytical_level=AnalyticalLevel.COMPANY,
            default_unit="percent",
        )
        self.catalog = self.catalog.model_copy(update={"metrics": (*self.catalog.metrics, npl_metric)})
        values = {"TCB": 2.0, "BID": 2.5, "CTG": 2.3, "VCB": 1.7}
        for ticker in ("TCB", "ACB", "BID", "CTG", "MBB", "VCB"):
            if ticker in {"ACB", "MBB"}:
                observation = CanonicalObservation(
                    observation_id=f"obs-{ticker}-npl-q1",
                    dataset_id=self.dataset_ref.dataset_id,
                    dataset_snapshot_id=self.dataset_ref.dataset_snapshot_id,
                    entity_id=ticker,
                    period_id="2024_Q1",
                    metric_id="bank.npl_g35",
                    validation_status=QualityStatus.MISSING,
                    missing_reason="DATA_UNAVAILABLE",
                    period_basis="point_in_time",
                    reporting_scope=None,
                )
            else:
                observation = CanonicalObservation(
                    observation_id=f"obs-{ticker}-npl-q1",
                    dataset_id=self.dataset_ref.dataset_id,
                    dataset_snapshot_id=self.dataset_ref.dataset_snapshot_id,
                    entity_id=ticker,
                    period_id="2024_Q1",
                    metric_id="bank.npl_g35",
                    value=values[ticker],
                    unit="percent",
                    period_basis="point_in_time",
                    source_ref=f"source-{ticker}",
                    source_locator=f"table:npl;row:{ticker}",
                    reporting_scope="consolidated",
                    validation_status=QualityStatus.VALID,
                )
            self.observations[(ticker, "2024_Q1", "bank.npl_g35")] = observation


class _DeclaredMacroProvider:
    """Injected provider proving Macro runs only when its catalog declares it."""

    def __init__(self) -> None:
        self.dataset_ref = DatasetRef(dataset_id="macro-fixture", dataset_snapshot_id="macro-fixture-v1")
        self.observation = CanonicalObservation(
            observation_id="macro-policy-rate-q4",
            dataset_id=self.dataset_ref.dataset_id,
            dataset_snapshot_id=self.dataset_ref.dataset_snapshot_id,
            entity_id="VN",
            period_id="2024_Q4",
            metric_id="macro.policy_rate",
            value=4.5,
            unit="percent",
            period_basis="period_average",
            reporting_scope="national",
            source_ref="source-macro",
            source_locator="table:policy-rate;row:2024-Q4",
            validation_status=QualityStatus.VALID,
        )
        self.source = DatasetSource(
            source_ref="source-macro",
            source_type="central_bank_filing",
            source_tier=SourceTier.PRIMARY,
            source_url="https://example.test/sbv/policy-rate",
            publisher="Accepted macro test source",
            retrieved_at="2026-09-25T00:00:00Z",
            content_hash="sha256-macro",
            validation_status=QualityStatus.VALID,
        )
        self.catalog = DatasetCapabilityCatalog(
            dataset_ref=self.dataset_ref,
            entities=(DatasetEntity(entity_id="VN", entity_type=DatasetEntityType.MACRO, display_name="Vietnam"),),
            periods=(DatasetPeriod(period_id="2024_Q4", label="2024 Q4"),),
            metrics=(DatasetMetric(
                metric_id="macro.policy_rate",
                display_name="policy rate",
                analytical_level=AnalyticalLevel.MACRO,
                default_unit="percent",
            ),),
            source_refs=("source-macro",),
            supported_operations=(
                SupportedOperation.GET_MACRO_OBSERVATION,
                SupportedOperation.RESOLVE_OBSERVATION,
                SupportedOperation.GET_SOURCE,
            ),
        )

    def get_capabilities(self, _dataset_ref):
        return self.catalog

    def get_macro_observation(self, *_args, **_kwargs):
        return self.observation

    def resolve_observation(self, _dataset_ref, observation_id):
        return self.observation if observation_id == self.observation.observation_id else None

    def get_source(self, _dataset_ref, source_ref):
        return self.source if source_ref == self.source.source_ref else None

    def get_evidence(self, *_args, **_kwargs):
        return ()


class ApiAnalyzeIntegrationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.db_path = _gold_fixture(Path(self.directory.name) / "accepted-gold.sqlite")
        self.settings = Settings(
            app_name="final-thesis-api-test",
            app_env="test",
            sqlite_db_path=str(self.db_path),
        )
        self.test_critic = _ExplicitOfflineAcceptingCritic()
        self.critic_factory_patch = patch(
            "thesis_api.adaptive_runtime.build_openai_semantic_critic",
            return_value=self.test_critic,
        )
        self.critic_factory_patch.start()
        self.addCleanup(self.critic_factory_patch.stop)
        self.settings.openai_api_key = "test-key"
        self.settings.analysis_runs_db_path = str(Path(self.directory.name) / "analysis-runs.sqlite")
        self.writer = _ExplicitOfflineAnalysisWriter()
        self.client = TestClient(create_app(self.settings, analysis_writer=self.writer))
        self.addCleanup(self.client.close)

    def _runtime_app(self, database: Path, *, api_key: str | None = "test-key", writer=None):
        settings = Settings(
            app_env="test",
            sqlite_db_path=str(database),
            analysis_runs_db_path=str(database.with_name(database.stem + "-runs.sqlite")),
            openai_api_key=api_key,
        )
        return create_app(settings, analysis_writer=writer or _ExplicitOfflineAnalysisWriter())

    def test_company_claims_are_provider_backed_and_both_stages_accepted(self) -> None:
        with patch(
            "thesis_api.service._load_provider",
            side_effect=lambda path: _fixture_provider_binding(path, expose_locator=True),
        ):
            response = self.client.post(
                "/api/analyze",
                json={
                    "query": "Phân tích ROE và NPL của ACB quý 4 năm 2024",
                    "target_ticker": "ACB",
                    "period": "2024_Q4",
                },
            )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        report = AnalysisResponse.model_validate(data)

        self.assertEqual(report.status, "completed")
        self.assertEqual(report.analysis_plan.required_capabilities, ["company"])
        self.assertEqual(report.analysis_plan.dataset_snapshot_id, "gold-snapshot-api-fixture")
        self.assertIsNone(report.macro_context)
        self.assertIsNone(report.sector_benchmark)
        self.assertEqual(report.revision_summary.status, "passed")
        self.assertEqual(report.cross_level_critique, [])
        self.assertEqual({claim.stage1_status for claim in report.atomic_claims}, {"accepted"})
        self.assertTrue(all(claim.evidence_refs == [] for claim in report.atomic_claims))
        self.assertEqual({claim.stage2_critique_status for claim in report.atomic_claims}, {"sound"})
        self.assertTrue(all(claim.confidence is None for claim in report.atomic_claims))
        self.assertNotIn("confidence", data["atomic_claims"][0])
        self.assertEqual(data["atomic_claims"][0]["stage2_critique_status"], "sound")
        self.assertTrue(any("primary source locator and source hash" in item for item in report.limitations))
        self.assertTrue(any("does not infer consolidated or parent-only scope" in item for item in report.limitations))
        self.assertEqual({claim.metric for claim in report.atomic_claims}, {"bank.roe", "bank.npl_g35"})
        self.assertEqual(
            {claim.metric: claim.observation_id for claim in report.atomic_claims},
            {"bank.roe": "obs-roe", "bank.npl_g35": "obs-npl"},
        )
        self.assertTrue(all(claim.input_observation_ids == [] for claim in report.atomic_claims))
        self.assertTrue(all(claim.formula_version is None for claim in report.atomic_claims))
        self.assertEqual({item.value for item in report.evidence_trail}, {17.25, 1.03})
        self.assertTrue(all(item.evidence_id is None for item in report.evidence_trail))
        self.assertEqual({item.table_locator for item in report.evidence_trail}, {"page:42;row:ROE", "page:61;row:NPL"})
        self.assertEqual({item.provenance_hash for item in report.evidence_trail}, {"sha256-roe-real", "sha256-npl-real"})
        claims_by_id = {claim.claim_id: claim for claim in report.atomic_claims}
        self.assertTrue(all(item.claim_id in claims_by_id for item in report.evidence_trail))
        self.assertTrue(
            all(
                item.observation_id == claims_by_id[item.claim_id].observation_id
                for item in report.evidence_trail
            )
        )
        self.assertEqual({item.source_id for item in report.evidence_trail}, {"source-roe", "source-npl"})
        self.assertTrue(all(item.source_url == "https://example.test/acb/report" for item in report.evidence_trail))

    def test_stage1_rejects_numeric_zero_claim_for_accepted_missing_observation(self) -> None:
        provider = _FiveMemberPeerProvider()
        missing = provider.resolve_observation(provider.dataset_ref, "obs-ACB-roe-q1")
        self.assertIsNotNone(missing)
        self.assertEqual(missing.validation_status, QualityStatus.MISSING)
        self.assertEqual(missing.missing_reason, "DATA_UNAVAILABLE")

        request = AnalysisRequest(
            query="What is the ROE for ACB in 2024 Q1?",
            target_ticker="ACB",
            period="2024_Q1",
        )
        plan, _target, periods, _company_metrics, _peers, _macro_metrics = _plan_request(
            request, provider.dataset_ref, provider.catalog
        )
        workload_scope = ClaimScope(
            entities=plan.scope.entities,
            periods=periods,
            metric_ids=plan.scope.metric_ids,
        )
        zero_claim = AtomicClaim(
            claim_id="zero-for-missing-observation",
            claim_text="ACB ROE was zero in 2024 Q1.",
            claim_type="numeric",
            title="ACB ROE",
            interpretation="A numeric value was supplied for an explicitly missing observation.",
            limitation="Regression fixture.",
            scope=ClaimScope(
                entities=("ACB",), periods=("2024_Q1",), metric_ids=("bank.roe",)
            ),
            assertions=(StructuredAssertion(
                assertion_id="zero-assertion",
                assertion_type=AssertionType.METRIC_VALUE,
                entity="ACB",
                period="2024_Q1",
                metric_id="bank.roe",
                asserted_value=0.0,
                unit="percent",
                data_refs=(ClaimDataRef(
                    ref_id="obs-ACB-roe-q1",
                    ref_type="observation",
                    entity="ACB",
                    period="2024_Q1",
                    metric_id="bank.roe",
                ),),
            ),),
            evidence_refs=(),
            source_refs=(),
            inference_type=InferenceType.FACT,
            support="partially_supported",
        )
        evaluator = _RuntimeStage1Evaluator(
            resolver=ProviderStage1DatasetResolver(provider, provider.dataset_ref),
            workload_scope=workload_scope,
        )

        report = evaluator.evaluate(plan=plan, claims=(zero_claim,), policy=_API_POLICY)

        self.assertFalse(report.passed)
        reference_violations = report.gate_results["reference_validity"].violations
        self.assertTrue(any(
            "observation_reference_unaccepted:obs-ACB-roe-q1" in item
            for item in reference_violations
        ), reference_violations)
        numeric_violations = report.gate_results["numeric_accuracy"].violations
        self.assertTrue(any(
            "observation_reference_unaccepted:obs-ACB-roe-q1" in item
            for item in numeric_violations
        ), numeric_violations)

    def test_writer_rejects_unsupported_prose_and_accepts_grounded_limitation(self) -> None:
        attacks = (
            ("The ratio improved over an earlier quarter.", "analysis_writer_unsupported_trend"),
            ("The ratio is elevated because of market conditions.", "analysis_writer_unsupported_causality"),
            ("VCB reports the ratio at the same level.", "analysis_writer_entity_scope_invalid"),
            ("NPL should be compared with the accepted ratio.", "analysis_writer_metric_scope_invalid"),
            ("The ratio equals 999 percent.", "analysis_writer_unsupported_number"),
            ("The ratio is documented at page:42 in the filing.", "analysis_writer_provenance_reference_rejected"),
        )
        request = AnalysisRequest(
            query="What is the return on equity for ACB in 2024 Q4?",
            target_ticker="ACB",
            period="2024_Q4",
        )
        for text, expected_code in attacks:
            with self.subTest(text=text):
                critic = _ExplicitOfflineAcceptingCritic()
                writer = _ExplicitOfflineAnalysisWriter(injected_text=text)
                with patch(
                    "thesis_api.service._load_provider",
                    side_effect=lambda path: _fixture_provider_binding(path, expose_locator=True),
                ):
                    report = AnalysisEngine(
                        self.db_path,
                        self.settings,
                        semantic_critic=critic,
                        analysis_writer=writer,
                    )._analyze(request)
                self.assertEqual(report.status, "error")
                self.assertIn(expected_code, report.limitations[0])
                self.assertEqual(critic.calls, 0)

        writer = _ExplicitOfflineAnalysisWriter(
            injected_text="This observation remains within the accepted scope and its stated limitation."
        )
        with patch(
            "thesis_api.service._load_provider",
            side_effect=lambda path: _fixture_provider_binding(path, expose_locator=True),
        ):
            report = AnalysisEngine(
                self.db_path,
                self.settings,
                semantic_critic=_ExplicitOfflineAcceptingCritic(),
                analysis_writer=writer,
            )._analyze(request)
        self.assertEqual(report.status, "completed", report.limitations)
        self.assertIn("stated limitation", report.atomic_claims[0].statement)

    def test_writer_cannot_swap_a_number_between_claims(self) -> None:
        writer = _ExplicitOfflineAnalysisWriter(injected_text="The ratio is 1.03 percent.")
        critic = _ExplicitOfflineAcceptingCritic()
        with patch(
            "thesis_api.service._load_provider",
            side_effect=lambda path: _fixture_provider_binding(path, expose_locator=True),
        ):
            report = AnalysisEngine(
                self.db_path,
                self.settings,
                semantic_critic=critic,
                analysis_writer=writer,
            )._analyze(AnalysisRequest(
                query="Analyze ROE and NPL of ACB in 2024 Q4",
                target_ticker="ACB",
                period="2024_Q4",
            ))
        self.assertEqual(report.status, "error")
        self.assertIn("analysis_writer_unsupported_number", report.limitations[0])
        self.assertEqual(critic.calls, 0)

    def test_writer_rejects_number_words_in_missing_claims_and_synthesis(self) -> None:
        for phrase in (
            "seventeen percent",
            "mười bảy phần trăm",
            "half the typical figure",
            "twice as high",
            "double the typical figure",
        ):
            with self.subTest(phrase=phrase):
                provider = _FiveMemberPeerProvider()
                binding = ProviderBinding(provider, provider.dataset_ref, provider.catalog, "peer-fixture")
                writer = _ExplicitOfflineAnalysisWriter(missing_text=phrase)
                critic = _ExplicitOfflineAcceptingCritic()
                with patch("thesis_api.service._load_provider", return_value=binding):
                    report = AnalysisEngine(
                        self.db_path,
                        self.settings,
                        semantic_critic=critic,
                        analysis_writer=writer,
                    )._analyze(AnalysisRequest(
                        query="Compare ROE of TCB with the five bank peer universe in 2024 Q1",
                        target_ticker="TCB",
                        period="2024_Q1",
                        peer_tickers=["ACB", "BID", "CTG", "MBB", "VCB"],
                    ))
                self.assertEqual(report.status, "error")
                self.assertIn("analysis_writer_unsupported_number", report.limitations[0])
                self.assertEqual(critic.calls, 0)

        writer = _ExplicitOfflineAnalysisWriter(
            injected_summary="The report mentions seventeen percent as context."
        )
        critic = _ExplicitOfflineAcceptingCritic()
        with patch(
            "thesis_api.service._load_provider",
            side_effect=lambda path: _fixture_provider_binding(path, expose_locator=True),
        ):
            report = AnalysisEngine(
                self.db_path,
                self.settings,
                semantic_critic=critic,
                analysis_writer=writer,
            )._analyze(AnalysisRequest(
                query="What is the return on equity for ACB in 2024 Q4?",
                target_ticker="ACB",
                period="2024_Q4",
            ))
        self.assertEqual(report.status, "error")
        self.assertIn("analysis_synthesis_fact_reference_rejected", report.limitations[0])
        self.assertEqual(critic.calls, 0)

    def test_missing_semantic_provider_blocks_before_specialist_retrieval(self) -> None:
        client = TestClient(create_app(Settings(
            app_env="test",
            sqlite_db_path=str(self.db_path),
            analysis_runs_db_path=str(Path(self.directory.name) / "no-model-runs.sqlite"),
            openai_api_key=None,
        )))
        self.addCleanup(client.close)
        binding = _fixture_provider_binding(self.db_path, expose_locator=True)
        with patch("thesis_api.service._load_provider", return_value=binding), patch(
            "thesis_api.adaptive_runtime.build_openai_semantic_critic",
            side_effect=ValueError("semantic_provider_unconfigured"),
        ), patch.object(binding.provider, "get_metric", wraps=binding.provider.get_metric) as get_metric:
            report = AnalysisResponse.model_validate(client.post(
                "/api/analyze",
                json={
                    "query": "What is the return on equity for ACB in 2024 Q4?",
                    "target_ticker": "ACB",
                    "period": "2024_Q4",
                },
            ).json())

        self.assertEqual(report.status, "error")
        self.assertIn("semantic_provider_unconfigured", report.limitations[0])
        self.assertEqual(report.atomic_claims, [])
        get_metric.assert_not_called()

    def test_unsupported_entity_returns_no_numeric_claims(self) -> None:
        report = AnalysisResponse.model_validate(
            self.client.post(
                "/api/analyze",
                json={"query": "Analyze ROE of XYZ", "target_ticker": "XYZ", "period": "2024_Q4"},
            ).json()
        )
        self.assertEqual(report.status, "error")
        self.assertEqual(report.atomic_claims, [])
        self.assertEqual(report.evidence_trail, [])
        self.assertIn("unsupported_entity", report.limitations[0])

    def test_unsupported_year_metric_and_capability_requests_fail_closed(self) -> None:
        requests = (
            {"query": "ROE of ACB in 2024", "target_ticker": "ACB", "period": "2024"},
            {"query": "CIR of ACB in 2024 Q4", "target_ticker": "ACB", "period": "2024_Q4"},
            {"query": "Compare ROE of ACB and TCB in 2024 Q4", "target_ticker": "ACB", "period": "2024_Q4"},
            {"query": "SBV policy rate effect on ACB in 2024 Q4", "target_ticker": "ACB", "period": "2024_Q4"},
        )
        for payload in requests:
            with self.subTest(payload=payload):
                report = AnalysisResponse.model_validate(self.client.post("/api/analyze", json=payload).json())
                self.assertEqual(report.status, "error")
                self.assertEqual(report.atomic_claims, [])
                self.assertEqual(report.evidence_trail, [])

    def test_macro_writer_runs_only_for_a_provider_declared_macro_metric(self) -> None:
        provider = _DeclaredMacroProvider()
        binding = ProviderBinding(provider, provider.dataset_ref, provider.catalog, "macro-fixture")
        writer = _ExplicitOfflineAnalysisWriter()
        with patch("thesis_api.service._load_provider", return_value=binding):
            report = AnalysisEngine(
                self.db_path,
                self.settings,
                semantic_critic=_ExplicitOfflineAcceptingCritic(),
                analysis_writer=writer,
            )._analyze(AnalysisRequest(
                query="What is the SBV policy rate for Vietnam in 2024 Q4?",
                period="2024_Q4",
            ))
        self.assertEqual(report.status, "completed", report.limitations)
        self.assertEqual(report.analysis_plan.required_capabilities, ["macro"])
        self.assertEqual(len(report.atomic_claims), 1)
        self.assertEqual(writer.specialist_calls[0]["role"], "macro")
        self.assertEqual(report.atomic_claims[0].capability, "macro")

    def test_multiperiod_comparison_is_explicitly_rejected_before_retrieval(self) -> None:
        provider = _FiveMemberPeerProvider()
        binding = ProviderBinding(provider, provider.dataset_ref, provider.catalog, "peer-fixture")
        with patch("thesis_api.service._load_provider", return_value=binding), patch.object(provider, "get_metric", wraps=provider.get_metric) as get_metric:
            for query in (
                "Compare ROE of TCB from 2024_Q1 to 2024_Q4",
                "Across 2024_Q1–Q4, compare TCB ROE with the peer set",
                "Across 2024_Q1 to Q4, compare TCB ROE with the peer set",
                "Compare TCB ROE for 2024 Q1 through Q4",
                "Compare TCB ROE in 2024 Q1 to Q4",
            ):
                with self.subTest(query=query):
                    report = AnalysisResponse.model_validate(self.client.post(
                        "/api/analyze",
                        json={
                            "query": query,
                            "target_ticker": "TCB",
                            "period": "2024_Q1",
                            "peer_tickers": ["ACB", "BID", "CTG", "MBB", "VCB"],
                        },
                    ).json())
                    self.assertEqual(report.status, "error")
                    self.assertIn("multi_period_unsupported", report.limitations[0])
            get_metric.assert_not_called()

    def test_peer_run_uses_provider_median_and_preserves_missing_member_denominator(self) -> None:
        provider = _FiveMemberPeerProvider()
        binding = ProviderBinding(provider, provider.dataset_ref, provider.catalog, "peer-fixture")
        with patch("thesis_api.service._load_provider", return_value=binding), patch.object(
            provider,
            "get_peer_benchmark",
            wraps=provider.get_peer_benchmark,
        ) as get_benchmark:
            report = AnalysisResponse.model_validate(self.client.post(
                "/api/analyze",
                json={
                    "query": "Compare ROE of TCB with the five bank peer universe in 2024 Q1",
                    "target_ticker": "TCB",
                    "period": "2024_Q1",
                    "peer_tickers": ["ACB", "BID", "CTG", "MBB", "VCB"],
                },
            ).json())
        self.assertEqual(
            get_benchmark.call_args_list[0].kwargs["peer_entity_ids"],
            ("ACB", "BID", "CTG", "MBB", "VCB"),
        )
        self.assertEqual(report.status, "completed", report.limitations)
        self.assertEqual(report.analysis_plan.required_capabilities, ["sector", "company"])
        benchmark = report.sector_benchmark
        self.assertEqual(benchmark.peer_median_roe, 13.0)
        self.assertEqual(benchmark.peer_universe_id, "vn-banks-v1")
        self.assertEqual(benchmark.requested_denominator, 5)
        self.assertEqual(benchmark.eligible_denominator, 4)
        self.assertEqual(benchmark.requested_peer_entity_ids, ["ACB", "BID", "CTG", "MBB", "VCB"])
        self.assertEqual(benchmark.eligible_peer_entity_ids, ["BID", "CTG", "MBB", "VCB"])
        self.assertEqual(benchmark.missing_members[0]["entity_id"], "ACB")
        self.assertEqual(benchmark.missing_members[0]["observation_id"], "obs-ACB-roe-q1")
        self.assertEqual(benchmark.missing_members[0]["validation_status"], "missing")
        self.assertEqual(benchmark.missing_members[0]["reason"], "DATA_UNAVAILABLE")
        aggregate = next(item for item in report.atomic_claims if item.capability == "sector" and item.formula_version == "peer_median_v1")
        self.assertEqual(len(aggregate.input_observation_ids), 4)
        self.assertEqual(aggregate.formula_version, "peer_median_v1")
        self.assertEqual({item.ticker for item in report.evidence_trail if item.claim_id == aggregate.claim_id}, {"BID", "CTG", "MBB", "VCB"})

    def test_peer_metrics_keep_distinct_membership_records(self) -> None:
        provider = _DifferentMetricEligibilityPeerProvider()
        binding = ProviderBinding(provider, provider.dataset_ref, provider.catalog, "peer-fixture")
        with patch("thesis_api.service._load_provider", return_value=binding):
            report = AnalysisResponse.model_validate(self.client.post(
                "/api/analyze",
                json={
                    "query": "Compare ROE and NPL of TCB with the peer universe in 2024 Q1",
                    "target_ticker": "TCB",
                    "period": "2024_Q1",
                    "peer_tickers": ["ACB", "BID", "CTG", "MBB", "VCB"],
                },
            ).json())

        self.assertEqual(report.status, "completed", report.limitations)
        benchmark = report.sector_benchmark
        self.assertEqual(len(benchmark.benchmarks), 2)
        by_metric = {item.metric_id: item for item in benchmark.benchmarks}
        roe = by_metric["bank.roe"]
        npl = by_metric["bank.npl_g35"]
        self.assertEqual((roe.requested_denominator, roe.eligible_denominator), (5, 4))
        self.assertEqual((npl.requested_denominator, npl.eligible_denominator), (5, 3))
        self.assertEqual(roe.missing_members[0]["entity_id"], "ACB")
        self.assertEqual({item["entity_id"] for item in npl.missing_members}, {"ACB", "MBB"})
        self.assertEqual(len(roe.input_observation_ids), 4)
        self.assertEqual(len(npl.input_observation_ids), 3)
        self.assertFalse(hasattr(benchmark, "requested_peer_entity_ids"))
        self.assertFalse(hasattr(benchmark, "eligible_peer_entity_ids"))
        self.assertFalse(hasattr(benchmark, "requested_denominator"))
        self.assertFalse(hasattr(benchmark, "eligible_denominator"))
        self.assertFalse(hasattr(benchmark, "missing_members"))

    def test_peer_run_fails_closed_without_scope_or_period_basis(self) -> None:
        for field, code in (
            ("reporting_scope", "peer_reporting_scope_unavailable"),
            ("period_basis", "peer_period_basis_unavailable"),
        ):
            with self.subTest(field=field):
                provider = _FiveMemberPeerProvider()
                observation_key = ("TCB", "2024_Q1", "bank.roe")
                provider.observations[observation_key] = provider.observations[observation_key].model_copy(
                    update={field: None}
                )
                binding = ProviderBinding(provider, provider.dataset_ref, provider.catalog, "peer-fixture")
                with patch("thesis_api.service._load_provider", return_value=binding), patch.object(
                    provider,
                    "get_peer_benchmark",
                    wraps=provider.get_peer_benchmark,
                ) as get_benchmark:
                    report = AnalysisResponse.model_validate(self.client.post(
                        "/api/analyze",
                        json={
                            "query": "Compare ROE of TCB with the five bank peer universe in 2024 Q1",
                            "target_ticker": "TCB",
                            "period": "2024_Q1",
                            "peer_tickers": ["ACB", "BID", "CTG", "MBB", "VCB"],
                        },
                    ).json())
                self.assertEqual(report.status, "error")
                self.assertIn(code, report.limitations[0])
                get_benchmark.assert_not_called()

    def test_peer_run_rejects_legacy_aggregate_metadata_without_requested_eligible_sets(self) -> None:
        provider = _FiveMemberPeerProvider()
        original_get_peer_benchmark = provider.get_peer_benchmark

        def legacy_benchmark(*args, **kwargs):
            rows = original_get_peer_benchmark(*args, **kwargs)
            result = []
            for row in rows:
                metadata = dict(row.metadata)
                metadata.pop("requested_peer_entity_ids", None)
                metadata.pop("eligible_peer_entity_ids", None)
                metadata["peer_entity_ids"] = ["ACB", "BID", "CTG", "MBB", "VCB"]
                result.append(row.model_copy(update={"metadata": metadata}))
            return tuple(result)

        binding = ProviderBinding(provider, provider.dataset_ref, provider.catalog, "peer-fixture")
        with patch("thesis_api.service._load_provider", return_value=binding), patch.object(
            provider, "get_peer_benchmark", side_effect=legacy_benchmark
        ):
            report = AnalysisResponse.model_validate(self.client.post(
                "/api/analyze",
                json={
                    "query": "Compare ROE of TCB with the five bank peer universe in 2024 Q1",
                    "target_ticker": "TCB",
                    "period": "2024_Q1",
                    "peer_tickers": ["ACB", "BID", "CTG", "MBB", "VCB"],
                },
            ).json())

        self.assertEqual(report.status, "error")
        self.assertIn("peer_benchmark_scope_invalid", report.limitations[0])
        self.assertEqual(report.atomic_claims, [])

    def test_injected_claim_issue_triggers_targeted_revision_and_acceptance(self) -> None:
        critic = _RevisionScenarioCritic(resolve_after_revision=True)
        self.writer.initial_text = "Test-injected wording defect requiring a company recheck."
        stage1_candidates: list[tuple[str, ...]] = []
        original_evaluate = _RuntimeStage1Evaluator.evaluate

        def capture_stage1(evaluator, *, plan, claims, policy):
            stage1_candidates.append(tuple(claim.claim_text for claim in claims))
            return original_evaluate(evaluator, plan=plan, claims=claims, policy=policy)

        with patch(
            "thesis_api.adaptive_runtime.build_openai_semantic_critic",
            return_value=critic,
        ), patch(
            "thesis_api.service._load_provider",
            side_effect=lambda path: _fixture_provider_binding(path, expose_locator=True),
        ), patch("thesis_api.service._stage1_claim", wraps=_stage1_claim) as stage1_claim, patch(
            "thesis_api.adaptive_runtime._RuntimeStage1Evaluator.evaluate",
            autospec=True,
            side_effect=capture_stage1,
        ):
            report = AnalysisResponse.model_validate(self.client.post(
                "/api/analyze",
                json={
                    "query": "Analyze ROE and NPL of ACB in 2024 Q4",
                    "target_ticker": "ACB",
                    "period": "2024_Q4",
                },
            ).json())

        self.assertEqual(report.status, "completed", report.limitations)
        self.assertEqual(report.revision_summary.status, "revised_and_passed")
        self.assertEqual(report.revision_summary.rounds_executed, 2)
        self.assertEqual(report.revision_summary.revised_capabilities, ["company"])
        self.assertTrue(report.revision_summary.synthesis_revised)
        self.assertIn("test-injected-claim-review [unsupported_claim/MAJOR/RESOLVED/REVISE_CLAIM]", report.revision_summary.reason)
        revised_claim = next(item for item in report.atomic_claims if "Action: REVISE_CLAIM." in item.statement)
        untouched_claim = next(item for item in report.atomic_claims if item.claim_id != revised_claim.claim_id)
        self.assertEqual(revised_claim.stage2_critique_status, "revised")
        self.assertEqual(untouched_claim.stage2_critique_status, "sound")
        self.assertIn("Test-injected wording defect", untouched_claim.statement)
        self.assertTrue(any(call["issues"] for call in self.writer.specialist_calls))
        revision_call = next(call for call in self.writer.specialist_calls if call["issues"])
        self.assertEqual(revision_call["role"], "company")
        self.assertEqual(revision_call["claim_ids"], [revised_claim.claim_id])
        self.assertEqual(revision_call["issues"][0]["issue_id"], "test-injected-claim-review")
        self.assertEqual(revision_call["issues"][0]["description"], "Test fixture requires the company specialist to recheck its claim.")
        self.assertEqual(revision_call["issues"][0]["required_action"], "REVISE_CLAIM")
        self.assertEqual(critic.calls, 2)
        self.assertEqual(stage1_claim.call_count, 3)
        self.assertIn("Test fixture requires the company specialist", revised_claim.statement)
        self.assertNotIn("Test-injected wording defect", revised_claim.statement)
        self.assertEqual(len(stage1_candidates), 2)
        self.assertTrue(any("Test-injected wording defect" in item for item in stage1_candidates[0]))
        self.assertTrue(any("Action: REVISE_CLAIM." in item for item in stage1_candidates[1]))
        self.assertTrue(any("Test-injected wording defect" in item for item in stage1_candidates[1]))

    def test_unrepairable_critical_issue_fails_after_bounded_revisions(self) -> None:
        critic = _RevisionScenarioCritic(resolve_after_revision=False)
        with patch(
            "thesis_api.adaptive_runtime.build_openai_semantic_critic",
            return_value=critic,
        ), patch(
            "thesis_api.service._load_provider",
            side_effect=lambda path: _fixture_provider_binding(path, expose_locator=True),
        ), patch(
            "thesis_api.service._stage1_claim",
            wraps=_stage1_claim,
        ) as stage1_claim:
            report = AnalysisResponse.model_validate(self.client.post(
                "/api/analyze",
                json={
                    "query": "What is the return on equity for ACB in 2024 Q4?",
                    "target_ticker": "ACB",
                    "period": "2024_Q4",
                },
            ).json())

        self.assertEqual(report.status, "error")
        self.assertIn("fail_acceptance", report.limitations[0])
        self.assertEqual(report.atomic_claims, [])
        self.assertEqual(critic.calls, 2)
        self.assertEqual(stage1_claim.call_count, 3)

    def test_synthesis_only_issue_revises_typed_summary_without_claim_contamination(self) -> None:
        critic = _SynthesisOnlyCritic()
        request = AnalysisRequest(
            query="Analyze ROE and NPL of ACB in 2024 Q4",
            target_ticker="ACB",
            period="2024_Q4",
        )
        with patch(
            "thesis_api.service._load_provider",
            side_effect=lambda path: _fixture_provider_binding(path, expose_locator=True),
        ):
            report = AnalysisEngine(
                self.db_path,
                self.settings,
                semantic_critic=critic,
                analysis_writer=self.writer,
            )._analyze(request)

        self.assertEqual(report.status, "completed", report.limitations)
        self.assertEqual(report.revision_summary.status, "revised_and_passed")
        self.assertTrue(report.revision_summary.synthesis_revised)
        self.assertEqual(report.revision_summary.revised_capabilities, [])
        self.assertEqual({item.stage2_critique_status for item in report.atomic_claims}, {"sound"})
        self.assertIn("Clarify how the specialist outputs fit together.", report.synthesis_summary)
        self.assertEqual(report.synthesis_supporting_claim_ids, [item.claim_id for item in report.atomic_claims])
        self.assertEqual(len(critic.contexts), 2)
        for context in critic.contexts:
            self.assertEqual(context["supporting_claim_ids"], tuple(item.claim_id for item in report.atomic_claims))
            self.assertNotIn(context["summary"], context["first_claim_text"])
        synthesis_calls = [item for item in self.writer.synthesis_calls if item["issues"]]
        self.assertEqual(len(synthesis_calls), 1)
        self.assertEqual(synthesis_calls[0]["issues"][0]["affected_agent"], "orchestrator")

    def test_full_metric_names_are_resolved_without_falling_back_to_all_metrics(self) -> None:
        with patch(
            "thesis_api.service._load_provider",
            side_effect=lambda path: _fixture_provider_binding(path, expose_locator=True),
        ):
            report = AnalysisResponse.model_validate(
                self.client.post(
                    "/api/analyze",
                    json={
                        "query": "What is the return on equity for ACB in 2024 Q4?",
                        "target_ticker": "ACB",
                        "period": "2024_Q4",
                    },
                ).json()
            )
        self.assertEqual(report.status, "completed")
        self.assertEqual({claim.metric for claim in report.atomic_claims}, {"bank.roe"})

        unsupported = AnalysisResponse.model_validate(
            self.client.post(
                "/api/analyze",
                json={
                    "query": "What is the loan loss reserve coverage for ACB in 2024 Q4?",
                    "target_ticker": "ACB",
                    "period": "2024_Q4",
                },
            ).json()
        )
        self.assertEqual(unsupported.status, "error")
        self.assertEqual(unsupported.atomic_claims, [])
        self.assertIn("unsupported_metric", unsupported.limitations[0])

    def test_missing_document_evidence_uses_accepted_observation_locator(self) -> None:
        db_path = _gold_fixture(Path(self.directory.name) / "no-evidence.sqlite", include_evidence=False)
        client = TestClient(self._runtime_app(db_path))
        self.addCleanup(client.close)
        with patch(
            "thesis_api.service._load_provider",
            side_effect=lambda path: _fixture_provider_binding(path, expose_locator=True),
        ):
            report = AnalysisResponse.model_validate(
                client.post(
                    "/api/analyze",
                    json={"query": "ROE of ACB in 2024 Q4", "target_ticker": "ACB", "period": "2024_Q4"},
                ).json()
            )
            capabilities = client.get("/api/capabilities").json()
            ready = client.get("/api/ready")
        self.assertEqual(report.status, "completed")
        self.assertEqual(len(report.atomic_claims), 1)
        self.assertEqual(report.atomic_claims[0].evidence_refs, [])
        self.assertEqual(len(report.evidence_trail), 1)
        self.assertIsNone(report.evidence_trail[0].evidence_id)
        self.assertEqual(report.evidence_trail[0].table_locator, "page:42;row:ROE")
        self.assertTrue(any("primary source locator and source hash" in item for item in report.limitations))
        self.assertTrue(capabilities["analysis_available"])
        self.assertEqual(ready.status_code, 200)

    def test_capabilities_and_readiness_reflect_snapshot_catalog(self) -> None:
        with patch(
            "thesis_api.service._load_provider",
            side_effect=lambda path: _fixture_provider_binding(path, expose_locator=True),
        ):
            capabilities_response = self.client.get("/api/capabilities")
            ready_response = self.client.get("/api/ready")
        self.assertEqual(capabilities_response.status_code, 200)
        capabilities = capabilities_response.json()
        self.assertTrue(capabilities["analysis_available"])
        self.assertEqual(capabilities["implemented_capabilities"], ["company"])
        self.assertEqual(capabilities["snapshotId"], "gold-snapshot-api-fixture")
        self.assertEqual(capabilities["database_status"], "connected")
        self.assertIn("get_evidence", capabilities["supported_operations"])
        self.assertEqual([item["ticker"] for item in capabilities["entities"]], ["ACB"])
        self.assertEqual([item["id"] for item in capabilities["periods"]], ["2024_Q4"])
        self.assertEqual({item["id"] for item in capabilities["metrics"]}, {"bank.roe", "bank.npl_g35"})
        self.assertTrue(all("sector" not in item["label"].casefold() for item in capabilities["peerUniverses"]))
        self.assertTrue(all(item["executable"] is False for item in capabilities["peerUniverses"]))
        self.assertEqual(ready_response.json()["status"], "ready")

    def test_readiness_requires_model_configuration_and_writable_distinct_run_store(self) -> None:
        missing_model = Settings(
            app_env="test",
            sqlite_db_path=str(self.db_path),
            analysis_runs_db_path=str(Path(self.directory.name) / "model-missing-runs.sqlite"),
            openai_api_key=None,
        )
        with patch(
            "thesis_api.service._load_provider",
            side_effect=lambda path: _fixture_provider_binding(path, expose_locator=True),
        ):
            capabilities = AnalysisEngine(self.db_path, missing_model).get_capabilities()
        self.assertFalse(capabilities["analysis_available"])
        self.assertTrue(capabilities["analysis_runs_store_configured"])
        self.assertFalse(capabilities["specialist_writer_configured"])
        self.assertEqual(capabilities["limitation_code"], "semantic_provider_unconfigured")

        alias_paths = [self.db_path, self.db_path / "child" / "runs.sqlite"]
        hard_link = Path(self.directory.name) / "accepted-hard-link.sqlite"
        try:
            hard_link.hardlink_to(self.db_path)
            alias_paths.append(hard_link)
        except OSError:
            pass
        symbolic_link = Path(self.directory.name) / "accepted-symbolic-link.sqlite"
        try:
            symbolic_link.symlink_to(self.db_path)
            alias_paths.append(symbolic_link)
        except OSError:
            pass

        for runs_path in alias_paths:
            with self.subTest(runs_path=runs_path):
                settings = Settings(
                    app_env="test",
                    sqlite_db_path=str(self.db_path),
                    analysis_runs_db_path=str(runs_path),
                    openai_api_key="test-key",
                )
                with patch(
                    "thesis_api.service._load_provider",
                    side_effect=lambda path: _fixture_provider_binding(path, expose_locator=True),
                ):
                    capabilities = AnalysisEngine(self.db_path, settings).get_capabilities()
                self.assertFalse(capabilities["analysis_available"])
                self.assertFalse(capabilities["analysis_runs_store_configured"])
                self.assertEqual(capabilities["limitation_code"], "analysis_runs_store_invalid")

    def test_exact_metric_selection_keeps_lineage_inputs_non_runnable(self) -> None:
        binding = _fixture_provider_binding(self.db_path, expose_locator=True)
        selected = _requested_metrics(
            AnalysisRequest(
                query="Analyze bank.npl_g35 for ACB in 2024 Q4",
                target_ticker="ACB",
                period="2024_Q4",
            ),
            binding.catalog,
        )
        self.assertEqual(selected, ("bank.npl_g35",))

        with self.assertRaises(AnalysisBlocked) as blocked:
            _requested_metrics(
                AnalysisRequest(
                    query="Analyze bank.input.npl_g35_balance for ACB in 2024 Q4",
                    target_ticker="ACB",
                    period="2024_Q4",
                ),
                binding.catalog,
            )
        self.assertEqual(blocked.exception.code, "lineage_only_metric")
        capability_metric_ids = {item["id"] for item in _capabilities_payload(binding)["metrics"]}
        self.assertNotIn("bank.input.npl_g35_balance", capability_metric_ids)

    def test_direct_claim_omits_same_source_metric_snippet_without_reviewed_link(self) -> None:
        binding = _fixture_provider_binding(self.db_path, expose_locator=True)
        unrelated = DatasetEvidence(
            evidence_id="same-source-metric-scope-unlinked",
            source_ref="source-roe",
            entity_id="ACB",
            period_id="2024_Q4",
            metric_id="bank.roe",
            locator="page:42;row:neighboring-note",
            quote="A same-source snippet with no reviewed observation link.",
        )
        claim_only_link = SimpleNamespace(
            evidence_id="claim-only-link-is-insufficient",
            source_ref="source-roe",
            entity_id="ACB",
            period_id="2024_Q4",
            metric_id="bank.roe",
            claim_id="claim-obs-roe",
            locator="page:42;row:ROE",
            quote="A claim identifier without an observation join.",
        )
        explicitly_linked = SimpleNamespace(
            evidence_id="reviewed-observation-link",
            source_ref="source-roe",
            entity_id="ACB",
            period_id="2024_Q4",
            metric_id="bank.roe",
            observation_id="obs-roe",
            locator="page:42;row:ROE",
            quote="Provider-declared reviewed link to the exact observation.",
        )

        class Provider:
            def __getattr__(self, name):
                return getattr(binding.provider, name)

            def get_evidence(self, *_args, **_kwargs):
                return unrelated, claim_only_link, explicitly_linked

        claim, observation, _, _, evidence = _stage1_claim(
            provider=Provider(),
            dataset_ref=binding.dataset_ref,
            ticker="ACB",
            period="2024_Q4",
            metric_id="bank.roe",
            display_name="ROE",
        )

        self.assertEqual(observation.observation_id, "obs-roe")
        self.assertEqual(claim.source_refs, ("source-roe",))
        self.assertEqual([item.evidence_id for item in evidence], ["reviewed-observation-link"])
        self.assertEqual(claim.evidence_refs, ("reviewed-observation-link",))
        self.assertEqual(claim.support, "evidence_backed")

    def test_acb_generic_gold_snippets_are_not_fanned_out_across_metrics(self) -> None:
        db_path = _gold_fanout_fixture(Path(self.directory.name) / "gold-fanout.sqlite")
        client = TestClient(self._runtime_app(db_path))
        self.addCleanup(client.close)
        with patch(
            "thesis_api.service._load_provider",
            side_effect=lambda path: _fixture_provider_binding(path, expose_locator=True),
        ):
            report = AnalysisResponse.model_validate(
                client.post(
                    "/api/analyze",
                    json={
                        "query": "Analyze ROA, ROE, NPL, and loan loss reserve coverage for ACB in 2024 Q4",
                        "target_ticker": "ACB",
                        "period": "2024_Q4",
                    },
                ).json()
            )
        self.assertEqual(report.status, "completed")
        self.assertEqual(
            {claim.metric for claim in report.atomic_claims},
            {"bank.roa", "bank.roe", "bank.npl_g35", "bank.llr"},
        )
        self.assertTrue(all(claim.evidence_refs == [] for claim in report.atomic_claims))
        self.assertEqual(len(report.evidence_trail), 4)
        self.assertTrue(all(item.evidence_id is None for item in report.evidence_trail))
        claims_by_id = {claim.claim_id: claim for claim in report.atomic_claims}
        self.assertEqual(len(claims_by_id), 4)
        self.assertTrue(all(item.claim_id in claims_by_id for item in report.evidence_trail))
        self.assertTrue(
            all(
                item.observation_id == claims_by_id[item.claim_id].observation_id
                for item in report.evidence_trail
            )
        )
        self.assertEqual(
            {item.table_locator for item in report.evidence_trail},
            {
                "page:41;row:ROA",
                "page:42;row:ROE",
                "page:61;row:NPL",
                "page:62;row:LLR",
            },
        )
        self.assertEqual({item.provenance_hash for item in report.evidence_trail}, {"sha256-acb-annual"})

    def test_derived_claim_resolves_primary_input_lineage_without_direct_source_ref(self) -> None:
        dataset_ref = DatasetRef(dataset_id="fixture", dataset_snapshot_id="snapshot-1")
        input_observations = {
            "input-npl": CanonicalObservation(
                observation_id="input-npl",
                dataset_id=dataset_ref.dataset_id,
                dataset_snapshot_id=dataset_ref.dataset_snapshot_id,
                entity_id="CTG",
                period_id="2024_Q4",
                metric_id="bank.input.npl_g35_balance",
                value=120.0,
                unit="billion_vnd",
                source_ref="source-npl",
                validation_status=QualityStatus.VALID,
                source_locator="page:57;row:bad-debts",
                metadata={"source_locator": "page:57;row:bad-debts"},
            ),
            "input-loans": CanonicalObservation(
                observation_id="input-loans",
                dataset_id=dataset_ref.dataset_id,
                dataset_snapshot_id=dataset_ref.dataset_snapshot_id,
                entity_id="CTG",
                period_id="2024_Q4",
                metric_id="bank.input.total_loans",
                value=10000.0,
                unit="billion_vnd",
                source_ref="source-loans",
                validation_status=QualityStatus.VALID,
                source_locator="page:54;row:loans",
                metadata={"source_locator": "page:54;row:loans"},
            ),
        }
        derived = CanonicalObservation(
            observation_id="derived-npl",
            dataset_id=dataset_ref.dataset_id,
            dataset_snapshot_id=dataset_ref.dataset_snapshot_id,
            entity_id="CTG",
            period_id="2024_Q4",
            metric_id="bank.npl_g35",
            value=1.2,
            unit="percent",
            source_ref=None,
            validation_status=QualityStatus.VALID,
            derivation_method="npl_g35_ratio_v1",
            input_observation_ids=("input-npl", "input-loans"),
        )
        sources = {
            ref: DatasetSource(
                source_ref=ref,
                source_type="filing",
                source_tier=SourceTier.PRIMARY,
                source_url=f"https://example.test/ctg/{ref}.pdf",
                publisher="CTG",
                retrieved_at="2026-09-24T00:00:00Z",
                content_hash=f"sha256-{ref}",
                validation_status=QualityStatus.VALID,
            )
            for ref in ("source-npl", "source-loans")
        }
        generic_evidence = DatasetEvidence(
            evidence_id="gold-source-period-snippet",
            source_ref="source-npl",
            entity_id="CTG",
            period_id="2024_Q4",
            metric_id="bank.npl_g35",
            locator="page:57;row:unrelated-note",
            quote="Same-source metric-scope snippet without a reviewed observation link.",
        )

        class Provider:
            def get_metric(self, *_args, **_kwargs):
                return derived

            def resolve_observation(self, _dataset_ref, observation_id):
                if observation_id == derived.observation_id:
                    return derived
                return input_observations.get(observation_id)

            def get_source(self, _dataset_ref, source_ref):
                return sources.get(source_ref)

            def get_evidence(self, *_args, **_kwargs):
                return (generic_evidence,)

            def resolve_evidence(self, *_args, **_kwargs):
                return None

        claim, observation, primary_observations, claim_sources, evidence = _stage1_claim(
            provider=Provider(),
            dataset_ref=dataset_ref,
            ticker="CTG",
            period="2024_Q4",
            metric_id="bank.npl_g35",
            display_name="NPL",
        )
        self.assertEqual(observation.observation_id, "derived-npl")
        self.assertIsNone(observation.source_ref)
        self.assertEqual(observation.input_observation_ids, ("input-npl", "input-loans"))
        self.assertEqual(claim.assertions[0].formula_version, "npl_g35_ratio_v1")
        self.assertEqual(claim.assertions[0].data_refs[0].ref_id, "derived-npl")
        self.assertEqual(claim.assertions[0].data_refs[0].ref_type, "derived_metric")
        self.assertEqual(claim.source_refs, ("source-npl", "source-loans"))
        self.assertEqual({item.observation_id for item in primary_observations}, {"input-npl", "input-loans"})
        self.assertEqual(
            {
                item.observation_id: item.metadata["source_locator"]
                for item in primary_observations
            },
            {
                "input-npl": "page:57;row:bad-debts",
                "input-loans": "page:54;row:loans",
            },
        )
        self.assertEqual({item.source_ref for item in claim_sources}, {"source-npl", "source-loans"})
        self.assertEqual({item.content_hash for item in claim_sources}, {"sha256-source-npl", "sha256-source-loans"})
        self.assertEqual(evidence, ())
        self.assertEqual(claim.evidence_refs, ())
        self.assertEqual(claim.support, "source_locator_only")

        same_metric_unlinked_evidence = DatasetEvidence(
            evidence_id="same-source-metric-scope-unlinked",
            source_ref="source-npl",
            entity_id="CTG",
            period_id="2024_Q4",
            metric_id="bank.npl_g35",
            locator="page:57;row:unrelated-note",
            quote="A same-source snippet without a reviewed observation link.",
        )

        class SameScopeProvider(Provider):
            def get_evidence(self, *_args, **_kwargs):
                return generic_evidence, same_metric_unlinked_evidence

            def resolve_evidence(self, _dataset_ref, evidence_id):
                return (
                    same_metric_unlinked_evidence
                    if evidence_id == same_metric_unlinked_evidence.evidence_id
                    else None
                )

        catalog = DatasetCapabilityCatalog(
            dataset_ref=dataset_ref,
            entities=(
                DatasetEntity(
                    entity_id="CTG",
                    entity_type=DatasetEntityType.COMPANY,
                    display_name="CTG",
                ),
            ),
            periods=(DatasetPeriod(period_id="2024_Q4", label="2024 Q4"),),
            metrics=(
                DatasetMetric(
                    metric_id="bank.npl_g35",
                    display_name="NPL",
                    analytical_level=AnalyticalLevel.COMPANY,
                    default_unit="percent",
                ),
            ),
            source_refs=("source-npl", "source-loans"),
            supported_operations=(
                SupportedOperation.GET_METRIC,
                SupportedOperation.RESOLVE_OBSERVATION,
                SupportedOperation.GET_SOURCE,
                SupportedOperation.GET_EVIDENCE,
            ),
        )
        with patch(
            "thesis_api.service._load_provider",
            return_value=ProviderBinding(SameScopeProvider(), dataset_ref, catalog, "fixture"),
        ):
            report = AnalysisEngine(
                self.db_path, self.settings,
                semantic_critic=self.test_critic,
                analysis_writer=self.writer,
            )._analyze(
                AnalysisRequest(
                    query="Analyze NPL of CTG in 2024 Q4",
                    target_ticker="CTG",
                    period="2024_Q4",
                )
            )
        self.assertEqual(report.status, "completed")
        output_claim = report.atomic_claims[0]
        self.assertEqual(output_claim.observation_id, "derived-npl")
        self.assertEqual(output_claim.input_observation_ids, ["input-npl", "input-loans"])
        self.assertEqual(output_claim.formula_version, "npl_g35_ratio_v1")
        self.assertEqual(output_claim.evidence_refs, [])
        self.assertTrue(
            all(item.claim_id == output_claim.claim_id for item in report.evidence_trail)
        )
        input_trails = {
            item.observation_id: item
            for item in report.evidence_trail
            if item.evidence_id is None
        }
        self.assertEqual(set(input_trails), {"input-npl", "input-loans"})
        self.assertEqual(input_trails["input-npl"].source_id, "source-npl")
        self.assertEqual(input_trails["input-npl"].source_url, sources["source-npl"].source_url)
        self.assertEqual(input_trails["input-npl"].table_locator, "page:57;row:bad-debts")
        self.assertEqual(input_trails["input-npl"].provenance_hash, "sha256-source-npl")
        self.assertEqual(input_trails["input-loans"].source_id, "source-loans")
        self.assertEqual(input_trails["input-loans"].table_locator, "page:54;row:loans")
        self.assertEqual(input_trails["input-loans"].provenance_hash, "sha256-source-loans")
        self.assertTrue(all(item.evidence_id is None for item in report.evidence_trail))

    def test_missing_metric_locator_fails_closed_even_when_source_snippets_exist(self) -> None:
        with patch(
            "thesis_api.service._load_provider",
            side_effect=lambda path: _fixture_provider_binding(path, expose_locator=False),
        ):
            response = self.client.post(
                "/api/analyze",
                json={"query": "ROE of ACB in 2024 Q4", "target_ticker": "ACB", "period": "2024_Q4"},
            )
            capabilities = self.client.get("/api/capabilities").json()
            ready = self.client.get("/api/ready")
        report = AnalysisResponse.model_validate(response.json())
        self.assertEqual(report.status, "error")
        self.assertEqual(report.atomic_claims, [])
        self.assertIn("observation_locator_missing", report.limitations[0])
        self.assertFalse(capabilities["analysis_available"])
        self.assertEqual(ready.status_code, 503)

    def test_missing_database_is_not_created_or_reported_ready(self) -> None:
        missing = Path(self.directory.name) / "does-not-exist.sqlite"
        settings = Settings(
            app_env="test",
            sqlite_db_path=str(missing),
            analysis_runs_db_path=str(Path(self.directory.name) / "missing-database-runs.sqlite"),
            openai_api_key="test-key",
        )
        client = TestClient(create_app(settings, analysis_writer=_ExplicitOfflineAnalysisWriter()))
        result = client.post(
            "/api/analyze",
            json={"query": "ROE of ACB in 2024 Q4", "target_ticker": "ACB", "period": "2024_Q4"},
        )
        self.assertEqual(result.json()["status"], "error")
        self.assertFalse(missing.exists())
        self.assertEqual(client.get("/api/capabilities").json()["analysis_available"], False)
        self.assertEqual(client.get("/api/ready").status_code, 503)
        client.close()


if __name__ == "__main__":
    unittest.main()
