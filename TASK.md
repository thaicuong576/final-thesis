# TASK: [THES-11] Set up OpenAI-Compatible LLM Client for Codely deepseek-v4.1-flash

## Linear Ticket
- Identifier: `THES-11`
- URL: `https://linear.app/eddiephung/issue/THES-11/featapi-thes-11-set-up-openai-compatible-llm-client-for-codely`
- Role: `worker-api` (Backend & AI Integration Specialist)
- Worktree: `D:\eddie-projects\personal-projects\final-thesis\.worktrees\feat-THES-11-setup-openai-llm-client`

---

## Context & Architecture
The user is integrating `deepseek-v4.1-flash` hosted on Codely Pixverse (`https://superup.codelypixverse.com/v1`).
Key requirements:
1. **OpenAI-Compatible Abstraction**: All LLM interactions must use standard OpenAI SDK protocols (`openai.OpenAI(base_url=..., api_key=...)`) so that switching between Codely Pixverse, official OpenAI (`api.openai.com/v1`), official DeepSeek (`api.deepseek.com/v1`), or local vLLM/Ollama requires ZERO code changes—only environment variables (`OPENAI_BASE_URL`, `OPENAI_MODEL`, `OPENAI_API_KEY`).
2. **Tool Calling & Function Calling Support**: The client factory and execution helper must handle standard OpenAI function calling schemas (`tools=[{"type": "function", "function": {...}}]`) and tool call responses (`choices[0].message.tool_calls`), including multi-turn tool result loops.
3. **Graceful Degradation**: If `OPENAI_API_KEY` is not configured, API calls or health checks must fail gracefully with descriptive error codes rather than crashing the server.

---

## Action Items
1. **Settings & Environment**:
   - In `src/thesis_api/settings.py`:
     - Add `openai_base_url: str = Field(default="https://superup.codelypixverse.com/v1", alias="OPENAI_BASE_URL")`
     - Add `openai_model: str = Field(default="deepseek-v4.1-flash", alias="OPENAI_MODEL")`
     - Ensure `openai_api_key: str | None = Field(default=None, alias="OPENAI_API_KEY")` is present.
   - In `.env.example`:
     - Document `OPENAI_BASE_URL`, `OPENAI_MODEL`, `OPENAI_API_KEY`.
   - In `render.yaml`:
     - Add `OPENAI_BASE_URL` and `OPENAI_MODEL` to `envVars`.
   - In `requirements-render.txt`:
     - Add `openai>=1.50.0,<3.0.0`.

2. **LLM Client & Tool Calling Infrastructure**:
   - Create `src/thesis_api/llm.py`:
     - `get_llm_client(settings: Settings | None = None) -> openai.OpenAI`
     - `get_llm_config(settings: Settings | None = None) -> dict[str, Any]`
     - Tool calling helper functions supporting OpenAI tool definitions and result formatting.

3. **Demonstration & Verification Probe**:
   - Create `scripts/probe_llm.py`:
     - Standalone script demonstrating:
       1. Instantiating OpenAI client with configured `base_url` and `model`.
       2. Simple chat completion test.
       3. Tool calling execution test with mock/live verification.

4. **Testing (Rule 19 - Zero-Failure)**:
   - Create `tests/test_llm.py`:
     - Test `get_llm_client` returns valid OpenAI instance.
     - Test environment variable overrides for `OPENAI_BASE_URL` and `OPENAI_MODEL`.
     - Test tool calling handling and error states when API key is missing.
   - Run backend test suite:
     `python -c "import sys; sys.path.insert(0, 'src'); import unittest; unittest.main(module='tests.test_llm', argv=['unittest', '-v'])"`
     `python -c "import sys; sys.path.insert(0, 'src'); import unittest; unittest.main(module='tests.test_thesis_api', argv=['unittest', '-v'])"`

5. **PR & Verification Loop**:
   - Commit: `feat(api): [THES-11] set up OpenAI-compatible LLM client for Codely deepseek-v4.1-flash`
   - Push branch `feat/THES-11-setup-openai-llm-client`.
   - Open PR to `main` citing `[THES-11]`.
   - Verify 100% CI/CD checks pass (`gh pr checks`).
