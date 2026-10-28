"""Interactive dashboard for the financial and forensic data in DuckDB."""

from __future__ import annotations

import os

import pandas as pd
import streamlit as st

from alphasentinel.db_schema import DEFAULT_DUCKDB_PATH, get_duckdb_conn

_NO_DATA = "数据不足"
_SCORE_FIELDS = (
    "fiscal_year",
    "altman_z_score",
    "beneish_m_score",
    "piotroski_f_score",
    "ai_washing_score",
)


def _load_data() -> tuple[pd.DataFrame, pd.DataFrame]:
    db_path = os.environ.get("ALPHASENTINEL_DB", str(DEFAULT_DUCKDB_PATH))
    connection = get_duckdb_conn(db_path)
    try:
        financials = connection.execute(
            "SELECT * FROM company_financials ORDER BY ticker, fiscal_year"
        ).fetchdf()
        scores = connection.execute(
            "SELECT * FROM forensic_scores ORDER BY ticker, fiscal_year"
        ).fetchdf()
    finally:
        connection.close()
    return financials, scores


def _display_nulls(frame: pd.DataFrame) -> pd.DataFrame:
    """Keep values unchanged except for visibly marking missing values."""
    return frame.astype(object).where(frame.notna(), _NO_DATA)


def _score_chart(scores: pd.DataFrame) -> None:
    chart = scores.set_index("fiscal_year")[
        ["altman_z_score", "beneish_m_score", "piotroski_f_score", "ai_washing_score"]
    ]
    if chart.notna().any().any():
        st.line_chart(chart)
    else:
        st.info(_NO_DATA)


def portfolio_kpis(scores: pd.DataFrame) -> list[tuple[str, int]]:
    """Four portfolio counts from stored score rows.

    A NULL ``ai_washing_score`` or ``beneish_m_score`` does not count as an
    alert. The counts are row counts, not filled-in financial amounts.
    """
    if scores.empty:
        return []
    verified = int(scores["ai_washing_status"].eq("VERIFIED_AI_ROI").fillna(False).sum())
    alerts = int(scores["ai_washing_score"].ge(35.0).fillna(False).sum())
    high_risk = int(scores["beneish_m_score"].gt(-1.78).fillna(False).sum())
    return [
        ("Monitored Equities", len(scores)),
        ("Verified AI-ROI Leaders", verified),
        ("AI-Washing / Watch Alerts", alerts),
        ("High Manipulation Risk (M > -1.78)", high_risk),
    ]


def _render_portfolio_kpis(scores: pd.DataFrame) -> None:
    kpis = portfolio_kpis(scores)
    if not kpis:
        return
    columns = st.columns(4, border=True)
    for column, (label, value) in zip(columns, kpis, strict=True):
        column.metric(label, str(value), height="stretch")


def main() -> None:
    st.set_page_config(page_title="AlphaSentinel 看板", layout="wide")
    st.title("AlphaSentinel 财务与四项评分看板")
    st.caption("所有数值均直接来自 DuckDB；NULL 显示为“数据不足”。")

    financials, scores = _load_data()
    _render_portfolio_kpis(scores)
    tickers = sorted(set(financials["ticker"]) | set(scores["ticker"]))
    if not tickers:
        st.warning("无数据")
        return

    selected = st.selectbox("公司选择", tickers)
    company_financials = financials[financials["ticker"] == selected]
    company_scores = scores[scores["ticker"] == selected]

    st.subheader("财务表")
    if company_financials.empty:
        st.info("无数据")
    else:
        st.dataframe(_display_nulls(company_financials), width="stretch")

    st.subheader("四项评分表")
    if company_scores.empty:
        st.info("无数据")
    else:
        st.dataframe(_display_nulls(company_scores[list(_SCORE_FIELDS)]), width="stretch")
        st.subheader("四项评分图")
        _score_chart(company_scores)


main()
