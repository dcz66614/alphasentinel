# 任务 A03：TASK-03 SEC EDGAR 采集 + XBRL 归一化 + 仅缓存离线回退
工作目录：C:\Users\Du200\Projects\alphasentinel-codex（只在此目录写文件）。
参考 spec：C:\Users\Du200\Projects\alphasentinel-codex\docs\spec\AlphaSentinel_方案全文.txt“任务包 TASK-03”（约第 368–560 行）；表结构用已合并的 src/alphasentinel/db_schema.py。
要求：
- src/alphasentinel/ingestor.py：用 edgartools（免费、无 key）取 spec 指定的 10 只核心股多年 10-K 财务数据，归一化 XBRL 科目写入 company_financials。SEC identity 从环境变量 SEC_IDENTITY 读取，缺省用 spec 中的值。
- 原始下载缓存到 data/cache/（gitignore）。离线回退：只能读取 data/cache 中真实下载过的文件；没有缓存就报错退出，绝不生成、插值或硬编码任何财务数字。
- CLI：python -m alphasentinel.ingestor --tickers ... [--offline]。
- tests/test_ingestor.py：不联网。归一化逻辑用 tests/fixtures/ 下的小片段测试，该片段必须是从 SEC 真实响应中截取的（在 fixtures/README.md 写明来源 URL 与下载日期），不得手编数字；另测“无缓存+offline→报错”。
- 完成后实际联网跑一次 2 只股票（如 AAPL、MSFT）作为冒烟，把命令和行数写入报告（数据库/缓存不提交）。
- 不加 spec 外机制。
通过标准：uv run python -m pytest -q 与 uv run ruff check . 退出码 0；冒烟真实写入行数>0。
禁止：运行 TEST 数据、编造数字。完成后提交一次 "A03 ingestor"。报告写到 C:\Users\Du200\Projects\alphasentinel-codex\A03_report.md（不提交）。
