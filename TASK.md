# Task Manifest: [THES-23] [ER-2] Question-type planner with tool plan and Vietnamese resolver

## Metadata
- **Branch:** `feat/er-2-question-planner`
- **Worktree:** `D:\eddie-projects\personal-projects\final-thesis\.worktrees\feat-er-2-question-planner`
- **Linear Issue:** `THES-23`
- **Spec:** `docs/plans/2026-09-28-er-report/PR-2-query-understanding.md`
- **Assigned Worker Role:** `worker-api`
- **Mode:** `/ponytail` (simplest, shortest, most minimal solution that completely satisfies spec)

## Objectives & Scope
1. `src/thesis_api/metric_presentation.py`:
   - `MetricPresentation` dataclass
   - Registries for bank metrics: `bank.npl_g35`, `bank.llr_coverage`, `bank.roa`, `bank.roe`
   - Future metric definitions (nim, casa, car, cir, ldr)
   - Topic synonym mappings (asset_quality, provisioning, profitability, comprehensive)
   - Derived formula: `derived.roe_over_roa`
   - Default scatter pairs: `[("bank.npl_g35","bank.llr_coverage"), ("bank.roe","bank.npl_g35")]`
   - Fallback for unknown metrics
   - `get_capabilities` extensions (label, shortLabel, unit, direction, decimals, group, groupLabel, suggestedQuestions, questionTypes)
2. `src/thesis_api/analysis_tools_catalog.py`:
   - Catalog of tools, agents, parameters, and defaults (lookup, peer_position, ranking, trend, head_to_head, decomposition, dispersion, relationship)
3. `src/thesis_api/query_understanding.py`:
   - `ResolvedQuery` dataclass
   - `resolve_query(query: str, catalog) -> ResolvedQuery`: deterministic normalization, period resolution (ranges, quarter, year_only, latest default), metric & topic resolution, entity matching & unknown tokens, flags (lookup, superlative, comparison, trend, macro, why, relationship)
4. `src/thesis_api/analysis_planner.py`:
   - `rules_plan(resolved, catalog) -> PlanSpec`
   - `model_plan(...)` with structured output & prompt
   - `validate_plan(...)`
   - `plan_question(...)` with fallback to rules
   - `build_analysis_plan(spec, catalog, dataset_ref) -> AnalysisPlan`
5. `src/thesis_api/messages_vi.py`:
   - Friendly Vietnamese error messages with placeholders
   - `suggestions_for(catalog) -> list[str]` (generated from catalog, no hardcoded tickers)
   - `_error_report` populates `ErrorInfoDTO`
6. Updates to `src/thesis_api/service.py` & `src/thesis_api/adaptive_runtime.py`:
   - Replace old path for queries without explicit `periods`
   - Clean up unused legacy helpers or redirect them
7. Tests:
   - `tests/test_query_understanding.py`
   - `tests/test_analysis_planner.py`
   - Update `tests/test_api_analyze.py`, `tests/test_api_stream.py`

## Verification Gates
1. `$env:PYTHONPATH="src"; $env:PYTHONUTF8="1"`
2. `python scripts/check_openapi_contract.py`
3. `python scripts/check_architecture_guardrails.py`
4. `python -m unittest discover -s tests -q`
5. `cd frontend; npm run lint; npm test -- --run; npm run build`
6. `gh pr checks <PR_NUMBER>`
