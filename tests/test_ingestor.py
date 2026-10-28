"""Offline tests for XBRL normalization and the cache-only fallback.

Expected amounts are read back out of the fixture facts. The fixture files are
cuts of SEC companyfacts responses; see tests/fixtures/README.md.
"""

from __future__ import annotations

import json
import xml.etree.ElementTree as ET
from datetime import date
from pathlib import Path

import pytest

from alphasentinel.db_schema import get_duckdb_conn
from alphasentinel.ingestor import (
    FLOW_CONCEPTS,
    INSTANT_CONCEPTS,
    SPEC_SEC_IDENTITY,
    CacheMissError,
    IngestError,
    _pick_value,
    _resolve_sga,
    _rows_from_cache,
    ingest_tickers,
    insider_net_sell_ratio,
    main,
    normalize_company_facts,
    sec_identity,
)

FIXTURES = Path(__file__).parent / "fixtures"
AAPL_FIXTURE = FIXTURES / "aapl_companyfacts_excerpt.json"
MSFT_FIXTURE = FIXTURES / "msft_companyfacts_excerpt.json"
META_FIXTURE = FIXTURES / "meta_companyfacts_excerpt.json"
AMZN_FIXTURE = FIXTURES / "amzn_companyfacts_excerpt.json"
ORCL_FIXTURE = FIXTURES / "orcl_companyfacts_excerpt.json"
PLTR_FIXTURE = FIXTURES / "pltr_companyfacts_excerpt.json"
GOOGL_FIXTURE = FIXTURES / "googl_companyfacts_excerpt.json"
AAPL_FORM4 = FIXTURES / "aapl_form4_0000320193-23-000088.xml"
OFFLINE_CACHE = FIXTURES / "offline_cache"

MIN_ANNUAL_DAYS = 300
MAX_ANNUAL_DAYS = 380


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _days(fact: dict) -> int | None:
    start = fact.get("start")
    end = fact.get("end")
    if not start or not end:
        return None
    return (date.fromisoformat(end) - date.fromisoformat(start)).days


def _is_annual(fact: dict) -> bool:
    days = _days(fact)
    return (
        fact.get("form") in {"10-K", "10-K/A"}
        and days is not None
        and MIN_ANNUAL_DAYS <= days <= MAX_ANNUAL_DAYS
    )


def _own_year_fact(facts: list[dict], period_end: str, accession: str | None = None) -> dict:
    """Year's own 10-K fact: fy matches the period end year, latest filed date."""
    if accession:
        same = [fact for fact in facts if fact.get("accn") == accession and _matches(fact, period_end)]
        if same:
            return max(same, key=lambda fact: (fact.get("filed") or "", fact.get("accn") or ""))
    end_year = int(period_end[:4])
    own = [
        fact
        for fact in facts
        if _matches(fact, period_end) and fact.get("fy") == end_year
    ]
    if not own:
        raise AssertionError(f"fixture has no own-year fact for {period_end}")
    return max(own, key=lambda fact: (fact.get("filed") or "", fact.get("accn") or ""))


def _matches(fact: dict, period_end: str) -> bool:
    if fact.get("end") != period_end:
        return False
    if fact.get("start"):
        return _is_annual(fact)
    return fact.get("form") in {"10-K", "10-K/A"}


def _unit_rows(payload: dict, concept: str, unit: str) -> list[dict]:
    node = payload["facts"]["us-gaap"].get(concept)
    if not node:
        return []
    return list(node.get("units", {}).get(unit, []))


def test_sec_identity_uses_env_or_spec_default(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("SEC_IDENTITY", raising=False)
    assert sec_identity() == SPEC_SEC_IDENTITY
    monkeypatch.setenv("SEC_IDENTITY", "Example Analyst example@example.com")
    assert sec_identity() == "Example Analyst example@example.com"


def test_aapl_excerpt_uses_annual_10k_fact() -> None:
    payload = _load(AAPL_FIXTURE)
    rows = normalize_company_facts(payload)
    assert len(rows) == 1
    row = rows[0]
    assert row["company_name"] == payload["entityName"]

    revenue_facts = _unit_rows(
        payload, "RevenueFromContractWithCustomerExcludingAssessedTax", "USD"
    )
    period_end = row["period_end"]
    chosen = _own_year_fact(revenue_facts, period_end)
    assert row["revenue"] == chosen["val"]
    assert row["period_start"] == chosen["start"]
    assert row["period_end"] == chosen["end"]
    assert row["accession"] == chosen["accn"]
    assert row["filing_date"] == chosen["filed"]
    for fact in revenue_facts:
        if _is_annual(fact):
            continue
        assert row["revenue"] != fact["val"] or row["period_start"] != fact.get("start")

    accession = chosen["accn"]
    expectations = {
        "cogs": ("CostOfGoodsAndServicesSold", "USD"),
        "rd_expense": ("ResearchAndDevelopmentExpense", "USD"),
        "depreciation": ("DepreciationDepletionAndAmortization", "USD"),
        "ebit": ("OperatingIncomeLoss", "USD"),
        "net_income": ("NetIncomeLoss", "USD"),
        "operating_cash_flow": ("NetCashProvidedByUsedInOperatingActivities", "USD"),
        "sga": ("SellingGeneralAndAdministrativeExpense", "USD"),
        "receivables": ("AccountsReceivableNetCurrent", "USD"),
        "current_assets": ("AssetsCurrent", "USD"),
        "ppe": ("PropertyPlantAndEquipmentNet", "USD"),
        "total_assets": ("Assets", "USD"),
        "current_liabilities": ("LiabilitiesCurrent", "USD"),
        "long_term_debt": ("LongTermDebtNoncurrent", "USD"),
        "total_liabilities": ("Liabilities", "USD"),
        "retained_earnings": ("RetainedEarningsAccumulatedDeficit", "USD"),
        "shares_outstanding": ("CommonStockSharesOutstanding", "shares"),
    }
    for column, (concept, unit) in expectations.items():
        fact = _own_year_fact(_unit_rows(payload, concept, unit), period_end, accession)
        assert row[column] == fact["val"]
    assert row["working_capital"] == row["current_assets"] - row["current_liabilities"]


def test_msft_sga_is_sum_of_reported_components() -> None:
    payload = _load(MSFT_FIXTURE)
    assert "SellingGeneralAndAdministrativeExpense" not in payload["facts"]["us-gaap"]
    rows = normalize_company_facts(payload)
    assert len(rows) == 1
    row = rows[0]
    period_end = row["period_end"]
    accession = row["accession"]
    selling = _own_year_fact(
        _unit_rows(payload, "SellingAndMarketingExpense", "USD"), period_end, accession
    )
    admin = _own_year_fact(
        _unit_rows(payload, "GeneralAndAdministrativeExpense", "USD"),
        period_end,
        accession,
    )
    assert row["sga"] == selling["val"] + admin["val"]


def test_missing_concept_is_not_zero_filled() -> None:
    payload = _load(AAPL_FIXTURE)
    del payload["facts"]["us-gaap"]["OperatingIncomeLoss"]
    with pytest.raises(IngestError, match="ebit"):
        normalize_company_facts(payload)


def _revenue_fact(payload: dict, period_end: str) -> dict:
    for name in FLOW_CONCEPTS["revenue"]:
        try:
            return _own_year_fact(_unit_rows(payload, name, "USD"), period_end)
        except AssertionError:
            continue
    raise AssertionError(f"no revenue fact for {period_end}")


def test_meta_shares_outstanding_is_not_the_weighted_average() -> None:
    """META files no period-end share count. The EPS average is not a substitute."""
    payload = _load(META_FIXTURE)
    assert "CommonStockSharesOutstanding" not in payload["facts"]["us-gaap"]
    assert "EntityCommonStockSharesOutstanding" not in payload["facts"].get("dei", {})
    assert "EntityPublicFloat" in payload["facts"]["dei"]
    period_end = "2025-12-31"
    basic = _own_year_fact(
        _unit_rows(payload, "WeightedAverageNumberOfSharesOutstandingBasic", "shares"),
        period_end,
    )
    assert basic.get("start")
    assert basic["val"] > 0
    rows = {row["fiscal_year"]: row for row in normalize_company_facts(payload)}
    assert set(rows) == {2024, 2025}
    for row in rows.values():
        assert row["shares_outstanding"] is None
        assert row["shares_outstanding"] != basic["val"]
        assert "shares_outstanding" not in row["derived_fields"]
        assert row["revenue"] > 0
        assert row["total_liabilities"] > 0
        assert "total_liabilities" not in row["derived_fields"]


def test_amzn_sga_uses_marketing_expense() -> None:
    """Amazon reports MarketingExpense and does not report the combined selling tag."""
    payload = _load(AMZN_FIXTURE)
    concepts = payload["facts"]["us-gaap"]
    assert "MarketingExpense" in concepts
    assert "SellingAndMarketingExpense" not in concepts
    assert "SellingGeneralAndAdministrativeExpense" not in concepts
    assert "ResearchAndDevelopmentExpense" not in concepts
    assert "Liabilities" not in concepts
    rows = {row["fiscal_year"]: row for row in normalize_company_facts(payload)}
    assert set(rows) == {2024, 2025}
    for period_end in ("2025-12-31", "2024-12-31"):
        revenue = _revenue_fact(payload, period_end)
        accession = revenue["accn"]
        sga = _resolve_sga(payload, period_end, accession)
        marketing = _own_year_fact(
            _unit_rows(payload, "MarketingExpense", "USD"), period_end, accession
        )
        admin = _own_year_fact(
            _unit_rows(payload, "GeneralAndAdministrativeExpense", "USD"),
            period_end,
            accession,
        )
        assert sga == marketing["val"] + admin["val"]
        assert sga > 0
        row = rows[int(period_end[:4])]
        assets = _own_year_fact(_unit_rows(payload, "Assets", "USD"), period_end, accession)
        equity = _own_year_fact(
            _unit_rows(payload, "StockholdersEquity", "USD"), period_end, accession
        )
        liabilities_and_equity = _own_year_fact(
            _unit_rows(payload, "LiabilitiesAndStockholdersEquity", "USD"),
            period_end,
            accession,
        )
        assert liabilities_and_equity["val"] == assets["val"]
        assert row["total_liabilities"] == assets["val"] - equity["val"]
        assert row["derived_fields"] == ("total_liabilities",)
        assert row["rd_expense"] is None
        shares = _own_year_fact(
            _unit_rows(payload, "CommonStockSharesOutstanding", "shares"),
            period_end,
            accession,
        )
        cover = [
            fact
            for fact in payload["facts"]["dei"]["EntityCommonStockSharesOutstanding"]["units"][
                "shares"
            ]
            if fact.get("fy") == int(period_end[:4]) and fact.get("form") == "10-K"
        ]
        assert len(cover) == 1
        assert cover[0]["end"] != period_end
        assert cover[0]["val"] != shares["val"]
        assert row["shares_outstanding"] == shares["val"]


def test_orcl_long_term_debt_uses_notes_payable() -> None:
    """Oracle's latest 10-K files noncurrent notes as LongTermNotesPayable."""
    payload = _load(ORCL_FIXTURE)
    concepts = payload["facts"]["us-gaap"]
    assert "LongTermDebtNoncurrent" not in concepts
    assert "LongTermNotesPayable" in concepts
    old_debt = _unit_rows(payload, "LongTermDebt", "USD")
    assert any(fact.get("end") == "2022-05-31" and fact.get("val") == 0 for fact in old_debt)
    assert "CostOfGoodsAndServicesSold" not in concepts
    rows = {row["fiscal_year"]: row for row in normalize_company_facts(payload)}
    assert set(rows) == {2025, 2026}
    for period_end in ("2026-05-31", "2025-05-31"):
        revenue = _revenue_fact(payload, period_end)
        accession = revenue["accn"]
        picked = _pick_value(
            payload,
            INSTANT_CONCEPTS["long_term_debt"],
            period_end,
            flow=False,
            unit="USD",
            accession=accession,
        )
        notes = _own_year_fact(
            _unit_rows(payload, "LongTermNotesPayable", "USD"), period_end, accession
        )
        assert picked is not None
        assert picked[0] == notes["val"]
        assert picked[0] > 0
        row = rows[int(period_end[:4])]
        assert row["long_term_debt"] == notes["val"]
        assert row["cogs"] is None
        assert "cogs" not in row["derived_fields"]
        costs = _own_year_fact(
            _unit_rows(payload, "CostsAndExpenses", "USD"), period_end, accession
        )
        assert costs["val"] > 0
        assert row["cogs"] != costs["val"]
        old_cost = [
            fact
            for fact in _unit_rows(payload, "CostOfRevenue", "USD")
            if fact.get("end") == period_end
        ]
        assert old_cost == []


def test_googl_prior_year_uses_the_own_10k_tag() -> None:
    """Alphabet's Revenues tag repeats 2024 inside the next 10-K. The own 10-K is the other tag."""
    payload = _load(GOOGL_FIXTURE)
    comparative = [
        fact
        for fact in _unit_rows(payload, "Revenues", "USD")
        if fact.get("end") == "2024-12-31" and _is_annual(fact)
    ]
    assert comparative
    assert all(fact.get("fy") != 2024 for fact in comparative)
    own = _own_year_fact(
        _unit_rows(payload, "RevenueFromContractWithCustomerExcludingAssessedTax", "USD"),
        "2024-12-31",
    )
    assert own["fy"] == 2024
    assert own["accn"] != comparative[0]["accn"]
    rows = {row["fiscal_year"]: row for row in normalize_company_facts(payload)}
    assert rows[2024]["accession"] == own["accn"]
    assert rows[2024]["revenue"] == own["val"]
    current = _own_year_fact(_unit_rows(payload, "Revenues", "USD"), "2025-12-31")
    assert rows[2025]["accession"] == current["accn"]
    assert rows[2025]["revenue"] == current["val"]


def test_pltr_omitted_long_term_debt_is_not_filled_with_zero() -> None:
    """Palantir's 2021 fact is zero. Later 10-Ks omit the tag. That zero is not reused."""
    payload = _load(PLTR_FIXTURE)
    debt = _unit_rows(payload, "LongTermDebtNoncurrent", "USD")
    assert any(fact.get("end") == "2021-12-31" and fact.get("val") == 0 for fact in debt)
    assert not any(fact.get("end") in {"2024-12-31", "2025-12-31"} for fact in debt)
    lease = _own_year_fact(
        _unit_rows(payload, "OperatingLeaseLiabilityNoncurrent", "USD"),
        "2025-12-31",
    )
    assert lease["val"] > 0
    rows = {row["fiscal_year"]: row for row in normalize_company_facts(payload)}
    assert set(rows) == {2024, 2025}
    for row in rows.values():
        assert row["long_term_debt"] is None
        assert row["long_term_debt"] != 0
        assert row["long_term_debt"] != lease["val"]
        assert "long_term_debt" not in row["derived_fields"]
        assert row["revenue"] > 0
        assert row["total_liabilities"] > 0


def test_incomplete_ticker_is_skipped_and_not_zero_filled(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from alphasentinel import ingestor

    original_rows = _rows_from_cache
    meta_gap = (
        "incomplete 10-K periods (2025-12-31: shares_outstanding; "
        "2024-12-31: shares_outstanding)"
    )

    def download(_cache_dir: Path, ticker: str) -> None:
        if ticker == "META":
            raise IngestError(meta_gap)
        if ticker != "AAPL":
            raise AssertionError(ticker)

    def rows(cache_dir: Path, ticker: str, *, offline: bool) -> list[dict]:
        if ticker == "META":
            raise AssertionError(
                f"failed ticker was loaded from {cache_dir} offline={offline}"
            )
        return original_rows(OFFLINE_CACHE, ticker, offline=True)

    monkeypatch.setattr(ingestor, "download_ticker", download)
    monkeypatch.setattr(ingestor, "_rows_from_cache", rows)
    database = tmp_path / "warehouse.duckdb"
    batch = ingest_tickers(
        ["AAPL", "META"],
        db_path=database,
        cache_dir=tmp_path / "cache",
        offline=False,
    )

    assert batch.written == 2
    assert batch.failures == (("META", meta_gap),)
    connection = get_duckdb_conn(database)
    try:
        tickers = connection.execute(
            "SELECT DISTINCT ticker FROM company_financials ORDER BY ticker"
        ).fetchall()
        shares = connection.execute(
            "SELECT MIN(shares_outstanding) FROM company_financials"
        ).fetchone()
    finally:
        connection.close()
    assert tickers == [("AAPL",)]
    assert shares is not None
    assert shares[0] > 0


def test_offline_without_cache_raises(tmp_path: Path) -> None:
    with pytest.raises(CacheMissError, match="offline cache miss"):
        ingest_tickers(["AAPL"], cache_dir=tmp_path, offline=True)


def test_cli_offline_without_cache_exits(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("alphasentinel.ingestor.DEFAULT_CACHE_DIR", tmp_path)
    assert main(["--tickers", "AAPL", "--offline"]) == 1


def _form4_open_market(xml: str) -> tuple[float, float, set[date], set[date]]:
    """Sum P and S shares from the fixture. Other codes are only used to pick a date."""
    root = ET.fromstring(xml)
    sold = 0.0
    bought = 0.0
    open_dates: set[date] = set()
    other_dates: set[date] = set()
    for transaction in root.iter("nonDerivativeTransaction"):
        when = date.fromisoformat(transaction.findtext("transactionDate/value"))
        code = transaction.findtext("transactionCoding/transactionCode", default="").strip()
        shares_text = transaction.findtext("transactionAmounts/transactionShares/value", default="")
        shares = float(shares_text.replace(",", ""))
        if code not in {"P", "S"}:
            other_dates.add(when)
            continue
        open_dates.add(when)
        side = transaction.findtext(
            "transactionAmounts/transactionAcquiredDisposedCode/value", default=""
        ).strip()
        if side == "D":
            sold += shares
        elif side == "A":
            bought += shares
    return sold, bought, open_dates, other_dates


def test_form4_ratio_counts_only_open_market_codes() -> None:
    xml = AAPL_FORM4.read_text(encoding="utf-8")
    sold, bought, open_dates, other_dates = _form4_open_market(xml)
    assert other_dates
    assert sold + bought > 0
    all_dates = open_dates | other_dates
    ratio = insider_net_sell_ratio(
        [xml], min(all_dates).isoformat(), max(all_dates).isoformat()
    )
    assert ratio == (sold - bought) / (sold + bought)
    quiet = min(other_dates - open_dates).isoformat()
    with pytest.raises(IngestError, match="no open-market"):
        insider_net_sell_ratio([xml], quiet, quiet)
