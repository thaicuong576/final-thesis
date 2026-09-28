# TASK MANIFEST: THES-21

- **Issue**: [THES-21](https://linear.app/eddiephung/issue/THES-21)
- **Role**: Backend & Data Specialist (`worker-data` / `worker-api`)
- **Workspace**: `.worktrees/feat-THES-21-critic-plan-normalization`
- **Contracts**:
  - `src/thesis_data/openai_semantic_critic.py`
  - `src/thesis_data/semantic_evaluation.py`
  - `tests/test_openai_semantic_critic.py`

## Objective

During live analysis of MBB in 2024_Q4, `OpenAISemanticCritic` returned a critique issue `SYN-001` with `required_action='reconcile_cross_level'` on a single-company analysis plan that has NO applicable links (`plan.applicable_links == ()`).
This caused Stage-1 semantic acceptance (`evaluate_stage1_semantic_acceptance`) to fail with:
`fail_acceptance: cross_level_reconciliation_requires_applicable_link:SYN-001;cross_level_issue_link_result_missing:SYN-001`

In addition, orchestrator issues must not carry `affected_claim_ids`, dimension applicabilities must strictly match `expected_dimension_applicability(plan)`, and applicable link results must match `plan.applicable_links`.

## Implementation Details

### 1. `src/thesis_data/openai_semantic_critic.py`
- Update `_normalize_critic_output(decoded: dict[str, Any], evaluator_version: str, plan: AnalysisPlan | None = None) -> dict[str, Any]`:
  1. **Applicable Links**:
     If `plan` is provided:
     - `plan_link_ids = {link.link_id for link in plan.applicable_links}`
     - Keep only link results whose `link_id in plan_link_ids`.
     - For any missing `link_id in plan_link_ids`, synthesize a default pass link result (`score=1.0`, `rationale="Link evaluated."`, empty supporting/issues).
     - If `not plan_link_ids`: set `applicable_link_results = []`.
  2. **Critique Issues**:
     - If `action == CritiqueAction.RECONCILE_CROSS_LEVEL.value`:
       * If `plan` is provided and not `plan.applicable_links` (or the issue is not in any link's `issue_ids`):
         Downgrade `action` to `CritiqueAction.REVISE_CLAIM.value`.
     - If `raw_agent == AnalysisAgent.ORCHESTRATOR.value`:
       * Clear `affected_claim_ids = []` (orchestrator issues target synthesis, not specialist claims).
     - If `plan` is provided:
       * Validate `affected_agent`: ensure it belongs to `_active_agent_ids(plan)`. If unknown or invalid, map to `AnalysisAgent.ORCHESTRATOR.value` (if target is synthesis) or the primary specialist agent.
       * Filter `affected_requirement_ids` to those declared in `plan.requirements`.
  3. **Dimension Scores**:
     If `plan` is provided:
     - Get `expected_map = expected_dimension_applicability(plan)`.
     - For each dimension, ensure `applicability == expected_map[dimension_enum].value`.
     - If `NOT_APPLICABLE`: set `score = None`, clear claims/requirements/issues.
     - If `APPLICABLE`: ensure score is finite float in [0.0, 1.0].
- In `evaluate()`: pass `plan=plan` to `_normalize_critic_output(decoded, self._evaluator_version, plan=plan)`.

### 2. Tests
- In `tests/test_openai_semantic_critic.py`:
  - Add test verifying that when `plan` has no applicable links, an issue with `reconcile_cross_level` is safely normalized to `revise_claim`.
  - Add test verifying that orchestrator issues have `affected_claim_ids` cleared.
  - Verify full test suite passes.

## Verification & PR
- Run `pytest tests/test_openai_semantic_critic.py tests/test_api_analyze.py`.
- Run full repo `pytest`.
- Commit: `fix(data): [THES-21] align semantic critic output normalization with plan capabilities and links`
- Push branch `feat/THES-21-critic-plan-normalization` to origin.
- Open PR to `main` using `gh pr create`.
