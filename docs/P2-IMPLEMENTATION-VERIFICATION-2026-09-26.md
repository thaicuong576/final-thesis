# P2 Runtime and Stage-1 Verification — 2026-09-26

## Result

The checked-out API implementation meets the supported P2 runtime acceptance
cases through explicit offline provider, writer, and critic fixtures. No
application-code gap was demonstrated in this worktree, so this change records
verification rather than changing runtime behavior. These fixtures establish
implementation behavior only; they do not establish live provider readiness,
live-model quality, deployment readiness, or a scored A/B/C result.

Base commit: `1a995ae157e552f9582de87d0b096ff0721b2697`
Work branch: `feat/p2-adaptive-hard-gates-20260926`

## P2 runtime probe matrix

This compact matrix records the exact existing API probes used for P2. It is a
runtime acceptance record, not the final A/B/C evaluation question-set freeze.
No question, prompt, run configuration, or plan artifact was changed.

| Probe | Exact existing request | Expected plan and verified behavior |
|---|---|---|
| Company-only | `Phân tích ROE và NPL của ACB quý 4 năm 2024`; target `ACB`; period `2024_Q4`. Companion stream/sync probe: `Analyze ROE and NPL of ACB in 2024 Q4`; target `ACB`; period `2024_Q4`. | The plan declares only `company`; the report has no Sector benchmark or Macro context; structured claims resolve through the accepted provider's observations, sources, and locators. Covered by `tests/test_api_analyze.py::test_company_claims_are_provider_backed_and_both_stages_accepted` and `tests/test_api_stream.py::test_company_stream_contains_only_actions_that_ran`. |
| Single-period Peer and multi-level synthesis | `Compare ROE of TCB with the five bank peer universe in 2024 Q1`; target `TCB`; period `2024_Q1`; peers `ACB`, `BID`, `CTG`, `MBB`, `VCB` | The plan activates `company` and `sector`; the provider supplies the benchmark. The report preserves five requested members, four eligible inputs, ACB's accepted missingness reason, the eligible observation IDs, and claim-level evidence lineage. Covered by `test_peer_run_uses_provider_median_and_preserves_missing_member_denominator` and `test_peer_metrics_keep_distinct_membership_records`. This request exercises Company-to-Peer synthesis in one supported period. |
| Requested Macro plus Company when Macro is unavailable | `SBV policy rate effect on ACB in 2024 Q4`; target `ACB`; period `2024_Q4` | The configured Gold sample declares no accepted Macro observations. The request returns an error with no numeric claims or evidence trail. Macro plus Company is therefore `NOT_APPLICABLE` for this snapshot. The Macro-only positive control uses a separate declared test provider; it does not prove Macro-plus-Company support in Gold. Covered by `test_unsupported_year_metric_and_capability_requests_fail_closed` and `test_macro_writer_runs_only_for_a_provider_declared_macro_metric`. |
| Multi-period Peer boundary (T08) | The exact range variants in `test_multiperiod_comparison_is_explicitly_rejected_before_retrieval` | The request is blocked during planning and the provider's metric retrieval is not called. Multi-period Peer/Macro remains unsupported under D-074. |

## Planning, snapshot identity, and adapter boundary

`_plan_request` in `src/thesis_api/adaptive_runtime.py` resolves entities,
metrics, periods, peer universe, and declared provider operations, then builds
the provider-bound `AnalysisPlan`. `execute` completes that planning and
capability validation before the first observation retrieval. Company-only
dispatch, Company/Sector Peer dispatch, and conditional Macro dispatch follow
the resulting plan.

The API runtime uses an operationally frozen plan identity. Specialist and
synthesis writers receive a serialized `plan.model_dump(...)`, not the
planner's live object. Stage-1 and the semantic critic receive deep copies.
The revision controller deep-copies the plan into workflow state, binds the
candidate identity, and separately fingerprints the full serialized plan.
`candidate_hash()` covers selected fields—plan version, dataset and snapshot
IDs, query ID, ordered periods, claims, and optional synthesis summary and
supporting claim IDs; it does not hash the full plan. `_plan_payload_hash()`
hashes the complete JSON serialization of the plan and is stored separately in
workflow state. Finalization recomputes that full-plan fingerprint and raises
`analysis_plan_mutated` if it changed. The final report is rendered from the
same request plan after the guarded workflow returns.

The reusable `AnalysisPlan` Pydantic class currently does not set
`frozen=True`; direct callers of the core can mutate a local instance. The API
route prevents adapter-driven drift through the boundaries above and the
workflow fingerprint check. A type-level immutability change belongs to the
reusable-core owner and is not needed to repair a demonstrated API acceptance
failure here.

The API preserves the accepted dataset snapshot ID in the plan and report,
ordered periods in Company trend scope, and structured observation/source/
locator/input lineage in numeric claims. Company-only data with unknown
reporting scope is reported with an explicit limitation and is not promoted to
a Peer/cross-bank comparison; Peer aggregation fails closed when shared
verified scope or period basis is unavailable.

## Stage-1 gates

The reusable provider-backed acceptance path checks numeric values, typed
references, accepted source/locator lineage, claim scope, expected Company
metric-period cells, peer input identity and denominators, and empty output
before semantic review. Existing checked-in tests cover numeric mismatch,
unresolvable references, out-of-scope claims, empty claims, unlinked evidence,
missing locators, invalid peer scope, and accepted missingness. Missing
observations cannot satisfy a numeric `observation` reference; a missing-cell
claim requires a provider-resolved missing observation with a null value and
reason. The API test below constructs the accepted ACB `DATA_UNAVAILABLE`
observation and a numeric zero claim against its observation reference; Stage-1
fails closed and retains `observation_reference_unaccepted:obs-ACB-roe-q1` in
both reference-validity and numeric-accuracy diagnostics.

Representative existing checks:

- `tests/test_acceptance.py::test_numeric_mismatch_fails_without_prose_parsing`
- `tests/test_acceptance.py::test_invalid_reference_fails_reference_and_unaccepted_gates`
- `tests/test_acceptance.py::test_claim_scope_is_generalized_and_validated_against_workload_scope`
- `tests/test_acceptance.py::test_empty_claim_set_fails_with_machine_readable_violation`
- `tests/test_acceptance_provider_boundary.py::test_explicit_missingness_uses_resolved_missing_state`
- `tests/test_acceptance_provider_boundary.py::test_valid_observation_cannot_satisfy_missing_cell_reference`
- `tests/test_api_analyze.py::test_stage1_rejects_numeric_zero_claim_for_accepted_missing_observation`
- `tests/test_acceptance_provider_boundary.py::test_direct_observation_route_requires_exact_locator`
- `tests/test_acceptance_provider_boundary.py::test_unlinked_same_source_snippet_cannot_support_numeric_claim`
- `tests/test_api_analyze.py::test_missing_metric_locator_fails_closed_even_when_source_snippets_exist`
- `tests/test_api_analyze.py::test_unsupported_year_metric_and_capability_requests_fail_closed`
- `tests/test_api_analyze.py::test_peer_run_fails_closed_without_scope_or_period_basis`

## Experiment-input boundary

The final A/B/C task and configuration gate remains separate from P2 runtime
conformance. The question and plan files were not edited. A read-only check of
the two checked-in complexity plans found both ineligible against the current
question-set bytes:

| Artifact | Hash in plan | Current question-set SHA-256 | Audit result |
|---|---|---|---|
| `experiments/runs/complexity-plan-gold-v1.json` | `c7700c714315c890bab54997eca6aa1c78406ca5539c2a6d46d6d78ad7f2f3fb` | `79d2ffd7eabf7ed85df8ce527e74b58a0afb9b8f19ff9528fb75f00242babf81` | `eligible=false`; blockers `plan_question_set_hash_mismatch`, `job_question_set_hash_mismatch` |
| `experiments/runs/complexity-plan-parallel-v1.json` | `c7700c714315c890bab54997eca6aa1c78406ca5539c2a6d46d6d78ad7f2f3fb` | `79d2ffd7eabf7ed85df8ce527e74b58a0afb9b8f19ff9528fb75f00242babf81` | `eligible=false`; blockers `plan_question_set_hash_mismatch`, `job_question_set_hash_mismatch` |

Keep both plans ineligible for P4 scoring until a separately reviewed repair
rebinds and audits the exact question/config artifacts. Their multi-period
peer workloads are also outside the public API scope established by D-074.
This verification does not score any run and does not claim that an A/B/C
question set is frozen.

## Architectural pre-flight

| Guardrail | P2 verification result |
|---|---|
| Gold coupling | No new Gold dependency; the API consumes a provider binding. |
| Physical SQLite coupling in core | No increase; acceptance resolves through the provider interface. |
| Bank-universe hardcoding | No runtime change or new fixed issuer list. Fixture tickers are test data. |
| Frontend replacement | No frontend changes; the checked OpenAPI contract passes. |
| Storage replacement | Planning and acceptance use provider-declared entities, periods, metrics, and operations. |
| Layer ownership | Request orchestration remains in API integration; generic acceptance remains in `thesis_data`. |
| Provenance | Numeric claim observation, source, locator, formula/input lineage, and evidence joins remain explicit. |
| Snapshot and period identity | Snapshot ID and ordered period scope are carried by the plan and accepted candidate. |
| Analyst capability limits | Unsupported Macro, Peer, and period scope produces explicit errors/limitations. |
| P2 scope | No OCR, new Macro data, UI work, live scoring, or deployment secrets were used. |

## Verification

All commands ran from the assigned worktree with `PYTHONPATH=src` where
required:

| Command | Result |
|---|---|
| `python -m unittest discover -s tests -p 'test_api_*.py' -q` | PASS — 47 tests |
| `python -m unittest discover -s tests -p 'test_acceptance*.py' -q` | PASS — 68 tests |
| `python -m unittest discover -s tests -p 'test_complexity_*.py' -q` | PASS — 12 tests |
| `python -m unittest discover -s tests -p 'test_experiment_contract.py' -q` | PASS — 10 tests |
| `python -m unittest discover -s tests -q` | PASS — 664 tests, 4 skipped |
| `python scripts/check_openapi_contract.py` | PASS — `OPENAPI_CONTRACT: PASS` |
| `python scripts/check_architecture_guardrails.py` | PASS — `ARCHITECTURE_GUARDRAILS: PASS` |
| `python -m compileall -q src` | PASS |
| `git diff --check` | PASS after excluding the dispatcher-provided local `TASK.md` manifest from the PR |

The full suite emitted its expected persistence-failure and database
connectivity-probe diagnostics; the process exited successfully. No live API,
external provider, secret, or ignored source evidence was accessed.
