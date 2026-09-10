"""OpenAI transport for typed multi-issuer composite workloads."""

from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
import json
from time import monotonic
from typing import Any, Mapping, Protocol

from pydantic import ValidationError

from .agent_runtime import AgentCallTelemetry, AgentToolCall
from .agent_tools import GoldToolRuntime, ToolExecutionError
from .composite_schema import CompositeAnalysisPayload, CompositeSubreport
from .transport_errors import OpenAITransportError
from .provider_config import ProviderExecutionConfig
from .workload_contract import AnalysisTask, CompositeWorkloadSpec


class CompositeResponsesClient(Protocol):
    class responses(Protocol):  # type: ignore[valid-type]
        @staticmethod
        def create(**kwargs: Any) -> Any: ...


def _value(item: Any, key: str, default: Any = None) -> Any:
    if isinstance(item, dict):
        return item.get(key, default)
    return getattr(item, key, default)


def _strict_schema(schema: dict[str, Any]) -> dict[str, Any]:
    def visit(node: Any) -> None:
        if isinstance(node, dict):
            if node.get("type") == "object" and isinstance(node.get("properties"), dict):
                node["required"] = list(node["properties"])
                node["additionalProperties"] = False
            for child in node.values():
                visit(child)
        elif isinstance(node, list):
            for child in node:
                visit(child)

    result = json.loads(json.dumps(schema))
    visit(result)
    return result


def _normalize_json_text(output_text: str) -> str:
    candidate = output_text.strip()
    if candidate.startswith("```"):
        candidate = candidate.strip("`").strip()
        if candidate.startswith("json"):
            candidate = candidate[4:].strip()
    try:
        value = json.loads(candidate)
    except json.JSONDecodeError:
        start, end = candidate.find("{"), candidate.rfind("}")
        if start < 0 or end <= start:
            raise OpenAITransportError(("provider_output_json_invalid",))
        try:
            value = json.loads(candidate[start : end + 1])
        except json.JSONDecodeError as exc:
            raise OpenAITransportError(("provider_output_json_invalid",)) from exc
    if not isinstance(value, dict):
        raise OpenAITransportError(("provider_output_json_invalid",))
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"), allow_nan=False)


def _remove_defaults_from_refs(node: Any) -> None:
    if isinstance(node, dict):
        if "$ref" in node:
            node.pop("default", None)
        for child in node.values():
            _remove_defaults_from_refs(child)
    elif isinstance(node, list):
        for child in node:
            _remove_defaults_from_refs(child)


def _safe_response_diagnostics(response: Any, output_text: Any) -> tuple[str, ...]:
    """Return non-content diagnostics for a provider response failure."""

    details: list[str] = []
    if isinstance(output_text, str):
        details.append(f"output_text_len={len(output_text)}")
    status = _value(response, "status")
    if isinstance(status, str):
        details.append(f"response_status={status}")
    incomplete = _value(response, "incomplete_details")
    reason = _value(incomplete, "reason")
    if isinstance(reason, str):
        details.append(f"incomplete_reason={reason}")
    output_items = list(_value(response, "output", []) or [])
    item_types = sorted(
        {
            item_type
            for item in output_items
            if isinstance((item_type := _value(item, "type")), str)
        }
    )
    if item_types:
        details.append("output_item_types=" + "+".join(item_types))
    return tuple(details)


def _estimated_context_chars(value: Any) -> int:
    """Estimate request size without serializing provider SDK objects.

    Responses SDK output items are often typed objects that are accepted by
    the next API request but are not JSON serializable in Python. Telemetry
    must not make a valid provider call fail merely because it is measuring
    the bounded context.
    """

    if value is None:
        return 4
    if isinstance(value, str):
        return len(value)
    if isinstance(value, (int, float, bool)):
        return len(str(value))
    if isinstance(value, Mapping):
        return sum(_estimated_context_chars(key) + _estimated_context_chars(item) + 4 for key, item in value.items())
    if isinstance(value, (list, tuple)):
        return sum(_estimated_context_chars(item) + 1 for item in value)
    return len(str(value))


@dataclass(frozen=True)
class CompositeProviderResponse:
    payload: CompositeAnalysisPayload
    telemetry: AgentCallTelemetry
    effective_context: Mapping[str, Any]
    tool_calls: tuple[AgentToolCall, ...] = ()
    role: str = ""


def _role_task_values(spec: CompositeWorkloadSpec, role: str) -> tuple[str, ...]:
    declared = {task.value for task in spec.analysis_tasks}
    if role == "company":
        allowed = {"snapshot", "trend", "missing_conflict", "anomaly_review", "evidence_summary"}
    elif role == "sector":
        allowed = {"peer_comparison", "anomaly_review"}
    else:
        allowed = {task.value for task in AnalysisTask}
    return tuple(task.value for task in AnalysisTask if task.value in declared and task.value in allowed)


def _expected_keys(spec: CompositeWorkloadSpec, role: str | None = None) -> set[tuple[str, str, str]]:
    tasks = (
        _role_task_values(spec, role)
        if role is not None and role in {"company", "sector"}
        else tuple(task.value for task in spec.analysis_tasks)
    )
    return {
        (issuer, period, task.value)
        for issuer in spec.issuers
        for period in spec.periods
        for task in (AnalysisTask(task) for task in tasks)
    }


def _provider_subreport_keys(
    spec: CompositeWorkloadSpec,
    role: str,
) -> tuple[str, ...]:
    keys = _expected_keys(spec, role) if role in {"company", "sector"} else _expected_keys(spec)
    return tuple(
        f"{issuer}|{period}|{task}"
        for issuer, period, task in sorted(keys)
    )


def _composite_response_schema(
    spec: CompositeWorkloadSpec,
    role: str,
) -> dict[str, Any]:
    """Create a strict provider schema constrained to this workload."""

    schema = _strict_schema(CompositeAnalysisPayload.model_json_schema())
    properties = schema.get("properties", {})
    properties["agent_id"] = {"type": "string", "enum": [role]}
    properties["question_id"] = {"type": "string", "enum": [spec.question_id]}
    properties["tier"] = {"type": "string", "enum": [spec.tier.value]}
    properties["issuers"] = {
        "type": "array",
        "items": {"type": "string", "enum": list(spec.issuers)},
    }
    properties["periods"] = {
        "type": "array",
        "items": {"type": "string", "enum": list(spec.periods)},
    }
    properties["metric_ids"] = {
        "type": "array",
        "items": {"type": "string", "enum": list(spec.metric_ids)},
    }
    subreport_schema = schema.get("$defs", {}).get("CompositeSubreport")
    if isinstance(subreport_schema, dict):
        subreport_properties = subreport_schema.get("properties", {})
        subreport_properties["issuer"] = {
            "type": "string", "enum": list(spec.issuers)
        }
        subreport_properties["period"] = {
            "type": "string", "enum": list(spec.periods)
        }
        subreport_properties["task"] = {
            "type": "string", "enum": list(_role_task_values(spec, role))
        }
        payload_schema = schema.get("$defs", {}).get("AgentPayload")
        if isinstance(payload_schema, dict):
            payload_properties = payload_schema.get("properties", {})
            payload_properties["ticker"] = {
                "anyOf": [
                    {"type": "string", "enum": list(spec.issuers)},
                    {"type": "null"},
                ]
            }
            payload_properties["period"] = {
                "type": "string", "enum": list(spec.periods)
            }
            payload_properties["agent_id"] = {
                "type": "string", "enum": [role]
            }
            number_or_null = {"anyOf": [{"type": "number"}, {"type": "null"}]}
            string_map = {
                "type": "object",
                "properties": {key: {"type": "string"} for key in spec.metric_ids},
                "required": list(spec.metric_ids),
                "additionalProperties": False,
            }
            numeric_map = {
                "type": "object",
                "properties": {key: number_or_null for key in spec.metric_ids},
                "required": list(spec.metric_ids),
                "additionalProperties": False,
            }
            payload_properties["metrics"] = numeric_map
            payload_properties["sector_benchmarks"] = numeric_map
            payload_properties["metric_units"] = string_map
            payload_properties["metric_periods"] = {
                "type": "object",
                "properties": {
                    key: {"type": "string", "enum": list(spec.periods)}
                    for key in spec.metric_ids
                },
                "required": list(spec.metric_ids),
                "additionalProperties": False,
            }
            payload_schema["required"] = list(payload_properties)
            subreport_properties["payload"] = {
                "anyOf": [
                    json.loads(json.dumps(payload_schema)),
                    {"type": "null"},
                ]
            }
            properties["data_slices"] = {
                "type": "array",
                "items": json.loads(json.dumps(payload_schema)),
            }
        if role in {"single_agent", "company", "sector", "orchestrator"}:
            # Keep the provider-facing schema compact as workload size grows.
            # The previous object keyed by every issuer-period-task repeated
            # the complete value schema once per cell; an array carries the
            # same exact keys while avoiding quadratic schema expansion.
            subreport_item_schema = json.loads(json.dumps(subreport_schema))
            item_properties = subreport_item_schema.get("properties", {})
            item_properties["issuer"] = {"type": "string", "enum": list(spec.issuers)}
            item_properties["period"] = {"type": "string", "enum": list(spec.periods)}
            item_properties["task"] = {"type": "string", "enum": list(_role_task_values(spec, role))}
            subreport_item_schema["properties"] = item_properties
            subreport_item_schema["required"] = list(item_properties)
            properties["subreports"] = {
                "type": "array",
                "items": subreport_item_schema,
            }
    schema["properties"] = properties
    schema["required"] = list(properties)
    _remove_defaults_from_refs(schema)
    return schema


def _validate_composite_payload(
    payload: CompositeAnalysisPayload,
    spec: CompositeWorkloadSpec,
    role: str,
) -> CompositeAnalysisPayload:
    blockers: list[str] = []
    if payload.agent_id != role:
        blockers.append("composite_agent_id_mismatch")
    if payload.question_id != spec.question_id:
        blockers.append("composite_question_id_mismatch")
    if payload.tier != spec.tier:
        blockers.append("composite_tier_mismatch")
    if role == "verification":
        if not payload.issuers or not set(payload.issuers).issubset(set(spec.issuers)):
            blockers.append("composite_issuer_scope_mismatch")
        if not payload.periods or not set(payload.periods).issubset(set(spec.periods)):
            blockers.append("composite_period_scope_mismatch")
    else:
        if tuple(payload.issuers) != tuple(spec.issuers):
            blockers.append("composite_issuer_scope_mismatch")
        if tuple(payload.periods) != tuple(spec.periods):
            blockers.append("composite_period_scope_mismatch")
    if tuple(payload.metric_ids) != tuple(spec.metric_ids):
        blockers.append("composite_metric_scope_mismatch")

    actual_keys = {
        (item.issuer, item.period, item.task.value) for item in payload.subreports
    }
    full_expected_keys = _expected_keys(spec)
    role_expected_keys = _expected_keys(spec, role)
    coverage_invalid = False
    if role in {"single_agent", "orchestrator"}:
        coverage_invalid = actual_keys != full_expected_keys
        expected_count = len(full_expected_keys)
    elif role in {"company", "sector"}:
        coverage_invalid = (
            # Claim-driven workers may publish useful, provenance-bound claims
            # without repeating the full task-reference array.  The
            # orchestrator will publish explicit partial references for any
            # omitted worker task, so this is not treated as a silent success.
            (bool(role_expected_keys) and not actual_keys and not payload.claims)
            or not actual_keys.issubset(role_expected_keys)
        )
        expected_count = len(role_expected_keys)
    elif role == "verification":
        coverage_invalid = not actual_keys or not actual_keys.issubset(full_expected_keys)
        expected_count = 1
    else:
        coverage_invalid = actual_keys != full_expected_keys
        expected_count = len(full_expected_keys)
    if coverage_invalid:
        blockers.extend(
            (
                "composite_subreport_coverage_invalid",
                f"subreport_expected={expected_count}",
                f"subreport_actual={len(actual_keys)}",
            )
        )

    allowed_metrics = set(spec.metric_ids)
    data_slice_keys: set[tuple[str, str]] = set()
    unsupported_data_slice_claims = 0
    for data_slice in payload.data_slices:
        if data_slice.ticker not in spec.issuers or data_slice.period not in spec.periods:
            blockers.append("composite_data_slice_scope_invalid")
        if data_slice.agent_id != role:
            blockers.append("composite_data_slice_agent_id_mismatch")
        data_slice_keys.add((data_slice.ticker or "", data_slice.period))
        fields = (
            set(data_slice.metrics)
            | set(data_slice.sector_benchmarks)
            | set(data_slice.metric_units)
            | set(data_slice.metric_periods)
        )
        if not fields.issubset(allowed_metrics):
            blockers.append("composite_data_slice_metric_outside_scope")
        if any(
            value is not None
            for value in (*data_slice.metrics.values(), *data_slice.sector_benchmarks.values())
        ) and not (
            data_slice.observation_ids
            or data_slice.source_ids
            or data_slice.evidence
        ):
            unsupported_data_slice_claims += 1
    if unsupported_data_slice_claims:
        blockers.extend(
            (
                "composite_numeric_claim_without_provenance",
                f"data_slice_claims_without_provenance={unsupported_data_slice_claims}",
            )
        )
    unsupported_numeric_claims = 0
    for item in payload.subreports:
        if item.payload is None:
            if item.payload_ref is not None and (item.issuer, item.period) not in data_slice_keys:
                blockers.append("composite_payload_ref_unresolved")
            continue
        if item.payload.agent_id != role:
            blockers.append("composite_subreport_agent_id_mismatch")
        fields = (
            set(item.payload.metrics)
            | set(item.payload.sector_benchmarks)
            | set(item.payload.metric_units)
            | set(item.payload.metric_periods)
        )
        if not fields.issubset(allowed_metrics):
            blockers.append("composite_subreport_metric_outside_scope")
        if any(
            value is not None
            for value in (*item.payload.metrics.values(), *item.payload.sector_benchmarks.values())
        ) and not (
            item.payload.observation_ids
            or item.payload.source_ids
            or item.payload.evidence
        ):
            unsupported_numeric_claims += 1
    if unsupported_numeric_claims:
        blockers.extend(
            (
                "composite_numeric_claim_without_provenance",
                f"numeric_claims_without_provenance={unsupported_numeric_claims}",
            )
        )
    allowed_claim_refs = {
        f"{issuer}|{period}|{metric}"
        for issuer in spec.issuers
        for period in spec.periods
        for metric in spec.metric_ids
    }
    published_evidence_ids = set(payload.evidence_ids)
    published_source_ids = set(payload.source_ids)
    for claim in payload.claims:
        invalid_refs = set(claim.data_refs) - allowed_claim_refs
        if invalid_refs:
            blockers.append("composite_claim_data_ref_outside_scope")
        if claim.support == "evidence_backed" and not claim.evidence_ids:
            blockers.append("composite_evidence_backed_claim_without_evidence")
        if not set(claim.evidence_ids).issubset(published_evidence_ids):
            blockers.append("composite_claim_evidence_not_published")
        if not set(claim.source_ids).issubset(published_source_ids):
            blockers.append("composite_claim_source_not_published")
    if blockers:
        raise OpenAITransportError(tuple(dict.fromkeys(blockers)))
    return payload


def _assemble_orchestrator_from_workers(
    payload: CompositeAnalysisPayload,
    spec: CompositeWorkloadSpec,
    prepared_context: Mapping[str, Any],
) -> CompositeAnalysisPayload:
    """Fill compact orchestrator coverage from validated worker context.

    Worker payloads are already validated before they enter the prepared
    context.  The orchestrator only needs to publish a synthesis plus stable
    references to those facts; it should not have to reproduce every worker
    subreport in its own response.  This helper therefore performs only a
    structural merge.  It never creates a numeric value or provenance ID.
    """

    expected_keys = _expected_keys(spec)
    actual_keys = {
        (item.issuer, item.period, item.task.value) for item in payload.subreports
    }
    if actual_keys == expected_keys:
        return payload

    raw_workers = prepared_context.get("worker_payloads")
    if not isinstance(raw_workers, Mapping):
        return payload

    # Sector owns cross-issuer comparison and is the preferred owner for the
    # overlapping anomaly-review task.  Company owns the issuer-level tasks.
    task_owner: dict[str, str] = {}
    for task in spec.analysis_tasks:
        task_value = task.value
        if task is AnalysisTask.PEER_COMPARISON:
            task_owner[task_value] = "sector"
        elif task is AnalysisTask.ANOMALY_REVIEW and "sector" in raw_workers:
            task_owner[task_value] = "sector"
        elif task_value in _role_task_values(spec, "company") and "company" in raw_workers:
            task_owner[task_value] = "company"
        elif task_value in _role_task_values(spec, "sector") and "sector" in raw_workers:
            task_owner[task_value] = "sector"

    worker_payloads: dict[str, Mapping[str, Any]] = {
        str(role): value
        for role, value in raw_workers.items()
        if isinstance(value, Mapping)
    }
    if not worker_payloads or any(task.value not in task_owner for task in spec.analysis_tasks):
        return payload

    slices_by_key: dict[tuple[str, str], dict[str, Any]] = {}
    # Company is the canonical source for issuer metrics; sector is a fallback
    # only for a missing company slice.  The copied agent_id makes the final
    # envelope's provenance boundary explicit: these are orchestrator-published
    # references to worker facts, not new model-generated facts.
    for worker_role in ("company", "sector"):
        worker = worker_payloads.get(worker_role)
        if worker is None:
            continue
        for raw_slice in worker.get("data_slices", ()) or ():
            if not isinstance(raw_slice, Mapping):
                continue
            ticker = raw_slice.get("ticker")
            period = raw_slice.get("period")
            key = (str(ticker), str(period))
            if ticker not in spec.issuers or period not in spec.periods or key in slices_by_key:
                continue
            candidate = dict(raw_slice)
            candidate["agent_id"] = "orchestrator"
            slices_by_key[key] = candidate

    # Require one canonical issuer-period slice for every composite cell.  If
    # workers did not return one, leave the provider response untouched so the
    # existing fail-closed validator reports the missing coverage.
    if len(slices_by_key) != len(spec.issuers) * len(spec.periods):
        return payload

    subreports: list[CompositeSubreport] = []
    for issuer in spec.issuers:
        for period in spec.periods:
            for task in spec.analysis_tasks:
                owner = task_owner[task.value]
                worker = worker_payloads.get(owner, {})
                raw_subreports = worker.get("subreports", {})
                if isinstance(raw_subreports, Mapping):
                    raw_item = raw_subreports.get(f"{issuer}|{period}|{task.value}")
                else:
                    raw_item = next(
                        (
                            item
                            for item in raw_subreports or ()
                            if isinstance(item, Mapping)
                            and item.get("issuer") == issuer
                            and item.get("period") == period
                            and item.get("task") == task.value
                        ),
                        None,
                    )
                if not isinstance(raw_item, Mapping):
                    # Keep the final envelope structurally complete while
                    # making the worker omission visible.  The reference
                    # points to an already validated issuer-period slice; it
                    # does not claim that the omitted worker task was fully
                    # executed.
                    raw_item = {
                        "status": "partial",
                        "missing_reasons": (
                            f"{owner}_worker_compact_task_reference_missing",
                        ),
                        "observation_ids": worker.get("observation_ids", ()) or (),
                        "source_ids": worker.get("source_ids", ()) or (),
                        "evidence_ids": worker.get("evidence_ids", ()) or (),
                    }
                subreports.append(
                    CompositeSubreport(
                        issuer=issuer,
                        period=period,
                        task=task,
                        status=raw_item.get("status", "partial"),
                        payload_ref=f"{issuer}|{period}",
                        missing_reasons=tuple(raw_item.get("missing_reasons", ()) or ()),
                        observation_ids=tuple(raw_item.get("observation_ids", ()) or ()),
                        source_ids=tuple(raw_item.get("source_ids", ()) or ()),
                        evidence_ids=tuple(raw_item.get("evidence_ids", ()) or ()),
                    )
                )

    def union_field(field: str) -> tuple[str, ...]:
        values: list[str] = []
        for item in (payload.model_dump(mode="json"), *worker_payloads.values()):
            raw_values = item.get(field, ()) if isinstance(item, Mapping) else ()
            for value in raw_values or ():
                if isinstance(value, str) and value not in values:
                    values.append(value)
        for raw_slice in slices_by_key.values():
            for value in raw_slice.get(field, ()) or ():
                if isinstance(value, str) and value not in values:
                    values.append(value)
        for item in subreports:
            for value in getattr(item, field, ()):
                if isinstance(value, str) and value not in values:
                    values.append(value)
        return tuple(values)

    def union_text_field(field: str) -> list[str]:
        values: list[str] = []
        for item in (payload.model_dump(mode="json"), *worker_payloads.values()):
            raw_values = item.get(field, ()) if isinstance(item, Mapping) else ()
            for value in raw_values or ():
                if isinstance(value, str) and value not in values:
                    values.append(value)
        return values

    updates = {
        "status": "partial" if any(
            str(item.get("status")) == "partial"
            for item in worker_payloads.values()
            if isinstance(item, Mapping)
        ) else payload.status,
        # The copied worker slices are re-validated by the enclosing Pydantic
        # model below; no field is synthesized here.
        "data_slices": list(slices_by_key.values()),
        "subreports": tuple(subreports),
        "missing_conflict_register": tuple(union_text_field("missing_conflict_register")),
        "anomaly_classifications": tuple(union_text_field("anomaly_classifications")),
        "findings": union_text_field("findings"),
        "quality_flags": union_text_field("quality_flags"),
        "observation_ids": union_field("observation_ids"),
        "source_ids": union_field("source_ids"),
        "evidence_ids": union_field("evidence_ids"),
    }
    return CompositeAnalysisPayload.model_validate(
        {**payload.model_dump(mode="json"), **updates}
    )


def _normalize_claim_provenance(
    payload: CompositeAnalysisPayload,
) -> CompositeAnalysisPayload:
    """Bind claim IDs to IDs actually present in the composite payload.

    Models sometimes cite an evidence/source ID from a tool result but omit
    the required top-level union.  The runtime can safely recover IDs already
    present in canonical slices or subreports.  Unknown IDs are dropped and
    an evidence-backed claim is downgraded instead of being published as
    supported.  No ID or numeric fact is created by this normalization.
    """

    known_evidence = set(payload.evidence_ids)
    known_sources = set(payload.source_ids)
    for data_slice in payload.data_slices:
        known_sources.update(data_slice.source_ids)
        known_evidence.update(item.evidence_id for item in data_slice.evidence)
    for subreport in payload.subreports:
        known_sources.update(subreport.source_ids)
        known_evidence.update(subreport.evidence_ids)

    changed = False
    claims = []
    for claim in payload.claims:
        evidence_ids = tuple(item for item in claim.evidence_ids if item in known_evidence)
        source_ids = tuple(item for item in claim.source_ids if item in known_sources)
        support = claim.support
        if support == "evidence_backed" and not evidence_ids:
            support = "source_locator_only" if source_ids else "partially_supported"
        if evidence_ids != claim.evidence_ids or source_ids != claim.source_ids or support != claim.support:
            changed = True
        claims.append(
            claim.model_copy(
                update={
                    "evidence_ids": evidence_ids,
                    "source_ids": source_ids,
                    "support": support,
                }
            )
        )

    if not changed and (
        set(payload.evidence_ids) == known_evidence
        and set(payload.source_ids) == known_sources
    ):
        return payload
    quality_flags = list(payload.quality_flags)
    if "claim_provenance_normalized" not in quality_flags:
        quality_flags.append("claim_provenance_normalized")
    return CompositeAnalysisPayload.model_validate(
        {
            **payload.model_dump(mode="json"),
            "claims": [claim.model_dump(mode="json") for claim in claims],
            "evidence_ids": sorted(known_evidence),
            "source_ids": sorted(known_sources),
            "quality_flags": quality_flags,
        }
    )


def parse_composite_provider_payload(
    output_text: str,
    spec: CompositeWorkloadSpec,
    role: str,
    prepared_context: Mapping[str, Any] | None = None,
) -> CompositeAnalysisPayload:
    """Parse and validate one provider final response before publication."""

    try:
        normalized = _normalize_json_text(output_text)
        raw = json.loads(normalized)
        if isinstance(raw, dict) and isinstance(raw.get("subreports"), dict):
            expanded_subreports: list[dict[str, Any]] = []
            for key, value in raw["subreports"].items():
                parts = key.split("|", 2)
                if len(parts) != 3 or not isinstance(value, dict):
                    expanded_subreports.append({"invalid_subreport_key": key})
                    continue
                expanded_subreports.append(
                    {
                        **value,
                        "issuer": parts[0],
                        "period": parts[1],
                        "task": parts[2],
                    }
                )
            raw["subreports"] = expanded_subreports
        payload = CompositeAnalysisPayload.model_validate(raw)
    except OpenAITransportError:
        raise
    except ValidationError as exc:
        locations = sorted(
            {
                ".".join(str(part) for part in error.get("loc", ()))
                for error in exc.errors()
            }
        )
        error_types = sorted({str(error.get("type", "unknown")) for error in exc.errors()})
        diagnostics = (
            f"validation_error_count={len(exc.errors())}",
            "validation_locs=" + ",".join(locations[:8]),
            "validation_types=" + ",".join(error_types[:8]),
        )
        raise OpenAITransportError(("provider_payload_schema_invalid", *diagnostics)) from exc
    except (TypeError, ValueError) as exc:
        raise OpenAITransportError(("provider_payload_schema_invalid",)) from exc
    # Large workloads can exceed the provider's structured-output budget when
    # every task reference is emitted verbatim. In compact v3 mode the model
    # may emit one canonical data slice per issuer-period and omit some or all
    # task references; these references are a deterministic expansion, not
    # generated financial facts or an answer repair. Existing subreports are
    # preserved and only missing references backed by a data slice are added.
    if payload.data_slices:
        allowed_tasks = _role_task_values(spec, role)
        subreports = list(payload.subreports)
        existing_keys = {
            (item.issuer, item.period, item.task.value) for item in subreports
        }
        for data_slice in payload.data_slices:
            if data_slice.ticker is None:
                continue
            for task in allowed_tasks:
                key = (data_slice.ticker, data_slice.period, task)
                if key in existing_keys:
                    continue
                subreports.append(
                    CompositeSubreport(
                        issuer=data_slice.ticker,
                        period=data_slice.period,
                        task=AnalysisTask(task),
                        payload_ref=f"{data_slice.ticker}|{data_slice.period}",
                        status=data_slice.status,
                        observation_ids=tuple(data_slice.observation_ids),
                        source_ids=tuple(data_slice.source_ids),
                        evidence_ids=tuple(item.evidence_id for item in data_slice.evidence),
                    )
                )
                existing_keys.add(key)
        payload = payload.model_copy(update={"subreports": tuple(subreports)})
    # The orchestrator is a synthesis boundary, not a second data-entry
    # worker.  On larger workloads the model can correctly synthesize claims
    # while returning an empty compact subreport list.  When the prepared
    # context contains already validated worker payloads, assemble the
    # canonical task references deterministically here.  This preserves the
    # full-coverage invariant without asking the model to retype 120 objects
    # that already exist in the worker outputs.
    if role == "orchestrator" and prepared_context:
        payload = _assemble_orchestrator_from_workers(payload, spec, prepared_context)
    payload = _normalize_claim_provenance(payload)
    return _validate_composite_payload(payload, spec, role)


class OpenAICompositeTransport:
    """Run one bounded Responses API tool loop for a composite workload."""

    def __init__(
        self,
        client: CompositeResponsesClient,
        db_path: Any,
        max_tool_calls: int = 32,
    ) -> None:
        self.client = client
        self.db_path = db_path
        self.max_tool_calls = max_tool_calls

    def complete_composite(
        self,
        spec: CompositeWorkloadSpec,
        role: str,
        rendered_prompt: str,
        config: ProviderExecutionConfig,
        prepared_context: Mapping[str, Any] | None = None,
    ) -> CompositeProviderResponse:
        runtime = GoldToolRuntime(
            self.db_path,
            tickers=spec.issuers,
            periods=spec.periods,
            metric_ids=spec.metric_ids,
            macro_indicator_ids=spec.macro_indicator_ids,
            peer_tickers=spec.peer_tickers,
            source_policy_id=config.source_policy_id,
            composite_tools=True,
        )
        tools = runtime.definitions(role)
        tool_names = {tool["name"] for tool in tools}
        input_items: list[Any] = [{"role": "user", "content": rendered_prompt}]
        traces: list[AgentToolCall] = []
        tool_results: list[dict[str, Any]] = []
        input_tokens = 0
        output_tokens = 0
        peak_context_chars = 0
        json_repair_attempts = 0
        started = monotonic()
        try:
            for _ in range(min(self.max_tool_calls, config.max_tool_calls) + 1):
                context_chars = _estimated_context_chars(input_items)
                peak_context_chars = max(peak_context_chars, context_chars)
                if context_chars > config.max_context_chars:
                    raise OpenAITransportError(
                        (
                            "context_budget_exceeded",
                            f"context_chars={context_chars}",
                            f"context_budget_chars={config.max_context_chars}",
                        )
                    )
                request_kwargs: dict[str, Any] = {
                    "model": config.model_id,
                    "input": input_items,
                    "tools": tools,
                    "text": {
                        "format": {
                            "type": "json_schema",
                            "name": "composite_analysis_payload",
                            "strict": True,
                            "schema": _composite_response_schema(spec, role),
                        }
                    },
                    "max_output_tokens": config.max_output_tokens,
                    "parallel_tool_calls": False,
                }
                if config.model_id.startswith("gpt-5"):
                    request_kwargs["reasoning"] = {"effort": config.reasoning_effort}
                if not config.model_id.startswith("gpt-5"):
                    request_kwargs["temperature"] = config.temperature
                response = self.client.responses.create(**request_kwargs)
                usage = _value(response, "usage")
                input_tokens += int(_value(usage, "input_tokens", 0) or 0)
                output_tokens += int(_value(usage, "output_tokens", 0) or 0)
                output_items = list(_value(response, "output", []) or [])
                input_items.extend(output_items)
                function_calls = [
                    item for item in output_items if _value(item, "type") == "function_call"
                ]
                if not function_calls:
                    output_text = _value(response, "output_text")
                    if not isinstance(output_text, str) or not output_text.strip():
                        raise OpenAITransportError(
                            ("provider_output_text_missing",)
                            + _safe_response_diagnostics(response, output_text)
                        )
                    try:
                        payload = parse_composite_provider_payload(
                            output_text,
                            spec,
                            role,
                            prepared_context=prepared_context,
                        )
                    except OpenAITransportError as exc:
                        if exc.blockers != ("provider_output_json_invalid",) or json_repair_attempts >= 1:
                            if exc.blockers == ("provider_output_json_invalid",):
                                raise OpenAITransportError(
                                    exc.blockers + _safe_response_diagnostics(response, output_text)
                                ) from exc
                            raise
                        json_repair_attempts += 1
                        input_items.append(
                            {
                                "role": "user",
                                "content": "The previous final response was not valid JSON. Return only the requested CompositeAnalysisPayload JSON object, with no markdown, prose, or code fence.",
                            }
                        )
                        continue
                    telemetry = AgentCallTelemetry(
                        status="provided",
                        latency_ms=(monotonic() - started) * 1000,
                        input_tokens=input_tokens,
                        output_tokens=output_tokens,
                        cost_estimate=(
                            input_tokens * 0.20 / 1_000_000
                            + output_tokens * 1.20 / 1_000_000
                            if input_tokens or output_tokens
                            else None
                        ),
                        context_chars=peak_context_chars,
                        context_budget_chars=config.max_context_chars,
                    )
                    return CompositeProviderResponse(
                        payload=payload,
                        telemetry=telemetry,
                        effective_context={"results": tool_results},
                        tool_calls=tuple(traces),
                        role=role,
                    )

                for item in function_calls:
                    name = _value(item, "name")
                    arguments_text = _value(item, "arguments", "{}")
                    call_id = _value(item, "call_id")
                    if not isinstance(name, str) or name not in tool_names:
                        raise OpenAITransportError(("tool_not_allowed",))
                    try:
                        arguments = json.loads(arguments_text)
                        execution = runtime.execute(role, name, arguments)
                    except ToolExecutionError as exc:
                        safe_error = {"error": "tool_query_rejected", "reason": str(exc)}
                        encoded_error = json.dumps(safe_error, sort_keys=True)
                        safe_arguments = arguments if isinstance(arguments, dict) else {}
                        rejected_trace = AgentToolCall(
                            name=name,
                            arguments=safe_arguments,
                            result_sha256=sha256(encoded_error.encode("utf-8")).hexdigest(),
                            status="rejected",
                        )
                        traces.append(rejected_trace)
                        tool_results.append(
                            {
                                "tool_name": name,
                                "arguments": safe_arguments,
                                "output": safe_error,
                                "result_sha256": rejected_trace.result_sha256,
                            }
                        )
                        input_items.append(
                            {
                                "type": "function_call_output",
                                "call_id": call_id,
                                "output": encoded_error,
                            }
                        )
                        continue
                    except (json.JSONDecodeError, TypeError, ValueError) as exc:
                        raise OpenAITransportError(
                            (f"tool_call_rejected:{name}:{exc.__class__.__name__}",)
                        ) from exc
                    encoded_output = json.dumps(
                        execution.output,
                        ensure_ascii=False,
                        sort_keys=True,
                        separators=(",", ":"),
                        allow_nan=False,
                    )
                    traces.append(execution.trace)
                    tool_results.append(
                        {
                            "tool_name": name,
                            "arguments": execution.trace.arguments,
                            "output": execution.output,
                            "result_sha256": sha256(encoded_output.encode("utf-8")).hexdigest(),
                        }
                    )
                    input_items.append(
                        {
                            "type": "function_call_output",
                            "call_id": call_id,
                            "output": encoded_output,
                        }
                    )
                if len(traces) >= min(self.max_tool_calls, config.max_tool_calls):
                    raise OpenAITransportError(("tool_call_budget_exhausted",))
        except OpenAITransportError:
            raise
        except Exception as exc:
            details = [f"provider_request_failed:{exc.__class__.__name__}"]
            for attribute in ("status_code", "code", "type", "param"):
                value = getattr(exc, attribute, None)
                if value is not None and isinstance(value, (str, int, float, bool)):
                    details.append(f"{attribute}={value}")
            body = getattr(exc, "body", None)
            if isinstance(body, dict) and isinstance(body.get("error"), dict):
                for attribute in ("code", "type", "param"):
                    value = body["error"].get(attribute)
                    if value is not None and isinstance(value, (str, int, float, bool)):
                        detail = f"{attribute}={value}"
                        if detail not in details:
                            details.append(detail)
            raise OpenAITransportError(tuple(details)) from exc
        raise OpenAITransportError(("provider_output_incomplete",))
