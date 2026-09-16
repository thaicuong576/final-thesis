# Historical branch cleanup and diverged-branch audit — 2026-09-16

## Scope and invariant

This report records the repository cleanup requested after the governance PR
was merged. It covers remote branch inventory, immutable milestone tags,
deletion of verified historical branches, and read-only audits of the three
diverged branches.

No business logic, thesis data, Gold data, schema, experiment, agent, or
frontend implementation was changed by the cleanup. No diverged branch was
merged, rebased, force-pushed, or deleted. `main` remains the only canonical
integration branch; all repository changes continue to require a short-lived
branch, commit, and Pull Request.

## Canonical state and preflight

| Item | Verified value |
|---|---|
| Default branch | `main` |
| `origin/main` | `85e840c221503a6d02955c4fd0c755f5b0c48057` |
| `origin/HEAD` | `origin/main` |
| Root worktree during cleanup | clean before cleanup artifact work; frontend worktree preserved |
| Open Pull Requests at preflight | none |
| Open Issues at preflight | none |
| Active workflow observed | `.github/workflows/frontend.yml` (`Frontend validation`) |

The preflight fetched all remote refs with pruning and tags. The cleanup was
allowed to proceed only because `origin/main` matched the expected
`85e840c...` commit.

## Immutable milestone tags

All tags below are annotated tags. The target commit is the dereferenced
`^{}` value returned by `git ls-remote --tags origin`; the annotation subject
is included so the tag meaning is auditable.

| Tag | Target commit | Annotation | Remote verification |
|---|---|---|---|
| `milestone/phase3b-query-adaptive-contract` | `559190bce0ca548d1490c9225e6608e56d9dfd20` | Query-adaptive semantic contract milestone | verified on `origin` |
| `milestone/phase3b-a-semantic-critic` | `6bfd5bb9453ef04dbaf53fb89729da9b7cd7357f` | Phase 3B-A provider-neutral semantic critic milestone | verified on `origin` |
| `milestone/phase3b-b-bounded-revision` | `8a4a2947caef831dd640d3f032b373c4545ffe94` | Phase 3B-B bounded revision milestone | verified on `origin` |
| `milestone/phase3b-c-langgraph-adapter` | `f9bdbba4f777f82e5026b55f7300de467d26f1b9` | Phase 3B-C LangGraph adapter milestone | verified on `origin` |
| `milestone/phase3b-d-openai-critic` | `0675869956888926963cf90a0280143b1b730cd3` | Phase 3B-D OpenAI semantic critic milestone | verified on `origin` |
| `milestone/pre-phase4-acquisition` | `92eaf3161bd6e811776e8f172bdc309737a6bb0e` | Pre-Phase-4 acquisition milestone | verified on `origin` |
| `milestone/pre-gold-decision` | `a83044886752b1ec6e5402014220875d87bbd18f` | Pre-Gold decision milestone | verified on `origin` |
| `milestone/ui-create-analysis-prototype` | `5cadddd3a66bdb615243ef525ec49860981733f7` | Create-analysis frontend prototype milestone | verified on `origin` |

The equal-head branches `thesis/phase-1-7` and
`prep/pre-gold-decision-pass` intentionally did not receive redundant
branch-specific tags. Their former head is preserved by
`milestone/pre-gold-decision`.

## Deleted historical branches

Each branch below was checked against `origin/main` before deletion. Equal or
ancestor branches had no unique commits relative to the canonical line that
needed to be retained as a branch. Each deletion was performed individually
with a normal remote delete and then verified absent from `origin`.

| Deleted branch | Former head | Relation to `main` | Preservation |
|---|---|---|---|
| `thesis/phase-1-7` | `a83044886752b1ec6e5402014220875d87bbd18f` | equal | `milestone/pre-gold-decision` |
| `prep/pre-gold-decision-pass` | `a83044886752b1ec6e5402014220875d87bbd18f` | equal | `milestone/pre-gold-decision` |
| `prep/pre-phase4-data-acquisition` | `92eaf3161bd6e811776e8f172bdc309737a6bb0e` | ancestor | `milestone/pre-phase4-acquisition` |
| `prep/phase3b-a-fixture-critic` | `6bfd5bb9453ef04dbaf53fb89729da9b7cd7357f` | ancestor | `milestone/phase3b-a-semantic-critic` |
| `prep/phase3b-b-bounded-controller` | `8a4a2947caef831dd640d3f032b373c4545ffe94` | ancestor | `milestone/phase3b-b-bounded-revision` |
| `prep/phase3b-c-langgraph-adapter` | `f9bdbba4f777f82e5026b55f7300de467d26f1b9` | ancestor | `milestone/phase3b-c-langgraph-adapter` |
| `prep/phase3b-d-openai-semantic-critic` | `0675869956888926963cf90a0280143b1b730cd3` | ancestor | `milestone/phase3b-d-openai-critic` |
| `prep/phase3b-query-adaptive-contract` | `559190bce0ca548d1490c9225e6608e56d9dfd20` | ancestor | `milestone/phase3b-query-adaptive-contract` |
| `ui/create-analysis-prototype` | `5cadddd3a66bdb615243ef525ec49860981733f7` | ancestor | `milestone/ui-create-analysis-prototype` |

## Final retained remote branches

After deletion, the retained pre-existing remote branches are:

| Branch | Head | Reason retained |
|---|---|---|
| `main` | `85e840c221503a6d02955c4fd0c755f5b0c48057` | canonical integration branch |
| `frontend/clean-room-redesign` | `039a76663598ce734c55340f5e0867163c265a89` | active frontend work; requires scoped review |
| `chore/reorganize-legacy-app` | `249c78f78d00946a9525c12a735e16405f7efad7` | parallel repository/frontend reorganization under review |
| `thesis/acceptance-phase-1-2` | `cdd5b713ccc1bf8e3878397edcb19179eb1b9d10` | legacy diverged line retained for audit only |

The cleanup branch carrying this report is separate and is submitted to
`main` by Pull Request. `origin/HEAD` is a symbolic ref to `origin/main`, not
an additional branch.

## Diverged branch audit

The following audits are read-only. For each branch, “main since merge base”
lists every canonical commit after the branch split. No recommendation below
was executed by this cleanup.

### `frontend/clean-room-redesign`

| Field | Finding |
|---|---|
| Head | `039a76663598ce734c55340f5e0867163c265a89` |
| Merge base | `359f940799efac968a15e8c2053e073e97488b16` |
| Net diff | 38 files; 5,821 insertions; 268 deletions |
| Functional area | frontend product workflow, query-adaptive analysis composer, event-driven analysis-session workspace, UI tests and mocks |
| Overlap/risk | branch is based before the query-adaptive/core and governance commits now on `main`; wholesale merge risks stale frontend assumptions and conflict with the current application boundary |
| Migration feasibility | yes, by selecting compatible frontend concepts into a new scoped PR |
| Recommendation | `MIGRATE VIA NEW SCOPED PR` |

Unique branch commits, oldest first:

```text
4d58ef5 docs: record clean-room frontend direction
9babe53 feat(frontend): implement query-adaptive Screen 1 analysis composer and clean-room shell
c149c04 feat(frontend): apply Screen 1 corrections for query-adaptive capability planning, dynamic mismatch detection, and clean business scope adjustment
8e8ab33 fix(frontend): preserve query intent during scope adjustment, resolve explicit years dynamically, and keep macro-only scope metric-consistent
bd22daf fix(frontend): remove peer capability toggle from scope adjustment, plan freshly from question intent, and render contextual read-only peer scope
e425172 feat(frontend): implement Screen 2 Live Multi-Agent Workflow (Query-Adaptive)
2624c85 feat(analysis-session): implement query-adaptive orchestrator workspace and specialist sessions
c013929 feat(analysis-session): refactor to event-driven orchestrator session model with pure projector and inline specialist chronology
108378c fix(analysis-session): resolve review blockers for event-driven session
c5b0734 fix(analysis-session): resolve semantic blockers for event-driven session model
039a766 fix(analysis-session): terminate in BLOCKED on empty analysis plan and prevent report synthesis
```

Main commits since the merge base, oldest first:

```text
a5a7089 docs: align architecture with query-adaptive constitution
29b5d59 feat: make semantic acceptance contracts query-adaptive
154ea18 docs: reconcile spec with current query-adaptive scope
559190b fix: tighten semantic issue acceptance contracts
6bfd5bb feat: add provider-neutral semantic critic boundary
1bfe1c7 feat: add bounded semantic revision state machine
8a4a294 fix: tighten revision lifecycle and limitation attribution
f9bdbba feat: add LangGraph revision workflow adapter
740f83b feat: add OpenAI semantic critic adapter
4bf77b6 fix: preserve semantic issue identity across revisions
0675869 fix: preserve issue identity across workflow history
143cb55 data: acquire pre-phase4 macro and sector sources
92eaf31 chore: make pre-phase4 acquisition verification reproducible
a830448 data: resolve pre-gold macro sector decision debt
85e840c chore: normalize repository sdlc governance
```

Exact changed file set versus the merge base:

```text
docs/FRONTEND-CLEAN-ROOM-STAGE-A-V1.md
frontend/src/components/ui/textarea.tsx
frontend/src/features/analysis-composer/components/ActiveDatasetCard.tsx
frontend/src/features/analysis-composer/components/DatasetSelectorSheet.tsx
frontend/src/features/analysis-composer/components/HeroComposer.tsx
frontend/src/features/analysis-composer/components/RecentReportsSummary.tsx
frontend/src/features/analysis-composer/components/RequestInterpretationCard.tsx
frontend/src/features/analysis-composer/components/ScopeAdjustmentDrawer.tsx
frontend/src/features/analysis-composer/components/ScopeMismatchAlert.tsx
frontend/src/features/analysis-composer/components/SuggestedQuestions.tsx
frontend/src/features/analysis-composer/index.ts
frontend/src/features/analysis-composer/model/intentParser.ts
frontend/src/features/analysis-composer/model/types.ts
frontend/src/features/analysis-session/components/AnalysisSessionWorkspace.tsx
frontend/src/features/analysis-session/components/InlineSpecialistInvocationCard.tsx
frontend/src/features/analysis-session/components/ObservableActivityTimeline.tsx
frontend/src/features/analysis-session/components/OrchestratorEntry.tsx
frontend/src/features/analysis-session/components/OrchestratorThread.tsx
frontend/src/features/analysis-session/components/ReviewFeedbackBlock.tsx
frontend/src/features/analysis-session/components/RevisionRoundBlock.tsx
frontend/src/features/analysis-session/components/SessionContextBar.tsx
frontend/src/features/analysis-session/components/SpecialistArtifactSummaryBlock.tsx
frontend/src/features/analysis-session/components/SpecialistSessionSheet.tsx
frontend/src/features/analysis-session/components/UserQuestionEntry.tsx
frontend/src/features/analysis-session/index.ts
frontend/src/features/analysis-session/mock/MockAnalysisSessionDriver.ts
frontend/src/features/analysis-session/mock/companyOnlyEvents.ts
frontend/src/features/analysis-session/mock/companyPeerEvents.ts
frontend/src/features/analysis-session/mock/dynamicEventGenerator.ts
frontend/src/features/analysis-session/mock/macroCompanyEvents.ts
frontend/src/features/analysis-session/mock/scenarioRegistry.ts
frontend/src/features/analysis-session/mock/targetedRevisionEvents.ts
frontend/src/features/analysis-session/model/projector.ts
frontend/src/features/analysis-session/model/types.ts
frontend/src/pages/create-analysis/CreateAnalysisPage.tsx
frontend/tests/AnalysisSessionWorkspace.test.tsx
frontend/tests/CreateAnalysisPage.test.tsx
frontend/tests/intentParser.test.ts
```

### `chore/reorganize-legacy-app`

| Field | Finding |
|---|---|
| Head | `249c78f78d00946a9525c12a735e16405f7efad7` |
| Merge base | `6748f21f8bee67bab8e5b0e976d7218d032848c8` |
| Net diff | 52 files; 6,505 insertions; 65 deletions |
| Functional area | create-analysis frontend foundation, package/runtime baseline, legacy UI and research UI separation, docs/index updates |
| Overlap/risk | its base predates the canonical Phase 0–3B, Macro/acquisition, and governance line; it adds/deletes/moves shared app paths and duplicates work represented by newer frontend branches |
| Migration feasibility | selected frontend foundation concepts may be reviewed independently; branch should not be merged wholesale |
| Recommendation | `ARCHIVE` |

Unique branch commits, oldest first:

```text
c3dad33 feat(frontend): add create analysis application foundation
249c78f chore: separate product research and legacy ui
```

Main commits since the merge base, oldest first:

```text
44c71e3 feat(frontend): add create analysis workspace
c70082b fix(frontend): address planner review feedback
5cadddd chore(frontend): harden runtime and dependency baseline
7765e76 chore: separate product research and legacy ui
5492b0c feat: integrate bounded macro gold layer
812431e fix: harden bounded macro gold materialization
df682a0 chore: clean up macro gold artifacts
832c193 feat: add phase 3a analysis plan contracts
dd23b68 feat: add application dataset boundary
2a0fbdf fix: harden phase 2.5 dataset boundary
eead247 fix: enforce sector metric level in tools
39f4568 docs: lock application-first architecture guardrails
76bd246 feat: add phase 0a onboarding contracts
8260573 fix: harden phase 0a onboarding invariants
0e14717 feat: add phase 0b csv onboarding slice
cc832cc fix: harden phase 0b snapshot integrity
7bd732d feat: add phase 0c evidence boundary
3fe51de fix: bind phase 0c snapshot content manifest
c47eecc fix: bind canonical observations to snapshot identity
fe6c2d5 feat(frontend): add analysis data workspace
1c60859 chore(frontend): establish shadcn design system
4cc8f60 feat(frontend): rebuild data screen with shadcn primitives
4f1f935 feat: add provider-neutral stage1 resolver boundary
7a04d83 feat: extract stage1 acceptance behind dataset resolver
41b10fa feat: use create analysis form in workspace shell
d9834e8 refine analysis workspace density
c8ee139 fix: bind phase3a semantics to dataset boundary
41009cb fix: scope phase3a fulfillment to assertions
359f940 fix: scope missingness refs to assertions
a5a7089 docs: align architecture with query-adaptive constitution
29b5d59 feat: make semantic acceptance contracts query-adaptive
154ea18 docs: reconcile spec with current query-adaptive scope
559190b fix: tighten semantic issue acceptance contracts
6bfd5bb feat: add provider-neutral semantic critic boundary
1bfe1c7 feat: add bounded semantic revision state machine
8a4a294 fix: tighten revision lifecycle and limitation attribution
f9bdbba feat: add LangGraph revision workflow adapter
740f83b feat: add OpenAI semantic critic adapter
4bf77b6 fix: preserve semantic issue identity across revisions
0675869 fix: preserve issue identity across workflow history
143cb55 data: acquire pre-phase4 macro and sector sources
92eaf31 chore: make pre-phase4 acquisition verification reproducible
a830448 data: resolve pre-gold macro sector decision debt
85e840c chore: normalize repository sdlc governance
```

Exact changed file set versus the merge base:

```text
.github/workflows/frontend.yml
.gitignore
README.md
app/README.md
docs/ADVISOR-ARTIFACT-INDEX-VI.md
docs/ANALYSIS-REPORT-HUMAN-SCORING-V1.md
docs/IMPLEMENTATION-ROADMAP-V1.md
docs/THESIS-VISUAL-PLAN-VI.md
frontend/.nvmrc
frontend/eslint.config.js
frontend/index.html
frontend/package-lock.json
frontend/package.json
frontend/postcss.config.js
frontend/src/app/App.tsx
frontend/src/app/providers.tsx
frontend/src/app/router.tsx
frontend/src/entities/analysis/api/analysisService.ts
frontend/src/entities/analysis/model/types.ts
frontend/src/entities/capability/api/capabilityService.ts
frontend/src/entities/capability/api/mockCapabilityProvider.ts
frontend/src/entities/capability/model/types.ts
frontend/src/features/create-analysis/components/AnalysisIntentSection.tsx
frontend/src/features/create-analysis/components/CapabilityDetailsDrawer.tsx
frontend/src/features/create-analysis/components/CapabilitySummaryBar.tsx
frontend/src/features/create-analysis/components/RequestSummary.tsx
frontend/src/features/create-analysis/components/ScopeSelectors.tsx
frontend/src/features/create-analysis/components/SystemContextSection.tsx
frontend/src/features/create-analysis/components/TopicMetricSelector.tsx
frontend/src/features/create-analysis/hooks/useAnalysisCapabilities.ts
frontend/src/features/create-analysis/index.ts
frontend/src/features/create-analysis/model/objective.ts
frontend/src/features/create-analysis/schema.ts
frontend/src/main.tsx
frontend/src/pages/create-analysis/CreateAnalysisPage.tsx
frontend/src/shared/lib/cn.ts
frontend/src/shared/lib/formatting.ts
frontend/src/styles/index.css
frontend/tailwind.config.ts
frontend/tests/CreateAnalysisPage.test.tsx
frontend/tests/testSetup.ts
frontend/tsconfig.app.json
frontend/tsconfig.json
frontend/tsconfig.node.json
frontend/vite.config.ts
frontend/vitest.config.ts
legacy/frozen-report-viewer/README.md
scripts/capture_thesis_ui.cjs -> legacy/frozen-report-viewer/capture_thesis_ui.cjs
app/index.html -> legacy/frozen-report-viewer/index.html
research/evaluation-ui/README.md
app/review.html -> research/evaluation-ui/review.html
scripts/build_analysis_report_v2_human_queue.py
```

The arrows denote Git rename detection, not an additional unreviewed
operation.

### `thesis/acceptance-phase-1-2`

| Field | Finding |
|---|---|
| Head | `cdd5b713ccc1bf8e3878397edcb19179eb1b9d10` |
| Merge base | `6748f21f8bee67bab8e5b0e976d7218d032848c8` |
| Net diff | same 52-file family and 6,505 insertions / 65 deletions as `chore/reorganize-legacy-app` |
| Functional area | same create-analysis foundation and legacy/research UI reorganization workstream, under a different branch name |
| Overlap/risk | the two unique commits are the same workstream family as `chore/reorganize-legacy-app`; it is equally stale relative to the canonical Phase 0–3B and governance history |
| Migration feasibility | any useful file must be selected and reworked through a new scoped PR; do not merge this line |
| Recommendation | `ARCHIVE` |

Unique branch commits, oldest first:

```text
c3dad33 feat(frontend): add create analysis application foundation
cdd5b71 chore: separate product research and legacy UI
```

Main commits since the merge base are exactly the same sequence listed in the
`chore/reorganize-legacy-app` subsection above. The changed file set is also
exactly the same 52-path set listed there. The only branch-specific difference
in the diverged line is the second commit identity/message; it does not make
this branch a separate backend or thesis implementation line.

## Decision and safety record

- The nine equal/ancestor historical branches were deleted only after their
  heads and ancestry were verified, and their milestones were pushed first.
- The three diverged branches were retained exactly as found.
- No force-push, history rewrite, merge, rebase, or cherry-pick was used.
- The cleanup does not promote data, change Gold status, start Phase 4, or
  alter the application architecture.
- The final cleanup artifact is submitted through
  `chore/historical-branch-cleanup` as a Pull Request to `main`; it must be
  reviewed and merged separately.
