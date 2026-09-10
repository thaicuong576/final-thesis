# Baseline build and thesis-writing plan

Status: prepared for the next phase; execution of experiments is gated by
`reports/data-foundation/readiness-decision.md`.

## Research question

On the same source-grounded snapshot and the same user questions, does a
hierarchical Macro/Sector/Company design improve factual correctness, evidence
completeness, and anomaly handling enough to justify its additional latency and
cost compared with a tool-equivalent single-agent baseline?

The experiment must be able to find no improvement. Multi-agent superiority is a
hypothesis, not a design assumption.

## Build order after `READY_FOR_BASELINE`

The deterministic query/evidence boundary, adapter interfaces, offline fixture,
run-manifest contract, and non-executing baseline plan may be built before the
gate. Only the provider-backed baseline and comparative results below require a
promoted Gold snapshot.

### Baseline 0 — deterministic data/query layer

Freeze the snapshot ID, question set, source policy, model configuration, metric
definitions, and output contract. Run the same read-only query and evidence tools
for every arm. Log observation IDs, source IDs, evidence IDs, prepared-context
hashes, canonical prompt fingerprints, tool calls, validation results, latency,
and token/cost estimates. A
provider adapter must supply telemetry when available; unavailable values stay
null and are labeled rather than converted to zero. The
typed question-set validator (`scripts/validate_question_set.py`) must pass and
the resulting question-set hash must be bound into every run manifest. The
prompt/configuration contract is versioned separately as
`docs/PROMPT-CONTRACT-VI.md`; the same non-empty `prompt_version` must be copied
into every arm's manifest. The
pre-Gold planner (`scripts/plan_baseline_runs.py`) expands the fixed question set
into one non-executing job per arm; its snapshot placeholder must be replaced by
the promoted Gold snapshot only after the readiness gate passes. The run-manifest
schema and offline fixture harness are implemented. The
reproducible plumbing check is available through
`scripts/run_offline_fixture.py`; provider-backed execution remains gated.
For `company_trend` jobs, the executor must pass the complete ordered
`BaselineJob.periods` tuple as one temporal scope; the runtime rejects a
single-period shortcut and records the same scope in the run manifest.
`src/thesis_data/baseline_runner.py` is the fail-closed one-job boundary: it
checks the plan job against the run configuration and typed question before
delegating to the guarded runtime, and carries the validated `job_id` into the
runtime result and run manifest.
`src/thesis_data/baseline_batch_runner.py` is the next guarded boundary: it
preflights the complete plan, rejects `PENDING_GOLD_SNAPSHOT`, executes every
job through the one-job boundary, and writes append-safe manifests only after
the plan jobs complete. It accepts an adapter by dependency injection and does
not create provider or network behavior.
`src/thesis_data/provider_config.py` now provides the secret-free provider
configuration contract. A provider-backed batch execution must receive this
config explicitly; model and source-policy mismatches fail before the first
adapter dispatch. The config loader never reads the referenced secret value or
creates a provider client. See `docs/PROVIDER-ADAPTER-CONTRACT-VI.md`.
`src/thesis_data/provider_adapter.py` now provides the provider-neutral
structured-response boundary: an injected transport returns a typed/JSON
`ProviderResponse`, which is parsed into `AgentPayload` and paired with typed
telemetry. Malformed responses, missing required telemetry, and transport
failures fail closed; this remains plumbing only and does not execute a
provider.
The offline fixture now routes its deterministic transport through this same
`StructuredProviderAdapter`, so the persisted-plan path exercises the boundary
end to end while remaining offline and non-comparative.
`src/thesis_data/prompting.py` renders the same request into a deterministic
prompt with stable scope/context serialization; the injected transport receives
that rendered prompt and must not rebuild it independently. Prompt calibration
against a real model remains gated until Gold is ready.
The read-only `scripts/preflight_baseline_plan_inputs.py` command exposes the
same all-job database/input preflight without dispatching an adapter.
Before dispatching the first job, run
`scripts/validate_baseline_plan.py` against the serialized plan and current
question set; this catches plan-level hash, coverage, and binding drift without
opening a provider.

For the first provider-backed comparison, prefer the bank-core question set in
`experiments/question-set-core-v1.json` (13 questions, 39 jobs). Keep the full
42-job plan as a draft that includes the macro extension. Do not aggregate the
macro job with core results until official period-aligned macro observations are
in Gold.

### Baseline 1 — single agent

One agent receives the target ticker, period, accepted query results, and bounded
evidence. It may explain and synthesize, but it cannot calculate ratios from prose,
call the network, or hide missing values.

### Baseline 2 — hierarchical without critique

Macro, Sector, and Company workers run with the same tools and snapshot. The
orchestrator validates payloads and synthesizes them, but does not run the second
verification loop. This isolates decomposition from critique.

### Baseline 3 — hierarchical with bounded critique

Use the same hierarchical setup plus deterministic anomaly triggers and at most two
focused verification attempts. The runtime records each generated trigger in
the run manifest. Missing or unaccepted values are triggerable by default;
numeric deviation rules require an explicit metric-specific threshold and a
matching known unit. Record every trigger and resolution. An anomaly trigger is
not automatically labeled a true contradiction.

## Fairness controls

- Same frozen issuer/period scope from the selected manifest (the 48-cell pilot
  or a later 80/200-cell expansion), question set, snapshot, source policy,
  model version, temperature/configuration, and output schema.
- Same accepted facts and evidence tools; the single agent is not given less data.
- No arm may silently fall back to staging, a network call, or an unaccepted source.
- Report failures and nulls rather than replacing them with plausible text.
- Use a blind review subset with a fixed rubric and independent checker IDs.

## Outcome table

| Outcome | Definition | Primary/secondary |
|---|---|---|
| Factual correctness | Claim agrees with gold observation or is correctly marked uncertain | Primary |
| Evidence completeness | Published claims have source ID and valid locator/evidence | Primary |
| Citation correctness | Citation actually supports the claim and period | Primary |
| Anomaly quality | True contradiction, explainable divergence, or insufficient evidence is labeled correctly | Primary for critique arm |
| Validation failure rate | Invalid payloads or contract violations per run | Secondary |
| Latency | Wall-clock time per completed question | Secondary |
| Token/cost | Input/output usage or local cost estimate | Secondary |
| Coverage of answer | Required metrics returned or explicitly missing | Secondary |

## Parallel writing matrix

| Thesis chapter | Write while building | Evidence to freeze |
|---|---|---|
| 1. Introduction | Problem, scope, research question, contributions, non-goals | `docs/SPEC.md`, advisor-approved selection manifest |
| 2. Background | Financial metrics, source-grounded QA, single vs multi-agent rationale | `docs/METRIC-DICTIONARY.md`, literature notes |
| 3. Methodology | Dataset protocol, source hierarchy, contracts, experiment arms, scoring rubric | readiness checklist, evaluation protocol, gold manifest |
| 4. System design | Ingestion, normalization, deterministic calculations, query boundary, agent roles | `docs/ARCHITECTURE.md`, source/metric/evidence schemas |
| 5. Implementation | Reconciliation, PDF handling, versioned prompt/tool configuration, run logging | hashes, code versions, question-bound run manifests, prompt version, parser report |
| 6. Evaluation | Results, error taxonomy, ablations, cost/latency, threats to validity | frozen experiment outputs and blind labels |
| 7. Conclusion | Answer research question, limitations, practical extension path | only claims supported by Chapter 6 |

## Definition of done for the next phase

The phase is complete only when:

1. `readiness-decision.md` is `READY_FOR_BASELINE`.
2. A single-agent run can be reproduced from a snapshot ID and question ID.
3. A trend question produces one request containing every declared period and a
   manifest that preserves that period scope.
4. All three experiment arms produce contract-valid outputs on the same fixture.
5. The blind review rubric and gold labels are frozen before result inspection.
6. Chapter drafts cite durable artifacts rather than undocumented chat decisions.

Until item 1 is true, work may proceed on reconciliation code, prompts as drafts,
test fixtures, run-manifest tooling, and thesis chapters 1–4, but not on claims
about comparative agent performance.
