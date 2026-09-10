# Phase 1–2 implementation handoff

## Scope

This repository snapshot contains the approved Phase 1–2 acceptance-contract
implementation. It does not start a provider call, critic loop, targeted
revision loop, Macro Gold build, UI change, or benchmark rerun.

## Code under review

- `src/thesis_data/schema.py`
  - structured assertion and generalized scope contracts;
  - acceptance-round and report-acceptance state schemas;
  - auditable limitation reason codes and hard-gate policy objects.
- `src/thesis_data/acceptance.py`
  - deterministic Stage-1 validation against the read-only Gold SQLite;
  - typed evidence/provenance checks;
  - legacy composite-claim compatibility adapters;
  - quality scoring and bounded acceptance-state helpers.
- `tests/test_acceptance.py`
  - contract, validator, adapter, and acceptance-state regression tests.

## Verification recorded for this snapshot

- Focused acceptance tests: `16` passed.
- Full suite: `python -m unittest discover -s tests -q` → `345` passed.
- Read-only Gold integration check: one valid observation/evidence case passed
  all six Stage-1 hard gates.
- The full test suite does not require provider credentials.

## Explicit non-scope

The current snapshot intentionally does not claim that semantic evidence
entailment, critic-driven revision, provider orchestration, Macro Gold, or a
new benchmark has been implemented. Historical benchmark artifacts remain
unchanged and local data/evidence stores are excluded from Git.

## Reproduction note

The ignored local data stores must remain available at their existing project
paths for the Gold integration check. They are not included in this source
handoff because they contain large/raw evidence artifacts.

## Second-commit contract hardening

The follow-up acceptance fix keeps the same scope and adds deterministic
evaluation semantics: empty claim sets fail with `empty_claim_set`; hard-gate
rates persist their evaluation unit plus passed/evaluated counts; one failed
assertion is counted once even when it has multiple diagnostics; and the MVP
peer median uses the versioned `peer_median_benchmark_id(...)` identity bound to
the sole Gold snapshot, peer set, period, and metric. Limited acceptance only
permits unresolved `MISSING_EVIDENCE` issues, while persisted quality totals,
round thresholds, and accepted payload versions are revalidated at the report
state boundary.
