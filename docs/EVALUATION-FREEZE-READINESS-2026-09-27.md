# A/B/C evaluation freeze readiness — 2026-09-27

**Status:** `NOT_READY_FOR_FREEZE`
**Purpose:** dated preflight record for a fair A/B/C run; this is not a scoring result.

## 1. Decision

The final experiment remains **pre-freeze**. No scoring run is authorized by
this record. The tracked candidate manifest reports
`protocol_final_freeze_ready: false`, `scoring_runs_created: false`, and
`ab_c_results_created: false`; every candidate task has
`scoring_eligible_now: false`.

This decision is deliberately fail-closed. A green offline implementation
probe, a prompt-version string, or a successful CI job does not establish live
provider quality, accepted-snapshot readiness, or fair A/B/C evidence.

## 2. Immutable identities to bind at freeze

| Control | Current recorded identity | Interpretation |
|---|---|---|
| Gold dataset/snapshot | `gold-bank-2025-expanded-v5-evidence` | The benchmark snapshot named by the peer-input audit; it must be resolved and verified by the runtime before a run. |
| Gold SQLite raw-byte SHA-256 | `1b1b5c090d2f8ede87a4c33ea3ee716f7a54c9de7c51089f4d3893d7a1ffce73` | Evidence identity in `gold-v5-peer-input-audit-v1.json`; not a claim that the deployment currently mounts it. |
| Candidate question-set | `data/evaluation/p4-questions-v1.jsonl` | Ten candidate tasks: eight analytical tasks plus T09/T10 rejection controls. |
| Question-set hash | `c4747af992441cc6063fa9dc08b1a09fc1a4a923a5415a2de4391c03e17fbc09` | SHA-256 over canonical LF UTF-8 bytes; preserve exact bytes and hash mode. |
| Prompt version | `prompt-contract-v1` | All ten candidate specs use this string. Arm-specific rendered prompt hashes remain a freeze-time requirement; see PR #65. |
| Rubric/repetitions | Not frozen | Select the repetition count, randomization seed, rubric anchors, retry policy, and budget before the first scored run. |

The Gold snapshot identity and question-set identity must be copied into every
run manifest. A task ID or prompt version by itself is not sufficient binding.

### Explicit evidence-root verification

On 27/09, the read-only `p4-evaluation-inputs-v1` verifier was run with an
explicit external evidence root because the ignored Gold SQLite artifact is not
present in this managed checkout. The verifier returned `PASS` with:

- Gold raw-byte SHA-256 unchanged at
  `1b1b5c090d2f8ede87a4c33ea3ee716f7a54c9de7c51089f4d3893d7a1ffce73`;
- SQLite integrity `ok`, 80 Gold cells checked, 76 valid cells and 4 missing;
- 17/17 source artifacts matched and 16 peer probes reproduced;
- candidate question-set, task-spec and expected-coverage hashes bound to the
  verifier output;
- `final_protocol_freeze_ready: false` and `scoring_eligible_now: false`.

The same command without `--evidence-root` fails closed because the ignored Gold
file is absent from the managed worktree. This is an evidence-packaging/runtime
provisioning blocker, not permission to copy, regenerate or silently substitute
the Gold database. Any future run must record the explicit evidence root or a
reviewed deployment artifact identity.

## 3. Candidate task gate matrix

| Tasks | Scope | Current gate | Why not scoring-eligible |
|---|---|---|---|
| T01–T03 | Company snapshot/missingness | Company Gold provider + Stage-1 E2E; missing-data fail-closed E2E | Same-snapshot end-to-end evidence is not recorded in the candidate manifest. |
| T04–T05 | Company trends | Multi-period request with exact ordered-period scope | Offline implementation probes exist, but live readiness and final freeze gates remain open. |
| T06–T07 | Peer snapshot | Query-adaptive peer runtime E2E; T07 also D-072 authority gate | Query-adaptive peer execution and authority-bound run evidence are not frozen. |
| T08 | Multi-period peer | Multi-period peer runtime, context budget, critique/revision E2E | Current public contract does not support this scope; it remains explicitly blocked. |
| T09–T10 | Rejection controls | Reject unsupported period/issuer before provider dispatch | Controls are candidate protocol fixtures, not evidence that a scored arm run exists. |

The manifest is the source of the current eligibility flags. This table does
not promote any task by inference and does not alter the task specs.

## 4. Evidence already available versus still missing

### Available, but limited in scope

- P1 records one reviewed CTG 2024 Q4 operational onboarding path with source
  reconciliation and derived-value receipts. It is not the Gold benchmark and
  does not establish live model/provider readiness.
- P2 and P4A records offline request planning, Stage-1, semantic critique,
  bounded revision, SSE terminal-event persistence, and run-history checks.
  These are implementation acceptance probes using explicit offline fixtures.
- CI, architecture checks, OpenAPI validation, and focused tests pass on the
  corresponding PR heads. CI success is not a deployed smoke test.
- PR #65 registers common prompt invariants and arm topology. It does not
  provide rendered `prompt_sha256` values for scored calls.

### Required before freeze

1. Resolve a runnable accepted snapshot and provider configuration in the
   target runtime; `/api/ready` must be truthful and non-503 for the run.
2. Execute same-snapshot Company and query-adaptive Peer paths through the
   public runtime, including missingness and exact period coverage checks.
3. Demonstrate the actual C path: structured critic issue/action, targeted
   affected-writer rerun, re-synthesis, and Stage-1 after every round, with a
   maximum of two rounds.
4. Freeze the eligible task list, rubric, repetition count, seed, model/provider
   version, source/evidence policy, output contract and budgets before scoring.
5. Render and persist prompt fingerprints for every call, preserving the same
   question bytes, snapshot, model, tools and contract across A/B/C.
6. Run the teacher walkthrough against the deployed link and preserve the
   resulting runtime evidence separately from offline fixtures.

If any gate fails, retain the failure in the denominator/record and keep the
protocol pre-freeze. Do not replace a missing live result with an offline
fixture or historical 75-job pilot.

## 5. Required run-manifest fields

Each scored attempt must bind at least:

- task ID, exact question-set bytes/hash and ordered run sequence;
- arm, repetition, randomization seed and final rubric version;
- accepted snapshot ID/hash, capability catalog, source/evidence policy and
  output/Stage-1 contract versions;
- model/provider name and version, prompt-set ID/version and every rendered
  `prompt_sha256`;
- start/end timestamps, latency, model calls, input/output tokens, cost,
  revision rounds, retry/error details and terminal acceptance state;
- structured claim/evidence lineage and the blinded scoring artifact.

The evaluator must preserve failed and incomplete runs, remove arm labels from
the blinded review, and report both completed-only and completion-adjusted
quality. Do not rewrite the rubric after observing results.

## 6. References

- [`Evaluation Protocol v1 draft`](EVALUATION-PROTOCOL-V1-DRAFT.md)
- [`Gold v5 peer-input audit`](../data/evaluation/gold-v5-peer-input-audit-v1.json)
- [`P4 task specifications`](../data/evaluation/p4-task-specs-v1.json)
- [`Experiments README`](../experiments/README.md)
- [`P2 implementation evidence`](P2-IMPLEMENTATION-VERIFICATION-2026-09-26.md)
- [`P4A runtime evidence`](P4A-IMPLEMENTATION-VERIFICATION-2026-09-26.md)
- [`Prompt Contract v1 register — PR #65`](https://github.com/thaicuong576/final-thesis/pull/65)

At this date the record proves disciplined non-scoring, not a successful final
experiment. The next state transition requires new runtime evidence and an
explicit freeze decision; it must not be inferred from this document.
