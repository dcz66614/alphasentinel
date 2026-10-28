# A07 报告：TASK-07 Streamlit 看板

## 交付内容

- `src/alphasentinel/dashboard.py`
  - 可通过 `uv run streamlit run src/alphasentinel/dashboard.py` 启动。
  - 数据库路径读取 `ALPHASENTINEL_DB`，未设置时使用项目默认路径。
  - 支持按公司选择，展示财务表、Altman Z、Beneish M、Piotroski F、AI-Washing 四项评分表及评分折线图。
  - 所有展示数值直接读取 `company_financials` 和 `forensic_scores`，不计算或填补指标。
  - NULL 显示“数据不足”；数据库两表均无公司记录时显示“无数据”。
- `tests/test_dashboard.py`
  - 验证 `py_compile`。
  - 使用 `streamlit.testing.v1.AppTest` 分别运行 tempfile 空库和占位行库，均验证无异常。
  - 未运行 TEST 集。

## 验证结果

- `uv run python -m pytest -q`：39 passed，0 failed（2 个第三方依赖弃用警告）。
- `uv run ruff check .`：All checks passed，退出码 0。

## 提交

- Commit：`8d4d158 A07 dashboard`
- 本报告未提交。
