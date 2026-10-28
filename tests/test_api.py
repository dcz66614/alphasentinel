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


def _insert_row(
    conn: duckdb.DuckDBPyConnection,
    table: str,
    overrides: dict[str, object] | None = None,
) -> dict[str, object]:
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
    supplied = overrides or {}
    values: list[object] = []
    for name, data_type in columns:
        if name in supplied:
            values.append(supplied[name])
        else:
            values.append(_placeholder(data_type))
    conn.execute(
        f"INSERT INTO {table} VALUES ({', '.join('?' for _ in values)})",
        values,
    )
    return dict(zip(names, values, strict=True))


def _insert_placeholder(conn: duckdb.DuckDBPyConnection, table: str) -> dict[str, object]:
    return _insert_row(conn, table)


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
    assert client.get("/api/v1/scores").json() == {"count": 0, "items": []}
    missing = client.get("/api/v1/ticker/TEST")
    assert missing.status_code == 404
    assert missing.json()["detail"] == "Ticker TEST not found in warehouse."


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
    listed = client.get("/api/v1/scores")
    assert listed.status_code == 200
    assert listed.json() == {"count": 1, "items": [score]}
    detail = client.get("/api/v1/ticker/test")
    assert detail.status_code == 200
    assert detail.json() == {
        "ticker": "TEST",
        "forensic_summary": score,
        "financial_history": [financial],
    }


def test_spec_routes_keep_nulls_and_latest_year(client: TestClient) -> None:
    conn = duckdb.connect(os.environ["ALPHASENTINEL_DB"])
    try:
        earlier = _insert_row(
            conn,
            "forensic_scores",
            {"fiscal_year": 1, "ai_washing_score": 1.0},
        )
        latest = _insert_row(
            conn,
            "forensic_scores",
            {"fiscal_year": 2, "ai_washing_score": None, "beneish_m_score": None},
        )
        first_year = _insert_row(
            conn,
            "company_financials",
            {"fiscal_year": 1, "shares_outstanding": None, "market_cap": None},
        )
        second_year = _insert_row(conn, "company_financials", {"fiscal_year": 2})
    finally:
        conn.close()

    listed = client.get("/api/v1/scores").json()
    assert listed["count"] == 2
    assert listed["items"][0]["ai_washing_score"] == earlier["ai_washing_score"]
    assert listed["items"][1]["ai_washing_score"] is None
    assert listed["items"][1]["beneish_m_score"] is None

    detail = client.get("/api/v1/ticker/TeSt").json()
    assert detail["ticker"] == "TEST"
    assert detail["forensic_summary"] == latest
    assert detail["financial_history"] == [first_year, second_year]
    assert detail["financial_history"][0]["shares_outstanding"] is None
    assert detail["financial_history"][0]["market_cap"] is None
