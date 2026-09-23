# TASK: [THES-12] Implement Dynamic Multi-Agent Cognitive Loop with DeepSeek Tool Calling

## Linear Ticket
- Identifier: `THES-12`
- URL: `https://linear.app/eddiephung/issue/THES-12/featapi-thes-12-implement-dynamic-multi-agent-cognitive-loop-with`
- Role: `worker-api` (Backend & Multi-Agent Specialist)
- Worktree: `D:\eddie-projects\personal-projects\final-thesis\.worktrees\feat-THES-12-dynamic-multi-agent-loop`

---

## Architectural Guardrails & Spec Zero Alignment
1. **Rule 3**: *"Code computes financial metrics; language models retrieve, explain, critique, and synthesize."*
   - LLMs **never hallucinate or guess** financial numbers. All metrics (`roe`, `nim`, `npl`, `car`, `casa`, `ldr`) are retrieved from the canonical SQLite database (`finance_master_v2.sqlite`) via structured Tool Calling (`get_company_metrics`, `get_sector_benchmarks`, `get_macro_context`).
2. **Two-Stage Quality Boundary** (`.agent/foundation/03-system-architecture.md` Section 5):
   - **Stage 1**: Deterministic Acceptance (100% Python code checking arithmetic accuracy, evidence references, and database provenance).
   - **Stage 2**: Semantic Critique & Bounded Revision (LLM evaluates cross-level coherence, paradox detection, and limits revisions to $\le 2$ rounds).
3. **SSE Streaming Contract** (`contracts/openapi.json`):
   - Preserves all event types subscribed by Screen 2 (`AnalysisSessionWorkspace.tsx`):
     - `USER_REQUEST_CONFIRMED`
     - `PLAN_CREATED`
     - `SPECIALIST_ACTIVATED`
     - `SPECIALIST_ACTIVITY`
     - `SPECIALIST_OUTPUT_CREATED`
     - `SPECIALIST_COMPLETED`
     - `REVIEW_STARTED`
     - `REVIEW_FEEDBACK_CREATED`
     - `REVISION_REQUESTED`
     - `REVISION_ACTIVITY`
     - `REVISION_COMPLETED`
     - `SYNTHESIS_STARTED`
     - `REPORT_READY`
4. **Graceful Fallback**:
   - If the LLM API call fails, times out, or has no key configured, the system falls back seamlessly to the deterministic baseline engine so the user experience is never interrupted.

---

## Action Items
1. **`src/thesis_api/agent_tools.py`**:
   - Implement OpenAI-compatible function calling schemas:
     - `TOOL_GET_COMPANY_METRICS`: `{"ticker": str, "period": str, "kpis": list[str]}`
     - `TOOL_GET_SECTOR_BENCHMARKS`: `{"sector": str, "period": str, "tickers": list[str], "kpis": list[str]}`
     - `TOOL_GET_MACRO_CONTEXT`: `{"period": str, "indicators": list[str]}`
   - Implement `execute_agent_tool(tool_name: str, args: dict, conn: sqlite3.Connection) -> dict[str, Any]` querying `finance_master_v2.sqlite`.

2. **`src/thesis_api/agents.py`**:
   - Implement `OrchestratorAgent`: Formulates query intent, dynamic plan, and capability activation with LLM reasoning.
   - Implement `CompanySpecialistAgent`: Invokes `get_company_metrics` tool, computes CAMEL breakdown, and returns grounded analytical findings.
   - Implement `SectorSpecialistAgent`: Invokes `get_sector_benchmarks` tool, analyzes competitive positioning against peer medians.
   - Implement `MacroSpecialistAgent`: Invokes `get_macro_context` tool, analyzes monetary policy transmission.
   - Implement `SemanticCriticAgent`: Checks cross-level consistency between company micro and sector/macro data, detects paradoxes, determines `ACCEPT` or `REVISE` (bounded revision $\le 2$ rounds).

3. **`src/thesis_api/service.py`**:
   - Upgrade `stream_analysis_query`:
     - If LLM client is configured:
       - Run Orchestrator dynamic plan -> emit `USER_REQUEST_CONFIRMED` & `PLAN_CREATED`.
       - For each capability:
         - Emit `SPECIALIST_ACTIVATED`.
         - When agent calls tools, emit `SPECIALIST_ACTIVITY` with real tool name and arguments.
         - Emit `SPECIALIST_OUTPUT_CREATED` with real LLM findings.
         - Emit `SPECIALIST_COMPLETED`.
       - Run Stage-1 deterministic validation.
       - Run Stage-2 Semantic Critic:
         - Emit `REVIEW_STARTED`.
         - If critique requires revision: emit `REVIEW_FEEDBACK_CREATED`, `REVISION_REQUESTED`, `REVISION_ACTIVITY`, `REVISION_COMPLETED`.
       - Run Synthesis:
         - Emit `SYNTHESIS_STARTED`.
         - Emit `REPORT_READY` with verified SQLite metrics + LLM narrative insights and claims.
     - If unconfigured or on error:
       - Transparently fall back to the existing deterministic generator.

4. **Testing**:
   - Create `tests/test_agent_tools.py` verifying tool execution against SQLite.
   - Create `tests/test_agents.py` verifying agent prompt construction and mocked tool calling responses.
   - Run backend test suite:
     `python -c "import sys; sys.path.insert(0, 'src'); import unittest; unittest.main(module='tests.test_agent_tools', argv=['unittest', '-v'])"`
     `python -c "import sys; sys.path.insert(0, 'src'); import unittest; unittest.main(module='tests.test_agents', argv=['unittest', '-v'])"`
     `python -c "import sys; sys.path.insert(0, 'src'); import unittest; unittest.main(module='tests.test_thesis_api', argv=['unittest', '-v'])"`
     `python -c "import sys; sys.path.insert(0, 'src'); import unittest; unittest.main(module='tests.test_llm', argv=['unittest', '-v'])"`

5. **PR & Verification Loop**:
   - Commit: `feat(api): [THES-12] implement dynamic multi-agent cognitive loop with DeepSeek tool calling`
   - Push branch `feat/THES-12-dynamic-multi-agent-loop`.
   - Open PR to `main` citing `[THES-12]`.
   - Verify 100% CI/CD checks pass (`gh pr checks`).
