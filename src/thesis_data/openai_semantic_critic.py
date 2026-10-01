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
import math
import re
from typing import Any, Protocol

from pydantic import ValidationError

from .analysis_plan import AnalysisAgent, AnalysisPlan
from .provider_config import ProviderExecutionConfig
from .schema import (
    AtomicClaim,
    CritiqueAction,
    CritiqueIssue,
    CritiqueIssueStatus,
    CritiqueIssueType,
    CritiqueSeverity,
    Stage1ValidationReport,
)
from .semantic_critic import (
    SemanticCritic,
    SemanticEvaluationError,
    SemanticRoundContext,
    validate_synthesis_supporting_claim_ids,
)
from .semantic_evaluation import (
    FROZEN_SEMANTIC_DIMENSIONS,
    SEMANTIC_EVALUATION_VERSION,
    STRUCTURED_CRITIC_RESULT_VERSION,
    SemanticDimension,
    SemanticDimensionApplicability,
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


_CRITIC_INSTRUCTIONS = """You are a semantic reviewer for a Vietnamese equity-research analytical report.
Evaluate only the public, auditable context in the JSON input.

Hướng dẫn phản biện (tiếng Việt):
1. Số liệu, phép tính, tỷ lệ đếm (ví dụ 3/4 chỉ tiêu), thứ hạng và phép so sánh đã được code kiểm định độc lập qua Stage-1 và bộ kiểm tra câu. Chiều tốt của từng chỉ tiêu (direction: higher_is_better hoặc lower_is_better, ví dụ nợ xấu NPL hay tỷ lệ chi phí CIR càng thấp càng tốt) đã được code tính toán chuẩn xác trong trường `direction` và `hien_thi` của từng fact trong payload. Critic TUYỆT ĐỐI KHÔNG kiểm lại số liệu, phép tính hay chiều chỉ tiêu.
2. Kiểm tra trả lời đúng câu hỏi: khối đầu tiên (answer hoặc headline) có trả lời trực tiếp câu hỏi người dùng không. Nếu không, tạo issue incomplete_synthesis cho orchestrator (required_action=REVISE_CLAIM).
3. Kiểm tra diễn giải: nhận định có nói quá, nói thiếu, hoặc khái quát thành "toàn ngành" trong khi chỉ là mẫu khảo sát không; có bỏ sót lưu ý quan trọng không. Nếu có, tạo issue unsupported_claim kèm affected_sentence_ids.
4. Kiểm tra hình: hình không hỗ trợ luận điểm nào, hoặc trùng ý → tạo issue incomplete_synthesis cho orchestrator, kèm affected_block_index, required_action=REMOVE_CLAIM.
5. Mỗi ứng viên mâu thuẫn (cross_level_candidates): xác nhận (confirmed) kèm 1–2 câu nhận định tiếng Việt có fact_ids, hoặc bác bỏ (dismissed) kèm lý do rõ ràng.
6. Nếu có finding confirmed mà báo cáo không nhắc tới → tạo issue cross_level_contradiction cho orchestrator (required_action=RECONCILE_CROSS_LEVEL).
7. Mỗi issue có description tiếng Việt, evidence_refs = fact_ids, required_action thuộc {REVISE_CLAIM, REMOVE_CLAIM, ADD_LIMITATION, RECONCILE_CROSS_LEVEL}.
8. Tiêu chí phản biện chỉ áp dụng theo các mục 2-7 ở trên (spec §6). TUYỆT ĐỐI KHÔNG áp dụng các requirement cũ của atomic claims pipeline (như đòi hỏi báo cáo giá trị trung vị do provider cung cấp).

Return exactly one JSON object matching the supplied strict schema. Do not make an acceptance decision or override Stage-1.
For every prior OPEN issue in prior_open_issues, return the same issue_id exactly once with status OPEN, RESOLVED, EXPLAINED, or UNRESOLVED.

Your JSON output MUST have the following top-level keys and structure:
- "contract_version": "structured-critic-result-v1"
- "evaluator_version": "<evaluator_version>"
- "dimension_scores": array of objects, one for each of the 6 frozen dimensions:
  ["groundedness", "cross_level_integration", "answer_coverage", "logical_soundness", "uncertainty_limitations", "analytical_usefulness"]
- "critique_issues": array of objects (if any issues found)
  Each issue object has:
  {"issue_id": "...", "issue_type": "...", "severity": "...", "affected_agent": "...", "description": "...", "required_action": "...", "resolution_status": "OPEN", "affected_requirement_ids": [], "affected_claim_ids": [], "affected_sentence_ids": [], "affected_block_index": null, "evidence_refs": []}
- "cross_level_findings": array of findings with status "confirmed" or "dismissed"
- "fulfilled_requirement_ids": array of requirement ID strings
- "partially_fulfilled_requirement_ids": array of requirement ID strings
- "unfulfilled_requirement_ids": array of requirement ID strings
- "applicable_link_results": array of link result objects
"""


def _value(item: Any, key: str, default: Any = None) -> Any:
    if isinstance(item, Mapping):
        return item.get(key, default)
    return getattr(item, key, default)


def _clean_json_text(text: str) -> str:
    cleaned = text.strip()
    if cleaned.startswith("```"):
        # Remove leading ```json or ```
        cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned, flags=re.IGNORECASE)
        # Remove trailing ```
        cleaned = re.sub(r"\s*```$", "", cleaned)
    return cleaned.strip()


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
    rendered_narrative = []
    for s in round_context.narrative:
        if isinstance(s, dict):
            rendered_narrative.append(s)
        elif hasattr(s, "model_dump"):
            rendered_narrative.append(s.model_dump(mode="json"))
        elif hasattr(s, "_asdict"):
            rendered_narrative.append(s._asdict())
        else:
            rendered_narrative.append({
                "sentence_id": getattr(s, "sentence_id", ""),
                "text": getattr(s, "text", ""),
                "fact_ids": list(getattr(s, "fact_ids", ())),
                "author_role": getattr(s, "author_role", None),
            })

    rendered_spec = None
    if round_context.report_spec:
        blocks_summary = []
        for b in round_context.report_spec.get("blocks", []):
            block_info = {"type": b.get("type")}
            if "title" in b:
                block_info["title"] = b["title"]
            if "chart" in b:
                block_info["chart"] = b["chart"]
            if "headline" in b:
                block_info["headline"] = b["headline"]
            blocks_summary.append(block_info)
        rendered_spec = {
            "kind": round_context.report_spec.get("kind"),
            "blocks": blocks_summary,
        }

    rendered_cross_level_candidates = []
    for cand in round_context.cross_level_candidates:
        if isinstance(cand, dict):
            rendered_cross_level_candidates.append(cand)
        elif hasattr(cand, "model_dump"):
            rendered_cross_level_candidates.append(cand.model_dump(mode="json"))
        else:
            rendered_cross_level_candidates.append(str(cand))

    rendered_facts = []
    for f in getattr(round_context, "facts", ()):
        if isinstance(f, dict):
            fid = f.get("fact_id", "")
            ftype = f.get("fact_type", "")
            ent = f.get("entity_id")
            mid = f.get("metric_id", "")
            p = f.get("period", "")
            val = f.get("value")
            unit = f.get("unit", "")
            direction = f.get("direction")
            hien_thi = f.get("hien_thi") or f.get("display_text")
        else:
            fid = getattr(f, "fact_id", "")
            ftype = getattr(f, "fact_type", "")
            ent = getattr(f, "entity_id", None)
            mid = getattr(f, "metric_id", "")
            p = getattr(f, "period", "")
            val = getattr(f, "value", None)
            unit = getattr(f, "unit", "")
            direction = getattr(f, "direction", None)
            hien_thi = getattr(f, "hien_thi", None) or getattr(f, "display_text", None)

        if not direction:
            if mid in ("bank.npl_g35", "bank.cir") or "npl" in mid or "cir" in mid:
                direction = "lower_is_better"
            else:
                direction = "higher_is_better"

        if not hien_thi and val is not None:
            if unit == "%":
                hien_thi = f"{val}%"
            elif unit == "pp":
                hien_thi = f"{val} điểm %"
            else:
                hien_thi = str(val)

        denom = getattr(f, "denominator", None) or (f.get("denominator") if isinstance(f, dict) else None)
        if ftype == "lead_count" and denom:
            int_val = int(val) if val is not None else 0
            hien_thi = f"{int_val}/{denom} chỉ tiêu"

        fact_dict = {
            "fact_id": fid,
            "fact_type": ftype,
            "entity_id": ent,
            "metric_id": mid,
            "period": p,
            "value": val,
            "unit": unit,
            "direction": direction,
            "hien_thi": hien_thi,
            "display_text": hien_thi,
        }
        if denom is not None:
            fact_dict["denominator"] = denom
            if ftype == "lead_count":
                fact_dict["mo_ta"] = f"{ent} dẫn trước ở {int(val) if val is not None else 0}/{denom} chỉ tiêu (đã tính đúng chiều lower_is_better như nợ xấu NPL)"
        rendered_facts.append(fact_dict)

    is_report_spec_mode = round_context.report_spec is not None

    return {
        "plan_version": plan.plan_version,
        "dataset_id": plan.dataset_id,
        "dataset_snapshot_id": plan.dataset_snapshot_id,
        "query_id": plan.query_id,
        "analysis_scope": plan.scope.model_dump(mode="json"),
        "question": plan.normalized_question,
        "question_type": getattr(plan, "question_type", None) or "company_profile",
        "narrative": rendered_narrative,
        "report_spec": rendered_spec,
        "cross_level_candidates": rendered_cross_level_candidates,
        "facts": rendered_facts,
        "report_level_synthesis": {
            "target_id": round_context.synthesis_target_id,
            "summary": round_context.synthesis_summary,
            "supporting_claim_ids": list(
                round_context.synthesis_supporting_claim_ids
            ),
        },
        "causal_claim_policy": plan.causal_claim_policy.value,
        "normalized_analytical_question": plan.normalized_question,
        "frozen_requirements": [
            requirement.model_dump(mode="json")
            for requirement in sorted(
                plan.requirements,
                key=lambda item: item.requirement_id,
            )
        ] if not is_report_spec_mode else [],
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
        ) if not is_report_spec_mode else [],
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


_DEFAULT_FROZEN_DIMENSIONS = (
    SemanticDimension.GROUNDEDNESS.value,
    SemanticDimension.CROSS_LEVEL_INTEGRATION.value,
    SemanticDimension.ANSWER_COVERAGE.value,
    SemanticDimension.LOGICAL_SOUNDNESS.value,
    SemanticDimension.UNCERTAINTY_LIMITATIONS.value,
    SemanticDimension.ANALYTICAL_USEFULNESS.value,
)

_DIMENSION_ALIAS_MAP: dict[str, str] = {
    "factual_accuracy": SemanticDimension.GROUNDEDNESS.value,
    "source_grounding": SemanticDimension.GROUNDEDNESS.value,
    "groundedness": SemanticDimension.GROUNDEDNESS.value,
    "scope_completeness": SemanticDimension.ANSWER_COVERAGE.value,
    "answer_coverage": SemanticDimension.ANSWER_COVERAGE.value,
    "logical_coherence": SemanticDimension.LOGICAL_SOUNDNESS.value,
    "logical_soundness": SemanticDimension.LOGICAL_SOUNDNESS.value,
    "synthesis_integration": SemanticDimension.CROSS_LEVEL_INTEGRATION.value,
    "cross_level_integration": SemanticDimension.CROSS_LEVEL_INTEGRATION.value,
    "constraint_adherence": SemanticDimension.UNCERTAINTY_LIMITATIONS.value,
    "uncertainty_limitations": SemanticDimension.UNCERTAINTY_LIMITATIONS.value,
    "analytical_usefulness": SemanticDimension.ANALYTICAL_USEFULNESS.value,
}

_SEVERITY_MAP: dict[str, str] = {
    "blocker": CritiqueSeverity.BLOCKER.value,
    "critical": CritiqueSeverity.BLOCKER.value,
    "major": CritiqueSeverity.MAJOR.value,
    "medium": CritiqueSeverity.MAJOR.value,
    "high": CritiqueSeverity.MAJOR.value,
    "moderate": CritiqueSeverity.MAJOR.value,
    "warning": CritiqueSeverity.MAJOR.value,
    "minor": CritiqueSeverity.MINOR.value,
    "low": CritiqueSeverity.MINOR.value,
    "info": CritiqueSeverity.MINOR.value,
}

_ACTION_MAP: dict[str, str] = {
    "requery_data": CritiqueAction.REQUERY_DATA.value,
    "retrieve_evidence": CritiqueAction.RETRIEVE_EVIDENCE.value,
    "revise_claim": CritiqueAction.REVISE_CLAIM.value,
    "remove_claim": CritiqueAction.REMOVE_CLAIM.value,
    "add_limitation": CritiqueAction.ADD_LIMITATION.value,
    "reconcile_cross_level": CritiqueAction.RECONCILE_CROSS_LEVEL.value,
}

_STATUS_MAP: dict[str, str] = {
    "open": CritiqueIssueStatus.OPEN.value,
    "resolved": CritiqueIssueStatus.RESOLVED.value,
    "explained": CritiqueIssueStatus.EXPLAINED.value,
    "unresolved": CritiqueIssueStatus.UNRESOLVED.value,
}


def _normalize_critic_output(
    decoded: dict[str, Any],
    evaluator_version: str,
    plan: AnalysisPlan | None = None,
) -> dict[str, Any]:
    """Normalize raw or alternative model output into a valid StructuredCriticResult dict."""

    normalized: dict[str, Any] = {}

    # 1. contract_version
    contract_ver = decoded.get("contract_version")
    if not isinstance(contract_ver, str) or contract_ver != STRUCTURED_CRITIC_RESULT_VERSION:
        normalized["contract_version"] = STRUCTURED_CRITIC_RESULT_VERSION
    else:
        normalized["contract_version"] = contract_ver

    # 2. evaluator_version
    # The evaluator identity is the configured adapter and model, not whatever string the
    # model echoes back (some models rewrite it, e.g. to their own name), so it is set here
    # the same way as contract_version.
    normalized["evaluator_version"] = evaluator_version

    # 3. applicable_link_results / link_results
    raw_links = decoded.get("applicable_link_results")
    if raw_links is None and "link_results" in decoded:
        raw_links = decoded.get("link_results")
    if not isinstance(raw_links, Sequence) or isinstance(raw_links, (str, bytes)):
        raw_links = []

    normalized_links: list[dict[str, Any]] = []
    seen_link_ids: set[str] = set()
    for idx, item in enumerate(raw_links):
        if not isinstance(item, Mapping):
            continue
        raw_link_id = str(item.get("link_id") or item.get("id", "")).strip()
        if not raw_link_id:
            raw_link_id = f"link_{idx + 1}"
        link_id = raw_link_id
        suffix = 1
        while link_id in seen_link_ids:
            suffix += 1
            link_id = f"{raw_link_id}_{suffix}"
        seen_link_ids.add(link_id)

        raw_score = item.get("score")
        score = 1.0
        if raw_score is not None:
            try:
                parsed_score = float(raw_score)
                if math.isfinite(parsed_score):
                    score = max(0.0, min(1.0, parsed_score))
            except (TypeError, ValueError):
                score = 1.0

        raw_rationale = item.get("rationale")
        rationale = str(raw_rationale).strip() if raw_rationale else "Evaluated link."
        if not rationale:
            rationale = "Evaluated link."

        supporting_claim_ids = [
            str(c).strip()
            for c in item.get("supporting_claim_ids", [])
            if str(c).strip()
        ]
        issue_ids = [
            str(i).strip()
            for i in item.get("issue_ids", [])
            if str(i).strip()
        ]

        normalized_links.append({
            "link_id": link_id,
            "score": score,
            "rationale": rationale,
            "supporting_claim_ids": list(dict.fromkeys(supporting_claim_ids)),
            "issue_ids": list(dict.fromkeys(issue_ids)),
        })

    if plan is not None:
        plan_link_ids = {link.link_id for link in plan.applicable_links}
        if not plan_link_ids:
            normalized_links = []
        else:
            filtered_links: list[dict[str, Any]] = []
            seen_plan_links: set[str] = set()
            for link in normalized_links:
                lid = link["link_id"]
                if lid in plan_link_ids and lid not in seen_plan_links:
                    filtered_links.append(link)
                    seen_plan_links.add(lid)
            for plan_link in sorted(plan.applicable_links, key=lambda item: item.link_id):
                if plan_link.link_id not in seen_plan_links:
                    filtered_links.append({
                        "link_id": plan_link.link_id,
                        "score": 1.0,
                        "rationale": "Link evaluated.",
                        "supporting_claim_ids": [],
                        "issue_ids": [],
                    })
                    seen_plan_links.add(plan_link.link_id)
            normalized_links = filtered_links

    candidate_link_issue_ids = {
        iid
        for link in normalized_links
        for iid in link.get("issue_ids", [])
    }

    # 4. critique_issues
    raw_issues = decoded.get("critique_issues")
    if raw_issues is None and "issues" in decoded:
        raw_issues = decoded.get("issues")
    if not isinstance(raw_issues, Sequence) or isinstance(raw_issues, (str, bytes)):
        raw_issues = []

    plan_req_ids = (
        {r.requirement_id for r in plan.requirements}
        if plan is not None
        else None
    )
    active_agents = _active_agent_ids(plan) if plan is not None else None

    normalized_issues: list[dict[str, Any]] = []
    seen_issue_ids: set[str] = set()
    for idx, item in enumerate(raw_issues):
        if not isinstance(item, Mapping):
            continue
        raw_id = str(item.get("issue_id", "")).strip()
        if not raw_id:
            raw_id = f"issue_{idx + 1}"
        issue_id = raw_id
        suffix = 1
        while issue_id in seen_issue_ids:
            suffix += 1
            issue_id = f"{raw_id}_{suffix}"
        seen_issue_ids.add(issue_id)

        target_id = str(item.get("target_id", "")).strip()
        raw_agent = str(item.get("affected_agent", "")).strip()
        if not raw_agent:
            raw_agent = "orchestrator" if target_id == "synthesis" else "company_specialist"

        if active_agents is not None and raw_agent not in active_agents:
            if target_id == "synthesis":
                raw_agent = AnalysisAgent.ORCHESTRATOR.value
            else:
                specialists = [
                    a for a in active_agents
                    if a != AnalysisAgent.ORCHESTRATOR.value
                ]
                raw_agent = specialists[0] if specialists else active_agents[0]

        raw_type = str(item.get("issue_type", "")).strip().lower()
        issue_type = (
            raw_type
            if raw_type in {t.value for t in CritiqueIssueType}
            else CritiqueIssueType.UNSUPPORTED_CLAIM.value
        )

        raw_sev = str(item.get("severity", "")).strip().lower()
        severity = _SEVERITY_MAP.get(raw_sev, CritiqueSeverity.MAJOR.value)

        raw_desc = (
            item.get("description")
            or item.get("rationale")
            or item.get("message")
        )
        description = str(raw_desc).strip() if raw_desc else "Critic evaluation issue."
        if not description:
            description = "Critic evaluation issue."

        raw_action = str(
            item.get("required_action") or item.get("action", "")
        ).strip().lower()
        action = _ACTION_MAP.get(raw_action, CritiqueAction.REVISE_CLAIM.value)

        if action == CritiqueAction.RECONCILE_CROSS_LEVEL.value:
            if (
                plan is None
                or not plan.applicable_links
                or issue_id not in candidate_link_issue_ids
            ):
                action = CritiqueAction.REVISE_CLAIM.value

        raw_status = str(
            item.get("resolution_status") or item.get("status", "")
        ).strip().lower()
        status = _STATUS_MAP.get(raw_status, CritiqueIssueStatus.OPEN.value)

        affected_claims = [
            str(c).strip()
            for c in item.get("affected_claim_ids", [])
            if str(c).strip()
        ]
        if raw_agent == AnalysisAgent.ORCHESTRATOR.value:
            affected_claims = []
        affected_sentence_ids = [
            str(s).strip()
            for s in item.get("affected_sentence_ids", [])
            if str(s).strip()
        ]
        raw_block_idx = item.get("affected_block_index")
        affected_block_index: int | None = None
        if raw_block_idx is not None:
            try:
                affected_block_index = int(raw_block_idx)
            except (ValueError, TypeError):
                affected_block_index = None

        affected_reqs = [
            str(r).strip()
            for r in item.get("affected_requirement_ids", [])
            if str(r).strip()
        ]
        if plan_req_ids is not None:
            affected_reqs = [r for r in affected_reqs if r in plan_req_ids]

        evidence_refs = [
            str(e).strip()
            for e in item.get("evidence_refs", [])
            if str(e).strip()
        ]

        issue_dict: dict[str, Any] = {
            "issue_id": issue_id,
            "issue_type": issue_type,
            "severity": severity,
            "affected_agent": raw_agent,
            "affected_claim_ids": list(dict.fromkeys(affected_claims)),
            "affected_requirement_ids": list(dict.fromkeys(affected_reqs)),
            "affected_sentence_ids": list(dict.fromkeys(affected_sentence_ids)),
            "affected_block_index": affected_block_index,
            "description": description,
            "evidence_refs": list(dict.fromkeys(evidence_refs)),
            "required_action": action,
            "resolution_status": status,
        }
        if status == CritiqueIssueStatus.UNRESOLVED.value:
            reason = item.get("unresolved_reason_code")
            if reason:
                issue_dict["unresolved_reason_code"] = reason
        normalized_issues.append(issue_dict)

    normalized["critique_issues"] = normalized_issues

    valid_issue_ids = {iss["issue_id"] for iss in normalized_issues}

    # Clean up link issue_ids now that valid_issue_ids is finalized
    assigned_cross_level_issues: set[str] = set()
    reconcile_issue_ids = {
        iss["issue_id"]
        for iss in normalized_issues
        if iss["required_action"] == CritiqueAction.RECONCILE_CROSS_LEVEL.value
    }
    for link in normalized_links:
        cleaned_iids: list[str] = []
        for iid in link["issue_ids"]:
            if iid in valid_issue_ids:
                if iid in reconcile_issue_ids:
                    if iid not in assigned_cross_level_issues:
                        cleaned_iids.append(iid)
                        assigned_cross_level_issues.add(iid)
                else:
                    cleaned_iids.append(iid)
        link["issue_ids"] = cleaned_iids

    normalized["applicable_link_results"] = normalized_links

    # 5. dimension_scores
    raw_dims = decoded.get("dimension_scores")
    dims_by_canonical: dict[str, dict[str, Any]] = {}
    if isinstance(raw_dims, Sequence) and not isinstance(raw_dims, (str, bytes)):
        for item in raw_dims:
            if not isinstance(item, Mapping):
                continue
            raw_name = str(item.get("dimension", "")).strip().lower().replace(" ", "_")
            canonical_dim = _DIMENSION_ALIAS_MAP.get(raw_name)
            if not canonical_dim or canonical_dim in dims_by_canonical:
                continue

            raw_score = item.get("score")
            score: float | None = 1.0
            if raw_score is not None:
                try:
                    parsed_score = float(raw_score)
                    if math.isfinite(parsed_score):
                        score = max(0.0, min(1.0, parsed_score))
                except (TypeError, ValueError):
                    score = 1.0

            raw_rationale = item.get("rationale")
            rationale = str(raw_rationale).strip() if raw_rationale else "Evaluated."
            if not rationale:
                rationale = "Evaluated."

            supporting_claim_ids = [
                str(c).strip()
                for c in item.get("supporting_claim_ids", [])
                if str(c).strip()
            ]
            affected_requirement_ids = [
                str(r).strip()
                for r in item.get("affected_requirement_ids", [])
                if str(r).strip()
            ]
            issue_ids = [
                str(i).strip()
                for i in item.get("issue_ids", [])
                if str(i).strip()
            ]

            applicability = str(item.get("applicability", "APPLICABLE")).upper()
            if applicability == "NOT_APPLICABLE":
                dims_by_canonical[canonical_dim] = {
                    "dimension": canonical_dim,
                    "applicability": "NOT_APPLICABLE",
                    "score": None,
                    "rationale": rationale,
                    "supporting_claim_ids": [],
                    "affected_requirement_ids": [],
                    "issue_ids": [],
                }
            else:
                dims_by_canonical[canonical_dim] = {
                    "dimension": canonical_dim,
                    "applicability": "APPLICABLE",
                    "score": score,
                    "rationale": rationale,
                    "supporting_claim_ids": list(dict.fromkeys(supporting_claim_ids)),
                    "affected_requirement_ids": list(dict.fromkeys(affected_requirement_ids)),
                    "issue_ids": list(dict.fromkeys(issue_ids)),
                }

    normalized_dims: list[dict[str, Any]] = []
    for dim_name in _DEFAULT_FROZEN_DIMENSIONS:
        if dim_name in dims_by_canonical:
            normalized_dims.append(dims_by_canonical[dim_name])
        else:
            normalized_dims.append({
                "dimension": dim_name,
                "applicability": "APPLICABLE",
                "score": 1.0,
                "rationale": "Evaluated.",
                "supporting_claim_ids": [],
                "affected_requirement_ids": [],
                "issue_ids": [],
            })

    if plan is not None:
        expected_map = expected_dimension_applicability(plan)
        for dim in normalized_dims:
            dim_enum = SemanticDimension(dim["dimension"])
            expected_app = expected_map[dim_enum]
            dim["applicability"] = expected_app.value
            if expected_app is SemanticDimensionApplicability.NOT_APPLICABLE:
                dim["score"] = None
                dim["supporting_claim_ids"] = []
                dim["affected_requirement_ids"] = []
                dim["issue_ids"] = []
            else:
                if dim["score"] is None or not math.isfinite(dim["score"]):
                    dim["score"] = 1.0
                else:
                    dim["score"] = max(0.0, min(1.0, float(dim["score"])))
                if plan_req_ids is not None:
                    dim["affected_requirement_ids"] = [
                        r for r in dim["affected_requirement_ids"] if r in plan_req_ids
                    ]
                dim["issue_ids"] = [
                    i for i in dim["issue_ids"] if i in valid_issue_ids
                ]
    else:
        for dim in normalized_dims:
            if dim["applicability"] == "NOT_APPLICABLE":
                dim["score"] = None
                dim["supporting_claim_ids"] = []
                dim["affected_requirement_ids"] = []
                dim["issue_ids"] = []
            else:
                dim["issue_ids"] = [
                    i for i in dim["issue_ids"] if i in valid_issue_ids
                ]

    normalized["dimension_scores"] = normalized_dims

    # 6. fulfilled / partially_fulfilled / unfulfilled requirement ids
    fulfilled: list[str] = []
    partially: list[str] = []
    unfulfilled: list[str] = []

    raw_req_results = decoded.get("requirement_results")
    if isinstance(raw_req_results, Sequence) and not isinstance(
        raw_req_results, (str, bytes)
    ):
        for item in raw_req_results:
            if not isinstance(item, Mapping):
                continue
            req_id = str(item.get("requirement_id") or item.get("id", "")).strip()
            if not req_id:
                continue
            status_val = str(item.get("status", "")).strip().lower()
            if "partial" in status_val:
                partially.append(req_id)
            elif (
                "unfulfill" in status_val
                or "fail" in status_val
                or "missing" in status_val
            ):
                unfulfilled.append(req_id)
            else:
                fulfilled.append(req_id)

    raw_fulfilled = decoded.get("fulfilled_requirement_ids")
    if isinstance(raw_fulfilled, Sequence) and not isinstance(
        raw_fulfilled, (str, bytes)
    ):
        for req in raw_fulfilled:
            req_str = str(req).strip()
            if req_str:
                fulfilled.append(req_str)

    raw_partially = decoded.get("partially_fulfilled_requirement_ids")
    if isinstance(raw_partially, Sequence) and not isinstance(
        raw_partially, (str, bytes)
    ):
        for req in raw_partially:
            req_str = str(req).strip()
            if req_str:
                partially.append(req_str)

    raw_unfulfilled = decoded.get("unfulfilled_requirement_ids")
    if isinstance(raw_unfulfilled, Sequence) and not isinstance(
        raw_unfulfilled, (str, bytes)
    ):
        for req in raw_unfulfilled:
            req_str = str(req).strip()
            if req_str:
                unfulfilled.append(req_str)

    fulfilled_dedup: list[str] = list(dict.fromkeys(fulfilled))
    fulfilled_set = set(fulfilled_dedup)
    partially_dedup: list[str] = list(
        dict.fromkeys(r for r in partially if r not in fulfilled_set)
    )
    partially_set = set(partially_dedup)
    unfulfilled_dedup: list[str] = list(
        dict.fromkeys(
            r
            for r in unfulfilled
            if r not in fulfilled_set and r not in partially_set
        )
    )

    if plan_req_ids is not None:
        classified = fulfilled_set | partially_set | set(unfulfilled_dedup)
        for req in plan_req_ids:
            if req not in classified:
                fulfilled_dedup.append(req)

    normalized["fulfilled_requirement_ids"] = fulfilled_dedup
    normalized["partially_fulfilled_requirement_ids"] = partially_dedup
    normalized["unfulfilled_requirement_ids"] = unfulfilled_dedup

    return normalized


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
        try:
            round_context = SemanticRoundContext.model_validate(
                round_context.model_dump(mode="python")
            )
        except (TypeError, ValueError, ValidationError) as exc:
            raise OpenAISemanticCriticError(
                "openai_semantic_critic_context_invalid"
            ) from exc
        normalized_claims = tuple(claims)
        if any(not isinstance(claim, AtomicClaim) for claim in normalized_claims):
            raise OpenAISemanticCriticError("openai_semantic_critic_claims_invalid")
        try:
            validate_synthesis_supporting_claim_ids(
                round_context.synthesis_summary,
                round_context.synthesis_supporting_claim_ids,
                normalized_claims,
            )
        except (TypeError, ValueError) as exc:
            raise OpenAISemanticCriticError(
                "openai_semantic_critic_synthesis_support_invalid"
            ) from exc

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

        response = None
        for attempt in range(3):
            try:
                response = self._client.responses.create(**request_kwargs)
                break
            except Exception as exc:
                if attempt < 2 and ("Connection error" in str(exc) or "timeout" in str(exc).lower()):
                    import time
                    time.sleep(1.0 * (attempt + 1))
                    continue
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

        clean_text = _clean_json_text(output_text)
        try:
            decoded = json.loads(
                clean_text,
                parse_constant=_reject_json_constant,
            )
        except (TypeError, ValueError, json.JSONDecodeError) as exc:
            raise OpenAISemanticCriticError(
                "openai_semantic_critic_json_invalid"
            ) from exc
        if not isinstance(decoded, dict):
            raise OpenAISemanticCriticError("openai_semantic_critic_json_invalid")
        if not decoded or not any(
            k in decoded
            for k in (
                "dimension_scores",
                "critique_issues",
                "issues",
                "requirement_results",
                "link_results",
                "applicable_link_results",
                "fulfilled_requirement_ids",
                "partially_fulfilled_requirement_ids",
                "unfulfilled_requirement_ids",
            )
        ):
            raise OpenAISemanticCriticError("openai_semantic_critic_result_invalid")

        normalized = _normalize_critic_output(
            decoded,
            self._evaluator_version,
            plan=plan,
        )
        try:
            result = StructuredCriticResult.model_validate(normalized)
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
    "_normalize_critic_output",
    "structured_critic_response_schema",
]
