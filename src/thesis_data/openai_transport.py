"""OpenAI Responses API transport for the closed-world tool-calling arm."""

from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
import json
from time import monotonic
from typing import Any, Protocol

from .agent_runtime import AgentCallRequest, AgentCallTelemetry, AgentToolCall
from .agent_tools import GoldToolRuntime, ToolExecutionError
from .provider_adapter import ProviderResponse
from .provider_config import ProviderExecutionConfig
from .schema import AgentPayload
from .transport_errors import OpenAITransportError


class ResponsesClient(Protocol):
    class responses(Protocol):  # type: ignore[valid-type]
        @staticmethod
        def create(**kwargs: Any) -> Any: ...


def _value(item: Any, key: str, default: Any = None) -> Any:
    if isinstance(item, dict):
        return item.get(key, default)
    return getattr(item, key, default)


def _strict_schema(schema: dict[str, Any]) -> dict[str, Any]:
    """Make Pydantic's schema compatible with strict structured outputs."""

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


def _response_schema(request: AgentCallRequest) -> dict[str, Any]:
    """Build a strict schema with fixed metric keys for OpenAI's subset."""

    schema = _strict_schema(AgentPayload.model_json_schema())
    metric_keys = (
        tuple(request.macro_indicator_ids)
        if request.role == "macro"
        else tuple(dict.fromkeys(request.metric_ids))
    )
    number_or_null = {"anyOf": [{"type": "number"}, {"type": "null"}]}
    string_map = {
        "type": "object",
        "properties": {key: {"type": "string"} for key in metric_keys},
        "required": list(metric_keys),
        "additionalProperties": False,
    }
    numeric_map = {
        "type": "object",
        "properties": {key: number_or_null for key in metric_keys},
        "required": list(metric_keys),
        "additionalProperties": False,
    }
    properties = schema.get("properties", {})
    properties["agent_id"] = {"type": "string", "enum": [request.role]}
    properties["period"] = {"type": "string", "enum": [request.period]}
    properties["ticker"] = {
        "anyOf": [
            {"type": "string", "enum": [request.ticker]},
            {"type": "null"},
        ]
    }
    properties["metrics"] = numeric_map
    properties["metric_units"] = string_map
    properties["metric_periods"] = {
        "type": "object",
        "properties": {
            key: {"type": "string", "enum": list(request.periods or (request.period,))}
            for key in metric_keys
        },
        "required": list(metric_keys),
        "additionalProperties": False,
    }
    properties["sector_benchmarks"] = numeric_map
    schema["properties"] = properties
    schema["required"] = list(properties)
    return schema


def _normalize_json_text(output_text: str) -> str:
    """Accept only a JSON object, tolerating a harmless markdown fence."""

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


@dataclass
class OpenAIResponsesTransport:
    client: ResponsesClient
    db_path: Any
    peer_tickers: tuple[str, ...]
    max_tool_calls: int = 8

    def complete_composite(
        self,
        spec: Any,
        role: str,
        rendered_prompt: str,
        config: ProviderExecutionConfig,
    ) -> Any:
        """Delegate composite workloads to the typed composite transport."""

        from .composite_transport import OpenAICompositeTransport

        return OpenAICompositeTransport(
            self.client,
            self.db_path,
            max_tool_calls=self.max_tool_calls,
        ).complete_composite(spec, role, rendered_prompt, config)

    def complete(
        self,
        request: AgentCallRequest,
        rendered_prompt: str,
        config: ProviderExecutionConfig,
    ) -> ProviderResponse:
        runtime = GoldToolRuntime(
            self.db_path,
            ticker=request.ticker,
            periods=request.periods or (request.period,),
            metric_ids=request.metric_ids,
            macro_indicator_ids=request.macro_indicator_ids,
            peer_tickers=request.peer_tickers or self.peer_tickers,
            source_policy_id=config.source_policy_id,
        )
        tools = runtime.definitions(request.role)
        input_items: list[Any] = [{"role": "user", "content": rendered_prompt}]
        traces: list[AgentToolCall] = []
        tool_results: list[dict[str, Any]] = []
        input_tokens = 0
        output_tokens = 0
        json_repair_attempts = 0
        started = monotonic()
        response: Any = None
        try:
            for _ in range(min(self.max_tool_calls, config.max_tool_calls) + 1):
                request_kwargs: dict[str, Any] = {
                    "model": config.model_id,
                    "input": input_items,
                    "tools": tools,
                    "text": {
                        "format": {
                            "type": "json_schema",
                            "name": "agent_payload",
                            "strict": True,
                            "schema": _response_schema(request),
                        }
                    },
                    "max_output_tokens": config.max_output_tokens,
                    "parallel_tool_calls": False,
                }
                # GPT-5 reasoning models use reasoning configuration rather than
                # the legacy temperature control; omit temperature from the request.
                if config.model_id.startswith("gpt-5"):
                    request_kwargs["reasoning"] = {"effort": config.reasoning_effort}
                else:
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
                        raise OpenAITransportError(("provider_output_text_missing",))
                    try:
                        normalized_output = _normalize_json_text(output_text)
                    except OpenAITransportError:
                        if json_repair_attempts >= 1:
                            raise
                        json_repair_attempts += 1
                        input_items.append(
                            {
                                "role": "user",
                                "content": "The previous final response was not valid JSON. Return only the requested AgentPayload JSON object, with no markdown, prose, or code fence.",
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
                    )
                    return ProviderResponse(
                        payload=normalized_output,
                        telemetry=telemetry,
                        effective_context={"results": tool_results},
                        tool_calls=tuple(traces),
                    )
                for item in function_calls:
                    name = _value(item, "name")
                    arguments_text = _value(item, "arguments", "{}")
                    call_id = _value(item, "call_id")
                    if not isinstance(name, str) or name not in {tool["name"] for tool in tools}:
                        raise OpenAITransportError(("tool_not_allowed",))
                    try:
                        arguments = json.loads(arguments_text)
                        execution = runtime.execute(request.role, name, arguments)
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
                error_body = body["error"]
                for attribute in ("code", "type", "param"):
                    value = error_body.get(attribute)
                    if value is not None and isinstance(value, (str, int, float, bool)):
                        detail = f"{attribute}={value}"
                        if detail not in details:
                            details.append(detail)
            raise OpenAITransportError(tuple(details)) from exc
        raise OpenAITransportError(("provider_output_incomplete",))
