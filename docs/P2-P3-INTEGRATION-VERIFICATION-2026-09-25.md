# P2/P3 integration verification — 2026-09-25

Status: under independent review; final experiment and deployment gates remain open.

## Scope and lineage

- Base: `main@9e0298a3de01c31b01a412ec574f265eeb79d2ea` (merged PR #51).
- Integration branch: `codex/p2p3-runtime-20260925`, PR #53.
- Included data PR #52 at `9060004d92cf5ccfb50798488b90eefc6b3046c8`.
- No merge or deployment is authorized by this verification record.

## Architecture pre-flight

| Question | Assessment |
|---|---|
| Gold coupling | Scope sidecar validation stays in the Gold adapter; generic peer/core interfaces do not assume a five-bank universe. |
| Physical storage coupling | No new analytical schema; Gold remains immutable and provider access remains the boundary. Deployment storage isolation is still pending. |
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

## Independent runtime findings

At head `3774046`, the local suite passed 608 tests with four skipped. Independent
review nevertheless found two blockers: the alleged revision only queried the
same facts again, and multi-metric peer metadata was overwritten by the last
metric. The contract now requires feedback-responsive writing and per-metric
benchmark records. These findings must be fixed and re-reviewed before merge.

Root integration also repaired eleven empty OpenAPI reference keys and added
Python CI. CI verifies checkout-available contracts/tests, not ignored source
evidence or live model quality. Subsequent verification results belong below.

## Remaining thesis gates

- Multi-period requests: T04/T05/T08 remain ineligible.
- Live model specialist/synthesis and critique behavior on the accepted snapshot.
- Fair A/B/C harness and exact-question validation before final freeze/scoring.
- Immutable deployed dataset separated from mutable run storage, readiness and UI smoke tests.
- Final new-bank demo, human scoring and the approved six-chapter report.

## Additional review gates

The reviewer also found shared dataset/run storage, incomplete rejection of
abbreviated multi-period ranges, and readiness that ignored required model
configuration. All are required fixes for #53. Live deployment provisioning
remains a later gate. Targeted revision acceptance includes role-specific model
writing, separate synthesis and preservation of unaffected specialist output.
