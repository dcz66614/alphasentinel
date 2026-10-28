# AlphaSentinel A02 报告

## 1. 位置与版本

- 仓库：`C:\Users\Du200\Projects\alphasentinel-codex`（分支 `codex`）
- 基线：`ca04274` A01 dag_ctl
- 本轮提交：`9923452fa0d291b58a3e3502570b4bdd7abe3619` A02 db_schema
- 本报告不提交

## 2. 要求与处理

| # | 要求 | 处理 | 文件 |
|---|---|---|---|
| 1 | 建 `company_financials`、`forensic_scores`，字段与主键照 spec TASK-02 | 29 列与 28 列均按 spec，类型 VARCHAR / INTEGER / DOUBLE，全部 NOT NULL，主键 `(ticker, fiscal_year)` | `src/alphasentinel/db_schema.py` |
| 2 | `init_db(path)`，默认 `data/alphasentinel.duckdb`，可传路径 | 默认路径由包文件定位到仓库 `data/alphasentinel.duckdb`。`CREATE TABLE IF NOT EXISTS`，重复调用不删已有行 | 同上 |
| 3 | schema 校验函数 | `validate_schema(path)`。缺文件、缺表、列名/类型/非空或主键不符时抛 `ValueError` | 同上 |
| 4 | 测试用 `tempfile.TemporaryDirectory`，断言表、列、主键、类型，重复 init 幂等 | `tests/test_schema.py`。不使用 pytest 的 `tmp_path` | `tests/test_schema.py` |
| 5 | 不插入虚构财务数字；占位行只做读写往返 | 文本列写 `TEST`，数值列写 `0` 以满足 NOT NULL。断言读回等于写入值，不把这些值当作财务事实 | 同上 |
| 6 | DAG artifact 改为 `src/alphasentinel/<模块>.py`，pytest 门禁改为 `python -m pytest -q tests/<对应>.py`，TASK-01 用 `python scripts/dag_ctl.py status`，跨平台 | TASK-02 至 TASK-06 按此改。TASK-01 的 artifact 仍是 `scripts/dag_ctl.py`。TASK-07 改为 `python -m py_compile src/alphasentinel/dashboard.py`。TASK-08/09 仍是交付物路径，只把 `python3` 换成 `python` | `scripts/dag_ctl.py`，`tests/test_dag_ctl.py` |
| 7 | 不加 spec 外机制 | 未加哈希、签名或额外表 | — |

TASK-07/08/09 没有对应的 pytest 文件。spec 与任务板给它们的门禁分别是编译、交付物校验和流水线校验，所以没有改成 `python -m pytest`。

## 3. 测试结果

- Windows：`uv run python -m pytest -q`，退出码 0

```
..............                                                           [100%]
14 passed in 2.28s
```

- Windows：`uv run ruff check .`，退出码 0，输出 `All checks passed!`
- Linux（git archive / git 检出）：本机未跑
- 未运行 TEST 数据，未写默认库 `data/alphasentinel.duckdb`

## 4. 审查结论

- Copilot：本轮没有独立审查
- 调度员：待审。执行侧自测为 pytest 14 passed、ruff 通过

## 5. 未解决问题与局限

- 已有的 `state/dag_state.db` 若是旧版 `init` 生成的，`INSERT OR IGNORE` 不会改已存在任务的 artifact 和 verify_cmd。新库会写入新路径。
- 占位行的数值是 `0`，只为满足 NOT NULL，不是公司财务数据。
- 没有在 Linux 上复跑测试。
- DevRelay 网关未连接，没有引用 dev.to 文章。
