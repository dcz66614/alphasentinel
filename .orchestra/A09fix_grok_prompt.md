# 任务 A09fix：修复 A09 真实运行失败
工作目录：C:\Users\Du200\Projects\alphasentinel-codex（只在此目录写文件）。上一轮报告：C:\Users\Du200\Projects\alphasentinel\.orchestra\A09_report.md（只读参考）。
问题：真实联网运行时 META 的 companyfacts 规范化失败，整条流水线在写库前退出；因此 Executive Briefing 未生成，--verify-all 中 TASK-09 FAILED。
要求：
1. 用 data/cache 中已下载的真实 META 数据定位失败原因。如果是科目映射/期间对齐的真实缺陷（例如 META 使用不同 XBRL 标签），按 SEC 原始标签修正映射，并加基于真实片段的回归测试（片段放 tests/fixtures 并在 README 写来源）。
2. 单只股票真实缺数据时：记录该股失败原因，其余股票继续，报告里列出失败股票及原因；绝不补零、插值或编造。
3. 重新联网（或 --offline 用真实缓存）完整运行 10 只，再跑 --verify-all。报告中的所有数字必须从本次命令输出原样贴出。
不加 spec 外机制；禁止运行 TEST 集。通过标准：pytest、ruff 0；流水线和 --verify-all 退出码 0，或如实说明剩余真实数据缺口。提交 "A09fix pipeline real run"。报告写 C:\Users\Du200\Projects\alphasentinel-codex\A09fix_report.md（不提交）。