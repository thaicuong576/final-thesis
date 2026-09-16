# Repository SDLC

This project follows a lightweight GitHub Flow / trunk-based process suitable
for a single-maintainer thesis software project.

## Canonical branch

`main` is the single canonical integration branch. It was bootstrapped from
the accepted thesis commit `a83044886752b1ec6e5402014220875d87bbd18f`.
Historical phase branches remain traceability artifacts and are not alternate
development trunks.

No coding agent may modify `main` directly. Every subsequent change starts
from the latest remote `main`, uses a dedicated short-lived branch, and enters
`main` through a reviewed Pull Request.

## Standard lifecycle

```text
research/specification
  → plan
  → data foundation
  → baseline
  → capability/agent implementation
  → evaluation
  → preview deployment
  → retest/release
```

For every repository change — including code, data, documentation, tests,
configuration, templates, metadata, experiments, and UI changes —:

1. `git fetch origin`.
2. Switch to `main` and run `git pull --ff-only origin main`.
3. Confirm `git status --porcelain` is empty.
4. Create a new branch from current `main`.
5. Keep the change within one declared scope.
6. Run focused tests, regressions, architecture checks, and build checks that
   apply to the change.
7. Review `git status`, `git diff`, and `git diff --check`.
8. Commit with a Conventional Commit title.
9. Push with `git push -u origin <branch>`.
10. Open a PR from the branch to `main`.
11. Review the exact diff and automated checks.
12. Squash merge only after review; do not merge automatically unless the
    repository owner explicitly authorizes it.
13. Verify remote `main` HEAD, then delete the short-lived branch.
14. Start the next task from the new `main` HEAD.

Required handoff fields are:

```text
Base SHA:
Branch:
Commit SHA:
PR:
Changed files:
Tests:
Known failures:
Working-tree status:
```

## Branch and commit policy

Allowed branch prefixes are:

`feat/`, `fix/`, `data/`, `docs/`, `refactor/`, `test/`, `chore/`, `ui/`,
`experiment/`, and `hotfix/`.

Names are lowercase, kebab-case, short, and descriptive. Do not create new
long-lived `prep/*` or `thesis/*` integration branches. Do not reuse a branch
for unrelated work.

Allowed Conventional Commit prefixes are `feat:`, `fix:`, `data:`, `docs:`,
`refactor:`, `test:`, `chore:`, `ui:`, and `experiment:`. Avoid `wip`,
`changes`, `final fix`, or similarly opaque titles.

Repository settings prefer squash merge, disable merge commits and rebase
merges, and delete the PR head branch after merge. `main` must never be
force-pushed or deleted.

## Change-type gates

| Change | Minimum evidence |
|---|---|
| Feature/architecture | Contract/design impact, focused tests, regression tests, architecture guard, explicit scope boundary |
| Bug fix | Reproduced failure, regression test, minimal correction |
| Data | Immutable raw source, provenance/hash, reconciliation, candidate/accepted state, snapshot impact, deterministic verification |
| Documentation | Docs-only scope; no hidden behavior change |
| Refactor | Equivalent behavior unless explicitly stated; relevant regression tests |
| UI | Frontend checks; no silent backend architecture change |
| Experiment | Isolated branch; no production/reference semantic changes without a separate architecture PR |
| Hotfix | Latest `main`, minimal patch, PR back to `main`, exception documented if outage bypasses normal flow |

## Testing and CI

Python changes should normally include focused unit tests, relevant
regressions, the architecture guard, compileall, and `git diff --check`.
Frontend changes should pass `npm ci`, lint, tests, and production build.

The tracked GitHub Actions inventory currently contains only
`.github/workflows/frontend.yml` (`Frontend validation`) for frontend paths.
There is no Python workflow or package-management specification yet. The
known Python baseline fixture/dependency failures must be repaired before a
full Python check is made required. Local results must be labeled as local;
CI status must be read from GitHub.

GitHub branch protection and repository rulesets are not available for this
private repository under the current plan. The project therefore records the
desired no-direct-push/review policy here and relies on the PR workflow until
the repository plan or visibility changes. The limitation must not be
misrepresented as active hard protection.

## Data-change review

Raw data is immutable. A data PR must identify the source, source URL/ID,
retrieval metadata, content hash, evidence locator, reconciliation decision,
candidate versus accepted status, missingness/conflict semantics, and snapshot
impact. Candidate facts are never promoted by editing a status string.

## Architecture-change review

An architecture PR must identify the affected layer and boundary, update the
appropriate contract/decision record, add regression tests, run the
architectural guard, and explain provider/storage implications. The reusable
core must remain independent of Gold and physical SQLite details; Macro,
Sector/Peer, and Company remain query-selected capabilities rather than a
mandatory pipeline.

## Historical branches

Historical branches are classified before cleanup:

- `A`: merged/ancestor of `main`;
- `B`: same head as `main`;
- `C`: diverged/unique commits;
- `D`: active work.

Branches in A/B may receive immutable milestone tags before deletion. Branches
in C/D require explicit inspection and must not be merged or deleted
automatically. An archive or separate PR is preferred when unique work is
valuable. The initial governance migration produces the inventory and does not
delete historical branches.
