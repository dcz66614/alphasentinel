# 任务 A08 执行报告：TASK-08 四份交付文档生成器

## 1. 任务概述

按照规范 `docs/spec/AlphaSentinel_方案全文.txt` 中 TASK-08 与“第四部分”（`scripts/build_four_deliverables.py`）要求，完成了机构级四份交付文档的自动化生成与验证体系：
1. `deliverables/PROJECT_CHARTER.md`
2. `deliverables/PROJECT_CHARTER.docx`
3. `deliverables/AGENT_EXECUTION_PLAN.md`
4. `deliverables/AGENT_EXECUTION_PLAN.docx`

## 2. 核心模块设计与实现

### 2.1 交付文档编译与验证器 (`scripts/build_four_deliverables.py`)
- **方案内容抽取 (`extract_spec_deliverables`)**：
  - 动态从 `docs/spec/AlphaSentinel_方案全文.txt` 中抽取 `PROJECT_CHARTER_MD` 与 `AGENT_EXECUTION_PLAN_MD` 原文内容。
  - 内置规范基准兜底模板，确保在隔离沙盒或无外部文件时仍具确定性回退能力。
  - **绝不编造数据原则**：严格复用方案原文已有的数学公式（Beneish 8 变量 M-Score 系数、Altman Z-Score 阈值、Piotroski 9 维指标、AI-Washing 评分标准）、EARS 需求项（REQ-ING-01 至 REQ-DEL-01）、Grok Bot 5 智能体配置与 TASK-01 ~ TASK-09 DAG 任务矩阵，杜绝编造任何统计数字。
- **排版渲染引擎 (`render_markdown_to_docx`)**：
  - 基于 `python-docx` 实现 Markdown 结构解析与 Word 文档排版。
  - **标题层级**：支持 Document Title（level 0）与各级 Heading（# -> level 1, ## -> level 2, ### -> level 3, #### -> level 4）。
  - **网格表格**：支持 Markdown 管道表格解析，设置 `Table Grid` 样式，表头单元格自动加粗。
  - **代码块字体**：识别 fenced code blocks（` ``` `），段落字体统一渲染为等宽代码字体 `Courier New`，保留代码与公式的清晰对齐。
  - **列表项**：识别 `- ` 语法，自动应用 Word 内置 `List Bullet` 样式。
- **验证检查门禁 (`verify_deliverables` & `--verify`)**：
  - 严格校验 4 个交付文件是否存在且为有效文件。
  - 校验文件大小非空（字节大小 >= 100 字节）。
  - 针对 `.docx` 文件执行 OpenXML ZIP 结构完整性校验与 `docx.Document` 反向读回解析校验，确保段落与表格结构无损坏。
- **CLI 命令行接口**：
  - 支持 `--out-dir` / `--output-dir`：自定义输出目录（支持测试环境 tempfile 隔离）。
  - 支持 `--spec-path` / `--spec`：自定义规范文件路径。
  - 支持 `--build` 与 `--verify`：支持单步生成、单步校验或结合生成校验。

### 2.2 基础库组件扩充 (`src/alphasentinel/report_compiler.py`)
- 按照方案规范在 `report_compiler.py` 中导出 `render_markdown_to_docx`，使研报编译模块与交付文档编译工具保持一致的渲染能力。

## 3. 测试套件设计 (`tests/test_deliverables.py`)

在 `tests/test_deliverables.py` 中构建了 9 项隔离测试，全量采用 pytest `tmp_path` 临时目录：
1. `test_build_and_verify_programmatic`：API 层面调用 `build_deliverables` 生成 4 个文件并进行校验。
2. `test_build_and_verify_convenience_function`：验证一体化便捷函数 `build_and_verify`。
3. `test_cli_generation_and_verify_in_temp_dir`：使用 `subprocess` 在 temp 目录中分别运行生成命令与 `--verify` 检查命令，断言退出码为 0。
4. `test_verify_fails_on_empty_directory`：验证 `--verify` 在空目录下正确拦截并返回退出码 1。
5. `test_verify_fails_on_corrupt_docx`：验证 docx 归档损坏或非合法 zip 时正确拦截并返回退出码 1。
6. `test_verify_fails_on_truncated_deliverable`：验证文件截断或过小时正确拦截。
7. `test_docx_structure_headings_tables_and_code_font`：通过 `python-docx` 读回生成的 docx，断言标题、表格（首行加粗）及等宽代码块字体（`Courier New`）符合规范。
8. `test_content_fidelity_and_zero_fabricated_numbers`：断言抽取的内容仅包含原文公式系数（-4.84, -1.78, 2.99, 1.81 等）与真实 Bot 职责，无编造数据。
9. `test_render_markdown_to_docx_standalone`：验证独立 Markdown 片段的 docx 渲染与读回。

## 4. 门禁验证结果

1. **测试套件运行**：
   ```bash
   uv run python -m pytest -q
   ```
   - 结果：`45 passed, 1 warning in 6.75s`（全量 45 个测试用例全部通过，零失败，未运行 TEST 数据集）。

2. **代码风格与规范检查**：
   ```bash
   uv run ruff check .
   ```
   - 结果：`All checks passed!`（零报错，完全符合 Ruff 规则）。

3. **文档生成与门禁自检**：
   ```bash
   uv run python scripts/build_four_deliverables.py --verify
   ```
   - 结果：
     - `[OK] Verified deliverable: deliverables\PROJECT_CHARTER.md (2534 bytes)`
     - `[OK] Verified deliverable: deliverables\PROJECT_CHARTER.docx (38415 bytes)`
     - `[OK] Verified deliverable: deliverables\AGENT_EXECUTION_PLAN.md (1967 bytes)`
     - `[OK] Verified deliverable: deliverables\AGENT_EXECUTION_PLAN.docx (37849 bytes)`
     - 退出码 0。
