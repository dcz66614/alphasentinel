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

from alphasentinel.ingestor import (
    SPEC_SEC_IDENTITY,
    CacheMissError,
    IngestError,
    ingest_tickers,
    insider_net_sell_ratio,
    main,
    normalize_company_facts,
    sec_identity,
)

FIXTURES = Path(__file__).parent / "fixtures"
AAPL_FIXTURE = FIXTURES / "aapl_companyfacts_excerpt.json"
MSFT_FIXTURE = FIXTURES / "msft_companyfacts_excerpt.json"
AAPL_FORM4 = FIXTURES / "aapl_form4_0000320193-23-000088.xml"

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
