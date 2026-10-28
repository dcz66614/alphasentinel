# A09 流水线

工作目录：`C:\Users\Du200\Projects\alphasentinel-codex`。下面的数字和退出码都来自本次命令输出。`EXIT` 行是外壳在进程结束后追加的。

## 结果

`uv run python -u scripts/run_pipeline.py` 退出码 1。十只核心股按 NVDA、MSFT、AAPL、META、GOOGL、AMZN、TSLA、CRM、PLTR、ORCL 的顺序下载。META 的 companyfacts 规范化失败，流水线在写入 DuckDB 之前返回。日志里没有 `financial_rows`、`metric_counts`、`ingested_records` 或 `PIPELINE_SUCCESS`。因此这次运行没有每只股票的写入行数，也没有各指标 NULL / 有值计数。

`uv run python -u scripts/run_pipeline.py --verify-all` 退出码 1。TASK-01 到 TASK-08 的退出码都是 0。TASK-09 的退出码是 1，因为 `reports/AlphaSentinel_Executive_Briefing.md` 不存在。账本里 TASK-09 为 FAILED，attempts 1/3。

`uv run python -m pytest -q` 退出码 0，输出 `55 passed, 2 warnings in 12.05s`。`uv run ruff check .` 退出码 0，输出 `All checks passed!`。

## pytest

命令：

```text
uv run python -m pytest -q
```

输出：

```text
.......................................................                  [100%]
============================== warnings summary ===============================
.venv\Lib\site-packages\fastapi\testclient.py:1
  C:\Users\Du200\Projects\alphasentinel-codex\.venv\Lib\site-packages\fastapi\testclient.py:1: StarletteDeprecationWarning: Using `httpx` with `starlette.testclient` is deprecated; install `httpx2` instead.
    from starlette.testclient import TestClient as TestClient  # noqa

tests/test_dashboard.py::test_placeholder_database_renders_tables_and_chart
  C:\Users\Du200\Projects\alphasentinel-codex\.venv\Lib\site-packages\streamlit\elements\lib\built_in_chart_utils.py:620: Pandas4Warning: The inplace keyword in DataFrame.reset_index is deprecated and will be removed in a future version (PDEP-8).
  See https://pandas.pydata.org/docs/dev/whatsnew/v3.1.0.html#deprecation-inplace for more details.
    df.reset_index(inplace=True)  # noqa: PD002

-- Docs: https://docs.pytest.org/en/stable/how-to/capture-warnings.html
55 passed, 2 warnings in 12.05s
EXIT 0
```

## ruff

命令：

```text
uv run ruff check .
```

输出末尾是绿色 ANSI 着色的 `All checks passed!`，随后外壳追加了退出码：

```text
All checks passed!
EXIT 0
```

## 十只股票的联网流水线

命令：

```text
uv run python -u scripts/run_pipeline.py
```

输出：

```text
[PIPELINE] tickers=NVDA,MSFT,AAPL,META,GOOGL,AMZN,TSLA,CRM,PLTR,ORCL offline=false
[INGESTOR] NVDA: downloading https://data.sec.gov/api/xbrl/companyfacts/CIK0001045810.json
[INGESTOR] NVDA: downloading https://data.sec.gov/submissions/CIK0001045810.json
[INGESTOR] NVDA FY2025: downloading https://www.sec.gov/Archives/edgar/data/1045810/000104581025000023/nvda-20250126.htm
[INGESTOR] NVDA FY2025: 116 Form 4 filings
[INGESTOR] NVDA FY2025: Form 4 25
[INGESTOR] NVDA FY2025: Form 4 50
[INGESTOR] NVDA FY2025: Form 4 75
[INGESTOR] NVDA FY2025: Form 4 100
[INGESTOR] NVDA FY2025: Form 4 116
[INGESTOR] NVDA FY2026: downloading https://www.sec.gov/Archives/edgar/data/1045810/000104581026000021/nvda-20260125.htm
[INGESTOR] NVDA FY2026: 121 Form 4 filings
[INGESTOR] NVDA FY2026: Form 4 25
[INGESTOR] NVDA FY2026: Form 4 50
[INGESTOR] NVDA FY2026: Form 4 75
[INGESTOR] NVDA FY2026: Form 4 100
[INGESTOR] NVDA FY2026: Form 4 121
[INGESTOR] NVDA: downloading yfinance closes
[INGESTOR] MSFT: downloading https://data.sec.gov/api/xbrl/companyfacts/CIK0000789019.json
[INGESTOR] MSFT: downloading https://data.sec.gov/submissions/CIK0000789019.json
[INGESTOR] MSFT FY2025: downloading https://www.sec.gov/Archives/edgar/data/789019/000095017025100235/msft-20250630.htm
[INGESTOR] MSFT FY2025: 122 Form 4 filings
[INGESTOR] MSFT FY2025: Form 4 25
[INGESTOR] MSFT FY2025: Form 4 50
[INGESTOR] MSFT FY2025: Form 4 75
[INGESTOR] MSFT FY2025: Form 4 100
[INGESTOR] MSFT FY2025: Form 4 122
[INGESTOR] MSFT FY2026: downloading https://www.sec.gov/Archives/edgar/data/789019/000119312526323660/msft-20260630.htm
[INGESTOR] MSFT FY2026: 128 Form 4 filings
[INGESTOR] MSFT FY2026: Form 4 25
[INGESTOR] MSFT FY2026: Form 4 50
[INGESTOR] MSFT FY2026: Form 4 75
[INGESTOR] MSFT FY2026: Form 4 100
[INGESTOR] MSFT FY2026: Form 4 125
[INGESTOR] MSFT FY2026: Form 4 128
[INGESTOR] MSFT: downloading yfinance closes
[INGESTOR] AAPL: downloading https://data.sec.gov/api/xbrl/companyfacts/CIK0000320193.json
[INGESTOR] AAPL: downloading https://data.sec.gov/submissions/CIK0000320193.json
[INGESTOR] AAPL FY2024: downloading https://www.sec.gov/Archives/edgar/data/320193/000032019324000123/aapl-20240928.htm
[INGESTOR] AAPL FY2024: 52 Form 4 filings
[INGESTOR] AAPL FY2024: Form 4 25
[INGESTOR] AAPL FY2024: Form 4 50
[INGESTOR] AAPL FY2024: Form 4 52
[INGESTOR] AAPL FY2025: downloading https://www.sec.gov/Archives/edgar/data/320193/000032019325000079/aapl-20250927.htm
[INGESTOR] AAPL FY2025: 51 Form 4 filings
[INGESTOR] AAPL FY2025: Form 4 25
[INGESTOR] AAPL FY2025: Form 4 50
[INGESTOR] AAPL FY2025: Form 4 51
[INGESTOR] AAPL: downloading yfinance closes
[INGESTOR] META: downloading https://data.sec.gov/api/xbrl/companyfacts/CIK0001326801.json
[PIPELINE_FAIL] incomplete 10-K periods (2025-12-31: shares_outstanding; 2024-12-31: shares_outstanding)
EXIT 1
```

META 的 companyfacts URL 是 `CIK0001326801`。流水线停在 `shares_outstanding`。现有 ingestor 只认 `us-gaap:CommonStockSharesOutstanding`，缺这个字段就抛 `IngestError`，不把别的股数概念填进去。

这次运行结束后，`data/cache` 目录是：

```text
AAPL index=True companyfacts=True
META index=False companyfacts=True
MSFT index=True companyfacts=True
NVDA index=True companyfacts=True
```

会话开始时缓存里只有 AAPL 和 MSFT。NVDA 在失败前下完并写了 `index.json`。META 只有 `companyfacts.json`，没有 `index.json`。

同一仓库在流水线之前的查询：

```text
FIN [('AAPL', 2), ('MSFT', 2)]
SCORES [('AAPL', 2025), ('MSFT', 2026)]
```

流水线失败之后的查询：

```text
FIN
[('AAPL', 2024, 'LIVE_HYBRID_SEC_YF'), ('AAPL', 2025, 'LIVE_HYBRID_SEC_YF'), ('MSFT', 2025, 'LIVE_HYBRID_SEC_YF'), ('MSFT', 2026, 'LIVE_HYBRID_SEC_YF')]
SCORES
[('AAPL', 2025, 'LIVE_HYBRID_SEC_YF'), ('MSFT', 2026, 'LIVE_HYBRID_SEC_YF')]
```

库里仍然只有 AAPL 和 MSFT。NVDA 已经进了缓存，没有进入这两张表。这两次查询的行是这次流水线开始前就在库里的记录。

## companyfacts 规范化核对

这是另一次命令，用来看现有 `normalize_company_facts` 对十只股票的 SEC companyfacts 能否读完。缓存里已有 `companyfacts.json` 就读缓存，否则下载 SEC companyfacts。它没有调用 `ingest_tickers`，没有写 DuckDB。

命令：

```text
uv run python -u C:\Users\Du200\AppData\Local\Temp\a09_normalize_probe.py
```

输出：

```text
NVDA OK has_CommonStockSharesOutstanding=True years=2025:2025-01-26,2026:2026-01-25 source=data\cache\NVDA\companyfacts.json
MSFT OK has_CommonStockSharesOutstanding=True years=2025:2025-06-30,2026:2026-06-30 source=data\cache\MSFT\companyfacts.json
AAPL OK has_CommonStockSharesOutstanding=True years=2024:2024-09-28,2025:2025-09-27 source=data\cache\AAPL\companyfacts.json
META FAIL has_CommonStockSharesOutstanding=False error=incomplete 10-K periods (2025-12-31: shares_outstanding; 2024-12-31: shares_outstanding) source=data\cache\META\companyfacts.json
DOWNLOAD GOOGL https://data.sec.gov/api/xbrl/companyfacts/CIK0001652044.json
GOOGL OK has_CommonStockSharesOutstanding=True years=2024:2024-12-31,2025:2025-12-31 source=https://data.sec.gov/api/xbrl/companyfacts/CIK0001652044.json
DOWNLOAD AMZN https://data.sec.gov/api/xbrl/companyfacts/CIK0001018724.json
AMZN FAIL has_CommonStockSharesOutstanding=True error=incomplete 10-K periods (2025-12-31: rd_expense, sga, total_liabilities; 2024-12-31: rd_expense, sga, total_liabilities) source=https://data.sec.gov/api/xbrl/companyfacts/CIK0001018724.json
DOWNLOAD TSLA https://data.sec.gov/api/xbrl/companyfacts/CIK0001318605.json
TSLA OK has_CommonStockSharesOutstanding=True years=2024:2024-12-31,2025:2025-12-31 source=https://data.sec.gov/api/xbrl/companyfacts/CIK0001318605.json
DOWNLOAD CRM https://data.sec.gov/api/xbrl/companyfacts/CIK0001108524.json
CRM OK has_CommonStockSharesOutstanding=True years=2025:2025-01-31,2026:2026-01-31 source=https://data.sec.gov/api/xbrl/companyfacts/CIK0001108524.json
DOWNLOAD PLTR https://data.sec.gov/api/xbrl/companyfacts/CIK0001321655.json
PLTR FAIL has_CommonStockSharesOutstanding=True error=incomplete 10-K periods (2025-12-31: long_term_debt; 2024-12-31: long_term_debt) source=https://data.sec.gov/api/xbrl/companyfacts/CIK0001321655.json
DOWNLOAD ORCL https://data.sec.gov/api/xbrl/companyfacts/CIK0001341439.json
ORCL FAIL has_CommonStockSharesOutstanding=True error=incomplete 10-K periods (2026-05-31: cogs, long_term_debt; 2025-05-31: cogs, long_term_debt) source=https://data.sec.gov/api/xbrl/companyfacts/CIK0001341439.json
```

流水线按名单顺序先碰到 META，所以日志停在 META。按这份核对，AMZN、PLTR、ORCL 也会被同一个规范化函数拒绝。没有把缺失字段写成 0，也没有改用加权平均股数。

## --verify-all

命令：

```text
uv run python -u scripts/run_pipeline.py --verify-all
```

输出：

```text
[VERIFY_ALL] run C:\Users\Du200\Projects\alphasentinel-codex\.venv\Scripts\python.exe C:\Users\Du200\Projects\alphasentinel-codex\scripts\dag_ctl.py verify --task TASK-01
[DAG_CTL] Initialized SQLite DAG state ledger at C:\Users\Du200\Projects\alphasentinel-codex\state\dag_state.db
[VERIFYING] TASK-01: python scripts/dag_ctl.py status
[PASSED] TASK-01 verified.
[VERIFY_ALL] TASK-01 exit=0
[VERIFY_ALL] run C:\Users\Du200\Projects\alphasentinel-codex\.venv\Scripts\python.exe C:\Users\Du200\Projects\alphasentinel-codex\scripts\dag_ctl.py verify --task TASK-02
[VERIFYING] TASK-02: python -m pytest -q tests/test_schema.py
[PASSED] TASK-02 verified.
[VERIFY_ALL] TASK-02 exit=0
[VERIFY_ALL] run C:\Users\Du200\Projects\alphasentinel-codex\.venv\Scripts\python.exe C:\Users\Du200\Projects\alphasentinel-codex\scripts\dag_ctl.py verify --task TASK-03
[VERIFYING] TASK-03: python -m pytest -q tests/test_ingestor.py
[PASSED] TASK-03 verified.
[VERIFY_ALL] TASK-03 exit=0
[VERIFY_ALL] run C:\Users\Du200\Projects\alphasentinel-codex\.venv\Scripts\python.exe C:\Users\Du200\Projects\alphasentinel-codex\scripts\dag_ctl.py verify --task TASK-04
[VERIFYING] TASK-04: python -m pytest -q tests/test_forensic.py
[PASSED] TASK-04 verified.
[VERIFY_ALL] TASK-04 exit=0
[VERIFY_ALL] run C:\Users\Du200\Projects\alphasentinel-codex\.venv\Scripts\python.exe C:\Users\Du200\Projects\alphasentinel-codex\scripts\dag_ctl.py verify --task TASK-05
[VERIFYING] TASK-05: python -m pytest -q tests/test_reports.py
[PASSED] TASK-05 verified.
[VERIFY_ALL] TASK-05 exit=0
[VERIFY_ALL] run C:\Users\Du200\Projects\alphasentinel-codex\.venv\Scripts\python.exe C:\Users\Du200\Projects\alphasentinel-codex\scripts\dag_ctl.py verify --task TASK-06
[VERIFYING] TASK-06: python -m pytest -q tests/test_api.py
[PASSED] TASK-06 verified.
[VERIFY_ALL] TASK-06 exit=0
[VERIFY_ALL] run C:\Users\Du200\Projects\alphasentinel-codex\.venv\Scripts\python.exe C:\Users\Du200\Projects\alphasentinel-codex\scripts\dag_ctl.py verify --task TASK-07
[VERIFYING] TASK-07: python -m py_compile src/alphasentinel/dashboard.py
[PASSED] TASK-07 verified.
[VERIFY_ALL] TASK-07 exit=0
[VERIFY_ALL] run C:\Users\Du200\Projects\alphasentinel-codex\.venv\Scripts\python.exe C:\Users\Du200\Projects\alphasentinel-codex\scripts\dag_ctl.py verify --task TASK-08
[VERIFYING] TASK-08: python scripts/build_four_deliverables.py --verify
[PASSED] TASK-08 verified.
[VERIFY_ALL] TASK-08 exit=0
[VERIFY_ALL] run C:\Users\Du200\Projects\alphasentinel-codex\.venv\Scripts\python.exe C:\Users\Du200\Projects\alphasentinel-codex\scripts\dag_ctl.py verify --task TASK-09
[VERIFYING] TASK-09: python scripts/run_pipeline.py --verify-all
[FAILED] TASK-09 failed verification (exit=1).
[VERIFY_ALL] TASK-09 artifact missing or short: C:\Users\Du200\Projects\alphasentinel-codex\reports\AlphaSentinel_Executive_Briefing.md
[VERIFY_ALL] TASK-09 exit=1
[VERIFY_ALL] failed=1 passed=8
[VERIFY_ALL] TASK-09 exit=1
EXIT 1
```

随后的账本：

命令：

```text
uv run python scripts/dag_ctl.py status
```

输出：

```text
TASK_ID  | SEQ | OWNER              | STATUS   | ATTEMPTS | DEPENDS_ON             | ARTIFACT
------------------------------------------------------------------------------------------------------------------------
TASK-01  |   1 | @CommanderBot      | PASSED   |      0/3 | []                     | scripts/dag_ctl.py
TASK-02  |   2 | @SpecArchitectBot  | PASSED   |      0/3 | ["TASK-01"]            | src/alphasentinel/db_schema.py
TASK-03  |   3 | @DataEngineBot     | PASSED   |      0/3 | ["TASK-02"]            | src/alphasentinel/ingestor.py
TASK-04  |   4 | @QuantForensicBot  | PASSED   |      0/3 | ["TASK-03"]            | src/alphasentinel/forensic_engine.py
TASK-05  |   5 | @UIAndReportBot    | PASSED   |      0/3 | ["TASK-04"]            | src/alphasentinel/report_compiler.py
TASK-06  |   6 | @UIAndReportBot    | PASSED   |      0/3 | ["TASK-04"]            | src/alphasentinel/api_server.py
TASK-07  |   7 | @UIAndReportBot    | PASSED   |      0/3 | ["TASK-05","TASK-06"]  | src/alphasentinel/dashboard.py
TASK-08  |   8 | @UIAndReportBot    | PASSED   |      0/3 | ["TASK-07"]            | deliverables/PROJECT_CHARTER.docx
TASK-09  |   9 | @CommanderBot      | FAILED   |      1/3 | ["TASK-08"]            | reports/AlphaSentinel_Executive_Briefing.docx
```

TASK-09 的 `verify_cmd` 仍是 `python scripts/run_pipeline.py --verify-all`。嵌套调用看到 `ALPHASENTINEL_VERIFY_ALL_CHILD=1` 后只检查简报文件，避免再次走进 TASK-01..09。这次简报不存在，所以返回 1。Windows 上 TASK-01 到 TASK-08 的 `python` 命令都由本次 `uv run` 的虚拟环境解释器执行并通过。

## 测试覆盖

`tests/test_pipeline.py` 用 `tests/fixtures/offline_cache` 和 tempfile 跑 AAPL、MSFT 的离线编排，并挡住下载函数。`--verify-all` 的顺序用假的子进程检查，不联网，也不跑 TEST 集。

## 未提交

`data/`、`state/`、`reports/` 和本报告不进入提交。数据库和简报都没有由这次十只股票的流水线生成。
