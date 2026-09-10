# Data Foundation Readiness Checklist

Status: `NOT_READY_FOR_BASELINE`

This checklist is the promotion gate between the current staging snapshot and the first baseline experiment. A successful download or a successful command is not sufficient evidence of readiness.

## Scope tracks

The first-baseline gate applies to the default 48-cell pilot: `ACB`, `TCB`, and
`VPB`; `2024_Q1`--`2024_Q4`; and NPL group 3--5, reserve coverage, ROA, and
ROE. The original five-bank/eight-period configuration below is an expansion
candidate and is not a blocker for the first baseline. If the advisor selects
an expansion, its selected manifest must replace the pilot scope before the
same gates are rerun.

The primary evaluation can use `experiments/question-set-core-v1.json`, which
has 13 bank-focused questions and excludes the macro-to-bank extension. The
macro-specific source gate below applies when that extension is retained in a
primary aggregate; it is not a reason to use fallback macro observations or to
block the bank-core comparison.

## Frozen missing-data policy (D-055)

- A missing cell is represented by `value=null` and `quality_status=missing`.
- The record must include a concrete reason: no approved primary source,
  unreadable or unstable evidence, or unresolved metric-definition conflict.
- No guessed value, silent zero fill, silent imputation, or unapproved vendor
  substitution is allowed.
- Fallback sources require explicit pre-review approval in a manifest or
  decision record.
- Numeric accuracy and peer averages use only accepted numeric Gold values.
  Missing cells are excluded from that denominator but their expected/valid/
  missing/conflict counts and the denominator must be shown in the report.
- Missing-data behavior is evaluated separately from numeric accuracy.

## Gate 0P — first-baseline pilot scope

- [x] Three-issuer pilot registry is recorded with inclusion reasons.
- [x] Four pilot periods are recorded as `2024_Q1` through `2024_Q4`.
- [x] Four core metrics are recorded with conditional CIR/NIM handling.
- [ ] Advisor confirms the gated pilot-first strategy and cutoff rule.

## Gate 0E — expansion scope (deferred)

- [ ] Five-bank registry is recorded with inclusion reasons.
- [ ] Eight benchmark periods are recorded as `2024_Q1` through `2025_Q4`.
- [ ] Benchmark cutoff/publication-availability rule is recorded.
- [ ] All period boundaries are valid calendar dates.
- [ ] TCBS is excluded from the primary benchmark unless its identity and data coverage are resolved before freeze.

## Gate 1 — raw-source integrity

- [x] Raw structured responses are preserved under `data/raw/structured-2026-09-01-v1/`.
- [x] Retrieved annual-report files have hash records.
- [ ] Each accepted source has publisher, URL, retrieval time, local path, content hash, source tier, and license note.
- [ ] Failed retrievals remain recorded in the manifest.
- [ ] Restatements and superseding records have explicit identity rules.

## Gate 2 — coverage and semantic validation

- [x] Coverage is reported by selected ticker, metric, and period for the pilot
      Gold snapshot.
- [ ] Raw statement-package availability is at least 95% for required packages.
- [x] Core metric validated coverage is at least 90%, or every gap has an explicit exclusion reason.
- [x] Pilot metric labels, units, report basis, and period semantics are
      reconciled to primary evidence; wider-scope vendor rows remain staging.
- [ ] Official SBV/GSO evidence is used for every macro variable retained in the primary benchmark or macro extension.
- [ ] Market-data unit and traded-value semantics are validated before ADTV is used.

## Gate 3 — normalization and formulas

- [ ] `docs/METRIC-DICTIONARY.md` is approved for every retained metric.
- [ ] Point-in-time and flow/YTD/FY values are separated.
- [ ] Unit conversions are explicit and tested.
- [x] Missing values are null with a reason; no silent zero filling exists.
- [x] D-055 freezes explicit missingness, approved-fallback, visible-denominator,
      and missing-data-reporting rules.
- [x] Derived metrics retain input facts and formula version.
- [x] Duplicate, date, unit, and cross-source conflict checks pass for the
      promoted pilot observations.

## Gate 4 — document evidence

- [x] Selected PDFs have text-layer/page-count/parser status records.
- [ ] Evidence snippets contain source ID, document, page or explicit non-paginated reason, section, period, ticker, and quote.
- [x] Table-extraction warnings are recorded.
- [ ] Quarterly evidence gaps are either filled from issuer/exchange routes or reported as missing.
- [ ] Vector retrieval is not used as a substitute for the original document/page reference.

## Gate 5 — gold promotion

- [x] A new versioned Gold database is created without overwriting staging.
- [x] At least 40 metric/evidence items are manually checked.
- [x] The manual checks use at least two independent checker IDs.
- [x] The manual sample covers every selected bank, at least two periods per bank, and every primary metric.
- [x] Every selected `(ticker, period, metric)` target cell has a linked `value_check` decision, including reasoned missing cells.
- [x] Every published Gold observation has complete provenance.
- [x] Critical/major conflicts are resolved or excluded.
- [x] The Gold snapshot has a unique versioned snapshot ID and immutable input lineage.
- [x] Blind review tooling keeps checker A and checker B decisions in separate
      copies and preserves disagreements for adjudication.
- [x] An eligible merged ledger can be exported to validated `GoldLabel` JSONL
      rows through a non-mutating, append-safe importer.

## Gate 6 — baseline handoff

- [x] Query functions read only accepted gold observations.
- [x] Contract and query tests pass.
- [x] Coverage and quality reports are stored with the Gold snapshot.
- [x] The readiness decision is `NOT_READY` with exact remaining handoff/provider
      blockers.

## Current known blockers

The wider SQLite staging snapshots are not Gold. The 48-cell bank-core pilot
now has a promoted Gold snapshot with `44/48` valid numeric observations and
`4/48` explicit missing cells. Remaining blockers for provider-backed baseline
are formal advisor confirmation of pilot scope/cutoff, a selected provider/model
configuration, and an injected real transport. Official macro evidence remains
an additional blocker for the macro extension, but not for the bank-core
question set. The invalid legacy period table, TCBS uncertainty, and unchecked
vendor breadth remain expansion-scope issues, not reasons to require 200 cells
before the first baseline.

The feasibility pilot has now confirmed a source-strategy split: the initial
ACB/VPB quarterly PDFs are scan-only, but searchable VPB lookup versions are
available for all four 2024 quarters, while a TCB FY24 analyst presentation
provides a text-layer KPI table for four quarters. The current recommended path
is official-KPI-first with searchable filing versions where available and
issuer-IR HTML candidates for selected ACB metrics, with bounded OCR/manual
review for the remaining ACB cells. Four official VPB performance packs are
also text-layered, but their inspected KPI pages are standalone (`RIÊNG LẺ`),
so they are not consolidated pilot evidence unless the scope is explicitly
changed. ACB's issuer pages also expose a Q4 NPL definition conflict (including
versus excluding CIC), so these candidates are not accepted automatically. The
TCB and VPB candidate observations are intentionally rejected by the baseline
guard until they are promoted through the same gold gates.

An additional official ACB Q2 alternate PDF was tested and remains scan-only
under the local parser (0/30 text-layer pages). Search-engine OCR is not treated
as a substitute for a stable page-aware evidence record.
