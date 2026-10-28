# 任务 A07：TASK-07 Streamlit 看板
工作目录：C:\Users\Du200\Projects\alphasentinel-wb（只在此目录写文件）。
参考 spec：C:\Users\Du200\Projects\alphasentinel-wb\docs\spec\AlphaSentinel_方案全文.txt 中 TASK-07。数据来源：src/alphasentinel/db_schema.py 的表；可复用 api_server/report_compiler 中的读库函数。
要求：src/alphasentinel/dashboard.py（streamlit run 可启动）：公司选择、财务表、四项评分表与简单图表；NULL 显示“数据不足”；库为空显示“无数据”。数值只来自库。DB 路径读 ALPHASENTINEL_DB。
tests/test_dashboard.py：py_compile 通过 + 用 streamlit.testing.v1.AppTest 在 tempfile 空库与占位行库各跑一次不报错。
不加 spec 外机制；禁止运行 TEST 集。通过标准：uv run python -m pytest -q 与 uv run ruff check . 0。提交 "A07 dashboard"。报告写 C:\Users\Du200\Projects\alphasentinel-wb\A07_report.md（不提交）。