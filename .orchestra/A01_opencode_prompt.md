# 任务 A01：TASK-01 任务账本 scripts/dag_ctl.py
工作目录：C:\Users\Du200\Projects\alphasentinel-codex（只在此目录写文件）。
参考 spec：C:\Users\Du200\Projects\alphasentinel-codex\docs\spec\AlphaSentinel_方案全文.txt 中“任务包 TASK-01”一节（约第 78–252 行）。
要求：
- scripts/dag_ctl.py：SQLite 账本 state/dag_state.db，表含 task_id, seq, owner, depends_on(JSON), artifact, verify_cmd, status, attempts, last_exit_code。预置 TASK-01..TASK-09（照 spec 的 9 行）。
- 子命令：init、status（打印表）、verify --task ID（若依赖未 PASSED 则拒绝；运行 verify_cmd，退出码 0 → PASSED，否则 attempts+1，>=3 → BLOCKED）。
- 不要做产物 SHA-256 哈希、签名或其它 spec 外机制。数据库路径可用 --db 覆盖。
- tests/test_dag_ctl.py：用 tempfile.TemporaryDirectory，覆盖 init/status/依赖拒绝/成功/失败计数/BLOCKED。verify_cmd 用 python -c "..." 这类跨平台命令测试。
- state/ 加进 .gitignore。
通过标准：uv run python -m pytest -q 与 uv run ruff check . 全部 0。
禁止：联网、运行 TEST 数据、编造数字。完成后提交一次 "A01 dag_ctl"。报告写 worktree 根目录 A01_report.md（不提交）。

