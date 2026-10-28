# A03 冒烟

日期：2026-10-27

命令（仓库根目录）：

```
uv run python -m alphasentinel.ingestor --tickers AAPL MSFT
```

退出码：0

标准输出末行：

```
[INGESTOR] Successfully ingested 4 company-year financial records into DuckDB.
```

`data/alphasentinel.duckdb` 里 `company_financials` 的行数：4。四行的 `data_source_mode` 都是 `LIVE_HYBRID_SEC_YF`。

| ticker | fiscal_year | filing_form | filing_date |
| --- | --- | --- | --- |
| AAPL | 2024 | 10-K | 2024-11-01 |
| AAPL | 2025 | 10-K | 2025-10-31 |
| MSFT | 2025 | 10-K | 2025-07-30 |
| MSFT | 2026 | 10-K | 2026-07-29 |

同一轮检查：

- `uv run python -m pytest -q`：21 passed
- `uv run ruff check .`：All checks passed

`data/alphasentinel.duckdb` 和 `data/cache/` 不进入提交。
