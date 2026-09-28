# TASK Manifest: [THES-16] Instruct presentation writer and synthesis on negative period and numeral constraints

- **Role**: worker-api
- **Linear Issue**: [THES-16](https://linear.app/eddiephung/issue/THES-16)
- **Worktree**: `D:\eddie-projects\personal-projects\final-thesis\.worktrees\feat-THES-16-writer-prompt-constraints`
- **Branch**: `feat/THES-16-writer-prompt-constraints`

## Problem & Context
In `adaptive_runtime.py`:
1. `_validate_writer_prose` checks `_WRITER_PERIOD_LITERAL_RE` and `_WRITER_PERIOD_WORD_RE`. If any year, quarter, or period word appears in specialist claim prose, it raises `AnalysisBlocked("analysis_writer_period_reference_rejected", "The presentation writer may not add or restate period labels.")`.
2. `_validate_synthesis_prose` checks `validate_synthesis_summary(clean)`. If any digits, numbers, or spelled-out number words appear in executive synthesis summary prose, it raises `AnalysisBlocked("analysis_synthesis_fact_reference_rejected", "The synthesis must not introduce numeric or period claims in this runtime slice.")`.

Currently in `src/thesis_api/analysis_writer.py`:
- `write_specialist()` instructions do not explicitly warn the model to NEVER mention year/quarter/period words in prose.
- `synthesize()` instructions do not explicitly warn the model that the summary is purely qualitative and must NEVER contain any digits, numbers, or number words.

## Requirements
In `src/thesis_api/analysis_writer.py`:
1. In `write_specialist()`:
   Update `instructions` to:
   ```python
            instructions=(
                "You are a specialist presentation writer. Use only the supplied frozen plan, accepted claims, "
                "and observations. Write concise grounded prose for each exact claim_id. Do not change facts, "
                "scope, uncertainty, limitations, or provenance. Do not add causal conclusions, external facts, "
                "source IDs, or numerical values that are absent from the supplied claim. Address the selected "
                "critique descriptions and required actions when present. Return every requested claim exactly once.\n\n"
                "CRITICAL CONSTRAINTS FOR PROSE:\n"
                "- NEVER mention any year (such as 2024), quarter (such as Q4, quý 4, fourth quarter), or period words in the 'prose' field. The period is bound at the report level; any period mention will cause an immediate validation failure.\n"
                "- Write narrative focus solely on the entity, metric concept, and asserted value without period words.\n\n"
                "CRITICAL OUTPUT FORMAT: You must output ONLY a valid JSON object with the root key 'claim_texts'. "
                "Schema: {\"claim_texts\": [{\"claim_id\": \"exact_claim_id\", \"prose\": \"grounded narrative with NO period words\", \"supporting_claim_ids\": [\"exact_claim_id\"]}]}"
            ),
   ```
2. In `synthesize()`:
   Update `instructions` to:
   ```python
            instructions=(
                "You are an executive synthesis writer. Summarize only the supplied claims into concise qualitative overview prose. "
                "Do not introduce external facts, causal conclusions, or claims absent from the supplied list. "
                "Cite every supporting claim ID exactly as provided.\n\n"
                "CRITICAL NEGATIVE CONSTRAINTS FOR SUMMARY:\n"
                "- You must write a strictly QUALITATIVE executive summary.\n"
                "- NEVER include digits, numbers, or spelled-out number words (do NOT write digits like 1.5, or words like one, two, half, percent, percentage, etc.).\n"
                "- NEVER write any years, quarters, dates, or period labels.\n"
                "- Describe the business insights qualitatively (e.g. credit quality health, provisioning discipline, profitability dynamics) without any quantitative words or numbers.\n\n"
                "CRITICAL OUTPUT FORMAT: You must output ONLY a valid JSON object with keys 'summary' and 'supporting_claim_ids'. "
                "Schema: {\"summary\": \"qualitative executive overview without numbers or period labels\", \"supporting_claim_ids\": [\"claim_id_1\", ...]}"
            ),
   ```
3. Test & Verification:
   - Run `python -m pytest tests/test_analysis_writer.py tests/test_api_analyze.py` with `PYTHONPATH=src`.
   - Ensure all tests pass.
4. Git & PR:
   - Commit: `fix(api): [THES-16] enforce negative constraints for period and numeral words in writer prompts`
   - Push to `origin feat/THES-16-writer-prompt-constraints`
   - Open PR to `main` via `gh pr create`
