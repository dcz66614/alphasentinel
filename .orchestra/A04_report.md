# A04 forensic_engine

日期：2026-10-27

对 `data/alphasentinel.duckdb` 里 A03 留下的 AAPL、MSFT 跑了 `uv run python -m alphasentinel.forensic_engine`。写出 2 行 `forensic_scores`。数据库在 `.gitignore` 里，本报告也不提交。

计算时点：`2026-10-27T23:50:13.594664+00:00`

## 结果

| 字段 | AAPL FY2025 | MSFT FY2026 |
| --- | ---: | ---: |
| 来源 | LIVE_HYBRID_SEC_YF | LIVE_HYBRID_SEC_YF |
| Altman Z | 10.1971 SAFE | 7.0411 SAFE |
| Beneish M | -2.2949 NORMAL | -2.6381 NORMAL |
| Piotroski F | NULL | NULL |
| EBIT 利润率 | 31.97% | 46.78% |
| EBIT 利润率同比 | +46.1 bp | +115.9 bp |
| 收入同比 | 6.43% | 17.79% |
| 研发 / 收入 | 8.30% | 10.72% |
| AI hype | 2.67 | 7.57 |
| AI ROI | 61.40 | 80.62 |
| AI-Washing | 20.00 VERIFIED_AI_ROI | 20.00 VERIFIED_AI_ROI |
| DSRI | 1.1187 | 0.9822 |
| GMI | 0.9851 | 1.0129 |
| AQI | 0.9863 | 0.8700 |
| SGI | 1.0643 | 1.1779 |
| DEPI | 1.0539 | 0.9817 |
| SGAI | 0.9938 | 0.8952 |
| LVGI | 0.9455 | 0.8996 |
| TATA | 0.0015 | -0.0649 |

Piotroski 的原因写在 `piotroski_tier`：

- AAPL：`missing fiscal year 2023 total_assets (Piotroski ROA, leverage, and asset turnover use beginning or average assets)`
- MSFT：`missing fiscal year 2024 total_assets (Piotroski ROA, leverage, and asset turnover use beginning or average assets)`

`company_financials` 每个代码只有两年（AAPL 2024–2025，MSFT 2025–2026）。Piotroski（2000）把 ROA、经营现金流和资产周转率除以期初总资产，把长期债务除以平均总资产。同比变化因此还要用再前一年的总资产。这一年不在表里，F 分记 NULL，没有用期末资产代替，也没有把缺的信号当成 0 再加总。

同一份 `data/cache` 的 companyfacts 用 ingestor 归一化出三年后，公式可以算出分。这组数没有写入 `forensic_scores`：

- AAPL FY2025：F = 8，STRONG
- MSFT FY2026：F = 6，MODERATE

AI-Washing 的 20 分来自任务包里的内部人条款。AAPL 的 `insider_net_sell_ratio` 是 1.0，MSFT FY2026 是 0.9599，都高于 0.70，加 20。两家的 hype 减去 0.85 倍 ROI 都是负数，按公式先截到 0，再加这 20。20 低于 35，状态是 VERIFIED_AI_ROI。

## 公式

Altman（1968，Journal of Finance）小数形式：

Z = 1.2 X1 + 1.4 X2 + 3.3 X3 + 0.6 X4 + 1.0 X5

X1 营运资本 / 总资产，X2 留存收益 / 总资产，X3 EBIT / 总资产，X4 股权市值 / 总负债，X5 收入 / 总资产。1968 年原文把前四项写成百分数，销售项系数是 0.999；这里用后来通用的小数形式，销售项系数为 1.0。Z > 2.99 为 SAFE，Z < 1.81 为 DISTRESS，其余为 GREY。

Beneish（1999，Financial Analysts Journal）八变量：

M = -4.84 + 0.920 DSRI + 0.528 GMI + 0.404 AQI + 0.892 SGI + 0.115 DEPI - 0.172 SGAI + 4.679 TATA - 0.327 LVGI

M > -1.78 为 MANIPULATION_RISK_HIGH，否则 NORMAL。资产质量是 `1 - (流动资产 + 净 PPE) / 总资产`，不另减一项证券。TATA 用 Beneish、Lee、Nichols（2013）的现金流应计 `(净利润 - 经营现金流) / 总资产`。1999 年的资产负债表应计还要现金、应交所得税和一年内到期的长期债务，仓库里没有这些科目，没有用 0 填上。

Piotroski（2000，Journal of Accounting Research）九个 0/1 信号。股权发行在原文里看的是发行股票的现金流。仓库只有流通股，信号改为流通股没有增加时得 1。档位按任务包：7 及以上 STRONG，4 到 6 MODERATE，其余 WEAK。

AI-Washing 只按 TASK-04 的定义，没有对应的论文。状态用未四舍五入的指数；入库数字按任务包保留小数。

缺科目、缺上一年，或某个比率的分母正好为 0 时，该指标为 NULL，原因写在旁边的文字列。`init_db` 会把已有库里这些数值列的 NOT NULL 去掉。身份列和文字列仍然非空。

## 验证

- `uv run python -m pytest -q`：30 passed
- `uv run ruff check .`：All checks passed

测试用了 AccountingTools 的 Altman 算例（Z = 2.095，灰色区，https://www.accountingtools.com/articles/the-altman-z-score-formula.html），以及 Beneish 1999 系数在“八个指数都是 1、TATA = 0.05”时的结果 M = -2.24605。SEC 数字来自 `tests/fixtures` 和 `data/cache` 的 companyfacts，经 `normalize_company_facts` / 离线 `ingest_tickers` 读出，测试文件里没有手写这些金额。全 0 占位行沿用 `test_schema.py` 的做法，只为满足财务表的 NOT NULL，断言法务分数仍是 NULL。
