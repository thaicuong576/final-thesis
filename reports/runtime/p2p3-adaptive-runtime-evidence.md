# P2/P3 adaptive runtime evidence

**Status:** implementation in progress; peer Stage-1 integration awaits the
contract-first requested-versus-eligible peer-scope correction.

## Implemented runtime behavior

- `/api/analyze` freezes a typed `AnalysisPlan` after request/catalog validation,
  then dispatches only the capabilities required by that plan.
- Company facts come from accepted provider observations and exact primary
  lineage. Peer benchmarks are obtained only through the provider's
  `get_peer_benchmark` operation; the API does not calculate a median.
- Peer execution requests the complete ordered peer set so provider metadata
  can disclose the requested denominator and excluded members. The runtime
  requires consistent, non-null provider-declared reporting scope, unit, and
  period basis for the target and accepted members, and verifies those fields
  on the provider aggregate before publishing a claim.
- A configured `GOLD_SCOPE_AUTHORITY_PATH` opts into the separately pinned
  reporting-scope sidecar. Loading uses the expected canonical SHA-256
  `fef07af9f3deea7afbaa60ad51c8db740388e88b64bcf843d8ab5ec8f0ad777f`; there is
  no sidecar auto-discovery. A configured but unverifiable authority blocks
  analysis. Without it, unavailable scope remains unavailable.
- Production semantic review uses the configured OpenAI-compatible provider.
  The tests inject explicit offline critics. Stage-1 must pass before the
  critic runs; open issues trigger at most two targeted specialist re-queries,
  re-synthesis, and another Stage-1 pass. An unresolved critical issue ends in
  `FAIL_ACCEPTANCE`.
- SSE events are emitted by actual runtime transitions. Detailed model
  reasoning is not included in events.

## Current peer acceptance blocker

The runtime requests the five frozen peers and receives a provider benchmark
whose accepted `input_observation_ids` contain the four valid members. The
current Stage-1 benchmark gate cannot express that distinction: it requires
`claim.scope.entities` to equal the entities on benchmark `data_refs`, then
asks the resolver for a benchmark using that same member set. A scope of four
therefore recomputes a different benchmark identity from the provider's
five-requested-member result; a scope of five fails the one-input-per-peer and
exact input-lineage checks when one member is missing. The route consequently
fails closed at `benchmark_reference_unresolved` on the current base even
though the provider supplies its median and missing-member records. The
contract-first core change must separately represent requested peers and
eligible input peers before the peer acceptance test can pass. This report
does not claim peer acceptance or P2 evaluation completion until that change
is integrated and verified.

## Multi-period boundary

The runtime rejects both expanded quarter ranges and compact forms such as
`2024_Q1–Q4` before specialist retrieval, with `multi_period_unsupported`.
`contracts/openapi.json` defines request `period` as one string (for example,
`2024` or `2024_Q4`) and has no multi-period request/plan shape. It also does
not yet declare typed sector metadata for peer universe, ordered requested
members, aggregation method, denominators, and missing-member records; the API
currently emits these through the response model's extension fields. The
contract owner should add those fields before clients rely on them. The pre-freeze
evaluation protocol requires exact per-quarter context for T04 and T05 and
per-period peer denominators for T08. Those tasks remain ineligible until the
public contract and runtime gain a contract-first multi-period representation.
No OpenAPI contract edits are included in this worker change.

## Verification recorded so far

- `python -m compileall -q src/thesis_api tests/test_api_analyze.py tests/test_api_stream.py` — passed.
- `python scripts/check_architecture_guardrails.py` — passed.
- `python -m unittest discover -s tests -p 'test_api_stream.py' -v` — 5 tests passed, including targeted revision event order and omission of injected review content.
- API analyze tests cover company-only execution, no-unused-specialist planning,
  compact and expanded multi-period rejection before retrieval, one injected
  issue followed by successful targeted revision, unrepairable critical issue
  failure after two revisions, fail-closed behavior without a semantic
  provider, explicit reporting-scope/period-basis failure, provenance joins,
  and peer denominator/missingness metadata. On the current base, 17 of 18
  analyze tests pass; the peer acceptance case reaches the documented Stage-1
  blocker above and awaits the core contract correction.
