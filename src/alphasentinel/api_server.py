"""Read-only API for AlphaSentinel financial and forensic data."""

from __future__ import annotations

import os

from fastapi import FastAPI, HTTPException

from alphasentinel.db_schema import DEFAULT_DUCKDB_PATH, get_duckdb_conn

app = FastAPI(title="Project AlphaSentinel API", version="1.0.0")


def _db_path() -> str:
    return os.environ.get("ALPHASENTINEL_DB", str(DEFAULT_DUCKDB_PATH))


def _rows(query: str, parameters: tuple[str, ...] = ()) -> list[dict[str, object]]:
    conn = get_duckdb_conn(_db_path())
    try:
        cursor = conn.execute(query, parameters)
        columns = [column[0] for column in cursor.description]
        return [dict(zip(columns, row, strict=True)) for row in cursor.fetchall()]
    finally:
        conn.close()


@app.get("/health")
def health_check() -> dict[str, str]:
    return {"status": "ok", "service": "AlphaSentinel Forensic Engine"}


@app.get("/companies")
def list_companies() -> list[dict[str, object]]:
    return _rows(
        """
        SELECT ticker, company_name, sector
        FROM company_financials
        GROUP BY ticker, company_name, sector
        ORDER BY ticker
        """
    )


@app.get("/financials/{ticker}")
def get_financials(ticker: str) -> list[dict[str, object]]:
    rows = _rows(
        "SELECT * FROM company_financials WHERE ticker = ? ORDER BY fiscal_year",
        (ticker.strip().upper(),),
    )
    if not rows:
        raise HTTPException(status_code=404, detail="Ticker not found")
    return rows


@app.get("/scores/{ticker}")
def get_scores(ticker: str) -> list[dict[str, object]]:
    rows = _rows(
        "SELECT * FROM forensic_scores WHERE ticker = ? ORDER BY fiscal_year",
        (ticker.strip().upper(),),
    )
    if not rows:
        raise HTTPException(status_code=404, detail="Ticker not found")
    return rows


@app.get("/api/v1/scores")
def list_all_scores() -> dict[str, object]:
    """All stored forensic rows. NULL scores stay NULL and sort after numbers."""
    rows = _rows("SELECT * FROM forensic_scores ORDER BY ai_washing_score DESC")
    return {"count": len(rows), "items": rows}


@app.get("/api/v1/ticker/{symbol}")
def get_ticker_detail(symbol: str) -> dict[str, object]:
    """Latest stored score plus the financial history for one ticker."""
    ticker = symbol.strip().upper()
    scores = _rows(
        "SELECT * FROM forensic_scores WHERE ticker = ? ORDER BY fiscal_year",
        (ticker,),
    )
    if not scores:
        raise HTTPException(
            status_code=404,
            detail=f"Ticker {ticker} not found in warehouse.",
        )
    financials = _rows(
        "SELECT * FROM company_financials WHERE ticker = ? ORDER BY fiscal_year",
        (ticker,),
    )
    return {
        "ticker": ticker,
        "forensic_summary": scores[-1],
        "financial_history": financials,
    }
