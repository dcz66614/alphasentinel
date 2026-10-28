"""Dashboard smoke tests with temporary placeholder warehouses only."""

from __future__ import annotations

import py_compile
from pathlib import Path

import duckdb
from streamlit.testing.v1 import AppTest

from alphasentinel.db_schema import init_db

_DASHBOARD = Path(__file__).parents[1] / "src" / "alphasentinel" / "dashboard.py"


def _insert_placeholder_rows(db_path) -> None:
    connection = duckdb.connect(str(db_path))
    try:
        for table in ("company_financials", "forensic_scores"):
            columns = connection.execute(
                """
                SELECT column_name, upper(data_type)
                FROM information_schema.columns
                WHERE table_schema = 'main' AND table_name = ?
                ORDER BY ordinal_position
                """,
                [table],
            ).fetchall()
            values = [
                {"VARCHAR": "PLACEHOLDER", "INTEGER": 0, "DOUBLE": 0.0}[data_type]
                for _, data_type in columns
            ]
            connection.execute(
                f"INSERT INTO {table} VALUES ({', '.join('?' for _ in values)})",
                values,
            )
    finally:
        connection.close()


def _run_dashboard(db_path, monkeypatch) -> AppTest:
    monkeypatch.setenv("ALPHASENTINEL_DB", str(db_path))
    app = AppTest.from_file(_DASHBOARD)
    app.run()
    assert not app.exception
    return app


def test_dashboard_compiles() -> None:
    py_compile.compile(str(_DASHBOARD), doraise=True)


def test_empty_database_shows_no_data(tmp_path, monkeypatch) -> None:
    db_path = tmp_path / "empty.duckdb"
    init_db(db_path)

    app = _run_dashboard(db_path, monkeypatch)

    assert any(item.value == "无数据" for item in app.warning)


def test_placeholder_database_renders_tables_and_chart(tmp_path, monkeypatch) -> None:
    db_path = tmp_path / "placeholder.duckdb"
    init_db(db_path)
    _insert_placeholder_rows(db_path)

    app = _run_dashboard(db_path, monkeypatch)

    assert len(app.dataframe) == 2
    assert app.selectbox[0].value == "PLACEHOLDER"
