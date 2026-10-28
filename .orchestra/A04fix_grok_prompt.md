# 任务 A04fix：修复 A04 测试依赖未提交缓存的问题
工作目录：C:\Users\Du200\Projects\alphasentinel-codex（只在此目录写文件）。先执行 git rebase master（master 已含 A06 api_server，冲突需正确合并）。
审查意见（Copilot）：python -m pytest -q 在没有 data/cache 的干净检出里失败：缺 data/cache/AAPL/companyfacts.json 和 AAPL/index.json，2 个测试失败。
要求：tests/test_forensic.py 及其它测试只能用 tests/fixtures 下已提交的真实 SEC 片段（必要时从本机 data/cache 截取真实片段加入 fixtures，并在 tests/fixtures/README.md 写来源 URL 和日期）或公开论文算例；不得依赖 data/ 目录；不得手编财务数字。在一个没有 data/ 的临时 clone 中验证（git clone 本 worktree 到临时目录后 uv run python -m pytest -q）。
通过标准：干净 clone 中 pytest 与 ruff 全部 0。完成后提交 "A04fix tests self-contained"。报告写到 C:\Users\Du200\Projects\alphasentinel-codex\A04fix_report.md（不提交）。禁止运行 TEST 集。