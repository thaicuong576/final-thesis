# TASK Manifest: [THES-17] Forbid entity tickers and metric acronyms in executive synthesis instructions

- **Role**: worker-api
- **Linear Issue**: [THES-17](https://linear.app/eddiephung/issue/THES-17)
- **Worktree**: `D:\eddie-projects\personal-projects\final-thesis\.worktrees\feat-THES-17-synthesis-entity-constraints`
- **Branch**: `feat/THES-17-synthesis-entity-constraints`

## Problem & Context
In `adaptive_runtime.py`, `_validate_synthesis_prose` enforces that for single-period reports:
- The synthesis summary is rendered from accepted specialist prose and cannot introduce entity or metric claims.
- If any entity ticker (e.g. `MBB`, `VCB`, `ACB`, `TCB`, `VPB`) or metric acronym (e.g. `NPL`, `ROE`, `ROA`, `LLR`) appears in the `summary`, it triggers `AnalysisBlocked("analysis_synthesis_fact_reference_rejected", "The report-level synthesis is rendered from accepted specialist prose and cannot introduce entity claims.")`.

Currently in `src/thesis_api/analysis_writer.py`, `synthesize()` instructions do not explicitly warn the model to omit specific ticker symbols and metric acronyms.

## Requirements
In `src/thesis_api/analysis_writer.py`:
In `synthesize()`:
Update `instructions` to:
```python
            instructions=(
                "You are an executive synthesis writer. Summarize the specialist findings into a concise qualitative overview.\n\n"
                "CRITICAL CONSTRAINTS FOR SUMMARY:\n"
                "- You must write a strictly QUALITATIVE executive summary.\n"
                "- NEVER include any ticker symbols (e.g., do NOT write MBB, VCB, ACB, TCB, VPB) or metric acronyms (do NOT write NPL, ROE, ROA, LLR). Use general descriptive terms such as 'the institution', 'credit quality', 'asset health', 'earnings profile'.\n"
                "- NEVER include digits, numbers, or spelled-out number words (do NOT write digits like 1.5, or words like one, two, half, percent, percentage, etc.).\n"
                "- NEVER write any years, quarters, dates, or period labels.\n\n"
                "CRITICAL OUTPUT FORMAT: You must output ONLY a valid JSON object with keys 'summary' and 'supporting_claim_ids'. "
                "Schema: {\"summary\": \"qualitative executive overview\", \"supporting_claim_ids\": [\"claim_id_1\", ...]}"
            ),
```

## Verification & Git
1. Run `python -m pytest tests/test_analysis_writer.py tests/test_api_analyze.py`.
2. Commit: `fix(api): [THES-17] forbid entity tickers and metric acronyms in executive synthesis instructions`
3. Push to `origin feat/THES-17-synthesis-entity-constraints`
4. Open PR via `gh pr create`
