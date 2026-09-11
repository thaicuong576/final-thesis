"""Versioned pre-generation analysis-plan contracts.

An ``AnalysisPlan`` is created from the question before any worker is asked to
write an answer.  It is deliberately small and thesis-specific: it describes
the required analytical units and applicable cross-level relationships without
becoming a general workflow language.
"""

from __future__ import annotations

from enum import StrEnum
from typing import Iterable

from pydantic import BaseModel, ConfigDict, Field, model_validator


ANALYSIS_PLAN_VERSION = "analysis-plan-v1"
FROZEN_TCB_MACRO_QUERY_ID = "TCB_macro_to_bank_q4"
FROZEN_TCB_MACRO_PERIOD = "2024_Q4"


class AnalysisAgent(StrEnum):
    """Agents that may be required by a planned analytical requirement."""

    MACRO = "macro"
    SECTOR = "sector"
    COMPANY = "company"
    ORCHESTRATOR = "orchestrator"


class RequirementType(StrEnum):
    FACTUAL_OBSERVATION = "factual_observation"
    COMPARISON = "comparison"
    TREND = "trend"
    CROSS_LEVEL_RELATION = "cross_level_relation"
    LIMITATION_MISSINGNESS_DISCLOSURE = "limitation_missingness_disclosure"


class FulfillmentPolicy(StrEnum):
    """The two allowed value/missingness fulfillment policies."""

    VALID_VALUE_REQUIRED = "VALID_VALUE_REQUIRED"
    VALUE_OR_ACCEPTED_MISSINGNESS = "VALUE_OR_ACCEPTED_MISSINGNESS"


class MissingDataPolicy(StrEnum):
    REJECT_MISSING = "reject_missing"
    ACCEPTED_GOLD_MISSINGNESS = "accepted_gold_missingness"
    NOT_APPLICABLE = "not_applicable"


class InferenceCeiling(StrEnum):
    OBSERVATION_ONLY = "observation_only"
    COMPARISON_ALLOWED = "comparison_allowed"
    TREND_ALLOWED = "trend_allowed"
    ASSOCIATION_ONLY = "association_only"
    LIMITATION_ONLY = "limitation_only"
    CAUSAL = "causal"


class CausalClaimPolicy(StrEnum):
    NO_CAUSAL_INFERENCE = "no_causal_inference"
    ASSOCIATION_ONLY = "association_only"
    CAUSAL_ALLOWED = "causal_allowed"


class LinkLevel(StrEnum):
    MACRO = "macro"
    SECTOR = "sector"
    COMPANY = "company"
    PEER_BENCHMARK = "peer_benchmark"


class ApplicableLinkType(StrEnum):
    MACRO_TO_COMPANY = "macro_to_company"
    SECTOR_TO_COMPANY = "sector_to_company"
    COMPANY_TO_PEER_BENCHMARK = "company_to_peer_benchmark"


def _unique_non_empty(values: Iterable[str], field_name: str) -> None:
    values = tuple(values)
    if any(not isinstance(value, str) or not value.strip() for value in values):
        raise ValueError(f"{field_name} must contain non-empty strings")
    if len(values) != len(set(values)):
        raise ValueError(f"{field_name} must be unique")


class AnalysisScope(BaseModel):
    """Question scope shared by company, sector, macro, and linked claims."""

    model_config = ConfigDict(extra="forbid")

    entities: tuple[str, ...] = Field(min_length=1)
    periods: tuple[str, ...] = Field(min_length=1)
    company_metric_ids: tuple[str, ...] = Field(default_factory=tuple)
    macro_indicator_ids: tuple[str, ...] = Field(default_factory=tuple)
    comparison_universe: tuple[str, ...] = Field(default_factory=tuple)

    @model_validator(mode="after")
    def validate_scope(self) -> "AnalysisScope":
        for field_name in (
            "entities",
            "periods",
            "company_metric_ids",
            "macro_indicator_ids",
            "comparison_universe",
        ):
            _unique_non_empty(getattr(self, field_name), field_name)
        if not self.company_metric_ids and not self.macro_indicator_ids:
            raise ValueError("analysis scope must contain a company or macro metric")
        if set(self.comparison_universe) - set(self.entities):
            raise ValueError("comparison_universe must be within scope entities")
        return self

    @property
    def metric_ids(self) -> tuple[str, ...]:
        """Return the stable combined metric namespace for requirement checks."""

        return self.company_metric_ids + self.macro_indicator_ids


class AnalysisRequirement(BaseModel):
    """One stable unit that the later answer must fulfill."""

    model_config = ConfigDict(extra="forbid")

    requirement_id: str = Field(min_length=1)
    requirement_type: RequirementType
    description: str = Field(min_length=1)
    required_agents: tuple[AnalysisAgent, ...] = Field(min_length=1)
    entities: tuple[str, ...] = Field(min_length=1)
    periods: tuple[str, ...] = Field(min_length=1)
    metric_ids: tuple[str, ...] = Field(min_length=1)
    inference_ceiling: InferenceCeiling
    fulfillment_policy: FulfillmentPolicy
    missing_data_policy: MissingDataPolicy
    critical: bool = True

    @model_validator(mode="after")
    def validate_requirement(self) -> "AnalysisRequirement":
        _unique_non_empty(self.required_agents, "required_agents")
        _unique_non_empty(self.entities, "requirement entities")
        _unique_non_empty(self.periods, "requirement periods")
        _unique_non_empty(self.metric_ids, "requirement metric_ids")
        if (
            self.fulfillment_policy is FulfillmentPolicy.VALUE_OR_ACCEPTED_MISSINGNESS
            and self.missing_data_policy is not MissingDataPolicy.ACCEPTED_GOLD_MISSINGNESS
        ):
            raise ValueError(
                "VALUE_OR_ACCEPTED_MISSINGNESS requires accepted_gold_missingness"
            )
        if (
            self.fulfillment_policy is FulfillmentPolicy.VALID_VALUE_REQUIRED
            and self.missing_data_policy is MissingDataPolicy.ACCEPTED_GOLD_MISSINGNESS
        ):
            raise ValueError(
                "VALID_VALUE_REQUIRED cannot allow accepted_gold_missingness"
            )
        return self


class ApplicableLink(BaseModel):
    """A cross-level relationship that is explicitly in scope for a question."""

    model_config = ConfigDict(extra="forbid")

    link_id: str = Field(min_length=1)
    link_type: ApplicableLinkType
    source_level: LinkLevel
    target_level: LinkLevel
    source_entities: tuple[str, ...] = Field(min_length=1)
    target_entities: tuple[str, ...] = Field(min_length=1)
    source_periods: tuple[str, ...] = Field(min_length=1)
    target_periods: tuple[str, ...] = Field(min_length=1)
    metric_ids: tuple[str, ...] = Field(min_length=1)
    description: str = Field(min_length=1)

    @model_validator(mode="after")
    def validate_link_shape(self) -> "ApplicableLink":
        _unique_non_empty(self.source_entities, "source_entities")
        _unique_non_empty(self.target_entities, "target_entities")
        _unique_non_empty(self.source_periods, "source_periods")
        _unique_non_empty(self.target_periods, "target_periods")
        _unique_non_empty(self.metric_ids, "link metric_ids")
        expected_levels = {
            ApplicableLinkType.MACRO_TO_COMPANY: (LinkLevel.MACRO, LinkLevel.COMPANY),
            ApplicableLinkType.SECTOR_TO_COMPANY: (LinkLevel.SECTOR, LinkLevel.COMPANY),
            ApplicableLinkType.COMPANY_TO_PEER_BENCHMARK: (
                LinkLevel.COMPANY,
                LinkLevel.PEER_BENCHMARK,
            ),
        }[self.link_type]
        if (self.source_level, self.target_level) != expected_levels:
            raise ValueError("link_type does not match source/target levels")
        return self


class AnalysisPlan(BaseModel):
    """Frozen question contract created before worker generation."""

    model_config = ConfigDict(extra="forbid")

    plan_version: str = Field(min_length=1)
    query_id: str = Field(min_length=1)
    normalized_question: str = Field(min_length=1)
    scope: AnalysisScope
    requirements: tuple[AnalysisRequirement, ...] = Field(min_length=1)
    applicable_links: tuple[ApplicableLink, ...] = Field(default_factory=tuple)
    requested_outputs: tuple[str, ...] = Field(min_length=1)
    causal_claim_policy: CausalClaimPolicy

    @model_validator(mode="after")
    def validate_plan(self) -> "AnalysisPlan":
        if self.plan_version != ANALYSIS_PLAN_VERSION:
            raise ValueError("unsupported analysis plan version")
        requirement_ids = [item.requirement_id for item in self.requirements]
        if len(requirement_ids) != len(set(requirement_ids)):
            raise ValueError("duplicate requirement IDs")
        link_ids = [item.link_id for item in self.applicable_links]
        if len(link_ids) != len(set(link_ids)):
            raise ValueError("duplicate applicable link IDs")
        _unique_non_empty(self.requested_outputs, "requested_outputs")

        allowed_entities = set(self.scope.entities)
        allowed_metrics = set(self.scope.metric_ids)
        allowed_periods = set(self.scope.periods)
        for requirement in self.requirements:
            if not set(requirement.entities).issubset(allowed_entities):
                raise ValueError(f"requirement entities outside scope: {requirement.requirement_id}")
            if not set(requirement.periods).issubset(allowed_periods):
                raise ValueError(f"requirement periods outside scope: {requirement.requirement_id}")
            if not set(requirement.metric_ids).issubset(allowed_metrics):
                raise ValueError(f"requirement metrics outside scope: {requirement.requirement_id}")
        for link in self.applicable_links:
            if not set(link.source_entities).issubset(allowed_entities):
                raise ValueError(f"link source entities outside scope: {link.link_id}")
            if not set(link.target_entities).issubset(allowed_entities):
                raise ValueError(f"link target entities outside scope: {link.link_id}")
            if not set(link.source_periods).issubset(allowed_periods):
                raise ValueError(f"link source periods outside scope: {link.link_id}")
            if not set(link.target_periods).issubset(allowed_periods):
                raise ValueError(f"link target periods outside scope: {link.link_id}")
            if not set(link.metric_ids).issubset(allowed_metrics):
                raise ValueError(f"link metrics outside scope: {link.link_id}")

        if self.causal_claim_policy in {
            CausalClaimPolicy.NO_CAUSAL_INFERENCE,
            CausalClaimPolicy.ASSOCIATION_ONLY,
        } and any(
            requirement.inference_ceiling is InferenceCeiling.CAUSAL
            for requirement in self.requirements
        ):
            raise ValueError("causal inference ceiling conflicts with plan causal policy")
        return self


def build_tcb_macro_analysis_plan() -> AnalysisPlan:
    """Build the deterministic plan for the pre-registered macro question."""

    period = FROZEN_TCB_MACRO_PERIOD
    macro_metrics = ("macro.policy_rate", "macro.credit_growth")
    bank_metrics = ("bank.roa", "bank.roe")
    all_metrics = macro_metrics + bank_metrics
    return AnalysisPlan(
        plan_version=ANALYSIS_PLAN_VERSION,
        query_id=FROZEN_TCB_MACRO_QUERY_ID,
        normalized_question=(
            "Relate the accepted 2024_Q4 macro context (policy rate and system "
            "credit growth) to TCB's ROA and ROE; separate observed facts from "
            "association and disclose unavailable observations."
        ),
        scope=AnalysisScope(
            entities=("VN", "TCB"),
            periods=(period,),
            company_metric_ids=bank_metrics,
            macro_indicator_ids=macro_metrics,
        ),
        requirements=(
            AnalysisRequirement(
                requirement_id="R1",
                requirement_type=RequirementType.FACTUAL_OBSERVATION,
                description="Report the 2024_Q4 SBV policy-rate observation.",
                required_agents=(AnalysisAgent.MACRO,),
                entities=("VN",),
                periods=(period,),
                metric_ids=("macro.policy_rate",),
                inference_ceiling=InferenceCeiling.OBSERVATION_ONLY,
                fulfillment_policy=FulfillmentPolicy.VALID_VALUE_REQUIRED,
                missing_data_policy=MissingDataPolicy.REJECT_MISSING,
            ),
            AnalysisRequirement(
                requirement_id="R2",
                requirement_type=RequirementType.FACTUAL_OBSERVATION,
                description=(
                    "Report system credit growth, or explicitly disclose the "
                    "accepted Gold missingness state."
                ),
                required_agents=(AnalysisAgent.MACRO,),
                entities=("VN",),
                periods=(period,),
                metric_ids=("macro.credit_growth",),
                inference_ceiling=InferenceCeiling.OBSERVATION_ONLY,
                fulfillment_policy=FulfillmentPolicy.VALUE_OR_ACCEPTED_MISSINGNESS,
                missing_data_policy=MissingDataPolicy.ACCEPTED_GOLD_MISSINGNESS,
            ),
            AnalysisRequirement(
                requirement_id="R3",
                requirement_type=RequirementType.FACTUAL_OBSERVATION,
                description="Report TCB ROA for 2024_Q4.",
                required_agents=(AnalysisAgent.COMPANY,),
                entities=("TCB",),
                periods=(period,),
                metric_ids=("bank.roa",),
                inference_ceiling=InferenceCeiling.OBSERVATION_ONLY,
                fulfillment_policy=FulfillmentPolicy.VALID_VALUE_REQUIRED,
                missing_data_policy=MissingDataPolicy.REJECT_MISSING,
            ),
            AnalysisRequirement(
                requirement_id="R4",
                requirement_type=RequirementType.FACTUAL_OBSERVATION,
                description="Report TCB ROE for 2024_Q4.",
                required_agents=(AnalysisAgent.COMPANY,),
                entities=("TCB",),
                periods=(period,),
                metric_ids=("bank.roe",),
                inference_ceiling=InferenceCeiling.OBSERVATION_ONLY,
                fulfillment_policy=FulfillmentPolicy.VALID_VALUE_REQUIRED,
                missing_data_policy=MissingDataPolicy.REJECT_MISSING,
            ),
            AnalysisRequirement(
                requirement_id="R5",
                requirement_type=RequirementType.CROSS_LEVEL_RELATION,
                description=(
                    "Relate available macro context to TCB performance using "
                    "association only."
                ),
                required_agents=(
                    AnalysisAgent.MACRO,
                    AnalysisAgent.COMPANY,
                    AnalysisAgent.ORCHESTRATOR,
                ),
                entities=("VN", "TCB"),
                periods=(period,),
                metric_ids=all_metrics,
                inference_ceiling=InferenceCeiling.ASSOCIATION_ONLY,
                fulfillment_policy=FulfillmentPolicy.VALUE_OR_ACCEPTED_MISSINGNESS,
                missing_data_policy=MissingDataPolicy.ACCEPTED_GOLD_MISSINGNESS,
            ),
            AnalysisRequirement(
                requirement_id="R6",
                requirement_type=RequirementType.LIMITATION_MISSINGNESS_DISCLOSURE,
                description="Do not claim that one period establishes causality.",
                required_agents=(AnalysisAgent.ORCHESTRATOR,),
                entities=("VN", "TCB"),
                periods=(period,),
                metric_ids=all_metrics,
                inference_ceiling=InferenceCeiling.LIMITATION_ONLY,
                fulfillment_policy=FulfillmentPolicy.VALID_VALUE_REQUIRED,
                missing_data_policy=MissingDataPolicy.NOT_APPLICABLE,
            ),
            AnalysisRequirement(
                requirement_id="R7",
                requirement_type=RequirementType.LIMITATION_MISSINGNESS_DISCLOSURE,
                description="Disclose unavailable macro observations and limitations.",
                required_agents=(AnalysisAgent.ORCHESTRATOR,),
                entities=("VN", "TCB"),
                periods=(period,),
                metric_ids=all_metrics,
                inference_ceiling=InferenceCeiling.LIMITATION_ONLY,
                fulfillment_policy=FulfillmentPolicy.VALUE_OR_ACCEPTED_MISSINGNESS,
                missing_data_policy=MissingDataPolicy.ACCEPTED_GOLD_MISSINGNESS,
            ),
        ),
        applicable_links=(
            ApplicableLink(
                link_id="L1",
                link_type=ApplicableLinkType.MACRO_TO_COMPANY,
                source_level=LinkLevel.MACRO,
                target_level=LinkLevel.COMPANY,
                source_entities=("VN",),
                target_entities=("TCB",),
                source_periods=(period,),
                target_periods=(period,),
                metric_ids=all_metrics,
                description="Macro context may be related to TCB performance.",
            ),
        ),
        requested_outputs=(
            "structured_facts",
            "cross_level_relation",
            "limitations",
            "evidence_trace",
        ),
        causal_claim_policy=CausalClaimPolicy.ASSOCIATION_ONLY,
    )
