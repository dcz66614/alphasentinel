"""Report round-trip tests using only placeholder rows, never the TEST data set."""

from __future__ import annotations

import subprocess
import sys

import duckdb
from docx import Document

from alphasentinel.db_schema import init_db
from alphasentinel.report_compiler import compile_report


def _insert_placeholder(db_path, ai_washing_score=0.0) -> None:
    connection = duckdb.connect(str(db_path))
    try:
        columns = connection.execute(
            """
            SELECT column_name, upper(data_type)
            FROM information_schema.columns
            WHERE table_schema = 'main' AND table_name = 'forensic_scores'
            ORDER BY ordinal_position
            """
        ).fetchall()
        values = [
            {"VARCHAR": "PLACEHOLDER", "INTEGER": 0, "DOUBLE": 0.0}[data_type]
            for _, data_type in columns
        ]
        values[[name for name, _ in columns].index("ai_washing_score")] = ai_washing_score
        connection.execute(
            f"INSERT INTO forensic_scores VALUES ({', '.join('?' for _ in values)})",
            values,
        )
    finally:
        connection.close()


def _docx_text(path) -> str:
    document = Document(path)
    paragraphs = [paragraph.text for paragraph in document.paragraphs]
    cells = [cell.text for table in document.tables for row in table.rows for cell in row.cells]
    return "\n".join(paragraphs + cells)


def test_placeholder_round_trip_in_both_formats(tmp_path) -> None:
    db_path = tmp_path / "report.duckdb"
    init_db(db_path)
    _insert_placeholder(db_path, ai_washing_score=17.25)

    paths = compile_report(db_path, tmp_path / "reports")

    assert paths["md"].name == "AlphaSentinel_Report.md"
    assert "17.25" in paths["md"].read_text(encoding="utf-8")
    assert "PLACEHOLDER" in paths["md"].read_text(encoding="utf-8")
    assert "17.25" in _docx_text(paths["docx"])


def test_null_metric_explains_insufficient_data(tmp_path) -> None:
    db_path = tmp_path / "report.duckdb"
    init_db(db_path)
    connection = duckdb.connect(str(db_path))
    try:
        connection.execute("ALTER TABLE forensic_scores ALTER ai_washing_score DROP NOT NULL")
    finally:
        connection.close()
    _insert_placeholder(db_path, ai_washing_score=None)

    paths = compile_report(db_path, tmp_path / "reports")

    assert "数据不足（数据库字段为 NULL）" in paths["md"].read_text(encoding="utf-8")
    assert "数据不足（数据库字段为 NULL）" in _docx_text(paths["docx"])


def test_empty_table_reports_no_data(tmp_path) -> None:
    db_path = tmp_path / "empty.duckdb"
    init_db(db_path)

    paths = compile_report(db_path, tmp_path / "reports")

    assert "无数据：forensic_scores 表为空" in paths["md"].read_text(encoding="utf-8")
    assert "无数据：forensic_scores 表为空" in _docx_text(paths["docx"])


def test_cli_accepts_database_and_output_paths(tmp_path) -> None:
    db_path = tmp_path / "cli.duckdb"
    init_db(db_path)

    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "alphasentinel.report_compiler",
            "--db",
            str(db_path),
            "--out",
            str(tmp_path / "cli-reports"),
        ],
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, result.stderr
    assert (tmp_path / "cli-reports" / "AlphaSentinel_Report.md").is_file()
    assert (tmp_path / "cli-reports" / "AlphaSentinel_Report.docx").is_file()
