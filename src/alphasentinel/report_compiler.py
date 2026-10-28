"""Compile the stored forensic scores into Markdown and Word reports."""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any

import duckdb
from docx import Document

from alphasentinel.db_schema import DEFAULT_DUCKDB_PATH

_REPORT_NAME = "AlphaSentinel_Report"
_SUMMARY_FIELDS = (
    ("ticker", "Ticker", "text"),
    ("company_name", "Company", "text"),
    ("fiscal_year", "Fiscal Year", "integer"),
    ("altman_z_score", "Altman Z", "decimal"),
    ("altman_zone", "Altman Zone", "text"),
    ("beneish_m_score", "Beneish M", "decimal"),
    ("beneish_flag", "Beneish Flag", "text"),
    ("piotroski_f_score", "Piotroski F", "integer"),
    ("piotroski_tier", "Piotroski Tier", "text"),
    ("ebit_margin_pct", "EBIT Margin (%)", "decimal"),
    ("ebit_margin_yoy_change_bps", "YoY EBIT (bps)", "decimal"),
    ("ai_washing_score", "AI-Washing Score", "decimal"),
    ("ai_washing_status", "AI-Washing Status", "text"),
)
_FACTOR_FIELDS = (
    ("ticker", "Ticker", "text"),
    ("fiscal_year", "Fiscal Year", "integer"),
    ("dsri", "DSRI", "factor"),
    ("gmi", "GMI", "factor"),
    ("aqi", "AQI", "factor"),
    ("sgi", "SGI", "factor"),
    ("depi", "DEPI", "factor"),
    ("sgai", "SGAI", "factor"),
    ("lvgi", "LVGI", "factor"),
    ("tata", "TATA", "factor"),
)


def _load_scores(db_path: Path | str) -> list[dict[str, Any]]:
    connection = duckdb.connect(str(db_path), read_only=True)
    try:
        cursor = connection.execute("SELECT * FROM forensic_scores ORDER BY ticker, fiscal_year")
        names = [column[0] for column in cursor.description]
        return [dict(zip(names, row, strict=True)) for row in cursor.fetchall()]
    finally:
        connection.close()


def _display(value: Any, kind: str) -> str:
    if value is None:
        return "数据不足（数据库字段为 NULL）"
    if kind == "decimal":
        return f"{value:.2f}"
    if kind == "factor":
        return f"{value:.3f}"
    return str(value)


def _escape_cell(value: str) -> str:
    return value.replace("|", "\\|").replace("\n", " ")


def _markdown_table(
    rows: list[dict[str, Any]], fields: tuple[tuple[str, str, str], ...]
) -> list[str]:
    lines = [
        "| " + " | ".join(label for _, label, _ in fields) + " |",
        "| " + " | ".join("---" for _ in fields) + " |",
    ]
    for row in rows:
        cells = [_escape_cell(_display(row[name], kind)) for name, _, kind in fields]
        lines.append("| " + " | ".join(cells) + " |")
    return lines


def _build_markdown(rows: list[dict[str, Any]]) -> str:
    lines = [
        "# AlphaSentinel Institutional Forensic & AI-ROI Briefing",
        "",
        "本报告仅呈现 DuckDB 中已存储的数据。指标为 NULL 时显示数据不足，不填补或推算数值。",
        "",
        "## 1. Executive Summary & Cross-Portfolio Risk Matrix",
        "",
    ]
    if not rows:
        lines.extend(["无数据：forensic_scores 表为空。", ""])
    else:
        lines.extend(_markdown_table(rows, _SUMMARY_FIELDS))
        lines.append("")

    lines.extend(["## 2. Beneish 8-Factor Forensic Decomposition", ""])
    if not rows:
        lines.append("无数据：forensic_scores 表为空。")
    else:
        lines.extend(_markdown_table(rows, _FACTOR_FIELDS))
    return "\n".join(lines) + "\n"


def _add_docx_table(
    document: Document,
    rows: list[dict[str, Any]],
    fields: tuple[tuple[str, str, str], ...],
) -> None:
    table = document.add_table(rows=1, cols=len(fields))
    table.style = "Table Grid"
    for index, (_, label, _) in enumerate(fields):
        table.rows[0].cells[index].text = label
        for run in table.rows[0].cells[index].paragraphs[0].runs:
            run.bold = True
    for row in rows:
        cells = table.add_row().cells
        for index, (name, _, kind) in enumerate(fields):
            cells[index].text = _display(row[name], kind)


def _write_docx(rows: list[dict[str, Any]], path: Path) -> None:
    document = Document()
    document.add_heading("AlphaSentinel Institutional Forensic & AI-ROI Briefing", level=0)
    document.add_paragraph(
        "本报告仅呈现 DuckDB 中已存储的数据。指标为 NULL 时显示数据不足，不填补或推算数值。"
    )
    document.add_heading("1. Executive Summary & Cross-Portfolio Risk Matrix", level=1)
    if rows:
        _add_docx_table(document, rows, _SUMMARY_FIELDS)
    else:
        document.add_paragraph("无数据：forensic_scores 表为空。")
    document.add_heading("2. Beneish 8-Factor Forensic Decomposition", level=1)
    if rows:
        _add_docx_table(document, rows, _FACTOR_FIELDS)
    else:
        document.add_paragraph("无数据：forensic_scores 表为空。")
    document.save(path)


def compile_report(
    db_path: Path | str = DEFAULT_DUCKDB_PATH,
    out_dir: Path | str = Path("reports"),
) -> dict[str, Path]:
    """Read the warehouse and write both report formats."""
    output_directory = Path(out_dir)
    output_directory.mkdir(parents=True, exist_ok=True)
    rows = _load_scores(db_path)
    markdown_path = output_directory / f"{_REPORT_NAME}.md"
    docx_path = output_directory / f"{_REPORT_NAME}.docx"
    markdown_path.write_text(_build_markdown(rows), encoding="utf-8")
    _write_docx(rows, docx_path)
    return {"md": markdown_path, "docx": docx_path}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db", type=Path, default=DEFAULT_DUCKDB_PATH)
    parser.add_argument("--out", type=Path, default=Path("reports"))
    arguments = parser.parse_args()
    paths = compile_report(arguments.db, arguments.out)
    print(f"Markdown: {paths['md']}")
    print(f"Word: {paths['docx']}")


if __name__ == "__main__":
    main()
