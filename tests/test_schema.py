"""Warehouse schema tests.

Placeholder rows use ticker ``TEST`` and zero numeric fields so NOT NULL
columns can be written. Those zeros are not financial figures. The test only
checks that the written row can be read back.
"""

from __future__ import annotations

import tempfile
from pathlib import Path

import duckdb
import pytest

from alphasentinel.db_schema import DEFAULT_DUCKDB_PATH, get_duckdb_conn, init_db, validate_schema

COMPANY_FINANCIALS = (
    ("ticker", "VARCHAR"),
    ("company_name", "VARCHAR"),
    ("sector", "VARCHAR"),
    ("fiscal_year", "INTEGER"),
    ("filing_form", "VARCHAR"),
    ("filing_date", "VARCHAR"),
    ("data_source_mode", "VARCHAR"),
    ("revenue", "DOUBLE"),
    ("cogs", "DOUBLE"),
    ("sga", "DOUBLE"),
    ("rd_expense", "DOUBLE"),
    ("depreciation", "DOUBLE"),
    ("ebit", "DOUBLE"),
    ("net_income", "DOUBLE"),
    ("operating_cash_flow", "DOUBLE"),
    ("receivables", "DOUBLE"),
    ("current_assets", "DOUBLE"),
    ("ppe", "DOUBLE"),
    ("total_assets", "DOUBLE"),
    ("current_liabilities", "DOUBLE"),
    ("long_term_debt", "DOUBLE"),
    ("total_liabilities", "DOUBLE"),
    ("retained_earnings", "DOUBLE"),
    ("working_capital", "DOUBLE"),
    ("shares_outstanding", "DOUBLE"),
    ("market_cap", "DOUBLE"),
    ("ai_mention_count", "INTEGER"),
    ("total_word_count", "INTEGER"),
    ("insider_net_sell_ratio", "DOUBLE"),
)

FORENSIC_SCORES = (
    ("ticker", "VARCHAR"),
    ("company_name", "VARCHAR"),
    ("sector", "VARCHAR"),
    ("fiscal_year", "INTEGER"),
    ("data_source_mode", "VARCHAR"),
    ("altman_z_score", "DOUBLE"),
    ("altman_zone", "VARCHAR"),
    ("beneish_m_score", "DOUBLE"),
    ("beneish_flag", "VARCHAR"),
    ("piotroski_f_score", "INTEGER"),
    ("piotroski_tier", "VARCHAR"),
    ("ebit_margin_pct", "DOUBLE"),
    ("ebit_margin_yoy_change_bps", "DOUBLE"),
    ("revenue_growth_yoy_pct", "DOUBLE"),
    ("rd_to_revenue_pct", "DOUBLE"),
    ("ai_hype_score", "DOUBLE"),
    ("ai_roi_realization_score", "DOUBLE"),
    ("ai_washing_score", "DOUBLE"),
    ("ai_washing_status", "VARCHAR"),
    ("dsri", "DOUBLE"),
    ("gmi", "DOUBLE"),
    ("aqi", "DOUBLE"),
    ("sgi", "DOUBLE"),
    ("depi", "DOUBLE"),
    ("sgai", "DOUBLE"),
    ("lvgi", "DOUBLE"),
    ("tata", "DOUBLE"),
    ("computed_at", "VARCHAR"),
)

TABLES = {
    "company_financials": COMPANY_FINANCIALS,
    "forensic_scores": FORENSIC_SCORES,
}
PRIMARY_KEY = ("ticker", "fiscal_year")

# Metric results may be unknown. The text columns next to them stay required
# so a NULL score still has a reason.
NULLABLE_FORENSIC = frozenset(
    {
        "altman_z_score",
        "beneish_m_score",
        "piotroski_f_score",
        "ebit_margin_pct",
        "ebit_margin_yoy_change_bps",
        "revenue_growth_yoy_pct",
        "rd_to_revenue_pct",
        "ai_hype_score",
        "ai_roi_realization_score",
        "ai_washing_score",
        "dsri",
        "gmi",
        "aqi",
        "sgi",
        "depi",
        "sgai",
        "lvgi",
        "tata",
    }
)


def _placeholder(data_type: str) -> str | int | float:
    if data_type == "VARCHAR":
        return "TEST"
    if data_type == "INTEGER":
        return 0
    if data_type == "DOUBLE":
        return 0.0
    raise AssertionError(data_type)


def _insert_placeholder(conn: duckdb.DuckDBPyConnection, table: str) -> tuple[object, ...]:
    columns = TABLES[table]
    names = [name for name, _ in columns]
    values = tuple(_placeholder(data_type) for _, data_type in columns)
    marks = ", ".join("?" for _ in names)
    conn.execute(
        f"INSERT INTO {table} ({', '.join(names)}) VALUES ({marks})",
        values,
    )
    return values


def _fetch_all(conn: duckdb.DuckDBPyConnection, table: str) -> list[tuple[object, ...]]:
    names = [name for name, _ in TABLES[table]]
    return conn.execute(f"SELECT {', '.join(names)} FROM {table} ORDER BY ticker").fetchall()


def _column_rows(conn: duckdb.DuckDBPyConnection, table: str) -> list[tuple[str, str, str]]:
    return conn.execute(
        """
        SELECT column_name, upper(data_type), is_nullable
        FROM information_schema.columns
        WHERE table_schema = 'main' AND table_name = ?
        ORDER BY ordinal_position
        """,
        [table],
    ).fetchall()


def _primary_key(conn: duckdb.DuckDBPyConnection, table: str) -> tuple[str, ...]:
    rows = conn.execute(
        """
        SELECT constraint_column_names
        FROM duckdb_constraints()
        WHERE schema_name = 'main'
          AND table_name = ?
          AND constraint_type = 'PRIMARY KEY'
        """,
        [table],
    ).fetchall()
    assert len(rows) == 1
    return tuple(rows[0][0])


def test_default_database_path() -> None:
    assert DEFAULT_DUCKDB_PATH.name == "alphasentinel.duckdb"
    assert DEFAULT_DUCKDB_PATH.parent.name == "data"


def _expected_nullable(table: str, name: str) -> str:
    if table == "forensic_scores" and name in NULLABLE_FORENSIC:
        return "YES"
    return "NO"


def test_tables_columns_types_and_primary_keys() -> None:
    with tempfile.TemporaryDirectory() as raw:
        db_path = Path(raw) / "nested" / "alphasentinel.duckdb"
        init_db(db_path)
        validate_schema(db_path)

        conn = get_duckdb_conn(db_path)
        try:
            tables = {row[0] for row in conn.execute("SHOW TABLES").fetchall()}
            assert set(TABLES) <= tables
            for table, columns in TABLES.items():
                assert _column_rows(conn, table) == [
                    (name, data_type, _expected_nullable(table, name))
                    for name, data_type in columns
                ]
                assert _primary_key(conn, table) == PRIMARY_KEY
        finally:
            conn.close()


def test_init_db_is_idempotent_and_keeps_placeholder_rows() -> None:
    with tempfile.TemporaryDirectory() as raw:
        db_path = Path(raw) / "alphasentinel.duckdb"
        init_db(db_path)

        conn = get_duckdb_conn(db_path)
        try:
            written = {
                table: _insert_placeholder(conn, table) for table in TABLES
            }
        finally:
            conn.close()

        init_db(db_path)
        validate_schema(db_path)

        conn = get_duckdb_conn(db_path)
        try:
            for table, values in written.items():
                assert _fetch_all(conn, table) == [values]
                assert values[0] == "TEST"
        finally:
            conn.close()


def test_duplicate_primary_key_is_rejected() -> None:
    with tempfile.TemporaryDirectory() as raw:
        db_path = Path(raw) / "alphasentinel.duckdb"
        init_db(db_path)
        conn = get_duckdb_conn(db_path)
        try:
            _insert_placeholder(conn, "company_financials")
            with pytest.raises(duckdb.ConstraintException):
                _insert_placeholder(conn, "company_financials")
        finally:
            conn.close()


def test_init_db_relaxes_legacy_forensic_not_null(tmp_path: Path) -> None:
    """A TASK-02 warehouse marked every forensic column NOT NULL."""
    db_path = tmp_path / "legacy.duckdb"
    column_sql = ",\n".join(
        f"    {name} {data_type} NOT NULL" for name, data_type in FORENSIC_SCORES
    )
    conn = duckdb.connect(str(db_path))
    conn.execute(
        "CREATE TABLE forensic_scores (\n"
        f"{column_sql},\n"
        "    PRIMARY KEY (ticker, fiscal_year)\n"
        ")"
    )
    conn.close()

    init_db(db_path)
    conn = get_duckdb_conn(db_path)
    try:
        nullable = {name: flag for name, _, flag in _column_rows(conn, "forensic_scores")}
        assert nullable["altman_z_score"] == "YES"
        assert nullable["piotroski_f_score"] == "YES"
        assert nullable["tata"] == "YES"
        assert nullable["altman_zone"] == "NO"
        assert nullable["computed_at"] == "NO"
        conn.execute(
            """
            INSERT INTO forensic_scores (
                ticker, company_name, sector, fiscal_year, data_source_mode,
                altman_z_score, altman_zone, beneish_m_score, beneish_flag,
                piotroski_f_score, piotroski_tier,
                ebit_margin_pct, ebit_margin_yoy_change_bps, revenue_growth_yoy_pct,
                rd_to_revenue_pct, ai_hype_score, ai_roi_realization_score,
                ai_washing_score, ai_washing_status,
                dsri, gmi, aqi, sgi, depi, sgai, lvgi, tata, computed_at
            ) VALUES (
                'TEST', 'TEST', 'TEST', 2025, 'TEST',
                NULL, 'total_assets is zero', NULL, 'missing prior fiscal year 2024',
                NULL, 'missing prior fiscal year 2024',
                NULL, NULL, NULL, NULL, NULL, NULL, NULL, 'total_word_count is zero',
                NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, 'TEST'
            )
            """
        )
        stored = conn.execute(
            "SELECT altman_z_score, beneish_m_score, piotroski_f_score FROM forensic_scores"
        ).fetchone()
        assert stored == (None, None, None)
    finally:
        conn.close()


def test_validate_schema_rejects_missing_or_empty_database() -> None:
    with tempfile.TemporaryDirectory() as raw:
        missing = Path(raw) / "missing.duckdb"
        with pytest.raises(ValueError, match="does not exist"):
            validate_schema(missing)

        empty = Path(raw) / "empty.duckdb"
        conn = duckdb.connect(str(empty))
        conn.close()
        with pytest.raises(ValueError, match="company_financials"):
            validate_schema(empty)
