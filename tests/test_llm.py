"""Unit tests for OpenAI-compatible LLM client and utilities."""

from __future__ import annotations

import os
import unittest
from unittest.mock import MagicMock, patch
try:
    from socket_guard import install_socket_guard
except ImportError:
    from tests.socket_guard import install_socket_guard


def setUpModule() -> None:
    install_socket_guard()

import openai

from thesis_api.llm import (
    LLMConfigurationError,
    execute_chat,
    format_function_tool,
    format_tool_result,
    get_llm_client,
    get_llm_config,
)
from thesis_api.settings import Settings


class LLMClientTests(unittest.TestCase):
    """Test suite covering OpenAI-compatible LLM configuration, factory, and execution."""

    def test_default_config_values(self) -> None:
        """Test default config resolves to Codely Pixverse DeepSeek endpoint."""
        clean_env = {k: v for k, v in os.environ.items() if not k.startswith("OPENAI_")}
        with patch.dict(os.environ, clean_env, clear=True):
            settings = Settings(_env_file=None)
            config = get_llm_config(settings)
            self.assertEqual(config["base_url"], "https://superup.codelypixverse.com/v1")
            self.assertEqual(config["model"], "deepseek-v4-pro-0813")
            self.assertFalse(config["is_configured"])

    def test_settings_env_overrides(self) -> None:
        """Test environment variables properly override LLM settings."""
        env_patch = {
            "OPENAI_BASE_URL": "https://custom.openai.endpoint/v1",
            "OPENAI_MODEL": "custom-deepseek-model",
            "OPENAI_API_KEY": "sk-custom-test-key-987",
        }
        with patch.dict(os.environ, env_patch):
            settings = Settings()
            self.assertEqual(settings.openai_base_url, "https://custom.openai.endpoint/v1")
            self.assertEqual(settings.openai_model, "custom-deepseek-model")
            self.assertEqual(settings.openai_api_key, "sk-custom-test-key-987")

            config = get_llm_config(settings)
            self.assertEqual(config["base_url"], "https://custom.openai.endpoint/v1")
            self.assertEqual(config["model"], "custom-deepseek-model")
            self.assertTrue(config["is_configured"])

    def test_format_function_tool(self) -> None:
        """Test formatting of standard OpenAI function calling tool definition."""
        params = {
            "type": "object",
            "properties": {
                "ticker": {"type": "string", "description": "Stock ticker"},
                "limit": {"type": "integer", "description": "Max items"},
            },
            "required": ["ticker"],
        }
        tool = format_function_tool(
            name="get_stock_quote",
            description="Fetch stock quote for given ticker",
            parameters=params,
        )

        self.assertEqual(tool["type"], "function")
        self.assertIn("function", tool)
        self.assertEqual(tool["function"]["name"], "get_stock_quote")
        self.assertEqual(tool["function"]["description"], "Fetch stock quote for given ticker")
        self.assertEqual(tool["function"]["parameters"], params)
        self.assertNotIn("strict", tool["function"])

        # Test strict flag option
        tool_strict = format_function_tool(
            name="get_strict",
            description="Strict tool",
            parameters={},
            strict=True,
        )
        self.assertTrue(tool_strict["function"]["strict"])

    def test_format_tool_result(self) -> None:
        """Test tool execution result format for multi-turn conversations."""
        result_msg = format_tool_result(
            tool_call_id="call_abc123",
            content='{"price": 95000, "currency": "VND"}',
        )
        self.assertEqual(result_msg["role"], "tool")
        self.assertEqual(result_msg["tool_call_id"], "call_abc123")
        self.assertEqual(result_msg["content"], '{"price": 95000, "currency": "VND"}')

    def test_get_llm_client_missing_key_raises_error(self) -> None:
        """Test client instantiation without API key raises LLMConfigurationError."""
        clean_env = {k: v for k, v in os.environ.items() if not k.startswith("OPENAI_")}
        with patch.dict(os.environ, clean_env, clear=True):
            settings = Settings(_env_file=None, openai_api_key=None)
            with self.assertRaises(LLMConfigurationError) as ctx:
                get_llm_client(settings)
            self.assertIn("OPENAI_API_KEY is not configured", str(ctx.exception))

    def test_get_llm_client_initialization_with_custom_settings(self) -> None:
        """Test client properly initialized with custom base_url and api_key."""
        settings = Settings(
            openai_base_url="https://custom.provider.com/v1",
            openai_api_key="sk-test-client-key",
        )
        client = get_llm_client(settings)
        self.assertIsInstance(client, openai.OpenAI)
        self.assertEqual(client.api_key, "sk-test-client-key")
        self.assertEqual(str(client.base_url).rstrip("/"), "https://custom.provider.com/v1")

    def test_get_llm_client_explicit_kwarg_overrides(self) -> None:
        """Test explicit kwargs override settings."""
        settings = Settings(
            openai_base_url="https://settings.provider.com/v1",
            openai_api_key="sk-settings-key",
        )
        client = get_llm_client(
            settings,
            api_key="sk-override-key",
            base_url="https://override.provider.com/v1",
        )
        self.assertEqual(client.api_key, "sk-override-key")
        self.assertEqual(str(client.base_url).rstrip("/"), "https://override.provider.com/v1")

    def test_execute_chat_mocked_completion(self) -> None:
        """Test execute_chat wrapper correctly forwards messages and kwargs to OpenAI."""
        mock_client = MagicMock(spec=openai.OpenAI)
        mock_response = MagicMock()
        mock_response.choices = [
            MagicMock(message=MagicMock(content="Hello world", tool_calls=None))
        ]
        mock_client.chat.completions.create.return_value = mock_response

        messages = [
            {"role": "system", "content": "You are a financial analyst."},
            {"role": "user", "content": "Explain NIM."},
        ]

        result = execute_chat(
            client=mock_client,
            model="deepseek-v4.1-flash",
            messages=messages,
            temperature=0.2,
        )

        self.assertEqual(result, mock_response)
        mock_client.chat.completions.create.assert_called_once_with(
            model="deepseek-v4.1-flash",
            messages=messages,
            temperature=0.2,
        )

    def test_execute_chat_with_tools_mocked(self) -> None:
        """Test execute_chat with tools properly forwards tool schemas and captures tool calls."""
        mock_client = MagicMock(spec=openai.OpenAI)
        mock_tool_call = MagicMock()
        mock_tool_call.id = "call_xyz789"
        mock_tool_call.function.name = "calculate_camels"
        mock_tool_call.function.arguments = '{"ticker": "VCB", "year": 2024}'

        mock_choice = MagicMock()
        mock_choice.message.content = None
        mock_choice.message.tool_calls = [mock_tool_call]

        mock_response = MagicMock()
        mock_response.choices = [mock_choice]
        mock_client.chat.completions.create.return_value = mock_response

        tools = [
            format_function_tool(
                name="calculate_camels",
                description="Calculate CAMEL ratios",
                parameters={"type": "object", "properties": {"ticker": {"type": "string"}}},
            )
        ]
        messages = [{"role": "user", "content": "Calculate CAMEL ratios for VCB"}]

        result = execute_chat(
            client=mock_client,
            model="deepseek-v4.1-flash",
            messages=messages,
            tools=tools,
        )

        self.assertEqual(result, mock_response)
        mock_client.chat.completions.create.assert_called_once_with(
            model="deepseek-v4.1-flash",
            messages=messages,
            tools=tools,
        )
        tool_calls = result.choices[0].message.tool_calls
        self.assertEqual(len(tool_calls), 1)
        self.assertEqual(tool_calls[0].function.name, "calculate_camels")
        self.assertEqual(tool_calls[0].function.arguments, '{"ticker": "VCB", "year": 2024}')


if __name__ == "__main__":
    unittest.main()
