# VPB ROE adjudication and Gold v5 authority handoff

Status: the 2024 Q1-Q4 parent-attributable ROE cells have two accepted checker
reviews and an accepted adjudication. A distinct independent reviewer accepted
the repository-bound records at reviewed head 2b292ddf21bd6be8a550f81fb518fca5dc419efb. The five-issuer ROE comparison gate is open for the Gold v5 scope because that ACCEPT is recorded in reports/data-foundation/vpb-roe-parent-equity-independent-review-attestation-20260925.json; the eligible gate output alone was not sufficient.

The earlier local README and v1 packet manifest both said
candidate_pending_fresh_review, which contradicted the adjudicated review
ledger. Their legacy Windows checkout-byte SHA-256 values (audit only) are
5D85C74ABA6B41A97A2F2D1A2AFFE1E251D1B8E1E46B7D62AB842FAE02BF2496 (README)
and 24BF42B3D19B2EEE264BCBB03827585755096AA278795B95EB00EC825267A0B2
(manifest v1). The original checker, adjudication and promotion ledgers remain
unchanged.

The current packet record is VPB_parent_roe_manifest-v2.json. It binds the
Q1-Q4 filing hashes and locators, adjudicated-review and promotion-ledger
hashes, Gold v5 SQLite and labels hashes, and comparative-definition gate
hash. Its canonical LF UTF-8 SHA-256 is bound by the status sidecar and current
authority manifest. The promotion ledger's register_review_status field is
blank for all four VPB targets; that original gap remains unchanged, and
accepted review status comes only from the adjudicated ledger.

The Git-bound authority manifest is
reports/data-foundation/vpb-roe-parent-equity-authority-manifest-20260925.json
(ID: vpb-roe-parent-equity-authority-20260925). It binds this README, packet,
status sidecar, hashing convention, verification script and independent-review
attestation. Stable paths identify linked records; their hashes are bound in
the authority manifest to avoid circular references. Source PDFs, ledgers and
Gold SQLite are local ignored evidence artifacts; their exact raw-byte hashes
and source trail remain recorded.

The read-only Gold v5 comparative gate returned eligible with no blockers
across 80 cells (76 valid and four missing). The distinct reviewer also
confirmed that output. VPB is eligible for the five-issuer ROE comparison
scope under D-063/D-072 because the ACCEPT attestation links the exact reviewed
head, source evidence, control records, Q4 recomputation and gate result.

To verify tracked controls and locally provisioned evidence, run
python scripts/verify_vpb_roe_authority_records.py --evidence-root <path-to-evidence-root>
from this checkout. The verifier uses tracked controls from this checkout and
reads ignored evidence only from the explicit evidence-root argument. CI can
verify canonical tracked-text hashes from its checkout, but cannot verify
ignored PDFs, ledgers, Gold SQLite or gate JSON unless that evidence root is
provisioned there.
