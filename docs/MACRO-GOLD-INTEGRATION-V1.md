# Bounded Macro Gold Integration v1

Status: implemented; Phase 3 semantic scoring, critic, revision, provider,
new data acquisition, RAG/vector infrastructure, UI expansion, and final macro
experiment remain out of scope.

## Frozen scope

Only these cells are materialized for `2024_Q4`:

| Indicator | Runtime state | Value | Reason |
|---|---|---:|---|
| `macro.policy_rate` | `valid` | `4.5 percent_per_annum` | SBV refinancing rate, Decision 1123/QĐ-NHNN, effective `2023-06-19`, carried forward to `2024-12-31` |
| `macro.credit_growth` | `missing` | `NULL` | `DATA_UNAVAILABLE`; no qualifying primary SBV year-end observation |

The raw acquisition artifacts remain immutable. The corrected candidate,
evidence package, and adjudication record resolve the effective date from the
official record identity `19-06-2023` and Decision 1123/QĐ-NHNN dated
16/06/2023; stale `ngayApDung`/overview date representations are excluded
from date mapping. Each V2 row references the adjudication record through
`adjudication_ref`.

## Versioned contract and compatibility

`MacroObservationV2` is defined in `src/thesis_data/schema.py`. The existing
8-column `macro_observations` table remains legacy. New acceptance-aware rows
use `macro_observations_v2`, whose fields preserve indicator definition,
source series, frequency, observation/effective/as-of dates, period basis,
alignment, transformation, input IDs, adjudication reference, and independent
review-check IDs.

The new snapshot is:

`data/processed/gold-bank-2025-pilot-v1-adjudicated-v2-macro-v1.sqlite`

It is copied only from the expected parent
`gold-bank-2025-pilot-v1-adjudicated-v2`, whose snapshot metadata must contain
the frozen ACB/TCB/VPB pilot scope and `status=gold`. The materializer records
that parent identity, the Macro contract version, period, and indicator IDs in
`snapshot_metadata.config_json.macro_gold_lineage`; it refuses a different or
ambiguous parent and refuses to overwrite an existing Macro snapshot. Inherited
coverage summaries are rebound to the new snapshot ID and summary IDs.
The snapshot contains exactly two `macro_observations_v2` rows and two typed
`macro_evidence_snippets` rows for the policy-rate evidence.

## Runtime behavior

- `ClaimDataRef.ref_type="macro_observation"` resolves only against
  `macro_observations_v2`; it never searches the legacy table.
- A valid numeric macro claim is checked against the V2 value/unit/period and
  accepted primary source provenance by Stage 1.
- An accepted missing credit-growth row is queryable and is returned as
  explicit missingness with `DATA_UNAVAILABLE`; it cannot supply a numeric
  value.
- Macro evidence is ticker-less and is routed through
  `macro_evidence_snippets`, binding source, indicator, period, locator, quote,
  and date semantics.
- Experiment preflight accepts either an accepted valid macro row or an
  accepted `missing/DATA_UNAVAILABLE` row. Pending, fallback, conflicting,
  unreviewed, or legacy-only macro inputs remain blocked.
- Querying both frozen indicators returns Macro Agent state `partial`, with
  the policy-rate value and an explicit credit-growth limitation.
- A valid Macro source row is inserted only after the manifest and adjudication
  establish the exact official SBV identity, primary tier, valid status, local
  hash match, and independent policy review. Source tier/status are never
  manufactured by the materializer.
- The accepted missing credit-growth row has `frequency=NULL` because no
  source-native series exists, and carries two independent missingness review
  IDs. Valid rows require a non-null source frequency.

## Verification

Focused macro tests: `13/13` passed.

Full Python unittest suite:

```text
Ran 367 tests in 21.964s
OK
```

No Stage-2 scorer, semantic critic, targeted revision controller, provider
change, UI change, new data acquisition, or historical Gold snapshot mutation
was performed.
