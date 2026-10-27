# AlphaSentinel 任务板（调度员不写项目代码）
规则：每任务全新会话；Copilot 只读审 + 调度员自审；禁止编造数据/硬编码数字；不加 spec 外机制。
| ID | 内容 (对应方案) | 执行者 | 通过标准 | 状态 |
|---|---|---|---|---|
| A00 | 脚手架：pyproject(uv, setuptools>=77)、LICENSE、ruff、pytest、CI(ubuntu+windows)、空包 src/alphasentinel | opencode deepseek-v4.1-flash-free | `uv sync && python -m pytest && ruff check` 通过 | 待派（里程碑1） |
| A01 | TASK-01 任务账本 scripts/dag_ctl.py（status/verify） | opencode 免费 | tests/test_dag_ctl.py 通过 | 待 |
| A02 | TASK-02 DuckDB schema (company_financials, forensic_scores) | Grok Build 4.7 high | tests/test_schema.py | 待 |
| A03 | TASK-03 edgartools 采集 + XBRL 归一化（10 只核心票）；离线回退只能用真实缓存，不得合成数字 | Grok Build | tests/test_ingestor.py（网络用录制 fixture） | 待 |
| A04 | TASK-04 Beneish M / Altman Z / Piotroski F / AI-Washing 指数 | Grok Build（公式核对：agy） | 教科书算例单测 | 待 |
| A05 | TASK-05 报告编译(.md+.docx) | qoder qwen3.8flash / opencode | test_reports.py | 待 |
| A06 | TASK-06 FastAPI | opencode 免费 | test_api.py | 待 |
| A07 | TASK-07 Streamlit 看板 | opencode / agy | py_compile + 冒烟 | 待 |
| A08 | TASK-08 四份交付文档 | agy (gemini flash) | build --verify | 待 |
| A09 | TASK-09 端到端 run_pipeline --verify-all + 审计报告 | 调度员 + Grok | 全绿，数字来自真实运行 | 待 |
