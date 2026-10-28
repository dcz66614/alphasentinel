# A05 report_compiler

## 实现内容

- 新增 `src/alphasentinel/report_compiler.py`。
- 以只读方式从 DuckDB 的 `forensic_scores` 表读取报告数据。
- 生成 `reports/AlphaSentinel_Report.md` 和 `reports/AlphaSentinel_Report.docx`。
- Word 文档使用 python-docx，包含标题、多级标题和标准网格表格。
- 报告包含跨组合风险矩阵及 Beneish 八因子分解；所有展示值均直接取自数据库，不推算或填补数据。
- NULL 指标显示“数据不足（数据库字段为 NULL）”；空表显示“无数据：forensic_scores 表为空”。
- 支持 CLI：`python -m alphasentinel.report_compiler [--db PATH] [--out DIR]`。

## 测试

- 新增 `tests/test_reports.py`，仅使用临时 DuckDB 和占位行。
- 覆盖 Markdown 数值往返、python-docx 读回、NULL 提示、空表提示和 CLI 参数。
- 未运行 TEST 集。

## 验证结果

- `uv run python -m pytest -q`：27 passed，退出码 0。
- `uv run ruff check .`：All checks passed，退出码 0。

## 提交

- Commit：`4d3459f A05 report_compiler`
- 本文件未提交。
