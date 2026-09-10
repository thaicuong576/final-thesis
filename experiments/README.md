# Experiment contract v1

These files define the questions and scoring rules before any agent arm is run.
They are deliberately independent of a particular gold snapshot. A run must
bind a promoted snapshot ID, model configuration, source policy, and question
set hash in its run manifest.

## Arms

1. `single_agent`: one agent receives the same accepted facts and evidence tools.
2. `hierarchical_no_critique`: Macro/Sector/Company workers plus orchestrator,
   without the second verification loop.
3. `hierarchical_bounded_critique`: the same hierarchy with deterministic
   anomaly triggers and at most two focused verification attempts.

The first arm is not a straw-man baseline: it must receive the same accepted
facts, evidence, output contract, and model/configuration as the other arms.

## Run preconditions

A run is invalid unless its manifest includes:

- a promoted gold snapshot ID;
- the exact question-set and rubric versions;
- the exact question ID, verified to exist in that question set;
- accepted-source policy and model/configuration;
- input observation/evidence IDs;
- tool-call, latency, token, and cost records;
- contract-validation results and unresolved-missing flags.

The candidate or staging SQLite files cannot satisfy the first precondition.
`src/thesis_data/experiment_contract.py` enforces these checks, including the
typed question-set schema, before dispatch. The runtime additionally binds
each request to the selected question's issuer, period, and declared metric
scope before preparing context. The adapter request also carries the selected
question ID, type, and prompt explicitly, while the manifest binds the exact
question-set hash. Sector context is likewise restricted to the selected
question peer set or the frozen Gold ticker scope. For `company_trend`, the
caller must pass the complete ordered period list from the question; the
runtime prepares one period-keyed context per period, scans anomaly triggers
per period, and records that list in the request and run manifest. Partial
trend requests fail before adapter dispatch. The current
`primary-only-v1` policy family resolves to `source_tier=primary` across all
query modes; unregistered policy IDs are rejected before dispatch;
the current normalized candidate snapshot is expected to be rejected.
The Gold promotion and baseline gates also require a `value_check` label for
every selected `(ticker, period, metric)` cell; aggregate labels from other
cells cannot satisfy that requirement.
`src/thesis_data/agent_runtime.py` provides the next guarded layer: an injected
adapter receives prepared contexts, worker/orchestrator dispatches, and bounded
verification requests while the runner records the call trace. It is a scaffold,
not an executed comparative result. `src/thesis_data/baseline_runner.py` now
checks one `BaselineJob` against its run configuration and typed question before
calling that runtime; it accepts an adapter by dependency injection and adds no
provider or network behavior. `src/thesis_data/run_manifest.py` records
the snapshot/question/arm identity, question-set hash, observation/source/evidence
IDs, validated plan `job_id` when present, prepared context hash, call traces, provider telemetry, and contract-valid
payloads. The offline fixture tests
exercise all three arms on the same accepted fixture; they are harness checks,
not thesis performance results. The bounded-critique scaffold records
conservative deterministic triggers in each run manifest: missing values are
triggerable by default, while numeric deviations require an explicit
metric-specific threshold and matching known units.

`src/thesis_data/baseline_batch_runner.py` executes a complete preflighted plan
through that one-job boundary and writes one immutable manifest per job. It
rejects the `PENDING_GOLD_SNAPSHOT` placeholder before dispatch and requires an
injected adapter, so adding this batch surface does not create a hidden provider
fallback.

`src/thesis_data/provider_config.py` is the secret-free provider boundary. A
`provider_backed` batch run must provide an explicit `ProviderExecutionConfig`;
the batch runner validates its environment, model, and source-policy binding for
every job before dispatch. The config contains only environment-variable names,
never API-key values, and does not create a provider client.

The read-only `scripts/preflight_baseline_plan_inputs.py` command runs the same
full-plan input audit without an adapter. Use it after Gold promotion and before
provider execution; it checks every job's snapshot, source policy, question
binding, and macro-extension requirements first.

## Fixed question design

`question-set-v1.json` contains 14 questions: four bank question types for each
of ACB, TCB, and VPB in the 2024 feasibility-pilot period, plus one explicit
macro-to-bank question and one pre-registered missing/conflict question. This
keeps the unit of comparison identical across arms while covering retrieval,
trend synthesis, peer context, macro interpretation, missing/conflicting
evidence, and anomaly handling. Anomaly questions declare the retained trigger
IDs (`company_metric_missing`, `sector_benchmark_missing`, and
`company_sector_deviation`) as coverage metadata; they do not assert that a
trigger is present or convert a trigger into a gold anomaly label.

`question-set-core-v1.json` is the guarded 13-question bank-core variant. It
removes only the macro-to-bank question and produces 39 planned jobs across the
same three arms. Use it for the primary aggregate when bank Gold is ready but
macro Gold is not; keep the macro question as a separately reported extension.

The macro-to-bank question requires accepted, period-aligned macro
observations. `src/thesis_data/experiment_contract.py` fails closed when the
selected macro question has no valid primary-source observation for any
requested indicator and period. The current fallback macro snapshot remains
pending validation, so it cannot satisfy the official benchmark gate.

Validate the question-set structure and print its exact hash with:

```powershell
python scripts/validate_question_set.py experiments/question-set-v1.json
```

This command is read-only and should be run before freezing the question set or
creating provider-backed run manifests.

Create the pre-Gold, non-executing 42-job plan with:

```powershell
python scripts/plan_baseline_runs.py experiments/question-set-v1.json PENDING_GOLD_SNAPSHOT --output experiments/runs/baseline-plan-pilot-v1.json
```

The plan expands 14 questions across the three arms and binds the question-set
hash. `PENDING_GOLD_SNAPSHOT` is an explicit placeholder; the plan authorizes
no provider call and is not a comparative result.

Create a non-executing core plan summary with:

```powershell
python scripts/validate_question_set.py experiments/question-set-core-v1.json
python scripts/plan_baseline_runs.py experiments/question-set-core-v1.json PENDING_GOLD_SNAPSHOT
```

The core plan expands 13 questions into 39 jobs. Do not mix its results with the
macro extension unless the macro question's primary-source and period-alignment
gate passes.

The committed core plan can be preflighted without changing it:

```powershell
python scripts/validate_baseline_plan.py `
  experiments/runs/baseline-plan-core-v1.json `
  experiments/question-set-core-v1.json
```

Validate an existing serialized plan without changing it:

```powershell
python scripts/validate_baseline_plan.py experiments/runs/baseline-plan-pilot-v1.json experiments/question-set-v1.json
```

This preflight rejects question-set hash drift, missing or duplicate jobs, and
job bindings that no longer match the typed questions.

If the advisor approves the proposed metric-reduced fallback, its isolated
blind-review copies can be generated without changing the canonical register:

```powershell
$env:PYTHONPATH='src'
python scripts/build_scoped_reviewer_copies.py `
  data/reconciliation/gold-bank-2025-pilot-v1/register.csv `
  data/manifests/gold-bank-2025-pilot-v1/fallback-36-selection.json `
  data/reconciliation/gold-bank-2025-pilot-v1/fallback-36-review
```

The fallback remains proposed until advisor confirmation and must use a
separate review ledger and Gold snapshot configuration.

## Scoring

`scoring-rubric-v1.md` scores atomic claims rather than prose quality. A missing
value marked with a valid reason is not a factual error; an unsupported precise
number is. Reviewers score outputs blind to the experiment arm.

`src/thesis_data/evaluation.py` provides the machine-readable claim-review
contract and deterministic per-arm/per-dimension aggregation. It keeps
unscorable contract or review failures visible instead of silently treating
them as zeroes. It consumes reviewer decisions only; it does not create gold
labels or infer correctness from model prose.

The corresponding read-only CLI is:

```powershell
python scripts/summarize_claim_reviews.py path/to/claim-reviews.jsonl
```

It emits JSON summaries and refuses to overwrite an existing output file when
`--output` is supplied.

No result should be aggregated into a superiority claim unless the gold labels,
question set, and blind-review protocol are frozen first.

## Offline plumbing check

Before a promoted thesis snapshot exists, the experiment plumbing can be
exercised with the deterministic fixture:

```powershell
python scripts/run_offline_fixture.py experiments/runs/offline-fixture-v9
```

This writes the fixture database, question set, serialized plan, and one
manifest per arm under `manifests/`. The expected call counts are `1`, `4`, and
`6`; every manifest is marked `environment=offline_fixture` and
`comparative_result=false`. The generated files under
`experiments/runs/offline-fixture-v9/` are harness evidence only, not financial
analysis or comparative thesis results. The v1 through v8 runs are retained as
earlier plumbing snapshots; v3 records the macro-evidence routing fix, v4
records the anomaly-trigger manifest field, v5 records the question-set
SHA-256 binding, v6 records unavailable telemetry fields, v7 records the
versioned prompt contract in schema version 2 manifests, and v8 replays the
same fixture after request-level propagation and manifest mismatch guards were
added. v9 additionally exercises the persisted plan and complete batch
preflight-to-manifest boundary. The command refuses
to write into a non-empty
directory.
