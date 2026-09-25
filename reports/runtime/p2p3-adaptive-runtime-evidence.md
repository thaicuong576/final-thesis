# P2/P3 adaptive runtime evidence

**Status:** single-period provider-backed peer and company analysis now runs through the frozen-plan and bounded-revision path. Multi-period evaluation tasks remain ineligible.

## Runtime behavior

- The API resolves the request against the accepted snapshot catalog, validates required capabilities, and freezes a typed `AnalysisPlan` before provider retrieval. Company-only plans invoke only Company; peer plans invoke Company and Sector. Unsupported macro requests fail before specialists run.
- Numeric claims retain explicit observation IDs and source-locator lineage. Stage-1 runs before semantic critique and checks plan coverage, provenance, numeric values, peer identity, missingness, and scope.
- Peer medians are obtained only from `get_peer_benchmark`; the API does not calculate or repair aggregates. It requires exact provider metadata for ordered requested and eligible peer IDs, versioned aggregation, both denominators, and every missing-member reason. The five-requested/four-eligible case passes Stage-1 only with the corrected core distinction.
- Peer claims require non-empty, provider-declared, consistent reporting scope, unit, and period basis across the target, accepted peer inputs, and benchmark. The API never infers scope. Gold scope authority is consumed only when an explicit `GOLD_SCOPE_AUTHORITY_PATH` is configured; the sidecar load pins canonical SHA-256 `fef07af9f3deea7afbaa60ad51c8db740388e88b64bcf843d8ab5ec8f0ad777f`.
- Production semantic review uses the configured OpenAI-compatible provider. If it is not configured, the request blocks before specialist retrieval. Tests inject explicit offline critics; they do not claim live provider validation.
- Open issues can trigger at most two targeted re-queries of only the selected specialist work, followed by re-synthesis and Stage-1 again. Unresolved critical issues fail acceptance. Run and SSE events report workflow transitions without detailed private reasoning.

## Peer response extension

The runtime places these fields on `sector_benchmark` (the Pydantic response allows extension fields): `peer_universe_id`, ordered `requested_peer_entity_ids`, ordered `eligible_peer_entity_ids`, `aggregation_method`, `requested_denominator`, `eligible_denominator`, and `missing_members` with `entity_id`, `observation_id`, `validation_status`, and `reason`. Numeric peer claims carry exact eligible observation IDs in `input_observation_ids` and `peer_median_v1` in `formula_version`. `contracts/openapi.json` has not yet declared these peer metadata fields; contract synchronization is assigned to root integration.

## Multi-period boundary

The API rejects expanded quarter ranges and compact forms such as `2024_Q1–Q4` before provider retrieval with `multi_period_unsupported`. The public request currently represents `period` as one string, with no multi-period request or plan shape. Evaluation tasks T04/T05 require per-quarter context, and T08 requires per-period peer denominators; all three remain ineligible until a contract-first multi-period path is implemented. This vertical slice does not claim P2/P4 evaluation completion.

## Verification

- `test_api_analyze.py`: 19 passed, including provider-backed peer median with five requested/four eligible, explicit metadata fail-closed behavior, scope/basis gates, targeted revision, bounded failure, and multi-period rejection.
- `test_api_stream.py`: 5 passed, including real revision event order and no detailed review text in events.
- `test_analysis_runs_api.py`: 6 passed.
- Stage-1/core focused suites: `test_acceptance.py` 25 passed; `test_acceptance_provider_boundary.py` 31 passed; `test_acceptance_resolver_boundary.py` 6 passed; `test_gold_scope_authority.py` 5 passed.
- P4 verifier: passed against the explicit root evidence directory. Gold integrity was `ok`; 80 cells checked (76 valid, 4 missing), 16 peer probes reproduced, all 17 source artifacts matched. Frozen control hashes: questions `c4747af992441cc6063fa9dc08b1a09fc1a4a923a5415a2de4391c03e17fbc09`, task specs `9744a06ceb2c703c2cfb1b15c45b0d7cee8fcf2fa9a1234c5b9c9fd9c8e4e50c`, expected coverage `21e29be555a75e7d774deb3e0f2ed7f87666b5f32b8d7592670b2d703e192252`, and reporting-scope authority `fef07af9f3deea7afbaa60ad51c8db740388e88b64bcf843d8ab5ec8f0ad777f`. The verifier reports `scoring_eligible_now=false` and `final_protocol_freeze_ready=false`.
- `test_p4_evaluation_verifier.py`: 5 passed, including LF/CRLF checkout equivalence.
- `python scripts/check_architecture_guardrails.py`: passed.
- Full Python suite after integrating the cross-platform hash correction: 608 tests passed, 4 skipped.
- Root `data/processed/finance_master_v2.sqlite` SHA-256 after verification: `7993005474B8E0C3F91261B0E39AC140B43AC98BD0A167E0C8EBC274E4834A86` (unchanged).
