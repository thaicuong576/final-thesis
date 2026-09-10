# Priorities and scope trade-offs

This is the operational priority list for the applied thesis. It intentionally
separates what must be true for a defensible result from what is merely attractive
to demo.

## P0 — Freeze the research contract, then time-box the scope

Confirm with the advisor the research question, three experiment arms, source
policy, output contract, scoring rubric, and the gated scope strategy. Do not
promise five banks × eight quarters as the minimum before the 48-cell pilot is
reconciled. Keep the five-bank/eight-quarter design as the provisional upper
bound, with the 48-cell pilot, the 36-cell metric-reduced fallback, and the
80-cell post-pilot expansion recorded in
`docs/SCOPE-STRESS-TEST.md` and `docs/NEXT-PHASE-PRIORITIES.md`.

Why first: changing the universe or period after labeling invalidates coverage,
peer medians, experiment inputs, and parts of the thesis. The first advisor
decision should approve the go/no-go rule; the final row count should follow
measured source feasibility, not optimism about the vendor database.

## P1 — Make a small gold dataset, not a large untrusted database

Use the current SQLite files as immutable staging. Reconcile the 48 pilot cells to
issuer filings or official IR KPI tables, preserve vendor rows as cross-checks,
and create a separate versioned gold snapshot only after the gates pass.

Initial target: 48 pilot cells; the full proposed target is 200 primary metric
cells, while 80 cells is an optional post-pilot expansion. Whichever scope is
frozen, require at least 40 manual metric/evidence labels covering every bank,
at least two periods per bank, and every
primary metric. The review worksheet is
`data/reconciliation/gold-bank-2025-pilot-v1/register.csv`; every row must carry an
official locator or a justified missing reason. The separate
`data/reconciliation/gold-bank-2025-v1/register.csv` remains the 200-cell upper
bound and must not be mistaken for the active pilot. A gap is recorded as null
with a reason, not imputed.

The private Checker-A first pass produced a timestamp-based planning signal of
111.4 rows/hour for 48 rows. The signal is recorded in
`reports/data-foundation/pilot-review-throughput-signal.md`, but it is not
human OCR/manual throughput, independent-review evidence, or Gold evidence.
It does not justify expanding to 80 or 200 cells before Checker B and
adjudication.

Why: the current staging has breadth, but all sources are pending/failed and vendor
semantics are not yet proven. The seven sampled ACB/VPB PDFs are scan-only, so
full-PDF extraction is a measurable OCR/manual workload rather than an assumption.

## P2 — Resolve semantics before adding agents

Freeze period boundaries, source basis, units, consolidated/standalone meaning,
YTD-to-quarter normalization, profit convention, and sign convention. Reconcile
the negative staged CIR and reserve-coverage values before using them.

Why: a sophisticated agent cannot repair an undefined metric; it can only make an
ambiguous number sound more convincing.

## P3 — Use three fair experiment arms

Compare single-agent, hierarchical without critique, and hierarchical with bounded
critique. Give all arms identical tools, accepted facts, source policy, model
configuration, questions, and output contract. Treat “no improvement” as a valid
result.

Why: this distinguishes the value of decomposition from the value of critique and
avoids a weak comparison between an informed multi-agent system and an underpowered
baseline.

## P4 — Build only the minimum agent behavior

Agents retrieve, explain, critique, and synthesize. Deterministic code owns
normalization, formulas, peer statistics, period checks, provenance, and anomaly
triggers. The critique loop is capped at two attempts and unresolved cases are
reported.

Defer: vector database, realtime feeds, investment execution, broad securities
coverage, and universal claims about multi-agent superiority.

## P5 — Write chapters from durable evidence

Write Chapters 1–4 while reconciliation and baseline code progress. Freeze Chapters
5–6 only from reproducible run manifests, gold labels, parser reports, and blind
review outputs. Do not turn design intentions or successful downloads into results.

## Current decision

The recommended route is a source-grounded applied system with controlled
multi-agent evaluation. The current project is ready for reconciliation,
scaffolded build work, and parallel thesis drafting of stable chapters, but not
yet ready for comparative experiments. The authoritative gate is
`reports/data-foundation/readiness-decision.md`; the operational next-phase
backlog is `docs/NEXT-PHASE-PRIORITIES.md`. The independent phase-entry audit is
recorded in `docs/PHASE-ENTRY-REVIEW-VI.md`.
