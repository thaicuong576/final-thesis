# Contributing

`main` is the only canonical integration branch for this repository. The
historical `thesis/phase-1-7` branch is retained for traceability, but new work
must start from the latest `main`.

## Required workflow

Every repository change must use a new short-lived branch, commit, and Pull
Request. This includes code, data, documentation, tests, configuration,
templates, metadata, experiments, and UI changes:

```text
fetch main → create branch → scoped change → test → commit → push → PR
→ review → squash merge → verify main → delete branch
```

Before starting:

```bash
git fetch origin
git switch main
git pull --ff-only origin main
git status --porcelain
git switch -c <type>/<short-kebab-description>
```

Never implement directly on `main`. Do not merge a Pull Request unless the
repository owner explicitly authorizes the merge.

## Branch names

Use one of these lowercase, short, descriptive prefixes:

`feat/`, `fix/`, `data/`, `docs/`, `refactor/`, `test/`, `chore/`, `ui/`,
`experiment/`, `hotfix/`.

Use kebab-case, avoid personal names and generic names such as `dev`, `work`,
`new`, or `temp`, and never reuse a branch for unrelated work. Do not create
new long-lived `prep/*` or `thesis/*` integration branches.

## Commits and Pull Requests

Use Conventional Commits, for example `feat:`, `fix:`, `data:`, `docs:`,
`refactor:`, `test:`, `chore:`, `ui:`, or `experiment:`. One commit should
represent one coherent unit; clean up iterative commits before opening the PR
when useful.

Every PR must state its purpose, scope, architecture impact, changed files,
verification commands and results, known baseline failures, provenance/data
effects, and explicit out-of-scope items. The repository PR template provides
the complete checklist.

The repository is configured to prefer squash merges, disallow merge commits
and rebase merges, and delete the head branch after a successful merge. Review
the exact PR diff before merging. After merge, verify the new remote `main`
SHA and start the next task from that SHA.

## Verification expectations

Run the smallest relevant focused tests, then regression tests for affected
boundaries. For Python changes, also run:

```bash
python scripts/check_architecture_guardrails.py
python -m compileall -q src scripts tests
git diff --check
```

Use `PYTHONPATH=src` when the local environment requires it. For frontend
changes, run the commands in the frontend validation workflow (`npm ci`,
`npm run lint`, `npm test -- --run`, and `npm run build`). Never report local
test output as GitHub CI output.

Worktree setup must copy SQLite through `scripts/copy_sqlite_snapshot.py`.
Never hardlink or symlink the database or its WAL/SHM files across worktrees.
Database tests and local API runs must use the isolated worktree snapshot or a
temporary copy, with the source artifact hash checked when relevant.

## Data and architecture changes

Data changes must preserve immutable raw inputs and include source identity,
URL, retrieval metadata, hashes where appropriate, reconciliation, candidate
versus accepted status, snapshot impact, and deterministic verification. Never
silently promote candidate data.

Architecture changes must document the affected contract/boundary, add focused
and regression tests, run the architecture guard, and preserve provider
transferability. Do not introduce Gold/SQLite coupling, hardcode the five-bank
sample, or turn Macro → Sector → Company into a mandatory pipeline without an
explicit architecture decision.

## Emergency changes

Use `hotfix/<short-description>` from the latest `main`, then open a PR back
to `main`. A direct emergency push is allowed only when a repository outage
makes the normal PR path impossible; document the exception immediately
afterward. Never force-push `main`.

## Current CI limitation

The repository currently has one tracked GitHub Actions workflow:
`.github/workflows/frontend.yml`, which validates frontend changes. Python
full-suite execution is not yet a stable required check because the repository
has known baseline fixture/dependency gaps. This limitation is recorded rather
than hidden; do not configure a required check that does not exist and pass
reliably on a clean `main`.
