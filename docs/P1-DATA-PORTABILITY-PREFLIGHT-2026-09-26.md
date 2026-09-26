# P1 data-portability preflight — 2026-09-26

## Scope and baseline

- Phase: P1, one validated operational onboarding path for a bank outside the Gold benchmark.
- Main baseline: `b87649af2c32f4499dcd6ebe82ae62799c9d5b1f` (PR #55 documentation sync).
- Candidate case: CTG 2024 Q4 packet. It remains a candidate until the source and observation gates below pass.
- Binding decisions/contracts: `docs/DECISIONS.md` D-069 and D-071, `docs/DATA-CONTRACT.md`, `contracts/bank-onboarding-packet-v1.schema.json`, `contracts/schema.sql`, and `docs/ARCHITECTURAL-GUARDRAILS.md`.

## Guardrail preflight

| Question | Decision before implementation |
|---|---|
| Can the reusable analysis core still run if the frontend and the current SQLite/Gold database are replaced? | It must. Gold SQLite and the operational CSV/onboarding adapter must provide the same canonical observations and capabilities through replaceable provider interfaces. No SQL, local path, fixed issuer list, or CTG-specific rule may enter the reusable core. |
| Does this phase increase dependence on Gold? | No. CTG is an out-of-Gold transferability case only. Gold v5 remains unchanged and is not the source of CTG acceptance. |
| Does this phase increase dependence on SQLite or a physical schema? | No new coupling is approved. A generic storage adapter may use SQLite, but operational snapshot promotion must be separate from Gold and mutable `analysis_runs`. If canonical DDL or a physical-schema exception is needed, stop for Lead review and a contract-first decision. |
| What is the current worktree database? | `worker-start.ps1` made an isolated copy of legacy `data/processed/finance_master_v2.sqlite` (source SHA `7993005474B8E0C3F91261B0E39AC140B43AC98BD0A167E0C8EBC274E4834A86`). It is not the ignored, hash-pinned Gold v5 artifact and must not be cited as Gold evidence. |
| How are raw and derived facts accepted? | Raw source bytes are immutable. Every direct observation needs primary-source reconciliation, an exact metric-specific locator, period basis, scope, unit, and review record. Derived values are recomputed at promotion from accepted inputs with a versioned formula and calculation receipt. Gold promotion remains a separate gate. |
| How are absent or ambiguous values handled? | `missing` is never zero. Unsupported mapping, ambiguous scope/period, absent evidence, invalid formula, or unresolved chart context stays missing/candidate or blocks promotion. |
| What does PDF/OCR support mean in this phase? | Text extraction/OCR/parser output can help create a candidate, never accepted financial evidence by itself. The user authorized a small LlamaParse pilot if a key is already configured: a few representative pages covering text/table and chart, checked against the original page with locator. Do not parse the full filing or expose the key. A chart needs visual context, labels, units, and locator; manual reconciliation against the original filing remains the acceptance path. |
| What claim may the result support? | At most, a demonstrated operational transfer path for the explicitly validated CTG snapshot and covered metrics/period. It cannot establish statistical representation of the Vietnamese banking sector or universal compatibility with arbitrary PDF/CSV files. |

## Evidence gate outcome

- Evidence-root invocation: `--evidence-root <worktree-root>`. The original PDF resolves at `data/raw/bank-onboarding-v1/ctg-2024-consolidated-audited.pdf`; its exact byte length is `5,651,992` and SHA-256 is `36513DD8B060712B188F9EAB03B1A7F9479AB21E63866DD95E45759D03EC5369`, matching the source manifest and packet. The PDF has 69 pages.
- Visual review of PDF pages 1, 5, and 6 confirms this is VietinBank's audited consolidated FY2024 filing and that Deloitte issued an unmodified opinion (printed pages 3–4). Pages 7, 8, 10, 38, and 39 (printed pages 5, 6, 8, 36, and 37) were visually checked against the packet's direct financial values and exact table/row/column locators. No chart-derived value is in this packet.
- The reconciliation register has 22 unique rows covering all 22 packet observations (15 directly reported inputs and 7 derived observations; no missing cells). Its metric, value, unit, period, basis, reporting scope, formula version, ordered input IDs, locator, reviewer, review time, decision, source hash, and source URL agree with the packet and manifest. The audit register is enforced before candidate materialization.
- `LLAMA_CLOUD_API_KEY` was absent, so no LlamaParse pilot or OCR was run. Manual visual reconciliation is the evidence path for this candidate.
- A separate accepted operational snapshot was materialized at `data/processed/onboarding/ctg-2024q4-operational-p1.sqlite` and read through `CanonicalSqliteDatasetProvider`. Dataset snapshot ID: `snapshot-b86db41dd976731cf3cf8c457c0874f8bea95798d9c42b3e3ff953efc8a58aaa`; local snapshot SHA-256: `81be2e1f7be707f3b1df3f45f780fdf0dbc0ee11ac925f23bf0e332ded2429ea`. Its status is accepted at the operational level; Gold benchmark promotion remains a separate gate. The Gold and analysis-run stores were not used as targets.
- Post-suite isolation check: the Gold v5 artifact at `data/processed/gold-bank-2025-expanded-v5-evidence.sqlite` still matches pinned raw-file SHA-256 `1b1b5c090d2f8ede87a4c33ea3ee716f7a54c9de7c51089f4d3893d7a1ffce73`; the explicit-root P4 verifier also passed and reported SQLite integrity `ok`. The operational snapshot's file path and filesystem identity differ from Gold. `data/processed/analysis_runs.sqlite` was absent, `ANALYSIS_RUNS_DB_PATH` was not configured, and the operational snapshot did not alias either run-history path.

## Phase gate

P1 passes only when the criteria in `TASK.md` are evidenced in tests and a clean operational snapshot/provider handoff, without Gold mutation or unsupported acceptance. Candidate-only success is not a pass. Any needed contract/schema change or missing primary evidence returns to the Lead for an explicit decision before promotion.
