"""OpenAI-compatible LLM client factory, configuration, and execution helpers."""

from __future__ import annotations

from typing import Any
import openai

from thesis_api.settings import Settings, get_settings


class LLMConfigurationError(ValueError):
    """Raised when LLM client configuration is invalid or missing required credentials."""


def get_llm_config(settings: Settings | None = None) -> dict[str, Any]:
    """Return LLM configuration metadata safe for public inspection (no secrets).

    Args:
        settings: Application settings. If None, loaded via get_settings().

    Returns:
        dict containing 'base_url', 'model', and 'is_configured'.
    """
    cfg = settings or get_settings()
    is_configured = bool(cfg.openai_api_key and cfg.openai_api_key.strip())
    return {
        "base_url": cfg.openai_base_url,
        "model": cfg.openai_model,
        "is_configured": is_configured,
    }


def get_llm_client(
    settings: Settings | None = None,
    *,
    api_key: str | None = None,
    base_url: str | None = None,
) -> openai.OpenAI:
    """Create and return an OpenAI-compatible client instance.

    Args:
        settings: Application settings. If None, loaded via get_settings().
        api_key: Optional explicit API key override.
        base_url: Optional explicit base URL override.

    Returns:
        Configured openai.OpenAI client instance.

    Raises:
        LLMConfigurationError: If no API key is configured.
    """
    cfg = settings or get_settings()
    effective_key = api_key if api_key is not None else cfg.openai_api_key
    effective_url = base_url if base_url is not None else cfg.openai_base_url

    if not effective_key or not effective_key.strip():
        raise LLMConfigurationError(
            "OPENAI_API_KEY is not configured. Please set the OPENAI_API_KEY "
            "environment variable or pass an explicit api_key."
        )

    return openai.OpenAI(
        base_url=effective_url,
        api_key=effective_key.strip(),
    )


def format_function_tool(
    name: str,
    description: str,
    parameters: dict[str, Any],
    *,
    strict: bool | None = None,
) -> dict[str, Any]:
    """Format a function tool definition conforming to the OpenAI JSON schema.

    Args:
        name: The name of the function to be called.
        description: A description of what the function does.
        parameters: The parameters the function accepts, described as a JSON Schema object.
        strict: Whether to enable strict schema adherence.

    Returns:
        OpenAI-compatible tool dictionary with type='function'.
    """
    fn: dict[str, Any] = {
        "name": name,
        "description": description,
        "parameters": parameters,
    }
    if strict is not None:
        fn["strict"] = strict

    return {
        "type": "function",
        "function": fn,
    }


def format_tool_result(tool_call_id: str, content: str) -> dict[str, Any]:
    """Format a tool execution result message for multi-turn conversation loops.

    Args:
        tool_call_id: The ID of the tool call being answered.
        content: The result content string (usually serialized JSON).

    Returns:
        OpenAI-compatible message dict with role='tool'.
    """
    return {
        "role": "tool",
        "tool_call_id": tool_call_id,
        "content": content,
    }


def execute_chat(
    client: openai.OpenAI,
    model: str,
    messages: list[dict[str, Any]],
    tools: list[dict[str, Any]] | None = None,
    **kwargs: Any,
) -> Any:
    """Execute a chat completion request using the OpenAI client.

    Args:
        client: Configured openai.OpenAI client instance.
        model: Target model name (e.g., deepseek-v4.1-flash).
        messages: Conversation history / message list.
        tools: Optional list of OpenAI-compatible function tool specifications.
        **kwargs: Additional parameters forwarded to chat.completions.create.

    Returns:
        ChatCompletion response object from the provider.
    """
    call_kwargs: dict[str, Any] = {
        "model": model,
        "messages": messages,
        **kwargs,
    }
    if tools:
        call_kwargs["tools"] = tools

    return client.chat.completions.create(**call_kwargs)
