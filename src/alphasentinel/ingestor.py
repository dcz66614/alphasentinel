"""SEC EDGAR 10-K ingest for company_financials.

edgartools downloads company facts, submission indexes, 10-K documents, and
Form 4 XML. yfinance supplies the daily close used for market cap. Raw
responses are stored under data/cache/. Offline mode reads that cache and
stops if a downloaded file is missing.

SEC companyfacts tags `fy` with the filing's fiscal year, including comparative
columns. A period is the annual span ending on `end` (about 300 to 380 days).
The year's own 10-K is the fact whose `fy` equals that end year. Later filings
that repeat the same end are comparative columns and are not substituted.

No financial amount is filled in, carried forward, or scaled. A missing XBRL
concept, price, or insider trade raises IngestError.
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import os
import re
import sys
import xml.etree.ElementTree as ET
from datetime import date, datetime, timedelta
from html import unescape
from pathlib import Path
from typing import Any

from alphasentinel.db_schema import DEFAULT_DUCKDB_PATH, get_duckdb_conn, init_db

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_CACHE_DIR = PROJECT_ROOT / "data" / "cache"

# TASK-03 calls set_identity with this string when SEC_IDENTITY is unset.
SPEC_SEC_IDENTITY = "alphasentinel-bot@example.com"

# Spec packet stores two fiscal years per company.
MAX_ANNUAL_PERIODS = 2
MIN_ANNUAL_DAYS = 300
MAX_ANNUAL_DAYS = 380
PRICE_WINDOW_DAYS = 7
FORM4_FILING_LAG_DAYS = 7

AI_KEYWORDS_PATTERN = re.compile(
    r"\b(artificial intelligence|generative ai|agentic ai|large language model|"
    r"llm|gpu cluster|neural network|copilot)\b",
    re.IGNORECASE,
)

# Concept order is the XBRL line to read first. Names are tags, not amounts.
FLOW_CONCEPTS: dict[str, tuple[str, ...]] = {
    "revenue": (
        "Revenues",
        "RevenueFromContractWithCustomerExcludingAssessedTax",
        "SalesRevenueNet",
    ),
    "cogs": (
        "CostOfRevenue",
        "CostOfGoodsAndServicesSold",
        "CostOfGoodsSold",
    ),
    "rd_expense": ("ResearchAndDevelopmentExpense",),
    "depreciation": (
        "DepreciationDepletionAndAmortization",
        "DepreciationAndAmortization",
        "Depreciation",
    ),
    "ebit": ("OperatingIncomeLoss",),
    "net_income": ("NetIncomeLoss",),
    "operating_cash_flow": ("NetCashProvidedByUsedInOperatingActivities",),
}

INSTANT_CONCEPTS: dict[str, tuple[str, ...]] = {
    "receivables": (
        "AccountsReceivableNetCurrent",
        "AccountsReceivableNet",
    ),
    "current_assets": ("AssetsCurrent",),
    "ppe": (
        "PropertyPlantAndEquipmentNet",
        "PropertyPlantAndEquipmentAndFinanceLeaseRightOfUseAssetAfterAccumulatedDepreciationAndAmortization",
    ),
    "total_assets": ("Assets",),
    "current_liabilities": ("LiabilitiesCurrent",),
    "long_term_debt": (
        "LongTermDebtNoncurrent",
        "LongTermDebt",
    ),
    "total_liabilities": ("Liabilities",),
    "retained_earnings": ("RetainedEarningsAccumulatedDeficit",),
    "shares_outstanding": ("CommonStockSharesOutstanding",),
}

SGA_AGGREGATE = "SellingGeneralAndAdministrativeExpense"
SGA_SELLING = "SellingAndMarketingExpense"
SGA_ADMIN = "GeneralAndAdministrativeExpense"
LIABILITIES_CURRENT = "LiabilitiesCurrent"
LIABILITIES_NONCURRENT = "LiabilitiesNoncurrent"

_INSERT_SQL = """
INSERT OR REPLACE INTO company_financials (
    ticker, company_name, sector, fiscal_year, filing_form, filing_date,
    data_source_mode, revenue, cogs, sga, rd_expense, depreciation,
    ebit, net_income, operating_cash_flow, receivables, current_assets,
    ppe, total_assets, current_liabilities, long_term_debt, total_liabilities,
    retained_earnings, working_capital, shares_outstanding, market_cap,
    ai_mention_count, total_word_count, insider_net_sell_ratio
) VALUES (
    ?, ?, ?, ?, ?, ?,
    ?, ?, ?, ?, ?, ?,
    ?, ?, ?, ?, ?,
    ?, ?, ?, ?, ?,
    ?, ?, ?, ?,
    ?, ?, ?
)
"""


class IngestError(RuntimeError):
    """The ingest cannot continue from the files it has."""


class CacheMissError(IngestError):
    """Offline mode was asked to read a download that is not in the cache."""


def sec_identity() -> str:
    """Identity sent to SEC. SEC_IDENTITY wins; otherwise the spec default."""
    configured = os.environ.get("SEC_IDENTITY", "").strip()
    return configured or SPEC_SEC_IDENTITY


def configure_identity() -> str:
    """Register the SEC user agent with edgartools."""
    identity = sec_identity()
    from edgar import set_identity

    set_identity(identity)
    return identity


def parse_tickers(values: list[str]) -> list[str]:
    tickers: list[str] = []
    for value in values:
        for part in value.split(","):
            ticker = part.strip().upper()
            if ticker:
                tickers.append(ticker)
    if not tickers:
        raise IngestError("pass at least one ticker")
    for ticker in tickers:
        if not re.fullmatch(r"[A-Z][A-Z0-9.\-]{0,9}", ticker):
            raise IngestError(f"not a ticker symbol: {ticker}")
    return tickers


def _cache_root(cache_dir: Path, ticker: str) -> Path:
    return cache_dir / ticker.upper()


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_bytes(path: Path, payload: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(payload)


def _download_bytes(url: str) -> bytes:
    """Save the SEC response body. edgartools applies the identity and rate limit."""
    from edgar.httprequests import get_with_retry, inspect_response

    response = get_with_retry(url)
    inspect_response(response)
    content = response.content
    if content:
        return bytes(content)
    if response.text:
        return response.text.encode("utf-8")
    raise IngestError(f"empty response from {url}")


def _is_tenk(form: object) -> bool:
    return form in {"10-K", "10-K/A"}


def _period_days(fact: dict[str, Any]) -> int | None:
    start = fact.get("start")
    end = fact.get("end")
    if not start or not end:
        return None
    return (date.fromisoformat(end) - date.fromisoformat(start)).days


def _is_annual_flow(fact: dict[str, Any]) -> bool:
    if not _is_tenk(fact.get("form")):
        return False
    days = _period_days(fact)
    return days is not None and MIN_ANNUAL_DAYS <= days <= MAX_ANNUAL_DAYS


def _is_instant(fact: dict[str, Any]) -> bool:
    return _is_tenk(fact.get("form")) and not fact.get("start") and bool(fact.get("end"))


def _filed_key(fact: dict[str, Any]) -> tuple[str, str]:
    return (str(fact.get("filed") or ""), str(fact.get("accn") or ""))


def _choose_fact(
    candidates: list[dict[str, Any]],
    period_end: str,
    accession: str | None = None,
) -> dict[str, Any]:
    """Pick the fact for this period from the year's own 10-K when it exists."""
    if accession:
        same_filing = [fact for fact in candidates if fact.get("accn") == accession]
        if same_filing:
            return max(same_filing, key=_filed_key)
    end_year = int(period_end[:4])
    own_year = [fact for fact in candidates if fact.get("fy") == end_year]
    pool = own_year or candidates
    return max(pool, key=_filed_key)


def _concept_rows(payload: dict[str, Any], name: str, unit: str) -> list[dict[str, Any]]:
    node = payload.get("facts", {}).get("us-gaap", {}).get(name)
    if not node:
        return []
    rows = node.get("units", {}).get(unit, [])
    return rows if isinstance(rows, list) else []


def _pick_value(
    payload: dict[str, Any],
    names: tuple[str, ...],
    period_end: str,
    *,
    flow: bool,
    unit: str,
    accession: str | None,
) -> tuple[float, dict[str, Any]] | None:
    for name in names:
        rows = _concept_rows(payload, name, unit)
        if flow:
            candidates = [
                fact for fact in rows if fact.get("end") == period_end and _is_annual_flow(fact)
            ]
        else:
            candidates = [
                fact for fact in rows if fact.get("end") == period_end and _is_instant(fact)
            ]
        if not candidates:
            continue
        fact = _choose_fact(candidates, period_end, accession)
        if "val" not in fact:
            continue
        return float(fact["val"]), fact
    return None


def _annual_period_ends(payload: dict[str, Any]) -> list[str]:
    ends: set[str] = set()
    for name in FLOW_CONCEPTS["revenue"]:
        for fact in _concept_rows(payload, name, "USD"):
            if _is_annual_flow(fact) and fact.get("end"):
                ends.add(fact["end"])
    return sorted(ends, reverse=True)


def _resolve_sga(
    payload: dict[str, Any], period_end: str, accession: str | None
) -> float | None:
    direct = _pick_value(
        payload,
        (SGA_AGGREGATE,),
        period_end,
        flow=True,
        unit="USD",
        accession=accession,
    )
    if direct is not None:
        return direct[0]
    selling = _pick_value(
        payload, (SGA_SELLING,), period_end, flow=True, unit="USD", accession=accession
    )
    admin = _pick_value(
        payload, (SGA_ADMIN,), period_end, flow=True, unit="USD", accession=accession
    )
    if selling is None or admin is None:
        return None
    return selling[0] + admin[0]


def _resolve_total_liabilities(
    payload: dict[str, Any], period_end: str, accession: str | None
) -> float | None:
    direct = _pick_value(
        payload,
        INSTANT_CONCEPTS["total_liabilities"],
        period_end,
        flow=False,
        unit="USD",
        accession=accession,
    )
    if direct is not None:
        return direct[0]
    current = _pick_value(
        payload,
        (LIABILITIES_CURRENT,),
        period_end,
        flow=False,
        unit="USD",
        accession=accession,
    )
    noncurrent = _pick_value(
        payload,
        (LIABILITIES_NONCURRENT,),
        period_end,
        flow=False,
        unit="USD",
        accession=accession,
    )
    if current is None or noncurrent is None:
        return None
    return current[0] + noncurrent[0]


def _try_period(
    payload: dict[str, Any], period_end: str
) -> tuple[dict[str, Any] | None, list[str]]:
    revenue = _pick_value(
        payload,
        FLOW_CONCEPTS["revenue"],
        period_end,
        flow=True,
        unit="USD",
        accession=None,
    )
    if revenue is None:
        return None, ["revenue"]
    revenue_value, revenue_fact = revenue
    accession = str(revenue_fact.get("accn") or "")
    missing: list[str] = []
    values: dict[str, float] = {"revenue": revenue_value}

    for column, names in FLOW_CONCEPTS.items():
        if column == "revenue":
            continue
        picked = _pick_value(
            payload, names, period_end, flow=True, unit="USD", accession=accession
        )
        if picked is None:
            missing.append(column)
        else:
            values[column] = picked[0]

    sga = _resolve_sga(payload, period_end, accession)
    if sga is None:
        missing.append("sga")
    else:
        values["sga"] = sga

    for column, names in INSTANT_CONCEPTS.items():
        if column == "total_liabilities":
            continue
        unit = "shares" if column == "shares_outstanding" else "USD"
        picked = _pick_value(
            payload, names, period_end, flow=False, unit=unit, accession=accession
        )
        if picked is None:
            missing.append(column)
        else:
            values[column] = picked[0]

    liabilities = _resolve_total_liabilities(payload, period_end, accession)
    if liabilities is None:
        missing.append("total_liabilities")
    else:
        values["total_liabilities"] = liabilities

    if missing:
        return None, missing

    company_name = str(payload.get("entityName") or "").strip()
    if not company_name:
        return None, ["entityName"]
    start = revenue_fact.get("start")
    filed = revenue_fact.get("filed")
    form = revenue_fact.get("form")
    if not start or not filed or not form or not accession:
        return None, ["filing metadata"]

    values["working_capital"] = values["current_assets"] - values["current_liabilities"]
    record = {
        "company_name": company_name,
        "fiscal_year": int(period_end[:4]),
        "period_start": start,
        "period_end": period_end,
        "filing_form": form,
        "filing_date": filed,
        "accession": accession,
        **values,
    }
    return record, []


def normalize_company_facts(
    payload: dict[str, Any], *, max_years: int = MAX_ANNUAL_PERIODS
) -> list[dict[str, Any]]:
    """Map a SEC companyfacts document to annual 10-K rows.

    Raises IngestError when one of the latest annual periods is missing a
    required concept. Nothing is inserted as zero in that case.
    """
    ends = _annual_period_ends(payload)
    if not ends:
        raise IngestError("companyfacts has no annual 10-K revenue period")
    selected = ends[:max_years]
    records: list[dict[str, Any]] = []
    gaps: list[str] = []
    for period_end in selected:
        record, missing = _try_period(payload, period_end)
        if missing or record is None:
            gaps.append(f"{period_end}: {', '.join(missing)}")
            continue
        records.append(record)
    if gaps:
        detail = "; ".join(gaps)
        raise IngestError(f"incomplete 10-K periods ({detail})")
    records.sort(key=lambda row: row["fiscal_year"])
    return records


def _index_paths(index: dict[str, Any]) -> list[str]:
    paths = [index["companyfacts"], index["prices"], *index["submissions"]]
    for year in index["years"]:
        paths.append(year["filing"])
        paths.extend(year["form4"])
    return paths


def require_cache(cache_dir: Path, ticker: str) -> dict[str, Any]:
    """Return the cache index or raise when the download is not on disk."""
    root = _cache_root(cache_dir, ticker)
    index_path = root / "index.json"
    if not index_path.is_file():
        raise CacheMissError(
            f"offline cache miss for {ticker}: {index_path} is not a downloaded cache index"
        )
    index = _load_json(index_path)
    for relative in _index_paths(index):
        path = root / relative
        if not path.is_file() or path.stat().st_size == 0:
            raise CacheMissError(
                f"offline cache miss for {ticker}: {path} is not a downloaded file"
            )
    return index


def _filing_blocks(document: dict[str, Any]) -> list[dict[str, Any]]:
    if "accessionNumber" in document:
        return [document]
    recent = document.get("filings", {}).get("recent")
    if isinstance(recent, dict) and "accessionNumber" in recent:
        return [recent]
    return []


def _iter_filings(documents: list[dict[str, Any]]) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for document in documents:
        for block in _filing_blocks(document):
            accessions = block.get("accessionNumber") or []
            forms = block.get("form") or []
            dates = block.get("filingDate") or []
            primaries = block.get("primaryDocument") or []
            count = min(len(accessions), len(forms), len(dates), len(primaries))
            for index in range(count):
                rows.append(
                    {
                        "accession": accessions[index],
                        "form": forms[index],
                        "filing_date": dates[index],
                        "primary": primaries[index],
                    }
                )
    return rows


def _form4_xml_filename(primary: str) -> str:
    """SEC lists Form 4 as an XSL path; the ownership XML is the same filename."""
    filename = primary.rsplit("/", 1)[-1]
    if not filename.lower().endswith(".xml"):
        raise IngestError(f"Form 4 primary document {primary} is not an ownership XML name")
    return filename


def _archive_url(cik: int, accession: str, filename: str) -> str:
    from edgar.urls import build_archive_url

    accession_path = accession.replace("-", "")
    return build_archive_url(f"data/{cik}/{accession_path}/{filename}")


def _find_filing(documents: list[dict[str, Any]], accession: str) -> dict[str, str]:
    matches = [row for row in _iter_filings(documents) if row["accession"] == accession]
    if not matches:
        raise IngestError(f"submissions index has no filing {accession}")
    return matches[0]


def _form4_in_window(
    documents: list[dict[str, Any]], period_start: str, period_end: str
) -> list[dict[str, str]]:
    start = date.fromisoformat(period_start)
    end = date.fromisoformat(period_end) + timedelta(days=FORM4_FILING_LAG_DAYS)
    selected: list[dict[str, str]] = []
    seen: set[str] = set()
    for row in _iter_filings(documents):
        if row["form"] != "4":
            continue
        filed = date.fromisoformat(row["filing_date"])
        if filed < start or filed > end or row["accession"] in seen:
            continue
        if not row["primary"]:
            raise IngestError(f"Form 4 {row['accession']} has no primary document")
        seen.add(row["accession"])
        selected.append(row)
    if not selected:
        raise IngestError(
            f"no Form 4 filings between {period_start} and {end.isoformat()}"
        )
    return selected


def filing_plain_text(raw: str) -> str:
    """Drop inline XBRL header, scripts, and tags before counting words."""
    without_blocks = re.sub(
        r"(?is)<(script|style|ix:header)\b[^>]*>.*?</\1>",
        " ",
        raw,
    )
    without_tags = re.sub(r"(?s)<[^>]+>", " ", without_blocks)
    return unescape(without_tags)


def count_filing_text(raw: str) -> tuple[int, int]:
    plain = filing_plain_text(raw)
    words = re.findall(r"[A-Za-z0-9]+(?:'[A-Za-z0-9]+)?", plain)
    if not words:
        raise IngestError("10-K document has no words after tag removal")
    return len(AI_KEYWORDS_PATTERN.findall(plain)), len(words)


def _decode_text(payload: bytes) -> str:
    for encoding in ("utf-8", "latin-1"):
        try:
            return payload.decode(encoding)
        except UnicodeDecodeError:
            continue
    raise IngestError("filing bytes are not utf-8 or latin-1")


def _as_date(value: Any) -> date:
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    text = str(value).strip()
    if not text or text.lower() == "nat":
        raise IngestError("Form 4 transaction has no date")
    return date.fromisoformat(text[:10])


def _as_float(value: Any) -> float:
    if isinstance(value, str):
        value = value.replace(",", "").strip()
        if not value:
            raise IngestError("Form 4 share count is blank")
    number = float(value)
    if math.isnan(number):
        raise IngestError("Form 4 share count is missing")
    return number


def _xml_local_name(tag: str) -> str:
    if not isinstance(tag, str):
        return ""
    return tag.rsplit("}", 1)[-1]


def _xml_child(parent: ET.Element, name: str) -> ET.Element | None:
    for child in list(parent):
        if _xml_local_name(child.tag) == name:
            return child
    return None


def _xml_field_text(node: ET.Element | None) -> str:
    """Form 4 fields are either direct text or a nested value element."""
    if node is None:
        return ""
    value = _xml_child(node, "value")
    if value is not None and (value.text or "").strip():
        return value.text.strip()
    return (node.text or "").strip()


def _open_market_shares(xml: str, period_start: date, period_end: date) -> tuple[float, float]:
    """Count non-derivative codes P and S from a cached ownership XML document.

    edgartools Form4 parsing looks up the reporting owner and would call SEC.
    This walk stays on the file already stored under data/cache.
    """
    try:
        root = ET.fromstring(xml.lstrip("\ufeff"))
    except ET.ParseError as exc:
        raise IngestError(f"Form 4 XML could not be parsed: {exc}") from exc
    if _xml_local_name(root.tag) != "ownershipDocument":
        raise IngestError("Form 4 XML has no ownershipDocument root")

    sold = 0.0
    bought = 0.0
    for transaction in root.iter():
        if _xml_local_name(transaction.tag) != "nonDerivativeTransaction":
            continue
        coding = _xml_child(transaction, "transactionCoding")
        code_node = _xml_child(coding, "transactionCode") if coding is not None else None
        code = _xml_field_text(code_node).upper()
        if code not in {"P", "S"}:
            continue
        when = _as_date(_xml_field_text(_xml_child(transaction, "transactionDate")))
        if when < period_start or when > period_end:
            continue
        amounts = _xml_child(transaction, "transactionAmounts")
        if amounts is None:
            raise IngestError("Form 4 open-market trade has no transactionAmounts")
        shares = _as_float(_xml_field_text(_xml_child(amounts, "transactionShares")))
        if shares < 0:
            raise IngestError("Form 4 reports a negative share count")
        side = _xml_field_text(_xml_child(amounts, "transactionAcquiredDisposedCode")).upper()
        if side == "D":
            sold += shares
        elif side == "A":
            bought += shares
        else:
            raise IngestError(f"Form 4 AcquiredDisposed is {side!r}")
    return sold, bought


def insider_net_sell_ratio(xml_documents: list[str], period_start: str, period_end: str) -> float:
    """(shares sold - shares bought) / (shares sold + shares bought) for code P and S."""
    start = date.fromisoformat(period_start)
    end = date.fromisoformat(period_end)
    sold = 0.0
    bought = 0.0
    for xml in xml_documents:
        filing_sold, filing_bought = _open_market_shares(xml, start, end)
        sold += filing_sold
        bought += filing_bought
    total = sold + bought
    if total == 0:
        raise IngestError(
            f"no open-market Form 4 buys or sells between {period_start} and {period_end}"
        )
    return (sold - bought) / total


def _read_prices(path: Path) -> list[tuple[date, float]]:
    prices: list[tuple[date, float]] = []
    with path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        if not reader.fieldnames or "Close" not in reader.fieldnames:
            raise IngestError(f"price cache {path} has no Close column")
        date_key = "Date" if "Date" in reader.fieldnames else reader.fieldnames[0]
        for row in reader:
            raw_date = (row.get(date_key) or "").strip()
            raw_close = (row.get("Close") or "").strip()
            if not raw_date or not raw_close or raw_close.lower() == "nan":
                continue
            prices.append((date.fromisoformat(raw_date[:10]), float(raw_close)))
    if not prices:
        raise IngestError(f"price cache {path} has no closes")
    return prices


def market_cap_from_prices(
    prices: list[tuple[date, float]], period_end: str, shares_outstanding: float
) -> float:
    """Close on the last session on or before period end, times reported shares."""
    if shares_outstanding <= 0:
        raise IngestError(f"shares outstanding for {period_end} are not positive")
    end = date.fromisoformat(period_end)
    eligible = [(session, close) for session, close in prices if session <= end and close > 0]
    if not eligible:
        raise IngestError(f"no positive close on or before {period_end}")
    session, close = max(eligible)
    if (end - session).days > PRICE_WINDOW_DAYS:
        raise IngestError(
            f"nearest close for {period_end} is {session.isoformat()}, outside "
            f"{PRICE_WINDOW_DAYS} days"
        )
    return close * shares_outstanding


def _download_prices(ticker: str, path: Path, records: list[dict[str, Any]]) -> None:
    import warnings

    import yfinance as yf

    start = min(date.fromisoformat(row["period_start"]) for row in records) - timedelta(days=14)
    end = max(date.fromisoformat(row["period_end"]) for row in records) + timedelta(days=7)
    with warnings.catch_warnings():
        warnings.filterwarnings("ignore", message="The inplace keyword")
        frame = yf.Ticker(ticker).history(
            start=start.isoformat(),
            end=(end + timedelta(days=1)).isoformat(),
            auto_adjust=False,
        )
    if frame is None or frame.empty:
        raise IngestError(f"{ticker}: yfinance returned no prices")
    path.parent.mkdir(parents=True, exist_ok=True)
    frame.to_csv(path)


def download_ticker(cache_dir: Path, ticker: str) -> None:
    """Download raw SEC and price files, then write index.json."""
    configure_identity()
    from edgar import Company
    from edgar.exceptions import CompanyNotFoundError
    from edgar.urls import build_company_facts_url, build_submissions_url

    try:
        company = Company(ticker)
    except CompanyNotFoundError as exc:
        raise IngestError(f"SEC has no company for ticker {ticker}") from exc
    cik = int(company.cik)
    root = _cache_root(cache_dir, ticker)

    facts_url = build_company_facts_url(cik)
    print(f"[INGESTOR] {ticker}: downloading {facts_url}")
    facts_rel = "companyfacts.json"
    _write_bytes(root / facts_rel, _download_bytes(facts_url))
    payload = _load_json(root / facts_rel)
    records = normalize_company_facts(payload)

    submissions_url = build_submissions_url(cik)
    main_rel = f"submissions/CIK{cik:010d}.json"
    print(f"[INGESTOR] {ticker}: downloading {submissions_url}")
    _write_bytes(root / main_rel, _download_bytes(submissions_url))
    main_doc = _load_json(root / main_rel)
    submission_rels = [main_rel]
    submission_urls = [submissions_url]
    for extra in main_doc.get("filings", {}).get("files") or []:
        name = extra.get("name")
        if not name:
            continue
        extra_url = f"https://data.sec.gov/submissions/{name}"
        extra_rel = f"submissions/{name}"
        _write_bytes(root / extra_rel, _download_bytes(extra_url))
        submission_rels.append(extra_rel)
        submission_urls.append(extra_url)

    documents = [_load_json(root / relative) for relative in submission_rels]
    years_index: list[dict[str, Any]] = []
    for record in records:
        filing = _find_filing(documents, record["accession"])
        filing_rel = f"filings/{record['accession']}/{filing['primary']}"
        filing_url = _archive_url(cik, record["accession"], filing["primary"])
        print(f"[INGESTOR] {ticker} FY{record['fiscal_year']}: downloading {filing_url}")
        _write_bytes(root / filing_rel, _download_bytes(filing_url))

        form4_rows = _form4_in_window(documents, record["period_start"], record["period_end"])
        form4_rels: list[str] = []
        print(
            f"[INGESTOR] {ticker} FY{record['fiscal_year']}: "
            f"{len(form4_rows)} Form 4 filings"
        )
        for offset, row in enumerate(form4_rows, start=1):
            relative = f"ownership/{row['accession']}.xml"
            url = _archive_url(cik, row["accession"], _form4_xml_filename(row["primary"]))
            _write_bytes(root / relative, _download_bytes(url))
            form4_rels.append(relative)
            if offset == len(form4_rows) or offset % 25 == 0:
                print(f"[INGESTOR] {ticker} FY{record['fiscal_year']}: Form 4 {offset}")
        years_index.append(
            {
                "fiscal_year": record["fiscal_year"],
                "period_start": record["period_start"],
                "period_end": record["period_end"],
                "accession": record["accession"],
                "filing": filing_rel,
                "form4": form4_rels,
            }
        )

    prices_rel = "prices.csv"
    print(f"[INGESTOR] {ticker}: downloading yfinance closes")
    _download_prices(ticker, root / prices_rel, records)

    index = {
        "ticker": ticker,
        "cik": cik,
        "companyfacts": facts_rel,
        "companyfacts_url": facts_url,
        "submissions": submission_rels,
        "submissions_urls": submission_urls,
        "prices": prices_rel,
        "prices_source": "yfinance.Ticker.history auto_adjust=false",
        "years": years_index,
    }
    (root / "index.json").write_text(json.dumps(index, indent=2), encoding="utf-8")


def _sector_from_submissions(root: Path, index: dict[str, Any]) -> str:
    document = _load_json(root / index["submissions"][0])
    sector = str(document.get("sicDescription") or "").strip()
    if not sector:
        raise IngestError(f"{index['ticker']}: submissions file has no sicDescription")
    return sector


def _rows_from_cache(cache_dir: Path, ticker: str, *, offline: bool) -> list[dict[str, Any]]:
    index = require_cache(cache_dir, ticker)
    root = _cache_root(cache_dir, ticker)
    payload = _load_json(root / index["companyfacts"])
    records = normalize_company_facts(payload)
    cached_ends = {year["period_end"] for year in index["years"]}
    normalized_ends = {record["period_end"] for record in records}
    if cached_ends != normalized_ends:
        raise CacheMissError(
            f"offline cache for {ticker} does not cover companyfacts periods "
            f"{sorted(normalized_ends)}"
        )
    by_end = {year["period_end"]: year for year in index["years"]}
    sector = _sector_from_submissions(root, index)
    prices = _read_prices(root / index["prices"])
    mode = "CACHE_SEC" if offline else "LIVE_HYBRID_SEC_YF"
    rows: list[dict[str, Any]] = []
    for record in records:
        year = by_end[record["period_end"]]
        filing_bytes = (root / year["filing"]).read_bytes()
        ai_count, word_count = count_filing_text(_decode_text(filing_bytes))
        xml_documents = [
            _decode_text((root / relative).read_bytes()) for relative in year["form4"]
        ]
        ratio = insider_net_sell_ratio(
            xml_documents, record["period_start"], record["period_end"]
        )
        market_cap = market_cap_from_prices(
            prices, record["period_end"], record["shares_outstanding"]
        )
        rows.append(
            {
                **record,
                "ticker": ticker,
                "sector": sector,
                "data_source_mode": mode,
                "market_cap": market_cap,
                "ai_mention_count": ai_count,
                "total_word_count": word_count,
                "insider_net_sell_ratio": ratio,
            }
        )
    return rows


def _insert_rows(db_path: Path, rows: list[dict[str, Any]]) -> int:
    init_db(db_path)
    connection = get_duckdb_conn(db_path)
    try:
        for row in rows:
            connection.execute(
                _INSERT_SQL,
                [
                    row["ticker"],
                    row["company_name"],
                    row["sector"],
                    int(row["fiscal_year"]),
                    row["filing_form"],
                    row["filing_date"],
                    row["data_source_mode"],
                    float(row["revenue"]),
                    float(row["cogs"]),
                    float(row["sga"]),
                    float(row["rd_expense"]),
                    float(row["depreciation"]),
                    float(row["ebit"]),
                    float(row["net_income"]),
                    float(row["operating_cash_flow"]),
                    float(row["receivables"]),
                    float(row["current_assets"]),
                    float(row["ppe"]),
                    float(row["total_assets"]),
                    float(row["current_liabilities"]),
                    float(row["long_term_debt"]),
                    float(row["total_liabilities"]),
                    float(row["retained_earnings"]),
                    float(row["working_capital"]),
                    float(row["shares_outstanding"]),
                    float(row["market_cap"]),
                    int(row["ai_mention_count"]),
                    int(row["total_word_count"]),
                    float(row["insider_net_sell_ratio"]),
                ],
            )
    finally:
        connection.close()
    return len(rows)


def ingest_tickers(
    tickers: list[str],
    db_path: Path | None = None,
    cache_dir: Path | None = None,
    offline: bool = False,
) -> int:
    """Load 10-K rows into DuckDB. Offline never calls the network."""
    symbols = parse_tickers(tickers)
    cache = Path(cache_dir) if cache_dir is not None else DEFAULT_CACHE_DIR
    database = Path(db_path) if db_path is not None else DEFAULT_DUCKDB_PATH
    if offline:
        for symbol in symbols:
            require_cache(cache, symbol)
    else:
        for symbol in symbols:
            download_ticker(cache, symbol)
    written = 0
    for symbol in symbols:
        rows = _rows_from_cache(cache, symbol, offline=offline)
        written += _insert_rows(database, rows)
    return written


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Ingest SEC 10-K financials into DuckDB")
    parser.add_argument("--tickers", nargs="+", required=True, help="Ticker symbols")
    parser.add_argument(
        "--offline",
        action="store_true",
        help="Read data/cache only. Missing cache is an error.",
    )
    args = parser.parse_args(argv)
    try:
        count = ingest_tickers(args.tickers, offline=args.offline)
    except IngestError as exc:
        print(f"[INGESTOR] {exc}", file=sys.stderr)
        return 1
    print(f"[INGESTOR] Successfully ingested {count} company-year financial records into DuckDB.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
