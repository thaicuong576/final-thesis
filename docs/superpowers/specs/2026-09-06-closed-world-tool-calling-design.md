# Closed-world role-isolated tool-calling design

Date: 2026-09-06
Status: approved for implementation

## Decision

The thesis system will use a closed-world, source-grounded multi-agent workflow.
The model will not explore the web, live financial services, arbitrary files, or
the SQLite database directly. It will call a small, read-only local toolset whose
implementation queries the promoted Gold snapshot and returns structured facts
with provenance.

The provider transport will target the exact model `gpt-5.6-luna` through the
OpenAI Responses API. The model is used for retrieval decisions, explanation,
critique, and synthesis. Python remains responsible for metric computation,
period alignment, source-policy filtering, validation, and missing-data handling.

## Alternatives considered

1. Prefetch the whole relevant context and put it in every prompt. This is the
   current offline scaffold and is a useful control, but it is less agentic and
   weakens the isolated-toolset contribution.
2. Expose one broad `query_gold` gateway. This reduces implementation effort,
   but role boundaries become mostly prompt-level boundaries.
3. Expose strict function tools by role. This is selected because it makes the
   agent's retrieval behaviour observable while preserving deterministic access
   control and source grounding.

## Runtime boundary

The provider adapter will implement a Responses API tool loop:

1. Build a role-specific prompt containing the immutable request scope, missing
   policy, closed-world rule, and output contract. It will not contain all Gold
   facts for the provider-backed treatment.
2. Send the prompt and only the tools allowed for that role.
3. Validate every function-call name and JSON argument against the current
   request before executing it.
4. Execute the local read-only tool against the Gold SQLite snapshot.
5. Append the structured tool result to the Responses input and continue until
   the model emits its final structured payload or the role's call budget is
   exhausted.
6. Parse the final JSON into `AgentPayload`, preserve the tool outputs as the
   provenance context, and let the existing runtime guards validate request
   binding and evidence IDs.

The loop is fail-closed. Unknown tools, invalid arguments, out-of-scope
tickers/periods/metrics, arbitrary SQL, filesystem access, network access, and
write attempts are rejected. Provider error text and secrets are not copied to
artifacts.

## Tool contract

The first implementation exposes these local functions:

- `get_company_metrics(ticker, period, metric_ids)` — accepted company
  observations, units, quality flags, missing reasons, observation IDs, and
  source IDs.
- `get_sector_benchmarks(sector, period, metric_ids, tickers)` — deterministic
  peer benchmark values computed from accepted observations only.
- `get_macro_context(period, indicator_ids)` — accepted macro observations for
  questions that declare macro indicators.
- `get_evidence(source_ids, ticker, period)` — page-aware evidence snippets
  from accepted sources.
- `get_source_metadata(source_ids)` — source tier, document identity, quality,
  and period metadata without exposing raw storage paths.
- `check_missing_or_conflict(ticker, period, metric_id)` — explicit state for a
  requested cell: valid, missing, unaccepted, or conflicting, including the
  reason and relevant IDs.

Every function has a strict JSON schema, deterministic ordering, bounded input
lists, and a structured JSON result. No tool computes a new financial ratio
from prose. Existing metric/query functions remain the single source of truth.

## Role isolation

| Role | Allowed tools | Responsibility |
|---|---|---|
| `single_agent` | company, sector, macro, evidence, source metadata, missing/conflict | retrieve and answer in one model call-loop |
| `company` | company, evidence, source metadata, missing/conflict | issuer-level facts and explanations |
| `sector` | sector, evidence, source metadata, missing/conflict | peer benchmark and sector comparison |
| `macro` | macro, evidence, source metadata, missing/conflict | declared macro context only |
| `orchestrator` | evidence, source metadata, missing/conflict | synthesize worker payloads; never invent facts |
| `verification` | company, sector, macro, evidence, source metadata, missing/conflict | re-check a bounded claim or uncertainty |

For the pilot's bank-core questions, macro tools are exposed only when the
question declares macro indicators. Tool availability and every tool call will
be recorded so that the thesis can distinguish architecture effects from data
access effects.

The single-agent arm receives the union of the bounded read-only tools. The
hierarchical arm uses specialist subsets and an orchestrator. The critique arm
adds bounded verification calls. All arms share the same snapshot, source
policy, question set, model, prompt/output contract, and missing-data policy.

## Payload and provenance

`AgentPayload` remains the only model-output contract. Numeric claims must carry
unit, period, and observation/source/evidence provenance. Missing values remain
null with explicit findings or quality flags. A tool-call trace records role,
tool name, validated arguments, result hash, and whether the result contained
valid, missing, or conflict states. Raw secrets, absolute local paths, and
provider exception details are excluded.

The runtime will extend the existing completion boundary with an optional
provider context/tool trace. This lets the current provenance validator check
model citations against tool outputs without putting the full database into the
request prompt.

## Configuration and secret handling

The committed provider configuration contains only:

- provider `openai`;
- exact model `gpt-5.6-luna`;
- Responses/function-calling adapter ID;
- Gold source policy ID;
- network enabled for the explicitly requested provider run;
- the name of an environment variable, never its value.

The API key will be read at process start from the user-authorized external
`.env` file under `D:\eddie-projects\personal-projects\mis-talent\\.env`.
It will remain process-local, never be printed, committed, or written to a run
manifest. If the key is absent or the model is unavailable, the run stops with
an actionable blocker and does not substitute another model.

## Evaluation and artifacts

The provider run will execute the existing 13-question × 3-arm pilot plan only
after Gold/input gates pass. Each manifest will include the treatment arm,
model/config identity, call count, telemetry, payloads, and bounded tool-call
traces. The evaluation will report accuracy and missing/conflict handling on
the same 44 valid and 4 missing Gold cells, plus latency, token usage, cost
estimate, tool-call count, and provider failures. No comparative claim is made
if a job fails or if telemetry is unavailable where required.

## Verification strategy

- Unit-test tool argument validation, role tool registries, deterministic
  outputs, missing/conflict semantics, and secret-safe trace serialization.
- Unit-test the Responses loop with a fake transport sequence containing tool
  calls, final structured output, invalid tool calls, call-budget exhaustion,
  and provider failures.
- Preserve the existing offline fixture suite and run it unchanged where its
  prefetch control is intended.
- Run the full repository test suite and compile checks before any live call.
- Smoke-test one provider-backed question with the external key and exact model
  before executing the full 39-job pilot. A smoke test is not reported as an
  evaluation result.

## Non-goals

This change does not expand source coverage, repair the four Gold-missing ACB
Q1 cells, add live web search, deploy a service, or claim that multi-agent is
superior before the three-arm pilot has completed and passed evaluation gates.
