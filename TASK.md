# Task Manifest: isolate mutable SQLite databases across worktrees

## Context

- Role: Lead Architect and Orchestrator infrastructure remediation.
- Branch: `codex/db-test-isolation`.
- Linear: waived by the repository owner for the active thesis completion run.
- Incident: a test process wrote through an NTFS hardlink and changed the root
  `data/processed/finance_master_v2.sqlite` artifact.

## Scope

1. Replace SQLite hardlinks/symlinks in both worktree bootstrap scripts with an
   independent snapshot created through SQLite's backup API.
2. Fail closed when source or destination integrity checks fail, the source
   changes during copying, or destination shares source file identity.
3. Preserve `.env` hardlink behavior.
4. Record the architecture rule and incident lesson.
5. Add an automated guard against reintroducing shared SQLite sidecars.

## Verification

- Exercise the copy helper only against a synthetic temporary SQLite database.
- Confirm destination mutation does not change source rows or SHA-256.
- Confirm destination uses WAL and does not share source file identity.
- Run `python scripts/check_architecture_guardrails.py`.
- Run `python -m compileall -q scripts tests`.
- Run `git diff --check`.

## Out of scope

- Restoring or deleting rows from the affected root database.
- Application behavior under `src/` or `frontend/`.
- Merging any open feature Pull Request.
