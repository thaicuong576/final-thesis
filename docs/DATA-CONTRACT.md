# Data and Agent Contracts

All contracts are versioned and validated at boundaries. A payload from staging data may be marked partial or pending, but only accepted gold observations can support a published benchmark claim.

## Enumerations

```text
source_type: api | filing | issuer_ir | policy | market_data | research_report
source_tier: primary | accelerator | cross_check | context | fallback | user_supplied
quality_status: valid | missing | estimated | conflicting | invalid | pending_validation
agent_status: success | partial | failed
critique_resolution: resolved | explained | unresolved
```

## SourceRecord

```text
source_id: string
source_type: enum
source_tier: enum
source_url: string
retrieved_at: datetime
local_path: string
content_hash: string
publisher: string
license_note: string
quality_status: enum
notes: string | null
```

Rules:

- `source_id` is stable within a snapshot.
- `content_hash` identifies the retrieved artifact; restatements receive a new record.
- A fallback or context source cannot silently become primary evidence.
- A user-supplied CSV is a candidate transport source, not primary evidence for
  its financial values. Attaching an issuer filing does not automatically
  upgrade those values; each promoted observation needs a recorded comparison
  to the filing's exact page, table, or note.
- Failed retrievals remain in manifests but cannot produce valid observations.

## Hash modes for repository evidence manifests

Any manifest field named sha256 must identify its hash mode:

- canonical_lf_utf8_sha256 applies to Git-tracked UTF-8 text control records.
  Decode as strict UTF-8, normalize CRLF and lone CR to LF, then encode as
  UTF-8. Preserve the BOM, Unicode code points, whitespace, and final newline;
  do not apply Unicode normalization. The digest must match whether a checkout
  uses LF or CRLF.
- raw_file_bytes_sha256 applies to immutable acquired evidence and local
  evidence inputs, including PDFs, SQLite files, CSV/JSON/JSONL ledgers, and
  gate manifests. Hash the exact stored bytes.

A legacy worktree-byte hash may be retained only as audit metadata. It is not
an authoritative hash for tracked text. A manifest that binds control artifacts
must record each artifact's hash_mode beside its sha256.

Verification scripts resolve tracked controls from their current checkout.
Ignored evidence must come only from an explicit `--evidence-root` argument;
default behavior is the current repository and fails closed when evidence is
absent. CI can validate canonical tracked-text hashes from its checkout, but
cannot validate ignored PDFs, ledgers, SQLite snapshots or gate manifests
unless the required evidence root is provisioned.

## Onboarding packet and acceptance boundary

`contracts/bank-onboarding-packet-v1.schema.json` describes the exchange packet
for a bank outside the current Gold sample. It is an input contract, not a new
physical database schema. A packet identifies its bank and carries immutable
source descriptors and candidate observations. Each observation identifies its
metric, period, unit, period basis, reporting scope, and source locator. A
derived value also lists its input observation IDs and formula version. A
missing cell has `value: null` and a reason. Source hashes identify the exact
artifacts reviewed.

There are three distinct gates:

1. **Structural validation:** parse types, explicit mapping, units, periods,
   supported metric IDs, source references, and `missing ≠ 0`. Passing this gate
   creates a candidate snapshot; its numeric observations are not yet accepted
   for a published analysis.
2. **Source reconciliation:** a reviewer checks each numeric candidate against
   a primary issuer filing and records its source ID, exact locator, reporting
   scope, period basis, result, reviewer, time, and notes. A derived metric also
   records accepted inputs and formula version. Failed or unresolved checks
   remain pending/conflicting and cannot be represented as valid facts.
3. **Analysis acceptance:** only a reconciled observation in an immutable
   validated snapshot may support a published numeric claim. The Stage-1
   acceptance harness resolves its primary source and locator through the
   provider; it must reject an unreviewed `user_supplied` CSV value, even when
   the CSV packet or its technical validation report is called `accepted`.

This case-study acceptance does not imply **Gold benchmark promotion**. The
existing Gold coverage and independent-checker requirements below continue to
govern evaluation datasets. A bank may demonstrate transferability through a
reviewed operational snapshot without joining the frozen five-bank Gold v5
benchmark. The app must label each snapshot's validation level and supported
entities, periods, and metrics accurately.

An OCR/parser output follows the same candidate route. Text, tables, or chart
descriptions from a scanned PDF cannot bypass source reconciliation, and page
order/locator must survive parsing. Unsupported charts or ambiguous numbers
remain pending or missing with a reason.

## MetricObservation

```text
observation_id: string
ticker: string
sector: enum(bank, securities)
metric: string
value: number | null
unit: string | null
period: string              # YYYY_QN or FYyyyy
as_of_date: date | null
period_basis: enum(point_in_time, quarter_only, ytd, annual, ttm) | null
source_id: string | null
source_locator: string | null
quality_status: enum
reason: string | null
```

Rules:

- Numeric/valid values must include unit, period, source ID, and period basis.
- `value=null` is required for missing or zero-denominator results and must include a reason.
- A reasoned `missing` observation may omit source ID, unit, period basis, and
  locator because no source was found; it must remain excluded from valid-only
  queries and must never be presented as a numeric fact.
- Missing observations must never be guessed, zero-filled, silently imputed, or
  replaced by a vendor value. A fallback source is allowed only when its source
  tier and route were explicitly approved before review and recorded in the
  relevant manifest or decision.
- Numeric accuracy and peer/statistical averages use only accepted numeric
  observations. Missing cells are excluded from the numeric denominator but
  must be reported explicitly by ticker, metric, and period; missing-data
  behavior is evaluated as a separate outcome.
- A source locator is required for every valid observation; a page/section locator is required for paginated evidence.
- Conflicting values are retained as separate observations until reconciled.

## DerivedMetric

```text
derived_id: string
ticker: string | null
sector: string | null
metric: string
value: number | null
unit: string
period: string
period_basis: string
input_observation_ids: list[string]
formula_version: string
quality_status: enum
reason: string | null
```

Derived metrics must be reproducible from the listed inputs. Formula code, unit conversion, YTD subtraction, and peer-statistics rules are versioned.

For a **new operational snapshot**, promoting a derived candidate to `valid`
requires a deterministic calculation against accepted input observations using
a recognized formula version. The promotion gate checks entity, period basis,
reporting scope and units, then compares the computed output with the submitted
candidate under a declared metric-specific numeric tolerance. It records a
calculation receipt with formula version, ordered input IDs/values, computed
output, tolerance and review result. Unknown formulas, unavailable inputs or a
failed comparison stay pending/conflicting. Stage-1 subsequently checks a
claim against the accepted derived output and its lineage; Stage-1 does not
itself re-execute financial formulas. Historical Gold artifacts retain their
separate review/promotion gate and are not retroactively approved by this rule.

## Evidence for published numeric claims

A critical numeric claim may be supported by **structured observation
provenance** without a document snippet when the frozen snapshot resolves all
of the following through the provider:

- a direct claim has the accepted observation ID, matching metric/entity/period,
  value and unit, an approved primary source record, and that observation's
  exact source locator;
- a derived claim has the formula version and accepted input observation IDs,
  reproduces the stated value under the recorded unit/period basis, and every
  required input resolves to an approved primary source and exact locator;
- the claim preserves these observation/source references in its report
  provenance, including the snapshot ID. A derived result must not pretend its
  user-supplied CSV is a direct primary source.

Stage-1 rejects missing or invalid source records, locator, inputs, formula,
scope, or value. This observation route does **not** remove the evidence gate;
it is a verifiable numeric evidence route. Narrative, policy, and unsupported
causal claims still require appropriate document snippets with page locators.

Document snippets may be attached as evidence for a particular numeric claim
only through an explicit reviewed observation-to-snippet association. Matching
the same source, bank and period—or overlapping PDF pages—is insufficient.
Unlinked snippets can be shown as related documents but cannot be copied into a
claim's `evidence_refs` or relabeled with that claim's metric/value/locator.

The published report carries the provenance graph explicitly. A numeric
`AtomicClaim` names its exact `observation_id`; a derived claim also names
`input_observation_ids` and `formula_version`. Every primary-source
`EvidenceTrailItem` supporting that claim names `claim_id`, the specific input
or direct `observation_id`, and `source_id`, with the reviewed locator and
source URL when available. Several trail rows may share a derived `claim_id`.
Report consumers must not infer these links from row order, ticker/metric
similarity, or an encoded claim ID. These additive fields are optional in the
public schema for older report compatibility but required for newly published
numeric claims on the observation-provenance route.

## EvidenceSnippet

```text
evidence_id: string
source_id: string
source_document: string
page_number: integer | null
section_name: string | null
period: string | null
ticker: string | null
quote: string
retrieval_score: number | null
parser_status: string
is_paginated: boolean
```

Rules:

- `quote` must be traceable to the source document.
- `page_number` is required for paginated documents.
- `is_paginated=false` is allowed only when the source is explicitly non-paginated;
  PDF evidence is always page-aware.
- Retrieval score is metadata, not proof of correctness.
- An evidence snippet cannot override a conflicting structured observation without a reconciliation record.

## GoldLabel

```text
label_id: string
target_id: string
label_type: enum(value_check, evidence_support, anomaly_case)
expected_value: number | null
expected_judgment: string | null
checker_id: string
checked_at: datetime
source_locator: string | null
resolution_note: string
```

At least 40 manually checked metric/evidence items are required for the first gold snapshot. Anomaly labels must distinguish true contradiction, explainable divergence, data conflict, and insufficient evidence.

## GoldConfig and promotion checks

```text
tickers: tuple[string, ...]
periods: tuple[string, ...]
required_metrics: tuple[string, ...]
min_manual_labels: integer >= 1       # default 40
min_independent_checkers: integer >= 2 # default 2
min_metric_coverage: number           # default 0.9
```

The promotion and baseline gates require every selected target cell to be
represented as `valid` or `missing` with a reason, require the configured label
count and at least two checker IDs, and require `value_check` labels to cover
every selected ticker/metric plus at least two periods per ticker when the scope
contains two or more periods. `evidence_support` labels are preserved when the
gold database is materialized.

## CoverageSummary

```text
summary_id: string
snapshot_id: string
ticker: string
metric: string
expected_count: integer
candidate_count: integer
valid_count: integer
missing_count: integer
coverage_ratio: number          # 0..1, valid_count / expected_count
```

Coverage summaries are generated during gold promotion. They provide evidence for
the coverage gate, but do not replace source reconciliation or manual labels. In
the candidate assembly and gold snapshot, `candidate_count` means target cells
represented by either a candidate observation or an explicit missing placeholder;
the number of cells with an actual candidate route is therefore
`candidate_count - missing_count`. Reports must not confuse represented-cell
coverage with source-candidate coverage.

## AgentPayload

```text
agent_id: string                 # must equal the AgentCallRequest.role
status: enum(success, partial, failed)
ticker: string | null
period: string
metrics: map[string, number | null]
metric_units: map[string, string]
metric_periods: map[string, string]
sector_benchmarks: map[string, number | null]
findings: list[string]
evidence: list[EvidenceSnippet]
quality_flags: list[string]
observation_ids: list[string]
source_ids: list[string]
```

Rules:

- `agent_id` must equal the role that received the request. The runtime uses
  `single_agent`, `macro`, `sector`, `company`, `orchestrator`, and
  `verification` as role identifiers; the role is part of the call trace.
- `macro`, `sector`, and `company` are available capabilities, not mandatory
  stages. A role is active only when required by the request-derived
  `AnalysisPlan`; an inactive role is `NOT_APPLICABLE`, not a failed role.
- Every published metric has a corresponding unit, period, observation ID/source
  ID, and evidence or explicit source-record locator.
- Agents preserve nulls and quality flags.
- Invalid payloads are rejected before critique or synthesis.
- Agents do not calculate financial ratios from unstructured prose.
- The read-only query boundary exposes only `quality_status=valid` observations and
  evidence linked to valid source records. Pending, fallback, or conflicting rows
  remain in storage for audit but are returned as missing/partial or excluded.

## AgentCallRequest and temporal scope

```text
role: string
ticker: string
period: string                 # anchor/target period used by the call
periods: tuple[string, ...]    # ordered periods represented in context
metric_ids: tuple[string, ...] # requested bank metrics
macro_indicator_ids: tuple[string, ...] # requested macro metrics, if any
question_id: string
question_type: string
question_prompt: string
prompt_version: string            # exact version selected for this run
context: object
```

Single-period questions use a one-item `periods` tuple. A `company_trend`
question must use exactly the ordered periods declared by that question; the
runtime rejects a partial list and prepares a separate period-keyed context for
each requested period. Run manifests preserve this period scope so trend calls
remain auditable and comparable.

For a `macro_to_bank` question, the runtime also requires the caller's macro
indicator list to match the question's declared `macro_indicator_ids` exactly
before adapter dispatch. This prevents a macro job from passing the database
gate while silently preparing an incomplete macro context. Non-macro questions
may still receive optional macro context when the architecture intentionally
uses it; that context must remain provenance-bound.

The runtime binds payload metric fields to this request scope. Macro payloads may
only publish the declared macro indicators; other roles may only publish the
requested bank metrics or sector benchmarks. Every published metric field must
carry a unit and a period within the request's ordered period scope. A non-null
numeric metric or benchmark must also carry at least one observation ID, source
ID, or evidence record; otherwise the payload is rejected as untraceable.
All numeric boundary fields reject `NaN` and infinite values.

When a call is dispatched from a `BaselineJob`, the resulting runtime result and
run manifest also carry that job's stable `job_id`. Direct offline fixture calls
may leave this field null for backward compatibility.

## Phase 3 semantic applicability and revision contract

The semantic critic runs only after synthesis has produced canonical candidate
claims and Stage-1 deterministic acceptance has evaluated those claims. Every
re-synthesis follows the same order:

```text
canonical candidate claims
  → Stage-1
  → semantic critic
  → plan-valid CritiqueIssue[]
  → affected active specialists only
  → re-synthesis
  → Stage-1 again
```

The six semantic dimensions are evaluated against the frozen `AnalysisPlan`.
A dimension with no evaluation target is explicitly `NOT_APPLICABLE`, not a
score of zero or one. It contributes neither a failure nor a perfect score.
The quality total renormalizes the policy weights over applicable dimensions:

```text
sum(score[d] * weight[d] for applicable d)
/ sum(weight[d] for applicable d)
```

This is a required Phase 3B-0 contract correction; provider adapters must not
decide applicability or perform the renormalization.

Critique issues are validated against the frozen plan before routing. The
affected agent must be active in the plan. A `RECONCILE_CROSS_LEVEL` issue is
valid only for a declared `ApplicableLink`; its link result must be known and
unique. Unknown, omitted, or duplicate applicable-link results are malformed.

`ACCEPT_WITH_LIMITATIONS` may represent only genuine data or evidence
availability/insufficiency. The semantic contract must distinguish data
availability from evidence availability (for example `MISSING_DATA` and
`MISSING_EVIDENCE`) and must not use limited acceptance for reasoning defects,
unsupported inference, hard-gate failures, unresolved contradictions, or
provider/system failures.

The reusable core now has a semantic evaluator and bounded revision controller,
with focused Phase 3B tests. The deployed API does not yet route its reports
through that core, so these clauses do not claim end-to-end runtime support.

## Run configuration and prompt version

Every `ExperimentRunConfig` must include a non-empty `prompt_version`. The
current scaffold uses `prompt-contract-v1`, documented in
`docs/PROMPT-CONTRACT-VI.md`. The run manifest copies this value together with
the snapshot ID, question-set hash, rubric version, model ID and source policy.
The runtime copies the same value into every `AgentCallRequest` delivered to an
adapter, so the provider cannot use a prompt configuration different from the
one recorded in the manifest without violating the run contract. The request
rejects an empty value, and manifest construction rejects a call/configuration
mismatch before writing the run artifact.
Changing role instructions, context layout, output rules, or verification
wording requires a new prompt version so a later comparison cannot silently
mix prompt configurations.
New manifests also record `RunCallTrace.prompt_sha256`, the SHA-256 fingerprint
of the canonical rendered prompt. The field is optional when reading legacy
schema-version-2 artifacts, but the current manifest builder always populates
it for a renderable call.

## CritiqueRecord

```text
critique_id: string
rule_id: string
conflict_detected: boolean
conflict_description: string
affected_agents: list[string]
verification_request: string | null
new_evidence_ids: list[string]
resolution: enum(resolved, explained, unresolved)
```

The `conflict_detected` field records a deterministic verification trigger. The final label of true contradiction is supplied by the evaluation protocol, not assumed from the trigger alone.

## FinalAnalysisState

```text
run_id: string
snapshot_id: string
target_ticker: string
target_period: string
macro_payload: AgentPayload
sector_payload: AgentPayload
company_payload: AgentPayload
critique_history: list[CritiqueRecord]
final_report_markdown: string
all_claims_have_evidence: boolean
```

## Contract rules

- Numeric values must include units and periods.
- A missing value is not a zero.
- A source URL or source identifier is required for every published claim.
- Page numbers are required when evidence comes from a paginated document.
- Agents must preserve uncertainty and quality flags.
- Invalid payloads are rejected before synthesis.
- Contract changes require an entry in `docs/DECISIONS.md` and a regression fixture.
