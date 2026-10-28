# 任务 A04：TASK-04 法务排雷与 AI-Washing 量化引擎
工作目录：C:\Users\Du200\Projects\alphasentinel-codex（只在此目录写文件）。
参考 spec：C:\Users\Du200\Projects\alphasentinel-codex\docs\spec\AlphaSentinel_方案全文.txt“任务包 TASK-04”（约第 561–786 行）；输入用已合并的 company_financials（src/alphasentinel/db_schema.py、ingestor.py），输出写 forensic_scores。
要求：
- src/alphasentinel/forensic_engine.py：Beneish M-Score（8 变量）、Altman Z-Score、Piotroski F-Score（9 项）、AI-Washing 指数（按 spec 定义）。公式和系数用学术原文的标准值，在 docstring 注明出处。
- 缺少计算所需科目或上一年数据时，该指标记为 NULL 并写明原因，不补零、不插值、不编造。
- CLI：python -m alphasentinel.forensic_engine 读库计算并写入。
- tests/test_forensic.py：用公开的教科书/论文算例（注明出处）或用 tests/fixtures 中的真实 SEC 片段经 ingestor 归一化后的数据做测试；不得手编财务数字。另测缺数据→NULL。
- 用本机 data/ 中 A03 冒烟留下的真实 AAPL/MSFT 数据实际跑一次，结果写入报告（不提交数据库）。
- 不加 spec 外机制；禁止运行 TEST 集。
通过标准：uv run python -m pytest -q 与 uv run ruff check . 退出码 0。完成后提交一次 "A04 forensic_engine"。报告写到 C:\Users\Du200\Projects\alphasentinel-codex\A04_report.md（不提交）。