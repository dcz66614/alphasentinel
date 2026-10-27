"""Forensic score tests.

Published worked example: Steven Bragg, AccountingTools, "Altman Z Score Formula"
(https://www.accountingtools.com/articles/the-altman-z-score-formula.html).
The dollar amounts in that example are the source's, and the page states a
Z-score of 2.095 in the gray zone.

Beneish coefficients are the eight-variable model in Messod D. Beneish,
"The Detection of Earnings Manipulation," Financial Analysts Journal 55, no. 5
(1999). The identity check sets every index to 1 and TATA to 0.05, which is
arithmetic on those coefficients, not a set of financial statements.

SEC amounts come from tests/fixtures or from data/cache companyfacts that the
ingestor normalizes. This file does not type those amounts. Placeholder zeros
are the same device as test_schema.py: they satisfy NOT NULL columns and are
not financial figures.
"""

from __future__ import annotations

import json
from pathlib import Path

import duckdb

from alphasentinel.db_schema import init_db
from alphasentinel.forensic_engine import (
    ai_washing_status,
    altman_z_from_ratios,
    altman_zone,
    beneish_flag,
    beneish_m_from_components,
    compute_ai_washing_index,
    compute_altman_z,
    compute_beneish_m,
    compute_piotroski_f,
    piotroski_tier,
    run_forensic_pipeline,
)
from alphasentinel.ingestor import ingest_tickers, normalize_company_facts

ROOT = Path(__file__).resolve().parents[1]
FIXTURES = Path(__file__).parent / "fixtures"
AAPL_FIXTURE = FIXTURES / "aapl_companyfacts_excerpt.json"
CACHE = ROOT / "data" / "cache"

# AccountingTools worked example. Market value of equity is market_cap here.
ACCOUNTINGTOOLS_ALTMAN = {
    "working_capital": 500_000.0,
    "retained_earnings": 1_000_000.0,
    "ebit": 750_000.0,
    "total_assets": 5_000_000.0,
    "market_cap": 2_000_000.0,
    "total_liabilities": 3_000_000.0,
    "revenue": 4_000_000.0,
}


def test_altman_matches_accountingtools_worked_example() -> None:
    result = compute_altman_z(ACCOUNTINGTOOLS_ALTMAN)
    ratios = (
        500_000 / 5_000_000,
        1_000_000 / 5_000_000,
        750_000 / 5_000_000,
        2_000_000 / 3_000_000,
        4_000_000 / 5_000_000,
    )
    z_score = altman_z_from_ratios(*ratios)
    assert round(z_score, 3) == 2.095
    assert result["altman_z_score"] == round(z_score, 4) == 2.095
    assert result["altman_zone"] == "GREY"
    assert result["altman_zone"] == altman_zone(z_score)


def test_zone_flag_and_tier_cutoffs() -> None:
    assert altman_zone(3.0) == "SAFE"
    assert altman_zone(2.99) == "GREY"
    assert altman_zone(1.81) == "GREY"
    assert altman_zone(1.80) == "DISTRESS"
    assert beneish_flag(-1.78) == "NORMAL"
    assert beneish_flag(-1.77) == "MANIPULATION_RISK_HIGH"
    assert beneish_flag(-2.22) == "NORMAL"
    assert piotroski_tier(9) == "STRONG"
    assert piotroski_tier(7) == "STRONG"
    assert piotroski_tier(6) == "MODERATE"
    assert piotroski_tier(4) == "MODERATE"
    assert piotroski_tier(3) == "WEAK"
    assert ai_washing_status(60) == "AI_WASHING_ALERT"
    assert ai_washing_status(59) == "WATCH"
    assert ai_washing_status(35) == "WATCH"
    assert ai_washing_status(34) == "VERIFIED_AI_ROI"


def test_beneish_coefficients_match_1999_model() -> None:
    """Every index is 1 and TATA is 0.05. The sum is the published weights."""
    indexes = (1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 0.05, 1.0)
    expected = (
        -4.84
        + 0.920
        + 0.528
        + 0.404
        + 0.892
        + 0.115
        - 0.172
        + 4.679 * 0.05
        - 0.327
    )
    assert expected == -2.24605
    assert beneish_m_from_components(*indexes) == expected
    assert beneish_flag(expected) == "NORMAL"


def _load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def test_aapl_fixture_nulls_missing_inputs_and_keeps_tata() -> None:
    rows = normalize_company_facts(_load_json(AAPL_FIXTURE))
    assert len(rows) == 1
    current = rows[0]
    assert "market_cap" not in current

    altman = compute_altman_z(current)
    assert altman["altman_z_score"] is None
    assert altman["altman_zone"] == "missing market_cap"

    beneish = compute_beneish_m(current, None)
    assert beneish["beneish_m_score"] is None
    assert beneish["dsri"] is None
    prior_year = int(current["fiscal_year"]) - 1
    assert f"missing prior fiscal year {prior_year}" in beneish["beneish_flag"]
    tata = (current["net_income"] - current["operating_cash_flow"]) / current["total_assets"]
    assert beneish["tata"] == round(tata, 4)
    assert beneish["tata"] != 0

    piotroski = compute_piotroski_f(current, None, None)
    assert piotroski["piotroski_f_score"] is None
    assert f"missing prior fiscal year {prior_year}" in piotroski["piotroski_tier"]

    washing = compute_ai_washing_index(current, None)
    assert washing["ai_washing_score"] is None
    assert washing["ai_hype_score"] is None
    assert "ai_mention_count" in washing["ai_washing_status"]
    assert f"missing prior fiscal year {prior_year}" in washing["ai_washing_status"]
    margin = current["ebit"] * 100.0 / current["revenue"]
    assert washing["ebit_margin_pct"] == round(margin, 2)
    assert washing["ebit_margin_yoy_change_bps"] is None


def test_deleted_published_account_is_null() -> None:
    incomplete = dict(ACCOUNTINGTOOLS_ALTMAN)
    del incomplete["ebit"]
    result = compute_altman_z(incomplete)
    assert result["altman_z_score"] is None
    assert "ebit" in result["altman_zone"]
    assert result["altman_z_score"] != 0


def _gross_margin(row: dict) -> float:
    return (row["revenue"] - row["cogs"]) / row["revenue"]


def _asset_quality(row: dict) -> float:
    return 1.0 - (row["current_assets"] + row["ppe"]) / row["total_assets"]


def _depreciation_rate(row: dict) -> float:
    return row["depreciation"] / (row["depreciation"] + row["ppe"])


def _leverage(row: dict) -> float:
    return (row["current_liabilities"] + row["long_term_debt"]) / row["total_assets"]


def _paper_beneish(curr: dict, prev: dict) -> dict[str, float]:
    """Beneish (1999) ratios, plus the 2013 cash-flow accrual, from stored lines."""
    return {
        "dsri": (curr["receivables"] / curr["revenue"]) / (prev["receivables"] / prev["revenue"]),
        "gmi": _gross_margin(prev) / _gross_margin(curr),
        "aqi": _asset_quality(curr) / _asset_quality(prev),
        "sgi": curr["revenue"] / prev["revenue"],
        "depi": _depreciation_rate(prev) / _depreciation_rate(curr),
        "sgai": (curr["sga"] / curr["revenue"]) / (prev["sga"] / prev["revenue"]),
        "lvgi": _leverage(curr) / _leverage(prev),
        "tata": (curr["net_income"] - curr["operating_cash_flow"]) / curr["total_assets"],
    }


def _paper_piotroski(curr: dict, prev: dict, prev2: dict) -> int:
    """Nine Piotroski (2000) signals from three normalized years."""
    roa_now = curr["net_income"] / prev["total_assets"]
    roa_prev = prev["net_income"] / prev2["total_assets"]
    cash_scaled = curr["operating_cash_flow"] / prev["total_assets"]
    average_now = (curr["total_assets"] + prev["total_assets"]) / 2.0
    average_prev = (prev["total_assets"] + prev2["total_assets"]) / 2.0
    leverage_now = curr["long_term_debt"] / average_now
    leverage_prev = prev["long_term_debt"] / average_prev
    current_now = curr["current_assets"] / curr["current_liabilities"]
    current_prev = prev["current_assets"] / prev["current_liabilities"]
    margin_now = (curr["revenue"] - curr["cogs"]) / curr["revenue"]
    margin_prev = (prev["revenue"] - prev["cogs"]) / prev["revenue"]
    turnover_now = curr["revenue"] / prev["total_assets"]
    turnover_prev = prev["revenue"] / prev2["total_assets"]
    signals = (
        roa_now > 0,
        cash_scaled > 0,
        roa_now > roa_prev,
        cash_scaled > roa_now,
        leverage_now < leverage_prev,
        current_now > current_prev,
        curr["shares_outstanding"] <= prev["shares_outstanding"],
        margin_now > margin_prev,
        turnover_now > turnover_prev,
    )
    return sum(1 if signal else 0 for signal in signals)


def test_piotroski_and_beneish_on_three_normalized_aapl_years() -> None:
    payload = _load_json(CACHE / "AAPL" / "companyfacts.json")
    rows = normalize_company_facts(payload, max_years=3)
    by_year = {int(row["fiscal_year"]): row for row in rows}
    year = max(by_year)
    current, prior, lagged = by_year[year], by_year[year - 1], by_year[year - 2]

    parts = _paper_beneish(current, prior)
    beneish = compute_beneish_m(current, prior)
    for name, value in parts.items():
        assert beneish[name] == round(value, 4)
    m_score = beneish_m_from_components(
        parts["dsri"],
        parts["gmi"],
        parts["aqi"],
        parts["sgi"],
        parts["depi"],
        parts["sgai"],
        parts["tata"],
        parts["lvgi"],
    )
    assert beneish["beneish_m_score"] == round(m_score, 4)
    assert beneish["beneish_flag"] == beneish_flag(m_score)

    expected = _paper_piotroski(current, prior, lagged)
    scored = compute_piotroski_f(current, prior, lagged)
    assert scored["piotroski_f_score"] == expected
    assert scored["piotroski_tier"] == piotroski_tier(expected)
    assert 0 <= expected <= 9

    without_lag = compute_piotroski_f(current, prior, None)
    assert without_lag["piotroski_f_score"] is None
    assert f"missing fiscal year {year - 2}" in without_lag["piotroski_tier"]


def _paper_ai(curr: dict, prev: dict) -> dict[str, float | str]:
    """TASK-04 AI-Washing arithmetic from stored lines."""
    mentions = curr["ai_mention_count"] * 10000.0 / curr["total_word_count"]
    hype = min(100.0, max(0.0, mentions * 1.45))

    def margin(row: dict) -> float:
        return row["ebit"] * 100.0 / row["revenue"]

    delta = margin(curr) - margin(prev)
    growth = (curr["revenue"] / prev["revenue"] - 1.0) * 100.0
    roi = min(100.0, max(0.0, 50.0 + 8.0 * delta + 1.2 * growth))
    penalty = 20.0 if curr["insider_net_sell_ratio"] > 0.70 else 0.0
    raw = min(100.0, max(0.0, max(0.0, hype - 0.85 * roi) + penalty))
    return {
        "ebit_margin_pct": round(margin(curr), 2),
        "ebit_margin_yoy_change_bps": round(delta * 100.0, 1),
        "revenue_growth_yoy_pct": round(growth, 2),
        "rd_to_revenue_pct": round(curr["rd_expense"] * 100.0 / curr["revenue"], 2),
        "ai_hype_score": round(hype, 2),
        "ai_roi_realization_score": round(roi, 2),
        "ai_washing_score": round(raw, 2),
        "ai_washing_status": ai_washing_status(raw),
    }


def test_pipeline_on_offline_sec_cache(tmp_path: Path) -> None:
    database = tmp_path / "forensic.duckdb"
    written = ingest_tickers(
        ["AAPL", "MSFT"], db_path=database, cache_dir=CACHE, offline=True
    )
    assert written == 4
    results = run_forensic_pipeline(database)
    assert [row["ticker"] for row in results] == ["AAPL", "MSFT"]

    connection = duckdb.connect(str(database))
    try:
        stored = connection.execute(
            """
            SELECT * FROM company_financials
            ORDER BY ticker, fiscal_year
            """
        )
        names = [item[0] for item in stored.description]
        financials = [dict(zip(names, row, strict=True)) for row in stored.fetchall()]
        score_cursor = connection.execute(
            "SELECT * FROM forensic_scores ORDER BY ticker"
        )
        score_names = [item[0] for item in score_cursor.description]
        scores = score_cursor.fetchall()
    finally:
        connection.close()

    assert len(scores) == 2
    by_ticker: dict[str, list[dict]] = {}
    for row in financials:
        by_ticker.setdefault(row["ticker"], []).append(row)

    for record in results:
        history = by_ticker[record["ticker"]]
        current, prior = history[-1], history[-2]
        assert record["fiscal_year"] == current["fiscal_year"]
        assert record["fiscal_year"] == prior["fiscal_year"] + 1
        total_assets = current["total_assets"]
        total_liabilities = current["total_liabilities"]
        z_score = altman_z_from_ratios(
            current["working_capital"] / total_assets,
            current["retained_earnings"] / total_assets,
            current["ebit"] / total_assets,
            current["market_cap"] / total_liabilities,
            current["revenue"] / total_assets,
        )
        assert record["altman_z_score"] == round(z_score, 4)
        assert record["altman_zone"] == altman_zone(z_score)
        parts = _paper_beneish(current, prior)
        for name, value in parts.items():
            assert record[name] == round(value, 4)
        m_score = beneish_m_from_components(
            parts["dsri"],
            parts["gmi"],
            parts["aqi"],
            parts["sgi"],
            parts["depi"],
            parts["sgai"],
            parts["tata"],
            parts["lvgi"],
        )
        assert record["beneish_m_score"] == round(m_score, 4)
        assert record["piotroski_f_score"] is None
        assert f"fiscal year {current['fiscal_year'] - 2}" in record["piotroski_tier"]
        expected_ai = _paper_ai(current, prior)
        for name, value in expected_ai.items():
            assert record[name] == value
        assert record["data_source_mode"] == "CACHE_SEC"

    stored_by_ticker = {
        row[score_names.index("ticker")]: dict(zip(score_names, row, strict=True)) for row in scores
    }
    for record in results:
        saved = stored_by_ticker[record["ticker"]]
        assert saved["altman_z_score"] == record["altman_z_score"]
        assert saved["piotroski_f_score"] is None
        assert saved["beneish_m_score"] == record["beneish_m_score"]
        assert saved["ai_washing_score"] == record["ai_washing_score"]


def _insert_zero_year(connection: duckdb.DuckDBPyConnection, year: int) -> None:
    """Write a NOT NULL placeholder. Zeros are not financial amounts."""
    columns = connection.execute(
        """
        SELECT column_name, data_type
        FROM information_schema.columns
        WHERE table_schema = 'main' AND table_name = 'company_financials'
        ORDER BY ordinal_position
        """
    ).fetchall()
    values: list[object] = []
    for name, data_type in columns:
        if name == "fiscal_year":
            values.append(year)
        elif str(data_type).upper().startswith("VARCHAR"):
            values.append("TEST")
        elif str(data_type).upper().startswith("INT"):
            values.append(0)
        else:
            values.append(0.0)
    names = [name for name, _ in columns]
    marks = ", ".join("?" for _ in names)
    connection.execute(
        f"INSERT INTO company_financials ({', '.join(names)}) VALUES ({marks})",
        values,
    )


def test_zero_placeholders_stay_null(tmp_path: Path) -> None:
    database = tmp_path / "zeros.duckdb"
    init_db(database)
    connection = duckdb.connect(str(database))
    try:
        for year in (2023, 2024, 2025):
            _insert_zero_year(connection, year)
    finally:
        connection.close()

    results = run_forensic_pipeline(database)
    assert len(results) == 1
    record = results[0]
    assert record["fiscal_year"] == 2025
    assert record["altman_z_score"] is None
    assert "total_assets is zero" in record["altman_zone"]
    assert "total_liabilities is zero" in record["altman_zone"]
    assert record["beneish_m_score"] is None
    assert "is zero" in record["beneish_flag"]
    assert record["beneish_flag"] != "NORMAL"
    assert record["piotroski_f_score"] is None
    assert "zero" in record["piotroski_tier"]
    assert record["ai_washing_score"] is None
    assert record["ai_hype_score"] is None
    assert "zero" in record["ai_washing_status"]

    connection = duckdb.connect(str(database))
    try:
        saved = connection.execute(
            """
            SELECT altman_z_score, beneish_m_score, piotroski_f_score, ai_washing_score, tata
            FROM forensic_scores
            """
        ).fetchone()
    finally:
        connection.close()
    assert saved == (None, None, None, None, None)
