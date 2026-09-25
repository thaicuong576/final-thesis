# Decisions

## D-001: Data-first implementation

Status: Accepted.

The project begins with source research, coverage measurement, normalization, metric definitions, and a gold validation set before implementing the full multi-agent loop.

Reason: agent quality cannot be evaluated on incomplete or unverified data.

## D-002: Deterministic financial calculations

Status: Accepted.

Python code calculates financial ratios, peer statistics, period conversions, and anomaly triggers. Language models may explain or investigate results but must not be the source of arithmetic truth.

## D-003: Fair single-agent baseline

Status: Accepted.

The primary baseline uses the same prepared dataset, deterministic tools, questions, evidence policy, model configuration, and output contract as the hierarchical system.

Reason: the comparison must measure architecture rather than data, model, or prompt differences.

## D-004: Primary-source hierarchy

Status: Accepted.

Official filings, company IR, SBV, GSO, HOSE, and HNX sources are preferred for factual claims. Research reports and fallback APIs are contextual supplements or cross-checks, not substitutes for primary data.

## D-005: Reproducible local storage first

Status: Accepted.

The first implementation uses cached raw files plus versioned SQLite/Parquet derivatives and a local evidence index where needed.

Reason: local snapshots make experiments repeatable and reduce network dependence.

## D-006: Bounded critique loop

Status: Accepted.

The critique loop has a maximum of two verification attempts and reports unresolved anomalies rather than looping indefinitely.

## D-007: Scoped applied-thesis benchmark

Status: Provisional upper bound; first-baseline scope is governed by D-036.

The original five-bank/eight-quarter design remains a candidate upper bound:
VCB, ACB, MBB, TCB, and VPB across `2024_Q1` through `2025_Q4`, subject to
primary-source coverage checks before freeze. The first reproducible baseline
defaults to the gated 48-cell pilot described in D-036. Securities companies
and TCBS remain extension material.

Reason: the original 16-issuer/two-sector scope exceeds the data-validation and evaluation capacity of an applied undergraduate thesis and introduces unresolved TCBS and sector-definition risks.

## D-008: Separate staging from gold

Status: Accepted.

Existing raw files and staging databases remain immutable and pending validation. A new versioned gold snapshot is created only after coverage, period, unit, provenance, formula, evidence, and manual-label gates pass.

## D-009: Anomaly triggers are not presumed contradictions

Status: Accepted.

Deterministic rules may trigger focused verification, but a true contradiction requires an independent evaluation label. Explainable company-specific divergence, source conflict, and insufficient evidence are separate outcomes.

## D-010: Three-arm evaluation

Status: Accepted.

The evaluation compares single-agent, hierarchical-without-critique, and hierarchical-with-bounded-critique. A document-only baseline is optional descriptive context and cannot replace the tool-equivalent single-agent baseline.

## D-011: Vector retrieval is optional for the first experiment

Status: Accepted.

Metadata-filtered, page-aware document retrieval is used first. A vector index is added only if document-quality validation passes and a measured task requires it.

## D-012: Gated empirical scope

Status: Accepted as the working execution rule; advisor confirmation remains a governance checkpoint.

The 48-cell set (ACB, TCB, VPB; four quarters of 2024; four core metrics) is the
minimum feasibility pilot and the first possible benchmark scope. Expansion to
80 cells is conditional on measured coverage, conflict rate, and review effort.
The 200-cell five-bank/eight-quarter/five-metric design is a stretch option, not
a prerequisite for thesis success.

Reason: the database currently has broad staging candidates but no accepted gold
observations, and source accessibility is not uniform across issuers.

## D-013: Reporting-basis consistency

Status: Accepted.

Consolidated and standalone observations are separate evidence variants and must
not be mixed in one benchmark cell or peer statistic. For the current VPB pilot,
searchable consolidated lookup filings are the preferred route. VPB performance
pack KPI pages labeled `RIÊNG LẺ` are cross-check or standalone-scope candidates
only.

Reason: a text-layer document can still be semantically incomparable with the
frozen benchmark.

## D-014: Guarded pre-gold build and writing

Status: Accepted.

Before `READY_FOR_BASELINE`, the project may build deterministic query layers,
contracts, adapter scaffolds, fixtures, review tooling, and draft Chapters 1--4.
It may not run provider-backed comparative experiments, publish agent results,
or claim live/validated database coverage. These activities begin only after a
versioned gold snapshot and frozen blind-review protocol pass the readiness gate.

Reason: this keeps implementation and thesis writing moving without allowing
unverified data to become an experimental conclusion.

## D-015: Fail-closed independent-review gate

Status: Accepted.

Gold promotion and the comparative-input gate now require complete target-cell
coverage (`valid` or reasoned `missing`), at least 40 manual labels by default,
at least two checker IDs, and value-check coverage for every selected
ticker/metric and the minimum period sample. Evidence-support labels are copied
into the versioned gold snapshot when their evidence belongs to the selected
source set.

Reason: a label-count threshold alone can produce a superficially complete
snapshot while leaving selected entities or metrics unchecked, and dropping
evidence labels during promotion would break the provenance audit trail.

## D-016: VPB pilot profitability candidate convention

Status: Working candidate rule; independent review and advisor confirmation
remain required before promotion.

For the VPB pilot, the derived ROA candidate uses consolidated net profit after
tax and beginning/end average total assets. The derived ROE candidate uses
profit attributable to bank shareholders and beginning/end average equity. For
Q1--Q3, TTM profit is `prior_fy - prior_ytd + current_ytd`; for Q4, FY2024 is
the TTM flow. Candidate values are rounded to four percentage points and retain
the statement pages and supporting source IDs.

Reason: the searchable consolidated filings expose the necessary balance-sheet
and income-statement inputs, but the convention must be checked independently
before these candidates become gold observations or peer statistics.

## D-017: Blind review copies before ledger merge

Status: Accepted.

Checker A and checker B must work from separate copies of the review template.
Their copies are merged only after both are complete into a ledger with distinct
checker slots. The merge refuses incomplete copies, mismatched target sets, or
the same checker identity in both slots; disagreements remain explicit until an
adjudicator records the resolution.

Reason: a shared worksheet can expose the first decision to the second reviewer
or overwrite it, weakening the independence claim even when two names appear in
the final database.

## D-018: Provenance-complete offline run manifests

Status: Accepted.

Every future arm run must bind a snapshot ID and question ID and record the
observation IDs, source IDs, evidence IDs, prepared-context hash, call trace,
and contract-valid payloads. The implementation is first exercised with an
offline gold fixture; fixture manifests are explicitly marked non-comparative
and cannot be presented as thesis results.

Reason: a call count alone cannot prove that the three arms received the same
facts or that a claim can be traced back to the accepted snapshot.

## D-019: Question identity is part of the run contract

Status: Accepted.

Each `ExperimentRunConfig` must bind one `question_id` in addition to the
question-set ID. The pre-dispatch audit verifies that the ID exists in the
question-set file, and the run-manifest builder refuses a different ID.

Reason: binding only the question-set version is insufficient for reproducing a
specific evaluation item or preventing an accidentally mismatched prompt from
being logged under the wrong result.

## D-020: Explicit placeholders for uncovered pilot cells

Status: Accepted.

The unified pilot candidate snapshot creates one `missing` observation with a
reason for every required ticker/period/metric cell that has no official
candidate route. Missing placeholders may have null source ID, unit, period
basis, and locator; valid observations still require all of those fields. The
placeholder is reviewable and keeps coverage accounting complete without
inventing a source or value.

Reason: dropping uncovered cells makes the dataset look more complete than the
source corpus, while fabricating a sentinel source would contaminate provenance
and peer statistics.

## D-021: Blind reviewer copies must exclude vendor context

Status: Accepted.

Private checker copies contain only target identity (`ticker`, `metric`, and
`period`) plus reviewer-fill fields. They must not contain vendor values,
vendor locators, vendor source URLs, or the register's pending status. The
merged ledger may retain internal candidate context separately, but the
reviewer-facing artifact is generated from the v2 blind template.

Reason: the previous template shape exposed vendor candidate context despite
being labelled blind. Removing it reduces anchoring risk and makes the claim
of independent source review technically defensible.

## D-022: Offline runner is plumbing evidence, not experiment evidence

Status: Accepted.

The repository may generate a deterministic fixture database, question set, and
one run manifest for each of the three arms before the official gold snapshot
is ready. These manifests must use `environment=offline_fixture` and
`comparative_result=false`, use a fixed adapter and timestamp, and refuse
overwriting an existing output directory. They validate query/dispatch/manifest
plumbing only and must not be included in financial accuracy, latency, cost, or
multi-agent superiority claims.

Reason: the build phase can progress without weakening the data gate, provided
the fixture is visibly separated from source-grounded thesis results.

## D-023: Prepared agent context includes page-aware evidence

Status: Accepted.

The runtime's prepared context must include only evidence snippets returned by
the read-only query boundary for valid source records and the requested ticker
and period. Run manifests must collect the snippet `evidence_id` values along
with observation and source IDs. An empty evidence result remains explicit; it
cannot be replaced by a prose citation invented by an agent.

Reason: a source ID alone does not prove that the retrieved passage supports a
claim. Binding evidence snippets and their IDs makes citation completeness
auditable and keeps the single-agent and hierarchical arms on the same facts.

## D-024: Reject agent provenance not present in prepared context

Status: Accepted.

The runtime rejects an adapter payload if it references an observation ID,
source ID, or evidence ID absent from the prepared context. If an adapter
returns an evidence object, its complete serialized fields must match the
retrieved context object for that ID. This guard applies before a call is added
to the run trace.

Reason: contract-valid JSON is not enough to make a citation trustworthy. The
adapter must not be able to invent a source or alter a retrieved quote while
retaining the original evidence ID.

## D-025: Route macro evidence by period, not company ticker

Status: Accepted.

Company and sector evidence is filtered by ticker and period. Macro evidence is
filtered by period and valid macro source IDs, because macro snippets may have
no company ticker. Both sets are deduplicated into the shared prepared context
and their evidence IDs are recorded in every arm's run manifest.

Reason: applying the company ticker filter to macro evidence silently produces
a source ID without a supporting passage and makes macro claims impossible to
audit.

## D-026: Conservative, auditable anomaly-trigger rules

Status: Accepted.

The bounded-critique arm evaluates deterministic triggers against the prepared
facts and records them in the run manifest. Missing or unaccepted company and
sector values are always triggerable. Numeric company-versus-sector deviations
are triggerable only when a metric-specific positive threshold is explicitly
registered and both values have the same known unit. Explicit orchestrator
verification requests take precedence; otherwise requests are generated from
the trigger list and capped by the two-attempt critique budget.

Reason: anomaly detection should expose evidence gaps and pre-registered
comparability checks without silently converting a model assumption or a unit
mismatch into a contradiction. Independent reviewers still assign the final
anomaly outcome.

## D-027: Review throughput must be measured from reviewer timestamps

Status: Accepted.

The review workflow includes a read-only progress reporter for blind copies and
merged ledgers. It reports completed decisions, decision distribution, coverage
by issuer/metric, reviewer disagreement, and throughput only when valid
timestamps span a positive interval. Blank cells remain incomplete rather than
being counted as `missing`; the reporter never edits review files or promotes
candidate data.

Reason: the 48/80/200 scope decision depends on actual review burden and
conflict rate. A row count or a successful export command cannot substitute for
measured human review effort.

## D-028: Gold promotion rejects duplicate publishable target cells

Status: Accepted.

`create_gold_snapshot` rejects more than one `valid` or `missing` observation
for the same `(ticker, period, metric)` target cell. Pending or conflicting
alternatives remain in staging until reconciliation, but they cannot be copied
into gold as competing publishable facts.

Reason: deterministic query order must never decide between two unresolved
variants. A source or definition conflict must be adjudicated before a target
cell becomes part of the experiment snapshot.

## D-029: Promotion is a separate non-mutating reviewed-snapshot step

Status: Accepted.

The completed two-checker ledger and exported label artifact are inputs to an
explicit promotion adapter. It verifies that the label artifact matches the
review ledger, materializes a temporary reviewed staging database, marks only
review-selected sources/observations as publishable, represents reviewed
missing cells with a reasoned null, and delegates final validation to
`create_gold_snapshot`. Candidate databases and reviewer files remain
unchanged; unresolved `conflicting` or `invalid` decisions fail closed.

Reason: separating review from promotion preserves an audit trail and prevents
manual status edits from silently turning pending variants into gold facts.

## D-030: Pre-register complete evaluation case coverage

Status: Accepted.

The pilot question set contains 14 fixed questions: the 12 bank-scoped
snapshot/trend/peer/anomaly questions, one macro-to-bank interpretation case,
and one known missing/conflicting-evidence case. Anomaly questions declare
coverage metadata for the three retained deterministic trigger rules:
`company_metric_missing`, `sector_benchmark_missing`, and
`company_sector_deviation`. These declarations do not assert that a trigger or
anomaly exists in Gold; the frozen snapshot must determine that, and absent
evidence is reported as not-triggered or unscorable.

The macro-to-bank case is eligible only when the Gold snapshot contains
period-aligned, accepted official macro observations for `macro.policy_rate`
and `macro.credit_growth`. The current fallback macro data remains staging and
cannot be used to claim benchmark coverage.

Reason: a comparison can be numerically reproducible yet still omit the
macro-to-bank and evidence-conflict behaviors that motivate the hierarchy.
Pre-registering these cases makes the evaluation contract visible without
silently widening the bank issuer/period/metric scope or manufacturing labels.

## D-031: Bind the exact question-set bytes in every run manifest

Status: Accepted.

Every generated run manifest records `question_set_sha256`, computed from the
exact question-set file passed to the runner. The manifest writer and offline
fixture verify this binding; an ID alone is not considered sufficient evidence
that all arms used identical questions.

Reason: question-set edits can otherwise preserve the same human-readable ID
while changing the evaluated task, weakening cross-arm reproducibility.

## D-032: Fail closed when a macro question lacks accepted macro facts

Status: Accepted.

The experiment input contract checks the selected `macro_to_bank` question
against the snapshot before dispatch. Every requested indicator and period must
have a non-null, valid observation linked to a valid primary-tier source. A
missing macro table, missing observation, pending/fallback source, or invalid
question metadata blocks that question from running.

Reason: an empty Macro context would make the hierarchical comparison appear to
test macro reasoning while actually testing graceful absence. The benchmark may
still report a missing-data behavior deliberately, but it must not silently
claim macro-to-bank coverage.

## D-033: Pre-Gold baseline plans are non-executing artifacts

Status: Accepted.

Before Gold promotion, the project may materialize a deterministic plan with
one job per fixed question and experiment arm. The plan must use an explicit
`PENDING_GOLD_SNAPSHOT` placeholder, bind the exact question-set hash, and set
`comparative_result=false`. It must not open a provider, read pending financial
facts, or be interpreted as experiment output. After promotion, the placeholder
is replaced by the actual snapshot ID and every job is revalidated through the
input gate.

Reason: planning the next phase reduces implementation churn while preserving
the data-foundation boundary and preventing an execution artifact from being
mistaken for evidence.

## D-034: Preserve unavailable telemetry as unavailable

Status: Accepted.

The runtime may accept an adapter completion with provider telemetry for
latency, input tokens, output tokens, and cost estimate. When an adapter cannot
provide those measurements, the run manifest records `telemetry_status` as
`unavailable` and the corresponding values as `null`; it never substitutes
zeroes or estimates silently. Offline fixtures therefore test call shapes and
provenance, not model performance or cost.

Reason: invented zero-cost or zero-token values would bias the architecture
trade-off, especially against a multi-agent arm with more calls.

## D-035: Provide source navigation without candidate anchoring

Status: Accepted.

Independent reviewers need a practical way to find the official page or HTML
paragraph for each target cell, but exposing candidate values, quotes, or
semantic extraction hints would anchor their decisions. The project therefore
generates `blind-source-navigation-index-v3.csv` from the official candidate
snapshot in read-only mode. It includes only primary-source identity, local/URL
paths, coarse physical locators, and page-aware evidence metadata. Candidate
values, observation IDs, quotes, source notes, and raw `phrase`/`formula`/
`scope` locator tokens are excluded. A navigation row never counts as a review
decision, Gold label, or accepted source; the checker must inspect the original
source and fill their private blind copy.

## D-036: Make the pilot the first-baseline scope

Status: Accepted for the working scope; advisor confirmation remains open.

The first provider-backed baseline will use the 48-cell pilot by default:
ACB, TCB, and VPB across the four 2024 quarters and four core metrics (NPL
group 3--5, reserve coverage, ROA, and ROE). The original five-bank/
eight-quarter design remains a provisional upper bound. An 80-cell or 200-cell
expansion may be considered only after the pilot passes source reconciliation,
definition/conflict checks, and measured review throughput. The expansion is
not a prerequisite for the first reproducible thesis result.

Reason: the research question tests architecture trade-offs on a frozen,
source-grounded dataset; increasing unchecked cell count adds acquisition and
review risk without strengthening the causal comparison between agent arms.

## D-037: Keep a measured metric-reduced fallback

Status: Proposed; not the canonical scope.

If the 48-cell pilot cannot reconcile ACB ROA to the same primary-source and
period-basis standard as TCB and VPB, the project may ask the advisor to approve
a 36-cell fallback: ACB, TCB, and VPB across four 2024 quarters with NPL group
3--5, reserve coverage, and ROE. The current candidate assembly has official
routes for 35/36 of these target cells; ACB Q1 coverage remains an explicit
missing-source gap. The fallback is recorded in
`data/manifests/gold-bank-2025-pilot-v1/fallback-36-selection.json` and does not
authorize vendor substitution or automatic Gold promotion.

Reason: reducing one unverified metric preserves issuer and period diversity,
keeps the database rectangular, and gives the thesis a clean go/no-go path
without silently weakening the source policy.

## D-038: Make trend period scope explicit at runtime

Status: Accepted.

The typed `company_trend` question is a multi-period task, not four independent
single-period calls. The runtime therefore requires the complete ordered period
list declared by the question, prepares a separate read-only context for each
period, scans deterministic anomaly rules per period, and records the period
scope in `AgentCallRequest`, `RunCallTrace`, and `ExperimentRunManifest`.
Incomplete trend requests fail before adapter dispatch. Single-period question
behavior remains unchanged.

Reason: allowing a trend question to run with one period would produce a
plausible-looking answer with incomplete evidence and would make later arm
comparisons invalid. The explicit period scope preserves both correctness and
reproducibility without widening the database or introducing provider-specific
logic.

## D-039: Execute baseline work through one validated job boundary

Status: Accepted.

The first executable unit after Gold promotion is one `BaselineJob`, not an
unvalidated loop over plan JSON. `src/thesis_data/baseline_runner.py` checks
snapshot ID, question-set ID and exact hash, question ID, arm, issuer, ordered
periods, metric IDs, and macro indicator IDs before delegating to the guarded
runtime. The adapter is injected by the caller; the boundary has no provider or
network fallback. Trend jobs pass their complete multi-period scope as one
request, while the existing Gold and source-policy gates remain authoritative.

Reason: a plan file is configuration, not proof that the selected job still
matches the question set or runtime contract. A narrow execution boundary makes
the next phase reproducible and prevents accidental provider calls or silently
changed job scope while reconciliation is still incomplete.

## D-040: Preserve plan job identity in executed manifests

Status: Accepted.

When a baseline run is dispatched from a `BaselineJob`, its stable `job_id` is
carried through `RuntimeRunResult` and persisted by
`ExperimentRunManifest`. Direct offline fixture calls may omit the field for
backward compatibility, but plan-backed executions must remain joinable to the
exact question/arm row in the frozen plan.

Reason: `run_id`, question ID, and arm identify most of a run but do not prove
which plan row was executed. Explicit job identity makes a 42-job result set
auditable and prevents accidental mixing of reruns or manually altered config.

## D-041: Preflight the complete baseline plan before dispatch

Status: Accepted.

The serialized baseline plan must pass a read-only preflight before any job is
dispatched. `scripts/validate_baseline_plan.py` verifies the exact question-set
hash, one job per question/arm, snapshot and question-set identity, issuer,
periods, metrics, macro indicators, and non-comparative status. The committed
pilot plan contains 42 jobs and passes this preflight, but its
`PENDING_GOLD_SNAPSHOT` placeholder still prevents provider execution.

Reason: validating only individual jobs leaves omissions, duplicates, or stale
bindings possible in the complete run set. A plan-level check makes the next
phase auditable without opening the Gold gate early.

## D-042: Require a value-check label for every target cell

Status: Accepted.

Both Gold promotion and the comparative-input gate now require at least one
`value_check` label linked to an observation in every configured
`(ticker, period, metric)` target cell. The existing total-label, checker-count,
metric-pair, and minimum-period checks remain in force. Missing cells must use a
synthetic reasoned observation and still receive a value-check decision; labels
from other cells cannot satisfy the missing cell.

Reason: aggregate label counts can look sufficient while an individual target
cell has never been reviewed. Cell-level coverage is the smallest invariant
that keeps a rectangular benchmark honest and makes the review register and
Gold snapshot semantically align.

## D-044: Separate the bank core benchmark from the macro extension

Status: Accepted as an execution guard; advisor confirmation of the overall
scope remains open.

Keep `experiments/question-set-v1.json` as the full draft, and add
`experiments/question-set-core-v1.json` with the 13 non-macro questions. The
core benchmark is the primary 39-job comparison across the three arms. The
`TCB_macro_to_bank_q4` question remains a pre-registered three-job extension
and may be run and reported separately only after period-aligned official macro
observations pass the Gold gate.

This does not remove the Macro Agent from the architecture and does not permit
fallback macro values to enter the benchmark. It prevents one unverified macro
domain from blocking the bank/sector/evidence comparison while keeping the
limitation explicit: the core result does not establish macro-to-bank reasoning
quality.

Reason: the bounded official SBV check established a usable rate source route,
but did not establish a 2024_Q4 year-end credit-growth observation. The current
macro fallback is explicitly pending validation. Separating evaluation tracks
preserves the research comparison and avoids a stronger-than-supported claim.

## D-045: Add formula-derived ACB ROA candidates without promoting them

Status: Accepted as a candidate-assembly decision; independent review still
required.

The v3 official pilot candidate snapshot adds ACB `bank.roa` TTM candidates for
`2024_Q2`, `2024_Q3`, and `2024_Q4`. They are calculated from visually checked
consolidated PAT and total-asset statement inputs using `roa-ttm-v1`, with the
input facts, page locators, source IDs, and annual-flow convention preserved in
candidate metadata. ACB `2024_Q1` ROA remains an explicit missing placeholder.

The new rows remain `pending_validation`; they do not change the canonical
48-cell register, create Gold labels, or authorize a baseline run. A Checker B
must independently verify the transcription and period convention before any
promotion. If the ROA metric later fails comparability, the documented 36-cell
fallback remains available as an advisor-approved option.

Reason: the existing ACB filings already expose the required PAT and balance
inputs. Recording a deterministic derived candidate improves measured source
coverage without substituting a vendor ratio or hiding the remaining Q1 gap.

## D-046: Version the prompt contract in every run manifest

Status: Accepted for the guarded build.

`ExperimentRunConfig` requires a non-empty `prompt_version`, and the run
manifest copies it alongside the snapshot ID, question-set hash, rubric, model,
and source policy. The current scaffold version is `prompt-contract-v1`, whose
shared and arm-specific rules are documented in
`docs/PROMPT-CONTRACT-VI.md`. The offline fixture uses its own explicit
`offline-fixture-prompt-v1` label. Every runtime `AgentCallRequest` carries the
same non-empty value, rejects an empty value, and manifest construction rejects
any call/configuration mismatch.

Changing role instructions, context layout, output rules, or verification
wording requires a new prompt version. This makes prompt drift observable and
prevents a later comparison from mixing configurations while still leaving
provider prompt calibration gated behind Gold readiness.

## D-047: Preserve the ACB Q1 source gaps after a bounded route check

Status: Accepted as a fail-closed source decision.

The inspected official ACB 2024 financial-statements route did not yield a
located `2024_Q1` consolidated attachment. The already captured official Q1
issuer-IR article does not fully specify the frozen pilot's reserve-coverage or
ROA observations. A Q1 PDF discovered on a secondary-hosted attachment URL is
excluded from Gold provenance under the current primary-source rule.

Keep ACB `2024_Q1` `bank.llr_coverage` and `bank.roa` as explicit missing
placeholders in the v3 candidate snapshot. Do not substitute a vendor ratio,
infer Q1 ROA from unrelated periods, or treat the secondary copy as official
evidence. The 48-cell pilot, its 36-cell contingency, and the `NOT_READY`
decision remain unchanged. The route evidence is recorded in
`reports/data-foundation/official-acb-q1-route-audit.md`.

Reason: an explicit missing cell is scientifically safer and easier to defend
than a numerically complete but provenance-inconsistent benchmark. If the
primary route remains unresolved after the time-box, the metric or target must
be narrowed with the limitation stated rather than hidden by source
substitution.

## D-048: Bind scoring records to one frozen evaluation configuration

Status: Accepted for the evaluation scaffold.

Each `ClaimReview` must carry its `run_id`, snapshot ID, question-set SHA-256,
rubric version, prompt version, and model ID. The deterministic scorer rejects
mixed snapshot, question-set, rubric, prompt, or model bindings before
aggregation; different run IDs remain allowed because one benchmark contains
multiple questions and arms.

Reason: a score table is not reproducible merely because it contains an arm and
a question ID. Without the frozen-run binding, claims from different snapshots
or prompt/model configurations could be aggregated while appearing to be one
comparison. The binding guard improves auditability without generating or
interpreting any model result.

## D-049: Allow guarded build and Chapters 1–4 before Gold

Status: Accepted for the current phase transition; empirical baseline
execution remains gated.

After the deterministic foundation checkpoint passes, the project may proceed
with read-only query/evidence layers, contract validation, offline fixtures,
run-manifest tooling, prompt drafts, and Chapters 1–4. This permission does not
allow provider-backed execution, live retrieval, comparative performance
claims, or results chapters before the readiness decision becomes
`READY_FOR_BASELINE` and a versioned Gold snapshot is promoted.

Reason: building and documenting stable interfaces now reduces implementation
churn and makes the later experiment reproducible, while keeping unvalidated
financial data and premature model comparisons out of the thesis evidence.

## D-050: Bind agent output scope and finite numeric claims

Status: Accepted for the guarded runtime contract.

Before a payload is published or enters provenance validation, its `agent_id`
must match the request role; its period must match the request period; its
ticker must match for non-macro roles; and its metric maps must stay within the
role-specific request scope. Published metric/benchmark fields require unit
and in-scope period metadata, while non-null numeric values require at least
one observation, source, or evidence reference. All numeric boundary models
reject `NaN` and infinite values.

Reason: a payload can be syntactically valid and still answer another issuer,
period, or metric—or publish an untraceable/non-finite number. These checks
protect the fairness and auditability of the later three-arm comparison without
requiring a provider or widening the empirical scope.

## D-051: Keep provider I/O behind an injected transport boundary

Status: Accepted for the guarded build; provider execution remains gated.

`src/thesis_data/provider_adapter.py` provides only a provider-neutral
`StructuredProviderAdapter`. It accepts a caller-injected `ProviderTransport`,
parses typed or JSON responses into `AgentPayload`, and carries typed
`AgentCallTelemetry` into the runtime. Missing telemetry is either rejected or
recorded explicitly as unavailable according to the secret-free provider
configuration. Malformed responses and transport failures fail closed.

The module must not create a provider client, resolve secret values, access the
network, retrieve financial data, or promote a snapshot. An external provider
transport implementation is a separate post-Gold change and must still pass
the existing provider configuration, `READY_FOR_BASELINE`, and run-manifest
gates. A deterministic local fixture transport is allowed only to exercise
this boundary offline; it is not provider evidence and must remain
non-comparative.

Reason: the thesis needs an executable and testable adapter seam, but coupling
that seam to a provider now would make accidental calls and unverifiable
results easier before the data foundation is ready. Dependency injection keeps
the offline harness and the later provider experiment on the same typed
contract.

## D-052: Canonicalize prompts before provider transport

Status: Accepted for the guarded build; prompt calibration remains gated.

`src/thesis_data/prompting.py` renders each `AgentCallRequest` into a stable
provider-neutral prompt containing the prompt version, role instruction,
question identity, issuer/period scope, metric/indicator scope, and canonical
prepared context JSON. `StructuredProviderAdapter` passes that exact rendered
prompt to the injected transport. A transport must not rebuild the prompt or
silently choose a different scope/version.

Unknown roles, missing questions, and non-JSON-safe context fail closed before
transport dispatch. This renderer is deterministic plumbing for offline replay;
it is not a claim that prompts have been calibrated or that any model has been
run.

Reason: prompt drift can invalidate a comparison even when the database,
question set, and model ID are unchanged. Centralizing rendering preserves a
single prompt contract across single-agent and both hierarchical arms without
introducing provider or network behavior before Gold readiness.

## D-053: Fingerprint canonical prompts in run traces

Status: Accepted for the guarded build; legacy manifests remain readable.

The current `build_run_manifest()` computes and records
`RunCallTrace.prompt_sha256` from the exact canonical prompt returned by
`render_agent_prompt()`. It stores only the SHA-256 fingerprint, not the full
context-bearing prompt. The field is optional when reading older schema-version
2 manifests, but every newly generated trace with a renderable request carries
the fingerprint.

Reason: `prompt_version` is necessary but depends on disciplined manual version
bumps. A per-call fingerprint gives the later evaluation an inexpensive way to
detect accidental prompt drift across arms without duplicating sensitive or
large context in manifests. This is an additive audit field and does not alter
the empirical scope or open provider execution.

## D-054: Exercise the provider boundary with a deterministic offline transport

Status: Accepted for the guarded build; external provider execution remains
gated.

`src/thesis_data/offline_fixture.py` routes `OfflineFixtureAdapter` through the
same `StructuredProviderAdapter` used by the later provider-backed path. Its
`OfflineFixtureTransport` returns only deterministic test payloads, uses an
`offline_fixture` configuration with network disabled, and reports telemetry as
explicitly unavailable. The fixture remains `comparative_result=false` and
must not read secrets, call a provider, or use financial data.

Reason: unit-testing the provider boundary alone could leave the real offline
batch path bypassing it. Exercising the same boundary in the fixture catches
integration drift before Gold is ready while preserving the no-provider and
no-comparative-claim gates.

## D-055: Freeze the missing-data policy

Status: Accepted for the pilot and all later benchmark scopes.

The project must not guess, silently fill, or silently impute a missing
ticker/period/metric cell. A cell with no sufficiently comparable evidence is
recorded as `value=null`, `quality_status=missing`, with a concrete reason such
as no approved primary source, unreadable/unstable document evidence, or an
unresolved metric-definition conflict. Conflicting candidates remain visible
until resolved; the system must not choose one without a recorded decision.

Fallback sources may be used only when the source tier and route were explicitly
approved before the review/run and are recorded in the applicable manifest or
decision. Vendor values remain cross-check material unless the approved source
policy says otherwise; they may not silently fill a missing official cell.

Numeric accuracy and peer/statistical averages use only accepted numeric Gold
observations. Reasoned missing cells are excluded from those numeric denominators
but are counted and reported explicitly by ticker, metric, and period. The
evaluation must score the system's missing-data behavior separately, for example
whether it correctly says that a value is unavailable. Reports must expose the
expected count, valid count, missing count, conflict/unresolved count, and the
denominator used for every aggregate. Dropping a missing cell without a visible
count is a policy violation.

Reason: fabricated completeness would contaminate peer statistics and make the
three-arm comparison unfair. Explicit missingness is scientifically preferable
to an unsupported number and lets the thesis distinguish data limitation from
agent failure.

## D-056: Adjudicate checker disagreements with an explicit source slot

Status: Accepted for the 48-cell pilot; the v2 Gold promotion passed after the
independent ACB ROE addendum, while wider scope remains subject to the same
coverage and source-acceptance gates.

The merged two-checker ledger must preserve both original checker slots. When
accepted rows disagree in value or source mapping, adjudication must record an
explicit `adjudication_source_slot` (`checker_a` or `checker_b`) and a reason.
The selected slot is the only mapping used by downstream label export and
promotion; the originals are never overwritten. A non-accepted resolution may
not carry a source slot, and all adjudication rows require an adjudicator,
timestamp, and reason.

For the pilot v1 overlay, 40 accepted mapping disagreements select Checker A;
ACB Q3 NPL selects the exact official-table derivation (while recording the
1.49% IR variant as a rejected alternative); and ACB Q1 NPL is resolved to
reasoned missing because the available CIC/group-3--5 variants are not
canonical enough to choose. The result is 41 accepted and 7 reasoned-missing
final cells, with 141 non-mutating labels exported. This does not itself make
the candidate snapshot Gold: promotion still requires accepted sources and
per-metric coverage.

The three new ACB Q2--Q4 ROE candidates in the v4 candidate snapshot were not
silently added to the original adjudicated result. A fresh, vendor-free
three-cell Checker-B addendum independently accepted them as consolidated TTM
ROE routes. The versioned v2 ledger selects `checker_b` for those three cells,
the v1 ledger remains unchanged, and the resulting Gold snapshot has 44 valid
and 4 reasoned-missing cells.

## D-057: Preserve multi-source provenance for derived TTM review

Status: Accepted for the MBB expansion review; implementation is backward
compatible with single-source review rows.

A derived TTM observation may depend on the current-quarter filing and a
prior-fiscal-year filing. Reviewers may therefore cite multiple source IDs and
URLs in the existing source fields, separated by `|` or `;`. The importer must
validate every cited source against the candidate database, map the reviewed
value to the candidate observation whose primary source FK matches one cited
source, and preserve the complete citation in the review label note. It must
never replace the candidate observation's single source FK with a composite
string. Promotion marks every explicitly cited source valid when the accepted
review is promoted.

Reason: requiring one source ID for a multi-document TTM calculation would
either lose the prior-year input provenance or force the candidate schema to
invent a composite foreign key. Parsing the existing reviewer notation keeps
the raw review copies immutable and makes the dependency auditable.

## D-058: MBB ROE remains reasoned missing until denominator is frozen

Status: Accepted for the MBB expansion adjudication; reopening requires an
explicit metric-definition decision and a fresh review of the affected cells.

Both independent MBB checkers identified the same unresolved denominator
choice: average parent-attributable equity versus average total consolidated
equity. The working metric dictionary specifies the equity-based ROE family
and the parent-attributable profit convention, but does not select between
these two equity denominators for MBB. The adjudication therefore records all
four MBB ROE cells as `missing` under the missing-data policy. No ROE candidate
variant is silently promoted, and the MBB scope fails the 90% metric-coverage
gate until the definition or the scope is explicitly changed.

Reason: the two formulas are both reproducible, but choosing between them
without a frozen convention would contaminate cross-issuer comparisons and
make the apparent database expansion stronger than the evidence supports.

## Open decisions

- Advisor confirmation of the five-bank/eight-quarter primary scope.
- Final issuer selection after official-source coverage checks.
- Exact benchmark cutoff and publication-availability rule.
- Final source endpoints, licensing conditions, and manual-retrieval policy.
- Final metric variants for NIM, ROA/ROE, CASA, LDR, and CAR.
- Gold-label reviewer assignment and final question-set size.
- Model provider/version and prompt configuration.
- PDF parser and embedding model, if vector retrieval is needed.
- Preview deployment target after local evaluation is stable.

## D-057: Treat the complexity-ladder result as a bounded negative scaling result

Status: Accepted for the current evaluation scope; broader database scaling
remains a separate future experiment.

The complexity pilot expands the user workload while holding the promoted Gold
snapshot, model, source policy, and missing-data policy fixed. Tier 2 covers
three issuers across four quarters, four metrics, and six linked tasks; Tier 3
adds the multi-issuer landscape workload. The run completed 10 of 12 jobs; both
hierarchical Tier 3 jobs timed out. In Tier 2, primary mechanical quality rates
were tied across arms while hierarchical no-critique cost 2.00x and latency
2.56x the single-agent arm, and bounded critique cost 2.83x and latency 3.47x.

No multi-agent break-even tier was observed. This is evidence about the tested
workload range and current sequential orchestration, not proof that multi-agent
systems cannot outperform single-agent systems at a larger or genuinely
parallel scale. Human blind adjudication remains required before thesis-level
superiority claims.

Reason: separating workload complexity from database expansion prevents a
confounded result. Database growth must be gated by Gold coverage and manual
review before being used as a new independent variable.

## D-058: Treat parallel/context engineering as a feasibility improvement, not a superiority result

Status: Accepted for the next evaluation stage; comparative superiority remains
unproven.

The controlled expansion candidate increases the selected scope from 48 to 80
cells by adding MBB and VCB, but its 32 added rows remain
`pending_validation` and are not Gold. The parallel complexity package uses
bounded issuer-worker parallelism, a fail-closed context budget, role-isolated
tools, and explicit telemetry. These changes improve the system's ability to
attempt larger composite workloads, but they do not justify calling the
hierarchical arms better.

The recovered 12-job package completed after retries, while the original
uninterrupted provider batch completed 10/12 and had two Tier 3 hierarchical
timeouts. Tier 2 bounded critique tied the single-agent arm on the mechanical
Gold checks, but cost $0.0888 versus $0.0337 per completed job and had lower
throughput. No bounded-critique break-even point was observed. The result must
therefore be reported as a bounded feasibility/operational finding, with raw
first-pass failures and recovery attempts shown separately.

Reason: parallelism can reduce waiting time without reducing token use, and a
larger context can expose more coordination and validation failure modes. The
long-term multi-agent hypothesis requires a workload-size sweep, repeated runs,
independent human adjudication, and a Gold-reviewed database expansion before
it can become a thesis-level causal claim.

## D-059: Use the issuer-count sweep as an amortization signal, not a scaling-law claim

Status: Accepted as preliminary evidence; human adjudication and larger Gold
coverage remain required.

The scaling sweep holds the 48-cell Gold snapshot, model, prompt contract,
source policy, and four-quarter/four-metric scope fixed while varying the
issuer count from 1 to 3 and repeating each size twice. The recovered package
contains 18/18 valid manifests after three explicit retries, while the first
uninterrupted pass was 15/18. Multi-agent remains more expensive and slower in
absolute terms at every size, but its relative cost overhead versus
single-agent narrows as issuer count increases. This is consistent with a
possible fixed orchestration overhead being amortized; it is not evidence of an
asymptotic advantage or a break-even point.

Mechanical quality has no stable monotonic multi-agent improvement. Human review
of all 18 blind packets/108 rubric rows is therefore required before using the
sweep in final thesis claims. The separate 80-cell MBB/VCB candidate remains
outside the sweep until its 32 rows receive independent source review and Gold
promotion decisions.

Reason: a long-term claim needs a slope/interaction signal, not a single
small-vs-large comparison. Repeated issuer-count workloads make the proposed
amortization mechanism testable while keeping the database factor controlled.

## D-060: Block the 80-cell expansion on semantic candidate-quality failures

Status: Accepted as a fail-closed data-quality decision.

The MBB/VCB 32-cell expansion remains a review candidate and is not Gold. The
candidate audit found all 32 rows still marked `pending_validation` and sourced
from the `accelerator` tier. More importantly, all eight
`bank.llr_coverage` candidates are negative, although the frozen metric
definition is `loan_loss_provisions / NPL_balance × 100`. The system must not
convert these values with `abs`, infer a sign convention, or count them as
validated coverage. Each row requires independent primary-source reconciliation
of field mapping, sign, unit, period basis, and consolidated/standalone scope.

Reason: representing every target cell is not equivalent to having usable
coverage. This gate turns a concrete semantic data error into an auditable
failure instead of allowing a larger database to create a false impression of
readiness or improve a multi-agent experiment by contaminated inputs.

## D-061: Carry forward only disjoint, eligible review scopes

Status: Accepted for the MBB v3 review workflow.

The previously adjudicated MBB ROA/ROE ledger may be reused for the v3
candidate snapshot only as an immutable, explicitly scoped input. A new credit
ledger must first pass the same two-checker and adjudication audit. The merge
utility refuses overlapping target IDs, incomplete ledgers, target IDs outside
the v3 register, or a union that does not exactly cover the register. It keeps
reviewer-owned fields and prior adjudication provenance unchanged and never
promotes a candidate database.

Reason: reducing duplicate human effort is valid only when the carried-forward
scope is disjoint and the full target set remains auditable. A convenience
merge must not become an implicit review decision or a route around the Gold
coverage gate.

## D-062: Use a unique 80-cell promotion register while preserving candidate variants

Status: Accepted as a review-integration decision; no promotion implied.

The official expansion candidate contains 80 target cells and 88 observations.
ROE denominator alternatives remain separate observations, so a raw
observation register is not a valid promotion register because it repeats
target IDs. The integration register therefore has exactly one row per target
cell and stores candidate alternatives internally. The 48 already adjudicated
pilot cells may be carried forward only through the existing eligible ledger;
the 16 MBB cells and 16 VCB cells must arrive through disjoint, eligible review
ledgers. The union must equal the 80-cell register before label export or Gold
promotion.

Reason: preserving alternatives protects provenance, while unique target IDs
protect review completeness. Both are required to prevent an apparent larger
database from bypassing the human-review and metric-coverage gates.

## D-063: Require cross-issuer ROE definition consistency before comparative runs

Status: Accepted. The working convention is parent_attributable_equity, and
the scoped five-issuer ROE comparison gate is open under D-072 after a distinct
independent reviewer ACCEPTed the repository-bound evidence.

The fresh MBB and VCB reviews accepted parent-attributable profit divided by
average parent-attributable equity. The existing ACB observations are
substantively compatible because the reviewed consolidated statements show no
separate non-controlling-interest line, and the TCB source definition uses
post-NCI profit and average equity excluding NCI. VPB Q1-Q4 source filings,
adjudicated reviews and Gold v5 values also use parent-attributable profit over
average parent-attributable equity. For Q4, the accepted filing calculation is
11.4117471457821869%; the total-equity alternative is 10.9929645262513979% and
is retained only as a diagnostic comparison.

The gate is open only because attestation
reports/data-foundation/vpb-roe-parent-equity-independent-review-attestation-20260925.json
(canonical SHA-256: FC1D17BDBBAE9877F482875E730766D049CA5151D32173857D9EDEF2F31E7BAB)
records reviewer task /root/vpb_d072_reviewer_luna, verdict ACCEPT, and exact
reviewed head 2b292ddf21bd6be8a550f81fb518fca5dc419efb. The current authority
manifest is reports/data-foundation/vpb-roe-parent-equity-authority-manifest-20260925.json
(canonical SHA-256: 9BC7BDD2EAACA8BFF723B50C547A48B65A7F12B2F81B23303D2B285F1C19C33E).

Reason: a high numeric coverage percentage cannot compensate for a
cross-issuer semantic mismatch. Parent-attributable profit and equity provide
the common definition used by accepted reviews; the distinct review
attestation closes the last D-072 gate for the scoped Gold v5 comparison.

## D-064: Lock the application-first architectural constitution

Status: Accepted and binding.

The reusable analysis core is separated from enterprise/application
integration. Dataset providers and adapters isolate physical storage, the
reference frontend remains replaceable, Macro/Sector/Company are the locked
initial specialist roles, and research A/B/C architecture comparison remains
outside the normal product UX. Gold is a validated dataset instance, not the
architecture. Future work must preserve evidence/provenance,
dataset/snapshot traceability, replaceable storage and model providers,
privacy-safe observable events, bounded critique/revision, and the
transferability test recorded in `docs/ARCHITECTURAL-GUARDRAILS.md`.

The guardrail is enforced as a repository-level pre-flight and by the focused
architecture guard test. A task that materially conflicts with it must stop
and report the affected components and minimum correction before code changes.

## D-065: Implement Phase 0 as three reviewable slices

Status: Accepted for the current implementation sequence.

Phase 0 is divided into three isolated reviewable commits. Phase 0A defines
raw-source descriptors, explicit field mappings, a small metric registry,
snapshot identity, and deterministic onboarding validation contracts. Phase 0B
will implement exactly one CSV-to-canonical-snapshot vertical slice and a
canonical SQLite provider. Phase 0C will add only the minimal document/evidence
boundary and transferability smoke test. No Phase 0 slice may silently expand
into a complete ETL platform, RAG, critic/revision, UI redesign, or Phase 3B.

Reason: the application architecture must be proven through a narrow
non-Gold source path while keeping the reusable core independent from physical
storage and keeping each review diff auditable.

## D-066: Adopt query-adaptive composition and freeze the Phase 3B contract order

Status: Accepted as a binding architecture delta; Phase 3B implementation is
not started by this decision.

The reference product is query-adaptive. Macro, Sector/Peer, and Company are
capabilities selected by the request-derived `AnalysisPlan`, not mandatory
stages. The active specialist set is the union of specialists required by the
frozen plan. Inactive capabilities are `NOT_APPLICABLE`, not failed, and the
product must show only active specialists.

The semantic/revision order is frozen as:

```text
selected specialist outputs
  → synthesis/re-synthesis
  → canonical candidate claims
  → Stage-1 deterministic acceptance
  → semantic critic
  → decision / targeted revision
```

Every `CritiqueIssue` must be validated against the frozen plan before routing.
Only active affected specialists may be rerun. Cross-level reconciliation is
valid only for a declared applicable link and must have exactly one valid link
result. Divergence remains distinct from contradiction.

Semantic applicability is plan-derived. A dimension with no evaluation target
is explicitly `NOT_APPLICABLE`, never an artificial score of zero or one; its
policy weight is excluded and the remaining weights are renormalized. The
current six-dimension result/acceptance contract requires a Phase 3B-0
compatibility correction before a model evaluator runs.

`ACCEPT_WITH_LIMITATIONS` is restricted to genuine data or evidence
availability/insufficiency. It cannot hide integrity failure, unsupported
inference, poor reasoning/synthesis, unresolved contradiction, or provider
failure. The implementation must distinguish data-availability and
evidence-availability issue families instead of relying on a single generic
missing-evidence label.

The implementation sequence is deliberately staged:

```text
rule/architecture sync
  → review and lock
  → Phase 3B-0 applicability and acceptance contract
  → Phase 3B-A fixture SemanticCritic protocol and plan validation
  → Phase 3B-B bounded revision controller with injected adapters
  → Phase 3B-C runtime/claim/synthesis adapters
  → Phase 3B-D replaceable LLM provider integration
```

No step in this decision authorizes changes to historical benchmark artifacts,
the existing Gold dataset, the Phase 0–3A locked semantics, or the normal
product's introduction of an A/B/C architecture selector.

## D-067: Resolve the bounded pre-Gold 2024 Q4 macro/sector decision debt

Status: Accepted for candidate reconciliation; Gold promotion remains pending.

The official National Statistics Office 2024 Statistical Yearbook provides a
direct year-end aggregate credit-growth observation of `15.1%` at
`2024-12-31` compared with end-2023, with the frozen `VN` entity scope and
`annual_change_vs_end_2023` period basis. The source-native one-decimal value
is retained; the `15.08%` SBV-hosted research statement remains excluded as a
secondary lead. The exact table/row and source hash are recorded in the
versioned pre-Gold decision package.

One underlying aggregate fact is reused by capability mapping. This decision
does not create a duplicate `sector.system_credit_growth` observation. The
exact yearbook `Outstanding / Prel. 2024` row maps a candidate
`sector.system_credit_outstanding` value of `15,617.1` trillion VND at
`2024-12-31`, but it remains review-required and unpromoted. Native
`sector.system_npl_ratio` remains `missing / DATA_UNAVAILABLE`; the five-bank
peer sample is not a substitute.

Reason: semantic reconciliation must be completed before Phase 4, while Gold
promotion still requires the existing independent review, source contract and
fail-closed materialization gate. This decision changes no raw artifact,
schema, runtime or historical Gold snapshot.

## D-068: Evaluate the application without presupposing multi-agent superiority

Status: Accepted for the applied-thesis completion plan on 2026-09-24.

The advisor-approved report uses six chapters and focuses its empirical case
study on listed banks. The application must be reachable for advisor testing;
interface quality is part of acceptance. At least one new bank outside the
current five-bank Gold sample must pass through a documented, validated input
path and run through the same analytical core without bank-specific changes to
that core. Raw/OCR-parsed data remains candidate material until validation and
acceptance. The author may be the human evaluator but must use a frozen rubric
and disclose the single-rater limitation.

The research asks whether and under which request conditions A (single agent),
B (query-adaptive hierarchical), and C (B plus genuine critique/revision) differ
in quality, completion, latency, calls, and cost. It does not assume C or B is
superior. Existing issuer-count experiments remain historical pilot evidence;
their verification calls do not become genuine targeted revision by renaming.
The phase gates and evidence requirements are in
`docs/THESIS-MASTERPLAN-2026-09-24.md`.

Reason: the thesis is an evaluated application. A working web link, portable
validated data input, fair comparison, and a report matching the approved
outline are necessary to substantiate its claimed contribution.

## D-069: Separate bank-input syntax checks from source-backed acceptance

Status: Accepted as the contract for the next data-onboarding implementation;
no bank outside Gold v5 has been promoted by this decision.

CSV and parser outputs are candidate transport artifacts. A successful schema
check or mapping does not establish that a numeric value matches a primary
filing. The bank onboarding packet v1 therefore records immutable source
hashes, bank/period/metric semantics, locator, period basis, reporting scope,
missingness, and a per-observation reconciliation decision. A derived value
also names its inputs and formula version. Only reviewed primary-backed values
may enter an operational validated snapshot used by a published report; the
existing Gold benchmark requirements remain separate and unchanged.

This is necessary because the current CSV onboarding path can mark structurally
valid user-supplied values `VALID` and name its resulting snapshot `accepted`,
while the Stage-1 policy properly rejects user-supplied sources as primary
claim support. Future implementation must align these statuses and preserve
the source linkage through the canonical provider. No issuer PDF, including
scan/OCR output, is automatically accepted by this contract alone.

## D-070: Accept exact observation provenance for numeric claims

Status: Accepted as a provider-neutral Stage-1 contract correction; API/core
implementation and combined E2E verification are pending.

The Gold v5 evidence-snippet table lacks a metric or observation foreign key.
A source/ticker/period query therefore returns snippets from several metrics;
attaching all of them to each numeric claim creates a false claim-to-evidence
graph even when the numeric observation itself is correct. Numeric claims may
instead pass the critical evidence gate through an accepted direct observation
with primary source and exact locator, or through a reproducible derived metric
whose accepted inputs each have primary source and exact locator. Stage-1 must
validate those links and values through provider interfaces. Narrative/policy
claims still require document evidence. An unlinked snippet cannot be relabeled
as if it specifically supports a numeric claim.

This follows the existing data-contract rule that a published metric has
evidence **or an explicit source-record locator**, and preserves the
structured/document source-family separation in the architectural guardrails.
It does not authorize accepting user-supplied CSV numerics, missing locators,
invalid sources, wrong formulas, or cross-scope claims.

The report API carries this relation with explicit claim, observation, input,
formula, and source IDs. A derived claim may have multiple source-trail rows,
each tied to a particular accepted input. The fields are additive in OpenAPI
for old report compatibility, but new observation-backed numeric reports must
populate them; interpreting array order or decoding a claim ID is not a valid
provenance join.

## D-071: Recompute derived bank metrics before operational snapshot acceptance

Status: Accepted as the contract for the next onboarding implementation;
the CTG materializer and Gold v5 do not gain arithmetic validation merely
from this decision.

The operational promotion gate must recompute each derived candidate from its
accepted, source-backed input observations using a known versioned formula.
It must check entity, period basis, reporting scope, units and a declared
metric-specific tolerance, and retain the calculation receipt. A supplied
derived number, even with plausible input IDs and a `valid` label, cannot pass
without this check. Unknown formula versions, invalid inputs or mismatches
remain pending/conflicting. The gate is metric-generic, not issuer-specific.

The Stage-1 harness verifies that a published claim matches the accepted
derived observation and its formula/input/source lineage. It does not need to
duplicate the arithmetic engine. Historical Gold v5 is governed by its own
independent review decisions; notably D-063 still blocks five-issuer ROE
comparison until the VPB denominator is checked and independently reviewed.

Reason: the current canonical snapshot validator checks that derived input IDs
exist, but does not recalculate their value. Formula unit tests by themselves
do not prove a submitted CTG candidate was computed by those formulas. The
promotion gate must enforce the `code computes financial metrics` invariant.

## D-072: Open the VPB ROE comparison gate after distinct confirmation

Status: Accepted. VPB ROE is eligible for the scoped five-issuer Gold v5
comparison under the parent-attributable-equity convention. The gate became
open only after the distinct reviewer ACCEPT attestation was recorded and
bound by the authority manifest; the eligible comparative gate result alone
did not open the gate.

The independent reviewer task /root/vpb_d072_reviewer_luna reviewed exact PR
head 2b292ddf21bd6be8a550f81fb518fca5dc419efb and returned ACCEPT. Durable
attestation: reports/data-foundation/vpb-roe-parent-equity-independent-review-attestation-20260925.json
(canonical SHA-256: FC1D17BDBBAE9877F482875E730766D049CA5151D32173857D9EDEF2F31E7BAB).
It records exact reviewed control hashes, raw hashes of the Q1-Q4
official source PDFs, candidate and adjudicated/promotion ledgers, Gold v5
SQLite and labels, and the comparative gate manifest. It also records the
reviewer's independent Q4 recalculation from official consolidated filing
pages 6 and 8: profit attributable to bank shareholders of 15,778,795 million
VND; 2023 total equity/NCI of 139,795,527/5,164,494; 2024 total equity/NCI of
147,275,262/5,370,287; average parent-attributable equity of 138,268,004;
parent-equity ROE 11.4117471457821869%; total-equity alternative
10.9929645262513979%. Gold v5 contains Q1-Q4 values 8.0671%, 8.5867%,
9.6445%, and 11.4117%.

The read-only comparative-definition gate used
data/manifests/gold-bank-2025-expansion-v5/comparative-definition-gate-v2.json
(raw SHA-256: 4DE186FE9A31AEE6467A153A546044D0E70142770B3F1C5817D62D97D5341410) and returned eligible with no blockers across 80 cells
(76 valid, four missing). The authority manifest
reports/data-foundation/vpb-roe-parent-equity-authority-manifest-20260925.json
(canonical SHA-256: 9BC7BDD2EAACA8BFF723B50C547A48B65A7F12B2F81B23303D2B285F1C19C33E)
binds the attestation, VPB-scoped control records and raw immutable evidence
hashes. Tracked-text hashes use canonical LF UTF-8 SHA-256; immutable evidence
uses raw-byte SHA-256. Living repository policy files are checked by stable
semantic markers rather than byte-pinned by this authority. The review verifier
reads scoped tracked controls from its checkout and ignored artifacts only from
an explicit evidence root.

D-063's earlier VPB factual statement that total consolidated equity was used
is superseded: Q1-Q4 evidence and accepted review use parent-attributable
equity. The five-issuer comparison gate is open for the scope recorded in the
authority manifest. The original promotion ledger remains unchanged, including
blank register_review_status cells for the four VPB targets; the accepted
adjudication and independent authority confirmation are linked through the
separate status sidecar and attestation.

Reason: the corrected evidence identifies parent-attributable equity as the
consistent issuer-comparable convention. The distinct ACCEPT record ties the
exact reviewed head, source hashes, control hashes, recomputation and gate
output to the open scoped decision.

## D-073: Bind peer scope to explicit authority and distinguish requested inputs

Status: Accepted for the single-period provider-backed runtime and candidate
evaluation inputs on 2026-09-25. Final A/B/C evaluation remains pre-freeze.

Gold v5 has no native verified reporting-scope field. Keep the SQLite artifact
unchanged and supply scope only through an explicit immutable sidecar:
`data/evaluation/gold-v5-reporting-scope-authority-v1.json`, canonical LF UTF-8
SHA-256 `fef07af9f3deea7afbaa60ad51c8db740388e88b64bcf843d8ab5ec8f0ad777f`.
It binds the exact Gold SQLite hash, dataset/snapshot identity and 76 accepted
observations to reviewed values/source locators and upstream authority. The
four missing cells receive no authority entries. Provider validation fails
closed on any mismatch; absence of authority leaves reporting scope unknown.
This is a Gold adapter responsibility, not a core dependency on that dataset.

Peer benchmark identity and claim scope bind all requested members. The
numeric denominator binds eligible accepted members and exact observation
inputs. Every excluded requested member has an explicit reason. The
five-requested/four-eligible case must retain both counts and pass Stage-1
against the requested identity. Shared non-null units, period basis and
verified scope are required; all-missing remains `all_values_missing`.

The reference API freezes the plan before retrieval and supports one-period
Company/Sector execution through synthesis, Stage-1, semantic critique and at
most two targeted revisions. Every revision is re-synthesized and rechecked.
Missing semantic configuration and unsupported macro/multi-period scope block
before specialist retrieval. Offline critic tests do not count as live model
validation. T04/T05/T08 remain ineligible and no final A/B/C result is created.

Candidate evaluation text controls use canonical LF UTF-8 hashing, preserving
BOM, Unicode code points, whitespace and final newline. A Windows checkout may
change line endings without changing analytical identity. Immutable source
files and SQLite continue to use raw-byte hashing.

The API contract also repairs eleven pre-existing empty reference keys to
`$ref` and documents additive peer metadata. Python CI validates the OpenAPI
document, architecture guardrails and the checkout-available suite. It cannot
verify ignored local evidence without an explicitly provisioned evidence root.

### D-073 implementation review correction

Independent review of implementation head `3774046` identified two blockers:
targeted reruns only re-read identical provider data, and report assembly
overwrote peer metadata across metrics. Acceptance requires an actual writer
step consuming issue/action content, observable targeted content correction,
preservation of unaffected output and another Stage-1 gate. Re-evaluation alone
must never be labeled a successful revision. Peer metadata must be emitted per
metric in `SectorBenchmark.benchmarks`; shared legacy metadata is omitted when
records differ. These are completion gates for this PR, not new research scope.

The review also identified accepted-snapshot mutation: run history shared
`SQLITE_DB_PATH`. This must be separated via `ANALYSIS_RUNS_DB_PATH` before
this slice is accepted, including alias rejection and repeated-run source-hash
tests. Readiness must incorporate required writer/critic configuration. Initial
model analysis is role-specific, followed by a separate constrained synthesis;
the new writer must not become one global call mislabeled as several agents.

The unchanged analysis_runs table definition is separated into contracts/run-store-schema.sql. New runtime history initialization applies it only to ANALYSIS_RUNS_DB_PATH; canonical analytical schema initialization excludes it. Existing dataset artifacts are not migrated.
