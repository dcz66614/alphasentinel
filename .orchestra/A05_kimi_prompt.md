# 任务 A05：TASK-05 报告编译器（.md + .docx）
工作目录：C:\Users\Du200\Projects\alphasentinel-wb（只在此目录写文件）。
参考 spec：C:\Users\Du200\Projects\alphasentinel-wb\docs\spec\AlphaSentinel_方案全文.txt 中 TASK-05（搜“TASK-05”）；表结构见 src/alphasentinel/db_schema.py（company_financials, forensic_scores）。评分引擎在另一分支开发，这里只读表。
要求：
- src/alphasentinel/report_compiler.py：从库读取数据，生成 reports/AlphaSentinel_Report.md 与 .docx（python-docx）。所有数字只能来自库；指标为 NULL 时显示“数据不足”及原因；表为空时报告写明“无数据”而不是编造。
- CLI：python -m alphasentinel.report_compiler [--db PATH] [--out DIR]。
- tests/test_reports.py：tempfile 建库，只用占位行测往返（md 内容含该值、docx 可被 python-docx 读回、NULL 显示“数据不足”）。
- 不加 spec 外机制；禁止运行 TEST 集。
通过标准：uv run python -m pytest -q 与 uv run ruff check . 退出码 0。完成后提交 "A05 report_compiler"。报告写到 C:\Users\Du200\Projects\alphasentinel-wb\A05_report.md（不提交）。