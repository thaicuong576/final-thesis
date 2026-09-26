# P4A Runtime Acceptance Evidence (2026-09-26)

## Identity

- **PR:** [#54](https://github.com/thaicuong576/final-thesis/pull/54)
- **Audited PR head:** `b094b603d83b3f129878656da9c3cbd021128c34`
- **Base:** `35fec43f7f8189614f585511c050ad2a9627d01f`
- **Squash merge:** `b1aeda4901a1cc2525a3d82409da24955bd0cecf`
- **Audit scope:** a separate internal, read-only subagent reviewed the exact PR head and returned GREEN. This is an internal code audit, not an external domain-expert review or a GitHub review approval.

## Acceptance evidence

- T04 and T05 use the canonical question text from `data/evaluation/p4-questions-v1.jsonl`; each offline API end-to-end case checks eight expected metric-period cells, Company-only dispatch, and claim/evidence joins.
- The plan-aware core Stage-1 gate checks the full `(entity, metric, period)` matrix. The T05 revision case changes only the targeted ROE claim prose, preserves factual and provenance fields, and revalidates all eight claims. An unresolved major issue fails within the bounded two-round controller.
- The actual `/api/analyze/stream` route reaches `REPORT_READY` only after the final run is persisted. The test fetches `/api/runs/{id}` and compares ordered periods, full serialized `atomic_claims`, full `evidence_trail`, cross-array claim IDs, and terminal state. A persistence failure emits `RUN_BLOCKED` without `REPORT_READY`.
- The implementation run reported **657 tests passed, 4 skipped**. OpenAPI, architecture guardrails, compileall, diff check, P4 and VPB verifiers passed. The accepted Gold v5 raw SQLite SHA-256 remained `1b1b5c090d2f8ede87a4c33ea3ee716f7a54c9de7c51089f4d3893d7a1ffce73`.
- PR CI passed the Python contracts/tests check. Vercel status checks were cancelled by ignored-build rules; they are not deployment smoke-test evidence.

## Limits

All new trend runtime cases use offline providers and critic/writer fixtures. They establish the tested implementation path, not live model quality, live-provider readiness, deployed analyst workflow, or final A/B/C scoring eligibility. T04/T05 remain unscored pending the live-readiness and experiment-freeze gates. Multi-period peer task T08 remains unsupported and requires a separate contract/runtime decision.
