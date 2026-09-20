#!/usr/bin/env python3
"""CLI probe script to verify OpenAI-compatible LLM connectivity and tool calling.

Supports Codely Pixverse DeepSeek, official OpenAI, DeepSeek, or local providers.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

# Force UTF-8 on Windows consoles to safely display Vietnamese & Unicode
if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

# Ensure src is in Python path when run directly
repo_root = Path(__file__).resolve().parents[1]
src_dir = repo_root / "src"
if str(src_dir) not in sys.path:
    sys.path.insert(0, str(src_dir))

from thesis_api.llm import (
    LLMConfigurationError,
    execute_chat,
    format_function_tool,
    get_llm_client,
    get_llm_config,
)
from thesis_api.settings import Settings


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Probe OpenAI-compatible LLM connectivity and tool-calling support.",
    )
    parser.add_argument(
        "--prompt",
        type=str,
        default=None,
        help="Custom prompt to send to the model.",
    )
    parser.add_argument(
        "--with-tools",
        action="store_true",
        help="Enable tool-calling demonstration mode with sample financial tool schema.",
    )
    parser.add_argument(
        "--base-url",
        type=str,
        default=None,
        help="Override base URL (default from OPENAI_BASE_URL or Settings).",
    )
    parser.add_argument(
        "--model",
        type=str,
        default=None,
        help="Override model name (default from OPENAI_MODEL or Settings).",
    )
    parser.add_argument(
        "--api-key",
        type=str,
        default=None,
        help="Override API key (default from OPENAI_API_KEY or Settings).",
    )
    return parser.parse_args()


def run_probe() -> int:
    args = parse_args()

    # Load base settings and apply CLI overrides if provided
    settings = Settings()
    if args.base_url:
        settings.openai_base_url = args.base_url
    if args.model:
        settings.openai_model = args.model
    if args.api_key:
        settings.openai_api_key = args.api_key

    config = get_llm_config(settings)

    print("=" * 60)
    print("OpenAI-Compatible LLM Probe")
    print("=" * 60)
    print(f"Base URL      : {config['base_url']}")
    print(f"Model         : {config['model']}")
    print(f"Configured    : {config['is_configured']}")
    print("-" * 60)

    if not config["is_configured"]:
        print("[SKIP] OPENAI_API_KEY is not configured in .env or environment.")
        print("[INFO] Set OPENAI_API_KEY to test live completion connectivity.")
        print("[INFO] Probe finished (safe skip).")
        return 0

    try:
        client = get_llm_client(settings)
    except LLMConfigurationError as err:
        print(f"[ERROR] Configuration error: {err}")
        return 1

    model = config["model"]

    if args.with_tools:
        demo_tools = [
            format_function_tool(
                name="get_financial_kpi",
                description="Retrieve financial KPIs (NIM, NPL, CAR, ROE) for a Vietnamese bank ticker symbol.",
                parameters={
                    "type": "object",
                    "properties": {
                        "ticker": {
                            "type": "string",
                            "description": "Stock ticker symbol (e.g. VCB, MBB, TCB)",
                        },
                        "kpis": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "List of KPI metric names (e.g. ['NIM', 'NPL'])",
                        },
                    },
                    "required": ["ticker", "kpis"],
                },
            )
        ]
        prompt = args.prompt or "What are the latest NIM and NPL for Vietcombank (ticker VCB)? Please check using the tool."
        messages = [{"role": "user", "content": prompt}]

        print(f"[PROBE] Testing tool calling with prompt: {prompt!r}")
        try:
            response = execute_chat(
                client=client,
                model=model,
                messages=messages,
                tools=demo_tools,
            )
            choice = response.choices[0]
            if choice.message.tool_calls:
                print(f"[SUCCESS] Model invoked {len(choice.message.tool_calls)} tool call(s):")
                for tc in choice.message.tool_calls:
                    print(f"  - ID: {tc.id}")
                    print(f"    Function: {tc.function.name}")
                    print(f"    Arguments: {tc.function.arguments}")
            else:
                print(f"[SUCCESS] Model response: {choice.message.content}")
        except Exception as exc:
            print(f"[FAIL] Tool call request failed: {exc}")
            return 1
    else:
        prompt = args.prompt or "Hello! Confirm you are deepseek-v4.1-flash and reply with 'ONLINE'."
        messages = [{"role": "user", "content": prompt}]

        print(f"[PROBE] Testing chat completion with prompt: {prompt!r}")
        try:
            response = execute_chat(
                client=client,
                model=model,
                messages=messages,
            )
            reply = response.choices[0].message.content
            print(f"[SUCCESS] Model response: {reply}")
        except Exception as exc:
            print(f"[FAIL] Chat completion failed: {exc}")
            return 1

    print("=" * 60)
    print("[SUCCESS] LLM probe completed successfully.")
    return 0


if __name__ == "__main__":
    sys.exit(run_probe())
