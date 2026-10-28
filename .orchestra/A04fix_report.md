# A04fix 报告

## Rebase

`codex` 已 rebase 到含 A06 的 `master`（`c19b102`）。这一笔无冲突。Rebase 后 A04 为 `69fffd1`，本修复提交在其上。

## 问题

干净检出没有 `data/cache` 时，`tests/test_forensic.py` 有两处读未提交缓存：

- `test_piotroski_and_beneish_on_three_normalized_aapl_years` 读 `data/cache/AAPL/companyfacts.json`
- `test_pipeline_on_offline_sec_cache` 把 `cache_dir` 指到 `data/cache`，缺 `AAPL/index.json` 就失败

## 修复

从本机 2026-10-27 的 `data/cache` 截取真实片段，放入 `tests/fixtures/offline_cache/`。来源 URL、期末和截取范围写在 `tests/fixtures/README.md`。金额、收盘价、10-K 文本和 Form 4 XML 都是从下载文件复制的。

AAPL `companyfacts.json` 保留三个年报期末：2023-09-30、2024-09-28、2025-09-27。用同一套 `normalize_company_facts(max_years=3)` 对比，截取结果与全量 companyfacts 逐字段一致。离线 ingest 仍只取最近两年。价格片段按这两年算出的市值与全量 `prices.csv` 一致。

`tests/test_forensic.py` 改为读 `tests/fixtures/offline_cache`。生产代码没有改。

## 验证

没有运行 TEST 集。

工作区：

```text
uv run ruff check .
All checks passed!

uv run python -m pytest -q
32 passed, 1 warning in 4.15s
```

干净 clone（`data/` 不存在）：

```text
git clone --branch codex <本 worktree> C:\Users\Du200\AppData\Local\Temp\a04fix-clone
DATA_EXISTS=False

uv run ruff check .
All checks passed!

uv run python -m pytest -q
32 passed, 1 warning in 4.22s
```

警告是 FastAPI / Starlette 的 `StarletteDeprecationWarning`，来自依赖里的 `testclient.py`。

`uv run ruff format --check .` 在这次改动之前就已经失败，涉及 `scripts/dag_ctl.py`、`src/alphasentinel/db_schema.py`、`forensic_engine.py`、`ingestor.py` 以及若干既有测试。这次没有为了格式化去改那些文件。

## 提交

`87e9e6aadd2c05a44fbc2387e09d75c2f25b5318`

`A04fix tests self-contained`

本报告不提交。
