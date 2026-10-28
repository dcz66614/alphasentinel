# AlphaSentinel

AlphaSentinel is a Python toolkit for forensic accounting and risk screening of public
companies: it gathers SEC filings, normalizes financial statements, scores earnings quality
and distress risk, and compiles the results into reports and a dashboard.

The commands below are the same on Windows PowerShell and Linux bash. Environment-variable
syntax is the only difference. The project requires Python 3.11 or newer and
[uv](https://docs.astral.sh/uv/).

## Install

From the repository root:

```powershell
uv sync
```

```bash
uv sync
```

`uv sync` creates `.venv` and installs the runtime and development dependencies, including
pytest and ruff.

## Checks

```powershell
uv run python -m pytest -q
uv run ruff check .
```

```bash
uv run python -m pytest -q
uv run ruff check .
```

The tests use files under `tests/fixtures/` and temporary databases. They do not need
`data/cache` or a network connection.

## Environment

`SEC_IDENTITY` is the contact string sent to SEC EDGAR. When it is unset, ingestion uses
`alphasentinel-bot@example.com`.

```powershell
$env:SEC_IDENTITY = "Your Name your.email@example.com"
$env:ALPHASENTINEL_DB = "D:\data\alphasentinel.duckdb"
```

```bash
export SEC_IDENTITY="Your Name your.email@example.com"
export ALPHASENTINEL_DB=/var/tmp/alphasentinel.duckdb
```

`ALPHASENTINEL_DB` selects the DuckDB warehouse for the API and the dashboard. The default
path is `data/alphasentinel.duckdb`. The pipeline writes that file unless `--db` is set.

## Data pipeline

Live run of the ten core tickers. This calls SEC EDGAR and Yahoo Finance, fills
`data/cache`, writes the warehouse, writes `reports/AlphaSentinel_Executive_Briefing.md`
and `.docx`, and rebuilds `deliverables/`.

```powershell
uv run python scripts/run_pipeline.py
```

```bash
uv run python scripts/run_pipeline.py
```

Offline run. This reads `data/cache` only. A missing cache file exits 1. `data/cache` is
not in git, so a fresh clone needs one live run before `--offline` can use the default cache.

```powershell
uv run python scripts/run_pipeline.py --offline
```

```bash
uv run python scripts/run_pipeline.py --offline
```

Task gate. This runs `scripts/dag_ctl.py verify` for TASK-01 through TASK-09. If
`reports/AlphaSentinel_Executive_Briefing.md` and `.docx` are not on disk yet, they are
written before the TASK-09 check:

1. From scores already stored in `data/alphasentinel.duckdb`, when that warehouse has rows.
2. Otherwise from `data/cache` offline, when that cache contains the ten core tickers.
3. Otherwise from `tests/fixtures/offline_cache` for AAPL and MSFT only.

That third step uses committed SEC excerpts. It does not call the network and it does not
invent amounts. A briefing file that already exists but is short, or a `.docx` that is not
a zip, is left as it is and the check fails.

```powershell
uv run python scripts/run_pipeline.py --verify-all
```

```bash
uv run python scripts/run_pipeline.py --verify-all
```

`reports/` is runtime output and is gitignored.

## API

```powershell
uv run uvicorn alphasentinel.api_server:app --port 8000
```

```bash
uv run uvicorn alphasentinel.api_server:app --port 8000
```

The server reads `ALPHASENTINEL_DB` or `data/alphasentinel.duckdb`. Endpoints:

- `GET /health`
- `GET /companies`
- `GET /financials/{ticker}`
- `GET /scores/{ticker}`
- `GET /api/v1/scores`
- `GET /api/v1/ticker/{symbol}`

`/api/v1/scores` returns `{"count", "items"}` for every stored `forensic_scores` row, ordered
by `ai_washing_score` descending. NULL scores stay null. `/api/v1/ticker/{symbol}` returns
the latest fiscal year as `forensic_summary` and the financial rows as `financial_history`.
An unknown ticker returns 404.

## Dashboard

```powershell
uv run streamlit run src/alphasentinel/dashboard.py
```

```bash
uv run streamlit run src/alphasentinel/dashboard.py
```

Streamlit serves http://localhost:8501. The page reads the same warehouse as the API. The
top row is four portfolio counts from stored `forensic_scores` rows. A NULL score is not
counted as an alert. Missing table values are shown as 数据不足.

## Deliverables

Check the four institutional files without rewriting them:

```powershell
uv run python scripts/build_four_deliverables.py --verify
```

```bash
uv run python scripts/build_four_deliverables.py --verify
```

Rebuild them in `deliverables/`:

```powershell
uv run python scripts/build_four_deliverables.py
```

```bash
uv run python scripts/build_four_deliverables.py
```
