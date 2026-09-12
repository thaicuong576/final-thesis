"""OpenAI Responses API adapter for the provider-neutral semantic critic.

This module is an application/provider boundary.  It renders the frozen
analysis context as deterministic JSON, asks an injected Responses-compatible
client for one strict structured result, and returns the existing
``StructuredCriticResult`` contract.  It has no data-provider, storage, or
tool-calling access.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
import json
from typing import Any, Protocol

from pydantic import ValidationError

from .analysis_plan import AnalysisAgent, AnalysisPlan
from .provider_config import ProviderExecutionConfig
from .schema import AtomicClaim, CritiqueIssueStatus, Stage1ValidationReport
from .semantic_critic import (
    SemanticCritic,
    SemanticEvaluationError,
    SemanticRoundContext,
)
from .semantic_evaluation import (
    SEMANTIC_EVALUATION_VERSION,
    STRUCTURED_CRITIC_RESULT_VERSION,
    StructuredCriticResult,
    expected_dimension_applicability,
)


OPENAI_SEMANTIC_CRITIC_ADAPTER_VERSION = "openai-semantic-critic-v1"


class ResponsesCreate(Protocol):
    """Small injected surface used from an OpenAI-compatible Responses client."""

    def create(self, **kwargs: Any) -> Any:
        ...


class ResponsesClient(Protocol):
    responses: ResponsesCreate


class OpenAISemanticCriticError(SemanticEvaluationError):
    """Fail-closed provider/transport error with a stable public code."""

    def __init__(self, code: str) -> None:
        self.code = code
        super().__init__(code)


_CRITIC_INSTRUCTIONS = """You are a semantic reviewer of one supplied analytical candidate.
Evaluate only the public, auditable context in the JSON input.

Return exactly one JSON object matching the supplied strict schema.  Do not
make an acceptance decision, choose a revision budget, activate an inactive
agent, invent undeclared links, override Stage-1, or decide accepted
missingness.  Use only the listed identifiers.  Every declared requirement
must be classified exactly once, and every declared applicable link must have
exactly one result.

For every prior OPEN issue in prior_open_issues, return the same issue_id
exactly once with status OPEN, RESOLVED, EXPLAINED, or UNRESOLVED.  Do not
silently rename it.  New issues must use unique concise IDs.

Return concise observable rationales, such as the claim IDs or requirement
that support a score.  Do not provide private chain-of-thought, hidden
reasoning, scratch work, or step-by-step internal deliberation.
"""


def _value(item: Any, key: str, default: Any = None) -> Any:
    if isinstance(item, Mapping):
        return item.get(key, default)
    return getattr(item, key, default)


def _strict_schema(schema: dict[str, Any]) -> dict[str, Any]:
    """Make a Pydantic schema satisfy strict structured-output object rules."""

    result = json.loads(json.dumps(schema))

    def visit(node: Any) -> None:
        if isinstance(node, dict):
            is_schema_node = any(
                key in node
                for key in (
                    "type",
                    "$ref",
                    "$defs",
                    "properties",
                    "items",
                    "anyOf",
                    "oneOf",
                    "allOf",
                    "enum",
                )
            )
            if is_schema_node:
                for unsupported in (
                    "title",
                    "description",
                    "default",
                    "minLength",
                    "maxLength",
                    "pattern",
                    "format",
                    "minItems",
                    "maxItems",
                    "uniqueItems",
                ):
                    node.pop(unsupported, None)
            if node.get("type") == "object" and isinstance(node.get("properties"), dict):
                node["required"] = list(node["properties"])
                node["additionalProperties"] = False
            for child in node.values():
                visit(child)
        elif isinstance(node, list):
            for child in node:
                visit(child)

    visit(result)
    return result


def structured_critic_response_schema(evaluator_version: str) -> dict[str, Any]:
    """Return the strict schema sent to the Responses API.

    Contract and evaluator identity are constrained to adapter-owned values;
    the model cannot select arbitrary version labels.
    """

    schema = _strict_schema(StructuredCriticResult.model_json_schema())
    properties = schema["properties"]
    properties["contract_version"] = {
        "type": "string",
        "enum": [STRUCTURED_CRITIC_RESULT_VERSION],
    }
    properties["evaluator_version"] = {
        "type": "string",
        "enum": [evaluator_version],
    }
    schema["required"] = list(properties)
    schema["additionalProperties"] = False
    return schema


def _active_agent_ids(plan: AnalysisPlan) -> tuple[str, ...]:
    agent_ids = {
        agent.value
        for requirement in plan.requirements
        for agent in requirement.required_agents
    }
    agent_ids.add(AnalysisAgent.ORCHESTRATOR.value)
    return tuple(sorted(agent_ids))


def _render_critic_payload(
    *,
    plan: AnalysisPlan,
    claims: Sequence[AtomicClaim],
    stage1_report: Stage1ValidationReport,
    round_context: SemanticRoundContext,
) -> dict[str, Any]:
    expected_applicability = {
        dimension.value: applicability.value
        for dimension, applicability in sorted(
            expected_dimension_applicability(plan).items(),
            key=lambda item: item[0].value,
        )
    }
    prior_issues = tuple(
        sorted(round_context.prior_issues, key=lambda issue: issue.issue_id)
    )
    return {
        "plan_version": plan.plan_version,
        "dataset_id": plan.dataset_id,
        "dataset_snapshot_id": plan.dataset_snapshot_id,
        "query_id": plan.query_id,
        "analysis_scope": plan.scope.model_dump(mode="json"),
        "causal_claim_policy": plan.causal_claim_policy.value,
        "normalized_analytical_question": plan.normalized_question,
        "frozen_requirements": [
            requirement.model_dump(mode="json")
            for requirement in sorted(
                plan.requirements,
                key=lambda item: item.requirement_id,
            )
        ],
        "requested_outputs": list(plan.requested_outputs),
        "applicable_links": [
            link.model_dump(mode="json")
            for link in sorted(plan.applicable_links, key=lambda item: item.link_id)
        ],
        "active_agent_ids": list(_active_agent_ids(plan)),
        "claims": [
            claim.model_dump(mode="json")
            for claim in sorted(claims, key=lambda item: item.claim_id)
        ],
        "stage1_gate_summary": {
            "passed": stage1_report.passed,
            "integrity_violations": list(stage1_report.integrity_violations),
            "gates": {
                gate_id: gate.model_dump(mode="json")
                for gate_id, gate in sorted(stage1_report.gate_results.items())
            },
        },
        "round_number": round_context.round_number,
        "prior_issue_ids": list(sorted(round_context.prior_issue_ids)),
        "prior_open_issues": [
            issue.model_dump(mode="json") for issue in prior_issues
        ],
        "expected_semantic_dimension_applicability": expected_applicability,
        "allowed_claim_ids": sorted(claim.claim_id for claim in claims),
        "allowed_requirement_ids": sorted(
            requirement.requirement_id for requirement in plan.requirements
        ),
        "allowed_applicable_link_ids": sorted(
            link.link_id for link in plan.applicable_links
        ),
        "critic_policy_metadata": {
            "role": "semantic_reviewer",
            "semantic_evaluation_version": SEMANTIC_EVALUATION_VERSION,
            "expected_dimension_applicability": expected_applicability,
            "allowed_active_agent_ids": list(_active_agent_ids(plan)),
            "prior_issue_statuses": [status.value for status in CritiqueIssueStatus],
            "acceptance_decision_owned_by_core": True,
            "stage1_integrity_owned_by_core": True,
            "data_retrieval_allowed": False,
            "tool_calls_allowed": False,
        },
    }


def _serialize_payload(payload: Mapping[str, Any]) -> str:
    try:
        return json.dumps(
            payload,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        )
    except (TypeError, ValueError) as exc:
        raise OpenAISemanticCriticError(
            "openai_semantic_critic_payload_invalid"
        ) from exc


def _reject_json_constant(value: str) -> None:
    raise ValueError(value)


def _contains_refusal(response: Any) -> bool:
    if _value(response, "refusal") not in (None, ""):
        return True
    output = _value(response, "output", ()) or ()
    for item in output:
        if _value(item, "type") in {"refusal", "output_refusal"}:
            return True
        if _value(item, "refusal") not in (None, ""):
            return True
        content = _value(item, "content", ()) or ()
        for content_item in content:
            if _value(content_item, "type") in {"refusal", "output_refusal"}:
                return True
            if _value(content_item, "refusal") not in (None, ""):
                return True
    return False


def _prior_issue_accounting(
    result: StructuredCriticResult,
    round_context: SemanticRoundContext,
) -> None:
    expected_ids = tuple(round_context.prior_issue_ids)
    if not expected_ids:
        return
    counts = {issue_id: 0 for issue_id in expected_ids}
    for issue in result.critique_issues:
        if issue.issue_id in counts:
            counts[issue.issue_id] += 1
    if any(counts[issue_id] != 1 for issue_id in expected_ids):
        raise OpenAISemanticCriticError("openai_semantic_critic_prior_issue_accounting_invalid")


class OpenAISemanticCritic:
    """Provider-backed implementation of the provider-neutral critic protocol."""

    def __init__(
        self,
        *,
        client: ResponsesClient,
        config: ProviderExecutionConfig,
    ) -> None:
        if config.provider_id != "openai":
            raise OpenAISemanticCriticError("openai_semantic_critic_provider_invalid")
        if config.retrieval_mode != "prefetched":
            raise OpenAISemanticCriticError(
                "openai_semantic_critic_retrieval_mode_invalid"
            )
        self._client = client
        self._config = config.model_copy(deep=True)
        self._evaluator_version = (
            f"{OPENAI_SEMANTIC_CRITIC_ADAPTER_VERSION}:{config.model_id}"
        )

    @property
    def evaluator_version(self) -> str:
        return self._evaluator_version

    def evaluate(
        self,
        *,
        plan: AnalysisPlan,
        claims: Sequence[AtomicClaim],
        stage1_report: Stage1ValidationReport,
        round_context: SemanticRoundContext,
    ) -> StructuredCriticResult:
        if not isinstance(plan, AnalysisPlan):
            raise OpenAISemanticCriticError("openai_semantic_critic_plan_invalid")
        if not isinstance(stage1_report, Stage1ValidationReport):
            raise OpenAISemanticCriticError("openai_semantic_critic_stage1_invalid")
        if not isinstance(round_context, SemanticRoundContext):
            raise OpenAISemanticCriticError("openai_semantic_critic_context_invalid")
        if round_context.prior_issue_ids:
            prior_issue_detail_ids = tuple(
                issue.issue_id for issue in round_context.prior_issues
            )
            if prior_issue_detail_ids != tuple(round_context.prior_issue_ids):
                raise OpenAISemanticCriticError(
                    "openai_semantic_critic_prior_issue_details_missing"
                )
        normalized_claims = tuple(claims)
        if any(not isinstance(claim, AtomicClaim) for claim in normalized_claims):
            raise OpenAISemanticCriticError("openai_semantic_critic_claims_invalid")

        payload = _render_critic_payload(
            plan=plan,
            claims=normalized_claims,
            stage1_report=stage1_report,
            round_context=round_context,
        )
        input_payload = _serialize_payload(payload)
        if len(input_payload) > self._config.max_context_chars:
            raise OpenAISemanticCriticError(
                "openai_semantic_critic_context_limit_exceeded"
            )

        request_kwargs: dict[str, Any] = {
            "model": self._config.model_id,
            "instructions": _CRITIC_INSTRUCTIONS,
            "input": input_payload,
            "text": {
                "format": {
                    "type": "json_schema",
                    "name": "structured_critic_result",
                    "strict": True,
                    "schema": structured_critic_response_schema(
                        self._evaluator_version
                    ),
                }
            },
            "max_output_tokens": self._config.max_output_tokens,
            "store": False,
        }
        if self._config.model_id.startswith("gpt-5"):
            request_kwargs["reasoning"] = {
                "effort": self._config.reasoning_effort,
            }
        else:
            request_kwargs["temperature"] = self._config.temperature

        try:
            response = self._client.responses.create(**request_kwargs)
        except Exception as exc:
            raise OpenAISemanticCriticError(
                "openai_semantic_critic_request_failed"
            ) from exc

        if _contains_refusal(response):
            raise OpenAISemanticCriticError("openai_semantic_critic_refused")
        status = _value(response, "status")
        if status is not None and status != "completed":
            raise OpenAISemanticCriticError(
                "openai_semantic_critic_response_incomplete"
            )
        output_text = _value(response, "output_text")
        if not isinstance(output_text, str) or not output_text.strip():
            raise OpenAISemanticCriticError("openai_semantic_critic_output_missing")

        try:
            decoded = json.loads(
                output_text,
                parse_constant=_reject_json_constant,
            )
        except (TypeError, ValueError, json.JSONDecodeError) as exc:
            raise OpenAISemanticCriticError(
                "openai_semantic_critic_json_invalid"
            ) from exc
        if not isinstance(decoded, dict):
            raise OpenAISemanticCriticError("openai_semantic_critic_json_invalid")

        try:
            result = StructuredCriticResult.model_validate(decoded)
        except (TypeError, ValueError, ValidationError) as exc:
            raise OpenAISemanticCriticError(
                "openai_semantic_critic_result_invalid"
            ) from exc
        if result.contract_version != STRUCTURED_CRITIC_RESULT_VERSION:
            raise OpenAISemanticCriticError(
                "openai_semantic_critic_contract_version_invalid"
            )
        if result.evaluator_version != self._evaluator_version:
            raise OpenAISemanticCriticError(
                "openai_semantic_critic_evaluator_version_invalid"
            )
        _prior_issue_accounting(result, round_context)
        return result.model_copy(deep=True)


__all__ = [
    "OPENAI_SEMANTIC_CRITIC_ADAPTER_VERSION",
    "OpenAISemanticCritic",
    "OpenAISemanticCriticError",
    "ResponsesClient",
    "ResponsesCreate",
    "structured_critic_response_schema",
]
