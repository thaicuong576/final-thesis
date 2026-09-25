# TASK — P2 peer-data readiness and P4 evaluation inputs

## Dispatch
- Role: `worker-data`
- Base: `origin/main@9e0298a3de01c31b01a412ec574f265eeb79d2ea`
- Branch: `codex/p4-evaluation-20260925`
- Tracking: Linear intentionally omitted because the user explicitly asked to skip Linear.
- Binding sources: `.agent/foundation/*`, `docs/ARCHITECTURAL-GUARDRAILS.md`, `docs/DATA-CONTRACT.md`, `docs/EVALUATION-PROTOCOL-V1-DRAFT.md`, Gold v5 authority records, decisions D-063/D-069–D-072.

## Objective
Prove that the provider-neutral data layer can supply the frozen five-bank peer inputs needed by P2 and reproducible A/B/C evaluation without hard-coding bank-specific logic or mutating source data.

## Required behavior
1. Audit the actual Gold v5 artifact/provider path for ACB, TCB, VPB, MBB, VCB; verify period, unit, scope, source locators, validation state, and four explicit missing cells.
2. Add the minimum provider-neutral peer retrieval or deterministic benchmark support needed by the runtime, only if absent.
3. Preserve explicit peer-universe membership and denominator; never label the five-bank sample as the whole sector.
4. Derived peer values must retain member observation IDs, formula/aggregation version, eligible denominator, and missing reasons.
5. Freeze 8–12 evaluation task specifications covering company-only, peer, combined complexity, invalid scope, and missingness. Macro tasks may be included only if validated same-period macro capability exists.
6. Produce machine-readable task and expected-coverage manifests. Do not create completed A/B/C results unless real runs execute.
7. Keep CTG as a transferability case outside Gold; do not silently add it to the Gold benchmark.

## Scope
- Allowed: `src/thesis_data/`, data-focused tests, immutable evaluation manifests under `data/evaluation/` or `reports/evaluation/`, and directly related scripts.
- Forbidden: `src/thesis_api/`, `frontend/`, in-place mutation of raw/Gold/root SQLite, synthetic evidence or labels.
- Do not change `contracts/schema.sql`; report any required schema change to Lead.
- Record unforeseen issues in `.agent/memory/lessons-learned.md`.

## Verification and handoff
Verify source hashes and SQLite integrity, run focused tests, the full Python suite, and architecture guardrails. Confirm the root DB checksum remains `7993005474B8E0C3F91261B0E39AC140B43AC98BD0A167E0C8EBC274E4834A86`. Commit, push, open a PR titled `feat(data): freeze peer evaluation inputs`, wait for all CI checks, and report the standard handoff. Do not merge.
