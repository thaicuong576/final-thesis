# Data Foundation and Readiness Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Promote the current staging snapshot into a validated, versioned gold
dataset for the pilot-first benchmark and expose deterministic,
provenance-preserving query interfaces that the later baseline and hierarchical
agents can use identically. The five-bank/eight-quarter corpus is a conditional
expansion.

**Architecture:** Keep existing raw retrievals and staging SQLite databases immutable. Add a validation/calculation package that creates a new accepted gold snapshot from explicitly selected source records, with normalized observations, derived metrics, evidence locators, coverage reports, and a gate decision. Build agent-facing query interfaces only over accepted observations; unvalidated or fallback records remain visible as quality flags but cannot be published as financial facts.

**Tech Stack:** Python, SQLite, Parquet where tabular export is useful, Pydantic for boundary contracts, Python standard-library `unittest` for deterministic tests, local PDF parsing/indexing after parser validation, and JSONL/Markdown manifests for auditable run records.

**Spec:** `docs/superpowers/specs/2026-09-04-source-grounded-thesis-scope-design.md`

**Execution amendment:** D-036 and `docs/SPEC.md` govern the current run. The
original five-bank/eight-quarter target in this historical plan is an upper
bound; complete the 48-cell pilot before any expansion.

## Global Constraints

- Raw source files are immutable.
- A missing value is not a zero.
- Numeric values must include units and periods.
- A source URL or source identifier is required for every published claim.
- Page numbers are required when evidence comes from a paginated document.
- Agents must preserve uncertainty and quality flags.
- Invalid payloads are rejected before synthesis.
- Data limitations are reported rather than silently imputed.
- Mocked, cached, or incomplete data must be labeled and must never be reported as live validation.
- Production deployment and access to real financial services require explicit approval.

---

### Task 1: Record the scoped design in project documentation

**Files:**
- Create: `docs/METRIC-DICTIONARY.md`
- Create: `docs/DATA-READINESS-CHECKLIST.md`
- Create: `docs/EVALUATION-PROTOCOL.md`
- Modify: `docs/SPEC.md`
- Modify: `docs/ARCHITECTURE.md`
- Modify: `docs/DATA-CONTRACT.md`
- Modify: `docs/DECISIONS.md`
- Modify: `docs/RESEARCH.md`

**Interfaces:**
- Consumes: `docs/superpowers/specs/2026-09-04-source-grounded-thesis-scope-design.md`, current source manifests, and the existing canonical documents.
- Produces: one consistent working scope, metric definition table, readiness gates, and evaluation protocol that later code and thesis chapters can cite.

- [x] **Step 1: Write the metric dictionary table**

Include one row per primary metric with `metric_id`, financial interpretation, numerator inputs, denominator inputs, formula, unit, point-in-time/flow basis, YTD normalization rule, preferred source, fallback source tier, missing-value rule, and validation status. Primary metrics are NPL, LLR coverage, CIR, ROA/ROE with one selected profit convention, and NIM only if earning-asset mapping is accepted.

- [x] **Step 2: Write the readiness checklist**

Define the five-bank registry, eight periods, source coverage thresholds, date validity check, formula-test requirement, gold-sample requirement, provenance requirement, conflict rule, and promotion rule from staging to gold. Mark the current database as `staging_not_gold`.

- [x] **Step 3: Write the evaluation protocol**

Define the three arms, fixed input controls, primary outcomes, secondary outcomes, blind review subset, anomaly-labeling process, and null-result policy. State that a document-QA baseline is optional and cannot replace the tool-equivalent single-agent baseline.

- [x] **Step 4: Update canonical scope and contracts**

Align `SPEC.md`, `ARCHITECTURE.md`, `DATA-CONTRACT.md`, `DECISIONS.md`, and `RESEARCH.md` with the scoped design. Preserve rejected alternatives and label the scope as a working proposal until advisor confirmation is recorded.

- [x] **Step 5: Run consistency checks**

Run:

```powershell
rg -n -i "16 mã|15-20|8-12|realtime|real-time|100% chính xác|TCBS.*benchmark|TBD|TODO" docs
```

Expected: no canonical requirement promises the rejected broad scope or unsupported accuracy; any historical thesis-source occurrence is left untouched and excluded from the modified canonical files.

- [x] **Step 6: Record the documentation handoff**

Record the files, scope assumptions, and remaining advisor decision in `.agents/handoffs/data-foundation-design.md` and add a project-state event.

### Task 2: Add reproducible snapshot and period validation

**Files:**
- Create: `src/thesis_data/__init__.py`
- Create: `src/thesis_data/snapshot.py`
- Create: `src/thesis_data/periods.py`
- Create: `tests/test_periods.py`
- Create: `tests/test_snapshot.py`
- Create: `scripts/audit_snapshot.py`

**Interfaces:**
- Consumes: a read-only SQLite path and a JSON/YAML-like snapshot configuration represented as a Python mapping.
- Produces:
  - `validate_period_bounds(period: str) -> tuple[date, date]`
  - `audit_snapshot(db_path: Path, expected_tickers: Sequence[str], expected_periods: Sequence[str]) -> SnapshotAudit`
  - `SnapshotAudit.to_json() -> dict`

- [x] **Step 1: Write failing date tests**

```python
def test_quarter_bounds_use_real_calendar_dates():
    assert validate_period_bounds("2024_Q2") == (
        date(2024, 4, 1), date(2024, 6, 30)
    )
    assert validate_period_bounds("2024_Q3") == (
        date(2024, 7, 1), date(2024, 9, 30)
    )

def test_invalid_period_is_rejected():
    with self.assertRaisesRegex(ValueError, "YYYY_QN"):
        validate_period_bounds("2024_Q5")
```

- [x] **Step 2: Run the focused tests and confirm failure**

Run: `$env:PYTHONPATH='src'; python -m unittest discover -s tests -p 'test_periods.py' -v`

Expected: FAIL because the validation module does not yet exist.

- [x] **Step 3: Implement calendar-boundary validation**

Use `datetime.date` and explicit quarter mapping. Never construct quarter ends by appending day `31` to a month.

- [x] **Step 4: Write failing snapshot audit tests**

The fixture must assert that an audit reports: missing ticker, missing period, invalid benchmark date, non-accepted source status, and absent expected gold tables. It must also report zero duplicate groups for a clean fixture.

- [x] **Step 5: Implement the read-only SQLite audit**

The audit must inspect `dataset_run`, `benchmark_periods`, `source_records`, `document_records`, and observation keys. It must return structured findings instead of raising on data-quality failures.

- [x] **Step 6: Run the audit against both current staging databases**

Run:

```powershell
python scripts/audit_snapshot.py data/processed/finance_master_v2.sqlite --json-out data/manifests/staging-readiness-audit.json
```

Expected: the command exits successfully as an audit command, reports the four invalid provisional quarter ends, reports all source records as pending/failed rather than valid, reports TCBS as absent, and does not mutate the database.

- [x] **Step 7: Commit or hand off the audit result**

Store the audit JSON and a concise Markdown interpretation. The audit output must remain labeled as staging validation, not gold validation.

### Task 3: Define normalized observations and provenance-preserving storage

**Files:**
- Create: `src/thesis_data/schema.py`
- Create: `src/thesis_data/storage.py`
- Create: `src/thesis_data/normalize.py`
- Create: `tests/test_schema.py`
- Create: `tests/test_storage.py`
- Create: `tests/test_normalize.py`
- Create: `scripts/normalize_vendor_snapshot.py`

**Interfaces:**
- Consumes: source records and vendor-native statement/ratio rows from the staging database.
- Produces:
  - `SourceRecord`
  - `MetricObservation`
  - `DerivedMetric`
  - `EvidenceSnippet`
  - `CoverageSummary`
  - `GoldPromotionResult`

- [x] **Step 1: Write contract tests for nulls, units, periods, and provenance**

Reject a numeric observation without unit, period, or source ID. Accept `value=None` only with `quality_status="missing"` and a reason. Reject a published claim without source ID and locator.

- [x] **Step 2: Implement Pydantic models**

Keep the field meanings aligned with `docs/DATA-CONTRACT.md`. Add `formula_version`, `source_tier`, and `reason` only where required for normalized or derived records; do not weaken existing contract fields.

- [x] **Step 3: Write the gold-schema migration test**

Create a temporary SQLite database and assert that the gold schema contains source records, metric observations, derived metrics, evidence snippets, gold labels, coverage summary, and experiment snapshot metadata.

- [x] **Step 4: Implement versioned gold snapshot creation**

`create_gold_snapshot(staging_db: Path, output_db: Path, config: GoldConfig) -> GoldPromotionResult` must fail closed when a required coverage or provenance gate is not met. It must never replace an existing output file.

- [x] **Step 5: Run schema and storage tests**

Run: `$env:PYTHONPATH='src'; python -m unittest discover -s tests -p 'test_schema.py' -v; python -m unittest discover -s tests -p 'test_storage.py' -v`

Expected: PASS with temporary databases and no changes to `data/processed/finance_master.sqlite` or `data/processed/finance_master_v2.sqlite`.

- [x] **Step 6: Normalize a real vendor candidate snapshot**

Run the adapter against `data/processed/finance_master_v2.sqlite` for the proposed
scope. Preserve `RATIO_TTM`, vendor-native units, source locators, and
`pending_validation`; do not apply unproven sign or unit conversions. Store the
result as a new candidate database for reconciliation.

### Task 4: Implement deterministic bank metrics and formula tests

**Files:**
- Create: `src/thesis_data/metrics.py`
- Create: `tests/test_metrics.py`
- Modify: `docs/METRIC-DICTIONARY.md`

**Interfaces:**
- Consumes: normalized numeric inputs with explicit units and period basis.
- Produces:
  - `calculate_npl(stage3: Number, stage4: Number, stage5: Number, gross_loans: Number) -> MetricResult`
  - `calculate_llr(provision_balance: Number, npl_balance: Number) -> MetricResult`
  - `calculate_cir_operating_expense(operating_expense: Number, operating_income: Number) -> MetricResult`
  - `calculate_roa(net_profit: Number, average_assets: Number) -> MetricResult`
  - `calculate_roa_from_ytd(current_ytd: Number, prior_ytd: Number, average_assets: Number) -> MetricResult`
  - `calculate_peer_median(values: Sequence[Decimal | None]) -> MetricResult`

- [x] **Step 1: Add hand-checkable failing cases**

Cover normal values, missing inputs, zero denominators, percent scaling, VND-billion scaling, YTD-to-quarter conversion, and preserved conflicting variants.

- [x] **Step 2: Run the metric tests to confirm failure**

Run: `$env:PYTHONPATH='src'; python -m unittest discover -s tests -p 'test_metrics.py' -v`

Expected: FAIL before implementation.

- [x] **Step 3: Implement formulas with Decimal and explicit units**

Return a value, unit, quality status, and formula version. A missing or zero denominator returns null with a reason; it never returns zero.

- [x] **Step 4: Add period-basis normalization**

Implement YTD subtraction only when both observations share fiscal year and statement basis. Preserve source YTD values alongside the derived quarter-only result.

- [x] **Step 5: Run all metric tests and compare hand examples**

Run: `$env:PYTHONPATH='src'; python -m unittest discover -s tests -p 'test_metrics.py' -v`

Expected: PASS, with every formula example in `docs/METRIC-DICTIONARY.md` matching the test expected value.

### Task 5: Reconcile selected issuers and build the gold sample

**Files:**
- Create: `data/manifests/gold-bank-2025-v1/selection.json`
- Create: `data/reconciliation/gold-bank-2025-v1/register.csv`
- Create: `data/reconciliation/gold-bank-2025-v1/README.md`
- Create: `data/manifests/gold-bank-2025-v1/gold-labels.jsonl`
- Create: `reports/data-foundation/gold-bank-2025-v1-quality.md`
- Modify: `docs/RESEARCH.md`

**Interfaces:**
- Consumes: selected five-bank registry, eight-quarter period configuration, official issuer filings/IR documents, SBV/GSO records used by the primary metrics, and staged vendor responses.
- Produces: a source-reconciled observation set, at least 40 manual gold labels, coverage/missingness/conflict report, and an accepted or rejected gold-promotion decision.

- [x] **Step 1: Create the selection manifest**

Record the five candidate banks, the eight periods, inclusion criteria, source tiers, benchmark cutoff, and the reason any staged issuer is excluded. Do not include TCBS in the primary benchmark.

- [ ] **Step 2: Retrieve or locate primary documents for the selected sample**

For each selected bank, collect the statement packages and relevant notes for the gold sample. Store URL, retrieval timestamp, local path, hash, publisher, license note, ticker, period, and document type. Preserve failed retrieval attempts in the manifest.

- [ ] **Step 3: Reconcile staged observations to primary evidence**

For each gold metric, record vendor value, primary-source value, unit conversion, period basis, tolerance, decision, source locator, and explanation for any conflict. Never overwrite the vendor observation.

- [ ] **Step 4: Create at least 40 manual labels**

Use at least two quarters per selected issuer and cover every primary metric plus representative evidence snippets. Each label records checker, check date, expected value or judgment, source page/section, and resolution note.

- [ ] **Step 5: Generate the coverage and quality report**

Report raw availability, field availability, normalized observation coverage, validated coverage, provenance completeness, missingness, conflicts, document parser status, and source-tier distribution by ticker, metric, and period.

- [ ] **Step 6: Promote only if all gates pass**

Run `create_gold_snapshot` with the selection manifest. If a gate fails, create a rejected quality report naming the exact metric/ticker/period and use the documented exclusion policy.

### Task 6: Validate document evidence and evidence retrieval boundaries

**Files:**
- Create: `src/thesis_data/documents.py`
- Create: `tests/test_documents.py`
- Create: `data/manifests/gold-bank-2025-v1/document-quality.jsonl`
- Modify: `docs/ARCHITECTURE.md`

**Interfaces:**
- Consumes: selected PDF files and document records.
- Produces:
  - `inspect_document(path: Path) -> DocumentQuality`
  - `extract_evidence(path: Path, query: EvidenceQuery) -> list[EvidenceSnippet]`
  - page-aware evidence records with source ID, page, section, period, ticker, quote, and parser status.

- [x] **Step 1: Add fixture tests for text-layer, page-number, and missing-page behavior**

Tests must reject an evidence record whose quote cannot be tied to a document and must preserve `page_number=None` only for non-paginated sources.

- [x] **Step 2: Inspect the selected PDF sample**

Run the parser on at least one bank statement and one annual report. Record text-layer presence, page count, extraction errors, table warnings, and hash match.

- [x] **Step 3: Implement bounded evidence extraction**

Start with deterministic page/section filtering. Do not add a vector database until the parser and page references pass the document-quality gate.

- [x] **Step 4: Run evidence tests and document-quality audit**

Run: `$env:PYTHONPATH='src'; python -m unittest discover -s tests -p 'test_documents.py' -v`

Expected: PASS, with every accepted evidence snippet linked to a source record and a page or explicit non-paginated reason.

### Task 7: Expose a validated query boundary for future agents

**Files:**
- Create: `src/thesis_data/query.py`
- Create: `tests/test_query.py`
- Modify: `docs/DATA-CONTRACT.md`

**Interfaces:**
- Consumes: an accepted gold snapshot only.
- Produces:
  - `get_company_metrics(db: Path, ticker: str, period: str, metric_ids: Sequence[str]) -> AgentPayload`
  - `get_sector_benchmarks(db: Path, sector: str, period: str, metric_ids: Sequence[str]) -> AgentPayload`
  - `get_macro_context(db: Path, period: str, indicator_ids: Sequence[str]) -> AgentPayload`
  - `get_evidence(db: Path, source_ids: Sequence[str], query: EvidenceQuery) -> list[EvidenceSnippet]`

- [x] **Step 1: Write failing query tests**

Verify accepted values are returned with units, periods, source IDs, quality flags, and evidence. Verify missing or unvalidated records are returned as missing/partial or rejected according to the contract.

- [x] **Step 2: Implement read-only query functions**

Queries must use parameterized SQL, deterministic ordering, and no network calls. They must not calculate ratios from prose or silently substitute fallback macro data for official data.

- [x] **Step 3: Run query and contract tests**

Run: `$env:PYTHONPATH='src'; python -m unittest discover -s tests -p 'test_query.py' -v; python -m unittest discover -s tests -p 'test_schema.py' -v`

Expected: PASS against a temporary gold fixture.

### Task 8: Close the data-foundation gate and hand off to baseline build

**Files:**
- Create: `.agents/handoffs/data-foundation-readiness.md`
- Create: `reports/data-foundation/readiness-decision.md`
- Modify: `.agents/project-state/current.json`
- Modify: `.agents/project-state/events.jsonl`

**Interfaces:**
- Consumes: audit output, gold quality report, formula tests, document-quality report, and query-contract tests.
- Produces: a durable `READY_FOR_BASELINE` or `NOT_READY` decision with exact evidence paths and limitations.

- [x] **Step 1: Run the complete foundation test suite**

Run: `$env:PYTHONPATH='src'; python -m unittest discover -s tests -v`

Expected: PASS for all data-foundation tests; any unavailable integration test is explicitly labeled and not counted as validation.

- [x] **Step 2: Verify the gate checklist manually**

Confirm scope, periods, coverage, provenance, formulas, gold labels, conflict handling, document quality, and snapshot immutability against the reports rather than relying on exit code alone.

- [x] **Step 3: Write the readiness decision**

Use `READY_FOR_BASELINE` only when every mandatory gate passes. Otherwise use `NOT_READY`, name the blocking metric/source/period, and preserve the staging snapshot.

- [x] **Step 4: Record the handoff and state event**

Update project state with the decision, artifact paths, test command, result, and known limitations. The next plan may start baseline work only after a `READY_FOR_BASELINE` decision.

## Plan self-review

- The plan covers the design requirements for scope, data foundation, provenance, deterministic calculations, evidence, validation, and the baseline handoff.
- No task promotes staging data automatically; promotion is gated and fail-closed.
- The invalid provisional quarter-end dates are tested at the source of generation rather than patched only in a report.
- The plan keeps the five-bank/eight-quarter scope separate from the later agent-system plan.
- The plan leaves raw data and thesis source artifacts untouched.
- No placeholder tasks remain; every task names files, interfaces, commands, and expected outcomes.
