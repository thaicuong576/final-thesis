# Data and Agent Contracts

All contracts are versioned and validated at boundaries. A payload from staging data may be marked partial or pending, but only accepted gold observations can support a published benchmark claim.

## Enumerations

```text
source_type: api | filing | issuer_ir | policy | market_data | research_report
source_tier: primary | accelerator | cross_check | context | fallback
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
- Failed retrievals remain in manifests but cannot produce valid observations.

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
