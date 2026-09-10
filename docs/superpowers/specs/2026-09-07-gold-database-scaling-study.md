# Gold database/workload scaling study

Status: design only; provider execution is gated on Gold coverage and human
review.

## Research question

Does a hierarchical multi-agent system become more useful as a source-grounded
bank-analysis workload grows, after accounting for orchestration cost and
failure risk?

The claim under test is conditional. It is not “multi-agent is always better.”
The test asks whether architecture-by-scale interaction exists: quality,
throughput, or cost per completed workload changes more favorably for the
hierarchical arms as the number of issuers and linked analysis tasks increases.

## Factors

| Factor | Levels | Control |
|---|---|---|
| Gold database scope | 3 issuers / 48 cells, then 5 issuers / 80 cells only after promotion | Same four 2024 periods and four core metrics where the snapshot is Gold |
| Workload size | 1, 2, 3, 5 issuers | The requested issuer set is a subset of the selected Gold snapshot |
| Architecture arm | single-agent, hierarchical-no-critique, hierarchical-bounded-critique | Same model, prompt contract, source policy, tool policy, output contract |
| Repetition | At least 5 runs per cell | Fixed question IDs and deterministic input snapshot |
| Execution mode | Sequential and bounded parallel issuer workers | Record worker parallelism, queueing, and context budget in every manifest |

The 80-cell scope is not valid merely because 80 rows are present. Every new
cell must pass the existing source, definition, period, unit, provenance,
independent-review, and Gold-promotion gates.

## Primary measurements

1. Quality after human blind review: factual correctness, evidence support,
   task coverage, missing/conflict discipline, and citation correctness.
2. Cost per completed workload, not cost per attempted call.
3. End-to-end wall time and completed-workload throughput.
4. First-pass timeout/failure rate, recovery rate, and recovery cost.
5. Input/output tokens, model-call count, context size, and critique count.

All metrics must be reported by database scope, issuer count, arm, and
repetition. Recovered runs remain separate from uninterrupted first-pass
results.

## Fairness and isolation rules

- Single-agent and hierarchical arms receive the same prepared, valid Gold
  facts for the same question.
- Issuer workers may read only their scoped issuer/period/metric tools.
- The orchestrator may receive bounded summaries, not the full raw database.
- Context compaction fails closed when a budget would be exceeded; it must not
  silently drop issuer, period, metric, or provenance fields.
- Financial arithmetic remains deterministic code; models retrieve, explain,
  critique, and synthesize.
- No candidate, fallback, pending, or conflicting value enters a comparative
  run as if it were Gold.

## Interpretation rule

The current 1-to-3 issuer result is only a preliminary amortization signal:
relative hierarchical overhead narrows, but absolute cost and latency still
favor single-agent and quality has no stable winner.

A thesis-level “longer-term benefit” claim requires all of the following:

- at least three workload sizes and five repetitions per arm/size;
- a promoted Gold snapshot for every database scope used;
- human blind review of all comparative packets, with disagreements adjudicated;
- a measured interaction or slope consistent with the claim, not just one
  favorable endpoint;
- the benefit is stated with its trade-off: quality gain, throughput gain, or
  operational robustness must be weighed against cost and failure recovery.

If these conditions are not met, the defensible conclusion is that the study
found a bounded operational signal but did not establish a scaling advantage.

## Current gate

The 48-cell Gold snapshot is usable for the existing issuer-count sweep. The
separate 32-cell MBB/VCB expansion is not Gold: all rows are pending
validation/accelerator sourced, and its eight reserve-coverage candidates are
negative under the frozen definition. The larger-scope arm must therefore wait
for source reconciliation and independent review.
