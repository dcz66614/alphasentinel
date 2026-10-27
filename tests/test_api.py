"""API tests using placeholder rows, not real or illustrative financial data."""

from __future__ import annotations

import os
from pathlib import Path

import duckdb
import pytest
from fastapi.testclient import TestClient

from alphasentinel.api_server import app
from alphasentinel.db_schema import init_db


def _placeholder(data_type: str) -> str | int | float:
    return {"VARCHAR": "TEST", "INTEGER": 0, "DOUBLE": 0.0}[data_type]


def _insert_placeholder(conn: duckdb.DuckDBPyConnection, table: str) -> dict[str, object]:
    columns = conn.execute(
        """
        SELECT column_name, upper(data_type)
        FROM information_schema.columns
        WHERE table_schema = 'main' AND table_name = ?
        ORDER BY ordinal_position
        """,
        [table],
    ).fetchall()
    names = [name for name, _ in columns]
    values = [_placeholder(data_type) for _, data_type in columns]
    conn.execute(
        f"INSERT INTO {table} VALUES ({', '.join('?' for _ in values)})",
        values,
    )
    return dict(zip(names, values, strict=True))


@pytest.fixture
def client(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> TestClient:
    db_path = tmp_path / "api.duckdb"
    init_db(db_path)
    monkeypatch.setenv("ALPHASENTINEL_DB", str(db_path))
    return TestClient(app)


def test_health_and_empty_tables(client: TestClient) -> None:
    assert client.get("/health").json() == {
        "status": "ok",
        "service": "AlphaSentinel Forensic Engine",
    }
    assert client.get("/companies").json() == []
    assert client.get("/financials/TEST").status_code == 404
    assert client.get("/scores/TEST").status_code == 404


def test_placeholder_rows_round_trip(client: TestClient) -> None:
    conn = duckdb.connect(os.environ["ALPHASENTINEL_DB"])
    try:
        financial = _insert_placeholder(conn, "company_financials")
        score = _insert_placeholder(conn, "forensic_scores")
    finally:
        conn.close()

    response = client.get("/companies")
    assert response.status_code == 200
    assert response.json() == [
        {"ticker": "TEST", "company_name": "TEST", "sector": "TEST"}
    ]
    assert client.get("/financials/test").json() == [financial]
    assert client.get("/scores/TEST").json() == [score]
