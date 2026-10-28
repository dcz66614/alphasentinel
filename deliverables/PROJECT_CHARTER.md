# Project AlphaSentinel — Complete Project Charter (项目书)

## 1. Executive Summary & Project Identity
- **Project Name**: Project AlphaSentinel (阿尔法哨兵：全自动美股 SEC 财报法务级会计排雷与 AI 投资回报率对冲情报系统)
- **Document ID**: AS-CHARTER-2026-V1.0
- **Execution Mode**: 100% Autonomous AI Agent Execution on Grok Bot Cloud Computer (`/workspace/alphasentinel`), Zero Physical Hardware.
- **API Cost**: $0.00 (Free SEC EDGAR via `edgartools` + Yahoo Finance via `yfinance` + DuckDB/SQLite).

## 2. EARS Formal Functional Requirements

| Requirement ID | Domain | EARS Deterministic Specification | Acceptance Metric |
| :--- | :--- | :--- | :--- |
| REQ-ING-01 | SEC Ingestion | WHEN ingestion starts, THE SYSTEM SHALL set a compliant SEC User-Agent identity and pull multi-year 10-K financials. | 0 HTTP 403 errors; <=15s per ticker |
| REQ-ING-02 | Offline Fallback | IF external network is restricted, THE SYSTEM SHALL use the deterministic baseline fallback so build never fails. | 100% pipeline completion rate |
| REQ-NRM-01 | XBRL Normalization | WHEN parsing XBRL, THE SYSTEM SHALL map heterogeneous tags into canonical fields in DuckDB. | 100% non-null completeness |
| REQ-QNT-01 | Forensic Models | WHEN financials load, THE SYSTEM SHALL compute Altman Z-Score, Beneish M-Score, and Piotroski F-Score. | Precision error < 1e-4 |
| REQ-QNT-02 | AI-Washing Index | WHEN evaluating AI ROI, THE SYSTEM SHALL contrast 10-K AI keyword density against YoY EBIT margin changes and Form 4 insider selling. | Flags divergence >= 60.0 |
| REQ-DEL-01 | Dual Deliverables | WHEN verification passes, THE SYSTEM SHALL output both Markdown (.md) and Microsoft Word (.docx) deliverables and start FastAPI/Streamlit. | Valid OpenXML .docx archives |

## 3. Forensic Mathematical Models
### 3.1 Beneish 8-Variable M-Score
```text
M = -4.84 + 0.920*DSRI + 0.528*GMI + 0.404*AQI + 0.892*SGI + 0.115*DEPI - 0.172*SGAI + 4.679*TATA - 0.327*LVGI
```
- **Threshold**: `M > -1.78` flags `MANIPULATION_RISK_HIGH`; `M <= -1.78` is `NORMAL`.

### 3.2 Altman Z-Score
```text
Z = 1.2*(WC/TA) + 1.4*(RE/TA) + 3.3*(EBIT/TA) + 0.6*(MCAP/TL) + 1.0*(REV/TA)
```
- **Thresholds**: `Z > 2.99` SAFE; `1.81 <= Z <= 2.99` GREY; `Z < 1.81` DISTRESS.

### 3.3 Piotroski 9-Point F-Score & AI-Washing Divergence Index
Evaluates 9 binary fundamental improvement signals (0-9) and contrasts AI narrative frequency against YoY EBIT margin expansion/contraction and insider selling ratio.