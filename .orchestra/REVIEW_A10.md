A10 review

Reviewed worktree: C:\Users\Du200\Projects\alphasentinel\.orchestra\review_A10
Spec sources: docs\spec\AlphaSentinel_方案全文.txt and A09fix_report.md

Findings
- META: `shares_outstanding` remains NULL because the SEC response has no period-end share count and the EPS weighted-average shares are not a substitute.
- AMZN: `rd_expense` remains NULL because `ResearchAndDevelopmentExpense` is absent; `total_liabilities` is derived only as `Assets - StockholdersEquity` on the same own-year 10-K period and clearly marked derived. No zero-fill or interpolation is used.
- PLTR: `long_term_debt` remains NULL because the tag is absent from the 2024/2025 10-Ks and the older 2021 zero is not reused.
- ORCL: `cogs` remains NULL because the companyfacts response has no later cost-of-revenue fact and `CostsAndExpenses` is not a substitute.
- GOOGL: the normalizer correctly prefers the own-year 10-K tag over the comparative revenue line in the later filing.
- Real SEC snippets and regression fixtures are included in tests/fixtures/README.md and the fixture JSON files.

Validation
- `cd C:\Users\Du200\Projects\alphasentinel\.orchestra\review_A10; uv run python -m pytest -q`
  Result: `63 passed, 2 warnings in 12.11s`
- `cd C:\Users\Du200\Projects\alphasentinel\.orchestra\review_A10; uv run ruff check .`
  Result: `All checks passed!`

VERDICT: PASS - real SEC sourcing, explicit NULL handling, no fabricated values, fixture-backed regressions, and both pytest and ruff pass.
