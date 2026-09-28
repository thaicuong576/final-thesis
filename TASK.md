# TASK Manifest: [THES-15] Parse markdown code-fenced JSON in analysis writer and semantic critic

- **Role**: worker-api
- **Linear Issue**: [THES-15](https://linear.app/eddiephung/issue/THES-15)
- **Worktree**: `D:\eddie-projects\personal-projects\final-thesis\.worktrees\feat-THES-15-parse-fenced-json`
- **Branch**: `feat/THES-15-parse-fenced-json`

## Context & Problem
DeepSeek and other third-party OpenAI-compatible model endpoints often wrap structured JSON responses in markdown code fences, for example:
```json
{
  "claim_texts": [...]
}
```
Currently, in `src/thesis_api/analysis_writer.py` (and similarly in `src/thesis_data/openai_semantic_critic.py`), `output_text` is decoded directly via `json.loads(output_text)` without stripping markdown code fences.
When the response begins with backticks (`` ` ``), `json.loads` raises `json.decoder.JSONDecodeError: Expecting value: line 1 column 1 (char 0)`, which raises `AnalysisWriterError: analysis_writer_json_invalid` and bubbles up to `adaptive_runtime_failure: The accepted provider or bounded semantic runtime could not satisfy this request.`

## Requirements
1. In `src/thesis_api/analysis_writer.py`:
   - Create a clean helper `_clean_json_text(text: str) -> str` that strips leading/trailing markdown fences (e.g., ```` ```json\n...``` ```` or ```` ```\n...``` ````) and leading/trailing whitespace.
   - Apply `_clean_json_text` to `output_text` before calling `json.loads(...)`.
2. In `src/thesis_data/openai_semantic_critic.py`:
   - Also sanitize `output_text` before `json.loads(..., parse_constant=_reject_json_constant)` to safely handle markdown code fences from OpenAI/DeepSeek endpoints.
3. Add Unit Tests:
   - Add unit tests verifying that markdown code-fenced JSON (```` ```json ... ``` ```` and ```` ``` ... ``` ````) parses correctly into dictionary without errors for both writer and critic.
   - Run `pytest` on relevant test files to verify everything passes.
4. Git & PR:
   - Commit changes with message: `fix(api): [THES-15] parse markdown code-fenced JSON in analysis writer and semantic critic`
   - Push to `origin feat/THES-15-parse-fenced-json`
   - Create PR to `main` using `gh pr create`
   - Verify `gh pr checks`
