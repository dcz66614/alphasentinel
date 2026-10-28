# 任务 A02：TASK-02 DuckDB 数仓 schema
工作目录：C:\Users\Du200\Projects\alphasentinel-codex（只在此目录写文件）。
参考 spec：C:\Users\Du200\Projects\alphasentinel-codex\docs\spec\AlphaSentinel_方案全文.txt 中“任务包 TASK-02”（约第 253–367 行），以其表结构为准。
要求：
- src/alphasentinel/db_schema.py：建表 company_financials、forensic_scores（字段照 spec），提供 init_db(path) 与 schema 校验函数；数据库默认 data/alphasentinel.duckdb，可传路径。
- tests/test_schema.py：tempfile.TemporaryDirectory 建库，断言表与列存在、主键/类型合理、重复 init 幂等。不插入任何虚构财务数字（测试行可用明显的占位如 ticker 'TEST' 且仅验证读写往返）。
- 同时把 scripts/dag_ctl.py 中各任务的 artifact 改为 src/alphasentinel/<模块>.py，verify_cmd 改为 python -m pytest -q tests/<对应>.py（TASK-01 用 python scripts/dag_ctl.py status），保持跨平台，并更新相应测试。
- 不加 spec 外机制（哈希、签名等）。
通过标准：uv run python -m pytest -q 与 uv run ruff check . 全部退出码 0。
禁止：联网下载、运行 TEST 数据、编造数字。完成后提交一次 "A02 db_schema"。报告写到 C:\Users\Du200\Projects\alphasentinel-codex\A02_report.md（不提交）。
