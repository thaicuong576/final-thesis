# Pre-Gold decision pass — 2024 Q4

Status: **decision resolved; Gold promotion not performed**.

This is a small reconciliation layer over the immutable
`pre-phase4-acquisition-v1` package. It does not rewrite raw files, the
existing Macro Gold artifacts, the Gold schema, or runtime behavior.

## 1. `macro.credit_growth`

The National Statistics Office of Vietnam yearbook contains the exact
year-end aggregate table:

- PDF page `263` / printed page `102`;
- table: `Credit outstanding of credit institutions, branches of foreign bank
  as of annual 31st December`;
- `2023` outstanding: `13,569.7` trillion VND;
- preliminary `2024` outstanding: `15,617.1` trillion VND;
- growth-rate row for preliminary 2024: `15.1%`;
- definition: PDF page `222`.

This matches the frozen candidate semantics: percentage change in total credit
outstanding to the Vietnamese economy at `2024-12-31` compared with
`2023-12-31`, entity scope `VN`, period `2024_Q4`, unit `percent`, and basis
`annual_change_vs_end_2023`. The source is classified as a direct official
NSO statistical artifact, with the exact acquisition hash recorded in
`decision.json`.

The stock pair independently gives:

```text
(15617.1 / 13569.7 - 1) * 100 = 15.08802700133385410141712790%
```

Rounded to the source's one-decimal precision, this is `15.1%`. The source's
native `15.1%` remains the candidate value; the calculation is a check, not a
replacement. The `15.08%` SBV-hosted research statement is not used.

Decision: `DEFINITIONAL_MATCH_ACCEPTED_CANDIDATE`,
`DIRECT_OFFICIAL`, `review_required`, `not_promoted`. The decision resolves
the semantic/source debt at candidate level. It does not alter the existing
Macro Gold contract, which still requires its own review and materialization
gate before a runtime Gold row can become valid.

## 2. Macro and Sector reuse

The NSO table supplies one underlying aggregate fact. This pass does **not**
create a second `sector.system_credit_growth` observation. The stable
underlying candidate identity is:

`nso_statistical_yearbook_2024_table_102_credit_growth_2024_q4`

The Macro capability has a candidate mapping to `macro.credit_growth`. The
Sector capability may later expose a declared compatible alias only after its
metric/entity mapping is explicitly registered. The alias is not canonical,
not promoted, and is not a five-bank peer statistic.

## 3. `sector.system_credit_outstanding`

The exact yearbook table/row maps to:

```text
entity       = VN_BANKING_SYSTEM
metric       = sector.system_credit_outstanding
value        = 15617.1 VND_trillion
as_of_date   = 2024-12-31
period_basis = point_in_time_year_end
```

The candidate is `review_required` and `not_promoted` because the independent
Gold review/materialization gate has not been run. No inference from deposits,
liquidity, or a similar table is used.

## 4. `sector.system_npl_ratio`

The cell remains:

```text
value          = NULL
quality_status = missing
reason         = DATA_UNAVAILABLE
```

No five-bank peer median or other derived substitute is used.

## 5. What this pass did not do

- no raw acquisition artifact was changed;
- no existing Macro Gold row was promoted or changed;
- no schema or materializer code was changed;
- no RAG, vector store, broad search, Phase 4, or application runtime work was
  started.

Machine-readable details and hashes are in
`data/reconciliation/pre-gold-decision-2024-q4-v1/decision.json`.
