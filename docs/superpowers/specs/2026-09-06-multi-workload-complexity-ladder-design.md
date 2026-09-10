# Multi-workload complexity ladder design

Status: proposed design for user review
Date: 2026-09-06

## Core decision

The next experiment will test whether the relative value of hierarchical
multi-agent coordination increases as a single request contains more related
financial-analysis workloads. It will not claim that a larger database alone
causes multi-agent superiority.

The current 39-job pilot remains the Tier 1 control. A new composite workload
question set will add Tier 2 and Tier 3 requests over the same promoted Gold
snapshot before any database expansion. This isolates workload coordination
complexity from source coverage and database-quality changes.

## Research claim to test

The falsifiable hypothesis is:

> After the three arms receive the same model, Gold snapshot, source policy,
> evidence rules, output contract, and workload scope, the quality gap
> `multi-agent - single-agent` increases with workload complexity, and at some
> tier the quality gain is large enough to justify additional cost and latency.

This is an interaction hypothesis, not a universal claim that multi-agent is
always better. The thesis may conclude that no break-even tier was observed.

## Known facts and boundaries

- The existing provider pilot has 13 questions × 3 arms and mostly separates
  snapshot, trend, peer-comparison, anomaly, and conflict tasks.
- The promoted Gold snapshot contains ACB, TCB, and VPB for 2024_Q1 through
  2024_Q4 and four core bank metrics.
- The current runtime binds one typed request to issuer/period/metric scope and
  `AgentPayload` is the single-agent and worker payload contract.
- The current result prefers single-agent, but it tests only the present
  workload and implementation. It does not identify a scaling threshold.
- Raw data, Gold observations, formulas, and source provenance remain
  immutable. No source-quality gap may be hidden by adding a larger request.

## Workload tiers

Each tier uses the same three arms and the same Gold snapshot.

### Tier 1 — atomic control

The existing `pilot-2024-bank-core-qa-v1` question set is unchanged. It keeps
the current 13 questions so the new run can be compared directly with the
completed pilot.

### Tier 2 — multi-workload issuer request

Add one composite request per issuer for ACB, TCB, and VPB. Each request covers
all four 2024 quarters, all four core metrics, and these linked tasks:

1. company snapshot by quarter;
2. supported quarterly trend;
3. peer comparison for the latest accepted period;
4. missing/conflict disclosure;
5. anomaly or explainable-divergence review; and
6. source-linked evidence summary.

The answer must preserve sections by task and period. A claim from one section
must not be silently reused as evidence for another section.

### Tier 3 — multi-issuer landscape request

Add a composite request over ACB, TCB, and VPB together for all four quarters
and all four core metrics. It must produce:

1. a comparable issuer-by-period metric matrix;
2. period-over-period trends;
3. peer-relative rankings or medians only where Gold benchmarks are accepted;
4. cross-issuer and cross-period anomaly classification;
5. a missing/conflict register; and
6. an evidence index linking each numeric claim to valid source/observation
   provenance and page/table/section locators where available.

The request is deliberately one user workload, but the output remains a set of
typed subclaims rather than an unstructured essay.

## Complexity measurement

Complexity is pre-registered from the typed question, not inferred from model
tokens after the run. The runner records:

- target issuer count;
- period count;
- metric count;
- analysis-task count;
- requested cross-issuer comparisons;
- requested anomaly/missing-conflict checks; and
- requested evidence groups.

The primary analysis uses tier as a categorical factor and also records a
complexity vector. Prompt length, output length, model call count, and cost are
outcomes, not complexity definitions.

## Composite request and output contract

Introduce a typed `CompositeWorkloadSpec` with:

- `question_id`;
- `tier` (`1`, `2`, or `3`);
- `issuers`;
- ordered `periods`;
- `metric_ids`;
- `analysis_tasks`;
- `peer_tickers`;
- `macro_indicator_ids`; and
- a deterministic `complexity_vector`.

Introduce a typed `CompositeAnalysisPayload` containing:

- request identity and tier;
- one validated subreport per issuer/period/task;
- metric claims with unit, period, observation IDs, source IDs, and evidence
  IDs;
- explicit missing/conflict states;
- anomaly labels from the existing allowed vocabulary; and
- a final synthesis that references only validated subreports.

The existing `AgentPayload` remains the contract for individual company,
sector, macro, orchestrator, and verification calls. The composite envelope
does not permit the model to invent a new numeric value or bypass existing
provenance validation.

## Three-arm protocol

### Single-agent

The single agent receives the composite request and the union of the same
closed-world read-only tools available to the hierarchical system. Its SOP is
explicit but remains one agent:

1. plan the required task/issuer/period matrix internally;
2. retrieve only in-scope Gold facts and evidence;
3. validate missing/conflict states and definition alignment;
4. construct typed subreports; and
5. synthesize the composite answer.

The single agent is not given the full database in the prompt. This preserves
the tool-calling comparison and prevents the control from being weakened by
prefetching.

### Hierarchical without critique

The orchestrator decomposes the same composite request into bounded specialist
work:

- company workers retrieve issuer-by-period metrics and evidence;
- the sector worker handles peer comparisons and cross-issuer summaries; and
- the orchestrator validates subpayloads and assembles the composite report.

No verification worker is called. The orchestrator may not repair, infer, or
silently fill an invalid worker payload.

### Hierarchical with bounded critique

This uses the same decomposition as the no-critique arm. Verification is
allowed only for deterministic triggers: missing provenance, metric-definition
misalignment, conflicting Gold state, unsupported cross-level comparison, or
anomaly classification requiring a focused check. Verification is capped per
composite job and every attempt is recorded.

The critique arm must not receive a wider source scope or extra Gold facts than
the other arms. Its only additional capability is the bounded verification
step, whose cost and latency are reported separately.

## Fairness and budget rules

- Exact model: `gpt-5.6-luna` for every arm and tier.
- Same Gold snapshot, source policy, question-set binding, evidence contract,
  missing-data policy, and final output schema.
- Same composite question is sent to all three arms; only routing and role
  decomposition differ.
- A tier-specific total tool/model-call ceiling is declared before execution
  and is shared as an experiment budget. The hierarchical arms cannot hide
  calls inside workers.
- Natural operational cost is a primary outcome. A secondary cost-matched
  view may report quality at the same budget when enough successful runs exist.
- Failed or partial jobs remain visible and are never converted into a score of
  zero without the rubric's explicit rule.

## Evaluation and decision rule

Report scores by tier and arm for:

- factual correctness;
- calculation correctness;
- evidence completeness;
- citation correctness;
- missing/conflict handling;
- cross-level consistency;
- anomaly classification;
- total latency;
- model calls/tool calls;
- input/output tokens; and
- cost estimate.

The primary result is the per-tier delta between each hierarchical arm and
single-agent. A multi-agent arm is a candidate for a break-even region only if
it improves at least one primary quality dimension by the pre-registered
margin, does not materially lose another primary dimension, and the report
shows whether the quality gain justifies its cost/latency under the stated
use-case value assumption.

The strongest thesis claim permitted by this design is bounded to the tested
tiers and Gold snapshot. It may say that multi-agent becomes more or less
useful as workload complexity increases within the experiment; it may not
claim an asymptotic law or universal superiority.

## Data expansion boundary

Database expansion to five banks, eight quarters, or additional metrics is a
separate follow-up factor. It requires its own source-coverage and Gold-readiness
gate. It must not be introduced in the same first comparison as the composite
question change, because that would confound workload complexity with data
quality and retrieval coverage.

## Failure modes and kill conditions

- If the composite output contract cannot preserve claim-level provenance, stop
  and keep the existing atomic evaluation.
- If Tier 2 or Tier 3 requests are not answerable from accepted Gold cells,
  mark the missing scope explicitly rather than expanding the database silently.
- If multi-agent quality does not improve with tier, report that no scaling
  advantage was observed.
- If quality improves only because the single-agent control receives less
  budget, tools, or SOP support, invalidate the comparison and rerun fairly.
- If cost/latency grows faster than quality, report the operational frontier
  rather than selecting multi-agent on quality alone.

## Verification deliverables

The implementation phase must produce:

1. a versioned composite question set and complexity manifest;
2. typed schema and validation tests for composite requests/subreports;
3. three-arm run manifests with per-tier telemetry and call traces;
4. blind packets that hide arm identity across all tiers;
5. a per-tier rubric report and interaction/sensitivity summary; and
6. a handoff that distinguishes observed scaling evidence from the remaining
   human thesis-validation gate.
