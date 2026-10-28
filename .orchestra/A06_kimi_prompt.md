# 任务 A06：TASK-06 FastAPI 只读接口
工作目录：C:\Users\Du200\Projects\alphasentinel-wb（只在此目录写文件）。
参考 spec：C:\Users\Du200\Projects\alphasentinel-wb\docs\spec\AlphaSentinel_方案全文.txt 中 TASK-06（搜“TASK-06”）；表结构用 src/alphasentinel/db_schema.py（company_financials, forensic_scores）。forensic_engine 正在另一分支开发，不要实现评分，只读表。
要求：
- src/alphasentinel/api_server.py：FastAPI app；GET /health；GET /companies；GET /financials/{ticker}；GET /scores/{ticker}（表空时返回空列表/404，不编造值）。数据库路径从环境变量 ALPHASENTINEL_DB 读取，缺省 data/alphasentinel.duckdb。
- tests/test_api.py：fastapi TestClient + tempfile 建库（db_schema.init_db），只用明显占位行验证往返，不写虚构财务数字作为“真实”数据。
- 若需 httpx 加到 dev 依赖并更新 uv.lock。
- 不加鉴权、限流等 spec 外机制；禁止运行 TEST 集。
通过标准：uv run python -m pytest -q 与 uv run ruff check . 退出码 0。完成后提交一次 "A06 api_server"。报告写到 C:\Users\Du200\Projects\alphasentinel-wb\A06_report.md（不提交）。