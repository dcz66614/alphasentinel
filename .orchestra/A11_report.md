# A11 final review fixes

Working tree: `C:\Users\Du200\Projects\alphasentinel-codex`, branch `codex`.
Scope: Gemini final review section 5, items MAJOR-01, MAJOR-02, MAJOR-03, MINOR-01, MINOR-03.
MINOR-02 (third-party deprecation warnings) was not in this task and was left unchanged.

## MAJOR-01 README install and run guide

`README.md` now documents Windows PowerShell and Linux bash for:

- `uv sync`
- `uv run python -m pytest -q`
- `uv run ruff check .`
- `uv run python scripts/run_pipeline.py`
- `uv run python scripts/run_pipeline.py --offline`
- `uv run python scripts/run_pipeline.py --verify-all`
- `uv run uvicorn alphasentinel.api_server:app --port 8000`
- `uv run streamlit run src/alphasentinel/dashboard.py`
- `uv run python scripts/build_four_deliverables.py --verify`
- `uv run python scripts/build_four_deliverables.py`
- `SEC_IDENTITY` and `ALPHASENTINEL_DB`

Commands that were run in this session:

- `uv sync` exited 0 (86 packages resolved, 84 already installed).
- `uv run python scripts/run_pipeline.py --help` exited 0 and lists `--offline` and `--verify-all`.
- `uv run python scripts/run_pipeline.py --offline --tickers AAPL` with a temporary `--db`, `--reports-dir`, and `--deliverables-dir` exited 0. It read `data/cache`, wrote 2 AAPL rows, and printed `[PIPELINE_SUCCESS]`.
- `uv run python scripts/run_pipeline.py --verify-all` exited 0. Summary: `[VERIFY_ALL] failed=0 passed=9`.
- With `reports/` moved aside and `ALPHASENTINEL_VERIFY_ALL_CHILD=1`, `uv run python scripts/run_pipeline.py --verify-all` exited 0. It compiled the briefing from `data/alphasentinel.duckdb` and printed `TASK-09 artifact present`. The original `reports/` directory was moved back.
- `uv run python scripts/build_four_deliverables.py --verify` exited 0 for all four files. The in-repo deliverables were not rebuilt.
- `uv run uvicorn alphasentinel.api_server:app --port 8000` started. `GET /health` returned ok. `GET /api/v1/scores` returned `count` 10. Null fields in that payload were `altman_z_score`, `beneish_m_score`, `gmi`, `lvgi`, `piotroski_f_score`, `rd_to_revenue_pct`. `GET /api/v1/ticker/aapl` returned ticker `AAPL` and financial years 2024, 2025. `GET /financials/AAPL` and `GET /scores/AAPL` returned 200. `GET /api/v1/ticker/NOTREAL` returned 404.
- `uv run streamlit run src/alphasentinel/dashboard.py --server.port 8501` started. `GET /_stcore/health` returned `ok` and `GET /` returned 200. The Streamlit shell HTML does not include widget text. The four KPI cards were checked with `AppTest` in `tests/test_dashboard.py`. No browser tool was available.

The default live command `uv run python scripts/run_pipeline.py` (all ten tickers, network) was not re-run here. That invocation rewrites `deliverables/` and calls SEC EDGAR and Yahoo Finance. The same `run_pipeline` function is what `--offline` ran.

## MAJOR-02 briefing_ready on a fresh clone

`scripts/run_pipeline.py` `briefing_ready()` used to fail when `reports/AlphaSentinel_Executive_Briefing.md` and `.docx` were absent. Those files are runtime output.

If both files are absent, the check now builds them and then validates them:

1. Compile from `data/alphasentinel.duckdb` when `forensic_scores` has rows.
2. Otherwise run the offline pipeline into a temporary warehouse from `data/cache` when that cache has the ten core tickers.
3. Otherwise build AAPL and MSFT from `tests/fixtures/offline_cache`.

No network call is added on that path. Amounts come from the warehouse or from committed SEC excerpts. A file that is already present but short, or a `.docx` that is not a zip, is left unchanged and the check still fails.

Tests: `test_missing_briefing_is_built_from_offline_fixtures`, `test_invalid_briefing_is_not_replaced`, `test_nested_verify_all_checks_the_briefing`.

## MAJOR-03 spec REST routes

`src/alphasentinel/api_server.py` keeps `GET /health`, `GET /companies`, `GET /financials/{ticker}`, and `GET /scores/{ticker}`.

Added:

- `GET /api/v1/scores` returns `{"count", "items"}` from `forensic_scores`, ordered by `ai_washing_score` descending. SQL NULL stays JSON null.
- `GET /api/v1/ticker/{symbol}` returns `ticker`, `forensic_summary` (latest `fiscal_year`), and `financial_history`. Unknown tickers return 404 with `Ticker {SYMBOL} not found in warehouse.`

Tests: extended `test_health_and_empty_tables` and `test_placeholder_rows_round_trip`, plus `test_spec_routes_keep_nulls_and_latest_year`.

## MINOR-01 portfolio KPI cards

`src/alphasentinel/dashboard.py` renders four cards at the top when `forensic_scores` has rows:

- Monitored Equities: number of stored score rows
- Verified AI-ROI Leaders: rows whose `ai_washing_status` is `VERIFIED_AI_ROI`
- AI-Washing / Watch Alerts: rows whose `ai_washing_score` is at least 35
- High Manipulation Risk (M > -1.78): rows whose `beneish_m_score` is greater than -1.78

NULL scores are not counted as alerts. An empty warehouse still shows `无数据` and no cards.

Tests: `test_empty_database_shows_no_data`, `test_placeholder_database_renders_tables_and_chart`, `test_portfolio_kpis_ignore_null_scores`.

## MINOR-03 gitignore

`.gitignore` now includes `reports/`.

## Files changed

- `.gitignore`
- `README.md`
- `scripts/run_pipeline.py`
- `src/alphasentinel/api_server.py`
- `src/alphasentinel/dashboard.py`
- `tests/test_api.py`
- `tests/test_dashboard.py`
- `tests/test_pipeline.py`

Not committed: this report, `reports/`, and the pre-existing `deliverables/*.docx` working-tree changes.

## pytest

Command: `uv run python -m pytest -q`

Exit code: 0

```text
...................................................................      [100%]
============================== warnings summary ===============================
.venv\Lib\site-packages\fastapi\testclient.py:1
  C:\Users\Du200\Projects\alphasentinel-codex\.venv\Lib\site-packages\fastapi\testclient.py:1: StarletteDeprecationWarning: Using `httpx` with `starlette.testclient` is deprecated; install `httpx2` instead.
    from starlette.testclient import TestClient as TestClient  # noqa

tests/test_dashboard.py::test_placeholder_database_renders_tables_and_chart
tests/test_dashboard.py::test_portfolio_kpis_ignore_null_scores
  C:\Users\Du200\Projects\alphasentinel-codex\.venv\Lib\site-packages\streamlit\elements\lib\built_in_chart_utils.py:620: Pandas4Warning: The inplace keyword in DataFrame.reset_index is deprecated and will be removed in a future version (PDEP-8).
  See https://pandas.pydata.org/docs/dev/whatsnew/v3.1.0.html#deprecation-inplace for more details.
    df.reset_index(inplace=True)  # noqa: PD002

-- Docs: https://docs.pytest.org/en/stable/how-to/capture-warnings.html
67 passed, 3 warnings in 14.23s
```

## ruff

Command: `uv run ruff check .`

Exit code: 0

```text
All checks passed!
```
