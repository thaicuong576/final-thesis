# P1 Truth and Provenance Integration Verification

**Date:** 2026-09-25

**Base:** `3e50b958eb39f589eb043af227bdd5d5fba6b73c`

**Integration branch:** `codex/integration-p1-truth-v2-20260925`

**Status:** verified and ready for review; not merged or deployed.

## Integrated change set

| Source PR | Verified head | Scope |
|---|---|---|
| #50 | `35c3be588c501528b07a884018ee18db2c99ea91` | Independent SQLite worktree snapshots |
| #45 | `5376c724633523297053dbf60157545948907e85` | Bank onboarding contract and scoped VPB D-072 authority |
| #47 | `86d484b15f002b8cefdc954a9dc3c988bb7950a5` | CTG onboarding and D-071 calculation receipts |
| #49 | `b4b40fe58471fb107683d2a94ce756b1be035b51` | Stage-1 numeric provenance and first-class locator |
| #48 | `98868461740282a1f079bd55ab78da560cf7c9b6` | Provider-backed API truth gates |
| #46 | `d00a92109b6c5bedf5a06422bbceb9f36b2bc69e` | Teacher-facing UI truth and capability states |
| #44 | `f9fc3fed86dfdbc44b20c840115d98ee4bccadf6` | Six-day plan, chapter guide, and five-bank evaluation protocol |

The integration resolution keeps one `CanonicalObservation.source_locator`,
the D-071 `calculation_receipt`, fail-closed Stage-1 lineage, exact
observation-to-evidence filtering, SQLite worktree isolation, the Luna/xhigh
subagent rule, and the complete five-bank thesis plan.

## Verification results

- Python full suite on the isolated child database: **586 tests passed, 4
  skipped**.
- Frontend: lint passed; Vitest **53 tests passed**; TypeScript build passed;
  production build passed. The build reports a non-blocking chunk-size warning
  above 500 KB.
- Final VPB authority delta: **16 focused tests passed**, architecture guard
  passed, and the authority verifier passed with an explicit evidence root.
- Gold v5 SHA-256:
  `1B1B5C090D2F8EDE87A4C33EA3EE716F7A54C9DE7C51089F4D3893D7A1FFCE73`.
- Root runtime database SHA-256 before and after verification:
  `7993005474B8E0C3F91261B0E39AC140B43AC98BD0A167E0C8EBC274E4834A86`.

## Runtime acceptance probes

### Gold ACB

- Terminal report status: `partial`, matching a company-only plan whose
  macro/sector/critique capabilities were not requested or run.
- Stage-1: accepted.
- Numeric claims retained the accepted observation, primary source hash, and
  metric-specific locator. Generic snippets were not fanned out as numeric
  evidence.

### CTG portability case

- Packet: valid and materialized into an accepted temporary canonical snapshot.
- Terminal report status: `partial`; Stage-1 accepted.
- ROE: `18.6012%`, formula `roe-ttm-v1`, four input observation IDs, and six
  primary statement locators under official report SHA-256
  `36513DD8B060712B188F9EAB03B1A7F9479AB21E63866DD95E45759D03EC5369`.

## VPB D-072 decision

The five-issuer Gold v5 ROE scope is open after a distinct reviewer accepted
the exact reviewed head and the authority bound that attestation. The final
authority graph byte-pins only VPB-scoped controls and immutable evidence;
living repository policy files are checked by semantic markers.

- Attestation canonical SHA-256:
  `FC1D17BDBBAE9877F482875E730766D049CA5151D32173857D9EDEF2F31E7BAB`.
- Authority canonical SHA-256:
  `9BC7BDD2EAACA8BFF723B50C547A48B65A7F12B2F81B23303D2B285F1C19C33E`.
- Comparative gate: eligible, no blockers, 80 cells checked, 76 valid, 4
  missing.
- VPB Q4 parent-equity ROE: `11.4117471457821869%`; total-equity diagnostic
  alternative: `10.9929645262513979%`.

## Remaining gates

1. Merge requires explicit repository-owner approval.
2. The evaluation protocol remains pre-freeze until the five-bank peer path and
   real critique/revision path pass the same end-to-end runtime gate.
3. Preview deployment requires a read-only dataset database separated from the
   `analysis_runs` database, startup hash/integrity/snapshot checks, and explicit
   deployment approval.
4. The root runtime database contains five test-run rows from the pre-isolation
   incident. No destructive cleanup was performed because no exact pre-incident
   byte copy was found.
