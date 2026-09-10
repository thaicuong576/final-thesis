# Scope stress test and fallback plan

This document tests whether the proposed benchmark is feasible as an applied
undergraduate thesis. It does not silently replace the provisional selection in
`data/manifests/gold-bank-2025-v1/selection.json`.

## Assumptions that must hold

The full proposal assumes that:

1. five banks have comparable consolidated disclosures for all eight quarters;
2. the vendor fields map to the thesis metric definitions without hidden sign,
   unit, TTM, or restatement differences;
3. official PDFs can be searched or manually checked within the available time;
4. 200 metric cells plus evidence labels can be independently reviewed;
5. the gold set will be large and consistent enough to distinguish the three
   agent arms, not merely demonstrate that the software runs.

The first three assumptions are not established. The current staging has 200/200
candidate rows, but 0/200 accepted gold rows; two sampled official ACB PDFs are
scan-only; and the vendor CIR and reserve-coverage values have unresolved sign
conventions. Therefore candidate-row count must not be presented as database
completeness.

The pilot source audit adds a stronger warning: seven official ACB/VPB PDFs were
retrieved, and all seven were scan-only with no extractable text layer. This makes
“one full PDF per issuer-period” a source-acquisition strategy with material OCR/
manual cost, not a free completeness guarantee.

The counterexample is TCB's FY24 analyst presentation: one text-layer document
contains source-disclosed KPI rows for all four 2024 quarters. This supports an
official-KPI-first ladder, but not automatic acceptance, because definition and
publication-cutoff checks still apply.

## Scope options

| Option | Coverage | Primary metrics | Use | Decision rule |
|---|---:|---|---|---|
| Full proposal | 5 banks × 8 quarters = 40 bank-periods | 5 metrics = 200 cells | Strongest trend story, highest execution risk | Use only if the pilot reaches source-reconciled coverage and the review workload is acceptable. |
| Recommended applied scope | 5 banks × 4 quarters = 20 bank-periods | 4 metrics = 80 cells; CIR conditional | Best balance for an undergraduate applied thesis | Prefer this if the pilot works but the full corpus is too slow or inconsistent. |
| Feasibility pilot | 3 banks × 4 quarters = 12 bank-periods | 4 metrics = 48 cells | Go/no-go before provider-backed comparative experiments | Must include at least two bank types/scale profiles and all four core metrics; complete this before claiming baseline readiness. |
| Metric-reduced fallback | 3 banks × 4 quarters = 12 bank-periods | 3 metrics = 36 cells; ROA excluded conditionally | Preserve issuer and period diversity when one metric is not comparable | Use only if ROA cannot be reconciled for ACB and the advisor confirms the reduction; current candidate routes cover 35/36 cells. |

The four core metrics for the reduced options are NPL group 3–5, loan-loss
reserve coverage, ROA, and ROE. CIR remains valuable, but it is conditional until
its sign and definition match the issuer disclosures. NIM remains conditional for
the same reason documented in the metric dictionary.

## Recommended sequence

1. Reconcile the 48-cell pilot using official issuer evidence, with at least 40
   labels and page/table locators. Prefer official KPI pages/releases for the
   pilot and use scan-only PDFs only for a bounded sample.
2. Measure actual review throughput, scan/OCR burden, conflict rate, and missing
   rate. Do not estimate these from the vendor row count.
3. If the pilot passes, keep the 48-cell pilot as the first reproducible
   benchmark. Consider the 80-cell recommended expansion only after the measured
   review/OCR burden is acceptable and the advisor wants broader peer coverage.
4. Promote a gold snapshot and run all three agent arms on the same snapshot.
5. Expand to 200 cells only as a documented extension or after the same gates
   pass for every added cell.

If the KPI-first ladder cannot provide four comparable metrics for three banks and
four periods, reduce the pilot to the largest fully source-reconciled set and
record the missing cells. The current concrete fallback is recorded in
`data/manifests/gold-bank-2025-pilot-v1/fallback-36-selection.json`: retain NPL,
coverage, and ROE for ACB/TCB/VPB over four quarters and treat ROA as conditional.
This is a proposed scope artifact, not an accepted Gold selection. Do not use the
vendor database to manufacture coverage.

## Independent judgment

The multi-agent comparison is feasible at the 48–80-cell scale because the
experiment tests answer quality, evidence grounding, anomaly handling, latency,
and cost—not database size alone. The full 200-cell design is academically
attractive but should be treated as a conditional upper bound, not the minimum
definition of success. If the advisor requires the eight-quarter scope, the safer
trade-off is to keep four core metrics and report CIR as an explicitly unresolved
or extension metric rather than forcing five ambiguous metrics into gold.
