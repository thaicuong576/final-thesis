# TASK MANIFEST: THES-20

- **Issue**: [THES-20](https://linear.app/eddiephung/issue/THES-20)
- **Role**: Backend Specialist (`worker-api`)
- **Workspace**: `.worktrees/feat-THES-20-synthesis-temporal-causal-constraints`
- **Contracts**:
  - `src/thesis_api/analysis_writer.py`
  - `src/thesis_api/adaptive_runtime.py`
  - `tests/test_analysis_writer.py`

## Objective

During live analysis on Render Staging, the executive synthesis writer generated summary prose containing temporal change words (e.g. `improved`, `increased`, `cải thiện`) or causal words (e.g. `due to`, `because`, `do`), causing `adaptive_runtime._validate_synthesis_prose` to reject the synthesis with:
`AnalysisBlocked("analysis_synthesis_fact_reference_rejected", "The synthesis may not introduce temporal or causal claims in this runtime slice.")`

## Implementation Details

### 1. `src/thesis_api/analysis_writer.py`
In `synthesize()` instructions:
Add explicit negative constraints:
```
- NEVER include temporal change or trend words (do NOT write words like: improve, improved, improves, improving, deteriorate, deteriorated, deteriorates, deteriorating, increase, increased, increases, increasing, decrease, decreased, decreases, decreasing, trend, trending, momentum, rising, fell, falling, decline, declined, declines, declining, growth, grew, shrank, tăng, giảm, cải thiện, xấu đi, xu hướng, tăng trưởng, suy giảm). Describe only the static standing or condition, not changes over time.
- NEVER include causal explanation or attribution words (do NOT write words like: because, due to, driven by, caused by, cause, causes, leads to, resulted from, as a result, do, bởi, vì, nhờ, khiến, dẫn đến). State observations without attributing causal mechanisms.
```

### 2. `tests/test_analysis_writer.py`
Add assertions in `test_analysis_writer.py` verifying that `synthesize()` instructions explicitly forbid temporal change and causal words.

### 3. Verification
- Run `pytest tests/test_analysis_writer.py tests/test_api_analyze.py`.
- Run full repo `pytest`.
- Commit: `fix(api): [THES-20] forbid temporal change and causal words in executive synthesis instructions`
- Push branch `feat/THES-20-synthesis-temporal-causal-constraints` to origin.
- Open PR to `main` using `gh pr create`.
