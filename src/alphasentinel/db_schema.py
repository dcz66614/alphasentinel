"""DuckDB warehouse schema for company financials and forensic scores."""

from __future__ import annotations

from pathlib import Path

import duckdb

_PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_DUCKDB_PATH = _PROJECT_ROOT / "data" / "alphasentinel.duckdb"

_PRIMARY_KEY = ("ticker", "fiscal_year")

_COMPANY_FINANCIALS_COLUMNS: tuple[tuple[str, str], ...] = (
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

_FORENSIC_SCORES_COLUMNS: tuple[tuple[str, str], ...] = (
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

_TABLES: dict[str, tuple[tuple[str, str], ...]] = {
    "company_financials": _COMPANY_FINANCIALS_COLUMNS,
    "forensic_scores": _FORENSIC_SCORES_COLUMNS,
}


def _resolve_path(path: Path | str | None) -> Path:
    if path is None:
        return DEFAULT_DUCKDB_PATH
    return Path(path)


def get_duckdb_conn(path: Path | str | None = None) -> duckdb.DuckDBPyConnection:
    """Open the warehouse, creating parent directories when needed."""
    db_path = _resolve_path(path)
    db_path.parent.mkdir(parents=True, exist_ok=True)
    return duckdb.connect(str(db_path))


def _create_table_sql(table: str, columns: tuple[tuple[str, str], ...]) -> str:
    column_sql = ",\n".join(f"    {name} {data_type} NOT NULL" for name, data_type in columns)
    primary_key = ", ".join(_PRIMARY_KEY)
    return (
        f"CREATE TABLE IF NOT EXISTS {table} (\n"
        f"{column_sql},\n"
        f"    PRIMARY KEY ({primary_key})\n"
        f")"
    )


def _schema_problems(conn: duckdb.DuckDBPyConnection) -> list[str]:
    problems: list[str] = []
    present = {row[0] for row in conn.execute("SHOW TABLES").fetchall()}

    for table, columns in _TABLES.items():
        if table not in present:
            problems.append(f"missing table {table}")
            continue

        found = conn.execute(
            """
            SELECT column_name, upper(data_type), is_nullable
            FROM information_schema.columns
            WHERE table_schema = 'main' AND table_name = ?
            ORDER BY ordinal_position
            """,
            [table],
        ).fetchall()
        expected = [(name, data_type, "NO") for name, data_type in columns]
        if found != expected:
            problems.append(
                f"{table} columns are {found}, expected {expected}"
            )

        keys = conn.execute(
            """
            SELECT constraint_column_names
            FROM duckdb_constraints()
            WHERE schema_name = 'main'
              AND table_name = ?
              AND constraint_type = 'PRIMARY KEY'
            """,
            [table],
        ).fetchall()
        if len(keys) != 1 or tuple(keys[0][0]) != _PRIMARY_KEY:
            actual = [tuple(row[0]) for row in keys]
            problems.append(f"{table} primary key is {actual}, expected {_PRIMARY_KEY}")

    return problems


def validate_schema(path: Path | str | None = None) -> None:
    """Raise ValueError when the warehouse file does not match the spec schema."""
    db_path = _resolve_path(path)
    if not db_path.is_file():
        raise ValueError(f"DuckDB file does not exist: {db_path}")

    conn = duckdb.connect(str(db_path))
    try:
        problems = _schema_problems(conn)
    finally:
        conn.close()

    if problems:
        detail = "\n".join(problems)
        raise ValueError(f"DuckDB schema mismatch:\n{detail}")


def init_db(path: Path | str | None = None) -> None:
    """Create the warehouse tables if they are absent, then check the schema."""
    conn = get_duckdb_conn(path)
    try:
        for table, columns in _TABLES.items():
            conn.execute(_create_table_sql(table, columns))
        problems = _schema_problems(conn)
    finally:
        conn.close()

    if problems:
        detail = "\n".join(problems)
        raise ValueError(f"DuckDB schema mismatch:\n{detail}")


if __name__ == "__main__":
    init_db()
    print("[DB_SCHEMA] DuckDB tables initialized successfully.")
