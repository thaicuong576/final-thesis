# Branch inventory — 2026-09-16

This inventory was captured after fetching all remote refs. The comparison
base is the accepted canonical commit:

`a83044886752b1ec6e5402014220875d87bbd18f`

The repository default branch is now `main`, and `origin/main` points to that
same SHA. No branch is deleted or rewritten by this migration.

## Remote branches

| Branch | Head | Relation to `main` | Classification | Proposed action |
|---|---|---|---|---|
| `main` | `a830448` | equal | B — canonical | Retain; governed by process and PR policy (hard protection unavailable) |
| `thesis/phase-1-7` | `a830448` | equal | B — historical canonical | Retain for traceability now; tag/archive before later deletion |
| `prep/pre-gold-decision-pass` | `a830448` | equal | B — completed workstream | Retain for review traceability; tag/archive before later deletion |
| `prep/pre-phase4-data-acquisition` | `92eaf316` | ancestor | A — completed workstream | Retain now; tag `milestone/pre-phase4-acquisition` before later deletion |
| `prep/phase3b-a-fixture-critic` | `6bfd5bb` | ancestor | A — completed milestone | Retain now; tag `milestone/phase3b-a` before later deletion |
| `prep/phase3b-b-bounded-controller` | `8a4a294` | ancestor | A — completed milestone | Retain now; tag `milestone/phase3b-b` before later deletion |
| `prep/phase3b-c-langgraph-adapter` | `f9bdbba` | ancestor | A — completed milestone | Retain now; tag `milestone/phase3b-c` before later deletion |
| `prep/phase3b-d-openai-semantic-critic` | `0675869` | ancestor | A — completed milestone | Retain now; tag `milestone/phase3b-d` before later deletion |
| `prep/phase3b-query-adaptive-contract` | `559190b` | ancestor | A — completed contract milestone | Retain now; tag/archive before later deletion |
| `ui/create-analysis-prototype` | `5cadddd` | ancestor | A — historical UI work | Retain now; tag/archive before later deletion |
| `frontend/clean-room-redesign` | `039a766` | diverged | D — active frontend work | Retain; review through a separate `ui/*` PR; never merge automatically |
| `chore/reorganize-legacy-app` | `249c78f` | diverged | D — active repository/frontend reorganization | Retain; inspect through a separate `chore/*` PR; never merge automatically |
| `thesis/acceptance-phase-1-2` | `cdd5b71` | diverged | C — legacy diverged line | Retain for audit; do not merge; archive or delete only after explicit review |

`origin/HEAD` is a symbolic ref and now points to `origin/main`; it is not an
additional branch.

## Diverged branch notes

### `frontend/clean-room-redesign`

Unique commits are frontend/product work, including the query-adaptive
analysis composer and event-driven analysis-session workspace:

```text
4d58ef5 docs: record clean-room frontend direction
9babe53 feat(frontend): implement query-adaptive Screen 1 analysis composer and clean-room shell
c149c04 feat(frontend): apply Screen 1 corrections for query-adaptive capability planning, dynamic mismatch detection, and clean business scope adjustment
e425172 feat(frontend): implement Screen 2 Live Multi-Agent Workflow (Query-Adaptive)
8e8ab33 fix(analysis-session): preserve query intent during scope adjustment, resolve explicit years dynamically, and keep macro-only scope metric-consistent
bd22daf fix(frontend): remove peer capability toggle from scope adjustment, plan freshly from question intent, and render contextual read-only peer scope
2624c85 feat(analysis-session): implement query-adaptive orchestrator workspace and specialist sessions
c013929 feat(analysis-session): refactor to event-driven orchestrator session model with pure projector and inline specialist chronology
108378c fix(analysis-session): resolve review blockers for event-driven orchestrator session
c5b0734 fix(analysis-session): resolve semantic blockers for event-driven session model
039a766 fix(analysis-session): terminate in BLOCKED on empty analysis plan and prevent report synthesis
```

This branch is active frontend work and also has a different net tree from
the canonical backend/data line. It must not be merged wholesale into `main`.

### `chore/reorganize-legacy-app`

Unique commits are:

```text
c3dad33 feat(frontend): add create analysis application foundation
249c78f chore: separate product research and legacy ui
```

The work is a frontend foundation plus repository/legacy-UI reorganization.
It changes many paths relative to `main`, including moving or removing legacy
and research surfaces. Retain it as active parallel work and review any
useful pieces in a separate scoped PR.

### `thesis/acceptance-phase-1-2`

Its unique commits are the same workstream family under a different diverged
line:

```text
c3dad33 feat(frontend): add create analysis application foundation
cdd5b71 chore: separate product research and legacy UI
```

It is not part of the canonical lineage. Do not use it as a development base
or merge it into `main` without an explicit file-level migration decision.

## Cleanup decision

No open Pull Requests or open Issues were found during the preflight. Even so,
no branch is deleted in this governance migration. Completed ancestor/equal
branches should first receive immutable milestone tags where useful, then be
deleted in a later explicit cleanup action. Diverged/active branches remain
retained until their owners decide whether to archive them or submit a
separate scoped PR.
