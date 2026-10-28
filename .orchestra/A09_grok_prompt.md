# 任务 A09：TASK-09 端到端流水线 + 全量验证
工作目录：C:\Users\Du200\Projects\alphasentinel-codex（只在此目录写文件）。
参考 spec：C:\Users\Du200\Projects\alphasentinel-codex\docs\spec\AlphaSentinel_方案全文.txt 中 TASK-09。现有模块：ingestor、forensic_engine、report_compiler、api_server、dashboard、scripts/dag_ctl.py、scripts/build_four_deliverables.py。
要求：
- scripts/run_pipeline.py：依次 ingest（spec 的 10 只核心股，联网真实 SEC 数据，缓存到 data/cache）→ forensic 计算 → 报告编译（含 reports/AlphaSentinel_Executive_Briefing.md/.docx）→ deliverables 生成；--offline 只用已缓存的真实数据；--verify-all 依次运行 dag_ctl verify TASK-01..09 并汇总。
- 确保 dag_ctl 中 TASK-09 的 verify_cmd 与此一致，且所有 verify_cmd 在 Windows 上可运行。
- tests/test_pipeline.py：用 tests/fixtures 真实片段 + tempfile 测流水线编排（不联网）。
- 实际联网运行一次完整流水线（10 只），把每只股票的写入行数、各指标是 NULL 还是有值的计数、--verify-all 结果写入报告。报告里所有数字必须来自该次真实运行的输出（贴命令与输出片段），不得手写。生成的数据库/报告文件不提交。
- 不加 spec 外机制；禁止运行 TEST 集。
通过标准：uv run python -m pytest -q 与 uv run ruff check . 0，--verify-all 退出码 0（若某任务因真实数据缺失而无法通过，如实写明，不要伪造）。提交 "A09 pipeline"。报告写 C:\Users\Du200\Projects\alphasentinel-codex\A09_report.md（不提交）。