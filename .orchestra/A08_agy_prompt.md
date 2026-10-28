# 任务 A08：TASK-08 四份交付文档生成器
工作目录：C:\Users\Du200\Projects\alphasentinel-codex（只在此目录写文件）。
参考 spec：C:\Users\Du200\Projects\alphasentinel-codex\docs\spec\AlphaSentinel_方案全文.txt 中 TASK-08 与“第四部分”（build_four_deliverables.py）。
要求：scripts/build_four_deliverables.py：从 docs/spec 中的方案原文抽取项目书与执行计划书内容，生成 deliverables/PROJECT_CHARTER.md/.docx 与 AGENT_EXECUTION_PLAN.md/.docx（python-docx，标题层级、表格、代码块字体）；--verify 检查 4 个文件存在且非空、docx 可读回。内容中不得新增编造的统计数字（只能复用原文已有、带出处的内容）。
tests/test_deliverables.py：tempfile 输出目录跑生成与 --verify。
不加 spec 外机制（如 OpenXML 兜底引擎可省略）；禁止运行 TEST 集。通过标准：uv run python -m pytest -q 与 uv run ruff check . 0。提交 「A08 deliverables」。报告写 C:\Users\Du200\Projects\alphasentinel-codex\A08_report.md（不提交）。