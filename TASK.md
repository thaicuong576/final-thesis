# Task manifest — six-chapter outline and Chapters 5–6 working draft

## Identity

- Branch: `codex/thesis-chapters-5-6-outline-20260927`
- Base: `1cab2549db20f710165cffe8197aaa24a4014d69` (`origin/main` at dispatch)
- Role: Lead Architect documentation worker
- Tracker: No Linear issue, per the user's explicit waiver for this thesis workstream.
- Scope: `docs/THESIS-DRAFT-OUTLINE-VI.md`, `docs/THESIS-CHAPTERS-5-6-WORKING-2026-09-27-VI.md`, and this manifest only.

## Objective

Restore the six-chapter report outline referenced by `README.md` and provide an evidence-bounded working draft for Chapters 5 and 6. The draft must distinguish verified offline/operational evidence from live deployment and final A/B/C evidence, and must not modify the read-only source thesis.

## Binding evidence

- `docs/THESIS-MASTERPLAN-2026-09-24.md`
- `docs/P1-DATA-PORTABILITY-PREFLIGHT-2026-09-26.md`
- `docs/P2-IMPLEMENTATION-VERIFICATION-2026-09-26.md`
- `docs/P4A-IMPLEMENTATION-VERIFICATION-2026-09-26.md`
- `docs/EVALUATION-PROTOCOL-V1-DRAFT.md`
- `data/evaluation/p4-task-specs-v1.json`
- `docs/TEACHER-WALKTHROUGH-CHECKLIST-2026-09-27-VI.md` on PR #64
- `docs/EVALUATION-FREEZE-READINESS-2026-09-27.md` on PR #66

## Acceptance criteria

1. The tracked outline has six chapters and explains that the old seven-chapter draft is historical input.
2. Chapter 5 reports only durable evidence: CTG operational onboarding, offline runtime/Stage-1/revision probes, and the current deployment/evaluation blockers.
3. Chapter 6 states bounded conclusions, limitations, reproducibility/ethics, and future work without claiming live readiness or A/B/C superiority.
4. Pending result tables are clearly marked as pending and contain no invented scores, latency, token, cost, or model values.
5. Links resolve, `git diff --check` passes, and only documentation plus this manifest change.
6. Open a PR and leave it unmerged until explicit user authorization.
