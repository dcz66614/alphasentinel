"""Forensic scores and the AI-Washing index.

Altman Z-Score
    Edward I. Altman, "Financial Ratios, Discriminant Analysis and the
    Prediction of Corporate Bankruptcy," Journal of Finance 23, no. 4 (1968):
    589-609. The 1968 paper enters the first four ratios as percentages
    (Z = 0.012 X1 + 0.014 X2 + 0.033 X3 + 0.006 X4 + 0.999 X5). The decimal
    form used here is the same model with those ratios entered as fractions
    and the sales coefficient rounded from 0.999 to 1.0:

        Z = 1.2 X1 + 1.4 X2 + 3.3 X3 + 0.6 X4 + 1.0 X5

    X1 = working capital / total assets
    X2 = retained earnings / total assets
    X3 = EBIT / total assets
    X4 = market value of equity / book value of total liabilities
    X5 = sales / total assets

    Zones from that paper: Z > 2.99 safe, Z < 1.81 distress, otherwise grey.
    Stored labels are SAFE, GREY, and DISTRESS.

Beneish M-Score
    Messod D. Beneish, "The Detection of Earnings Manipulation," Financial
    Analysts Journal 55, no. 5 (1999): 24-36. Eight-variable coefficients:

        M = -4.84 + 0.920 DSRI + 0.528 GMI + 0.404 AQI + 0.892 SGI
            + 0.115 DEPI - 0.172 SGAI + 4.679 TATA - 0.327 LVGI

    M > -1.78 is the screen cited for this coefficient set (Beneish 1999;
    Beneish, Lee, and Nichols 2013). Stored labels are MANIPULATION_RISK_HIGH
    and NORMAL. A score equal to -1.78 is NORMAL.

    Variable definitions follow Beneish (1999):

    DSRI = (receivables_t / sales_t) / (receivables_t-1 / sales_t-1)
    GMI = gross margin_t-1 / gross margin_t
          gross margin = (sales - COGS) / sales
    AQI = [1 - (current assets + net PPE) / total assets]_t
          / the same quantity at t-1
    SGI = sales_t / sales_t-1
    DEPI = depreciation rate_t-1 / depreciation rate_t
           depreciation rate = depreciation / (depreciation + net PPE)
    SGAI = (SG&A_t / sales_t) / (SG&A_t-1 / sales_t-1)
    LVGI = leverage_t / leverage_t-1
           leverage = (current liabilities + long-term debt) / total assets

    TATA uses the cash-flow accrual in Beneish, Lee, and Nichols, "Earnings
    Manipulation and Expected Returns," Financial Analysts Journal 69, no. 2
    (2013): 57-82, with the 1999 coefficients:

        TATA = (net income - cash flow from operations) / total assets

    The 1999 balance-sheet accrual also needs cash, income taxes payable, and
    the current portion of long-term debt. Those accounts are not in
    company_financials. They are not filled with zero. Net income is the
    stored NetIncomeLoss line. US GAAP no longer reports a separate
    extraordinary item, so none is invented.

    Asset quality does not subtract a securities balance. In the 1999
    definition, current assets already include current securities, and
    non-current securities stay inside the soft-asset residual.

Piotroski F-Score
    Joseph D. Piotroski, "Value Investing: The Use of Historical Financial
    Statement Information to Separate Winners from Losers," Journal of
    Accounting Research 38, no. 1 (2000): 1-41. Nine binary signals. Each is
    1 or 0. The score is their sum.

    ROA and cash flow from operations are scaled by beginning total assets
    (the prior fiscal year's total assets). Asset turnover uses the same
    beginning-assets base. Leverage is long-term debt over average total
    assets, and average assets are the mean of ending assets and beginning
    assets. Change in ROA, change in leverage, and change in turnover
    therefore need total assets from the year before the prior year. If that
    row is absent the F-score is NULL. A six-signal partial sum is not stored.

    The equity-offer signal in the paper is an equity-issuance indicator.
    This warehouse stores shares outstanding and not the cash proceeds from
    issuing stock. The signal is 1 when shares outstanding did not increase.
    Gross issuance that is offset by repurchases cannot be seen.

    Stored tiers are the task packet's labels, not the paper's portfolio
    bins: STRONG at 7 or above, MODERATE at 4 to 6, otherwise WEAK.

AI-Washing index
    Defined by the TASK-04 packet. It is not a published model. Hype is
    AI mentions per 10,000 words, times 1.45, clamped to 0-100. Realized
    ROI is 50 + 8 * the year-over-year change in EBIT margin (percentage
    points) + 1.2 * revenue growth (percent), clamped to 0-100. An insider
    net-sell ratio above 0.70 adds 20. The index is

        clamp(max(0, hype - 0.85 * roi) + insider penalty, 0, 100)

    60 and above is AI_WASHING_ALERT, 35 to 60 is WATCH, below 35 is
    VERIFIED_AI_ROI. The status uses the unrounded index. Stored figures
    are rounded.

Missing inputs
    A missing account, a missing prior fiscal year, or a denominator of
    exactly zero makes that metric NULL. Nothing is replaced with 0 or 1,
    interpolated, or carried forward. The text column next to a NULL
    headline score states the reason. forensic_scores metric columns are
    nullable for this reason. The original TASK-02 table marked them NOT
    NULL; init_db drops that constraint on an existing warehouse.
"""

from __future__ import annotations

import math
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from alphasentinel.db_schema import DEFAULT_DUCKDB_PATH, get_duckdb_conn, init_db

_BENEISH_COMPONENTS = ("dsri", "gmi", "aqi", "sgi", "depi", "sgai", "lvgi", "tata")

_SCORE_COLUMNS = (
    "ticker",
    "company_name",
    "sector",
    "fiscal_year",
    "data_source_mode",
    "altman_z_score",
    "altman_zone",
    "beneish_m_score",
    "beneish_flag",
    "piotroski_f_score",
    "piotroski_tier",
    "ebit_margin_pct",
    "ebit_margin_yoy_change_bps",
    "revenue_growth_yoy_pct",
    "rd_to_revenue_pct",
    "ai_hype_score",
    "ai_roi_realization_score",
    "ai_washing_score",
    "ai_washing_status",
    "dsri",
    "gmi",
    "aqi",
    "sgi",
    "depi",
    "sgai",
    "lvgi",
    "tata",
    "computed_at",
)

_NULL_REPORTS = (
    ("altman_z_score", "altman_zone"),
    ("beneish_m_score", "beneish_flag"),
    ("piotroski_f_score", "piotroski_tier"),
    ("ai_washing_score", "ai_washing_status"),
)

_INSERT_SQL = f"""
INSERT OR REPLACE INTO forensic_scores (
    {", ".join(_SCORE_COLUMNS)}
) VALUES (
    {", ".join("?" for _ in _SCORE_COLUMNS)}
)
"""


def _number(row: dict[str, Any] | None, key: str) -> float | None:
    if row is None or key not in row:
        return None
    value = row[key]
    if isinstance(value, bool) or value is None or isinstance(value, str):
        return None
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    if not math.isfinite(number):
        return None
    return number


def _missing(row: dict[str, Any] | None, keys: tuple[str, ...]) -> list[str]:
    return [key for key in keys if _number(row, key) is None]


def _year(row: dict[str, Any] | None) -> int | None:
    if row is None or "fiscal_year" not in row or row["fiscal_year"] is None:
        return None
    value = row["fiscal_year"]
    if isinstance(value, (bool, str)):
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _join(reasons: list[str]) -> str:
    return "; ".join(reason for reason in reasons if reason)


def _round(value: float | None, digits: int) -> float | None:
    if value is None:
        return None
    return round(value, digits)


def altman_z_from_ratios(x1: float, x2: float, x3: float, x4: float, x5: float) -> float:
    """Decimal form of Altman (1968). See the module docstring."""
    return 1.2 * x1 + 1.4 * x2 + 3.3 * x3 + 0.6 * x4 + 1.0 * x5


def altman_zone(z_score: float) -> str:
    """Map an Altman Z to SAFE, GREY, or DISTRESS. See the module docstring."""
    if z_score > 2.99:
        return "SAFE"
    if z_score >= 1.81:
        return "GREY"
    return "DISTRESS"


def beneish_m_from_components(
    dsri: float,
    gmi: float,
    aqi: float,
    sgi: float,
    depi: float,
    sgai: float,
    tata: float,
    lvgi: float,
) -> float:
    """Eight-variable Beneish (1999) M-score. See the module docstring."""
    return (
        -4.84
        + 0.920 * dsri
        + 0.528 * gmi
        + 0.404 * aqi
        + 0.892 * sgi
        + 0.115 * depi
        - 0.172 * sgai
        + 4.679 * tata
        - 0.327 * lvgi
    )


def beneish_flag(m_score: float) -> str:
    """M > -1.78 is the 1999 eight-variable screen. Equality stays NORMAL."""
    if m_score > -1.78:
        return "MANIPULATION_RISK_HIGH"
    return "NORMAL"


def piotroski_tier(f_score: int) -> str:
    """Task-packet tiers for a completed 0-9 Piotroski score."""
    if f_score >= 7:
        return "STRONG"
    if f_score >= 4:
        return "MODERATE"
    return "WEAK"


def ai_washing_status(score: float) -> str:
    """Task-packet bands. ``score`` is the unrounded index."""
    if score >= 60.0:
        return "AI_WASHING_ALERT"
    if score >= 35.0:
        return "WATCH"
    return "VERIFIED_AI_ROI"


def _clamp(value: float, low: float = 0.0, high: float = 100.0) -> float:
    return min(high, max(low, value))


def compute_altman_z(curr: dict[str, Any]) -> dict[str, Any]:
    """Altman (1968) Z and zone for one fiscal year. NULL when inputs are missing."""
    fields = (
        "working_capital",
        "retained_earnings",
        "ebit",
        "market_cap",
        "total_liabilities",
        "revenue",
        "total_assets",
    )
    missing = _missing(curr, fields)
    if missing:
        return {"altman_z_score": None, "altman_zone": "missing " + ", ".join(missing)}

    total_assets = _number(curr, "total_assets")
    total_liabilities = _number(curr, "total_liabilities")
    assert total_assets is not None and total_liabilities is not None
    problems: list[str] = []
    if total_assets == 0:
        problems.append("total_assets is zero")
    if total_liabilities == 0:
        problems.append("total_liabilities is zero")
    if problems:
        return {"altman_z_score": None, "altman_zone": _join(problems)}

    working_capital = _number(curr, "working_capital")
    retained = _number(curr, "retained_earnings")
    ebit = _number(curr, "ebit")
    market_cap = _number(curr, "market_cap")
    revenue = _number(curr, "revenue")
    assert None not in (working_capital, retained, ebit, market_cap, revenue)
    z_score = altman_z_from_ratios(
        working_capital / total_assets,  # type: ignore[operator]
        retained / total_assets,  # type: ignore[operator]
        ebit / total_assets,  # type: ignore[operator]
        market_cap / total_liabilities,  # type: ignore[operator]
        revenue / total_assets,  # type: ignore[operator]
    )
    return {"altman_z_score": round(z_score, 4), "altman_zone": altman_zone(z_score)}


def _pair_values(
    label: str,
    curr: dict[str, Any],
    prev: dict[str, Any],
    keys: tuple[str, ...],
) -> tuple[dict[str, float], dict[str, float]] | tuple[None, str]:
    missing_now = _missing(curr, keys)
    missing_then = _missing(prev, keys)
    if missing_now or missing_then:
        parts: list[str] = []
        if missing_now:
            parts.append("missing " + ", ".join(missing_now))
        if missing_then:
            parts.append("missing prior year " + ", ".join(missing_then))
        return None, f"{label}: {_join(parts)}"
    current = {key: _number(curr, key) for key in keys}
    previous = {key: _number(prev, key) for key in keys}
    assert all(value is not None for value in current.values())
    assert all(value is not None for value in previous.values())
    return (
        {key: float(value) for key, value in current.items() if value is not None},
        {key: float(value) for key, value in previous.items() if value is not None},
    )


def _dsri(
    curr: dict[str, Any], prev: dict[str, Any]
) -> tuple[float | None, str | None]:
    loaded = _pair_values("DSRI", curr, prev, ("receivables", "revenue"))
    if loaded[0] is None:
        return None, str(loaded[1])
    now, then = loaded
    assert isinstance(now, dict) and isinstance(then, dict)
    if now["revenue"] == 0 or then["revenue"] == 0:
        return None, "DSRI: revenue is zero"
    prior_ratio = then["receivables"] / then["revenue"]
    if prior_ratio == 0:
        return None, "DSRI: prior receivables over revenue is zero"
    return (now["receivables"] / now["revenue"]) / prior_ratio, None


def _gross_margin(sales: float, cogs: float) -> float | None:
    if sales == 0:
        return None
    return (sales - cogs) / sales


def _gmi(curr: dict[str, Any], prev: dict[str, Any]) -> tuple[float | None, str | None]:
    loaded = _pair_values("GMI", curr, prev, ("revenue", "cogs"))
    if loaded[0] is None:
        return None, str(loaded[1])
    now, then = loaded
    assert isinstance(now, dict) and isinstance(then, dict)
    margin_now = _gross_margin(now["revenue"], now["cogs"])
    margin_then = _gross_margin(then["revenue"], then["cogs"])
    if margin_now is None or margin_then is None:
        return None, "GMI: revenue is zero"
    if margin_now == 0:
        return None, "GMI: current gross margin is zero"
    return margin_then / margin_now, None


def _asset_quality(current_assets: float, ppe: float, total_assets: float) -> float | None:
    if total_assets == 0:
        return None
    return 1.0 - (current_assets + ppe) / total_assets


def _aqi(curr: dict[str, Any], prev: dict[str, Any]) -> tuple[float | None, str | None]:
    loaded = _pair_values("AQI", curr, prev, ("current_assets", "ppe", "total_assets"))
    if loaded[0] is None:
        return None, str(loaded[1])
    now, then = loaded
    assert isinstance(now, dict) and isinstance(then, dict)
    quality_now = _asset_quality(now["current_assets"], now["ppe"], now["total_assets"])
    quality_then = _asset_quality(then["current_assets"], then["ppe"], then["total_assets"])
    if quality_now is None or quality_then is None:
        return None, "AQI: total_assets is zero"
    if quality_then == 0:
        return None, "AQI: prior asset quality is zero"
    return quality_now / quality_then, None


def _sgi(curr: dict[str, Any], prev: dict[str, Any]) -> tuple[float | None, str | None]:
    loaded = _pair_values("SGI", curr, prev, ("revenue",))
    if loaded[0] is None:
        return None, str(loaded[1])
    now, then = loaded
    assert isinstance(now, dict) and isinstance(then, dict)
    if then["revenue"] == 0:
        return None, "SGI: prior revenue is zero"
    return now["revenue"] / then["revenue"], None


def _depreciation_rate(depreciation: float, ppe: float) -> float | None:
    base = ppe + depreciation
    if base == 0:
        return None
    return depreciation / base


def _depi(curr: dict[str, Any], prev: dict[str, Any]) -> tuple[float | None, str | None]:
    loaded = _pair_values("DEPI", curr, prev, ("depreciation", "ppe"))
    if loaded[0] is None:
        return None, str(loaded[1])
    now, then = loaded
    assert isinstance(now, dict) and isinstance(then, dict)
    rate_now = _depreciation_rate(now["depreciation"], now["ppe"])
    rate_then = _depreciation_rate(then["depreciation"], then["ppe"])
    if rate_now is None or rate_then is None:
        return None, "DEPI: depreciation plus PPE is zero"
    if rate_now == 0:
        return None, "DEPI: current depreciation rate is zero"
    return rate_then / rate_now, None


def _sgai(curr: dict[str, Any], prev: dict[str, Any]) -> tuple[float | None, str | None]:
    loaded = _pair_values("SGAI", curr, prev, ("sga", "revenue"))
    if loaded[0] is None:
        return None, str(loaded[1])
    now, then = loaded
    assert isinstance(now, dict) and isinstance(then, dict)
    if now["revenue"] == 0 or then["revenue"] == 0:
        return None, "SGAI: revenue is zero"
    prior_ratio = then["sga"] / then["revenue"]
    if prior_ratio == 0:
        return None, "SGAI: prior SG&A over revenue is zero"
    return (now["sga"] / now["revenue"]) / prior_ratio, None


def _leverage(current_liabilities: float, long_term_debt: float, total_assets: float) -> float | None:
    if total_assets == 0:
        return None
    return (current_liabilities + long_term_debt) / total_assets


def _lvgi(curr: dict[str, Any], prev: dict[str, Any]) -> tuple[float | None, str | None]:
    loaded = _pair_values(
        "LVGI", curr, prev, ("current_liabilities", "long_term_debt", "total_assets")
    )
    if loaded[0] is None:
        return None, str(loaded[1])
    now, then = loaded
    assert isinstance(now, dict) and isinstance(then, dict)
    leverage_now = _leverage(now["current_liabilities"], now["long_term_debt"], now["total_assets"])
    leverage_then = _leverage(
        then["current_liabilities"], then["long_term_debt"], then["total_assets"]
    )
    if leverage_now is None or leverage_then is None:
        return None, "LVGI: total_assets is zero"
    if leverage_then == 0:
        return None, "LVGI: prior leverage is zero"
    return leverage_now / leverage_then, None


def _tata(curr: dict[str, Any]) -> tuple[float | None, str | None]:
    missing = _missing(curr, ("net_income", "operating_cash_flow", "total_assets"))
    if missing:
        return None, "TATA: missing " + ", ".join(missing)
    total_assets = _number(curr, "total_assets")
    net_income = _number(curr, "net_income")
    cash_flow = _number(curr, "operating_cash_flow")
    assert total_assets is not None and net_income is not None and cash_flow is not None
    if total_assets == 0:
        return None, "TATA: total_assets is zero"
    return (net_income - cash_flow) / total_assets, None


def compute_beneish_m(
    curr: dict[str, Any], prev: dict[str, Any] | None
) -> dict[str, Any]:
    """Beneish (1999) eight-variable M-score. NULL when a ratio is undefined."""
    blank = {name: None for name in _BENEISH_COMPONENTS}
    raw: dict[str, float] = {}
    reasons: list[str] = []
    rounded: dict[str, float | None] = {}

    if prev is None:
        year = _year(curr)
        prior_year = year - 1 if year is not None else "prior"
        reasons.append(f"missing prior fiscal year {prior_year}")
        tata, tata_reason = _tata(curr)
        if tata_reason:
            reasons.append(tata_reason)
        return {
            "beneish_m_score": None,
            "beneish_flag": _join(reasons),
            **blank,
            "tata": _round(tata, 4),
        }

    calculators = (
        ("dsri", _dsri),
        ("gmi", _gmi),
        ("aqi", _aqi),
        ("sgi", _sgi),
        ("depi", _depi),
        ("sgai", _sgai),
        ("lvgi", _lvgi),
    )
    for name, calculator in calculators:
        value, reason = calculator(curr, prev)
        rounded[name] = _round(value, 4)
        if value is None:
            reasons.append(reason or f"{name}: undefined")
        else:
            raw[name] = value

    tata, tata_reason = _tata(curr)
    rounded["tata"] = _round(tata, 4)
    if tata is None:
        reasons.append(tata_reason or "TATA: undefined")
    else:
        raw["tata"] = tata

    result: dict[str, Any] = {"beneish_m_score": None, "beneish_flag": "", **blank, **rounded}
    if reasons:
        result["beneish_flag"] = _join(reasons)
        return result

    m_score = beneish_m_from_components(
        raw["dsri"],
        raw["gmi"],
        raw["aqi"],
        raw["sgi"],
        raw["depi"],
        raw["sgai"],
        raw["tata"],
        raw["lvgi"],
    )
    result["beneish_m_score"] = round(m_score, 4)
    result["beneish_flag"] = beneish_flag(m_score)
    return result


def _point(passed: bool) -> int:
    return 1 if passed else 0


def compute_piotroski_f(
    curr: dict[str, Any],
    prev: dict[str, Any] | None,
    prev2: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Piotroski (2000) nine-signal F-score. NULL unless all nine can be scored."""
    year = _year(curr)
    if prev is None:
        prior_year = year - 1 if year is not None else "prior"
        return {
            "piotroski_f_score": None,
            "piotroski_tier": f"missing prior fiscal year {prior_year}",
        }
    if prev2 is None:
        lagged_year = year - 2 if year is not None else "t-2"
        return {
            "piotroski_f_score": None,
            "piotroski_tier": (
                f"missing fiscal year {lagged_year} total_assets "
                "(Piotroski ROA, leverage, and asset turnover use beginning or average assets)"
            ),
        }

    reasons: list[str] = []
    current_fields = (
        "net_income",
        "operating_cash_flow",
        "total_assets",
        "long_term_debt",
        "current_assets",
        "current_liabilities",
        "shares_outstanding",
        "revenue",
        "cogs",
    )
    prior_fields = current_fields
    missing_now = _missing(curr, current_fields)
    missing_then = _missing(prev, prior_fields)
    missing_lag = _missing(prev2, ("total_assets", "net_income", "revenue", "long_term_debt"))
    if missing_now:
        reasons.append("missing " + ", ".join(missing_now))
    if missing_then:
        reasons.append("missing prior year " + ", ".join(missing_then))
    if missing_lag:
        reasons.append("missing year t-2 " + ", ".join(missing_lag))
    if reasons:
        return {"piotroski_f_score": None, "piotroski_tier": _join(reasons)}

    assets_now = _number(curr, "total_assets")
    assets_prev = _number(prev, "total_assets")
    assets_lag = _number(prev2, "total_assets")
    assert assets_now is not None and assets_prev is not None and assets_lag is not None
    if assets_prev == 0 or assets_lag == 0:
        return {
            "piotroski_f_score": None,
            "piotroski_tier": "beginning total_assets is zero",
        }
    average_now = (assets_now + assets_prev) / 2.0
    average_prev = (assets_prev + assets_lag) / 2.0
    if average_now == 0 or average_prev == 0:
        return {
            "piotroski_f_score": None,
            "piotroski_tier": "average total_assets is zero",
        }

    income_now = _number(curr, "net_income")
    income_prev = _number(prev, "net_income")
    cash_now = _number(curr, "operating_cash_flow")
    assert income_now is not None and income_prev is not None and cash_now is not None
    roa_now = income_now / assets_prev
    roa_prev = income_prev / assets_lag
    cash_scaled = cash_now / assets_prev

    liabilities_now = _number(curr, "current_liabilities")
    liabilities_prev = _number(prev, "current_liabilities")
    assert liabilities_now is not None and liabilities_prev is not None
    if liabilities_now == 0 or liabilities_prev == 0:
        return {
            "piotroski_f_score": None,
            "piotroski_tier": "current_liabilities is zero",
        }
    current_ratio_now = _number(curr, "current_assets") / liabilities_now  # type: ignore[operator]
    current_ratio_prev = _number(prev, "current_assets") / liabilities_prev  # type: ignore[operator]

    sales_now = _number(curr, "revenue")
    sales_prev = _number(prev, "revenue")
    assert sales_now is not None and sales_prev is not None
    if sales_now == 0 or sales_prev == 0:
        return {"piotroski_f_score": None, "piotroski_tier": "revenue is zero"}
    cogs_now = _number(curr, "cogs")
    cogs_prev = _number(prev, "cogs")
    assert cogs_now is not None and cogs_prev is not None
    margin_now = (sales_now - cogs_now) / sales_now
    margin_prev = (sales_prev - cogs_prev) / sales_prev
    turnover_now = sales_now / assets_prev
    turnover_prev = sales_prev / assets_lag

    debt_now = _number(curr, "long_term_debt")
    debt_prev = _number(prev, "long_term_debt")
    assert debt_now is not None and debt_prev is not None
    leverage_now = debt_now / average_now
    leverage_prev = debt_prev / average_prev

    shares_now = _number(curr, "shares_outstanding")
    shares_prev = _number(prev, "shares_outstanding")
    assert shares_now is not None and shares_prev is not None

    score = (
        _point(roa_now > 0)
        + _point(cash_scaled > 0)
        + _point(roa_now > roa_prev)
        + _point(cash_scaled > roa_now)
        + _point(leverage_now < leverage_prev)
        + _point(current_ratio_now > current_ratio_prev)
        + _point(shares_now <= shares_prev)
        + _point(margin_now > margin_prev)
        + _point(turnover_now > turnover_prev)
    )
    return {"piotroski_f_score": score, "piotroski_tier": piotroski_tier(score)}


def _margin_percent(
    row: dict[str, Any] | None, when: str
) -> tuple[float | None, str | None]:
    if row is None:
        return None, f"missing {when}"
    missing = _missing(row, ("ebit", "revenue"))
    if missing:
        return None, f"{when} missing " + ", ".join(missing)
    revenue = _number(row, "revenue")
    ebit = _number(row, "ebit")
    assert revenue is not None and ebit is not None
    if revenue == 0:
        return None, f"{when}: revenue is zero"
    return ebit * 100.0 / revenue, None


def compute_ai_washing_index(
    curr: dict[str, Any], prev: dict[str, Any] | None
) -> dict[str, Any]:
    """TASK-04 AI-Washing index. Each output is NULL when its own inputs are missing."""
    result: dict[str, Any] = {
        "ebit_margin_pct": None,
        "ebit_margin_yoy_change_bps": None,
        "revenue_growth_yoy_pct": None,
        "rd_to_revenue_pct": None,
        "ai_hype_score": None,
        "ai_roi_realization_score": None,
        "ai_washing_score": None,
        "ai_washing_status": "",
    }
    status_reasons: list[str] = []

    year = _year(curr)
    prior_label = f"prior fiscal year {year - 1}" if year is not None else "prior fiscal year"
    margin_now, margin_reason = _margin_percent(curr, "current year")
    result["ebit_margin_pct"] = _round(margin_now, 2)
    if margin_reason:
        status_reasons.append(margin_reason)

    margin_then, prior_margin_reason = _margin_percent(prev, prior_label)
    if margin_now is not None and margin_then is not None:
        delta_margin = margin_now - margin_then
        result["ebit_margin_yoy_change_bps"] = round(delta_margin * 100.0, 1)
    else:
        delta_margin = None
        if prior_margin_reason:
            status_reasons.append(prior_margin_reason)

    sales_now = _number(curr, "revenue")
    sales_prev = _number(prev, "revenue") if prev is not None else None
    if prev is None:
        growth = None
    elif sales_now is None or sales_prev is None:
        growth = None
        status_reasons.append("revenue growth: missing revenue")
    elif sales_prev == 0:
        growth = None
        status_reasons.append("revenue growth: prior revenue is zero")
    else:
        growth = (sales_now / sales_prev - 1.0) * 100.0
        result["revenue_growth_yoy_pct"] = round(growth, 2)

    rd_expense = _number(curr, "rd_expense")
    if rd_expense is None or sales_now is None:
        status_reasons.append("R&D ratio: missing rd_expense or revenue")
    elif sales_now == 0:
        status_reasons.append("R&D ratio: revenue is zero")
    else:
        result["rd_to_revenue_pct"] = round(rd_expense * 100.0 / sales_now, 2)

    mentions = _number(curr, "ai_mention_count")
    words = _number(curr, "total_word_count")
    hype: float | None = None
    if mentions is None or words is None:
        status_reasons.append("hype: missing ai_mention_count or total_word_count")
    elif words == 0:
        status_reasons.append("hype: total_word_count is zero")
    else:
        hype = _clamp(mentions * 10000.0 / words * 1.45)
        result["ai_hype_score"] = round(hype, 2)

    roi: float | None = None
    if delta_margin is not None and growth is not None:
        roi = _clamp(50.0 + 8.0 * delta_margin + 1.2 * growth)
        result["ai_roi_realization_score"] = round(roi, 2)

    insider = _number(curr, "insider_net_sell_ratio")
    if insider is None:
        status_reasons.append("missing insider_net_sell_ratio")
        penalty = None
    else:
        penalty = 20.0 if insider > 0.70 else 0.0

    if hype is None or roi is None or penalty is None:
        result["ai_washing_status"] = _join(status_reasons) or "AI-Washing inputs are incomplete"
        return result

    raw = _clamp(max(0.0, hype - 0.85 * roi) + penalty)
    result["ai_washing_score"] = round(raw, 2)
    result["ai_washing_status"] = ai_washing_status(raw)
    return result


def _index_by_year(rows: list[dict[str, Any]]) -> dict[int, dict[str, Any]]:
    indexed: dict[int, dict[str, Any]] = {}
    for row in rows:
        year = _year(row)
        if year is not None:
            indexed[year] = row
    return indexed


def _score_row(
    curr: dict[str, Any],
    prev: dict[str, Any] | None,
    prev2: dict[str, Any] | None,
    computed_at: str,
) -> dict[str, Any]:
    altman = compute_altman_z(curr)
    beneish = compute_beneish_m(curr, prev)
    piotroski = compute_piotroski_f(curr, prev, prev2)
    washing = compute_ai_washing_index(curr, prev)
    f_score = piotroski["piotroski_f_score"]
    return {
        "ticker": curr.get("ticker"),
        "company_name": curr.get("company_name"),
        "sector": curr.get("sector"),
        "fiscal_year": _year(curr),
        "data_source_mode": curr.get("data_source_mode"),
        "altman_z_score": altman["altman_z_score"],
        "altman_zone": altman["altman_zone"],
        "beneish_m_score": beneish["beneish_m_score"],
        "beneish_flag": beneish["beneish_flag"],
        "piotroski_f_score": None if f_score is None else int(f_score),
        "piotroski_tier": piotroski["piotroski_tier"],
        "ebit_margin_pct": washing["ebit_margin_pct"],
        "ebit_margin_yoy_change_bps": washing["ebit_margin_yoy_change_bps"],
        "revenue_growth_yoy_pct": washing["revenue_growth_yoy_pct"],
        "rd_to_revenue_pct": washing["rd_to_revenue_pct"],
        "ai_hype_score": washing["ai_hype_score"],
        "ai_roi_realization_score": washing["ai_roi_realization_score"],
        "ai_washing_score": washing["ai_washing_score"],
        "ai_washing_status": washing["ai_washing_status"],
        "dsri": beneish["dsri"],
        "gmi": beneish["gmi"],
        "aqi": beneish["aqi"],
        "sgi": beneish["sgi"],
        "depi": beneish["depi"],
        "sgai": beneish["sgai"],
        "lvgi": beneish["lvgi"],
        "tata": beneish["tata"],
        "computed_at": computed_at,
    }


def run_forensic_pipeline(db_path: Path | str | None = None) -> list[dict[str, Any]]:
    """Score the latest fiscal year of every ticker and upsert forensic_scores.

    A ticker with only one stored year is still written. Year-over-year metrics
    on that row are NULL, with the reason in the text column. Scores are not
    filled with zero.
    """
    database = Path(db_path) if db_path is not None else DEFAULT_DUCKDB_PATH
    init_db(database)
    connection = get_duckdb_conn(database)
    computed_at = datetime.now(UTC).isoformat()
    results: list[dict[str, Any]] = []
    try:
        tickers = [
            row[0]
            for row in connection.execute(
                "SELECT DISTINCT ticker FROM company_financials ORDER BY ticker"
            ).fetchall()
        ]
        for ticker in tickers:
            cursor = connection.execute(
                """
                SELECT * FROM company_financials
                WHERE ticker = ?
                ORDER BY fiscal_year
                """,
                [ticker],
            )
            names = [item[0] for item in cursor.description]
            rows = [dict(zip(names, values, strict=True)) for values in cursor.fetchall()]
            indexed = _index_by_year(rows)
            if not indexed:
                continue
            current_year = max(indexed)
            record = _score_row(
                indexed[current_year],
                indexed.get(current_year - 1),
                indexed.get(current_year - 2),
                computed_at,
            )
            connection.execute(_INSERT_SQL, [record[column] for column in _SCORE_COLUMNS])
            results.append(record)
    finally:
        connection.close()
    return results


def main() -> int:
    """Read the warehouse, write forensic_scores, and print NULL reasons."""
    results = run_forensic_pipeline()
    print(
        "[FORENSIC_ENGINE] Computed forensic & AI-Washing scores "
        f"for {len(results)} companies."
    )
    for record in results:
        for score_key, reason_key in _NULL_REPORTS:
            if record[score_key] is None:
                print(
                    "[FORENSIC_ENGINE] "
                    f"{record['ticker']} FY{record['fiscal_year']} "
                    f"{score_key} NULL: {record[reason_key]}"
                )
    return 0


if __name__ == "__main__":
    sys.exit(main())
