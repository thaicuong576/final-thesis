# Multi-workload complexity ladder Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Extend the provider experiment from mostly atomic questions to a typed Tier 1–3 workload ladder, optimize all three arms under fair contracts, and rerun blind evaluation to test whether multi-agent quality improves as one request contains more analysis work.

**Architecture:** Preserve the existing `AgentPayload` for individual role calls and add a composite workload envelope around validated subreports. A typed workload spec controls issuer, period, metric, task, and complexity scope; a composite controller routes the same request through either one staged single-agent loop or isolated hierarchical workers with optional bounded verification. The old 39-job pilot remains immutable as Tier 1 control, while Tier 2/3 runs use a separate question set and output directory.

**Tech Stack:** Python 3.11, Pydantic v2, SQLite read-only Gold snapshot, OpenAI Responses API, existing provider transport/tool registry, `unittest`, JSON/JSONL experiment manifests.

**Spec:** `docs/superpowers/specs/2026-09-06-multi-workload-complexity-ladder-design.md`

## Global Constraints

- Exact provider/model remains `openai` / `gpt-5.6-luna`.
- Gold snapshot `data/processed/gold-bank-2025-pilot-v1-adjudicated-v2.sqlite` is read-only.
- Raw data, accepted observations, formulas, and source provenance are immutable.
- No web search, arbitrary SQL, filesystem tools, DB writes, or secret persistence.
- All numeric claims must retain unit, period, observation/source/evidence provenance.
- Missing and conflicting values remain explicit; no guessing or imputation.
- All three arms receive the same composite question, Gold snapshot, source policy, model, output contract, and missing-data policy.
- The existing 39-job provider output is immutable; every new run writes to a fresh directory.
- Human thesis-validation limitations remain explicit; AI-assisted scoring is not presented as human validation.
- The current workspace has no `.git` repository; task checkpoints are recorded in `.agents/project-state/current.json` and `.agents/project-state/events.jsonl` instead of Git commits.

---

### Task 1: Add typed workload and composite-output contracts

**Files:**
- Create: `src/thesis_data/workload_contract.py`
- Create: `src/thesis_data/composite_schema.py`
- Modify: `src/thesis_data/question_set.py`
- Create: `tests/test_workload_contract.py`
- Create: `tests/test_composite_schema.py`
- Modify: `tests/test_question_set.py`

**Interfaces:**
- `WorkloadTier`: enum values `tier_1`, `tier_2`, `tier_3`.
- `AnalysisTask`: enum values `snapshot`, `trend`, `peer_comparison`, `missing_conflict`, `anomaly_review`, `evidence_summary`.
- `CompositeWorkloadSpec`: `question_id`, `tier`, `issuers`, `periods`, `metric_ids`, `analysis_tasks`, `peer_tickers`, `macro_indicator_ids`, `complexity_vector`.
- `CompositeSubreport`: `issuer`, `period`, `task`, `payload: AgentPayload | None`, `status`, `missing_reasons`, and provenance IDs.
- `CompositeAnalysisPayload`: request identity, tier, ordered subreports, missing/conflict register, anomaly classifications, final findings, and quality flags.
- `load_question_set()` accepts both existing atomic questions and a `composite_workload` question type without weakening old validation.

- [x] **Step 1: Write failing contract tests.**

  Test that a composite spec rejects empty issuer/period/metric/task lists, a complexity vector that does not match the declared scope, out-of-scope peer tickers, invalid quarter strings, duplicate task IDs, and a Tier 1 spec that declares composite-only tasks. Test that a valid Tier 2 issuer request and Tier 3 multi-issuer request round-trip through Pydantic with stable ordering.

- [x] **Step 2: Run focused tests and verify the expected red failure.**

  Run:

  ```powershell
  $env:PYTHONPATH='src'; python -m unittest tests.test_workload_contract tests.test_composite_schema tests.test_question_set -q
  ```

  Expected result: import or missing-model failures because the new contracts do not exist yet.

- [x] **Step 3: Implement the smallest typed contracts.**

  Add strict Pydantic models with `extra="forbid"`, deterministic tuple/list normalization, finite numeric checks, and validators that derive and compare the complexity vector from the declared workload fields. Add `COMPOSITE_WORKLOAD` to `QuestionType` and validate its required fields without changing validation rules for the six existing question types.

- [x] **Step 4: Run focused tests and the existing question tests.**

  Expected result: all new contract tests and all existing `test_question_set.py` tests pass.

- [x] **Step 5: Record the contract checkpoint.**

  Register the changed files and focused-test result in `.agents/project-state/current.json` and append a matching event to `.agents/project-state/events.jsonl`.

### Task 2: Build Gold-bound multi-scope tool validation

**Files:**
- Modify: `src/thesis_data/agent_tools.py`
- Modify: `src/thesis_data/agent_runtime.py`
- Modify: `src/thesis_data/prompting.py`
- Create: `tests/test_composite_tools.py`
- Modify: `tests/test_agent_tools.py`
- Modify: `tests/test_prompting.py`

**Interfaces:**
- `GoldToolRuntime(..., tickers: Sequence[str] | None = None, periods: Sequence[str], ...)` keeps the old single-`ticker` call compatible and supports a bounded issuer set.
- `GoldToolRuntime.allowed_tickers` exposes an immutable scope for validation only.
- `render_composite_prompt(spec, role, prompt_version) -> str` renders scope, SOP, missing policy, and output contract without serializing the whole database.
- `validate_composite_tool_scope(arguments, spec, role) -> None` rejects out-of-scope issuer, period, metric, peer, source, and macro requests.

- [x] **Step 1: Write failing tool-scope tests.**

  Use the existing SQLite fixture to prove a Tier 3 runtime accepts company queries for each declared issuer and quarter, accepts only the declared peer set, rejects an undeclared ticker/period/metric, preserves source-tier filtering, and returns deterministic ordering. Prove old single-ticker tests remain valid.

- [x] **Step 2: Run focused tool tests and verify red failures.**

  ```powershell
  $env:PYTHONPATH='src'; python -m unittest tests.test_composite_tools tests.test_agent_tools tests.test_prompting -q
  ```

- [x] **Step 3: Implement bounded multi-scope validation and composite prompt rendering.**

  Extend the runtime scope with a frozen ticker set while preserving the existing role allowlists. Add composite prompt instructions that require task/issuer/period coverage, claim-level provenance, explicit missing/conflict states, and no causal inference. Do not add a broad unrestricted query tool.

- [x] **Step 4: Verify focused tests and prompt secrecy.**

  Assert that the composite provider prompt contains request scope and policy but not raw metric/evidence values before tool calls, and that out-of-scope calls fail closed.

- [x] **Step 5: Record the tool checkpoint.**

  Register the changed files and focused-test result in `.agents/project-state/current.json` and append a matching event to `.agents/project-state/events.jsonl`.

### Task 3: Add composite provider transport and response validation

**Files:**
- Modify: `src/thesis_data/openai_transport.py`
- Create: `src/thesis_data/composite_transport.py`
- Modify: `src/thesis_data/provider_adapter.py`
- Create: `tests/test_composite_transport.py`
- Modify: `tests/test_openai_transport.py`

**Interfaces:**
- `CompositeProviderResponse`: composite payload, telemetry, effective context, tool traces, and role/call metadata.
- `OpenAIResponsesTransport.complete_composite(spec, role, prompt, config) -> CompositeProviderResponse`.
- `_composite_response_schema(spec, role) -> dict[str, Any]` creates strict JSON schema with fixed issuer/period/task keys and no arbitrary properties.
- `parse_composite_provider_payload(text, spec, role) -> CompositeAnalysisPayload` validates the final provider output before it reaches the experiment manifest.

- [x] **Step 1: Write failing fake-client tests.**

  Cover a successful multi-issuer tool loop, two tool calls followed by a valid composite payload, rejected out-of-scope tool arguments, invalid final JSON, missing subreport, unsupported extra issuer/task, tool-call budget exhaustion, telemetry accumulation, and secret-safe traces.

- [x] **Step 2: Run focused transport tests and verify red failures.**

  ```powershell
  $env:PYTHONPATH='src'; python -m unittest tests.test_composite_transport tests.test_openai_transport -q
  ```

- [x] **Step 3: Implement the composite transport as a thin extension.**

  Reuse the current Responses loop, strict tool definitions, fail-closed errors, usage telemetry, and result hashing. The new response schema must validate every subreport against the declared workload; it must not replace or weaken the existing `AgentPayload` path.

- [x] **Step 4: Verify provider-neutral behavior.**

  Run fake-client tests and assert that no network or real API key is required. Confirm old transport tests remain green.

- [x] **Step 5: Record the transport checkpoint.**

  Register the changed files and focused-test result in `.agents/project-state/current.json` and append a matching event to `.agents/project-state/events.jsonl`.

### Task 4: Implement fair three-arm composite orchestration

**Files:**
- Create: `src/thesis_data/composite_runner.py`
- Modify: `src/thesis_data/agent_runtime.py`
- Modify: `src/thesis_data/experiment_contract.py`
- Create: `tests/test_composite_runner.py`
- Modify: `tests/test_agent_runtime.py`
- Modify: `tests/test_experiment_contract.py`

**Interfaces:**
- `CompositeArmRunResult`: arm, workload spec, final composite payload, call records, critique records, telemetry, and failure status.
- `run_composite_arm(spec, arm_config, adapter, ...) -> CompositeArmRunResult`.
- `build_arm_sop(arm, spec) -> tuple[str, ...]` returns deterministic stage names recorded in the manifest.
- `bounded_verification_requests(spec, payload, triggers, max_attempts) -> tuple[...]` returns only trigger-backed verification requests.

- [x] **Step 1: Write failing runner tests.**

  With a fake adapter, prove:

  - single-agent receives one composite request and follows the same scope/tools/output contract;
  - no-critique runs company/sector/orchestrator stages without verification;
  - bounded-critique uses verification only for deterministic triggers and never exceeds its cap;
  - all arms receive the same workload spec and Gold scope;
  - invalid worker payloads are not silently repaired or published;
  - call counts and stage names are preserved.

- [x] **Step 2: Run focused runner tests and verify red failures.**

  ```powershell
  $env:PYTHONPATH='src'; python -m unittest tests.test_composite_runner tests.test_agent_runtime tests.test_experiment_contract -q
  ```

- [x] **Step 3: Implement the composite controller.**

  Use the existing runtime validation for each worker payload. The single arm uses the composite transport directly. Hierarchical arms use bounded company/sector/orchestrator calls; the critique arm adds only trigger-backed verification. Enforce a per-tier total call ceiling shared across arms and record budget exhaustion as an explicit failure state.

- [x] **Step 4: Verify fair-scope invariants.**

  Assert identical snapshot/question bindings and allowed scope across arm requests; assert no critique calls in the no-critique arm; assert verification calls are absent when no trigger exists.

- [x] **Step 5: Record the arm-controller checkpoint.**

  Register the changed files and focused-test result in `.agents/project-state/current.json` and append a matching event to `.agents/project-state/events.jsonl`.

### Task 5: Freeze Tier 2/Tier 3 question set and complexity plan

**Files:**
- Create: `experiments/question-set-complexity-v1.json`
- Create: `experiments/runs/complexity-plan-gold-v1.json`
- Create: `scripts/validate_complexity_plan.py`
- Create: `tests/test_complexity_question_set.py`
- Create: `tests/test_complexity_plan.py`
- Modify: `src/thesis_data/question_set.py`
- Modify: `src/thesis_data/baseline_plan.py`

**Interfaces:**
- `load_complexity_question_set(path) -> QuestionSet`.
- `build_complexity_plan(question_set, arms, snapshot_id, model_id, ...) -> BaselinePlan`.
- `validate_complexity_plan_inputs(...) -> audit result`.
- Question-set ID: `pilot-2024-bank-complexity-v1`.
- New questions: three Tier 2 issuer workloads plus one Tier 3 multi-issuer landscape workload, with Tier 1 references bound to the existing 13-question set rather than copied or mutated.

- [x] **Step 1: Write failing question/plan tests.**

  Assert exact Tier 2/Tier 3 issuer, period, metric, task, peer, and complexity-vector bindings; unique question IDs; 3 arms per composite question; no staging snapshot; and a tier-specific total call ceiling.

- [x] **Step 2: Run focused tests and verify red failures.**

  ```powershell
  $env:PYTHONPATH='src'; python -m unittest tests.test_complexity_question_set tests.test_complexity_plan -q
  ```

- [x] **Step 3: Write the frozen versioned question set and plan.**

  Use the current Gold scope only: ACB, TCB, VPB; 2024_Q1–2024_Q4; four core metrics. Include the exact prompts, required task list, ordered periods, peer set, complexity vector, model/config identity, and `comparative_result: false` until the run and scoring gates pass.

- [x] **Step 4: Implement read-only preflight validation.**

  Reject mismatched snapshot/question hashes, undeclared issuers/periods/metrics/tasks, duplicate jobs, wrong arm counts, missing call budgets, and any non-Gold input before a provider call.

- [x] **Step 5: Record the experiment-plan checkpoint.**

  Register the changed files and preflight result in `.agents/project-state/current.json` and append a matching event to `.agents/project-state/events.jsonl`.

### Task 6: Persist composite manifests and tier-aware telemetry

**Files:**
- Modify: `src/thesis_data/run_manifest.py`
- Modify: `tests/test_run_manifest.py`
- Create: `tests/test_complexity_manifest.py`

**Interfaces:**
- `RunManifest.workload_tier`.
- `RunManifest.complexity_vector`.
- `RunManifest.arm_sop`.
- `RunManifest.subreport_count`.
- `RunManifest.total_tool_calls` and existing per-call telemetry remain additive and backward-compatible.

- [x] **Step 1: Write failing manifest tests.**

  Assert composite manifests preserve question hash, tier, complexity vector, stage/role identity, subreport provenance, tool traces, total tokens, cost, latency, failure status, and critique count. Assert old atomic manifests deserialize unchanged.

- [x] **Step 2: Run focused manifest tests and verify red failures.**

  ```powershell
  $env:PYTHONPATH='src'; python -m unittest tests.test_complexity_manifest tests.test_run_manifest -q
  ```

- [x] **Step 3: Add additive manifest fields and secret-safe serialization.**

  Default new fields for old manifests; reject mismatched workload bindings for new manifests. Never serialize API keys, absolute DB paths, raw provider errors, or unbounded tool output.

- [x] **Step 4: Verify atomic compatibility and composite completeness.**

  Run old manifest tests and new composite manifest tests together.

- [x] **Step 5: Record the manifest checkpoint.**

  Register the changed files and focused-test result in `.agents/project-state/current.json` and append a matching event to `.agents/project-state/events.jsonl`.

### Task 7: Add tier-aware blind scoring and scaling analysis

**Files:**
- Modify: `src/thesis_data/blind_scoring.py`
- Modify: `src/thesis_data/blind_ai_review.py`
- Modify: `src/thesis_data/blind_aggregate.py`
- Create: `scripts/build_complexity_blind_score.py`
- Create: `scripts/aggregate_complexity_score.py`
- Create: `tests/test_complexity_blind_scoring.py`
- Modify: `tests/test_blind_aggregate.py`

**Interfaces:**
- `build_composite_blind_packets(run_dir, db_path, question_set_path, seed) -> artifacts`.
- `score_composite_answer(packet) -> list[ClaimReview]`.
- `aggregate_by_tier_and_arm(reviews, manifests) -> dict`.
- `compute_scaling_deltas(scores_by_tier, baseline_arm="single_agent") -> dict`.
- `classify_break_even_region(deltas, operational_by_tier) -> dict`.

- [x] **Step 1: Write failing scoring tests.**

  Test that arm/run/model identity is absent from composite packets, every subclaim retains task/issuer/period binding, missing/conflict handling is scored separately from factual correctness, and tier aggregation does not mix Tier 1 with Tier 2/3.

- [x] **Step 2: Run focused scoring tests and verify red failures.**

  ```powershell
  $env:PYTHONPATH='src'; python -m unittest tests.test_complexity_blind_scoring tests.test_blind_aggregate -q
  ```

- [x] **Step 3: Implement tier-aware mechanical and AI-assisted scoring.**

  Reuse the existing rubric and arm-blinding rules. Add explicit coverage for task completeness, cross-issuer consistency, cross-period consistency, and claim-level evidence binding. Preserve original reviewer decisions and disagreement/adjudication artifacts.

- [x] **Step 4: Implement interaction and operational analysis.**

  Report per-tier deltas versus single-agent, quality slopes, cost/latency ratios, failure/partial rates, and whether a hierarchical arm has a tier where it wins a primary quality dimension without a material loss. Do not fit or report a universal asymptotic law.

- [x] **Step 5: Record the tier-scoring checkpoint.**

  Register the changed files and focused-test result in `.agents/project-state/current.json` and append a matching event to `.agents/project-state/events.jsonl`.

### Task 8: Run offline gates and provider smoke test

**Files:**
- Modify: `scripts/run_openai_baseline.py` or create `scripts/run_complexity_pilot.py` only if the existing runner cannot preserve the old plan.
- Create: `tests/test_run_complexity_pilot.py`
- Create: `experiments/outputs/provider/complexity-gpt-5.6-luna-<timestamp>/`
- Create: `reports/complexity-provider-smoke-<timestamp>.md`

- [x] **Step 1: Add a fake-client runner test.**

  Prove the runner loads only the complexity plan, refuses to overwrite a non-empty output directory, keeps Tier 1 and Tier 2/3 question hashes distinct, and records failures without fabricating composite output.

- [x] **Step 2: Run the complete offline verification before network access.**

  ```powershell
  $env:PYTHONPATH='src'; python -m unittest discover -s tests -q
  python -m compileall -q src scripts
  python scripts/validate_complexity_plan.py experiments/runs/complexity-plan-gold-v1.json
  ```

  Expected result: all tests pass, compileall passes, and the complexity plan is eligible against the promoted Gold snapshot.

- [x] **Step 3: Run one smoke question for each new tier.**

  Use the external authorized `.env`, exact `gpt-5.6-luna`, and a fresh smoke directory. Inspect payload schema, tool scope, provenance, call budget, telemetry, and secret-safe artifacts. Smoke output is not comparative evidence.

- [x] **Step 4: Stop on any smoke blocker.**

  Do not run the full provider pilot if any composite payload is malformed, out of scope, missing telemetry, or unable to preserve provenance.

- [x] **Step 5: Record the offline-gate checkpoint before live outputs.**

  Register the code/tests/config artifacts and offline verification result in `.agents/project-state/current.json` and append a matching event to `.agents/project-state/events.jsonl`.

### Task 9: Execute the complexity pilot and score it

**Files:**
- Create: `experiments/outputs/provider/complexity-gpt-5.6-luna-<timestamp>/`
- Create: `reports/provider-complexity-gpt-5.6-luna-<timestamp>.md`
- Create: `reports/provider-complexity-gpt-5.6-luna-<timestamp>.json`
- Create: `reports/provider-complexity-blind-score-gpt-5.6-luna-<timestamp>/`
- Create: `.agents/handoffs/<date>-complexity-pilot.md`

- [x] **Step 1: Run the frozen complexity plan into a fresh directory.**

  Execute all planned Tier 2/3 jobs and retain every manifest, payload, tool trace, failure ledger, latency, usage, and cost estimate. Do not overwrite the completed Tier 1 run.

- [x] **Step 2: Verify run integrity before scoring.**

  Require complete arm/tier coverage, identical snapshot/question/config bindings within each comparison, valid provenance, no secret hits, and explicit failure accounting.

- [x] **Step 3: Build blind packets and run the two independent AI-assisted reviewers.**

  Hide arm, role, run, filename, and model identity. Keep the same reviewer prompts/rubric principles as the first pilot, extending only the composite task-completeness checks.

- [x] **Step 4: Preserve reviewer disagreements; human adjudication remains open.**

  Produce the disagreement queue and, if used, a separate AI-adjudicated overlay. Do not overwrite original labels or call AI adjudication human validation.

- [x] **Step 5: Generate the per-tier scaling report.**

  Include Tier 1 reference values, Tier 2/3 scores, interaction deltas, operational frontier, failure modes, and a bounded conclusion about the tested workload range.

### Task 10: Final verification and durable state update

**Files:**
- Modify: `.agents/project-state/current.json`
- Modify: `.agents/project-state/events.jsonl`
- Modify: `docs/DECISIONS.md`
- Create: `.agents/handoffs/<date>-complexity-pilot.md`

- [x] **Step 1: Run final verification.**

  ```powershell
  $env:PYTHONPATH='src'; python -m unittest discover -s tests -q
  python -m compileall -q src scripts
  ```

  Also parse every new JSON/JSONL artifact, verify state/event synchronization, verify all expected artifacts are registered, and scan outputs for `OPENAI_API_KEY` and `sk-`.

- [x] **Step 2: Record the result without overclaiming.**

  Record whether a tested break-even tier exists. If no tier shows a robust quality/overhead advantage, keep single-agent as the practical baseline and document the negative scaling result. If a tier does show an advantage, state its exact scope and cost/latency trade-off.

- [x] **Step 3: Keep the human thesis-validation gate explicit.**

  Preserve an open decision for independent human blind review before final thesis superiority claims, even if the AI-assisted scaling report is internally complete.

- [x] **Step 4: Mark this goal complete only after the run, score, report, and verification artifacts exist.**

  Do not mark the goal complete after writing the plan or after an offline smoke test.
