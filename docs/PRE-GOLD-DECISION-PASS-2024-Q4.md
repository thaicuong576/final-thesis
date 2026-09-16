# Pre-Gold decision pass — 2024 Q4

This report records the bounded decision pass after the locked pre-Phase-4
acquisition. It is not a Gold promotion record.

## Decisions

| Area | Decision | Current status |
|---|---|---|
| `macro.credit_growth` | Use the NSO yearbook's direct official `15.1%` year-end value; it matches the frozen definition, `VN` scope, `2024_Q4`, and `annual_change_vs_end_2023`. | Candidate accepted at pre-Gold level; review required; not promoted |
| `15.08%` SBV-hosted article | Keep as rejected secondary research lead. | Excluded |
| Macro/Sector credit growth | Reuse one underlying aggregate fact; do not create a duplicate sector observation. | Sector alias only; not canonical |
| `sector.system_credit_outstanding` | Map the exact NSO `Outstanding / Prel. 2024` row to `15,617.1 VND_trillion` at `2024-12-31`. | Candidate mapped; review required; not promoted |
| `sector.system_npl_ratio` | No native official year-end source established. | `missing / DATA_UNAVAILABLE` |

## Evidence

The immutable source is the National Statistics Office of Vietnam's 2024
Statistical Yearbook:

- PDF page `263` / printed page `102` contains the credit-outstanding table;
- PDF page `222` contains the credit-outstanding definition;
- preliminary 2024 outstanding is `15,617.1` trillion VND;
- source-native growth is `15.1%`;
- the source artifact, URL and SHA-256 are recorded in the
  [machine-readable decision package](../data/reconciliation/pre-gold-decision-2024-q4-v1/decision.json).

The raw artifact is linked from the immutable
[pre-Phase-4 acquisition manifest](../data/manifests/pre-phase4-acquisition-v1.jsonl).

## Boundary

This pass changes only decision/reconciliation artifacts. It does not modify
the raw source package, Macro Gold code/schema/materializer, or existing Gold
snapshot. The repository is therefore ready for review of the semantic
decision, but a final valid Macro Gold row still requires the existing
independent review and fail-closed promotion process.
