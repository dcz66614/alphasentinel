# 调度注意事项（silicon control / TechPulse-AI 教训 + 本项目）
1. grok：.cmd + `< NUL` 启动，日志末行 `EXIT <code>`；静默 10–20 分钟可能在思考，30 分钟无文件改动才算卡住。
2. copilot：`--add-dir` 加 worktree 和 .orchestra；在 worktree 里跑 `python -m pytest`；diff 方向 base..head（head 为新）；每次审查约 0.5–1.2 AI credits；出现免费额度用尽或收费提示立刻停，不换模型，报告负责人。
3. opencode：worktree 外读写会被 auto-reject（A01 attempt1），spec 用 worktree 内 docs/spec；报告写 worktree 根目录不提交。TechPulse 发现直接从 PowerShell 启动约 24s 退出——本项目用 Start-Process 隐藏窗口启动 .ps1 能跑完（A00/A01），若出问题改 .cmd + `< NUL`。
4. 编码：UTF-8 无 BOM（PS5 Set-Content -Encoding utf8 带 BOM，用 [IO.File]::WriteAllText）；提交前统一换行（.gitattributes）。
5. 进程：只管理自己启动的 PID（PIDS.md），不动负责人的 codex/agy/opencode-serve/空闲 grok（opencode PID 17320 是负责人的）。一次性计划任务用完删除。
6. prompt 写明禁止运行 TEST 集（适用时）。agy 必须带 `--dangerously-skip-permissions`。
7. dsh headless：Qwen3.8-Flash 不支持 high，需 --patch 改 medium；即便如此仍 CONTEXT_WINDOW_EXCEEDED → 直接调中转 Base URL（OpenAI 兼容）或 opencode wb provider。
8. 付费：禁止官方付费 API；WorkBuddy 付费上限 175 credits（CREDIT_LEDGER.md）。
9. 关机：2026-10-28 09:59 计划任务 AlphaSentinel_Shutdown_1000 → 10:00 关机。09:30 后不派新任务，09:50 前提交并写 HANDOFF.md。
10. 电源：2026-10-27 23:50 执行 powercfg /change standby-timeout-ac 0 与 hibernate-timeout-ac 0。执行前 AC 待机/休眠超时读数均为 0（已是不休眠，之前的睡眠可能来自合盖/手动），因此交接时无需恢复。
11. copilot --deny-tool write does not stop shell Set-Content: reviewer overwrote A10_report.md. In review prompts, forbid writing any file; keep report copies.
