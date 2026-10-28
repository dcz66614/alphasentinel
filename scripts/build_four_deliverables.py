#!/usr/bin/env python3
"""
scripts/build_four_deliverables.py
Dual-Format Institutional Deliverable Generator and Verifier for Project AlphaSentinel:
1. deliverables/PROJECT_CHARTER.md
2. deliverables/PROJECT_CHARTER.docx
3. deliverables/AGENT_EXECUTION_PLAN.md
4. deliverables/AGENT_EXECUTION_PLAN.docx
"""

from __future__ import annotations

import argparse
import re
import sys
import zipfile
from pathlib import Path

import docx
from docx.shared import Pt

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DELIVERABLES_DIR = PROJECT_ROOT / "deliverables"
DEFAULT_SPEC_PATH = PROJECT_ROOT / "docs" / "spec" / "AlphaSentinel_方案全文.txt"

# Canonical extracted templates from docs/spec/AlphaSentinel_方案全文.txt
_FALLBACK_CHARTER_MD = """# Project AlphaSentinel — Complete Project Charter (项目书)

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
"""

_FALLBACK_PLAN_MD = """# Project AlphaSentinel — Zero-Thinking Agent Execution Plan (确定性执行计划书)

## 1. Grok Bot 5-Agent Roster & Single-Threaded Write Ownership

| Task ID | Assigned Grok Bot | Owned Artifact Path | Deterministic Verification Command |
| :--- | :--- | :--- | :--- |
| TASK-01 | @CommanderBot | scripts/dag_ctl.py | python3 scripts/dag_ctl.py status |
| TASK-02 | @SpecArchitectBot | src/db_schema.py | pytest tests/test_schema.py |
| TASK-03 | @DataEngineBot | src/ingestor.py | pytest tests/test_ingestor.py |
| TASK-04 | @QuantForensicBot | src/forensic_engine.py | pytest tests/test_forensic.py |
| TASK-05 | @UIAndReportBot | src/report_compiler.py | pytest tests/test_reports.py |
| TASK-06 | @UIAndReportBot | src/api_server.py | pytest tests/test_api.py |
| TASK-07 | @UIAndReportBot | src/dashboard.py | python3 -m py_compile src/dashboard.py |
| TASK-08 | @UIAndReportBot | deliverables/PROJECT_CHARTER.docx | python3 scripts/build_four_deliverables.py --verify |
| TASK-09 | @CommanderBot | reports/AlphaSentinel_Executive_Briefing.docx | python3 scripts/run_pipeline.py --verify-all |

## 2. Hard Operational Rules & Guardrails
- **Max Retries**: Every task in `state/dag_state.db` is capped at `max_attempts = 3`.
- **Single-Threaded Writes**: Never edit a file owned by another Bot.
- **Handoff Protocol**: Only post a Group Chat `@BotName` handoff after `dag_ctl.py verify --task TASK-XX` returns exit code 0.
- **Routine Scheduling**: Once TASK-09 passes, @CommanderBot saves the workflow as Skill `AlphaSentinel-Daily-Audit` and schedules Routine at 08:00 UTC weekdays with Auto-review set to `Ask first` for any external publishing.

## 3. Machine Constitution & Operational Commands

```text
Activate Virtualenv: source .venv/bin/activate
Check DAG Status: python scripts/dag_ctl.py status
Run All Tests: pytest tests/ -v --tb=short
Compile Deliverables: python scripts/build_four_deliverables.py --verify
```
"""


def extract_spec_deliverables(spec_path: Path | str | None = None) -> tuple[str, str]:
    """Extract Project Charter and Execution Plan Markdown contents from the spec text."""
    target_path = Path(spec_path) if spec_path else DEFAULT_SPEC_PATH
    if target_path.is_file():
        text = target_path.read_text(encoding="utf-8")
        m_charter = re.search(r'PROJECT_CHARTER_MD\s*=\s*"""(.*?)"""', text, re.DOTALL)
        m_plan = re.search(r'AGENT_EXECUTION_PLAN_MD\s*=\s*"""(.*?)"""', text, re.DOTALL)
        charter = m_charter.group(1).strip() if m_charter else ""
        plan = m_plan.group(1).strip() if m_plan else ""

        if charter and plan:
            # Format mathematical formulas as code blocks for monospace rendering if not fenced
            if "```" not in charter and "M = -4.84" in charter:
                charter = charter.replace(
                    "M = -4.84 + 0.920*DSRI + 0.528*GMI + 0.404*AQI + 0.892*SGI + 0.115*DEPI - 0.172*SGAI + 4.679*TATA - 0.327*LVGI.\nThreshold: M > -1.78 flags MANIPULATION_RISK_HIGH; M <= -1.78 is NORMAL.",
                    "```text\nM = -4.84 + 0.920*DSRI + 0.528*GMI + 0.404*AQI + 0.892*SGI + 0.115*DEPI - 0.172*SGAI + 4.679*TATA - 0.327*LVGI\n```\n- **Threshold**: `M > -1.78` flags `MANIPULATION_RISK_HIGH`; `M <= -1.78` is `NORMAL`.",
                )
                charter = charter.replace(
                    "Z = 1.2*(WC/TA) + 1.4*(RE/TA) + 3.3*(EBIT/TA) + 0.6*(MCAP/TL) + 1.0*(REV/TA).\nThresholds: Z > 2.99 SAFE; 1.81 <= Z <= 2.99 GREY; Z < 1.81 DISTRESS.",
                    "```text\nZ = 1.2*(WC/TA) + 1.4*(RE/TA) + 3.3*(EBIT/TA) + 0.6*(MCAP/TL) + 1.0*(REV/TA)\n```\n- **Thresholds**: `Z > 2.99` SAFE; `1.81 <= Z <= 2.99` GREY; `Z < 1.81` DISTRESS.",
                )

            # Ensure execution plan has operational commands code block
            if "```" not in plan:
                plan += (
                    "\n\n## 3. Machine Constitution & Operational Commands\n\n```text\n"
                    "Activate Virtualenv: source .venv/bin/activate\n"
                    "Check DAG Status: python scripts/dag_ctl.py status\n"
                    "Run All Tests: pytest tests/ -v --tb=short\n"
                    "Compile Deliverables: python scripts/build_four_deliverables.py --verify\n"
                    "```"
                )
            return charter, plan

    return _FALLBACK_CHARTER_MD, _FALLBACK_PLAN_MD


def render_markdown_to_docx(
    markdown_text: str, output_docx_path: Path, title: str | None = None
) -> Path:
    """Render structured Markdown (headings, tables, code blocks, lists) into a .docx file."""
    output_docx_path.parent.mkdir(parents=True, exist_ok=True)
    doc = docx.Document()
    if title:
        doc.add_heading(title, level=0)

    lines = markdown_text.splitlines()
    i = 0
    in_code_block = False
    code_buffer: list[str] = []

    while i < len(lines):
        line = lines[i]
        stripped = line.strip()

        if stripped.startswith("```"):
            if not in_code_block:
                in_code_block = True
                code_buffer = []
            else:
                in_code_block = False
                p = doc.add_paragraph()
                p.paragraph_format.space_before = Pt(4)
                p.paragraph_format.space_after = Pt(4)
                run = p.add_run("\n".join(code_buffer))
                run.font.name = "Courier New"
                run.font.size = Pt(9.5)
            i += 1
            continue

        if in_code_block:
            code_buffer.append(line)
            i += 1
            continue

        if stripped.startswith("|") and stripped.endswith("|"):
            table_rows: list[list[str]] = []
            while (
                i < len(lines)
                and lines[i].strip().startswith("|")
                and lines[i].strip().endswith("|")
            ):
                row_str = lines[i].strip()
                content = row_str.replace("|", "").replace("-", "").replace(":", "").strip()
                if content:
                    cells = [c.strip() for c in row_str.strip("|").split("|")]
                    table_rows.append(cells)
                i += 1
            if table_rows:
                num_cols = max(len(r) for r in table_rows)
                tbl = doc.add_table(rows=len(table_rows), cols=num_cols)
                tbl.style = "Table Grid"
                for r_idx, r_cells in enumerate(table_rows):
                    for c_idx in range(min(len(r_cells), num_cols)):
                        cell_obj = tbl.cell(r_idx, c_idx)
                        cell_obj.text = r_cells[c_idx]
                        if r_idx == 0:
                            for p in cell_obj.paragraphs:
                                for r in p.runs:
                                    r.bold = True
            continue

        if stripped.startswith("# "):
            if not title:
                doc.add_heading(stripped[2:], level=0)
            else:
                doc.add_heading(stripped[2:], level=1)
        elif stripped.startswith("## "):
            doc.add_heading(stripped[3:], level=2)
        elif stripped.startswith("### "):
            doc.add_heading(stripped[4:], level=3)
        elif stripped.startswith("#### "):
            doc.add_heading(stripped[5:], level=4)
        elif stripped.startswith("- "):
            doc.add_paragraph(stripped[2:], style="List Bullet")
        elif stripped:
            doc.add_paragraph(stripped)

        i += 1

    if in_code_block and code_buffer:
        p = doc.add_paragraph()
        p.paragraph_format.space_before = Pt(4)
        p.paragraph_format.space_after = Pt(4)
        run = p.add_run("\n".join(code_buffer))
        run.font.name = "Courier New"
        run.font.size = Pt(9.5)

    doc.save(str(output_docx_path))
    return output_docx_path


def build_deliverables(
    out_dir: Path | str = DEFAULT_DELIVERABLES_DIR,
    spec_path: Path | str | None = None,
) -> dict[str, Path]:
    """Generate all 4 institutional deliverable files (.md + .docx)."""
    output_dir = Path(out_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    charter_md, plan_md = extract_spec_deliverables(spec_path)

    charter_md_path = output_dir / "PROJECT_CHARTER.md"
    charter_docx_path = output_dir / "PROJECT_CHARTER.docx"
    plan_md_path = output_dir / "AGENT_EXECUTION_PLAN.md"
    plan_docx_path = output_dir / "AGENT_EXECUTION_PLAN.docx"

    charter_md_path.write_text(charter_md, encoding="utf-8")
    plan_md_path.write_text(plan_md, encoding="utf-8")

    render_markdown_to_docx(
        charter_md,
        charter_docx_path,
        title="Project AlphaSentinel — Project Charter (项目书)",
    )
    render_markdown_to_docx(
        plan_md,
        plan_docx_path,
        title="Project AlphaSentinel — Agent Execution Plan (执行计划书)",
    )

    return {
        "charter_md": charter_md_path,
        "charter_docx": charter_docx_path,
        "plan_md": plan_md_path,
        "plan_docx": plan_docx_path,
    }


def verify_deliverables(out_dir: Path | str = DEFAULT_DELIVERABLES_DIR) -> int:
    """Verify that all 4 deliverable files exist, are non-empty, and docx can be read back."""
    target_dir = Path(out_dir)
    expected_files = [
        target_dir / "PROJECT_CHARTER.md",
        target_dir / "PROJECT_CHARTER.docx",
        target_dir / "AGENT_EXECUTION_PLAN.md",
        target_dir / "AGENT_EXECUTION_PLAN.docx",
    ]

    for fp in expected_files:
        if not fp.exists() or not fp.is_file():
            print(f"[FAIL] Deliverable missing: {fp}")
            return 1

        size = fp.stat().st_size
        if size < 100:
            print(f"[FAIL] Deliverable empty or truncated ({size} bytes): {fp}")
            return 1

        if fp.suffix == ".docx":
            if not zipfile.is_zipfile(fp):
                print(f"[FAIL] Invalid OpenXML .docx archive: {fp}")
                return 1
            try:
                doc = docx.Document(str(fp))
                if len(doc.paragraphs) == 0 and len(doc.tables) == 0:
                    print(f"[FAIL] Deliverable docx contains no content: {fp}")
                    return 1
            except (
                zipfile.BadZipFile,
                docx.opc.exceptions.PackageNotFoundError,
                KeyError,
                ValueError,
                IndexError,
                OSError,
            ) as exc:
                print(f"[FAIL] Cannot read back docx {fp}: {exc}")
                return 1

        print(f"[OK] Verified deliverable: {fp} ({size} bytes)")

    return 0


def build_and_verify(
    out_dir: Path | str = DEFAULT_DELIVERABLES_DIR,
    spec_path: Path | str | None = None,
) -> int:
    """Build all 4 deliverables and verify them in a single call."""
    build_deliverables(out_dir, spec_path=spec_path)
    return verify_deliverables(out_dir)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Generate and verify the 4 mandatory AlphaSentinel deliverables."
    )
    parser.add_argument(
        "--out-dir",
        "--output-dir",
        dest="out_dir",
        type=Path,
        default=DEFAULT_DELIVERABLES_DIR,
        help="Directory where deliverables are written/verified (default: deliverables/)",
    )
    parser.add_argument(
        "--spec-path",
        "--spec",
        dest="spec_path",
        type=Path,
        default=DEFAULT_SPEC_PATH,
        help="Path to AlphaSentinel spec text file",
    )
    parser.add_argument(
        "--verify",
        action="store_true",
        help="Verify deliverables exist, are non-empty, and docx can be read back",
    )
    parser.add_argument(
        "--build",
        action="store_true",
        help="Build deliverables (default if --verify is not passed)",
    )

    args = parser.parse_args(argv)

    out_dir = args.out_dir.resolve()
    spec_path = args.spec_path.resolve() if args.spec_path else None

    # If --verify was explicitly requested without --build, run verification only
    if args.verify and not args.build:
        return verify_deliverables(out_dir)

    # Build deliverables
    build_deliverables(out_dir, spec_path=spec_path)

    # If --verify was also requested along with build
    if args.verify:
        return verify_deliverables(out_dir)

    print(f"[OK] All 4 deliverables successfully built in {out_dir}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
