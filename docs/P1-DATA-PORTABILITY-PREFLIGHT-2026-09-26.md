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

## Evidence gate still to resolve

The repository contains `data/onboarding/ctg-2024-audited-2024q4-v1.json`, its source manifest, and reconciliation ledger. The manifest identifies an audited consolidated filing by SHA-256 `36513DD8B060712B188F9EAB03B1A7F9479AB21E63866DD95E45759D03EC5369` and describes manual visual review rather than OCR acceptance. This metadata is not proof that the raw source bytes are present or that every candidate row passes the current contracts. The data worker must verify the original file by an explicit evidence root and reconcile each observation. If it cannot, the candidate remains unpromoted and the exact blocker is recorded.

## Phase gate

P1 passes only when the criteria in `TASK.md` are evidenced in tests and a clean operational snapshot/provider handoff, without Gold mutation or unsupported acceptance. Candidate-only success is not a pass. Any needed contract/schema change or missing primary evidence returns to the Lead for an explicit decision before promotion.
