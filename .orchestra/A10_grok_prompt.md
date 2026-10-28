# 任务 A10：补齐 META/AMZN/PLTR/ORCL 的真实数据缺口
工作目录：C:\Users\Du200\Projects\alphasentinel-codex（只在此目录写文件）。参考：C:\Users\Du200\Projects\alphasentinel\.orchestra\A09fix_report.md（只读）。
现状：真实运行中 4 只失败：META shares_outstanding；AMZN rd_expense、total_liabilities；PLTR long_term_debt；ORCL cogs。
要求：
1. 对每个缺口，在 data/cache 的真实 SEC companyfacts 中查找公司实际使用的等价 us-gaap/dei 标签（例如 dei:EntityCommonStockSharesOutstanding、TechnologyAndInfrastructure/ResearchAndDevelopmentExpense 等），或可由真实已报告科目按会计恒等式严格推导的值（如 总负债 = 总资产 − 股东权益合计，仅当两者在同一期间均有报告；推导须在代码与报告中标注“derived”）。
2. 若某公司确实未报告该科目（如 PLTR 无长期债务），按 spec 允许的语义处理：只在 SEC 数据明确表明为零/不适用时才可记 0 并标注来源；否则保持该指标 NULL，但不应让整只股票失败——仅受影响的指标为 NULL。
3. 每条新映射配真实片段回归测试（fixtures + README 来源）。重新完整运行 10 只与 --verify-all，所有数字原样贴命令输出。
不编造、不插值；不加 spec 外机制；禁止运行 TEST 集。通过标准：pytest、ruff 0；流水线退出码 0（或如实说明）。提交 "A10 close data gaps"。报告写 C:\Users\Du200\Projects\alphasentinel-codex\A10_report.md（不提交）。生成的 deliverables/reports 不要提交。