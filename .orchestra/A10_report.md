# A10 流水线

工作目录：`C:\Users\Du200\Projects\alphasentinel-codex`。对照只读参考：`C:\Users\Du200\Projects\alphasentinel\.orchestra\A09fix_report.md`。下面的数字和退出码都来自本次命令输出。`pytest` 与 `ruff` 的命令本身不打印 `EXIT`；进程退出码是 0。流水线、`--verify-all` 和 `dag_ctl.py status` 的 `EXIT` 行是外壳在进程结束后追加的。`ruff` 这次捕获到的 stdout 没有 ANSI 着色。

没有编造金额，没有插值，没有把以前年度的 0 结转到后面的年度。没有跑 TEST 集。

## 结果

`uv run python -m pytest -q` 退出码 0：63 passed，2 warnings。`uv run ruff check .` 退出码 0。

`uv run python -u scripts/run_pipeline.py` 退出码 0。十只核心股按 NVDA、MSFT、AAPL、META、GOOGL、AMZN、TSLA、CRM、PLTR、ORCL 联网跑完。`ingested_records=20`，十只都是 `count=2`、`mode=LIVE_HYBRID_SEC_YF`，`scored_companies=10`。日志里没有失败股票。`[PIPELINE_SUCCESS] Ingested 20 records, scored 10 companies.`

`uv run python -u scripts/run_pipeline.py --verify-all` 退出码 0。TASK-01 到 TASK-09 的退出码都是 0。`[VERIFY_ALL] failed=0 passed=9`。TASK-09 的检查在子进程里只看简报文件是否在磁盘上。`uv run python scripts/dag_ctl.py status` 退出码 0。TASK-01 到 TASK-09 都是 PASSED。TASK-09 为 attempts 1/3，产物 `reports/AlphaSentinel_Executive_Briefing.docx`。其余任务 attempts 0/3。

## 缺口处理

数据来自 `data/cache` 里的 SEC companyfacts。片段与来源 URL 写在 `tests/fixtures/README.md`。金额从响应里复制，没有手敲。

### META `shares_outstanding`：NULL

us-gaap 里没有 `CommonStockSharesOutstanding`。dei 里没有 `EntityCommonStockSharesOutstanding`，有的是 `EntityPublicFloat`：

- end 2024-06-30，val 1103000000000，accn 0001326801-25-000017，fy 2024，filed 2025-01-30
- end 2025-06-30，val 1600000000000，accn 0001628280-26-003942，fy 2025，filed 2026-01-29

这两天不是 2024-12-31 和 2025-12-31。`WeightedAverageNumberOfSharesOutstandingBasic` 是 EPS 的期间加权股数，不用作期末股本。两期 `shares_outstanding` 与 `market_cap` 为 NULL。`Liabilities` 有报告，`total_liabilities` 不是 derived。

### AMZN `rd_expense`：NULL；`total_liabilities`：derived

响应里没有 `ResearchAndDevelopmentExpense`。概念名和 label 里没有 Technology、Fulfillment、infrastructure。没有用 `CostsAndExpenses` 减去营业成本、销售费用和管理费用去倒推研发。`rd_expense` 为 NULL。

`Liabilities` 不在响应里。`LiabilitiesNoncurrent` 的 10-K 停在 2011。同年自己的 10-K 上，`Assets` 和 `StockholdersEquity` 都有，且 `LiabilitiesAndStockholdersEquity` 等于 `Assets`。没有 `StockholdersEquityIncludingPortionAttributableToNoncontrollingInterest`，也没有 `MinorityInterest` 余额。名称里带 minority 或 noncontrolling 的只有利润表科目 `IncomeLossFromContinuingOperationsBeforeIncomeTaxesMinorityInterestAndIncomeLossFromEquityMethodInvestments`，不是权益余额。

代码注释写的是 `derived: total liabilities = total assets - stockholders' equity`。只用 `fy` 等于期末年份的事实。流动负债加非流动负债仍是两条已报告科目相加，不标 derived。

- 2024-12-31，accn 0001018724-25-000004，fy 2024：Assets 624894000000 − StockholdersEquity 285970000000 = 338924000000。`LiabilitiesAndStockholdersEquity` 同为 624894000000。
- 2025-12-31，accn 0001018724-26-000004，fy 2025：Assets 818042000000 − StockholdersEquity 411065000000 = 406977000000。`LiabilitiesAndStockholdersEquity` 同为 818042000000。

内存记录的 `derived_fields` 为 `("total_liabilities",)`。这不是数据库列。后一年 10-K 里重复的 2024-12-31 比较列（fy 2025，金额相同）没有拿来推导。`StockholdersEquity` 的 SEC label 是 Stockholders' Equity Attributable to Parent。

股本仍是 us-gaap `CommonStockSharesOutstanding`：2024-12-31 为 10593000000，2025-12-31 为 10731000000。dei `EntityCommonStockSharesOutstanding` 的 end 是封面日 2025-01-29（val 10597729352，accn 0001018724-25-000004）和 2026-01-28（val 10734920870，accn 0001018724-26-000004），不是资产负债表日，没有使用。代码只在 dei 事实的 end 等于该期期末、且 `fy` 等于期末年份时才接受它。这十只的 dei 封面日都不是资产负债表日，所以这条别名没有改动原先已经入库的六只。

### PLTR `long_term_debt`：NULL

`LongTermDebtNoncurrent` 的 10-K 停在 2021-12-31，val 0，accn 0001193125-22-050913。2024 与 2025 没有再报这个标签，也没有另一条长期借款 0。这个 0 不结转。这两期没有 `LongTermDebt`、`LongTermDebtCurrent`、`LongTermNotesPayable`、`DebtCurrent`。`OperatingLeaseLiabilityNoncurrent` 是经营租赁：2024-12-31 val 195226000，2025-12-31 val 183474000（accn 0001321655-26-000011）。不记作长期借款。`long_term_debt` 为 NULL。`Liabilities` 有报告，总负债不是 derived。

### ORCL `cogs`：NULL

`CostOfRevenue` 的 10-K 停在 2011-05-31。没有 `CostOfGoodsAndServicesSold`，也没有 `CostOfGoodsSold`。`CostsAndExpenses` 的 label 是费用合计。FY2026，accn 0001193125-26-277521，end 2026-05-31：`Revenues` 与 `RevenueFromContractWithCustomerExcludingAssessedTax` 都是 67357000000，`CostsAndExpenses` 46751000000，`OperatingIncomeLoss` 20606000000。67357000000 − 46751000000 = 20606000000。同年 `ResearchAndDevelopmentExpense` 10272000000，`SellingAndMarketingExpense` 8331000000，`GeneralAndAdministrativeExpense` 1618000000。FY2025 的 `CostsAndExpenses` 为 39721000000，accn 0000950170-25-087926。没有用费用合计减去其他费用去倒推营业成本。`cogs` 为 NULL，不在 `derived_fields` 里。

`long_term_debt` 仍是 A09 已接上的 `LongTermNotesPayable`，两年都大于 0。`LongTermDebt` 只有一条 2022-05-31 的 0，不结转。总负债来自 `LiabilitiesCurrent` 加 `LiabilitiesNoncurrent`，不是 derived。

### 其余六只

改映射之前对缓存做了 normalize 快照。改完后同一脚本对比，NVDA、MSFT、AAPL、GOOGL、TSLA、CRM 都打印 `same`，`derived_fields` 为两个空元组。股本仍是改前的 us-gaap 期末数：NVDA 24477000000 / 24304000000，MSFT 7434000000 / 7427000000，AAPL 15116786000 / 14773260000，GOOGL 12211000000 / 12088000000，TSLA 3216000000 / 3751000000，CRM 962000000 / 929000000。输出见下方「改前改后对照」。

### 缺了不让整只失败

`cogs`、`rd_expense`、`long_term_debt`、`total_liabilities`、`shares_outstanding` 未报告、且不能按上面的恒等式得到时写入 NULL，该股继续。其它缺概念仍使该期失败。`test_missing_concept_is_not_zero_filled` 删掉 `OperatingIncomeLoss` 后仍因缺少 ebit 抛出 `IngestError`。选中的事实如果值是 0，仍存 0。没有选中的旧 0 不结转。股本为 NULL 时 `market_cap` 为 NULL。`derived_fields` 只在内存记录里，插入时不写库。

已有仓库的 `CREATE TABLE IF NOT EXISTS` 不会改掉旧的 NOT NULL。`init_db` 对 `company_financials` 的 `cogs`、`rd_expense`、`long_term_debt`、`total_liabilities`、`shares_outstanding`、`market_cap`，以及原先可空的 forensic 列，执行 DROP NOT NULL。身份列保持 NOT NULL。

### 打分

打分规则没有改。日志里的 NULL 是原有公式在输入缺失时的结果。

- 每只最新年度的 `piotroski_f_score` 都是 NULL。`compute_piotroski_f` 在没有再前一年（t−2）时返回 NULL。流水线每只只保留两个会计年度，所以财务行没有变化的六只也是这个 NULL。
- META FY2025 另有 `altman_z_score` NULL。Altman 需要 `market_cap`。股本缺失时市值为空。
- AMZN FY2025 另有 `rd_to_revenue_pct` NULL，因为 `rd_expense` 为空。Altman 有值。
- PLTR FY2025 另有 `beneish_m_score` 与 `lvgi` NULL。LVGI 需要 `long_term_debt`。Beneish 在任一组成比率缺失时整分 NULL。
- ORCL FY2026 另有 `beneish_m_score` 与 `gmi` NULL。GMI 需要 `cogs`。

十只都写入了分数行。

### 回归

META、AMZN、ORCL 的片段增加了上面用到的真实事实。PLTR 片段里原有的 2021 年 0 和经营租赁已经够用，文件没有改。流水线重新下载 companyfacts 之后，对照脚本对裁进片段的事实逐条匹配，缺失条数都是 0。

测试：`test_meta_shares_outstanding_is_not_the_weighted_average`，`test_amzn_sga_uses_marketing_expense`（同测 derived 总负债、rd 为 NULL、不用 dei 封面股本），`test_pltr_omitted_long_term_debt_is_not_filled_with_zero`，`test_orcl_long_term_debt_uses_notes_payable`（同测 cogs 为 NULL，且不等于 `CostsAndExpenses`），`test_init_db_relaxes_legacy_financial_not_null`。

## pytest

命令：

```text
uv run python -m pytest -q
```

输出：

```text
...............................................................          [100%]
============================== warnings summary ===============================
.venv\Lib\site-packages\fastapi\testclient.py:1
  C:\Users\Du200\Projects\alphasentinel-codex\.venv\Lib\site-packages\fastapi\testclient.py:1: StarletteDeprecationWarning: Using `httpx` with `starlette.testclient` is deprecated; install `httpx2` instead.
    from starlette.testclient import TestClient as TestClient  # noqa

tests/test_dashboard.py::test_placeholder_database_renders_tables_and_chart
  C:\Users\Du200\Projects\alphasentinel-codex\.venv\Lib\site-packages\streamlit\elements\lib\built_in_chart_utils.py:620: Pandas4Warning: The inplace keyword in DataFrame.reset_index is deprecated and will be removed in a future version (PDEP-8).
  See https://pandas.pydata.org/docs/dev/whatsnew/v3.1.0.html#deprecation-inplace for more details.
    df.reset_index(inplace=True)  # noqa: PD002

-- Docs: https://docs.pytest.org/en/stable/how-to/capture-warnings.html
63 passed, 2 warnings in 12.59s
```

进程退出码 0。命令没有打印 `EXIT` 行。

## ruff

命令：

```text
uv run ruff check .
```

输出：

```text
All checks passed!
```

进程退出码 0。捕获到的这一行没有 ANSI 着色。命令没有打印 `EXIT` 行。

## 改前改后对照

命令：`uv run python` 运行对照脚本，读改映射前的 normalize 快照和当时的 `data/cache`。退出码 0。

```text
same NVDA derived [(), ()]
same MSFT derived [(), ()]
same AAPL derived [(), ()]
same GOOGL derived [(), ()]
same TSLA derived [(), ()]
same CRM derived [(), ()]
--- gaps ---
META 2024 cogs 30161000000.0 rd 43873000000.0 ltd 28826000000.0 tl 93417000000.0 sh None derived () accn 0001326801-25-000017
META 2025 cogs 36175000000.0 rd 57372000000.0 ltd 58744000000.0 tl 148778000000.0 sh None derived () accn 0001628280-26-003942
AMZN 2024 cogs 326288000000.0 rd None ltd 52623000000.0 tl 338924000000.0 sh 10593000000.0 derived ('total_liabilities',) accn 0001018724-25-000004
AMZN 2025 cogs 356414000000.0 rd None ltd 65648000000.0 tl 406977000000.0 sh 10731000000.0 derived ('total_liabilities',) accn 0001018724-26-000004
PLTR 2024 cogs 565990000.0 rd 507878000.0 ltd None tl 1246477000.0 sh 2338795000.0 derived () accn 0001321655-25-000022
PLTR 2025 cogs 789177000.0 rd 557677000.0 ltd None tl 1412381000.0 sh 2391192000.0 derived () accn 0001321655-26-000011
ORCL 2025 cogs None rd 9860000000.0 ltd 85297000000.0 tl 147392000000.0 sh 2807000000.0 derived () accn 0000950170-25-087926
ORCL 2026 cogs None rd 10272000000.0 ltd 122342000000.0 tl 218703000000.0 sh 2880000000.0 derived () accn 0001193125-26-277521
```

流水线重新下载之后，裁进片段的事实仍在新的 companyfacts 里。退出码 0。

```text
AMZN us-gaap StockholdersEquity missing 0
AMZN us-gaap LiabilitiesAndStockholdersEquity missing 0
AMZN dei EntityCommonStockSharesOutstanding missing 0
META dei EntityPublicFloat missing 0
ORCL us-gaap CostsAndExpenses missing 0
```

流水线写入 DuckDB 之后，这四只的缺口列。退出码 0。`None` 是 SQL NULL。

```text
('AMZN', 2024, 326288000000.0, None, 52623000000.0, 338924000000.0, 10593000000.0, 2323998263534.546)
('AMZN', 2025, 356414000000.0, None, 65648000000.0, 406977000000.0, 10731000000.0, 2476929498596.1914)
('META', 2024, 30161000000.0, 43873000000.0, 28826000000.0, 93417000000.0, None, None)
('META', 2025, 36175000000.0, 57372000000.0, 58744000000.0, 148778000000.0, None, None)
('ORCL', 2025, None, 9860000000.0, 85297000000.0, 147392000000.0, 2807000000.0, 464642706573.4863)
('ORCL', 2026, None, 10272000000.0, 122342000000.0, 218703000000.0, 2880000000.0, 650246396484.375)
('PLTR', 2024, 565990000.0, 507878000.0, None, 1246477000.0, 2338795000.0, 176883059426.30768)
('PLTR', 2025, 789177000.0, 557677000.0, None, 1412381000.0, 2391192000.0, 425034378000.0)
```

列顺序：ticker，fiscal_year，cogs，rd_expense，long_term_debt，total_liabilities，shares_outstanding，market_cap。

## 十只股票的联网流水线

命令：

```text
uv run python -u scripts/run_pipeline.py
```

外壳把 stdout 写入日志，并在进程结束后追加 `EXIT` 与退出码。输出：

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
[INGESTOR] META: downloading https://data.sec.gov/submissions/CIK0001326801.json
[INGESTOR] META FY2024: downloading https://www.sec.gov/Archives/edgar/data/1326801/000132680125000017/meta-20241231.htm
[INGESTOR] META FY2024: 339 Form 4 filings
[INGESTOR] META FY2024: Form 4 25
[INGESTOR] META FY2024: Form 4 50
[INGESTOR] META FY2024: Form 4 75
[INGESTOR] META FY2024: Form 4 100
[INGESTOR] META FY2024: Form 4 125
[INGESTOR] META FY2024: Form 4 150
[INGESTOR] META FY2024: Form 4 175
[INGESTOR] META FY2024: Form 4 200
[INGESTOR] META FY2024: Form 4 225
[INGESTOR] META FY2024: Form 4 250
[INGESTOR] META FY2024: Form 4 275
[INGESTOR] META FY2024: Form 4 300
[INGESTOR] META FY2024: Form 4 325
[INGESTOR] META FY2024: Form 4 339
[INGESTOR] META FY2025: downloading https://www.sec.gov/Archives/edgar/data/1326801/000162828026003942/meta-20251231.htm
[INGESTOR] META FY2025: 273 Form 4 filings
[INGESTOR] META FY2025: Form 4 25
[INGESTOR] META FY2025: Form 4 50
[INGESTOR] META FY2025: Form 4 75
[INGESTOR] META FY2025: Form 4 100
[INGESTOR] META FY2025: Form 4 125
[INGESTOR] META FY2025: Form 4 150
[INGESTOR] META FY2025: Form 4 175
[INGESTOR] META FY2025: Form 4 200
[INGESTOR] META FY2025: Form 4 225
[INGESTOR] META FY2025: Form 4 250
[INGESTOR] META FY2025: Form 4 273
[INGESTOR] META: downloading yfinance closes
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
[INGESTOR] AMZN: downloading https://data.sec.gov/submissions/CIK0001018724.json
[INGESTOR] AMZN FY2024: downloading https://www.sec.gov/Archives/edgar/data/1018724/000101872425000004/amzn-20241231.htm
[INGESTOR] AMZN FY2024: 97 Form 4 filings
[INGESTOR] AMZN FY2024: Form 4 25
[INGESTOR] AMZN FY2024: Form 4 50
[INGESTOR] AMZN FY2024: Form 4 75
[INGESTOR] AMZN FY2024: Form 4 97
[INGESTOR] AMZN FY2025: downloading https://www.sec.gov/Archives/edgar/data/1018724/000101872426000004/amzn-20251231.htm
[INGESTOR] AMZN FY2025: 74 Form 4 filings
[INGESTOR] AMZN FY2025: Form 4 25
[INGESTOR] AMZN FY2025: Form 4 50
[INGESTOR] AMZN FY2025: Form 4 74
[INGESTOR] AMZN: downloading yfinance closes
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
[INGESTOR] PLTR: downloading https://data.sec.gov/submissions/CIK0001321655.json
[INGESTOR] PLTR FY2024: downloading https://www.sec.gov/Archives/edgar/data/1321655/000132165525000022/pltr-20241231.htm
[INGESTOR] PLTR FY2024: 138 Form 4 filings
[INGESTOR] PLTR FY2024: Form 4 25
[INGESTOR] PLTR FY2024: Form 4 50
[INGESTOR] PLTR FY2024: Form 4 75
[INGESTOR] PLTR FY2024: Form 4 100
[INGESTOR] PLTR FY2024: Form 4 125
[INGESTOR] PLTR FY2024: Form 4 138
[INGESTOR] PLTR FY2025: downloading https://www.sec.gov/Archives/edgar/data/1321655/000132165526000011/pltr-20251231.htm
[INGESTOR] PLTR FY2025: 82 Form 4 filings
[INGESTOR] PLTR FY2025: Form 4 25
[INGESTOR] PLTR FY2025: Form 4 50
[INGESTOR] PLTR FY2025: Form 4 75
[INGESTOR] PLTR FY2025: Form 4 82
[INGESTOR] PLTR: downloading yfinance closes
[INGESTOR] ORCL: downloading https://data.sec.gov/api/xbrl/companyfacts/CIK0001341439.json
[INGESTOR] ORCL: downloading https://data.sec.gov/submissions/CIK0001341439.json
[INGESTOR] ORCL FY2025: downloading https://www.sec.gov/Archives/edgar/data/1341439/000095017025087926/orcl-20250531.htm
[INGESTOR] ORCL FY2025: 63 Form 4 filings
[INGESTOR] ORCL FY2025: Form 4 25
[INGESTOR] ORCL FY2025: Form 4 50
[INGESTOR] ORCL FY2025: Form 4 63
[INGESTOR] ORCL FY2026: downloading https://www.sec.gov/Archives/edgar/data/1341439/000119312526277521/orcl-20260531.htm
[INGESTOR] ORCL FY2026: 75 Form 4 filings
[INGESTOR] ORCL FY2026: Form 4 25
[INGESTOR] ORCL FY2026: Form 4 50
[INGESTOR] ORCL FY2026: Form 4 75
[INGESTOR] ORCL: downloading yfinance closes
[PIPELINE] ingested_records=20
[PIPELINE] financial_rows AAPL count=2 years=2024,2025 mode=LIVE_HYBRID_SEC_YF
[PIPELINE] financial_rows AMZN count=2 years=2024,2025 mode=LIVE_HYBRID_SEC_YF
[PIPELINE] financial_rows CRM count=2 years=2025,2026 mode=LIVE_HYBRID_SEC_YF
[PIPELINE] financial_rows GOOGL count=2 years=2024,2025 mode=LIVE_HYBRID_SEC_YF
[PIPELINE] financial_rows META count=2 years=2024,2025 mode=LIVE_HYBRID_SEC_YF
[PIPELINE] financial_rows MSFT count=2 years=2025,2026 mode=LIVE_HYBRID_SEC_YF
[PIPELINE] financial_rows NVDA count=2 years=2025,2026 mode=LIVE_HYBRID_SEC_YF
[PIPELINE] financial_rows ORCL count=2 years=2025,2026 mode=LIVE_HYBRID_SEC_YF
[PIPELINE] financial_rows PLTR count=2 years=2024,2025 mode=LIVE_HYBRID_SEC_YF
[PIPELINE] financial_rows TSLA count=2 years=2024,2025 mode=LIVE_HYBRID_SEC_YF
[PIPELINE] scored_companies=10
[PIPELINE] nullable_metrics altman_z_score,beneish_m_score,piotroski_f_score,ebit_margin_pct,ebit_margin_yoy_change_bps,revenue_growth_yoy_pct,rd_to_revenue_pct,ai_hype_score,ai_roi_realization_score,ai_washing_score,dsri,gmi,aqi,sgi,depi,sgai,lvgi,tata
[PIPELINE] metric_counts AAPL FY2025 with_value=17 null=1
[PIPELINE] metric_null AAPL piotroski_f_score
[PIPELINE] metric_value AAPL altman_z_score,beneish_m_score,ebit_margin_pct,ebit_margin_yoy_change_bps,revenue_growth_yoy_pct,rd_to_revenue_pct,ai_hype_score,ai_roi_realization_score,ai_washing_score,dsri,gmi,aqi,sgi,depi,sgai,lvgi,tata
[PIPELINE] metric_counts AMZN FY2025 with_value=16 null=2
[PIPELINE] metric_null AMZN piotroski_f_score,rd_to_revenue_pct
[PIPELINE] metric_value AMZN altman_z_score,beneish_m_score,ebit_margin_pct,ebit_margin_yoy_change_bps,revenue_growth_yoy_pct,ai_hype_score,ai_roi_realization_score,ai_washing_score,dsri,gmi,aqi,sgi,depi,sgai,lvgi,tata
[PIPELINE] metric_counts CRM FY2026 with_value=17 null=1
[PIPELINE] metric_null CRM piotroski_f_score
[PIPELINE] metric_value CRM altman_z_score,beneish_m_score,ebit_margin_pct,ebit_margin_yoy_change_bps,revenue_growth_yoy_pct,rd_to_revenue_pct,ai_hype_score,ai_roi_realization_score,ai_washing_score,dsri,gmi,aqi,sgi,depi,sgai,lvgi,tata
[PIPELINE] metric_counts GOOGL FY2025 with_value=17 null=1
[PIPELINE] metric_null GOOGL piotroski_f_score
[PIPELINE] metric_value GOOGL altman_z_score,beneish_m_score,ebit_margin_pct,ebit_margin_yoy_change_bps,revenue_growth_yoy_pct,rd_to_revenue_pct,ai_hype_score,ai_roi_realization_score,ai_washing_score,dsri,gmi,aqi,sgi,depi,sgai,lvgi,tata
[PIPELINE] metric_counts META FY2025 with_value=16 null=2
[PIPELINE] metric_null META altman_z_score,piotroski_f_score
[PIPELINE] metric_value META beneish_m_score,ebit_margin_pct,ebit_margin_yoy_change_bps,revenue_growth_yoy_pct,rd_to_revenue_pct,ai_hype_score,ai_roi_realization_score,ai_washing_score,dsri,gmi,aqi,sgi,depi,sgai,lvgi,tata
[PIPELINE] metric_counts MSFT FY2026 with_value=17 null=1
[PIPELINE] metric_null MSFT piotroski_f_score
[PIPELINE] metric_value MSFT altman_z_score,beneish_m_score,ebit_margin_pct,ebit_margin_yoy_change_bps,revenue_growth_yoy_pct,rd_to_revenue_pct,ai_hype_score,ai_roi_realization_score,ai_washing_score,dsri,gmi,aqi,sgi,depi,sgai,lvgi,tata
[PIPELINE] metric_counts NVDA FY2026 with_value=17 null=1
[PIPELINE] metric_null NVDA piotroski_f_score
[PIPELINE] metric_value NVDA altman_z_score,beneish_m_score,ebit_margin_pct,ebit_margin_yoy_change_bps,revenue_growth_yoy_pct,rd_to_revenue_pct,ai_hype_score,ai_roi_realization_score,ai_washing_score,dsri,gmi,aqi,sgi,depi,sgai,lvgi,tata
[PIPELINE] metric_counts ORCL FY2026 with_value=15 null=3
[PIPELINE] metric_null ORCL beneish_m_score,piotroski_f_score,gmi
[PIPELINE] metric_value ORCL altman_z_score,ebit_margin_pct,ebit_margin_yoy_change_bps,revenue_growth_yoy_pct,rd_to_revenue_pct,ai_hype_score,ai_roi_realization_score,ai_washing_score,dsri,aqi,sgi,depi,sgai,lvgi,tata
[PIPELINE] metric_counts PLTR FY2025 with_value=15 null=3
[PIPELINE] metric_null PLTR beneish_m_score,piotroski_f_score,lvgi
[PIPELINE] metric_value PLTR altman_z_score,ebit_margin_pct,ebit_margin_yoy_change_bps,revenue_growth_yoy_pct,rd_to_revenue_pct,ai_hype_score,ai_roi_realization_score,ai_washing_score,dsri,gmi,aqi,sgi,depi,sgai,tata
[PIPELINE] metric_counts TSLA FY2025 with_value=17 null=1
[PIPELINE] metric_null TSLA piotroski_f_score
[PIPELINE] metric_value TSLA altman_z_score,beneish_m_score,ebit_margin_pct,ebit_margin_yoy_change_bps,revenue_growth_yoy_pct,rd_to_revenue_pct,ai_hype_score,ai_roi_realization_score,ai_washing_score,dsri,gmi,aqi,sgi,depi,sgai,lvgi,tata
[REPORTS] C:\Users\Du200\Projects\alphasentinel-codex\reports\AlphaSentinel_Executive_Briefing.md | C:\Users\Du200\Projects\alphasentinel-codex\reports\AlphaSentinel_Executive_Briefing.docx
[OK] Verified deliverable: C:\Users\Du200\Projects\alphasentinel-codex\deliverables\PROJECT_CHARTER.md (2534 bytes)
[OK] Verified deliverable: C:\Users\Du200\Projects\alphasentinel-codex\deliverables\PROJECT_CHARTER.docx (38415 bytes)
[OK] Verified deliverable: C:\Users\Du200\Projects\alphasentinel-codex\deliverables\AGENT_EXECUTION_PLAN.md (1967 bytes)
[OK] Verified deliverable: C:\Users\Du200\Projects\alphasentinel-codex\deliverables\AGENT_EXECUTION_PLAN.docx (37849 bytes)
[PIPELINE_SUCCESS] Ingested 20 records, scored 10 companies.
EXIT 0
```

## --verify-all

命令：

```text
uv run python -u scripts/run_pipeline.py --verify-all
```

外壳在同一条命令后打印 `EXIT` 与 `$LASTEXITCODE`。输出：

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

## dag 状态

命令：

```text
uv run python scripts/dag_ctl.py status
```

外壳在同一条命令后打印 `EXIT` 与 `$LASTEXITCODE`。输出：

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
