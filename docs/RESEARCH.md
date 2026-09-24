# Research Register

## Reviewed materials

- `docs/Khoá luận tốt nghiệp - Cường - GVHD_ Lê Văn.md`, converted from the 33-page thesis PDF.
- `docs/thesis_images/page-028-image-01.png`, overall data-flow diagram.
- `docs/thesis_images/page-031-image-01.png`, cross-level critique-loop diagram.
- `docs/PRODUCT-DIRECTION-SOURCE-DRIVEN.md`, source-driven product framing.
- Current source manifests, staging database reports, and research handoffs under `.agents/handoffs/` and `data/manifests/`.

## Established design direction

The project uses a source-grounded data foundation and evaluates Macro, Sector, and Company agents coordinated by a Master Orchestrator. Deterministic code owns source normalization, formulas, peer statistics, period/unit validation, and anomaly triggers. Agents retrieve, explain, verify, and synthesize evidence.

The default first applied-thesis benchmark is the 48-cell pilot: ACB, TCB, and
VPB over the four 2024 quarters. The five-bank/eight-quarter design remains a
conditional expansion upper bound. Securities companies and TCBS remain
extension material until their identity, coverage, and metric comparability are
resolved.

## Current data truth

- The wider candidate SQLite snapshots remain staging, not gold; the separate
  pilot snapshot `data/processed/gold-bank-2025-pilot-v1-adjudicated-v2.sqlite`
  is the promoted Gold artifact for the first bank-core baseline.
- Structured vendor responses contain statement histories for 15 of the 16 staged issuer identities; TCBS responses are empty.
- The selected public annual-report corpus contains 43 of 48 target issuer-year files; HDB 2023, STB 2023, and all TCBS documents are absent from the selected index.
- Daily market history exists through at least one tested source for 15 staged issuer identities, with source-specific gaps and pending unit/semantics validation.
- World Bank and DBnomics/IMF observations are fallbacks and do not replace official SBV/GSO evidence.
- The nine source records used by the promoted pilot are valid and provenance-
  linked; wider source records remain pending validation or failed and are not
  Gold truth.
- The provisional benchmark period table contains invalid month-end dates and must be regenerated through a calendar-aware validator.
- The candidate staging databases have no promoted benchmark truth. The separate
  pilot Gold snapshot contains 48 target observations (44 valid and 4 explicit
  missing), provenance/evidence records, and deduplicated Gold labels.
- A separate `normalized_candidate_bank-2025-v1.sqlite` now contains 200 mapped vendor-ratio rows for the proposed scope, explicitly marked TTM/vendor-native/pending; it is a reconciliation input and not an agent or gold source.
- The provisional five-bank/eight-quarter upper-bound selection is recorded in `data/manifests/gold-bank-2025-v1/selection.json`, but remains deferred pending the 48-cell pilot and advisor confirmation. The 2024 PDF quality audit shows heterogeneous text-layer coverage: VCB is text-searchable, while ACB and VPB are predominantly scan/mixed-text; table structure is not yet evaluated.
- Broad official source discovery for the upper-bound universe is recorded in `data/manifests/gold-bank-2025-v1/official-source-backlog.jsonl`. Discovery is not source acceptance: exact attachment URLs, hashes, licensing notes, and period-level reconciliation are still required. The active first-baseline source audit is under `data/manifests/gold-bank-2025-pilot-v1/`.

## Data classes and cadence

### Reference and configuration data

Ticker registry, sector membership, metric definitions, formulas, units, thresholds, source registry, fiscal-calendar rules, and evaluation questions are versioned repository data. They change only through recorded decisions.

### Periodic fundamental data

Quarterly and annual financial statements, ratios, company notes, sector aggregates, credit/deposit growth, and macro indicators are collected in fixed snapshots aligned to reporting period and publication date.

### Event-driven evidence

Company filings, annual reports, SBV circulars and decisions, GSO publications, exchange notices, and selected contextual research reports are collected when published or when a verification request requires supporting evidence.

### Market time series

Daily end-of-day prices, volume, market capitalization, and ADTV are optional context for the bank MVP. Intraday or continuous polling is not required to evaluate the architecture.

### Derived and validation data

Ratios, peer medians, percentiles, anomaly flags, gold labels, and evaluation scores are recomputed deterministically from versioned raw and normalized inputs.

## Source hierarchy

Official issuer/IR documents, SBV, GSO, HOSE, and HNX are primary sources where available. Vendor APIs are accelerators or cross-checks until reconciled. Research reports are contextual supplements. A source is usable only when it has stable identity, period coverage, field meaning, provenance, and a validation path.

## Metric findings

- Vietnamese interim income statements are YTD by default; quarter-only flow requires within-fiscal-year subtraction.
- Simple average beginning/ending stocks are used for average-balance ratios unless a source-disclosed convention is available.
- NPL group 3–5, loan-loss-reserve coverage, CIR, ROA/ROE, peer medians, and percentiles are candidates for the primary bank benchmark.
- NIM requires earning-asset mapping; CASA and LDR require category/definition mapping; CAR should use a source-disclosed regulatory value in the MVP.
- Missing values remain null; conflicting source variants are preserved.

## Outside-Gold source-backed transferability packet

The provider-neutral onboarding vertical slice records the VietinBank 2024
consolidated audited filing at
[`data/onboarding/ctg-2024-audited-2024q4-v1.json`](../data/onboarding/ctg-2024-audited-2024q4-v1.json).
The immutable source PDF is
[`data/raw/bank-onboarding-v1/ctg-2024-consolidated-audited.pdf`](../data/raw/bank-onboarding-v1/ctg-2024-consolidated-audited.pdf),
retrieved from the issuer's [investor relations filing](https://investor.vietinbank.vn/documents/20126/214683/BCTC%2Bhop%2Bnhat%2Bkiem%2Btoan%2Bnam%2B2024.pdf/a3536120-403d-0b92-4090-4e909fda27c2).
It is 5,651,992 bytes with SHA-256
`36513DD8B060712B188F9EAB03B1A7F9479AB21E63866DD95E45759D03EC5369` and has
69 PDF pages. The sidecar manifest records the byte count, URL, hash, and scan
status. The statement pages were manually inspected as rendered images because
the PDF has no selectable text layer; OCR output was not accepted as evidence.

The packet contains reconciled consolidated values for `bank.npl_g35`,
`bank.llr_coverage`, `bank.roa`, and `bank.roe` at `2024_Q4`. NPL and coverage
use Note 10 on PDF page 38 (printed page 36) and Note 11 on PDF page 39
(printed page 37); FY2024 profit
and total assets/equity inputs come from pages 7–10 (printed pages 5–8). The
ratios are 1.2190%, 174.6762%, 1.1536%, and 18.6012%, respectively. ROE uses
parent-attributable profit divided by average consolidated equity less
non-controlling interests, matching the metric dictionary. The packet stores
normalized monetary inputs in VND billion and records each physical/printed
page, table/note, row, and unit in its observation locator.

The companion
[`ctg-2024-audited-2024q4-v1-reconciliation.csv`](../data/onboarding/ctg-2024-audited-2024q4-v1-reconciliation.csv)
lists all 22 reported inputs and reconciled outputs with value, unit, period,
basis, scope, formula version/input IDs, page locator, reviewer/time, source
URL, and PDF hash. ROA and ROE are TTM metrics at `2024_Q4`; compare them with
other TTM values, not quarter-only profitability ratios.

These facts demonstrate reviewed outside-Gold transferability only. They do
not alter or extend Gold v5, and the existing Gold promotion gates still apply
before any new bank joins the evaluation benchmark.

## Research tasks before provider-backed baseline

1. Confirm the pilot-first scope strategy and benchmark cutoff with the advisor;
   keep the five-bank/eight-quarter design as a conditional expansion.
2. Confirm the final source/metric convention for any scope expansion.
3. Select a real provider/model, secret-free configuration, and injected
   transport implementation.
4. Change the readiness decision to `READY_FOR_BASELINE` only after the formal
   handoff is recorded.
5. Run the single-agent baseline, hierarchical-no-critique arm, and bounded-
   critique arm on the same promoted Gold snapshot and question set.
6. Score correctness, evidence, missingness/conflict handling, latency, calls,
   and cost before deciding whether to expand to 80 or 200 cells.

## Evidence and artifact paths

- `docs/METRIC-DICTIONARY.md`
- `docs/DATA-READINESS-CHECKLIST.md`
- `docs/EVALUATION-PROTOCOL.md`
- `data/manifests/coverage-matrix.md`
- `data/manifests/structured-coverage.md`
- `data/processed/README.md`
- `.agents/handoffs/research-metric-dictionary.md`
- `.agents/handoffs/research-validation-plan.md`
- `.agents/handoffs/dataset-structured-options.md`
- `.agents/handoffs/dataset-document-options.md`
- `.agents/handoffs/dataset-macro-market-options.md`
- `.agents/handoffs/data-foundation-design.md`
- `data/manifests/gold-bank-2025-v1/document-quality.jsonl`
- `data/manifests/gold-bank-2025-v1/official-source-backlog.jsonl`
- `data/manifests/gold-bank-2025-v1/normalized-candidate-report.md`
