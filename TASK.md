# Task Manifest: P1 truth and provenance composite v2

## Context

- Role: auditor integration proof, promoted by the Lead after all acceptance
  gates passed.
- Branch: `codex/integration-p1-truth-v2-20260925`.
- Base: latest `origin/main` at worktree creation.
- Linear: waived by the repository owner for the active thesis completion run.
- This branch is the verified integration candidate. It may be pushed and
  opened as one review PR; it must not be merged or deployed without the
  repository owner's explicit approval.

## Inputs

Merge the exact latest remote heads for PRs in this dependency order:

1. #50 `35c3be588c501528b07a884018ee18db2c99ea91`
2. #45 `5376c724633523297053dbf60157545948907e85` final scoped-authority head
3. #47 `86d484b15f002b8cefdc954a9dc3c988bb7950a5`
4. #49 `b4b40fe58471fb107683d2a94ce756b1be035b51`
5. #48 `98868461740282a1f079bd55ab78da560cf7c9b6`
6. #46 `d00a92109b6c5bedf5a06422bbceb9f36b2bc69e`
7. #44 `f9fc3fed86dfdbc44b20c840115d98ee4bccadf6` final five-bank thesis-plan head

Resolve conflicts by preserving every compatible contract, architecture,
incident-memory, data, API, UI, and thesis-plan change. In particular, dedupe
the first-class `CanonicalObservation.source_locator` field shared by #47/#49,
preserve #47 `calculation_receipt`, preserve #49 fail-closed Stage-1 locator
logic, preserve #48 exact observation-to-evidence filtering, preserve #44 Luna
xhigh subagent instruction, and preserve #50 SQLite isolation rule.

## Acceptance

1. Record exact merged SHAs and all conflict resolutions.
2. Verify Gold v5 SHA-256 remains
   `1B1B5C090D2F8EDE87A4C33EA3EE716F7A54C9DE7C51089F4D3893D7A1FFCE73`.
3. Run focused D-070/D-071/Stage-1/API truth tests first.
4. Run frontend lint, tests, type/build checks.
5. Run architecture guardrails and diff checks.
6. Run the full Python suite only against the isolated worktree or an explicit
   temporary database. Never use the root database path.
7. Exercise at least one Gold ACB company analysis and one CTG portability
   analysis, reporting terminal status and exact provenance failures/successes.
8. Record root database SHA before/after; expected unchanged:
   `7993005474B8E0C3F91261B0E39AC140B43AC98BD0A167E0C8EBC274E4834A86`.

## Handoff

Open one integration PR containing the exact verified composite and link the
source PRs as audit trails. Do not merge or deploy any PR without explicit
repository-owner approval.
