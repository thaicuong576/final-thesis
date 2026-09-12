# Pre-Phase-4 Internet Data Acquisition Report

Status: acquisition package complete for this bounded pass; candidate-only,
not Gold promotion.

Canonical base: `0675869956888926963cf90a0280143b1b730cd3`

Branch: `prep/pre-phase4-data-acquisition`

No Phase 4 capability, Phase 5 orchestration, RAG, chunking, embeddings or
vector database was implemented.

## Executive summary

This pass acquired and registered a small official-source package for the
future Macro and Sector/Peer capabilities. The strongest new structured result
is the NSO 2024 statistical summary candidate of `15.1%` credit growth at
31/12/2024. It is not promoted because its source-native rounding and exact
definition still need reconciliation against the frozen `macro.credit_growth`
contract.

The current result is:

```text
macro.policy_rate       candidate packaged, previous review preserved
macro.credit_growth     official candidate found, review required
native sector NPL       unavailable in this bounded pass
native sector credit    official source package acquired, row mapping pending
company/peer Gold       unchanged; five-bank sample is not the sector
```

The package contains 16 retrieved records (7 structured artifacts and 9
documents), 6 explicitly recorded failed routes, and 5 conservative candidate
observation records. Every retrieved local file has a SHA-256 entry in the
[acquisition manifest](../data/manifests/pre-phase4-acquisition-v1.jsonl).

## Structured acquisition results

### `macro.credit_growth`

Acquired:

- [NSO 2024 statistical summary PDF](../data/raw/pre-phase4-acquisition-v1/structured/nso/nien-giam-tom-tat-2024.pdf)
- [NSO 2024 Statistical Yearbook PDF](../data/raw/pre-phase4-acquisition-v1/structured/nso/NGTK-Cuc-TK-2024_BQ.pdf)
- [SBV credit-statistics route artifact](../data/raw/pre-phase4-acquisition-v1/structured/sbv/sbv-credit-statistics-route.html)
- [SBV 2024 API negative-evidence artifact](../data/raw/pre-phase4-acquisition-v1/structured/sbv/sbv-credit-statistics-api-2024.json)

The NSO summary's page-15 sentence states that at 31/12/2024 credit growth
of the economy reached 15.1% compared with end-2023. It is registered as:

```text
entity        = VN
metric_id     = macro.credit_growth
value         = 15.1
unit          = percent
period        = 2024_Q4
as_of_date    = 2024-12-31
period_basis  = annual_change_vs_end_2023
status        = review_required
```

This does not overwrite the previous `DATA_UNAVAILABLE` adjudication. The new
source must first pass the existing acquisition/reconciliation and Gold
promotion rules.

### `macro.policy_rate`

The prior SBV official API artifact was packaged again, with its source-native
record and stable locator preserved:

```text
metric_id      = macro.policy_rate
rate           = SBV refinancing rate
value          = 4.5% per annum
effective_from = 2023-06-19
as_of_date     = 2024-12-31
alignment      = latest_effective_state_at_period_end_v1
```

The policy record is registered as a candidate in this package. No new Gold
promotion was performed.

### Native-sector structured candidates

The NSO yearbook and banking-statistics catalogue are independent aggregate
sources, not five-bank peer data. The package registers:

- proposed `sector.system_credit_growth`: `15.1%`, review required;
- proposed `sector.system_credit_outstanding`: value null, mapping pending;
- proposed `sector.system_npl_ratio`: explicit missing with `DATA_UNAVAILABLE`.

No company observation was relabelled as a native sector observation.

## Successful official sources

The successful source package consists of National Statistics Office PDFs and
landing pages, prior-acquired State Bank of Vietnam public API/page artifacts,
and Government Portal legal documents. The manifest records the publisher,
source URL, retrieval method, timestamp when known, source tier and hash for
each item. The SBV-hosted research article is retained for discovery and
cross-check only; it is not treated as primary evidence.

## Unstructured corpus inventory

The unstructured lane stops after preservation and hashing. No chunking,
embedding, vector indexing, RAG or regulatory-prose extraction was performed.

### Law and legal framework

- [Luật Các tổ chức tín dụng 32/2024/QH15, part 1](../data/raw/pre-phase4-acquisition-v1/documents/laws/Luat-Cac-To-Chuc-Tin-Dung-32-2024-QH15-part1.pdf)
- [Luật Các tổ chức tín dụng 32/2024/QH15, part 2](../data/raw/pre-phase4-acquisition-v1/documents/laws/Luat-Cac-To-Chuc-Tin-Dung-32-2024-QH15-part2.pdf)
- [Official Government metadata page](../data/raw/pre-phase4-acquisition-v1/documents/laws/Luat-32-2024-QH15-official-page.html)

### SBV regulations and policy context

- [Thông tư 06/2024/TT-NHNN](../data/raw/pre-phase4-acquisition-v1/documents/circulars/Thong-tu-06-2024-TT-NHNN.pdf)
- [Thông tư 09/2024/TT-NHNN official publication page](../data/raw/pre-phase4-acquisition-v1/documents/circulars/Thong-tu-09-2024-TT-NHNN.html)
- [Official Government policy-rate context article](../data/raw/pre-phase4-acquisition-v1/documents/decisions/sbv-policy-rate-decision-context-2023-06-16.html)

The policy-rate context article is marked secondary official context. The
primary policy observation remains the SBV API artifact and prior adjudication.

### Macro and sector statistical reports

- [NSO banking-statistics catalogue](../data/raw/pre-phase4-acquisition-v1/documents/sector-reports/nso-banking-statistics-landing.html)
- [NSO Statistical Yearbook 2024 landing page](../data/raw/pre-phase4-acquisition-v1/documents/sector-reports/nso-statistical-yearbook-2024-landing.html)
- [SBV 17/09/2024 credit-growth article](../data/raw/pre-phase4-acquisition-v1/documents/macro-reports/sbv-credit-growth-2024-09-17.html)
- [SBV 18/03/2025 research lead](../data/raw/pre-phase4-acquisition-v1/documents/macro-reports/sbv-credit-growth-lead-2025-03-18.html)

The SBV-hosted 15.08% research article is discovery/cross-check material only.

No additional company documents were downloaded because the existing corpus
already covers the selected company sample and duplication was out of scope.

## Source hierarchy and trust assessment

1. NSO/GSO and SBV official statistical PDFs/APIs/pages: primary candidates.
2. Government portal and Electronic Gazette legal artifacts: primary legal
   documents/publication records.
3. Government context article: official secondary context.
4. SBV-hosted Tạp chí Ngân hàng research article: secondary research lead.

Successful HTTP retrieval is not treated as acceptance. The manifest records
source tier and candidate status separately.

## Metric-definition and period findings

`macro.credit_growth` is kept as annual change at 31/12/2024 compared with
31/12/2023. The NSO value is source-native rounded `15.1%`; the package does
not convert it into `15.08%` or derive a more precise value.

`macro.policy_rate` is an effective-state observation, carried forward from
2023-06-19 to the 2024-12-31 analytical boundary.

`sector.system_npl_ratio` is not created from five-bank NPL values. The sector
entity remains independent and the missing candidate is explicit.

The full candidate reconciliation is in
[reconciliation.md](../data/reconciliation/pre-phase4-acquisition-v1/reconciliation.md).

## Downloaded artifact inventory

The package contains `16` retrieved files:

- `7` structured artifacts under
  `data/raw/pre-phase4-acquisition-v1/structured/`;
- `9` unstructured documents under
  `data/raw/pre-phase4-acquisition-v1/documents/`.

The exact file-level inventory, including local paths, original filenames,
MIME types and SHA-256 hashes, is the machine-readable
[acquisition manifest](../data/manifests/pre-phase4-acquisition-v1.jsonl).
The raw package is preserved byte-for-byte; the scoped `.gitattributes` rule
prevents Windows line-ending conversion for these artifacts.

## Candidate observations

The candidate registry contains five records and no `ACCEPTED` record:

| Candidate | Value/status | Interpretation |
|---|---:|---|
| `macro.policy_rate` | `4.5`, `REVIEW_REQUIRED` | SBV refinancing rate, carried from 2023-06-19 to 2024-12-31 |
| `macro.credit_growth` | `15.1`, `REVIEW_REQUIRED` | NSO year-end candidate, rounded source-native value |
| `sector.system_credit_growth` | `15.1`, `REVIEW_REQUIRED` | Aggregate candidate, not five-bank peer data |
| `sector.system_credit_outstanding` | `NULL`, `REVIEW_REQUIRED` | Exact official table row mapping pending |
| `sector.system_npl_ratio` | `NULL`, `MISSING` | `DATA_UNAVAILABLE`; no sufficiently clear official year-end observation |

The complete normalized records, raw values, locators and reasons are in the
[candidate registry](../data/reconciliation/pre-phase4-acquisition-v1/candidate-observations.jsonl).

## Unresolved/missing data

- `macro.credit_growth` remains review-required because the `15.1%` source is
  rounded and still needs reconciliation against the frozen contract and any
  exact year-end stock inputs.
- `sector.system_credit_outstanding` remains unmapped until a controlled
  table/row extraction establishes the exact aggregate definition and value.
- `sector.system_npl_ratio` remains explicit `MISSING / DATA_UNAVAILABLE`.
- The existing policy-rate adjudication is preserved, but this acquisition
  pass does not promote a new Gold observation.
- The `15.08%` SBV-hosted research statement remains secondary and is not used
  to resolve the macro credit-growth cell.

## Credit-growth reconciliation

| Value | Source meaning | Result |
|---|---|---|
| 7.38% | SBV observation at 17/09/2024 | Out of period |
| 15% | SBV orientation/target | Not an observation |
| 15.08% | SBV-hosted research statement | Secondary lead, not Gold |
| 15.1% | NSO year-end summary statement | Official candidate, review required |

The official SBV credit-statistics route remains valuable, but the bounded
prior API response has no exact 2024 Q4 row. The route and empty result are
preserved as negative evidence rather than converted into a missing source
claim without provenance.

## Failed acquisition routes

The manifest records:

- HTTP 403 on the direct VBPL law PDF route; Government Portal PDF succeeded;
- HTTP 403/WAF on current SBV policy page;
- HTTP 403/WAF on current SBV credit-statistics route;
- HTTP 403/WAF on an SBV sector-survey PDF;
- HTTP 502 on the Công báo PDF CDN for Thông tư 09;
- HTTP 403/WAF on a new direct SBV API attempt.

No access-control circumvention was attempted. Alternate official pages or
previously acquired artifacts were used only when their identity and hash were
preserved.

## Hash and provenance coverage

The manifest includes for each retrieved file:

- source/artifact or document ID;
- publisher and source URL;
- relative local path;
- MIME type and original filename;
- SHA-256 content hash;
- retrieval method and timestamp when known;
- primary/secondary classification;
- acquisition status and notes.

Existing SBV artifacts reused from the previous tracked macro acquisition keep
`retrieved_at_utc=null` because their original retrieval time is not known; the
script does not fabricate it.

The candidate registry contains only source-referenced values or explicit
missingness. No candidate is marked accepted.

## Reproducibility assessment

The new branch contains the acquisition script, manifest, candidate registry,
reconciliation, report and raw files. Run:

```text
python scripts/acquire_pre_phase4.py --verify
python -m unittest discover -s tests -p 'test_pre_phase4_acquisition.py'
```

The script verifies file existence, non-empty artifacts, unique IDs, hashes and
known candidate source references. Dynamic/WAF routes remain documented as
unstable; the package does not depend on silently repeating those routes.

## Verification record

- Acquisition verification: PASS (`16` retrieved records, `7` structured
  artifacts, `9` documents, `6` failed routes, `5` candidates).
- Focused acquisition and existing data/regression tests: `43/43` PASS.
- Architecture guard: PASS.
- Python compile check (`compileall`): PASS.
- Non-raw code/metadata whitespace check (`git diff --check`): PASS. Downloaded
  HTML source files contain source-native trailing whitespace; they were left
  unchanged so their manifest hashes remain exact.
- Raw artifact byte/hash check: PASS for all `16` retrieved files.
- Correctly configured full-suite run (`PYTHONPATH=src`): `600` tests run,
  `590` passed, `5` failures and `5` errors. The untouched canonical base
  produced the same pre-existing `5` failures and `5` errors on `593` tests;
  the acquisition package therefore introduced no observed change to those
  baseline failures. The failures concern ignored historical Gold/review
  artifacts and baseline question-set hashes, not this acquisition package.

## Potential licensing/republication concerns

The package uses publicly accessible government artifacts for research. Before
external redistribution, verify the relevant portal terms and prefer sharing
metadata, hashes and source links rather than republishing full documents.

## Recommended next steps

1. Independently review the NSO 15.1% candidate and decide whether the frozen
   contract accepts source-native rounded precision or requires the exact
   year-end stock pair.
2. Controlled-extract the yearbook credit-outstanding row and preserve table,
   page, units and vintage before registering stock observations.
3. Search/acquire a definitionally clear year-end native system NPL source.
4. Choose one canonical company Gold scope (pilot or five-bank expansion).
5. Package the selected dataset snapshot and capabilities before final Phase 4
   evaluation.

## GO/HOLD verdict

```text
Phase 4 capability planning/design       GO
Final Macro Gold completion              HOLD
Native Sector Agent with accepted data   HOLD
Final experiment/evaluation              HOLD
```

The data acquisition task is successful even though native sector NPL remains
unavailable: uncertainty is explicit, official raw evidence is preserved, and
no unsupported observation was promoted.
