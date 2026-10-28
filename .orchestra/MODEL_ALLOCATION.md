# 模型分配（2026-10-27 更新；变更记录在此）

## 预算硬规则
- 禁止任何付费官方 API（环境里存在 DEEPSEEK_API_KEY / DASHSCOPE_API_KEY / MOONSHOT_API_KEY / KIMI_CN_API_KEY / LITELLM_API_KEY / OMNIROUTE_API_KEY / GEMINI_PROXY_API_KEY 等，一律不用）。
- WorkBuddy 中转付费额度：与 TechPulse-AI 共用 350，本项目上限 **175 credits**，整个项目用完即止。只用于核心公式/schema 逻辑和最难的审查，优先便宜档。每次付费调用记入 CREDIT_LEDGER.md（中转响应 usage.credit 字段；没有余额接口）。

## 默认分配
| 用途 | 首选 | 备选 |
|---|---|---|
| 批量/样板/小修复 | opencode `opencode/deepseek-v4.1-flash-free` | `wb/deepseek-v4.1-flash`（中转，credit=0） |
| 文档/文本 | `wb/deepseek-v4.1-flash` / glm-5.3-flash-free | agy gemini-3.8-flash-high |
| 核心模块 | Grok Build grok-4.7 high（包含额度） | 付费 wb kimi-k3.1-pro（计入 175） |
| 只读审查 | Copilot auto（包含额度） | 难审：付费 wb gpt-6.1-sol（计入 175） |

## 调用方式（Windows dcz666）
- opencode 免费：`opencode run -m opencode/deepseek-v4.1-flash-free --title <T> <prompt>`
- WorkBuddy 中转经 opencode：`<WORKBUDDY_KEY_REDACTED>` 从 `C:\Users\Du200\Downloads\workbuddy反代key.txt` 第一行读入（不打印）；`C:\Users\Du200\Projects\alphasentinel\.orchestra\opencode_wb.json='<repo>\.orchestra\opencode_wb.json'`；`opencode run -m wb/deepseek-v4.1-flash ...`。冒烟 2026-10-27 22:5x：/v1/models 68 个，deepseek-v4.1-flash 回 PONG，credit=0。
- Grok：`grok.exe -m grok-4.7 --reasoning-effort high --always-approve --prompt-file <p> < NUL`
- agy：`agy.exe --model gemini-3.8-flash-high --dangerously-skip-permissions -p <prompt>`
- Copilot：`copilot -p ... --allow-all-tools --deny-tool write --add-dir ...`
- dsh 本地 headless（qoder-proxy 127.0.0.1:8790）：默认 reasoningEffort=high 对 Qwen3.8-Flash 不支持；用 dsh_qwen38flash.patch.yml 改 medium 后仍报 CONTEXT_WINDOW_EXCEEDED（约150s），**暂不可用**。headless profile 没有 workbuddy-ai adapter（NO_ADAPTER），改走上面的中转。

## 订阅额度（放开用，遇额外收费提示即停）
- Grok Build：每周重置，稳定使用。
- Antigravity：每周额度 + 5 小时滚动窗口，分散到不同 5h 窗口。
- Copilot：总 200 AI credits 与 TechPulse-AI 共用，本项目上限 95 AIC（TechPulse-AI 95，silicon control 10）；每次审查约 1 AIC（已用：A00 1.07, A01 0.51, A02 0.96）。
