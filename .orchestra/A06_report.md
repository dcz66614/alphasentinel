# A06 报告：FastAPI 只读接口

## 完成内容

- 新增 `src/alphasentinel/api_server.py`，实现 `GET /health`、`GET /companies`、`GET /financials/{ticker}`、`GET /scores/{ticker}`。
- 数据库路径读取 `ALPHASENTINEL_DB`，未设置时使用项目默认 `data/alphasentinel.duckdb`。
- 只查询现有表，不实现评分；公司列表为空时返回空列表，指定 ticker 无记录时返回 404。
- 新增 `tests/test_api.py`，使用 FastAPI TestClient 和临时 DuckDB，以明显占位行验证读写往返及空表行为。
- 添加 `httpx` 开发依赖并更新 `uv.lock`。

## 验证

- `uv run python -m pytest -q`：23 passed，退出码 0。
- `uv run ruff check .`：All checks passed，退出码 0。
- 未运行 TEST 集。
