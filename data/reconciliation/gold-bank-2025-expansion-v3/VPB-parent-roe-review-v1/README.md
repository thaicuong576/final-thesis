# VPB ROE adjudication and Gold v5 authority handoff

Status: the Q1-Q4 2024 parent-attributable ROE cells have two accepted checker
reviews and an accepted adjudication. A distinct independent confirmation of
the repository-bound authority record and comparative-gate result remains
pending, so D-072 keeps VPB ROE excluded from five-issuer peer tasks.

The prior local README and v1 packet manifest both said
`candidate_pending_fresh_review`, which contradicted the adjudicated review
ledger. Their superseded SHA-256 values are `5D85C74ABA6B41A97A2F2D1A2AFFE1E251D1B8E1E46B7D62AB842FAE02BF2496` (README)
and `24BF42B3D19B2EEE264BCBB03827585755096AA278795B95EB00EC825267A0B2`
(manifest v1). The original checker, adjudication and promotion ledgers remain
unchanged.

The current packet record is
[`VPB_parent_roe_manifest-v2.json`](VPB_parent_roe_manifest-v2.json) (SHA-256:
`1078E659064825A564F50226DF52BC3844F7713B02310FB79953BD2C736B8B26`). It binds the Q1-Q4 filing hashes and locators, the
adjudicated review and promotion-ledger hashes, Gold v5 SQLite and labels
hashes, and the comparative-definition gate manifest hash. The promotion
ledger's `register_review_status` field is blank for these four targets; the
separate status reconciliation record below preserves that fact and takes
accepted review status only from the adjudicated ledger.

The current Git-bound authority manifest is
[`vpb-roe-parent-equity-authority-manifest-20260925.json`](../../../../reports/data-foundation/vpb-roe-parent-equity-authority-manifest-20260925.json)
(ID: `vpb-roe-parent-equity-authority-20260925`). It binds the exact hashes of
this README, the v2 packet record, and the status reconciliation sidecar. The
sidecar is
[`vpb-roe-promotion-review-status-reconciliation-20260925.json`](../../../../reports/data-foundation/vpb-roe-promotion-review-status-reconciliation-20260925.json).
The source PDFs, source ledgers, and Gold SQLite are local ignored evidence
artifacts; the authority record preserves their exact identities and source
trail.

The hash-matched read-only Gold v5 comparative gate is eligible with no
blockers across 80 cells (76 valid and four missing). That gate output does
not satisfy the separate D-072 reviewer gate. A reviewer distinct from the
prior audit must confirm the linked authority record and gate result before
the five-issuer comparison gate can open.
