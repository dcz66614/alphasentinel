# 任务 A00：AlphaSentinel 脚手架
工作目录：C:\Users\Du200\Projects\alphasentinel-codex（绝对路径）。只在此目录内写文件。
目标：建 Python 3.11+ 项目骨架。
- pyproject.toml（name=alphasentinel, MIT, build-system setuptools>=77, 依赖：duckdb, edgartools, pandas, fastapi, streamlit, python-docx, yfinance；dev：pytest, ruff）
- LICENSE(MIT)、README.md（一段简介）、.gitignore（data/*.duckdb, .venv, __pycache__）
- src/alphasentinel/__init__.py（__version__="0.0.1"）
- tests/test_smoke.py：import alphasentinel 并断言版本
- .github/workflows/ci.yml：ubuntu-latest + windows-latest，uv sync --locked，python -m pytest，ruff check
- 生成 uv.lock
通过标准：`uv sync && uv run python -m pytest -q && uv run ruff check .` 全部退出码 0。
禁止：联网下载 SEC 数据、编造任何数字、spec 外的额外机制。完成后提交一次，信息 "A00 scaffold"。报告写到 worktree 根目录 A00_report.md（不提交）。
