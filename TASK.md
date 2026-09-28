# TASK MANIFEST: THES-22

- **Issue**: [THES-22](https://linear.app/eddiephung/issue/THES-22)
- **Role**: Backend & Data Specialist (`worker-api` / `worker-data`)
- **Workspace**: `.worktrees/feat-THES-22-synthesis-numeric-robustness`
- **Contracts / Source Files**:
  - `src/thesis_api/analysis_writer.py`
  - `src/thesis_api/adaptive_runtime.py`
  - `src/thesis_data/openai_semantic_critic.py`
  - `tests/test_analysis_writer.py`
  - `tests/test_api_analyze.py`
  - `tests/test_openai_semantic_critic.py`

## Objective

Prevent synthesis and critic failures regarding numeric values:
1. In `src/thesis_api/analysis_writer.py`:
   - In `synthesize()` instructions, explicitly forbid spelling out numbers into words (e.g. 'one', 'two', 'three', 'four', 'five', 'half', 'percent', 'percentage', 'units'). Numbers belong exclusively in structured claims and specialist presentations.
   - Instruct the writer to refuse critique requests that ask to add numbers or metrics to the synthesis.
2. In `src/thesis_api/adaptive_runtime.py`:
   - In `_allowed_numbers(self, claims: Sequence[AtomicClaim]) -> set[str]`, if any assertion metric is `"bank.npl_g35"` (or contains `"g35"`), add `{"3", "4", "5"}` to `allowed` (because models naturally refer to debt groups 3, 4, 5 / nợ nhóm 3, 4, 5).
3. In `src/thesis_data/openai_semantic_critic.py`:
   - In `_CRITIC_INSTRUCTIONS`, instruct the critic that executive synthesis is strictly qualitative and must NEVER contain numbers, digits, or metric values.
   - In `_normalize_critic_output()`, filter out / drop any issue targeting `affected_agent == "orchestrator"` that complains about missing numbers, figures, or metrics in synthesis.

## Verification & PR

- Run `pytest tests/test_analysis_writer.py tests/test_api_analyze.py tests/test_openai_semantic_critic.py`.
- Run full repo `pytest`.
- Commit with conventional commit message:
  `fix(api): [THES-22] enforce qualitative synthesis constraints and loan group numbers in writer and critic`
- Push branch `feat/THES-22-synthesis-numeric-robustness` to origin.
- Open PR to `main` using `gh pr create`.
- Verify remote CI checks pass using `gh pr checks`.
