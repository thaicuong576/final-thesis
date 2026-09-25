# P2/P3 adaptive runtime evidence

**Status:** single-period provider-backed analysis now runs through a frozen
plan, role-specific grounded writing, separate synthesis and bounded targeted
revision. Multi-period evaluation tasks remain ineligible.

## Runtime behavior

- The API resolves the request against the accepted snapshot catalog, validates required capabilities, and freezes a typed `AnalysisPlan` before provider retrieval. Company-only plans invoke only Company; peer plans invoke Company and Sector. Macro runs only when the provider declares an accepted compatible capability and observations; Gold v5 currently declares none.
- Numeric claims retain explicit observation IDs and source-locator lineage. Stage-1 runs before semantic critique and checks plan coverage, provenance, numeric values, peer identity, missingness, and scope.
- Peer medians are obtained only from `get_peer_benchmark`; the API does not calculate or repair aggregates. It requires exact provider metadata for ordered requested and eligible peer IDs, versioned aggregation, both denominators, and every missing-member reason. The five-requested/four-eligible case passes Stage-1 only with the corrected core distinction.
- Peer claims require non-empty, provider-declared, consistent reporting scope, unit, and period basis across the target, accepted peer inputs, and benchmark. The API never infers scope. Gold scope authority is consumed only when an explicit `GOLD_SCOPE_AUTHORITY_PATH` is configured; the sidecar load pins canonical SHA-256 `fef07af9f3deea7afbaa60ad51c8db740388e88b64bcf843d8ab5ec8f0ad777f`.
- Production analysis uses configured, role-specific Company/Sector/Macro writers for active roles and a separate Orchestrator synthesis call. Structured writer output is keyed by canonical claim ID and supporting claim IDs. It may revise qualitative prose but cannot mutate accepted numbers, identities, scope or provenance.
- Specialist prose and synthesis are fail-closed against new numeric assertions, including digits and English/Vietnamese number words, fractions and multipliers. Unsupported trend, causality, entity, metric and reference statements are rejected. These deterministic guards complement semantic critique; they do not prove prose quality.
- Production semantic review uses the configured OpenAI-compatible provider. If mandatory writer/critic configuration or the separate run store is unavailable, readiness and analysis fail before specialist retrieval. Tests inject explicit offline writers and critics; they do not claim live-provider validation.
- Open issues can trigger at most two targeted writer revisions of only the affected specialist or the Orchestrator synthesis, followed by re-synthesis and Stage-1 again. The issue and required action reach the target writer; a no-op targeted revision is rejected. Unaffected specialist output is preserved, unresolved critical issues fail acceptance, and SSE events expose workflow transitions without private reasoning.

## Typed synthesis and revision state

`AnalysisResponse.synthesis_summary` and ordered, unique
`synthesis_supporting_claim_ids` are one typed report artifact. The exact pair
is included in candidate hashing, semantic-round context, revision state,
persisted history and the public response. A synthesis-only correction sets
`revision_summary.synthesis_revised`; it does not relabel unchanged claims.
Final supporting IDs must equal valid final candidate claim IDs.

## Peer response extension

Each metric is represented by a `PeerBenchmarkRecord` under
`sector_benchmark.benchmarks`, with `peer_universe_id`, ordered requested and
eligible member IDs, aggregation method, both denominators, missing-member
reasons and exact eligible input observation IDs. Numeric peer claims carry
those same input IDs and `peer_median_v1` as `formula_version`. Shared top-level
metadata remains a compatibility view and is omitted when metric records differ.
`contracts/openapi.json` declares these additive fields and restores the
pre-existing malformed reference keys. Older saved reports may omit the new
metadata; new provider-backed peer reports must populate per-metric records.

## Immutable data and mutable run history

`SQLITE_DB_PATH` identifies accepted read-only analytical data.
`ANALYSIS_RUNS_DB_PATH` identifies a distinct writable operational database.
Startup rejects identical paths, descendants, hardlinks and symlink aliases;
readiness performs a real writeability check. Sync and SSE execution retain the
source dataset hash/schema while storing run history only in the operational
store. Persistence failure prevents success and `REPORT_READY`.

## Multi-period boundary

The API rejects expanded quarter ranges and compact forms such as `2024_Q1–Q4`
and `2024 Q1 through Q4` before provider retrieval with
`multi_period_unsupported`. The public request currently represents `period`
as one string, with no multi-period request or plan shape. Evaluation tasks
T04/T05 require per-quarter context, and T08 requires per-period peer
denominators; all three remain ineligible until a contract-first multi-period
path is implemented. This vertical slice does not claim P2/P4 evaluation
completion.

## Verification

- API analyze/SSE/history/writer focused suite: 41 passed, including role-specific writing, separate synthesis, feedback-responsive targeted revision, synthesis-only revision, immutable numeric assertions, written-quantity rejection, provider-backed peer median with five requested/four eligible, per-metric peer metadata, storage isolation, persistence failure, readiness and multi-period rejection.
- Core acceptance/revision focused suite at `0d82021`: 115 passed, including material target-by-target revision, stable claim IDs, exact changed-claim mappings, synthesis hashing and synthesis-only revision state.
- P4 verifier: passed against the explicit root evidence directory. Gold integrity was `ok`; 80 cells checked (76 valid, 4 missing), 16 peer probes reproduced, all 17 source artifacts matched. Frozen control hashes: questions `c4747af992441cc6063fa9dc08b1a09fc1a4a923a5415a2de4391c03e17fbc09`, task specs `9744a06ceb2c703c2cfb1b15c45b0d7cee8fcf2fa9a1234c5b9c9fd9c8e4e50c`, expected coverage `21e29be555a75e7d774deb3e0f2ed7f87666b5f32b8d7592670b2d703e192252`, and reporting-scope authority `fef07af9f3deea7afbaa60ad51c8db740388e88b64bcf843d8ab5ec8f0ad777f`. The verifier reports `scoring_eligible_now=false` and `final_protocol_freeze_ready=false`.
- `test_p4_evaluation_verifier.py`: 5 passed, including LF/CRLF checkout equivalence.
- `python scripts/check_architecture_guardrails.py`: passed.
- Full local Python suite with application head `7de4f4b` and the current root-owned contract edits: 635 passed, four skipped. Exact final-head CI is recorded on PR #53.
- Root `data/processed/finance_master_v2.sqlite` SHA-256 after verification: `7993005474B8E0C3F91261B0E39AC140B43AC98BD0A167E0C8EBC274E4834A86` (unchanged).
