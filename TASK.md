# TASK MANIFEST: THES-18

- **Issue**: [THES-18](https://linear.app/eddiephung/issue/THES-18)
- **Role**: Backend & Data Specialist (`worker-api` / `worker-data`)
- **Workspace**: `.worktrees/feat-THES-18-critic-schema-robustness`
- **Contracts**:
  - `src/thesis_data/semantic_evaluation.py` (`StructuredCriticResult`, `FROZEN_SEMANTIC_DIMENSIONS`, `STRUCTURED_CRITIC_RESULT_VERSION`)
  - `src/thesis_data/openai_semantic_critic.py`

## Objective

When running live analysis against the DeepSeek proxy endpoint, the model ignores the `json_schema` BNF grammar in `responses.create` and produces alternative JSON keys (e.g. `issues`, `requirement_results`, `link_results`, omitting `contract_version` and `dimension_scores`), causing 8 Pydantic validation errors when `StructuredCriticResult.model_validate(decoded)` runs.

We need to:
1. Provide an explicit JSON output structure directly in `_CRITIC_INSTRUCTIONS` in `src/thesis_data/openai_semantic_critic.py`.
2. Add a robust normalizer function `_normalize_critic_output(decoded: dict[str, Any], evaluator_version: str) -> dict[str, Any]` in `src/thesis_data/openai_semantic_critic.py` before `StructuredCriticResult.model_validate(normalized)` is called.
3. Add unit tests verifying both standard and alternative model JSON responses are cleanly parsed and validated into `StructuredCriticResult`.

## Implementation Details

### 1. Update `_CRITIC_INSTRUCTIONS` in `src/thesis_data/openai_semantic_critic.py`
Add explicit JSON output format guidance:
```
Your JSON output MUST have the following top-level keys:
- "contract_version": "structured-critic-result-v1"
- "evaluator_version": "<evaluator_version>"
- "dimension_scores": array of objects, one for each of the 6 frozen dimensions:
  ["factual_accuracy", "scope_completeness", "logical_coherence", "synthesis_integration", "constraint_adherence", "source_grounding"]
  Each dimension object has:
  {"dimension": "<name>", "score": 1.0, "status": "pass", "rationale": "...", "supporting_claim_ids": [], "affected_requirement_ids": [], "issue_ids": []}
- "critique_issues": array of objects (if any issues found)
  Each issue object has:
  {"issue_id": "...", "affected_agent": "...", "status": "OPEN", "severity": "...", "rationale": "...", "affected_requirement_ids": [], "affected_claim_ids": [], "target_id": "...", "required_action": "..."}
- "fulfilled_requirement_ids": array of requirement ID strings
- "partially_fulfilled_requirement_ids": array of requirement ID strings
- "unfulfilled_requirement_ids": array of requirement ID strings
- "applicable_link_results": array of link result objects
  Each link object has:
  {"link_id": "...", "score": 1.0, "rationale": "...", "supporting_claim_ids": [], "issue_ids": []}
```

### 2. Implement Normalization in `_normalize_critic_output`
In `src/thesis_data/openai_semantic_critic.py`:
- Map `contract_version` -> default `STRUCTURED_CRITIC_RESULT_VERSION`
- Map `evaluator_version` -> default `evaluator_version` passed in
- Handle `critique_issues`: if `critique_issues` is missing, check `issues`. Ensure each issue has required fields (`issue_id`, `affected_agent`, `status`, `severity`, `rationale`, `affected_requirement_ids`, `affected_claim_ids`, `target_id`, `required_action`).
- Handle `requirement_results`: if the model returns `requirement_results: [{"requirement_id": "...", "status": "fulfilled"|"partially_fulfilled"|"unfulfilled"}]`, populate `fulfilled_requirement_ids`, `partially_fulfilled_requirement_ids`, `unfulfilled_requirement_ids`.
- Handle `dimension_scores`: ensure all 6 frozen dimensions exist. If any dimension is missing from `dimension_scores`, add it with default score `1.0`, status `"pass"`, rationale `"Evaluated by model."`, empty lists for `supporting_claim_ids`, `affected_requirement_ids`, `issue_ids`.
- Handle `applicable_link_results`: if missing, check `link_results`.

### 3. Testing
- In `tests/test_openai_semantic_critic.py`:
  - Add test for `_normalize_critic_output` with alternative model keys (e.g. `issues`, missing contract/evaluator version).
  - Verify `evaluate()` successfully returns `StructuredCriticResult` without validation error.
- Run `pytest tests/test_openai_semantic_critic.py tests/test_phase3bd_openai_semantic_critic.py tests/test_api_analyze.py`.

## Verification & PR
- Run all tests to ensure 100% pass.
- Commit: `fix(data): [THES-18] enforce explicit schema prompt and normalize model output in OpenAISemanticCritic`
- Push branch `feat/THES-18-critic-schema-robustness` to origin.
- Open PR to `main` using `gh pr create`.
