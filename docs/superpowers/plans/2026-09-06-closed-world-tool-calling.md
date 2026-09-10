# Closed-world role-isolated tool-calling implementation plan

> This plan is executed in the current task after the user approved the
> closed-world function-tool design. Tests are written before implementation
> for each functional slice.

## Goal

Replace provider-backed prefetch-only dispatch with a real OpenAI Responses API
tool-calling loop over the promoted Gold snapshot, while preserving the
existing offline control, fail-closed contracts, missing-data policy, and
three-arm baseline experiment.

## Scope and invariants

- Exact provider/model: `openai` / `gpt-5.6-luna`.
- Dataset: `data/processed/gold-bank-2025-pilot-v1-adjudicated-v2.sqlite`.
- Source policy: `primary-only-v1`.
- Pilot plan: `experiments/runs/baseline-plan-core-gold-v1.json`, 13 questions ×
  3 arms = 39 jobs.
- No web search, live filings, arbitrary SQL, filesystem tools, DB writes, or
  secret persistence.
- Existing offline fixtures remain a prefetch control and must continue to pass.
- All model output still crosses `AgentPayload`; Python computes/validates data.
- Provider runs remain non-comparative until all jobs finish with valid
  telemetry and the evaluation report is generated.

## Task 1 — Define trace and completion extensions (TDD)

Files:

- `tests/test_agent_runtime.py`
- `tests/test_provider_adapter.py`
- `src/thesis_data/agent_runtime.py`
- `src/thesis_data/provider_adapter.py`

Steps:

1. Add tests proving a provider completion can return an effective provenance
   context and bounded tool-call records, while old adapters default to empty
   traces.
2. Add immutable `AgentToolCall` data with tool name, validated arguments,
   result hash, status, and result quality counts; reject secret/path fields in
   serialized trace data.
3. Extend `AgentCompletion` and `ProviderResponse` with optional effective
   context and tool-call trace fields.
4. Extend `RuntimeRunResult` with per-call effective contexts and tool calls.
5. Update dispatch to validate payload provenance against the effective context
   returned by the adapter, but retain the original request context for prompt
   and request hashing.
6. Preserve all existing adapter/runtime behavior and tests.

Verification: focused runtime/provider tests.

## Task 2 — Implement the read-only Gold tool registry (TDD)

Files:

- `tests/test_agent_tools.py` (new)
- `src/thesis_data/agent_tools.py` (new)

Steps:

1. Build typed argument models for company metrics, sector benchmarks, macro
   context, evidence, source metadata, and missing/conflict checks.
2. Implement `GoldToolRuntime` with a read-only DB path, frozen ticker/period/
   metric/macro scope, and source-tier resolution from the run policy.
3. Delegate metric/evidence retrieval to existing query functions.
4. Implement source metadata and missing/conflict checks with parameterized,
   read-only SQL against the Gold schema; return explicit states rather than
   guessing or filling values.
5. Add deterministic role registries and strict tool definitions for the
   Responses API. Tool schemas must have `additionalProperties: false` and
   `strict: true`.
6. Reject out-of-scope arguments, unknown tool names, empty lists, excessive
   list sizes, and tools not allowed for the current role.
7. Serialize tool results as JSON-safe values with stable ordering and no raw
   local paths or source secrets.

Verification: tool unit tests against a small SQLite fixture covering valid,
missing, pending, conflicting, and macro cases.

## Task 3 — Make prompts tool-aware without weakening the offline control

Files:

- `tests/test_prompting.py`
- `src/thesis_data/prompting.py`
- `src/thesis_data/agent_runtime.py`

Steps:

1. Add a tool-calling prompt mode that states the closed-world boundary,
   missing-data policy, role responsibility, tool-use requirement, and exact
   output contract.
2. Keep the current prepared-context prompt mode for offline fixtures and the
   explicit prefetch control.
3. Add an adapter capability check so tool-calling adapters receive request
   scope and an empty/minimal context instead of the full prefetched facts.
4. Keep question binding, periods, metrics, and macro indicators in the frozen
   request scope.

Verification: prompt tests prove provider mode does not serialize company
facts/evidence before a tool call, while offline mode remains byte-stable.

## Task 4 — Implement the OpenAI Responses function-calling transport (TDD)

Files:

- `tests/test_openai_transport.py` (new)
- `src/thesis_data/openai_transport.py` (new)
- `src/thesis_data/provider_config.py`
- `src/thesis_data/provider_adapter.py`

Steps:

1. Add a fake Responses client in tests that emits function calls followed by a
   final JSON response.
2. Implement an injectable client protocol so unit tests never need network or
   a real key.
3. Implement `OpenAIResponsesTransport` using `client.responses.create` with
   exact model ID, role-specific function tools, strict final JSON schema, and
   configured timeout/token settings.
4. Implement the loop: inspect response output, execute only validated local
   calls, append `response.output` and `function_call_output`, repeat up to a
   bounded call budget, then parse `output_text`.
5. Hash tool results and record per-call trace/quality counts; preserve all tool
   outputs in effective context for provenance validation.
6. Extract provider usage and elapsed time into `AgentCallTelemetry`; estimate
   cost using the model configuration and recorded token counts, with null cost
   if usage is unavailable.
7. Map all provider/SDK errors to secret-safe `ProviderAdapterError` blockers.
8. Add config fields for retrieval mode and maximum tool calls with validation.

Verification: focused fake-client tests for happy path, invalid tool,
out-of-scope args, final-schema failure, budget exhaustion, provider failure,
telemetry handling, and no-secret trace output.

## Task 5 — Persist tool traces in experiment manifests (TDD)

Files:

- `tests/test_run_manifest.py`
- `src/thesis_data/run_manifest.py`

Steps:

1. Add a versioned `RunToolCallTrace` manifest model.
2. Record tool name, role, sanitized arguments, result hash, status, and quality
   counts for every model tool call.
3. Include effective tool provenance IDs in manifest input IDs and hashes.
4. Preserve schema compatibility for existing offline manifests by defaulting to
   an empty trace list.
5. Ensure manifest serialization never includes API keys, environment values,
   absolute DB paths, raw exception text, or full unbounded tool output.

Verification: manifest tests for offline compatibility and provider trace
serialization.

## Task 6 — Add provider config, secret loader, smoke runner, and full runner

Files:

- `experiments/config/openai-gpt-5.6-luna.json` (new, secret-free)
- `scripts/run_openai_baseline.py` (new)
- `tests/test_run_openai_baseline.py` (new)
- `.gitignore`

Steps:

1. Add a committed config referencing only the external env-var name and
   exact model ID; keep provider output directories ignored.
2. Implement a secret loader that reads only the user-authorized external
   `.env` file, supports `OPENAI_API_KEY`, never prints the value, and only
   places it in the child process environment/client constructor.
3. Require an explicit `--smoke-question-id` for the one-question smoke run;
   write smoke output separately and never mark it comparative.
4. Add the full-run mode that executes the existing 39-job plan into a new
   empty provider output directory, with the same Gold/config gates.
5. Refuse to overwrite output, run with a different model, use a missing key,
   or silently substitute a model/provider.
6. Ensure the script can run from the repo root without installing project code
   into the environment beyond the existing test setup.

Verification: CLI unit tests with fake client and no secret; then compile and
full test suite.

## Task 7 — Execute smoke, then the three-arm pilot

Steps:

1. Read the external `.env` without displaying it and confirm only key
   presence/format metadata, never the secret value.
2. Run the Gold/input/config preflight and record any blockers.
3. Run one smoke question with `gpt-5.6-luna`; inspect status, payload schema,
   provenance, tool trace, usage, and no-secret artifact hygiene.
4. If smoke passes, run all 39 jobs into a fresh output directory. If a job
   fails, preserve the failure as non-comparative and do not fabricate output.
5. Run the existing evaluation/report tooling plus a new tool-call summary if
   needed; report accuracy, missing/conflict behavior, latency, tokens, cost,
   tool-call counts, and failure counts by arm.

Verification: no live result is called complete until manifests and evaluation
artifacts pass schema/provenance checks.

## Task 8 — Update durable project state and handoff

Files:

- `.agents/project-state/current.json`
- `.agents/project-state/events.jsonl`
- `.agents/handoffs/`
- `docs/PROVIDER-EXECUTION-HANDOFF-VI.md`

Steps:

1. Record the selected architecture, model, config identity, smoke result,
   pilot status, blockers, and verification commands.
2. Register new code/config/manifest/report artifacts.
3. Keep the thesis source artifacts read-only and document any remaining scope
   or data limitations.

## Final verification command set

```powershell
python -m unittest discover -s tests -p "test_*.py" -v
python -m compileall src scripts
python scripts/preflight_baseline_plan_inputs.py --help
python scripts/run_openai_baseline.py --help
```

Only after these pass will a provider smoke call be attempted. The final report
must distinguish implementation readiness, smoke success, and completed
comparative evaluation.
