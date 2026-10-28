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
    assert len(app.metric) == 0


def test_placeholder_database_renders_tables_and_chart(tmp_path, monkeypatch) -> None:
    db_path = tmp_path / "placeholder.duckdb"
    init_db(db_path)
    _insert_placeholder_rows(db_path)

    app = _run_dashboard(db_path, monkeypatch)

    assert len(app.dataframe) == 2
    assert app.selectbox[0].value == "PLACEHOLDER"
    shown = {item.label: item.value for item in app.metric}
    assert shown == {
        "Monitored Equities": "1",
        "Verified AI-ROI Leaders": "0",
        "AI-Washing / Watch Alerts": "0",
        "High Manipulation Risk (M > -1.78)": "1",
    }


def _insert_score(db_path, **overrides: object) -> None:
    row: dict[str, object] = {
        "ticker": "AAA",
        "company_name": "Placeholder Co",
        "sector": "Placeholder",
        "fiscal_year": 2024,
        "data_source_mode": "PLACEHOLDER",
        "altman_zone": "PLACEHOLDER",
        "beneish_flag": "PLACEHOLDER",
        "piotroski_tier": "PLACEHOLDER",
        "ai_washing_status": "PLACEHOLDER",
        "computed_at": "2026-01-01T00:00:00Z",
        "ai_washing_score": None,
        "beneish_m_score": None,
    }
    row.update(overrides)
    columns = list(row)
    connection = duckdb.connect(str(db_path))
    try:
        connection.execute(
            f"INSERT INTO forensic_scores ({', '.join(columns)}) "
            f"VALUES ({', '.join('?' for _ in columns)})",
            [row[name] for name in columns],
        )
    finally:
        connection.close()


def test_portfolio_kpis_ignore_null_scores(tmp_path, monkeypatch) -> None:
    db_path = tmp_path / "scores.duckdb"
    init_db(db_path)
    _insert_score(
        db_path,
        ticker="AAA",
        ai_washing_status="VERIFIED_AI_ROI",
        ai_washing_score=10.0,
        beneish_m_score=-2.0,
    )
    _insert_score(
        db_path,
        ticker="BBB",
        ai_washing_status="WATCH",
        ai_washing_score=40.0,
        beneish_m_score=-1.0,
    )
    _insert_score(
        db_path,
        ticker="CCC",
        ai_washing_status="AI-Washing inputs are incomplete",
        ai_washing_score=None,
        beneish_m_score=None,
    )

    app = _run_dashboard(db_path, monkeypatch)

    shown = {item.label: item.value for item in app.metric}
    assert shown["Monitored Equities"] == "3"
    assert shown["Verified AI-ROI Leaders"] == "1"
    assert shown["AI-Washing / Watch Alerts"] == "1"
    assert shown["High Manipulation Risk (M > -1.78)"] == "1"
