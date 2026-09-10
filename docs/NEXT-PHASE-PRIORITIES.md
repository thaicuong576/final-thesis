# Next-phase priorities and decision gates

This document turns the current data-foundation findings into an executable
next phase. It is intentionally stricter than a feature roadmap: a working
prototype is not evidence of a defensible thesis result.

## Independent verdict

The applied multi-agent direction remains feasible, but the feasible thesis is
smaller than the original product-shaped ambition.

The best route is:

> source-grounded financial QA prototype + fair single-agent baseline +
> hierarchical comparison + bounded verification loop

The wider database is still an immutable staging and cross-check layer, but the
48-cell pilot now has a separate validated Gold snapshot. The main risk is not
whether three agents can be wired together; it is whether the same claims can
be checked against comparable, period-aligned, primary evidence at the intended
expanded scope.

## Reality snapshot

The following facts are recorded in the current project artifacts:

| Item | Current evidence | Interpretation |
|---|---:|---|
| Vendor candidates in the full proposed scope | 200/200 | Breadth exists; this is not accepted coverage. |
| Accepted gold cells | 44/48 pilot cells | The pilot Gold snapshot is promoted; the wider 200-cell scope is not accepted coverage. |
| Feasibility-pilot review | 48/48 reviewed and adjudicated | The original pilot plus the independent 3-cell ACB ROE addendum produce 44 valid and 4 reasoned-missing Gold cells. |
| Initial official ACB/VPB pilot PDFs with text layer | 0/7 | The initial files require OCR/manual labeling. |
| ACB alternate Q2 PDF with text layer | 0/1 | The official alternate file is also scan-only locally; search-index OCR is not accepted as page-stable evidence. |
| Additional VPB lookup PDFs with text layer | 4/4 | VPB's four pilot filing packages can use a searchable official route; metric mapping is still pending. |
| VPB performance-pack PDFs with text layer | 4/4 | The inspected KPI pages are standalone (`RIÊNG LẺ`); useful for cross-check or a separately frozen standalone option, not consolidated gold coverage. |
| VPB consolidated core candidates | 16 cells | Lookup filing tables support derived candidates for NPL, coverage, ROA, and ROE across four quarters; all are pending independent review. |
| ACB Q2 bounded OCR candidates | 2 target cells / 3 pending variants | The official alternate consolidated PDF is scan-only locally; RapidOCR recovered NPL and coverage inputs, while preserving two coverage-scope variants for manual adjudication. |
| ACB Q3--Q4 targeted visual candidates | 4 target cells / 4 pending rows | Page 17 of the official consolidated filings is visually readable; NPL and coverage inputs are recorded with locators but still require independent checking. |
| ACB Q1 issuer-IR capture | 2 target cells / 3 pending variants | The official issuer article supplies ROE and two CIC-scope NPL variants; raw HTML is hash-recorded, but definition and period-basis review remain pending. |
| ACB Q2--Q4 issuer-IR captures | 5 target cells / 6 pending rows | Q2 and Q4 article bodies are usable; the corrected Q3 route is usable while the earlier Q3 slug is recorded as a failed shell-only route. All candidate conventions remain pending. |
| ACB issuer-IR metric candidates | 4 quarters discovered | HTML updates may reduce OCR for selected metrics, but Q4 NPL wording conflicts and all candidates remain pending. |
| TCB official KPI candidates | 20 metrics + 5 evidence snippets | A promising KPI-first route, still pending definition and independent checks. |
| Unified official pilot candidate snapshot v3 | 55 pending candidate rows + 2 explicit missing placeholders | ACB/TCB/VPB official inputs are assembled with 18 source records and 42 evidence snippets; three ACB Q2--Q4 ROA candidates were added from statement inputs, but no labels or values are promoted. |
| Unified official pilot candidate snapshot v4 | 58 pending candidate rows + 2 explicit missing placeholders | Adds three ACB Q2--Q4 consolidated ROE candidates with formula/input/page provenance; their independent addendum is complete and selected into the v2 ledger. |
| Adjudicated review ledger and labels | 48 final cells; v2 exports 144 rows | v1 remains immutable; v2 audits eligible and selects the completed `checker_b` addendum. The promoted Gold retains 141 deduplicated labels plus 44 valid and 4 missing observations. |
| Promoted pilot Gold snapshot | 44 valid + 4 reasoned-missing | `gold-bank-2025-pilot-v1-adjudicated-v2.sqlite` has a clean audit (`finding_count=0`) and passes the baseline input gate. |
| Candidate snapshot read-only audit | 1 versioned JSON report | The metric snapshot schema, issuer/period coverage, and duplicate groups are audited; the only finding is the expected pending-source condition. This does not make the snapshot Gold. |
| Deterministic evaluation scoring scaffold | Contract + aggregation CLI | Reviewer-supplied claim scores can be aggregated per arm/dimension/reviewer while unscorable claims remain visible; no comparative result is generated before Gold and blind output review. |
| Versioned prompt contract | `prompt-contract-v1` + manifest binding | Shared arm instructions and output rules are documented; `ExperimentRunConfig` requires the version and every generated manifest records it. Provider prompt calibration remains gated. |
| Pilot question-set protocol coverage | 14 full-draft questions + 13-question core set | The full set covers macro-to-bank interpretation, a known ACB evidence conflict, and all three retained anomaly-trigger IDs. The core set permits a bank-only primary aggregate; official macro observations remain a blocker only for the separate macro extension. |
| Pre-Gold baseline execution plan | 42 planned jobs | Each of the 14 questions is expanded across the three arms with a snapshot placeholder and exact question-set hash; no provider call or comparative claim is made. |
| Gold-bound bank-core execution plan | 39 planned jobs | `baseline-plan-core-gold-v1.json` is bound to the promoted Gold snapshot and validates cleanly; it is planned, not executed. |
| Blind source-navigation index | 48/48 target cells mapped; 2 explicit source gaps | The v3 index is generated from the v3 snapshot, exposes only primary-source paths and coarse locators, strips candidate values/quotes/semantic extraction hints, and is not a Gold artifact. |
| Independent checker/adjudication status | A: 48/48; B: 48/48; addendum 3/3 | The original two-checker review is complete; 40 accepted mapping differences plus one NPL conflict were explicitly adjudicated. The separate ACB ROE addendum is complete and Gold promotion passed. |
| Private Checker-A elapsed-throughput signal | 48 rows in 0.4308 hours; 111.4 rows/hour | Planning-only timestamp signal from one private pass; it is not human OCR/manual throughput, independent-review evidence, or Gold evidence. See `reports/data-foundation/pilot-review-throughput-signal.md`. |
| Deterministic foundation tests | 200 passing | The validation, independent-review gate, adjudication source-slot, per-target-cell value-check gate, evidence-label preservation, query boundary, TTM profitability formulas, finite numeric boundary validation, blind-review merge/import path, scoped fallback-review materialization, question-bound run-manifest provenance, unified candidate assembly, blind vendor-context exclusion, complete-register export gate, direct CLI paths, offline three-arm harness, agent provenance guard, macro-evidence routing, macro-indicator scope binding, payload agent-role/ticker/period/metric-scope/metadata/provenance binding, conservative anomaly-trigger rules, snapshot-coverage-policy binding, review-progress instrumentation, duplicate-publishable-cell promotion guard, reviewed-snapshot promotion path, unique review-label identity, pilot comparability-matrix coverage, candidate-schema audit routing, evaluation scoring contract, scoring CLI, question-set protocol-coverage, macro-question data-gate, typed question-set contract, validator CLI, baseline-plan, telemetry-contract, blind-navigation-index leakage checks, adapter-context isolation, cross-call worker isolation, identical-prepared-facts fairness, typed question-set dispatch gate, question issuer/period/metric binding, frozen-peer-set benchmark filtering, valid-source query enforcement, source-tier policy filtering, unknown-policy fail-closed behavior, complete multi-period trend context, per-period anomaly scanning, multi-period manifest provenance, fail-closed one-job baseline execution, plan-to-manifest job identity, full-plan preflight validation, core plan validation, secret-free provider configuration, provider-backed pre-dispatch binding, structured provider response parsing and telemetry boundary, deterministic prompt rendering, canonical prompt forwarding, offline structured-provider boundary integration, per-call prompt fingerprinting, prompt-version binding, request-level prompt-version propagation, and manifest-level prompt-version mismatch rejection, non-empty request prompt validation, evaluation-run binding, and the addendum merge path are testable. |

Therefore the honest status is **foundation-ready for reconciliation and
scaffolded build work; not ready for comparative performance claims**.

## Assumption audit

| Assumption | Why it may be wrong | Test before relying on it |
|---|---|---|
| Five banks × eight quarters is a reasonable minimum | 200 cells create a large review burden, and source formats are not uniform. | Complete the 48-cell pilot and measure review time, missingness, and conflict rate. |
| Vendor fields represent the thesis metrics | Negative staged CIR and reserve-coverage values indicate unresolved sign or semantic mappings. | Reconcile each metric to an official label, formula, unit, and period basis. Never fix by taking absolute values. |
| A downloaded PDF is usable evidence | The initial seven PDFs are scan-only, while the four VPB lookup PDFs have text layers; neither fact proves metric comparability. | Require page/table evidence, metric mapping, and a checker decision per accepted row. |
| Official issuer HTML is automatically comparable | ACB's Q4 issuer pages report different NPL conventions (including versus excluding CIC). | Preserve both candidates and adjudicate definition, period, and denominator before acceptance. |
| Performance-pack KPI pages are consolidated | The inspected VPB KPI pages explicitly use the standalone/`RIÊNG LẺ` basis. | Keep them out of the consolidated pilot unless the scope is explicitly changed to standalone. |
| More rows make the database academically stronger | Unchecked rows can create false precision and contaminate peer statistics. | Promote only source-backed rows into a separate gold snapshot. |
| Multi-agent is the thesis contribution by itself | Decomposition can add latency and cost without improving answer quality. | Compare tool-equivalent single-agent, hierarchical, and hierarchical-plus-critique arms. |
| Four metrics are equally comparable across issuers | NPL and coverage labels may differ between issuer presentations and statements. | Maintain a per-metric comparability decision; allow conditional metrics and explicit nulls. |

## Priority 0 — freeze the research contract, not the maximum dataset

Freeze these now, independent of the final row count:

1. The research question: whether hierarchical decomposition and bounded
   verification improve factual correctness, evidence traceability, and anomaly
   handling enough to justify extra calls, latency, and cost.
2. The three arms: single-agent; hierarchical without critique; hierarchical
   with at most two focused verification attempts.
3. The fixed question set, output contract, source hierarchy, model/configuration,
   scoring rubric, and run logging fields.
4. The rule that every arm receives the same accepted facts and evidence tools.
5. The rule that no arm may use pending staging rows as published facts.

The full question set includes one macro-to-bank case and one pre-registered
missing/conflict case. The bank-core question set excludes only the macro case,
so its 39 planned jobs can be prepared as the primary comparison after bank Gold
promotion. The macro case cannot be scored until period-aligned official macro
observations are accepted; fallback macro retrieval remains staging only.

Do **not** freeze five banks × eight quarters as the final empirical scope until
the pilot passes. Advisor confirmation is still required, but the first question
for confirmation should be whether the advisor accepts this gated scope
strategy, not whether 200 unchecked cells should be promised.

## Priority 1 — run a time-boxed feasibility pilot

Use the proposed pilot as the go/no-go experiment:

- issuers: ACB, TCB, VPB;
- periods: 2024_Q1–2024_Q4;
- core metrics: NPL group 3–5, loan-loss-reserve coverage, ROA, ROE;
- CIR and NIM: conditional until their definitions and signs reconcile.

For each cell, record one of:

- accepted: official source, locator, definition, unit, period basis, and checker;
- conflicting: competing values with the conflict preserved;
- missing: null plus a concrete missing-source reason;
- invalid: source or extraction failed a quality check.

The pilot passes only if:

- at least 90% of the selected core cells are accepted or have an explicit,
  reviewable exclusion reason;
- every issuer and metric has evidence coverage;
- no unresolved critical definition conflict remains in an included metric;
- at least 40 metric/evidence labels receive an independent check;
- actual review time and OCR/manual burden are recorded.

If four metrics do not pass, reduce the empirical core to the largest set of
three comparable metrics. This is a legitimate result; it is preferable to
pretending that a fourth metric is comparable.

## Priority 2 — choose the empirical scope using a decision tree

| Pilot outcome | Scope to freeze | Rationale |
|---|---|---|
| 48 cells pass and review burden is manageable | 48-cell pilot for the first reproducible benchmark; optionally expand to 80 | Safest undergraduate applied scope. |
| Pilot passes, but source work is slow or inconsistent | 80 cells: five banks × four quarters × four core metrics; CIR conditional | Better balance of peer diversity and execution risk. |
| Pilot and a second source sample pass with low conflict | Consider 200 cells: five banks × eight quarters × five metrics | Upper bound, not a requirement. |
| Pilot fails for one or more metrics/issuers | Freeze the largest fully source-reconciled subset and report gaps | Protects validity; do not manufacture coverage from vendor rows. |

The default first result is the **48-cell pilot**. The 80-cell design is an
optional expansion only after the pilot passes and measured review/OCR burden is
acceptable. The 200-cell design is an extension or stretch goal, not the
definition of thesis success.

There is now a concrete metric-reduced fallback before dropping an issuer:
`gold-bank-2025-pilot-fallback-36-v1` keeps ACB, TCB, and VPB for four quarters
with NPL, reserve coverage, and ROE (36 cells). The current official candidate
routes cover 35/36 of those cells; ACB Q1 coverage remains an explicit gap.
ROA is excluded only if its ACB route cannot be reconciled, and the fallback
requires advisor confirmation before it becomes the selected benchmark. This
preserves issuer and period diversity while preventing one unavailable metric
from forcing an unverified vendor substitution.

## Priority 3 — repair the data foundation before adding complexity

Use this source ladder:

1. issuer investor-relations KPI table or official results presentation;
2. issuer consolidated filing with page/table locator, preferring searchable lookup versions where available;
3. issuer performance-pack KPI pages only when the reporting basis matches the
   frozen scope; the inspected VPB pages are standalone and therefore remain
   cross-check candidates for this consolidated pilot;
4. bounded OCR or manual page labeling for a small, auditable subset;
5. structured vendor API as an accelerator and cross-check;
6. explicit missing value when none of the above is sufficient.

The database changes required are narrow:

- keep raw and staging SQLite immutable;
- create a separate versioned gold snapshot;
- add a per-cell reconciliation decision rather than overwriting vendor values;
- preserve source hash, publication time, page/table locator, period basis, unit,
  definition mapping, checker ID, and decision reason;
- compute peer medians and derived ratios only from accepted observations;
- keep unresolved vendor sign conventions visible in the quality report.
- export an eligible merged review ledger to validated `GoldLabel` JSONL rows;
  refuse ambiguous candidate-cell mappings and keep this export separate from
  the immutable candidate DB until an explicit gold-promotion step.
- use the unified pilot candidate snapshot assembled from the official ACB/TCB/VPB
  candidate JSONL files and source manifests; vendor-only rows must not
  masquerade as the official review target.

The project does not need a vector database, real-time feed, broad securities
coverage, or a production crawler to pass this phase.

## Priority 4 — build the minimum system in parallel with Chapters 1–4

Build order after a promoted gold snapshot:

1. deterministic read-only query and evidence layer;
2. complete multi-period context and run-manifest support for trend questions;
3. fail-closed execution of one validated baseline job;
4. single-agent baseline;
5. hierarchical Macro/Sector/Company routing;
6. bounded critique and anomaly triggers;
7. reproducible run manifest and evaluation report.

While reconciliation runs, write only the stable parts of Chapters 1–4:

- problem, scope, and non-goals;
- metric definitions and source hierarchy;
- contracts, data-quality gates, and system architecture;
- experiment arms and scoring rubric.

Do not write comparative results, claims of superiority, or “live database”
claims before the gold snapshot and blind review are frozen.

## Phase-transition rule

The project is in a guarded transition, not yet in the baseline-experiment
phase:

| Allowed now | Still blocked |
|---|---|
| Deterministic query/evidence layers, schema contracts, multi-period context, offline adapters, fixtures, review workflow, and Chapters 1–4 drafts | Provider-backed comparative runs, live retrieval, agent-performance claims, and deployment claims |

The transition to the next phase is triggered by a versioned gold snapshot,
coverage/missingness report, at least 40 independently checked metric/evidence
labels, and a `READY_FOR_BASELINE` decision. The existing runtime scaffold is
therefore preparation for the next phase, not experimental evidence.

## Next sprint acceptance checklist

The next sprint is complete when all of the following exist:

- [x] advisor-facing one-page scope decision drafted using this decision tree (approval pending);
- [ ] completed 48-cell reconciliation register, including missing reasons;
- [x] draft metric comparability matrix for NPL, coverage, ROA, and ROE (review still pending);
- [ ] at least 40 independently checked labels;
- [x] blind reviewer copies and a two-checker merge/audit path;
- [x] source-only blind navigation index with candidate-context leakage checks;
- [x] fail-closed ledger-to-label export that does not mutate candidate data;
- [x] exporter requires the complete 48-cell register and rejects partial ledgers;
- [x] offline fixture runner produces three non-comparative manifests with fixed call budgets;
- [x] trend runtime requires the complete ordered period list and records it in call/run manifests;
- [x] one baseline job validates plan identity and typed question metadata before dispatch;
- [x] executed plan jobs preserve stable job identity in the runtime result and manifest;
- [x] serialized baseline plan has a read-only hash/coverage/binding preflight CLI;
- [x] Gold promotion and baseline input gates require a value-check label for every target cell;
- [x] pre-Gold planner expands the fixed question set into 42 non-executing arm jobs;
- [x] metric-reduced 36-cell fallback manifest records the measured ROA contingency without changing the default 48-cell scope;
- [x] isolated blank 36-cell fallback review copies are materialized and explicitly marked advisor-pending;
- [x] bank-core question set separates the 39-job primary comparison from the 3-job macro extension;
- [x] deterministic anomaly-trigger scaffold records conservative missing-value
      and explicitly configured same-unit deviation triggers;
- [x] read-only review progress reporter measures completion, disagreement, and
      timestamp-based throughput without mutating reviewer files;
- [x] reviewed-snapshot promotion adapter verifies labels, preserves candidate
      immutability, and delegates final gold validation;
- [x] unified official pilot candidate snapshot with explicit missing-cell
      placeholders;
- [ ] measured OCR/manual review throughput and conflict rate;
- [ ] promoted gold snapshot, or a written fail-closed report explaining why it
      could not be promoted;
- [x] fixed question set and blind scoring rubric drafted (freeze pending Gold);
- [x] Chapter 1–4 drafts linked to durable artifacts (results remain gated);
- [x] guarded baseline/query/runtime scaffolding is present without provider calls;
- [ ] provider-backed baseline execution starts only if the readiness gate is green.

The kill condition is explicit: if a metric cannot be sourced comparably within
the time-box, remove it from the core evaluation and state the limitation. Do
not add agent complexity to compensate for a data-definition failure.
