# Pre-Phase-4 acquisition reconciliation

Status: candidate package only. No observation or document in this package is
promoted to Gold by this acquisition step.

## Frozen macro candidates

### `macro.policy_rate`

The SBV Headless Delivery response identifies the specific rate as `Lãi suất
tái cấp vốn`, with a source-native value of `4,500%` and a reference to
Decision `1123/QĐ-NHNN` dated 16/06/2023. The frozen mapping is:

```text
value          = 4.5
effective_from = 2023-06-19
as_of_date     = 2024-12-31
alignment      = latest_effective_state_at_period_end_v1
```

This is registered as `review_required` in the new acquisition package. The
previous two independent review passes remain the source of the existing
adjudication, but this package does not silently promote a new snapshot row.

### `macro.credit_growth`

The NSO 2024 statistical summary reports, on PDF page 15 / printed page 14,
that at 31/12/2024 credit growth of the economy reached `15.1%` compared with
the end of 2023. This is the best newly acquired official year-end candidate,
but it remains `review_required` until the definition, source precision,
publication vintage and source locator are reconciled against the frozen
contract.

The values are not interchangeable:

| Candidate | Meaning | Decision |
|---|---|---|
| 7.38% | SBV observation at 17/09/2024 | Out of period |
| approximately 15% | SBV policy orientation/target | Not an observation |
| 15.08% | SBV-hosted research/commentary statement | Secondary lead only |
| 15.1% | NSO year-end statistical-summary statement | Official candidate; not yet accepted |

The package does not derive an exact value because the underlying year-end
stock pair has not yet been machine-mapped and accepted.

## Native-sector candidates

The NSO yearbook and banking-statistics catalogue were acquired as independent
aggregate-source candidates. A proposed `sector.system_credit_growth` record
is kept separate from the frozen macro record until the entity/domain mapping
is reviewed. A proposed `sector.system_credit_outstanding` record remains
`review_required` with a null value because the exact table/row mapping has not
yet been proven. No `sector.system_npl_ratio` value was found in this bounded
pass; the explicit candidate state is missing rather than a peer-derived
substitute.

The five-bank sample is not used as a sector observation.

## Route failures

The source manifest preserves HTTP 403/WAF failures for direct SBV routes and
an HTTP 502 failure for the Công báo PDF CDN route. Alternate official
representations were used where available. No authentication, CAPTCHA,
paywall or access-control circumvention was attempted.
