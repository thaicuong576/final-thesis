# Run artifact directory

These directories contain reproducibility-harness outputs only. They are not
financial analysis and must not be aggregated as thesis experiment results.

- `offline-fixture-v9/` is the current harness artifact. It exercises metric,
  source, and evidence-ID provenance across all three arms, includes the
  deterministic anomaly-trigger field, binds the question-set SHA-256, and
  records unavailable provider telemetry as explicit nulls. It also verifies
  request-level prompt-version propagation, manifest-level prompt-version
  consistency, and the persisted-plan/full-batch preflight boundary.
- `offline-fixture-v7/` is retained as the prior prompt-contract harness
  artifact.
- `offline-fixture-v3/` is retained as the prior harness artifact from the
  macro-evidence routing fix.
- `offline-fixture-v1/` through `offline-fixture-v8/` are earlier
  non-comparative plumbing runs retained for history; use v9 for current checks.

Provider-backed runs require a promoted gold snapshot and a green readiness
gate. They do not belong in this directory until those conditions are met.

`baseline-plan-core-v1.json` is the non-executing 39-job bank-core plan.
`baseline-plan-pilot-v1.json` is the non-executing 42-job full draft that keeps
the macro-to-bank extension. Both plans use `PENDING_GOLD_SNAPSHOT` and are not
comparative results.
