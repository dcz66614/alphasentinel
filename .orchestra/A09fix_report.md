# A09fix 流水线

工作目录：`C:\Users\Du200\Projects\alphasentinel-codex`。下面的数字和退出码都来自本次命令输出。`EXIT` 行是外壳在进程结束后追加的。

## 结果

`uv run python -m pytest -q` 退出码 0。`uv run ruff check .` 退出码 0。

`uv run python -u scripts/run_pipeline.py` 退出码 1。十只核心股按 NVDA、MSFT、AAPL、META、GOOGL、AMZN、TSLA、CRM、PLTR、ORCL 联网跑完。META、AMZN、PLTR、ORCL 各记一条失败原因后继续。DuckDB 写入 6 只、12 个公司年度，打分 6 只，并写出 Executive Briefing。失败股票非空，且写入行数低于 10 只 × 2 的门槛，所以进程以 1 退出。没有补零、插值或编造缺失科目。

`uv run python -u scripts/run_pipeline.py --verify-all` 退出码 0。TASK-01 到 TASK-09 的退出码都是 0。账本里 TASK-09 为 PASSED，attempts 1/3。TASK-09 的检查看的是简报文件是否在磁盘上。流水线本身仍是上面的退出码 1。

## 映射修正

对照 `data/cache` 里已下载的 companyfacts，以及 `tests/fixtures/` 里从这些响应裁下的片段（来源写在 `tests/fixtures/README.md`）：

- AMZN 的销售费用行是 `MarketingExpense`，响应里没有 `SellingAndMarketingExpense`，也没有 `SellingGeneralAndAdministrativeExpense`。销售费用别名改为先取合并销售行，没有时再取 `MarketingExpense`，再与 `GeneralAndAdministrativeExpense` 相加。两条销售标签不叠成一笔。本次流水线里 AMZN 的失败字段不再包含 `sga`。
- ORCL 的非流动票据是 `LongTermNotesPayable`，这两期没有 `LongTermDebtNoncurrent`。`long_term_debt` 增加这个 SEC 标签。本次流水线里 ORCL 的失败字段是 `cogs`。
- GOOGL 的 `Revenues` 在 2024-12-31 上只有后一年 10-K 的比较列。同年自己的 10-K 在 `RevenueFromContractWithCustomerExcludingAssessedTax` 上。取值改为优先采用 `fy` 等于期末年份的标签。本次日志里 FY2024 下载的是 `goog-20241231.htm`（路径 `000165204425000014`），FY2025 下载的是 `goog-20251231.htm`（路径 `000165204426000018`）。

CRM 的 FY2025 和 FY2026 都下载了 `000110852426000060/crm-20260131.htm`。同一 `fy` 的多条事实仍取申报日较晚的那条，金额选择规则没有改。

## 仍缺的真实字段

这些字段在对应 companyfacts 里没有可用的 10-K 期末或全年事实。流水线记下原因并跳过该股，不把别的概念填进去。

- META：`CommonStockSharesOutstanding` 不在响应里。保留的加权平均股本是 EPS 的期间数，不用作期末 `shares_outstanding`。失败原因见下方日志。
- AMZN：没有 `ResearchAndDevelopmentExpense`。`Liabilities` 不在响应里，`LiabilitiesNoncurrent` 的 10-K 事实停在 2011。没有用资产减权益去补总负债。
- PLTR：`LongTermDebtNoncurrent` 的 10-K 事实停在 2021-12-31，其中包含 0。2024 与 2025 的 10-K 没有再报这个标签。0 不结转到这两年。经营租赁负债不是长期借款。
- ORCL：`CostOfRevenue` 的 10-K 事实停在 2011。`CostsAndExpenses` 是费用合计，不用差额去反推营业成本。

回归测试在 `tests/test_ingestor.py`，片段为 `meta_companyfacts_excerpt.json`、`amzn_companyfacts_excerpt.json`、`orcl_companyfacts_excerpt.json`、`googl_companyfacts_excerpt.json`、`pltr_companyfacts_excerpt.json`。

## pytest

命令：

```text
uv run python -m pytest -q
```

输出：

```text
..............................................................           [100%]
============================== warnings summary ===============================
.venv\Lib\site-packages\fastapi\testclient.py:1
  C:\Users\Du200\Projects\alphasentinel-codex\.venv\Lib\site-packages\fastapi\testclient.py:1: StarletteDeprecationWarning: Using `httpx` with `starlette.testclient` is deprecated; install `httpx2` instead.
    from starlette.testclient import TestClient as TestClient  # noqa

tests/test_dashboard.py::test_placeholder_database_renders_tables_and_chart
  C:\Users\Du200\Projects\alphasentinel-codex\.venv\Lib\site-packages\streamlit\elements\lib\built_in_chart_utils.py:620: Pandas4Warning: The inplace keyword in DataFrame.reset_index is deprecated and will be removed in a future version (PDEP-8).
  See https://pandas.pydata.org/docs/dev/whatsnew/v3.1.0.html#deprecation-inplace for more details.
    df.reset_index(inplace=True)  # noqa: PD002

-- Docs: https://docs.pytest.org/en/stable/how-to/capture-warnings.html
62 passed, 2 warnings in 13.26s
EXIT 0
```

## ruff

命令：

```text
uv run ruff check .
```

输出。日志里的 `All checks passed!` 带绿色 ANSI 着色：

```text
[1;32mAll checks passed![0m
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
[INGESTOR] META failed: incomplete 10-K periods (2025-12-31: shares_outstanding; 2024-12-31: shares_outstanding)
[INGESTOR] GOOGL: downloading https://data.sec.gov/api/xbrl/companyfacts/CIK0001652044.json
[INGESTOR] GOOGL: downloading https://data.sec.gov/submissions/CIK0001652044.json
[INGESTOR] GOOGL FY2024: downloading https://www.sec.gov/Archives/edgar/data/1652044/000165204425000014/goog-20241231.htm
[INGESTOR] GOOGL FY2024: 177 Form 4 filings
[INGESTOR] GOOGL FY2024: Form 4 25
[INGESTOR] GOOGL FY2024: Form 4 50
[INGESTOR] GOOGL FY2024: Form 4 75
[INGESTOR] GOOGL FY2024: Form 4 100
[INGESTOR] GOOGL FY2024: Form 4 125
[INGESTOR] GOOGL FY2024: Form 4 150
[INGESTOR] GOOGL FY2024: Form 4 175
[INGESTOR] GOOGL FY2024: Form 4 177
[INGESTOR] GOOGL FY2025: downloading https://www.sec.gov/Archives/edgar/data/1652044/000165204426000018/goog-20251231.htm
[INGESTOR] GOOGL FY2025: 173 Form 4 filings
[INGESTOR] GOOGL FY2025: Form 4 25
[INGESTOR] GOOGL FY2025: Form 4 50
[INGESTOR] GOOGL FY2025: Form 4 75
[INGESTOR] GOOGL FY2025: Form 4 100
[INGESTOR] GOOGL FY2025: Form 4 125
[INGESTOR] GOOGL FY2025: Form 4 150
[INGESTOR] GOOGL FY2025: Form 4 173
[INGESTOR] GOOGL: downloading yfinance closes
[INGESTOR] AMZN: downloading https://data.sec.gov/api/xbrl/companyfacts/CIK0001018724.json
[INGESTOR] AMZN failed: incomplete 10-K periods (2025-12-31: rd_expense, total_liabilities; 2024-12-31: rd_expense, total_liabilities)
[INGESTOR] TSLA: downloading https://data.sec.gov/api/xbrl/companyfacts/CIK0001318605.json
[INGESTOR] TSLA: downloading https://data.sec.gov/submissions/CIK0001318605.json
[INGESTOR] TSLA FY2024: downloading https://www.sec.gov/Archives/edgar/data/1318605/000162828025003063/tsla-20241231.htm
[INGESTOR] TSLA FY2024: 24 Form 4 filings
[INGESTOR] TSLA FY2024: Form 4 24
[INGESTOR] TSLA FY2025: downloading https://www.sec.gov/Archives/edgar/data/1318605/000162828026003952/tsla-20251231.htm
[INGESTOR] TSLA FY2025: 40 Form 4 filings
[INGESTOR] TSLA FY2025: Form 4 25
[INGESTOR] TSLA FY2025: Form 4 40
[INGESTOR] TSLA: downloading yfinance closes
[INGESTOR] CRM: downloading https://data.sec.gov/api/xbrl/companyfacts/CIK0001108524.json
[INGESTOR] CRM: downloading https://data.sec.gov/submissions/CIK0001108524.json
[INGESTOR] CRM FY2025: downloading https://www.sec.gov/Archives/edgar/data/1108524/000110852426000060/crm-20260131.htm
[INGESTOR] CRM FY2025: 297 Form 4 filings
[INGESTOR] CRM FY2025: Form 4 25
[INGESTOR] CRM FY2025: Form 4 50
[INGESTOR] CRM FY2025: Form 4 75
[INGESTOR] CRM FY2025: Form 4 100
[INGESTOR] CRM FY2025: Form 4 125
[INGESTOR] CRM FY2025: Form 4 150
[INGESTOR] CRM FY2025: Form 4 175
[INGESTOR] CRM FY2025: Form 4 200
[INGESTOR] CRM FY2025: Form 4 225
[INGESTOR] CRM FY2025: Form 4 250
[INGESTOR] CRM FY2025: Form 4 275
[INGESTOR] CRM FY2025: Form 4 297
[INGESTOR] CRM FY2026: downloading https://www.sec.gov/Archives/edgar/data/1108524/000110852426000060/crm-20260131.htm
[INGESTOR] CRM FY2026: 220 Form 4 filings
[INGESTOR] CRM FY2026: Form 4 25
[INGESTOR] CRM FY2026: Form 4 50
[INGESTOR] CRM FY2026: Form 4 75
[INGESTOR] CRM FY2026: Form 4 100
[INGESTOR] CRM FY2026: Form 4 125
[INGESTOR] CRM FY2026: Form 4 150
[INGESTOR] CRM FY2026: Form 4 175
[INGESTOR] CRM FY2026: Form 4 200
[INGESTOR] CRM FY2026: Form 4 220
[INGESTOR] CRM: downloading yfinance closes
[INGESTOR] PLTR: downloading https://data.sec.gov/api/xbrl/companyfacts/CIK0001321655.json
[INGESTOR] PLTR failed: incomplete 10-K periods (2025-12-31: long_term_debt; 2024-12-31: long_term_debt)
[INGESTOR] ORCL: downloading https://data.sec.gov/api/xbrl/companyfacts/CIK0001341439.json
[INGESTOR] ORCL failed: incomplete 10-K periods (2026-05-31: cogs; 2025-05-31: cogs)
[PIPELINE] ticker_fail META incomplete 10-K periods (2025-12-31: shares_outstanding; 2024-12-31: shares_outstanding)
[PIPELINE] ticker_fail AMZN incomplete 10-K periods (2025-12-31: rd_expense, total_liabilities; 2024-12-31: rd_expense, total_liabilities)
[PIPELINE] ticker_fail PLTR incomplete 10-K periods (2025-12-31: long_term_debt; 2024-12-31: long_term_debt)
[PIPELINE] ticker_fail ORCL incomplete 10-K periods (2026-05-31: cogs; 2025-05-31: cogs)
[PIPELINE] ingested_records=12
[PIPELINE] financial_rows AAPL count=2 years=2024,2025 mode=LIVE_HYBRID_SEC_YF
[PIPELINE] financial_rows CRM count=2 years=2025,2026 mode=LIVE_HYBRID_SEC_YF
[PIPELINE] financial_rows GOOGL count=2 years=2024,2025 mode=LIVE_HYBRID_SEC_YF
[PIPELINE] financial_rows MSFT count=2 years=2025,2026 mode=LIVE_HYBRID_SEC_YF
[PIPELINE] financial_rows NVDA count=2 years=2025,2026 mode=LIVE_HYBRID_SEC_YF
[PIPELINE] financial_rows TSLA count=2 years=2024,2025 mode=LIVE_HYBRID_SEC_YF
[PIPELINE] scored_companies=6
[PIPELINE] nullable_metrics altman_z_score,beneish_m_score,piotroski_f_score,ebit_margin_pct,ebit_margin_yoy_change_bps,revenue_growth_yoy_pct,rd_to_revenue_pct,ai_hype_score,ai_roi_realization_score,ai_washing_score,dsri,gmi,aqi,sgi,depi,sgai,lvgi,tata
[PIPELINE] metric_counts AAPL FY2025 with_value=17 null=1
[PIPELINE] metric_null AAPL piotroski_f_score
[PIPELINE] metric_value AAPL altman_z_score,beneish_m_score,ebit_margin_pct,ebit_margin_yoy_change_bps,revenue_growth_yoy_pct,rd_to_revenue_pct,ai_hype_score,ai_roi_realization_score,ai_washing_score,dsri,gmi,aqi,sgi,depi,sgai,lvgi,tata
[PIPELINE] metric_counts CRM FY2026 with_value=17 null=1
[PIPELINE] metric_null CRM piotroski_f_score
[PIPELINE] metric_value CRM altman_z_score,beneish_m_score,ebit_margin_pct,ebit_margin_yoy_change_bps,revenue_growth_yoy_pct,rd_to_revenue_pct,ai_hype_score,ai_roi_realization_score,ai_washing_score,dsri,gmi,aqi,sgi,depi,sgai,lvgi,tata
[PIPELINE] metric_counts GOOGL FY2025 with_value=17 null=1
[PIPELINE] metric_null GOOGL piotroski_f_score
[PIPELINE] metric_value GOOGL altman_z_score,beneish_m_score,ebit_margin_pct,ebit_margin_yoy_change_bps,revenue_growth_yoy_pct,rd_to_revenue_pct,ai_hype_score,ai_roi_realization_score,ai_washing_score,dsri,gmi,aqi,sgi,depi,sgai,lvgi,tata
[PIPELINE] metric_counts MSFT FY2026 with_value=17 null=1
[PIPELINE] metric_null MSFT piotroski_f_score
[PIPELINE] metric_value MSFT altman_z_score,beneish_m_score,ebit_margin_pct,ebit_margin_yoy_change_bps,revenue_growth_yoy_pct,rd_to_revenue_pct,ai_hype_score,ai_roi_realization_score,ai_washing_score,dsri,gmi,aqi,sgi,depi,sgai,lvgi,tata
[PIPELINE] metric_counts NVDA FY2026 with_value=17 null=1
[PIPELINE] metric_null NVDA piotroski_f_score
[PIPELINE] metric_value NVDA altman_z_score,beneish_m_score,ebit_margin_pct,ebit_margin_yoy_change_bps,revenue_growth_yoy_pct,rd_to_revenue_pct,ai_hype_score,ai_roi_realization_score,ai_washing_score,dsri,gmi,aqi,sgi,depi,sgai,lvgi,tata
[PIPELINE] metric_counts TSLA FY2025 with_value=17 null=1
[PIPELINE] metric_null TSLA piotroski_f_score
[PIPELINE] metric_value TSLA altman_z_score,beneish_m_score,ebit_margin_pct,ebit_margin_yoy_change_bps,revenue_growth_yoy_pct,rd_to_revenue_pct,ai_hype_score,ai_roi_realization_score,ai_washing_score,dsri,gmi,aqi,sgi,depi,sgai,lvgi,tata
[REPORTS] C:\Users\Du200\Projects\alphasentinel-codex\reports\AlphaSentinel_Executive_Briefing.md | C:\Users\Du200\Projects\alphasentinel-codex\reports\AlphaSentinel_Executive_Briefing.docx
[OK] Verified deliverable: C:\Users\Du200\Projects\alphasentinel-codex\deliverables\PROJECT_CHARTER.md (2534 bytes)
[OK] Verified deliverable: C:\Users\Du200\Projects\alphasentinel-codex\deliverables\PROJECT_CHARTER.docx (38415 bytes)
[OK] Verified deliverable: C:\Users\Du200\Projects\alphasentinel-codex\deliverables\AGENT_EXECUTION_PLAN.md (1967 bytes)
[OK] Verified deliverable: C:\Users\Du200\Projects\alphasentinel-codex\deliverables\AGENT_EXECUTION_PLAN.docx (37849 bytes)
[PIPELINE_FAIL] Verification checks did not meet minimum thresholds.
[PIPELINE_FAIL] ingested_records=12 scored_companies=6 deliverables_exit=0 minimum_records=20 failed_tickers=META,AMZN,PLTR,ORCL
EXIT 1
```

## --verify-all

命令：

```text
uv run python -u scripts/run_pipeline.py --verify-all
```

输出：

```text
[VERIFY_ALL] run C:\Users\Du200\Projects\alphasentinel-codex\.venv\Scripts\python.exe C:\Users\Du200\Projects\alphasentinel-codex\scripts\dag_ctl.py verify --task TASK-01
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
[PASSED] TASK-09 verified.
[VERIFY_ALL] TASK-09 exit=0
[VERIFY_ALL] failed=0 passed=9
EXIT 0
```

## 账本

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
TASK-09  |   9 | @CommanderBot      | PASSED   |      1/3 | ["TASK-08"]            | reports/AlphaSentinel_Executive_Briefing.docx
EXIT 0
```
