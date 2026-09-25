# P2/P3 integration verification — 2026-09-25

Status: implementation verified for PR review. Final experiment and deployment
gates remain open, and merge still requires explicit user approval.

## Scope and lineage

- Base: `main@9e0298a3de01c31b01a412ec574f265eeb79d2ea` (merged PR #51).
- Integration branch: `codex/p2p3-runtime-20260925`, PR #53.
- Included data PR #52 at `9060004d92cf5ccfb50798488b90eefc6b3046c8`.
- No merge or deployment is authorized by this verification record.

## Architecture pre-flight

| Question | Assessment |
|---|---|
| Gold coupling | Scope sidecar validation stays in the Gold adapter; generic peer/core interfaces do not assume a five-bank universe. |
| Physical storage coupling | Gold remains immutable and provider access remains the boundary. Mutable run history uses a separate configured store, with same-file and filesystem-alias rejection. |
| Fixed issuer universe | Only the candidate evaluation manifest fixes five issuers; runtime scope comes from the catalog. |
| Replaceable frontend | API and canonical claims are independently testable. |
| Replaceable database | Peer calculation consumes provider observations; SQL is adapter-owned. |
| Core versus app | Acceptance/revision policy is reusable; HTTP, DTOs and configured transports are application adapters. |
| Provenance | Requested peer identity, eligible numeric inputs, locators and authority remain explicit. |
| Snapshot traceability | Exact dataset/snapshot/hash authority; no silent fallback. |
| Analyst value | Company/peer scope, truthful missingness and reviewable correction are the intended deliverables. |
| Scope restraint | No macro data promotion, unrestricted PDF ingestion or whole-sector generalization. Macro activation requires accepted provider-declared capability. |

## Verified data inputs

The P4 verifier reproduced 80 Gold cells (76 accepted, four missing), 16 peer
probes and 17 source hashes against an explicit local evidence root. The scope
sidecar has exactly 76 accepted entries and leaves missing observations intact.
Tracked controls verify identically with LF and CRLF checkouts. The ten-task
candidate set contains no A/B/C results and remains pre-freeze.

## Independent runtime findings and resolution

At head `3774046`, the local suite passed 608 tests with four skipped, but
independent review found material design defects. The alleged revision only
queried the same facts again; multi-metric peer metadata was overwritten by the
last metric; analytical data and mutable run history could share one SQLite
file; abbreviated period ranges were not all rejected; and readiness did not
prove mandatory model/run-store configuration.

The reviewed follow-ups replace those behaviors:

- `aa6c33e` binds typed synthesis text and its ordered supporting claim IDs to
  candidate hashes, semantic context, revision rounds and the final result.
- `0d82021` requires a material, issue-responsive revision for each targeted
  specialist and rejects unchanged targeted output.
- `553f810` wires role-specific Company/Sector/Macro writers, separate
  Orchestrator synthesis, per-metric peer records, fail-closed period parsing,
  readiness checks and isolated run-history persistence through the API.
- `7de4f4b` closes written-quantity bypasses for fractions and multipliers such
  as `half`, `twice` and `double` in specialist prose.
- `2db043d` makes readiness fixtures portable on Linux and supplies the explicit
  test model/run-store configuration required by the production contract.

Unchanged numeric assertions, identities and provenance stay immutable through
revision. An Orchestrator-only correction records `synthesis_revised` without
marking untouched specialist claims as revised. New runtime reports expose
`SectorBenchmark.benchmarks` per metric; legacy shared metadata is emitted only
when every record is identical. Dataset and run-store paths, including hardlink
and symlink aliases, are rejected when they resolve to the same file.

Root integration also repaired eleven empty OpenAPI reference keys and added
Python CI. CI verifies checkout-available contracts/tests, not ignored source
evidence or live model quality. Exact final-head results are recorded after the
root contract commit below.

## Remaining thesis gates

- Multi-period requests: T04/T05/T08 remain ineligible.
- Live-provider specialist/synthesis and critique behavior on the accepted snapshot.
- Fair A/B/C harness and exact-question validation before final freeze/scoring.
- Deployment provisioning, `/api/ready` and UI smoke tests against the immutable
  snapshot plus separate mutable run store.
- Final new-bank demo, human scoring and the approved six-chapter report.

## Verification boundary

Offline critics and writers are test doubles. Their passing tests establish
control flow, immutability, scope and failure behavior; they do not establish
live-model analytical quality. Macro execution remains conditional on an
accepted provider-declared capability, which Gold v5 does not provide. No
result in this PR is a final A/B/C thesis score.

The production API owns an explicit claim-to-specialist map and checks it in
targeted reruns. The framework-neutral core cannot independently prove that an
arbitrary injected executor placed a changed claim under the correct specialist:
`AtomicClaim` has no immutable producer/owner field, and plan requirements can
legitimately name several agents. Adding that field would require a coordinated
core, API and public-contract migration. This does not bypass the reference API
gate, but remains a portability limitation for future alternative executors.

## Local verification before final push

With application head `7de4f4b`, contract commit `067c22b` and Linux-fixture
follow-up `2db043d`, the full Python suite passed 635 tests with four skipped.
The focused API suite passed 41 tests; the combined API/thesis API fixture suite
passed 53. OpenAPI reference validation, architectural guardrails,
`compileall` and `git diff --check` passed. Storage regressions preserved the
accepted SQLite bytes and schema across two synchronous analyses and one SSE
run while three histories persisted and round-tripped in the separate run
store. The root Gold SQLite SHA-256 remained
`7993005474B8E0C3F91261B0E39AC140B43AC98BD0A167E0C8EBC274E4834A86`.

## Remote CI and independent verdict

Independent audit returned **GREEN** on exact reviewed head
`36693b0ace158a815eb2b793247f993bf572acf0`. GitHub Python contracts/tests run
`36169971894` passed on that head, and the PR was open and mergeable. Vercel
status contexts passed, while both deployment builds were intentionally
canceled by their configured ignored-build step; those contexts are not live
deployment evidence. The auditor accepted the documented generic-core ownership
limitation as non-blocking for the reference API path. No merge or deployment
was performed by this verification.
