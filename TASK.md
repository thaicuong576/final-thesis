# Task manifest — P1 validated bank onboarding

## Identity

- Branch: `codex/p1-validated-bank-onboarding-20260926`
- Base: `b87649af2c32f4499dcd6ebe82ae62799c9d5b1f` (`main` after PR #55)
- Role: `worker-data`
- Tracker: No Linear issue, per the user's explicit waiver for this thesis workstream.
- Binding contracts: `docs/DATA-CONTRACT.md`, `contracts/bank-onboarding-packet-v1.schema.json`, `contracts/schema.sql`, `docs/DECISIONS.md` D-069 and D-071, `docs/ARCHITECTURAL-GUARDRAILS.md`.
- Preflight record: `docs/P1-DATA-PORTABILITY-PREFLIGHT-2026-09-26.md`.

## Objective

Prove one bounded, repeatable CSV-to-canonical-candidate-to-validated-operational-snapshot/provider path for an out-of-Gold Vietnamese bank using the same reusable analysis contract as the Gold SQLite adapter. CTG 2024 Q4 is the candidate case, not assumed accepted data. First verify the raw filing and every observation's source trail. If evidence, scope, formula, or review gates do not pass, fail closed and report the exact blocker; do not promote a candidate or claim transferability has passed.

## Scope

- Audit the existing CTG packet, source manifest, reconciliation ledger, raw-file availability/hash using an explicit evidence root, exact source locators, period basis, reporting scope, metric definitions, missing cells, and existing derivation lineage.
- Implement or repair only the generic data-side path needed for candidate validation, accepted operational snapshot promotion, deterministic derived-value recomputation with versioned formula and calculation receipt, and provider access.
- Keep accepted operational data distinct from immutable Gold v5 and mutable analysis-run history. Never treat the worktree initializer's `finance_master_v2.sqlite` snapshot as Gold v5 evidence.
- Demonstrate the supported adapters against the same analysis contract. Do not hard-code CTG, a fixed bank universe, a bank-specific calculation, or a physical SQLite schema into the reusable analysis core.
- Preserve `missing != 0`; distinguish structural candidate, source-reconciled candidate, reviewed operational snapshot, and Gold benchmark promotion.
- Treat PDF text/table/chart/OCR/parser output as candidate evidence only. Do not infer chart meaning from OCR text alone. If `LLAMA_CLOUD_API_KEY` is already configured, the user has authorized a small representative pilot (a few pages covering text/table and chart); compare every extracted value with the original page and record its locator. Do not print or commit the key, process the full 69-page filing, or treat parser output as accepted evidence. If the key is unavailable, proceed with the manually reconciled CSV path.
- If a change to canonical contracts or `contracts/schema.sql` is necessary, stop and report the proposed change to the Lead Architect before implementing it.

## Out of scope

Frontend/API work, changing Gold v5 or its authority evidence, expanding the evaluation sample, asserting industry-wide statistical representativeness, enabling unrestricted PDF/OCR ingestion, or claiming all new-bank files work without normalization and review.

## Acceptance criteria

1. The raw filing hash and evidence-root verification are recorded, or the failure to resolve them is explicitly documented and no observation is promoted.
2. Every accepted direct observation resolves to an accepted source and metric-specific exact locator, period basis, reporting scope, units, and review record.
3. Derived observations are recomputed from accepted source-backed inputs using a recognized versioned deterministic formula; a receipt records ordered input IDs, outputs, tolerance, and result.
4. Missingness, invalid scope, unsupported mapping, absent evidence, bad formulas, and hash mismatches fail closed with actionable validation output.
5. Gold SQLite and the validated operational CSV/onboarding path exercise the same reusable analytical contract/provider boundary; no hard-coded issuer count is required.
6. Gold v5 and `analysis_runs` remain unmodified and physically separate from the operational snapshot. Worktree SQLite remains isolated.
7. Focused tests plus required data, OpenAPI/architecture boundary and full checkout-available checks pass; ignored evidence is verified only with an explicit evidence root.
8. The PR reports exact evidence, snapshot identity/status, tests, limitations, whether transferability was demonstrated, and does not call candidate-only or offline/mock behavior live validation.

## Required handoff

Report base SHA, branch, commit SHA, PR, changed files, tests, known failures, evidence-root used (without secret values), snapshot IDs/hashes, and working-tree status. Do not request review until remote CI passes and the independent audit is complete.

## Local verification outcome

- Evidence-root invocation: `--evidence-root <worktree-root>`; source file path is relative to that root.
- CTG original filing: `data/raw/bank-onboarding-v1/ctg-2024-consolidated-audited.pdf`, 5,651,992 bytes, SHA-256 `36513dd8b060712b188f9eab03b1a7f9479ab21e63866dd95e45759d03ec5369`. The value matches the packet and source manifest. Manual page/table reconciliation is recorded in the P1 preflight; no chart value was accepted.
- The packet/register gate reconciles 22 unique observations (15 reported inputs and 7 derived values); none are missing. LlamaParse key presence was false, so no parser/OCR run occurred.
- A distinct accepted operational snapshot was written to ignored `data/processed/onboarding/ctg-2024q4-operational-p1.sqlite`: dataset `bank-onboarding-ctg-2024q4`, snapshot `snapshot-b86db41dd976731cf3cf8c457c0874f8bea95798d9c42b3e3ff953efc8a58aaa`, local file SHA-256 `81be2e1f7be707f3b1df3f45f780fdf0dbc0ee11ac925f23bf0e332ded2429ea`. Its accepted status is operational only; Gold benchmark promotion remains separate.
- Generic primary-source promotion now requires an opaque receipt from the explicit evidence-root resolver. The resolver reads bytes itself and binds the computed SHA-256 to the source identity/type/tier; canonical promotion rejects missing or mismatched receipts, unsupported source types, malformed hashes, and document/source hash mismatches. Regression coverage includes a forged 64-hex hash without a receipt, resolver byte mismatch, and document/source hash mismatch.
- Seven derived CTG observations were recalculated from ordered accepted inputs using versioned formulas; persisted receipts verify outputs, tolerance, and result. `run_metric_probe` tests use the shared provider-neutral request contract with both the operational canonical provider and a Gold SQLite test adapter fixture. This does not verify an installed Gold v5 artifact or establish broad bank-sector representativeness.
- The isolated worktree initializer `data/processed/finance_master_v2.sqlite` remains at SHA-256 `00c05ae4cd4a95b05e2ad35c86183aaa9e7e8db63d4bdc9a19854c239fbea994`; it is not Gold evidence. Post-suite, the actual Gold v5 artifact at `data/processed/gold-bank-2025-expanded-v5-evidence.sqlite` still matches pinned SHA-256 `1b1b5c090d2f8ede87a4c33ea3ee716f7a54c9de7c51089f4d3893d7a1ffce73`; the explicit-root P4 verifier passed and reported SQLite integrity `ok`. The operational snapshot does not alias Gold by path or filesystem identity. `data/processed/analysis_runs.sqlite` was absent, `ANALYSIS_RUNS_DB_PATH` was not configured, and the snapshot does not alias the configured/default run-history path. Neither store was used as a target.
- Validation passed: focused onboarding/provider tests (53), OpenAPI contract, architecture guardrails, compileall, and full unittest discovery (663 tests, 4 skipped). The suite emitted its expected persistence-failure and DB-connectivity-probe diagnostics; the test process exited successfully. `git diff --check` passed. `scripts/verify_p4_evaluation_inputs.py --evidence-root <project-root>` passed against the explicitly supplied evidence root.
- Transferability is demonstrated only for the exact reviewed CTG 2024 Q4 snapshot and covered metrics. No live provider or final evaluation result is claimed. Remote CI and independent audit are pending.
- Base SHA: `b87649af2c32f4499dcd6ebe82ae62799c9d5b1f`.
- Branch: `codex/p1-validated-bank-onboarding-20260926`.
- Implementation commit SHA: `8d31901dcfa83e6a2514a062f1d9cf6f72d4f83d`.
- PR: [#56 — feat(data): validated bank onboarding path](https://github.com/thaicuong576/final-thesis/pull/56), opened as draft. Initial remote checks passed; they will rerun after this handoff update.
- Changed files: `.agent/memory/lessons-learned.md`, `TASK.md`, `docs/P1-DATA-PORTABILITY-PREFLIGHT-2026-09-26.md`, `src/thesis_data/bank_onboarding.py`, `src/thesis_data/canonical_snapshot.py`, `src/thesis_data/operational_onboarding.py`, `src/thesis_data/source_artifacts.py`, `tests/test_acceptance_resolver_boundary.py`, `tests/test_bank_onboarding_packet.py`, `tests/test_phase0b_csv_onboarding.py`, and `tests/test_phase0c_evidence_transferability.py`.
- Tests: 53 focused onboarding/provider tests; full unittest discovery (663 tests, 4 skipped); OpenAPI, architecture guardrails, compileall, explicit-root P4 verifier, and `git diff --check` all passed.
- Known failures: none. The suite's persistence-failure and DB-connectivity probes emitted their expected diagnostic messages and exited successfully.
- Working tree: clean after the final handoff commit; ignored source evidence and operational SQLite artifacts are not tracked.
