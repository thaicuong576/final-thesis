# TASK MANIFEST: THES-19

- **Issue**: [THES-19](https://linear.app/eddiephung/issue/THES-19)
- **Role**: Backend Specialist (`worker-api`)
- **Workspace**: `.worktrees/feat-THES-19-writer-exact-numbers`
- **Contracts**:
  - `src/thesis_api/analysis_writer.py`
  - `src/thesis_api/adaptive_runtime.py`
  - `tests/test_api_analyze.py`

## Objective

During live analysis of MBB in 2024_Q4, the specialist presentation writer generated prose with rounded figures (e.g. `1.62%` instead of verbatim `1.6205%`), causing `adaptive_runtime._validate_writer_prose` to raise:
`AnalysisBlocked("analysis_writer_unsupported_number", "The presentation writer introduced a number absent from accepted claim facts.")`

We need a two-pronged solution:
1. **Instruct the writer strictly**: In `src/thesis_api/analysis_writer.py`, instruct the model in `write_specialist()` never to round, abbreviate, or alter numerical values, and to repeat the exact asserted value characters verbatim if mentioning figures.
2. **Accept standard decimal rounding in `_allowed_numbers`**: In `src/thesis_api/adaptive_runtime.py`, in `_allowed_numbers`, permit standard 1-3 decimal place rounded representations of `assertion.asserted_value` so that legitimate rounded presentations (e.g. `1.62%` for `1.6205%`, or `92.25%` for `92.2484%`) are accepted within the claim's allowed numeric scope.

## Implementation Details

### 1. `src/thesis_api/analysis_writer.py`
In `write_specialist()` instructions, add:
```
- NUMERIC CONSTRAINTS FOR PROSE:
  * NEVER invent numbers, counts, rankings, differences, or quantities.
  * If you mention any numeric value from the claim, you MUST write the EXACT asserted value verbatim as provided (e.g. if the value is 1.6205, write '1.6205%', NEVER round to '1.62%' or '1.6%'). Any rounded or altered number risks immediate rejection.
  * When in doubt, describe the metric qualitatively without introducing additional digits.
```

### 2. `src/thesis_api/adaptive_runtime.py`
In `_allowed_numbers(self, claims: Sequence[AtomicClaim]) -> set[str]`:
Expand `allowed` for each `assertion.asserted_value`:
```python
        for claim in claims:
            claim_without_period = _WRITER_PERIOD_LITERAL_RE.sub(" ", claim.claim_text)
            allowed.update(self._numeric_tokens(claim_without_period))
            for assertion in claim.assertions:
                if assertion.asserted_value is not None:
                    allowed.update(self._numeric_tokens(str(assertion.asserted_value)))
                    try:
                        raw_dec = Decimal(str(assertion.asserted_value))
                        for places in (1, 2, 3):
                            allowed.update(self._numeric_tokens(str(round(raw_dec, places).normalize())))
                            allowed.add(f"{raw_dec:.{places}f}")
                    except (InvalidOperation, TypeError):
                        pass
        return allowed
```

### 3. Tests
- In `tests/test_api_analyze.py`:
  - Add test case verifying that prose using a standard 2-decimal rounded version of the asserted value (e.g. `1.62%` when asserted value is `1.6205%`) is accepted by `_validate_writer_prose` and does not trigger `analysis_writer_unsupported_number`.
  - Ensure negative test cases (like `999 percent`, or swapping numbers across different claims) still properly fail as expected.
- Run `pytest tests/test_api_analyze.py tests/test_analysis_writer.py`.
- Run full pytest test suite.

## Verification & PR
- Run all tests to ensure 100% pass.
- Commit: `fix(api): [THES-19] prevent writer unsupported number rejection for rounded metric values`
- Push branch `feat/THES-19-writer-exact-numbers` to origin.
- Open PR to `main` using `gh pr create`.
