# TASK — P2/P3 real adaptive runtime and bounded revision

## Dispatch
- Role: `worker-api`
- Base: `origin/main@9e0298a3de01c31b01a412ec574f265eeb79d2ea`
- Branch: `codex/p2p3-runtime-20260925`
- Tracking: Linear intentionally omitted because the user explicitly asked to skip Linear.
- Binding sources: `.agent/foundation/*`, `docs/ARCHITECTURAL-GUARDRAILS.md`, `docs/DATA-CONTRACT.md`, `contracts/openapi.json`, `docs/EVALUATION-PROTOCOL-V1-DRAFT.md`, decisions D-069 through D-072.

## Objective
Make the production analysis path execute the real query-adaptive plan, selected specialists, deterministic Stage-1 checks, bounded semantic critique/revision, re-synthesis, and final acceptance. Remove scripted or unconditional success behavior from `/api/analyze` and SSE.

## Required behavior
1. Freeze one AnalysisPlan per accepted request after capability validation.
2. Company-only requests call only Company. Peer requests call only the relevant Company/Sector capabilities. Macro remains absent unless the validated snapshot supports the requested macro data.
3. Specialists return structured claims with observation/evidence/reference/limitation fields.
4. Stage-1 fails closed for numeric, scope, reference, provenance, contradiction, and missingness errors.
5. Configuration C produces structured critique issues, reruns only affected work, re-synthesizes, reruns Stage-1, and stops within the configured maximum revision count.
6. Expose terminal states equivalent to ACCEPT, ACCEPT_WITH_LIMITATIONS, and FAIL_ACCEPTANCE. Limitations are allowed only for genuine data/evidence insufficiency.
7. SSE events reflect actual runtime transitions and never expose chain-of-thought.
8. Do not alter `contracts/openapi.json` without stopping and reporting the required contract change.

## Acceptance cases
- Accepted company-only run with no unused specialist.
- Accepted peer run using the explicit five-bank peer universe and preserving missingness.
- One injected defect causes a targeted revision and subsequent acceptance.
- One unrepairable critical defect ends in FAIL_ACCEPTANCE.
- Out-of-scope request fails closed before specialist execution.
- Existing API, data boundary, and provenance tests remain green.

## Scope
- Allowed: `src/thesis_api/`, `src/thesis_agents/`, directly relevant API/agent tests, and a short evidence report under `reports/runtime/`.
- Forbidden: `frontend/`, raw/processed data mutation, hard-coded five-bank logic inside reusable core, fabricated model results.
- Record unforeseen issues in `.agent/memory/lessons-learned.md`.

## Verification and handoff
Run focused tests, the full Python suite, and `python scripts/check_architecture_guardrails.py`. Commit, push, open a PR titled `feat(api): real adaptive critique and revision runtime`, wait for all CI checks, and report base SHA, branch, commit, PR, changed files, tests, known failures, and working-tree status. Do not merge.